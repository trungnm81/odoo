import base64
import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase3", "post_install", "-at_install")
class TestPhase3B2BDocuments(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 3 Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
        })
        cls.sales_user = new_test_user(
            cls.env,
            login="phase3_sales",
            groups="base.group_user",
            name="Phase 3 Sales",
            email="phase3_sales@example.com",
        )

    def _create_lead(self, **values):
        partner = values.pop("partner_id", None)
        vals = {
            "name": "Phase 3 Lead",
            "type": "opportunity",
            "user_id": self.sales_user.id,
            "product_type": "vay_kinh_doanh",
        }
        if partner:
            vals["partner_id"] = partner.id if hasattr(partner, "id") else partner
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_account_contact_map_stores_stakeholder_roles(self):
        lead = self._create_lead()

        contact = self.env["crm.account.contact"].create({
            "lead_id": lead.id,
            "name": "Nguyen CFO",
            "title": "CFO",
            "role": "cfo",
            "influence_level": "decision_maker",
            "relationship_strength": "4",
            "email": "cfo@example.com",
        })

        self.assertIn(contact, lead.account_contact_ids)
        self.assertIn("CFO", contact.role_label)
        self.assertIn("Ra quy", contact.influence_level_label)

    def test_gpkd_scan_action_prefills_lead_partner_and_scan_type(self):
        partner = self.env["res.partner"].create({"name": "ABC Company", "is_company": True})
        lead = self._create_lead(partner_id=partner)

        action = lead.action_scan_gpkd()

        self.assertEqual(action["res_model"], "crm.ai.scan.document")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_scan_type"], "gpkd")
        self.assertEqual(action["context"]["default_lead_id"], lead.id)
        self.assertEqual(action["context"]["default_partner_id"], partner.id)

    def test_apply_gpkd_updates_partner_and_does_not_log_tax_id_in_chatter(self):
        lead = self._create_lead()
        tax_id = "0312345678"
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "gpkd",
            "lead_id": lead.id,
            "extracted_company": "ABC Manufacturing JSC",
            "extracted_address": "1 Nguyen Hue",
            "result_json": json.dumps({
                "company_name": "ABC Manufacturing JSC",
                "tax_id": tax_id,
                "representative": "Tran CEO",
            }),
        })

        action = wizard.action_apply_to_lead()

        lead.invalidate_recordset(["partner_id", "name"])
        partner = lead.partner_id
        self.assertEqual(action["res_model"], "crm.lead")
        self.assertEqual(partner.name, "ABC Manufacturing JSC")
        self.assertEqual(partner.street, "1 Nguyen Hue")
        self.assertEqual(partner.function, "Tran CEO")
        self.assertEqual(partner.cccd_number, tax_id)
        self.assertEqual(lead.name, "[GPKD] ABC Manufacturing JSC")
        self.assertEqual(lead.customer_type, "business")
        self.assertFalse(self.env["mail.message"].search([
            ("model", "=", "res.partner"),
            ("res_id", "=", partner.id),
            ("body", "ilike", tax_id),
        ], limit=1))

    def test_apply_gpkd_requires_company_when_no_partner_exists(self):
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "gpkd",
            "result_json": "{}",
        })

        with self.assertRaises(UserError):
            wizard.action_apply_to_lead()

    def test_action_add_bctc_creates_ai_document_for_lead(self):
        lead = self._create_lead()

        action = lead.action_add_bctc()
        document = self.env["crm.ai.document"].browse(action["res_id"])

        self.assertTrue(document.exists())
        self.assertEqual(action["res_model"], "crm.ai.document")
        self.assertEqual(document.lead_id, lead)
        self.assertEqual(document.document_type, "bctc")
        self.assertIn(document, lead.ai_document_ids)

    def test_ai_document_requires_attachment_before_analyze(self):
        document = self.env["crm.ai.document"].create({
            "lead_id": self._create_lead().id,
            "document_type": "bctc",
        })

        with self.assertRaises(UserError):
            document.action_analyze()

    def test_ai_document_do_analyze_runs_ocr_financial_ai_and_posts_note(self):
        lead = self._create_lead()
        attachment = self.env["ir.attachment"].create({
            "name": "bctc.pdf",
            "type": "binary",
            "datas": base64.b64encode(b"fake-pdf-bytes"),
            "res_model": "crm.lead",
            "res_id": lead.id,
        })
        document = self.env["crm.ai.document"].create({
            "lead_id": lead.id,
            "document_type": "bctc",
            "attachment_id": attachment.id,
        })
        ocr_result = {"raw": "Revenue 2025: 100 ty. Debt ratio high.", "year": "2025"}
        analysis = {
            "highlights": ["Revenue grows", "Debt ratio high"],
            "questions": ["Can customer explain debt increase?"],
        }

        with patch.object(CrmAiService, "_call_ocr", return_value=ocr_result) as call_ocr, \
             patch.object(CrmAiService, "read_financial_statement", return_value=analysis) as read_fs:
            document._do_analyze()

        call_ocr.assert_called_once()
        read_fs.assert_called_once_with(ocr_result["raw"])
        self.assertEqual(document.processing_status, "done")
        self.assertEqual(document.year, "2025")
        self.assertIn("Revenue grows", document.ai_highlights_json)
        self.assertIn("Can customer explain", document.ai_questions_json)
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Debt ratio high"),
        ], limit=1))

    def test_proposal_generate_fills_template_without_ai_when_no_custom_notes(self):
        partner = self.env["res.partner"].create({"name": "Home Buyer"})
        lead = self._create_lead(partner_id=partner, product_type="vay_mua_nha")
        wizard = self.env["crm.ai.generate.proposal"].create({
            "lead_id": lead.id,
            "template_key": "vay_mua_nha",
            "partner_name": "Home Buyer",
            "loan_amount": "2 ty VND",
            "loan_term": "20 nam",
            "property_address": "Thu Duc",
        })

        with patch.object(CrmAiService, "generate_proposal_content") as generate_content:
            action = wizard.action_generate()

        generate_content.assert_not_called()
        self.assertEqual(action["res_id"], wizard.id)
        self.assertEqual(wizard.state, "result")
        self.assertIn("2 ty VND", wizard.generated_content)
        self.assertIn("Thu Duc", wizard.generated_content)

    def test_proposal_generate_uses_ai_enhancement_when_custom_notes_exist(self):
        lead = self._create_lead(product_type="vay_kinh_doanh")
        wizard = self.env["crm.ai.generate.proposal"].create({
            "lead_id": lead.id,
            "template_key": "vay_kinh_doanh",
            "partner_name": "Business Owner",
            "company_name": "Biz Co",
            "loan_amount": "5 ty VND",
            "purpose": "Bo sung von luu dong",
            "custom_notes": "Make it concise",
        })

        with patch.object(CrmAiService, "generate_proposal_content", return_value="Enhanced proposal") as generate_content:
            wizard.action_generate()

        generate_content.assert_called_once()
        self.assertEqual(wizard.generated_content, "Enhanced proposal")
        self.assertEqual(wizard.state, "result")

    def test_proposal_attach_creates_attachment_and_chatter_note(self):
        lead = self._create_lead()
        wizard = self.env["crm.ai.generate.proposal"].create({
            "lead_id": lead.id,
            "template_key": "vay_kinh_doanh",
            "generated_content": "Proposal body",
            "state": "result",
        })

        action = wizard.action_attach_to_lead()

        self.assertEqual(action["res_model"], "crm.lead")
        self.assertTrue(self.env["ir.attachment"].search([
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("name", "ilike", "Proposal_"),
        ], limit=1))
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Proposal body"),
        ], limit=1))

    def test_crosssell_action_schedules_async_worker(self):
        lead = self._create_lead(product_type="vay_kinh_doanh")

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            action = lead.action_crosssell_suggestions()

        self.assertEqual(action["tag"], "display_notification")
        trigger_async.assert_called_once()
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_run_crosssell")
        self.assertEqual(kwargs["args"], ())

    def test_ai_run_crosssell_posts_suggestions_to_chatter(self):
        lead = self._create_lead(product_type="vay_kinh_doanh")
        result = {
            "priority_product": "payroll",
            "suggestions": [{
                "product": "Payroll",
                "reason": "Company has many employees",
                "approach": "Ask about salary payment process",
            }],
        }

        with patch.object(CrmAiService, "get_crosssell_suggestions", return_value=result):
            lead._ai_run_crosssell()

        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Payroll"),
        ], limit=1))

    def test_financial_statement_service_anonymizes_sensitive_data_before_llm(self):
        service = CrmAiService(self.env)
        captured = {}

        def fake_claude(prompt):
            captured["prompt"] = prompt
            return {"highlights": [], "questions": []}

        with patch.object(CrmAiService, "_claude_json", side_effect=fake_claude):
            service.read_financial_statement("MST 0312345678, phone 0901234567, revenue 100 ty")

        self.assertNotIn("0312345678", captured["prompt"])
        self.assertNotIn("0901234567", captured["prompt"])
