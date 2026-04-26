"""Telegram alert module - format đẹp cho Phan B v2."""

import requests
import config


def send(text: str) -> bool:
    """Gửi message Telegram. Skip nếu user chưa setup."""
    if not config.TELEGRAM_TOKEN or "PASTE" in config.TELEGRAM_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        return r.ok
    except Exception:
        return False


def format_signal(result: dict, ticker: dict, vn_time: str) -> str:
    """
    Format tín hiệu ra Telegram message.
    result = output của combine_signals()
    """
    sig = result["final_signal"]

    if sig == "LONG":
        emoji  = "🟢"
        title  = "LONG OPPORTUNITY"
        action = "Có thể xem xét MUA."
    elif sig == "SHORT":
        emoji  = "🔴"
        title  = "SHORT OPPORTUNITY"
        action = "Có thể xem xét BÁN KHỐNG."
    else:
        return ""

    # Lieu ke alphas
    alpha_lines = []
    for a in result["alphas"]:
        if a["signal"] == "NEUTRAL":
            mark = "⚪"
        elif a["signal"] == result["final_signal"]:
            mark = "✓"
        else:
            mark = "✗"
        alpha_lines.append(f"  {mark} <b>{a['name']}</b>: {a['reason']}")

    funding = ticker.get("funding_rate", 0) * 100
    return (
        f"{emoji} <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🪙 <b>{result['symbol']}</b>\n"
        f"💰 Giá: ${ticker.get('last', 0):.6f}\n"
        f"📊 24h: {ticker.get('rise_fall_rate', 0):+.2f}%\n"
        f"💹 Funding: {funding:+.4f}%\n"
        f"🎯 Score: {result['score']:+.2f} | Confidence: {result['confidence']:.0%}\n"
        f"⏰ {vn_time}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>4 ALPHA SIGNALS:</b>\n" +
        "\n".join(alpha_lines) +
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>HÀNH ĐỘNG:</b> {action}"
    )


def send_startup(num_pairs: int, alpha_count: int):
    send(
        f"🚀 <b>Signal Scanner ONLINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 Quét: <b>{num_pairs} cap</b> USDT-M Perpetual\n"
        f"🧠 <b>{alpha_count} Alpha</b>: Momentum, MeanRevert, Funding, OI Divergence\n"
        f"⏱ Quét mỗi {60}s\n"
        f"💡 Bot CHỈ quét & báo tín hiệu - bạn tự vào MEXC đặt lệnh"
    )


def send_shutdown():
    send("🛑 <b>Signal Scanner OFFLINE</b>")
