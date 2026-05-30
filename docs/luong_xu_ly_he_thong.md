# Luồng xử lý hệ thống CRM AI Banking

> Tài liệu kỹ thuật: mô tả luồng dữ liệu, kiến trúc xử lý, và tích hợp giữa các module.

---

## 1. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    KÊNH ĐẦU VÀO                                  │
│  Zalo OA  │  Email  │  Voice/Twilio  │  Scan ảnh  │  Core Banking│
└─────┬─────┴────┬────┴───────┬────────┴──────┬──────┴──────┬──────┘
      │          │            │               │             │
      ▼          ▼            ▼               ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CRM AI BANKING MODULE                          │
│                                                                  │
│  controllers/  ←── REST endpoints, Webhooks, WebSocket          │
│       ↓                                                          │
│  models/crm_lead.py  ←── Business logic chính                   │
│       ↓                                                          │
│  models/crm_ai_service.py  ←── Router tất cả AI calls           │
│       ↓                                                          │
│  ┌─────────┬──────────┬─────────┬──────────┐                    │
│  │  Claude  │  OCR API │  STT    │  Zalo OA │                    │
│  │ (Anthropic│(OpenRouter│(Whisper/│  API v3  │                    │
│  │  /local) │ /Local)  │Deepgram)│          │                    │
│  └─────────┴──────────┴─────────┴──────────┘                    │
│                                                                  │
│  Kết quả → Odoo crm.lead + chatter + activities + discuss       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Luồng xử lý: Gọi điện AI Realtime

```
[Browser]                [Controller]              [Service/AI]
    │                         │                         │
    │ Click "🎤 Gọi AI"       │                         │
    ├──POST /crm/ai/call/start─►                         │
    │◄── {session_id} ────────┤                         │
    │                         │                         │
    │ (record audio)           │                         │
    │ Upload chunks           │                         │
    ├──POST /transcript/add──►│                         │
    │                         │ STT batch/stream        │
    │                         ├────────────────────────►│
    │                         │◄── transcript text ─────┤
    │                         │ save TranscriptLine     │
    │                         │ push via Odoo Bus       │
    │◄── bus notification ────┤                         │
    │ (transcript updates)    │                         │
    │                         │                         │
    │ Every 30s (AI Hints ON) │                         │
    ├──GET /crm/ai/call/hints─►                         │
    │                         ├──Claude: hints prompt──►│
    │                         │◄── hints JSON ──────────┤
    │◄── {hints} ─────────────┤                         │
    │                         │                         │
    │ Click "⏹ Kết thúc"     │                         │
    ├──POST /crm/ai/call/end──►                         │
    │◄── {status: ok} ────────┤                         │
    │                         │ threading.Thread()      │
    │                         ├─[async]─────────────────►
    │                         │   merge full transcript │
    │                         │   Claude: summarize     │
    │                         │   write session fields  │
    │                         │   message_post(Markup)  │
    │                         │   activity_schedule     │
    │                         │   _ai_run_nba()         │
    │◄── (chatter updates) ───┤                         │
```

### Anonymization trong gọi điện

```
Transcript thô (có thể chứa số CCCD, MST, tài khoản)
        ↓
CrmAiService.anonymize(text)
        ↓ (thứ tự quan trọng: dài → ngắn)
  1. _ACCOUNT_RE  (\d{13,19})  → [ACCOUNT_NO]
  2. _TAX_ID_RE   (\d{10})     → [TAX_ID]
  3. _CCCD_RE     (\d{9,12})   → [ID_NUMBER]
        ↓
Văn bản đã anonymize → gửi Claude
```

---

## 3. Luồng xử lý: Zalo Webhook

```
[Zalo OA Server]          [/crm/ai/webhook/zalo]        [crm.lead]
        │                           │                        │
        │ POST webhook event        │                        │
        ├──────────────────────────►│                        │
        │                           │ verify HMAC-SHA256     │
        │                           │ signature check        │
        │                           │                        │
        │                           │ extract: user_id,      │
        │                           │ message, event_type    │
        │                           │                        │
        │                           │ search lead by         │
        │                           │ zalo_user_id           │
        │                           │──────────────────────► │
        │                           │◄── lead / None ────────│
        │                           │                        │
        │                           │ if not found:          │
        │                           │   create new Lead      │
        │                           │   tag "Từ Zalo"        │
        │                           │                        │
        │                           │ message_post(chatter)  │
        │                           │ _trigger_async(        │
        │                           │   '_ai_process_zalo')  │
        │                           │                        │
        │◄── HTTP 200 ──────────────│                        │
        │                           │                        │
        │                    [async thread]                  │
        │                           │ detect_needs()         │
        │                           │ → Claude classify      │
        │                           │ → update tag_ids       │
        │                           │ → post internal note   │
        │                           │ → notify salesperson   │
        │                           │   if urgency=high      │
```

