"""
tests/test_retrieval_query_hints.py — Tests for query hint extraction and filtering.
"""

from financial_text_to_pandas.retrieval.query_hints import extract_query_hints, filter_by_metadata
import pandas as pd

def test_extract_ticker():
    hints = extract_query_hints("Doanh thu của AAA năm 2023 là bao nhiêu?")
    assert hints.ticker == "AAA"
    assert hints.years == [2023]
    assert hints.confidence == 0.9

def test_extract_report_type():
    hints = extract_query_hints("Báo cáo hợp nhất của FPT")
    assert hints.ticker == "FPT"
    assert hints.report_type == "consolidated"
    assert hints.confidence >= 0.5

def test_extract_statement_type():
    hints = extract_query_hints("Bảng cân đối kế toán VNM 2024")
    assert hints.ticker == "VNM"
    assert hints.years == [2024]
    assert hints.statement_type == "balance_sheet"

def test_extract_no_hints():
    hints = extract_query_hints("Doanh thu tăng bao nhiêu?")
    assert hints.ticker is None
    assert hints.years == []
    assert hints.confidence == 0.0

def test_filter_by_metadata():
    corpus = pd.DataFrame([
        {"table_id": "1", "ticker": "AAA", "year": "2023"},
        {"table_id": "2", "ticker": "AAA", "year": "2022"},
        {"table_id": "3", "ticker": "FPT", "year": "2023"},
    ])
    
    hints = extract_query_hints("AAA năm 2023")
    filtered = filter_by_metadata(corpus, hints)
    
    assert len(filtered) == 1
    assert filtered.iloc[0]["table_id"] == "1"

def test_filter_over_filtering_fallback():
    # If filter results in empty set, fallback to full corpus
    corpus = pd.DataFrame([
        {"table_id": "1", "ticker": "AAA", "year": "2023"},
    ])
    
    hints = extract_query_hints("VNM năm 2024")
    filtered = filter_by_metadata(corpus, hints)
    
    assert len(filtered) == 1
    assert filtered.iloc[0]["table_id"] == "1"
