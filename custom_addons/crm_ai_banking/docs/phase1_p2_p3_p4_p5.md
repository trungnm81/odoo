# P1-2 đến P1-5: Email AI, Checklist, Cảnh báo, Daily Digest

---

## P1-2: Email AI

**Files:** `models/crm_lead.py`, `models/crm_ai_service.py`

### Cách hoạt động

```
Email gửi đến alias Odoo (VD: sales@yourbank.com)
        │
        ▼
crm.lead.message_new() bị override
        │
        ├─ Kiểm tra config.auto_process_email
        └─ True → _trigger_async(lead_id, '_ai_process_incoming_email', ...)
                        │
                        ▼
              Background thread (daemon, sleep 2s)
                        │
                        ▼
              _ai_process_incoming_email(body, subject)
```

### Chi tiết `_ai_process_incoming_email()`

```
1. CrmAiService.summarize_email(body, subject)
        │
        ▼ Claude trả về:
   {
     summary_bullets: ["..."],    ← tối đa 3 bullet
     intent: "pricing_inquiry",   ← phân loại ý định
     urgency: "high",             ← mức độ khẩn
     detected_needs: ["loan"],    ← nhu cầu tài chính
     suggested_action: "..."
   }

2. Post internal note vào Chatter:
   "🤖 AI Tóm tắt email:
    • Khách hỏi lãi suất vay mua nhà
    Intent: pricing_inquiry | Urgency: high
    Gợi ý: Gửi bảng lãi suất + gọi trong 24h"

3. Auto-schedule activity:
```

| Intent | Activity | Deadline |
|--------|---------|---------|
| `pricing_inquiry` | Gửi báo giá | +1 ngày |
| `ready_to_buy` | Follow up ngay | +0 ngày |
| `complaint` | Xử lý khiếu nại | +0 ngày |
| `document_request` | Kiểm tra hồ sơ | +1 ngày |
| `follow_up` | Follow up | +2 ngày |
| `general_inquiry` | Phản hồi khách | +1 ngày |

```
4. Notify qua Odoo bus nếu urgency = 'high' và có user_id
5. _apply_needs_tags(needs) — cập nhật tags trên Lead
6. Nếu intent = 'document_request' → _ensure_document_checklist()
```

### Async pattern

```python
def _trigger_async(self, record_id, method_name, args=()):
    # Spawn thread → sleep(2) → mở DB cursor mới → chạy method
    # Pattern này dùng chung cho Email AI, Cold Lead, Daily Digest, AI Summary
```

`sleep(2)` để đảm bảo transaction chính (tạo lead + message_new) đã commit trước khi thread đọc dữ liệu.

---

## P1-3: Checklist Hồ sơ Động

**File:** `models/crm_ai_document_checklist.py`

### Models

#### `crm.document.checklist.template`
Template giấy tờ theo loại sản phẩm. Admin tạo/sửa qua UI.

| Field | Mô tả |
|-------|-------|
| `product_type` | Loại sản phẩm (vay_mua_nha, the_tin_dung, ...) |
| `item_ids` | Danh sách giấy tờ theo template |
| `remind_after_days` | Số ngày sau khi tạo checklist sẽ nhắc (mặc định: 2) |

#### `crm.document.checklist.template.item`
Mỗi loại giấy tờ trong template:
- `name`: tên giấy tờ (VD: "CCCD 2 mặt")
- `required`: bắt buộc hay không
- `description`: mô tả thêm
- `file_format_hint`: định dạng yêu cầu (VD: "PDF, ảnh rõ nét")

#### `crm.document.checklist`
Checklist gắn với 1 Lead cụ thể.

| Field | Mô tả |
|-------|-------|
| `lead_id` | Lead liên quan |
| `product_type` | Loại sản phẩm (copy từ lead tại thời điểm tạo) |
| `completion_rate` | % hoàn thành — computed |
| `pending_count` | Số giấy tờ còn thiếu — computed |
| `line_ids` | Các dòng giấy tờ thực tế |

#### `crm.document.checklist.line`
Từng giấy tờ cụ thể của Lead.

| Status | Ý nghĩa |
|--------|---------|
| `pending` | Chờ nộp |
| `submitted` | Đã nộp |
| `approved` | Đã duyệt |
| `rejected` | Từ chối |

### Flow tạo checklist

```
Trigger bởi:
  ├─ Lead.product_type thay đổi (onchange)
  ├─ Email AI nhận intent = 'document_request'
  └─ Nhân viên tạo thủ công

        │
        ▼
crm.document.checklist.create_from_template(lead_id, product_type)
        │
        ├─ Tìm template phù hợp
        ├─ Tạo checklist + copy tất cả items
        └─ Schedule activity "📎 Nhắc bổ sung hồ sơ" sau N ngày
```

