"""
metrics.py — QA and Grounding Metrics Calculation.
"""

from __future__ import annotations
import math

def calculate_exact_numeric_accuracy(predicted: float, expected: float) -> bool:
    """Exact numeric match, ignoring floating point errors."""
    if predicted is None or expected is None:
        return False
    return math.isclose(predicted, expected, rel_tol=1e-5)

def calculate_tolerance_numeric_accuracy(predicted: float, expected: float, tol: float = 0.05) -> bool:
    """Check if predicted is within a given tolerance (e.g. 5%)."""
    if predicted is None or expected is None:
        return False
    if expected == 0:
        return math.isclose(predicted, 0, abs_tol=1e-5)
    return abs(predicted - expected) / abs(expected) <= tol

def is_cell_match(pred_table: str, pred_row: str, pred_col: str, gold_table: str, gold_row: str, gold_col: str) -> bool:
    """Check if the predicted cell matches the golden cell."""
    if not pred_table or not gold_table:
        return False
        
    t_match = pred_table == gold_table
    r_match = str(pred_row).lower().strip() == str(gold_row).lower().strip()
    c_match = str(pred_col).lower().strip() == str(gold_col).lower().strip()
    
    return t_match and r_match and c_match
