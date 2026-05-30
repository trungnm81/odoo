import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from .crm_customer_segment import CUSTOMER_TYPE_SELECTION
from .banking_profile import PRODUCT_CATEGORY_SELECTION, HOLDING_STATUS_SELECTION


STAGING_RECORD_TYPE_SELECTION = [
    ('customer_master', 'Customer Master'),
    ('customer_profile', 'Customer Profile'),
    ('product_holding', 'Product Holding'),
]


class CrmCorebankingCustomerBatch(models.Model):
    _name = 'crm.corebanking.customer.batch'
    _description = 'Core Banking Customer Sync Batch'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, default=lambda self: _('Core Banking Sync'))
    sync_type = fields.Selection(
        [
            ('init', 'Init Sync'),
            ('daily', 'Daily Delta'),
            ('manual', 'Manual'),
        ],
        string='Loại đồng bộ',
        required=True,
        default='daily',
    )
    source_ref = fields.Char(string='Nguồn / Batch ID')
    allow_create_partner = fields.Boolean(
        string='Cho phép tạo Contact mới',
        help='Nếu tắt, CIF chưa match Contact sẽ ở trạng thái cần kiểm tra thủ công.',
    )
    line_ids = fields.One2many('crm.corebanking.customer.staging', 'batch_id', string='Dòng staging')
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('processing', 'Đang xử lý'),
            ('done', 'Hoàn thành'),
            ('partial', 'Hoàn thành có lỗi'),
        ],
        default='draft',
        string='Trạng thái',
        readonly=True,
    )
    started_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    total_count = fields.Integer(compute='_compute_counts', store=True)
    created_count = fields.Integer(compute='_compute_counts', store=True)
    updated_count = fields.Integer(compute='_compute_counts', store=True)
    review_count = fields.Integer(compute='_compute_counts', store=True)
    error_count = fields.Integer(compute='_compute_counts', store=True)
    unmapped_segment_count = fields.Integer(compute='_compute_counts', store=True)
    profile_count = fields.Integer(compute='_compute_counts', store=True)
    holding_count = fields.Integer(compute='_compute_counts', store=True)
    note = fields.Text()

    @api.depends('line_ids.state', 'line_ids.action_taken')
    def _compute_counts(self):
        for batch in self:
            lines = batch.line_ids
            batch.total_count = len(lines)
            batch.created_count = len(lines.filtered(lambda line: line.action_taken == 'created'))
            batch.updated_count = len(lines.filtered(lambda line: line.action_taken == 'updated'))
            batch.review_count = len(lines.filtered(lambda line: line.state == 'manual_review'))
            batch.error_count = len(lines.filtered(lambda line: line.state == 'error'))
            batch.unmapped_segment_count = len(lines.filtered(lambda line: line.action_taken == 'unmapped_segment'))
            batch.profile_count = len(lines.filtered(lambda line: line.record_type == 'customer_profile'))
            batch.holding_count = len(lines.filtered(lambda line: line.record_type == 'product_holding'))

    def action_process(self):
        for batch in self:
            batch.write({'state': 'processing', 'started_at': fields.Datetime.now()})
            lines = batch.line_ids.filtered(lambda line: line.state in ('draft', 'error', 'manual_review'))
            lines.action_process()
            has_issue = any(line.state in ('error', 'manual_review') for line in batch.line_ids)
            batch.write({
                'state': 'partial' if has_issue else 'done',
                'completed_at': fields.Datetime.now(),
            })
        return True

    @api.model
    def _cron_process_daily_staging(self):
        batches = self.search([('state', 'in', ('draft', 'partial')), ('sync_type', '=', 'daily')])
        batches.action_process()


