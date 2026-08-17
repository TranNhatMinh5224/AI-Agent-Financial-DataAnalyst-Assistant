"""
evaluate.py — Evaluate retrieval quality against golden answers.

Phase 2, Step 8.
"""

from __future__ import annotations

from typing import List, Dict
import pandas as pd
from pathlib import Path

from financial_text_to_pandas.types import RetrievalMetrics

def evaluate_retrieval(predictions_df: pd.DataFrame, gold_df: pd.DataFrame, output_path: Path) -> RetrievalMetrics:
    """Evaluate retrieval results.
    
    Args:
        predictions_df: DataFrame of retrieval results. Must have 'query_id', 'table_id', 'rank'.
        gold_df: DataFrame of golden answers. Must have 'query_id', 'golden_table_id'.
        output_path: Where to save retrieval_eval.csv.
        
    Returns:
        RetrievalMetrics object.
    """
    total_queries = len(gold_df)
    if total_queries == 0:
        return RetrievalMetrics(0, 0, 0, 0, 0, 0)
        
    hits_at_10 = 0
    hits_at_50 = 0
    mrr_sum = 0.0
    
    eval_rows = []
    
    for _, gold_row in gold_df.iterrows():
        qid = gold_row["query_id"]
        gold_tid = gold_row["golden_table_id"]
        
        preds = predictions_df[predictions_df["query_id"] == qid].sort_values("rank")
        
        hit_rank = -1
        for rank, pred_tid in zip(preds["rank"], preds["table_id"]):
            if pred_tid == gold_tid:
                hit_rank = rank
                break
                
        if hit_rank != -1 and hit_rank <= 10:
            hits_at_10 += 1
        if hit_rank != -1 and hit_rank <= 50:
            hits_at_50 += 1
            
        if hit_rank != -1:
            mrr_sum += 1.0 / hit_rank
            
        eval_rows.append({
            "query_id": qid,
            "golden_table_id": gold_tid,
            "hit_rank": hit_rank,
            "found_top10": hit_rank != -1 and hit_rank <= 10,
            "found_top50": hit_rank != -1 and hit_rank <= 50
        })
        
    recall_10 = hits_at_10 / total_queries
    recall_50 = hits_at_50 / total_queries
    mrr = mrr_sum / total_queries
    missing_rate = 1.0 - recall_50 # If not in top 50, it's missing from candidate pool entirely
    
    # Reranker hit rate would require knowing dense vs rerank differences, simple proxy here
    reranker_hit = recall_10
    
    metrics = RetrievalMetrics(
        recall_at_10=recall_10,
        recall_at_50=recall_50,
        mrr=mrr,
        missing_evidence_rate=missing_rate,
        reranker_hit_rate=reranker_hit,
        latency_ms=0.0
    )
    
    eval_df = pd.DataFrame(eval_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    eval_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    return metrics
