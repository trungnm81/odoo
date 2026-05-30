# P1-1: Realtime Call & Meeting Screen

> Màn hình gọi AI — ghi transcript realtime + AI hints + tổng hợp sau cuộc gọi.

---

## Tổng quan kiến trúc

```
Nhân viên bấm "🎤 Gọi AI" trên Lead
        │
        ▼
ir.actions.client → mở OWL LiveCallScreen (dialog mới)
        │
        ▼
Chọn kênh gọi:
  ├─ 📲 Twilio  → nhập số → Twilio gọi ra SĐT khách
  ├─ 🖥️ Softphone/WebRTC → micro của máy tính
  ├─ 📞 Điện thoại thường → để gần mic máy tính
  └─ 📱 Zalo/Mobile → upload từ điện thoại

        │ (sau khi chọn kênh)
        ▼
Tạo session (POST /crm/ai/call/start)
        │
        ▼
Bật mic → thu âm → STT → transcript realtime
        │
        ▼ (sau khi kết thúc)
AI Summary async → post Chatter của Lead
```

---

## 1. Models

### `crm.ai.call.session`

**File:** `models/crm_ai_call_session.py`

Lưu toàn bộ thông tin mỗi phiên gọi.

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lead_id` | Many2one | Lead/Opportunity liên quan |
| `session_type` | Selection | `call` hoặc `meeting` |
| `call_channel` | Selection | `twilio` / `webrtc` / `phone_mic` / `mobile` |
| `status` | Selection | `active` → `paused` → `ended` → `summarized` |
| `user_id` | Many2one | Nhân viên thực hiện |
| `date_start`, `date_end` | Datetime | Thời gian bắt đầu/kết thúc |
| `duration` | Float | Thời lượng (phút) — computed |
| `transcript_ids` | One2many | Các dòng transcript |
| `full_transcript` | Text | Ghép tất cả dòng final — computed |
| `summary` | Html | Tóm tắt AI |
| `action_items_json` | Text | JSON array việc cần làm |
| `sentiment` | Selection | positive / neutral / negative / objection |
| `detected_needs_json` | Text | JSON array nhu cầu nhận diện |
| `audio_attachment_id` | Many2one | File ghi âm |

### `crm.ai.transcript.line`

**File:** `models/crm_ai_transcript_line.py`

Mỗi dòng transcript của cuộc gọi.

| Field | Mô tả |
|-------|-------|
| `session_id` | Session cha |
| `sequence` | Thứ tự (10, 20, 30...) |
| `speaker` | `agent` (NV) / `customer` (KH) / `unknown` |
| `text` | Nội dung |
| `timestamp` | Giây tính từ đầu cuộc gọi |
| `is_final` | `False` = partial (đang nói), `True` = đã xác nhận |

`create_or_update_partial()`: nếu sequence đã tồn tại → cập nhật (partial thành final), chưa có → tạo mới.

---

## 2. OWL Component: `LiveCallScreen`

**File:** `static/src/js/live_call_screen.js`

### UI Steps

```
channel_select → [phone_input] → ready → recording → paused → processing → done
```

| Step | Hiển thị |
|------|---------|
| `channel_select` | 4 nút chọn kênh gọi |
| `phone_input` | Nhập SĐT (chỉ kênh Twilio) + nút "Bắt đầu gọi" |
| `ready` | Thông tin session + nút "🎙️ Bật mic & Transcript" |
| `recording` | Timer + transcript realtime + AI hints |
| `paused` | Tạm dừng |
| `processing` | Upload audio → đang xử lý STT |
| `done` | Hiện tóm tắt + action items |

### Hai chế độ STT

| Chế độ | Cách hoạt động | Khi nào dùng |
|--------|---------------|-------------|
| `record` | Ghi âm toàn bộ → upload sau khi kết thúc → Whisper batch STT | Mặc định nếu không config Deepgram |
| `realtime` | Stream audio chunks 250ms → Deepgram/whisper-streaming WebSocket → transcript ngay | Khi đã cấu hình Deepgram API key hoặc local server |

Chế độ được chọn tự động khi mount: nếu `stt_config.api_key` có giá trị → `realtime`, không thì `record`.

### Flow Twilio (kênh Twilio)

```
selectChannel('twilio')
        │ state.step = 'phone_input'
        ▼
User nhập SĐT → bấm "Bắt đầu gọi"
        │
        ▼
confirmTwilioCall()
  ├─ 1. _createSession() → POST /crm/ai/call/start  (session_id)
  ├─ 2. POST /crm/ai/twilio/call (to_number, session_id) → call_sid
  └─ 3. state.step = 'ready'  ← QUAN TRỌNG: không auto-start mic
                                  (browser mất gesture context sau nhiều await)
        │
        ▼
User bấm "🎙️ Bật mic & Transcript"  ← gesture trực tiếp
        │
        ▼
startRecording()  ← getUserMedia() chạy được vì đây là gesture trực tiếp
```

**Lý do không auto-start mic:** Browser yêu cầu `getUserMedia()` phải được gọi trong vòng xử lý sự kiện người dùng trực tiếp (user gesture). Sau chuỗi `await RPC → await RPC`, gesture context đã mất → `getUserMedia()` bị block.

### Flow kết thúc cuộc gọi

```
Bấm "⏹ Kết thúc"
        │
        ├─ [Twilio] endTwilioCall() → POST /crm/ai/twilio/hangup (call_sid)
        │
        ▼
