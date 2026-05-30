from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)


class CrmAiCallSession(models.Model):
    _name = 'crm.ai.call.session'
    _description = 'AI Call / Meeting Session'
    _order = 'date_start desc'
    _rec_name = 'display_name'

    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity', required=True, ondelete='cascade', index=True)
    session_type = fields.Selection(
        [('call', 'Cuộc gọi'), ('meeting', 'Meeting')],
        string='Loại phiên',
        required=True,
        default='call',
    )
    call_channel = fields.Selection(
        [
            ('twilio', 'Twilio (gọi ra tự động)'),
            ('webrtc', 'Softphone / WebRTC'),
            ('phone_mic', 'Điện thoại thường + Mic máy tính'),
            ('mobile', 'Zalo / App Mobile'),
        ],
        string='Kênh gọi',
        default='webrtc',
    )
    status = fields.Selection(
        [('active', 'Đang gọi'), ('paused', 'Tạm dừng'), ('ended', 'Đã kết thúc'), ('summarized', 'Đã tóm tắt')],
        string='Trạng thái',
        default='active',
        index=True,
    )
    user_id = fields.Many2one('res.users', string='Nhân viên', default=lambda self: self.env.user, index=True)
    date_start = fields.Datetime(string='Bắt đầu', default=fields.Datetime.now)
    date_end = fields.Datetime(string='Kết thúc')
    duration = fields.Float(string='Thời lượng (phút)', compute='_compute_duration', store=True)

    transcript_ids = fields.One2many('crm.ai.transcript.line', 'session_id', string='Transcript')
    transcript_count = fields.Integer(compute='_compute_transcript_count')
    full_transcript = fields.Text(string='Full Transcript', compute='_compute_full_transcript', store=True)

    audio_attachment_id = fields.Many2one('ir.attachment', string='Ghi âm')

    # AI summary fields (populated after session ends)
    summary = fields.Html(string='Tóm tắt')
    action_items_json = fields.Text(string='Action Items (JSON)', default='[]')
    action_items_display = fields.Html(string='Action Items', compute='_compute_action_items_display')
    sentiment = fields.Selection(
        [('positive', 'Tích cực'), ('neutral', 'Trung lập'),
         ('negative', 'Tiêu cực'), ('objection', 'Có phản đối')],
        string='Sentiment',
    )
    detected_needs_json = fields.Text(string='Detected Needs (JSON)', default='[]')
    next_activity_type_id = fields.Many2one('mail.activity.type', string='Bước tiếp theo')
    next_activity_note = fields.Char(string='Ghi chú bước tiếp theo')

    coaching_report_ids = fields.One2many('crm.ai.coaching.report', 'call_session_id', string='Báo cáo Coach')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('lead_id', 'session_type', 'date_start')
    def _compute_display_name(self):
        for rec in self:
            type_label = dict(rec._fields['session_type'].selection).get(rec.session_type, '')
            date_str = rec.date_start.strftime('%d/%m/%Y %H:%M') if rec.date_start else ''
            lead_name = rec.lead_id.name or ''
            rec.display_name = f'{type_label} — {lead_name} — {date_str}'

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.duration = delta.total_seconds() / 60.0
            else:
                rec.duration = 0.0

    @api.depends('transcript_ids')
    def _compute_transcript_count(self):
        for rec in self:
            rec.transcript_count = len(rec.transcript_ids.filtered('is_final'))

    @api.depends('transcript_ids.text', 'transcript_ids.speaker', 'transcript_ids.is_final', 'transcript_ids.sequence')
    def _compute_full_transcript(self):
        for rec in self:
            lines = rec.transcript_ids.filtered('is_final').sorted('sequence')
            speaker_map = {'agent': 'NV', 'customer': 'KH', 'unknown': '?'}
            rec.full_transcript = '\n'.join(
                f'[{speaker_map.get(l.speaker, "?")}] {l.text}' for l in lines
            )

    @api.depends('action_items_json')
    def _compute_action_items_display(self):
        for rec in self:
            try:
                items = json.loads(rec.action_items_json or '[]')
                if items:
                    html = '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'
                else:
                    html = '<em>Không có action item</em>'
            except Exception:
                html = rec.action_items_json or ''
            rec.action_items_display = html

    def action_end_session(self):
        self.ensure_one()
        self.write({'status': 'ended', 'date_end': fields.Datetime.now()})
        self._trigger_ai_summary()
        return {'type': 'ir.actions.act_window_close'}

    def action_pause_session(self):
        self.ensure_one()
        self.write({'status': 'paused'})

    def action_resume_session(self):
        self.ensure_one()
        self.write({'status': 'active'})

    def _trigger_ai_summary(self):
        """Run AI summary in a background thread after current transaction commits."""
        self.ensure_one()
        session_id = self.id
        dbname = self.env.cr.dbname

        def _run_in_thread():
            import time
            time.sleep(2)  # Chờ transaction chính commit xong
            try:
                from odoo.modules.registry import Registry
                from odoo import SUPERUSER_ID
                import odoo.api
                with Registry(dbname).cursor() as cr:
                    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                    session = env['crm.ai.call.session'].browse(session_id)
                    if session.exists():
                        session._run_ai_summary()
            except Exception as e:
                _logger.error('AI summary thread error for session %s: %s', session_id, e, exc_info=True)

        import threading
        t = threading.Thread(target=_run_in_thread, daemon=True)
        t.start()

    def _run_ai_summary(self):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        lead = self.lead_id
        lead_context = (
            f'Lead: {lead.name}, '
            f'Stage: {lead.stage_id.name}, '
            f'Partner: {lead.partner_id.name or lead.contact_name or "N/A"}, '
            f'Product: {lead.product_type or "N/A"}, '
            f'Revenue: {lead.expected_revenue or 0:,.0f} VND'
        )
        transcript = self.full_transcript
        if not transcript:
            # Không có transcript (chưa config STT) → tóm tắt từ context lead
            transcript = f'[Không có transcript — cuộc gọi {self.duration:.0f} phút với {lead_context}]'
        result = service.summarize_call(transcript, lead_context)
        if not result:
            return
        action_items = result.get('action_items', [])
        needs = result.get('detected_needs', [])
        self.write({
            'summary': result.get('summary', ''),
            'action_items_json': json.dumps(action_items, ensure_ascii=False),
            'sentiment': result.get('sentiment', 'neutral'),
            'detected_needs_json': json.dumps(needs, ensure_ascii=False),
            'status': 'summarized',
        })
        # Log call record on lead chatter (log_meeting requires a calendar.event — not applicable here)
        duration_str = f'{self.duration:.0f} phút' if self.duration else 'không rõ'
        date_str = self.date_start.strftime('%d/%m/%Y %H:%M') if self.date_start else ''
        channel_label = dict(self._fields['call_channel'].selection).get(self.call_channel, '')
        self.lead_id._message_log(
            body=f'📞 Cuộc gọi kết thúc: {date_str} — {duration_str} — kênh: {channel_label}'
        )
        # Post summary as internal note
        body = f'<b>AI Tóm tắt {dict(self._fields["session_type"].selection).get(self.session_type)}:</b><br/>'
        body += self.summary or ''
        if action_items:
            body += '<br/><b>Action items:</b><ul>' + ''.join(f'<li>{i}</li>' for i in action_items) + '</ul>'
        self.lead_id.message_post(body=Markup(body), subtype_xmlid='mail.mt_note')
        # Auto-schedule next activity
        next_step = result.get('next_step', '')
        if next_step and self.next_activity_type_id:
            self.lead_id.activity_schedule(
                activity_type_id=self.next_activity_type_id.id,
                summary=next_step[:100],
                user_id=self.user_id.id,
            )
        # Update lead tags from detected needs
        if needs:
            self._update_lead_needs_tags(needs)

    def _update_lead_needs_tags(self, needs: list):
        tag_map = {
            'loan': 'Vay vốn', 'credit_card': 'Thẻ tín dụng', 'savings': 'Tiết kiệm',
            'insurance': 'Bảo hiểm', 'payroll': 'Payroll', 'lc': 'L/C',
            'fx': 'Ngoại tệ', 'pos': 'POS',
        }
        tag_ids = []
        for need in needs:
            tag_name = tag_map.get(need)
            if not tag_name:
                continue
            tag = self.env['crm.tag'].search([('name', '=', tag_name)], limit=1)
            if not tag:
                tag = self.env['crm.tag'].create({'name': tag_name})
            tag_ids.append(tag.id)
        if tag_ids:
            self.lead_id.write({'tag_ids': [(4, tid) for tid in tag_ids]})

    def action_run_ai_summary(self):
        """Chạy lại AI tóm tắt thủ công — dùng khi tóm tắt tự động thất bại."""
        self.ensure_one()
        self._trigger_ai_summary()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'AI đang tóm tắt... Kết quả xuất hiện trong Chatter của Opportunity sau ~30 giây.',
                'type': 'info',
                'sticky': False,
            },
        }

    def action_open_live_call(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/crm/ai/call/live/{self.id}',
            'target': 'new',
        }

    def action_create_coaching_report(self):
        """Tạo báo cáo AI Sales Coach cho phiên gọi này."""
        self.ensure_one()
        report = self.env['crm.ai.coaching.report'].create({
            'call_session_id': self.id,
            'user_id': self.user_id.id or self.env.user.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.ai.coaching.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'new',
        }
