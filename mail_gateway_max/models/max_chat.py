from odoo import fields, models


class MaxChat(models.Model):
    _name = "max.chat"
    _description = "MAX Chat"

    name = fields.Char(
        required=True, help="Friendly name for the chat (e.g. Client Group)"
    )
    chat_id = fields.Char(required=True, help="Chat ID from MAX")
    gateway_id = fields.Many2one(
        "mail.gateway", ondelete="cascade", string="Mail Gateway"
    )
