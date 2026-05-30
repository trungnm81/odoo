import json
import logging
import threading

from markupsafe import Markup, escape

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmAiCoachingReport(models.Model):
    _name = 'crm.ai.coaching.report'
    _description = 'Báo cáo AI Sales Coach'
    _order = 'report_date desc'

    call_session_id = fields.Many2one(
        'crm.ai.call.session', string='Phiên gọi', required=True, ondelete='cascade', index=True,
    )
    user_id = fields.Many2one('res.users', string='Nhân viên', required=True)
    lead_id = fields.Many2one(related='call_session_id.lead_id', string='Lead', store=True)
    report_date = fields.Date(string='Ngày', default=fields.Date.today)
    visible_to_user = fields.Boolean(string='Hiện cho nhân viên', default=True)

    score_opening = fields.Float(string='Chào hỏi', digits=(4, 1))
    score_needs_discovery = fields.Float(string='Khám phá nhu cầu', digits=(4, 1))
    score_product_fit = fields.Float(string='Kết nối sản phẩm', digits=(4, 1))
    score_objection = fields.Float(string='Xử lý từ chối', digits=(4, 1))
    score_closing = fields.Float(string='Kỹ năng chốt', digits=(4, 1))
    score_overall = fields.Float(string='Tổng thể', digits=(4, 1), compute='_compute_overall', store=True)

    strengths_json = fields.Text(string='Điểm mạnh (JSON)', default='[]')
    improvements_json = fields.Text(string='Cần cải thiện (JSON)', default='[]')
    missed_opportunities_json = fields.Text(string='Cơ hội bỏ lỡ (JSON)', default='[]')
    key_moments_json = fields.Text(string='Khoảnh khắc quan trọng (JSON)', default='[]')

    coaching_html = fields.Html(string='Báo cáo Coach', compute='_compute_coaching_html', store=False)
    processing_status = fields.Selection([
        ('draft', 'Chưa xử lý'), ('processing', 'Đang xử lý'),
        ('done', 'Hoàn thành'), ('error', 'Lỗi'),
    ], string='Trạng thái', default='draft')

    @api.depends('score_opening', 'score_needs_discovery', 'score_product_fit',
                 'score_objection', 'score_closing')
    def _compute_overall(self):
        for rec in self:
            scores = [s for s in [
                rec.score_opening, rec.score_needs_discovery,
                rec.score_product_fit, rec.score_objection, rec.score_closing,
            ] if s > 0]
            rec.score_overall = sum(scores) / len(scores) if scores else 0.0

    @api.depends('strengths_json', 'improvements_json', 'key_moments_json',
                 'missed_opportunities_json', 'score_overall', 'processing_status')
    def _compute_coaching_html(self):
        for rec in self:
            if rec.processing_status == 'processing':
                rec.coaching_html = Markup('<em class="text-muted">⏳ Đang phân tích...</em>')
                continue
            if rec.processing_status == 'draft':
                rec.coaching_html = Markup('<em class="text-muted">Nhấn "Phân tích AI" để tạo báo cáo coach.</em>')
                continue

            html = ['<div class="o_coaching_report">']

            scores = [
                ('Chào hỏi', rec.score_opening), ('Khám phá', rec.score_needs_discovery),
                ('Sản phẩm', rec.score_product_fit), ('Từ chối', rec.score_objection),
                ('Chốt sale', rec.score_closing),
            ]
            html.append('<div class="d-flex flex-wrap gap-2 mb-3">')
            for label, score in scores:
                cls = 'success' if score >= 7 else 'warning' if score >= 5 else 'danger'
                html.append(
                    f'<div class="text-center border rounded p-2" style="min-width:80px">'
                    f'<div class="fs-5 fw-bold text-{cls}">{score:.1f}</div>'
                    f'<div class="small text-muted">{label}</div></div>'
                )
            overall_cls = 'success' if rec.score_overall >= 7 else 'warning' if rec.score_overall >= 5 else 'danger'
            html.append(
                f'<div class="text-center border rounded p-2 bg-light" style="min-width:80px">'
                f'<div class="fs-5 fw-bold text-{overall_cls}">{rec.score_overall:.1f}</div>'
                f'<div class="small fw-bold">Tổng thể</div></div>'
            )
            html.append('</div>')

            def _section(json_str, icon, title):
                try:
                    items = json.loads(json_str or '[]')
                    if not items:
                        return ''
                    rows = ''
                    for it in items:
                        if isinstance(it, dict):
                            rows += f'<li><strong>{escape(it.get("text", ""))}</strong>'
                            if it.get('feedback'):
                                rows += f'<br/><em class="text-muted small">→ {escape(it["feedback"])}</em>'
                            rows += '</li>'
                        else:
                            rows += f'<li>{escape(str(it))}</li>'
                    return f'<div class="mb-2"><b>{icon} {title}:</b><ul class="mb-1">{rows}</ul></div>'
                except Exception:
                    return ''

            html.append(_section(rec.strengths_json, '✅', 'Điểm mạnh'))
            html.append(_section(rec.improvements_json, '📈', 'Cần cải thiện'))
            html.append(_section(rec.missed_opportunities_json, '⚠️', 'Cơ hội bỏ lỡ'))
            html.append(_section(rec.key_moments_json, '🎯', 'Khoảnh khắc quan trọng'))
            html.append('</div>')
            rec.coaching_html = Markup(''.join(html))

    def action_generate_coaching(self):
        """Phân tích transcript cuộc gọi và tạo báo cáo coach."""
        self.ensure_one()
        self.write({'processing_status': 'processing'})
        dbname = self.env.cr.dbname
        rec_id = self.id

        def _run():
            import time
            time.sleep(2)
            try:
                from odoo.modules.registry import Registry
                from odoo import SUPERUSER_ID
                import odoo.api
                with Registry(dbname).cursor() as cr:
                    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                    rec = env['crm.ai.coaching.report'].browse(rec_id)
                    if rec.exists():
                        rec._do_generate()
            except Exception as e:
                _logger.error('CoachingReport async error: %s', e, exc_info=True)

        threading.Thread(target=_run, daemon=True).start()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang phân tích cuộc gọi... Kết quả sẽ xuất hiện sau ~30 giây.',
                'type': 'info', 'sticky': False,
            },
        }

    def _do_generate(self):
        try:
            session = self.call_session_id
            transcript_lines = session.transcript_ids.sorted('sequence')
            transcript = '\n'.join(
                f'[{line.speaker.upper()}] {line.text}' for line in transcript_lines if line.text
            )
            if not transcript.strip():
                self.write({'processing_status': 'error', 'error_message': 'Không có transcript để phân tích'})
                return

            from .crm_ai_service import CrmAiService
            service = CrmAiService(self.env)
            product_type = session.lead_id.product_type if session.lead_id else ''
            result = service.analyze_call_coaching(transcript, product_type)

            if not result:
                self.write({'processing_status': 'error', 'error_message': 'AI không trả về kết quả'})
                return

            scores = result.get('scores', {})
            self.write({
                'score_opening': float(scores.get('opening', 0)),
                'score_needs_discovery': float(scores.get('needs_discovery', 0)),
                'score_product_fit': float(scores.get('product_fit', 0)),
                'score_objection': float(scores.get('objection', 0)),
                'score_closing': float(scores.get('closing', 0)),
                'strengths_json': json.dumps(result.get('strengths', []), ensure_ascii=False),
                'improvements_json': json.dumps(result.get('improvements', []), ensure_ascii=False),
                'missed_opportunities_json': json.dumps(result.get('missed_opportunities', []), ensure_ascii=False),
                'key_moments_json': json.dumps(result.get('key_moments', []), ensure_ascii=False),
                'processing_status': 'done',
            })
        except Exception as e:
            _logger.error('CoachingReport._do_generate: %s', e, exc_info=True)
            self.write({'processing_status': 'error', 'error_message': str(e)[:250]})
