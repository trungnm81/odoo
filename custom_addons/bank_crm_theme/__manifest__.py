{
    'name': 'Bank CRM Theme — Mobile Responsive',
    'version': '19.0.1.1.0',
    'summary': 'Tối ưu giao diện CRM ngân hàng cho mobile/tablet — cấu hình qua Settings',
    'category': 'Themes',
    'depends': ['crm', 'web_responsive', 'crm_ai_banking', 'bank_theme', 'base_setup'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bank_crm_theme/static/src/scss/mobile.scss',
            'bank_crm_theme/static/src/js/mobile_settings.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
