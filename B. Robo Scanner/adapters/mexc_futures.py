"""
============================================================
MEXC FUTURES ADAPTER - Phần B v2 (Signal Scanner)
============================================================

Lấy dữ liệu công khai từ MEXC Futures contract API.
KHÔNG cần API key vì đề bài chỉ yêu cầu bot QUÉT TÍN HIỆU và BÁO QUA TELEGRAM, KHÔNG đặt lệnh tự động.
không đặt lệnh tự động.

Endpoint base: https://contract.mexc.com/api/v1/contract/
Symbol format: BTC_USDT (có dấu gạch dưới, khác Spot)

Các endpoint quan trọng:
    /ticker                    - bid/ask + funding + holdVol của tất cả các cặp
    /ticker?symbol=BTC_USDT    - riêng 1 cặp 
    /kline/BTC_USDT            - nến OHLCV
    /funding_rate/BTC_USDT     - funding rate hiện tại + lịch sử (nếu cần)
    /detail                    - danh sách symbol khả dụng
"""

from typing import Optional, List, Dict
import numpy as np
import pandas as pd
import requests


class MEXCFuturesAdapter:
    """Public-only adapter cho MEXC Futures."""

    name = "MEXC_FUTURES"
    BASE_URL = "https://contract.mexc.com/api/v1/contract"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()  # tai su dung connection -> nhanh hon
        self._symbols_cache = None

    # ============================================================
    # METADATA
    # ============================================================

    def get_all_symbols(self) -> List[str]:
        """
        Lấy danh sách các cặp USDT-M Perpetual đang hoạt động.
        Trả về list ['BTC_USDT', 'ETH_USDT', ...].
        """
        if self._symbols_cache is None:
            r = self.session.get(f"{self.BASE_URL}/detail", timeout=self.timeout)
            data = r.json().get("data", [])
            # Chi giu USDT pairs đang hoạt động (state=0)
            self._symbols_cache = [
                d["symbol"] for d in data
                if d.get("quoteCoin") == "USDT" and d.get("state") == 0
            ]
        return self._symbols_cache

    # ============================================================
    # MARKET DATA
    # ============================================================

    def fetch_klines(self, symbol: str, interval: str = "Min15",
                     limit: int = 100) -> pd.DataFrame:
        """
        Lấy nến OHLCV.
        interval: Min1, Min5, Min15, Min30, Min60, Hour4, Hour8, Day1
        Trả về DataFrame với cột: ts, open, high, low, close, volume.
        """
        url = f"{self.BASE_URL}/kline/{symbol}"
        params = {"interval": interval}
        r = self.session.get(url, params=params, timeout=self.timeout)
        d = r.json().get("data", {})
        if not d or "time" not in d:
            return pd.DataFrame()

        df = pd.DataFrame({
            "ts":     pd.to_datetime(d["time"], unit="s"),
            "open":   [float(x) for x in d["open"]],
            "high":   [float(x) for x in d["high"]],
            "low":    [float(x) for x in d["low"]],
            "close":  [float(x) for x in d["close"]],
            "volume": [float(x) for x in d.get("vol", [0]*len(d["time"]))],
        })
        # Chỉ lấy 'limit' nến gần đây
        return df.tail(limit).reset_index(drop=True)

    def get_ticker(self, symbol: str) -> dict:
        """
        Lấy ticker chi tiết cho 1 cặp. Trả về:
            {
                'symbol', 'last', 'bid', 'ask', 'high24', 'low24',
                'volume24', 'rise_fall_rate' (% 24h),
                'funding_rate', 'hold_vol' (open interest), 'fair_price'
            }
        """
        url = f"{self.BASE_URL}/ticker"
        r = self.session.get(url, params={"symbol": symbol}, timeout=self.timeout)
        d = r.json().get("data", {})
        if not d:
            return {}
        return {
            "symbol":          d.get("symbol", symbol),
            "last":            float(d.get("lastPrice", 0)),
            "bid":             float(d.get("bid1", 0)),
            "ask":             float(d.get("ask1", 0)),
            "high24":          float(d.get("high24Price", 0)),
            "low24":           float(d.get("lower24Price", 0)),
            "volume24":        float(d.get("volume24", 0)),
            "rise_fall_rate":  float(d.get("riseFallRate", 0)) * 100,  # %
            "funding_rate":    float(d.get("fundingRate", 0)),
            "hold_vol":        float(d.get("holdVol", 0)),  # Open Interest
            "fair_price":      float(d.get("fairPrice", 0)),
        }

    def get_all_tickers(self) -> Dict[str, dict]:
        """
        Lấy ticker của TẤT CẢ các cặp trong 1 request -> rất nhanh.
        Trả về dict {symbol: ticker_dict}. Hiệu quả hơn nhiều so với
        gọi get_ticker() 20 lần.
        """
        url = f"{self.BASE_URL}/ticker"
        r = self.session.get(url, timeout=self.timeout)
        data = r.json().get("data", [])
        result = {}
        for d in data:
            sym = d.get("symbol")
            if not sym or not sym.endswith("_USDT"):
                continue
            result[sym] = {
                "symbol":          sym,
                "last":            float(d.get("lastPrice", 0)),
                "bid":             float(d.get("bid1", 0)),
                "ask":             float(d.get("ask1", 0)),
                "high24":          float(d.get("high24Price", 0)),
                "low24":           float(d.get("lower24Price", 0)),
                "volume24":        float(d.get("volume24", 0)),
                "rise_fall_rate":  float(d.get("riseFallRate", 0)) * 100,
                "funding_rate":    float(d.get("fundingRate", 0)),
                "hold_vol":        float(d.get("holdVol", 0)),
                "fair_price":      float(d.get("fairPrice", 0)),
            }
        return result

    def get_funding_rate(self, symbol: str) -> dict:
        """Funding rate hiện tại - có thể lấy riêng nếu cần chi tiết hơn."""
        url = f"{self.BASE_URL}/funding_rate/{symbol}"
        r = self.session.get(url, timeout=self.timeout)
        d = r.json().get("data", {})
        return {
            "rate":               float(d.get("fundingRate", 0)),
            "max_rate":           float(d.get("maxFundingRate", 0)),
            "min_rate":           float(d.get("minFundingRate", 0)),
            "next_settle_time":   d.get("nextSettleTime", 0),
            "collect_cycle_hour": int(d.get("collectCycle", 8)),
        }
