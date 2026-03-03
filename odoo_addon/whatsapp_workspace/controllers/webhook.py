import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import http
from odoo.http import request


class WhatsappWorkspaceWebhookController(http.Controller):
    @http.route("/whatsapp_workspace/webhook/incoming", type="http", auth="public", methods=["POST"], csrf=False)
    def incoming(self, **kwargs):
        raw = request.httprequest.data or b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        payload = payload if isinstance(payload, dict) else {}
        params = request.env["ir.config_parameter"].sudo()
        forward_url = str(params.get_param("whatsapp_workspace.webhook_forward_url", "") or "").strip()

        forwarded = False
        status_code = 0
        forward_error = ""
        response_body = ""

        if forward_url:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            forward_request = Request(
                url=forward_url,
                data=body_bytes,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            try:
                with urlopen(forward_request, timeout=20) as response:
                    status_code = int(response.getcode() or 0)
                    response_body = response.read().decode("utf-8", errors="replace")[:3000]
                    forwarded = 200 <= status_code < 300
            except HTTPError as exc:
                status_code = int(exc.code or 0)
                response_body = (exc.read() or b"").decode("utf-8", errors="replace")[:3000]
                forward_error = str(exc)
            except URLError as exc:
                forward_error = str(getattr(exc, "reason", exc))
            except TimeoutError:
                forward_error = "timeout"
            except Exception as exc:
                forward_error = str(exc)

        request.env["whatsapp.workspace.webhook.log"].sudo().create(
            {
                "event": str(payload.get("event") or ""),
                "message_id": str(payload.get("messageId") or payload.get("requestId") or ""),
                "from_jid": str(payload.get("from") or payload.get("userJid") or ""),
                "to_jid": str(payload.get("to") or payload.get("receiverJid") or ""),
                "body": str(payload.get("body") or payload.get("text") or ""),
                "forwarded": bool(forwarded),
                "forward_url": forward_url,
                "forward_status_code": status_code,
                "forward_error": forward_error,
                "response_body": response_body,
            }
        )

        result = {
            "success": True,
            "forwarded": bool(forwarded),
            "forward_status_code": status_code,
            "forward_error": forward_error,
        }
        return request.make_response(
            json.dumps(result, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8")],
        )

