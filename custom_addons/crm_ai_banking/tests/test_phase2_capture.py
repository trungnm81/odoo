import base64
from unittest.mock import patch

from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.exceptions import UserError

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase2", "post_install", "-at_install")
class TestPhase2Capture(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.config = cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 2 Capture Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
        })
        cls.sales_user = new_test_user(
            cls.env,
            login="phase2_capture_sales",
            groups="base.group_user",
            name="Phase 2 Capture Sales",
            email="phase2_capture_sales@example.com",
        )

    def _image_b64(self):
        return base64.b64encode(b"fake-image-bytes")

    def _create_lead(self, **values):
        vals = {
            "name": "Phase 2 Capture Lead",
            "type": "opportunity",
            "user_id": self.sales_user.id,
        }
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_name_card_scan_maps_fields_and_moves_to_review(self):
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "name_card",
            "image_data": self._image_b64(),
            "image_filename": "card.jpg",
        })
        card_result = {
            "full_name": "Nguyen Van A",
            "title": "CFO",
            "company": "ABC Bank Client",
            "phone": "0901234567",
            "email": "a@example.com",
            "address": "1 Nguyen Hue",
            "website": "https://abc.example",
        }

        with patch.object(CrmAiService, "extract_card", return_value=card_result) as extract_card:
            action = wizard.action_scan()

        extract_card.assert_called_once()
        self.assertEqual(wizard.state, "review")
        self.assertEqual(wizard.extracted_full_name, "Nguyen Van A")
        self.assertEqual(wizard.extracted_phone, "0901234567")
        self.assertEqual(wizard.extracted_company, "ABC Bank Client")
        self.assertEqual(action["res_model"], "crm.ai.scan.document")
        self.assertEqual(action["res_id"], wizard.id)

    def test_scan_requires_image_data(self):
        wizard = self.env["crm.ai.scan.document"].create({"scan_type": "name_card"})

        with self.assertRaises(UserError):
            wizard.action_scan()

    def test_apply_name_card_creates_partner_and_opportunity(self):
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "name_card",
            "extracted_full_name": "Tran Thi B",
            "extracted_phone": "0912345678",
            "extracted_email": "b@example.com",
            "extracted_company": "B Company",
            "extracted_title": "CEO",
        })

        action = wizard.action_apply_to_lead()

        lead = self.env["crm.lead"].browse(action["res_id"])
        self.assertTrue(lead.exists())
        self.assertEqual(lead.type, "opportunity")
        self.assertEqual(lead.partner_id.name, "Tran Thi B")
        self.assertEqual(lead.partner_id.phone, "0912345678")
        self.assertEqual(lead.partner_id.email, "b@example.com")
        self.assertEqual(lead.partner_id.function, "CEO")
        self.assertEqual(wizard.state, "done")

    def test_apply_name_card_reuses_existing_partner_by_phone(self):
        partner = self.env["res.partner"].create({
            "name": "Old Name",
            "phone": "0987654321",
            "email": "old@example.com",
        })
        lead = self._create_lead()
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "name_card",
            "lead_id": lead.id,
            "extracted_full_name": "New Name",
            "extracted_phone": "0987654321",
            "extracted_email": "new@example.com",
            "extracted_company": "New Company",
        })

        wizard.action_apply_to_lead()

        self.assertEqual(lead.partner_id, partner)
        self.assertEqual(partner.name, "New Name")
        self.assertEqual(partner.email, "new@example.com")
        self.assertEqual(self.env["res.partner"].search_count([("phone", "=", "0987654321")]), 1)

    def test_cccd_scan_routes_to_id_card_ocr_and_maps_dates(self):
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "cccd_front",
            "image_data": self._image_b64(),
            "image_filename": "cccd.jpg",
        })
        cccd_result = {
            "full_name": "Le Van C",
            "date_of_birth": "25/03/1990",
            "gender": "Nam",
            "place_of_residence": "Ho Chi Minh",
            "id_number": "012345678901",
        }

        with patch.object(CrmAiService, "extract_id_card", return_value=cccd_result) as extract_id_card, \
             patch.object(CrmAiService, "extract_card") as extract_card:
            wizard.action_scan()

        extract_id_card.assert_called_once()
        extract_card.assert_not_called()
        self.assertEqual(wizard.state, "review")
        self.assertEqual(wizard.extracted_full_name, "Le Van C")
        self.assertEqual(wizard.extracted_date_of_birth.isoformat(), "1990-03-25")
        self.assertEqual(wizard.extracted_gender, "male")
        self.assertEqual(wizard.extracted_cccd_number, "012345678901")

    def test_apply_cccd_updates_partner_and_links_lead(self):
        lead = self._create_lead()
        wizard = self.env["crm.ai.scan.document"].create({
            "scan_type": "cccd_front",
            "lead_id": lead.id,
            "extracted_full_name": "Pham Thi D",
            "extracted_date_of_birth": "1992-02-20",
            "extracted_gender": "female",
            "extracted_address": "Da Nang",
            "extracted_cccd_number": "079092000001",
            "extracted_cccd_issue_date": "2021-05-15",
            "extracted_cccd_issue_place": "C06",
        })

        action = wizard.action_apply_to_lead()

        lead.invalidate_recordset(["partner_id"])
        partner = lead.partner_id
        self.assertTrue(partner.exists())
        self.assertEqual(partner.name, "Pham Thi D")
        self.assertEqual(partner.date_of_birth.isoformat(), "1992-02-20")
        self.assertEqual(partner.gender, "female")
        self.assertEqual(partner.street, "Da Nang")
        self.assertEqual(partner.cccd_number, "079092000001")
        self.assertEqual(partner.cccd_issue_date.isoformat(), "2021-05-15")
        self.assertEqual(partner.cccd_issue_place, "C06")
        self.assertEqual(lead.customer_type, "individual")
        self.assertEqual(action["res_model"], "crm.lead")
        self.assertEqual(wizard.state, "done")

    def test_cccd_number_is_restricted_to_system_group(self):
        self.assertEqual(
            self.env["res.partner"]._fields["cccd_number"].groups,
            "base.group_system",
        )
