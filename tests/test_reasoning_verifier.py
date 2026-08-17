"""
tests/test_reasoning_verifier.py — Tests for the reasoning verifier.
"""

from financial_text_to_pandas.reasoning.verifier import verify_answer
from financial_text_to_pandas.types import ReasoningResult, CellGroundingResult, GroundedCell, EvidencePackage
import pandas as pd

def test_verify_answer_valid():
    dfs = {
        "T1": pd.DataFrame({"row_label_full": ["R"], "C": [10.0]})
    }
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    
    result = ReasoningResult("deterministic", None, 10.0, 10.0, "trace", None)
    
    # Mock package
    package = EvidencePackage("q1", "q", None, [], [])
    
    verification = verify_answer(result, grounding, package, dfs)
    assert verification.is_valid
    assert verification.verification_status == "valid"

def test_verify_answer_missing_table():
    dfs = {} # Missing table
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    result = ReasoningResult("deterministic", None, 10.0, 10.0, "trace", None)
    package = EvidencePackage("q1", "q", None, [], [])
    
    verification = verify_answer(result, grounding, package, dfs)
    assert not verification.is_valid
    assert verification.error_type == "E_NUMERICAL_EXTRACTION"

def test_verify_answer_missing_column():
    dfs = {
        "T1": pd.DataFrame({"row_label_full": ["R"], "OtherCol": [10.0]})
    }
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    result = ReasoningResult("deterministic", None, 10.0, 10.0, "trace", None)
    package = EvidencePackage("q1", "q", None, [], [])
    
    verification = verify_answer(result, grounding, package, dfs)
    assert not verification.is_valid
    assert verification.error_type == "E_NUMERICAL_EXTRACTION"

def test_verify_answer_invalid_result():
    dfs = {"T1": pd.DataFrame({"row_label_full": ["R"], "C": [10.0]})}
    cell = GroundedCell("T1", "", 1, "R", "C", "10", 10.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    
    # Result had an error
    result = ReasoningResult("pot", None, None, None, "trace", "C_CALCULATION_ERROR")
    package = EvidencePackage("q1", "q", None, [], [])
    
    verification = verify_answer(result, grounding, package, dfs)
    assert not verification.is_valid
    assert verification.error_type == "C_CALCULATION_ERROR"
