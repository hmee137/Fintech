"""
============================================================
CONFIG - Phần B (Signal Scanner)
============================================================
"""

# ============================================================
# TELEGRAM 
# ============================================================
TELEGRAM_TOKEN   = "tele_token_hier"
TELEGRAM_CHAT_ID = "tele_id_here"

# ============================================================
# 20 CẶP USDT-M PERPETUAL ĐỂ QUÉT
# ============================================================
WATCHLIST = [
    # Tier 1 - Top majors (ưu tiên quan sát)
    "BTC_USDT", "ETH_USDT", "BNB_USDT", "SOL_USDT", "XRP_USDT",

    # Tier 2 - Layer 1 / blue chips
    "ADA_USDT", "AVAX_USDT", "DOT_USDT", "LINK_USDT", "MATIC_USDT",

    # Tier 3 - DeFi và smart contract
    "UNI_USDT", "AAVE_USDT", "ATOM_USDT", "NEAR_USDT", "APT_USDT",

    # Tier 4 - Memecoin và altcoin có biến động cao
    "DOGE_USDT", "SHIB_USDT", "PEPE_USDT", "WIF_USDT", "TRX_USDT",
]

# Timeframe quét
TIMEFRAME      = "Min15"   # Min1, Min5, Min15, Min30, Min60
KLINE_LIMIT    = 100       # số nến cũ lấy mỗi lần

# Vòng lặp
SCAN_INTERVAL_SEC = 60     # Quét mỗi 60s
SIGNAL_THRESHOLD  = 0.5    # Ngưỡng score để phát tín hiệu LONG/SHORT

# Concurrent fetch (tốc độ quét 20 cặp)
MAX_WORKERS = 5            # số thread chạy song song

# ============================================================
# LOGGING
# ============================================================
LOG_FILE       = "logs/scanner.log"
SIGNALS_FILE   = "logs/signals.csv"  # lưu mỗi tín hiệu đã phát
