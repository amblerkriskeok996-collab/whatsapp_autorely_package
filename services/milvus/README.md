# DRG Milvus Keyword RAG

This project deploys a local Milvus instance and ingests data from:

`D:\code\programs\Whatsapp\milvus\修改版费用(1).xlsx`

It uses:
- key/label: `DRG名称`
- value fields: `预计起步费用（单位：人民币）`, `预计封顶费用（单位：人民币）`

The search mode is keyword retrieval (BM25 sparse vector) and returns top-10 most relevant records.

## 1) Start Milvus (local ports)

```powershell
docker compose up -d
```

Ports:
- Milvus gRPC: `19530`
- Milvus HTTP health: `9091`
- MinIO: `9000` (console `9001`)

## 2) Install Python dependencies

```powershell
conda run -n milvus python -m pip install -r requirements.txt
```

## 3) Ingest Excel data

```powershell
conda run -n milvus python scripts/ingest_drg_to_milvus.py --excel-path "修改版费用(1).xlsx"
```

Artifacts:
- BM25 model: `artifacts/bm25_model.json`
- metadata: `artifacts/bm25_model.meta.json`

## 4) Query top-10 by keyword

```powershell
conda run -n milvus python scripts/query_drg_keyword.py --keyword "阑尾炎" --top-k 10
```

## 4.1) Direct BM25 model query (without Milvus search)

Train local BM25 artifacts:

```powershell
conda run -n milvus python scripts/train_bm25_local.py --excel-path "修改版费用(1).xlsx"
```

Query directly from local BM25 model:

```powershell
conda run -n milvus python scripts/query_bm25_local.py --keyword "心脏" --top-k 10
```

## 5) Optional RAG API

```powershell
conda run -n milvus uvicorn scripts.serve_rag_api:app --host 0.0.0.0 --port 18080
```

Then call:

`GET http://127.0.0.1:18080/search?keyword=阑尾炎&top_k=10`