### Hiển thị trên Lead

Tab "Hồ sơ / Checklist" trên form Lead (view `crm_lead_views_inherit.xml`):
- Nhân viên cập nhật status từng giấy tờ (pending → submitted → approved)
- Attach file trực tiếp vào từng dòng
- `completion_rate` tự cập nhật theo trạng thái

---

## P1-4: Cảnh báo Lead Nguội + Deal Lớn

**File:** `models/crm_lead.py`, `data/ir_cron_data.xml`

### Cron: Cold Lead Alert

**Trigger:** Hàng ngày (lịch định trong cron)

```
Tìm tất cả opportunity active + pending + write_date < (hôm nay - threshold)
        │
        ▼ Per lead:
  ├─ Bỏ qua nếu đã có activity có chữ "nguội" trong summary
  ├─ CrmAiService.get_cold_lead_reengage(lead_name, stage, days_cold, history)
  │         → Claude → {reason_cold, reengage_suggestion, suggested_message}
  ├─ Post internal note: "❄️ Lead nguội (X ngày không cập nhật)"
  └─ Schedule activity "❄️ Re-engage lead nguội" deadline = hôm nay
```

**Threshold cấu hình:** `config.cold_lead_threshold_days` (mặc định 10 ngày)

### Cron: Large Deal Alert

**Trigger:** Hàng ngày

```
Tìm opportunity active + pending + expected_revenue >= threshold
        │
        ▼ Per lead:
  ├─ Lấy manager của team (team_id.user_id)
  ├─ Kiểm tra: manager có message nào trong N ngày qua không?
  ├─ Nếu không có → alert
  │     ├─ Post vào channel Discuss của team
  │     │   "👔 Deal lớn: [tên lead] — X tỷ | Stage: ..."
  │     └─ Schedule activity "👔 Cần hỗ trợ của manager" cho manager
```

**Threshold cấu hình:**
- `config.large_deal_threshold` (mặc định 5 tỷ VND)
- `config.large_deal_no_manager_days` (mặc định 7 ngày)

---

## P1-5: Daily Digest Cá nhân hóa

**File:** `models/crm_lead.py`, `data/ir_cron_data.xml`

### Cron: Daily Digest

**Trigger:** Hàng ngày lúc 8:00 sáng (giờ config trong `config.daily_digest_time`)

```
Lấy tất cả nhân viên nội bộ active
        │
        ▼ Per user:
  ├─ Bỏ qua nếu không có opportunity đang mở
  ├─ Tổng hợp dữ liệu:
  │     • overdue: activity quá hạn
  │     • hot: probability >= 70%
  │     • cold: write_date < threshold
  │     • pending_checklist: checklist có pending_count > 0
  ├─ CrmAiService.generate_daily_digest(name, overdue, hot, pending, cold)
  │         → Claude → Text tiếng Việt (< 150 từ, thân thiện, actionable)
  └─ Gửi qua Discuss DM (chat 1-1 giữa bot và nhân viên)
```

### Ví dụ output

```
Chào Minh, hôm nay có 3 việc ưu tiên:

🔥 Nguyễn Văn A (Vay 2.5 tỷ) — 5 ngày chờ, xác suất 78%
📎 Công ty ABC — còn thiếu BCTC 2024
⏰ 2 activities quá hạn cần xử lý

Chúc Minh có ngày làm việc hiệu quả!
```

### Cách gửi qua Discuss

```python
# Tìm DM channel đã có
dm = channel.search([
    ('channel_type', '=', 'chat'),
    ('channel_member_ids.partner_id', '=', user.partner_id.id),
    ...
], limit=1)

# Nếu chưa có → tạo mới
if not dm:
    dm = channel.create({'channel_type': 'chat', ...})

dm.message_post(body=digest)
```

---

## Tóm tắt luồng async chung (Pattern)

Tất cả processing nặng đều dùng cùng một pattern:

```python
def _trigger_async(self, record_id, method_name, args=()):
    dbname = self.env.cr.dbname

    def _run():
        time.sleep(2)          # Chờ transaction commit
        with Registry(dbname).cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            rec = env[model].browse(record_id)
            getattr(rec, method_name)(*args)

    threading.Thread(target=_run, daemon=True).start()
```

**Lý do không dùng Odoo queue_job:**
- `queue_job` (OCA) không phải core module — không muốn thêm dependency
- Threading đủ dùng cho load hiện tại, không cần persistent queue

**Nhược điểm cần biết:**
- Nếu server restart ngay sau khi trigger → job bị mất
- Không có retry mechanism — lỗi chỉ log, không thử lại
- Với production load lớn nên chuyển sang `ir.cron` one-time hoặc queue_job
