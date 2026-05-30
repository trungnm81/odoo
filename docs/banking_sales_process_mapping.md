# Mapping Quy trình Bán hàng Ngân hàng Bán lẻ → CRM AI Banking

## Tổng quan

Quy trình bán hàng chuẩn 8 bước của nhân viên kinh doanh bán lẻ (PFC/RM/SR) được map vào các chức năng hiện có của hệ thống CRM AI Banking.

**Mức độ hỗ trợ:**
- ✅ **Có đầy đủ** — Tính năng hoạt động hoàn chỉnh
- 🟡 **Có một phần** — Cần bổ sung hoặc chỉnh sửa
- ❌ **Chưa có** — Cần phát triển mới

---

## Bước 1 — Chuẩn bị & Tìm kiếm Khách hàng (Prospecting)

| Nguồn khách hàng | Tính năng CRM | Trạng thái | Ghi chú |
|-----------------|---------------|-----------|---------|
| Hội sở đẩy danh sách KH hiện hữu xuống | Tạo Opportunity với `source_id = "Hội sở"`, gán `user_id` chi nhánh | ✅ Có | Thủ công hoặc import |
| KH có tiền gửi đến hạn | Cảnh báo tự động từ đồng bộ core banking | 🟡 Một phần | Cần hoàn thiện `corebanking_sync` |
| Danh sách từ chiến dịch marketing | Import Lead hàng loạt (Odoo built-in) | ✅ Có | Dùng chức năng Import của Odoo |
| Tự khai thác: hội nhóm BĐS, SME | Tạo Lead thủ công hoặc từ Zalo | 🟡 Một phần | Tạo Lead được; chưa có tính năng khai thác tự động từ mạng xã hội |
| Kênh liên kết: môi giới BĐS, showroom ô tô | `source_id` + `referred` field | 🟡 Một phần | Ghi nhận nguồn được; chưa có portal riêng cho đối tác giới thiệu |

**Quy trình thực hiện trên CRM:**
1. Nhận danh sách từ hội sở → Import hoặc tạo Opportunity hàng loạt
2. Gán `source_id = "Hội sở"`, `user_id = nhân viên chi nhánh`, `product_type = sản phẩm mục tiêu`
3. KH tự liên hệ qua Zalo OA → tự động tạo Lead, gán cho nhân viên trực

---

## Bước 2 — Tiếp cận & Khơi gợi Nhu cầu (Approach & Qualification)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Gọi điện Telemarketing | `crm.ai.call.session` — Phiên gọi với transcription realtime | ✅ Có | Ghi âm, diarization, transcript |
| AI gợi ý câu hỏi mở trong lúc gọi | AI Hints trên LiveCallScreen (mỗi 30 giây) | ✅ Có | Opt-in per user |
| Nhận diện nhu cầu từ hội thoại | `ai_detected_needs_json`, `ai_last_sentiment` | ✅ Có | Tự động từ transcript |
| Ghi chú sau cuộc gọi | Tóm tắt cuộc gọi tự động → chatter | ✅ Có | Claude summarize post-call |
| Qualify: CIC, thu nhập | Đồng bộ từ core banking qua `corebanking_sync` | 🟡 Một phần | Cần cấu hình endpoint core banking |
| Chuyển Lead → Opportunity sau qualify | Nút "Chuyển thành Cơ hội" (Odoo built-in) | ✅ Có | |

**Quy trình thực hiện trên CRM:**
1. Mở Lead → nhấn "📞 Bắt đầu Cuộc gọi" → LiveCallScreen
2. AI Hints gợi ý câu hỏi khơi gợi nhu cầu
3. Kết thúc gọi → AI tóm tắt, cập nhật `ai_detected_needs_json`, `ai_last_sentiment`
4. Nếu qualify được → "Chuyển thành Cơ hội" → chọn `product_type` → Checklist hồ sơ tự động tạo

---

## Bước 3 — Tìm hiểu Nhu cầu & Tư vấn Giải pháp (Presentation)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Tư vấn sản phẩm vay (hạn mức, lãi suất, kỳ hạn) | Ghi chú + Proposal template | 🟡 Một phần | Template có; lãi suất thực tế nhân viên tự điền |
| Tư vấn tiết kiệm / đầu tư | Ghi chú chatter | 🟡 Một phần | Chưa có module riêng cho sản phẩm tiết kiệm |
| Gợi ý Cross-sell (thẻ, bảo hiểm, app) | `action_crosssell_suggestions()` — AI gợi ý cross-sell | ✅ Có | Hiển thị trong chatter |
| AI Product Recommendation (top 3 phù hợp) | Tab "Sản phẩm phù hợp" + `crm.product.recommendation` | ✅ Có | Rule engine + AI scoring |
| Sinh Proposal / Term Sheet | Wizard "📄 Sinh đề xuất" + `crm.ai.generate.proposal` | ✅ Có | Template vay nhà, vay KD, thẻ tín dụng |
| Customer 360 để hiểu KH trước tư vấn | Tab "👤 Customer 360°" | ✅ Có | Tổng hợp từ mọi nguồn |
| Copilot soạn tin nhắn / email tư vấn | `AiCopilot` trong chatter | ✅ Có | 2 draft, nhân viên chọn và chỉnh |

