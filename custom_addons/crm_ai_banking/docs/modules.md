# Tài liệu Module — crm_ai_banking (Phase 1)

## Tổng quan

Addon `crm_ai_banking` mở rộng Odoo CRM với các tính năng AI cho ngân hàng bán lẻ. Toàn bộ code nằm trong `/custom_addons/crm_ai_banking/`, sử dụng `_inherit` — không chỉnh sửa `/odoo/addons`.

---

## Module 1: `crm.ai.config` — Cấu hình AI tập trung

**File**: `models/crm_ai_config.py`  
**View**: `views/crm_ai_config_views.xml`  
**Menu**: CRM → AI Banking → Cấu hình AI (chỉ System Admin)

### Mục đích
Lưu toàn bộ config API keys và provider settings tại một nơi. Mọi AI call trong toàn bộ module đều đọc từ đây.

### Models
| Model | Mô tả |
|-------|-------|
| `crm.ai.config` | Singleton config (lấy bằng `get_config()`) |

### Fields chính
| Nhóm | Field | Mô tả |
|------|-------|-------|
| LLM | `claude_api_key`, `claude_model_text`, `claude_model_vision` | Anthropic Claude |
| OCR | `ocr_provider` (api/local), `openrouter_api_key`, `ocr_local_endpoint` | Switch 1 field |
| STT Batch | `stt_batch_provider`, `whisper_api_key`, `whisper_local_endpoint` | Upload file sau gọi |
| STT Realtime | `stt_realtime_provider`, `deepgram_api_key`, `whisper_streaming_ws` | Live call screen |
| Zalo | `zalo_oa_access_token`, `zalo_webhook_secret` | Zalo OA API |
| Automation | `auto_process_email`, `cold_lead_threshold_days`, `large_deal_threshold` | Ngưỡng cảnh báo |

### Pattern chuyển môi trường
```
ocr_provider = 'api'   → OpenRouter + Qwen 3 VL
ocr_provider = 'local' → API nội bộ (endpoint tự deploy)
(chỉ đổi 1 field, không thay code)
```

---

## Module 2: `CrmAiService` — Service Layer

**File**: `models/crm_ai_service.py`

### Mục đích
Class thuần Python (không phải Odoo model). Tất cả AI API calls đi qua đây. Code tính năng không gọi trực tiếp Claude/OCR/Whisper — chỉ gọi methods của `CrmAiService`.

### Internal Routers
| Method | provider='api' | provider='local' |
|--------|----------------|------------------|
| `_call_ocr()` | OpenRouter + Qwen 3 VL | OCR API nội bộ |
| `_call_stt_batch()` | OpenAI Whisper API | faster-whisper HTTP |
| `_call_stt_stream()` | Deepgram WebSocket | whisper-streaming WS |

### Anonymization (bảo mật data)
`CrmAiService.anonymize(text)` mask trước khi gửi external API:
- Số CCCD 9-12 chữ số → `[ID_NUMBER]`
- MST 10-13 chữ số → `[TAX_ID]`
- Số tài khoản 13-19 chữ số → `[ACCOUNT_NO]`

### Public Methods
| Method | Input | Output | Dùng cho |
|--------|-------|--------|----------|
| `extract_card()` | image_bytes | dict (name, phone, email...) | Name card scan |
| `extract_id_card()` | image_bytes, side | dict (OCR result) | CCCD scan |
| `transcribe_audio()` | audio_bytes | str (transcript) | Batch STT |
| `summarize_call()` | transcript, context | dict (summary, action_items...) | Post-call |
| `summarize_email()` | body, subject | dict (intent, bullets...) | Email AI |
| `generate_reply()` | conversation, tone | list[dict] | Copilot |
| `detect_needs()` | message_text | dict (needs, signals) | Zalo AI |
| `get_ai_hints()` | transcript, product_type | dict (suggestions) | Realtime hints |
| `generate_daily_digest()` | name, stats... | str (message) | Daily cron |
| `get_cold_lead_reengage()` | lead_name, days... | dict (suggestion) | Cold alert |

---

## Module 3: `crm.ai.call.session` + `crm.ai.transcript.line` — Call Session

**Files**: `models/crm_ai_call_session.py`, `models/crm_ai_transcript_line.py`  
**View**: `views/crm_ai_call_session_views.xml`

