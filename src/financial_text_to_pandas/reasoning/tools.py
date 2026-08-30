"""
tools.py — Helper functions for the PoT Sandbox.

Phase 3, Step 4.
"""

from __future__ import annotations

import re
import pandas as pd
from typing import Optional, Dict
from rapidfuzz import fuzz

from financial_text_to_pandas.preprocessing.number_parser import parse_vn_number as preprocess_parse_vn_number


def parse_vn_number(raw_val: str) -> Optional[float]:
    """Parse a Vietnamese number string. Returns None nếu không parse được."""
    parsed = preprocess_parse_vn_number(str(raw_val))
    return parsed.parsed_value


def normalize_unit(val: float, from_unit: Optional[str], to_unit: Optional[str]) -> float:
    """Normalize a value between units (triệu đồng, tỷ đồng, etc.).
    
    BUG-015 FIX: Dùng safe division để tránh ZeroDivisionError khi to_mult = 0.
    """
    if not from_unit or not to_unit:
        return val

    from_u = from_unit.lower().replace("đồng", "").strip()
    to_u = to_unit.lower().replace("đồng", "").strip()

    multipliers = {
        "vnđ": 1,
        "vnd": 1,
        "nghìn": 10**3,
        "triệu": 10**6,
        "tỷ": 10**9,
        "tỉ": 10**9,
    }

    from_mult = multipliers.get(from_u, 1)
    to_mult = multipliers.get(to_u, 1)

    # Scale to base (VND) then divide by target unit
    base_val = val * from_mult
    if to_mult == 0:
        return base_val
    return base_val / to_mult


def _normalize_label(text: str) -> str:
    """Chuẩn hóa nhãn để fuzzy match: lower, xóa ghi chú thuyết minh, rút khoảng trắng."""
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Xóa ghi chú dạng (1), (V.1), (i)
    text = re.sub(r'\([ivxIVX\d\.]+\)', ' ', text)
    # Xóa ký tự đặc biệt
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def safe_get_cell(
    dfs: Dict[str, pd.DataFrame],
    table_id: str,
    row_label: str,
    col_label: str,
    fuzzy_threshold: int = 75,
) -> float:
    """Safely get and parse a cell from the dataframes.

    BUG-011 FIX: Thêm fuzzy matching cho row_label để chống OCR noise.
    Thứ tự ưu tiên: exact match → normalized exact match → fuzzy match.

    Args:
        dfs: Dictionary of loaded DataFrames.
        table_id: ID của bảng.
        row_label: Nhãn dòng cần tìm.
        col_label: Nhãn cột cần tìm.
        fuzzy_threshold: Ngưỡng fuzzy score tối thiểu (0–100).

    Returns:
        Giá trị số đã parse.

    Raises:
        ValueError: Nếu table, row, col không tìm thấy hoặc không parse được.
    """
    if table_id not in dfs:
        raise ValueError(f"Table '{table_id}' not found in evidence.")

    df = dfs[table_id]

    row_col = "row_label_full" if "row_label_full" in df.columns else "row_label_raw"
    if row_col not in df.columns:
        raise ValueError(f"Row label column not found in table '{table_id}'.")

    # ── Bước 1: Exact string match ─────────────────────────────────────────────
    matches = df[df[row_col] == row_label]

    # ── Bước 2: Normalized exact match ────────────────────────────────────────
    if matches.empty:
        row_label_norm = _normalize_label(row_label)
        for idx, lbl in df[row_col].items():
            if _normalize_label(str(lbl)) == row_label_norm:
                matches = df.loc[[idx]]
                break

    # ── Bước 3: Fuzzy match fallback ──────────────────────────────────────────
    if matches.empty:
        row_label_norm = _normalize_label(row_label)
        best_score = 0
        best_idx = None

        for idx, lbl in df[row_col].items():
            lbl_norm = _normalize_label(str(lbl))
            score = max(
                fuzz.partial_ratio(row_label_norm, lbl_norm),
                fuzz.token_sort_ratio(row_label_norm, lbl_norm),
            )
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is None or best_score < fuzzy_threshold:
            raise ValueError(
                f"Row '{row_label}' not found in table '{table_id}' "
                f"(best fuzzy score={best_score}, threshold={fuzzy_threshold})."
            )
        matches = df.loc[[best_idx]]

    # ── Lấy giá trị ô ─────────────────────────────────────────────────────────
    if col_label not in df.columns:
        raise ValueError(f"Column '{col_label}' not found in table '{table_id}'.")

    raw_val = matches.iloc[0][col_label]
    parsed = parse_vn_number(str(raw_val))

    if parsed is None:
        raise ValueError(
            f"Cell value '{raw_val}' (row='{row_label}', col='{col_label}') "
            f"could not be parsed as a number in table '{table_id}'."
        )

    return parsed
