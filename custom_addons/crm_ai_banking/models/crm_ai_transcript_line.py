from odoo import models, fields, api


class CrmAiTranscriptLine(models.Model):
    _name = 'crm.ai.transcript.line'
    _description = 'Realtime Transcript Line'
    _order = 'session_id, sequence'

    session_id = fields.Many2one('crm.ai.call.session', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    speaker = fields.Selection(
        [('agent', 'Nhân viên'), ('customer', 'Khách hàng'), ('unknown', 'Không rõ')],
        default='unknown',
    )
    text = fields.Text(string='Nội dung', required=True)
    timestamp = fields.Float(string='Thời điểm (giây)', default=0.0)
    is_final = fields.Boolean(string='Đã xác nhận', default=False)

    @api.model
    def create_or_update_partial(self, session_id: int, sequence: int, speaker: str,
                                  text: str, timestamp: float, is_final: bool):
        """Upsert a transcript line. Called from WebSocket controller."""
        existing = self.search([('session_id', '=', session_id), ('sequence', '=', sequence)], limit=1)
        vals = {'speaker': speaker, 'text': text, 'timestamp': timestamp, 'is_final': is_final}
        if existing:
            existing.write(vals)
            return existing.id
        vals.update({'session_id': session_id, 'sequence': sequence})
        new = self.create(vals)
        return new.id
