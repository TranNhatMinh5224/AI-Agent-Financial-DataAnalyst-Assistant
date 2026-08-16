"""
metadata.py — Infer report metadata and write metadata CSV files.

Phase 1, Steps 3, 12.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from financial_text_to_pandas.types import ReportMetadata, TableMetadata

# ── Report type keywords in directory names ───────────────────────────────────
_REPORT_TYPE_MAP = {
    "consolidated": "consolidated",
    "hop_nhat": "consolidated",
    "hopnhat": "consolidated",
    "separate": "separate",
    "rieng_le": "separate",
    "riengle": "separate",
    "explanation": "explanation",
    "giai_trinh": "explanation",
    "giai trinh": "explanation",
}

# Map ticker -> company name from ViFinQA code_stock.csv (lazy loaded)
_COMPANY_NAME_CACHE: dict[str, str] = {}


def infer_report_metadata(path: Path, dataset_root: Path) -> ReportMetadata:
    """Infer ReportMetadata from an OCR TXT file path.

    Expected path structure:
        {dataset_root}/{ticker}/{year}/{document_name}/{filename}.txt

    Args:
        path: Absolute or relative path to the OCR TXT file.
        dataset_root: Root of the financial_statements directory.

    Returns:
        ReportMetadata.

    Raises:
        ValueError: If the path doesn't match the expected structure.
    """
    # Resolve relative to cwd if not absolute
    if not path.is_absolute():
        path = Path.cwd() / path

    # Make path relative to dataset_root for segment parsing
    try:
        rel = path.relative_to(dataset_root.resolve())
    except ValueError:
        # Try resolving both
        rel = path.resolve().relative_to(dataset_root.resolve())

    parts = rel.parts
    # Expected: ticker / year / document_name / filename.txt
    if len(parts) < 4:
        raise ValueError(
            f"Expected path structure: ticker/year/document_name/file.txt, got: {rel}"
        )

    ticker = parts[0].upper()
    year_str = parts[1]
    document_name = parts[2]
    # filename is parts[3] (may have more nesting, take first 3 after root)

    try:
        year = int(year_str)
    except ValueError:
        raise ValueError(f"Cannot parse year from path segment: {year_str!r}")

    report_type = _infer_report_type(document_name)
    report_id = _build_report_id(ticker, year, report_type, document_name)
    source_txt_path = str(rel)

    try:
        file_size_bytes = path.stat().st_size
    except OSError:
        file_size_bytes = 0

    return ReportMetadata(
        report_id=report_id,
        ticker=ticker,
        year=year,
        report_type=report_type,
        document_name=document_name,
        source_txt_path=source_txt_path,
        file_size_bytes=file_size_bytes,
    )


def _infer_report_type(document_name: str) -> str:
    """Infer report_type from the document directory name."""
    dn_lower = document_name.lower().replace("-", "_")
    for keyword, rtype in _REPORT_TYPE_MAP.items():
        if keyword in dn_lower:
            return rtype
    return "unknown"


def _build_report_id(ticker: str, year: int, report_type: str, document_name: str) -> str:
    """Build a stable report_id."""
    return f"{ticker}_{year}_{report_type}"


def lookup_company_name(ticker: str, dataset_root: Path) -> str:
    """Look up company name from ViFinQA code_stock.csv.

    Falls back to ticker string if not found.
    """
    global _COMPANY_NAME_CACHE

    if ticker in _COMPANY_NAME_CACHE:
        return _COMPANY_NAME_CACHE[ticker]

    code_stock_path = dataset_root.parent / "code_stock.csv"
    if not code_stock_path.exists():
        return ticker

    try:
        with code_stock_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                t = (row.get("ticker") or row.get("code") or "").strip().upper()
                name = (row.get("company_name") or row.get("name") or "").strip()
                if t:
                    _COMPANY_NAME_CACHE[t] = name
    except Exception:
        pass

    return _COMPANY_NAME_CACHE.get(ticker, ticker)


# ─────────────────────────────────────────────────────────────────────────────
# CSV writers
# ─────────────────────────────────────────────────────────────────────────────

_TABLE_METADATA_COLUMNS = [
    "table_id", "csv_path", "ticker", "company_name", "year", "report_type",
    "statement_type", "unit", "source_txt_path", "page_number", "table_index",
    "title", "nearby_text_before", "nearby_text_after", "row_count",
    "column_count", "numeric_cell_count", "quality_score", "needs_review",
    "review_reason", "created_at",
]

_REPORT_METADATA_COLUMNS = [
    "report_id", "ticker", "year", "report_type", "document_name",
    "source_txt_path", "file_size_bytes",
]


def write_table_metadata(rows: List[TableMetadata], output_root: Path) -> None:
    """Append table metadata rows to table_metadata.csv.

    Creates or appends to the file, preserving stable column order.
    """
    output_path = output_root / "table_metadata.csv"
    _write_csv(output_path, _TABLE_METADATA_COLUMNS, [_tm_to_dict(r) for r in rows])


def write_report_metadata(rows: List[ReportMetadata], output_root: Path) -> None:
    """Append report metadata rows to report_metadata.csv."""
    output_path = output_root / "report_metadata.csv"
    _write_csv(output_path, _REPORT_METADATA_COLUMNS, [_rm_to_dict(r) for r in rows])


def _write_csv(path: Path, columns: List[str], rows: List[dict]) -> None:
    """Write rows to a CSV file, creating or appending."""
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _tm_to_dict(tm: TableMetadata) -> dict:
    return {
        "table_id": tm.table_id,
        "csv_path": tm.csv_path,
        "ticker": tm.ticker,
        "company_name": tm.company_name,
        "year": tm.year,
        "report_type": tm.report_type,
        "statement_type": tm.statement_type,
        "unit": tm.unit,
        "source_txt_path": tm.source_txt_path,
        "page_number": tm.page_number,
        "table_index": tm.table_index,
        "title": tm.title,
        "nearby_text_before": tm.nearby_text_before,
        "nearby_text_after": tm.nearby_text_after,
        "row_count": tm.row_count,
        "column_count": tm.column_count,
        "numeric_cell_count": tm.numeric_cell_count,
        "quality_score": tm.quality_score,
        "needs_review": tm.needs_review,
        "review_reason": tm.review_reason,
        "created_at": tm.created_at,
    }


def _rm_to_dict(rm: ReportMetadata) -> dict:
    return {
        "report_id": rm.report_id,
        "ticker": rm.ticker,
        "year": rm.year,
        "report_type": rm.report_type,
        "document_name": rm.document_name,
        "source_txt_path": rm.source_txt_path,
        "file_size_bytes": rm.file_size_bytes,
    }
