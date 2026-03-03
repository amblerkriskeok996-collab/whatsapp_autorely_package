from odoo import fields, models


class WhatsappWorkspaceWebhookLog(models.Model):
    _name = "whatsapp.workspace.webhook.log"
    _description = "WhatsApp Workspace Webhook Forward Log"
    _order = "id desc"

    event = fields.Char(readonly=True)
    message_id = fields.Char(readonly=True)
    from_jid = fields.Char(readonly=True)
    to_jid = fields.Char(readonly=True)
    body = fields.Text(readonly=True)
    forwarded = fields.Boolean(readonly=True)
    forward_url = fields.Char(readonly=True)
    forward_status_code = fields.Integer(readonly=True)
    forward_error = fields.Text(readonly=True)
    response_body = fields.Text(readonly=True)