**Quy trình thực hiện trên CRM:**
1. Xem **Customer 360** để hiểu rõ KH trước khi tư vấn
2. Xem **Tab Sản phẩm phù hợp** → top 3 gợi ý với lý do cụ thể
3. Nhấn "📄 Sinh đề xuất" → chọn template → điền thông tin → AI fill từ CRM data
4. Dùng **Copilot** để soạn email/Zalo tư vấn, gửi đi sau khi review

---

## Bước 4 — Thẩm định & Thu thập Hồ sơ (Underwriting & Documentation)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Checklist hồ sơ theo loại sản phẩm | `crm.document.checklist` — tự tạo khi chọn `product_type` | ✅ Có | 8 loại sản phẩm, có % hoàn thành |
| Nhắc KH bổ sung hồ sơ còn thiếu | Activity tự động + Zalo nhắc | 🟡 Một phần | Activity có; Zalo nhắc tự động chưa hoàn thiện |
| Scan CCCD → auto-fill thông tin KH | Wizard "Scan CCCD" — OCR + anonymize | ✅ Có | Số CCCD encrypted, không lộ chatter |
| Scan GPKD → auto-fill thông tin công ty | Wizard "🏢 Quét GPKD" | ✅ Có | OCR extract MST, tên công ty, ngành nghề |
| Đọc BCTC → gợi ý câu hỏi cho RM | Tab "📊 Tài liệu AI" + `crm.ai.document` | ✅ Có | AI gợi ý câu hỏi, không phân tích rủi ro tín dụng |
| Thẩm định thực tế (đi xem tài sản) | Activity "Thẩm định thực tế" | 🟡 Một phần | Ghi nhận qua activity; chưa có form checklist thẩm định |

**Quy trình thực hiện trên CRM:**
1. Chọn `product_type` → Checklist tự sinh với danh sách giấy tờ cần thiết
2. Scan CCCD/GPKD → auto-fill `res.partner`
3. Đính kèm BCTC → nhấn "Phân tích AI" → xem câu hỏi gợi ý để hỏi KH
4. Tạo activity "📋 Thẩm định thực tế" → giao cho nhân viên, set deadline

---

## Bước 5 — Xử lý Từ chối & Giải quyết Băn khoăn (Handling Objections)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Ghi nhận objection trong cuộc gọi | Transcript + `ai_last_sentiment = objection` | ✅ Có | Tự động nhận diện từ transcript |
| AI Sales Coach phân tích kỹ năng xử lý từ chối | `crm.ai.coaching.report` — điểm `score_objection` | ✅ Có | Sau cuộc gọi, gợi ý câu nói thay thế |
| Gợi ý bước tiếp theo sau objection | `nba_suggested_message` từ NBA | 🟡 Một phần | NBA gợi ý bước tiếp; chưa có thư viện xử lý objection theo loại |
| Copilot soạn email / Zalo phản hồi | `AiCopilot` | ✅ Có | |
| Theo dõi KH đang do dự | `ai_last_sentiment`, NBA urgency | ✅ Có | NBA tính toán lại sau mỗi tương tác |

**Quy trình thực hiện trên CRM:**
1. Sau cuộc gọi có objection → AI tự động đặt `ai_last_sentiment = objection`
2. **NBA** tính toán lại → gợi ý hành động phù hợp (ví dụ: "Gửi so sánh lợi ích qua Zalo")
3. Dùng **Copilot** soạn tin nhắn giải thích lợi thế cạnh tranh
4. Cuối tuần → **AI Sales Coach** phân tích kỹ năng xử lý từ chối, cho điểm và gợi ý cải thiện

---

## Bước 6 — Phê duyệt & Chốt Bán hàng (Closing)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Thông báo kết quả phê duyệt cho KH | Copilot soạn Zalo/email thông báo | 🟡 Một phần | Copilot soạn được; kết quả phê duyệt đồng bộ từ core banking |
| Hướng dẫn ký kết hợp đồng | Activity + ghi chú chatter | 🟡 Một phần | Ghi nhận được; chưa có form hướng dẫn tích hợp |
| Chuyển stage → "Thắng" (Won) | Nút "Đánh dấu Thắng" (Odoo built-in) | ✅ Có | |
| NBA gợi ý "Chốt hợp đồng" khi đủ điều kiện | `nba_action_type = close_won` | ✅ Có | NBA tự động đề xuất khi tín hiệu đủ mạnh |
| Nhận diện tín hiệu sẵn sàng chốt | `ai_last_sentiment = positive` + probability cao | 🟡 Một phần | Nhận diện được; chưa có alert nổi bật riêng |

