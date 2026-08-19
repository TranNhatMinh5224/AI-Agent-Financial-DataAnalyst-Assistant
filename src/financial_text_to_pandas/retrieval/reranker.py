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
        # Implement actual CrossEncoder reranker
        from sentence_transformers import CrossEncoder
        print("Loading reranker model BAAI/bge-reranker-m3...")
        # Note: BAAI/bge-reranker-m3 is a large model. 
        # In a real app this should be loaded once globally.
        encoder = CrossEncoder('BAAI/bge-reranker-m3')
        
        # We need the table search_text. Since we only have table_id in Candidate,
        # we might need to load corpus here, or assume the candidate holds enough info.
        # Wait, the search_py doesn't pass search_text into candidates yet.
        # For simplicity, if we don't have it, we'll just mock it or we must load the corpus.
        # Let's load corpus locally to get the texts for reranking.
        from pathlib import Path
        import pandas as pd
        
        # Hardcoding index path for this demo, usually should be passed in.
        corpus_df = pd.read_csv(Path("artifacts/preprocessing/indexes/table_corpus.csv"), encoding="utf-8-sig")
        corpus_dict = dict(zip(corpus_df["table_id"], corpus_df["search_text"]))
        
        pairs = []
        for cand in reranked:
            text = str(corpus_dict.get(cand.table_id, ""))
            pairs.append([question, text])
            
        scores = encoder.predict(pairs)
        for i, cand in enumerate(reranked):
            cand.reranker_score = float(scores[i])
            
    # Sort descending
    reranked.sort(key=lambda x: x.reranker_score, reverse=True)
    reranked = reranked[:top_k]
    
    # Re-rank and wrap in EvidenceTable
    evidence = []
    for rank, cand in enumerate(reranked, 1):
        cand.rank = rank
        evidence.append(EvidenceTable(candidate=cand))
        
    return evidence
