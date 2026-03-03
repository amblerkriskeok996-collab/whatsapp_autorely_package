from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pymilvus import Collection, connections
from pymilvus.model.sparse import BM25EmbeddingFunction
from pymilvus.model.sparse.bm25.tokenizers import build_default_analyzer
from scipy.sparse import csr_matrix

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.drg_pipeline import sparse_row_to_dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keyword search DRG records from Milvus")
    parser.add_argument("--keyword", required=True, help="Keyword text")
    parser.add_argument("--top-k", type=int, default=10, help="How many results to return")
    parser.add_argument("--collection", default="drg_costs", help="Milvus collection name")
    parser.add_argument("--host", default="127.0.0.1", help="Milvus host")
    parser.add_argument("--port", default="19530", help="Milvus port")
    parser.add_argument(
        "--bm25-model-path",
        type=Path,
        default=Path("artifacts/bm25_model.json"),
        help="Path to BM25 model file",
    )
    return parser.parse_args()


def load_bm25(model_path: Path) -> BM25EmbeddingFunction:
    if not model_path.exists():
        raise FileNotFoundError(
            f"BM25 model not found at {model_path}. Run scripts/ingest_drg_to_milvus.py first."
        )
    analyzer = build_default_analyzer(language="zh")
    bm25 = BM25EmbeddingFunction(analyzer=analyzer)
    bm25.load(str(model_path))
    return bm25


def main() -> None:
    args = parse_args()
    bm25 = load_bm25(args.bm25_model_path)
    query_vector = csr_matrix(bm25.encode_queries([args.keyword]))
    query_row = sparse_row_to_dict(query_vector.getrow(0))

    connections.connect(alias="default", host=args.host, port=args.port)
    collection = Collection(args.collection)
    collection.load()

    results = collection.search(
        data=[query_row],
        anns_field="sparse_vector",
        param={"metric_type": "IP"},
        limit=args.top_k,
        output_fields=["drg_name", "start_cost", "cap_cost"],
    )

    output = []
    for rank, hit in enumerate(results[0], start=1):
        output.append(
            {
                "rank": rank,
                "score": float(hit.distance),
                "drg_name": hit.entity.get("drg_name"),
                "start_cost_cny": hit.entity.get("start_cost"),
                "cap_cost_cny": hit.entity.get("cap_cost"),
            }
        )

    if not output:
        escaped_keyword = args.keyword.replace("\\", "\\\\").replace('"', '\\"')
        fallback = collection.query(
            expr=f'drg_name like "%{escaped_keyword}%"',
            limit=args.top_k,
            output_fields=["drg_name", "start_cost", "cap_cost"],
        )
        output = [
            {
                "rank": idx,
                "score": 0.0,
                "drg_name": item.get("drg_name"),
                "start_cost_cny": item.get("start_cost"),
                "cap_cost_cny": item.get("cap_cost"),
            }
            for idx, item in enumerate(fallback, start=1)
        ]

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
