# Phần B v2 — Signal Scanner Bot (MEXC Futures Demo)

**Tác giả:** Phú Thiên
**Môn:** Công nghệ Tài chính (Fintech) — Đề thi giữa kỳ

---

## 1. Khác biệt so với v1

Đề thi đã được cập nhật. Phần B chuyển từ **auto-trading bot** sang **signal scanner bot**:

| | v1 (đề cũ) | **v2 (đề mới)** |
|---|---|---|
| Vai trò bot | Đặt lệnh tự động | **Quét tín hiệu — giao dịch thủ công** |
| Số cặp | 3 token | **20+ cặp song song** |
| Sàn | Binance Testnet | **MEXC Futures Demo** |
| Vốn | 1,000 USDT testnet | **50,000 USDT demo** |
| Lệnh tối thiểu | 0 | **≥10 lệnh, ≥3 cặp** |
| Số alpha | 2 (Momentum + MeanRevert) | **4 (thêm Funding + OI Divergence)** |

## 2. Cấu trúc thư mục

```
phan_b_v2/
├── adapters/
│   ├── __init__.py
│   └── mexc_futures.py     # MEXC Futures public API
├── signals.py              # 4 alpha logic
├── notifier.py             # Telegram alert
├── config.py               # Whitelist 20 cặp + tham số
├── scanner_bot.py          # Bot chính
└── logs/                   # Log + signals.csv
```

## 3. Setup MEXC Futures Demo (~3 phút)

**KHÔNG cần API key vì bot chỉ đọc public data.**

### Tạo tài khoản Demo trading
1. Vào https://www.mexc.com → đăng ký account thường (nếu chưa có)
2. Vào https://futures.mexc.com → click avatar góc trên phải
3. Tìm mục **Demo Trading** hoặc **Futures Demo** → kích hoạt
4. Sàn cấp tự động **50,000 USDT demo**
5. **CẢNH BÁO**: Đảm bảo bạn đang ở chế độ Demo (giao diện thường có badge "DEMO" hoặc background khác). Đặt nhầm trên tài khoản thật là mất tiền thật!

### Setup Telegram (TUỲ CHỌN, nhưng nên có cho điểm thưởng)
1. Tìm `@BotFather` trên Telegram → `/newbot` → đặt tên bot
2. Copy token bot trả về
3. Tìm bot vừa tạo → bấm Start → gõ vài tin
4. Mở `https://api.telegram.org/bot<TOKEN>/getUpdates` → lấy `chat_id`
5. Paste vào `config.py` 2 dòng đầu

## 4. Chạy bot

```bash
pip install -r Requirements.txt
cd phan_b_v2
python scanner_bot.py
```

Bot sẽ:
- In ra terminal trạng thái 20 cặp mỗi phút
- Gửi Telegram alert khi có tín hiệu LONG/SHORT mới
- Log tất cả tín hiệu ra `logs/signals.csv`

Mẫu output console:
```
[INFO] === Scan @ 11:32:00 - 25/04/2026 VN ===
[INFO]   ▲ BTC_USDT     LONG    score=+0.78 conf=75%
[INFO]   ▼ ETH_USDT     SHORT   score=-0.65 conf=50%
[INFO]   ─ BNB_USDT     NEUTRAL score=+0.12 conf=25%
...
[INFO] === Da phat 2 tin hieu MOI ===
```

## 5. Logic 4 alpha — giải trình cho thầy

Theo triết lý **Portfolio of Alphas** (Bài 7.3.2): càng nhiều alpha trực giao, Sharpe Ratio tổng càng cao theo công thức `Sharpe(N) = √N × Sharpe(đơn lẻ)`.

### Alpha 1 — Momentum (Bài 7.3)
- **Logic**: EMA9 cross EMA21 + xác nhận RSI
- **Giả thuyết kinh tế**: Quán tính giá (herding behavior) — giá đang trend sẽ tiếp tục trend
- **Trigger**:
  - Golden cross + RSI 50-70 → **LONG mạnh**
  - Death cross + RSI 30-50 → **SHORT mạnh**

### Alpha 2 — Mean Reversion (Bài 7.4.1)
- **Logic**: Bollinger Bands z-score
- **Giả thuyết kinh tế**: Giá lệch xa SMA có xu hướng quay về cân bằng
- **Trigger**:
  - Z < -2 (oversold) → **LONG**
  - Z > +2 (overbought) → **SHORT**

### Alpha 3 — Funding Rate Arbitrage (NÂNG CAO — Bài 7.3.2)
- **Logic**: Khai thác bất cân bằng giữa long/short qua funding rate
- **Giả thuyết kinh tế**:
  - Funding âm sâu → short đang đông quá → squeeze sắp xảy ra → **LONG**
  - Funding dương cao → long đang đông quá → correction sắp đến → **SHORT**
- **Ngưỡng**: |funding| > 0.05% mỗi 8 giờ (annualized ~5.5%/năm)

### Alpha 4 — Open Interest Divergence (NÂNG CAO — Bài 7.3.2)
- **Logic**: So sánh thay đổi giá vs thay đổi OI
- **Giả thuyết kinh tế**: 4 trường hợp:
  - Giá ↑ + OI ↑ → trend thật, **LONG xác nhận**
  - Giá ↑ + OI ↓ → long chốt lời, **SHORT phân kỳ giảm**
  - Giá ↓ + OI ↑ → short đang vào, **SHORT xác nhận**
  - Giá ↓ + OI ↓ → short cover, **LONG phân kỳ tăng**

### Combiner — Voting với trọng số

```python
weights = {Momentum: 1.0, MeanRevert: 1.0, Funding: 0.7, OIDiverge: 0.7}
score = sum(alpha_score * weight) / sum(weights)
```

Alpha cơ bản trọng số 1.0 (tin cậy cao hơn), nâng cao 0.7 (noisy hơn).
**Tín hiệu chỉ trigger khi**: |score| > 0.5 **VÀ** ≥2 alpha cùng đồng thuận.

## 6. Strategy thực chiến

Đề yêu cầu **≥10 lệnh trong 24h, ≥3 cặp khác nhau**. Khuyến nghị:

| Khung giờ | Việc cần làm |
|-----------|--------------|
| 11h00 25/04 | Chụp screenshot T₀ ±60s. Bật bot scanner. |
| 11h00-14h00 | Đặt 3-4 lệnh đầu trên BTC/ETH với leverage thấp (3-5x) để làm quen |
| 14h00-22h00 | Đặt 4-5 lệnh tiếp trên altcoin mid-cap (SOL, BNB, AVAX) |
| 22h00-08h00 | Để bot chạy, ngủ. Bot không tự đặt lệnh nên an toàn. |
| 08h00-10h59 26/04 | Đặt 2-3 lệnh cuối, đóng tất cả vị thế trước 10h59 |
| 11h00 26/04 | Chụp screenshot T_end ±60s |

**Quy tắc kỷ luật:**
- **Đa dạng cặp**: ít nhất 3 cặp khác nhau (ví dụ BTC, ETH, SOL)
- **Leverage**: bắt đầu 3-5x, không vượt 10x dù đề cho không giới hạn
- **Position size**: mỗi lệnh ≤ 10% vốn (5,000 USDT/lệnh) để chịu được 2-3 lệnh thua liên tiếp
- **Take profit / Stop loss**: đặt thủ công trên web khi vào lệnh, không dùng leverage cao mà không có SL
