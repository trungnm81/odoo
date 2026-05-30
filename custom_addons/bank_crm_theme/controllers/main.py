from odoo import http
from odoo.http import request


class BankCrmThemeController(http.Controller):

    @http.route('/bank_crm_theme/mobile_config', type='json', auth='user')
    def mobile_config(self):
        ICP = request.env['ir.config.parameter'].sudo()

        def get_bool(key, default='True'):
            return ICP.get_param(key, default) == 'True'

        return {
            'mobile_hide_account_map':    get_bool('bank_crm.mobile_hide_account_map'),
            'mobile_hide_ai_documents':   get_bool('bank_crm.mobile_hide_ai_documents'),
            'mobile_hide_product_recs':   get_bool('bank_crm.mobile_hide_product_recs'),
            'mobile_hide_btn_scan_card':  get_bool('bank_crm.mobile_hide_btn_scan_card'),
            'mobile_hide_btn_scan_gpkd':  get_bool('bank_crm.mobile_hide_btn_scan_gpkd'),
            'mobile_hide_btn_proposal':   get_bool('bank_crm.mobile_hide_btn_proposal'),
            'mobile_hide_btn_zalo_remind':get_bool('bank_crm.mobile_hide_btn_zalo_remind'),
        }
