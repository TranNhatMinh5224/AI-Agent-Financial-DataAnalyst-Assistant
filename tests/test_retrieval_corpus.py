"""
tests/test_retrieval_corpus.py — Tests for corpus building.
"""

from financial_text_to_pandas.retrieval.corpus import build_table_corpus
import pandas as pd
from pathlib import Path
import tempfile

def test_build_table_corpus(tmp_path):
    # Create fake table_metadata.csv
    meta_path = tmp_path / "table_metadata.csv"
    meta_df = pd.DataFrame([
        {
            "table_id": "T1",
            "csv_path": "T1.csv",
            "ticker": "AAA",
            "company_name": "Cong ty AAA",
            "year": 2023,
            "report_type": "consolidated",
            "statement_type": "balance_sheet",
            "unit": "VND",
            "title": "Bang Can Doi",
            "nearby_text_before": "Text before",
            "nearby_text_after": "Text after",
            "needs_review": False,
            "quality_score": 1.0
        }
    ])
    meta_df.to_csv(meta_path, index=False, encoding="utf-8-sig")
    
    # Create fake table CSV
    t1_path = tmp_path / "T1.csv"
    t1_df = pd.DataFrame({
        "row_label_raw": ["Item 1"],
        "numeric__col1": [100]
    })
    t1_df.to_csv(t1_path, index=False, encoding="utf-8-sig")
    
    # Build corpus
    out_path = tmp_path / "table_corpus.csv"
    corpus = build_table_corpus(meta_path, out_path)
    
    assert len(corpus) == 1
    assert "search_text" in corpus.columns
    search_text = corpus.iloc[0]["search_text"]
    
    # Check if key info is in search text
    assert "AAA" in search_text
    assert "Bang Can Doi" in search_text
    assert "Text before Text after" in search_text
    assert "VND" in search_text
    assert "Item 1" in search_text
    assert "numeric__" not in search_text # excluded

def test_skip_needs_review(tmp_path):
    meta_path = tmp_path / "table_metadata.csv"
    meta_df = pd.DataFrame([
        {"table_id": "T1", "csv_path": "T1.csv", "needs_review": True},
        {"table_id": "T2", "csv_path": "T2.csv", "needs_review": False},
    ])
    meta_df.to_csv(meta_path, index=False, encoding="utf-8-sig")
    
    out_path = tmp_path / "table_corpus.csv"
    corpus = build_table_corpus(meta_path, out_path, include_review=False)
    
    assert len(corpus) == 1
    assert corpus.iloc[0]["table_id"] == "T2"
