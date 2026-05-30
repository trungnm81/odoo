import hmac
import hashlib
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CrmAiBankingController(http.Controller):

    # ── Zalo Webhook ──────────────────────────────────────────────────────────

    @http.route('/crm/ai/webhook/zalo', type='http', auth='public', methods=['POST'], csrf=False)
    def zalo_webhook(self):
        try:
            body = request.httprequest.get_data(as_text=True)
            data = json.loads(body)
        except Exception:
            return request.make_json_response({'error': 'invalid json'}, status=400)

        config = request.env['crm.ai.config'].sudo().get_config()
        # Verify signature
        sig = request.httprequest.headers.get('X-ZaloOA-Signature', '')
        if config.zalo_webhook_secret and not self._verify_zalo_sig(body, sig, config.zalo_webhook_secret):
            return request.make_json_response({'error': 'invalid signature'}, status=403)

        event_name = data.get('event_name', '')
        if event_name == 'user_send_text':
            self._handle_zalo_message(data, config)

        return request.make_json_response({'status': 'ok'})

    def _verify_zalo_sig(self, body: str, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _handle_zalo_message(self, data: dict, config):
        sender = data.get('sender', {})
        phone = sender.get('id', '')
        sender_name = sender.get('display_name', '')
        message_text = data.get('message', {}).get('text', '')
        if not message_text:
            return

        env = request.env.sudo()
        # Find lead by phone
        lead = env['crm.lead'].search(
            [('phone_sanitized', '=', env['crm.lead']._phone_format(phone)),
             ('active', '=', True)],
            limit=1,
        ) if phone else env['crm.lead']

        if not lead:
            # Create new lead from Zalo
            tag = env['crm.tag'].search([('name', '=', 'Từ Zalo')], limit=1)
            if not tag:
                tag = env['crm.tag'].create({'name': 'Từ Zalo'})
            lead = env['crm.lead'].create({
                'name': f'Zalo — {sender_name}',
                'contact_name': sender_name,
                'phone': phone,
                'tag_ids': [(4, tag.id)],
                'type': 'lead',
            })

        # Log message to chatter
        lead.message_post(
            body=f'<b>[Zalo]</b> {message_text}',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # AI intent detection (async thread)
        if config.auto_process_email:
            lead._trigger_async(lead.id, '_ai_process_zalo_message', args=(message_text,))

    # ── Name Card Upload (mobile) ─────────────────────────────────────────────

    @http.route('/crm/ai/scan-card', type='http', auth='user', methods=['POST'], csrf=False)
    def scan_card(self):
        image_file = request.httprequest.files.get('image')
        if not image_file:
            return request.make_json_response({'error': 'no image'}, status=400)
        image_bytes = image_file.read()
        from ..models.crm_ai_service import CrmAiService
        service = CrmAiService(request.env)
        result = service.extract_card(image_bytes)
        if not result:
            return request.make_json_response({'error': 'extraction failed'}, status=422)

        # Check duplicate
        existing = None
        if result.get('email'):
            existing = request.env['crm.lead'].search(
                [('email_normalized', '=', result['email']), ('active', '=', True)], limit=1
            )
        if not existing and result.get('phone'):
            existing = request.env['crm.lead'].search(
                [('phone_sanitized', '=', result.get('phone', '')), ('active', '=', True)], limit=1
            )

        if existing:
            return request.make_json_response({'lead_id': existing.id, 'action': 'found', 'data': result})

        tag = request.env['crm.tag'].search([('name', '=', 'Từ name card')], limit=1)
        if not tag:
            tag = request.env['crm.tag'].create({'name': 'Từ name card'})
        lead = request.env['crm.lead'].create({
            'name': result.get('full_name') or result.get('company') or 'New Lead',
            'contact_name': result.get('full_name', ''),
            'partner_name': result.get('company', ''),
            'email_from': result.get('email', ''),
            'phone': result.get('phone', ''),
            'website': result.get('website', ''),
            'function': result.get('title', ''),
            'tag_ids': [(4, tag.id)],
            'type': 'lead',
        })
        return request.make_json_response({'lead_id': lead.id, 'action': 'created', 'data': result})
