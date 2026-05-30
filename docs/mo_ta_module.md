# Mô tả các module CRM AI Banking

> Tài liệu tham chiếu: mô tả từng model, field quan trọng, và quan hệ giữa các model.

---

## Tổng quan module `crm_ai_banking`

Module duy nhất, kế thừa và mở rộng `crm`, `mail`, `discuss`.  
**Đường dẫn**: `/custom_addons/crm_ai_banking/`

```
crm_ai_banking/
├── models/                     # Business logic
├── controllers/                # REST endpoints + WebSocket
├── wizard/                     # Transient models (popup)
├── views/                      # XML views
├── static/src/js/              # OWL components
├── data/                       # Dữ liệu mặc định + cron
├── security/                   # Access rights
└── docs/                       # Tài liệu kỹ thuật
```

---

## Nhóm 1 — Cấu hình & Service Layer

### `crm.ai.config` — Cấu hình tập trung
**File**: `models/crm_ai_config.py`

Singleton — một bản ghi duy nhất cho toàn hệ thống. Tất cả API keys, endpoints, toggles đều ở đây.

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `claude_api_key` | Char | Anthropic API key (encrypted) |
| `claude_model_text` | Char | Model Claude cho text (mặc định: claude-sonnet-4-6) |
| `claude_model_vision` | Char | Model Claude cho vision |
| `ocr_provider` | Selection | `api` (OpenRouter) / `local` |
| `openrouter_api_key` | Char | OpenRouter API key |
| `openrouter_ocr_model` | Char | Model OCR (mặc định: qwen/qwen3-vl) |
| `ocr_local_endpoint` | Char | URL OCR server nội bộ |
| `stt_batch_provider` | Selection | `api` (OpenAI Whisper) / `local` |
| `stt_realtime_provider` | Selection | `api` (Deepgram) / `local` |
| `deepgram_api_key` | Char | Deepgram API key |
| `zalo_oa_access_token` | Char | Zalo OA access token |
| `zalo_webhook_secret` | Char | Bí mật xác thực webhook Zalo |
| `auto_process_email` | Boolean | Tự xử lý email đến bằng AI |
| `enable_ai_hints` | Boolean | Bật AI hints khi gọi (opt-in) |
| `cold_lead_threshold_days` | Integer | Ngưỡng ngày không cập nhật → lead nguội |
| `large_deal_threshold` | Float | Ngưỡng deal lớn (VNĐ) |

**Method**: `get_config()` — trả về bản ghi config (singleton pattern).

---

### `CrmAiService` — Service Layer
**File**: `models/crm_ai_service.py`

Class thuần Python, không phải Odoo model. Tất cả AI calls đi qua đây.

| Method | Input | Output | Mô tả |
|--------|-------|--------|-------|
| `anonymize(text)` | str | str | Mask CCCD/MST/TK trước khi gửi API |
| `_call_ocr(bytes, doc_type)` | bytes, str | dict | Route OCR: api hoặc local |
| `_call_stt_batch(bytes, mime)` | bytes, str | str | Route STT batch |
| `_call_claude(prompt)` | str | str | Gọi Claude, trả về raw text |
| `_claude_json(prompt)` | str | dict | Gọi Claude, parse JSON |
| `extract_card(bytes)` | bytes | dict | Name card → {name, phone, email, company, title} |
| `extract_id_card(bytes)` | bytes | dict | CCCD → {name, dob, gender, address} |
| `extract_business_license(bytes)` | bytes | dict | GPKD → {company, tax_id, address, business_lines} |
| `read_financial_statement(text)` | str | dict | BCTC → {highlights, questions} |
| `summarize_call(transcript, ctx)` | str, str | dict | Tóm tắt cuộc gọi |
| `summarize_email(body, subject)` | str, str | dict | Phân tích email |
| `generate_reply(conversation, tone)` | str, str | list | 2 draft reply |
| `detect_needs(text)` | str | dict | Nhận diện nhu cầu tài chính |
| `get_cold_lead_reengage(...)` | ... | dict | Gợi ý re-engage lead nguội |
| `get_crosssell_suggestions(ctx, products)` | dict, list | dict | Gợi ý cross-sell |
| `generate_proposal_content(base, ctx, notes)` | str, str, str | str | Enhance proposal |
| `compute_next_best_action(ctx)` | dict | dict | NBA: action_type, urgency, suggested_message |
| `score_products(products, ctx)` | list, str | list | Xếp hạng sản phẩm theo mức độ phù hợp |
| `analyze_call_coaching(transcript, product)` | str, str | dict | Phân tích kỹ năng bán hàng |
| `generate_customer_360(lead_data)` | dict | dict | Tổng hợp Customer 360 |
| `generate_daily_digest(...)` | ... | str | Tóm tắt Daily Digest |
| `send_zalo_message(user_id, message)` | str, str | bool | Gửi tin nhắn Zalo OA |

