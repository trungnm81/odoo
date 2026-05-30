# Test Report Phase 2 - Capture & Zalo

Ngay tao report: 2026-05-30  
Database: `odoo_dev`  
Module: `crm_ai_banking`  
Test tag: `crm_ai_banking_phase2`  
Raw log: `custom_addons/crm_ai_banking/docs/test_phase2_raw.log`

## Lenh da chay

```bash
python3 odoo-bin -c odoo.conf -d odoo_dev -u crm_ai_banking --test-enable --test-tags crm_ai_banking_phase2 --stop-after-init --no-http --logfile=custom_addons/crm_ai_banking/docs/test_phase2_raw.log
```

## Ket qua tong quan

Trang thai: **PASSED**

Theo dong ket qua cua Odoo:

- Post-tests: 20
- Failed: 0
- Errors: 0
- Thoi gian: 0.97s
- Queries: 1685

Dong `odoo.tests.stats` ghi `crm_ai_banking: 24 tests`, trong khi `odoo.tests.result` ghi `20 tests`. Report nay lay ket luan pass/fail theo `odoo.tests.result`.

## Test da chay

### Capture / OCR

- `TestPhase2Capture.test_apply_cccd_updates_partner_and_links_lead`
- `TestPhase2Capture.test_apply_name_card_creates_partner_and_opportunity`
- `TestPhase2Capture.test_apply_name_card_reuses_existing_partner_by_phone`
- `TestPhase2Capture.test_cccd_number_is_restricted_to_system_group`
- `TestPhase2Capture.test_cccd_scan_routes_to_id_card_ocr_and_maps_dates`
- `TestPhase2Capture.test_name_card_scan_maps_fields_and_moves_to_review`
- `TestPhase2Capture.test_scan_requires_image_data`

### Zalo / Copilot

- `TestPhase2ZaloCopilot.test_action_send_zalo_falls_back_to_partner_zalo_id`
- `TestPhase2ZaloCopilot.test_action_send_zalo_opens_compose_wizard_with_lead_zalo_id`
- `TestPhase2ZaloCopilot.test_ai_process_zalo_message_posts_note_and_tags_needs`
- `TestPhase2ZaloCopilot.test_find_or_create_lead_for_zalo_creates_tagged_lead`
- `TestPhase2ZaloCopilot.test_find_or_create_lead_for_zalo_uses_existing_lead`
- `TestPhase2ZaloCopilot.test_find_or_create_lead_for_zalo_uses_partner_latest_lead`
- `TestPhase2ZaloCopilot.test_handle_zalo_incoming_logs_message_and_schedules_ai`
- `TestPhase2ZaloCopilot.test_manual_detect_needs_schedules_async_from_chatter`
- `TestPhase2ZaloCopilot.test_manual_detect_needs_warns_when_no_chatter_content`
- `TestPhase2ZaloCopilot.test_zalo_compose_get_ai_drafts_uses_informal_tone`
- `TestPhase2ZaloCopilot.test_zalo_compose_send_posts_to_api_and_logs_chatter`
- `TestPhase2ZaloCopilot.test_zalo_compose_send_requires_access_token`
- `TestPhase2ZaloCopilot.test_zalo_compose_use_draft_updates_message_but_does_not_send`

## Loi / Failure

Khong co failure hoac error.

## Danh gia phase 2

Phase 2 **dat** theo test suite hien tai. Cac luong chinh hoat dong dung ky vong:

- Scan name card/CCCD map du lieu sang partner/lead.
- Bao ve field CCCD bang group he thong.
- Zalo lead matching, tao lead moi, logging chatter, async needs detection.
- Wizard gui Zalo mo dung context, dung draft AI, khong gui network khi chi chon draft.
- Gui Zalo mock API va validate access token.
