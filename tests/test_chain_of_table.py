"""
tests/test_chain_of_table.py — Unit tests for Chain-of-Table operation pool.

Tests cover each operation in the pool (f_select_row, f_select_col, f_add_col,
f_group_by, f_sort_by) plus the full execute_chain pipeline.
"""

import pytest
import pandas as pd
from financial_text_to_pandas.reasoning.chain_of_table import (
    f_select_row,
    f_select_col,
    f_add_col,
    f_group_by,
    f_sort_by,
    apply_operation,
    execute_chain,
    format_trace_for_display,
    OPERATION_POOL,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "ticker": ["VCB", "BID", "CTG", "VCB", "BID"],
        "year":   [2023, 2023, 2023, 2022, 2022],
        "revenue": [120.0, 95.0, 88.0, 100.0, 80.0],
        "profit":  [30.0, 20.0, 15.0, 25.0, 18.0],
    })


# ── Individual operations ─────────────────────────────────────────────────────

def test_f_select_row(sample_df):
    result = f_select_row(sample_df, "year == 2023")
    assert len(result) == 3
    assert set(result["year"]) == {2023}


def test_f_select_col(sample_df):
    result = f_select_col(sample_df, ["ticker", "revenue"])
    assert list(result.columns) == ["ticker", "revenue"]
    assert "profit" not in result.columns


def test_f_add_col(sample_df):
    result = f_add_col(sample_df, "margin", "profit / revenue * 100")
    assert "margin" in result.columns
    assert abs(result.iloc[0]["margin"] - 25.0) < 1e-6


def test_f_group_by(sample_df):
    result = f_group_by(sample_df, group_col="ticker", agg_col="revenue", agg_func="sum")
    assert "ticker" in result.columns
    assert "revenue" in result.columns
    vcb_row = result[result["ticker"] == "VCB"]
    assert abs(vcb_row.iloc[0]["revenue"] - 220.0) < 1e-6


def test_f_sort_by_descending(sample_df):
    result = f_sort_by(sample_df, col="revenue", ascending=False)
    assert result.iloc[0]["revenue"] == 120.0


def test_f_sort_by_ascending(sample_df):
    result = f_sort_by(sample_df, col="revenue", ascending=True)
    assert result.iloc[0]["revenue"] == 80.0


# ── apply_operation dispatcher ────────────────────────────────────────────────

def test_apply_operation_select_row(sample_df):
    new_df, op_result = apply_operation(sample_df, "f_select_row", {"condition": "year == 2023"})
    assert op_result.success
    assert len(new_df) == 3


def test_apply_operation_unknown(sample_df):
    _, op_result = apply_operation(sample_df, "f_unknown_op", {})
    assert not op_result.success
    assert "Unknown operation" in op_result.error


def test_apply_operation_final_answer_passes_through(sample_df):
    new_df, op_result = apply_operation(sample_df, "f_final_answer", {})
    assert op_result.success
    assert new_df.shape == sample_df.shape


# ── execute_chain ─────────────────────────────────────────────────────────────

def test_execute_chain_bank_top_margin(sample_df):
    """Simulates: Which bank had the highest profit margin in 2023?"""
    plan = [
        {"operation": "f_select_row", "arguments": {"condition": "year == 2023"}},
        {"operation": "f_add_col",    "arguments": {"col_name": "margin_pct", "formula": "profit / revenue * 100"}},
        {"operation": "f_sort_by",    "arguments": {"col": "margin_pct", "ascending": False}},
        {"operation": "f_final_answer", "arguments": {}},
    ]
    trace = execute_chain(sample_df, "Ngân hàng nào có tỷ suất LN cao nhất 2023?", plan)
    assert trace.finished
    assert trace.error is None
    assert trace.final_table is not None
    # VCB should be first: margin = 30/120*100 = 25%
    assert trace.final_table.iloc[0]["ticker"] == "VCB"
    assert len(trace.steps) == 4


def test_execute_chain_stops_on_error(sample_df):
    plan = [
        {"operation": "f_select_row", "arguments": {"condition": "bad_col == 999"}},
        {"operation": "f_final_answer", "arguments": {}},
    ]
    trace = execute_chain(sample_df, "Test error handling", plan)
    assert not trace.finished
    assert trace.error is not None


def test_execute_chain_max_steps(sample_df):
    """Chain exceeding max_steps should not finish."""
    plan = [{"operation": "f_sort_by", "arguments": {"col": "revenue"}}] * 20
    trace = execute_chain(sample_df, "Infinite loop test", plan, max_steps=5)
    assert not trace.finished
    assert "f_final_answer" in (trace.error or "")


# ── format_trace_for_display ──────────────────────────────────────────────────

def test_format_trace_for_display(sample_df):
    plan = [
        {"operation": "f_select_col", "arguments": {"columns": ["ticker", "revenue"]}},
        {"operation": "f_final_answer", "arguments": {}},
    ]
    trace = execute_chain(sample_df, "Test display?", plan)
    display = format_trace_for_display(trace)
    assert "Chain-of-Table" in display
    assert "f_select_col" in display
    assert "f_final_answer" in display
    assert "✅" in display
