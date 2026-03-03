import os
import shutil
import signal
import subprocess

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .wa_runtime import DEFAULT_RAG_API_BASE_URL, DEFAULT_WA_API_BASE_URL, DEFAULT_WORKSPACE_ROOT


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_workspace_root_path = fields.Char(
        string="Whatsapp Workspace Root Path",
        config_parameter="whatsapp_workspace.root_path",
        default=DEFAULT_WORKSPACE_ROOT,
    )
    whatsapp_workspace_api_base_url = fields.Char(
        string="Whatsapp Workspace API Base URL",
        config_parameter="whatsapp_workspace.api_base_url",
        default=DEFAULT_WA_API_BASE_URL,
    )
    whatsapp_workspace_rag_api_base_url = fields.Char(
        string="Whatsapp Workspace RAG API Base URL",
        config_parameter="whatsapp_workspace.rag_api_base_url",
        default=DEFAULT_RAG_API_BASE_URL,
    )
    whatsapp_workspace_webhook_forward_url = fields.Char(
        string="WhatsApp Incoming Forward Webhook URL",
        config_parameter="whatsapp_workspace.webhook_forward_url",
        help="When Odoo receives incoming webhook payload at /whatsapp_workspace/webhook/incoming, it forwards payload to this URL.",
    )

    def _get_workspace_root_path(self):
        self.ensure_one()
        return str(
            self.env["ir.config_parameter"].sudo().get_param("whatsapp_workspace.root_path", DEFAULT_WORKSPACE_ROOT) or ""
        ).strip()

    def _get_example_script_path(self):
        self.ensure_one()
        return os.path.join(self._get_workspace_root_path(), "whatsapp-web", "example.js")

    def _notify(self, message, level="success"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Workspace"),
                "message": message,
                "type": level,
                "sticky": False,
            },
        }

    @api.model
    def _build_example_start_command(self, script_path):
        conda_exe = str(os.environ.get("CONDA_EXE") or "").strip() or shutil.which("conda")
        if conda_exe:
            return [conda_exe, "run", "-n", "whatsapp-web", "node", script_path]

        node_exe = shutil.which("node")
        if node_exe:
            return [node_exe, script_path]

        raise UserError(_("无法启动 WhatsApp 服务：未找到可用的 conda 或 node 可执行文件。"))

    @api.model
    def _is_pid_running(self, pid_value):
        try:
            pid = int(str(pid_value or "").strip())
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # 进程存在但权限不足。
            return True
        except OSError:
            return False
        return True

    @api.model
    def ensure_whatsapp_web_example_running(self):
        params = self.env["ir.config_parameter"].sudo()
        existing_pid = str(params.get_param("whatsapp_workspace.example_service_pid", "") or "").strip()
        if existing_pid:
            if self._is_pid_running(existing_pid):
                return {"running": True, "started": False, "pid": existing_pid}
            params.set_param("whatsapp_workspace.example_service_pid", "")

        root_path = str(params.get_param("whatsapp_workspace.root_path", DEFAULT_WORKSPACE_ROOT) or "").strip()
        script_path = os.path.join(root_path, "whatsapp-web", "example.js")
        if not root_path or not os.path.isdir(root_path):
            raise UserError(_("WhatsApp 工作目录不存在，请检查配置：%s") % root_path)
        if not os.path.isfile(script_path):
            raise UserError(_("未找到启动脚本 example.js：%s") % script_path)

        start_command = self._build_example_start_command(script_path)
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            start_command,
            cwd=os.path.dirname(script_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        params.set_param("whatsapp_workspace.example_service_pid", str(process.pid))
        return {"running": True, "started": True, "pid": str(process.pid)}

    def action_start_whatsapp_web_example(self):
        self.ensure_one()
        result = self.ensure_whatsapp_web_example_running()
        if result.get("started"):
            return self._notify(_("WhatsApp 服务已启动（PID: %s）。") % result.get("pid"), level="success")
        return self._notify(_("WhatsApp 服务已在运行（PID: %s）。") % result.get("pid"), level="info")

    def action_stop_whatsapp_web_example(self):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        raw_pid = str(params.get_param("whatsapp_workspace.example_service_pid", "") or "").strip()
        if not raw_pid:
            return self._notify(_("当前没有可停止的 WhatsApp 服务进程。"), level="warning")

        try:
            pid = int(raw_pid)
        except ValueError as exc:
            params.set_param("whatsapp_workspace.example_service_pid", "")
            raise UserError(_("保存的服务 PID 无效：%s") % raw_pid) from exc

        if os.name == "nt":
            subprocess.run(  # nosec B603,B607
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            os.kill(pid, signal.SIGTERM)

        params.set_param("whatsapp_workspace.example_service_pid", "")
        return self._notify(_("已发送停止信号（PID: %s）。") % pid, level="success")
