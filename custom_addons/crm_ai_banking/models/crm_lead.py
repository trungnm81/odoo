from markupsafe import Markup

from odoo import models, fields, api, _
import json
import logging

from .crm_customer_segment import CUSTOMER_TYPE_SELECTION

_logger = logging.getLogger(__name__)

INTENT_ACTIVITY_MAP = {
    'pricing_inquiry': ('Gửi báo giá', 1),
    'ready_to_buy': ('Follow up ngay', 0),
    'complaint': ('Xử lý khiếu nại', 0),
    'document_request': ('Kiểm tra hồ sơ', 1),
    'follow_up': ('Follow up', 2),
    'general_inquiry': ('Phản hồi khách', 1),
}

NEEDS_TAG_MAP = {
    'loan': 'Vay vốn', 'credit_card': 'Thẻ tín dụng', 'savings': 'Tiết kiệm',
    'insurance': 'Bảo hiểm', 'payroll': 'Payroll', 'lc': 'L/C',
    'fx': 'Ngoại tệ', 'pos': 'POS',
}


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ── AI fields ────────────────────────────────────────────────────────────
    ai_call_session_ids = fields.One2many('crm.ai.call.session', 'lead_id', string='Phiên gọi AI')
    ai_call_session_count = fields.Integer(compute='_compute_ai_call_count', string='Số cuộc gọi')

    document_checklist_ids = fields.One2many('crm.document.checklist', 'lead_id', string='Checklist hồ sơ')

    ai_last_sentiment = fields.Selection(
        [('positive', 'Tích cực'), ('neutral', 'Trung lập'),
         ('negative', 'Tiêu cực'), ('objection', 'Có phản đối')],
        string='Sentiment gần nhất',
    )
    ai_detected_needs_json = fields.Text(string='Nhu cầu nhận diện (JSON)', default='[]')

    customer_type = fields.Selection(
        CUSTOMER_TYPE_SELECTION,
        string='Loại khách hàng',
        index=True,
        help='Tự gợi ý theo loại Contact/Partner: cá nhân hoặc công ty.',
    )
    customer_display_name = fields.Char(
        string='Tên khách hàng',
        compute='_compute_customer_display_name',
        store=True,
        readonly=True,
    )
    product_type = fields.Selection(
        [
            ('vay_mua_nha', 'Vay mua nhà'),
            ('vay_kinh_doanh', 'Vay kinh doanh'),
            ('the_tin_dung', 'Thẻ tín dụng'),
            ('tiet_kiem', 'Tiết kiệm'),
            ('bao_hiem', 'Bảo hiểm'),
            ('payroll', 'Payroll'),
            ('lc_fx', 'L/C / Ngoại tệ'),
            ('other', 'Khác'),
        ],
        string='Loại sản phẩm',
        index=True,
    )
    zalo_user_id = fields.Char(string='Zalo User ID', index=True)

    # ── Referral tracking ────────────────────────────────────────────────────
    referred_by_partner_id = fields.Many2one(
        'res.partner', string='Người giới thiệu',
        help='Khách hàng hoặc đối tác đã giới thiệu lead này.',
        index=True,
    )
    referral_source = fields.Selection([
        ('existing_customer', 'Khách hàng hiện hữu'),
        ('bds_broker', 'Môi giới BĐS'),
        ('car_showroom', 'Showroom ô tô'),
        ('insurance_agent', 'Đại lý bảo hiểm'),
        ('partner', 'Đối tác khác'),
    ], string='Kênh giới thiệu')

    # ── Phase 3 fields ────────────────────────────────────────────────────────
    account_contact_ids = fields.One2many('crm.account.contact', 'lead_id', string='Account Map B2B')
    ai_document_ids = fields.One2many('crm.ai.document', 'lead_id', string='Tài liệu AI')
    ai_document_count = fields.Integer(compute='_compute_ai_doc_count', string='Tài liệu')

    # ── Phase 4 fields ────────────────────────────────────────────────────────
    # P4-1 NBA
    nba_action_type = fields.Selection([
        ('call', 'Gọi điện'), ('send_zalo', 'Gửi Zalo'), ('send_email', 'Gửi Email'),
        ('send_proposal', 'Gửi đề xuất'), ('schedule_meeting', 'Hẹn gặp'),
        ('escalate_manager', 'Báo manager'), ('send_document_reminder', 'Nhắc hồ sơ'),
        ('close_won', 'Chốt thắng'), ('mark_cold', 'Đánh dấu nguội'),
    ], string='NBA — Hành động')
    nba_action_detail = fields.Char(string='NBA — Chi tiết')
    nba_urgency = fields.Selection(
        [('high', 'Khẩn'), ('medium', 'Trung bình'), ('low', 'Thấp')],
        string='NBA — Mức độ',
    )
    nba_reasoning = fields.Text(string='NBA — Lý do')
    nba_suggested_message = fields.Text(string='NBA — Tin nhắn gợi ý')
    nba_confidence = fields.Float(string='NBA — Độ tin cậy', digits=(4, 2))
    nba_computed_date = fields.Datetime(string='NBA — Ngày tính')
    nba_dismissed = fields.Boolean(string='NBA — Đã bỏ qua', default=False)

    # P4-2 Product Recommendations
    product_recommendation_ids = fields.One2many(
        'crm.product.recommendation', 'lead_id', string='Gợi ý sản phẩm',
    )
    latest_recommendation_html = fields.Html(
        string='Gợi ý sản phẩm mới nhất', compute='_compute_latest_recommendation',
    )

    # P4-4 Customer 360
    customer_360_json = fields.Text(string='Customer 360 (JSON)')
    customer_360_html = fields.Html(string='Customer 360', compute='_compute_customer_360_html')
    customer_360_date = fields.Datetime(string='360 — Ngày cập nhật')

    # Banking 360 on Opportunity: readonly mirror of linked Contact data.
    banking_profile_ids = fields.One2many(
        related='partner_id.banking_profile_ids',
        string='Banking 360 profile',
        readonly=True,
    )
    banking_individual_profile_ids = fields.One2many(
        related='partner_id.banking_individual_profile_ids',
        string='Thông tin cá nhân Banking 360',
        readonly=True,
    )
    banking_business_profile_ids = fields.One2many(
        related='partner_id.banking_business_profile_ids',
        string='Thông tin doanh nghiệp Banking 360',
        readonly=True,
    )
    banking_product_holding_ids = fields.One2many(
        related='partner_id.banking_product_holding_ids',
        string='Sản phẩm đang sử dụng',
        readonly=True,
    )

    # ── Badge HTML — đọc từ banking_profile_ids[:1], render màu động ─────────
    badge_html = fields.Html(
        string='Badges KH', compute='_compute_badge_html', store=False,
        sanitize=False,
    )

    _SEGMENT_STYLE = {
        'diamond':  'background:#c9a227;color:#fff',
        'DIAMOND':  'background:#c9a227;color:#fff',
        'platinum': 'background:#a0a0b8;color:#fff',
        'PLATINUM': 'background:#a0a0b8;color:#fff',
        'gold':     'background:#e8a000;color:#fff',
        'GOLD':     'background:#e8a000;color:#fff',
        'silver':   'background:#888;color:#fff',
        'SILVER':   'background:#888;color:#fff',
    }
    _DEBT_STYLE = {
        '1': 'background:#198754;color:#fff',
        '2': 'background:#ffc107;color:#000',
        '3': 'background:#fd7e14;color:#fff',
        '4': 'background:#dc3545;color:#fff',
        '5': 'background:#6f1c24;color:#fff',
    }
    _BADGE_BASE = (
        'display:inline-block;padding:.3em .65em;font-size:.78rem;'
        'border-radius:4px;line-height:1.2;font-weight:500;'
    )

    @api.depends('banking_profile_ids', 'banking_business_profile_ids')
    def _compute_badge_html(self):
        for lead in self:
            profile = lead.banking_profile_ids[:1]
            biz = lead.banking_business_profile_ids[:1]
            parts = []

            seg = profile.customer_segment or ''
            if seg:
                s = self._SEGMENT_STYLE.get(seg, 'background:#6c757d;color:#fff')
                parts.append(f'<span style="{self._BADGE_BASE}{s}">{seg}</span>')

            debt = biz.debt_group or ''
            if debt:
                # lấy chữ số cuối để map style (Core Banking có thể trả "Nhóm 2" hoặc "2")
                debt_key = debt.strip()[-1] if debt.strip() else ''
                s = self._DEBT_STYLE.get(debt_key, 'background:#198754;color:#fff')
                parts.append(f'<span style="{self._BADGE_BASE}{s}">Nhóm nợ: {debt}</span>')

            grade = profile.risk_grade or ''
            if grade:
                parts.append(
                    f'<span style="{self._BADGE_BASE}background:#0054A5;color:#fff">'
                    f'{grade}</span>'
                )

            cif = profile.cif_code or ''
            if cif:
                parts.append(
                    f'<span style="{self._BADGE_BASE}background:#6c757d;color:#fff;'
                    f'font-family:monospace">CIF: {cif}</span>'
                )

            lead.badge_html = Markup(' '.join(parts)) if parts else Markup('')

    def action_open_banking_360_popup(self):
        """Mở popup Hồ Sơ 360° — số dư và TOI của khách hàng."""
        self.ensure_one()
        profile = self.banking_profile_ids[:1]
        if not profile:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Chưa có dữ liệu Banking 360 cho khách hàng này.',
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hồ Sơ 360° — {self.partner_id.name}',
            'res_model': 'crm.banking.customer.profile',
            'res_id': profile.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(
                self.env.ref('crm_ai_banking.view_banking_profile_360_popup').id,
                'form',
            )],
        }

    @api.depends('ai_call_session_ids')
    def _compute_ai_call_count(self):
        for lead in self:
            lead.ai_call_session_count = len(lead.ai_call_session_ids)

    @api.depends('ai_document_ids')
    def _compute_ai_doc_count(self):
        for lead in self:
            lead.ai_document_count = len(lead.ai_document_ids)

    @api.depends('partner_id', 'partner_id.display_name', 'contact_name', 'partner_name')
    def _compute_customer_display_name(self):
        for lead in self:
            lead.customer_display_name = (
                lead.partner_id.display_name
                or lead.contact_name
                or lead.partner_name
                or False
            )

    @api.depends('product_recommendation_ids')
    def _compute_latest_recommendation(self):
        for lead in self:
            latest = lead.product_recommendation_ids.sorted('computed_date', reverse=True)[:1]
            lead.latest_recommendation_html = latest.recommendations_html if latest else \
                Markup('<em class="text-muted">Chưa có gợi ý sản phẩm. Nhấn "Gợi ý AI" để phân tích.</em>')

    @api.depends('customer_360_json')
    def _compute_customer_360_html(self):
        for lead in self:
            if not lead.customer_360_json:
                lead.customer_360_html = Markup('<em class="text-muted">Chưa có tóm tắt 360°.</em>')
                continue
            try:
                data = json.loads(lead.customer_360_json)
                from markupsafe import escape
                html = ['<div class="o_customer_360">']
                if data.get('profile_snapshot'):
                    html.append(f'<p class="fw-semibold">👤 {escape(data["profile_snapshot"])}</p>')
                if data.get('relationship_history'):
                    html.append(f'<p class="small text-muted">📊 {escape(data["relationship_history"])}</p>')
                if data.get('current_status'):
                    html.append(f'<div class="border border-info rounded p-1 small mb-1">📍 {escape(data["current_status"])}</div>')

                def _tags(items, icon):
                    if not items:
                        return ''
                    tags = ''.join(f'<span class="badge bg-secondary me-1">{escape(i)}</span>' for i in items)
                    return f'<div class="mb-1">{icon} {tags}</div>'

                html.append(_tags(data.get('key_needs', []), '🎯'))
                html.append(_tags(data.get('concerns_objections', []), '⚠️'))
                html.append(_tags(data.get('opportunities', []), '💡'))
                if data.get('recommended_approach'):
                    html.append(f'<div class="border border-success rounded p-1 small mt-1">🚀 {escape(data["recommended_approach"])}</div>')
                html.append('</div>')
                lead.customer_360_html = Markup(''.join(html))
            except Exception:
                lead.customer_360_html = Markup(f'<pre class="small">{lead.customer_360_json[:300]}</pre>')

    # ── Email AI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _customer_type_from_partner(partner):
        if not partner:
            return False
        return partner.customer_type or ('business' if partner.is_company else 'individual')

    @api.onchange('partner_id')
    def _onchange_partner_id_customer_type(self):
        for lead in self:
            customer_type = self._customer_type_from_partner(lead.partner_id)
            if customer_type:
                lead.customer_type = customer_type

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id') and not vals.get('customer_type'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['customer_type'] = self._customer_type_from_partner(partner)
        return super().create(vals_list)

    def _create_customer(self, with_parent=None):
        self.ensure_one()
        if self.customer_type != 'business':
            return super()._create_customer(with_parent=with_parent)

        Partner = self.env['res.partner']
        partner_company = with_parent
        if not partner_company:
            company_name = self.partner_name or self.contact_name or self.name
            partner_company = Partner.create(self._prepare_customer_values(company_name, is_company=True))
        elif not partner_company.customer_type:
            partner_company.write({'customer_type': 'business'})

        if self.contact_name and self.contact_name != partner_company.name:
            existing_contact = Partner.search([
                ('parent_id', '=', partner_company.id),
                ('name', '=', self.contact_name),
            ], limit=1)
            if not existing_contact:
                Partner.create(self._prepare_customer_values(
                    self.contact_name,
                    is_company=False,
                    parent_id=partner_company.id,
                ))
        return partner_company

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        vals = super()._prepare_customer_values(partner_name, is_company=is_company, parent_id=parent_id)
        if is_company:
            vals['customer_type'] = 'business'
        elif parent_id:
            vals['customer_type'] = 'individual'
        elif self.customer_type:
            vals['customer_type'] = self.customer_type
            vals['is_company'] = self.customer_type == 'business'
        return vals

    def message_new(self, msg_dict, custom_values=None):
        lead = super().message_new(msg_dict, custom_values)
        config = self.env['crm.ai.config'].get_config()
        if config.auto_process_email:
            self._trigger_async(
                lead.id, '_ai_process_incoming_email',
                args=(msg_dict.get('body', ''), msg_dict.get('subject', '')),
            )
        return lead

    def _trigger_async(self, record_id, method_name, args=()):
        """Run a method on this model in a background thread after transaction commits."""
        dbname = self.env.cr.dbname
        model_name = self._name

        def _run():
            import time
            time.sleep(2)
            try:
                from odoo.modules.registry import Registry
                from odoo import SUPERUSER_ID
                import odoo.api
                with Registry(dbname).cursor() as cr:
                    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                    rec = env[model_name].browse(record_id)
                    if rec.exists():
                        getattr(rec, method_name)(*args)
            except Exception as e:
                _logger.error('Async %s.%s error: %s', model_name, method_name, e, exc_info=True)

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def _ai_process_incoming_email(self, body: str, subject: str = ''):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        result = service.summarize_email(body, subject)
        if not result:
            return

        intent = result.get('intent', 'general_inquiry')
        urgency = result.get('urgency', 'low')
        bullets = result.get('summary_bullets', [])
        needs = result.get('detected_needs', [])
        suggested = result.get('suggested_action', '')

        # Post internal note with AI summary
        note_lines = ['<b>🤖 AI Tóm tắt email:</b><ul>']
        for b in bullets:
            note_lines.append(f'<li>{b}</li>')
        note_lines.append('</ul>')
        note_lines.append(f'<b>Intent:</b> {intent} | <b>Urgency:</b> {urgency}<br/>')
        if suggested:
            note_lines.append(f'<b>Gợi ý:</b> {suggested}')
        self.message_post(body=Markup(''.join(note_lines)), subtype_xmlid='mail.mt_note')

        # Auto-schedule activity based on intent
        activity_label, days_deadline = INTENT_ACTIVITY_MAP.get(intent, ('Xử lý email', 1))
        act_type = self.env.ref('mail.mail_activity_data_email', raise_if_not_found=False)
        if act_type:
            from datetime import date, timedelta
            self.activity_schedule(
                activity_type_id=act_type.id,
                summary=f'{activity_label} — {subject[:60]}' if subject else activity_label,
                date_deadline=date.today() + timedelta(days=days_deadline),
                user_id=self.user_id.id or self.env.user.id,
            )

        # Notify salesperson if high urgency
        if urgency == 'high' and self.user_id:
            self.env['bus.bus']._sendone(
                self.user_id.partner_id,
                'mail.message',
                {'message': f'🔥 Email khẩn từ lead {self.name}: {subject or "(no subject)"}'},
            )

        # Update tags from detected needs
        self._apply_needs_tags(needs)

        # Trigger document checklist if document_request intent
        if intent == 'document_request' and self.product_type:
            self._ensure_document_checklist()

    def _ai_process_zalo_message(self, message_text: str):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        result = service.detect_needs(message_text)
        if not result:
            return
        needs = result.get('needs', [])
        confidence = result.get('confidence', 0)
        signals = result.get('signals', [])
        if needs:
            note = f'<b>🤖 AI Nhận diện nhu cầu (Zalo):</b> {", ".join(needs)}'
            if signals:
                note += f'<br/>Signals: {", ".join(signals)}'
            note += f'<br/>Confidence: {int(confidence * 100)}%'
            self.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')
            self._apply_needs_tags(needs)

    def _apply_needs_tags(self, needs: list):
        tag_ids = []
        for need in needs:
            tag_name = NEEDS_TAG_MAP.get(need)
            if not tag_name:
                continue
            tag = self.env['crm.tag'].search([('name', '=', tag_name)], limit=1)
            if not tag:
                tag = self.env['crm.tag'].create({'name': tag_name})
            tag_ids.append(tag.id)
        if tag_ids:
            self.write({'tag_ids': [(4, tid) for tid in tag_ids]})

    def _ensure_document_checklist(self):
        """Create checklist if not already present for this lead's product type."""
        self.ensure_one()
        if not self.product_type:
            return
        existing = self.env['crm.document.checklist'].search(
            [('lead_id', '=', self.id), ('product_type', '=', self.product_type)], limit=1
        )
        if not existing:
            self.env['crm.document.checklist'].create_from_template(self.id, self.product_type)

    def action_create_document_checklist(self):
        """Tạo checklist hồ sơ thủ công từ template — gọi được từ button trên view."""
        self.ensure_one()
        self._ensure_document_checklist()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Checklist hồ sơ đã được tạo.' if self.product_type
                           else 'Vui lòng chọn Loại sản phẩm trước.',
                'type': 'success' if self.product_type else 'warning',
                'sticky': False,
            },
        }

    def write(self, vals):
        vals = dict(vals)
        if 'partner_id' in vals and 'customer_type' not in vals:
            partner = self.env['res.partner'].browse(vals['partner_id']) if vals.get('partner_id') else False
            vals['customer_type'] = self._customer_type_from_partner(partner)
        old_product_types = {lead.id: lead.product_type for lead in self} if 'product_type' in vals else {}
        result = super().write(vals)
        if 'product_type' in vals and vals.get('product_type'):
            for lead in self:
                if old_product_types.get(lead.id) != vals['product_type']:
                    lead._ensure_document_checklist()
        return result

    # ── Action: Start new call session ───────────────────────────────────────

    def action_start_ai_call(self):
        self.ensure_one()
        # Lấy số điện thoại tốt nhất để pre-fill cho kênh Twilio
        phone = (
            self.phone
            or getattr(self, 'mobile', '')
            or self.partner_id.phone
            or getattr(self.partner_id, 'mobile', '')
            or ''
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'crm_ai_banking.live_call_screen',
            'target': 'new',
            'name': '🎤 Gọi AI — ' + (self.name or ''),
            'params': {
                'leadId': self.id,
                'leadName': self.name or '',
                'sessionType': 'call',
                'phone': phone,
            },
        }

    def action_twilio_call(self):
        """Mở dialog chọn số điện thoại rồi gọi qua Twilio."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'crm_ai_banking.twilio_call_dialog',
            'target': 'new',
            'name': f'📞 Gọi — {self.name}',
            'params': {
                'leadId': self.id,
                'leadName': self.name or '',
                'phone': self.phone or getattr(self, 'mobile', '') or '',
                'partnerPhone': self.partner_id.phone or getattr(self.partner_id, 'mobile', '') or '',
            },
        }

    def action_view_ai_calls(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử cuộc gọi AI',
            'res_model': 'crm.ai.call.session',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
        }

    # ── P2-1: Name Card Scan ──────────────────────────────────────────────────

    def action_scan_name_card(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quét Name Card',
            'res_model': 'crm.ai.scan.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scan_type': 'name_card',
                'default_lead_id': self.id,
            },
        }

    def action_scan_cccd(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quét CCCD',
            'res_model': 'crm.ai.scan.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scan_type': 'cccd_front',
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    # ── P2-3: Zalo Integration ────────────────────────────────────────────────

    def action_send_zalo(self):
        """Mở dialog soạn và gửi tin nhắn Zalo — qua wizard nhập nội dung."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Gửi Zalo — {self.name}',
            'res_model': 'crm.ai.zalo.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_zalo_user_id': self.zalo_user_id or (
                    self.partner_id.zalo_user_id if self.partner_id else ''
                ),
            },
        }

    @api.model
    def _handle_zalo_incoming(self, webhook_data: dict):
        """Xử lý message đến từ Zalo webhook."""
        sender = webhook_data.get('sender', {})
        zalo_uid = sender.get('id', '')
        message_obj = webhook_data.get('message', {})
        text = message_obj.get('text', '')
        attachments = message_obj.get('attachments', [])

        if not zalo_uid:
            return

        # Tìm lead hoặc partner theo Zalo User ID / phone
        lead = self._find_or_create_lead_for_zalo(zalo_uid, sender)
        if not lead:
            return

        # Log message vào chatter
        body = f'📱 [Zalo nhận] {text}' if text else '📎 [Zalo] Khách gửi file/ảnh'
        for att in attachments:
            att_type = att.get('type', '')
            payload = att.get('payload', {})
            if att_type == 'image':
                body += f'<br/>🖼️ <a href="{payload.get("url", "#")}">Ảnh</a>'
            elif att_type == 'file':
                body += f'<br/>📎 <a href="{payload.get("url", "#")}">{payload.get("name", "File")}</a>'
        lead._message_log(body=body)

        # AI detect intent/needs
        if text:
            self._trigger_async(lead.id, '_ai_process_zalo_message', args=(text,))

    def _find_or_create_lead_for_zalo(self, zalo_uid: str, sender_info: dict):
        """Tìm lead theo Zalo User ID hoặc tạo mới."""
        # Tìm theo Zalo User ID trên lead
        lead = self.search([('zalo_user_id', '=', zalo_uid)], limit=1)
        if lead:
            return lead

        # Tìm theo Zalo User ID trên partner
        partner = self.env['res.partner'].search([('zalo_user_id', '=', zalo_uid)], limit=1)
        if partner:
            lead = self.search([('partner_id', '=', partner.id)], order='create_date desc', limit=1)
            if lead:
                return lead

        # Tạo lead mới từ Zalo
        display_name = sender_info.get('display_name', f'Zalo User {zalo_uid}')
        partner = partner or self.env['res.partner'].create({
            'name': display_name,
            'zalo_user_id': zalo_uid,
        })
        lead = self.create({
            'name': f'[Zalo] {display_name}',
            'partner_id': partner.id,
            'zalo_user_id': zalo_uid,
            'type': 'lead',
        })
        tag = self.env['crm.tag'].search([('name', '=', 'Từ Zalo')], limit=1)
        if not tag:
            tag = self.env['crm.tag'].create({'name': 'Từ Zalo'})
        lead.write({'tag_ids': [(4, tag.id)]})
        return lead

    # ── P2-4: Manual Needs Detection ─────────────────────────────────────────

    def action_detect_needs(self):
        """Phân tích chatter gần nhất để nhận diện nhu cầu tài chính."""
        self.ensure_one()
        messages = self.env['mail.message'].search([
            ('res_id', '=', self.id),
            ('model', '=', 'crm.lead'),
            ('message_type', 'in', ['email', 'comment']),
        ], order='date desc', limit=10)
        text_content = ' '.join(
            m.body.replace('<br/>', ' ').replace('<br>', ' ') for m in messages
            if m.body
        )[:3000]
        if not text_content.strip():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': 'Chưa có nội dung để phân tích.', 'type': 'warning'},
            }
        self._trigger_async(self.id, '_ai_run_needs_detection', args=(text_content,))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang phân tích nhu cầu... Kết quả xuất hiện trong Chatter.',
                'type': 'info',
                'sticky': False,
            },
        }

    def _ai_run_needs_detection(self, text: str):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        result = service.detect_needs(text)
        if not result:
            return
        needs = result.get('needs', [])
        confidence = result.get('confidence', 0)
        signals = result.get('signals', [])
        if needs:
            note = f'<b>🤖 AI Nhận diện nhu cầu:</b> {", ".join(needs)}'
            if signals:
                note += f'<br/>Tín hiệu: {", ".join(signals)}'
            note += f'<br/>Độ tin cậy: {int(confidence * 100)}%'
            self.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')
            self._apply_needs_tags(needs)

    # ── P3-2: GPKD Scan ──────────────────────────────────────────────────────

    def action_scan_gpkd(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quét GPKD',
            'res_model': 'crm.ai.scan.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scan_type': 'gpkd',
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    # ── P3-3: Financial AI BCTC ───────────────────────────────────────────────

    def action_add_bctc(self):
        self.ensure_one()
        doc = self.env['crm.ai.document'].create({
            'lead_id': self.id,
            'document_type': 'bctc',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phân tích BCTC',
            'res_model': 'crm.ai.document',
            'res_id': doc.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_ai_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tài liệu AI',
            'res_model': 'crm.ai.document',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    # ── P3-4: Proposal Generator ──────────────────────────────────────────────

    def action_generate_proposal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sinh đề xuất AI',
            'res_model': 'crm.ai.generate.proposal',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    # ── P3-5: Cross-sell Engine ───────────────────────────────────────────────

    def action_crosssell_suggestions(self):
        self.ensure_one()
        self._trigger_async(self.id, '_ai_run_crosssell', args=())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang phân tích cross-sell... Kết quả trong Chatter.',
                'type': 'info', 'sticky': False,
            },
        }

    def _ai_run_crosssell(self):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        existing = [self.product_type] if self.product_type else []
        lead_ctx = (
            f'Lead: {self.name}, Stage: {self.stage_id.name}, '
            f'Partner: {self.partner_id.name or ""}, '
            f'Detected needs: {self.ai_detected_needs_json or "[]"}'
        )
        result = service.get_crosssell_suggestions(lead_ctx, existing)
        if not result:
            return
        suggestions = result.get('suggestions', [])
        priority = result.get('priority_product', '')
        if suggestions:
            note = '<b>🔁 Gợi ý Cross-sell AI:</b><ul>'
            for s in suggestions:
                note += f'<li><b>{s.get("product", "")}</b>: {s.get("reason", "")} — <em>{s.get("approach", "")}</em></li>'
            note += '</ul>'
            if priority:
                note += f'<b>Ưu tiên:</b> {priority}'
            self.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')

    # ── P4-1: NBA ─────────────────────────────────────────────────────────────

    def action_compute_nba(self):
        self.ensure_one()
        self._trigger_async(self.id, '_ai_run_nba', args=())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang tính toán hành động tốt nhất...', 'type': 'info', 'sticky': False,
            },
        }

    def _ai_run_nba(self):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)

        messages = self.env['mail.message'].search([
            ('res_id', '=', self.id), ('model', '=', 'crm.lead'),
        ], order='date desc', limit=5)
        msg_snippets = [m.body[:200] for m in messages if m.body]

        lead_ctx = {
            'name': self.name,
            'stage': self.stage_id.name,
            'probability': self.probability,
            'product_type': self.product_type,
            'expected_revenue': self.expected_revenue,
            'last_update_days': (fields.Datetime.now() - self.write_date).days if self.write_date else 0,
            'pending_activities': len(self.activity_ids),
            'sentiment': self.ai_last_sentiment,
            'detected_needs': self.ai_detected_needs_json,
            'recent_messages': msg_snippets,
        }
        checklist = self.document_checklist_ids[:1]
        if checklist:
            lead_ctx['checklist_completion'] = checklist.completion_rate

        result = service.compute_next_best_action(lead_ctx)
        if not result:
            return

        self.write({
            'nba_action_type': result.get('action_type') if result.get('action_type') in dict(
                self._fields['nba_action_type'].selection) else False,
            'nba_action_detail': result.get('action_detail', '')[:250],
            'nba_urgency': result.get('urgency') if result.get('urgency') in ['high', 'medium', 'low'] else 'medium',
            'nba_reasoning': result.get('reasoning', '')[:500],
            'nba_suggested_message': result.get('suggested_message', '')[:500],
            'nba_confidence': min(float(result.get('confidence', 0.5)), 1.0),
            'nba_computed_date': fields.Datetime.now(),
            'nba_dismissed': False,
        })

    def action_dismiss_nba(self):
        self.ensure_one()
        self.nba_dismissed = True

    # ── P4-2: Product Recommendations ────────────────────────────────────────

    def action_ai_product_recommendations(self):
        self.ensure_one()
        self._trigger_async(self.id, '_ai_run_product_recommendations', args=())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang phân tích sản phẩm phù hợp...', 'type': 'info', 'sticky': False,
            },
        }

    def _ai_run_product_recommendations(self):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)

        # Layer 1: rule-based eligibility
        all_rules = self.env['crm.product.eligibility.rule'].search([('active', '=', True)])
        held_product_codes = set()
        if self.partner_id:
            held_product_codes = set(self.partner_id.banking_product_holding_ids.filtered(
                lambda holding: holding.status == 'active' and holding.product_code
            ).mapped('product_code'))
        eligible = []
        for rule in all_rules:
            if rule.product_code in held_product_codes:
                continue
            if rule.check_eligibility(self.partner_id):
                eligible.append({
                    'product_code': rule.product_code,
                    'product_name': rule.product_name,
                    'category': rule.product_category,
                    'description': rule.description or '',
                })

        # Layer 2: AI scoring
        profile = self.partner_id.banking_profile_ids[:1] if self.partner_id else self.env['crm.banking.customer.profile']
        active_holdings = self.partner_id.banking_product_holding_ids.filtered(
            lambda holding: holding.status == 'active'
        )[:10] if self.partner_id else self.env['crm.banking.product.holding']
        holding_names = ', '.join(active_holdings.mapped('product_name'))
        banking_ctx = ''
        if profile:
            banking_ctx = (
                f'Tổng tiền gửi: {profile.total_deposit_balance}, Tổng dư nợ: {profile.total_loan_balance}, '
                f'TOI 12M: {profile.toi_12m}, Risk: {profile.risk_grade or profile.risk_level or ""}, '
                f'Sản phẩm đang dùng: {holding_names}'
            )
        lead_ctx = (
            f'Lead: {self.name}, Sản phẩm hiện tại: {self.product_type or "chưa có"}, '
            f'Nhu cầu: {self.ai_detected_needs_json}, Sentiment: {self.ai_last_sentiment}, '
            f'Partner: {self.partner_id.name or ""}. {banking_ctx}'
        )
        ranked = service.score_products(eligible, lead_ctx)
        if not ranked:
            ranked = [{'product_code': r['product_code'], 'product_name': r['product_name'],
                       'match_score': 0.5, 'match_reasons': ['Đủ điều kiện cơ bản'],
                       'approach_suggestion': ''} for r in eligible[:3]]

        rec = self.env['crm.product.recommendation'].create({
            'lead_id': self.id,
            'recommendations_json': json.dumps(ranked[:5], ensure_ascii=False),
            'top_product_name': ranked[0].get('product_name', '') if ranked else '',
            'top_match_score': (ranked[0].get('match_score', 0) * 100) if ranked else 0,
        })
        note = f'<b>🏦 AI Gợi ý sản phẩm:</b><ul>'
        for item in ranked[:3]:
            score_pct = int(item.get('match_score', 0) * 100)
            note += f'<li><b>{item.get("product_name", "")}</b> — {score_pct}% phù hợp'
            reasons = item.get('match_reasons', [])
            if reasons:
                note += f': {reasons[0]}'
            note += '</li>'
        note += '</ul>'
        self.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')

    # ── P4-4: Customer 360 ────────────────────────────────────────────────────

    def action_refresh_customer_360(self):
        self.ensure_one()
        self._trigger_async(self.id, '_ai_run_customer_360', args=())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đang tổng hợp Customer 360°...', 'type': 'info', 'sticky': False,
            },
        }

    def _ai_run_customer_360(self):
        self.ensure_one()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)

        messages = self.env['mail.message'].search([
            ('res_id', '=', self.id), ('model', '=', 'crm.lead'),
        ], order='date desc', limit=8)
        recent_msgs = [{'author': m.author_id.name or '', 'body': m.body[:200]} for m in messages]

        call_summaries = []
        for session in self.ai_call_session_ids.filtered('summary')[:3]:
            call_summaries.append(session.summary[:200] if session.summary else '')

        lead_data = {
            'lead_name': self.name,
            'stage': self.stage_id.name,
            'probability': self.probability,
            'product_type': self.product_type,
            'expected_revenue': self.expected_revenue,
            'partner_name': self.partner_id.name or '',
            'partner_phone': self.partner_id.phone or '',
            'days_in_pipeline': (fields.Datetime.now() - self.create_date).days if self.create_date else 0,
            'sentiment': self.ai_last_sentiment,
            'detected_needs': self.ai_detected_needs_json,
            'recent_messages': recent_msgs,
            'call_summaries': call_summaries,
            'pending_activities': len(self.activity_ids),
        }
        if self.partner_id:
            profile = self.partner_id.banking_profile_ids[:1]
            if profile:
                lead_data['banking_profile'] = {
                    'total_deposit_balance': profile.total_deposit_balance,
                    'total_loan_balance': profile.total_loan_balance,
                    'total_aum': profile.total_aum,
                    'toi_ytd': profile.toi_ytd,
                    'toi_12m': profile.toi_12m,
                    'risk_grade': profile.risk_grade,
                    'risk_level': profile.risk_level,
                    'preferred_channel': profile.preferred_channel,
                    'digital_adoption_level': profile.digital_adoption_level,
                }
            holdings = self.partner_id.banking_product_holding_ids.filtered(lambda h: h.status == 'active')[:10]
            if holdings:
                lead_data['product_holdings'] = [
                    {
                        'product_code': holding.product_code,
                        'product_name': holding.product_name,
                        'category': holding.product_category,
                        'current_balance': holding.current_balance,
                        'outstanding_balance': holding.outstanding_balance,
                        'toi_ytd': holding.toi_ytd,
                    }
                    for holding in holdings
                ]
        if self.document_checklist_ids:
            lead_data['checklist_completion'] = self.document_checklist_ids[0].completion_rate

        result = service.generate_customer_360(lead_data)
        if not result:
            return

        self.write({
            'customer_360_json': json.dumps(result, ensure_ascii=False),
            'customer_360_date': fields.Datetime.now(),
        })

    # ── Cron: Recompute NBA for all active leads ──────────────────────────────

    @api.model
    def _cron_refresh_nba(self):
        active_leads = self.search([
            ('active', '=', True), ('type', '=', 'opportunity'), ('won_status', '=', 'pending'),
        ], limit=100)
        for lead in active_leads:
            try:
                lead._ai_run_nba()
            except Exception as e:
                _logger.error('NBA cron error for lead %s: %s', lead.id, e)

    # ── Cron: Cold Lead Alert ─────────────────────────────────────────────────

    @api.model
    def _cron_cold_lead_alert(self):
        config = self.env['crm.ai.config'].get_config()
        threshold = config.cold_lead_threshold_days or 10
        from datetime import datetime, timedelta
        cutoff = fields.Datetime.now() - timedelta(days=threshold)
        cold_leads = self.search([
            ('active', '=', True),
            ('type', '=', 'opportunity'),
            ('won_status', '=', 'pending'),
            ('write_date', '<', cutoff),
        ])
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        for lead in cold_leads:
            # Check if there's already a cold-lead activity
            existing_act = lead.activity_ids.filtered(
                lambda a: a.summary and 'nguội' in (a.summary or '').lower()
            )
            if existing_act:
                continue
            # AI suggest re-engage
            history_summary = lead.description or lead.name
            result = service.get_cold_lead_reengage(
                lead.name, lead.stage_id.name,
                (fields.Datetime.now() - lead.write_date).days,
                history_summary,
            )
            note = f'<b>❄️ Lead nguội ({threshold}+ ngày không cập nhật)</b>'
            if result.get('reason_cold'):
                note += f'<br/>Lý do có thể: {result["reason_cold"]}'
            if result.get('reengage_suggestion'):
                note += f'<br/>Gợi ý: {result["reengage_suggestion"]}'
            lead.message_post(body=Markup(note), subtype_xmlid='mail.mt_note')
            act_type = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
            if act_type:
                from datetime import date
                lead.activity_schedule(
                    activity_type_id=act_type.id,
                    summary='❄️ Re-engage lead nguội',
                    date_deadline=date.today(),
                    user_id=lead.user_id.id or self.env.user.id,
                )

    # ── Cron: Large Deal Alert ────────────────────────────────────────────────

    @api.model
    def _cron_large_deal_alert(self):
        config = self.env['crm.ai.config'].get_config()
        threshold = config.large_deal_threshold or 5_000_000_000
        no_manager_days = config.large_deal_no_manager_days or 7
        from datetime import datetime, timedelta, date
        cutoff = fields.Datetime.now() - timedelta(days=no_manager_days)
        large_leads = self.search([
            ('active', '=', True),
            ('type', '=', 'opportunity'),
            ('won_status', '=', 'pending'),
            ('expected_revenue', '>=', threshold),
        ])
        for lead in large_leads:
            # Check last manager interaction
            manager = lead.team_id.user_id if lead.team_id else None
            if not manager:
                continue
            last_manager_msg = self.env['mail.message'].search([
                ('res_id', '=', lead.id),
                ('model', '=', 'crm.lead'),
                ('author_id', '=', manager.partner_id.id),
                ('date', '>=', cutoff),
            ], limit=1)
            if last_manager_msg:
                continue
            # Alert manager via discuss
            channel = self.env['discuss.channel'].search([
                ('name', '=', lead.team_id.name),
                ('channel_type', '=', 'channel'),
            ], limit=1)
            revenue_b = lead.expected_revenue / 1_000_000_000
            alert_msg = (
                f'👔 <b>Deal lớn cần chú ý:</b> <a href="/web#id={lead.id}&model=crm.lead">{lead.name}</a>'
                f'<br/>Giá trị: {revenue_b:.1f} tỷ | Stage: {lead.stage_id.name}'
                f'<br/>Chưa có tương tác của manager trong {no_manager_days} ngày'
            )
            if channel:
                channel.message_post(body=Markup(alert_msg))
            # Schedule manager activity
            act_type = self.env.ref('mail.mail_activity_data_meeting', raise_if_not_found=False)
            if act_type:
                lead.activity_schedule(
                    activity_type_id=act_type.id,
                    summary='👔 Cần hỗ trợ của manager',
                    date_deadline=date.today(),
                    user_id=manager.id,
                )

    # ── Cron: Daily Digest ───────────────────────────────────────────────────

    @api.model
    def _cron_send_daily_digest(self):
        config = self.env['crm.ai.config'].get_config()
        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        from datetime import datetime, timedelta, date
        # Find all active salespeople with open opportunities
        salespeople = self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ])
        for user in salespeople:
            leads = self.search([
                ('user_id', '=', user.id),
                ('active', '=', True),
                ('type', '=', 'opportunity'),
                ('won_status', '=', 'pending'),
            ])
            if not leads:
                continue
            overdue = leads.filtered(lambda l: l.activity_ids.filtered(
                lambda a: a.date_deadline and a.date_deadline < date.today()
            ))
            hot = leads.filtered(lambda l: l.probability >= 70)
            cold_cutoff = fields.Datetime.now() - timedelta(days=config.cold_lead_threshold_days or 10)
            cold = leads.filtered(lambda l: l.write_date < cold_cutoff)
            pending_checklist = self.env['crm.document.checklist'].search([
                ('lead_id', 'in', leads.ids),
                ('pending_count', '>', 0),
            ])
            hot_list = [f'{l.name} ({int(l.probability)}%)' for l in hot[:5]]
            cold_list = [f'{l.name} ({(fields.Datetime.now() - l.write_date).days}d)' for l in cold[:5]]
            pending_list = [f'{c.display_name}' for c in pending_checklist[:5]]
            digest = service.generate_daily_digest(
                name=user.name,
                overdue_count=len(overdue),
                hot_leads=hot_list,
                checklist_pending=pending_list,
                cold_leads=cold_list,
                cold_days=config.cold_lead_threshold_days or 10,
            )
            if not digest:
                continue
            # Send via discuss DM
            channel = self.env['discuss.channel'].with_context(mail_create_nosubscribe=True)
            dm = channel.search([
                ('channel_type', '=', 'chat'),
                ('channel_member_ids.partner_id', '=', user.partner_id.id),
                ('channel_member_ids.partner_id', '=', self.env.user.partner_id.id),
            ], limit=1)
            if not dm:
                dm = channel.create({
                    'name': f'AI Digest — {user.name}',
                    'channel_type': 'chat',
                    'channel_member_ids': [
                        (0, 0, {'partner_id': user.partner_id.id}),
                        (0, 0, {'partner_id': self.env.user.partner_id.id}),
                    ],
                })
            dm.message_post(body=Markup(digest.replace('\n', '<br/>')), message_type='comment')

    # ── Cron: Birthday & Special Occasion Activities ──────────────────────────

    @api.model
    def _cron_birthday_activities(self):
        """Tạo activity chúc sinh nhật cho KH có sinh nhật trong 3 ngày tới."""
        from datetime import date, timedelta
        today = date.today()
        upcoming = [today + timedelta(days=d) for d in range(0, 4)]
        upcoming_md = [(d.month, d.day) for d in upcoming]

        partners = self.env['res.partner'].search([
            ('date_of_birth', '!=', False),
            ('customer_rank', '>', 0),
        ])
        act_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not act_type:
            return

        for partner in partners:
            dob = partner.date_of_birth
            if (dob.month, dob.day) not in upcoming_md:
                continue
            # Tìm lead đang active của partner này
            leads = self.search([
                ('partner_id', '=', partner.id),
                ('active', '=', True),
                ('won_status', '=', 'pending'),
            ], limit=1)
            target = leads[0] if leads else None
            # Kiểm tra đã có activity sinh nhật năm nay chưa
            check_model = target or partner
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead' if target else 'res.partner'),
                ('res_id', '=', check_model.id),
                ('summary', 'ilike', 'sinh nhật'),
                ('date_deadline', '>=', str(today)),
            ], limit=1)
            if existing:
                continue
            birthday_date = date(today.year, dob.month, dob.day)
            if birthday_date < today:
                birthday_date = date(today.year + 1, dob.month, dob.day)
            salesperson_id = (target.user_id.id if target else False) or self.env.user.id
            if target:
                target.activity_schedule(
                    activity_type_id=act_type.id,
                    summary=f'🎂 Chúc sinh nhật {partner.name}',
                    note=f'Sinh nhật {birthday_date.strftime("%d/%m/%Y")}. Gửi lời chúc và nhắc chương trình ưu đãi.',
                    date_deadline=birthday_date,
                    user_id=salesperson_id,
                )
            _logger.info('Birthday activity created for partner %s (%s)', partner.name, birthday_date)

    # ── Cron: Deposit Maturity Alert (from core banking) ─────────────────────

    @api.model
    def _cron_deposit_maturity_alert(self):
        """Cảnh báo tiền gửi đến hạn trong 14 ngày — tạo Lead/Opportunity để cross-sell."""
        from datetime import date, timedelta
        today = date.today()
        maturity_window = today + timedelta(days=14)

        maturing = self.env['crm.banking.product.holding'].search([
            ('product_category', '=', 'deposit'),
            ('status', '=', 'active'),
            ('maturity_date', '>=', str(today)),
            ('maturity_date', '<=', str(maturity_window)),
        ])
        act_type = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
        source = self.env.ref('crm.crm_source_newsletter', raise_if_not_found=False)

        for holding in maturing:
            partner = holding.partner_id
            # Kiểm tra đã có opportunity deposit renewal chưa
            existing = self.search([
                ('partner_id', '=', partner.id),
                ('product_type', '=', 'tiet_kiem'),
                ('active', '=', True),
                ('won_status', '=', 'pending'),
                ('create_date', '>=', str(fields.Datetime.now() - __import__('datetime').timedelta(days=30))),
            ], limit=1)
            if existing:
                continue
            # Tìm salesperson: ưu tiên RM từ banking profile
            profile = partner.banking_profile_ids[:1]
            rm_code = profile.rm_code if profile else False
            salesperson = False
            if rm_code:
                salesperson = self.env['res.users'].search([
                    ('employee_id.barcode', '=', rm_code),
                ], limit=1) or self.env['res.users'].search([
                    ('name', 'ilike', profile.rm_name or ''),
                ], limit=1) if profile.rm_name else False

            balance_vnd = f'{holding.current_balance:,.0f} VNĐ' if holding.current_balance else 'N/A'
            lead_vals = {
                'name': f'Tiền gửi đến hạn — {partner.name} — {holding.product_name}',
                'partner_id': partner.id,
                'type': 'opportunity',
                'product_type': 'tiet_kiem',
                'expected_revenue': holding.current_balance or 0,
                'description': (
                    f'Sản phẩm: {holding.product_name}\n'
                    f'Số dư: {balance_vnd}\n'
                    f'Đáo hạn: {holding.maturity_date}\n'
                    f'Gợi ý: Liên hệ tư vấn gia hạn hoặc chuyển sang sản phẩm tiết kiệm khác.'
                ),
            }
            if salesperson:
                lead_vals['user_id'] = salesperson.id
            if source:
                lead_vals['source_id'] = source.id

            new_lead = self.create(lead_vals)
            new_lead.message_post(
                body=Markup(
                    f'<b>⏰ Tiền gửi đến hạn:</b> {holding.product_name}<br/>'
                    f'Số dư: {balance_vnd} — Đáo hạn: {holding.maturity_date}<br/>'
                    f'<em>Lead tự động tạo để tư vấn gia hạn / cross-sell.</em>'
                ),
                subtype_xmlid='mail.mt_note',
            )
            if act_type:
                new_lead.activity_schedule(
                    activity_type_id=act_type.id,
                    summary=f'⏰ Tiền gửi đến hạn {holding.maturity_date}',
                    date_deadline=holding.maturity_date,
                    user_id=(salesperson.id if salesperson else self.env.user.id),
                )

    # ── Cron: Loan Repayment Reminder / NPL Alert ─────────────────────────────

    @api.model
    def _cron_loan_repayment_alert(self):
        """Nhắc nhở khi sản phẩm vay có dư nợ và chưa có activity follow-up trong 30 ngày."""
        from datetime import date, timedelta
        today = date.today()
        cutoff = fields.Datetime.now() - __import__('datetime').timedelta(days=30)

        active_loans = self.env['crm.banking.product.holding'].search([
            ('product_category', '=', 'loan'),
            ('status', '=', 'active'),
            ('outstanding_balance', '>', 0),
        ])
        act_type = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False)

        for holding in active_loans:
            partner = holding.partner_id
            # Chỉ alert nếu KH có lead active và không có activity gần đây
            leads = self.search([
                ('partner_id', '=', partner.id),
                ('active', '=', True),
                ('won_status', '=', 'pending'),
            ], limit=1)
            if not leads:
                continue
            lead = leads[0]
            # Kiểm tra đã có activity trong 30 ngày chưa
            recent_act = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('create_date', '>=', str(cutoff)),
            ], limit=1)
            if recent_act:
                continue
            if act_type:
                balance_vnd = f'{holding.outstanding_balance:,.0f} VNĐ'
                lead.activity_schedule(
                    activity_type_id=act_type.id,
                    summary=f'💳 Theo dõi khoản vay — Dư nợ {balance_vnd}',
                    note='Liên hệ kiểm tra tình trạng trả nợ, nhắc lịch trả nợ nếu cần.',
                    date_deadline=today,
                    user_id=lead.user_id.id or self.env.user.id,
                )

    # ── Close-Won Alert: NBA banner highlight ─────────────────────────────────

    def action_nba_start_closing(self):
        """Từ NBA banner close_won — mở wizard hoặc log activity chốt hợp đồng."""
        self.ensure_one()
        act_type = self.env.ref('mail.mail_activity_data_meeting', raise_if_not_found=False)
        from datetime import date, timedelta
        if act_type:
            self.activity_schedule(
                activity_type_id=act_type.id,
                summary='✍️ Chốt hợp đồng',
                note=self.nba_action_detail or 'Khách hàng sẵn sàng chốt — lên lịch ký hợp đồng.',
                date_deadline=date.today() + timedelta(days=2),
                user_id=self.user_id.id or self.env.user.id,
            )
        self.message_post(
            body=Markup(
                f'<b>🎯 Đang tiến hành chốt hợp đồng</b><br/>'
                f'{self.nba_action_detail or ""}'
            ),
            subtype_xmlid='mail.mt_note',
        )
        self.write({'nba_dismissed': True})
        return {'type': 'ir.actions.act_window_close'}

    # ── Zalo: Nhắc hồ sơ thiếu ───────────────────────────────────────────────

    def action_zalo_remind_checklist(self):
        """Gửi Zalo nhắc KH về các giấy tờ còn thiếu trong checklist."""
        self.ensure_one()
        if not self.zalo_user_id:
            from odoo.exceptions import UserError as UE
            raise UE('Khách hàng chưa có Zalo User ID. Vui lòng cập nhật trước.')

        checklist = self.document_checklist_ids[:1]
        if not checklist:
            from odoo.exceptions import UserError as UE
            raise UE('Chưa có checklist hồ sơ. Vui lòng tạo checklist trước.')

        pending_items = checklist.line_ids.filtered(lambda l: l.status == 'pending')
        if not pending_items:
            from odoo.exceptions import UserError as UE
            raise UE('Không có giấy tờ nào còn thiếu trong checklist.')

        items_text = '\n'.join(f'• {line.item_id.name}' for line in pending_items[:10])
        partner_name = self.partner_id.name or 'Anh/Chị'
        message = (
            f'Xin chào {partner_name},\n\n'
            f'Để hoàn thiện hồ sơ vay/sản phẩm, Ngân hàng cần bổ sung các giấy tờ sau:\n'
            f'{items_text}\n\n'
            f'Kính nhờ Anh/Chị bổ sung sớm để chúng tôi xử lý nhanh nhất. '
            f'Mọi thắc mắc vui lòng liên hệ nhân viên phụ trách. Trân trọng!'
        )

        from .crm_ai_service import CrmAiService
        service = CrmAiService(self.env)
        success = service.send_zalo_message(self.zalo_user_id, message)

        if success:
            self.message_post(
                body=Markup(
                    f'<b>📱 Đã gửi Zalo nhắc hồ sơ:</b><br/>'
                    f'<pre style="font-size:11px">{message}</pre>'
                ),
                subtype_xmlid='mail.mt_note',
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': 'Đã gửi Zalo nhắc hồ sơ thành công!', 'type': 'success'},
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': 'Gửi Zalo thất bại. Kiểm tra cấu hình Zalo OA.', 'type': 'danger'},
            }
