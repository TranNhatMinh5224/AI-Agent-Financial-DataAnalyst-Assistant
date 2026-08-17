"""
golden.py — Manage Golden Datasets for Evaluation.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GoldenQuestion:
    query_id: str
    question: str
    difficulty_level: str
    expected_answer: Optional[float]
    expected_unit: Optional[str]

@dataclass
class GoldenCell:
    query_id: str
    table_id: str
    row_label: str
    column_label: str
    raw_value: str

def load_golden_questions(eval_root: Path) -> List[GoldenQuestion]:
    """Load golden_questions.csv"""
    path = eval_root / "golden_questions.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, encoding="utf-8-sig")
    res = []
    for _, row in df.iterrows():
        res.append(GoldenQuestion(
            query_id=str(row.get("query_id", "")),
            question=str(row.get("question", "")),
            difficulty_level=str(row.get("difficulty_level", "easy")),
            expected_answer=float(row["expected_answer"]) if pd.notna(row.get("expected_answer")) else None,
            expected_unit=str(row.get("expected_unit", "")) if pd.notna(row.get("expected_unit")) else None,
        ))
    return res

def load_golden_cells(eval_root: Path) -> List[GoldenCell]:
    """Load golden_cells.csv"""
    path = eval_root / "golden_cells.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, encoding="utf-8-sig")
    res = []
    for _, row in df.iterrows():
        res.append(GoldenCell(
            query_id=str(row.get("query_id", "")),
            table_id=str(row.get("table_id", "")),
            row_label=str(row.get("row_label", "")),
            column_label=str(row.get("column_label", "")),
            raw_value=str(row.get("raw_value", "")),
        ))
    return res