---

## Nhóm 2 — Gọi điện & Transcription

### `crm.ai.call.session` — Phiên gọi điện / họp
**File**: `models/crm_ai_call_session.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one → `crm.lead` | Lead liên kết |
| `session_type` | Selection | `call` / `meeting` |
| `call_channel` | Selection | `twilio` / `webrtc` / `phone_mic` / `mobile` |
| `status` | Selection | `active` / `paused` / `ended` |
| `date_start`, `date_end` | Datetime | Thời gian bắt đầu/kết thúc |
| `duration` | Float | Thời lượng (giây) |
| `transcript_ids` | One2many → `crm.ai.transcript.line` | Nội dung hội thoại |
| `audio_attachment_id` | Many2one → `ir.attachment` | File ghi âm |
| `summary` | Html | Tóm tắt AI |
| `action_items` | Text (JSON) | Danh sách việc cần làm |
| `sentiment` | Selection | `positive`/`neutral`/`negative`/`objection` |
| `detected_needs` | Many2many → `crm.tag` | Nhu cầu nhận diện |
| `coaching_report_ids` | One2many → `crm.ai.coaching.report` | Báo cáo Sales Coach |

### `crm.ai.transcript.line` — Dòng transcript
**File**: `models/crm_ai_transcript_line.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `session_id` | Many2one | Phiên gọi |
| `sequence` | Integer | Thứ tự |
| `speaker` | Selection | `agent` / `customer` / `unknown` |
| `text` | Text | Nội dung |
| `timestamp` | Float | Giây từ đầu cuộc gọi |
| `is_final` | Boolean | False = partial (đang nói), True = confirmed |

---

## Nhóm 3 — Tài liệu AI

### `crm.ai.document` — Phân tích tài liệu BCTC/GPKD
**File**: `models/crm_ai_document.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one → `crm.lead` | Lead liên kết |
| `document_type` | Selection | `bctc`/`gpkd`/`bank_statement`/`contract`/`other` |
| `attachment_id` | Many2one → `ir.attachment` | File đính kèm |
| `ocr_raw_text` | Text | Văn bản OCR thô (tối đa 10.000 ký tự) |
| `ai_highlights_json` | Text (JSON) | Điểm cần chú ý: `["...", "..."]` |
| `ai_questions_json` | Text (JSON) | Câu hỏi gợi ý cho RM |
| `ai_analysis_html` | Html (computed) | HTML render kết quả |
| `processing_status` | Selection | `draft`/`processing`/`done`/`error` |
| `year` | Char | Năm tài chính |
| `name` | Char (computed) | "{loại} — {năm} — {lead}" |

**Methods**:
- `action_analyze()` — kích hoạt phân tích async
- `_do_analyze()` — OCR → anonymize → Claude → write fields

---

## Nhóm 4 — Checklist Hồ sơ

### `crm.document.checklist` — Checklist hồ sơ theo lead
**File**: `models/crm_ai_document_checklist.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one → `crm.lead` | Lead liên kết |
| `template_id` | Many2one | Template theo loại sản phẩm |
| `line_ids` | One2many | Từng item hồ sơ |
| `completion_rate` | Float (computed) | % items đã approved |
| `pending_count` | Integer (computed) | Số item chưa nộp |

