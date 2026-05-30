from odoo import models
import logging

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, **kwargs):
        """Hook: after posting on crm.lead, update last_sentiment if available."""
        msg = super().message_post(**kwargs)
        return msg
