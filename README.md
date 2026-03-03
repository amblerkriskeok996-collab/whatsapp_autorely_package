# WhatsApp Autorely Package

This package contains:
- Odoo addon: `odoo_addon/whatsapp_workspace`
- WhatsApp webhook service: `services/whatsapp-web`
- Milvus + RAG service: `services/milvus`
- Install/start/stop scripts: `scripts/*.ps1`

Use this README from the extracted package root folder (the folder containing this file).

## 1) Prerequisites
- Windows + PowerShell
- Conda
- Docker Desktop
- An Odoo source folder (for example: `C:\work\odoo`)

Recommended conda envs:
- `odoo`
- `whatsapp-web`
- `milvus`

## 2) Install the Odoo App
```powershell
cd .\scripts
.\install_odoo_addon.ps1 -OdooRoot "C:\path\to\your\odoo" -TargetAddonsDir custom_addons -UpgradeModule
```

## 3) Start Required Services
One command:
```powershell
cd .\scripts
.\start_all.ps1
```

Or step-by-step:
```powershell
.\start_milvus.ps1
.\start_rag_api.ps1
.\start_whatsapp_web.ps1
```

## 4) Verify Service Health
```powershell
Invoke-WebRequest http://127.0.0.1:18080/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000/api/account/status -UseBasicParsing
```

## 5) Use in Odoo
1. Open app: `WhatsApp Workspace`
2. Create/select account record
3. Click `Login` (auto warmup + QR redirect)
4. Scan QR from WhatsApp mobile app

## 6) End-to-End Mock Test
```powershell
cd .\services\whatsapp-web
node tools\mock-incoming-8617628627274.js --api-url http://127.0.0.1:3000/webhook/whatsapp-workflow --body "I want to know DRG cost range for heart transplant"
```

Expected response fields:
- `ai.used = true`
- `ai.rag.searched = true`
- `ai.rag.resultsCount > 0`
- `delivery.sent = true/false`

## 7) Stop Services
```powershell
cd .\scripts
.\stop_all.ps1              # stop RAG + webhook
.\stop_all.ps1 -StopMilvus  # stop RAG + webhook + Milvus docker
```

## 8) Locations
- Logs: `runtime/logs`
- PID files: `runtime/pids`

## 9) Notes
- If WhatsApp binding fails, use `Switch & Re-Scan` in Odoo.
- Ensure phone-side linked devices are managed before scanning.