### `crm.document.checklist.line`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `item_id` | Many2one | Loại giấy tờ |
| `status` | Selection | `pending`/`submitted`/`approved`/`rejected` |
| `attachment_id` | Many2one → `ir.attachment` | File đã nộp |
| `notes` | Text | Ghi chú |

---

## Nhóm 5 — Phase 3: B2B

### `crm.account.contact` — Stakeholder Map B2B
**File**: `models/crm_account_contact.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one → `crm.lead` | Lead doanh nghiệp |
| `partner_id` | Many2one → `res.partner` | Người liên hệ |
| `name` | Char | Tên đầy đủ |
| `title` | Many2one → `res.partner.title` | Danh xưng |
| `role` | Selection | `ceo`/`cfo`/`coo`/`hr_director`/`chief_accountant`/v.v. |
| `influence_level` | Selection | `decision_maker`/`influencer`/`gatekeeper`/`user` |
| `relationship_strength` | Integer | 1–5 (mức độ quan hệ) |
| `last_contact_date` | Date | Ngày liên hệ gần nhất |
| `notes` | Text | Ghi chú chiến lược |

---

## Nhóm 6 — Phase 4: AI Intelligence

### `crm.product.eligibility.rule` — Quy tắc sản phẩm
**File**: `models/crm_product_recommendation.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `product_code` | Char | Mã sản phẩm |
| `product_name` | Char | Tên sản phẩm |
| `product_category` | Selection | `credit`/`card`/`savings`/`insurance`/v.v. |
| `min_income_million` | Float | Thu nhập tối thiểu (triệu/tháng) |
| `min_age` | Integer | Tuổi tối thiểu |
| `max_age` | Integer | Tuổi tối đa |
| `description` | Text | Mô tả & điểm bán hàng |
| `cross_sell_codes` | Char | Mã sản phẩm cross-sell (cách nhau dấu phẩy) |

**Method**: `check_eligibility(partner)` — kiểm tra KH đủ điều kiện.

### `crm.product.recommendation` — Kết quả gợi ý sản phẩm

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one → `crm.lead` | Lead liên kết |
| `computed_date` | Datetime | Thời điểm tính |
| `recommendations_json` | Text (JSON) | Top 5 sản phẩm với match_score, reasons, approach |
| `recommendations_html` | Html (computed) | HTML render top 3 |
| `top_product_name` | Char | Sản phẩm phù hợp nhất |
| `top_match_score` | Float | Điểm phù hợp (%) |

### `crm.ai.coaching.report` — Báo cáo Sales Coach
**File**: `models/crm_ai_coaching_report.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `call_session_id` | Many2one → `crm.ai.call.session` | Phiên gọi |
| `user_id` | Many2one → `res.users` | Nhân viên được coach |
| `score_opening` | Float (0–10) | Điểm chào hỏi |
| `score_needs_discovery` | Float (0–10) | Điểm khám phá nhu cầu |
| `score_product_fit` | Float (0–10) | Điểm kết nối sản phẩm |
| `score_objection` | Float (0–10) | Điểm xử lý từ chối |
| `score_closing` | Float (0–10) | Điểm kỹ năng chốt |
| `score_overall` | Float (computed) | Trung bình 5 điểm |
| `strengths_json` | Text (JSON) | Điểm mạnh |
| `improvements_json` | Text (JSON) | Cần cải thiện |
| `missed_opportunities_json` | Text (JSON) | Cơ hội bỏ lỡ |
| `key_moments_json` | Text (JSON) | `[{timestamp, speaker, text, feedback, type}]` |
| `coaching_html` | Html (computed) | HTML render báo cáo |
| `visible_to_user` | Boolean | Manager ẩn/hiện cho nhân viên |

---

## Nhóm 7 — Banking 360 (Core Banking Data)

### `crm.banking.customer.profile` — Hồ sơ tài chính chung
**File**: `models/banking_profile.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `partner_id` | Many2one → `res.partner` | Khách hàng |
| `total_deposit_balance` | Monetary | Tổng tiền gửi |
| `total_loan_balance` | Monetary | Tổng dư nợ |
| `total_aum` | Monetary | AUM |
| `toi_mtd`/`toi_ytd`/`toi_12m` | Monetary | Thu nhập từ KH (MTD/YTD/12M) |
| `risk_score` | Float | Điểm rủi ro |
| `risk_grade` | Char | Hạng rủi ro (A/B/C...) |
| `kyc_status` | Char | Trạng thái KYC |
| `preferred_channel` | Char | Kênh ưa thích |

