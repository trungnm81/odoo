# Hướng dẫn sử dụng Phase 2: Capture & Zalo

> Cập nhật: 2026-05-29

---

## 1. Cấu hình cần thiết trước khi dùng

### 1.1 Cấu hình chung (đã có từ Phase 1)
Vào **CRM → AI Banking → Cấu hình AI**:
- LLM: Claude API key hoặc OpenRouter API key
- OCR: OpenRouter API key (dùng Qwen VL cho CCCD/GPKD) hoặc cấu hình OCR server nội bộ

### 1.2 Cấu hình Zalo OA (mới — Phase 2)
```
Tab "Zalo OA":
  Zalo OA Access Token: lấy từ Zalo Developer Console
  Webhook Secret: chuỗi bí mật để verify request Zalo
```

Đăng ký webhook URL với Zalo:
```
https://your-domain.com/crm/ai/webhook/zalo
```
*Khi Zalo verify (GET request), server tự trả về challenge. Không cần xử lý thêm.*

---

## 2. Quét Name Card (P2-1)

### Từ form Lead/Opportunity:
1. Mở Lead → Header → **[📇 Quét Card]**
2. Wizard mở ra:
   - `Loại tài liệu`: chọn "Name Card / Danh thiếp"
   - `Ảnh tài liệu`: upload ảnh name card (JPG/PNG)
   - Bấm **[🔍 Quét OCR]**
3. Kết quả hiển thị (JSON + bảng thông tin trích xuất)
4. Chỉnh sửa nếu cần → Bấm **[✅ Áp dụng vào Lead / Partner]**
5. Hệ thống:
   - Kiểm tra trùng partner qua phone hoặc email
   - Nếu đã có: cập nhật thông tin
   - Nếu chưa có: tạo partner mới → gắn vào lead hiện tại

### Từ mobile (REST API):
```bash
POST /crm/ai/scan-card
Content-Type: multipart/form-data

image=@namecard.jpg
scan_type=name_card
lead_id=123   (tùy chọn)
```
Response:
```json
{"result": {"full_name": "Nguyễn Văn A", "phone": "0912345678", ...}}
```

---

## 3. Quét CCCD (P2-2)

### Lưu ý bảo mật quan trọng
- Số CCCD **chỉ lưu trong database**, không gửi ra ngoài
- Chỉ admin (group `base.group_system`) mới thấy số CCCD trong profile
- Nhân viên thường chỉ thấy họ tên, ngày sinh, giới tính, địa chỉ

### Cách dùng:
1. Mở Lead → **[📇 Quét Card]** → chọn "CCCD mặt trước"
2. Upload ảnh mặt trước CCCD
3. Bấm **[🔍 Quét OCR]**
4. Kết quả hiển thị (số CCCD ẩn, chỉ thấy tên/ngày sinh/địa chỉ)
5. Bấm **[✅ Áp dụng vào Lead / Partner]**
6. Thông tin được cập nhật vào `res.partner`:
   - Họ tên, ngày sinh, giới tính
   - Địa chỉ thường trú
   - Số CCCD (chỉ admin thấy)
   - Ngày cấp, nơi cấp

---

## 4. Zalo Integration (P2-3)

### 4.1 Nhận tin nhắn từ Zalo
Khi khách nhắn tin qua Zalo OA:
1. Zalo gửi webhook đến `/crm/ai/webhook/zalo`
2. Hệ thống verify signature → tìm lead theo `zalo_user_id`
   - Có lead: log message vào chatter
   - Không có: tạo lead mới, gán tag "Từ Zalo"
3. AI tự động phân tích nhu cầu từ nội dung tin nhắn → cập nhật tags

### 4.2 Gán Zalo User ID cho khách hàng
Cách 1: Hệ thống tự gán khi nhận tin nhắn đầu tiên từ Zalo
Cách 2: Nhập thủ công:
- Mở Lead → Field **"Zalo User ID"** → nhập ID
- Hoặc vào `res.partner` → tab thông tin → field "Zalo User ID"

