import base64
import json
import logging

from markupsafe import Markup, escape
import threading

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmAiDocument(models.Model):
    _name = 'crm.ai.document'
    _description = 'AI Phân tích tài liệu (BCTC / GPKD / Khác)'
    _order = 'create_date desc'

    lead_id = fields.Many2one('crm.lead', string='Lead', index=True, ondelete='cascade')
    document_type = fields.Selection([
        ('bctc', 'Báo cáo tài chính (BCTC)'),
        ('gpkd', 'Giấy phép kinh doanh (GPKD)'),
        ('bank_statement', 'Sao kê ngân hàng'),
        ('contract', 'Hợp đồng'),
        ('other', 'Khác'),
    ], string='Loại tài liệu', required=True, default='bctc')

    attachment_id = fields.Many2one('ir.attachment', string='File đính kèm')
    attachment_name = fields.Char(related='attachment_id.name', string='Tên file', readonly=True)

    ocr_raw_text = fields.Text(string='Văn bản OCR thô')
    ai_highlights_json = fields.Text(string='Điểm nổi bật (JSON)', default='[]')
    ai_questions_json = fields.Text(string='Câu hỏi gợi ý (JSON)', default='[]')
    ai_analysis_html = fields.Html(string='Kết quả phân tích', compute='_compute_analysis_html', store=False)

    processing_status = fields.Selection([
        ('draft', 'Chưa xử lý'),
        ('processing', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
        ('error', 'Lỗi'),
    ], string='Trạng thái', default='draft')
    error_message = fields.Char(string='Lỗi')
    year = fields.Char(string='Năm tài chính')
    name = fields.Char(string='Tiêu đề', compute='_compute_name', store=True)

    @api.depends('document_type', 'lead_id', 'year')
    def _compute_name(self):
        type_map = dict(self._fields['document_type'].selection)
        for rec in self:
            parts = [type_map.get(rec.document_type, 'Tài liệu')]
            if rec.year:
                parts.append(rec.year)
            if rec.lead_id:
                parts.append(rec.lead_id.name or '')
            rec.name = ' — '.join(p for p in parts if p)

    @api.depends('ai_highlights_json', 'ai_questions_json', 'processing_status', 'error_message')
    def _compute_analysis_html(self):
        for rec in self:
            if rec.processing_status == 'processing':
                rec.ai_analysis_html = Markup('<em class="text-muted">⏳ Đang xử lý... Vui lòng làm mới sau 30 giây.</em>')
                continue
            if rec.processing_status == 'error':
                rec.ai_analysis_html = Markup(f'<div class="text-danger">❌ Lỗi: {escape(rec.error_message or "Không rõ")}</div>')
                continue
            if not rec.ai_highlights_json and not rec.ai_questions_json:
                rec.ai_analysis_html = Markup('<em class="text-muted">Nhấn "Phân tích AI" để bắt đầu.</em>')
                continue
            html = []
            try:
                highlights = json.loads(rec.ai_highlights_json or '[]')
                if highlights:
                    html.append('<b>🔍 Điểm cần chú ý:</b><ul>')
                    for h in highlights:
                        html.append(f'<li>{escape(h)}</li>')
                    html.append('</ul>')
            except Exception:
                pass
            try:
                questions = json.loads(rec.ai_questions_json or '[]')
                if questions:
                    html.append('<b>❓ Câu hỏi gợi ý cho RM:</b><ul>')
                    for q in questions:
                        html.append(f'<li>{escape(q)}</li>')
                    html.append('</ul>')
            except Exception:
                pass
            rec.ai_analysis_html = Markup(''.join(html)) if html else Markup('<em>Không có dữ liệu</em>')

    def action_analyze(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError('Vui lòng đính kèm file tài liệu trước khi phân tích.')
        self.write({'processing_status': 'processing', 'error_message': False})
        self._trigger_async()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang phân tích tài liệu bằng AI... Kết quả xuất hiện sau ~30 giây.',
                'type': 'info', 'sticky': False,
            },
        }

    def _trigger_async(self):
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
                    rec = env['crm.ai.document'].browse(rec_id)
                    if rec.exists():
                        rec._do_analyze()
            except Exception as e:
                _logger.error('CrmAiDocument async error: %s', e, exc_info=True)

        threading.Thread(target=_run, daemon=True).start()

    def _do_analyze(self):
        try:
            raw_bytes = base64.b64decode(self.attachment_id.datas)
            from .crm_ai_service import CrmAiService
            service = CrmAiService(self.env)

            ocr_result = service._call_ocr(raw_bytes, self.document_type)
            ocr_text = ocr_result.get('raw', '') or json.dumps(ocr_result, ensure_ascii=False)

            analysis = service.read_financial_statement(ocr_text)

            vals = {
                'ocr_raw_text': ocr_text[:10000],
                'ai_highlights_json': json.dumps(analysis.get('highlights', []), ensure_ascii=False),
                'ai_questions_json': json.dumps(analysis.get('questions', []), ensure_ascii=False),
                'processing_status': 'done',
            }
            if isinstance(ocr_result, dict) and ocr_result.get('year'):
                vals['year'] = str(ocr_result['year'])

            self.write(vals)

            if self.lead_id:
                highlights = analysis.get('highlights', [])
                questions = analysis.get('questions', [])
                type_label = dict(self._fields['document_type'].selection).get(self.document_type, '')
                note = f'<b>📊 AI Phân tích {type_label}:</b>'
                if highlights:
                    note += '<br/><b>Điểm cần chú ý:</b><ul>' + ''.join(f'<li>{h}</li>' for h in highlights) + '</ul>'
                if questions:
                    note += '<b>Câu hỏi gợi ý cho RM:</b><ul>' + ''.join(f'<li>{q}</li>' for q in questions) + '</ul>'
                self.lead_id.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')
        except Exception as e:
            _logger.error('CrmAiDocument._do_analyze error: %s', e, exc_info=True)
            self.write({'processing_status': 'error', 'error_message': str(e)[:250]})
