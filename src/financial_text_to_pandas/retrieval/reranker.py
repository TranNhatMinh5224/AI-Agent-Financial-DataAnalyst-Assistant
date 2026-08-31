"""
reranker.py — Reranker interface for Candidate tables with Cloud API and RRF Fallback.

Phase 2, Step 7.
"""

from __future__ import annotations

import json
import random
import urllib.request
from typing import List, Optional
import pandas as pd
from pathlib import Path

from financial_text_to_pandas.types import Candidate, EvidenceTable
from financial_text_to_pandas.config import settings

# Lazy load reranker model for optional local use
_RERANKER_MODEL = None


def _call_api_reranker(
    query: str,
    documents: List[str],
    model_name: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[List[float]]:
    """Call Cloud Rerank API (e.g. SiliconFlow, Cohere, Jina)."""
    api_key = api_key or settings.RERANKER_API_KEY
    base_url = (base_url or settings.RERANKER_BASE_URL).rstrip("/")
    if not api_key:
        return None
    url = f"{base_url}/rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Clean doc texts (truncate if very long to prevent token overflow)
    clean_docs = [d[:1500] if d.strip() else "Báo cáo tài chính" for d in documents]
    payload = {
        "model": model_name,
        "query": query,
        "documents": clean_docs
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            results = res.get("results", [])
            scores = [0.0] * len(documents)
            for item in results:
                idx = item.get("index", 0)
                if idx < len(scores):
                    scores[idx] = float(item.get("relevance_score", 0.0))
            return scores
    except Exception as e:
        print(f"[WARN] Cloud Rerank API ({model_name}) call failed: {e}. Falling back to Reciprocal Rank Fusion (RRF).")
        return None


def get_reranker(model_name: str = "BAAI/bge-reranker-v2-m3"):
    """Singleton pattern to load CrossEncoder once locally if needed."""
    global _RERANKER_MODEL
    if not model_name:
        return None
    if _RERANKER_MODEL is None:
        try:
            from sentence_transformers import CrossEncoder
            print(f"[INFO] Loading Local Cross-Encoder Reranker: {model_name}...")
            _RERANKER_MODEL = CrossEncoder(model_name)
        except Exception:
            return None
    return _RERANKER_MODEL


def rerank_candidates(
    question: str, 
    candidates: List[Candidate], 
    corpus_df: pd.DataFrame = None,
    top_k: int = 10,
    mock: bool = False,
    model_name: str = "Qwen/Qwen3-Reranker-8B",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> List[EvidenceTable]:
    """Rerank candidates using Cloud API, local cross-encoder, or RRF.
    
    Args:
        question: The user's query.
        candidates: List of Candidate objects from retriever.
        corpus_df: DataFrame containing the actual 'search_text' to feed the reranker.
        top_k: Max final tables to return.
        mock: If True, assign random reranker scores.
        model_name: Model identifier for Cloud API or local CrossEncoder.
        base_url: Reranker API Base URL.
        api_key: Reranker API Key.
        
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
        # Extract document texts
        doc_texts = []
        if corpus_df is not None and not corpus_df.empty:
            doc_map = dict(zip(corpus_df["table_id"], corpus_df["search_text"]))
            doc_texts = [str(doc_map.get(cand.table_id, cand.csv_path or "")) for cand in reranked]
        else:
            doc_texts = [cand.csv_path or "" for cand in reranked]

        # 1. Check if RRF is explicitly chosen or API key is missing
        use_rrf = (model_name or "").lower() in ("rrf", "reciprocal_rank_fusion", "none", "fusion") or not api_key
        api_scores = None
        if not use_rrf:
            api_scores = _call_api_reranker(
                question, doc_texts, model_name=model_name, base_url=base_url, api_key=api_key
            )
        
        if api_scores is not None and len(api_scores) == len(reranked):
            for cand, score in zip(reranked, api_scores):
                cand.reranker_score = score
        else:
            # 2. Reciprocal Rank Fusion (RRF) Fallback / Standard
            bm25_sorted = sorted(reranked, key=lambda x: x.bm25_score, reverse=True)
            dense_sorted = sorted(reranked, key=lambda x: x.dense_score, reverse=True)
            bm25_rank = {cand.table_id: i for i, cand in enumerate(bm25_sorted)}
            dense_rank = {cand.table_id: i for i, cand in enumerate(dense_sorted)}
            
            for cand in reranked:
                r_bm = bm25_rank.get(cand.table_id, 999)
                r_de = dense_rank.get(cand.table_id, 999)
                cand.reranker_score = (1.0 / (60.0 + r_bm)) + (1.0 / (60.0 + r_de))
            
    # Sort descending
    reranked.sort(key=lambda x: x.reranker_score, reverse=True)
    reranked = reranked[:top_k]
    
    # Wrap in EvidenceTable
    evidence = []
    for rank, cand in enumerate(reranked, 1):
        cand.rank = rank
        evidence.append(EvidenceTable(candidate=cand))
        
    return evidence
