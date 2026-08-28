"""tests/test_table_clean.py — Unit tests for table grid cleaning."""

import pytest
import pandas as pd
from bs4 import BeautifulSoup

from financial_text_to_pandas.preprocessing.table_clean import (
    align_grid,
    drop_empty_rows_and_columns,
    expand_rowspan_colspan,
    detect_header_rows,
    flatten_headers,
    propagate_group_context,
)


# ── expand_rowspan_colspan ────────────────────────────────────────────────────

def _parse_table(html: str):
    soup = BeautifulSoup(html, "lxml")
    return soup.find("table")


def test_expand_rowspan_only():
    html = """<table>
      <tr><td rowspan="2">A</td><td>B</td></tr>
      <tr><td>C</td></tr>
    </table>"""
    grid = expand_rowspan_colspan(_parse_table(html))
    assert len(grid) == 2
    assert grid[0][0] == "A"
    assert grid[1][0] == "A"  # Expanded down
    assert grid[0][1] == "B"
    assert grid[1][1] == "C"


def test_expand_colspan_only():
    html = """<table>
      <tr><td colspan="2">Header</td></tr>
      <tr><td>A</td><td>B</td></tr>
    </table>"""
    grid = expand_rowspan_colspan(_parse_table(html))
    assert len(grid) == 2
    assert grid[0][0] == "Header"
    assert grid[0][1] == "Header"  # Expanded right
    assert grid[1][0] == "A"
    assert grid[1][1] == "B"


def test_expand_both_rowspan_colspan():
    html = """<table>
      <tr><td rowspan="2" colspan="2">Corner</td><td>H3</td></tr>
      <tr><td>R2C3</td></tr>
      <tr><td>R3C1</td><td>R3C2</td><td>R3C3</td></tr>
    </table>"""
    grid = expand_rowspan_colspan(_parse_table(html))
    assert grid[0][0] == "Corner"
    assert grid[0][1] == "Corner"
    assert grid[1][0] == "Corner"
    assert grid[1][1] == "Corner"


def test_empty_table():
    html = "<table></table>"
    grid = expand_rowspan_colspan(_parse_table(html))
    assert grid == []


# ── align_grid ────────────────────────────────────────────────────────────────

def test_align_grid_pads_short_rows():
    rows = [["A", "B", "C"], ["D"]]
    aligned = align_grid(rows)
    assert aligned[0] == ["A", "B", "C"]
    assert aligned[1] == ["D", "", ""]


def test_align_grid_already_aligned():
    rows = [["A", "B"], ["C", "D"]]
    aligned = align_grid(rows)
    assert aligned == rows


# ── drop_empty_rows_and_columns ───────────────────────────────────────────────

def test_drop_empty_rows():
    rows = [["A", "B"], ["", ""], ["C", "D"]]
    result = drop_empty_rows_and_columns(rows)
    assert len(result) == 2
    assert result[0] == ["A", "B"]
    assert result[1] == ["C", "D"]


def test_drop_empty_columns():
    rows = [["A", "", "B"], ["C", "", "D"]]
    result = drop_empty_rows_and_columns(rows)
    assert all(len(r) == 2 for r in result)
    assert result[0] == ["A", "B"]


def test_empty_input():
    assert drop_empty_rows_and_columns([]) == []


# ── detect_header_rows ────────────────────────────────────────────────────────

def test_detect_header_keywords():
    grid = [["Chỉ tiêu", "2023", "2022"], ["Doanh thu", "100", "90"]]
    hd = detect_header_rows(grid)
    assert 0 in hd.header_rows


def test_detect_year_header():
    grid = [["", "2023", "2022"], ["Doanh thu", "100", "90"]]
    hd = detect_header_rows(grid)
    assert 0 in hd.header_rows


def test_fallback_header_when_no_keyword():
    grid = [["Item", "Value"], ["Row1", "100"]]
    hd = detect_header_rows(grid)
    # Should at least return row 0 via fallback
    assert len(hd.header_rows) >= 1


# ── flatten_headers ───────────────────────────────────────────────────────────

def test_single_header_row():
    grid = [["Chỉ tiêu", "2023", "2022"], ["Doanh thu", "100", "90"]]
    names = flatten_headers(grid, header_rows=[0])
    assert len(names) == 3
    assert names[0] == "Chỉ tiêu"


def test_multi_row_header():
    grid = [["", "Năm", "Năm"], ["Chỉ tiêu", "2023", "2022"], ["Doanh thu", "100", "90"]]
    names = flatten_headers(grid, header_rows=[0, 1])
    # Should combine "Năm > 2023" and "Năm > 2022"
    assert len(names) == 3
    assert names[1] == "Năm > 2023"
    assert names[2] == "Năm > 2022"

def test_hierarchical_multi_row_header_three_levels():
    grid = [
        ["", "Năm 2023", "Năm 2023"],
        ["", "Quý 4", "Quý 4"],
        ["Chỉ tiêu", "Số tiền", "Tỷ lệ %"],
        ["Doanh thu", "1000", "15%"]
    ]
    names = flatten_headers(grid, header_rows=[0, 1, 2])
    assert names[1] == "Năm 2023 > Quý 4 > Số tiền"
    assert names[2] == "Năm 2023 > Quý 4 > Tỷ lệ %"


def test_duplicate_column_names_are_deduplicated():
    grid = [["Col", "Col", "Col"], ["1", "2", "3"]]
    names = flatten_headers(grid, header_rows=[0])
    # All should be unique
    assert len(names) == len(set(names))


def test_empty_header_cells_get_fallback():
    grid = [["", "", ""], ["1", "2", "3"]]
    names = flatten_headers(grid, header_rows=[0])
    assert all(n.startswith("col_") for n in names)


# ── propagate_group_context ───────────────────────────────────────────────────

def test_one_level_section():
    df = pd.DataFrame({
        "row_label_raw": ["I. Tài sản ngắn hạn", "1. Tiền"],
        "numeric__col": [None, 100.0],
    })
    result = propagate_group_context(df)
    assert "row_label_full" in result.columns
    assert result["row_label_full"].iloc[0] == "I. Tài sản ngắn hạn"
    assert "I. Tài sản ngắn hạn" in result["row_label_full"].iloc[1]
    assert "1. Tiền" in result["row_label_full"].iloc[1]


def test_rows_with_numeric_not_treated_as_section():
    df = pd.DataFrame({
        "row_label_raw": ["Doanh thu", "Giá vốn"],
        "numeric__col": [100.0, 80.0],
    })
    result = propagate_group_context(df)
    # Neither row is a section header since both have numeric values
    assert result["row_label_full"].iloc[0] == "Doanh thu"
    assert result["row_label_full"].iloc[1] == "Giá vốn"
