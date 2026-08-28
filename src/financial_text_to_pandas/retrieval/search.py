"""
search.py — Main orchestrator for Phase 2 Table Retrieval.

Phase 2, Step 6.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd

from financial_text_to_pandas.config import RunConfig, load_config
from financial_text_to_pandas.types import Candidate, EvidenceTable
from financial_text_to_pandas.retrieval.query_hints import extract_query_hints, filter_by_metadata
from financial_text_to_pandas.retrieval.bm25 import search_bm25
from financial_text_to_pandas.retrieval.embeddings import embed_tables, embed_query, search_dense, _hash_text
from financial_text_to_pandas.retrieval.reranker import rerank_candidates


def merge_candidates(candidates_lists: List[List[Candidate]]) -> List[Candidate]:
    """Merge and deduplicate multiple lists of candidates.
    
    Highest scores are preserved.
    """
    merged: Dict[str, Candidate] = {}
    
    for c_list in candidates_lists:
        for cand in c_list:
            tid = cand.table_id
            if tid not in merged:
                merged[tid] = cand
            else:
                # Merge scores and sources
                existing = merged[tid]
                existing.bm25_score = max(existing.bm25_score, cand.bm25_score)
                existing.dense_score = max(existing.dense_score, cand.dense_score)
                if cand.retrieval_source not in existing.retrieval_source:
                    existing.retrieval_source += f"+{cand.retrieval_source}"
                    
    # Return as list, sorted arbitrarily (will be reranked anyway)
    return list(merged.values())


def run_search(
    query: str,
    cfg: RunConfig,
    method: str = "hybrid",
    top_k: int = 10,
    mock_embeddings: bool = False,
    no_reranker: bool = False
) -> List[EvidenceTable]:
    """Run the complete retrieval pipeline for a single query.
    
    Args:
        query: User's question.
        cfg: Run configuration.
        method: "bm25", "dense", or "hybrid".
        top_k: Final number of evidence tables.
        mock_embeddings: Use random embeddings.
        no_reranker: Skip reranker scoring.
        
    Returns:
        List of EvidenceTable.
    """
    output_root = cfg.output_root
    if not output_root.is_absolute():
        output_root = Path.cwd() / output_root
        
    index_root = output_root / "indexes"
    corpus_path = index_root / "table_corpus.csv"
    bm25_path = index_root / "bm25_index.pkl"
    dense_path = index_root / "table_embeddings.parquet"
    
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found at {corpus_path}. Run corpus.py first.")
        
    corpus_df = pd.read_csv(corpus_path, encoding="utf-8-sig")
    
    # 1. Query Hints & Filtering
    hints = extract_query_hints(query)
    filtered_corpus = filter_by_metadata(corpus_df, hints)
    filter_ids = set(filtered_corpus["table_id"].tolist())
    
    all_candidates: List[List[Candidate]] = []
    
    # 2. BM25
    if method in ["bm25", "hybrid"]:
        if not bm25_path.exists():
            print(f"[WARN] BM25 index not found at {bm25_path}", file=sys.stderr)
        else:
            bm25_cands = search_bm25(bm25_path, hints.query_id, query, top_k=50, filter_ids=filter_ids)
            all_candidates.append(bm25_cands)
            
    if method in ["dense", "hybrid"]:
        from financial_text_to_pandas.retrieval.embeddings import embed_tables
        emb_model = cfg.embedding_config.get("model_name", "Alibaba-NLP/gte-Qwen2-7B-instruct")
        emb_batch = cfg.embedding_config.get("batch_size", 16)
        store = embed_tables(corpus_df, dense_path, model_name=emb_model, mock=mock_embeddings, batch_size=emb_batch)
        q_vec = embed_query(query, model_name=emb_model, mock=mock_embeddings)
        dense_cands = search_dense(store, hints.query_id, query, q_vec, top_k=50, filter_ids=filter_ids)
        all_candidates.append(dense_cands)
        
    # 4. Merge
    merged = merge_candidates(all_candidates)
    
    # Fill csv paths
    path_map = dict(zip(corpus_df["table_id"], corpus_df["csv_path"]))
    for c in merged:
        c.csv_path = str(path_map.get(c.table_id, ""))
        
    # 5. Rerank
    reranker_model = cfg.reranker_config.get("model_name", "BAAI/bge-reranker-v2-m3")
    evidence = rerank_candidates(query, merged, top_k=top_k, mock=not no_reranker, model_name=reranker_model)
    
    return evidence


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Retrieval Search CLI")
    parser.add_argument("--config", type=Path, default=Path("config/run_profile.yaml"))
    parser.add_argument("--query", type=str, required=True, help="Question to answer")
    parser.add_argument("--method", type=str, choices=["bm25", "dense", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--mock-embeddings", action="store_true")
    parser.add_argument("--no-reranker", action="store_true")
    
    args = parser.parse_args()
    
    cfg = load_config(args.config)
    
    print(f"Query: {args.query}")
    print(f"Method: {args.method}")
    print("-" * 50)
    
    try:
        evidence = run_search(
            query=args.query,
            cfg=cfg,
            method=args.method,
            top_k=args.top_k,
            mock_embeddings=args.mock_embeddings,
            no_reranker=args.no_reranker
        )
        
        for i, ev in enumerate(evidence, 1):
            c = ev.candidate
            print(f"{i}. {c.table_id} (BM25: {c.bm25_score:.3f}, Dense: {c.dense_score:.3f}, Rerank: {c.reranker_score:.3f})")
            print(f"   Path: {c.csv_path}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
