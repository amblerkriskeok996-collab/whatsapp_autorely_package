# Whatsapp Workspace 项目总述

更新时间：2026-02-28

## 1. 总体定位
`D:\code\programs\Whatsapp` 是本地联调工作区，包含两个核心子项目：

1. `whatsapp-web`：基于 `whatsapp-web.js` 的 WhatsApp 接入、自动回复、账号管理前端（Node.js）。
2. `milvus`：DRG 医疗费用知识库检索服务（Python + Milvus + BM25）。

当前整体链路：
`WhatsApp 来消息 -> AI 分诊提取关键词 -> RAG 检索 DRG 费用 -> 生成回复 -> 回发用户`

## 2. 目录结构
```text
D:\code\programs\Whatsapp
├─ whatsapp-web\           # WhatsApp 接入层 + 账号门户前端
├─ milvus\                 # DRG 知识库与检索 API
└─ .tmp_model_test.py      # 临时测试文件
```

## 3. 子项目说明
### 3.1 whatsapp-web（消息接入 + 账号门户）
- 技术栈：Node.js、whatsapp-web.js、Puppeteer
- 关键能力：
  - 维持 WhatsApp 登录会话（`LocalAuth`）
  - 接收入站消息并标准化
  - AI 分诊 + 可选 RAG 查询 + 自动回复
  - 提供账号管理前端：
    - 点击登录：拉起已登录账号的 WhatsApp Web 首页
    - 账号失效：提示重新登录
    - 更换账号：清理登录信息并重启登录流程
  - 登录页关闭恢复：`Session closed` 时自动恢复一次再重试登录跳转
- 关键文件：
  - `example.js`：服务主入口、Webhook 路由、账号门户 API 路由
  - `public/account-portal.html`：账号管理页（登录 / 更换账号）
  - `public/account-home.html`：登录后首页
  - `src/accountPortalState.js`：门户状态机（ready/qr_required/auth_failure 等）
  - `src/whatsappPortalConfig.js`：门户运行配置（system chrome、UA、清理目录）
  - `src/portalLoginRecovery.js`：登录恢复策略
  - `src/webhookWorkflow.js`：AI+RAG 消息工作流
  - `src/medicalAiAssistant.js`：分诊与回复生成
  - `src/webhookPayload.js`：入站消息标准化
  - `tools/mock-incoming-8617628627274.js`：固定账号入站模拟工具

### 3.2 milvus（知识库层）
- 技术栈：Python、FastAPI、pymilvus、Milvus、BM25
- 数据源：`修改版费用(1).xlsx`
- 关键能力：
  - 清洗并入库 DRG 费用数据
  - 关键词检索（BM25 稀疏向量）
  - 为上游提供 `/search` API
- 关键文件：
  - `scripts/serve_rag_api.py`：RAG API（`/health`、`/search`）
  - `scripts/ingest_drg_to_milvus.py`：导入与建索引
  - `src/drg_pipeline.py`：清洗与向量处理主逻辑
  - `docker-compose.yml`：Milvus/etcd/minio 本地部署

## 4. 服务接口与端口
### 4.1 whatsapp-web（默认端口 `3000`）
- 前端页面：
  - `GET /`：账号管理页
  - `GET /account-home`：登录后首页
- 账号 API：
  - `GET /api/account/status`：查询门户状态与账号信息
  - `POST /api/account/login`：尝试拉起已登录 WhatsApp 首页（失效则返回重新登录提示）
  - `POST /api/account/switch-account`：清理登录数据并重启登录流程
- 消息 API：
  - `POST /webhook/whatsapp-workflow`：处理来消息（AI+RAG+回发）
  - `POST /webhook/reply`：直接发送消息

### 4.2 milvus / RAG API
- `GET /health`：健康检查
- `GET /search?keyword=<关键词>&top_k=<数量>`：DRG 检索
- 常用端口：
  - RAG API：`18080`
  - Milvus gRPC：`19530`
  - Milvus health：`9091`

## 5. 关键联调关系
- `whatsapp-web/example.js` 中 `RAG_API_URL` 默认 `http://127.0.0.1:18080`
- 分诊判定 `needRag=true` 时调用 `milvus /search`
- 返回结果参与回复文本生成并回发 WhatsApp
- 门户登录依赖 `portalState=ready`；失效态（`qr_required/auth_failure/disconnected`）会返回“请重新登录”

## 6. 运行与验证（常用）
### 6.1 启动 milvus/RAG
```powershell
cd D:\code\programs\Whatsapp\milvus
docker compose up -d
conda run -n milvus uvicorn scripts.serve_rag_api:app --host 0.0.0.0 --port 18080
```

### 6.2 启动 whatsapp-web
```powershell
cd D:\code\programs\Whatsapp\whatsapp-web
conda run -n whatsapp-web node example.js
```

### 6.3 门户验证（新增）
```powershell
Invoke-WebRequest -Uri http://127.0.0.1:3000/api/account/status -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:3000/api/account/login -Method POST -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:3000/api/account/switch-account -Method POST -UseBasicParsing
```

### 6.4 消息链路验证
```powershell
conda run -n whatsapp-web node tools/mock-incoming-8617628627274.js `
  --api-url http://127.0.0.1:3000/webhook/whatsapp-workflow `
  --body "我想了解心脏移植DRG费用区间"
```

预期关键字段：
- `ai.triage.needRag = true`
- `ai.rag.searched = true`
- `ai.rag.resultsCount > 0`
- `delivery.sent = true/false`

## 7. 当前状态与边界
- RAG 当前是关键词检索（BM25），不是语义向量检索。
- 门户登录依赖本机可用浏览器会话（Puppeteer + WhatsApp Web）。
- 更换账号会清理 `.wwebjs_auth` 与 `.wwebjs_cache`，会触发重新扫码登录。
- 生产化仍需补强：关键词归一化、术语同义词、审计日志、异常重试。

## 8. 建议的后续优化
1. 增加门户操作审计日志（谁在何时执行了 switch-account / login）。
2. 增加账号状态健康探针与告警（长期停留在 `initializing` / `qr_required`）。
3. 给 RAG 结果增加置信度阈值与同义词扩展。
4. 固化端到端回归脚本（门户 + webhook + RAG 一键联测）。
