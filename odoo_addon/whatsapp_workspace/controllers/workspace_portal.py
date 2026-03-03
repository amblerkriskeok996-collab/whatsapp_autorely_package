from werkzeug.utils import redirect

from odoo import http
from odoo.http import request

from ..models.wa_runtime import normalize_base_url


class WhatsappWorkspacePortalController(http.Controller):
    @http.route("/whatsapp_workspace/account/home_embed/<int:account_id>", type="http", auth="user", methods=["GET"])
    def home_embed(self, account_id, **kwargs):
        account = request.env["whatsapp.workspace.account"].sudo().browse(account_id)
        if not account.exists():
            return request.not_found()
        base_url = normalize_base_url(account.api_base_url)
        if not base_url:
            return request.not_found()
        return redirect(f"{base_url}/account-home", code=302)

    @http.route("/whatsapp_workspace/account/login_and_open/<int:account_id>", type="http", auth="user", methods=["GET"])
    def login_and_open(self, account_id, **kwargs):
        account = request.env["whatsapp.workspace.account"].sudo().browse(account_id)
        if not account.exists():
            return request.not_found()
        account.action_login()
        return redirect(f"/whatsapp_workspace/account/home_embed/{account.id}", code=302)
