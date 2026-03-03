from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.drg_pipeline import build_bm25_embeddings, load_records_from_excel, sparse_matrix_to_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest DRG Excel data into Milvus")
    parser.add_argument(
        "--excel-path",
        type=Path,
        default=Path("修改版费用(1).xlsx"),
        help="Path to the source Excel file",
    )
    parser.add_argument("--collection", default="drg_costs", help="Milvus collection name")
    parser.add_argument("--host", default="127.0.0.1", help="Milvus host")
    parser.add_argument("--port", default="19530", help="Milvus port")
    parser.add_argument(
        "--bm25-model-path",
        type=Path,
        default=Path("artifacts/bm25_model.json"),
        help="Path to save BM25 model metadata",
    )
    return parser.parse_args()


def create_collection(collection_name: str) -> Collection:
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="drg_name", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="start_cost", dtype=DataType.DOUBLE, nullable=True),
        FieldSchema(name="cap_cost", dtype=DataType.DOUBLE, nullable=True),
        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
    ]
    schema = CollectionSchema(fields=fields, description="DRG cost keyword retrieval collection")
    collection = Collection(name=collection_name, schema=schema)
    collection.create_index(
        field_name="sparse_vector",
        index_params={"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"},
    )
    return collection


def main() -> None:
    args = parse_args()
    if not args.excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {args.excel_path}")

    records = load_records_from_excel(args.excel_path)
    if not records:
        raise ValueError("No records found after cleaning; please check source Excel data.")

    drg_names = [record["drg_name"] for record in records]
    start_costs = [record["start_cost"] for record in records]
    cap_costs = [record["cap_cost"] for record in records]

    bm25, sparse_vectors = build_bm25_embeddings(drg_names)

    args.bm25_model_path.parent.mkdir(parents=True, exist_ok=True)
    bm25.save(str(args.bm25_model_path))

    connections.connect(alias="default", host=args.host, port=args.port)
    collection = create_collection(args.collection)

    sparse_rows = sparse_matrix_to_rows(sparse_vectors)
    collection.insert([drg_names, start_costs, cap_costs, sparse_rows])
    collection.flush()
    collection.load()

    meta_path = args.bm25_model_path.with_suffix(".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "collection": args.collection,
                "host": args.host,
                "port": args.port,
                "record_count": len(records),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Inserted {len(records)} records into collection '{args.collection}'.")
    print(f"Saved BM25 model to: {args.bm25_model_path}")
    print(f"Saved metadata to: {meta_path}")


if __name__ == "__main__":
    main()
