from odoo import models, fields, api


class CrmAccountContact(models.Model):
    _name = 'crm.account.contact'
    _description = 'B2B Stakeholder / Account Contact Map'
    _order = 'influence_level, sequence'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Liên hệ Odoo')
    sequence = fields.Integer(default=10)

    name = fields.Char(string='Họ tên', required=True)
    title = fields.Char(string='Chức danh')
    phone = fields.Char(string='Điện thoại')
    email = fields.Char(string='Email')
    department = fields.Char(string='Phòng ban')

    role = fields.Selection([
        ('ceo', 'CEO / Tổng Giám đốc'),
        ('cfo', 'CFO / Giám đốc Tài chính'),
        ('coo', 'COO / Giám đốc Vận hành'),
        ('hr_director', 'Giám đốc Nhân sự'),
        ('chief_accountant', 'Kế toán trưởng'),
        ('procurement', 'Phụ trách Mua sắm'),
        ('influencer', 'Người ảnh hưởng'),
        ('other', 'Khác'),
    ], string='Vai trò', default='other')

    influence_level = fields.Selection([
        ('decision_maker', 'Ra quyết định'),
        ('influencer', 'Người ảnh hưởng'),
        ('gatekeeper', 'Gatekeeper'),
        ('user', 'Người dùng'),
    ], string='Mức độ ảnh hưởng', default='influencer')

    relationship_strength = fields.Selection([
        ('1', '1 — Chưa biết'), ('2', '2 — Mới quen'),
        ('3', '3 — Đang xây dựng'), ('4', '4 — Tin tưởng'),
        ('5', '5 — Rất thân thiết'),
    ], string='Độ thân thiết', default='2')

    last_contact_date = fields.Date(string='Liên hệ gần nhất')
    notes = fields.Text(string='Ghi chú')

    influence_level_label = fields.Char(compute='_compute_labels')
    role_label = fields.Char(compute='_compute_labels')

    @api.depends('influence_level', 'role')
    def _compute_labels(self):
        inf_map = dict(self._fields['influence_level'].selection)
        role_map = dict(self._fields['role'].selection)
        for rec in self:
            rec.influence_level_label = inf_map.get(rec.influence_level, '')
            rec.role_label = role_map.get(rec.role, '')
