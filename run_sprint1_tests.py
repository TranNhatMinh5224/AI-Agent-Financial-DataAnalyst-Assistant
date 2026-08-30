"""
run_sprint1_tests.py — Chạy toàn bộ Sprint 1 tests mà không cần pytest.
Dùng khi pytest chưa được cài hoặc muốn xem output đơn giản.

Chạy: python run_sprint1_tests.py
"""

import sys
import traceback
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def run_test(name, fn):
    try:
        fn()
        results.append((PASS, name))
        print(f"  {PASS}  {name}")
    except Exception as e:
        results.append((FAIL, name))
        print(f"  {FAIL}  {name}")
        traceback.print_exc()
        print()


# ── Imports ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("  SPRINT 1 TEST RUNNER")
print("=" * 60)

try:
    import pandas as pd
    from financial_text_to_pandas.reasoning.intent import extract_intent
    from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
    from financial_text_to_pandas.reasoning.tools import safe_get_cell, _normalize_label
    from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox, safe_div
    from financial_text_to_pandas.reasoning.strategy import choose_reasoning_strategy, _OP_TO_STRATEGY
    from financial_text_to_pandas.types import Intent, CellGroundingResult, GroundedCell
    print("✅ All imports successful\n")
except Exception as e:
    print(f"❌ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_df():
    return pd.DataFrame({
        "row_label_full": ["Doanh thu thuần", "Lợi nhuận sau thuế", "Tổng tài sản"],
        "numeric__2023":  [1000.0, 200.0, 5000.0],
        "numeric__2022":  [900.0,  180.0, 4500.0],
    })

def _grounding(n):
    cells = [
        GroundedCell("T1", "", 0, f"row_{i}", "col", "100", 100.0, None, 1.0, "exact", None, f"NUM_{i}")
        for i in range(n)
    ]
    return CellGroundingResult(cells, None)


# ══════════════════════════════════════════════════════════════
print("\n--- [1] INTENT EXTRACTION (BUG-006) ---")
# ══════════════════════════════════════════════════════════════

def t_intent_lookup():
    i = extract_intent("Doanh thu thuần của AAA năm 2023 là bao nhiêu?")
    assert i.ticker == "AAA", f"Expected AAA, got {i.ticker}"
    assert 2023 in i.years, f"Expected 2023 in years, got {i.years}"
    assert "doanh thu thuần" in i.metrics, f"metrics={i.metrics}"
    assert i.operation == "lookup", f"op={i.operation}"
run_test("Intent lookup — ticker/year/metric/op", t_intent_lookup)

def t_intent_loi_nhuan():
    i = extract_intent("Lợi nhuận sau thuế của FPT năm 2022 là bao nhiêu tỷ?")
    assert "lợi nhuận sau thuế" in i.metrics, f"metrics={i.metrics}"
    assert i.unit_requested == "tỷ", f"unit={i.unit_requested}"
run_test("Intent — lợi nhuận sau thuế + tỷ đồng", t_intent_loi_nhuan)

def t_intent_growth():
    i = extract_intent("Tốc độ tăng trưởng doanh thu của VNM từ 2021 đến 2023")
    assert i.operation == "growth_rate", f"op={i.operation}"
    assert 2021 in i.years and 2023 in i.years
run_test("Intent operation — growth_rate", t_intent_growth)

def t_intent_difference():
    i = extract_intent("Chênh lệch lợi nhuận gộp của HPG giữa 2022 và 2023")
    assert i.operation == "difference", f"op={i.operation}"
    assert "lợi nhuận gộp" in i.metrics, f"metrics={i.metrics}"
run_test("Intent operation — difference + lợi nhuận gộp", t_intent_difference)

def t_intent_ratio():
    i = extract_intent("Biên lợi nhuận gộp của MWG năm 2023")
    assert i.operation == "ratio", f"op={i.operation}"
run_test("Intent operation — ratio", t_intent_ratio)

def t_intent_sum():
    i = extract_intent("Tổng doanh thu của AAA trong năm 2023")
    assert i.operation == "sum", f"op={i.operation}"
run_test("Intent operation — sum", t_intent_sum)

def t_intent_long_preferred():
    i = extract_intent("Lợi nhuận sau thuế thu nhập doanh nghiệp của AAA 2023")
    assert any("thuế" in m for m in i.metrics), f"metrics={i.metrics}"
run_test("Intent — chuỗi dài ưu tiên hơn sub-string", t_intent_long_preferred)


# ══════════════════════════════════════════════════════════════
print("\n--- [2] CELL GROUNDING — MULTI-METRIC (BUG-001/002/021) ---")
# ══════════════════════════════════════════════════════════════

def t_single_metric():
    dfs = {"T1": _make_df()}
    i = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
    r = ground_cells(i, dfs)
    assert r.error_type is None
    assert len(r.grounded_cells) == 1
    assert r.grounded_cells[0].parsed_value == 1000.0
run_test("Grounding — single metric single year", t_single_metric)

def t_multi_metric():
    dfs = {"T1": _make_df()}
    i = Intent(None, None, [2023], "unknown",
                ["doanh thu thuần", "lợi nhuận sau thuế"], None, "difference")
    r = ground_cells(i, dfs)
    assert r.error_type is None, f"error={r.error_type}"
    assert len(r.grounded_cells) == 2, f"got {len(r.grounded_cells)} cells"
    vals = {c.parsed_value for c in r.grounded_cells}
    assert 1000.0 in vals and 200.0 in vals, f"vals={vals}"
run_test("Grounding — multi-metric (BUG-001 fix)", t_multi_metric)

def t_symbol_sequential():
    dfs = {"T1": _make_df()}
    i = Intent(None, None, [2022, 2023], "unknown", ["doanh thu thuần"], None, "growth_rate")
    r = ground_cells(i, dfs)
    assert r.error_type is None
    syms = [c.symbol_name for c in r.grounded_cells]
    assert "NUM_0" in syms and "NUM_1" in syms, f"symbols={syms}"
run_test("Grounding — symbol_name sequential (BUG-021 fix)", t_symbol_sequential)

def t_unparseable_skipped():
    dfs = {"T1": pd.DataFrame({
        "row_label_full": ["Doanh thu thuần"],
        "numeric__2023":  ["N/A"],
    })}
    i = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
    r = ground_cells(i, dfs)
    assert r.error_type == "E_NUMERICAL_EXTRACTION", f"error={r.error_type}"
    assert len(r.grounded_cells) == 0
run_test("Grounding — unparseable cell skipped (BUG-002 fix)", t_unparseable_skipped)

def t_empty_dfs():
    i = Intent(None, None, [2023], "unknown", ["doanh thu"], None, "lookup")
    r = ground_cells(i, {})
    assert r.error_type == "I_INSUFFICIENT_EVIDENCE"
run_test("Grounding — empty dfs → INSUFFICIENT_EVIDENCE", t_empty_dfs)


# ══════════════════════════════════════════════════════════════
print("\n--- [3] SAFE_GET_CELL — FUZZY MATCH (BUG-011) ---")
# ══════════════════════════════════════════════════════════════

def _tool_dfs():
    return {"T1": pd.DataFrame({
        "row_label_full": ["Doanh thu thuần (1)", "Lợi nhuận  sau  thuế"],
        "numeric__2023":  [1000.0, 200.0],
    })}

def t_safe_exact():
    val = safe_get_cell(_tool_dfs(), "T1", "Doanh thu thuần (1)", "numeric__2023")
    assert val == 1000.0
run_test("safe_get_cell — exact match", t_safe_exact)

def t_safe_fuzzy_note():
    """OCR thêm ghi chú (1) → fuzzy vẫn match."""
    val = safe_get_cell(_tool_dfs(), "T1", "Doanh thu thuần", "numeric__2023")
    assert val == 1000.0, f"got {val}"
run_test("safe_get_cell — fuzzy OCR note (BUG-011 fix)", t_safe_fuzzy_note)

def t_safe_fuzzy_spaces():
    val = safe_get_cell(_tool_dfs(), "T1", "Lợi nhuận sau thuế", "numeric__2023")
    assert val == 200.0, f"got {val}"
run_test("safe_get_cell — fuzzy extra spaces (BUG-011 fix)", t_safe_fuzzy_spaces)

def t_safe_missing_table():
    try:
        safe_get_cell({}, "NOPE", "row", "col")
        assert False, "Should raise"
    except ValueError as e:
        assert "not found in evidence" in str(e)
run_test("safe_get_cell — missing table raises ValueError", t_safe_missing_table)

def t_normalize_label():
    assert _normalize_label("Doanh thu thuần (V.1)") == "doanh thu thuan v 1"
run_test("_normalize_label — strip ghi chú", t_normalize_label)


# ══════════════════════════════════════════════════════════════
print("\n--- [4] STRATEGY SELECTION (BUG-012) ---")
# ══════════════════════════════════════════════════════════════

def t_lookup_1cell_deterministic():
    i = Intent(None, None, [2023], "unknown", ["m"], None, "lookup")
    assert choose_reasoning_strategy(i, _grounding(1)) == "deterministic"
run_test("Strategy — lookup + 1 cell → deterministic", t_lookup_1cell_deterministic)

def t_lookup_2cell_pot():
    i = Intent(None, None, [2023], "unknown", ["m"], None, "lookup")
    assert choose_reasoning_strategy(i, _grounding(2)) == "pot"
run_test("Strategy — lookup + 2 cells → pot", t_lookup_2cell_pot)

def t_all_arithmetic_in_map():
    for op in ["difference", "ratio", "sum", "count", "mean", "median", "growth_rate"]:
        assert op in _OP_TO_STRATEGY, f"'{op}' missing from _OP_TO_STRATEGY"
        assert _OP_TO_STRATEGY[op] == "pot", f"'{op}' should map to 'pot'"
run_test("Strategy — all arithmetic ops in _OP_TO_STRATEGY (BUG-012 fix)", t_all_arithmetic_in_map)

def t_two_years_multi_hop():
    i = Intent(None, None, [2022, 2023], "unknown", ["m"], None, "difference")
    assert choose_reasoning_strategy(i, _grounding(2)) == "multi_hop"
run_test("Strategy — 2 years → multi_hop", t_two_years_multi_hop)


# ══════════════════════════════════════════════════════════════
print("\n--- [5] SANDBOX REGRESSION (Sprint 0) ---")
# ══════════════════════════════════════════════════════════════

def t_safe_div_zero():
    assert safe_div(100.0, 0.0) == 0.0
run_test("safe_div — zero denominator = 0.0", t_safe_div_zero)

def t_safe_div_normal():
    assert safe_div(10.0, 2.0) == 5.0
run_test("safe_div — normal division", t_safe_div_normal)

def t_sandbox_growth():
    code = "result = safe_div(NUM_1 - NUM_0, NUM_0) * 100"
    val = run_pandas_sandbox(code, {}, symbol_map={"NUM_0": 1000.0, "NUM_1": 1200.0})
    assert abs(val - 20.0) < 1e-9, f"got {val}"
run_test("Sandbox — growth rate formula with safe_div", t_sandbox_growth)

def t_sandbox_markdown():
    code = "```python\nresult = 42.0\n```"
    val = run_pandas_sandbox(code, {})
    assert val == 42.0
run_test("Sandbox — strip markdown code fence", t_sandbox_markdown)

def t_sandbox_optional_import():
    """BUG-005 FIX: Không còn NameError do thiếu Optional."""
    from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox as _f
    assert _f is not None
run_test("Sandbox — Optional import fixed (BUG-005)", t_sandbox_optional_import)


# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
passed = sum(1 for r, _ in results if r == PASS)
failed = sum(1 for r, _ in results if r == FAIL)
total = len(results)
print(f"  RESULTS: {passed}/{total} PASSED  |  {failed} FAILED")
print("=" * 60)
if failed > 0:
    print("\nFailed tests:")
    for r, name in results:
        if r == FAIL:
            print(f"  - {name}")
    sys.exit(1)
else:
    print("  🎉 All Sprint 1 tests passed!")
    sys.exit(0)
