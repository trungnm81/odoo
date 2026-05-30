Error with Permissions-Policy header: Unrecognized feature: 'vr'.Understand this warning
login:1 Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/v833ccba57c9e4d2798f2e76cebdd09a11778172276447' violates the following Content Security Policy directive: "script-src 'self' 'unsafe-inline'". Note that 'script-src-elem' was not explicitly set, so 'script-src' is used as a fallback. The action has been blocked.# Phase 2: Capture & Zalo — Luồng xử lý chi tiết

> Cập nhật: 2026-05-29

---

## P2-1. Name Card Scan — Quét danh thiếp tạo Lead

### Luồng người dùng
```
Nhân viên nhận name card từ khách
        │
        ▼
Mở Lead → Header → [📇 Quét Card]
        │
        ▼
Wizard crm.ai.scan.document
  ├── Chọn scan_type = name_card
  ├── Upload ảnh
  └── [🔍 Quét OCR]
        │
        ▼
CrmAiService.extract_card(image_bytes)
  ├── llm_provider = 'openrouter' → OpenRouter + vision model
  └── llm_provider = 'anthropic'  → Anthropic Claude vision
        │
        ▼
JSON: {full_name, title, company, phone, email, address, website}
        │
        ▼
Wizard hiển thị kết quả → nhân viên chỉnh sửa nếu cần
        │
        ▼
[✅ Áp dụng vào Lead / Partner]
  ├── Tìm partner trùng qua phone hoặc email
  ├── Nếu có: update partner
  └── Nếu không: tạo partner mới → tạo/gắn lead
```

### Mobile REST
```
POST /crm/ai/scan-card
  Form: image (file), scan_type, lead_id (optional)
  Response: {"result": {...}}
```

### Files liên quan
- `wizard/crm_ai_scan_document.py` — logic OCR + field mapping + apply
- `controllers/zalo_webhook.py` — REST endpoint `/crm/ai/scan-card`
- `views/wizard_scan_document_views.xml` — form wizard
- `models/crm_ai_service.py:extract_card()` — Vision AI call

---

## P2-2. CCCD Scan — Quét CCCD tự động điền thông tin KH

### Luồng người dùng
```
Mở Lead → Header → [📇 Quét Card] → chọn "CCCD mặt trước"
        │
        ▼
CrmAiService.extract_id_card(image_bytes, 'cccd_front')
  ├── ocr_provider = 'api'   → OCR qua OpenRouter (Qwen VL)
  └── ocr_provider = 'local' → OCR server nội bộ
        │
        ▼
JSON: {full_name, date_of_birth, gender, place_of_origin,
       place_of_residence, id_number}
        │
        ▼
Anonymize: id_number không gửi ra Claude
        │
        ▼
Wizard hiển thị kết quả (id_number ẩn) → nhân viên xác nhận
        │
        ▼
[✅ Áp dụng] → res.partner.write({
  name, date_of_birth, gender, street,
  cccd_number (encrypted, chỉ admin thấy),
  cccd_issue_date, cccd_issue_place
})
Log chatter: "CCCD cập nhật ngày XX/XX/XXXX"
```

### Security
- `cccd_number` chỉ hiển thị cho `groups="base.group_system"`
- Không log số CCCD vào mail.message chatter
- OCR extract → wizard local → chỉ ghi vào database, không gửi ra external API

### Fields thêm vào res.partner
```python
cccd_number      # Char, groups=base.group_system (ẩn với nhân viên thường)
cccd_issue_date  # Date
cccd_issue_place # Char
date_of_birth    # Date
gender           # Selection: male/female/other
zalo_user_id     # Char, index=True (dùng cho Zalo matching)
```

---

## P2-3. Zalo Integration

