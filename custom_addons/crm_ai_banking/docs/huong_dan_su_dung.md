# Hướng dẫn sử dụng — CRM AI Banking

## Mục lục
1. [Cài đặt module](#1-cài-đặt-module)
2. [Cấu hình AI](#2-cấu-hình-ai)
3. [Gọi điện / Meeting với AI](#3-gọi-điện--meeting-với-ai)
4. [Email AI tự động](#4-email-ai-tự-động)
5. [Checklist hồ sơ](#5-checklist-hồ-sơ)
6. [Cảnh báo lead nguội & deal lớn](#6-cảnh-báo-lead-nguội--deal-lớn)
7. [Daily Digest](#7-daily-digest)
8. [Zalo Webhook](#8-zalo-webhook)
9. [Quản lý lịch sử cuộc gọi](#9-quản-lý-lịch-sử-cuộc-gọi)

---

## 1. Cài đặt module

### Bước 1 — Cập nhật addons_path

File `odoo.conf` đã được cập nhật tự động:
```
addons_path = /path/to/odoo/addons,/path/to/odoo/custom_addons
```

### Bước 2 — Cài module

```bash
./odoo-bin -c odoo.conf -u crm_ai_banking -d <tên_database>
```

Hoặc vào Odoo:
**Settings → Apps → Tìm "CRM AI Banking" → Install**

---

## 2. Cấu hình AI

**Đường dẫn**: `CRM → AI Banking → Cấu hình AI`
*(Chỉ System Administrator mới thấy menu này)*

### Tab LLM (Claude)

Chọn **LLM Provider**:

**`OpenRouter` — khuyến nghị để bắt đầu**

| Field | Giá trị | Ghi chú |
|-------|---------|---------|
| OpenRouter API Key | `sk-or-v1-...` | openrouter.ai — dùng chung với OCR |
| Text Model | `anthropic/claude-sonnet-4-6` | Dùng cho tóm tắt, phân tích |
| Vision Model | `anthropic/claude-opus-4-8` | Dùng cho scan name card |

> **Lưu ý**: Nếu cả LLM và OCR đều dùng OpenRouter thì chỉ cần **1 API key** duy nhất.

**`Anthropic API` — gọi trực tiếp (không qua OpenRouter)**

| Field | Giá trị |
|-------|---------|
| Anthropic API Key | `sk-ant-api03-...` (console.anthropic.com) |

Sau khi điền → click **"Test LLM Connection"** để kiểm tra.

---

### Tab OCR

Chọn **OCR Provider**:

**`External API (OpenRouter)` — dùng khi bắt đầu / test**

| Field | Giá trị |
|-------|---------|
| OpenRouter API Key | `sk-or-v1-...` (openrouter.ai) |
| OCR Model | `qwen/qwen3-vl` |

**`Local API` — dùng khi production (data không rời nội bộ)**

| Field | Giá trị |
|-------|---------|
| Local OCR Endpoint | `http://ocr-server:8080/api/ocr` |
| Local OCR API Key | Bearer token của server nội bộ |

> **Lưu ý bảo mật**: CCCD, GPKD, BCTC chỉ nên dùng **Local API**. OpenRouter dùng cho name card (không nhạy cảm).

Sau khi điền → click **"Test OCR Connection"**.

---

### Tab STT (Speech-to-Text)

Có 2 nhóm cấu hình:

**Batch Transcription** — dùng khi upload file audio sau cuộc gọi

| Provider | Field | Giá trị |
|----------|-------|---------|
| `External API (OpenAI Whisper)` | Whisper API Key | OpenAI API key |
| | API Endpoint | `https://api.openai.com/v1/audio/transcriptions` |
| `Local Server` | Local Endpoint | `http://whisper-server:9000/transcribe` |
| | Local Model | `large-v3` (GPU) hoặc `medium` (CPU) |

**Realtime Transcription** — dùng cho màn hình gọi trực tiếp

| Provider | Field | Giá trị |
|----------|-------|---------|
| `External API (Deepgram)` | Deepgram API Key | deepgram.com |
| | Deepgram Model | `nova-3` |
| `Local Server` | WebSocket URL | `ws://whisper-server:9001/stream` |

---

### Tab Zalo OA

| Field | Giá trị | Lấy ở đâu |
|-------|---------|-----------|
| Zalo OA Access Token | `OA_ACCESS_TOKEN_...` | developers.zalo.me → OA của bạn |
| Zalo Webhook Secret | chuỗi bất kỳ | Tự đặt, dùng để verify request |

Sau khi lưu → cấu hình Webhook URL trên Zalo OA:
```
https://yourdomain.com/crm/ai/webhook/zalo
```

---

### Tab Automation

| Field | Giá trị mặc định | Ý nghĩa |
|-------|-----------------|---------|
| Auto Process Incoming Emails | ✅ Bật | AI tự tóm tắt email đến |
| Auto Process Attachments | ❌ Tắt | Phase 3 |
| Daily Digest Time | `8.0` (8:00 AM) | Giờ gửi digest |
| Cold Lead Threshold | `10` ngày | Sau bao nhiêu ngày không cập nhật = nguội |
| Large Deal Threshold | `5,000,000,000` VND | Deal từ 5 tỷ trở lên = deal lớn |
| Alert if no manager activity | `7` ngày | Deal lớn mà manager không tương tác trong 7 ngày |
| Enable Realtime AI Hints | ❌ Tắt | Opt-in từng người trong profile |
| Enable Speaker Diarization | ✅ Bật | Phân biệt giọng NV và KH |

---

## 3. Gọi điện / Meeting với AI

### Bắt đầu cuộc gọi

1. Mở một **Opportunity** trong CRM
2. Click nút **"🎤 Gọi AI"** ở header form
3. Chọn kênh gọi:

| Kênh | Dùng khi | Độ chính xác |
|------|----------|-------------|
| 💻 **Softphone / WebRTC** | Gọi qua máy tính (Skype, Zoom, softphone) | Cao nhất — tách 2 giọng riêng |
| 📞 **Điện thoại + Mic** | Gọi điện thoại thường, để gần mic máy tính | Trung bình |
| 📱 **Zalo / Mobile** | Gọi trên điện thoại di động | Trung bình |

4. Trình duyệt sẽ hỏi quyền **truy cập microphone** → cho phép

### Màn hình gọi realtime

```
┌──────────────────────────────────────────────┐
│ 📞 Nguyễn Văn A — Vay mua nhà   ⏱ 04:32    │
│ 🔴 ĐANG GHI  [Kênh: Softphone]              │
├──────────────────────────────────────────────┤
│ [NV] Anh cần vay khoảng bao nhiêu?           │
│ [KH] Tầm 500 triệu, mua căn hộ              │
│ [NV] Thu nhập hàng tháng của anh? ▌          │
├──────────────────────────────────────────────┤
│ 🤖 AI HINTS  [toggle bật/tắt]               │
│ • Chưa hỏi: Thời hạn vay, tài sản đảm bảo  │
│ 💬 "Anh đang có tài sản thế chấp chưa?"     │
├──────────────────────────────────────────────┤
│ [⏸ Tạm dừng]    [⏹ Kết thúc & Tóm tắt]     │
└──────────────────────────────────────────────┘
```

- **[NV]** = Nhân viên (màu xanh dương)
- **[KH]** = Khách hàng (màu xanh lá)
- Chữ mờ = đang nói (partial), chữ đậm = đã xác nhận

### AI Hints (gợi ý realtime)

- Toggle **"Bật"** trong panel AI Hints để nhận gợi ý mỗi 30 giây
- Gợi ý gồm: câu hỏi chưa hỏi, cảnh báo thiếu thông tin
- Mặc định **tắt** — từng nhân viên tự bật theo nhu cầu

### Kết thúc cuộc gọi

1. Click **"⏹ Kết thúc & Tóm tắt"**
2. Thông báo: *"AI đang tóm tắt cuộc gọi..."*
3. Sau ~1 phút, vào lại Opportunity → tab **Chatter** thấy:
   - Note tóm tắt cuộc gọi
   - Danh sách action items
   - Activity follow-up được tạo tự động

### Xem lại lịch sử cuộc gọi

- Trên form Opportunity → stat button **"Cuộc gọi AI"** → xem danh sách
- Hoặc: `CRM → AI Banking → Lịch sử cuộc gọi AI`

---

## 4. Email AI tự động

### Cách hoạt động

Khi email khách hàng gửi đến alias của CRM team → AI **tự động** (không cần thao tác):

1. Tóm tắt nội dung email thành 2-3 bullet points
2. Nhận diện **intent** (hỏi giá, sẵn sàng mua, khiếu nại, yêu cầu hồ sơ)
3. Tạo **activity** phù hợp với deadline
4. Gắn **tags** theo nhu cầu nhận diện được (Vay vốn, Thẻ tín dụng...)

### Xem kết quả

Vào Opportunity → tab **Chatter** → tìm note có icon 🤖:

```
🤖 AI Tóm tắt email:
• Khách hỏi về lãi suất vay mua nhà 500 triệu
• Muốn biết thủ tục và thời gian xét duyệt
• Có sẵn tài sản thế chấp

Intent: pricing_inquiry | Urgency: medium
Gợi ý: Gửi báo giá trong ngày
```

### Bảng mapping Intent → Activity

| Intent nhận diện | Activity tạo ra | Deadline |
|-----------------|----------------|---------|
| `pricing_inquiry` | Gửi báo giá | +1 ngày |
| `ready_to_buy` | Follow up ngay | Hôm nay |
| `complaint` | Xử lý khiếu nại | Hôm nay |
| `document_request` | Kiểm tra hồ sơ | +1 ngày |
| `follow_up` | Follow up | +2 ngày |
| `general_inquiry` | Phản hồi khách | +1 ngày |

### Bật/tắt

`CRM → AI Banking → Cấu hình AI → Tab Automation → Auto Process Incoming Emails`

---

## 5. Checklist hồ sơ

### Kích hoạt checklist

**Cách 1 — Chọn loại sản phẩm trên Opportunity:**
1. Mở Opportunity
2. Field **"Loại sản phẩm"** → chọn (Vay mua nhà / Thẻ tín dụng / ...)
3. Checklist tự động xuất hiện trong tab **"Hồ sơ / Checklist"**

**Cách 2 — Tự động từ Email AI:**
Khi email khách có intent = `document_request` → checklist tự tạo nếu đã có `Loại sản phẩm`

### Sử dụng checklist

Tab **"Hồ sơ / Checklist"** trên form Opportunity:

| Màu sắc | Trạng thái | Ý nghĩa |
|---------|-----------|---------|
| ⬜ Trắng | Chờ nộp | Khách chưa gửi |
| 🟡 Vàng | Đã nộp | Đang chờ duyệt |
| 🟢 Xanh | Đã duyệt | Hoàn thành |
| 🔴 Đỏ | Từ chối | Cần nộp lại |

- Click vào dòng → đổi **Status**, đính kèm file, ghi chú
- **% Hoàn thành** tự tính trên cùng

### Nhắc tự động

Sau khi tạo checklist → activity **"📎 Nhắc bổ sung hồ sơ"** tự tạo sau N ngày (cấu hình trong template).

### Cấu hình templates hồ sơ

`CRM → AI Banking → Templates Hồ sơ` *(System Admin)*

Mỗi template gồm:
- **Loại sản phẩm**: Vay mua nhà / Thẻ tín dụng / Vay kinh doanh...
- **Danh sách giấy tờ**: thêm/xóa/sắp xếp theo nhu cầu
- **Nhắc sau (ngày)**: bao nhiêu ngày sau khi tạo thì nhắc

**Templates có sẵn** (Phase 1):

| Loại sản phẩm | Số giấy tờ |
|--------------|-----------|
| Vay mua nhà | 8 (CCCD, hôn nhân, sao kê lương, HĐLĐ, TSĐB, đơn vay...) |
| Thẻ tín dụng | 4 (CCCD, sao kê lương, HĐLĐ, đơn mở thẻ) |
| Vay kinh doanh | 6 (CCCD, GPKD, BCTC, sao kê, phương án KD, TSĐB) |

---

## 6. Cảnh báo lead nguội & deal lớn

### Lead nguội

**Tự động hàng ngày** — không cần thao tác. Khi lead không được cập nhật quá N ngày (mặc định 10):

1. AI phân tích lý do có thể nguội
2. Gợi ý cách re-engage
3. Note xuất hiện trong Chatter: `❄️ Lead nguội (10+ ngày không cập nhật)`
4. Activity **"Re-engage lead nguội"** tự tạo, assign cho salesperson

**Cấu hình ngưỡng**: Tab Automation → `Cold Lead Threshold`

### Deal lớn cần manager

Khi deal thỏa mãn đồng thời 3 điều kiện:
- `expected_revenue ≥ 5 tỷ` (cấu hình được)
- Stage = Proposal hoặc Negotiation
- Manager chưa có tương tác trong 7 ngày

→ Thông báo xuất hiện trong **team channel** trên Discuss  
→ Activity **"👔 Cần hỗ trợ manager"** assign cho manager

**Cấu hình**:
- `Large Deal Threshold` (VND)
- `Alert if no manager activity` (ngày)

---

## 7. Daily Digest

### Nhận digest ở đâu

Mỗi sáng **8:00 AM**, nhân viên nhận tin nhắn tự động qua **Discuss** (chat DM):

```
Chào Minh, hôm nay có 3 việc ưu tiên:

🔥 Anh Nguyễn Văn A (Vay 2.5 tỷ) — chờ 5 ngày, xác suất 78%
   → Chưa có phản hồi sau buổi gặp hôm thứ 2

📎 Công ty ABC — còn thiếu BCTC năm 2024
   → Đã nhắc 1 lần ngày 20/05

⏰ 2 activities quá hạn từ hôm qua
```

### Tìm trong Discuss

`Discuss → Direct Messages → AI Digest — [Tên bạn]`

### Cấu hình giờ gửi

`CRM → AI Banking → Cấu hình AI → Tab Automation → Daily Digest Time`  
Nhập số thập phân: `8.0` = 8:00, `8.5` = 8:30, `9.0` = 9:00

---

## 8. Zalo Webhook

### Cấu hình phía Zalo OA

1. Vào [developers.zalo.me](https://developers.zalo.me) → Official Account của bạn
2. **Webhook** → nhập URL:
   ```
   https://yourdomain.com/crm/ai/webhook/zalo
   ```
3. Chọn các events: `user_send_text`, `user_send_image`
4. Lưu OA Access Token và tạo Webhook Secret

### Cấu hình trong Odoo

`CRM → AI Banking → Cấu hình AI → Tab Zalo OA`

### Cách hoạt động

Khi khách nhắn tin qua Zalo OA:
1. Odoo tự động tìm Opportunity theo số điện thoại
2. Nếu chưa có → tạo Lead mới, gắn tag **"Từ Zalo"**
3. Tin nhắn xuất hiện trong Chatter: `[Zalo] Nội dung tin nhắn`
4. AI nhận diện nhu cầu → gắn tag tự động

### Xem tin nhắn Zalo trong CRM

Vào Opportunity → tab Chatter → tìm các message có prefix `[Zalo]`

---

## 9. Quản lý lịch sử cuộc gọi

### Xem tất cả cuộc gọi

`CRM → AI Banking → Lịch sử cuộc gọi AI`

Danh sách hiển thị:
- Thời gian gọi, lead liên quan
- Loại (call/meeting), kênh gọi
- Thời lượng, sentiment, trạng thái

### Xem chi tiết một phiên gọi

Click vào record → 2 tabs:

**Tab "Tóm tắt AI"**
- Tóm tắt nội dung cuộc gọi (Claude tạo)
- Danh sách action items

**Tab "Transcript"**
- Toàn bộ transcript từng câu
- Phân biệt NV / KH / Không rõ
- Timestamp từng câu

---

## Câu hỏi thường gặp

**Q: Email đến nhưng không thấy AI note trong Chatter?**
A: Kiểm tra `CRM → AI Banking → Cấu hình AI → Tab Automation → Auto Process Incoming Emails` đã bật chưa. Nếu bật rồi, AI xử lý bất đồng bộ ~1 phút, reload lại trang.

**Q: Transcript không hiện hoặc bị trống?**
A: Kiểm tra trình duyệt đã cấp quyền microphone chưa. Nếu dùng Deepgram, kiểm tra API key trong Tab STT.

**Q: Muốn đổi từ Deepgram sang server nội bộ cho realtime STT?**
A: `Tab STT → Realtime Transcription → đổi provider sang Local Server → nhập WebSocket URL`. Không cần restart Odoo.

**Q: Muốn thêm loại sản phẩm mới vào checklist?**
A: `CRM → AI Banking → Templates Hồ sơ → New`. Lưu ý field `product_type` phải trùng với giá trị trong field **"Loại sản phẩm"** trên Opportunity.

**Q: Daily digest gửi lúc mấy giờ và có thể tắt không?**
A: Giờ gửi cấu hình trong Tab Automation. Tắt toàn bộ tại `Settings → Technical → Scheduled Actions → CRM AI: Daily Digest → uncheck Active`.
