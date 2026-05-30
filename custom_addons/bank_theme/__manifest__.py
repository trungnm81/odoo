{
    'name': 'Bank Theme',
    'version': '19.0.1.0.0',
    'summary': 'Giao diện ngân hàng — màu chủ đạo #0054A5, logo ngân hàng',
    'category': 'Themes',
    'depends': ['web', 'web_responsive'],
    'data': [],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'bank_theme/static/src/scss/primary_variables_override.scss'),
        ],
    },
    'post_init_hook': '_post_init_set_logo',
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
