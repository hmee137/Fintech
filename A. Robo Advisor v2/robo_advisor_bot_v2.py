"""
============================================================
ROBO-ADVISOR TELEGRAM BOT  v2.0
Fintech Midterm - Phan A
Author: Phu Thien
============================================================

LIEN HE BAI GIANG:
    - Bai 7.3.1: Trich xuat tin hieu Alpha tu Market Data
                 (Momentum, Realized Volatility, Volume spike)
    - Bai 7.3.2: Portfolio of Alphas - ket hop nhieu tin hieu
                 doc lap thanh tin hieu tong hop manh hon.
    - Bai 7.4.1: Chien luoc giao dich thuat toan co ban
                 (Mean Reversion voi Bollinger, Momentum voi EMA)

LOGIC TIN HIEU:
    Bot khong dua ra 1 tin hieu don le, ma TONG HOP 4 tin hieu:
        (1) Xu huong (Trend)        : EMA9 vs EMA21
        (2) Dong luong (Momentum)   : MACD cat tin hieu
        (3) Qua mua/ban (Oscillator): RSI
        (4) Khoi luong (Volume)     : so voi SMA20 cua volume

    -> Ra quyet dinh tong hop:
        STRONG_BUY / BUY / CONSIDER_BUY / SIDEWAYS
        CONSIDER_SELL / SELL / STRONG_SELL

CHAY:
    python robo_advisor_bot_v2.py
"""

import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


# ============================================================
# [1] CONFIG
# ============================================================

# --- Telegram ---
TELEGRAM_TOKEN = "8689397744:AAF6gw6JFpjpevd3sjlJZ4zy1N5-7TkF7xQ"
TELEGRAM_CHAT_ID = "8596078554"

# --- Whitelist dung dinh dang Bitget: {TICKER}ONUSDT ---
# Toan bo 54 token tokenized stocks trong de thi (Muc A.5)
WATCHLIST = [
    "NVDAONUSDT", "BTCUSDT", "XAUTUSDT"
]

# --- Tham so ---
TIMEFRAME       = "15min"     # 1min, 5min, 15min, 1h, 4h, 1day
CANDLE_LIMIT    = 100
CHECK_INTERVAL  = 60          # giay giua 2 lan quet

# Indicator params
RSI_PERIOD      = 14
EMA_FAST        = 9
EMA_SLOW        = 21
MACD_FAST       = 12
MACD_SLOW       = 26
MACD_SIGNAL     = 9
BB_PERIOD       = 20
BB_STD          = 2
VOL_SMA_PERIOD  = 20

# Timezone Viet Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


# ============================================================
# [2] BITGET API
# ============================================================

BITGET_BASE = "https://api.bitget.com"

def fetch_symbols():
    """Lay danh sach tat ca symbol spot tren Bitget."""
    try:
        r = requests.get(f"{BITGET_BASE}/api/v2/spot/public/symbols", timeout=10)
        return {item["symbol"] for item in r.json().get("data", [])}
    except Exception as e:
        print(f"[ERROR] fetch_symbols: {e}")
        return set()


def fetch_candles(symbol, granularity="15min", limit=100):
    """
    Lay nen OHLCV tu Bitget.
    Response format: [ts_ms, open, high, low, close, baseVol, quoteVol, usdtVol]
    """
    url = f"{BITGET_BASE}/api/v2/spot/market/candles"
    params = {"symbol": symbol, "granularity": granularity, "limit": str(limit)}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json().get("data", [])
        if not data:
            return None
        df = pd.DataFrame(data, columns=[
            "ts", "open", "high", "low", "close",
            "baseVol", "quoteVol", "usdtVol"
        ])
        for col in ["open", "high", "low", "close",
                    "baseVol", "quoteVol", "usdtVol"]:
            df[col] = df[col].astype(float)
        df["ts"] = pd.to_datetime(df["ts"].astype(np.int64), unit="ms")
        df = df.sort_values("ts").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[ERROR] fetch_candles {symbol}: {e}")
        return None


