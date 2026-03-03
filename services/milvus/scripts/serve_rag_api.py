from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException, Query
from pymilvus import Collection, connections
from pymilvus.model.sparse import BM25EmbeddingFunction
from pymilvus.model.sparse.bm25.tokenizers import build_default_analyzer
from scipy.sparse import csr_matrix

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.drg_pipeline import sparse_row_to_dict

DEFAULT_COLLECTION = "drg_costs"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "19530"
DEFAULT_BM25_PATH = Path("artifacts/bm25_model.json")

app = FastAPI(title="DRG Milvus RAG API", version="1.0.0")

_bm25: BM25EmbeddingFunction | None = None
_collection: Collection | None = None


def _init_once() -> None:
    global _bm25, _collection
    if _bm25 is not None and _collection is not None:
        return
    if not DEFAULT_BM25_PATH.exists():
        raise RuntimeError(f"BM25 model not found: {DEFAULT_BM25_PATH}")

    analyzer = build_default_analyzer(language="zh")
    _bm25 = BM25EmbeddingFunction(analyzer=analyzer)
    _bm25.load(str(DEFAULT_BM25_PATH))

    connections.connect(alias="default", host=DEFAULT_HOST, port=DEFAULT_PORT)
    _collection = Collection(DEFAULT_COLLECTION)
    _collection.load()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/search")
def search(keyword: str = Query(..., min_length=1), top_k: int = Query(10, ge=1, le=50)) -> dict:
    try:
        _init_once()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    assert _bm25 is not None
    assert _collection is not None
    query_vector = csr_matrix(_bm25.encode_queries([keyword]))
    query_row = sparse_row_to_dict(query_vector.getrow(0))
    results = _collection.search(
        data=[query_row],
        anns_field="sparse_vector",
        param={"metric_type": "IP"},
        limit=top_k,
        output_fields=["drg_name", "start_cost", "cap_cost"],
    )

    items = []
    for rank, hit in enumerate(results[0], start=1):
        items.append(
            {
                "rank": rank,
                "score": float(hit.distance),
                "drg_name": hit.entity.get("drg_name"),
                "start_cost_cny": hit.entity.get("start_cost"),
                "cap_cost_cny": hit.entity.get("cap_cost"),
            }
        )

    if not items:
        escaped_keyword = keyword.replace("\\", "\\\\").replace('"', '\\"')
        fallback = _collection.query(
            expr=f'drg_name like "%{escaped_keyword}%"',
            limit=top_k,
            output_fields=["drg_name", "start_cost", "cap_cost"],
        )
        items = [
            {
                "rank": idx,
                "score": 0.0,
                "drg_name": item.get("drg_name"),
                "start_cost_cny": item.get("start_cost"),
                "cap_cost_cny": item.get("cap_cost"),
            }
            for idx, item in enumerate(fallback, start=1)
        ]
    return {"keyword": keyword, "top_k": top_k, "items": items}
