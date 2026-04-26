"""
============================================================
SIGNALS - 4 Alpha cho PhầN B 
============================================================

LIÊN HỆ BÀI GIẢNG:
    - Bài 7.3.2: Portfolio of Alphas - càng nhiều alpha trực giao, Sharpe tổng càng theo công thức √N.
    - Bài 7.4.1: Mean Reversion (Bollinger Bands)
    - Bài 7.3 : Momentum (MACD/EMA cross)
    - Bài 7.3.2: Funding rate arbitrage (alpha nâng cao)

CẤU TRÚC:
    Mỗi alpha trả về dict:
        {
            'name': str,                 # tên alpha
            'signal': 'LONG'/'SHORT'/'NEUTRAL',
            'score': float in [-1, +1],  # cường độ tín hiệu, dùng
            'reason': str,               # giải thích người đọc hiểu
        }

    combine_signals() kết hợp 4 alpha thành 1 kết luận.
"""

import numpy as np
import pandas as pd


# ============================================================
# INDICATORS
# ============================================================

def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _bollinger_z(close: pd.Series, period: int = 20) -> pd.Series:
    mid = close.rolling(period).mean()
    sd  = close.rolling(period).std()
    return (close - mid) / sd


# ============================================================
# ALPHA 1 - MOMENTUM (co ban) - Bai 7.3
# ============================================================

def alpha_momentum(df: pd.DataFrame) -> dict:
    """
    Logic: EMA9 cat EMA21 + xac nhan boi RSI.
    - Golden cross (EMA9 vượt lên EMA21) + RSI > 50 -> LONG
    - Death cross (EMA9 cắt xuống EMA21) + RSI < 50 -> SHORT
    """
    if df is None or len(df) < 30:
        return {"name": "Momentum", "signal": "NEUTRAL", "score": 0,
                "reason": "không đủ dữ liệu để tính momentum"}

    close = df["close"]
    ema_fast = _ema(close, 9).iloc[-1]
    ema_slow = _ema(close, 21).iloc[-1]
    ema_fast_prev = _ema(close, 9).iloc[-2]
    ema_slow_prev = _ema(close, 21).iloc[-2]
    rsi_val = _rsi(close, 14).iloc[-1]

    # Golden cross
    if ema_fast_prev <= ema_slow_prev and ema_fast > ema_slow:
        if rsi_val > 50 and rsi_val < 70:
            return {"name": "Momentum", "signal": "LONG", "score": 0.8,
                    "reason": f"Golden cross EMA9>EMA21, RSI={rsi_val:.1f}"}

    # Death cross
    if ema_fast_prev >= ema_slow_prev and ema_fast < ema_slow:
        if rsi_val < 50 and rsi_val > 30:
            return {"name": "Momentum", "signal": "SHORT", "score": -0.8,
                    "reason": f"Death cross EMA9<EMA21, RSI={rsi_val:.1f}"}

    # Trend dang dien ra
    if ema_fast > ema_slow and rsi_val > 55:
        return {"name": "Momentum", "signal": "LONG", "score": 0.4,
                "reason": f"Trend up, RSI={rsi_val:.1f}"}
    if ema_fast < ema_slow and rsi_val < 45:
        return {"name": "Momentum", "signal": "SHORT", "score": -0.4,
                "reason": f"Trend down, RSI={rsi_val:.1f}"}

    return {"name": "Momentum", "signal": "NEUTRAL", "score": 0,
            "reason": f"không có cross rõ ràng, RSI={rsi_val:.1f}"}


# ============================================================
# ALPHA 2 - MEAN REVERSION (co ban) - Bai 7.4.1
# ============================================================

def alpha_mean_reversion(df: pd.DataFrame) -> dict:
    """
    Logic: Bollinger Bands z-score.
    Z > 2  -> qua mua, ky vong gia ve trung binh -> SHORT
    Z < -2 -> qua ban, ky vong gia ve trung binh -> LONG
    """
    if df is None or len(df) < 25:
        return {"name": "MeanRevert", "signal": "NEUTRAL", "score": 0,
                "reason": "không đủ dữ liệu"}

    z = _bollinger_z(df["close"], 20).iloc[-1]
    if pd.isna(z):
        return {"name": "MeanRevert", "signal": "NEUTRAL", "score": 0,
                "reason": "z-score NaN"}

    if z < -2:
        return {"name": "MeanRevert", "signal": "LONG", "score": 0.85,
                "reason": f"Z={z:.2f} < -2 (quá bán)"}
    if z > 2:
        return {"name": "MeanRevert", "signal": "SHORT", "score": -0.85,
                "reason": f"Z={z:.2f} > +2 (quá mua)"}
    if z < -1.5:
        return {"name": "MeanRevert", "signal": "LONG", "score": 0.4,
                "reason": f"Z={z:.2f} (gần oversold)"}
    if z > 1.5:
        return {"name": "MeanRevert", "signal": "SHORT", "score": -0.4,
                "reason": f"Z={z:.2f} (gần overbought)"}

    return {"name": "MeanRevert", "signal": "NEUTRAL", "score": 0,
            "reason": f"Z={z:.2f} trong vùng trung bình"}


