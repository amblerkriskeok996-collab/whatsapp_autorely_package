{
    "name": "WhatsApp Workspace Bridge",
    "summary": "Manage external Whatsapp workspace services from Odoo",
    "version": "18.0.3.0.0",
    "category": "Marketing/Social Marketing",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["base", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/whatsapp_account_views.xml",
        "views/res_config_settings_views.xml",
        "views/whatsapp_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "whatsapp_workspace/static/src/js/whatsapp_workspace_cache_bust.js",
        ],
    },
    "application": True,
    "installable": True,
}
