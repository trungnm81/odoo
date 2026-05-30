from unittest.mock import patch

from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase1", "post_install", "-at_install")
class TestPhase1CallCron(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.config = cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 1 Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
            "cold_lead_threshold_days": 10,
            "large_deal_threshold": 5000000000,
            "large_deal_no_manager_days": 7,
        })
        cls.sales_user = new_test_user(cls.env, login="phase1_call_sales", groups="base.group_user", **{
            "name": "Phase 1 Call Sales User",
            "email": "phase1_call_sales@example.com",
        })
        cls.manager_user = new_test_user(cls.env, login="phase1_manager", groups="base.group_user", **{
            "name": "Phase 1 Manager User",
            "email": "phase1_manager@example.com",
        })
        cls.sales_team = cls.env["crm.team"].create({
            "name": "Phase 1 Sales Team",
            "user_id": cls.manager_user.id,
        })

    def _create_lead(self, **values):
        vals = {
            "name": "Phase 1 Opportunity",
            "type": "opportunity",
            "user_id": self.sales_user.id,
            "team_id": self.sales_team.id,
            "expected_revenue": 100000000,
        }
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_transcript_line_upsert_partial_then_final(self):
        lead = self._create_lead()
        session = self.env["crm.ai.call.session"].create({
            "lead_id": lead.id,
            "session_type": "call",
            "call_channel": "phone_mic",
            "user_id": self.sales_user.id,
        })

        line_id = self.env["crm.ai.transcript.line"].create_or_update_partial(
            session.id, 10, "customer", "toi can vay", 1.5, False
        )
        same_line_id = self.env["crm.ai.transcript.line"].create_or_update_partial(
            session.id, 10, "customer", "toi can vay mua nha", 2.0, True
        )

        self.assertEqual(line_id, same_line_id)
        line = self.env["crm.ai.transcript.line"].browse(line_id)
        self.assertTrue(line.is_final)
        self.assertEqual(line.text, "toi can vay mua nha")
        self.assertIn("[KH] toi can vay mua nha", session.full_transcript)

    def test_call_summary_posts_chatter_updates_tags_and_next_activity(self):
        lead = self._create_lead(product_type="vay_mua_nha")
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        session = self.env["crm.ai.call.session"].create({
            "lead_id": lead.id,
            "session_type": "call",
            "call_channel": "phone_mic",
            "user_id": self.sales_user.id,
            "next_activity_type_id": activity_type.id,
        })
        self.env["crm.ai.transcript.line"].create({
            "session_id": session.id,
            "sequence": 10,
            "speaker": "customer",
            "text": "I need a home loan quote.",
            "is_final": True,
        })
        ai_result = {
            "summary": "Customer wants a home loan quote.",
            "action_items": ["Send quote"],
            "sentiment": "positive",
            "detected_needs": ["loan"],
            "next_step": "Send home loan quote",
            "key_concerns": [],
        }

        with patch.object(CrmAiService, "summarize_call", return_value=ai_result):
            session._run_ai_summary()

        self.assertEqual(session.status, "summarized")
        self.assertEqual(session.sentiment, "positive")
        self.assertTrue(any(name.startswith("Vay") for name in lead.tag_ids.mapped("name")))
        self.assertTrue(lead.activity_ids.filtered(lambda activity: activity.summary == "Send home loan quote"))
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Customer wants a home loan quote"),
        ], limit=1))

    def test_cold_lead_cron_posts_reengagement_activity(self):
        lead = self._create_lead(name="Cold Lead")
        original_search = type(self.env["crm.lead"]).search

        def search_cold_leads(recordset, domain, *args, **kwargs):
            if recordset._name == "crm.lead" and any(item[0] == "write_date" for item in domain):
                return lead
            return original_search(recordset, domain, *args, **kwargs)

        ai_result = {
            "reason_cold": "No update for two weeks",
            "reengage_suggestion": "Call with a concrete offer",
            "suggested_message": "Would you like a revised quote?",
        }
        with patch.object(type(self.env["crm.lead"]), "search", autospec=True, side_effect=search_cold_leads), \
             patch.object(CrmAiService, "get_cold_lead_reengage", return_value=ai_result):
            self.env["crm.lead"]._cron_cold_lead_alert()

        self.assertTrue(lead.activity_ids.filtered(lambda activity: activity.summary and "Re-engage" in activity.summary))
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "No update for two weeks"),
        ], limit=1))

    def test_large_deal_cron_schedules_manager_activity(self):
        lead = self._create_lead(name="Large Deal", expected_revenue=6000000000)

        self.env["crm.lead"]._cron_large_deal_alert()

        self.assertTrue(lead.activity_ids.filtered(
            lambda activity: activity.user_id == self.manager_user
            and activity.activity_type_id == self.env.ref("mail.mail_activity_data_meeting")
        ))
