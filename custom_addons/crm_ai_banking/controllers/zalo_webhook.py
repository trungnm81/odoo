import hashlib
import hmac
import json
import logging

import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ZALO_OA_SEND_URL = 'https://openapi.zalo.me/v3.0/oa/message/cs'


class ZaloWebhookController(http.Controller):

    # ── Incoming message webhook ──────────────────────────────────────────────

    @http.route('/crm/ai/webhook/zalo', type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def zalo_webhook(self, **kwargs):
        """Zalo OA webhook — verify GET, process POST."""
        if request.httprequest.method == 'GET':
            # Zalo dùng GET để verify webhook khi đăng ký
            challenge = request.httprequest.args.get('challenge', '')
            return request.make_response(challenge, headers=[('Content-Type', 'text/plain')])

        # POST: nhận message từ Zalo user
        try:
            body = request.httprequest.data
            config = request.env['crm.ai.config'].sudo().get_config()

            # Verify Zalo signature
            if config.zalo_webhook_secret:
                sig_header = request.httprequest.headers.get('X-ZEvent-Signature', '')
                expected = hmac.new(
                    config.zalo_webhook_secret.encode(), body, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(sig_header, expected):
                    _logger.warning('Zalo webhook: invalid signature')
                    return request.make_response('forbidden', status=403)

            data = json.loads(body)
            event_name = data.get('event_name', '')
            _logger.info('Zalo webhook event: %s', event_name)

            if event_name in ('user_send_text', 'user_send_image', 'user_send_file'):
                request.env['crm.lead'].sudo()._handle_zalo_incoming(data)

        except Exception as e:
            _logger.error('Zalo webhook error: %s', e, exc_info=True)

        return request.make_response('ok', headers=[('Content-Type', 'text/plain')])

    # ── Send message to Zalo user ─────────────────────────────────────────────

    @http.route('/crm/ai/zalo/send', type='jsonrpc', auth='user', methods=['POST'])
    def zalo_send(self, lead_id: int, message: str):
        """Gửi tin nhắn Zalo tới khách hàng của lead qua Zalo OA API."""
        config = request.env['crm.ai.config'].sudo().get_config()
        if not config.zalo_oa_access_token:
            return {'error': 'Chưa cấu hình Zalo OA Access Token'}

        lead = request.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            return {'error': 'Lead không tồn tại'}

        zalo_uid = (
            lead.partner_id.zalo_user_id
            if lead.partner_id
            else lead.zalo_user_id
        )
        if not zalo_uid:
            return {'error': 'Khách hàng chưa có Zalo User ID'}

        try:
            payload = {
                'recipient': {'user_id': zalo_uid},
                'message': {'text': message},
            }
            resp = requests.post(
                ZALO_OA_SEND_URL,
                headers={
                    'access_token': config.zalo_oa_access_token,
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('error') == 0:
                lead._message_log(
                    body=f'📱 [Zalo gửi đi] {message}'
                )
                return {'ok': True}
            return {'error': result.get('message', 'Zalo API lỗi')}
        except Exception as e:
            _logger.error('Zalo send error: %s', e)
            return {'error': str(e)}

    # ── Mobile REST: scan card ────────────────────────────────────────────────

    @http.route('/crm/ai/scan-card', type='http', auth='user', csrf=False, methods=['POST'])
    def mobile_scan_card(self, **kwargs):
        """REST endpoint cho mobile upload ảnh name card và nhận JSON kết quả."""
        import base64
        file = request.httprequest.files.get('image')
        scan_type = request.httprequest.form.get('scan_type', 'name_card')
        lead_id = request.httprequest.form.get('lead_id', 0)

        if not file:
            return request.make_response(
                json.dumps({'error': 'Thiếu file ảnh'}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        image_bytes = file.read()
        from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
        service = CrmAiService(request.env)

        try:
            if scan_type == 'name_card':
                result = service.extract_card(image_bytes)
            else:
                result = service.extract_id_card(image_bytes, scan_type)

            if lead_id and result and scan_type == 'name_card':
                lead = request.env['crm.lead'].sudo().browse(int(lead_id))
                if lead.exists():
                    wizard = request.env['crm.ai.scan.document'].sudo().create({
                        'scan_type': scan_type,
                        'lead_id': lead.id,
                        'image_data': base64.b64encode(image_bytes).decode(),
                    })
                    wizard._populate_extracted_fields(result)
                    wizard._apply_name_card()

            return request.make_response(
                json.dumps({'result': result}, ensure_ascii=False),
                headers=[('Content-Type', 'application/json; charset=utf-8')],
            )
        except Exception as e:
            _logger.error('Mobile scan error: %s', e)
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500,
            )

    # ── AI Copilot: suggest reply ─────────────────────────────────────────────

    @http.route('/crm/ai/copilot/suggest', type='jsonrpc', auth='user', methods=['POST'])
    def copilot_suggest(self, lead_id: int, channel: str = 'general'):
        """Sinh 2 draft phản hồi từ lịch sử chatter gần nhất của lead."""
        lead = request.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            return {'error': 'Lead không tồn tại'}

        # Lấy 5 messages gần nhất (bỏ internal note)
        messages = request.env['mail.message'].search([
            ('res_id', '=', lead_id),
            ('model', '=', 'crm.lead'),
            ('message_type', 'in', ['email', 'comment']),
            ('subtype_id.internal', '=', False),
        ], order='date desc', limit=5)

        conversation = [
            {
                'author': m.author_id.name or 'Unknown',
                'body': m.body or '',
            }
            for m in reversed(messages)
        ]

        lead_context = (
            f'Lead: {lead.name}, '
            f'Stage: {lead.stage_id.name}, '
            f'Partner: {lead.partner_id.name or lead.contact_name or "N/A"}, '
            f'Product: {lead.product_type or "N/A"}'
        )

        tone = 'informal' if channel == 'zalo' else 'professional'

        from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
        service = CrmAiService(request.env)
        try:
            drafts = service.generate_reply(conversation, lead_context, tone)
            return {'drafts': drafts}
        except Exception as e:
            _logger.error('Copilot suggest error: %s', e)
            return {'error': str(e)}