endRecording()
  ├─ [record mode] → upload audio → POST /crm/ai/call/upload_audio
  └─ [realtime mode] → đóng WebSocket → POST /crm/ai/call/end
        │
        ▼
state.step = 'done' → hiện tóm tắt khi AI xử lý xong
```

### AI Hints

```
hintsEnabled = true (toggle trong UI)
        │
        ▼
Mỗi 30 giây (configurable)
        │
        ▼
POST /crm/ai/call/hints {session_id, product_type}
        │
        ▼
Server lấy transcript → Claude → {missing_questions, suggested_question, alert}
        │
        ▼
Hiển thị trong panel "🤖 AI HINTS"
```

---

## 3. Controllers

**File:** `controllers/call_stream.py`

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `POST /crm/ai/call/start` | JSON-RPC | Tạo session mới, trả về `session_id` |
| `POST /crm/ai/call/end` | JSON-RPC | Kết thúc session, trigger AI summary async |
| `POST /crm/ai/call/transcript/add` | JSON-RPC | Thêm/cập nhật 1 dòng transcript + broadcast Odoo bus |
| `POST /crm/ai/call/hints` | JSON-RPC | Lấy AI hints từ transcript hiện tại |
| `POST /crm/ai/call/upload_audio` | HTTP multipart | Upload file audio → batch STT → lưu transcript → trigger summary |
| `GET /crm/ai/call/stt_config` | JSON-RPC | Trả về config STT cho frontend (provider, key, ws_url) |
| `GET /crm/ai/call/session/<id>` | JSON-RPC | Lấy toàn bộ thông tin session kèm transcript |

**File:** `controllers/twilio_voice.py`

| Endpoint | Method | Auth | Mô tả |
|----------|--------|------|-------|
| `POST /crm/ai/twilio/call` | JSON-RPC | user | Gọi Twilio REST API để khởi tạo cuộc gọi ra |
| `POST /crm/ai/twilio/hangup` | JSON-RPC | user | Cúp máy — PATCH Twilio call với Status=completed |
| `POST /crm/ai/twilio/voice` | HTTP | public | TwiML: Twilio gọi để nhận kịch bản (Dial/Conference) |
| `POST /crm/ai/twilio/status` | HTTP | public | Twilio callback khi trạng thái thay đổi → auto-end session |
| `POST /crm/ai/twilio/recording` | HTTP | public | Twilio callback khi ghi âm xong → download → batch STT |

---

## 4. Post-call AI Summary Flow

```
session.action_end_session()
        │
        ▼
_trigger_ai_summary()
  └─ Spawn background thread (daemon=True)
        │ sleep(2)  ← chờ transaction chính commit
        ▼
_run_ai_summary()  [trong transaction mới]
        │
        ├─ 1. Lấy full_transcript từ DB
        ├─ 2. CrmAiService.summarize_call(transcript, lead_context)
        │       → Claude → {summary, action_items, sentiment, detected_needs, next_step}
        ├─ 3. Ghi vào session: summary, action_items_json, sentiment, ...
        ├─ 4. lead.log_meeting() — log vào lịch sử
        ├─ 5. lead.message_post() — post AI tóm tắt vào Chatter (internal note)
        ├─ 6. lead.activity_schedule() — tạo activity bước tiếp theo
        └─ 7. _update_lead_needs_tags() — update tags trên Lead
```

**Xử lý khi không có transcript:**
Nếu session kết thúc không có dòng transcript nào (chưa cấu hình STT), Claude vẫn tóm tắt dựa trên context lead:
```
[Không có transcript — cuộc gọi X phút với Lead: ..., Stage: ..., Product: ...]
```

---

## 5. Phone Number Normalization (Twilio)

`_normalize_phone()` trong `TwilioVoiceController`:

| Input | Output |
|-------|--------|
| `0983511981` | `+84983511981` |
| `+840983511981` | `+84983511981` |
| `+84983511981` | `+84983511981` (giữ nguyên) |
| `983511981` (không có 0, không có +) | `+983511981` |

---

## 6. Lưu ý vận hành

### Twilio trial account
- Chỉ gọi được số đã **verified** trong Twilio Console → Verified Caller IDs
- Lỗi `21219`: số chưa verified → vào console.twilio.com để verify hoặc upgrade account

### Twilio public URL (ngrok)
```bash
ngrok http 8069
# Copy HTTPS URL → AI Config → Twilio Voice → Public URL
# VD: https://abc123.ngrok.io
```
Nếu không cấu hình public URL: Twilio sẽ dùng demo TwiML (chỉ phát nhạc) — ghi âm và AI summary sẽ **không** hoạt động.

### Deepgram (STT Realtime)
- Cấu hình API key → AI Config → STT Realtime → Deepgram API Key
- Test bằng nút "Test STT Realtime" trên form config
- Model `nova-3` hỗ trợ tiếng Việt tốt, latency < 500ms
