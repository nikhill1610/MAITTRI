"""
Shared Pytest Configuration and Fixtures for MAITTRI Backend Test Suite.
"""

import sys
import pytest
from unittest.mock import MagicMock


def create_mock_chroma_collection(chunk_count: int = 150):
    """
    Creates a properly contracted mock ChromaDB collection.
    Guarantees:
    - collection.count() returns an int
    - collection.query(...) returns standard dict structure
    - collection.get(...) returns standard dict structure
    """
    mock_coll = MagicMock()
    mock_coll.count.return_value = chunk_count
    mock_coll.query.return_value = {
        "documents": [["Sample agricultural advisory text"]],
        "metadatas": [[{
            "title": "Wheat Production Guide",
            "section": "Irrigation Management",
            "section_type": "Irrigation",
            "source": "ICAR-IIWBR",
            "source_type": "curated_reference",
            "url": "https://iiwbr.icar.gov.in",
            "version": "2024.1",
            "category": "Irrigation",
            "crop": "Wheat",
            "page_number": 1
        }]],
        "distances": [[0.15]]
    }
    mock_coll.get.return_value = {
        "ids": ["chunk_1"],
        "documents": ["Sample agricultural advisory text"],
        "metadatas": [{
            "title": "Wheat Production Guide",
            "section": "Irrigation Management",
            "section_type": "Irrigation",
            "source": "ICAR-IIWBR",
            "source_type": "curated_reference",
            "url": "https://iiwbr.icar.gov.in",
            "version": "2024.1",
            "category": "Irrigation",
            "crop": "Wheat",
            "page_number": 1
        }]
    }
    return mock_coll


@pytest.fixture(autouse=True)
def ensure_clean_chroma_state():
    """
    Autouse fixture to prevent mock leakage across test files.
    If a test mocked chromadb or rag_service._COLLECTION, ensure
    the collection contract is intact and reset any broken state.
    """
    yield

    try:
        import app.services.rag_service as rs
        if rs._COLLECTION is not None and isinstance(rs._COLLECTION, MagicMock):
            if not isinstance(rs._COLLECTION.count.return_value, int):
                rs._COLLECTION.count.return_value = 0
            if not isinstance(rs._COLLECTION.query.return_value, dict):
                rs._COLLECTION.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    except Exception:
        pass
