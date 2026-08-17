"""
tests/test_evaluation.py — Tests for evaluation metrics and routines.
"""

from financial_text_to_pandas.evaluation.metrics import (
    calculate_exact_numeric_accuracy,
    calculate_tolerance_numeric_accuracy,
    is_cell_match
)

def test_exact_numeric_accuracy():
    assert calculate_exact_numeric_accuracy(100.0, 100.0) is True
    assert calculate_exact_numeric_accuracy(100.000001, 100.0) is True
    assert calculate_exact_numeric_accuracy(100.0, 101.0) is False
    assert calculate_exact_numeric_accuracy(None, 100.0) is False

def test_tolerance_numeric_accuracy():
    assert calculate_tolerance_numeric_accuracy(104.0, 100.0, 0.05) is True
    assert calculate_tolerance_numeric_accuracy(106.0, 100.0, 0.05) is False
    assert calculate_tolerance_numeric_accuracy(0.000001, 0.0) is True

def test_is_cell_match():
    assert is_cell_match("T1", "Revenue", "2023", "T1", "revenue", "2023") is True
    assert is_cell_match("T1", "Revenue", "2023", "T2", "Revenue", "2023") is False
    assert is_cell_match(None, "Revenue", "2023", "T1", "Revenue", "2023") is False
