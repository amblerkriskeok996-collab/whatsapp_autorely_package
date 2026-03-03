# WhatsApp Autorely 安装与启动说明

## 目录说明
- `odoo_addon/whatsapp_workspace`：Odoo 应用源码
- `services/whatsapp-web`：WhatsApp webhook 服务
- `services/milvus`：Milvus + RAG 服务
- `scripts`：安装、启动、停止脚本
- `runtime/logs`：运行日志
- `runtime/pids`：进程 PID 记录

## 前置条件
1. 已安装 Conda
2. 已安装 Docker Desktop 并启动
3. 本机有 Odoo 源码目录（默认：`D:\code\programs\odoo`）
4. 建议存在以下 conda 环境：
   - `odoo`
   - `whatsapp-web`
   - `milvus`

## 安装 Odoo App
```powershell
cd D:\code\programs\whatsapp_autorely_package\scripts
.\install_odoo_addon.ps1 -OdooRoot D:\code\programs\odoo -TargetAddonsDir custom_addons -UpgradeModule
```

## 启动服务
### 一键启动
```powershell
cd D:\code\programs\whatsapp_autorely_package\scripts
.\start_all.ps1
```

### 分步启动
```powershell
.\start_milvus.ps1
.\start_rag_api.ps1
.\start_whatsapp_web.ps1
```

## 健康检查
```powershell
Invoke-WebRequest http://127.0.0.1:18080/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000/api/account/status -UseBasicParsing
```

## Odoo 内使用
1. 打开 `WhatsApp Workspace` 应用
2. 新建/选择账号记录
3. 点击 `Login`（自动预热服务并打开扫码）
4. 手机扫码登录

## 模拟消息联调
```powershell
cd D:\code\programs\whatsapp_autorely_package\services\whatsapp-web
node tools\mock-incoming-8617628627274.js --api-url http://127.0.0.1:3000/webhook/whatsapp-workflow --body "I want to know DRG cost range for heart transplant"
```

预期返回关键字段：
- `ai.used=true`
- `ai.rag.searched=true`
- `ai.rag.resultsCount>0`
- `delivery.sent=true/false`

## 停止服务
```powershell
cd D:\code\programs\whatsapp_autorely_package\scripts
.\stop_all.ps1
.\stop_all.ps1 -StopMilvus
```

## 常见问题
1. `3000` 不通：执行 `.\start_whatsapp_web.ps1`，并查看 `runtime/logs/whatsapp_web.err.log`
2. `18080` 不通：执行 `.\start_rag_api.ps1`，并查看 `runtime/logs/rag_api.err.log`
3. 扫码失败：在 Odoo 里点 `Switch & Re-Scan`，并在手机端清理历史关联设备
