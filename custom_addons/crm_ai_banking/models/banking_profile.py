from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError


PRODUCT_CATEGORY_SELECTION = [
    ('deposit', 'Tiền gửi'),
    ('loan', 'Tín dụng'),
    ('card', 'Thẻ'),
    ('insurance', 'Bảo hiểm'),
    ('payment', 'Thanh toán'),
    ('trade', 'Tài trợ thương mại'),
    ('fx', 'Ngoại hối'),
    ('other', 'Khác'),
]


HOLDING_STATUS_SELECTION = [
    ('active', 'Đang hoạt động'),
    ('inactive', 'Không hoạt động'),
    ('closed', 'Đã đóng'),
]


def _can_write_banking_data(env):
    return (
        env.su
        or env.context.get('allow_corebanking_sync_write')
        or env.user.has_group('base.group_system')
        or env.user.has_group('crm_ai_banking.group_corebanking_integration')
    )


class BankingCoreMixin(models.AbstractModel):
    _name = 'crm.banking.core.mixin'
    _description = 'Banking Core Data Access Mixin'

    def _check_banking_write_access(self):
        if not _can_write_banking_data(self.env):
            raise AccessError(_('Chỉ nhóm Core Banking Integration hoặc quản trị hệ thống được cập nhật Banking 360.'))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_banking_write_access()
        return super().create(vals_list)

    def write(self, vals):
        self._check_banking_write_access()
        return super().write(vals)

    def unlink(self):
        self._check_banking_write_access()
        return super().unlink()


class CrmBankingCustomerProfile(models.Model):
    _name = 'crm.banking.customer.profile'
    _inherit = 'crm.banking.core.mixin'
    _description = 'Banking 360 Customer Profile'
    _order = 'corebanking_updated_at desc, id desc'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    total_deposit_balance = fields.Monetary(string='Tổng tiền gửi', currency_field='currency_id')
    total_loan_balance = fields.Monetary(string='Tổng dư nợ', currency_field='currency_id')
    total_aum = fields.Monetary(string='AUM / Tổng tài sản quản lý', currency_field='currency_id')
    total_limit = fields.Monetary(string='Tổng hạn mức', currency_field='currency_id')
    collateral_value = fields.Monetary(string='Giá trị tài sản bảo đảm', currency_field='currency_id')
    casa_balance = fields.Monetary(string='CASA balance', currency_field='currency_id')
    toi_mtd = fields.Monetary(string='TOI MTD', currency_field='currency_id')
    toi_ytd = fields.Monetary(string='TOI YTD', currency_field='currency_id')
    toi_12m = fields.Monetary(string='TOI 12M', currency_field='currency_id')
    cif_code = fields.Char(string='Mã CIF', index=True)
    customer_segment = fields.Char(string='Phân khúc KH')
    risk_score = fields.Float(string='Risk score')
    risk_grade = fields.Char(string='Risk grade')
    kyc_status = fields.Char(string='KYC status')
    risk_level = fields.Char(string='Risk level')
    branch_code = fields.Char(string='Mã chi nhánh')
    branch_name = fields.Char(string='Chi nhánh quản lý')
    rm_code = fields.Char(string='Mã RM')
    rm_name = fields.Char(string='RM quản lý')
    preferred_channel = fields.Char(string='Kênh ưa thích')
    digital_adoption_level = fields.Char(string='Mức digital adoption')
    raw_summary_json = fields.Text(string='Raw summary JSON')
    corebanking_updated_at = fields.Datetime(string='Core Banking cập nhật lúc', index=True)
    last_sync_date = fields.Datetime(string='Đồng bộ vào CRM lúc', default=fields.Datetime.now)

    _partner_unique = models.Constraint(
        'UNIQUE(partner_id)',
        'Mỗi Contact chỉ có một Banking 360 profile chung.',
    )


class CrmBankingIndividualProfile(models.Model):
    _name = 'crm.banking.individual.profile'
    _inherit = 'crm.banking.core.mixin'
    _description = 'Banking 360 Individual Profile'
    _order = 'corebanking_updated_at desc, id desc'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    marital_status = fields.Char(string='Tình trạng hôn nhân')
    dependent_count = fields.Integer(string='Số người phụ thuộc')
    residential_area = fields.Char(string='Khu vực cư trú')
    occupation = fields.Char(string='Nghề nghiệp')
    employer_name = fields.Char(string='Employer')
    job_title = fields.Char(string='Chức danh')
    monthly_income = fields.Monetary(string='Thu nhập tháng')
    income_source = fields.Char(string='Nguồn thu nhập')
    income_stability = fields.Char(string='Mức ổn định thu nhập')
    verified_income = fields.Monetary(string='Thu nhập xác minh')
    non_financial_json = fields.Text(string='Thông tin phi tài chính JSON')
    compliance_flags = fields.Char(string='Compliance flags')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    corebanking_updated_at = fields.Datetime(string='Core Banking cập nhật lúc', index=True)
    last_sync_date = fields.Datetime(string='Đồng bộ vào CRM lúc', default=fields.Datetime.now)

    _partner_unique = models.Constraint(
        'UNIQUE(partner_id)',
        'Mỗi Contact cá nhân chỉ có một profile cá nhân.',
    )

    @api.constrains('partner_id')
    def _check_partner_type(self):
        for rec in self:
            if rec.partner_id.customer_type and rec.partner_id.customer_type != 'individual':
                raise ValidationError(_('Individual profile chỉ áp dụng cho khách hàng cá nhân.'))


