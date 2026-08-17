"""
tests/test_reasoning_grounding.py — Tests for cell grounding.
"""

from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
from financial_text_to_pandas.types import Intent
import pandas as pd

def test_ground_cells_exact_match():
    dfs = {
        "T1": pd.DataFrame({
            "row_label_full": ["Doanh thu thuần", "Chi phí"],
            "numeric__2023": [100.0, 50.0],
            "numeric__2022": [90.0, 45.0]
        })
    }
    intent = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
    
    result = ground_cells(intent, dfs)
    assert result.error_type is None
    assert len(result.grounded_cells) == 1
    
    cell = result.grounded_cells[0]
    assert cell.table_id == "T1"
    assert cell.row_label == "Doanh thu thuần"
    assert cell.column_label == "numeric__2023"
    assert cell.parsed_value == 100.0
    assert cell.grounding_method == "exact"

def test_ground_cells_fuzzy_match():
    dfs = {
        "T1": pd.DataFrame({
            "row_label_raw": ["Doanh thu thuan ban hang", "Chi phi"],
            "numeric__2023": [100.0, 50.0]
        })
    }
    # Slight typo in metric
    intent = Intent(None, None, [2023], "unknown", ["doanh thu thuần"], None, "lookup")
    
    result = ground_cells(intent, dfs)
    assert result.error_type is None
    assert len(result.grounded_cells) == 1
    
    cell = result.grounded_cells[0]
    assert cell.grounding_method == "fuzzy"
    assert cell.row_label == "Doanh thu thuan ban hang"
    assert cell.confidence >= 0.8

def test_ground_cells_missing_evidence():
    result = ground_cells(Intent(None, None, [], "unknown", ["metric"], None, "lookup"), {})
    assert result.error_type == "I_INSUFFICIENT_EVIDENCE"
