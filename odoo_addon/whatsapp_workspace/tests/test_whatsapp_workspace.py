from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from unittest.mock import patch

from odoo.addons.whatsapp_workspace.models.wa_runtime import normalize_base_url


@tagged("post_install", "-at_install")
class TestWhatsappWorkspace(TransactionCase):
    def test_normalize_base_url(self):
        self.assertEqual(normalize_base_url("http://127.0.0.1:3000/"), "http://127.0.0.1:3000")
        self.assertEqual(normalize_base_url("  http://127.0.0.1:3000/// "), "http://127.0.0.1:3000")

    def test_apply_status_payload(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
            }
        )
        payload = {
            "portalState": "ready",
            "detail": "ok",
            "waState": "CONNECTED",
            "loginAction": {"allowed": True, "message": "Account is ready"},
            "account": {
                "wid": "8617628627274@c.us",
                "pushName": "Alice",
                "platform": "android",
            },
        }

        account._apply_status_payload(payload)

        self.assertEqual(account.portal_state, "ready")
        self.assertEqual(account.portal_detail, "ok")
        self.assertEqual(account.wa_state, "CONNECTED")
        self.assertEqual(account.login_allowed, True)
        self.assertEqual(account.login_message, "Account is ready")
        self.assertEqual(account.account_wid, "8617628627274@c.us")
        self.assertEqual(account.account_push_name, "Alice")
        self.assertEqual(account.account_platform, "android")

    def test_webhook_config_roundtrip(self):
        account_model = self.env["whatsapp.workspace.account"]
        account_model.action_set_webhook_forward_url("https://example.test/incoming")
        config = account_model.action_get_webhook_config()

        self.assertEqual(config["incoming_path"], "/whatsapp_workspace/webhook/incoming")
        self.assertEqual(config["forward_url"], "https://example.test/incoming")

    def test_login_not_ready_opens_scan_page(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
                "portal_state": "qr_required",
                "login_allowed": False,
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ), patch.object(type(account), "_is_api_port_reachable", return_value=True
        ), patch.object(type(account), "_request_api", return_value=(200, {"success": True, "data": {"portalState": "qr_required"}})):
            action = account.action_login()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "http://127.0.0.1:3000/")

    def test_get_home_embed_url(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000/",
            }
        )
        data = account.action_get_home_embed_data()
        self.assertEqual(data["account_id"], account.id)
        self.assertEqual(data["embed_url"], "http://127.0.0.1:3000/account-home")
        self.assertEqual(data["proxy_embed_url"], f"/whatsapp_workspace/account/home_embed/{account.id}")
        self.assertEqual(data["proxy_login_url"], f"/whatsapp_workspace/account/login_and_open/{account.id}")

    def test_login_ready_state_calls_remote_api_and_opens_home(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
                "portal_state": "ready",
                "login_allowed": True,
            }
        )

        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ), patch.object(type(account), "_is_api_port_reachable", return_value=True
        ), patch.object(
            type(account),
            "_request_api",
            side_effect=[
                (200, {"success": True, "data": {"portalState": "ready"}}),
                (200, {"success": True, "openedUrl": "https://web.whatsapp.com/"}),
            ],
        ) as mock_call:
            action = account.action_login()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "https://web.whatsapp.com/")
        self.assertEqual(mock_call.call_count, 2)

    def test_open_scan_page_action(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000/",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ) as mock_ensure:
            action = account.action_open_scan_page()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "http://127.0.0.1:3000/")
        self.assertEqual(action["target"], "new")
        self.assertEqual(mock_ensure.call_count, 1)

    def test_open_account_home_action(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000/",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ):
            action = account.action_open_account_home()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "http://127.0.0.1:3000/account-home")

    def test_switch_account_and_open_scan(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ), patch.object(type(account), "_is_api_port_reachable", return_value=True), patch.object(
            type(account), "action_switch_account", return_value={"status_code": 200}
        ) as mock_switch:
            action = account.action_switch_account_and_open_scan()
        self.assertEqual(mock_switch.call_count, 1)
        self.assertEqual(action["url"], "http://127.0.0.1:3000/")

    def test_start_example_service(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("whatsapp_workspace.root_path", r"D:\code\programs\Whatsapp")
        settings = self.env["res.config.settings"].create({})

        with patch("odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isdir", return_value=True), patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isfile", return_value=True
        ), patch("odoo.addons.whatsapp_workspace.models.res_config_settings.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 5566
            action = settings.action_start_whatsapp_web_example()

        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(params.get_param("whatsapp_workspace.example_service_pid"), "5566")
        self.assertEqual(mock_popen.call_count, 1)

    def test_start_example_service_fallback_to_node(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("whatsapp_workspace.root_path", r"D:\code\programs\Whatsapp")
        settings = self.env["res.config.settings"].create({})

        with patch("odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isdir", return_value=True), patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isfile", return_value=True
        ), patch("odoo.addons.whatsapp_workspace.models.res_config_settings.os.environ", {}, create=True), patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.shutil.which", side_effect=[None, r"C:\Program Files\nodejs\node.exe"]
        ), patch("odoo.addons.whatsapp_workspace.models.res_config_settings.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 6677
            action = settings.action_start_whatsapp_web_example()

        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(params.get_param("whatsapp_workspace.example_service_pid"), "6677")
        self.assertEqual(mock_popen.call_count, 1)

    def test_stop_example_service(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("whatsapp_workspace.example_service_pid", "5566")
        settings = self.env["res.config.settings"].create({})

        with patch("odoo.addons.whatsapp_workspace.models.res_config_settings.os.name", "nt"), patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.subprocess.run"
        ) as mock_run:
            action = settings.action_stop_whatsapp_web_example()

        self.assertEqual(action["tag"], "display_notification")
        self.assertFalse(params.get_param("whatsapp_workspace.example_service_pid"))
        self.assertEqual(mock_run.call_count, 1)

    def test_ensure_example_service_restarts_when_stale_pid(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("whatsapp_workspace.root_path", r"D:\code\programs\Whatsapp")
        params.set_param("whatsapp_workspace.example_service_pid", "5566")
        settings = self.env["res.config.settings"].create({})

        with patch.object(type(settings), "_is_pid_running", return_value=False) as mock_is_running, patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isdir", return_value=True
        ), patch("odoo.addons.whatsapp_workspace.models.res_config_settings.os.path.isfile", return_value=True), patch(
            "odoo.addons.whatsapp_workspace.models.res_config_settings.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value.pid = 6677
            result = settings.ensure_whatsapp_web_example_running()

        self.assertEqual(result["running"], True)
        self.assertEqual(result["started"], True)
        self.assertEqual(result["pid"], "6677")
        self.assertEqual(params.get_param("whatsapp_workspace.example_service_pid"), "6677")
        self.assertEqual(mock_is_running.call_count, 1)
        self.assertEqual(mock_popen.call_count, 1)

    def test_sync_status_warms_service_and_calls_api(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ) as mock_ensure, patch.object(type(account), "_is_api_port_reachable", return_value=True), patch.object(
            type(account), "_request_api", return_value=(200, {"success": True, "data": {"portalState": "ready"}})
        ) as mock_request:
            account.action_sync_status()
        self.assertEqual(mock_ensure.call_count, 1)
        self.assertEqual(mock_request.call_count, 1)

    def test_sync_status_raises_clear_error_when_api_not_ready(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ), patch.object(type(account), "_is_api_port_reachable", return_value=False):
            with self.assertRaises(UserError) as exc:
                account.action_sync_status()
        self.assertIn("服务正在启动中", str(exc.exception))

    def test_login_raises_clear_error_when_api_not_ready(self):
        account = self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal",
                "api_base_url": "http://127.0.0.1:3000",
            }
        )
        with patch.object(
            self.env["res.config.settings"].__class__,
            "ensure_whatsapp_web_example_running",
            return_value={"running": True, "started": False, "pid": "5566"},
        ), patch.object(type(account), "_is_api_port_reachable", return_value=False):
            with self.assertRaises(UserError) as exc:
                account.action_login()
        self.assertIn("服务正在启动中", str(exc.exception))

    def test_duplicate_account_wid_not_allowed_for_active_records(self):
        self.env["whatsapp.workspace.account"].create(
            {
                "name": "Portal A",
                "api_base_url": "http://127.0.0.1:3000",
                "account_wid": "8617628627274@c.us",
                "active": True,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["whatsapp.workspace.account"].create(
                {
                    "name": "Portal B",
                    "api_base_url": "http://127.0.0.1:3000",
                    "account_wid": "8617628627274@c.us",
                    "active": True,
                }
            )