### 4.3 Gửi tin nhắn Zalo
Button **[📱 Gửi Zalo]** chỉ hiện khi lead có `zalo_user_id`.

1. Bấm **[📱 Gửi Zalo]** trên form lead
2. Wizard mở ra:
   - `Zalo User ID`: tự điền từ lead/partner
   - `Nội dung tin nhắn`: soạn thủ công
3. Tùy chọn: **[✨ AI Gợi ý]** → hệ thống sinh 2 draft dựa trên lịch sử chatter
4. Chọn draft → chỉnh sửa → **[📱 Gửi Zalo]**
5. Tin nhắn được log vào chatter: "📱 [Zalo gửi đi] ..."

---

## 5. AI Nhận diện Nhu cầu (P2-4)

### Auto-trigger (tự động)
Hệ thống tự nhận diện nhu cầu khi:
- **Email đến**: Claude phân tích body email
- **Zalo message**: Claude phân tích text
- **Cuộc gọi kết thúc**: Claude phân tích transcript

Kết quả → tự động thêm tags vào lead:
| Nhu cầu nhận diện | Tag được thêm |
|-------------------|---------------|
| loan | Vay vốn |
| credit_card | Thẻ tín dụng |
| savings | Tiết kiệm |
| insurance | Bảo hiểm |
| payroll | Payroll |
| lc | L/C |
| fx | Ngoại tệ |
| pos | POS |

---

## 6. AI Copilot Soạn Tin nhắn (P2-5)

### Từ Wizard Gửi Zalo
1. Mở **[📱 Gửi Zalo]**
2. Bấm **[✨ AI Gợi ý]**
3. Hệ thống lấy 5 messages gần nhất + context lead → gọi Claude
4. 2 draft xuất hiện (tone: informal cho Zalo)
5. Bấm **"Dùng phương án 1/2"** → điền vào ô soạn
6. Chỉnh sửa → **[📱 Gửi Zalo]**

### API trực tiếp (cho developer)
```
POST /crm/ai/copilot/suggest
{
  "lead_id": 123,
  "channel": "zalo"   // "zalo" = informal, "general" = professional
}
```
Response:
```json
{
  "drafts": [
    {"tone": "informal", "text": "Anh ơi, ..."},
    {"tone": "informal", "text": "Chào anh, ..."}
  ]
}
```

---

## 7. Kiểm tra hoạt động

### Checklist
- [ ] OCR Name Card: upload ảnh → kết quả đúng họ tên, phone, email
- [ ] OCR CCCD: upload ảnh mặt trước → họ tên/ngày sinh điền đúng vào partner
- [ ] Số CCCD: chỉ hiện khi login bằng admin, ẩn với nhân viên thường
- [ ] Zalo webhook: gửi test POST từ Zalo console → message xuất hiện trong chatter
- [ ] Gửi Zalo: nhập nội dung → gửi → chatter log "📱 [Zalo gửi đi]"
- [ ] AI Copilot: bấm "✨ AI Gợi ý" → 2 draft xuất hiện trong vài giây
- [ ] Mobile scan: `curl -X POST /crm/ai/scan-card -F image=@card.jpg` → JSON

### Troubleshooting thường gặp

**Quét OCR không có kết quả:**
- Kiểm tra `ocr_provider` trong AI Config
- Nếu dùng OpenRouter: verify `openrouter_api_key` và `openrouter_ocr_model` (mặc định: qwen/qwen3-vl)
- Ảnh phải rõ nét, đủ sáng, không bị mờ

**Gửi Zalo lỗi "Token không hợp lệ":**
- Zalo Access Token hết hạn sau 3 tháng — lấy token mới từ Zalo Developer Console
- Cập nhật tại: AI Banking → Cấu hình AI → Zalo OA

**Webhook Zalo không nhận message:**
- Kiểm tra URL đã đăng ký đúng chưa
- Server phải có HTTPS certificate hợp lệ
- Test bằng cách gửi tin nhắn thử qua Zalo app
