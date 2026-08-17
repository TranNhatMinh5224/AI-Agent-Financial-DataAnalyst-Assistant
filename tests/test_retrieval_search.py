"""
tests/test_retrieval_search.py — Tests for candidate merging and search orchestration.
"""

from financial_text_to_pandas.retrieval.search import merge_candidates
from financial_text_to_pandas.types import Candidate

def _cand(tid: str, bm25: float, dense: float, source: str) -> Candidate:
    return Candidate(
        query_id="q1",
        question="question",
        table_id=tid,
        rank=0,
        bm25_score=bm25,
        dense_score=dense,
        reranker_score=0.0,
        retrieval_source=source,
        csv_path="",
        metadata_filter_status="",
        model_name="",
        model_version="",
        created_at=""
    )

def test_merge_candidates():
    c1 = _cand("T1", 10.0, 0.0, "bm25")
    c2 = _cand("T2", 5.0, 0.0, "bm25")
    c3 = _cand("T1", 0.0, 0.8, "dense") # Overlaps with c1
    c4 = _cand("T3", 0.0, 0.9, "dense")
    
    merged = merge_candidates([[c1, c2], [c3, c4]])
    
    assert len(merged) == 3
    # Check T1 merged scores
    t1 = next(c for c in merged if c.table_id == "T1")
    assert t1.bm25_score == 10.0
    assert t1.dense_score == 0.8
    assert "bm25" in t1.retrieval_source
    assert "dense" in t1.retrieval_source
