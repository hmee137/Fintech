# Fintech Part A & B Overview

**Tác giả:** Phú Thiên
**Môn:** Công nghệ Tài chính (Fintech) — Đề thi giữa kỳ
**Học viện Chính sách và Phát triển — Khoa Kinh tế số**

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [PHẦN A — Robo-Advisor Bot (Bitget Spot)](#phần-a--robo-advisor-bot-bitget-spot)
4. [PHẦN B — Signal Scanner Bot (MEXC Futures Demo)](#phần-b--signal-scanner-bot-mexc-futures-demo)
5. [Setup chung — cài thư viện một lần](#5-setup-chung--cài-thư-viện-một-lần)
6. [Telegram integration (dùng chung A và B)](#6-telegram-integration-dùng-chung-a-và-b)
7. [Liên hệ Bài giảng](#7-liên-hệ-bài-giảng)

---

## 1. Tổng quan hệ thống

Hệ thống được thiết kế cho 2 phần đầu của đề thi với cùng **triết lý cốt lõi**:

> *Bot là trợ lý phát tín hiệu — con người ra quyết định cuối cùng và đặt lệnh thủ công.*

Triết lý này tuân thủ Bài 7.1 (Robo-Advisors là rule-based system, không phải AI ra quyết định) và phù hợp với cả 2 yêu cầu của đề:
- **Phần A**: Mục A.3 — *"Giao dịch hoàn toàn bằng tay (Manual Trade)"*
- **Phần B**: Mục B.2 — *"Bot chỉ cần đóng vai trò quét/cảnh báo tín hiệu, không cần bắn lệnh tự động qua API"*

**Khác biệt chính giữa A và B:**

| Đặc điểm | Phần A | Phần B |
|----------|--------|--------|
| Sàn | Bitget Spot | MEXC Futures Demo |
| Loại tài sản | Tokenized US Stocks (cổ phiếu Mỹ) | USDT-M Perpetual Futures (crypto) |
| Vốn | 100 USDT thật | 50,000 USDT giả lập |
| Số mã theo dõi | 54 token whitelist | 20 cặp song song |
| Đòn bẩy | Không có (Spot) | Tự chọn (đề khuyến nghị 3-7x) |
| Thời gian chạy | 30 giờ (15h 23/04 → 21h 24/04) | 24 giờ (11h 25/04 → 11h 26/04) |
| Lệnh tối thiểu | ≥1 | ≥10 lệnh, ≥3 cặp |
| Số alpha | 4 (Trend, MACD, RSI, Volume) | 4 (Momentum, MeanRevert, Funding, OI) |
| Stop-loss bắt buộc | -7% toàn danh mục | Tự chịu trách nhiệm |

## 2. Cấu trúc thư mục

```
fintech_final_v2/
├── PartA/                      Phần A — Bitget Spot
│   └── robo_advisor_bot_v2.py  Bot chính (đầy đủ logic + Telegram)
│
├── PartB/                      Phần B — MEXC Futures Demo
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── mexc_futures.py     MEXC Futures public API
│   ├── config.py               20 cặp + tham số
│   ├── signals.py              4 alpha logic
│   ├── notifier.py             Telegram alert
│   ├── scanner_bot.py          Bot scanner chính
│   └── logs/                   scanner.log, signals.csv
│
├── PartC/                      Phần C — Arbitrage (nhóm)
├── Reports/                    Báo cáo Word A/B/C
└── Documentation/              CHECKLIST + Q&A Defense Guide
```

---

## PHẦN A — Robo-Advisor Bot (Bitget Spot)

### A.1. Mục tiêu

Theo Mục A.1 đề bài, Phần A đo lường khả năng kết hợp 3 năng lực:
1. Xây dựng Robo-Advisor Bot từ public API
2. Thực thi giao dịch Spot có kỷ luật trên Tokenized US Stocks
3. Tuân thủ stop-loss toàn danh mục 7%

### A.2. Kiến trúc Bot

Bot kết nối **Bitget Public API REST**, lấy dữ liệu nến 15min cho 54 token tokenized stocks, tính 4 nhóm chỉ báo độc lập, kết hợp thành **9 trạng thái tín hiệu tổng hợp**, gửi alert qua Telegram + console.

#### 4 nhóm chỉ báo độc lập

| Nhóm | Chỉ báo | Logic | Tham chiếu Bài giảng |
|------|---------|-------|----------------------|
| Trend | Giá vs EMA9 vs EMA21 | Vị trí giá so với EMA → xu hướng | 7.3 (Momentum) |
| Momentum | MACD cross signal | Gia tốc giá tăng/giảm | 7.3 |
| Oscillator | RSI 14 | Quá mua > 70 / quá bán < 30 | 7.4.1 (Mean Reversion) |
| Volume | Vol vs SMA20 của vol | Volume bất thường > 2× → xác nhận | 7.3.1 (Market Data) |

#### 9 trạng thái tín hiệu tổng hợp

Khác với cách phát "BUY/SELL" rời rạc, bot phân loại 9 mức tinh tế:

- **STRONG_BUY**: Trend up + MACD Golden Cross + RSI 50-70
- **UPTREND**: Giá trên cả EMA9 và EMA21
- **CONSIDER_BUY**: Giá vừa vượt EMA9, chờ xác nhận
- **SIDEWAYS**: Không có xu hướng rõ → tránh trade
- **CONSIDER_SELL**: Giá rớt dưới EMA9, thận trọng
- **DOWNTREND**: Giá dưới cả EMA9 và EMA21
- **STRONG_SELL**: Trend down + MACD Death Cross
- **OVERBOUGHT_RISK**: Uptrend nhưng RSI > 75 → cảnh báo đảo chiều
- **OVERSOLD_RISK**: Downtrend nhưng RSI < 25 → có thể hồi

### A.3. Whitelist 54 token

Bot load toàn bộ whitelist Mục A.5 đề bài với format Bitget chuẩn `{TICKER}ONUSDT`:

```
AAPLONUSDT, ABNBONUSDT, ACNONUSDT, ADBEONUSDT, AMDONUSDT, APPONUSDT,
AVGOONUSDT, AXPONUSDT, BAONUSDT, BIDUONUSDT, CMGONUSDT, COINONUSDT,
COSTONUSDT, CRCLONUSDT, CRMONUSDT, DASHONUSDT, DISONUSDT, EQIXONUSDT,
FIGONUSDT, FUTUONUSDT, GEONUSDT, GMEONUSDT, GOOGLONUSDT, GSONUSDT,
HIMSONUSDT, HOODONUSDT, INTCONUSDT, INTUONUSDT, JDONUSDT, LINONUSDT,
MAONUSDT, MARAONUSDT, METAONUSDT, MRVLONUSDT, MSFTONUSDT, MSTRONUSDT,
MUONUSDT, NFLXONUSDT, NOWONUSDT, NVDAONUSDT, PANWONUSDT, PBRONUSDT,
PLTRONUSDT, PYPLONUSDT, RDDTONUSDT, RIOTONUSDT, SBETONUSDT, SHOPONUSDT,
SPGIONUSDT, SPOTONUSDT, TSLAONUSDT, TSMONUSDT, UNHONUSDT, WFCONUSDT
```

Hàm `fetch_symbols()` tự động lọc bỏ symbol chưa niêm yết.

### A.4. Setup & Chạy Bot Phần A

```bash
cd PartA/
# Sửa TOKEN, CHAT_ID Telegram trong file robo_advisor_bot_v2.py (xem Mục 6)
python robo_advisor_bot_v2.py
```

Bot sẽ:
- Quét 54 token mỗi 60 giây
- In console dashboard: trạng thái từng token
- Gửi Telegram alert khi có tín hiệu mới (chống spam, chỉ gửi khi tín hiệu đổi)
- Định dạng tin nhắn HTML với: tên token, giá, biến động %, RSI, EMA9/EMA21, Volume ratio, giờ Việt Nam, hành động đề xuất

Mẫu Telegram alert:
```
🟢 ROBO-ADVISOR SIGNAL
━━━━━━━━━━━━━━━━━━
🪙 Token: NVDAONUSDT
💰 Giá: 199.6900 USDT
🎯 Tín hiệu: 📈 XU HƯỚNG TĂNG (UPTREND)
📈 Biến động: +0.0450%
📊 RSI: 46.74
📉 EMA9: 199.7929
📉 EMA21: 200.2270
🔊 Vol: 1.3x (TB: 66.2)
⏰ Giờ VN: 09:37:23 - 24/04/2026
━━━━━━━━━━━━━━━━━━
👉 HÀNH ĐỘNG: Giá trên cả EMA9 và EMA21. Xu hướng tích cực, có thể theo trend.
```

### A.5. Quản trị rủi ro (BẮT BUỘC)

Đề Mục A.4: nếu equity giảm vượt **-7% so với 100 USDT** (tức < 93 USDT), BẮT BUỘC đóng tất cả vị thế và rút tiền. Vi phạm = 0 điểm Kỷ luật.

**Chiến lược 2 lớp:**
- **Lớp 1 (cá nhân)**: Stop-loss -2% mỗi lệnh — chặt hơn ngưỡng đề
- **Lớp 2 (đề bắt buộc)**: Stop-loss -7% toàn danh mục — buffer còn lại

Logic kinh tế của ngưỡng 7%: tham chiếu Bài 7.5 (bài học Knight Capital, Quant Quake 2007) — rèn phản xạ cắt lỗ có hệ thống.

---

## PHẦN B — Signal Scanner Bot (MEXC Futures Demo)

### B.1. Mục tiêu

Theo Mục B.1 đề bài, Phần B đẩy sinh viên rời vùng an toàn của Spot sang Futures — *"nửa trader, nửa kỹ sư dữ liệu"*. Năng lực được đo: **Cut Through The Noise** — giữa hàng trăm token đang biến động đồng thời, biết dùng công nghệ để sàng lọc tín hiệu xác suất cao.

### B.2. Setup MEXC Futures Demo (~3 phút)

**KHÔNG cần API key vì bot chỉ đọc public data.**

1. Vào https://www.mexc.com → đăng ký account thường (nếu chưa có)
2. Vào https://futures.mexc.com → click avatar góc trên phải
3. Tìm mục **Demo Trading** hoặc **Futures Demo** → kích hoạt
4. Sàn cấp tự động **50,000 USDT demo**
5. ⚠️ **Đảm bảo đang ở chế độ Demo** (giao diện thường có badge "DEMO" hoặc background khác). Đặt nhầm trên tài khoản thật là mất tiền thật!

### B.3. Chạy bot

```bash
cd PartB/
python scanner_bot.py
```

Mẫu output console:
```
[INFO] === Scan @ 11:32:00 - 25/04/2026 VN ===
[INFO]   ▲ BTC_USDT     LONG    score=+0.78 conf=75%
[INFO]   ▼ ETH_USDT     SHORT   score=-0.65 conf=50%
[INFO]   ─ BNB_USDT     NEUTRAL score=+0.12 conf=25%
...
[INFO] === Đã phát 2 tín hiệu MỚI ===
```

### B.4. Logic 4 alpha — giải trình cho thầy

Theo triết lý **Portfolio of Alphas** (Bài 7.3.2): càng nhiều alpha trực giao, Sharpe Ratio tổng càng cao theo công thức `Sharpe(N) = √N × Sharpe(đơn lẻ)`.

#### Alpha 1 — Momentum (Bài 7.3)
- **Logic**: EMA9 cross EMA21 + xác nhận RSI
- **Giả thuyết kinh tế**: Quán tính giá (herding behavior) — giá đang trend sẽ tiếp tục trend
- **Trigger**:
  - Golden cross + RSI 50-70 → **LONG mạnh**
  - Death cross + RSI 30-50 → **SHORT mạnh**

#### Alpha 2 — Mean Reversion (Bài 7.4.1)
- **Logic**: Bollinger Bands z-score
- **Giả thuyết kinh tế**: Giá lệch xa SMA có xu hướng quay về cân bằng
- **Trigger**:
  - Z < -2 (oversold) → **LONG**
  - Z > +2 (overbought) → **SHORT**

#### Alpha 3 — Funding Rate Arbitrage (NÂNG CAO — Bài 7.3.2)
- **Logic**: Khai thác bất cân bằng long/short qua funding rate
- **Giả thuyết kinh tế**:
  - Funding âm sâu → short đang đông quá → squeeze sắp xảy ra → **LONG**
  - Funding dương cao → long đang đông quá → correction sắp đến → **SHORT**
- **Ngưỡng**: |funding| > 0.05% mỗi 8 giờ (annualized ~5.5%/năm)

#### Alpha 4 — Open Interest Divergence (NÂNG CAO — Bài 7.3.2)
- **Logic**: So sánh thay đổi giá vs thay đổi OI
- **Giả thuyết kinh tế**: 4 trường hợp:
  - Giá ↑ + OI ↑ → trend thật, **LONG xác nhận**
  - Giá ↑ + OI ↓ → long chốt lời, **SHORT phân kỳ giảm**
  - Giá ↓ + OI ↑ → short đang vào, **SHORT xác nhận**
  - Giá ↓ + OI ↓ → short cover, **LONG phân kỳ tăng**

#### Combiner — Voting với trọng số

```python
weights = {Momentum: 1.0, MeanRevert: 1.0, Funding: 0.7, OIDiverge: 0.7}
score = sum(alpha_score * weight) / sum(weights)
```

Alpha cơ bản trọng số 1.0 (tin cậy cao hơn), nâng cao 0.7 (noisy hơn).
**Tín hiệu chỉ trigger khi**: |score| > 0.5 **VÀ** ≥2 alpha cùng đồng thuận.

### B.5. Whitelist 20 cặp

Theo Mục B.5 đề bài yêu cầu quét tối thiểu 20 cặp song song. Mix 4 tier:

```python
# Tier 1 - Top majors
"BTC_USDT", "ETH_USDT", "BNB_USDT", "SOL_USDT", "XRP_USDT"
# Tier 2 - Layer 1 / blue chips
"ADA_USDT", "AVAX_USDT", "DOT_USDT", "LINK_USDT", "MATIC_USDT"
# Tier 3 - DeFi / smart contract
"UNI_USDT", "AAVE_USDT", "ATOM_USDT", "NEAR_USDT", "APT_USDT"
# Tier 4 - Memecoin / altcoin biến động cao
"DOGE_USDT", "SHIB_USDT", "PEPE_USDT", "WIF_USDT", "TRX_USDT"
```

### B.6. Strategy thực chiến 24h

Đề yêu cầu **≥10 lệnh trong 24h, ≥3 cặp khác nhau**.

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
- **Position size**: mỗi lệnh ≤ 10% vốn (5,000 USDT/lệnh)
- **Take profit / Stop loss**: đặt thủ công trên web khi vào lệnh

### B.7. Hiệu suất kỹ thuật của bot

Bot dùng `ThreadPoolExecutor` 5 thread → quét 20 cặp song song xong trong **~2 giây** (so với 10 giây nếu chạy tuần tự — tăng tốc 5x). Với chu kỳ scan 60 giây, có 58 giây buffer.

Dùng MEXC public API `contract.mexc.com/api/v1/contract/ticker` — trả về full data 200+ cặp trong 1 request → hiệu quả hơn nhiều so với gọi 20 lần riêng lẻ.

---

## 5. Setup chung — cài thư viện một lần

```bash
# Cài cho cả Phần A và Phần B
pip install -r requirements.txt
```

Cả 2 bot đều dùng chung các thư viện này, không cần cài thêm gì khác.

---

## 6. Telegram integration (dùng chung A và B)

Theo Mục A.6 và B.6, tích hợp Telegram là **điểm thưởng**. Setup 1 lần, dùng cho cả 2 bot.

### 6.1. Tạo Telegram Bot

1. Mở Telegram, tìm `@BotFather`
2. Gõ `/newbot` → đặt tên (ví dụ "PhuThien Robo Advisor")
3. Đặt username kết thúc bằng `_bot` (ví dụ `phuthien_advisor_bot`)
4. BotFather trả về **TOKEN** dạng `7812345678:AAH...xyz` — copy ngay

### 6.2. Lấy CHAT_ID

1. Tìm bot vừa tạo trong Telegram → bấm **Start**
2. Gõ vài tin nhắn bất kỳ
3. Mở trình duyệt, vào URL:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   (thay `<TOKEN>` bằng token ở bước 6.1)
4. Trong JSON trả về, tìm `"chat":{"id": 123456789, ...}` → đó là **CHAT_ID**

### 6.3. Paste vào code

**Phần A** (`PartA/robo_advisor_bot_v2.py`):
```python
TELEGRAM_TOKEN   = "7812345678:AAH...xyz"
TELEGRAM_CHAT_ID = "123456789"
```

**Phần B** (`PartB/config.py`):
```python
TELEGRAM_TOKEN   = "7812345678:AAH...xyz"
TELEGRAM_CHAT_ID = "123456789"
```

Có thể dùng **CHUNG 1 BOT** cho cả A và B — mỗi alert sẽ ghi rõ source.

### 6.4. Nếu không setup Telegram

Cả 2 bot đều **chạy bình thường** kể cả không có Telegram — chỉ là không gửi alert thôi. Bạn vẫn thấy log đầy đủ trên terminal.

---

## 7. Liên hệ Bài giảng

Bot được thiết kế bám sát chương 7 sách giảng:

| Tính năng | Phần | Bài giảng | Nội dung |
|-----------|------|-----------|----------|
| Rule-based system, không AI | A & B | 7.1 (WealthTech) | Robo-Advisors là rule-based, không phải AI ra quyết định |
| Self-coded indicators | A & B | 7.3.1 (Market Data) | Trích xuất tín hiệu từ price/volume |
| EMA cross + RSI | A & B | 7.3 (Momentum) | Chiến lược momentum cơ bản |
| Bollinger z-score | B | 7.4.1 (Mean Reversion) | Khôi phục trung bình |
| 4 alpha kết hợp | B | 7.3.2 (Portfolio of Alphas) | √N × Sharpe |
| Funding rate alpha | B | 7.3.2 | Funding rate arbitrage |
| OI Divergence alpha | B | 7.3.2 | Open Interest analysis |
| Stop-loss 7% | A | 7.5 (Knight Capital) | Maximum drawdown |
| Volume spike detection | A | 7.3.1 | Volume bất thường > 2× SMA20 |

---

## Liên hệ & Hỗ trợ

Nếu có lỗi khi chạy bot, kiểm tra theo thứ tự:

1. **Thư viện đã cài chưa?** → `pip list | grep -E "pandas|numpy|requests"`
2. **Internet có thông không?** → ping bitget.com hoặc mexc.com
3. **API có bị rate limit không?** → đợi 60 giây rồi thử lại
4. **Telegram không gửi?** → kiểm tra TOKEN có "PASTE" không, CHAT_ID có đúng số không
