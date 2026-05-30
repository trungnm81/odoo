# P1-0: Cấu hình & Service Layer

> Module nền tảng — mọi tính năng khác đều phụ thuộc vào đây.

---

## 1. `crm.ai.config` — Cấu hình tập trung

**File:** `models/crm_ai_config.py`

Singleton model (chỉ có 1 bản ghi active). Mọi provider key và toggle đều ở đây — thay provider chỉ đổi 1 field, không sửa code.

### Các nhóm cấu hình

#### LLM (Claude)

| Field | Mô tả |
|-------|-------|
| `llm_provider` | `openrouter` hoặc `anthropic` |
| `openrouter_api_key` | Dùng chung cho cả LLM lẫn OCR khi provider=openrouter |
| `openrouter_llm_model_text` | Mặc định: `anthropic/claude-sonnet-4-6` |
| `openrouter_llm_model_vision` | Mặc định: `anthropic/claude-opus-4-8` |
| `claude_api_key` | API key Anthropic trực tiếp (chỉ dùng khi provider=anthropic) |
| `claude_model_text` | Computed — code luôn đọc field này, không đọc raw fields |
| `claude_model_vision` | Computed — tương tự trên |

#### OCR

| Field | Mô tả |
|-------|-------|
| `ocr_provider` | `openrouter` (Qwen3 VL) hoặc `local` |
| `openrouter_ocr_model` | Mặc định: `qwen/qwen3-vl` |
| `ocr_local_endpoint` | URL server OCR nội bộ |
| `ocr_local_api_key` | Bearer token cho local OCR |

#### STT Batch (ghi âm upload sau cuộc gọi)

| Field | Mô tả |
|-------|-------|
| `stt_batch_provider` | `api` (OpenAI Whisper) hoặc `local` (faster-whisper) |
| `whisper_api_key` | OpenAI API key |
| `whisper_api_endpoint` | Mặc định: `https://api.openai.com/v1/audio/transcriptions` |
| `whisper_api_model` | Mặc định: `whisper-1` |
| `whisper_local_endpoint` | URL server faster-whisper nội bộ |
| `whisper_local_model` | `large-v3` (GPU) hoặc `medium` (CPU) |

#### STT Realtime (streaming trong cuộc gọi)

| Field | Mô tả |
|-------|-------|
| `stt_realtime_provider` | `api` (Deepgram) hoặc `local` (whisper-streaming) |
| `deepgram_api_key` | Deepgram API key |
| `deepgram_model` | Mặc định: `nova-3` |
| `whisper_streaming_ws` | WebSocket URL server nội bộ |

#### Twilio Voice

| Field | Mô tả |
|-------|-------|
| `twilio_account_sid` | Account SID |
| `twilio_auth_token` | Auth Token |
| `twilio_phone_number` | Số từ Twilio (E.164, VD: `+84...`) |
| `twilio_public_url` | URL ngrok/domain để Twilio callback — cần cho ghi âm và AI summary |
| `twilio_agent_phone` | Số điện thoại nhân viên (nếu muốn conference call) |

#### Automation Toggles

| Field | Mặc định | Mô tả |
|-------|---------|-------|
| `auto_process_email` | `True` | Tự động phân tích email đến |
| `auto_process_attachment` | `False` | Tự động OCR file đính kèm (Phase 2) |
| `cold_lead_threshold_days` | 10 | Số ngày không cập nhật để coi là lead nguội |
| `large_deal_threshold` | 5 tỷ | Ngưỡng deal lớn cần alert manager |
| `large_deal_no_manager_days` | 7 | Ngày không có tương tác của manager thì alert |
| `enable_ai_hints` | `False` | Opt-in realtime hints trong cuộc gọi |
| `ai_hints_interval_seconds` | 30 | Tần suất fetch AI hints |
| `daily_digest_time` | 8.0 | Giờ gửi daily digest (giờ trong ngày) |

### Test buttons

Mỗi provider có nút test riêng trên form config:

| Button | Kiểm tra |
|--------|---------|
| `action_test_claude` | Ping LLM (OpenRouter hoặc Anthropic) |
| `action_test_ocr` | Ping OCR endpoint |
| `action_test_twilio` | GET Twilio account info |
| `action_test_stt_batch` | Upload 1 giây silence WAV → kiểm tra endpoint phản hồi |
| `action_test_stt_realtime` | Kiểm tra Deepgram API key hoặc local health endpoint |

---

## 2. `CrmAiService` — Service Layer

