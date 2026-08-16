"""tests/test_table_extract.py — Unit tests for HTML table extraction."""

import pytest
from financial_text_to_pandas.preprocessing.table_extract import extract_html_tables
from financial_text_to_pandas.types import ReportMetadata

REPORT_META = ReportMetadata(
    report_id="AAA_2023_consolidated",
    ticker="AAA",
    year=2023,
    report_type="consolidated",
    document_name="AAA_financial_statements_2023_consolidated",
    source_txt_path="AAA/2023/AAA_financial_statements_2023_consolidated/file.txt",
    file_size_bytes=1000,
)


def test_one_table():
    page_text = "Some text before\n<table><tr><td>A</td><td>B</td></tr></table>\nSome text after"
    blocks = extract_html_tables(page_text, REPORT_META, page_number=1)
    assert len(blocks) == 1
    assert blocks[0].table_index == 0
    assert blocks[0].page_number == 1
    assert "AAA_2023_consolidated_page1_table0" == blocks[0].table_id
    assert "<table>" in blocks[0].html


def test_multiple_tables():
    page_text = (
        "<table><tr><td>A</td></tr></table>\n"
        "Middle text\n"
        "<table><tr><td>B</td></tr></table>"
    )
    blocks = extract_html_tables(page_text, REPORT_META, page_number=2)
    assert len(blocks) == 2
    assert blocks[0].table_index == 0
    assert blocks[1].table_index == 1
    assert "page2_table0" in blocks[0].table_id
    assert "page2_table1" in blocks[1].table_id


def test_page_without_table():
    page_text = "This page has no tables, just plain text."
    blocks = extract_html_tables(page_text, REPORT_META, page_number=3)
    assert len(blocks) == 0


def test_malformed_html():
    # Missing closing tag — should still extract best-effort
    page_text = "<table><tr><td>Unclosed"
    blocks = extract_html_tables(page_text, REPORT_META, page_number=4)
    # Either 0 or 1 — should not raise an exception
    assert isinstance(blocks, list)


def test_nearby_text_captured():
    page_text = "Context before the table\n<table><tr><td>X</td></tr></table>\nContext after"
    blocks = extract_html_tables(page_text, REPORT_META, page_number=5)
    assert len(blocks) == 1
    assert "Context before" in blocks[0].nearby_text_before
    assert "Context after" in blocks[0].nearby_text_after


def test_table_id_format():
    page_text = "<table><tr><td>Z</td></tr></table>"
    blocks = extract_html_tables(page_text, REPORT_META, page_number=9)
    assert blocks[0].table_id == "AAA_2023_consolidated_page9_table0"
