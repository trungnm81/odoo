import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmAiZaloCompose(models.TransientModel):
    _name = 'crm.ai.zalo.compose'
    _description = 'Soạn và gửi tin nhắn Zalo'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    zalo_user_id = fields.Char(string='Zalo User ID', required=True)
    message = fields.Text(string='Nội dung tin nhắn', required=True)

    ai_drafts = fields.Text(string='AI Draft (JSON)')
    draft_1 = fields.Text(string='Phương án 1 (AI)', readonly=True)
    draft_2 = fields.Text(string='Phương án 2 (AI)', readonly=True)

    def action_get_ai_drafts(self):
        """Gọi AI Copilot để sinh 2 draft phản hồi."""
        self.ensure_one()
        from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        lead = self.lead_id
        messages = self.env['mail.message'].search([
            ('res_id', '=', lead.id),
            ('model', '=', 'crm.lead'),
            ('message_type', 'in', ['email', 'comment']),
            ('subtype_id.internal', '=', False),
        ], order='date desc', limit=5)
        conversation = [
            {'author': m.author_id.name or '?', 'body': m.body or ''}
            for m in reversed(messages)
        ]
        lead_context = (
            f'Lead: {lead.name}, Stage: {lead.stage_id.name}, '
            f'Partner: {lead.partner_id.name or lead.contact_name or "N/A"}, '
            f'Product: {lead.product_type or "N/A"}'
        )
        drafts = service.generate_reply(conversation, lead_context, tone='informal')
        if drafts:
            self.draft_1 = drafts[0].get('text', '') if len(drafts) > 0 else ''
            self.draft_2 = drafts[1].get('text', '') if len(drafts) > 1 else ''
        return self._reopen()

    def action_use_draft_1(self):
        self.ensure_one()
        self.message = self.draft_1
        return self._reopen()

    def action_use_draft_2(self):
        self.ensure_one()
        self.message = self.draft_2
        return self._reopen()

    def action_send(self):
        self.ensure_one()
        config = self.env['crm.ai.config'].get_config()
        if not config.zalo_oa_access_token:
            raise UserError('Chưa cấu hình Zalo OA Access Token. Vào AI Banking → Cấu hình AI.')
        if not self.zalo_user_id:
            raise UserError('Zalo User ID trống. Cập nhật trên lead hoặc profile khách hàng.')

        payload = {
            'recipient': {'user_id': self.zalo_user_id},
            'message': {'text': self.message},
        }
        try:
            resp = requests.post(
                'https://openapi.zalo.me/v3.0/oa/message/cs',
                headers={
                    'access_token': config.zalo_oa_access_token,
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('error') != 0:
                raise UserError(f'Zalo API lỗi: {result.get("message", "unknown")}')
        except requests.RequestException as e:
            raise UserError(f'Không gửi được Zalo: {e}') from e

        self.lead_id._message_log(body=f'📱 [Zalo gửi đi] {self.message}')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Tin nhắn Zalo đã gửi thành công.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
