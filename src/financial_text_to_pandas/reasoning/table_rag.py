"""
table_rag.py — TableRAG: Two-level schema + cell retrieval for large tables.

Reference: Chen et al., NeurIPS 2024
           "TableRAG: Million-Token Table Understanding with Language Models"

Mechanism:
    Traditional RAG on tables fails because:
    - Row chunking loses column headers → LLM can't interpret values.
    - Full-table injection causes token inflation and exceeds context limits.

    TableRAG solves this with two-level retrieval:

    Level 1 — Schema Retrieval:
        Use metadata (statement_type, column_names, row_label index)
        to identify WHICH columns and row groups are relevant,
        without loading any cell values into the prompt.

    Level 2 — Cell-targeted Pointers:
        Once columns and row labels are known, retrieve only the exact
        cells at their intersection from the loaded DataFrame.
        Produces a compact snippet < 100 tokens regardless of table size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz


# ─────────────────────────────────────────────────────────────────────────────
# Schema index types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TableSchema:
    """Lightweight schema descriptor for one table (no cell values)."""
    table_id: str
    ticker: str
    year: int
    statement_type: str          # "balance_sheet" | "income_statement" | "cash_flow" | ...
    column_names: List[str]      # flattened column names (after hierarchical flatten)
    row_label_index: List[str]   # unique row_label_raw or row_label_full values
    unit: str
    csv_path: str


@dataclass
class SchemaMatch:
    """Result of Level-1 schema retrieval for a single table."""
    table_id: str
    matched_columns: List[str]
    matched_row_labels: List[str]
    schema_score: float          # 0.0–1.0 relevance estimate


@dataclass
class CellSnippet:
    """Compact cell snippet returned by Level-2 cell-targeted retrieval."""
    table_id: str
    row_label: str
    column_label: str
    raw_value: str
    parsed_value: Optional[float]
    unit: str


# ─────────────────────────────────────────────────────────────────────────────
# Level 1 — Schema Retrieval
# ─────────────────────────────────────────────────────────────────────────────

def build_schema_index(schemas: List[TableSchema]) -> Dict[str, TableSchema]:
    """Build an in-memory schema index keyed by table_id."""
    return {s.table_id: s for s in schemas}


def schema_retrieval(
    query_terms: List[str],
    year_hints: List[int],
    statement_type_hint: Optional[str],
    schemas: List[TableSchema],
    top_k: int = 5,
) -> List[SchemaMatch]:
    """Level 1: Retrieve relevant table schemas without loading any cell data.

    Args:
        query_terms: List of metric keywords extracted from the question.
                     Example: ["doanh thu", "lợi nhuận gộp"]
        year_hints: Years extracted from question. Example: [2022, 2023]
        statement_type_hint: Optional statement type filter.
        schemas: All available table schemas from the corpus metadata.
        top_k: Max number of schema matches to return.

    Returns:
        List of SchemaMatch, sorted by relevance score descending.
    """
    matches: List[SchemaMatch] = []

    for schema in schemas:
        # Hard filter: year and statement type
        if year_hints and schema.year not in year_hints:
            continue
        if statement_type_hint and schema.statement_type != statement_type_hint:
            continue

        # Fuzzy match query terms against column names and row label index
        matched_cols = []
        for term in query_terms:
            term_lower = term.lower()
            for col in schema.column_names:
                if fuzz.partial_ratio(term_lower, col.lower()) >= 70:
                    if col not in matched_cols:
                        matched_cols.append(col)

        matched_rows = []
        for term in query_terms:
            term_lower = term.lower()
            for label in schema.row_label_index:
                if fuzz.partial_ratio(term_lower, label.lower()) >= 70:
                    if label not in matched_rows:
                        matched_rows.append(label)

        if not matched_cols and not matched_rows:
            continue

        # Score: proportion of query terms matched
        total_terms = max(len(query_terms), 1)
        matched_count = len(set(matched_cols + matched_rows))
        score = min(matched_count / total_terms, 1.0)

        matches.append(SchemaMatch(
            table_id=schema.table_id,
            matched_columns=matched_cols,
            matched_row_labels=matched_rows,
            schema_score=score,
        ))

    matches.sort(key=lambda m: m.schema_score, reverse=True)
    return matches[:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# Level 2 — Cell-targeted Retrieval (Pointer-based)
# ─────────────────────────────────────────────────────────────────────────────

def cell_targeted_retrieval(
    df: pd.DataFrame,
    schema_match: SchemaMatch,
    unit: str = "unknown",
) -> List[CellSnippet]:
    """Level 2: Retrieve exact cell values at (row_label × column) intersections.

    Args:
        df: Loaded DataFrame for the matched table.
        schema_match: Level-1 result specifying which rows and columns to target.
        unit: Unit string from table metadata.

    Returns:
        List of CellSnippet — compact evidence for the LLM.
    """
    snippets: List[CellSnippet] = []

    row_col = "row_label_full" if "row_label_full" in df.columns else \
              "row_label_raw" if "row_label_raw" in df.columns else None
    if row_col is None:
        return snippets

    for row_label in schema_match.matched_row_labels:
        # Exact then fuzzy row match
        mask = df[row_col].astype(str).str.lower() == row_label.lower()
        if not mask.any():
            # Fuzzy fallback
            scores = df[row_col].astype(str).apply(
                lambda x: fuzz.partial_ratio(row_label.lower(), x.lower())
            )
            best_idx = scores.idxmax()
            if scores[best_idx] < 70:
                continue
            row = df.loc[[best_idx]]
        else:
            row = df[mask]

        for col in schema_match.matched_columns:
            # Try numeric__ prefixed version first
            num_col = f"numeric__{col}" if not col.startswith("numeric__") else col
            target_col = num_col if num_col in df.columns else (col if col in df.columns else None)
            if target_col is None:
                continue

            raw_val = str(row.iloc[0][target_col]) if len(row) > 0 else ""
            parsed = None
            try:
                parsed = float(raw_val)
            except (ValueError, TypeError):
                pass

            snippets.append(CellSnippet(
                table_id=schema_match.table_id,
                row_label=str(row.iloc[0][row_col]),
                column_label=col,
                raw_value=raw_val,
                parsed_value=parsed,
                unit=unit,
            ))

    return snippets


def format_snippets_for_prompt(snippets: List[CellSnippet]) -> str:
    """Format cell snippets into a compact string for inclusion in the LLM prompt."""
    if not snippets:
        return "(no cells found via TableRAG)"
    lines = ["[TableRAG Cell Snippets]"]
    for s in snippets:
        val_str = f"{s.parsed_value}" if s.parsed_value is not None else s.raw_value
        lines.append(f"  [{s.table_id}] {s.row_label} | {s.column_label} = {val_str} {s.unit}")
    return "\n".join(lines)