# ============================================================
# [3] INDICATORS  (tham chieu Bai 7.3.1 + 7.4.1)
# ============================================================

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI = 100 - 100/(1+RS),  RS = avg_gain/avg_loss trong 'period' nen."""
    delta = close.diff() #thay đổi giá giữa các nến liên tiếp   
    gain = delta.where(delta > 0, 0.0).rolling(period).mean() #tính trung bình cộng của các giá trị tăng dương trong khoảng thời gian 'period'
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean() #tính trung bình cộng của các giá trị giảm âm trong khoảng thời gian 'period'
    rs = gain / loss.replace(0, np.nan) #tính tỷ lệ RS, thay thế các giá trị mất định nghĩa (do chia cho 0) bằng NaN để tránh lỗi
    return 100 - (100 / (1 + rs))


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    """EMA - trung binh dong theo trong so mu."""
    return close.ewm(span=period, adjust=False).mean()


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    Khi MACD cat LEN Signal -> momentum tang.
    """
    macd = compute_ema(close, fast) - compute_ema(close, slow)
    sig  = compute_ema(macd, signal)
    hist = macd - sig
    return macd, sig, hist


def compute_bollinger(close: pd.Series, period=20, num_std=2.0):
    """Bollinger = SMA +/- num_std * std."""
    mid   = close.rolling(period).mean()
    sd    = close.rolling(period).std()
    return mid + num_std * sd, mid, mid - num_std * sd


# ============================================================
# [4] SIGNAL AGGREGATION  (tham chieu Bai 7.3.2 - Portfolio of Alphas)
# ============================================================

def classify_signal(price, ema9, ema21, rsi_val, macd_cross, vol_ratio):
    """
    Ket hop 4 Alpha doc lap -> 1 tin hieu tong hop.

    Alpha 1: Trend        (vi tri gia vs EMA9 vs EMA21)
    Alpha 2: Momentum     (MACD cross)
    Alpha 3: Oscillator   (RSI)
    Alpha 4: Volume       (vol so voi SMA20 cua vol)

    Logic dua vao vi tri gia:
        price > EMA9 > EMA21  -> UPTREND
        price < EMA9 < EMA21  -> DOWNTREND
        price > EMA9, EMA9<EMA21 hoac nguoc lai -> TRANSITION
    """
    # --- Xep hang Trend ---
    if price > ema9 > ema21:
        base = "UPTREND"
    elif price < ema9 < ema21:
        base = "DOWNTREND"
    elif price > ema9 and ema9 < ema21:
        base = "CONSIDER_BUY"
    elif price < ema9 and ema9 > ema21:
        base = "CONSIDER_SELL"
    else:
        base = "SIDEWAYS"

    # --- Nang cap len STRONG neu co xac nhan ---
    if base == "UPTREND" and macd_cross == "GOLDEN" and rsi_val < 70:
        return "STRONG_BUY"
    if base == "DOWNTREND" and macd_cross == "DEATH" and rsi_val > 30:
        return "STRONG_SELL"

    # --- Canh bao dao chieu khi RSI cuc doan ---
    if base == "UPTREND" and rsi_val > 75:
        return "OVERBOUGHT_RISK"
    if base == "DOWNTREND" and rsi_val < 25:
        return "OVERSOLD_RISK"

    return base


