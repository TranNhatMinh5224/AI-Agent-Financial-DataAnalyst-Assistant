"""
tests/test_reasoning_evidence.py — Tests for loading evidence.
"""

from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.types import EvidencePackage, Intent, EvidenceTable, Candidate
import pandas as pd
from pathlib import Path
import pytest

def test_load_evidence_tables(tmp_path):
    # Setup mock csv
    csv_path = tmp_path / "T1.csv"
    df = pd.DataFrame({"A": [1, 2]})
    df.to_csv(csv_path, index=False)
    
    cand = Candidate("q1", "q", "T1", 1, 1.0, 1.0, 1.0, "mock", "T1.csv", "pass", "mock", "1", "now")
    table = EvidenceTable(cand)
    
    package = EvidencePackage(
        query_id="q1",
        question="q",
        intent=Intent(None, None, [], "unknown", [], None, "unknown"),
        tables=[table],
        linked_text_context=[]
    )
    
    dfs = load_evidence_tables(package, tmp_path)
    
    assert "T1" in dfs
    assert len(dfs["T1"]) == 2
    assert "A" in dfs["T1"].columns

def test_load_evidence_tables_missing_file(tmp_path):
    cand = Candidate("q1", "q", "T1", 1, 1.0, 1.0, 1.0, "mock", "missing.csv", "pass", "mock", "1", "now")
    table = EvidenceTable(cand)
    package = EvidencePackage("q1", "q", Intent(None, None, [], "unknown", [], None, "unknown"), [table], [])
    
    with pytest.raises(FileNotFoundError):
        load_evidence_tables(package, tmp_path)
