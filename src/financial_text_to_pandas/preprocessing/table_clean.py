"""
table_clean.py — HTML table grid cleaning, header detection, context propagation.

Phase 1, Steps 5–9.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup, Tag

from financial_text_to_pandas.preprocessing.number_parser import parse_vn_number
from financial_text_to_pandas.types import (
    CleanTable,
    HeaderDetection,
    TableMetadata,
)

# ── Vietnamese financial header keywords ─────────────────────────────────────
_HEADER_KEYWORDS = {
    "chỉ tiêu", "chi tieu", "mã số", "ma so", "thuyết minh", "thuyet minh",
    "năm", "nam", "tháng", "thang", "ngày", "ngay", "đơn vị", "don vi",
    "số tiền", "so tien", "giá trị", "gia tri", "nội dung", "noi dung",
    "khoản mục", "khoan muc", "tài khoản", "tai khoan",
    "31/12", "01/01", "đầu năm", "cuối năm",
}

_UNIT_KEYWORDS = {
    "triệu đồng": "triệu đồng",
    "tỷ đồng": "tỷ đồng",
    "đồng": "đồng",
    "vnđ": "VNĐ",
    "vnd": "VNĐ",
    "usd": "USD",
    "%": "%",
}

_STATEMENT_KEYWORDS = {
    "bảng cân đối": "balance_sheet",
    "bang can doi": "balance_sheet",
    "cân đối kế toán": "balance_sheet",
    "kết quả hoạt động kinh doanh": "income_statement",
    "ket qua hoat dong": "income_statement",
    "lưu chuyển tiền": "cash_flow",
    "luu chuyen tien": "cash_flow",
    "thuyết minh": "notes",
    "thuyet minh": "notes",
    "vốn chủ sở hữu": "equity_statement",
    "von chu so huu": "equity_statement",
}


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Rowspan / Colspan expansion
# ─────────────────────────────────────────────────────────────────────────────

def expand_rowspan_colspan(table_tag: Tag) -> List[List[str]]:
    """Expand a <table> Tag into a rectangular grid, handling rowspan and colspan.

    Args:
        table_tag: A BeautifulSoup Tag for the <table> element.

    Returns:
        2-D list of strings (rows × columns). Empty cells are "".
    """
    # Pre-pass: determine grid dimensions
    rows_tags = table_tag.find_all("tr")
    if not rows_tags:
        return []

    # We use a span map: span_map[(row, col)] = True means cell is occupied
    span_map: dict[Tuple[int, int], str] = {}
    max_col = 0

    for ri, tr in enumerate(rows_tags):
        cells = tr.find_all(["td", "th"])
        ci = 0
        for cell in cells:
            # Advance past occupied cells
            while (ri, ci) in span_map:
                ci += 1

            text = _cell_text(cell)
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))

            for r_offset in range(rowspan):
                for c_offset in range(colspan):
                    span_map[(ri + r_offset, ci + c_offset)] = text

            ci += colspan
            if ci > max_col:
                max_col = ci

    if not span_map:
        return []

    n_rows = max(r for r, _ in span_map) + 1
    n_cols = max(c for _, c in span_map) + 1

    grid: List[List[str]] = []
    for ri in range(n_rows):
        row = [span_map.get((ri, ci), "") for ci in range(n_cols)]
        grid.append(row)

    return grid


def align_grid(rows: List[List[str]]) -> List[List[str]]:
    """Make all rows the same width by padding shorter rows with empty strings."""
    if not rows:
        return rows
    max_width = max(len(r) for r in rows)
    return [r + [""] * (max_width - len(r)) for r in rows]


def drop_empty_rows_and_columns(rows: List[List[str]]) -> List[List[str]]:
    """Remove rows and columns where every cell is empty."""
    if not rows:
        return rows

    # Drop empty rows
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return rows

    # Drop empty columns
    n_cols = len(rows[0])
    non_empty_cols = [
        ci for ci in range(n_cols) if any(rows[ri][ci].strip() for ri in range(len(rows)))
    ]
    rows = [[row[ci] for ci in non_empty_cols] for row in rows]
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Header detection and flattening
# ─────────────────────────────────────────────────────────────────────────────

def detect_header_rows(grid: List[List[str]]) -> HeaderDetection:
    """Detect which rows are header rows using keyword scoring.

    Args:
        grid: 2-D list of strings (clean, no empty rows/cols).

    Returns:
        HeaderDetection with header_rows, confidence, and method.
    """
    if not grid:
        return HeaderDetection(header_rows=[], confidence=0.0, method="empty")

    scores = []
    for row in grid:
        score = _score_header_row(row)
        scores.append(score)

    # Greedily collect consecutive rows from top while score is significant
    header_rows: List[int] = []
    for i, score in enumerate(scores):
        if score >= 0.3:
            header_rows.append(i)
        else:
            break  # Stop at first non-header row

    if not header_rows:
        # Fallback: treat row 0 as header
        return HeaderDetection(header_rows=[0], confidence=0.5, method="fallback")

    confidence = min(1.0, sum(scores[i] for i in header_rows) / len(header_rows))
    return HeaderDetection(header_rows=header_rows, confidence=confidence, method="keyword_score")


def _score_header_row(row: List[str]) -> float:
    """Score a row on how likely it is to be a header row (0.0–1.0)."""
    if not row:
        return 0.0
    row_text = " ".join(row).lower()
    # Check for financial header keywords
    keyword_hits = sum(1 for kw in _HEADER_KEYWORDS if kw in row_text)
    # Check for year-like patterns (4-digit numbers between 2000–2030)
    year_hits = len(re.findall(r"\b20[0-2]\d\b", row_text))
    # Check how many cells are non-numeric (headers are mostly text)
    numeric_ratio = sum(1 for c in row if _is_numeric_cell(c)) / max(len(row), 1)
    # Empty cell ratio (headers often have empty leader cells)
    empty_ratio = sum(1 for c in row if not c.strip()) / max(len(row), 1)

    score = 0.0
    score += min(keyword_hits * 0.3, 0.6)
    score += min(year_hits * 0.25, 0.5)
    score += (1.0 - numeric_ratio) * 0.2
    score += empty_ratio * 0.1
    return min(score, 1.0)


def flatten_headers(grid: List[List[str]], header_rows: List[int]) -> List[str]:
    """Flatten multi-row headers into single column names.

    Args:
        grid: Full 2-D grid.
        header_rows: 0-indexed row indices that are headers.

    Returns:
        List of column name strings.
    """
    if not header_rows or not grid:
        n_cols = len(grid[0]) if grid else 0
        return [f"col_{i}" for i in range(n_cols)]

    n_cols = len(grid[0])
    col_parts: List[List[str]] = [[] for _ in range(n_cols)]

    for ri in header_rows:
        if ri >= len(grid):
            continue
        for ci, cell in enumerate(grid[ri]):
            cell_stripped = cell.strip()
            if cell_stripped:
                col_parts[ci].append(cell_stripped)

    # Build column names
    col_names: List[str] = []
    seen: dict[str, int] = {}
    for ci, parts in enumerate(col_parts):
        name = "_".join(parts) if parts else f"col_{ci}"
        # Clean whitespace
        name = re.sub(r"\s+", " ", name).strip()
        # Deduplicate
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        col_names.append(name)

    return col_names


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Financial group context propagation
# ─────────────────────────────────────────────────────────────────────────────

def propagate_group_context(df: pd.DataFrame) -> pd.DataFrame:
    """Add row_label_full by propagating section group labels to child rows.

    A 'section row' is a row where row_label_raw has text but all numeric columns are empty.
    Child rows beneath a section row inherit the section label in row_label_full.

    Args:
        df: DataFrame with at least a 'row_label_raw' column.

    Returns:
        DataFrame with 'row_label_full' column added.
    """
    if "row_label_raw" not in df.columns:
        df["row_label_full"] = ""
        return df

    labels_full: List[str] = []
    current_group: List[str] = []

    # Identify numeric columns (those starting with numeric__)
    numeric_cols = [c for c in df.columns if c.startswith("numeric__")]

    for _, row in df.iterrows():
        raw_label = str(row.get("row_label_raw", "")).strip()

        # A section row: has label but all numeric values are NaN/empty
        is_section = raw_label and _is_section_row(row, numeric_cols)

        if is_section:
            # Start a new group or push onto group stack
            current_group = [raw_label]
            labels_full.append(raw_label)
        elif raw_label:
            full = " > ".join(current_group + [raw_label]) if current_group else raw_label
            labels_full.append(full)
        else:
            labels_full.append("")

    df = df.copy()
    df["row_label_full"] = labels_full
    return df


def _is_section_row(row: pd.Series, numeric_cols: List[str]) -> bool:
    """Return True if the row appears to be a section header (no numeric data)."""
    if not numeric_cols:
        return False
    for col in numeric_cols:
        val = row.get(col)
        if pd.notna(val) and val != "":
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Steps 8–9 — Build clean table DataFrame
# ─────────────────────────────────────────────────────────────────────────────

def clean_table(grid: List[List[str]], metadata: TableMetadata) -> CleanTable:
    """Convert a cleaned grid into a CleanTable with parsed numeric columns.

    Args:
        grid: 2-D list (already expanded rowspan/colspan, aligned, empty-dropped).
        metadata: TableMetadata used for table_id and csv_path.

    Returns:
        CleanTable dataclass.
    """
    from pathlib import Path

    if not grid or len(grid) < 2:
        # Not enough rows to have data
        df = pd.DataFrame()
        return CleanTable(
            table_id=metadata.table_id,
            dataframe=df,
            csv_path=Path(metadata.csv_path),
            row_count=0,
            column_count=0,
            numeric_cell_count=0,
            quality_score=0.0,
            needs_review=True,
            review_reason="too_few_rows",
        )

    # ── Detect and flatten headers ──────────────────────────────────────────
    header_det = detect_header_rows(grid)
    col_names = flatten_headers(grid, header_det.header_rows)

    # Data rows start after the last header row
    data_start = (max(header_det.header_rows) + 1) if header_det.header_rows else 1
    data_rows = grid[data_start:]

    if not data_rows:
        df = pd.DataFrame(columns=col_names)
        return CleanTable(
            table_id=metadata.table_id,
            dataframe=df,
            csv_path=Path(metadata.csv_path),
            row_count=0,
            column_count=len(col_names),
            numeric_cell_count=0,
            quality_score=0.0,
            needs_review=True,
            review_reason="no_data_rows",
        )

    # Ensure all rows match number of columns
    n_cols = len(col_names)
    data_rows = [r + [""] * max(0, n_cols - len(r)) for r in data_rows]
    data_rows = [r[:n_cols] for r in data_rows]

    df = pd.DataFrame(data_rows, columns=col_names)

    # ── row_label_raw — use the first column as the label column ─────────────
    first_col = col_names[0] if col_names else None
    if first_col:
        df["row_label_raw"] = df[first_col].astype(str).str.strip()
    else:
        df["row_label_raw"] = ""

    # ── numeric__ columns — parse every data column ───────────────────────────
    data_cols = col_names[1:] if len(col_names) > 1 else []
    numeric_cell_count = 0

    for col in data_cols:
        numeric_col = f"numeric__{col}"
        parsed_values = []
        for raw in df[col]:
            pn = parse_vn_number(str(raw))
            parsed_values.append(pn.parsed_value)
            if pn.parse_status == "ok":
                numeric_cell_count += 1
        df[numeric_col] = parsed_values

    # ── Propagate group context → row_label_full ─────────────────────────────
    df = propagate_group_context(df)

    # ── Reorder columns for readability ──────────────────────────────────────
    # Put label columns first, then original data cols, then numeric__ cols
    label_cols = ["row_label_raw", "row_label_full"]
    numeric_cols = [c for c in df.columns if c.startswith("numeric__")]
    other_cols = [c for c in df.columns if c not in label_cols and c not in numeric_cols]
    ordered = label_cols + other_cols + numeric_cols
    ordered = [c for c in ordered if c in df.columns]
    df = df[ordered]

    # ── Quality scoring ───────────────────────────────────────────────────────
    total_cells = len(df) * max(len(data_cols), 1)
    quality_score = round(numeric_cell_count / max(total_cells, 1), 3)

    needs_review = False
    review_reason = ""
    if quality_score < 0.1:
        needs_review = True
        review_reason = "low_numeric_density"
    elif len(df) < 2:
        needs_review = True
        review_reason = "too_few_rows"

    return CleanTable(
        table_id=metadata.table_id,
        dataframe=df,
        csv_path=Path(metadata.csv_path),
        row_count=len(df),
        column_count=len(df.columns),
        numeric_cell_count=numeric_cell_count,
        quality_score=quality_score,
        needs_review=needs_review,
        review_reason=review_reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cell_text(cell: Tag) -> str:
    """Extract normalized text from a <td> or <th> tag."""
    text = cell.get_text(separator=" ")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_numeric_cell(value: str) -> bool:
    """Quick check: does this cell contain a numeric-looking value?"""
    v = value.strip()
    if not v or v in {"-", "–", "—"}:
        return False
    pn = parse_vn_number(v)
    return pn.parse_status == "ok"


def infer_statement_type(nearby_before: str, nearby_after: str, col_names: List[str]) -> str:
    """Infer the financial statement type from nearby text and column names."""
    combined = (nearby_before + " " + nearby_after + " " + " ".join(col_names)).lower()
    for keyword, stype in _STATEMENT_KEYWORDS.items():
        if keyword in combined:
            return stype
    return "unknown"


def infer_unit(nearby_before: str, nearby_after: str) -> str:
    """Infer the unit from nearby text."""
    combined = (nearby_before + " " + nearby_after).lower()
    for keyword, unit in _UNIT_KEYWORDS.items():
        if keyword in combined:
            return unit
    return "unknown"
