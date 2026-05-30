from odoo import models, fields


CUSTOMER_TYPE_SELECTION = [
    ('individual', 'Khách hàng cá nhân'),
    ('business', 'Khách hàng doanh nghiệp'),
]


class CrmCustomerSegment(models.Model):
    _name = 'crm.customer.segment'
    _description = 'Customer Segment by Customer Type'
    _order = 'customer_type, sequence, name'

    name = fields.Char(string='Tên phân khúc', required=True)
    code = fields.Char(string='Mã phân khúc', required=True, index=True)
    customer_type = fields.Selection(
        CUSTOMER_TYPE_SELECTION,
        string='Loại khách hàng',
        required=True,
        default='individual',
        index=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Mô tả')

    _code_customer_type_unique = models.Constraint(
        'UNIQUE(code, customer_type)',
        'Mã phân khúc phải là duy nhất trong từng loại khách hàng.',
    )