### Mục đích
Lưu toàn bộ dữ liệu của một phiên gọi/meeting: từng dòng transcript realtime, AI summary sau khi kết thúc.

### Models
| Model | Mô tả |
|-------|-------|
| `crm.ai.call.session` | Phiên gọi (lead_id, status, summary, action_items) |
| `crm.ai.transcript.line` | Một câu thoại (speaker, text, timestamp, is_final) |

### Lifecycle
```
create (status=active)
  → transcript_ids nhận lines realtime
  → action_end_session() → status=ended
  → _trigger_ai_summary() → async cron
  → _run_ai_summary() → status=summarized
  → lead.log_meeting() + message_post + activity_schedule
```

### 3 kênh gọi
| `call_channel` | Cách capture | Diarization |
|---------------|-------------|-------------|
| `webrtc` | 2 stream riêng (mic + speaker) | Tự động theo stream |
| `phone_mic` | 1 stream từ mic | Deepgram diarize=true |
| `mobile` | Upload chunks từ mobile browser | Deepgram diarize=true |

---

## Module 4: WebSocket Controller + LiveCallScreen OWL

**Files**: `controllers/call_stream.py`, `static/src/js/live_call_screen.js`, `static/src/xml/ai_templates.xml`

### Mục đích
Backend endpoints phục vụ realtime call screen. Frontend OWL component capture audio, stream tới STT service, hiển thị transcript từng câu.

### REST Endpoints
| Route | Method | Mô tả |
|-------|--------|-------|
| `/crm/ai/call/start` | POST jsonrpc | Tạo session mới |
| `/crm/ai/call/end` | POST jsonrpc | Kết thúc, trigger AI summary |
| `/crm/ai/call/transcript/add` | POST jsonrpc | Thêm/update transcript line + broadcast bus |
| `/crm/ai/call/hints` | POST jsonrpc | Lấy AI hints tại thời điểm hiện tại |
| `/crm/ai/call/stt_config` | GET jsonrpc | Trả config STT cho frontend |

### OWL LiveCallScreen
- Nhận `leadId` prop, hiển thị channel selector → bắt đầu session
- Capture audio qua `getUserMedia()` → stream tới Deepgram WS hoặc local WS
- Nhận partial/final transcript → render realtime với phân biệt màu NV/KH
- AI Hints panel: opt-in, poll mỗi 30 giây
- Nút "Kết thúc" → call `/crm/ai/call/end` → thông báo AI đang tóm tắt

---

## Module 5: Email AI — `crm.lead` Override

**File**: `models/crm_lead.py`

### Mục đích
Override `message_new()` để tự động xử lý email đến bằng AI. Dùng `_inherit = 'crm.lead'` — không sửa file gốc.

### Luồng xử lý email
```
Email vào alias
  → message_new() [override]
  → tạo ir.cron async (1 minute)
  → _ai_process_incoming_email(body, subject)
  → CrmAiService.summarize_email()
  → Post internal note (bullets + intent + urgency)
  → activity_schedule() theo intent
  → Notify salesperson nếu high urgency
  → _apply_needs_tags() cập nhật tag_ids
  → _ensure_document_checklist() nếu document_request
```

### Intent → Activity mapping
| Intent | Activity | Deadline |
|--------|----------|---------|
| `pricing_inquiry` | Gửi báo giá | +1 ngày |
| `ready_to_buy` | Follow up ngay | Hôm nay |
| `complaint` | Xử lý khiếu nại | Hôm nay |
| `document_request` | Kiểm tra hồ sơ | +1 ngày |
| `follow_up` | Follow up | +2 ngày |

### Fields thêm vào `crm.lead`
| Field | Mô tả |
|-------|-------|
| `product_type` | Loại sản phẩm (vay mua nhà, thẻ, tiết kiệm...) |
| `ai_last_sentiment` | Sentiment gần nhất từ call/email |
| `ai_call_session_ids` | O2M → crm.ai.call.session |
| `ai_call_session_count` | Computed: số cuộc gọi |

---

## Module 6: Document Checklist — Hồ sơ Động

**File**: `models/crm_ai_document_checklist.py`  
**Views**: `views/crm_document_checklist_views.xml`  
**Data**: `data/product_checklist_data.xml`

