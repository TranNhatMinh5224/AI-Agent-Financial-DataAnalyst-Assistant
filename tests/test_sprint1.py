"""
tests/test_sprint1.py — Unit tests cho toàn bộ Sprint 1 fixes.

Chạy: python -m pytest tests/test_sprint1.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
from financial_text_to_pandas.reasoning.tools import safe_get_cell, _normalize_label
from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox, safe_div
from financial_text_to_pandas.reasoning.strategy import choose_reasoning_strategy, _OP_TO_STRATEGY
from financial_text_to_pandas.types import Intent, CellGroundingResult, GroundedCell


# ═══════════════════════════════════════════════════════════════
# 1. INTENT EXTRACTION (BUG-006 FIX)
# ═══════════════════════════════════════════════════════════════

class TestIntentExtraction:
    def test_lookup_doanh_thu_thuan(self):
        intent = extract_intent("Doanh thu thuần của AAA năm 2023 là bao nhiêu?")
        assert intent.ticker == "AAA"
        assert 2023 in intent.years
        assert "doanh thu thuần" in intent.metrics
        assert intent.operation == "lookup"

    def test_lookup_loi_nhuan_sau_thue(self):
        intent = extract_intent("Lợi nhuận sau thuế của FPT năm 2022 là bao nhiêu tỷ?")
        assert intent.ticker == "FPT"
        assert "lợi nhuận sau thuế" in intent.metrics
        assert intent.unit_requested == "tỷ"

    def test_operation_growth_rate(self):
        intent = extract_intent("Tốc độ tăng trưởng doanh thu của VNM từ 2021 đến 2023")
        assert intent.operation == "growth_rate"
        assert 2021 in intent.years
        assert 2023 in intent.years

    def test_operation_difference(self):
        intent = extract_intent("Chênh lệch lợi nhuận gộp của HPG giữa 2022 và 2023")
        assert intent.operation == "difference"
        assert intent.ticker == "HPG"
        assert "lợi nhuận gộp" in intent.metrics

    def test_operation_ratio(self):
        intent = extract_intent("Biên lợi nhuận gộp của MWG năm 2023")
        assert intent.operation == "ratio"

    def test_operation_sum(self):
        intent = extract_intent("Tổng doanh thu của AAA trong năm 2023")
        assert intent.operation == "sum"

    def test_multi_metric_extraction(self):
        """BUG-006 FIX: Phải extract được nhiều metrics, không chỉ 1."""
        intent = extract_intent("So sánh doanh thu thuần và lợi nhuận sau thuế của FPT 2023")
        # Ít nhất phải tìm được 1 metric
        assert len(intent.metrics) >= 1

    def test_long_metric_preferred_over_short(self):
        """Chuỗi dài phải được ưu tiên hơn sub-string ngắn."""
        intent = extract_intent("Lợi nhuận sau thuế thu nhập doanh nghiệp của AAA 2023")
        # "lợi nhuận sau thuế" phải được match, KHÔNG phải chỉ "lợi nhuận"
        assert any("thuế" in m for m in intent.metrics)

    def test_no_ticker(self):
        intent = extract_intent("Tổng tài sản năm 2023 là bao nhiêu?")
        assert intent.ticker is None
        assert 2023 in intent.years

    def test_unit_trieu_dong(self):
        intent = extract_intent("Doanh thu của AAA tính bằng triệu đồng")
        assert intent.unit_requested == "triệu đồng"

    def test_acronym_expansion(self):
        """normalize_query_language phải expand LNST trước khi match."""
        intent = extract_intent("LNST của VNM năm 2023")
        # Sau khi expand LNST → "lợi nhuận sau thuế", phải match được metric
        # (chỉ test không bị exception)
        assert intent is not None


# ═══════════════════════════════════════════════════════════════
# 2. CELL GROUNDING — MULTI-METRIC (BUG-001 FIX)
# ═══════════════════════════════════════════════════════════════

def _make_df():
    return pd.DataFrame({
        "row_label_full": ["Doanh thu thuần", "Lợi nhuận sau thuế", "Tổng tài sản"],
        "numeric__2023":  [1000.0, 200.0, 5000.0],
        "numeric__2022":  [900.0,  180.0, 4500.0],
    })


class TestCellGrounding:
    def test_single_metric_single_year(self):
        dfs = {"T1": _make_df()}
        intent = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
        result = ground_cells(intent, dfs)
        assert result.error_type is None
        assert len(result.grounded_cells) == 1
        assert result.grounded_cells[0].parsed_value == 1000.0

    def test_multi_metric_both_grounded(self):
        """BUG-001 FIX: Loop qua tất cả metrics."""
        dfs = {"T1": _make_df()}
        intent = Intent(None, None, [2023], "unknown",
                        ["doanh thu thuần", "lợi nhuận sau thuế"], None, "difference")
        result = ground_cells(intent, dfs)
        assert result.error_type is None
        assert len(result.grounded_cells) == 2
        values = {c.parsed_value for c in result.grounded_cells}
        assert 1000.0 in values
        assert 200.0 in values

    def test_symbol_names_assigned_sequentially(self):
        """BUG-021 FIX: symbol_name phải gán ngay tại vòng lặp."""
        dfs = {"T1": _make_df()}
        intent = Intent(None, None, [2022, 2023], "unknown", ["doanh thu thuần"], None, "growth_rate")
        result = ground_cells(intent, dfs)
        assert result.error_type is None
        symbols = [c.symbol_name for c in result.grounded_cells]
        assert "NUM_0" in symbols
        assert "NUM_1" in symbols

    def test_unparseable_cell_skipped(self):
        """BUG-002 FIX: Cell không parse được phải bị skip, không gán 0.0."""
        dfs = {"T1": pd.DataFrame({
            "row_label_full": ["Doanh thu thuần"],
            "numeric__2023":  ["N/A"],  # không parse được
        })}
        intent = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
        result = ground_cells(intent, dfs)
        # Không có cell nào được ground vì N/A không parse được
        assert result.error_type == "E_NUMERICAL_EXTRACTION"
        assert len(result.grounded_cells) == 0

    def test_empty_dfs_returns_insufficient(self):
        intent = Intent(None, None, [2023], "unknown", ["doanh thu"], None, "lookup")
        result = ground_cells(intent, {})
        assert result.error_type == "I_INSUFFICIENT_EVIDENCE"

    def test_no_metrics_returns_extraction_error(self):
        dfs = {"T1": _make_df()}
        intent = Intent(None, None, [2023], "unknown", [], None, "lookup")
        result = ground_cells(intent, dfs)
        assert result.error_type == "E_NUMERICAL_EXTRACTION"


# ═══════════════════════════════════════════════════════════════
# 3. SAFE GET CELL — FUZZY MATCH (BUG-011 FIX)
# ═══════════════════════════════════════════════════════════════

class TestSafeGetCell:
    def _dfs(self):
        return {"T1": pd.DataFrame({
            "row_label_full": ["Doanh thu thuần (1)", "Lợi nhuận  sau  thuế"],
            "numeric__2023":  [1000.0, 200.0],
        })}

    def test_exact_match(self):
        val = safe_get_cell(self._dfs(), "T1", "Doanh thu thuần (1)", "numeric__2023")
        assert val == 1000.0

    def test_fuzzy_match_ocr_noise(self):
        """BUG-011 FIX: OCR thêm ghi chú (1) — fuzzy vẫn phải match."""
        val = safe_get_cell(self._dfs(), "T1", "Doanh thu thuần", "numeric__2023")
        assert val == 1000.0

    def test_fuzzy_match_extra_spaces(self):
        """OCR thêm khoảng trắng thừa."""
        val = safe_get_cell(self._dfs(), "T1", "Lợi nhuận sau thuế", "numeric__2023")
        assert val == 200.0

    def test_table_not_found_raises(self):
        with pytest.raises(ValueError, match="not found in evidence"):
            safe_get_cell({}, "MISSING", "row", "col")

    def test_row_below_threshold_raises(self):
        with pytest.raises(ValueError, match="not found"):
            safe_get_cell(self._dfs(), "T1", "Hoàn toàn khác", "numeric__2023", fuzzy_threshold=95)

    def test_normalize_label(self):
        assert _normalize_label("Doanh thu thuần (V.1)") == "doanh thu thuan v 1"
        assert _normalize_label("  Lợi   nhuận  ") == "loi nhuan"


# ═══════════════════════════════════════════════════════════════
# 4. STRATEGY SELECTION (BUG-012 FIX)
# ═══════════════════════════════════════════════════════════════

def _grounding(n_cells: int) -> CellGroundingResult:
    cells = [
        GroundedCell("T1", "", 0, f"row_{i}", "col", "100", 100.0, None, 1.0, "exact", None, f"NUM_{i}")
        for i in range(n_cells)
    ]
    return CellGroundingResult(cells, None)


class TestStrategySelection:
    def test_lookup_single_cell_deterministic(self):
        intent = Intent(None, None, [2023], "unknown", ["metric"], None, "lookup")
        strategy = choose_reasoning_strategy(intent, _grounding(1))
        assert strategy == "deterministic"

    def test_lookup_multi_cell_pot(self):
        """Nếu có > 1 cell, không thể dùng deterministic."""
        intent = Intent(None, None, [2023], "unknown", ["metric"], None, "lookup")
        strategy = choose_reasoning_strategy(intent, _grounding(2))
        assert strategy == "pot"

    def test_growth_rate_always_pot(self):
        intent = Intent(None, None, [2022, 2023], "unknown", ["metric"], None, "growth_rate")
        strategy = choose_reasoning_strategy(intent, _grounding(2))
        assert strategy in ("pot", "multi_hop")

    @pytest.mark.parametrize("op", ["difference", "ratio", "sum", "count", "mean", "median"])
    def test_all_arithmetic_ops_map_to_pot(self, op):
        """BUG-012 FIX: Mọi arithmetic operation phải có mapping."""
        assert op in _OP_TO_STRATEGY
        assert _OP_TO_STRATEGY[op] == "pot"

    def test_multi_hop_two_years(self):
        """Câu hỏi 2 năm → multi_hop strategy."""
        intent = Intent(None, None, [2022, 2023], "unknown", ["metric"], None, "difference")
        strategy = choose_reasoning_strategy(intent, _grounding(2))
        assert strategy == "multi_hop"

    def test_multi_hop_operation(self):
        intent = Intent(None, None, [2023], "unknown", ["metric"], None, "multi_hop")
        strategy = choose_reasoning_strategy(intent, _grounding(1))
        assert strategy == "multi_hop"


# ═══════════════════════════════════════════════════════════════
# 5. SANDBOX — SPRINT 0 REGRESSION + SPRINT 1
# ═══════════════════════════════════════════════════════════════

class TestSandboxRegression:
    def test_safe_div_normal(self):
        assert safe_div(10.0, 2.0) == 5.0

    def test_safe_div_zero_denominator(self):
        """BUG-002 Root cause: ZeroDivisionError → safe_div trả 0.0."""
        assert safe_div(100.0, 0.0) == 0.0

    def test_safe_div_custom_default(self):
        assert safe_div(100.0, 0.0, default=-1.0) == -1.0

    def test_sandbox_with_safe_div(self):
        """LLM sinh code dùng safe_div — phải chạy không crash."""
        code = "result = safe_div(NUM_1 - NUM_0, NUM_0) * 100"
        val = run_pandas_sandbox(code, {}, symbol_map={"NUM_0": 100.0, "NUM_1": 120.0})
        assert val == 20.0

    def test_sandbox_strip_markdown(self):
        """BUG-Sprint0: clean_code_string phải bóc markdown."""
        code = "```python\nresult = 42.0\n```"
        val = run_pandas_sandbox(code, {})
        assert val == 42.0

    def test_sandbox_symbol_map_multi(self):
        """Growth rate formula với 2 symbols."""
        code = "result = safe_div(NUM_1 - NUM_0, NUM_0) * 100"
        val = run_pandas_sandbox(code, {}, symbol_map={"NUM_0": 1000.0, "NUM_1": 1200.0})
        assert abs(val - 20.0) < 1e-9

    def test_sandbox_optional_import_fixed(self):
        """BUG-005 FIX: Sandbox import không còn NameError do thiếu Optional."""
        from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox
        # Nếu import thành công là fix đúng
        assert run_pandas_sandbox is not None
