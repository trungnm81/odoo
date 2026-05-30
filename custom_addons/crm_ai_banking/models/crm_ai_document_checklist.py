from odoo import models, fields, api, _
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class CrmDocumentChecklistTemplate(models.Model):
    _name = 'crm.document.checklist.template'
    _description = 'Document Checklist Template'
    _rec_name = 'product_type'

    product_type = fields.Selection(
        [
            ('vay_mua_nha', 'Vay mua nhà'),
            ('vay_kinh_doanh', 'Vay kinh doanh'),
            ('the_tin_dung', 'Thẻ tín dụng'),
            ('tiet_kiem', 'Tiết kiệm'),
            ('bao_hiem', 'Bảo hiểm'),
            ('payroll', 'Payroll'),
            ('lc_fx', 'L/C / Ngoại tệ'),
            ('other', 'Khác'),
        ],
        string='Loại sản phẩm',
        required=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    item_ids = fields.One2many('crm.document.checklist.template.item', 'template_id', string='Danh sách giấy tờ')
    item_count = fields.Integer(compute='_compute_item_count')
    remind_after_days = fields.Integer(string='Nhắc sau (ngày)', default=2)

    @api.depends('item_ids')
    def _compute_item_count(self):
        for rec in self:
            rec.item_count = len(rec.item_ids)


class CrmDocumentChecklistTemplateItem(models.Model):
    _name = 'crm.document.checklist.template.item'
    _description = 'Checklist Template Item'
    _order = 'sequence, id'

    template_id = fields.Many2one('crm.document.checklist.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Tên giấy tờ', required=True)
    required = fields.Boolean(string='Bắt buộc', default=True)
    description = fields.Char(string='Mô tả / Ghi chú')
    file_format_hint = fields.Char(string='Định dạng yêu cầu', help='VD: PDF, ảnh chụp rõ 2 mặt')


class CrmDocumentChecklist(models.Model):
    _name = 'crm.document.checklist'
    _description = 'Lead Document Checklist'
    _rec_name = 'display_name'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade', index=True)
    product_type = fields.Char(string='Loại sản phẩm', readonly=True)
    template_id = fields.Many2one('crm.document.checklist.template', string='Template')
    line_ids = fields.One2many('crm.document.checklist.line', 'checklist_id', string='Hồ sơ')

    completion_rate = fields.Float(string='Hoàn thành (%)', compute='_compute_completion', store=True)
    pending_count = fields.Integer(compute='_compute_completion', store=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('lead_id', 'product_type')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'Hồ sơ {rec.product_type or ""} — {rec.lead_id.name or ""}'

    @api.depends('line_ids.status')
    def _compute_completion(self):
        for rec in self:
            total = len(rec.line_ids)
            if total == 0:
                rec.completion_rate = 0.0
                rec.pending_count = 0
            else:
                done = len(rec.line_ids.filtered(lambda l: l.status in ('submitted', 'approved')))
                rec.completion_rate = done / total * 100
                rec.pending_count = total - done

    @api.model
    def create_from_template(self, lead_id: int, product_type: str):
        template = self.env['crm.document.checklist.template'].search(
            [('product_type', '=', product_type), ('active', '=', True)], limit=1
        )
        if not template:
            _logger.warning('No checklist template for product_type=%s', product_type)
            return False

        checklist = self.create({
            'lead_id': lead_id,
            'product_type': product_type,
            'template_id': template.id,
        })
        line_vals = []
        for item in template.item_ids:
            line_vals.append({
                'checklist_id': checklist.id,
                'item_name': item.name,
                'required': item.required,
                'description': item.description or '',
                'file_format_hint': item.file_format_hint or '',
                'sequence': item.sequence,
            })
        if line_vals:
            self.env['crm.document.checklist.line'].create(line_vals)

        # Schedule reminder activity
        remind_days = template.remind_after_days or 2
        lead = self.env['crm.lead'].browse(lead_id)
        act_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if act_type:
            lead.activity_schedule(
                activity_type_id=act_type.id,
                summary='📎 Nhắc bổ sung hồ sơ',
                date_deadline=date.today() + timedelta(days=remind_days),
                user_id=lead.user_id.id or self.env.user.id,
            )
        return checklist

    def get_pending_items_text(self) -> str:
        pending = self.line_ids.filtered(lambda l: l.status == 'pending')
        if not pending:
            return ''
        items = '\n'.join(f'- {l.item_name}' for l in pending)
        return f'Hồ sơ còn thiếu:\n{items}'


class CrmDocumentChecklistLine(models.Model):
    _name = 'crm.document.checklist.line'
    _description = 'Checklist Line'
    _order = 'checklist_id, sequence'

    checklist_id = fields.Many2one('crm.document.checklist', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    item_name = fields.Char(string='Giấy tờ', required=True)
    required = fields.Boolean(string='Bắt buộc', default=True)
    description = fields.Char(string='Mô tả')
    file_format_hint = fields.Char(string='Định dạng')
    status = fields.Selection(
        [
            ('pending', 'Chờ nộp'),
            ('submitted', 'Đã nộp'),
            ('approved', 'Đã duyệt'),
            ('rejected', 'Từ chối'),
        ],
        string='Trạng thái',
        default='pending',
        required=True,
    )
    attachment_id = fields.Many2one('ir.attachment', string='File đính kèm')
    note = fields.Char(string='Ghi chú')
    submitted_date = fields.Date(string='Ngày nộp')

    @api.onchange('status')
    def _onchange_status(self):
        if self.status == 'submitted' and not self.submitted_date:
            self.submitted_date = date.today()