### Mục đích
Template checklist hồ sơ theo loại sản phẩm. Khi nhân viên chọn `product_type` trên lead → checklist tự động tạo → nhắc nhở tự động.

### Models
| Model | Mô tả |
|-------|-------|
| `crm.document.checklist.template` | Template per product_type (vay_mua_nha, the_tin_dung...) |
| `crm.document.checklist.template.item` | Từng giấy tờ trong template |
| `crm.document.checklist` | Checklist thực tế gắn với lead |
| `crm.document.checklist.line` | Từng item với status (pending/submitted/approved/rejected) |

### Templates có sẵn (Phase 1)
| Loại SP | Số giấy tờ | Nhắc sau |
|---------|-----------|---------|
| Vay mua nhà | 8 | 2 ngày |
| Thẻ tín dụng | 4 | 3 ngày |
| Vay kinh doanh | 6 | 2 ngày |

### Auto-trigger
- `_ensure_document_checklist()` được gọi khi:
  - Email intent = `document_request`
  - `lead.product_type` thay đổi (qua `@api.onchange` hoặc write)

---

## Module 7 & 8: Cron Jobs — Alert + Daily Digest

**File**: `models/crm_lead.py` (cron methods)  
**Data**: `data/ir_cron_data.xml`

### Cron: Cold Lead Alert (daily)
```python
_cron_cold_lead_alert()
```
- Tìm leads `write_date < now - threshold_days`
- AI gợi ý cách re-engage (`get_cold_lead_reengage()`)
- Post internal note + tạo activity "Re-engage lead nguội"
- Skip nếu đã có activity nguội pending

### Cron: Large Deal Alert (daily)
```python
_cron_large_deal_alert()
```
- Tìm leads `expected_revenue >= threshold AND no manager message >= X days`
- Post alert vào team channel
- Tạo activity "Cần hỗ trợ manager" assign cho manager

### Cron: Daily Digest (daily 8:00 AM)
```python
_cron_send_daily_digest()
```
- Per salesperson: tính overdue, hot leads (≥70%), cold leads, pending checklist
- AI generate tin nhắn tiếng Việt tự nhiên
- Gửi qua `discuss.channel` DM (không qua email)

---

## Zalo & Name Card Controllers

**File**: `controllers/main.py`

| Route | Mô tả |
|-------|-------|
| `POST /crm/ai/webhook/zalo` | Nhận message từ Zalo OA, match lead, log chatter, AI intent |
| `POST /crm/ai/scan-card` | Upload ảnh name card từ mobile, tạo lead |

---

## Phase 3+4 Models (xem chi tiết: `docs/phase3_phase4_guide.md`)

| Model | File | Mô tả |
|-------|------|-------|
| `crm.account.contact` | `models/crm_account_contact.py` | B2B stakeholder map |
| `crm.ai.document` | `models/crm_ai_document.py` | Phân tích BCTC/GPKD |
| `crm.product.eligibility.rule` | `models/crm_product_recommendation.py` | Quy tắc sản phẩm |
| `crm.product.recommendation` | `models/crm_product_recommendation.py` | Gợi ý sản phẩm AI |
| `crm.ai.coaching.report` | `models/crm_ai_coaching_report.py` | Sales Coach |
| `crm.ai.generate.proposal` | `wizard/crm_ai_generate_proposal.py` | Sinh đề xuất AI |

### Phase 4 fields trên `crm.lead`

| Field prefix | Tính năng |
|-------------|----------|
| `nba_*` | Next Best Action (P4-1) |
| `product_recommendation_ids` | Product Recommendations (P4-2) |
| `account_contact_ids` | Account Map B2B (P3-1) |
| `ai_document_ids` | BCTC/GPKD documents (P3-3) |
| `customer_360_*` | Customer 360 summary (P4-4) |

### Phase 4 service methods (`CrmAiService`)

| Method | Mô tả |
|--------|-------|
| `compute_next_best_action(ctx)` | NBA — 1 hành động tốt nhất |
| `score_products(eligible, ctx)` | Xếp hạng sản phẩm |
| `analyze_call_coaching(transcript)` | Sales coach scoring |
| `generate_customer_360(data)` | Tóm tắt 360° |
| `get_crosssell_suggestions(ctx, existing)` | Cross-sell AI |
| `generate_proposal_content(base, ctx)` | Cải thiện nội dung đề xuất |