### `crm.banking.individual.profile` — Hồ sơ cá nhân

| Field quan trọng | Mô tả |
|-----------------|-------|
| `monthly_income` | Thu nhập tháng |
| `verified_income` | Thu nhập đã xác minh |
| `occupation`, `employer_name` | Nghề nghiệp, nơi làm |
| `marital_status`, `dependent_count` | Tình trạng hôn nhân, số người phụ thuộc |

### `crm.banking.business.profile` — Hồ sơ doanh nghiệp

| Field quan trọng | Mô tả |
|-----------------|-------|
| `annual_revenue`, `net_profit` | Doanh thu, lợi nhuận |
| `debt_group` | Nhóm nợ (1–5) |
| `approved_limit`, `used_limit` | Hạn mức cấp/đã dùng |
| `payroll_volume`, `lc_volume`, `fx_volume` | Khối lượng giao dịch |

### `crm.banking.product.holding` — Sản phẩm đang sử dụng

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `partner_id` | Many2one | Khách hàng |
| `product_code`, `product_name` | Char | Mã/Tên sản phẩm |
| `product_category` | Selection | `deposit`/`loan`/`card`/`insurance`/v.v. |
| `current_balance` | Monetary | Số dư hiện tại |
| `outstanding_balance` | Monetary | Dư nợ (với khoản vay) |
| `maturity_date` | Date | Ngày đáo hạn (tiền gửi) |
| `masked_account_number` | Char | Số TK masked (***xxxx) |
| `status` | Selection | `active`/`inactive`/`closed` |

---

## Nhóm 8 — Đồng bộ Core Banking

### `crm.corebanking.customer.batch` — Batch đồng bộ
**File**: `models/corebanking_sync.py`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `sync_type` | Selection | `init`/`daily`/`manual` |
| `state` | Selection | `draft`/`processing`/`done`/`partial` |
| `line_ids` | One2many → staging | Các dòng dữ liệu |
| `total_count` | Integer (computed) | Tổng số dòng |
| `created_count` | Integer (computed) | Số contact mới tạo |
| `error_count` | Integer (computed) | Số lỗi |

### `crm.corebanking.customer.staging` — Dữ liệu staging

Chứa dữ liệu thô từ core banking trước khi xử lý vào `res.partner` và các profile models.

**3 loại record** (`record_type`):
- `customer_master` → tạo/cập nhật `res.partner`
- `customer_profile` → upsert `crm.banking.customer.profile` + individual/business profile
- `product_holding` → upsert `crm.banking.product.holding`

---

## Nhóm 9 — Extensions

### `res.partner` (extended)
**File**: `models/res_partner.py`

Trường thêm vào partner:

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `bank_cif` | Char | Mã CIF từ core banking |
| `customer_type` | Selection | `individual`/`business` |
| `customer_segment_id` | Many2one → `crm.customer.segment` | Phân khúc KH |
| `cccd_number` | Char | Số CCCD (encrypted, hạn chế access) |
| `date_of_birth` | Date | Ngày sinh (dùng cho birthday cron) |
| `gender` | Selection | `male`/`female`/`other` |
| `zalo_user_id` | Char | Zalo User ID |
| `banking_profile_ids` | One2many | Hồ sơ Banking 360 |
| `banking_product_holding_ids` | One2many | Sản phẩm đang sử dụng |
| `corebanking_last_sync_date` | Datetime | Lần sync cuối từ core banking |

### `crm.lead` (extended)
**File**: `models/crm_lead.py`

Tất cả fields xem **[Tài liệu trường Lead](../docs/lead_vs_opportunity_guide.md)**.

