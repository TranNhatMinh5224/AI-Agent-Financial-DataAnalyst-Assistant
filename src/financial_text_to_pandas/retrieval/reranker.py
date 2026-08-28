"""
reranker.py — Reranker interface for Candidate tables.

Phase 2, Step 7.
"""

from __future__ import annotations

import random
from typing import List
import pandas as pd
from pathlib import Path

from financial_text_to_pandas.types import Candidate, EvidenceTable

# Lazy load reranker model to save memory if not used
_RERANKER_MODEL = None


def get_reranker(model_name: str = "BAAI/bge-reranker-v2-m3"):
    """Singleton pattern to load CrossEncoder once."""
    global _RERANKER_MODEL
    if _RERANKER_MODEL is None:
        try:
            from sentence_transformers import CrossEncoder
            print(f"[INFO] Loading Cross-Encoder Reranker: {model_name}...")
            _RERANKER_MODEL = CrossEncoder(model_name)
        except ImportError:
            print("[WARN] sentence_transformers not installed. Reranker will fallback to sum.")
            return None
    return _RERANKER_MODEL


def rerank_candidates(
    question: str, 
    candidates: List[Candidate], 
    corpus_df: pd.DataFrame = None,
    top_k: int = 10,
    mock: bool = False
) -> List[EvidenceTable]:
    """Rerank candidates using a cross-encoder or a mock for testing.
    
    Args:
        question: The user's query.
        candidates: List of Candidate objects from retriever.
        corpus_df: DataFrame containing the actual 'search_text' to feed the reranker.
        top_k: Max final tables to return.
        mock: If True, assign random reranker scores.
        
    Returns:
        List of EvidenceTable objects sorted by reranker_score.
    """
    if not candidates:
        return []
        
    reranked = list(candidates)
    
    if mock:
        for cand in reranked:
            base_score = max(cand.bm25_score, cand.dense_score)
            cand.reranker_score = base_score * 0.1 + random.random()
    else:
        # Actual CrossEncoder logic
        reranker = get_reranker()
        if reranker is not None and corpus_df is not None:
            # Prepare pairs (question, document)
            pairs = []
            for cand in reranked:
                # Find document text in corpus
                doc_row = corpus_df[corpus_df["table_id"] == cand.table_id]
                if not doc_row.empty:
                    doc_text = str(doc_row.iloc[0]["search_text"])
                else:
                    doc_text = ""
                pairs.append((question, doc_text))
                
            # Predict semantic relevance scores
            scores = reranker.predict(pairs)
            for cand, score in zip(reranked, scores):
                cand.reranker_score = float(score)
        else:
            # Fallback to sum of retrieved scores if no reranker or missing corpus
            for cand in reranked:
                cand.reranker_score = cand.bm25_score + cand.dense_score
            
    # Sort descending
    reranked.sort(key=lambda x: x.reranker_score, reverse=True)
    reranked = reranked[:top_k]
    
    # Wrap in EvidenceTable
    evidence = []
    for rank, cand in enumerate(reranked, 1):
        cand.rank = rank
        evidence.append(EvidenceTable(candidate=cand))
        
    return evidence