**Quy trình thực hiện trên CRM:**
1. **NBA widget** hiển thị `action_type = close_won` khi probability cao + sentiment tích cực
2. Nhấn "Bắt đầu gọi" → thông báo kết quả phê duyệt → ghi transcript
3. Tạo activity "✍️ Ký hợp đồng" với deadline cụ thể
4. Sau ký → chuyển stage "Won" → Customer 360 cập nhật

---

## Bước 7 — Giải ngân / Bàn giao Sản phẩm (Delivery)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Ghi nhận giải ngân thành công | Đồng bộ từ core banking qua `corebanking_sync` | 🟡 Một phần | Model có sẵn; cần cấu hình endpoint |
| Kích hoạt thẻ / bàn giao hợp đồng BH | Activity + ghi chú | 🟡 Một phần | Ghi nhận được; chưa tự động |

**Quy trình thực hiện trên CRM:**
1. Core banking đồng bộ trạng thái giải ngân → cập nhật lead
2. Tạo activity "🎴 Kích hoạt thẻ" hoặc "📋 Bàn giao hợp đồng BH"
3. Ghi chú chatter xác nhận bàn giao

---

## Bước 8 — Chăm sóc Sau bán hàng & Khai thác Tiếp nối (After-sales)

| Hoạt động | Tính năng CRM | Trạng thái | Ghi chú |
|-----------|---------------|-----------|---------|
| Nhắc nợ / theo dõi lịch trả nợ | Đồng bộ lịch trả nợ từ core banking | 🟡 Một phần | Cần hoàn thiện `corebanking_sync` |
| Chúc sinh nhật, lễ Tết | Activity tự động từ `partner.date_of_birth` | 🟡 Một phần | Trường có; cần cron tự tạo activity |
| Thông báo chương trình ưu đãi mới | Copilot soạn Zalo/email | 🟡 Một phần | Soạn được; chưa có mass Zalo blast |
| Daily Digest cá nhân hóa cho nhân viên | Cron 8h AM → DM qua Discuss | ✅ Có | Danh sách việc ưu tiên buổi sáng |
| NBA cảnh báo KH lâu không liên hệ | `nba_action_type = mark_cold` | ✅ Có | Cron daily tính toán lại NBA |
| Xin referral từ KH hài lòng | NBA gợi ý + Copilot soạn tin | 🟡 Một phần | NBA gợi ý được; chưa có referral tracking |
| Cross-sell tiếp theo (upsell) | AI Cross-sell engine + NBA | ✅ Có | AI gợi ý sản phẩm tiếp theo sau khi KH dùng |
| AI Sales Coach tổng kết tuần | Weekly digest coaching report | ✅ Có | Gửi qua Discuss, track KPI theo team |

**Quy trình thực hiện trên CRM:**
1. **Daily Digest 8h** nhắc nhân viên KH nào cần chăm sóc hôm nay
2. **NBA** tự động đề xuất thời điểm cross-sell tiếp theo
3. Khi KH satisfied → NBA gợi ý "Xin referral" → Copilot soạn tin nhắn
4. **AI Sales Coach** cuối tuần: phân tích kỹ năng, track cải thiện theo thời gian

---

## Tổng hợp Gap Analysis

### ✅ Có đầy đủ
- Realtime call transcription + AI Hints
- Post-call summary + sentiment detection
- Checklist hồ sơ theo sản phẩm
- CCCD / GPKD scan + OCR
- BCTC AI analysis (gợi ý câu hỏi RM)
- Customer 360
- Next Best Action (NBA)
- AI Product Recommendation (rule engine + AI scoring)
- AI Sales Coach
- Cross-sell engine
- Daily Digest cá nhân hóa
- Proposal / Term Sheet generator
- Copilot soạn tin nhắn / email

### 🟡 Có một phần — Cần bổ sung

| Gap | Việc cần làm |
|-----|-------------|
| CIC / credit score KH | Hoàn thiện `corebanking_sync` để đồng bộ CIC từ core banking |
| KH tiền gửi đến hạn | Đồng bộ lịch đến hạn từ core banking → tạo Lead/cảnh báo tự động |
| Nhắc nộ / cảnh báo NPL | Đồng bộ lịch trả nợ từ core banking |
| Ghi nhận giải ngân | Kết nối `corebanking_sync` với endpoint thực tế |
| Zalo nhắc hồ sơ thiếu tự động | Hoàn thiện Zalo OA send API |
| Chúc sinh nhật tự động | Cron tạo activity từ `partner.date_of_birth` |
| Alert "KH sẵn sàng chốt" nổi bật | NBA badge đặc biệt khi `nba_action_type = close_won` |
| Referral tracking | Thêm field `referred_by_partner_id` + báo cáo nguồn |

### ❌ Chưa có — Cần phát triển mới

| Gap | Mô tả | Độ ưu tiên |
|-----|-------|-----------|
| Mass Zalo blast theo chiến dịch | Gửi Zalo hàng loạt theo segment KH | Trung bình |
| Referral portal cho đối tác | Link riêng cho môi giới BĐS / showroom giới thiệu KH | Thấp |