---

## 4. Luồng xử lý: OCR Scan tài liệu

```
[User Upload ảnh/PDF]
        │
        ▼
CrmAiService._call_ocr(image_bytes, doc_type)
        │
        ├─ ocr_provider == 'api'
        │       ↓
        │  POST https://openrouter.ai/api/v1/chat/completions
        │  model: qwen/qwen3-vl
        │  message: [{type: image_url, url: base64}, {type: text, prompt}]
        │  prompt theo doc_type:
        │    cccd_front → extract: name, dob, gender, address, id_number
        │    gpkd       → extract: company_name, tax_id, address, business_lines
        │    bctc       → extract: raw text cho analysis
        │
        └─ ocr_provider == 'local'
                ↓
           POST http://ocr-server/api/ocr
           multipart: file + doc_type
           Response: {fields extracted theo doc_type}
        │
        ▼
OCR Result dict
        │
        ▼ (với CCCD và GPKD)
anonymize() — MST/CCCD không rời server
        │
        ▼ (với BCTC)
CrmAiService.read_financial_statement(anonymized_text)
        │
        ▼
Claude prompt:
  "Phân tích BCTC, chỉ gợi ý câu hỏi cho RM.
   Trả về: {highlights: [...], questions: [...]}"
        │
        ▼
Lưu vào crm.ai.document:
  ocr_raw_text, ai_highlights_json, ai_questions_json
  processing_status = 'done'
        │
        ▼
message_post(Markup(note)) → chatter
```

---

## 5. Luồng xử lý: NBA (Next Best Action)

```
Trigger: sau call / email / Zalo / activity done / cron 3AM
        │
        ▼
crm.lead._ai_run_nba()
        │
        ▼ _build_lead_context()
Tổng hợp signals:
  • stage_id, probability, days_in_stage
  • write_date (days since last update)
  • ai_last_sentiment
  • ai_detected_needs_json
  • last 5 mail.message (body truncated)
  • call session summaries
  • document_checklist completion_rate
  • pending activities count
  • banking profile: TOI, risk_grade, product_holdings
        │
        ▼
CrmAiService.compute_next_best_action(context_dict)
        │
        ▼ anonymize(context) → Claude
Prompt template:
  "Phân tích trạng thái lead, đề xuất 1 hành động tốt nhất.
   JSON: {action_type, action_detail, urgency,
          reasoning, suggested_message, confidence}"
        │
        ▼
Validate action_type (phải nằm trong selection list)
        │
        ▼
Write to crm.lead:
  nba_action_type, nba_action_detail, nba_urgency
  nba_reasoning, nba_suggested_message, nba_confidence
  nba_computed_date = now()
  nba_dismissed = False  (reset khi tính lại)
        │
        ▼
View: NBA banner tự cập nhật (computed field không store)
      → close_won: banner xanh lá + nút ký HĐ
      → khác: banner xanh dương thông thường
```

---

## 6. Luồng xử lý: Email AI

```
Email đến alias của crm.lead
        │
        ▼
mail.thread.message_new() [override trong mail_thread.py]
        │
        ├─ super().message_new() — tạo lead/message bình thường
        │
        └─ if auto_process_email:
               lead._trigger_async('_ai_process_incoming_email', args=(msg_dict,))
                        │
                        ▼ [async thread - 2s delay]
                 extract body + subject từ msg_dict
                        │
                        ▼
                 CrmAiService.summarize_email(body, subject)
                 → Claude: {summary_bullets, intent, urgency, detected_needs}
                        │
                        ▼
                 post internal note (Markup HTML) vào chatter
                        │
                        ▼
                 map intent → activity:
                   pricing_inquiry   → "Gửi báo giá" (1 ngày)
                   ready_to_buy      → "Follow up ngay" (hôm nay)
                                        + notify salesperson qua Discuss
                   complaint         → "Xử lý khiếu nại" (hôm nay)
                   document_request  → "Kiểm tra hồ sơ" (1 ngày)
                        │
                        ▼
                 _apply_needs_tags() → update lead.tag_ids
```