Fields mới nhất (2026-05-30):
| Field | Kiểu | Mô tả |
|-------|------|-------|
| `referred_by_partner_id` | Many2one → `res.partner` | Người giới thiệu |
| `referral_source` | Selection | Kênh giới thiệu (BĐS/Showroom/KH hiện hữu/v.v.) |

---

## Nhóm 10 — Wizard (Transient Models)

### `crm.ai.scan.document` — Wizard scan tài liệu

| scan_type | Xử lý | Kết quả |
|-----------|-------|---------|
| `name_card` | Claude Vision | Fill partner: tên, phone, email, company |
| `cccd` | OCR + anonymize | Fill partner: tên, ngày sinh, địa chỉ, giới tính |
| `gpkd` | OCR + anonymize | Fill partner: tên công ty, ngành nghề |

### `crm.ai.generate.proposal` — Wizard sinh Proposal

Templates có sẵn: `vay_mua_nha`, `vay_kinh_doanh`, `the_tin_dung`

State machine: `input` → (generate) → `result` → (attach) → đóng wizard

### `crm.ai.zalo.compose` — Wizard soạn tin Zalo

AI tạo 2 draft → user chọn → chỉnh → gửi.

---

## Nhóm 11 — Phân khúc KH

### `crm.customer.segment` — Phân khúc khách hàng
**File**: `models/crm_customer_segment.py`

| Field | Mô tả |
|-------|-------|
| `code` | Mã phân khúc từ core banking |
| `name` | Tên phân khúc (Platinum / Gold / Silver / Mass) |
| `customer_type` | `individual` / `business` |
| `description` | Mô tả điều kiện phân khúc |

---

## Quan hệ giữa các Model (ERD tóm tắt)

```
res.partner
  ├── crm.banking.customer.profile (1-1)
  ├── crm.banking.individual.profile (1-1)
  ├── crm.banking.business.profile (1-1)
  └── crm.banking.product.holding (1-N)

crm.lead (extends crm.lead)
  ├── crm.ai.call.session (1-N)
  │     ├── crm.ai.transcript.line (1-N)
  │     └── crm.ai.coaching.report (1-N)
  ├── crm.document.checklist (1-N)
  │     └── crm.document.checklist.line (1-N)
  ├── crm.ai.document (1-N) [BCTC/GPKD]
  ├── crm.account.contact (1-N) [B2B stakeholders]
  ├── crm.product.recommendation (1-N)
  └── partner_id → res.partner
                      └── crm.banking.product.holding → dùng trong cross-sell, NBA

crm.corebanking.customer.batch
  └── crm.corebanking.customer.staging (1-N)
        → processes into → res.partner + banking profiles

crm.product.eligibility.rule  (admin-configured)
  → used by → crm.lead._ai_run_product_recommendations()
```

---

## Cron Jobs

| Cron | Model | Method | Lịch | Mô tả |
|------|-------|--------|------|-------|
| Daily Digest | `crm.lead` | `_cron_send_daily_digest` | 8:00 AM daily | Digest cá nhân hóa qua Discuss |
| Cold Lead Alert | `crm.lead` | `_cron_cold_lead_alert` | 9:00 AM daily | Cảnh báo lead nguội |
| Large Deal Alert | `crm.lead` | `_cron_large_deal_alert` | 9:30 AM daily | Deal lớn không có manager |
| NBA Refresh | `crm.lead` | `_cron_refresh_nba` | 3:00 AM daily | Tính lại Next Best Action |
| Birthday Activities | `crm.lead` | `_cron_birthday_activities` | 7:00 AM daily | Tạo activity chúc sinh nhật |
| Deposit Maturity | `crm.lead` | `_cron_deposit_maturity_alert` | 7:30 AM daily | Cảnh báo tiền gửi đến hạn |
| Loan Repayment | `crm.lead` | `_cron_loan_repayment_alert` | Thứ Hai weekly | Nhắc theo dõi khoản vay |
| Core Banking Sync | `crm.corebanking.customer.batch` | `_cron_process_daily_staging` | 18:00 daily | Xử lý batch staging |
