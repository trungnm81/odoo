# Test Report Phase 1 - Core Infrastructure

Ngay tao report: 2026-05-30  
Database: `odoo_dev`  
Module: `crm_ai_banking`  
Test tag: `crm_ai_banking_phase1`  
Raw log: `custom_addons/crm_ai_banking/docs/test_phase1_raw.log`

## Lenh da chay

```bash
python3 odoo-bin -c odoo.conf -d odoo_dev -u crm_ai_banking --test-enable --test-tags crm_ai_banking_phase1 --stop-after-init --no-http --logfile=custom_addons/crm_ai_banking/docs/test_phase1_raw.log
```

## Ket qua tong quan

Trang thai: **FAILED**

Theo dong ket qua cua Odoo:

- Post-tests: 11
- Failed: 1
- Errors: 0
- Thoi gian: 0.87s
- Queries: 1224

Dong `odoo.tests.stats` ghi `crm_ai_banking: 17 tests`, trong khi `odoo.tests.result` ghi `11 tests`. Report nay lay ket luan pass/fail theo `odoo.tests.result`.

## Test da chay

- `TestPhase1CallCron.test_call_summary_posts_chatter_updates_tags_and_next_activity`
- `TestPhase1CallCron.test_cold_lead_cron_posts_reengagement_activity`
- `TestPhase1CallCron.test_large_deal_cron_schedules_manager_activity`
- `TestPhase1CallCron.test_transcript_line_upsert_partial_then_final`
- `TestPhase1EmailChecklist.test_email_ai_posts_note_schedules_activity_tags_and_checklist`
- `TestPhase1EmailChecklist.test_message_new_schedules_email_ai_processing`
- `TestPhase1EmailChecklist.test_selecting_product_type_creates_checklist_once`
- `TestPhase1Service.test_anonymize_masks_sensitive_numbers`
- `TestPhase1Service.test_safe_format_keeps_prompt_stable_with_braces`
- `TestPhase1Service.test_summarize_email_routes_to_llm_and_parses_json`
- `TestPhase1Service.test_twilio_phone_normalization_for_vietnam_numbers`

## Loi / Failure

### 1. `TestPhase1Service.test_anonymize_masks_sensitive_numbers`

Ket qua mong doi:

- Chuoi sau anonymize phai co token `[TAX_ID]` cho MST.

Ket qua thuc te:

```text
AssertionError: '[TAX_ID]' not found in 'CCCD [ID_NUMBER], MST [ID_NUMBER], account [ACCOUNT_NO]'
```

Nhan dinh:

- Chuc nang mask du lieu nhay cam co hoat dong mot phan: CCCD va account number da duoc mask.
- MST/tax id dang bi mask thanh `[ID_NUMBER]` thay vi `[TAX_ID]`.
- Day co kha nang la van de thu tu regex trong `CrmAiService.anonymize()`: pattern CCCD/ID number bat truoc pattern tax id.

## Danh gia phase 1

Phase 1 **chua dat hoan toan** theo test suite hien tai vi con 1 failure lien quan den phan loai mask MST. Cac nhom con lai da pass trong lan chay nay:

- Call session summary, transcript upsert, cron lead nguoi/deal lon.
- Email AI orchestration, activity, tag, checklist.
- Safe format, email summary route, Twilio phone normalization.

Khuyen nghi: sua rieng logic anonymize MST/tax id sau khi duoc phe duyet, roi chay lai tag `crm_ai_banking_phase1`.