# ============================================================
# ALPHA 3 - FUNDING RATE ARBITRAGE (nâng cao) - Bài 7.3.2
# ============================================================

def alpha_funding_rate(ticker: dict) -> dict:
    """
    Logic kinh tế (Funding Rate Arbitrage):
        Funding rate la chi phí long trả cho short (nếu dương) hoặc ngược lại. Khi funding rate ÂM SÂU bất thường:
            - Phe short đang đóng qua đông, đập giá xuống
            - Long nhan duoc tien tu short -> co loi giu long
            -> Tín hiệu LONG (mean reversion về funding 0)

        Khi funding rate DƯƠNG QUÁ CAO:
            - Phe long dang qua dong (ai cung mua)
            - Short duoc tra tien
            -> Tín hiệu SHORT (mean reversion về funding 0)

        Ngưỡng an toàn:
            |funding| < 0.01%  -> bình thường, NEUTRAL
            |funding| > 0.05%  -> bất thường, tín hiệu mạnh
            |funding| > 0.1%   -> rất mạnh

    Tham số đầu vào là ticker (không phải df) vì funding rate cần gọi riêng ngoài kline.
    """
    if not ticker:
        return {"name": "Funding", "signal": "NEUTRAL", "score": 0,
                "reason": "không có ticker"}

    rate = ticker.get("funding_rate", 0) * 100  # quy doi sang %

    if rate < -0.10:
        return {"name": "Funding", "signal": "LONG", "score": 0.9,
                "reason": f"Funding={rate:.4f}% âm sâu bất thường"}
    if rate < -0.05:
        return {"name": "Funding", "signal": "LONG", "score": 0.5,
                "reason": f"Funding={rate:.4f}% âm đáng chú ý"}
    if rate > 0.10:
        return {"name": "Funding", "signal": "SHORT", "score": -0.9,
                "reason": f"Funding={rate:.4f}% dương quá cao"}
    if rate > 0.05:
        return {"name": "Funding", "signal": "SHORT", "score": -0.5,
                "reason": f"Funding={rate:.4f}% dương đáng chú ý    "}

    return {"name": "Funding", "signal": "NEUTRAL", "score": 0,
            "reason": f"Funding={rate:.4f}% bình thường"}


# ============================================================
# ALPHA 4 - OPEN INTEREST DIVERGENCE (nâng cao) - Bài 7.3.2
# ============================================================

# State lưu OI của mỗi symbol giữa các lần check
# Bot quét 1 phút/lần -> cần lưu OI từ lần trước để so sánh với OI hiện tại
_oi_history: dict = {}


