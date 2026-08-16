"""tests/test_text_linker.py — Unit tests for TABLE_REF text linker."""

import pytest
from financial_text_to_pandas.preprocessing.text_linker import replace_tables_with_refs
from financial_text_to_pandas.types import TableRef


def _make_ref(table_id: str, csv_path: str) -> TableRef:
    return TableRef(table_id=table_id, csv_path=csv_path, html_snippet="")


def test_one_table_replacement():
    text = "Before\n<table><tr><td>X</td></tr></table>\nAfter"
    refs = [_make_ref("T001", "tables_csv/AAA/2023/consolidated/T001.csv")]
    result = replace_tables_with_refs(text, refs)
    assert "<table>" not in result
    assert "[[TABLE_REF:T001|tables_csv/AAA/2023/consolidated/T001.csv]]" in result
    assert "Before" in result
    assert "After" in result


def test_multiple_table_replacement():
    text = (
        "<table><tr><td>A</td></tr></table>\n"
        "Middle\n"
        "<table><tr><td>B</td></tr></table>"
    )
    refs = [
        _make_ref("T001", "path/T001.csv"),
        _make_ref("T002", "path/T002.csv"),
    ]
    result = replace_tables_with_refs(text, refs)
    assert "[[TABLE_REF:T001|path/T001.csv]]" in result
    assert "[[TABLE_REF:T002|path/T002.csv]]" in result
    assert "<table>" not in result
    assert "Middle" in result


def test_no_table_page_unchanged():
    text = "===== PAGE 1 =====\nNo tables here, just text."
    refs = []
    result = replace_tables_with_refs(text, refs)
    assert result == text


def test_page_boundaries_preserved():
    text = (
        "===== PAGE 1 =====\nText before\n"
        "<table><tr><td>Data</td></tr></table>\n"
        "===== PAGE 2 =====\nNext page"
    )
    refs = [_make_ref("T001", "path/T001.csv")]
    result = replace_tables_with_refs(text, refs)
    assert "===== PAGE 1 =====" in result
    assert "===== PAGE 2 =====" in result
    assert "[[TABLE_REF:T001" in result


def test_surplus_tables_removed():
    """More HTML tables than refs — surplus tables should be removed."""
    text = (
        "<table><tr><td>A</td></tr></table>\n"
        "<table><tr><td>B</td></tr></table>"
    )
    refs = [_make_ref("T001", "path/T001.csv")]  # only one ref
    result = replace_tables_with_refs(text, refs)
    assert "[[TABLE_REF:T001" in result
    assert "<table>" not in result
