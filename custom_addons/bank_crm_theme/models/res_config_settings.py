from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Tabs ẩn trên mobile ──────────────────────────────────
    mobile_hide_account_map = fields.Boolean(
        string='Account Map B2B',
        config_parameter='bank_crm.mobile_hide_account_map',
        default=True,
    )
    mobile_hide_ai_documents = fields.Boolean(
        string='Tài liệu AI',
        config_parameter='bank_crm.mobile_hide_ai_documents',
        default=True,
    )
    mobile_hide_product_recs = fields.Boolean(
        string='Sản phẩm phù hợp',
        config_parameter='bank_crm.mobile_hide_product_recs',
        default=True,
    )

    # ── Nút header ẩn trên mobile ────────────────────────────
    mobile_hide_btn_scan_card = fields.Boolean(
        string='Quét Card',
        config_parameter='bank_crm.mobile_hide_btn_scan_card',
        default=True,
    )
    mobile_hide_btn_scan_gpkd = fields.Boolean(
        string='Quét GPKD',
        config_parameter='bank_crm.mobile_hide_btn_scan_gpkd',
        default=True,
    )
    mobile_hide_btn_proposal = fields.Boolean(
        string='Sinh đề xuất',
        config_parameter='bank_crm.mobile_hide_btn_proposal',
        default=True,
    )
    mobile_hide_btn_zalo_remind = fields.Boolean(
        string='Nhắc hồ sơ Zalo',
        config_parameter='bank_crm.mobile_hide_btn_zalo_remind',
        default=True,
    )
