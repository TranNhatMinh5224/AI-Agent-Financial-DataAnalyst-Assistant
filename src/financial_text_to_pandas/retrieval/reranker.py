"""
reranker.py — Reranker interface for Candidate tables.

Phase 2, Step 7.
"""

from __future__ import annotations

import random
from typing import List

from financial_text_to_pandas.types import Candidate, EvidenceTable


def rerank_candidates(
    question: str, 
    candidates: List[Candidate], 
    top_k: int = 10,
    mock: bool = False
) -> List[EvidenceTable]:
    """Rerank candidates using a cross-encoder or a mock for testing.
    
    Args:
        question: The user's query.
        candidates: List of Candidate objects from retriever.
        top_k: Max final tables to return.
        mock: If True, assign random reranker scores.
        
    Returns:
        List of EvidenceTable objects sorted by reranker_score.
    """
    if not candidates:
        return []
        
    # Copy candidates to avoid mutating the originals directly if passed by ref
    reranked = list(candidates)
    
    if mock:
        # Give higher BM25/dense score candidates a slight bias in mock to simulate reality
        for cand in reranked:
            base_score = max(cand.bm25_score, cand.dense_score)
            cand.reranker_score = base_score * 0.1 + random.random()
    else:
        # TODO: Implement actual CrossEncoder reranker
        for cand in reranked:
            # Fallback to sum of retrieved scores if no reranker
            cand.reranker_score = cand.bm25_score + cand.dense_score
            
    # Sort descending
    reranked.sort(key=lambda x: x.reranker_score, reverse=True)
    reranked = reranked[:top_k]
    
    # Re-rank and wrap in EvidenceTable
    evidence = []
    for rank, cand in enumerate(reranked, 1):
        cand.rank = rank
        evidence.append(EvidenceTable(candidate=cand))
        
    return evidence
