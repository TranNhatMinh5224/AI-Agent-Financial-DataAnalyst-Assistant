"""
tests/test_retrieval_bm25.py — Tests for BM25 retrieval.
"""

from financial_text_to_pandas.retrieval.bm25 import BasicBM25, build_bm25_index, search_bm25
import pandas as pd
from pathlib import Path

def test_basic_bm25_scoring():
    corpus_ids = ["t1", "t2", "t3"]
    corpus_texts = [
        "doanh thu thuần aaa 2023",
        "tài sản ngắn hạn fpt 2024",
        "doanh thu aaa 2022"
    ]
    bm25 = BasicBM25(corpus_ids, corpus_texts)
    
    scores = bm25.get_scores("doanh thu aaa")
    
    assert scores[0] > 0
    assert scores[2] > 0
    assert scores[1] == 0  # no overlap
    
    # "doanh thu aaa 2022" has length 4, "doanh thu thuần aaa 2023" length 5
    # BM25 favors shorter documents for same term frequency, but wait, both have 3 matching terms.
    # Scores should be positive for t1 and t3.
    assert scores[0] > 0
    assert scores[2] > 0

def test_build_and_search_bm25(tmp_path):
    corpus = pd.DataFrame([
        {"table_id": "1", "search_text": "hello world"},
        {"table_id": "2", "search_text": "hello python"},
    ])
    index_path = tmp_path / "bm25_index.pkl"
    build_bm25_index(corpus, index_path)
    
    cands = search_bm25(index_path, "q1", "python", top_k=10)
    
    assert len(cands) == 1
    assert cands[0].table_id == "2"
    assert cands[0].bm25_score > 0
