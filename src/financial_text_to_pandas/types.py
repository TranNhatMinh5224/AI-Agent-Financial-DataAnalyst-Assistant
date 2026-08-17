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


# ── Phase 2: Retrieval ────────────────────────────────────────────────────────

@dataclass
class QueryHints:
    """Metadata extracted from the user's natural language question."""
    query_id: str
    question: str
    ticker: Optional[str]
    company_name: Optional[str]
    years: list[int]
    report_type: Optional[str]
    statement_type: Optional[str]
    metric_terms: list[str]
    unit_requested: Optional[str]
    operation: Optional[str]
    confidence: float         # 0.0-1.0


@dataclass
class Candidate:
    """A table candidate retrieved during the search phase."""
    query_id: str
    question: str
    table_id: str
    rank: int
    bm25_score: float
    dense_score: float
    reranker_score: float
    retrieval_source: str     # "bm25", "dense", "hybrid"
    csv_path: str
    metadata_filter_status: str # e.g., "pass", "filtered_by_year"
    model_name: str
    model_version: str
    created_at: str


@dataclass
class EvidenceTable:
    """Final selected evidence table after reranking."""
    candidate: Candidate
    # Could include summarized content later
    

@dataclass
class RetrievalMetrics:
    """Evaluation metrics for table retrieval."""
    recall_at_10: float
    recall_at_50: float
    mrr: float
    missing_evidence_rate: float
    reranker_hit_rate: float
    latency_ms: float


# ── Phase 3: Reasoning ────────────────────────────────────────────────────────

from typing import Literal, Any

@dataclass
class Intent:
    """Parsed intention from the user's query for Phase 3."""
    ticker: Optional[str]
    company_name: Optional[str]
    years: list[int]
    report_type: str # "consolidated" | "separate" | "unknown"
    metrics: list[str]
    unit_requested: Optional[str]
    operation: str # "lookup" | "difference" | "growth_rate" | "ratio" | "mean" | "median" | "multi_hop" | "unknown"

@dataclass
class EvidencePackage:
    """The evidence payload passed from Retrieval to Reasoning."""
    query_id: str
    question: str
    intent: Intent
    tables: list[EvidenceTable]
    linked_text_context: list[str]

@dataclass
class GroundedCell:
    """A specific cell matched to answer the query."""
    table_id: str
    csv_path: str
    page_number: int
    row_label: str
    column_label: str
    raw_value: str
    parsed_value: float
    unit: Optional[str]
    confidence: float
    grounding_method: str # "exact" | "row_label_full" | "row_label_raw" | "fuzzy"
    error_type: Optional[str]

@dataclass
class CellGroundingResult:
    """Result of the grounding phase."""
    grounded_cells: list[GroundedCell]
    error_type: Optional[str] # "I_INSUFFICIENT_EVIDENCE", "E_NUMERICAL_EXTRACTION", etc.

@dataclass
class ReasoningResult:
    """Result from a reasoning strategy (Lookup, PoT, CoT, Multi-hop)."""
    strategy: str
    code_generated: Optional[str]
    sandbox_result: Any # Raw value returned by sandbox/LLM
    numeric_result: Optional[float]
    trace: str
    error_type: Optional[str]

@dataclass
class VerificationResult:
    """Result of the verification step."""
    is_valid: bool
    verification_status: str # "valid" | "invalid" | "unverified"
    error_type: Optional[str]
    checked_cells: list[GroundedCell]
    calculation_check: str
    final_answer: float

@dataclass
class Citation:
    """A reference to a source cell for the final answer."""
    table_id: str
    csv_path: str
    page_number: int
    row_label: str
    column_label: str

@dataclass
class FinalAnswer:
    """The final structured answer returned to the user."""
    answer: float
    answer_type: str # "numeric"
    unit: Optional[str]
    citations: list[Citation]
    verification_status: str
    error_type: Optional[str]
    trace: str
    code_generated: Optional[str]
