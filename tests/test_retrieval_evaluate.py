"""
tests/test_retrieval_evaluate.py — Tests for evaluation metrics.
"""

from financial_text_to_pandas.retrieval.evaluate import evaluate_retrieval
import pandas as pd
from pathlib import Path

def test_evaluate_retrieval(tmp_path):
    preds = pd.DataFrame([
        {"query_id": "q1", "table_id": "T1", "rank": 1},
        {"query_id": "q1", "table_id": "T2", "rank": 2},
        {"query_id": "q2", "table_id": "T3", "rank": 15}, # Hit at 15
        {"query_id": "q3", "table_id": "T4", "rank": 60}, # Miss top 50
    ])
    
    gold = pd.DataFrame([
        {"query_id": "q1", "golden_table_id": "T2"}, # Hit at rank 2
        {"query_id": "q2", "golden_table_id": "T3"}, # Hit at rank 15
        {"query_id": "q3", "golden_table_id": "T4"}, # Hit at rank 60 -> miss top 50
    ])
    
    out_path = tmp_path / "retrieval_eval.csv"
    metrics = evaluate_retrieval(preds, gold, out_path)
    
    # 3 queries.
    # q1: rank 2 -> hit@10, hit@50
    # q2: rank 15 -> miss@10, hit@50
    # q3: rank 60 -> miss@10, miss@50
    
    import math
    assert math.isclose(metrics.recall_at_10, 1 / 3)
    assert math.isclose(metrics.recall_at_50, 2 / 3)
    assert math.isclose(metrics.missing_evidence_rate, 1 / 3)
    
    # MRR = (1/2 + 1/15 + 1/60) / 3
    expected_mrr = (0.5 + 1/15 + 1/60) / 3
    assert abs(metrics.mrr - expected_mrr) < 1e-6
    
    assert out_path.exists()