def alpha_oi_divergence(symbol: str, ticker: dict) -> dict:
    """
    Logic kinh tế (Open Interest Divergence):
        OI = tổng vị thế đang mở. Khi:
            - Giá TĂNG + OI TĂNG  : LONG đang vào mạnh, trend tăng
            - Giá TĂNG + OI GIẢM  : LONG đang chốt lời -> sắp đảo chiều, SHORT
            - Giá GIẢM + OI TĂNG  : SHORT đang vào mạnh, trend giảm
            - Giá GIẢM + OI GIẢM  : SHORT đang chốt lời -> sắp đảo chiều, LONG

    Để đơn giản, ta dùng 'last price' để tính 'price change', và 'hold_vol' (OI hiện tại) để tính 'OI change'.:
        rise_fall_rate (% 24h) làm 'price change'
        OI hiện tại vs OI lưu lượng _oi_history làm 'OI change'

    Lần đầu tiên cho 1 symbol -> lưu OI, NEUTRAL.
    Lần thứ 2 trở đi -> có thể so sánh.
    """
    if not ticker:
        return {"name": "OIDiverge", "signal": "NEUTRAL", "score": 0,
                "reason": "không có ticker"}

    price_change = ticker.get("rise_fall_rate", 0)  # % 24h
    oi_now = ticker.get("hold_vol", 0)
    oi_prev = _oi_history.get(symbol)
    _oi_history[symbol] = oi_now

    if oi_prev is None or oi_prev == 0:
        return {"name": "OIDiverge", "signal": "NEUTRAL", "score": 0,
                "reason": "lần đầu, lưu OI làm baseline"}

    oi_change_pct = (oi_now - oi_prev) / oi_prev * 100

    # Can ngưỡng đủ lớn để có ý nghĩa
    if abs(price_change) < 1.0 or abs(oi_change_pct) < 2.0:
        return {"name": "OIDiverge", "signal": "NEUTRAL", "score": 0,
                "reason": f"PriceChg={price_change:+.2f}%, OIChg={oi_change_pct:+.2f}% chưa đủ mạnh"}

    # Bullish divergence: gia giam nhung OI giam -> short dang chot
    if price_change < -1.0 and oi_change_pct < -2.0:
        return {"name": "OIDiverge", "signal": "LONG", "score": 0.7,
                "reason": f"Giá giảm {price_change:.2f}%, OI giảm {oi_change_pct:.2f}% (short cover)"}

    # Bearish divergence: gia tang nhung OI giam -> long dang chot
    if price_change > 1.0 and oi_change_pct < -2.0:
        return {"name": "OIDiverge", "signal": "SHORT", "score": -0.7,
                "reason": f"Giá tăng {price_change:.2f}%, OI giảm {oi_change_pct:.2f}% (long take-profit)"}

    # Confirmation: gia tang + OI tang -> trend that
    if price_change > 1.0 and oi_change_pct > 2.0:
        return {"name": "OIDiverge", "signal": "LONG", "score": 0.5,
                "reason": f"Giá + OI cung tang -> trend tăng có thể tiếp diễn"}

    if price_change < -1.0 and oi_change_pct > 2.0:
        return {"name": "OIDiverge", "signal": "SHORT", "score": -0.5,
                "reason": f"Giá giảm + OI tăng -> short lực đang vào mạnh, trend giảm có thể tiếp diễn"}

    return {"name": "OIDiverge", "signal": "NEUTRAL", "score": 0,
            "reason": "không có divergence rõ ràng"}


# ============================================================
# COMBINER - Portfolio of Alphas (Bài 7.3.2)
# ============================================================

def combine_signals(df: pd.DataFrame, symbol: str, ticker: dict,
                    threshold: float = 0.5) -> dict:
    """
    Kết hợp 4 alpha thành 1 quyết định.

    Trọng số:
        Alpha cơ bản (Momentum, MeanRevert): trọng số 1.0
        Alpha nâng cao (Funding, OI):        trọng số 0.7
        (alpha nang cao tin cậy ít hơn vì noisy hơn, nhưng vẫn có giá trị tham khảo)

    Trả về:
        {
            'symbol', 'final_signal', 'score', 'confidence',
            'alphas': [a1_dict, a2_dict, a3_dict, a4_dict]
        }
    """
    a1 = alpha_momentum(df)
    a2 = alpha_mean_reversion(df)
    a3 = alpha_funding_rate(ticker)
    a4 = alpha_oi_divergence(symbol, ticker)

    weights = {"Momentum": 1.0, "MeanRevert": 1.0,
               "Funding": 0.7, "OIDiverge": 0.7}

    weighted_sum = (
        a1["score"] * weights["Momentum"] +
        a2["score"] * weights["MeanRevert"] +
        a3["score"] * weights["Funding"] +
        a4["score"] * weights["OIDiverge"]
    )
    total_weight = sum(weights.values())
    score = weighted_sum / total_weight  # chuẩn hoá về [-1, +1]

    # Đếm số alpha đồng thuận (signal != NEUTRAL và cùng hướng với score)
    alphas = [a1, a2, a3, a4]
    longs  = sum(1 for a in alphas if a["signal"] == "LONG")
    shorts = sum(1 for a in alphas if a["signal"] == "SHORT")

    # Quyết định cuối cùng dựa trên score và số alpha đồng thuận
    if score > threshold and longs >= 2:
        final = "LONG"
    elif score < -threshold and shorts >= 2:
        final = "SHORT"
    elif score > threshold * 1.5:  # 1 alpha rất mạnh có thể trigger
        final = "LONG"
    elif score < -threshold * 1.5:
        final = "SHORT"
    else:
        final = "NEUTRAL"

    # Confidence: % alpha đồng thuận
    confidence = max(longs, shorts) / 4.0

    return {
        "symbol":       symbol,
        "final_signal": final,
        "score":        round(score, 3),
        "confidence":   round(confidence, 2),
        "alphas":       alphas,
    }
