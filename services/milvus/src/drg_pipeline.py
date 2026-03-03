from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np

import pandas as pd
from pymilvus.model.sparse import BM25EmbeddingFunction
from pymilvus.model.sparse.bm25.tokenizers import build_default_analyzer
from scipy.sparse import csr_matrix

DRG_NAME_COLUMN = "DRG名称"
START_COST_COLUMN = "预计起步费用（单位：人民币）"
CAP_COST_COLUMN = "预计封顶费用（单位：人民币）"

REQUIRED_COLUMNS = [DRG_NAME_COLUMN, START_COST_COLUMN, CAP_COST_COLUMN]

_COST_CLEAN_RE = re.compile(r"[,\s￥¥元]")


def normalize_cost(value: object) -> Optional[float]:
    """Parse cost cells that may contain currency symbols or separators."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("人民币", "")
    text = _COST_CLEAN_RE.sub("", text)
    if text in {"-", "--", "/", "N/A", "n/a", "nan", "None"}:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def load_records_from_excel(excel_path: Path) -> list[dict]:
    """Load and clean DRG records from the provided Excel file."""
    df = pd.read_excel(excel_path, engine="openpyxl")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df = df[REQUIRED_COLUMNS].copy()
    df = df.dropna(subset=[DRG_NAME_COLUMN])
    df[DRG_NAME_COLUMN] = df[DRG_NAME_COLUMN].astype(str).str.strip()
    df = df[(df[DRG_NAME_COLUMN] != "") & (df[DRG_NAME_COLUMN].str.lower() != "nan")]

    df[START_COST_COLUMN] = df[START_COST_COLUMN].map(normalize_cost)
    df[CAP_COST_COLUMN] = df[CAP_COST_COLUMN].map(normalize_cost)

    records: list[dict] = []
    for _, row in df.iterrows():
        start_cost = row[START_COST_COLUMN]
        cap_cost = row[CAP_COST_COLUMN]
        if pd.isna(start_cost):
            start_cost = None
        if pd.isna(cap_cost):
            cap_cost = None
        records.append(
            {
                "drg_name": row[DRG_NAME_COLUMN],
                "start_cost": start_cost,
                "cap_cost": cap_cost,
            }
        )
    return records


def build_bm25_embeddings(texts: list[str]) -> tuple[BM25EmbeddingFunction, csr_matrix]:
    """Build a Chinese BM25 embedding function and encode document vectors."""
    analyzer = build_default_analyzer(language="zh")
    bm25 = BM25EmbeddingFunction(analyzer=analyzer)
    bm25.fit(texts)
    sparse_vectors = bm25.encode_documents(texts)
    return bm25, csr_matrix(sparse_vectors)


def sparse_row_to_dict(row: csr_matrix) -> dict[int, float]:
    """Convert one sparse row to Milvus sparse vector format."""
    row = csr_matrix(row)
    if row.shape[0] != 1:
        raise ValueError(f"Expected one sparse row, got shape={row.shape}")
    return {int(idx): float(val) for idx, val in zip(row.indices, row.data)}


def sparse_matrix_to_rows(matrix: csr_matrix) -> list[dict[int, float]]:
    """Convert a sparse matrix into a list of sparse dict rows."""
    matrix = csr_matrix(matrix)
    return [sparse_row_to_dict(matrix.getrow(i)) for i in range(matrix.shape[0])]


def compute_bm25_scores(doc_vectors: csr_matrix, query_vector: csr_matrix) -> np.ndarray:
    """Compute BM25 scores using sparse matrix multiplication."""
    doc_vectors = csr_matrix(doc_vectors)
    query_vector = csr_matrix(query_vector)
    if query_vector.shape[0] != 1:
        raise ValueError(f"Expected single query row, got shape={query_vector.shape}")
    return (doc_vectors @ query_vector.transpose()).toarray().ravel()


def top_k_score_indices(scores: np.ndarray, top_k: int) -> list[int]:
    """Return indices of top-k scores sorted descending."""
    if top_k <= 0:
        return []
    if scores.size == 0:
        return []
    top_k = min(top_k, scores.size)
    candidate = np.argpartition(-scores, top_k - 1)[:top_k]
    ordered = candidate[np.argsort(-scores[candidate])]
    return ordered.tolist()
