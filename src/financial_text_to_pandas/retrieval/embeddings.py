"""
embeddings.py — Dense retrieval and mock embeddings.

Phase 2, Step 5.
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from financial_text_to_pandas.types import Candidate

class EmbeddingStore:
    def __init__(self, df: pd.DataFrame, model_name: str, model_version: str):
        self.df = df
        self.model_name = model_name
        self.model_version = model_version
        
        # Ensure vectors are numpy arrays
        if not self.df.empty and "embedding" in self.df.columns:
            if isinstance(self.df["embedding"].iloc[0], list):
                self.df["embedding"] = self.df["embedding"].apply(np.array)


def _hash_text(text: str) -> str:
    """Generate SHA-256 hash for source text to invalidate cache if text changes."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def embed_tables(
    corpus: pd.DataFrame, 
    output_path: Path, 
    model_name: str = "keepitreal/vietnamese-sbert", 
    model_version: str = "1.0",
    mock: bool = False
) -> EmbeddingStore:
    """Embed corpus tables or load from cache if valid.
    
    Args:
        corpus: The table_corpus.csv DataFrame.
        output_path: Path to save/load table_embeddings.parquet.
        model_name: The embedding model name.
        model_version: The embedding model version.
        mock: If True, generate random embeddings for testing.
        
    Returns:
        EmbeddingStore.
    """
    corpus = corpus.copy()
    # Calculate current hashes
    corpus["current_hash"] = corpus["search_text"].apply(_hash_text)
    
    existing_df = pd.DataFrame()
    if output_path.exists():
        try:
            existing_df = pd.read_parquet(output_path)
            # Check model/version mismatch
            if not existing_df.empty:
                if (existing_df["model_name"].iloc[0] != model_name or 
                    existing_df["model_version"].iloc[0] != model_version):
                    print(f"[WARN] Embedding cache mismatch for {model_name} v{model_version}. Regenerating.")
                    existing_df = pd.DataFrame()
        except Exception:
            existing_df = pd.DataFrame()
            
    # Figure out which ones need embedding
    to_embed = []
    cached_rows = []
    
    if not existing_df.empty:
        existing_dict = existing_df.set_index("table_id").to_dict("index")
        for _, row in corpus.iterrows():
            tid = row["table_id"]
            chash = row["current_hash"]
            if tid in existing_dict and existing_dict[tid]["source_text_checksum"] == chash:
                cached_rows.append(existing_dict[tid])
            else:
                to_embed.append(row)
    else:
        to_embed = corpus.to_dict("records")
        
    if to_embed:
        print(f"[INFO] Generating embeddings for {len(to_embed)} new/changed tables (mock={mock})...")
        new_rows = []
        now = datetime.datetime.now().isoformat()
        
        # Dimensions
        dim = 1536 if "Qwen" in model_name else 768
        
        encoder = None
        if not mock:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model {model_name}...")
            encoder = SentenceTransformer(model_name)
        
        # Extract all texts to embed
        texts = [str(row["search_text"]) for row in to_embed]
        
        if mock:
            embeddings_list = [np.random.rand(dim) for _ in texts]
            embeddings_list = [vec / np.linalg.norm(vec) for vec in embeddings_list]
        else:
            # Batch encoding is much faster
            print(f"Encoding {len(texts)} tables in batches...")
            embeddings_matrix = encoder.encode(texts, batch_size=256, show_progress_bar=True)
            embeddings_list = embeddings_matrix.tolist()
            
        for i, row in enumerate(to_embed):
            vec_list = embeddings_list[i] if not mock else embeddings_list[i].tolist()
            new_rows.append({
                "table_id": row["table_id"],
                "model_name": model_name,
                "model_version": model_version,
                "embedding_dim": len(vec_list),
                "source_text_checksum": row["current_hash"],
                "created_at": now,
                "embedding": vec_list # Parquet saves lists well
            })
            
        cached_rows.extend(new_rows)
        
        # Save updated cache
        final_df = pd.DataFrame(cached_rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_parquet(output_path, index=False)
        return EmbeddingStore(final_df, model_name, model_version)
    
    # All cached
    final_df = existing_df[existing_df["table_id"].isin(corpus["table_id"])].copy()
    return EmbeddingStore(final_df, model_name, model_version)


def embed_query(
    question: str, 
    model_name: str = "keepitreal/vietnamese-sbert", 
    mock: bool = False
) -> np.ndarray:
    """Embed a query.
    
    Args:
        question: The user's query.
        model_name: Must match table embedding model.
        mock: If True, generate random embedding.
    """
    dim = 1536 if "Qwen" in model_name else 768
    if mock:
        vec = np.random.rand(dim)
        vec = vec / np.linalg.norm(vec)
        return vec
    else:
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer(model_name)
        return encoder.encode(question)
        

def search_dense(
    store: EmbeddingStore, 
    query_id: str, 
    query: str, 
    query_vector: np.ndarray, 
    top_k: int = 50,
    filter_ids: Optional[set[str]] = None
) -> List[Candidate]:
    """Search the dense embedding store.
    
    Args:
        store: EmbeddingStore returned by embed_tables.
        query_id: ID of the query.
        query: The raw query text.
        query_vector: Embedded query vector.
        top_k: Max results.
        filter_ids: Optional metadata filter.
    """
    if store.df.empty:
        return []
        
    df = store.df.copy()
    
    if filter_ids is not None:
        df = df[df["table_id"].isin(filter_ids)]
        if df.empty:
            return []
            
    # Calculate cosine similarity (assuming normalized vectors)
    # Using dot product
    embeddings = np.stack(df["embedding"].values)
    scores = np.dot(embeddings, query_vector)
    
    df["dense_score"] = scores
    df = df.sort_values("dense_score", ascending=False).head(top_k)
    
    now = datetime.datetime.now().isoformat()
    candidates = []
    
    for rank, (idx, row) in enumerate(df.iterrows(), 1):
        candidates.append(
            Candidate(
                query_id=query_id,
                question=query,
                table_id=row["table_id"],
                rank=rank,
                bm25_score=0.0,
                dense_score=float(row["dense_score"]),
                reranker_score=0.0,
                retrieval_source="dense",
                csv_path="", # Will be filled by search orchestrator
                metadata_filter_status="pass",
                model_name=store.model_name,
                model_version=store.model_version,
                created_at=now
            )
        )
        
    return candidates
