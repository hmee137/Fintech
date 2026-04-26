"""
============================================================
SIGNAL SCANNER BOT - Phần B v2
============================================================

CHỨC NĂNG:
    - Quét song song 20 cặp USDT-M Perpetual trên MEXC Futures
    - Tính 4 alpha độc lập cho mỗi cặp
    - Phát tín hiệu LONG/SHORT khi có đồng thuận giữa các alpha
    - Báo qua Telegram + log ra console + ghi CSV
    - KHÔNG đặt lệnh - sinh viên tự vào MEXC web đặt tay

LIÊN HỆ BÀI GIẢNG:
    - Bai 7.3 / 7.4: 2 alpha cơ bản (Momentum, Mean Reversion)
    - Bai 7.3.2:    Portfolio of Alphas (combine 4 alpha) + 2 alpha nâng cao (Funding, OI Divergence)
    - Bai 7.5.3:    Bot là trợ lý, con người giữ quyền quyết định cuối cùng

CHẠY:
    cd phan_b_v2
    python scanner_bot.py
"""

import os
import sys
import time
import csv
import logging
import signal as sig_module
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import notifier
from signals import combine_signals
from adapters import MEXCFuturesAdapter


# ============================================================
# SETUP
# ============================================================

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("Scanner")
VN_TZ = timezone(timedelta(hours=7))


# ============================================================
# SIGNAL LOGGER (CSV)
# ============================================================

class SignalLogger:
    """Ghi mỗi tín hiệu đã phát ra CSV - phục vụ phân tích + báo cáo."""

    COLS = ["timestamp_vn", "symbol", "final_signal", "score", "confidence",
            "price", "funding_rate_pct", "rise_fall_24h_pct",
            "momentum_signal", "momentum_reason",
            "mean_revert_signal", "mean_revert_reason",
            "funding_signal", "funding_reason",
            "oi_signal", "oi_reason"]

    def __init__(self, path: str):
        self.path = path
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.COLS)

    def log(self, result: dict, ticker: dict):
        a = result["alphas"]
        row = [
            datetime.now(VN_TZ).isoformat(),
            result["symbol"], result["final_signal"],
            result["score"], result["confidence"],
            ticker.get("last", 0),
            ticker.get("funding_rate", 0) * 100,
            ticker.get("rise_fall_rate", 0),
            a[0]["signal"], a[0]["reason"],
            a[1]["signal"], a[1]["reason"],
            a[2]["signal"], a[2]["reason"],
            a[3]["signal"], a[3]["reason"],
        ]
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)


# ============================================================
# SCANNER BOT
# ============================================================

class ScannerBot:

    def __init__(self):
        self.exchange = MEXCFuturesAdapter()
        self.signal_log = SignalLogger(config.SIGNALS_FILE)
        self.running = True
        # Trạng thái tín hiệu trước đó từng cặp -> tránh spam
        self.last_signal = {sym: "NEUTRAL" for sym in config.WATCHLIST}

        # Graceful shutdown
        sig_module.signal(sig_module.SIGINT,  self._shutdown)
        sig_module.signal(sig_module.SIGTERM, self._shutdown)

    def _shutdown(self, *_):
        log.info("Nhận tín hiệu dừng. Thoát...")
        self.running = False
        notifier.send_shutdown()
        sys.exit(0)

    def _analyze_one(self, symbol: str, all_tickers: dict):
        """
        Phân tích 1 cặp. Trả về (result, ticker) hoặc None nếu lỗi.
        Được gọi trong ThreadPoolExecutor để chạy song song.
        """
        try:
            ticker = all_tickers.get(symbol)
            if not ticker:
                # Fallback: goi rieng
                ticker = self.exchange.get_ticker(symbol)
            if not ticker or ticker.get("last", 0) == 0:
                return None

            df = self.exchange.fetch_klines(
                symbol, config.TIMEFRAME, config.KLINE_LIMIT
            )
            if df.empty:
                return None

            result = combine_signals(
                df, symbol, ticker, threshold=config.SIGNAL_THRESHOLD
            )
            return (result, ticker)
        except Exception as e:
            log.error(f"[{symbol}] error: {e}")
            return None

    def _scan_once(self):
        """Quét 1 vòng của tất cả symbol."""
        now_vn = datetime.now(VN_TZ).strftime("%H:%M:%S - %d/%m/%Y")
        log.info(f"=== Scan @ {now_vn} VN ===")

        # Lấy all_tickers 1 lần (1 request thay vì 20)
        try:
            all_tickers = self.exchange.get_all_tickers()
        except Exception as e:
            log.error(f"Không lấy được tickers: {e}")
            return

        # Chạy song song 5 thread
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
            futures = {
                ex.submit(self._analyze_one, sym, all_tickers): sym
                for sym in config.WATCHLIST
            }
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    results.append(res)

        # Sort theo abs(score) giảm dần -> tín hiệu mạnh nhất lên đầu
        results.sort(key=lambda r: abs(r[0]["score"]), reverse=True)

        # Hiển thị summary toàn bộ + gửi Telegram cho tín hiệu mạnh
        new_signals = 0
        for result, ticker in results:
            sym  = result["symbol"]
            sig  = result["final_signal"]
            sc   = result["score"]

            # Console: hiển thị 1 dòng gói gọn + mũi tên lên/xuống/đứng
            arrow = "▲" if sig == "LONG" else ("▼" if sig == "SHORT" else "─")
            log.info(f"  {arrow} {sym:12s} {sig:7s} score={sc:+.2f} "
                     f"conf={result['confidence']:.0%}")

            # Chỉ gửi Telegram + log CSV cho tín hiệu MỚI (đồng thời reset state nếu đã về NEUTRAL)
            if sig != "NEUTRAL" and sig != self.last_signal.get(sym):
                self.signal_log.log(result, ticker)
                msg = notifier.format_signal(result, ticker, now_vn)
                if msg:
                    notifier.send(msg)
                self.last_signal[sym] = sig
                new_signals += 1
            elif sig == "NEUTRAL":
                # Reset state để lần sau có LONG/SHORT mới sẽ được gửi
                self.last_signal[sym] = "NEUTRAL"

        if new_signals > 0:
            log.info(f"=== Da phat {new_signals} tin hieu MOI ===")

    def run(self):
        log.info("=" * 60)
        log.info(f"SIGNAL SCANNER BOT v2 START")
        log.info(f"Quet: {len(config.WATCHLIST)} cap | TF: {config.TIMEFRAME}")
        log.info(f"Alpha: 4 (Momentum, MeanRevert, Funding, OI Divergence)")
        log.info(f"Quet moi {config.SCAN_INTERVAL_SEC}s")
        log.info("=" * 60)
        notifier.send_startup(len(config.WATCHLIST), 4)

        # Loop chính: quét liên tục với khoảng nghỉ giữa các vòng
        while self.running:
            try:
                self._scan_once()
                time.sleep(config.SCAN_INTERVAL_SEC)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception(f"Loop error: {e}")
                time.sleep(30)

        log.info("Bot stopped.")


if __name__ == "__main__":
    ScannerBot().run()
