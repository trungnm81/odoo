from odoo import SUPERUSER_ID, api


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if not (
        _column_exists(cr, 'crm_lead', 'customer_segment_id')
        and _column_exists(cr, 'res_partner', 'customer_segment_id')
    ):
        return

    cr.execute(
        """
        UPDATE res_partner partner
           SET customer_segment_id = lead.customer_segment_id,
               customer_type = COALESCE(partner.customer_type, lead.customer_type)
          FROM crm_lead lead
         WHERE lead.partner_id = partner.id
           AND lead.customer_segment_id IS NOT NULL
           AND partner.customer_segment_id IS NULL
        """
    )
    env['res.partner'].invalidate_model(['customer_segment_id', 'customer_type'])