### Webhook nhận message
```
Zalo OA → POST /crm/ai/webhook/zalo
        │
        ▼
Verify HMAC SHA256 signature (X-ZEvent-Signature)
        │
        ▼
event_name == 'user_send_text' | 'user_send_image' | 'user_send_file'
        │
        ▼
crm.lead._handle_zalo_incoming(data)
  ├── sender.id = zalo_user_id
  ├── Tìm lead theo zalo_user_id (trên lead hoặc partner)
  │   └── Nếu không tìm thấy: tạo lead mới, tag "Từ Zalo"
  ├── Log message vào chatter: "📱 [Zalo nhận] ..."
  └── Async: _ai_process_zalo_message(text)
              └── detect_needs() → auto-update tags
```

### Gửi tin nhắn Zalo
```
Lead Form → Header → [📱 Gửi Zalo]
        │
        ▼
Wizard crm.ai.zalo.compose
  ├── Hiển thị zalo_user_id (từ lead hoặc partner)
  ├── Ô soạn tin nhắn
  ├── [✨ AI Gợi ý] → gọi /crm/ai/copilot/suggest → 2 draft options
  └── [📱 Gửi Zalo]
        │
        ▼
POST https://openapi.zalo.me/v3.0/oa/message/cs
  Headers: access_token
  Body: {recipient: {user_id}, message: {text}}
        │
        ▼
Log chatter: "📱 [Zalo gửi đi] ..."
```

### Matching logic
- Lead có `zalo_user_id` field → tìm trực tiếp
- Partner có `zalo_user_id` → tìm lead gắn với partner
- Không tìm thấy → tạo lead type='lead', tag 'Từ Zalo'

### Cấu hình cần thiết
```
AI Banking → Cấu hình AI → Zalo OA:
  - Zalo OA Access Token
  - Webhook Secret
```

Webhook URL đăng ký với Zalo: `https://your-domain/crm/ai/webhook/zalo`

---

## P2-4. Nhận diện Nhu cầu Tài chính

### Auto-trigger
- Email đến → `_ai_process_incoming_email()` → `detect_needs()` → auto-tag
- Zalo message → `_ai_process_zalo_message()` → `detect_needs()` → auto-tag
- Cuộc gọi kết thúc → `_run_ai_summary()` → `detected_needs` → auto-tag

### Manual trigger
```
Lead Form → (không có button riêng, dùng Zalo compose → AI Gợi ý
             hoặc chạy lại AI Summary từ cuộc gọi)
```

### Needs mapping
```python
'loan'        → tag 'Vay vốn'
'credit_card' → tag 'Thẻ tín dụng'
'savings'     → tag 'Tiết kiệm'
'insurance'   → tag 'Bảo hiểm'
'payroll'     → tag 'Payroll'
'lc'          → tag 'L/C'
'fx'          → tag 'Ngoại tệ'
'pos'         → tag 'POS'
```

---

## P2-5. AI Copilot Soạn Tin nhắn

### Luồng
```
Lead Form → Wizard Zalo Compose → [✨ AI Gợi ý]
        │
        ▼
POST /crm/ai/copilot/suggest
  Params: {lead_id, channel: 'zalo' | 'general'}
        │
        ▼
Lấy 5 messages gần nhất từ chatter (loại internal note)
        │
        ▼
CrmAiService.generate_reply(conversation, lead_context, tone)
  - channel='zalo'    → tone='informal'
  - channel='general' → tone='professional'
        │
        ▼
Return: [{tone, text}, {tone, text}]  (2 drafts)
        │
        ▼
Wizard hiển thị 2 phương án → nhân viên click "Dùng" → điền vào ô soạn
```

### Nguyên tắc
- **Nhân viên luôn phải review** trước khi gửi — không auto-send
- Draft chỉ là gợi ý khởi đầu, nhân viên chỉnh sửa tự do
- Claude được cung cấp: 5 messages lịch sử + context lead (stage, product, partner name)

---

## Tóm tắt endpoints Phase 2

| Method | URL | Auth | Mô tả |
|--------|-----|------|-------|
| GET/POST | `/crm/ai/webhook/zalo` | public | Zalo OA webhook |
| POST | `/crm/ai/zalo/send` | user | Gửi tin Zalo từ browser |
| POST | `/crm/ai/scan-card` | user | Mobile REST scan card/CCCD |
| POST | `/crm/ai/copilot/suggest` | user | Sinh 2 AI draft reply |
