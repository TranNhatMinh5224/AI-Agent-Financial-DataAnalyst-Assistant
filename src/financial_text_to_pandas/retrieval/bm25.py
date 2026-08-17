"""
bm25.py — BM25 index builder and searcher.

Phase 2, Step 4.
"""

from __future__ import annotations

import math
import pickle
from collections import Counter
from pathlib import Path
from typing import Any, List, Dict

import pandas as pd

from financial_text_to_pandas.types import Candidate


class BasicBM25:
    """A basic BM25 implementation."""
    
    def __init__(self, corpus_ids: List[str], corpus_texts: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_ids = corpus_ids
        
        self.doc_len = []
        self.doc_freqs = []
        self.idf = {}
        self.nd = len(corpus_ids)
        
        doc_freqs_all = Counter()
        
        for text in corpus_texts:
            tokens = self._tokenize(text)
            self.doc_len.append(len(tokens))
            freq = Counter(tokens)
            self.doc_freqs.append(freq)
            
            for token in freq.keys():
                doc_freqs_all[token] += 1
                
        self.avgdl = sum(self.doc_len) / self.nd if self.nd else 0
        
        # Calculate IDF
        for word, freq in doc_freqs_all.items():
            # BM25 IDF formulation
            idf = math.log(1 + (self.nd - freq + 0.5) / (freq + 0.5))
            self.idf[word] = idf
            
    def _tokenize(self, text: str) -> List[str]:
        # Simple whitespace and punctuation tokenization for Vietnamese
        text = str(text).lower()
        import re
        tokens = re.findall(r"\w+", text)
        return tokens
        
    def get_scores(self, query: str) -> List[float]:
        tokens = self._tokenize(query)
        scores = [0.0] * self.nd
        
        for token in tokens:
            if token not in self.idf:
                continue
            
            q_idf = self.idf[token]
            for i in range(self.nd):
                freq = self.doc_freqs[i].get(token, 0)
                if freq == 0:
                    continue
                    
                dl = self.doc_len[i]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[i] += q_idf * (numerator / denominator)
                
        return scores


def build_bm25_index(corpus: pd.DataFrame, output_path: Path) -> None:
    """Build and save a BM25 index from the corpus search_text.
    
    Args:
        corpus: The table_corpus.csv DataFrame.
        output_path: Where to save the bm25_index.pkl file.
    """
    ids = corpus["table_id"].tolist()
    texts = corpus["search_text"].fillna("").tolist()
    
    bm25 = BasicBM25(corpus_ids=ids, corpus_texts=texts)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        pickle.dump(bm25, f)


def search_bm25(index_path: Path, query_id: str, query: str, top_k: int = 50, filter_ids: set[str] | None = None) -> List[Candidate]:
    """Search the BM25 index.
    
    Args:
        index_path: Path to bm25_index.pkl.
        query_id: ID of the query.
        query: The user's question.
        top_k: Number of candidates to return.
        filter_ids: Optional set of table_ids to restrict search to (metadata filtering).
        
    Returns:
        List of Candidate objects.
    """
    if not index_path.exists():
        return []
        
    with index_path.open("rb") as f:
        bm25: BasicBM25 = pickle.load(f)
        
    scores = bm25.get_scores(query)
    
    # Sort and create candidates
    results = []
    for i, score in enumerate(scores):
        if score <= 0:
            continue
            
        table_id = bm25.corpus_ids[i]
        
        # Apply metadata filter if provided
        if filter_ids is not None and table_id not in filter_ids:
            continue
            
        results.append((score, table_id))
        
    results.sort(key=lambda x: x[0], reverse=True)
    results = results[:top_k]
    
    import datetime
    now = datetime.datetime.now().isoformat()
    
    candidates = []
    for rank, (score, table_id) in enumerate(results, 1):
        candidates.append(
            Candidate(
                query_id=query_id,
                question=query,
                table_id=table_id,
                rank=rank,
                bm25_score=score,
                dense_score=0.0,
                reranker_score=0.0,
                retrieval_source="bm25",
                csv_path="", # Will be filled by search orchestrator
                metadata_filter_status="pass",
                model_name="bm25",
                model_version="1.0",
                created_at=now
            )
        )
        
    return candidates
