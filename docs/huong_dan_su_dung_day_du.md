# Hướng dẫn sử dụng CRM AI Banking — Toàn bộ tính năng

> Phiên bản: 2026-05-30 | Phù hợp với: Odoo 19 + crm_ai_banking (Phase 1–4 + Gap fixes)

---

## Mục lục

1. [Cấu hình hệ thống](#1-cấu-hình-hệ-thống)
2. [Quản lý Lead & Opportunity](#2-quản-lý-lead--opportunity)
3. [Gọi điện AI Realtime](#3-gọi-điện-ai-realtime)
4. [Email AI tự động](#4-email-ai-tự-động)
5. [Zalo Integration](#5-zalo-integration)
6. [Scan tài liệu (CCCD / Name Card / GPKD / BCTC)](#6-scan-tài-liệu)
7. [Checklist hồ sơ động](#7-checklist-hồ-sơ-động)
8. [AI Sales Coach](#8-ai-sales-coach)
9. [Next Best Action (NBA)](#9-next-best-action-nba)
10. [AI Product Recommendation](#10-ai-product-recommendation)
11. [Customer 360°](#11-customer-360)
12. [Account Map B2B](#12-account-map-b2b)
13. [Sinh đề xuất / Proposal](#13-sinh-đề-xuất--proposal)
14. [Cross-sell Engine](#14-cross-sell-engine)
15. [Cảnh báo tự động (Cron)](#15-cảnh-báo-tự-động-cron)
16. [Referral Tracking](#16-referral-tracking)
17. [Báo cáo & Theo dõi KPI](#17-báo-cáo--theo-dõi-kpi)

---

## 1. Cấu hình hệ thống

**Menu:** AI Banking → Cấu hình AI

### 1.1 Cấu hình LLM (Claude)

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| Claude API Key | Key từ console.anthropic.com | `sk-ant-...` |
| Model Text | Model Claude dùng cho phân tích văn bản | `claude-sonnet-4-6` |
| Model Vision | Model Claude dùng cho phân tích ảnh | `claude-opus-4-8` |

### 1.2 Cấu hình OCR

| Provider | Khi nào dùng | Cấu hình |
|----------|-------------|---------|
| `api` (OpenRouter) | Giai đoạn test / bắt đầu | OpenRouter API Key + model `qwen/qwen3-vl` |
| `local` | Môi trường production nội bộ | OCR Local Endpoint + API Key |

> **Chuyển provider**: Chỉ đổi trường "OCR Provider" từ `api` → `local`, không cần thay code.

### 1.3 Cấu hình STT (Speech-to-Text)

| Loại | Provider API | Provider Local |
|------|-------------|---------------|
| Batch (upload file) | OpenAI Whisper | faster-whisper server |
| Realtime (streaming) | Deepgram | whisper-streaming WebSocket |

### 1.4 Cấu hình Zalo OA

Điền **Zalo OA Access Token** và **Webhook Secret** để:
- Nhận tin nhắn từ khách hàng qua Zalo
- Gửi tin nhắn nhắc hồ sơ / tư vấn

### 1.5 Kiểm tra kết nối

Nhấn các nút **"Test LLM"**, **"Test OCR"**, **"Test STT Batch"** để xác nhận provider hoạt động trước khi dùng thực tế.

---

## 2. Quản lý Lead & Opportunity

### 2.1 Khi nào tạo Lead?

Tạo **Lead** khi chưa biết rõ khách hàng hoặc nhu cầu chưa xác nhận:
- Khách hàng mới liên hệ lần đầu qua Zalo/Web/Email
- Danh sách import từ hội thảo, chiến dịch marketing
- Số điện thoại chưa gọi lần nào

### 2.2 Khi nào tạo Opportunity?

Tạo **Opportunity** khi đã biết KH + nhu cầu rõ ràng:
- Hội sở đẩy khách hiện hữu xuống chi nhánh
- Sau khi qualify Lead thành công
- Khách cũ quay lại với nhu cầu mới

### 2.3 Chuyển Lead → Opportunity

1. Mở Lead → Nhấn **"Chuyển thành Cơ hội"**
2. Chọn `product_type` (Vay mua nhà / Thẻ tín dụng / v.v.)
3. Hệ thống tự động tạo **Checklist hồ sơ** theo sản phẩm

### 2.4 Trường quan trọng trên Opportunity

| Trường | Mô tả |
|--------|-------|
| Loại sản phẩm (`product_type`) | Xác định loại sản phẩm → kích hoạt checklist, NBA, gợi ý cross-sell |
| Zalo User ID | Để gửi tin nhắn Zalo OA trực tiếp cho KH |
| Người giới thiệu (`referred_by_partner_id`) | KH hoặc đối tác đã giới thiệu lead này |
| Kênh giới thiệu (`referral_source`) | BĐS / Showroom ô tô / KH hiện hữu / v.v. |

---

## 3. Gọi điện AI Realtime

**Nút:** `🎤 Gọi AI` trên header form Opportunity

### 3.1 Luồng thực hiện

```
Nhấn "🎤 Gọi AI"
    ↓
Chọn kênh gọi:
  [Twilio]      → Hệ thống gọi ra SĐT của KH qua Twilio
  [Softphone]   → Dùng mic máy tính (WebRTC)
  [Điện thoại]  → Để điện thoại thường gần mic
  [Mobile]      → Upload audio từ điện thoại di động
    ↓
LiveCallScreen hiển thị:
  • Transcript realtime (phân biệt NV / KH)
  • AI Hints mỗi 30 giây (opt-in)
    ↓
Nhấn "⏹ Kết thúc & Tóm tắt"
    ↓
AI (Claude) phân tích transcript:
  • Tóm tắt cuộc gọi
  • Danh sách việc cần làm (action items)
  • Sentiment (tích cực / tiêu cực / có phản đối)
  • Nhu cầu nhận diện được
    ↓
Tự động:
  • Post tóm tắt vào chatter
  • Tạo activity follow-up
  • Cập nhật ai_last_sentiment
  • Kích hoạt tính lại NBA
```

### 3.2 AI Hints (opt-in)

- Bật/tắt trong **AI Configuration → Enable AI Hints**
- Mỗi 30 giây gửi transcript gần nhất → Claude phân tích → gợi ý câu hỏi còn thiếu
- Ví dụ: *"Chưa hỏi về thời hạn vay và tài sản đảm bảo"*

### 3.3 Xem lịch sử cuộc gọi

Nhấn nút **stat button "Cuộc gọi AI"** trên đầu form → Danh sách tất cả phiên gọi với transcript đầy đủ.

---

## 4. Email AI tự động

**Không cần thao tác thủ công** — hệ thống tự xử lý email đến.

### 4.1 Luồng xử lý

```
Email đến alias của Lead
    ↓
Odoo tạo message → hook override message_new()
    ↓
Async: Claude phân tích email
  • Tóm tắt nội dung (3-5 gạch đầu dòng)
  • Intent: pricing_inquiry / ready_to_buy / complaint / document_request / follow_up
  • Urgency: high / medium / low
  • Nhu cầu nhận diện
    ↓
Post internal note tóm tắt vào chatter
    ↓
Tạo activity tự động theo intent:
  pricing_inquiry   → "Gửi báo giá" (deadline 1 ngày)
  ready_to_buy      → "Follow up ngay" (deadline hôm nay) + notify qua Discuss
  complaint         → "Xử lý khiếu nại" (deadline hôm nay)
  document_request  → "Kiểm tra hồ sơ" (deadline 1 ngày)
```

---

## 5. Zalo Integration

### 5.1 Nhận tin nhắn từ KH

- KH nhắn Zalo OA → Webhook tự nhận → match với Lead theo `zalo_user_id`
- Nếu không match → tạo Lead mới, tag "Từ Zalo"
- AI phân tích intent + nhu cầu → post internal note

### 5.2 Gửi tin nhắn Zalo

**Cách 1 — Nút "📱 Gửi Zalo"** (cần `zalo_user_id` trên lead):
1. Nhấn **"📱 Gửi Zalo"**
2. Wizard hiện 2 draft gợi ý từ AI (dựa trên lịch sử chatter)
3. Chọn draft → chỉnh sửa → Gửi

**Cách 2 — Nhắc hồ sơ tự động**:
1. Nhấn **"📋 Nhắc hồ sơ Zalo"** (hiện khi lead có `zalo_user_id` + checklist)
2. Hệ thống tự soạn tin nhắn liệt kê các giấy tờ còn thiếu
3. Gửi qua Zalo OA + log vào chatter

> **Yêu cầu**: Phải điền `Zalo User ID` của KH vào trường tương ứng trên Lead.

### 5.3 AI Copilot soạn tin nhắn

Trong ô soạn tin ở chatter → nhấn nút **"✨ Gợi ý AI"**:
- Lấy 5 messages gần nhất + context lead
- Claude trả về 2 draft khác nhau
- Chọn draft → chỉnh → gửi (**nhân viên phải review, không auto-send**)

---

## 6. Scan tài liệu

### 6.1 Name Card → Tạo Lead

**Nút:** `📇 Quét Card` trên header Lead

1. Upload ảnh name card
2. Claude Vision extract: tên, số điện thoại, email, công ty, chức vụ
3. Hệ thống kiểm tra trùng theo phone/email
4. Tạo Lead mới hoặc confirm merge nếu trùng

### 6.2 CCCD → Auto-fill thông tin KH

**Wizard Scan tài liệu** → chọn `scan_type = cccd`:

1. Upload ảnh CCCD mặt trước
2. OCR extract: họ tên, ngày sinh, giới tính, địa chỉ, số CCCD
3. Số CCCD lưu **encrypted** vào `res.partner.cccd_number` — không xuất hiện trong chatter
4. Auto-fill partner: tên, ngày sinh, địa chỉ, giới tính

> **Bảo mật**: Số CCCD được anonymize (`[ID_NUMBER]`) trước khi gửi bất kỳ API nào.

### 6.3 GPKD → Auto-fill thông tin doanh nghiệp

**Nút:** `🏢 Quét GPKD` trên header Lead

1. Upload ảnh GPKD
2. OCR extract: tên công ty, MST, địa chỉ, ngành nghề, vốn điều lệ, người đại diện
3. MST anonymize (`[TAX_ID]`) trước khi gửi Claude
4. Auto-fill partner: tên công ty, MST (encrypted), ngành nghề

### 6.4 BCTC → Gợi ý câu hỏi cho RM

**Tab "📊 Tài liệu AI"** trên form Lead:

1. Nhấn **"Thêm BCTC"** → đính kèm file PDF
2. Nhấn **"Phân tích AI"**
3. Hệ thống OCR → anonymize tên công ty/MST → Claude phân tích
4. Kết quả hiển thị:
   - **Điểm cần chú ý**: Tài sản ngắn hạn giảm 40%, vòng quay hàng tồn kho chậm, v.v.
   - **Câu hỏi gợi ý cho RM**: Hỏi KH về lý do và kế hoạch xử lý

> **Lưu ý quan trọng**: AI chỉ **gợi ý câu hỏi cho RM** — không phân tích rủi ro tín dụng thay thế bộ phận thẩm định.

---

## 7. Checklist hồ sơ động

### 7.1 Tự động tạo checklist

Khi chọn `product_type` trên Opportunity → Checklist tự động tạo với danh sách giấy tờ theo sản phẩm.

| Sản phẩm | Ví dụ giấy tờ |
|----------|--------------|
| Vay mua nhà | CCCD, đăng ký kết hôn, sao kê lương 3 tháng, giấy tờ tài sản |
| Vay kinh doanh | CCCD, GPKD, BCTC 2 năm gần nhất, sao kê ngân hàng |
| Thẻ tín dụng | CCCD, hợp đồng lao động, sao kê lương |

### 7.2 Cập nhật trạng thái hồ sơ

Trong tab **Checklist hồ sơ** → Cập nhật từng item:
- `pending` → Chưa nộp
- `submitted` → Đã nộp, chờ duyệt
- `approved` → Đã duyệt
- `rejected` → Cần bổ sung lại

Trường `completion_rate` tự tính % hoàn thành.

### 7.3 Nhắc hồ sơ thiếu qua Zalo

1. Nhấn **"📋 Nhắc hồ sơ Zalo"** trên header
2. Hệ thống lấy danh sách item trạng thái `pending`
3. Tự soạn tin nhắn lịch sự, gửi qua Zalo OA
4. Log tin nhắn vào chatter

---

## 8. AI Sales Coach

**Menu:** AI Banking → Báo cáo Sales Coach  
**Hoặc:** Tab "🏆 AI Sales Coach" trong phiên gọi

### 8.1 Tạo báo cáo coach

1. Mở phiên gọi đã có transcript
2. Tab **"🏆 AI Sales Coach"** → Nhấn **"Tạo báo cáo Coach"**
3. Nhấn **"Phân tích AI"** → Claude phân tích transcript

### 8.2 Các chỉ số đánh giá (0–10)

| Chỉ số | Nội dung đánh giá |
|--------|------------------|
| Chào hỏi | Xây dựng rapport, tạo thiện cảm ban đầu |
| Khám phá nhu cầu | Đặt câu hỏi mở, lắng nghe chủ động |
| Kết nối sản phẩm | Liên kết nhu cầu KH với sản phẩm phù hợp |
| Xử lý từ chối | Kỹ năng phản hồi objection |
| Kỹ năng chốt | Dẫn dắt đến bước tiếp theo, chốt hành động |
| **Tổng thể** | Trung bình 5 chỉ số |

### 8.3 Phản hồi chi tiết

- **Điểm mạnh**: Những gì nhân viên làm tốt
- **Cần cải thiện**: Điểm cụ thể cần thay đổi
- **Cơ hội bỏ lỡ**: Tình huống có thể khai thác tốt hơn
- **Khoảnh khắc quan trọng**: Timestamp + câu nói cụ thể + gợi ý câu thay thế

> **Quyền truy cập**: Manager có thể ẩn báo cáo (`visible_to_user = False`) trước khi chia sẻ với nhân viên.

---

## 9. Next Best Action (NBA)

NBA là **1 hành động tốt nhất cần làm ngay** — không phải danh sách, mà là quyết định cụ thể kèm lý do rõ ràng.

### 9.1 NBA Banner trên form Lead

Banner xuất hiện ở đầu form khi NBA đã được tính:

```
┌─────────────────────────────────────────────────────┐
│  🎯 HÀNH ĐỘNG TIẾP THEO:  [KHẨN]                   │
│  Gọi xác nhận tiến độ hồ sơ                         │
│  Lý do: Sentiment tích cực, chờ 3 ngày              │
│  💬 "Anh ơi, em muốn hỏi thăm về hồ sơ..."          │
│  [🔄 Tính lại]  [✕ Bỏ qua]                          │
└─────────────────────────────────────────────────────┘
```

Khi NBA = `close_won` (KH sẵn sàng chốt), banner chuyển **màu xanh lá nổi bật**:
```
┌─────────────────────────────────────────────────────┐
│  🏆 KHÁCH HÀNG SẴN SÀNG CHỐT HỢP ĐỒNG!             │
│  [✍️ Lên lịch ký hợp đồng]  [✕ Bỏ qua]              │
└─────────────────────────────────────────────────────┘
```

### 9.2 Các loại hành động NBA

| action_type | Ý nghĩa |
|-------------|---------|
| `call` | Gọi điện cho KH |
| `send_zalo` | Gửi tin nhắn Zalo |
| `send_email` | Gửi email |
| `send_proposal` | Gửi đề xuất/term sheet |
| `schedule_meeting` | Hẹn gặp trực tiếp |
| `escalate_manager` | Báo cáo manager |
| `send_document_reminder` | Nhắc bổ sung hồ sơ |
| `close_won` | Tiến hành ký hợp đồng |
| `mark_cold` | Đánh dấu lead nguội |

### 9.3 Khi nào NBA tự động tính lại?

- Sau mỗi cuộc gọi kết thúc
- Sau khi có email / Zalo message mới
- Sau khi activity được mark done
- Cron hàng ngày 3:00 AM (100 leads active)

### 9.4 Tính NBA thủ công

Nhấn **"🔄"** trên NBA banner → Tính ngay lập tức.

---

## 10. AI Product Recommendation

**Tab:** "🏦 Sản phẩm phù hợp" trên form Opportunity

### 10.1 Kiến trúc 2 lớp

```
Lớp 1 — Rule Engine (bắt buộc qua trước)
  Lọc sản phẩm KH đủ điều kiện (tuổi, thu nhập, sản phẩm hiện có)
        ↓
Lớp 2 — AI Scoring (Claude)
  Xếp hạng theo mức độ phù hợp dựa trên:
  • Nhu cầu đã nhận diện từ transcript/email/Zalo
  • Sentiment + lịch sử tương tác
  • Banking 360 profile (từ core banking)
        ↓
Top 3 sản phẩm + lý do cụ thể + cách tiếp cận gợi ý
```

### 10.2 Cách dùng

1. Mở tab **"🏦 Sản phẩm phù hợp"**
2. Nhấn **"Gợi ý AI"** → Kết quả xuất hiện sau ~30 giây
3. Mỗi sản phẩm hiển thị:
   - Tên sản phẩm + % phù hợp
   - 3 lý do cụ thể
   - Gợi ý cách tiếp cận

### 10.3 Cấu hình Quy tắc sản phẩm

**Menu:** AI Banking → Quy tắc sản phẩm

Admin cấu hình điều kiện cho từng sản phẩm:
- Thu nhập tối thiểu
- Độ tuổi (min/max)
- Mã cross-sell (sản phẩm nên bán kèm)

---

## 11. Customer 360°

**Tab:** "👤 Customer 360°" trên form Opportunity

### 11.1 Nội dung tổng hợp

```
profile_snapshot     — 2 câu mô tả KH: tuổi, nghề, thu nhập, nhu cầu chính
relationship_history — Lịch sử tương tác: số cuộc gọi, sentiment, kênh liên lạc
current_status       — Tình trạng hiện tại, checklist hoàn thành bao nhiêu %
key_needs            — Danh sách nhu cầu chính đã xác nhận
concerns_objections  — Lo lắng / từ chối đã ghi nhận
opportunities        — Cơ hội cross-sell / upsell chưa khai thác
recommended_approach — Cách tiếp cận được AI khuyến nghị
```

### 11.2 Cách làm mới

- Nhấn **"🔄 Làm mới"** thủ công bất kỳ lúc nào
- Tự động cập nhật sau cuộc gọi / email mới / Zalo message
- Cron hàng ngày (background, ưu tiên thấp)

### 11.3 B2B: Thông tin doanh nghiệp thêm vào

Nếu lead có tài liệu BCTC đã phân tích → Customer 360 tự bổ sung tình hình tài chính doanh nghiệp (đã anonymize).

---

## 12. Account Map B2B

**Tab:** "🏢 Account Map B2B" trên form Opportunity (dành cho KH doanh nghiệp)

### 12.1 Thêm stakeholder

1. Mở tab **"🏢 Account Map B2B"**
2. Nhấn **"Thêm"** → Điền thông tin:

| Trường | Giá trị |
|--------|---------|
| Vai trò | CEO / CFO / COO / Giám đốc HR / Kế toán trưởng / v.v. |
| Mức ảnh hưởng | Người quyết định / Người ảnh hưởng / Người gác cổng / Người dùng |
| Sức mạnh quan hệ | 1–5 sao |
| Ngày liên hệ cuối | Ngày gần nhất đã gặp/gọi |

### 12.2 Chiến lược tiếp cận B2B

- **Người quyết định (Decision Maker)**: CEO / CFO → cần gặp trực tiếp
- **Người ảnh hưởng (Influencer)**: Giám đốc tài chính → tư vấn chi tiết kỹ thuật
- **Người gác cổng (Gatekeeper)**: Thư ký / Trợ lý → xây dựng quan hệ để được giới thiệu

---

## 13. Sinh đề xuất / Proposal

**Nút:** `📄 Sinh đề xuất` trên header Opportunity

### 13.1 Luồng tạo Proposal

```
Nhấn "📄 Sinh đề xuất"
    ↓
Wizard hiện:
  • Chọn template (Vay mua nhà / Vay kinh doanh / Thẻ tín dụng)
  • Điền thông tin: số tiền, kỳ hạn, mục đích, địa chỉ tài sản
  • Tùy chọn: Ghi chú thêm cho AI (AI sẽ enhance nội dung)
    ↓
Nhấn "Tạo đề xuất"
    ↓
AI điền placeholder từ CRM data
AI enhance nếu có ghi chú thêm
    ↓
Preview nội dung
    ↓
Nhấn "Đính kèm vào Lead"
    ↓
Tạo file .txt đính kèm + post vào chatter
```

> **Quan trọng**: Lãi suất và hạn mức **không được AI tự điền** nếu không có trong CRM — nhân viên phải điền tay theo biểu phí.

---

## 14. Cross-sell Engine

**Menu:** AI Banking → Gợi ý sản phẩm AI  
**Hoặc:** Tab "Gợi ý sản phẩm" trên form Lead

### 14.1 Logic cross-sell B2B

| Điều kiện | Gợi ý |
|-----------|-------|
| Có payroll, chưa có POS | Gợi ý dịch vụ POS |
| Có tín dụng, doanh thu tăng > 20% | Gợi ý tăng hạn mức |
| Có L/C, công ty thương mại | Gợi ý FX hedging |

### 14.2 Cách sử dụng

Trên form Lead → Nhấn **"🔁 Cross-sell"** → AI phân tích sản phẩm hiện có → Gợi ý sản phẩm phù hợp tiếp theo trong chatter.

---

## 15. Cảnh báo tự động (Cron)

Hệ thống tự động chạy các công việc định kỳ, không cần thao tác thủ công.

### 15.1 Daily Digest (8:00 AM)

Mỗi sáng, nhân viên nhận tin nhắn tóm tắt qua **Discuss (DM)**:

```
Chào Minh, hôm nay có 3 việc ưu tiên:
🔥 Anh Nguyễn Văn A (Vay 2.5 tỷ) — xác suất 78%, chờ 3 ngày
📎 Công ty ABC — còn thiếu BCTC 2024
⏰ 2 activities quá hạn
❄️ 1 lead nguội cần re-engage
```

### 15.2 Sinh nhật tự động (7:00 AM)

Khi KH có sinh nhật trong **3 ngày tới**:
- Tự tạo activity "🎂 Chúc sinh nhật [Tên KH]" cho nhân viên phụ trách
- Deadline = ngày sinh nhật

### 15.3 Tiền gửi đến hạn (7:30 AM)

Khi sản phẩm tiết kiệm của KH đến hạn trong **14 ngày tới**:
- Tự tạo Opportunity "Tiết kiệm — Tư vấn gia hạn" với:
  - `partner_id` = KH có tiền gửi đến hạn
  - `product_type = tiet_kiem`
  - Activity "⏰ Tiền gửi đến hạn [ngày]"
- Nhân viên chỉ cần mở Opportunity và liên hệ KH

### 15.4 Lead nguội (9:00 AM)

Leads không cập nhật quá **N ngày** (cấu hình trong AI Config):
- AI phân tích lý do nguội
- Gợi ý cách re-engage
- Tạo activity "❄️ Re-engage lead nguội"

### 15.5 Deal lớn không có manager (9:30 AM)

Deal > **threshold** (mặc định 5 tỷ) mà không có tương tác manager trong 7 ngày:
- Gửi alert vào channel Discuss của nhóm
- Tạo activity "👔 Cần hỗ trợ manager"

### 15.6 Nhắc nộ khoản vay (thứ Hai hàng tuần)

KH có khoản vay active mà lead không có activity trong 30 ngày:
- Tạo activity "💳 Theo dõi khoản vay — Dư nợ [số tiền]"

### 15.7 NBA Refresh (3:00 AM)

Tính lại NBA cho tối đa 100 leads active mỗi đêm.

---

## 16. Referral Tracking

### 16.1 Ghi nhận người giới thiệu

Trên form Opportunity → Điền:
- **Người giới thiệu** (`referred_by_partner_id`): Chọn KH hoặc đối tác từ danh bạ
- **Kênh giới thiệu** (`referral_source`): BĐS / Showroom / KH hiện hữu / Đại lý BH / Khác

### 16.2 Dùng referral data

- Báo cáo **nguồn lead** theo `referral_source` + `source_id`
- Theo dõi đối tác nào giới thiệu nhiều nhất
- Ưu tiên chăm sóc đối tác có referral tốt

---

## 17. Báo cáo & Theo dõi KPI

### 17.1 Menu AI Banking

| Menu | Nội dung |
|------|---------|
| Tài liệu AI | Danh sách BCTC/GPKD đã phân tích |
| Quy tắc sản phẩm | Cấu hình điều kiện eligibility |
| Báo cáo Sales Coach | Điểm kỹ năng theo nhân viên, theo thời gian |
| Gợi ý sản phẩm AI | Lịch sử recommendation |
| Core Banking Sync | Trạng thái đồng bộ dữ liệu từ core banking |

### 17.2 Dashboard CRM (Odoo built-in)

- **Kanban Pipeline**: Kéo thả opportunity qua các stage
- **Forecast**: Dự báo doanh số theo tháng/quý
- **Activity**: Các việc cần làm hôm nay

### 17.3 AI Sales Coach Dashboard

**Menu:** AI Banking → Báo cáo Sales Coach

Xem điểm kỹ năng của từng nhân viên:
- Radar chart 5 kỹ năng
- So sánh tuần này vs tuần trước
- Top 3 điểm yếu cần cải thiện của team

---

## Phụ lục: Danh sách phím tắt & nút quan trọng

| Nút | Vị trí | Chức năng |
|-----|--------|-----------|
| 🎤 Gọi AI | Header Lead | Mở LiveCallScreen |
| 📱 Gửi Zalo | Header Lead | Soạn & gửi Zalo có AI draft |
| 📋 Nhắc hồ sơ Zalo | Header Lead | Gửi danh sách giấy tờ còn thiếu qua Zalo |
| 📇 Quét Card | Header Lead | Scan name card → tạo lead |
| 🏢 Quét GPKD | Header Lead | Scan GPKD → fill thông tin công ty |
| 📄 Sinh đề xuất | Header Lead | Tạo Proposal từ template |
| 🎯 Tính NBA | NBA Banner | Tính lại Next Best Action |
| ✍️ Lên lịch ký HĐ | NBA Banner (close_won) | Tạo activity ký hợp đồng |
| 🔄 Làm mới | Tab Customer 360 | Cập nhật lại Customer 360 |
| Gợi ý AI | Tab Sản phẩm phù hợp | Chạy AI Product Recommendation |
| 🔁 Cross-sell | Tab Gợi ý | Chạy AI Cross-sell |
| Phân tích AI | Tab Tài liệu AI | Phân tích BCTC/GPKD bằng AI |
