# Hướng dẫn sử dụng Phase 3 & Phase 4

> CRM AI Banking — Odoo 19 | Cập nhật: 2026-05-29

---

## Phase 3 — B2B Deep Features

### P3-1. Account Map B2B

**Mục đích:** Quản lý danh sách stakeholders tại doanh nghiệp — ai ra quyết định, ai ảnh hưởng, ai là gatekeeper.

**Cách dùng:**
1. Mở form Lead/Opportunity
2. Vào tab **"🏢 Account Map B2B"**
3. Nhấn **+ Add a line** để thêm stakeholder
4. Điền: Họ tên, Chức danh, Vai trò (CEO/CFO/...), Mức độ ảnh hưởng, Độ thân thiết
5. Cập nhật **Ngày liên hệ gần nhất** sau mỗi lần tiếp xúc

**Trường quan trọng:**
| Trường | Giải thích |
|--------|-----------|
| Vai trò | Chức vụ trong tổ chức |
| Mức độ ảnh hưởng | Ra quyết định / Người ảnh hưởng / Gatekeeper / Người dùng |
| Độ thân thiết | 1-5 sao — mức độ quan hệ với ngân hàng |

---

### P3-2. GPKD Scan — Quét Giấy phép kinh doanh

**Mục đích:** Chụp ảnh/scan GPKD → AI trích xuất tên công ty, MST, địa chỉ, ngành nghề → auto-fill vào partner.

**Cách dùng:**
1. Mở form Lead → nhấn **"🏢 Quét GPKD"** (header)
2. Wizard mở ra → chụp ảnh hoặc upload file GPKD
3. Nhấn **"Quét AI"** — OCR đọc thông tin
4. Kiểm tra kết quả, chỉnh sửa nếu cần
5. Nhấn **"Áp dụng"** → thông tin điền vào Partner

**Bảo mật:** Mã số thuế (MST) được lưu encrypted, không hiển thị trong chatter/log.

---

### P3-3. Financial AI — Phân tích BCTC

**Mục đích:** Upload BCTC (PDF hoặc ảnh) → OCR → AI highlight điểm bất thường → gợi ý câu hỏi cho RM. **AI chỉ gợi ý câu hỏi, không phân tích rủi ro tín dụng.**

**Cách dùng:**
1. Mở form Lead → tab **"📊 Tài liệu AI"**
2. Nhấn **"+ Thêm tài liệu"**
3. Chọn loại: **Báo cáo tài chính (BCTC)**
4. Đính kèm file PDF hoặc ảnh
5. Nhấn **"🔍 Phân tích AI"** → chờ ~30 giây
6. Kết quả xuất hiện trong tab **"Kết quả AI"** và post vào Chatter

**Ví dụ output AI:**
- 🔍 "Tài sản ngắn hạn giảm 40% so với năm trước"
- ❓ "Hỏi: Lý do và kế hoạch xử lý nợ ngắn hạn?"

**Bảo mật:** Tên công ty và MST được ẩn danh trước khi gửi Claude.

---

### P3-4. Proposal Generator — Sinh Đề xuất

**Mục đích:** AI fill template đề xuất từ dữ liệu CRM. Nhân viên điền lãi suất/hạn mức từ biểu phí, AI không tự điền số tài chính.

**Cách dùng:**
1. Mở form Lead → nhấn **"📄 Sinh đề xuất"** (header)
2. Chọn template phù hợp (Vay mua nhà / Vay kinh doanh / Thẻ tín dụng)
3. Kiểm tra thông tin khách hàng đã được điền tự động
4. Thêm ghi chú đặc biệt nếu cần
5. Nhấn **"✨ Sinh đề xuất"**
6. Đọc kết quả → nhấn **"📎 Đính kèm vào Lead"** để lưu

