import base64
import os
import logging

_logger = logging.getLogger(__name__)


def _post_init_set_logo(env):
    """Đặt logo ngân hàng cho tất cả công ty khi cài module lần đầu."""
    logo_path = os.path.join(
        os.path.dirname(__file__),
        'static', 'img', 'bank_logo.svg',
    )
    if not os.path.exists(logo_path):
        _logger.warning('bank_theme: logo file không tìm thấy tại %s', logo_path)
        return

    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read())

    companies = env['res.company'].search([])
    companies.write({'logo': logo_b64})
    _logger.info('bank_theme: đã cập nhật logo cho %d công ty', len(companies))