class CrmBankingBusinessProfile(models.Model):
    _name = 'crm.banking.business.profile'
    _inherit = 'crm.banking.core.mixin'
    _description = 'Banking 360 Business Profile'
    _order = 'corebanking_updated_at desc, id desc'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    tax_code = fields.Char(string='MST/GPKD')
    industry_code = fields.Char(string='Mã ngành')
    industry_name = fields.Char(string='Ngành nghề')
    legal_form = fields.Char(string='Loại hình doanh nghiệp')
    establishment_date = fields.Date(string='Ngày thành lập')
    employee_count = fields.Integer(string='Quy mô nhân sự')
    business_area = fields.Char(string='Địa bàn hoạt động')
    annual_revenue = fields.Monetary(string='Doanh thu năm')
    net_profit = fields.Monetary(string='Lợi nhuận')
    ebitda = fields.Monetary(string='EBITDA')
    total_assets = fields.Monetary(string='Tổng tài sản')
    equity = fields.Monetary(string='Vốn chủ sở hữu')
    cash_flow = fields.Monetary(string='Dòng tiền')
    approved_limit = fields.Monetary(string='Hạn mức cấp')
    used_limit = fields.Monetary(string='Hạn mức sử dụng')
    debt_group = fields.Char(string='Nhóm nợ')
    dscr = fields.Float(string='DSCR')
    avg_casa_balance = fields.Monetary(string='CASA bình quân')
    payment_volume = fields.Monetary(string='Doanh số thanh toán')
    payroll_volume = fields.Monetary(string='Payroll volume')
    lc_volume = fields.Monetary(string='LC volume')
    fx_volume = fields.Monetary(string='FX volume')
    trade_finance_volume = fields.Monetary(string='Trade finance volume')
    toi_deposit = fields.Monetary(string='TOI tiền gửi')
    toi_credit = fields.Monetary(string='TOI tín dụng')
    toi_fee = fields.Monetary(string='TOI phí dịch vụ')
    toi_fx_trade = fields.Monetary(string='TOI FX/Trade')
    ecosystem_json = fields.Text(string='Hệ sinh thái / phi tài chính JSON')
    management_json = fields.Text(string='Ban lãnh đạo / stakeholder JSON')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    corebanking_updated_at = fields.Datetime(string='Core Banking cập nhật lúc', index=True)
    last_sync_date = fields.Datetime(string='Đồng bộ vào CRM lúc', default=fields.Datetime.now)

    _partner_unique = models.Constraint(
        'UNIQUE(partner_id)',
        'Mỗi Contact doanh nghiệp chỉ có một profile doanh nghiệp.',
    )

    @api.constrains('partner_id')
    def _check_partner_type(self):
        for rec in self:
            if rec.partner_id.customer_type and rec.partner_id.customer_type != 'business':
                raise ValidationError(_('Business profile chỉ áp dụng cho khách hàng doanh nghiệp.'))


class CrmBankingProductHolding(models.Model):
    _name = 'crm.banking.product.holding'
    _inherit = 'crm.banking.core.mixin'
    _description = 'Banking 360 Product Holding'
    _order = 'partner_id, product_category, product_name'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    source_system = fields.Char(default='corebanking', required=True, index=True)
    source_ref = fields.Char(string='Mã tham chiếu Core', required=True, index=True)
    masked_account_number = fields.Char(string='Số tài khoản/HĐ masked')
    product_code = fields.Char(string='Mã sản phẩm', index=True)
    product_name = fields.Char(string='Tên sản phẩm')
    product_category = fields.Selection(PRODUCT_CATEGORY_SELECTION, string='Nhóm sản phẩm', default='other')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    current_balance = fields.Monetary(string='Số dư hiện tại', currency_field='currency_id')
    outstanding_balance = fields.Monetary(string='Dư nợ', currency_field='currency_id')
    credit_limit = fields.Monetary(string='Hạn mức', currency_field='currency_id')
    toi_mtd = fields.Monetary(string='TOI MTD', currency_field='currency_id')
    toi_ytd = fields.Monetary(string='TOI YTD', currency_field='currency_id')
    toi_12m = fields.Monetary(string='TOI 12M', currency_field='currency_id')
    open_date = fields.Date(string='Ngày mở')
    maturity_date = fields.Date(string='Ngày đáo hạn')
    status = fields.Selection(HOLDING_STATUS_SELECTION, string='Trạng thái', default='active', index=True)
    raw_holding_json = fields.Text(string='Raw holding JSON')
    corebanking_updated_at = fields.Datetime(string='Core Banking cập nhật lúc', index=True)
    last_sync_date = fields.Datetime(string='Đồng bộ vào CRM lúc', default=fields.Datetime.now)

    _partner_source_ref_unique = models.Constraint(
        'UNIQUE(partner_id, source_system, source_ref)',
        'Mỗi sản phẩm/tài khoản Core Banking chỉ được lưu một lần cho mỗi Contact.',
    )