**Templates hiện có:**
| Template | Placeholders AI fill |
|----------|---------------------|
| Vay mua nhà | Tên KH, số tiền, thời hạn, địa chỉ TS |
| Vay kinh doanh | Tên KH, tên công ty, hạn mức, mục đích |
| Thẻ tín dụng | Tên KH, hạn mức |

---

### P3-5. Cross-sell Engine B2B

**Mục đích:** AI gợi ý sản phẩm cross-sell dựa trên sản phẩm hiện tại và profile khách.

**Cách dùng:**
1. Mở form Lead → tab **"🏦 Sản phẩm phù hợp"**
2. Nhấn **"🔁 Cross-sell"**
3. Kết quả xuất hiện trong Chatter sau ~30 giây

---

## Phase 4 — AI Intelligence Layer

### P4-1. AI Next Best Action (NBA)

**Mục đích:** Phân tích toàn bộ trạng thái lead → đề xuất 1 hành động tốt nhất cần làm ngay.

**Banner NBA** hiển thị ngay đầu form lead:

```
🎯 HÀNH ĐỘNG TIẾP THEO:  [KHẨN]
📞 Gọi xác nhận tiến độ hồ sơ — khách im 3 ngày
"Lý do: Sentiment tích cực, XS 78%, checklist thiếu 2 giấy tờ"
💬 "Anh ơi, em muốn hỏi thăm về hồ sơ của anh..."
[🔄 Tính lại]  [✕ Bỏ qua]
```

**Trigger tự động:**
- Sau mỗi cuộc gọi kết thúc
- Sau email/Zalo message mới
- Cron hàng ngày 3:00 AM

**Manual trigger:** Nhấn **"🔄"** trong banner NBA.

**Action types NBA:**

| Action | Ý nghĩa |
|--------|---------|
| `call` | Gọi điện cho khách |
| `send_zalo` | Gửi tin Zalo |
| `send_proposal` | Gửi đề xuất |
| `schedule_meeting` | Hẹn gặp |
| `escalate_manager` | Leo thang manager |
| `send_document_reminder` | Nhắc hồ sơ |
| `close_won` | Chốt thắng |
| `mark_cold` | Đánh dấu nguội |

---

### P4-2. AI Product Recommendation

**Mục đích:** Kết hợp rule-based eligibility + AI scoring → gợi ý top 3 sản phẩm phù hợp nhất.

**Kiến trúc 2 lớp:**
1. **Rule Engine** — lọc sản phẩm đủ điều kiện (thu nhập, tuổi, v.v.)
2. **AI Scoring** — Claude xếp hạng theo nhu cầu, hành vi, sentiment

**Cách dùng:**
1. Tab **"🏦 Sản phẩm phù hợp"** → nhấn **"✨ Phân tích gợi ý"**
2. Chờ ~30 giây → top 3 sản phẩm hiển thị với:
   - % phù hợp (màu xanh ≥80%, vàng ≥60%, xám <60%)
   - Lý do cụ thể (từ hành vi, nhu cầu nhận diện)
   - Cách tiếp cận gợi ý

**Cấu hình Admin:**
- Menu **AI Banking → Quy tắc sản phẩm** → thêm/sửa điều kiện eligibility
- Sản phẩm mặc định: Vay mua nhà, Vay KD, Thẻ Vàng, Thẻ Bạch Kim, Tiết kiệm, Payroll, POS, L/C

---

### P4-3. AI Sales Coach

**Mục đích:** Phân tích transcript cuộc gọi sau khi kết thúc → cho điểm 5 kỹ năng → highlight khoảnh khắc quan trọng.

**5 kỹ năng được đánh giá (thang 0-10):**

| Kỹ năng | Đánh giá về |
|---------|-----------|
| Chào hỏi / Rapport | Mở đầu, xây dựng tin tưởng |
| Khám phá nhu cầu | Câu hỏi mở, lắng nghe |
| Kết nối sản phẩm | Liên kết nhu cầu → sản phẩm đúng |
| Xử lý từ chối | Xử lý objection, lo lắng |
| Kỹ năng chốt | Chốt deal, bước tiếp theo cụ thể |

