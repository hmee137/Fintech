# Robo-Advisor Telegram Bot — Hướng dẫn sử dụng

Bot cho **Phần A** của đề thi Fintech. Kết nối Bitget API → tính RSI / Bollinger / EMA → gửi tín hiệu qua Telegram.

---

## 1. Cài đặt thư viện

```bash
pip install requests pandas numpy
```

## 2. Tạo Telegram Bot 

**Bước 1 — Lấy TOKEN:**
1. Mở Telegram, tìm `@BotFather`.
2. Gõ `/newbot` → đặt tên bot → đặt username kết thúc bằng `_bot`.
3. BotFather trả về một chuỗi dạng `7812345678:AAH...xyz`. **Đây là TOKEN.**

**Bước 2 — Lấy CHAT_ID:**
1. Tìm bot vừa tạo trong Telegram, bấm **Start**, gõ vài tin nhắn bất kỳ.
2. Mở trình duyệt, truy cập:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   (thay `<TOKEN>` bằng token ở bước 1)
3. Trong JSON trả về, tìm `"chat":{"id": 123456789, ...}` → số đó là **CHAT_ID**.

**Bước 3 — Paste vào file `robo_advisor_bot.py`:**
```python
TELEGRAM_TOKEN   = "7812345678:AAH...xyz"
TELEGRAM_CHAT_ID = "123456789"
```

## 3. Kiểm tra symbol trên Bitget

Danh sách `WATCHLIST` trong code để **dự phòng** — hàm `fetch_symbols()` sẽ tự lọc bỏ những symbol không tồn tại trước khi chạy. Nếu bot báo `Khong co symbol nao hop le`, bạn cần:

1. Vào [bitget.com](https://www.bitget.com) → Spot → gõ "AAPL" hoặc "TSLA" vào ô search.
2. Xem ký hiệu chính xác (ví dụ có thể là `AAPLUSDT`, `AAPLON_USDT`, `xAAPLUSDT`…).
3. Sửa lại `WATCHLIST` trong file.

Hoặc chạy nhanh script kiểm tra:
```python
import requests
r = requests.get("https://api.bitget.com/api/v2/spot/public/symbols").json()
stocks = [s["symbol"] for s in r["data"] if any(t in s["symbol"] for t in ["AAPL","TSLA","NVDA","META"])]
print(stocks)
```

## 4. Chạy bot

```bash
python robo_advisor_bot.py
```

Bạn sẽ nhận tin nhắn `🚀 Robo-Advisor online` ngay. Sau đó cứ mỗi 60 giây bot sẽ quét và chỉ gửi tin khi **có tín hiệu mới** (chống spam).

Dừng bot: `Ctrl + C`.

---

## Logic tín hiệu (để giải trình với thầy)

Bot phát tín hiệu dựa trên **3 nhóm chỉ báo độc lập** (đúng theo Mục A.2 của đề):

| Nhóm | Logic | Ý nghĩa kinh tế |
|------|-------|-----------------|
| **RSI (14)** | < 30 → BUY, > 70 → SELL | Mean reversion: khi giá đi quá đà, có xu hướng quay về trung bình |
| **Bollinger Bands (20, 2σ)** | Giá phá band dưới → BUY, phá band trên → SELL | Mean reversion theo độ lệch chuẩn của giá |
| **EMA cross (9 / 21)** | Golden cross → BUY, Death cross → SELL | Momentum: EMA ngắn vượt EMA dài báo hiệu xu hướng đang hình thành |

Kết hợp **mean reversion + momentum** giúp bot bắt được cả hai chế độ thị trường (đi ngang và có xu hướng) — phù hợp với triết lý **Portfolio of Alphas** được nhắc trong đề.

## Cách tinh chỉnh

- Muốn ít tín hiệu hơn (chỉ tín hiệu mạnh) → nâng `RSI_OVERSOLD = 25`, `RSI_OVERBOUGHT = 75`, `BB_STD = 2.5`.
- Muốn timeframe nhanh hơn (nhiều tín hiệu) → `TIMEFRAME = "5min"`.
- Muốn timeframe chậm hơn (ít nhiễu) → `TIMEFRAME = "1h"`.
- Muốn chỉ theo dõi vài mã yêu thích → bớt `WATCHLIST`.
