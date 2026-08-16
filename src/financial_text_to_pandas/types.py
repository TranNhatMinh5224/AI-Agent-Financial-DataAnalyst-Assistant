"""
types.py — Shared dataclass definitions for Phase 1 preprocessing.

All phases import types from this module. Do not define domain types elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# ── Raw OCR ───────────────────────────────────────────────────────────────────

@dataclass
class Page:
    """A single page extracted from an OCR TXT report."""
    page_number: int
    raw_text: str


# ── Report-level ──────────────────────────────────────────────────────────────

@dataclass
class ReportMetadata:
    """Metadata inferred from the file path and OCR content of one report."""
    report_id: str
    ticker: str
    year: int
    report_type: str          # "consolidated" | "separate" | "explanation" | "unknown"
    document_name: str        # directory name of the report
    source_txt_path: str      # relative path from dataset root
    file_size_bytes: int


# ── Table extraction ──────────────────────────────────────────────────────────

@dataclass
class HtmlTableBlock:
    """Raw HTML table block as found in the OCR TXT."""
    table_id: str
    page_number: int
    table_index: int          # position among tables on that page
    html: str                 # raw HTML string of the <table>
    nearby_text_before: str   # up to 300 chars of text before the table
    nearby_text_after: str    # up to 300 chars of text after the table


# ── Table cleaning ────────────────────────────────────────────────────────────

@dataclass
class HeaderDetection:
    """Result of header row detection on a raw grid."""
    header_rows: list[int]    # 0-indexed row indices that are header rows
    confidence: float         # 0.0–1.0
    method: str               # "keyword_score" | "heuristic" | "fallback"


@dataclass
class ParsedNumber:
    """Result of parsing a single Vietnamese numeric string."""
    raw_value: str
    parsed_value: Optional[float]   # None if not a number
    number_type: str                # "integer" | "decimal" | "percent" | "not_number" | "empty"
    unit_hint: Optional[str]        # "%" or None
    parse_status: str               # "ok" | "not_number" | "empty" | "error"


@dataclass
class CleanTable:
    """A cleaned DataFrame ready to write to CSV."""
    table_id: str
    dataframe: pd.DataFrame
    csv_path: Path
    row_count: int
    column_count: int
    numeric_cell_count: int
    quality_score: float      # 0.0–1.0
    needs_review: bool
    review_reason: str


# ── Metadata ──────────────────────────────────────────────────────────────────

@dataclass
class TableMetadata:
    """Per-table metadata row written to table_metadata.csv."""
    table_id: str
    csv_path: str             # relative path from output_root
    ticker: str
    company_name: str
    year: int
    report_type: str
    statement_type: str       # inferred from nearby text / headers
    unit: str                 # inferred unit (e.g. "triệu đồng")
    source_txt_path: str
    page_number: int
    table_index: int
    title: str
    nearby_text_before: str
    nearby_text_after: str
    row_count: int
    column_count: int
    numeric_cell_count: int
    quality_score: float
    needs_review: bool
    review_reason: str
    created_at: str           # ISO datetime string


# ── Audit ─────────────────────────────────────────────────────────────────────

@dataclass
class AuditRow:
    """One row in preprocessing_audit.csv — records outcome of processing one table."""
    report_id: str
    table_id: str
    status: str               # "success" | "failed" | "needs_review"
    raw_shape: str            # e.g. "15x4"
    clean_shape: str          # e.g. "13x6"
    numeric_cell_count: int
    quality_score: float
    needs_review: bool
    review_reason: str
    error_message: str        # empty string if no error


# ── Linked text ───────────────────────────────────────────────────────────────

@dataclass
class TableRef:
    """A reference linking a table_id to its CSV path, used when replacing HTML."""
    table_id: str
    csv_path: str             # relative path for the TABLE_REF marker
    html_snippet: str         # the original HTML string to replace


# ── Pipeline result ───────────────────────────────────────────────────────────

@dataclass
class PreprocessingResult:
    """Summary result returned by the preprocessing pipeline for one report."""
    report_metadata: ReportMetadata
    clean_tables: list[CleanTable]
    table_metadata_rows: list[TableMetadata]
    audit_rows: list[AuditRow]
    linked_text_path: Optional[Path]
    success: bool
    error_message: str