---

## 7. Luồng xử lý: Core Banking Sync

```
[Core Banking System]
        │
        │ Đẩy dữ liệu (JSON/CSV) theo batch
        ▼
crm.corebanking.customer.batch (staging area)
  record_type: customer_master / customer_profile / product_holding
        │
        ▼ action_process() hoặc Cron 18:00 daily
        │
        ├─ customer_master → _process_customer_master()
        │     _find_partner() theo bank_cif hoặc CCCD/MST
        │     if found: update partner fields
        │     if not found + allow_create: create partner
        │     → write: bank_cif, customer_type, segment, sync_status
        │
        ├─ customer_profile → _process_customer_profile()
        │     upsert crm.banking.customer.profile (TOI, AUM, risk)
        │     if individual: upsert crm.banking.individual.profile
        │     if business:   upsert crm.banking.business.profile
        │
        └─ product_holding → _process_product_holding()
              upsert crm.banking.product.holding
              (deposit, loan, card, insurance, v.v.)
              key: partner_id + source_system + source_ref

Result:
  state: done / partial (có lỗi) / error
  action_taken: created / updated / profile_updated / holding_upserted

Dùng trong CRM:
  lead.banking_product_holding_ids → checklist cross-sell, NBA context
  lead.banking_individual_profile_ids → monthly_income cho eligibility rule
  crm.lead._cron_deposit_maturity_alert() → quét maturity_date
  crm.lead._cron_loan_repayment_alert() → quét outstanding_balance
```

---

## 8. Luồng xử lý: AI Product Recommendation

```
User nhấn "Gợi ý AI" trên tab Sản phẩm
        │
        ▼ action_ai_product_recommendations()
        │
        ▼ _trigger_async('_ai_run_product_recommendations')
        │
        ▼ [async - 2s delay]

LAYER 1 — Rule Engine:
  Search all active crm.product.eligibility.rule
  For each rule:
    - skip nếu KH đang có product_code này (from banking_product_holding)
    - check rule.check_eligibility(partner):
        * age: partner.date_of_birth vs min_age/max_age
        * (có thể mở rộng thêm income check)
  → eligible_products list

LAYER 2 — AI Scoring:
  Build banking_ctx từ crm.banking.customer.profile
  Build lead_ctx (needs, sentiment, product_type)
  
  CrmAiService.score_products(eligible_products, lead_ctx)
  → Claude: xếp hạng theo match_score (0-1)
             + match_reasons (list)
             + approach_suggestion
        │
        ▼
Create crm.product.recommendation:
  recommendations_json = top 5 ranked
  top_product_name, top_match_score
        │
        ▼
message_post(Markup) vào chatter (top 3)
```

---

## 9. Luồng xử lý: Cron Jobs tự động

### 9.1 Birthday Alert (7:00 AM daily)

```
Search res.partner WHERE:
  date_of_birth IS NOT NULL
  AND customer_rank > 0
  AND (month, day) IN next 3 days
        │
        ▼
For each partner:
  Find active opportunity (won_status=pending)
  Check no existing birthday activity this year
        │
        ▼
activity_schedule(
  type = "To Do"
  summary = "🎂 Chúc sinh nhật {name}"
  deadline = birthday_date
  user_id = lead.user_id hoặc SUPERUSER
)
```

### 9.2 Deposit Maturity Alert (7:30 AM daily)

```
Search crm.banking.product.holding WHERE:
  product_category = 'deposit'
  status = 'active'
  maturity_date BETWEEN today AND today+14
        │
        ▼
For each holding:
  Check no existing tiet_kiem opportunity in last 30 days
  Find RM từ banking profile (rm_code → res.users)
        │
        ▼
create crm.lead:
  type = opportunity
  product_type = tiet_kiem
  partner_id = holding.partner_id
  user_id = RM (nếu tìm được)
        │
        ▼
message_post + activity_schedule
```

### 9.3 NBA Refresh (3:00 AM daily)

