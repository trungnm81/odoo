# Luồng xử lý Phase 1 — crm_ai_banking

## Tổng quan kiến trúc

```
INPUT                   AI LAYER                    ODOO CRM OUTPUT
─────                   ────────                    ───────────────
Email đến      ─→  CrmAiService.summarize_email() ─→  internal note + activity
Voice/Meeting  ─→  STT (batch/realtime) + Claude  ─→  call_session + log_meeting
Zalo message   ─→  CrmAiService.detect_needs()   ─→  chatter + tags
Name card      ─→  Claude Vision                 ─→  crm.lead (tạo mới)
Cron daily     ─→  CrmAiService + rules           ─→  alerts + digest DM
```

---

## Luồng 1: Realtime Call / Meeting

```
Nhân viên mở form lead
  → Click "🎤 Gọi AI"
  → Chọn kênh (Softphone / Điện thoại + Mic / Mobile)
  → POST /crm/ai/call/start → tạo crm.ai.call.session (status=active)

[Trong khi gọi]
  Browser getUserMedia() → capture audio stream
    ↓ chunks 250ms
  Kênh Deepgram (api): wss://api.deepgram.com/v1/listen?language=vi
  Kênh Local:          ws://whisper-server:PORT/stream
    ↓ partial + final transcript + speaker
  POST /crm/ai/call/transcript/add
    → crm.ai.transcript.line.create_or_update_partial()
    → bus.sendone('crm_ai_call_{id}', 'transcript_update', {...})
    → OWL LiveCallScreen cập nhật realtime

  [AI Hints, nếu opt-in, mỗi 30s]
    POST /crm/ai/call/hints
    → CrmAiService.get_ai_hints(transcript, product_type)
    → Claude → {missing_questions, suggested_question, alert}
    → Hiển thị trong panel hints

[Kết thúc]
  Nhân viên click "⏹ Kết thúc & Tóm tắt"
  → POST /crm/ai/call/end
  → session.action_end_session() → status=ended
  → _trigger_ai_summary() → ir.cron one-time (async)

[Async — trong ~1 phút]
  _run_ai_summary():
    → CrmAiService.summarize_call(full_transcript, lead_context)
    → Claude → {summary, action_items, sentiment, detected_needs, next_step}
    → session.write(summary, action_items_json, sentiment, status=summarized)
    → lead.log_meeting(subject, date, duration)
    → lead.message_post(body=summary_html, subtype=mt_note)
    → lead.activity_schedule(next_activity_type)
    → _update_lead_needs_tags(detected_needs) → lead.tag_ids
```

---

## Luồng 2: Email AI

```
Email đến (SMTP → Odoo fetchmail / alias)
  → crm.lead.message_new(msg_dict) [_inherit override]
  → super().message_new() → tạo lead
  → config.auto_process_email? YES:
    → ir.cron.create (async, 1 minute)
    → _ai_process_incoming_email(body, subject)

[Async]
  CrmAiService.summarize_email(body, subject)
  → Claude → {summary_bullets, intent, urgency, detected_needs, suggested_action}

  → message_post(body=note_html, subtype=mt_note)
      Nội dung note:
      🤖 AI Tóm tắt email:
      • [bullet 1]
      • [bullet 2]
      Intent: pricing_inquiry | Urgency: medium
      Gợi ý: Gửi báo giá trong ngày

  → activity_schedule(type=email, summary=activity_label, deadline=today+N)
      pricing_inquiry  → "Gửi báo giá"          +1 ngày
      ready_to_buy    → "Follow up ngay"         hôm nay
      complaint       → "Xử lý khiếu nại"        hôm nay
      document_request→ "Kiểm tra hồ sơ"         +1 ngày

  → urgency=high? → bus notify salesperson realtime

  → _apply_needs_tags(detected_needs)
      'loan' → tag 'Vay vốn'
      'credit_card' → tag 'Thẻ tín dụng'
      ...

  → intent=document_request AND lead.product_type?
      → _ensure_document_checklist()
      → crm.document.checklist.create_from_template(lead_id, product_type)
```

---

## Luồng 3: Document Checklist

```
Trigger (1 trong 3 cách):
  A. Nhân viên chọn product_type trên form lead
  B. Email AI detect intent=document_request
  C. Nhân viên tạo thủ công

  → lead._ensure_document_checklist()
  → crm.document.checklist.search existing? → skip (không tạo duplicate)
  → crm.document.checklist.template.search(product_type)
  → crm.document.checklist.create(lead_id, product_type, template_id)
  → crm.document.checklist.line.create_many(from template.item_ids)
  → activity_schedule(type=todo, summary='Nhắc bổ sung hồ sơ', deadline=today+remind_days)

[Khi nhân viên cập nhật line.status = 'submitted']
  → onchange → submitted_date = today
  → completion_rate recomputed

[Nhắc qua Zalo — Phase 2]
  → get_pending_items_text() → gửi qua Zalo OA API
```

