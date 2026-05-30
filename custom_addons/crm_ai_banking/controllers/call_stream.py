import json
import logging
import base64
import threading

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Per-session STT WebSocket connections (provider='api' uses Deepgram)
_stt_connections = {}
_stt_lock = threading.Lock()


class CrmAiCallStreamController(http.Controller):

    @http.route('/crm/ai/call/start', type='jsonrpc', auth='user', methods=['POST'])
    def start_call_session(self, lead_id: int, session_type: str = 'call', call_channel: str = 'webrtc'):
        """Create a new call session and return session_id."""
        lead = request.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            return {'error': 'Lead not found'}
        session = request.env['crm.ai.call.session'].create({
            'lead_id': lead_id,
            'session_type': session_type,
            'call_channel': call_channel,
            'user_id': request.env.user.id,
        })
        return {
            'session_id': session.id,
            'lead_name': lead.name,
            'call_channel': call_channel,
        }

    @http.route('/crm/ai/call/end', type='jsonrpc', auth='user', methods=['POST'])
    def end_call_session(self, session_id: int):
        """End session and trigger async AI summary."""
        session = request.env['crm.ai.call.session'].browse(session_id)
        if not session.exists():
            return {'error': 'Session not found'}
        session.action_end_session()
        return {'status': 'ended', 'duration': session.duration}

    @http.route('/crm/ai/call/transcript/add', type='jsonrpc', auth='user', methods=['POST'])
    def add_transcript_line(self, session_id: int, sequence: int, speaker: str,
                             text: str, timestamp: float = 0.0, is_final: bool = False):
        """Add or update a transcript line. Called by frontend after receiving STT result."""
        line_id = request.env['crm.ai.transcript.line'].create_or_update_partial(
            session_id=session_id,
            sequence=sequence,
            speaker=speaker,
            text=text,
            timestamp=timestamp,
            is_final=is_final,
        )
        # Broadcast to all clients watching this session via Odoo bus
        request.env['bus.bus']._sendone(
            f'crm_ai_call_{session_id}',
            'transcript_update',
            {
                'session_id': session_id,
                'line_id': line_id,
                'sequence': sequence,
                'speaker': speaker,
                'text': text,
                'timestamp': timestamp,
                'is_final': is_final,
            },
        )
        return {'line_id': line_id}

    @http.route('/crm/ai/call/hints', type='jsonrpc', auth='user', methods=['POST'])
    def get_ai_hints(self, session_id: int, product_type: str = ''):
        """Get realtime AI hints. Called by frontend when user enables hints toggle."""
        session = request.env['crm.ai.call.session'].browse(session_id)
        if not session.exists():
            return {}
        # Lấy transcript trực tiếp từ lines (không dùng computed field có thể stale)
        lines = session.transcript_ids.filtered('is_final').sorted('sequence')
        speaker_map = {'agent': 'NV', 'customer': 'KH', 'unknown': '?'}
        transcript = '\n'.join(
            f'[{speaker_map.get(l.speaker, "?")}] {l.text}' for l in lines
        )
        if not transcript:
            return {'missing_questions': [], 'suggested_question': 'Hãy bắt đầu cuộc trò chuyện', 'alert': None}
        from ..models.crm_ai_service import CrmAiService
        service = CrmAiService(request.env)
        product_type = product_type or session.lead_id.product_type or ''
        return service.get_ai_hints(transcript, product_type)

    @http.route('/crm/ai/call/upload_audio', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_audio(self):
        """
        Nhận file audio từ browser (chế độ ghi âm batch).
        Gọi STT → lưu transcript vào session → trigger AI summary.
        """
        audio_file = request.httprequest.files.get('audio')
        session_id = int(request.httprequest.form.get('session_id', 0))
        if not audio_file or not session_id:
            return request.make_json_response({'error': 'missing audio or session_id'}, status=400)

        session = request.env['crm.ai.call.session'].browse(session_id)
        if not session.exists():
            return request.make_json_response({'error': 'session not found'}, status=404)

        audio_bytes = audio_file.read()
        mime = audio_file.mimetype or 'audio/webm'

        # Batch STT
        from ..models.crm_ai_service import CrmAiService
        service = CrmAiService(request.env)
        transcript_text = ''
        try:
            transcript_text = service.transcribe_audio(audio_bytes, mime)
        except Exception as e:
            _logger.error('STT error for session %s: %s', session_id, e)

        # Lưu transcript lines
        if transcript_text:
            lines = [l.strip() for l in transcript_text.split('\n') if l.strip()]
            for i, line in enumerate(lines):
                request.env['crm.ai.transcript.line'].create({
                    'session_id': session_id,
                    'sequence': (i + 1) * 10,
                    'speaker': 'unknown',
                    'text': line,
                    'is_final': True,
                })

        # Kết thúc session và trigger summary async
        session.write({'status': 'ended'})
        session._trigger_ai_summary()

        return request.make_json_response({
            'status': 'ok',
            'transcript': transcript_text,
            'lines': len(transcript_text.split('\n')) if transcript_text else 0,
        })

    @http.route('/crm/ai/call/stt_config', type='jsonrpc', auth='user', readonly=True)
    def get_stt_config(self):
        """Return STT config for frontend to connect to correct streaming provider."""
        config = request.env['crm.ai.config'].get_config()
        if config.stt_realtime_provider == 'api':
            return {
                'provider': 'deepgram',
                'api_key': config.deepgram_api_key or '',
                'model': config.deepgram_model or 'nova-3',
                'language': 'vi',
                'diarize': config.enable_speaker_diarization,
            }
        else:
            return {
                'provider': 'local',
                'ws_url': config.whisper_streaming_ws or 'ws://localhost:9001/stream',
                'api_key': config.whisper_streaming_key or '',
                'language': 'vi',
            }

    @http.route('/crm/ai/call/session/<int:session_id>', type='jsonrpc', auth='user', readonly=True)
    def get_session(self, session_id: int):
        session = request.env['crm.ai.call.session'].browse(session_id)
        if not session.exists():
            return {}
        lines = session.transcript_ids.sorted('sequence')
        return {
            'id': session.id,
            'lead_id': session.lead_id.id,
            'lead_name': session.lead_id.name,
            'session_type': session.session_type,
            'call_channel': session.call_channel,
            'status': session.status,
            'date_start': session.date_start.isoformat() if session.date_start else None,
            'summary': session.summary or '',
            'action_items': json.loads(session.action_items_json or '[]'),
            'sentiment': session.sentiment or '',
            'transcript': [
                {
                    'sequence': l.sequence,
                    'speaker': l.speaker,
                    'text': l.text,
                    'timestamp': l.timestamp,
                    'is_final': l.is_final,
                }
                for l in lines
            ],
        }
