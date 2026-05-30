import base64
import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmAiScanDocument(models.TransientModel):
    _name = 'crm.ai.scan.document'
    _description = 'Quét tài liệu AI (Name Card / CCCD / GPKD)'

    scan_type = fields.Selection(
        [
            ('name_card', 'Name Card / Danh thiếp'),
            ('cccd_front', 'CCCD mặt trước'),
            ('cccd_back', 'CCCD mặt sau'),
            ('gpkd', 'Giấy phép kinh doanh'),
        ],
        string='Loại tài liệu',
        required=True,
        default='name_card',
    )
    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')

    image_data = fields.Binary(string='Ảnh tài liệu')
    image_filename = fields.Char(string='Tên file')

    # OCR result (readonly)
    result_json = fields.Text(string='Kết quả OCR (JSON)', readonly=True)
    result_display = fields.Html(string='Kết quả', compute='_compute_result_display')

    # Extracted fields — name card / CCCD
    extracted_full_name = fields.Char(string='Họ và tên')
    extracted_phone = fields.Char(string='Điện thoại')
    extracted_email = fields.Char(string='Email')
    extracted_company = fields.Char(string='Công ty')
    extracted_title = fields.Char(string='Chức danh')
    extracted_address = fields.Char(string='Địa chỉ')
    extracted_website = fields.Char(string='Website')
    # CCCD specific
    extracted_date_of_birth = fields.Date(string='Ngày sinh')
    extracted_gender = fields.Selection([('male', 'Nam'), ('female', 'Nữ')], string='Giới tính')
    extracted_cccd_number = fields.Char(string='Số CCCD')
    extracted_cccd_issue_date = fields.Date(string='Ngày cấp')
    extracted_cccd_issue_place = fields.Char(string='Nơi cấp')

    state = fields.Selection(
        [('scan', 'Quét ảnh'), ('review', 'Xem kết quả'), ('done', 'Hoàn thành')],
        default='scan',
    )

    @api.depends('result_json', 'scan_type')
    def _compute_result_display(self):
        for rec in self:
            if not rec.result_json:
                rec.result_display = '<em class="text-muted">Chưa quét</em>'
                continue
            try:
                data = json.loads(rec.result_json)
                rows = ''.join(
                    f'<tr><td class="fw-semibold pe-3">{k}</td><td>{v}</td></tr>'
                    for k, v in data.items() if v
                )
                rec.result_display = f'<table class="table table-sm">{rows}</table>'
            except Exception:
                rec.result_display = f'<pre>{rec.result_json[:500]}</pre>'

    def action_scan(self):
        """Gọi OCR / Vision AI và điền kết quả vào các trường."""
        self.ensure_one()
        if not self.image_data:
            raise UserError('Vui lòng chọn ảnh tài liệu.')
        image_bytes = base64.b64decode(self.image_data)
        from odoo.addons.crm_ai_banking.models.crm_ai_service import CrmAiService
        service = CrmAiService(self.env)

        if self.scan_type == 'name_card':
            result = service.extract_card(image_bytes)
        else:
            result = service.extract_id_card(image_bytes, self.scan_type)

        if not result:
            raise UserError('OCR không trả về kết quả. Kiểm tra API key và kết nối mạng.')

        self.result_json = json.dumps(result, ensure_ascii=False, indent=2)
        self._populate_extracted_fields(result)
        self.state = 'review'
        return self._reopen()

    def _populate_extracted_fields(self, data: dict):
        """Map OCR result dict → extracted_* fields."""
        self.extracted_full_name = data.get('full_name', '')
        self.extracted_phone = data.get('phone', '')
        self.extracted_email = data.get('email', '')
        self.extracted_company = data.get('company', '')
        self.extracted_title = data.get('title', '')
        self.extracted_address = data.get('address', '') or data.get('place_of_residence', '')
        self.extracted_website = data.get('website', '')
        self.extracted_cccd_number = data.get('id_number', '')
        self.extracted_cccd_issue_place = data.get('issue_place', '')

        dob_str = data.get('date_of_birth', '')
        if dob_str:
            self.extracted_date_of_birth = self._parse_vn_date(dob_str)

        issue_date_str = data.get('issue_date', '')
        if issue_date_str:
            self.extracted_cccd_issue_date = self._parse_vn_date(issue_date_str)

        gender_raw = (data.get('gender', '') or '').lower()
        if 'nữ' in gender_raw or 'nu' in gender_raw or 'female' in gender_raw or 'f' == gender_raw:
            self.extracted_gender = 'female'
        elif gender_raw:
            self.extracted_gender = 'male'

    @staticmethod
    def _parse_vn_date(date_str: str):
        """Parse Vietnamese date strings like 25/03/1990 or 25-03-1990."""
        import re
        from datetime import date
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y'):
            try:
                import datetime
                return datetime.datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return False

    def action_apply_to_lead(self):
        """Áp dụng thông tin đã trích xuất vào Lead hoặc Partner."""
        self.ensure_one()
        if self.scan_type == 'name_card':
            return self._apply_name_card()
        elif self.scan_type in ('cccd_front', 'cccd_back'):
            return self._apply_cccd()
        elif self.scan_type == 'gpkd':
            return self._apply_gpkd()
        return {'type': 'ir.actions.act_window_close'}

    def _apply_gpkd(self):
        """Cập nhật thông tin GPKD vào res.partner của lead."""
        partner = self.partner_id
        if not partner and self.lead_id:
            partner = self.lead_id.partner_id
        if not partner:
            if not self.extracted_company:
                from odoo.exceptions import UserError
                raise UserError('Không đọc được tên công ty từ GPKD.')
            partner = self.env['res.partner'].create({
                'name': self.extracted_company, 'is_company': True,
            })

        vals = {}
        vals['is_company'] = True
        vals['customer_type'] = 'business'
        if self.extracted_company:
            vals['name'] = self.extracted_company
        if self.extracted_address:
            vals['street'] = self.extracted_address

        try:
            ocr_data = json.loads(self.result_json or '{}')
        except Exception:
            ocr_data = {}

        # MST — lưu encrypted, không log rõ
        tax_id = ocr_data.get('tax_id', '')
        if tax_id and hasattr(partner, 'cccd_number'):
            vals['cccd_number'] = tax_id  # reuse encrypted field tạm thời

        if ocr_data.get('representative'):
            vals['function'] = ocr_data['representative']

        partner.write(vals)
        partner._message_log(
            body=f'🏢 Thông tin GPKD cập nhật từ ảnh quét — ngày {fields.Date.today()}'
        )

        if self.lead_id:
            if not self.lead_id.partner_id:
                self.lead_id.write({'partner_id': partner.id})
            self.lead_id.write({'customer_type': 'business'})
            if ocr_data.get('company_name'):
                self.lead_id.write({'name': f'[GPKD] {ocr_data["company_name"]}'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.lead_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _apply_name_card(self):
        """Tạo lead mới hoặc update partner từ name card."""
        # Kiểm tra trùng lặp qua phone / email
        existing_partner = False
        if self.extracted_phone:
            existing_partner = self.env['res.partner'].search(
                [('phone', '=', self.extracted_phone)], limit=1
            )
        if not existing_partner and self.extracted_email:
            existing_partner = self.env['res.partner'].search(
                [('email', '=', self.extracted_email)], limit=1
            )

        partner_vals = {}
        if self.extracted_full_name:
            partner_vals['name'] = self.extracted_full_name
        if self.extracted_phone:
            partner_vals['phone'] = self.extracted_phone
        if self.extracted_email:
            partner_vals['email'] = self.extracted_email
        if self.extracted_company:
            partner_vals['company_name'] = self.extracted_company
        if self.extracted_title:
            partner_vals['function'] = self.extracted_title
        if self.extracted_address:
            partner_vals['street'] = self.extracted_address
        if self.extracted_website:
            partner_vals['website'] = self.extracted_website

        if existing_partner:
            existing_partner.write(partner_vals)
            partner = existing_partner
        else:
            partner_vals.setdefault('name', 'Unknown')
            partner = self.env['res.partner'].create(partner_vals)

        # Tạo lead hoặc cập nhật lead hiện tại
        if self.lead_id:
            lead = self.lead_id
            lead.write({'partner_id': partner.id})
        else:
            lead = self.env['crm.lead'].create({
                'name': f'[Name Card] {partner.name}',
                'partner_id': partner.id,
                'type': 'opportunity',
            })
            lead._message_log(
                body=f'📇 Lead tạo từ name card quét bởi {self.env.user.name}'
            )

        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _apply_cccd(self):
        """Cập nhật thông tin CCCD vào res.partner — số CCCD lưu encrypted."""
        partner = self.partner_id
        if not partner and self.lead_id:
            partner = self.lead_id.partner_id
        if not partner:
            # Tạo partner mới từ thông tin CCCD
            if not self.extracted_full_name:
                raise UserError('Không đọc được tên từ CCCD. Vui lòng nhập thủ công.')
            partner = self.env['res.partner'].create({
                'name': self.extracted_full_name,
                'is_company': False,
            })

        vals = {}
        vals['customer_type'] = 'individual'
        if self.extracted_full_name and self.scan_type == 'cccd_front':
            vals['name'] = self.extracted_full_name
        if self.extracted_date_of_birth:
            vals['date_of_birth'] = self.extracted_date_of_birth
        if self.extracted_gender:
            vals['gender'] = self.extracted_gender
        if self.extracted_address:
            vals['street'] = self.extracted_address
        if self.extracted_cccd_number:
            vals['cccd_number'] = self.extracted_cccd_number
        if self.extracted_cccd_issue_date:
            vals['cccd_issue_date'] = self.extracted_cccd_issue_date
        if self.extracted_cccd_issue_place:
            vals['cccd_issue_place'] = self.extracted_cccd_issue_place

        partner.write(vals)
        partner._message_log(
            body=f'🪪 Thông tin CCCD cập nhật từ ảnh quét — ngày {fields.Date.today()}'
        )

        self.state = 'done'
        if self.lead_id:
            if not self.lead_id.partner_id:
                self.lead_id.write({'partner_id': partner.id})
            self.lead_id.write({'customer_type': 'individual'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.lead_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_rescan(self):
        """Quay lại bước upload ảnh để quét lại."""
        self.ensure_one()
        self.write({
            'state': 'scan',
            'result_json': False,
            'extracted_full_name': False,
            'extracted_phone': False,
            'extracted_email': False,
            'extracted_company': False,
            'extracted_title': False,
            'extracted_address': False,
            'extracted_website': False,
            'extracted_cccd_number': False,
            'extracted_date_of_birth': False,
            'extracted_gender': False,
            'extracted_cccd_issue_date': False,
            'extracted_cccd_issue_place': False,
        })
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': dict(self._fields['scan_type'].selection).get(self.scan_type, 'Quét tài liệu'),
        }
