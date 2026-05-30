import json
import logging

from markupsafe import Markup

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PROPOSAL_TEMPLATES = {
    'vay_mua_nha': {
        'name': 'Đề xuất Vay mua nhà',
        'placeholders': ['{{partner_name}}', '{{loan_amount}}', '{{loan_term}}', '{{property_address}}'],
        'template': """ĐỀ XUẤT VAY MUA NHÀ

Kính gửi: {{partner_name}}

Ngân hàng trân trọng gửi đến Quý khách đề xuất vay mua nhà như sau:

Số tiền vay đề xuất: {{loan_amount}}
Thời hạn vay: {{loan_term}}
Tài sản đảm bảo: {{property_address}}

Lãi suất: [NV điền]
Tỉ lệ tài trợ: [NV điền theo thẩm định]

Trân trọng,
[Tên nhân viên]""",
    },
    'vay_kinh_doanh': {
        'name': 'Đề xuất Vay kinh doanh',
        'placeholders': ['{{partner_name}}', '{{company_name}}', '{{loan_amount}}', '{{purpose}}'],
        'template': """ĐỀ XUẤT TÀI TRỢ VỐN KINH DOANH

Kính gửi: {{partner_name}} — {{company_name}}

Ngân hàng đề xuất gói tài trợ vốn kinh doanh:

Mục đích sử dụng vốn: {{purpose}}
Hạn mức đề xuất: {{loan_amount}}
Hình thức: [NV điền — vay ngắn hạn/trung hạn]
Lãi suất: [NV điền theo biểu phí]

Trân trọng,
[Tên nhân viên]""",
    },
    'the_tin_dung': {
        'name': 'Đề xuất Thẻ tín dụng',
        'placeholders': ['{{partner_name}}', '{{credit_limit}}'],
        'template': """ĐỀ XUẤT MỞ THẺ TÍN DỤNG

Kính gửi: {{partner_name}}

Ngân hàng đề xuất mở thẻ tín dụng với hạn mức: {{credit_limit}}

Ưu đãi áp dụng: [NV điền]
Phí thường niên: [NV điền theo biểu phí]

Trân trọng,
[Tên nhân viên]""",
    },
}


class CrmAiGenerateProposal(models.TransientModel):
    _name = 'crm.ai.generate.proposal'
    _description = 'Wizard: AI sinh Proposal/Term Sheet'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    product_type = fields.Selection(
        related='lead_id.product_type', string='Loại sản phẩm', readonly=True,
    )
    template_key = fields.Selection(
        [(k, v['name']) for k, v in PROPOSAL_TEMPLATES.items()],
        string='Chọn template',
    )
    partner_name = fields.Char(string='Tên khách hàng')
    loan_amount = fields.Char(string='Số tiền vay/hạn mức')
    loan_term = fields.Char(string='Thời hạn')
    purpose = fields.Char(string='Mục đích sử dụng vốn')
    property_address = fields.Char(string='Địa chỉ tài sản')
    company_name = fields.Char(string='Tên công ty')
    credit_limit = fields.Char(string='Hạn mức thẻ')

    custom_notes = fields.Text(string='Ghi chú thêm cho AI')

    generated_content = fields.Text(string='Nội dung đề xuất', readonly=True)
    state = fields.Selection([('input', 'Nhập thông tin'), ('result', 'Kết quả')], default='input')

    @api.onchange('lead_id')
    def _onchange_lead(self):
        if self.lead_id:
            partner = self.lead_id.partner_id
            self.partner_name = partner.name or ''
            self.company_name = partner.company_name or (partner.name if partner.is_company else '')
            product_type = self.lead_id.product_type
            if product_type in PROPOSAL_TEMPLATES:
                self.template_key = product_type

    def action_generate(self):
        self.ensure_one()
        if not self.template_key:
            raise UserError('Vui lòng chọn template đề xuất.')

        tpl = PROPOSAL_TEMPLATES.get(self.template_key, {})
        base_content = tpl.get('template', '')

        # Fill placeholders
        replacements = {
            '{{partner_name}}': self.partner_name or self.lead_id.partner_id.name or 'Quý khách',
            '{{loan_amount}}': self.loan_amount or '[Số tiền vay]',
            '{{loan_term}}': self.loan_term or '[Thời hạn]',
            '{{property_address}}': self.property_address or '[Địa chỉ tài sản]',
            '{{company_name}}': self.company_name or '[Tên công ty]',
            '{{purpose}}': self.purpose or '[Mục đích]',
            '{{credit_limit}}': self.credit_limit or '[Hạn mức]',
        }
        content = base_content
        for k, v in replacements.items():
            content = content.replace(k, v)

        # Ask AI to enhance if custom notes provided
        if self.custom_notes:
            try:
                from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
                service = CrmAiService(self.env)

                lead = self.lead_id
                lead_context = (
                    f'Lead: {lead.name}, Stage: {lead.stage_id.name}, '
                    f'Sản phẩm: {lead.product_type}, '
                    f'Partner: {lead.partner_id.name or ""}'
                )
                enhanced = service.generate_proposal_content(content, lead_context, self.custom_notes)
                if enhanced:
                    content = enhanced
            except Exception as e:
                _logger.warning('AI proposal enhancement failed: %s', e)

        self.write({'generated_content': content, 'state': 'result'})
        return self._reopen()

    def action_attach_to_lead(self):
        """Lưu nội dung đề xuất vào chatter và tạo attachment text."""
        self.ensure_one()
        if not self.generated_content:
            raise UserError('Chưa có nội dung đề xuất.')

        import base64
        filename = f'Proposal_{self.lead_id.name or "Lead"}_{fields.Date.today()}.txt'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(self.generated_content.encode('utf-8')),
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
        })
        self.lead_id.message_post(
            body=Markup(f'📄 <b>Đề xuất đã được tạo:</b> {filename}<br/><pre style="font-size:11px">{self.generated_content[:500]}...</pre>'),
            subtype_xmlid='mail.mt_note',
            attachment_ids=[attachment.id],
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': 'Đề xuất AI',
        }
