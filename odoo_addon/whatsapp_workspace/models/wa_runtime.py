import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _
from odoo.exceptions import UserError


DEFAULT_WORKSPACE_ROOT = r"D:\code\programs\Whatsapp"
DEFAULT_WA_API_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_RAG_API_BASE_URL = "http://127.0.0.1:18080"
DEFAULT_HTTP_TIMEOUT_SECONDS = 20


def normalize_base_url(raw):
    return str(raw or "").strip().rstrip("/")


def get_configured_base_url(env):
    value = env["ir.config_parameter"].sudo().get_param("whatsapp_workspace.api_base_url", DEFAULT_WA_API_BASE_URL)
    return normalize_base_url(value)


def build_url(base_url, path):
    normalized = normalize_base_url(base_url)
    if not normalized:
        raise UserError(_("WhatsApp Workspace API base URL is empty."))
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{normalized}{path}"


def dump_json(payload):
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return str(payload)


def _decode_response_payload(body_bytes):
    raw_text = body_bytes.decode("utf-8", errors="replace")
    if not raw_text.strip():
        return {}
    try:
        return json.loads(raw_text)
    except Exception:
        return {"raw": raw_text}


def request_json(base_url, method, path, payload=None, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS):
    body_bytes = b""
    headers = {"Accept": "application/json"}
    if payload is not None:
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url=build_url(base_url, path),
        data=body_bytes if body_bytes else None,
        headers=headers,
        method=str(method or "GET").upper(),
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            parsed_payload = _decode_response_payload(response.read())
            return status_code, parsed_payload
    except HTTPError as exc:
        parsed_payload = _decode_response_payload(exc.read() or b"")
        return exc.code, parsed_payload
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise UserError(_("Failed to connect to WhatsApp Workspace API: %s") % reason) from exc
    except TimeoutError as exc:
        raise UserError(_("WhatsApp Workspace API request timed out.")) from exc
