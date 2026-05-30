import hmac
import hashlib
import json
import logging

import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TwilioVoiceController(http.Controller):

    # ── Token cho Twilio.js (browser calling) ────────────────────────────────

    @http.route('/crm/ai/twilio/token', type='jsonrpc', auth='user', readonly=True)
    def get_twilio_token(self, lead_id: int = 0):
        """Tạo Access Token cho Twilio.js để gọi từ trình duyệt."""
        config = request.env['crm.ai.config'].get_config()
        if not config.twilio_account_sid or not config.twilio_auth_token:
            return {'error': 'Twilio chưa được cấu hình'}

        # Tạo Capability Token (không cần twilio SDK — dùng JWT thủ công)
        import time, base64
        account_sid = config.twilio_account_sid
        auth_token = config.twilio_auth_token
        app_sid = config.twilio_twiml_app_sid

        # JWT payload cho Twilio Voice
        now = int(time.time())
        payload = {
            'jti': f'{account_sid}-{now}',
            'iss': account_sid,
            'sub': account_sid,
            'nbf': now,
            'exp': now + 3600,
            'grants': {
                'voice': {
                    'incoming': {'allow': True},
                    'outgoing': {'application_sid': app_sid} if app_sid else {},
                }
            },
        }
        # Twilio dùng JWT với HS256
        header = base64.urlsafe_b64encode(
            json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()
        ).rstrip(b'=').decode()
        body = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        signing_input = f'{header}.{body}'.encode()
        signature = base64.urlsafe_b64encode(
            hmac.new(auth_token.encode(), signing_input, hashlib.sha256).digest()
        ).rstrip(b'=').decode()
        token = f'{header}.{body}.{signature}'

        return {
            'token': token,
            'from_number': config.twilio_phone_number or '',
        }

    # ── Gọi ra qua REST API (không cần browser SDK) ───────────────────────────

    @staticmethod
    def _normalize_phone(number: str) -> str:
        """Chuẩn hoá số điện thoại VN sang E.164 cho Twilio."""
        import re
        n = re.sub(r'[\s\-\.]', '', number.strip())
        # Số VN bắt đầu bằng 0 → +84
        if n.startswith('0') and len(n) == 10:
            return '+84' + n[1:]
        # Số VN +840xxx → +84xxx (bỏ số 0 thừa)
        if n.startswith('+840') and len(n) == 13:
            return '+84' + n[4:]
        # Đã đúng định dạng
        return n if n.startswith('+') else '+' + n

    @http.route('/crm/ai/twilio/call', type='jsonrpc', auth='user', methods=['POST'])
    def make_call(self, lead_id: int, to_number: str, session_id: int = 0):
        """Khởi tạo cuộc gọi ra qua Twilio REST API."""
        config = request.env['crm.ai.config'].sudo().get_config()
        if not all([config.twilio_account_sid, config.twilio_auth_token, config.twilio_phone_number]):
            return {'error': 'Twilio chưa cấu hình đầy đủ (Account SID, Auth Token, From Number)'}
        to_number = self._normalize_phone(to_number)
        _logger.info('Twilio call to (normalized): %s', to_number)

        # Xác định base URL — ưu tiên public_url trong config
        public_url = (config.twilio_public_url or '').rstrip('/')
        if not public_url:
            # Fallback: dùng Twilio demo TwiML (chỉ để test — chỉ phát nhạc)
            twiml_url = 'http://demo.twilio.com/docs/voice.xml'
            status_url = ''
            recording_cb = ''
            _logger.warning(
                'Twilio public_url chưa cấu hình — dùng demo TwiML. '
                'Ghi âm và AI summary sẽ không hoạt động. '
                'Cấu hình ngrok URL tại: CRM → AI Banking → Cấu hình AI → Twilio Voice → Public URL'
            )
        else:
            agent_phone = config.twilio_agent_phone or ''
            twiml_url = f'{public_url}/crm/ai/twilio/voice?lead_id={lead_id}&session_id={session_id}&agent_phone={agent_phone}'
            status_url = f'{public_url}/crm/ai/twilio/status?lead_id={lead_id}&session_id={session_id}'
            recording_cb = f'{public_url}/crm/ai/twilio/recording?session_id={session_id}'

        call_data = {
            'To': to_number,
            'From': config.twilio_phone_number,
            'Url': twiml_url,
        }
        if status_url:
            call_data['StatusCallback'] = status_url
            call_data['StatusCallbackMethod'] = 'POST'
        if recording_cb:
            call_data['Record'] = 'true'
            call_data['RecordingStatusCallback'] = recording_cb

        try:
            resp = requests.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{config.twilio_account_sid}/Calls.json',
                auth=(config.twilio_account_sid, config.twilio_auth_token),
                data=call_data,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            call_sid = data.get('sid', '')
            _logger.info('Twilio call initiated: %s → %s (SID: %s)', config.twilio_phone_number, to_number, call_sid)
            return {'call_sid': call_sid, 'status': data.get('status')}
        except requests.HTTPError as e:
            err = {}
            if e.response is not None:
                try:
                    err = e.response.json()
                except Exception:
                    err = {'message': e.response.text}
            _logger.error('Twilio 400 error — call_data: %s — response: %s', call_data, err)
            # Trả về lỗi đầy đủ để debug
            code = err.get('code', '')
            msg = err.get('message', str(e))
            more_info = err.get('more_info', '')
            return {'error': f'[{code}] {msg}', 'more_info': more_info, 'call_data': {k: v for k, v in call_data.items() if k != 'auth'}}
        except Exception as e:
            return {'error': str(e)}

    # ── Cúp máy từ browser ───────────────────────────────────────────────────

    @http.route('/crm/ai/twilio/hangup', type='jsonrpc', auth='user', methods=['POST'])
    def hangup_call(self, call_sid: str = '', session_id: int = 0):
        """Cúp máy từ browser — gọi Twilio REST để cancel/complete call."""
        config = request.env['crm.ai.config'].sudo().get_config()
        if not call_sid or not all([config.twilio_account_sid, config.twilio_auth_token]):
            return {'ok': False, 'error': 'Thiếu thông tin'}
        try:
            resp = requests.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{config.twilio_account_sid}/Calls/{call_sid}.json',
                auth=(config.twilio_account_sid, config.twilio_auth_token),
                data={'Status': 'completed'},
                timeout=10,
            )
            resp.raise_for_status()
            _logger.info('Twilio call %s cancelled by user', call_sid)
            return {'ok': True}
        except Exception as e:
            _logger.warning('Twilio hangup error: %s', e)
            return {'ok': False, 'error': str(e)}

    # ── TwiML: kịch bản cuộc gọi ─────────────────────────────────────────────

    @http.route('/crm/ai/twilio/voice', type='http', auth='public', csrf=False)
    def twiml_voice(self, lead_id=0, session_id=0, agent_phone='', **kwargs):
        """
        TwiML: Twilio gọi URL này để biết kịch bản cuộc gọi.
        - Nếu có agent_phone: gọi hội nghị 3 bên (agent + customer)
        - Nếu không: gọi thẳng tới customer
        """
        base_url = request.httprequest.host_url.rstrip('/')
        recording_cb = f'{base_url}/crm/ai/twilio/recording?session_id={session_id}'
        status_cb = f'{base_url}/crm/ai/twilio/status?session_id={session_id}'
        customer_number = kwargs.get('To', '')

        if agent_phone:
            # Gọi hội nghị: nhân viên nghe máy trước, sau đó kết nối khách vào
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial record="record-from-answer"
          recordingStatusCallback="{recording_cb}"
          recordingStatusCallbackMethod="POST">
        <Conference beep="false"
                    record="record-from-start"
                    recordingStatusCallback="{recording_cb}"
                    statusCallback="{status_cb}"
                    statusCallbackEvent="end"
                    maxParticipants="2">crm-session-{session_id}</Conference>
    </Dial>