```
Search crm.lead WHERE:
  active = True, type = opportunity
  won_status = pending
LIMIT 100
        │
        ▼
For each lead:
  try:
    lead._ai_run_nba()  ← gọi Claude
  except:
    log error, continue next
```

---

## 10. Pattern xử lý bất đồng bộ (Async Pattern)

Tất cả AI calls đều **non-blocking** — không làm chậm UI.

```python
# Pattern dùng trong toàn module:
def action_xxx(self):
    self.ensure_one()
    self._trigger_async(self.id, '_ai_run_xxx', args=())
    return {notification: "Đang xử lý..."}

def _trigger_async(self, rec_id, method_name, args=()):
    dbname = self.env.cr.dbname
    def _run():
        time.sleep(2)  # chờ transaction commit
        with Registry(dbname).cursor() as cr:
            env = odoo.api.Environment(cr, SUPERUSER_ID, {})
            rec = env[self._name].browse(rec_id)
            if rec.exists():
                getattr(rec, method_name)(*args)
    threading.Thread(target=_run, daemon=True).start()
```

**Tại sao `time.sleep(2)`?**  
Đảm bảo transaction hiện tại (write `processing_status = 'processing'`) đã commit trước khi thread con mở connection mới.

---

## 11. Bảo mật dữ liệu

### 11.1 Nguyên tắc Anonymization

```
Dữ liệu thô vào CrmAiService
        │
        ▼ CrmAiService.anonymize(text)
Thứ tự replace (quan trọng: dài → ngắn để tránh partial match):
  1. \d{13,19}  → [ACCOUNT_NO]   (số tài khoản ngân hàng)
  2. \d{10}     → [TAX_ID]       (MST doanh nghiệp 10 số)
  3. \d{9,12}   → [ID_NUMBER]    (CCCD/CMND 9-12 số)
        │
        ▼
Văn bản anonymized → gửi Claude / OCR API

Kết quả trả về từ Claude:
  KHÔNG chứa số thực → lưu vào JSON fields
  Hiển thị trong HTML fields (Markup)
```

### 11.2 Lưu trữ dữ liệu nhạy cảm

| Dữ liệu | Nơi lưu | Access control |
|---------|---------|----------------|
| Số CCCD | `res.partner.cccd_number` | group_crm_manager + group_system |
| MST (GPKD) | `res.partner.vat` (standard) | Mọi user CRM |
| Số tài khoản | `crm.banking.product.holding.masked_account_number` | group_corebanking_integration |
| Banking 360 data | `crm.banking.*.profile` | BankingCoreMixin → _check_banking_write_access() |

### 11.3 BankingCoreMixin — Access Control

```python
def _can_write_banking_data(env):
    return (
        env.su                                              # SUPERUSER
        or env.context.get('allow_corebanking_sync_write') # sync context
        or env.user.has_group('base.group_system')         # admin
        or env.user.has_group('crm_ai_banking.group_corebanking_integration')
    )
```

Mọi write/create/unlink trên banking profile models đều qua check này.

---

## 12. Tích hợp Odoo Bus (Realtime notifications)

```
STT streaming → partial transcript
        │
        ▼
Controller: env['bus.bus']._sendone(session_channel, 'transcript_update', data)
        │
        ▼ WebSocket
Browser OWL LiveCallScreen: bus.subscribe('transcript_update')
        │
        ▼
Cập nhật transcript lines realtime (không reload trang)
```

---

## 13. HTML Rendering trong Chatter (Markup)

**Quy tắc bắt buộc** — Odoo 19:

```python
# ❌ SAI — str bị escape, hiện thị raw HTML tags
lead.message_post(body='<b>Hello</b>')

# ✅ ĐÚNG — Markup không bị escape
from markupsafe import Markup, escape
lead.message_post(body=Markup('<b>Hello</b>'))

# ✅ ĐÚNG — escape user content bên trong Markup
note = Markup('<b>Gợi ý:</b><ul>')
for item in user_items:
    note += Markup('<li>{}</li>').format(escape(item))
note += Markup('</ul>')
lead.message_post(body=note)

# ✅ ĐÚNG — computed Html fields
def _compute_xxx_html(self):
    for rec in self:
        rec.xxx_html = Markup(''.join(html_parts))
```
