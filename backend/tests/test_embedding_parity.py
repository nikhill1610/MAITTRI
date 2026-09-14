"""
test_embedding_parity.py
-------------------------
Verifies embedding parity between runtime all-MiniLM-L6-v2 embedding model
and the 384-dimensional vectors stored in Supabase PostgreSQL pgvector.
"""

import os
import pytest
from app.services.rag_service import (
    get_embedding_function,
    compute_query_embedding,
    query_knowledge_base_pgvector
)


def test_embedding_model_dimensions():
    """Verify runtime embedding produces 384-dimensional float vectors."""
    text_sample = "Wheat crop requires irrigation at Crown Root Initiation (CRI) stage."
    embedding = compute_query_embedding(text_sample)
    
    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(val, float) for val in embedding)


def test_embedding_model_singleton():
    """Verify that get_embedding_function returns the exact same singleton instance."""
    fn1 = get_embedding_function()
    fn2 = get_embedding_function()
    assert fn1 is fn2


def test_pgvector_similarity_retrieval():
    """Verify that computed embedding retrieves matching knowledge chunks from pgvector."""
    db_url = os.getenv("DATABASE_URL", "")
    if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
        pytest.skip("Supabase PostgreSQL pgvector not configured in current environment")

    # Query for known agronomic term
    query_text = "Wheat CRI irrigation timing and urea fertilizer"
    results = query_knowledge_base_pgvector(query_text, top_k=3, match_threshold=0.20)
    
    assert results is not None
    assert len(results) > 0
    top_chunk = results[0]
    assert "content" in top_chunk
    assert "similarity" in top_chunk
    assert float(top_chunk["similarity"]) >= 0.20
