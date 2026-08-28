"""
tests/test_reasoning_strategy.py — Tests for strategy selection and execution.
"""

from financial_text_to_pandas.reasoning.strategy import choose_reasoning_strategy, run_deterministic_lookup
from financial_text_to_pandas.types import Intent, CellGroundingResult, GroundedCell

def test_choose_strategy_deterministic():
    intent = Intent(None, None, [], "unknown", [], None, "lookup")
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    
    strategy = choose_reasoning_strategy(intent, grounding)
    assert strategy == "deterministic"

def test_choose_strategy_pot_multi_cell():
    intent = Intent(None, None, [], "unknown", [], None, "lookup")
    c1 = GroundedCell("T1", "", 1, "R", "C1", "10", 10.0, None, 1.0, "exact", None)
    c2 = GroundedCell("T1", "", 1, "R", "C2", "20", 20.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([c1, c2], None)
    
    strategy = choose_reasoning_strategy(intent, grounding)
    assert strategy == "pot" # multiple cells

def test_choose_strategy_pot_arithmetic():
    intent = Intent(None, None, [], "unknown", [], None, "difference")
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    
    strategy = choose_reasoning_strategy(intent, grounding)
    assert strategy == "pot"

def test_choose_strategy_multi_hop():
    intent = Intent(None, None, [], "unknown", [], None, "multi_hop")
    grounding = CellGroundingResult([], None)
    
    strategy = choose_reasoning_strategy(intent, grounding)
    assert strategy == "multi_hop"

def test_run_deterministic_lookup():
    intent = Intent(None, None, [], "unknown", [], None, "lookup")
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    
    result = run_deterministic_lookup(intent, grounding)
    assert result.strategy == "deterministic"
    assert result.numeric_result == 10.0
    assert result.error_type is None

from unittest.mock import patch
from financial_text_to_pandas.reasoning.strategy import run_pot_strategy
from financial_text_to_pandas.types import EvidencePackage

def test_run_pot_strategy_self_correction():
    intent = Intent(None, None, [2022, 2023], "unknown", ["doanh thu"], None, "difference")
    c0 = GroundedCell("T1", "", 1, "R", "C1", "100", 100.0, None, 1.0, "exact", None, symbol_name="NUM_0")
    c1 = GroundedCell("T1", "", 1, "R", "C2", "150", 150.0, None, 1.0, "exact", None, symbol_name="NUM_1")
    grounding = CellGroundingResult([c0, c1], None)
    package = EvidencePackage("Q1", "Doanh thu tăng bao nhiêu?", intent, [], [])
    
    # Mock generate_pot_code to fail on attempt 1 with bad syntax, but succeed on attempt 2
    codes = ["result = NUM_1 - ", "result = NUM_1 - NUM_0"]
    with patch("financial_text_to_pandas.reasoning.strategy.generate_pot_code", side_effect=codes):
        res = run_pot_strategy(package, grounding, {}, {})
        assert res.numeric_result == 50.0
        assert "Attempt 2: Self-Correction fix code generated" in res.trace
        assert res.error_type is None

