"""
evaluator.py — Generate evaluation reports.
"""

from __future__ import annotations

import csv
from pathlib import Path
from financial_text_to_pandas.evaluation.golden import load_golden_questions
from financial_text_to_pandas.evaluation.metrics import calculate_exact_numeric_accuracy
from financial_text_to_pandas.reasoning.answer import run_reasoning_pipeline
from financial_text_to_pandas.types import Candidate, EvidenceTable

def run_qa_evaluation(eval_root: Path, output_root: Path):
    """Run QA evaluation and write to qa_eval.csv"""
    questions = load_golden_questions(eval_root)
    
    out_path = eval_root / "qa_eval.csv"
    
    with open(out_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "predicted_answer", "expected_answer", 
            "exact_numeric_accuracy", "verification_status", "error_type"
        ])
        
        for q in questions:
            # Mock candidate tables based on some logic (or oracle).
            # In a real run, this would call Retrieval first.
            # Here we just want to test the pipeline flow.
            
            # Use empty tables so it fails or mock specific ones
            tables = [] 
            
            # Since this is evaluator, we need llm config. Let's mock it empty
            # In a real evaluation script, you would load the config.
            llm_config = {}
            ans = run_reasoning_pipeline(q.question, tables, output_root, llm_config)
            
            acc = calculate_exact_numeric_accuracy(ans.answer, q.expected_answer) if q.expected_answer is not None else False
            
            writer.writerow([
                q.query_id,
                ans.answer,
                q.expected_answer,
                "True" if acc else "False",
                ans.verification_status,
                ans.error_type
            ])
            
    print(f"Generated {out_path}")