**Cách dùng:**
1. Mở phiên gọi đã kết thúc
2. Tab **"🏆 AI Sales Coach"** → nhấn **"+ Tạo báo cáo Sales Coach"**
3. Trong form báo cáo → nhấn **"🤖 Phân tích AI"**
4. Chờ ~30 giây → xem điểm số + nhận xét chi tiết

**Quyền truy cập:**
- Nhân viên thấy báo cáo của mình (`visible_to_user = True`)
- Manager thấy tất cả → có thể ẩn trước khi share

---

### P4-4. AI Customer 360°

**Mục đích:** Tổng hợp toàn bộ thông tin khách hàng thành 1 bản tóm tắt ngắn gọn — nhân viên mới hiểu ngay trong 30 giây.

**Nguồn dữ liệu tổng hợp:**
- Stage, xác suất, thời gian trong pipeline
- Lịch sử cuộc gọi + sentiment
- Email + Zalo messages gần nhất
- Tiến độ checklist hồ sơ
- Nhu cầu đã nhận diện

**Cách dùng:**
1. Tab **"👤 Customer 360°"** trên form Lead
2. Nhấn **"🔄 Cập nhật"** → chờ ~30 giây
3. Panel hiển thị:
   - 👤 Profile snapshot
   - 📊 Lịch sử quan hệ
   - 📍 Tình trạng hiện tại + việc cần làm
   - 🎯 Nhu cầu chính
   - ⚠️ Lo lắng / phản đối
   - 💡 Cơ hội bán thêm
   - 🚀 Cách tiếp cận được khuyến nghị

---

## Luồng dữ liệu tổng thể

```
Khách hàng
    │
    ├─[Zalo/Email]──────→ Lead + chatter log → AI intent/needs → NBA update
    ├─[Cuộc gọi]────────→ Transcript → AI summary → Coaching report → NBA update
    ├─[CCCD/GPKD scan]──→ OCR extract → Partner fields (MST/CCCD encrypted)
    ├─[BCTC upload]─────→ OCR → Anonymize → AI câu hỏi → Chatter note
    └─[Manual input]────→ Lead fields → NBA + 360 recompute
                                           │
                    ┌──────────────────────┤
                    │                      │
                    ▼                      ▼
            NBA banner         Customer 360 panel
          (1 hành động)      (tóm tắt toàn diện)
                    │
                    ▼
          Product Recommendations
            (top 3 sản phẩm)
```

---

## Cài đặt ban đầu cho Phase 3+4

### 1. Nâng cấp module sau khi deploy

```bash
cd /Users/trung/projects/odoo
./odoo-bin -u crm_ai_banking -d odoo_dev -c odoo.conf
```

### 2. Cấu hình quy tắc sản phẩm (Admin)

1. Menu **CRM → AI Banking → Quy tắc sản phẩm**
2. Dữ liệu mẫu đã được cài sẵn (8 sản phẩm)
3. Tùy chỉnh theo biểu phí thực tế của ngân hàng

### 3. NBA tự động tính lại hàng ngày

Cron **"CRM AI: Refresh NBA"** chạy lúc 3:00 AM — tự động cập nhật NBA cho tối đa 100 leads active.

Để trigger thủ công: **CRM → Technical → Automation → Scheduled Actions → CRM AI: Refresh NBA → Run Manually**

---

## Kiến trúc bảo mật

| Dữ liệu | Xử lý |
|---------|-------|
| Số CCCD | Lưu encrypted, không log chatter, không gửi external API |
| MST (Mã số thuế) | Như trên |
| Số tài khoản | Pattern `[ACCOUNT_NO]` trước khi gửi Claude |
| BCTC | Tên công ty → `[COMPANY]`, MST → `[TAX_ID]` trước khi gửi |
| Tên, nhu cầu KH | Có thể gửi Claude (data không định danh) |