</Response>'''
        else:
            # Gọi thẳng tới khách (nhân viên không nghe qua Twilio)
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial record="record-from-answer"
          recordingStatusCallback="{recording_cb}"
          recordingStatusCallbackMethod="POST">
        <Number statusCallback="{status_cb}"
                statusCallbackEvent="completed"
                statusCallbackMethod="POST">{customer_number}</Number>
    </Dial>
</Response>'''

        return request.make_response(twiml, headers=[('Content-Type', 'text/xml')])

    # ── Status callback ───────────────────────────────────────────────────────

    @http.route('/crm/ai/twilio/status', type='http', auth='public', csrf=False, methods=['POST'])
    def twilio_status(self, lead_id=0, session_id=0, **kwargs):
        """Twilio gọi URL này khi trạng thái cuộc gọi thay đổi."""
        call_status = kwargs.get('CallStatus', '')
        call_duration = kwargs.get('CallDuration', 0)
        _logger.info('Twilio call status: %s (duration: %ss, session: %s)', call_status, call_duration, session_id)

        if call_status == 'completed' and session_id:
            try:
                sid = int(session_id)
                session = request.env['crm.ai.call.session'].sudo().browse(sid)
                if session.exists() and session.status not in ('ended', 'summarized'):
                    session.sudo().write({
                        'status': 'ended',
                        'duration': float(call_duration) / 60.0 if call_duration else 0,
                    })
                    # Không trigger AI summary ngay — để recording callback làm (có transcript đầy đủ hơn).
                    # Chỉ trigger nếu Twilio không record (không có RecordingUrl trong config).
                    config = request.env['crm.ai.config'].sudo().get_config()
                    if not config.twilio_public_url:
                        session.sudo()._trigger_ai_summary()
            except Exception as e:
                _logger.error('Error updating session from Twilio status: %s', e)

        return request.make_response('', headers=[('Content-Type', 'text/xml')])

    # ── Recording callback ────────────────────────────────────────────────────

    @http.route('/crm/ai/twilio/recording', type='http', auth='public', csrf=False, methods=['POST'])
    def twilio_recording(self, session_id=0, **kwargs):
        """Twilio gọi URL này khi ghi âm hoàn thành — download và transcribe."""
        recording_url = kwargs.get('RecordingUrl', '')
        recording_sid = kwargs.get('RecordingSid', '')
        if not recording_url or not session_id:
            return request.make_response('ok')

        _logger.info('Twilio recording ready: %s (session: %s)', recording_sid, session_id)

        # Download ghi âm và transcribe async
        config = request.env['crm.ai.config'].sudo().get_config()
        dbname = request.env.cr.dbname
        sid = int(session_id)

        def _download_and_transcribe():
            import time
            time.sleep(3)
            try:
                # Download MP3 từ Twilio
                audio_resp = requests.get(
                    f'{recording_url}.mp3',
                    auth=(config.twilio_account_sid, config.twilio_auth_token),
                    timeout=60,
                )
                audio_resp.raise_for_status()
                audio_bytes = audio_resp.content

                from odoo.modules.registry import Registry
                from odoo import SUPERUSER_ID
                import odoo.api
                with Registry(dbname).cursor() as cr:
                    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                    session = env['crm.ai.call.session'].browse(sid)
                    if not session.exists():
                        return
                    # STT
                    from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
                    service = CrmAiService(env)
                    transcript_text = service.transcribe_audio(audio_bytes, 'audio/mpeg')
                    if transcript_text:
                        lines = [l.strip() for l in transcript_text.split('\n') if l.strip()]
                        for i, line in enumerate(lines):
                            env['crm.ai.transcript.line'].create({
                                'session_id': sid,
                                'sequence': (i + 1) * 10,
                                'speaker': 'unknown',
                                'text': line,
                                'is_final': True,
                            })
                    session._run_ai_summary()
            except Exception as e:
                _logger.error('Twilio recording transcribe error: %s', e, exc_info=True)

        import threading
        threading.Thread(target=_download_and_transcribe, daemon=True).start()
        return request.make_response('ok')
