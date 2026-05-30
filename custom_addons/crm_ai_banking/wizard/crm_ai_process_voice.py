from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class CrmAiProcessVoice(models.TransientModel):
    _name = 'crm.ai.process.voice'
    _description = 'Upload Audio for AI Transcription'

    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity', required=True)
    session_type = fields.Selection(
        [('call', 'Cuộc gọi'), ('meeting', 'Meeting')],
        string='Loại',
        default='call',
        required=True,
    )
    audio_file = fields.Binary(string='File Audio', required=True)
    audio_filename = fields.Char(string='Tên file')
    transcript = fields.Text(string='Transcript', readonly=True)
    state = fields.Selection(
        [('upload', 'Upload'), ('transcribed', 'Đã transcript'), ('done', 'Hoàn thành')],
        default='upload',
    )

    def action_transcribe(self):
        self.ensure_one()
        if not self.audio_file:
            raise UserError(_('Vui lòng upload file audio.'))
        from ..models.crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        audio_bytes = base64.b64decode(self.audio_file)
        mime = 'audio/mpeg'
        if self.audio_filename:
            if self.audio_filename.endswith('.wav'):
                mime = 'audio/wav'
            elif self.audio_filename.endswith('.m4a'):
                mime = 'audio/m4a'
            elif self.audio_filename.endswith('.ogg'):
                mime = 'audio/ogg'
        transcript = service.transcribe_audio(audio_bytes, mime)
        if not transcript:
            raise UserError(_('Không thể transcript audio. Kiểm tra cấu hình STT.'))
        self.write({'transcript': transcript, 'state': 'transcribed'})
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_create_session(self):
        self.ensure_one()
        if not self.transcript:
            raise UserError(_('Chưa có transcript. Vui lòng bấm Transcribe trước.'))
        session = self.env['crm.ai.call.session'].create({
            'lead_id': self.lead_id.id,
            'session_type': self.session_type,
            'call_channel': 'mobile',
            'status': 'ended',
        })
        # Create transcript lines from text
        lines = self.transcript.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                self.env['crm.ai.transcript.line'].create({
                    'session_id': session.id,
                    'sequence': (i + 1) * 10,
                    'speaker': 'unknown',
                    'text': line.strip(),
                    'is_final': True,
                })
        session._trigger_ai_summary()
        self.write({'state': 'done'})
        return {'type': 'ir.actions.act_window_close'}
