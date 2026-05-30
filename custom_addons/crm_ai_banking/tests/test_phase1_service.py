from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.crm_ai_banking.controllers.twilio_voice import TwilioVoiceController
from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase1", "post_install", "-at_install")
class TestPhase1Service(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.config = cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 1 Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
            "whisper_api_key": "test-whisper",
            "deepgram_api_key": "test-deepgram",
        })

    def test_safe_format_keeps_prompt_stable_with_braces(self):
        prompt = CrmAiService._safe_format(
            "Subject: {subject}\nBody: {body}",
            subject="Need {loan} quote",
            body='{"amount": 1000000}',
        )

        self.assertIn("Need (loan) quote", prompt)
        self.assertIn('("amount": 1000000)', prompt)
        self.assertNotIn("{subject}", prompt)
        self.assertNotIn("{body}", prompt)

    def test_anonymize_masks_sensitive_numbers(self):
        text = "CCCD 012345678901, MST 0312345678, account 1234567890123456"

        masked = CrmAiService.anonymize(text)

        self.assertIn("[ID_NUMBER]", masked)
        self.assertIn("[TAX_ID]", masked)
        self.assertIn("[ACCOUNT_NO]", masked)
        self.assertNotIn("012345678901", masked)
        self.assertNotIn("0312345678", masked)
        self.assertNotIn("1234567890123456", masked)

    def test_summarize_email_routes_to_llm_and_parses_json(self):
        service = CrmAiService(self.env)
        raw = (
            '{"summary_bullets":["Customer asks for rate"],'
            '"intent":"pricing_inquiry","urgency":"medium",'
            '"detected_needs":["loan"],"suggested_action":"Send quote"}'
        )

        with patch.object(CrmAiService, "_claude", return_value=raw) as claude:
            result = service.summarize_email("I need a loan rate", "Loan")

        claude.assert_called_once()
        self.assertEqual(result["intent"], "pricing_inquiry")
        self.assertEqual(result["detected_needs"], ["loan"])

    def test_twilio_phone_normalization_for_vietnam_numbers(self):
        self.assertEqual(TwilioVoiceController._normalize_phone("0983 511 981"), "+84983511981")
        self.assertEqual(TwilioVoiceController._normalize_phone("+840983511981"), "+84983511981")
        self.assertEqual(TwilioVoiceController._normalize_phone("+84983511981"), "+84983511981")