# Mapping tin hieu -> emoji + text + action
SIGNAL_DISPLAY = {
    "STRONG_BUY":      ("🟢", "MUA MẠNH (STRONG BUY)",
                        "Tất cả các chỉ báo xác nhận xu hướng tăng. Có thể vào lệnh với size chuẩn."),
    "UPTREND":         ("📈", "XU HƯỚNG TĂNG (UPTREND)",
                        "Giá cao trên cả EMA9 và EMA21. Xu hướng tích cực, theo trend."),
    "CONSIDER_BUY":    ("🟡", "XEM XÉT MUA",
                        "Giá bắt đầu vượt lên EMA9. Chờ xác nhận để vào lệnh."),
    "SIDEWAYS":        ("⚪", "ĐI NGANG (SIDEWAYS)",
                        "Thị trường không có xu hướng rõ. Tránh vào lệnh trend-following."),
    "CONSIDER_SELL":   ("🟠", "XEM XÉT BÁN",
                        "Giá bắt đầu rơi dưới EMA9. Cần thận trọng nếu đang giữ vị thế."),
    "DOWNTREND":       ("📉", "XU HƯỚNG GIẢM (DOWNTREND)",
                        "Giá nằm dưới các đường trung bình. Nguy hiểm, không nên GIAO DỊCH."),
    "STRONG_SELL":     ("🔴", "BÁN MẠNH (STRONG SELL)",
                        "Tất cả các chỉ báo xác nhận xu hướng giảm. Cần thoát vị thế."),
    "OVERBOUGHT_RISK": ("⚠️", "CẢNH BÁO QUÁ MUA",
                        "RSI > 75. Nguy cơ đảo chiều giảm, giảm tham gia mua them."),
    "OVERSOLD_RISK":   ("⚠️", "CẢNH BÁO QUÁ BÁN",
                        "RSI < 25. Có thể hồi nhưng rủi ro cao, chờ xác nhận."),
}


def analyze(df: pd.DataFrame):
    """Nhan DataFrame OHLCV -> tra ve dict cac chi so + tin hieu tong hop."""
    if df is None or len(df) < max(MACD_SLOW, BB_PERIOD, EMA_SLOW) + 5:
        return None

    close  = df["close"]
    volume = df["baseVol"]

    # --- Tinh cac chi bao ---
    rsi = compute_rsi(close, RSI_PERIOD)
    ema_fast_s = compute_ema(close, EMA_FAST)
    ema_slow_s = compute_ema(close, EMA_SLOW)
    macd, macd_sig, macd_hist = compute_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    upper, mid, lower = compute_bollinger(close, BB_PERIOD, BB_STD)
    vol_sma = volume.rolling(VOL_SMA_PERIOD).mean()

    # --- Gia tri hien tai ---
    last, prev = -1, -2
    price   = float(close.iloc[last])
    rsi_val = float(rsi.iloc[last])
    ema9    = float(ema_fast_s.iloc[last])
    ema21   = float(ema_slow_s.iloc[last])
    vol     = float(volume.iloc[last])
    vol_ma  = float(vol_sma.iloc[last])
    vol_ratio = vol / vol_ma if vol_ma > 0 else 0.0

    # Bien dong % so voi nen truoc
    change_pct = (price / float(close.iloc[prev]) - 1) * 100

    # MACD cross
    if macd.iloc[prev] <= macd_sig.iloc[prev] and macd.iloc[last] > macd_sig.iloc[last]:
        macd_cross = "GOLDEN"
    elif macd.iloc[prev] >= macd_sig.iloc[prev] and macd.iloc[last] < macd_sig.iloc[last]:
        macd_cross = "DEATH"
    else:
        macd_cross = "NONE"

    # Phan loai tin hieu tong hop
    signal = classify_signal(price, ema9, ema21, rsi_val, macd_cross, vol_ratio)

    return {
        "price":      price,
        "change_pct": change_pct,
        "rsi":        rsi_val,
        "ema9":       ema9,
        "ema21":      ema21,
        "macd_cross": macd_cross,
        "bb_upper":   float(upper.iloc[last]),
        "bb_lower":   float(lower.iloc[last]),
        "vol":        vol,
        "vol_ma":     vol_ma,
        "vol_ratio":  vol_ratio,
        "signal":     signal,
    }


# ============================================================
# [5] TELEGRAM  (format giong anh mau)
# ============================================================

