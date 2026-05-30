# Test Report Phase 4 - NBA, Product Recommendation, Coaching, Customer 360

Ngay tao report: 2026-05-30  
Database: `odoo_dev`  
Module: `crm_ai_banking`  
Test tag: `crm_ai_banking_phase4`  
Raw log: `custom_addons/crm_ai_banking/docs/test_phase4_raw.log`

## Lenh da chay

```bash
python3 odoo-bin -c odoo.conf -d odoo_dev -u crm_ai_banking --test-enable --test-tags crm_ai_banking_phase4 --stop-after-init --no-http --logfile=custom_addons/crm_ai_banking/docs/test_phase4_raw.log
```

## Ket qua tong quan

Trang thai: **FAILED**

Theo dong ket qua cua Odoo:

- Post-tests: 16
- Failed: 2
- Errors: 1
- Thoi gian: 0.95s
- Queries: 1654

Dong `odoo.tests.stats` ghi `crm_ai_banking: 18 tests`, trong khi `odoo.tests.result` ghi `16 tests`. Report nay lay ket luan pass/fail theo `odoo.tests.result`.

## Test da chay

- `TestPhase4Intelligence.test_action_ai_product_recommendations_schedules_async_worker`
- `TestPhase4Intelligence.test_action_compute_nba_schedules_async_worker`
- `TestPhase4Intelligence.test_action_dismiss_nba_sets_flag`
- `TestPhase4Intelligence.test_action_refresh_customer_360_schedules_async_worker`
- `TestPhase4Intelligence.test_ai_product_recommendations_creates_ranked_record_and_note`
- `TestPhase4Intelligence.test_ai_run_customer_360_writes_json_and_update_date`
- `TestPhase4Intelligence.test_ai_run_nba_rejects_unknown_action_type`
- `TestPhase4Intelligence.test_ai_run_nba_writes_validated_fields_and_resets_dismissal`
- `TestPhase4Intelligence.test_call_session_action_create_coaching_report`
- `TestPhase4Intelligence.test_coaching_report_do_generate_uses_transcript_and_writes_scores`
- `TestPhase4Intelligence.test_coaching_report_overall_score_averages_non_zero_scores`
- `TestPhase4Intelligence.test_coaching_report_without_transcript_moves_to_error`
- `TestPhase4Intelligence.test_customer_360_html_escapes_rendered_content`
- `TestPhase4Intelligence.test_product_eligibility_rule_filters_by_customer_age`
- `TestPhase4Intelligence.test_product_recommendation_html_renders_only_top_three_items`
- `TestPhase4Intelligence.test_product_recommendations_fall_back_to_rules_when_ai_returns_empty`

## Loi / Failure

### 1. Failure: Customer 360 recent messages ordering

Test:

```text
TestPhase4Intelligence.test_ai_run_customer_360_writes_json_and_update_date
```

Ket qua thuc te:

```text
AssertionError: 'Customer asked' not found in Markup('<span><span>Dear Phase 4 Sales,</span>...')
```

Nhan dinh:

- `_ai_run_customer_360()` lay cac `mail.message` gan nhat cua lead.
- Message dau tien trong payload la notification he thong "You have been assigned to the Lead...", khong phai chatter comment do test tao.
- Day co the la van de thiet ke neu Customer 360 khong nen dua system assignment message vao recent customer messages.
- Cung co the la test can kiem tra toan bo danh sach `recent_messages`, thay vi gia dinh message can tim nam o index 0.

### 2. Error: Coaching Report ghi field khong ton tai

Test:

```text
TestPhase4Intelligence.test_coaching_report_without_transcript_moves_to_error
```

Ket qua thuc te:

```text
ValueError: Invalid field 'error_message' in 'crm.ai.coaching.report'
```

Nhan dinh:

- Trong `crm.ai.coaching.report._do_generate()`, khi khong co transcript, code goi:

```python
self.write({'processing_status': 'error', 'error_message': 'Không có transcript để phân tích'})
```

- Model `crm.ai.coaching.report` hien khong co field `error_message`.
- Day la loi nghiep vu/model kha ro: luong error handling cua coaching report khong hoat dong dung.

### 3. Failure: Product recommendation fallback bi anh huong boi rule co san

Test:

```text
TestPhase4Intelligence.test_product_recommendations_fall_back_to_rules_when_ai_returns_empty
```

Ket qua thuc te:

```text
AssertionError: 'Thẻ tín dụng Bạch Kim' != 'Savings Account'
```

Nhan dinh:

- Test tao rule `Savings Account` va mock AI tra ve empty list de kiem fallback rule-based.
- Code `_ai_run_product_recommendations()` search tat ca rule active trong DB:

```python
all_rules = self.env['crm.product.eligibility.rule'].search([('active', '=', True)])
```

- DB da co rule active khac (`Thẻ tín dụng Bạch Kim`) va rule nay duoc chon truoc.
- Day co the la van de test isolation hoac van de thiet ke neu fallback can sap xep/loc theo context san pham/nhu cau thay vi lay tat ca active rules theo order hien tai.

## Danh gia phase 4

Phase 4 **chua dat** theo test suite hien tai.

Phan da pass:

- NBA action scheduling.
- NBA ghi field hop le, clamp confidence, reset dismissed.
- NBA reject action type khong hop le.
- Dismiss NBA.
- Product eligibility rule theo tuoi.
- Product recommendation tao ranked record va chatter note khi AI co ranking.
- Product recommendation HTML chi render top 3.
- Tao coaching report tu call session.
- Coaching report generate co transcript va ghi score/json.
- Customer 360 action scheduling.
- Customer 360 HTML escape noi dung nguy hiem.

Phan can xem lai:

- Customer 360 nen loc/uu tien message nguoi dung thay vi system assignment message.
- `crm.ai.coaching.report` can co field `error_message` hoac code khong duoc write field nay.
- Product recommendation fallback can deterministic hon khi DB co nhieu active rule, hoac test can isolate/deactivate rule co san truoc khi kiem fallback.