class CrmCorebankingCustomerStaging(models.Model):
    _name = 'crm.corebanking.customer.staging'
    _description = 'Core Banking Customer Staging'
    _order = 'create_date desc, id desc'

    batch_id = fields.Many2one(
        'crm.corebanking.customer.batch',
        string='Batch',
        ondelete='cascade',
        required=True,
    )
    record_type = fields.Selection(
        STAGING_RECORD_TYPE_SELECTION,
        string='Loại dữ liệu',
        required=True,
        default='customer_master',
        index=True,
    )
    cif = fields.Char(string='CIF', required=True, index=True)
    customer_name = fields.Char(string='Tên khách hàng')
    customer_type = fields.Selection(CUSTOMER_TYPE_SELECTION, string='Loại khách hàng')
    segment_code = fields.Char(string='Mã segment', index=True)
    segment_name = fields.Char(string='Tên segment từ Core Banking')
    customer_status = fields.Char(string='Trạng thái khách hàng')
    corebanking_updated_at = fields.Datetime(string='Core Banking cập nhật lúc')
    identity_number = fields.Char(string='CCCD/MST')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # Common Banking 360 profile
    total_deposit_balance = fields.Monetary(string='Tổng tiền gửi', currency_field='currency_id')
    total_loan_balance = fields.Monetary(string='Tổng dư nợ', currency_field='currency_id')
    total_aum = fields.Monetary(string='AUM', currency_field='currency_id')
    total_limit = fields.Monetary(string='Tổng hạn mức', currency_field='currency_id')
    collateral_value = fields.Monetary(string='Tài sản bảo đảm', currency_field='currency_id')
    casa_balance = fields.Monetary(string='CASA balance', currency_field='currency_id')
    toi_mtd = fields.Monetary(string='TOI MTD', currency_field='currency_id')
    toi_ytd = fields.Monetary(string='TOI YTD', currency_field='currency_id')
    toi_12m = fields.Monetary(string='TOI 12M', currency_field='currency_id')
    risk_score = fields.Float(string='Risk score')
    risk_grade = fields.Char(string='Risk grade')
    kyc_status = fields.Char(string='KYC status')
    risk_level = fields.Char(string='Risk level')
    branch_code = fields.Char(string='Mã chi nhánh')
    branch_name = fields.Char(string='Chi nhánh')
    rm_code = fields.Char(string='Mã RM')
    rm_name = fields.Char(string='RM')
    preferred_channel = fields.Char(string='Kênh ưa thích')
    digital_adoption_level = fields.Char(string='Digital adoption')
    raw_summary_json = fields.Text(string='Raw profile JSON')

    # Individual profile
    marital_status = fields.Char(string='Tình trạng hôn nhân')
    dependent_count = fields.Integer(string='Số người phụ thuộc')
    residential_area = fields.Char(string='Khu vực cư trú')
    occupation = fields.Char(string='Nghề nghiệp')
    employer_name = fields.Char(string='Employer')
    job_title = fields.Char(string='Chức danh')
    monthly_income = fields.Monetary(string='Thu nhập tháng', currency_field='currency_id')
    income_source = fields.Char(string='Nguồn thu nhập')
    income_stability = fields.Char(string='Ổn định thu nhập')
    verified_income = fields.Monetary(string='Thu nhập xác minh', currency_field='currency_id')
    non_financial_json = fields.Text(string='Phi tài chính JSON')
    compliance_flags = fields.Char(string='Compliance flags')

    # Business profile
    tax_code = fields.Char(string='MST/GPKD')
    industry_code = fields.Char(string='Mã ngành')
    industry_name = fields.Char(string='Ngành nghề')
    legal_form = fields.Char(string='Loại hình')
    establishment_date = fields.Date(string='Ngày thành lập')
    employee_count = fields.Integer(string='Số nhân sự')
    business_area = fields.Char(string='Địa bàn')
    annual_revenue = fields.Monetary(string='Doanh thu năm', currency_field='currency_id')
    net_profit = fields.Monetary(string='Lợi nhuận', currency_field='currency_id')
    ebitda = fields.Monetary(string='EBITDA', currency_field='currency_id')
    total_assets = fields.Monetary(string='Tổng tài sản', currency_field='currency_id')
    equity = fields.Monetary(string='Vốn chủ sở hữu', currency_field='currency_id')
    cash_flow = fields.Monetary(string='Dòng tiền', currency_field='currency_id')
    approved_limit = fields.Monetary(string='Hạn mức cấp', currency_field='currency_id')
    used_limit = fields.Monetary(string='Hạn mức sử dụng', currency_field='currency_id')
    debt_group = fields.Char(string='Nhóm nợ')
    dscr = fields.Float(string='DSCR')
    avg_casa_balance = fields.Monetary(string='CASA bình quân', currency_field='currency_id')
    payment_volume = fields.Monetary(string='Doanh số thanh toán', currency_field='currency_id')
    payroll_volume = fields.Monetary(string='Payroll volume', currency_field='currency_id')
    lc_volume = fields.Monetary(string='LC volume', currency_field='currency_id')
    fx_volume = fields.Monetary(string='FX volume', currency_field='currency_id')
    trade_finance_volume = fields.Monetary(string='Trade finance volume', currency_field='currency_id')
    toi_deposit = fields.Monetary(string='TOI tiền gửi', currency_field='currency_id')
    toi_credit = fields.Monetary(string='TOI tín dụng', currency_field='currency_id')
    toi_fee = fields.Monetary(string='TOI phí', currency_field='currency_id')
    toi_fx_trade = fields.Monetary(string='TOI FX/Trade', currency_field='currency_id')
    ecosystem_json = fields.Text(string='Hệ sinh thái JSON')
    management_json = fields.Text(string='Ban lãnh đạo JSON')

    # Product holding
    source_system = fields.Char(default='corebanking')
    source_ref = fields.Char(string='Mã tham chiếu sản phẩm')
    masked_account_number = fields.Char(string='Số TK/HĐ masked')
    product_code = fields.Char(string='Mã sản phẩm')
    product_name = fields.Char(string='Tên sản phẩm')
    product_category = fields.Selection(PRODUCT_CATEGORY_SELECTION, string='Nhóm sản phẩm', default='other')
    current_balance = fields.Monetary(string='Số dư hiện tại', currency_field='currency_id')
    outstanding_balance = fields.Monetary(string='Dư nợ', currency_field='currency_id')
    credit_limit = fields.Monetary(string='Hạn mức', currency_field='currency_id')
    open_date = fields.Date(string='Ngày mở')
    maturity_date = fields.Date(string='Ngày đáo hạn')
    holding_status = fields.Selection(HOLDING_STATUS_SELECTION, string='Trạng thái sản phẩm', default='active')
    raw_holding_json = fields.Text(string='Raw holding JSON')

    partner_id = fields.Many2one('res.partner', string='Contact được match', readonly=True)
    state = fields.Selection(
        [
            ('draft', 'Chờ xử lý'),
            ('done', 'Đã xử lý'),
            ('manual_review', 'Cần kiểm tra'),
            ('error', 'Lỗi'),
        ],
        default='draft',
        string='Trạng thái xử lý',
        index=True,
        readonly=True,
    )
    action_taken = fields.Selection(
        [
            ('created', 'Tạo Contact'),
            ('updated', 'Cập nhật Contact'),
            ('profile_updated', 'Cập nhật profile'),
            ('holding_upserted', 'Cập nhật sản phẩm'),
            ('unmapped_segment', 'Segment chưa map'),
            ('manual_review', 'Chờ kiểm tra'),
            ('error', 'Lỗi'),
        ],
        string='Kết quả',
        readonly=True,
    )
    error_message = fields.Text(readonly=True)
    processed_at = fields.Datetime(readonly=True)

    _cif_batch_unique = models.Constraint(
        'UNIQUE(batch_id, record_type, cif, source_ref)',
        'Một dòng staging phải là duy nhất theo batch, loại dữ liệu, CIF và mã tham chiếu.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('source_ref') and vals.get('record_type') != 'product_holding':
                vals['source_ref'] = vals.get('cif')
        return super().create(vals_list)

    @api.constrains('record_type', 'customer_name', 'customer_type', 'source_ref')
    def _check_required_by_record_type(self):
        for line in self:
            if line.record_type == 'customer_master' and (not line.customer_name or not line.customer_type):
                raise ValidationError(_('Customer Master cần Tên khách hàng và Loại khách hàng.'))
            if line.record_type == 'product_holding' and not line.source_ref:
                raise ValidationError(_('Product Holding cần Mã tham chiếu sản phẩm.'))

    def action_process(self):
        for line in self:
            line._process_one()
        return True

    def _find_partner(self):
        self.ensure_one()
        Partner = self.env['res.partner'].with_context(active_test=False)
        if self.cif:
            partner = Partner.search([('bank_cif', '=', self.cif)], limit=1)
            if partner:
                return partner
        if self.identity_number:
            domain = ['|', ('cccd_number', '=', self.identity_number), ('vat', '=', self.identity_number)]
            partner = Partner.search(domain, limit=1)
            if partner:
                return partner
        return self.env['res.partner']

    def _find_segment(self):
        self.ensure_one()
        if not self.segment_code or not self.customer_type:
            return self.env['crm.customer.segment']
        return self.env['crm.customer.segment'].search([
            ('code', '=', self.segment_code),
            ('customer_type', '=', self.customer_type),
        ], limit=1)

    def _corebanking_partner_vals(self, segment):
        sync_status = 'done'
        message = False
        action_taken = False
        if self.segment_code and not segment:
            sync_status = 'warning'
            message = _('Chưa map được mã segment %s từ Core Banking.') % self.segment_code
            action_taken = 'unmapped_segment'
        vals = {
            'bank_cif': self.cif,
            'customer_type': self.customer_type,
            'corebanking_segment_code': self.segment_code,
            'corebanking_customer_status': self.customer_status,
            'corebanking_last_sync_date': fields.Datetime.now(),
            'corebanking_sync_status': sync_status,
            'corebanking_sync_message': message,
        }
        if segment:
            vals['customer_segment_id'] = segment.id
        else:
            vals['customer_segment_id'] = False
        return vals, action_taken

    def _process_one(self):
        self.ensure_one()
        try:
            if self.record_type == 'customer_master':
                self._process_customer_master()
            elif self.record_type == 'customer_profile':
                self._process_customer_profile()
            elif self.record_type == 'product_holding':
                self._process_product_holding()
        except Exception as exc:
            self.write({
                'state': 'error',
                'action_taken': 'error',
                'error_message': str(exc),
                'processed_at': fields.Datetime.now(),
            })
            if self.env.context.get('raise_corebanking_sync_errors'):
                raise UserError(str(exc)) from exc

    def _manual_review(self, message):
        self.write({
            'state': 'manual_review',
            'action_taken': 'manual_review',
            'error_message': message,
            'processed_at': fields.Datetime.now(),
        })

    def _done(self, partner, action_taken):
        self.write({
            'partner_id': partner.id,
            'state': 'done',
            'action_taken': action_taken,
            'error_message': False,
            'processed_at': fields.Datetime.now(),
        })

    def _process_customer_master(self):
        partner = self._find_partner()
        if not partner and not self.batch_id.allow_create_partner:
            return self._manual_review(_('Không tìm thấy Contact match CIF/CCCD/MST.'))

        segment = self._find_segment()
        vals, warning_action = self._corebanking_partner_vals(segment)
        Partner = self.env['res.partner'].with_context(allow_corebanking_sync_write=True)

        if partner:
            partner.with_context(allow_corebanking_sync_write=True).write(vals)
            action_taken = warning_action or 'updated'
        else:
            vals.update({
                'name': self.customer_name,
                'is_company': self.customer_type == 'business',
            })
            partner = Partner.create(vals)
            action_taken = warning_action or 'created'
        return self._done(partner, action_taken)

    def _profile_common_vals(self):
        return {
            'currency_id': self.currency_id.id,
            'total_deposit_balance': self.total_deposit_balance,
            'total_loan_balance': self.total_loan_balance,
            'total_aum': self.total_aum,
            'total_limit': self.total_limit,
            'collateral_value': self.collateral_value,
            'casa_balance': self.casa_balance,
            'toi_mtd': self.toi_mtd,
            'toi_ytd': self.toi_ytd,
            'toi_12m': self.toi_12m,
            'risk_score': self.risk_score,
            'risk_grade': self.risk_grade,
            'kyc_status': self.kyc_status,
            'risk_level': self.risk_level,
            'branch_code': self.branch_code,
            'branch_name': self.branch_name,
            'rm_code': self.rm_code,
            'rm_name': self.rm_name,
            'preferred_channel': self.preferred_channel,
            'digital_adoption_level': self.digital_adoption_level,
            'raw_summary_json': self.raw_summary_json,
            'corebanking_updated_at': self.corebanking_updated_at,
            'last_sync_date': fields.Datetime.now(),
        }

    def _process_customer_profile(self):
        partner = self._find_partner()
        if not partner:
            return self._manual_review(_('Không tìm thấy Contact theo CIF để cập nhật profile.'))

        Profile = self.env['crm.banking.customer.profile'].with_context(allow_corebanking_sync_write=True)
        common = Profile.search([('partner_id', '=', partner.id)], limit=1)
        vals = self._profile_common_vals()
        if common:
            common.write(vals)
        else:
            vals['partner_id'] = partner.id
            common = Profile.create(vals)

        if partner.customer_type == 'individual':
            self._upsert_individual_profile(partner)
        elif partner.customer_type == 'business':
            self._upsert_business_profile(partner)
        return self._done(partner, 'profile_updated')

    def _upsert_individual_profile(self, partner):
        Model = self.env['crm.banking.individual.profile'].with_context(allow_corebanking_sync_write=True)
        vals = {
            'currency_id': self.currency_id.id,
            'marital_status': self.marital_status,
            'dependent_count': self.dependent_count,
            'residential_area': self.residential_area,
            'occupation': self.occupation,
            'employer_name': self.employer_name,
            'job_title': self.job_title,
            'monthly_income': self.monthly_income,
            'income_source': self.income_source,
            'income_stability': self.income_stability,
            'verified_income': self.verified_income,
            'non_financial_json': self.non_financial_json,
            'compliance_flags': self.compliance_flags,
            'corebanking_updated_at': self.corebanking_updated_at,
            'last_sync_date': fields.Datetime.now(),
        }
        rec = Model.search([('partner_id', '=', partner.id)], limit=1)
        if rec:
            rec.write(vals)
        else:
            vals['partner_id'] = partner.id
            Model.create(vals)

    def _upsert_business_profile(self, partner):
        Model = self.env['crm.banking.business.profile'].with_context(allow_corebanking_sync_write=True)
        vals = {
            'currency_id': self.currency_id.id,
            'tax_code': self.tax_code,
            'industry_code': self.industry_code,
            'industry_name': self.industry_name,
            'legal_form': self.legal_form,
            'establishment_date': self.establishment_date,
            'employee_count': self.employee_count,
            'business_area': self.business_area,
            'annual_revenue': self.annual_revenue,
            'net_profit': self.net_profit,
            'ebitda': self.ebitda,
            'total_assets': self.total_assets,
            'equity': self.equity,
            'cash_flow': self.cash_flow,
            'approved_limit': self.approved_limit,
            'used_limit': self.used_limit,
            'debt_group': self.debt_group,
            'dscr': self.dscr,
            'avg_casa_balance': self.avg_casa_balance,
            'payment_volume': self.payment_volume,
            'payroll_volume': self.payroll_volume,
            'lc_volume': self.lc_volume,
            'fx_volume': self.fx_volume,
            'trade_finance_volume': self.trade_finance_volume,
            'toi_deposit': self.toi_deposit,
            'toi_credit': self.toi_credit,
            'toi_fee': self.toi_fee,
            'toi_fx_trade': self.toi_fx_trade,
            'ecosystem_json': self.ecosystem_json,
            'management_json': self.management_json,
            'corebanking_updated_at': self.corebanking_updated_at,
            'last_sync_date': fields.Datetime.now(),
        }
        rec = Model.search([('partner_id', '=', partner.id)], limit=1)
        if rec:
            rec.write(vals)
        else:
            vals['partner_id'] = partner.id
            Model.create(vals)

    def _process_product_holding(self):
        partner = self._find_partner()
        if not partner:
            return self._manual_review(_('Không tìm thấy Contact theo CIF để cập nhật sản phẩm.'))

        Model = self.env['crm.banking.product.holding'].with_context(allow_corebanking_sync_write=True)
        source_system = self.source_system or 'corebanking'
        vals = {
            'partner_id': partner.id,
            'source_system': source_system,
            'source_ref': self.source_ref,
            'masked_account_number': self.masked_account_number,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'product_category': self.product_category,
            'currency_id': self.currency_id.id,
            'current_balance': self.current_balance,
            'outstanding_balance': self.outstanding_balance,
            'credit_limit': self.credit_limit,
            'toi_mtd': self.toi_mtd,
            'toi_ytd': self.toi_ytd,
            'toi_12m': self.toi_12m,
            'open_date': self.open_date,
            'maturity_date': self.maturity_date,
            'status': self.holding_status,
            'raw_holding_json': self.raw_holding_json or self._holding_raw_json(),
            'corebanking_updated_at': self.corebanking_updated_at,
            'last_sync_date': fields.Datetime.now(),
        }
        holding = Model.search([
            ('partner_id', '=', partner.id),
            ('source_system', '=', source_system),
            ('source_ref', '=', self.source_ref),
        ], limit=1)
        if holding:
            holding.write(vals)
        else:
            holding = Model.create(vals)
        return self._done(partner, 'holding_upserted')

    def _holding_raw_json(self):
        data = {
            'source_ref': self.source_ref,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'product_category': self.product_category,
        }
        return json.dumps(data, ensure_ascii=False)