def format_message(symbol: str, data: dict) -> str:
    """Dong goi thong tin phan tich thanh message HTML cho Telegram."""
    emoji, title, action = SIGNAL_DISPLAY[data["signal"]]
    vn_now = datetime.now(VN_TZ).strftime("%H:%M:%S - %d/%m/%Y")

    # Them dau hieu MACD cross neu co
    macd_note = ""
    if data["macd_cross"] == "GOLDEN":
        macd_note = "\n✨ <b>MACD Golden Cross</b> (momentum tăng)"
    elif data["macd_cross"] == "DEATH":
        macd_note = "\n💀 <b>MACD Death Cross</b> (momentum giảm)"

    # Them canh bao volume spike
    vol_note = ""
    if data["vol_ratio"] > 2.0:
        vol_note = "\n🔥 <b>Volume bất thường</b> (> 2x trung bình)"

    return (
        f"📊 <b>ROBO-ADVISOR SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🪙 Token: <b>{symbol}</b>\n"
        f"💰 Giá: <b>{data['price']:.4f} USDT</b>\n"
        f"🎯 Tín hiệu: {emoji} <b>{title}</b>\n"
        f"📈 Biến động: {data['change_pct']:+.4f}%\n"
        f"📊 RSI: {data['rsi']:.2f}\n"
        f"📉 EMA9: {data['ema9']:.4f}\n"
        f"📉 EMA21: {data['ema21']:.4f}\n"
        f"🔊 Vol: {data['vol_ratio']:.1f}x (TB: {data['vol_ma']:.1f})\n"
        f"⏰ Giờ VN: {vn_now}"
        f"{macd_note}"
        f"{vol_note}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>HÀNH ĐỘNG:</b> {action}"
    )


def send_telegram(text: str) -> bool:
    url = f"https://api.telegram.org/bot8689397744:AAF6gw6JFpjpevd3sjlJZ4zy1N5-7TkF7xQ/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"[TELEGRAM] HTTP {r.status_code}: {r.text}")
        return r.ok
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False


# ============================================================
# [6] MAIN LOOP
# ============================================================

def main():
    print("=" * 60)
    print("ROBO-ADVISOR v2.0 STARTING")
    print("=" * 60)

    # 1) Xac minh symbol
    print("[INIT] Lay danh sach symbol tu Bitget ...")
    all_symbols = fetch_symbols()
    if not all_symbols:
        print("[INIT] Khong lay duoc symbol list. Thoat.")
        return

    valid   = [s for s in WATCHLIST if s in all_symbols]
    invalid = [s for s in WATCHLIST if s not in all_symbols]
    if invalid:
        print(f"[INIT] Bo qua {len(invalid)} symbol khong ton tai: {invalid[:5]}...")
    if not valid:
        print("[INIT] Khong co symbol nao hop le. Kiem tra WATCHLIST.")
        return
    print(f"[INIT] Theo doi {len(valid)}/{len(WATCHLIST)} symbol")

    # 2) Thong bao online
    send_telegram(
        "🚀 <b>Robo-Advisor v2.0 ONLINE</b>\n"
        f"📋 Theo dõi: <b>{len(valid)} tokenized stocks</b>\n"
        f"⏱ Timeframe: {TIMEFRAME} | Quet moi {CHECK_INTERVAL}s\n"
        f"🧠 Logic: Portfolio of Alphas (Trend + MACD + RSI + Volume)"
    )

    # 3) State de tranh spam
    last_signal = {sym: "" for sym in valid}

    # 4) Loop
    while True:
        now = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n=== {now} VN ===")

        for sym in valid:
            df = fetch_candles(sym, TIMEFRAME, CANDLE_LIMIT)
            data = analyze(df)
            if data is None:
                print(f"  [{sym}] khong du du lieu")
                continue

            sig = data["signal"]
            # Chi gui khi tin hieu MOI hoac la tin hieu manh (luon gui)
            is_strong = sig in ("STRONG_BUY", "STRONG_SELL",
                                "OVERBOUGHT_RISK", "OVERSOLD_RISK")
            if sig != last_signal[sym] or is_strong:
                if sig != "SIDEWAYS":  # Khong spam sideways
                    send_telegram(format_message(sym, data))
                    print(f"  [{sym}] ${data['price']:.4f} RSI={data['rsi']:.1f} "
                          f"-> {sig} [SENT]")
                else:
                    print(f"  [{sym}] ${data['price']:.4f} -> SIDEWAYS (skip)")
                last_signal[sym] = sig
            else:
                print(f"  [{sym}] ${data['price']:.4f} -> {sig} (no change)")

            time.sleep(0.15)  # tranh rate-limit Bitget

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Dừng bot.")
        send_telegram("🛑 <b>Robo-Advisor v2.0 OFFLINE</b>")
