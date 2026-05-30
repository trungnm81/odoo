import json
import logging

from markupsafe import Markup, escape

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmProductEligibilityRule(models.Model):
    _name = 'crm.product.eligibility.rule'
    _description = 'Quy tắc điều kiện sản phẩm ngân hàng'
    _order = 'product_category, product_name'

    product_code = fields.Char(string='Mã sản phẩm', required=True)
    product_name = fields.Char(string='Tên sản phẩm', required=True)
    product_category = fields.Selection([
        ('credit', 'Tín dụng'), ('card', 'Thẻ'), ('savings', 'Tiết kiệm'),
        ('insurance', 'Bảo hiểm'), ('payment', 'Thanh toán'), ('trade', 'Tài trợ TM'),
    ], string='Nhóm sản phẩm', default='credit')
    product_type = fields.Selection([
        ('vay_mua_nha', 'Vay mua nhà'), ('vay_kinh_doanh', 'Vay kinh doanh'),
        ('the_tin_dung', 'Thẻ tín dụng'), ('tiet_kiem', 'Tiết kiệm'),
        ('bao_hiem', 'Bảo hiểm'), ('payroll', 'Payroll'),
        ('lc_fx', 'L/C / Ngoại tệ'), ('other', 'Khác'),
    ], string='Loại sản phẩm CRM')

    min_income_million = fields.Float(string='Thu nhập tối thiểu (triệu/tháng)')
    min_age = fields.Integer(string='Tuổi tối thiểu', default=18)
    max_age = fields.Integer(string='Tuổi tối đa', default=70)
    description = fields.Text(string='Mô tả & điểm bán hàng')
    cross_sell_codes = fields.Char(string='Cross-sell sản phẩm (mã, cách nhau dấu phẩy)')
    active = fields.Boolean(default=True)

    def check_eligibility(self, partner):
        """Kiểm tra khách hàng có đủ điều kiện không — simple rule check."""
        self.ensure_one()
        if not partner:
            return True
        age = 0
        if hasattr(partner, 'date_of_birth') and partner.date_of_birth:
            from datetime import date
            age = (date.today() - partner.date_of_birth).days // 365
            if age < self.min_age or (self.max_age and age > self.max_age):
                return False
        return True


class CrmProductRecommendation(models.Model):
    _name = 'crm.product.recommendation'
    _description = 'Gợi ý sản phẩm AI cho Lead'
    _order = 'computed_date desc'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade', index=True)
    computed_date = fields.Datetime(string='Ngày tính', default=fields.Datetime.now)
    recommendations_json = fields.Text(string='Kết quả JSON', default='[]')
    recommendations_html = fields.Html(string='Gợi ý sản phẩm', compute='_compute_html', store=False)
    top_product_name = fields.Char(string='Sản phẩm phù hợp nhất')
    top_match_score = fields.Float(string='Điểm phù hợp (%)', digits=(5, 1))

    @api.depends('recommendations_json')
    def _compute_html(self):
        for rec in self:
            if not rec.recommendations_json:
                rec.recommendations_html = Markup('<em class="text-muted">Chưa có gợi ý sản phẩm.</em>')
                continue
            try:
                items = json.loads(rec.recommendations_json)
                if not items:
                    rec.recommendations_html = Markup('<em class="text-muted">Chưa có gợi ý sản phẩm.</em>')
                    continue
                html = []
                for item in items[:3]:
                    score_pct = int(item.get('match_score', 0) * 100)
                    badge = 'success' if score_pct >= 80 else 'warning' if score_pct >= 60 else 'secondary'
                    reasons_html = ''.join(f'<li class="small">{escape(r)}</li>' for r in item.get('match_reasons', [])[:3])
                    approach = escape(item.get('approach_suggestion', ''))
                    product_name = escape(item.get('product_name', ''))
                    html.append(
                        f'<div class="border border-{badge} rounded p-2 mb-2">'
                        f'<div class="d-flex justify-content-between">'
                        f'<strong>{product_name}</strong>'
                        f'<span class="badge bg-{badge}">{score_pct}% phù hợp</span></div>'
                        f'<ul class="mb-1 ps-3">{reasons_html}</ul>'
                        f'{"<em class=text-muted>" + str(approach) + "</em>" if approach else ""}'
                        f'</div>'
                    )
                rec.recommendations_html = Markup(''.join(html))
            except Exception:
                rec.recommendations_html = Markup(f'<pre class="small">{rec.recommendations_json[:300]}</pre>')