**File:** `models/crm_ai_service.py`

Class Python thuần (không phải Odoo model), instantiate mỗi request:

```python
service = CrmAiService(self.env)
```

Đóng vai trò **router**: mọi AI call đều đi qua đây, không call trực tiếp từ models hay controllers.

### Internal routers (không gọi trực tiếp từ bên ngoài)

```
_claude(prompt)           → OpenRouter hoặc Anthropic tuỳ llm_provider
_claude_json(prompt)      → _claude() + parse JSON (xử lý cả markdown code block)
_call_ocr(image, type)    → OpenRouter Qwen3 VL hoặc local OCR server
_call_stt_batch(audio)    → OpenAI Whisper API hoặc faster-whisper local
```

### Anonymization

`anonymize(text)` — bắt buộc gọi trước khi gửi bất kỳ dữ liệu nhạy cảm ra external API:

| Pattern | Thay bằng |
|---------|----------|
| Số CCCD (9-12 chữ số) | `[ID_NUMBER]` |
| Mã số thuế (10 hoặc 13 chữ số) | `[TAX_ID]` |
| Số tài khoản ngân hàng (13-19 chữ số) | `[ACCOUNT_NO]` |

### Public methods

| Method | Input | Output | Dùng ở |
|--------|-------|--------|--------|
| `summarize_email(body, subject)` | Nội dung email | `{summary_bullets, intent, urgency, detected_needs, suggested_action}` | `crm_lead.message_new()` |
| `summarize_call(transcript, lead_context)` | Transcript text | `{summary, action_items, sentiment, detected_needs, next_step}` | `crm_ai_call_session._run_ai_summary()` |
| `get_ai_hints(transcript, product_type)` | Transcript hiện tại | `{detected_needs, missing_questions, suggested_question, alert}` | Controller `/crm/ai/call/hints` |
| `generate_reply(conversation, tone)` | 5 messages gần nhất | `[{tone, text}, ...]` 2 draft | P2-5 Copilot (Phase 2) |
| `detect_needs(message_text)` | Tin nhắn khách | `{needs, confidence, signals}` | Email/Zalo processing |
| `generate_daily_digest(...)` | Stats per user | Text tiếng Việt | Cron daily digest |
| `get_cold_lead_reengage(...)` | Lead info + history | `{reason_cold, suggestion, message}` | Cron cold lead alert |
| `read_financial_statement(ocr_text)` | Text BCTC đã anonymize | `{highlights, questions}` | Phase 3 |
| `extract_card(image_bytes)` | Ảnh name card | `{full_name, title, company, phone, email}` | Phase 2 |
| `extract_id_card(image_bytes)` | Ảnh CCCD | `{full_name, date_of_birth, id_number, ...}` | Phase 2 |
| `transcribe_audio(audio_bytes)` | File audio | Text transcript | Upload batch STT |

### Luồng xử lý LLM

```
Code gọi service.xxx()
        │
        ▼
_claude_json(prompt)
        │
        ▼
_claude(prompt)
        │
        ├─ llm_provider = 'openrouter' → POST openrouter.ai/api/v1/chat/completions
        └─ llm_provider = 'anthropic'  → POST api.anthropic.com/v1/messages
        │
        ▼
Parse JSON (xử lý cả ```json ... ``` wrapper)
        │
        ▼
Trả về dict
```

### Lưu ý kỹ thuật: `_safe_format()`

Thay vì dùng `str.format(**kwargs)` thông thường, service dùng `_safe_format()` để tránh `KeyError` khi user content có ký tự `{` hoặc `}`:

```python
# Thay thế {key} bằng value, đồng thời escape { } trong value
safe_val = str(val).replace('{', '(').replace('}', ')')
template = template.replace('{' + key + '}', safe_val)
```

---

## 3. Data Privacy — Nguyên tắc bảo mật

```
DỮ LIỆU NHẠY CẢM              DỮ LIỆU THƯỜNG
CCCD, MST, số tài khoản        Tên, email, hội thoại
        │                              │
        ▼                              ▼
   _call_ocr()                   _claude() trực tiếp
   (OCR → extract)
        │
        ▼
   anonymize() ← BẮT BUỘC
        │
        ▼
   Không bao giờ gửi số thực ra external API
```

**Quy tắc cứng:** `extract_id_card()` và `extract_business_license()` dùng `_call_ocr()` (có thể local), KHÔNG gửi ảnh gốc qua Claude. Chỉ gửi text đã anonymize nếu cần phân tích thêm.