---

## Luồng 4: Cold Lead Alert (Cron daily)

```
ir.cron → crm.lead._cron_cold_lead_alert()
  → search leads: write_date < now - threshold_days, active, opportunity, pending
  → per lead:
    → skip if activity 'nguội' đang pending
    → CrmAiService.get_cold_lead_reengage(name, stage, days, history)
      → Claude → {reason_cold, reengage_suggestion, suggested_message}
    → lead.message_post(note: ❄️ Lead nguội + gợi ý)
    → lead.activity_schedule(type=call, summary='Re-engage lead nguội', deadline=today)
```

---

## Luồng 5: Large Deal Alert (Cron daily)

```
ir.cron → crm.lead._cron_large_deal_alert()
  → search leads: expected_revenue >= threshold, active, opportunity, pending
  → per lead:
    → manager = lead.team_id.user_id
    → search mail.message: author=manager, date >= now-7days → found? skip
    → discuss.channel (team channel):
        message_post("👔 Deal lớn cần chú ý: ...")
    → lead.activity_schedule(type=meeting, summary='Cần hỗ trợ manager', user=manager)
```

---

## Luồng 6: Daily Digest (Cron 8:00 AM)

```
ir.cron → crm.lead._cron_send_daily_digest()
  → search res.users (active salespeople)
  → per user:
    → leads = search(user_id=user, active, opportunity, pending)
    → overdue = leads with overdue activities
    → hot = leads with probability >= 70%
    → cold = leads with write_date < now - threshold
    → pending_checklist = crm.document.checklist where pending_count > 0

    → CrmAiService.generate_daily_digest(name, stats...)
      → Claude → tin nhắn tiếng Việt tự nhiên <150 từ

    → discuss.channel (DM) gửi message
```

---

## Luồng 7: Zalo Webhook

```
POST /crm/ai/webhook/zalo (auth=public)
  → verify Zalo OA signature (HMAC-SHA256)
  → parse: sender.id (phone), message.text
  → search crm.lead by phone_sanitized
    → not found → tạo lead mới, tag 'Từ Zalo'
  → lead.message_post(body='[Zalo] ' + text)
  → ir.cron async → lead._ai_process_zalo_message(text)
    → CrmAiService.detect_needs(message)
    → Claude → {needs, confidence, signals}
    → post internal note + _apply_needs_tags()
```

---

## Sơ đồ phụ thuộc giữa các modules

```
crm.ai.config  ←────────────── (đọc config)
      ↑
CrmAiService  ←──────────────── (khởi tạo với env)
      ↑              ↑              ↑
crm.lead       call_stream.py   crm_lead.py
(email AI,     (call endpoints) (cron methods)
 zalo, crons)

crm.ai.call.session ←── crm.ai.transcript.line
      ↑
crm.lead (O2M)

crm.document.checklist ←── crm.document.checklist.line
      ↑
crm.document.checklist.template ←── product_checklist_data.xml
```

---

## Async Pattern

Tất cả AI calls chạy qua `ir.cron` one-time để không block request:

```python
# Pattern dùng trong toàn module
self.env['ir.cron'].sudo().create({
    'name': f'AI task: {self.id}',
    'model_id': self.env['ir.model']._get('crm.lead').id,
    'state': 'code',
    'code': f'model.browse({self.id})._ai_method()',
    'interval_number': 1,
    'interval_type': 'minutes',
    'numbercall': 1,
    'active': True,
})
```

Ngoại lệ: Realtime call screen dùng WebSocket trực tiếp (Deepgram/whisper-streaming) — không qua Odoo backend.

---

## Cài đặt và chạy

```bash
# 1. Cài Python packages
# Không cần cài thêm package nào cho Phase 1
# requests đã có sẵn trong Odoo
# Claude API, OpenAI Whisper API, OCR API đều gọi qua requests HTTP trực tiếp
# pdfminer.six + python-docx chỉ cần ở Phase 3 (đọc BCTC PDF, sinh proposal DOCX)

# 2. Cập nhật module list
./odoo-bin -c odoo.conf --update=crm_ai_banking

# 3. Cấu hình
CRM → AI Banking → Cấu hình AI → điền API keys → Save

# 4. Test
CRM → Opportunities → mở lead → click "🎤 Gọi AI"
```
