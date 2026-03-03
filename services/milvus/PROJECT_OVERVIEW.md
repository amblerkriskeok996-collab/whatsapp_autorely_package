# 项目总览（给 AI 快速理解）

## 1. 项目目标
本项目用于构建一个可本地运行的 DRG 费用检索系统，供 RAG 场景调用。

核心目标：
- 从 Excel 中读取 DRG 数据。
- 以 `DRG名称` 作为检索标签（文本主键）。
- 返回两个费用字段：
  - `预计起步费用（单位：人民币）`
  - `预计封顶费用（单位：人民币）`
- 支持关键词检索，返回最相关前 10 条。

## 2. 数据来源与字段映射
数据源文件：
- `修改版费用(1).xlsx`

清洗与映射逻辑：
- 输入列（必需）：
  - `DRG名称`
  - `预计起步费用（单位：人民币）`
  - `预计封顶费用（单位：人民币）`
- 输出记录结构：
  - `drg_name: str`
  - `start_cost: float | None`
  - `cap_cost: float | None`
- 费用列会做标准化（去掉货币符号、空白、分隔符，无法解析则置为 `None`）。

对应实现：
- `src/drg_pipeline.py` 的 `load_records_from_excel`、`normalize_cost`

## 3. 两条检索链路
项目提供两种可用检索路径，底层都用 BM25 稀疏表示。

### A) Milvus 检索链路（在线检索）
流程：
1. 用 BM25 对 `drg_name` 训练并编码文档稀疏向量。
2. 将数据写入 Milvus 集合 `drg_costs`。
3. 在 `sparse_vector` 上建立 `SPARSE_INVERTED_INDEX`（IP 度量）。
4. 查询时将关键词编码为稀疏向量，Milvus 返回 Top-K。
5. 若无结果，回退到 `drg_name like` 字符串匹配。

入口脚本：
- 训练+入库：`scripts/ingest_drg_to_milvus.py`
- 命令行查询：`scripts/query_drg_keyword.py`
- HTTP API：`scripts/serve_rag_api.py`

### B) 本地 BM25 直连链路（不依赖 Milvus 查询）
流程：
1. 训练 BM25 并持久化：
   - `bm25_model.json`
   - `doc_vectors.npz`
   - `records.json`
2. 查询时：
   - 将关键词编码为查询向量
   - 与文档向量做稀疏矩阵乘法得到分数
   - 排序取 Top-K
3. 若分数都为 0，回退到 `drg_name` 子串匹配。

入口脚本：
- 本地训练：`scripts/train_bm25_local.py`
- 本地查询：`scripts/query_bm25_local.py`

## 4. 系统组件与关键文件
- 部署：
  - `docker-compose.yml`
  - 提供 `milvus + etcd + minio`，Milvus 端口 `19530`、健康检查 `9091`
- 核心逻辑：
  - `src/drg_pipeline.py`
- Milvus 管道：
  - `scripts/ingest_drg_to_milvus.py`
  - `scripts/query_drg_keyword.py`
  - `scripts/serve_rag_api.py`
- 本地 BM25 管道：
  - `scripts/train_bm25_local.py`
  - `scripts/query_bm25_local.py`
- 测试：
  - `tests/test_drg_pipeline.py`

## 5. 运行方式（最常用命令）
依赖安装：
```powershell
conda run -n milvus python -m pip install -r requirements.txt
```

启动 Milvus：
```powershell
docker compose up -d
```

Milvus 路径导入：
```powershell
conda run -n milvus python scripts/ingest_drg_to_milvus.py --excel-path "修改版费用(1).xlsx"
```

Milvus 查询：
```powershell
conda run -n milvus python scripts/query_drg_keyword.py --keyword "心脏" --top-k 10
```

本地 BM25 训练：
```powershell
conda run -n milvus python scripts/train_bm25_local.py --excel-path "修改版费用(1).xlsx"
```

本地 BM25 查询：
```powershell
conda run -n milvus python scripts/query_bm25_local.py --keyword "心脏" --top-k 10
```

API 服务：
```powershell
conda run -n milvus uvicorn scripts.serve_rag_api:app --host 0.0.0.0 --port 18080
```

## 6. RAG 调用契约（建议）
推荐调用 API：
- `GET /search?keyword=<关键词>&top_k=<1..50>`

响应结构：
```json
{
  "keyword": "心脏",
  "top_k": 10,
  "items": [
    {
      "rank": 1,
      "score": 6.21,
      "drg_name": "心脏移植",
      "start_cost_cny": 421677.27,
      "cap_cost_cny": 632515.91
    }
  ]
}
```

## 7. 当前实现边界
- 检索是“关键词/BM25”，不是语义向量检索。
- 关键词与文档无词项重叠时，BM25 可能返回空，系统已加字符串匹配回退。
- 中文分词依赖 BM25 分词器（含中文 analyzer）；同义词、医学术语归一化未单独建模。

## 8. 给 AI Agent 的建议入口
如果你是接入型 AI（需要稳定调用）：
1. 首选 `scripts/serve_rag_api.py` 的 `/search`。
2. 若不希望依赖 Milvus 在线检索，改用 `query_bm25_local.py` 直接查本地模型。
3. 若 Excel 更新，先重新执行训练/导入，再对外提供检索。

