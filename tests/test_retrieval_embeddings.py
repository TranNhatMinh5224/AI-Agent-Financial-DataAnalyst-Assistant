"""
tests/test_retrieval_embeddings.py — Tests for dense embeddings and caching.
"""

from financial_text_to_pandas.retrieval.embeddings import embed_tables, embed_query, search_dense, _hash_text
import pandas as pd
from pathlib import Path

def test_embed_tables_mock(tmp_path):
    corpus = pd.DataFrame([
        {"table_id": "T1", "search_text": "text 1"},
        {"table_id": "T2", "search_text": "text 2"},
    ])
    
    out_path = tmp_path / "table_embeddings.parquet"
    store = embed_tables(corpus, out_path, mock=True)
    
    assert not store.df.empty
    assert "embedding" in store.df.columns
    assert len(store.df) == 2
    
    # Check dimensions
    assert len(store.df.iloc[0]["embedding"]) == 1536 # Default is Qwen (1536)

def test_embedding_cache_invalidation(tmp_path):
    corpus = pd.DataFrame([
        {"table_id": "T1", "search_text": "text 1"},
    ])
    out_path = tmp_path / "table_embeddings.parquet"
    
    # First run
    store1 = embed_tables(corpus, out_path, mock=True)
    hash1 = store1.df.iloc[0]["source_text_checksum"]
    
    # Second run with same text
    store2 = embed_tables(corpus, out_path, mock=True)
    hash2 = store2.df.iloc[0]["source_text_checksum"]
    assert hash1 == hash2 # Should hit cache
    
    # Third run with changed text
    corpus.loc[0, "search_text"] = "text 1 changed"
    store3 = embed_tables(corpus, out_path, mock=True)
    hash3 = store3.df.iloc[0]["source_text_checksum"]
    assert hash1 != hash3 # Cache invalidated
    
def test_search_dense():
    corpus = pd.DataFrame([
        {"table_id": "T1", "search_text": "text 1"},
        {"table_id": "T2", "search_text": "text 2"},
    ])
    # Store
    import numpy as np
    from financial_text_to_pandas.retrieval.embeddings import EmbeddingStore
    
    # Fake embeddings
    vec1 = np.array([1.0, 0.0])
    vec2 = np.array([0.0, 1.0])
    
    df = pd.DataFrame([
        {"table_id": "T1", "embedding": vec1},
        {"table_id": "T2", "embedding": vec2},
    ])
    store = EmbeddingStore(df, "mock", "1.0")
    
    # Search
    query_vec = np.array([1.0, 0.0])
    cands = search_dense(store, "q1", "query", query_vec, top_k=10)
    
    assert len(cands) == 2
    assert cands[0].table_id == "T1"
    assert cands[0].dense_score == 1.0
    assert cands[1].table_id == "T2"
    assert cands[1].dense_score == 0.0
