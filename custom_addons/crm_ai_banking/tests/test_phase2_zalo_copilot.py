from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.exceptions import UserError

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase2", "post_install", "-at_install")
class TestPhase2ZaloCopilot(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.config = cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 2 Zalo Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
            "zalo_oa_access_token": "test-zalo-token",
            "zalo_webhook_secret": "test-zalo-secret",
        })
        cls.sales_user = new_test_user(
            cls.env,
            login="phase2_zalo_sales",
            groups="base.group_user",
            name="Phase 2 Zalo Sales",
            email="phase2_zalo_sales@example.com",
        )

    def _create_lead(self, **values):
        vals = {
            "name": "Phase 2 Zalo Lead",
            "type": "opportunity",
            "user_id": self.sales_user.id,
        }
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_find_or_create_lead_for_zalo_uses_existing_lead(self):
        lead = self._create_lead(zalo_user_id="zalo-001")

        found = self.env["crm.lead"]._find_or_create_lead_for_zalo(
            "zalo-001",
            {"display_name": "Existing Zalo"},
        )

        self.assertEqual(found, lead)

    def test_find_or_create_lead_for_zalo_uses_partner_latest_lead(self):
        partner = self.env["res.partner"].create({
            "name": "Partner From Zalo",
            "zalo_user_id": "zalo-002",
        })
        lead = self._create_lead(partner_id=partner.id)

        found = self.env["crm.lead"]._find_or_create_lead_for_zalo(
            "zalo-002",
            {"display_name": "Partner From Zalo"},
        )

        self.assertEqual(found, lead)

    def test_find_or_create_lead_for_zalo_creates_tagged_lead(self):
        lead = self.env["crm.lead"]._find_or_create_lead_for_zalo(
            "zalo-003",
            {"display_name": "New Zalo User"},
        )

        self.assertTrue(lead.exists())
        self.assertEqual(lead.type, "lead")
        self.assertEqual(lead.zalo_user_id, "zalo-003")
        self.assertEqual(lead.partner_id.zalo_user_id, "zalo-003")
        self.assertTrue(any("Zalo" in name for name in lead.tag_ids.mapped("name")))

    def test_handle_zalo_incoming_logs_message_and_schedules_ai(self):
        webhook_data = {
            "sender": {"id": "zalo-004", "display_name": "Webhook User"},
            "message": {"text": "toi can vay mua nha"},
        }

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            self.env["crm.lead"]._handle_zalo_incoming(webhook_data)

        lead = self.env["crm.lead"].search([("zalo_user_id", "=", "zalo-004")], limit=1)
        self.assertTrue(lead.exists())
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "toi can vay mua nha"),
        ], limit=1))
        trigger_async.assert_called_once()
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_process_zalo_message")
        self.assertEqual(kwargs["args"], ("toi can vay mua nha",))

    def test_ai_process_zalo_message_posts_note_and_tags_needs(self):
        lead = self._create_lead(zalo_user_id="zalo-005")
        ai_result = {
            "needs": ["loan", "credit_card"],
            "confidence": 0.87,
            "signals": ["vay", "the tin dung"],
        }

        with patch.object(CrmAiService, "detect_needs", return_value=ai_result):
            lead._ai_process_zalo_message("toi can vay va mo the")

        tag_names = lead.tag_ids.mapped("name")
        self.assertTrue(any(name.startswith("Vay") for name in tag_names))
        self.assertTrue(any("Thẻ" in name or "The" in name for name in tag_names))
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "loan"),
        ], limit=1))

    def test_action_send_zalo_opens_compose_wizard_with_lead_zalo_id(self):
        lead = self._create_lead(zalo_user_id="zalo-006")

        action = lead.action_send_zalo()

        self.assertEqual(action["res_model"], "crm.ai.zalo.compose")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_lead_id"], lead.id)
        self.assertEqual(action["context"]["default_zalo_user_id"], "zalo-006")

    def test_action_send_zalo_falls_back_to_partner_zalo_id(self):
        partner = self.env["res.partner"].create({
            "name": "Zalo Partner",
            "zalo_user_id": "partner-zalo-001",
        })
        lead = self._create_lead(partner_id=partner.id)

        action = lead.action_send_zalo()

        self.assertEqual(action["context"]["default_zalo_user_id"], "partner-zalo-001")

    def test_manual_detect_needs_schedules_async_from_chatter(self):
        lead = self._create_lead()
        lead.message_post(body="Khach hoi lai suat vay mua nha", message_type="comment")

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            action = lead.action_detect_needs()

        trigger_async.assert_called_once()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "info")
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_run_needs_detection")
        self.assertIn("vay mua nha", kwargs["args"][0])

    def test_manual_detect_needs_warns_when_no_chatter_content(self):
        lead = self._create_lead()

        action = lead.action_detect_needs()

        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "warning")

    def test_zalo_compose_get_ai_drafts_uses_informal_tone(self):
        lead = self._create_lead(zalo_user_id="zalo-007")
        lead.message_post(body="Khach can tu van khoan vay", message_type="comment")
        wizard = self.env["crm.ai.zalo.compose"].create({
            "lead_id": lead.id,
            "zalo_user_id": "zalo-007",
            "message": "draft placeholder",
        })
        drafts = [
            {"tone": "informal", "text": "Em gui anh thong tin khoan vay nhe."},
            {"tone": "informal", "text": "Anh cho em xin them muc vay du kien nhe."},
        ]

        with patch.object(CrmAiService, "generate_reply", return_value=drafts) as generate_reply:
            action = wizard.action_get_ai_drafts()

        generate_reply.assert_called_once()
        self.assertEqual(generate_reply.call_args.kwargs["tone"], "informal")
        self.assertEqual(wizard.draft_1, drafts[0]["text"])
        self.assertEqual(wizard.draft_2, drafts[1]["text"])
        self.assertEqual(action["res_id"], wizard.id)

    def test_zalo_compose_use_draft_updates_message_but_does_not_send(self):
        lead = self._create_lead(zalo_user_id="zalo-008")
        wizard = self.env["crm.ai.zalo.compose"].create({
            "lead_id": lead.id,
            "zalo_user_id": "zalo-008",
            "message": "old message",
            "draft_1": "selected draft",
        })

        with patch("odoo.addons.crm_ai_banking.wizard.crm_ai_zalo_compose.requests.post") as post:
            wizard.action_use_draft_1()

        post.assert_not_called()
        self.assertEqual(wizard.message, "selected draft")

    def test_zalo_compose_send_posts_to_api_and_logs_chatter(self):
        lead = self._create_lead(zalo_user_id="zalo-009")
        wizard = self.env["crm.ai.zalo.compose"].create({
            "lead_id": lead.id,
            "zalo_user_id": "zalo-009",
            "message": "Xin chao anh chi",
        })
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"error": 0}

        with patch("odoo.addons.crm_ai_banking.wizard.crm_ai_zalo_compose.requests.post", return_value=response) as post:
            action = wizard.action_send()

        post.assert_called_once()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["recipient"]["user_id"], "zalo-009")
        self.assertEqual(payload["message"]["text"], "Xin chao anh chi")
        self.assertEqual(post.call_args.kwargs["headers"]["access_token"], "test-zalo-token")
        self.assertEqual(action["tag"], "display_notification")
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Xin chao anh chi"),
        ], limit=1))

    def test_zalo_compose_send_requires_access_token(self):
        self.config.zalo_oa_access_token = False
        lead = self._create_lead(zalo_user_id="zalo-010")
        wizard = self.env["crm.ai.zalo.compose"].create({
            "lead_id": lead.id,
            "zalo_user_id": "zalo-010",
            "message": "hello",
        })

        with self.assertRaises(UserError):
            wizard.action_send()
