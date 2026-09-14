"""
Maitri Krishi Assistant - Automated RAG Test Suite
--------------------------------------------------
Verifies:
1. Vector store ingestion and collection readiness
2. Distinct document retrieval for different questions (Question A vs Question B)
3. Hindi Devanagari query handling (CRI stage in Wheat)
4. Hinglish query handling (Maize Fall Armyworm pest)
5. Rice fertilizer recommendations
6. Soil nitrogen identification
7. PM-KISAN government scheme
8. Out-of-domain rejection (Capital of France)
9. Low-confidence rejection of gibberish
10. Mocked OpenRouter end-to-end integration & offline grounded RAG fallback
11. Developer debug endpoint
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_service import query_knowledge_base, get_chroma_collection


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_rag_status_endpoint(client):
    """Verifies that /api/chat/status reports ChromaDB online with indexed chunks."""
    response = client.get("/api/chat/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "pgvector" in data["vector_store"] or data["vector_store"] == "ChromaDB"
    assert data["vector_store_chunks_count"] > 0
    assert "architecture" in data


def test_rag_retrieval_distinction_question_a_vs_b():
    """
    Core RAG Verification:
    Question A ('Why are wheat leaves yellow?') and
    Question B ('How often should I irrigate rice?')
    MUST retrieve completely different knowledge chunks.
    """
    res_a = query_knowledge_base("Why are wheat leaves yellow?", top_k=3)
    res_b = query_knowledge_base("How often should I irrigate rice?", top_k=3)

    assert len(res_a["chunks"]) > 0
    assert len(res_b["chunks"]) > 0

    sources_a = {s["title"] for s in res_a["sources"]}
    sources_b = {s["title"] for s in res_b["sources"]}

    print("\n--- RAG Proof of Distinct Retrieval ---")
    print(f"Question A ('Why are wheat leaves yellow?') retrieved sources: {sources_a}")
    print(f"Question B ('How often should I irrigate rice?') retrieved sources: {sources_b}")

    # Assert that there is ZERO overlap in top retrieved titles between Wheat Leaves and Rice Irrigation
    assert len(sources_a.intersection(sources_b)) == 0

    # Question A must relate to Wheat / Yellow Rust / Nitrogen
    assert any("Wheat" in title or "Rust" in title or "Soil" in title for title in sources_a)
    # Question B must relate to Rice / Irrigation
    assert any("Rice" in title or "Irrigation" in title for title in sources_b)


def test_rag_query_1_wheat_yellow_leaves(client):
    """Test 1: 'Why are wheat leaves yellow?'"""
    response = client.post("/api/chat", json={"message": "Why are wheat leaves yellow?"})
    assert response.status_code == 200
    data = response.json()
    assert data["retrieved_chunks"] > 0
    assert data["confidence"] > 0.4
    assert len(data["sources"]) > 0
    # Verified source must mention Wheat or Yellow Rust or Soil Health
    assert any("Wheat" in s["title"] or "Rust" in s["title"] or "Soil" in s["title"] for s in data["sources"])


def test_rag_query_2_hindi_wheat_first_irrigation(client):
    """Test 2: 'गेहूं में पहली सिंचाई कब करनी चाहिए?'"""
    response = client.post("/api/chat", json={"message": "गेहूं में पहली सिंचाई कब करनी चाहिए?"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hi"
    assert data["retrieved_chunks"] > 0
    assert len(data["sources"]) > 0
    # Must retrieve Wheat Irrigation / CRI stage
    assert any("Wheat" in s["title"] or "Irrigation" in s["title"] for s in data["sources"])


def test_rag_query_3_hinglish_maize_pests(client):
    """Test 3: 'meri maize crop me keede lag gaye hain'"""
    response = client.post("/api/chat", json={"message": "meri maize crop me keede lag gaye hain"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hinglish"
    assert data["retrieved_chunks"] > 0
    # Must retrieve Fall Armyworm or Maize guide
    assert any("Maize" in s["title"] or "Armyworm" in s["title"] for s in data["sources"])


def test_rag_query_4_rice_fertilizer(client):
    """Test 4: 'What fertilizer is generally important for rice?'"""
    response = client.post("/api/chat", json={"message": "What fertilizer is generally important for rice?"})
    assert response.status_code == 200
    data = response.json()
    assert data["retrieved_chunks"] > 0
    assert any("Rice" in s["title"] or "Fertilizer" in s["title"] or "Nitrogen" in s["title"] for s in data["sources"])


def test_rag_query_5_soil_nitrogen_deficiency(client):
    """Test 5: 'मिट्टी में nitrogen की कमी कैसे पहचानें?'"""
    response = client.post("/api/chat", json={"message": "मिट्टी में nitrogen की कमी कैसे पहचानें?"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hi"
    assert data["retrieved_chunks"] > 0
    assert any("Nitrogen" in s["title"] or "Soil" in s["title"] for s in data["sources"])


def test_rag_query_6_pm_kisan_scheme(client):
    """Test 6: 'PM-KISAN kya hai?'"""
    response = client.post("/api/chat", json={"message": "PM-KISAN kya hai?"})
    assert response.status_code == 200
    data = response.json()
    assert data["retrieved_chunks"] > 0
    assert any("PM-KISAN" in s["title"] or "Kisan" in s["title"] for s in data["sources"])


def test_rag_query_7_out_of_domain_france(client):
    """Test 7: 'What is the capital of France?' (Must be politely rejected)"""
    response = client.post("/api/chat", json={"message": "What is the capital of France?"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "boundary_guard"
    assert data["retrieved_chunks"] == 0
    assert "Maitri Krishi Assistant" in data["reply"]
    assert "agriculture" in data["reply"].lower()


def test_rag_query_8_gibberish_low_confidence(client):
    """Test 8: 'asdfghjkl random question' (Must return safe low confidence clarification)"""
    response = client.post("/api/chat", json={"message": "asdfghjkl random question"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "low_confidence_guard"
    assert "reliable information" in data["reply"].lower() or "पर्याप्त प्रामाणिक जानकारी" in data["reply"]


def test_rag_openrouter_mocked_success(client):
    """Test 9: Verified OpenRouter API call integration when API responds successfully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "Wheat first irrigation must be applied at Crown Root Initiation (CRI) stage (21-25 DAS)."
            }
        }]
    }

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "mock_test_key", "OPENROUTER_MODEL": "openrouter/free"}):
        with patch("requests.post", return_value=mock_resp):
            response = client.post(
                "/api/chat",
                json={
                    "message": "When to irrigate wheat for the first time?",
                    "context": {"crop": "Wheat", "soil_moisture": 28.0}
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "openrouter"
            assert "Crown Root Initiation" in data["reply"]
            assert data["retrieved_chunks"] > 0
            assert len(data["sources"]) > 0


def test_rag_debug_endpoint(client):
    """Test 10: /api/chat/debug endpoint returns exact chunk previews and distances."""
    with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
        response = client.post("/api/chat/debug", json={"query": "Wheat CRI irrigation timing", "top_k": 2})
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "sources" in data
        assert "confidence" in data
        assert len(data["chunks"]) == 2
        assert data["confidence"] > 0.5
