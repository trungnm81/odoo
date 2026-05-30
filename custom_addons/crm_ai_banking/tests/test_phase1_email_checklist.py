from unittest.mock import patch

from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase1", "post_install", "-at_install")
class TestPhase1EmailChecklist(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.config = cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 1 Test Config",
            "active": True,
            "auto_process_email": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
        })
        cls.sales_user = new_test_user(cls.env, login="phase1_sales_user", groups="base.group_user", **{
            "name": "Phase 1 Sales User",
            "email": "phase1_sales_user@example.com",
        })

    def _create_lead(self, **values):
        vals = {
            "name": "Phase 1 Lead",
            "type": "opportunity",
            "user_id": self.sales_user.id,
        }
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_message_new_schedules_email_ai_processing(self):
        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            lead = self.env["crm.lead"].message_new({
                "subject": "Need home loan documents",
                "from": "customer@example.com",
                "body": "Please send the document checklist.",
            })

        self.assertTrue(lead.exists())
        self.assertEqual(trigger_async.call_count, 1)
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_process_incoming_email")
        self.assertEqual(kwargs["args"][1], "Need home loan documents")

    def test_email_ai_posts_note_schedules_activity_tags_and_checklist(self):
        lead = self._create_lead(product_type="vay_mua_nha")
        ai_result = {
            "summary_bullets": ["Customer asks which documents are needed"],
            "intent": "document_request",
            "urgency": "high",
            "detected_needs": ["loan"],
            "suggested_action": "Send document checklist",
        }

        with patch.object(CrmAiService, "summarize_email", return_value=ai_result):
            lead._ai_process_incoming_email("Need document checklist", "Documents")

        message = self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "document_request"),
        ], limit=1)
        self.assertTrue(message, "Email AI should post an internal summary note on the lead.")
        self.assertTrue(any(name.startswith("Vay") for name in lead.tag_ids.mapped("name")))
        self.assertTrue(lead.activity_ids.filtered(lambda activity: activity.activity_type_id == self.env.ref("mail.mail_activity_data_email")))

        checklist = self.env["crm.document.checklist"].search([
            ("lead_id", "=", lead.id),
            ("product_type", "=", "vay_mua_nha"),
        ])
        self.assertEqual(len(checklist), 1)
        self.assertGreater(len(checklist.line_ids), 0)

    def test_selecting_product_type_creates_checklist_once(self):
        lead = self._create_lead()

        lead.write({"product_type": "vay_mua_nha"})

        checklist = self.env["crm.document.checklist"].search([
            ("lead_id", "=", lead.id),
            ("product_type", "=", "vay_mua_nha"),
        ])
        self.assertEqual(
            len(checklist),
            1,
            "Selecting product_type on a lead should create the matching document checklist.",
        )

        lead.write({"product_type": "vay_mua_nha"})
        checklist = self.env["crm.document.checklist"].search([
            ("lead_id", "=", lead.id),
            ("product_type", "=", "vay_mua_nha"),
        ])
        self.assertEqual(len(checklist), 1, "Re-saving the same product_type must not duplicate checklists.")
