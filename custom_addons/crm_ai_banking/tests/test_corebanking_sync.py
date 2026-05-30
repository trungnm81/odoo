import json
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService


@tagged("crm_ai_banking_corebanking", "post_install", "-at_install")
class TestCorebankingSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.individual_segment = cls.env.ref('crm_ai_banking.customer_segment_individual_vip')
        cls.business_segment = cls.env.ref('crm_ai_banking.customer_segment_business_sme')
        cls.sales_user = new_test_user(
            cls.env,
            login='corebanking_sales_user',
            groups='base.group_user',
            name='Core Banking Sales User',
        )

    def test_sales_user_cannot_write_cif_or_segment(self):
        partner = self.env['res.partner'].create({'name': 'Restricted Customer'})

        with self.assertRaises(AccessError):
            partner.with_user(self.sales_user).write({'bank_cif': 'CIF-001'})

        with self.assertRaises(AccessError):
            partner.with_user(self.sales_user).write({'customer_segment_id': self.individual_segment.id})

    def test_convert_individual_lead_creates_individual_partner_without_cif_or_segment(self):
        lead = self.env['crm.lead'].create({
            'name': 'Individual Lead',
            'contact_name': 'Nguyen Van A',
            'customer_type': 'individual',
            'type': 'lead',
        })

        partner = lead._create_customer()

        self.assertFalse(partner.is_company)
        self.assertEqual(partner.customer_type, 'individual')
        self.assertFalse(partner.bank_cif)
        self.assertFalse(partner.customer_segment_id)

    def test_convert_business_lead_returns_company_partner(self):
        lead = self.env['crm.lead'].create({
            'name': 'Business Lead',
            'partner_name': 'ABC Company',
            'contact_name': 'Tran Thi B',
            'customer_type': 'business',
            'type': 'lead',
        })

        partner = lead._create_customer()

        self.assertTrue(partner.is_company)
        self.assertEqual(partner.name, 'ABC Company')
        self.assertEqual(partner.customer_type, 'business')
        self.assertEqual(
            self.env['res.partner'].search_count([('parent_id', '=', partner.id), ('name', '=', 'Tran Thi B')]),
            1,
        )
        self.assertFalse(partner.bank_cif)
        self.assertFalse(partner.customer_segment_id)

    def test_corebanking_staging_upserts_by_cif_and_maps_segment(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Existing Customer',
            'bank_cif': 'CIF-100',
            'customer_type': 'individual',
        })
        batch = self.env['crm.corebanking.customer.batch'].create({
            'name': 'Daily Batch',
            'sync_type': 'daily',
        })
        line = self.env['crm.corebanking.customer.staging'].create({
            'batch_id': batch.id,
            'cif': 'CIF-100',
            'customer_name': 'Core Name',
            'customer_type': 'individual',
            'segment_code': self.individual_segment.code,
            'customer_status': 'ACTIVE',
        })

        line.action_process()

        self.assertEqual(line.state, 'done')
        self.assertEqual(line.partner_id, partner)
        self.assertEqual(line.action_taken, 'updated')
        self.assertEqual(partner.customer_segment_id, self.individual_segment)
        self.assertEqual(partner.corebanking_customer_status, 'ACTIVE')

    def test_corebanking_staging_unmapped_segment_keeps_code_without_segment(self):
        batch = self.env['crm.corebanking.customer.batch'].create({
            'name': 'Create Batch',
            'sync_type': 'init',
            'allow_create_partner': True,
        })
        line = self.env['crm.corebanking.customer.staging'].create({
            'batch_id': batch.id,
            'cif': 'CIF-200',
            'customer_name': 'Missing Segment Customer',
            'customer_type': 'business',
            'segment_code': 'UNKNOWN-SEG',
        })

        line.action_process()

        self.assertEqual(line.state, 'done')
        self.assertEqual(line.action_taken, 'unmapped_segment')
        self.assertEqual(line.partner_id.bank_cif, 'CIF-200')
        self.assertEqual(line.partner_id.corebanking_segment_code, 'UNKNOWN-SEG')
        self.assertFalse(line.partner_id.customer_segment_id)
        self.assertEqual(line.partner_id.corebanking_sync_status, 'warning')

    def test_segment_must_match_partner_customer_type(self):
        partner = self.env['res.partner'].create({
            'name': 'Individual Customer',
            'customer_type': 'individual',
        })

        with self.assertRaises(ValidationError):
            partner.with_context(allow_corebanking_sync_write=True).write({
                'customer_segment_id': self.business_segment.id,
            })

    def test_profile_staging_creates_individual_profile_only(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Individual CIF Customer',
            'bank_cif': 'CIF-IND-PROFILE',
            'customer_type': 'individual',
        })
        batch = self.env['crm.corebanking.customer.batch'].create({
            'name': 'Individual Profile Batch',
            'sync_type': 'daily',
        })
        line = self.env['crm.corebanking.customer.staging'].create({
            'batch_id': batch.id,
            'record_type': 'customer_profile',
            'cif': 'CIF-IND-PROFILE',
            'customer_type': 'individual',
            'total_deposit_balance': 500000000,
            'total_loan_balance': 100000000,
            'toi_12m': 12000000,
            'occupation': 'Engineer',
            'monthly_income': 45000000,
            'verified_income': 43000000,
            'preferred_channel': 'Mobile Banking',
        })

        line.action_process()

        self.assertEqual(line.state, 'done')
        self.assertEqual(line.action_taken, 'profile_updated')
        self.assertEqual(partner.banking_profile_ids.total_deposit_balance, 500000000)
        self.assertEqual(partner.banking_individual_profile_ids.occupation, 'Engineer')
        self.assertFalse(partner.banking_business_profile_ids)

    def test_profile_staging_creates_business_profile_only(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Business CIF Customer',
            'bank_cif': 'CIF-BIZ-PROFILE',
            'customer_type': 'business',
            'is_company': True,
        })
        batch = self.env['crm.corebanking.customer.batch'].create({
            'name': 'Business Profile Batch',
            'sync_type': 'daily',
        })
        line = self.env['crm.corebanking.customer.staging'].create({
            'batch_id': batch.id,
            'record_type': 'customer_profile',
            'cif': 'CIF-BIZ-PROFILE',
            'customer_type': 'business',
            'total_deposit_balance': 2000000000,
            'total_loan_balance': 900000000,
            'toi_ytd': 70000000,
            'industry_name': 'Manufacturing',
            'annual_revenue': 25000000000,
            'approved_limit': 3000000000,
            'debt_group': '1',
        })

        line.action_process()

        self.assertEqual(line.state, 'done')
        self.assertEqual(partner.banking_profile_ids.toi_ytd, 70000000)
        self.assertEqual(partner.banking_business_profile_ids.industry_name, 'Manufacturing')
        self.assertEqual(partner.banking_business_profile_ids.annual_revenue, 25000000000)
        self.assertFalse(partner.banking_individual_profile_ids)

    def test_product_holding_staging_is_idempotent_by_source_ref(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Holding Customer',
            'bank_cif': 'CIF-HOLDING',
            'customer_type': 'individual',
        })
        batch = self.env['crm.corebanking.customer.batch'].create({
            'name': 'Holding Batch',
            'sync_type': 'daily',
        })
        vals = {
            'batch_id': batch.id,
            'record_type': 'product_holding',
            'cif': 'CIF-HOLDING',
            'source_ref': 'ACC-001',
            'product_code': 'CASA',
            'product_name': 'Current Account',
            'product_category': 'deposit',
            'current_balance': 10000000,
        }
        line = self.env['crm.corebanking.customer.staging'].create(vals)
        line.action_process()
        holding = partner.banking_product_holding_ids
        self.assertEqual(len(holding), 1)
        self.assertEqual(holding.current_balance, 10000000)

        line.write({'current_balance': 15000000})
        line.action_process()

        self.assertEqual(len(partner.banking_product_holding_ids), 1)
        self.assertEqual(partner.banking_product_holding_ids.current_balance, 15000000)

    def test_opportunity_reads_banking_360_from_linked_partner(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Opportunity Banking Customer',
            'bank_cif': 'CIF-OPP-360',
            'customer_type': 'individual',
        })
        profile = self.env['crm.banking.customer.profile'].with_context(allow_corebanking_sync_write=True).create({
            'partner_id': partner.id,
            'total_deposit_balance': 120000000,
            'toi_ytd': 9000000,
        })
        individual_profile = self.env['crm.banking.individual.profile'].with_context(
            allow_corebanking_sync_write=True,
        ).create({
            'partner_id': partner.id,
            'occupation': 'Relationship Manager',
            'monthly_income': 55000000,
        })
        holding = self.env['crm.banking.product.holding'].with_context(allow_corebanking_sync_write=True).create({
            'partner_id': partner.id,
            'source_ref': 'CASA-OPP-001',
            'product_code': 'CASA',
            'product_name': 'Current Account',
            'product_category': 'deposit',
            'current_balance': 25000000,
            'status': 'active',
        })
        lead = self.env['crm.lead'].create({
            'name': 'Opportunity Banking 360',
            'partner_id': partner.id,
            'type': 'opportunity',
        })

        self.assertEqual(lead.banking_profile_ids, profile)
        self.assertEqual(lead.banking_individual_profile_ids, individual_profile)
        self.assertFalse(lead.banking_business_profile_ids)
        self.assertEqual(lead.banking_product_holding_ids, holding)

    def test_product_recommendation_excludes_existing_holdings(self):
        partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True).create({
            'name': 'Recommendation Customer',
            'bank_cif': 'CIF-REC',
            'customer_type': 'individual',
        })
        self.env['crm.banking.product.holding'].with_context(allow_corebanking_sync_write=True).create({
            'partner_id': partner.id,
            'source_ref': 'CARD-001',
            'product_code': 'CARD',
            'product_name': 'Existing Credit Card',
            'product_category': 'card',
            'status': 'active',
        })
        self.env['crm.product.eligibility.rule'].create({
            'product_code': 'CARD',
            'product_name': 'Credit Card',
            'product_category': 'card',
            'active': True,
        })
        self.env['crm.product.eligibility.rule'].create({
            'product_code': 'LOAN',
            'product_name': 'Personal Loan',
            'product_category': 'credit',
            'active': True,
        })
        lead = self.env['crm.lead'].create({
            'name': 'Recommendation Lead',
            'partner_id': partner.id,
            'type': 'opportunity',
        })

        def _score_products(_service, eligible, _ctx):
            return [
                {
                    'product_code': item['product_code'],
                    'product_name': item['product_name'],
                    'match_score': 0.8,
                    'match_reasons': ['Eligible'],
                    'approach_suggestion': '',
                }
                for item in eligible
            ]

        with patch.object(CrmAiService, 'score_products', autospec=True, side_effect=_score_products):
            lead._ai_run_product_recommendations()

        recommendations = json.loads(lead.product_recommendation_ids[:1].recommendations_json)
        self.assertNotIn('CARD', [item['product_code'] for item in recommendations])
        self.assertIn('LOAN', [item['product_code'] for item in recommendations])
