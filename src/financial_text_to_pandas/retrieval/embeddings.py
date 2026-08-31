import json
import urllib.request
import datetime
import hashlib
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

from financial_text_to_pandas.types import Candidate
from financial_text_to_pandas.config import settings

_EMBEDDING_MODEL = None  # Singleton for local SentenceTransformer


def _call_api_embeddings(
    texts: list[str], 
    model_name: str, 
    base_url: Optional[str] = None, 
    api_key: Optional[str] = None
) -> Optional[list[list[float]]]:
    """Call OpenRouter or OpenAI-compatible embeddings endpoint using central settings."""
    api_key = api_key or settings.OPENROUTER_API_KEY
    base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
    if not api_key:
        return None
    url = f"{base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    model = model_name.lower() if "bge-m3" in model_name.lower() else model_name
    # Handle empty or whitespace strings
    clean_texts = [t if t.strip() else "table" for t in texts]
    data = json.dumps({"model": model, "input": clean_texts}).encode("utf-8")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return [item["embedding"] for item in res["data"]]
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(2 * attempt)
            else:
                print(f"[WARN] Embedding API call failed after {max_attempts} attempts: {e}. Falling back to local SentenceTransformer.")
                return None


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
    model_name: str = "baai/bge-m3", 
    model_version: str = "1.0",
    mock: bool = False,
    batch_size: int = 32,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> EmbeddingStore:
    """Embed corpus tables or load from cache if valid.
    
    Args:
        corpus: The table_corpus.csv DataFrame.
        output_path: Path to save/load table_embeddings.parquet.
        model_name: The embedding model name.
        model_version: The embedding model version.
        mock: If True, generate random embeddings for testing.
        batch_size: Batch size for model inference.
        base_url: Base URL for Embeddings API (optional).
        api_key: API Key for Embeddings API (optional).
        
    Returns:
        EmbeddingStore.
    """
    corpus = corpus.copy()
    corpus["current_hash"] = corpus["search_text"].apply(_hash_text)
    
    existing_df = pd.DataFrame()
    if output_path.exists():
        try:
            existing_df = pd.read_parquet(output_path)
            if not existing_df.empty:
                if (existing_df["model_name"].iloc[0] != model_name or 
                    existing_df["model_version"].iloc[0] != model_version):
                    print(f"[WARN] Embedding cache mismatch for {model_name} v{model_version}. Regenerating.")
                    existing_df = pd.DataFrame()
        except Exception:
            existing_df = pd.DataFrame()
            
    to_embed = []
    cached_rows = []
    
    if not existing_df.empty:
        existing_df = existing_df.drop_duplicates(subset=["table_id"], keep="last")
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
        print(f"[INFO] Generating embeddings for {len(to_embed)} tables via API/Model (mock={mock})...")
        new_rows = []
        now = datetime.datetime.now().isoformat()
        
        dim = 1024 if "bge-m3" in model_name.lower() else 768
        
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
                # 1. Try OpenRouter / Cloud API first
                api_vecs = _call_api_embeddings(texts, model_name=model_name, base_url=base_url, api_key=api_key)
                if api_vecs is not None:
                    vecs = [np.array(v) for v in api_vecs]
                    dim = len(vecs[0])
                else:
                    # 2. Local fallback
                    try:
                        from sentence_transformers import SentenceTransformer
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                        global _EMBEDDING_MODEL
                        if _EMBEDDING_MODEL is None:
                            _EMBEDDING_MODEL = SentenceTransformer(model_name, trust_remote_code=True)
                            _EMBEDDING_MODEL.to(device)
                        model = _EMBEDDING_MODEL
                        with torch.no_grad():
                            embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
                            vecs = [vec for vec in embeddings]
                            dim = len(vecs[0])
                    except Exception as e:
                        print(f"[ERROR] Could not generate embeddings: {e}")
                        vecs = [np.zeros(dim) for _ in batch]
                
            for row, vec in zip(batch, vecs):
                new_rows.append({
                    "table_id": row["table_id"],
                    "model_name": model_name,
                    "model_version": model_version,
                    "embedding_dim": dim,
                    "source_text_checksum": row["current_hash"],
                    "created_at": now,
                    "embedding": vec.tolist() if hasattr(vec, "tolist") else list(vec)
                })
            
            if (i + batch_size) % 1000 < batch_size and i > 0:
                temp_df = pd.DataFrame(cached_rows + new_rows)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temp_df.to_parquet(output_path, index=False)
                
        cached_rows.extend(new_rows)
        final_df = pd.DataFrame(cached_rows)
        final_df = final_df.drop_duplicates(subset=["table_id"], keep="last")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_parquet(output_path, index=False)
        return EmbeddingStore(final_df, model_name, model_version)
    
    final_df = existing_df[existing_df["table_id"].isin(corpus["table_id"])].copy()
    return EmbeddingStore(final_df, model_name, model_version)


def embed_query(
    question: str, 
    model_name: str = "baai/bge-m3", 
    mock: bool = False,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> np.ndarray:
    """Embed a query using API or local SentenceTransformer."""
    dim = 1024 if "bge-m3" in model_name.lower() else 768
    if mock:
        vec = np.random.rand(dim)
        return vec / np.linalg.norm(vec)
        
    # 1. Try API first
    api_res = _call_api_embeddings([question], model_name=model_name, base_url=base_url, api_key=api_key)
    if api_res is not None and len(api_res) > 0:
        return np.array(api_res[0])
        
    # 2. Local fallback
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        global _EMBEDDING_MODEL
        if _EMBEDDING_MODEL is None:
            _EMBEDDING_MODEL = SentenceTransformer(model_name, trust_remote_code=True)
            _EMBEDDING_MODEL.to(device)
        model = _EMBEDDING_MODEL
        with torch.no_grad():
            return model.encode(question, normalize_embeddings=True)
    except Exception as e:
        print(f"[WARN] Local embedding failed: {e}. Returning zeros.")
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
