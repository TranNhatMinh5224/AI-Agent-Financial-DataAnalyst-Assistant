"""
tests/test_delex.py — Unit tests for the 3-Step De-lexicalization pipeline.

Tests cover:
    - Step 1: mask_numbers_in_text
    - Step 2: build_delex_context (integration of question + grounded cells)
    - Step 3: Deterministic Value Binding (via symbol_map in sandbox)
    - render_audit_trace
"""

import pytest
from financial_text_to_pandas.reasoning.delex import (
    mask_numbers_in_text,
    build_delex_context,
    render_audit_trace,
)
from financial_text_to_pandas.types import GroundedCell


# ── Step 1: mask_numbers_in_text ──────────────────────────────────────────────

def test_mask_simple_integers():
    text = "Tăng từ 500 lên 650"
    masked, num_map = mask_numbers_in_text(text)
    assert "[NUM_0]" in masked
    assert "[NUM_1]" in masked
    assert "500" not in masked
    assert "650" not in masked
    assert num_map["NUM_0"] == "500"
    assert num_map["NUM_1"] == "650"


def test_mask_with_suffix():
    text = "Revenue grew from $500M to $650M"
    masked, num_map = mask_numbers_in_text(text)
    assert "500M" not in masked
    assert "650M" not in masked
    assert len(num_map) == 2


def test_mask_percentage():
    text = "Gross margin improved to 68.4%"
    masked, num_map = mask_numbers_in_text(text)
    assert "68.4" not in masked
    assert any("68.4" in v for v in num_map.values())


def test_mask_thousand_separated():
    text = "Doanh thu đạt 1,234,567 triệu đồng"
    masked, num_map = mask_numbers_in_text(text)
    assert "1,234,567" not in masked
    assert len(num_map) >= 1


def test_mask_start_index_offset():
    """Ensure start_index avoids collision with grounded cell symbols (NUM_0, NUM_1...)."""
    text = "Tăng từ 500 lên 650"
    masked, num_map = mask_numbers_in_text(text, start_index=5)
    assert "NUM_5" in masked
    assert "NUM_6" in masked


def test_mask_no_numbers():
    text = "Không có con số nào trong câu này."
    masked, num_map = mask_numbers_in_text(text)
    assert masked == text
    assert num_map == {}


# ── Step 2: build_delex_context ───────────────────────────────────────────────

def _make_cell(sym: str, row: str, col: str, val: float) -> GroundedCell:
    return GroundedCell(
        table_id="T1", csv_path="", page_number=1,
        row_label=row, column_label=col,
        raw_value=str(val), parsed_value=val,
        unit=None, confidence=1.0,
        grounding_method="exact", error_type=None,
        symbol_name=sym,
    )


def test_build_delex_context_masks_question():
    cells = [
        _make_cell("NUM_0", "Doanh thu", "numeric__2022", 500.0),
        _make_cell("NUM_1", "Doanh thu", "numeric__2023", 650.0),
    ]
    question = "Doanh thu tăng bao nhiêu phần trăm từ 500 lên 650?"
    ctx = build_delex_context(question, cells)

    # Question should have its inline numbers masked
    assert "500" not in ctx.masked_question
    assert "650" not in ctx.masked_question

    # Grounded cell symbols present in symbol_map
    assert ctx.symbol_map["NUM_0"] == 500.0
    assert ctx.symbol_map["NUM_1"] == 650.0


def test_build_delex_context_cell_paths_in_cells_str():
    cells = [_make_cell("NUM_0", "Lợi nhuận gộp > EBITDA", "Năm 2023 > Quý 4", 120.5)]
    ctx = build_delex_context("Lợi nhuận là bao nhiêu?", cells)

    assert "RowPath: Lợi nhuận gộp > EBITDA" in ctx.masked_cells_str
    assert "ColPath: Năm 2023 > Quý 4" in ctx.masked_cells_str
    assert "NUM_0" in ctx.masked_cells_str


def test_build_delex_context_no_cells():
    ctx = build_delex_context("Câu hỏi không có ô grounded nào.", [])
    assert ctx.masked_cells_str == "(no grounded cells)"
    assert ctx.symbol_map == {}


# ── render_audit_trace ────────────────────────────────────────────────────────

def test_render_audit_trace():
    cells = [_make_cell("NUM_0", "Doanh thu", "numeric__2023", 650.0)]
    ctx = build_delex_context("Doanh thu 650?", cells)
    trace = render_audit_trace(ctx)

    assert "[De-lexicalization Binding Table]" in trace
    assert "NUM_0" in trace
    assert "650" in trace


# ── Integration: Step 3 — Deterministic Value Binding via Sandbox ─────────────

def test_sandbox_executes_symbolic_formula():
    """Confirm sandbox correctly resolves NUM_X symbols to compute a real result."""
    from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox
    symbol_map = {"NUM_0": 500.0, "NUM_1": 650.0}
    code = "result = (NUM_1 - NUM_0) / NUM_0 * 100"
    val = run_pandas_sandbox(code, {}, symbol_map=symbol_map)
    assert abs(val - 30.0) < 1e-6
