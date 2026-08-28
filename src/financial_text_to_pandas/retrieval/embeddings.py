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
from tqdm import tqdm

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
    model_name: str = "Alibaba-NLP/gte-Qwen2-7B-instruct", 
    model_version: str = "1.0",
    mock: bool = False,
    batch_size: int = 16
) -> EmbeddingStore:
    """Embed corpus tables or load from cache if valid.
    
    Args:
        corpus: The table_corpus.csv DataFrame.
        output_path: Path to save/load table_embeddings.parquet.
        model_name: The embedding model name.
        model_version: The embedding model version.
        mock: If True, generate random embeddings for testing.
        batch_size: Batch size for model inference.
        
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
        
        dim = 768
        if "Qwen" in model_name or "gte" in model_name.lower():
            dim = 3584 # gte-Qwen2-7B uses 3584 dim, Qwen3 varies
        elif "bge-m3" in model_name.lower():
            dim = 1024
            
        if not mock:
            print(f"[INFO] Loading SentenceTransformer model: {model_name}...")
            try:
                from sentence_transformers import SentenceTransformer
                import torch
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"[INFO] Using device: {device}")
                
                model = SentenceTransformer(model_name, trust_remote_code=True)
                model.to(device)
            except ImportError:
                print("[ERROR] sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
        
        # Batch processing
        for i in tqdm(range(0, len(to_embed), batch_size), desc="Embedding tables"):
            batch = to_embed[i:i + batch_size]
            texts = [str(row["search_text"]) for row in batch]
            
            if mock:
                vecs = []
                for _ in batch:
                    vec = np.random.rand(dim)
                    vec = vec / np.linalg.norm(vec)
                    vecs.append(vec)
            else:
                with torch.no_grad():
                    # Generate embeddings and normalize
                    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
                    vecs = [vec for vec in embeddings]
                    dim = len(vecs[0]) # Update dim based on actual model output
                
            for row, vec in zip(batch, vecs):
                new_rows.append({
                    "table_id": row["table_id"],
                    "model_name": model_name,
                    "model_version": model_version,
                    "embedding_dim": dim,
                    "source_text_checksum": row["current_hash"],
                    "created_at": now,
                    "embedding": vec.tolist() # Parquet saves lists well
                })
            
            # Auto-save every 1000 records to prevent data loss
            if (i + batch_size) % 1000 < batch_size and i > 0:
                temp_df = pd.DataFrame(cached_rows + new_rows)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temp_df.to_parquet(output_path, index=False)
                
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
    model_name: str = "Alibaba-NLP/gte-Qwen2-7B-instruct", 
    mock: bool = False
) -> np.ndarray:
    """Embed a query.
    
    Args:
        question: The user's query.
        model_name: Must match table embedding model.
        mock: If True, generate random embedding.
    """
    dim = 3584 if "gte-Qwen" in model_name else 768
    if mock:
        vec = np.random.rand(dim)
        vec = vec / np.linalg.norm(vec)
        return vec
    else:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = SentenceTransformer(model_name, trust_remote_code=True)
            model.to(device)
            
            with torch.no_grad():
                vec = model.encode(question, normalize_embeddings=True)
                return vec
        except ImportError:
            print("[ERROR] sentence-transformers not installed. Returning zeros.")
            return np.zeros(dim)

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
