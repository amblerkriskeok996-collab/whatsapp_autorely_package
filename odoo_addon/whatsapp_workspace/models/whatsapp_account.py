import socket
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .wa_runtime import dump_json, get_configured_base_url, normalize_base_url, request_json


class WhatsappWorkspaceAccount(models.Model):
    _name = "whatsapp.workspace.account"
    _description = "Whatsapp Workspace Account"

    name = fields.Char(required=True)
    api_base_url = fields.Char(required=True, default=lambda self: get_configured_base_url(self.env))
    portal_state = fields.Selection(
        [
            ("initializing", "Initializing"),
            ("qr_required", "QR Required"),
            ("authenticated", "Authenticated"),
            ("ready", "Ready"),
            ("auth_failure", "Auth Failure"),
            ("disconnected", "Disconnected"),
            ("switching_account", "Switching Account"),
            ("reinitializing", "Reinitializing"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        required=True,
        readonly=True,
    )
    portal_detail = fields.Char()
    wa_state = fields.Char()
    login_allowed = fields.Boolean(default=False)
    login_message = fields.Char()
    account_wid = fields.Char()
    account_push_name = fields.Char()
    account_platform = fields.Char()
    last_checked_at = fields.Datetime()
    raw_payload = fields.Text()
    note = fields.Text()
    active = fields.Boolean(default=True)

    def _ensure_unique_account_wid(self, wid):
        self.ensure_one()
        normalized_wid = str(wid or "").strip()
        if not normalized_wid:
            return
        duplicate = self.search(
            [
                ("id", "!=", self.id),
                ("active", "=", True),
                ("account_wid", "=", normalized_wid),
            ],
            limit=1,
        )
        if duplicate:
            raise UserError(_("该账号已绑定请勿重复绑定"))

    def _apply_status_payload(self, payload):
        self.ensure_one()
        data = payload if isinstance(payload, dict) else {}
        login_action = data.get("loginAction") if isinstance(data.get("loginAction"), dict) else {}
        account = data.get("account") if isinstance(data.get("account"), dict) else {}

        state_value = str(data.get("portalState") or "").strip() or "unknown"
        allowed_states = {item[0] for item in self._fields["portal_state"].selection}
        if state_value not in allowed_states:
            state_value = "unknown"

        values = {
            "portal_state": state_value,
            "portal_detail": str(data.get("detail") or ""),
            "wa_state": str(data.get("waState") or ""),
            "login_allowed": bool(login_action.get("allowed")),
            "login_message": str(login_action.get("message") or ""),
            "account_wid": str(account.get("wid") or ""),
            "account_push_name": str(account.get("pushName") or ""),
            "account_platform": str(account.get("platform") or ""),
            "last_checked_at": fields.Datetime.now(),
            "raw_payload": dump_json(data),
        }
        self._ensure_unique_account_wid(values["account_wid"])
        self.write(values)
        return values

    @api.constrains("account_wid", "active")
    def _check_account_wid_unique(self):
        for record in self:
            if not record.active:
                continue
            normalized_wid = str(record.account_wid or "").strip()
            if not normalized_wid:
                continue
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("active", "=", True),
                    ("account_wid", "=", normalized_wid),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(_("该账号已绑定请勿重复绑定"))

    def _request_api(self, method, path, payload=None):
        self.ensure_one()
        try:
            status_code, response_payload = request_json(self.api_base_url, method, path, payload=payload)
        except UserError as exc:
            raise UserError(_("无法连接 WhatsApp 服务，请确认服务已启动或端口可达：%s") % normalize_base_url(self.api_base_url)) from exc
        if not isinstance(response_payload, dict):
            response_payload = {"raw": str(response_payload)}
        data = response_payload.get("data")
        if isinstance(data, dict):
            self._apply_status_payload(data)
        self.write({"note": str(response_payload.get("message") or response_payload.get("error") or "")})
        return status_code, response_payload

    def _ensure_success(self, status_code, response_payload):
        if status_code >= 400 or response_payload.get("success") is False:
            error_text = str(response_payload.get("error") or _("请求 WhatsApp 服务失败。"))
            raise UserError(error_text)

    def _is_api_port_reachable(self, timeout_seconds=2.0):
        self.ensure_one()
        base_url = normalize_base_url(self.api_base_url)
        if not base_url:
            return False
        parsed_url = urlparse(base_url)
        host = parsed_url.hostname
        if not host:
            return False
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds):
                return True
        except OSError:
            return False

    def _warmup_whatsapp_service(self, require_api_ready=False):
        self.ensure_one()
        self.env["res.config.settings"].ensure_whatsapp_web_example_running()
        base_url = normalize_base_url(self.api_base_url)
        if not base_url:
            raise UserError(_("未配置 WhatsApp API 地址，请先在设置中填写。"))

        if require_api_ready and not self._is_api_port_reachable():
            raise UserError(_("WhatsApp 服务正在启动中或端口不可达，请稍后重试：%s") % base_url)

    def action_sync_status(self):
        results = []
        for account in self:
            account._warmup_whatsapp_service(require_api_ready=True)
            status_code, response_payload = account._request_api("GET", "/api/account/status")
            account._ensure_success(status_code, response_payload)
            results.append(
                {
                    "id": account.id,
                    "status_code": status_code,
                    "payload": response_payload,
                }
            )
        return results[0] if len(results) == 1 else results

    def action_login(self):
        self.ensure_one()
        self._warmup_whatsapp_service(require_api_ready=True)
        status_code, response_payload = self._request_api("GET", "/api/account/status")
        self._ensure_success(status_code, response_payload)

        if self.portal_state != "ready":
            return self.action_open_scan_page()

        status_code, response_payload = self._request_api("POST", "/api/account/login", payload={})
        self._ensure_success(status_code, response_payload)
        opened_url = str(response_payload.get("openedUrl") or "").strip()
        if opened_url:
            return self._build_open_url_action(opened_url)
        return self.action_open_account_home()

    def action_get_home_embed_data(self):
        self.ensure_one()
        base_url = normalize_base_url(self.api_base_url)
        return {
            "account_id": self.id,
            "embed_url": f"{base_url}/account-home" if base_url else "",
            "proxy_embed_url": f"/whatsapp_workspace/account/home_embed/{self.id}",
            "proxy_login_url": f"/whatsapp_workspace/account/login_and_open/{self.id}",
        }

    def action_switch_account(self):
        results = []
        for account in self:
            status_code, response_payload = account._request_api("POST", "/api/account/switch-account", payload={})
            account._ensure_success(status_code, response_payload)
            results.append(
                {
                    "id": account.id,
                    "status_code": status_code,
                    "payload": response_payload,
                }
            )
        return results[0] if len(results) == 1 else results

    def _build_open_url_action(self, target_url):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": target_url,
            "target": "new",
        }

    def action_open_scan_page(self):
        self.ensure_one()
        self._warmup_whatsapp_service(require_api_ready=False)
        base_url = normalize_base_url(self.api_base_url)
        if not base_url:
            raise UserError(_("未配置 WhatsApp API 地址，请先在设置中填写。"))
        return self._build_open_url_action(f"{base_url}/")

    def action_open_account_home(self):
        self.ensure_one()
        self._warmup_whatsapp_service(require_api_ready=False)
        base_url = normalize_base_url(self.api_base_url)
        if not base_url:
            raise UserError(_("未配置 WhatsApp API 地址，请先在设置中填写。"))
        return self._build_open_url_action(f"{base_url}/account-home")

    def action_switch_account_and_open_scan(self):
        self.ensure_one()
        self._warmup_whatsapp_service(require_api_ready=True)
        self.action_switch_account()
        return self.action_open_scan_page()

    @api.model
    def action_get_webhook_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "incoming_path": "/whatsapp_workspace/webhook/incoming",
            "forward_url": params.get_param("whatsapp_workspace.webhook_forward_url", ""),
        }

    @api.model
    def action_set_webhook_forward_url(self, forward_url):
        url = str(forward_url or "").strip()
        self.env["ir.config_parameter"].sudo().set_param("whatsapp_workspace.webhook_forward_url", url)
        return {
            "forward_url": url,
            "incoming_path": "/whatsapp_workspace/webhook/incoming",
        }

    @api.model
    def action_get_webhook_logs(self, limit=30):
        safe_limit = max(1, min(int(limit or 30), 200))
        logs = self.env["whatsapp.workspace.webhook.log"].sudo().search([], order="id desc", limit=safe_limit)
        return logs.read(
            [
                "event",
                "message_id",
                "from_jid",
                "to_jid",
                "body",
                "forwarded",
                "forward_url",
                "forward_status_code",
                "forward_error",
                "create_date",
            ]
        )
