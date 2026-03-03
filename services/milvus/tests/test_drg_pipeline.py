from pathlib import Path

import pandas as pd
import pytest

from src.drg_pipeline import (
    CAP_COST_COLUMN,
    DRG_NAME_COLUMN,
    START_COST_COLUMN,
    build_bm25_embeddings,
    compute_bm25_scores,
    load_records_from_excel,
    normalize_cost,
    sparse_matrix_to_rows,
    top_k_score_indices,
)


def test_normalize_cost_parses_currency_text() -> None:
    assert normalize_cost("1,234.50") == 1234.5
    assert normalize_cost("￥2,000 元") == 2000.0
    assert normalize_cost("人民币300") == 300.0
    assert normalize_cost("--") is None
    assert normalize_cost(None) is None


def test_load_records_from_excel_extracts_required_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "input.xlsx"
    df = pd.DataFrame(
        {
            DRG_NAME_COLUMN: ["急性阑尾炎", "  ", None, "慢性胃炎"],
            START_COST_COLUMN: ["1000", "2000", "3000", "4,000"],
            CAP_COST_COLUMN: ["5000", "6000", None, "8,000"],
            "other_column": [1, 2, 3, 4],
        }
    )
    df.to_excel(file_path, index=False)

    records = load_records_from_excel(file_path)
    assert len(records) == 2
    assert records[0]["drg_name"] == "急性阑尾炎"
    assert records[0]["start_cost"] == 1000.0
    assert records[0]["cap_cost"] == 5000.0
    assert records[1]["drg_name"] == "慢性胃炎"
    assert records[1]["start_cost"] == 4000.0
    assert records[1]["cap_cost"] == 8000.0


def test_load_records_from_excel_raises_when_missing_columns(tmp_path: Path) -> None:
    file_path = tmp_path / "input.xlsx"
    pd.DataFrame({"A": [1], "B": [2]}).to_excel(file_path, index=False)
    with pytest.raises(ValueError):
        load_records_from_excel(file_path)


def test_build_bm25_embeddings_returns_sparse_matrix() -> None:
    bm25, vectors = build_bm25_embeddings(["acute appendicitis", "chronic gastritis"])
    assert vectors.shape[0] == 2
    query = bm25.encode_queries(["appendicitis"])
    assert query.shape[0] == 1


def test_sparse_matrix_to_rows_returns_dicts() -> None:
    _, vectors = build_bm25_embeddings(["acute appendicitis", "chronic gastritis"])
    rows = sparse_matrix_to_rows(vectors)
    assert len(rows) == 2
    assert isinstance(rows[0], dict)


def test_compute_bm25_scores_and_topk() -> None:
    bm25, vectors = build_bm25_embeddings(["heart transplant", "chronic gastritis", "appendectomy"])
    query = bm25.encode_queries(["heart"])
    scores = compute_bm25_scores(vectors, query)
    assert len(scores) == 3
    top_idx = top_k_score_indices(scores, 2)
    assert top_idx[0] == 0
