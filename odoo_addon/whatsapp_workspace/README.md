# whatsapp_workspace

Independent Odoo app for managing an external Whatsapp workspace project through HTTP APIs.

## Design Goal

- Keep `D:\code\programs\Whatsapp` unchanged.
- Keep Odoo and Whatsapp project codebases independent.
- Manage account status, login, account switching, manual reply, and workflow tests directly in Odoo.

## Mapped Endpoints

- `GET /api/account/status`
- `POST /api/account/login`
- `POST /api/account/switch-account`
- `POST /webhook/reply`
- `POST /webhook/whatsapp-workflow`

## Settings

Use `Settings -> WhatsApp Workspace` to configure:

- `Workspace Root Path`
- `WhatsApp API Base URL` (default: `http://127.0.0.1:3000`)
- `RAG API Base URL` (default: `http://127.0.0.1:18080`)

