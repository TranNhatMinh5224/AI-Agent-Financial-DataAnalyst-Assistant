"""
multi_hop.py — Multi-hop Reasoning Controller.

Phase 3, Step 9.
"""

from __future__ import annotations

import uuid
from typing import Dict, Any, Tuple
from pathlib import Path

from financial_text_to_pandas.types import EvidencePackage, ReasoningResult, CellGroundingResult, EvidenceTable
from financial_text_to_pandas.retrieval.search import run_search
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
from financial_text_to_pandas.reasoning.strategy import run_pot_strategy


def run_multi_hop(
    question: str, 
    intent: Any, 
    run_config: Any, 
    output_root: Path, 
    llm_config: dict[str, str | float]
) -> Tuple[ReasoningResult, CellGroundingResult, Dict[str, Any], EvidencePackage]:
    """Run iterative multi-hop reasoning by decomposing question into sub-queries.
    
    Returns:
        Tuple of (result, grounding, new_dfs, new_package)
    """
    # 1. Tạo sub-queries (ví dụ: so sánh 2 năm → bóc tách thành từng năm)
    sub_queries = []
    tickers = intent.tickers if hasattr(intent, "tickers") and intent.tickers else ([intent.ticker] if intent.ticker else [])
    ticker_str = ", ".join(tickers)
    
    for year in intent.years:
        for metric in intent.metrics:
            sq = f"{metric} {ticker_str} năm {year}".strip()
            sub_queries.append(sq)
            
    if not sub_queries:
        sub_queries = [question]
        
    # 2. Parallel retrieval (thực thi tuần tự trong bản stub này)
    all_tables: Dict[str, EvidenceTable] = {}
    for sq in sub_queries:
        try:
            # Fallback bm25 if hybrid is not fully setup
            try:
                tables = run_search(sq, run_config, method="hybrid", top_k=20)
            except Exception:
                tables = run_search(sq, run_config, method="bm25", top_k=20, no_reranker=True)
                
            for ev in tables:
                all_tables[ev.candidate.table_id] = ev
        except Exception:
            pass
            
    if not all_tables:
        res = ReasoningResult("multi_hop", None, None, None,
                              "Multi-hop retrieval found no tables.", "I_INSUFFICIENT_EVIDENCE")
        # Dummy package
        pkg = EvidencePackage(str(uuid.uuid4()), question, intent, [], [])
        return res, CellGroundingResult([], "I_INSUFFICIENT_EVIDENCE"), {}, pkg
        
    # 3. Load DataFrames cho tất cả các bảng tìm được
    merged_tables = list(all_tables.values())
    package = EvidencePackage(
        query_id=str(uuid.uuid4()),
        question=question,
        intent=intent,
        tables=merged_tables,
        linked_text_context=[]
    )
    new_dfs = load_evidence_tables(package, output_root)
    
    # 4. Ground cells trên tệp dữ liệu đã gộp
    grounding = ground_cells(intent, new_dfs)
    if grounding.error_type:
        res = ReasoningResult("multi_hop", None, None, None,
                              f"Grounding failed: {grounding.error_type}", grounding.error_type)
        return res, grounding, new_dfs, package
        
    # 5. Chạy PoT Strategy trên bộ cells đã ground từ nhiều nguồn
    result = run_pot_strategy(package, grounding, new_dfs, llm_config)
    result.strategy = "multi_hop"
    
    return result, grounding, new_dfs, package
