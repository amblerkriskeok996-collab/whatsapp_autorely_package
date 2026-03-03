from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scipy.sparse import save_npz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.drg_pipeline import build_bm25_embeddings, load_records_from_excel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and persist local BM25 model for DRG data")
    parser.add_argument(
        "--excel-path",
        type=Path,
        default=Path("修改版费用(1).xlsx"),
        help="Path to source Excel file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/local_bm25"),
        help="Artifact output directory",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {args.excel_path}")

    records = load_records_from_excel(args.excel_path)
    if not records:
        raise ValueError("No records found after cleaning.")

    drg_names = [record["drg_name"] for record in records]
    bm25, doc_vectors = build_bm25_embeddings(drg_names)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "bm25_model.json"
    records_path = args.output_dir / "records.json"
    matrix_path = args.output_dir / "doc_vectors.npz"

    bm25.save(str(model_path))
    save_npz(matrix_path, doc_vectors)
    records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"trained_records={len(records)}")
    print(f"model={model_path}")
    print(f"records={records_path}")
    print(f"doc_vectors={matrix_path}")


if __name__ == "__main__":
    main()

