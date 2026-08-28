"""
evaluate.py — Evaluate system performance against official contest metrics.

Phase 4, Step 8.
"""

from __future__ import annotations

import math
from typing import List, Dict
import pandas as pd
from pathlib import Path

from financial_text_to_pandas.types import ContestMetrics

def evaluate_contest_metrics(
    predictions: List[Dict], 
    gold_data: List[Dict], 
    error_threshold: float = 0.05
) -> ContestMetrics:
    """Evaluate system outputs against golden test set using official BTC formulas.
    
    Args:
        predictions: List of dicts matching SubmissionItem format (id, relevant_tables, answer, pandas_query_status).
        gold_data: List of dicts matching Golden format (id, golden_tables, golden_answer).
        error_threshold: Allowed error margin for numeric answers (e.g., 0.05 for 5%).
        
    Returns:
        ContestMetrics object containing official scores.
    """
    total_queries = len(gold_data)
    if total_queries == 0:
        return ContestMetrics(0, 0, 0, 0, 0)
        
    gold_map = {item["id"] if "id" in item else item.get("query_id"): item for item in gold_data}
    
    precision_sum = 0.0
    recall_sum = 0.0
    correct_answers = 0
    correct_executions = 0
    
    for pred in predictions:
        q_id = pred.get("id") or pred.get("query_id")
        if q_id not in gold_map:
            continue
            
        gold = gold_map[q_id]
        
        # 1. Retrieval Metrics (Macro-Average)
        # Bảng dữ liệu đã truy hồi
        pred_tables = set(pred.get("relevant_tables", []))
        # Bảng dữ liệu liên quan (chuẩn)
        gold_tables = set(gold.get("golden_tables", [gold.get("golden_table_id")] if gold.get("golden_table_id") else []))
        
        num_retrieved = len(pred_tables)
        num_relevant = len(gold_tables)
        
        # Số bảng dữ liệu truy hồi đúng
        num_correct = len(pred_tables.intersection(gold_tables))
        
        # Precision cho truy vấn này
        p_q = num_correct / num_retrieved if num_retrieved > 0 else 0.0
        # Recall cho truy vấn này
        r_q = num_correct / num_relevant if num_relevant > 0 else 0.0
        
        precision_sum += p_q
        recall_sum += r_q
        
        # 2. Answer Accuracy (Trong ngưỡng sai số)
        pred_ans = pred.get("answer")
        gold_ans = gold.get("golden_answer")
        
        if pred_ans is not None and gold_ans is not None:
            try:
                pred_val = float(pred_ans)
                gold_val = float(gold_ans)
                
                # Check within threshold
                if gold_val == 0:
                    if pred_val == 0:
                        correct_answers += 1
                else:
                    error = abs(pred_val - gold_val) / abs(gold_val)
                    if error <= error_threshold:
                        correct_answers += 1
            except (ValueError, TypeError):
                pass
                
        # 3. Execution Accuracy
        # (số code chạy được và cho kết quả đúng)
        # Giả định: Trường is_execution_success được gán trong prediction
        is_success = pred.get("is_execution_success", False)
        if is_success:
            correct_executions += 1
            
    # Tính trung bình Macro
    macro_precision = precision_sum / total_queries
    macro_recall = recall_sum / total_queries
    
    # Tính F2
    if macro_precision + macro_recall == 0:
        f2 = 0.0
    else:
        f2 = (5 * macro_precision * macro_recall) / (4 * macro_precision + macro_recall)
        
    answer_acc = correct_answers / total_queries
    exec_acc = correct_executions / total_queries
    
    return ContestMetrics(
        retrieval_precision=macro_precision,
        retrieval_recall=macro_recall,
        retrieval_f2_macro=f2,
        answer_accuracy=answer_acc,
        execution_accuracy=exec_acc
    )
