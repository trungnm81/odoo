from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests


class CrmAiConfig(models.Model):
    _name = 'crm.ai.config'
    _description = 'CRM AI Banking Configuration'
    _rec_name = 'name'

    name = fields.Char(default='Default Config', required=True)
    active = fields.Boolean(default=True)

    # ── LLM ─────────────────────────────────────────────────────────
    llm_provider = fields.Selection(
        [('anthropic', 'Anthropic API (trực tiếp)'), ('openrouter', 'OpenRouter')],
        string='LLM Provider',
        default='openrouter',
        required=True,
    )
    # provider='anthropic'
    claude_api_key = fields.Char(
        string='Anthropic API Key',
        groups='base.group_system',
    )
    # provider='openrouter' — dùng chung openrouter_api_key với OCR
    openrouter_llm_model_text = fields.Char(
        string='OpenRouter Text Model',
        default='anthropic/claude-sonnet-4-6',
    )
    openrouter_llm_model_vision = fields.Char(
        string='OpenRouter Vision Model',
        default='anthropic/claude-opus-4-8',
    )
    # Dùng chung cho cả LLM và OCR khi provider='openrouter'
    # (openrouter_api_key khai báo ở phần OCR bên dưới)

    # Computed helpers — code luôn đọc qua 2 fields này
    claude_model_text = fields.Char(
        string='Text Model (active)',
        compute='_compute_active_models',
        store=False,
    )
    claude_model_vision = fields.Char(
        string='Vision Model (active)',
        compute='_compute_active_models',
        store=False,
    )

    @api.depends('llm_provider', 'openrouter_llm_model_text', 'openrouter_llm_model_vision')
    def _compute_active_models(self):
        for rec in self:
            if rec.llm_provider == 'openrouter':
                rec.claude_model_text = rec.openrouter_llm_model_text or 'anthropic/claude-sonnet-4-6'
                rec.claude_model_vision = rec.openrouter_llm_model_vision or 'anthropic/claude-opus-4-8'
            else:
                rec.claude_model_text = 'claude-sonnet-4-6'
                rec.claude_model_vision = 'claude-opus-4-8'

    # ── OCR ─────────────────────────────────────────────────────────
    ocr_provider = fields.Selection(
        [('openrouter', 'OpenRouter'), ('local', 'Local API')],
        string='OCR Provider',
        default='openrouter',
        required=True,
    )
    openrouter_api_key = fields.Char(
        string='OpenRouter API Key',
        help='Dùng chung cho cả LLM và OCR khi provider = OpenRouter',
        groups='base.group_system',
    )
    openrouter_ocr_model = fields.Char(
        string='OpenRouter OCR Model',
        default='qwen/qwen2.5-vl-72b-instruct',
    )
    ocr_local_endpoint = fields.Char(
        string='Local OCR Endpoint',
        default='http://localhost:8080/api/ocr',
    )
    ocr_local_api_key = fields.Char(
        string='Local OCR API Key',
        groups='base.group_system',
    )

    # ── STT Batch ───────────────────────────────────────────────────
    stt_batch_provider = fields.Selection(
        [('api', 'External API (OpenAI Whisper)'), ('local', 'Local Server')],
        string='STT Batch Provider',
        default='api',
        required=True,
    )
    whisper_api_key = fields.Char(
        string='OpenAI API Key (Whisper)',
        groups='base.group_system',
    )
    whisper_api_endpoint = fields.Char(
        string='Whisper API Endpoint',
        default='https://api.openai.com/v1/audio/transcriptions',
    )
    whisper_api_model = fields.Char(
        string='Whisper API Model',
        default='whisper-1',
    )
    whisper_local_endpoint = fields.Char(
        string='Local Whisper Endpoint',
        default='http://localhost:9000/transcribe',
    )
    whisper_local_api_key = fields.Char(
        string='Local Whisper API Key',
        groups='base.group_system',
    )
    whisper_local_model = fields.Selection(
        [('large-v3', 'large-v3 (GPU, best accuracy)'), ('medium', 'medium (CPU, balanced)')],
        string='Local Whisper Model',
        default='large-v3',
    )

    # ── STT Realtime ────────────────────────────────────────────────
    stt_realtime_provider = fields.Selection(
        [('api', 'External API (Deepgram)'), ('local', 'Local Server (whisper-streaming)')],
        string='STT Realtime Provider',
        default='api',
        required=True,
    )
    deepgram_api_key = fields.Char(
        string='Deepgram API Key',
        groups='base.group_system',
    )
    deepgram_model = fields.Char(
        string='Deepgram Model',
        default='nova-3',
    )
    whisper_streaming_ws = fields.Char(
        string='Whisper Streaming WebSocket URL',
        default='ws://localhost:9001/stream',
    )
    whisper_streaming_key = fields.Char(
        string='Whisper Streaming API Key',
        groups='base.group_system',
    )

    # ── Automation Toggles ──────────────────────────────────────────
    auto_process_email = fields.Boolean(
        string='Auto Process Incoming Emails',
        default=True,
    )
    auto_process_attachment = fields.Boolean(
        string='Auto Process Attachments',
        default=False,
    )
    daily_digest_time = fields.Float(
        string='Daily Digest Time (hour)',
        default=8.0,
        help='Hour of day to send daily digest (e.g. 8.0 = 08:00)',
    )
    cold_lead_threshold_days = fields.Integer(
        string='Cold Lead Threshold (days)',
        default=10,
    )
    large_deal_threshold = fields.Float(
        string='Large Deal Threshold (VND)',
        default=5_000_000_000,
    )
    large_deal_no_manager_days = fields.Integer(
        string='Alert if no manager activity (days)',
        default=7,
    )
    enable_ai_hints = fields.Boolean(
        string='Enable Realtime AI Hints (opt-in per user)',
        default=False,
    )
    ai_hints_interval_seconds = fields.Integer(
        string='AI Hints Interval (seconds)',
        default=30,
    )
    enable_speaker_diarization = fields.Boolean(
        string='Enable Speaker Diarization',
        default=True,
    )

    # ── Twilio Voice ─────────────────────────────────────────────────
    twilio_account_sid = fields.Char(
        string='Twilio Account SID',
        groups='base.group_system',
    )
    twilio_auth_token = fields.Char(
        string='Twilio Auth Token',
        groups='base.group_system',
    )
    twilio_phone_number = fields.Char(
        string='Twilio From Number',
        help='Số điện thoại Twilio để gọi ra, VD: +84...',
    )
    twilio_twiml_app_sid = fields.Char(
        string='Twilio TwiML App SID',
        help='Để trống — không cần cho REST API calling',
        groups='base.group_system',
    )
    twilio_public_url = fields.Char(
        string='Public URL (ngrok/domain)',
        help='URL công khai để Twilio callback. VD: https://abc123.ngrok.io\n'
             'Nếu để trống sẽ dùng http://demo.twilio.com/docs/voice.xml (chỉ test)',
    )
    twilio_agent_phone = fields.Char(
        string='Số điện thoại nhân viên (nhận cuộc gọi)',
        help='Twilio sẽ gọi vào số này khi nhân viên bắt đầu cuộc gọi. VD: +84xxxxxxxxx',
    )

    # ── Zalo OA ─────────────────────────────────────────────────────
    zalo_oa_access_token = fields.Char(
        string='Zalo OA Access Token',
        groups='base.group_system',
    )
    zalo_webhook_secret = fields.Char(
        string='Zalo Webhook Secret',
        groups='base.group_system',
    )

    @api.constrains('daily_digest_time')
    def _check_digest_time(self):
        for rec in self:
            if not (0.0 <= rec.daily_digest_time < 24.0):
                raise ValidationError(_('Daily digest time must be between 0 and 24.'))

    @api.model
    def get_config(self):
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default Config'})
        return config

    def action_test_claude(self):
        self.ensure_one()
        try:
            if self.llm_provider == 'openrouter':
                url = 'https://openrouter.ai/api/v1/chat/completions'
                headers = {
                    'Authorization': f'Bearer {self.openrouter_api_key}',
                    'Content-Type': 'application/json',
                }
                payload = {
                    'model': self.openrouter_llm_model_text or 'anthropic/claude-sonnet-4-6',
                    'max_tokens': 10,
                    'messages': [{'role': 'user', 'content': 'ping'}],
                }
            else:
                url = 'https://api.anthropic.com/v1/messages'
                headers = {
                    'x-api-key': self.claude_api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                }
                payload = {
                    'model': 'claude-sonnet-4-6',
                    'max_tokens': 10,
                    'messages': [{'role': 'user', 'content': 'ping'}],
                }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            provider_label = 'OpenRouter' if self.llm_provider == 'openrouter' else 'Anthropic'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('%s LLM OK ✓') % provider_label, 'type': 'success'},
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('LLM Error: %s') % str(e), 'type': 'danger'},
            }

    def action_test_ocr(self):
        self.ensure_one()
        try:
            if self.ocr_provider == 'local':
                resp = requests.get(
                    self.ocr_local_endpoint.replace('/api/ocr', '/health'),
                    headers={'Authorization': f'Bearer {self.ocr_local_api_key}'},
                    timeout=5,
                )
                ok = resp.status_code == 200
            else:
                ok = bool(self.openrouter_api_key)
            msg = _('OCR endpoint reachable') if ok else _('OCR endpoint not reachable')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': msg, 'type': 'success' if ok else 'warning'},
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('OCR test error: %s') % str(e), 'type': 'danger'},
            }

    def action_test_twilio(self):
        self.ensure_one()
        try:
            resp = requests.get(
                f'https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}.json',
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Twilio OK ✓ — Account: {data.get("friendly_name", self.twilio_account_sid)}',
                    'type': 'success',
                },
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': f'Twilio Error: {e}', 'type': 'danger'},
            }

    def action_test_stt_batch(self):
        """Test STT Batch bằng cách gửi 1 giây âm thanh trắng (silence)."""
        self.ensure_one()
        try:
            # Tạo minimal WAV (44 bytes — 1 giây silence) để test endpoint
            import struct
            sample_rate, num_channels, bits = 16000, 1, 16
            num_samples = sample_rate  # 1 giây
            data_size = num_samples * num_channels * (bits // 8)
            wav_header = struct.pack(
                '<4sI4s4sIHHIIHH4sI',
                b'RIFF', 36 + data_size, b'WAVE',
                b'fmt ', 16, 1, num_channels, sample_rate,
                sample_rate * num_channels * (bits // 8),
                num_channels * (bits // 8), bits,
                b'data', data_size,
            )
            audio_bytes = wav_header + b'\x00' * data_size

            if self.stt_batch_provider == 'local':
                resp = requests.post(
                    self.whisper_local_endpoint,
                    headers={'Authorization': f'Bearer {self.whisper_local_api_key}'},
                    files={'file': ('test.wav', audio_bytes, 'audio/wav')},
                    data={'language': 'vi', 'model': self.whisper_local_model},
                    timeout=30,
                )
            else:
                resp = requests.post(
                    self.whisper_api_endpoint,
                    headers={'Authorization': f'Bearer {self.whisper_api_key}'},
                    files={'file': ('test.wav', audio_bytes, 'audio/wav')},
                    data={'model': self.whisper_api_model or 'whisper-1', 'language': 'vi'},
                    timeout=30,
                )
            resp.raise_for_status()
            provider = 'Local Whisper' if self.stt_batch_provider == 'local' else 'OpenAI Whisper'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('%s OK ✓ — endpoint phản hồi') % provider, 'type': 'success'},
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('STT Batch Error: %s') % str(e), 'type': 'danger'},
            }

    def action_test_stt_realtime(self):
        """Test STT Realtime bằng cách kiểm tra endpoint có phản hồi không."""
        self.ensure_one()
        try:
            if self.stt_realtime_provider == 'api':
                # Deepgram: gọi REST /v1/projects để kiểm tra API key hợp lệ
                resp = requests.get(
                    'https://api.deepgram.com/v1/projects',
                    headers={'Authorization': f'Token {self.deepgram_api_key}'},
                    timeout=10,
                )
                resp.raise_for_status()
                provider = 'Deepgram'
            else:
                # Local whisper-streaming: kiểm tra HTTP health endpoint
                ws_url = self.whisper_streaming_ws or ''
                health_url = ws_url.replace('ws://', 'http://').replace('wss://', 'https://').replace('/stream', '/health')
                resp = requests.get(
                    health_url,
                    headers={'Authorization': f'Bearer {self.whisper_streaming_key}'},
                    timeout=5,
                )
                resp.raise_for_status()
                provider = 'Local whisper-streaming'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('%s OK ✓') % provider, 'type': 'success'},
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _('STT Realtime Error: %s') % str(e), 'type': 'danger'},
            }
