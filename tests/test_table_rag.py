"""
tests/test_table_rag.py — Unit tests for TableRAG two-level retrieval.

Tests cover:
    - Level 1: schema_retrieval with year/statement_type/fuzzy term matching
    - Level 2: cell_targeted_retrieval using SchemaMatch pointers
    - format_snippets_for_prompt
"""

import pytest
import pandas as pd
from financial_text_to_pandas.reasoning.table_rag import (
    TableSchema,
    SchemaMatch,
    schema_retrieval,
    cell_targeted_retrieval,
    format_snippets_for_prompt,
)


@pytest.fixture
def schemas():
    return [
        TableSchema(
            table_id="VCB_2023_IS",
            ticker="VCB",
            year=2023,
            statement_type="income_statement",
            column_names=["numeric__2023", "numeric__2022"],
            row_label_index=["Doanh thu thuần", "Lợi nhuận gộp", "Chi phí hoạt động"],
            unit="tỷ đồng",
            csv_path="output/VCB/VCB_2023_IS.csv",
        ),
        TableSchema(
            table_id="BID_2023_BS",
            ticker="BID",
            year=2023,
            statement_type="balance_sheet",
            column_names=["numeric__31/12/2023", "numeric__01/01/2023"],
            row_label_index=["Tổng tài sản", "Vốn chủ sở hữu"],
            unit="tỷ đồng",
            csv_path="output/BID/BID_2023_BS.csv",
        ),
        TableSchema(
            table_id="VCB_2022_IS",
            ticker="VCB",
            year=2022,
            statement_type="income_statement",
            column_names=["numeric__2022", "numeric__2021"],
            row_label_index=["Doanh thu thuần", "Lợi nhuận gộp"],
            unit="tỷ đồng",
            csv_path="output/VCB/VCB_2022_IS.csv",
        ),
    ]


# ── Level 1: schema_retrieval ─────────────────────────────────────────────────

def test_schema_retrieval_year_filter(schemas):
    matches = schema_retrieval(["doanh thu"], [2023], None, schemas)
    table_ids = [m.table_id for m in matches]
    assert "VCB_2023_IS" in table_ids
    assert "VCB_2022_IS" not in table_ids


def test_schema_retrieval_statement_type_filter(schemas):
    matches = schema_retrieval(["tài sản"], [2023], "balance_sheet", schemas)
    assert all(m.table_id.endswith("BS") for m in matches)


def test_schema_retrieval_fuzzy_row_term(schemas):
    matches = schema_retrieval(["lợi nhuận"], [2023], None, schemas)
    # "Lợi nhuận gộp" in VCB_2023_IS should match
    vcb_match = next((m for m in matches if m.table_id == "VCB_2023_IS"), None)
    assert vcb_match is not None
    assert any("nhuận" in r.lower() for r in vcb_match.matched_row_labels)


def test_schema_retrieval_no_match_returns_empty(schemas):
    matches = schema_retrieval(["xyz_nonexistent"], [2023], None, schemas)
    assert matches == []


def test_schema_retrieval_top_k(schemas):
    # Without filters, all 3 schemas could match "doanh thu"
    matches = schema_retrieval(["doanh thu"], [], None, schemas, top_k=2)
    assert len(matches) <= 2


# ── Level 2: cell_targeted_retrieval ─────────────────────────────────────────

@pytest.fixture
def sample_is_df():
    return pd.DataFrame({
        "row_label_raw":  ["Doanh thu thuần", "Lợi nhuận gộp", "Chi phí hoạt động"],
        "row_label_full": ["Doanh thu thuần", "Lợi nhuận gộp", "Chi phí hoạt động"],
        "numeric__2023":  [1200.0, 480.0, 200.0],
        "numeric__2022":  [1000.0, 400.0, 180.0],
    })


def test_cell_targeted_retrieval_exact_match(sample_is_df):
    match = SchemaMatch(
        table_id="VCB_2023_IS",
        matched_columns=["2023"],
        matched_row_labels=["Doanh thu thuần"],
        schema_score=1.0,
    )
    snippets = cell_targeted_retrieval(sample_is_df, match, unit="tỷ đồng")
    assert len(snippets) == 1
    assert snippets[0].parsed_value == 1200.0
    assert snippets[0].row_label == "Doanh thu thuần"


def test_cell_targeted_retrieval_multiple_rows(sample_is_df):
    match = SchemaMatch(
        table_id="VCB_2023_IS",
        matched_columns=["2023"],
        matched_row_labels=["Doanh thu thuần", "Lợi nhuận gộp"],
        schema_score=0.9,
    )
    snippets = cell_targeted_retrieval(sample_is_df, match, unit="tỷ đồng")
    assert len(snippets) == 2


def test_cell_targeted_retrieval_empty_when_no_match(sample_is_df):
    match = SchemaMatch(
        table_id="VCB_2023_IS",
        matched_columns=["2023"],
        matched_row_labels=["Không có dòng này"],
        schema_score=0.5,
    )
    snippets = cell_targeted_retrieval(sample_is_df, match)
    assert snippets == []


# ── format_snippets_for_prompt ────────────────────────────────────────────────

def test_format_snippets_non_empty(sample_is_df):
    match = SchemaMatch("T1", ["2023"], ["Doanh thu thuần"], 1.0)
    snippets = cell_targeted_retrieval(sample_is_df, match, unit="tỷ đồng")
    text = format_snippets_for_prompt(snippets)
    assert "[TableRAG Cell Snippets]" in text
    assert "Doanh thu thuần" in text
    assert "1200" in text


def test_format_snippets_empty():
    text = format_snippets_for_prompt([])
    assert "no cells found" in text
