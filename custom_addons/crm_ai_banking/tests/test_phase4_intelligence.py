import json
from unittest.mock import patch

from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_phase4", "post_install", "-at_install")
class TestPhase4Intelligence(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.ai.config"].sudo().search([]).write({"active": False})
        cls.env["crm.ai.config"].sudo().create({
            "name": "Phase 4 Test Config",
            "active": True,
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-openrouter",
        })
        cls.sales_user = new_test_user(
            cls.env,
            login="phase4_sales",
            groups="base.group_user",
            name="Phase 4 Sales",
            email="phase4_sales@example.com",
        )

    def _create_partner(self, **values):
        vals = {
            "name": "Phase 4 Partner",
            "phone": "0909000000",
            "date_of_birth": "1990-01-01",
        }
        vals.update(values)
        return self.env["res.partner"].create(vals)

    def _create_lead(self, **values):
        partner = values.pop("partner_id", None) or self._create_partner()
        vals = {
            "name": "Phase 4 Lead",
            "type": "opportunity",
            "partner_id": partner.id,
            "user_id": self.sales_user.id,
            "product_type": "vay_mua_nha",
            "expected_revenue": 2000000000,
            "ai_detected_needs_json": json.dumps(["loan"]),
            "ai_last_sentiment": "positive",
        }
        vals.update(values)
        return self.env["crm.lead"].create(vals)

    def test_action_compute_nba_schedules_async_worker(self):
        lead = self._create_lead()

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            action = lead.action_compute_nba()

        self.assertEqual(action["tag"], "display_notification")
        trigger_async.assert_called_once()
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_run_nba")
        self.assertEqual(kwargs["args"], ())

    def test_ai_run_nba_writes_validated_fields_and_resets_dismissal(self):
        lead = self._create_lead(nba_dismissed=True)
        result = {
            "action_type": "send_zalo",
            "action_detail": "Send follow-up offer",
            "urgency": "urgent",
            "reasoning": "Customer is warm",
            "suggested_message": "Anh chi can them thong tin nao khong?",
            "confidence": 1.4,
        }

        with patch.object(CrmAiService, "compute_next_best_action", return_value=result):
            lead._ai_run_nba()

        self.assertEqual(lead.nba_action_type, "send_zalo")
        self.assertEqual(lead.nba_action_detail, "Send follow-up offer")
        self.assertEqual(lead.nba_urgency, "medium")
        self.assertEqual(lead.nba_reasoning, "Customer is warm")
        self.assertEqual(lead.nba_suggested_message, "Anh chi can them thong tin nao khong?")
        self.assertEqual(lead.nba_confidence, 1.0)
        self.assertTrue(lead.nba_computed_date)
        self.assertFalse(lead.nba_dismissed)

    def test_ai_run_nba_rejects_unknown_action_type(self):
        lead = self._create_lead()

        with patch.object(CrmAiService, "compute_next_best_action", return_value={
            "action_type": "unknown_action",
            "action_detail": "Invalid action",
            "urgency": "high",
            "confidence": 0.7,
        }):
            lead._ai_run_nba()

        self.assertFalse(lead.nba_action_type)
        self.assertEqual(lead.nba_urgency, "high")
        self.assertEqual(lead.nba_confidence, 0.7)

    def test_action_dismiss_nba_sets_flag(self):
        lead = self._create_lead(nba_dismissed=False)

        lead.action_dismiss_nba()

        self.assertTrue(lead.nba_dismissed)

    def test_product_eligibility_rule_filters_by_customer_age(self):
        adult = self._create_partner(name="Adult", date_of_birth="1990-01-01")
        too_young = self._create_partner(name="Young", date_of_birth="2015-01-01")
        rule = self.env["crm.product.eligibility.rule"].create({
            "product_code": "CARD-GOLD",
            "product_name": "Gold Card",
            "product_category": "card",
            "product_type": "the_tin_dung",
            "min_age": 21,
            "max_age": 65,
        })

        self.assertTrue(rule.check_eligibility(adult))
        self.assertFalse(rule.check_eligibility(too_young))

    def test_action_ai_product_recommendations_schedules_async_worker(self):
        lead = self._create_lead()

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            action = lead.action_ai_product_recommendations()

        self.assertEqual(action["tag"], "display_notification")
        trigger_async.assert_called_once()
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_run_product_recommendations")
        self.assertEqual(kwargs["args"], ())

    def test_ai_product_recommendations_creates_ranked_record_and_note(self):
        lead = self._create_lead()
        self.env["crm.product.eligibility.rule"].create({
            "product_code": "PAYROLL",
            "product_name": "Payroll",
            "product_category": "payment",
            "product_type": "payroll",
            "description": "Salary payment package",
            "min_age": 18,
            "max_age": 70,
        })
        ranked = [{
            "product_code": "PAYROLL",
            "product_name": "Payroll",
            "match_score": 0.91,
            "match_reasons": ["Company salary payment potential"],
            "approach_suggestion": "Ask about payroll process",
        }]

        with patch.object(CrmAiService, "score_products", return_value=ranked) as score_products:
            lead._ai_run_product_recommendations()

        score_products.assert_called_once()
        recommendation = lead.product_recommendation_ids[:1]
        self.assertTrue(recommendation)
        self.assertEqual(recommendation.top_product_name, "Payroll")
        self.assertEqual(recommendation.top_match_score, 91)
        self.assertIn("Company salary", recommendation.recommendations_json)
        self.assertTrue(self.env["mail.message"].search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("body", "ilike", "Payroll"),
        ], limit=1))

    def test_product_recommendations_fall_back_to_rules_when_ai_returns_empty(self):
        lead = self._create_lead()
        self.env["crm.product.eligibility.rule"].create({
            "product_code": "SAVE",
            "product_name": "Savings Account",
            "product_category": "savings",
            "product_type": "tiet_kiem",
            "min_age": 18,
            "max_age": 70,
        })

        with patch.object(CrmAiService, "score_products", return_value=[]):
            lead._ai_run_product_recommendations()

        recommendation = lead.product_recommendation_ids[:1]
        self.assertEqual(recommendation.top_product_name, "Savings Account")
        self.assertEqual(recommendation.top_match_score, 50)
        self.assertIn('"match_score": 0.5', recommendation.recommendations_json)

    def test_product_recommendation_html_renders_only_top_three_items(self):
        items = [
            {"product_name": "Product 1", "match_score": 0.9, "match_reasons": ["R1"]},
            {"product_name": "Product 2", "match_score": 0.8, "match_reasons": ["R2"]},
            {"product_name": "Product 3", "match_score": 0.7, "match_reasons": ["R3"]},
            {"product_name": "Product 4", "match_score": 0.6, "match_reasons": ["R4"]},
        ]
        recommendation = self.env["crm.product.recommendation"].create({
            "lead_id": self._create_lead().id,
            "recommendations_json": json.dumps(items),
        })

        html = str(recommendation.recommendations_html)
        self.assertIn("Product 1", html)
        self.assertIn("Product 3", html)
        self.assertNotIn("Product 4", html)

    def test_call_session_action_create_coaching_report(self):
        lead = self._create_lead()
        session = self.env["crm.ai.call.session"].create({
            "lead_id": lead.id,
            "session_type": "call",
            "user_id": self.sales_user.id,
        })

        action = session.action_create_coaching_report()
        report = self.env["crm.ai.coaching.report"].browse(action["res_id"])

        self.assertTrue(report.exists())
        self.assertEqual(action["res_model"], "crm.ai.coaching.report")
        self.assertEqual(report.call_session_id, session)
        self.assertEqual(report.user_id, self.sales_user)

    def test_coaching_report_overall_score_averages_non_zero_scores(self):
        session = self.env["crm.ai.call.session"].create({
            "lead_id": self._create_lead().id,
            "session_type": "call",
            "user_id": self.sales_user.id,
        })
        report = self.env["crm.ai.coaching.report"].create({
            "call_session_id": session.id,
            "user_id": self.sales_user.id,
            "score_opening": 8,
            "score_needs_discovery": 6,
            "score_product_fit": 0,
            "score_objection": 7,
            "score_closing": 5,
        })

        self.assertEqual(report.score_overall, 6.5)

    def test_coaching_report_do_generate_uses_transcript_and_writes_scores(self):
        lead = self._create_lead(product_type="the_tin_dung")
        session = self.env["crm.ai.call.session"].create({
            "lead_id": lead.id,
            "session_type": "call",
            "user_id": self.sales_user.id,
        })
        self.env["crm.ai.transcript.line"].create({
            "session_id": session.id,
            "sequence": 1,
            "speaker": "agent",
            "text": "Em chao anh, em co the ho tro nhu cau the tin dung.",
            "is_final": True,
        })
        report = self.env["crm.ai.coaching.report"].create({
            "call_session_id": session.id,
            "user_id": self.sales_user.id,
        })
        result = {
            "scores": {
                "opening": 8,
                "needs_discovery": 7,
                "product_fit": 8,
                "objection": 6,
                "closing": 5,
            },
            "strengths": ["Clear opening"],
            "improvements": [{"text": "Ask more questions", "feedback": "Use open-ended questions"}],
            "missed_opportunities": ["Did not ask income"],
            "key_moments": [{"speaker": "agent", "text": "Em chao anh", "type": "strength"}],
        }

        with patch.object(CrmAiService, "analyze_call_coaching", return_value=result) as analyze:
            report._do_generate()

        analyze.assert_called_once()
        self.assertIn("[AGENT]", analyze.call_args.args[0])
        self.assertEqual(analyze.call_args.args[1], "the_tin_dung")
        self.assertEqual(report.processing_status, "done")
        self.assertEqual(report.score_overall, 6.8)
        self.assertIn("Clear opening", report.strengths_json)

    def test_coaching_report_without_transcript_moves_to_error(self):
        session = self.env["crm.ai.call.session"].create({
            "lead_id": self._create_lead().id,
            "session_type": "call",
            "user_id": self.sales_user.id,
        })
        report = self.env["crm.ai.coaching.report"].create({
            "call_session_id": session.id,
            "user_id": self.sales_user.id,
        })

        report._do_generate()

        self.assertEqual(report.processing_status, "error")

    def test_action_refresh_customer_360_schedules_async_worker(self):
        lead = self._create_lead()

        with patch.object(type(self.env["crm.lead"]), "_trigger_async", autospec=True) as trigger_async:
            action = lead.action_refresh_customer_360()

        self.assertEqual(action["tag"], "display_notification")
        args, kwargs = trigger_async.call_args
        self.assertEqual(args[1], lead.id)
        self.assertEqual(args[2], "_ai_run_customer_360")
        self.assertEqual(kwargs["args"], ())

    def test_ai_run_customer_360_writes_json_and_update_date(self):
        lead = self._create_lead()
        lead.message_post(body="Customer asked about interest rate", message_type="comment")
        result = {
            "profile_snapshot": "Warm mortgage prospect",
            "relationship_history": "One prior call and one chat",
            "current_status": "Needs rate follow-up",
            "key_needs": ["home loan"],
            "concerns_objections": ["interest rate"],
            "opportunities": ["insurance"],
            "recommended_approach": "Send personalized mortgage proposal",
        }

        with patch.object(CrmAiService, "generate_customer_360", return_value=result) as generate_360:
            lead._ai_run_customer_360()

        generate_360.assert_called_once()
        payload = generate_360.call_args.args[0]
        self.assertEqual(payload["lead_name"], lead.name)
        self.assertEqual(payload["partner_name"], lead.partner_id.name)
        self.assertIn("Customer asked", payload["recent_messages"][0]["body"])
        self.assertTrue(lead.customer_360_date)
        self.assertIn("Warm mortgage prospect", lead.customer_360_json)

    def test_customer_360_html_escapes_rendered_content(self):
        lead = self._create_lead()
        lead.customer_360_json = json.dumps({
            "profile_snapshot": "<script>alert(1)</script>",
            "key_needs": ["loan"],
            "recommended_approach": "Call back",
        })

        html = str(lead.customer_360_html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
