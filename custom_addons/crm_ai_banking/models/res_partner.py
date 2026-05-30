from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError

from .crm_customer_segment import CUSTOMER_TYPE_SELECTION


COREBANKING_FIELDS = {
    'bank_cif',
    'customer_segment_id',
    'corebanking_segment_code',
    'corebanking_customer_status',
    'corebanking_last_sync_date',
    'corebanking_sync_status',
    'corebanking_sync_message',
    'banking_profile_ids',
    'banking_individual_profile_ids',
    'banking_business_profile_ids',
    'banking_product_holding_ids',
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── CCCD / ID Card fields ─────────────────────────────────────────────────
    cccd_number = fields.Char(string='Số CCCD / CMND', groups='base.group_system')
    cccd_issue_date = fields.Date(string='Ngày cấp CCCD')
    cccd_issue_place = fields.Char(string='Nơi cấp CCCD')
    date_of_birth = fields.Date(string='Ngày sinh')
    gender = fields.Selection(
        [('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')],
        string='Giới tính',
    )

    # ── Zalo ─────────────────────────────────────────────────────────────────
    zalo_user_id = fields.Char(string='Zalo User ID', index=True)

    # ── Core Banking master data ─────────────────────────────────────────────
    bank_cif = fields.Char(
        string='Mã CIF',
        copy=False,
        index=True,
        groups='base.group_system,crm_ai_banking.group_corebanking_integration',
    )
    customer_type = fields.Selection(
        CUSTOMER_TYPE_SELECTION,
        string='Loại khách hàng',
        index=True,
    )
    customer_segment_id = fields.Many2one(
        'crm.customer.segment',
        string='Customer Segment',
        domain="[('customer_type', '=', customer_type)]",
        index=True,
        copy=False,
    )
    corebanking_segment_code = fields.Char(
        string='Mã segment Core Banking',
        copy=False,
        index=True,
    )
    corebanking_customer_status = fields.Char(
        string='Trạng thái Core Banking',
        copy=False,
    )
    corebanking_last_sync_date = fields.Datetime(
        string='Lần đồng bộ Core Banking cuối',
        copy=False,
    )
    corebanking_sync_status = fields.Selection(
        [
            ('never', 'Chưa đồng bộ'),
            ('done', 'Đã đồng bộ'),
            ('warning', 'Cảnh báo'),
            ('error', 'Lỗi'),
        ],
        string='Trạng thái đồng bộ',
        default='never',
        copy=False,
    )
    corebanking_sync_message = fields.Text(
        string='Ghi chú đồng bộ Core Banking',
        copy=False,
    )
    banking_profile_ids = fields.One2many(
        'crm.banking.customer.profile',
        'partner_id',
        string='Banking 360 profile',
        readonly=True,
    )
    banking_individual_profile_ids = fields.One2many(
        'crm.banking.individual.profile',
        'partner_id',
        string='Thông tin cá nhân Banking 360',
        readonly=True,
    )
    banking_business_profile_ids = fields.One2many(
        'crm.banking.business.profile',
        'partner_id',
        string='Thông tin doanh nghiệp Banking 360',
        readonly=True,
    )
    banking_product_holding_ids = fields.One2many(
        'crm.banking.product.holding',
        'partner_id',
        string='Sản phẩm đang sử dụng',
        readonly=True,
    )

    _bank_cif_unique = models.Constraint(
        'UNIQUE(bank_cif)',
        'Mã CIF phải là duy nhất.',
    )

    @staticmethod
    def _customer_type_from_is_company(is_company):
        return 'business' if is_company else 'individual'

    def _can_write_corebanking_fields(self):
        return (
            self.env.su
            or self.env.context.get('allow_corebanking_sync_write')
            or self.env.user.has_group('base.group_system')
            or self.env.user.has_group('crm_ai_banking.group_corebanking_integration')
        )

    def _check_corebanking_write_access(self, vals):
        if COREBANKING_FIELDS.intersection(vals) and not self._can_write_corebanking_fields():
            raise AccessError(_('Chỉ nhóm Core Banking Integration hoặc quản trị hệ thống được cập nhật CIF/segment.'))

    @api.onchange('is_company')
    def _onchange_is_company_customer_type(self):
        for partner in self:
            partner.customer_type = self._customer_type_from_is_company(partner.is_company)

    @api.onchange('customer_type')
    def _onchange_customer_type(self):
        for partner in self:
            if partner.customer_type:
                partner.is_company = partner.customer_type == 'business'
            if partner.customer_segment_id and partner.customer_segment_id.customer_type != partner.customer_type:
                partner.customer_segment_id = False

    @api.constrains('customer_type', 'customer_segment_id')
    def _check_customer_segment_matches_type(self):
        for partner in self:
            if partner.customer_segment_id and partner.customer_segment_id.customer_type != partner.customer_type:
                raise ValidationError(_('Customer Segment phải thuộc đúng Loại khách hàng.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_corebanking_write_access(vals)
            if vals.get('customer_segment_id') and not vals.get('customer_type'):
                segment = self.env['crm.customer.segment'].browse(vals['customer_segment_id'])
                vals['customer_type'] = segment.customer_type
            if 'is_company' in vals and not vals.get('customer_type'):
                vals['customer_type'] = self._customer_type_from_is_company(vals.get('is_company'))
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._check_corebanking_write_access(vals)
        if 'is_company' in vals and 'customer_type' not in vals:
            vals['customer_type'] = self._customer_type_from_is_company(vals.get('is_company'))
        if 'customer_type' in vals and 'customer_segment_id' not in vals:
            if any(
                partner.customer_segment_id
                and partner.customer_segment_id.customer_type != vals['customer_type']
                for partner in self
            ):
                vals['customer_segment_id'] = False
        return super().write(vals)
