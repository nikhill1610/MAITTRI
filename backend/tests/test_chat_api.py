import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_status_endpoint():
    """Verify GET /api/chat/status returns online status and knowledge base info."""
    response = client.get("/api/chat/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["assistant_name"] == "Maitri Krishi Assistant"
    assert "active_model" in data
    assert "knowledge_base_categories" in data
    assert len(data["knowledge_base_categories"]) > 0


def test_chat_english_farming_question():
    """Verify POST /api/chat responds properly to English question."""
    payload = {
        "message": "What is the recommended fertilizer for wheat?",
        "context": {
            "crop": "Wheat",
            "soil_type": "Loam"
        }
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 10
    assert data["language"] == "en"
    assert "sources" in data


def test_chat_hindi_farming_question():
    """Verify POST /api/chat responds in Hindi when given Devanagari Hindi text."""
    payload = {
        "message": "गेहूं के पत्ते पीले हो रहे हैं क्या करूं?",
        "context": {
            "crop": "Wheat"
        }
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["language"] == "hi"


def test_chat_hinglish_farming_question():
    """Verify POST /api/chat detects Hinglish and responds in Hinglish."""
    payload = {
        "message": "meri wheat crop me growth slow hai aur leaves yellow ho rahe hain",
        "context": {
            "crop": "Wheat"
        }
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["language"] == "hinglish"


def test_chat_empty_message_validation():
    """Verify empty message is rejected."""
    payload = {"message": ""}
    response = client.post("/api/chat", json=payload)
    assert response.status_code in (400, 422)


def test_chat_non_agricultural_rejection():
    """Verify non-agricultural question is politely declined."""
    payload = {"message": "What is the capital of France?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Maitri Krishi Assistant" in data["reply"]
    assert "agriculture" in data["reply"].lower() or "कृषि" in data["reply"]


def test_chat_with_full_context_and_history():
    """Verify context and conversation history are accepted without error."""
    payload = {
        "message": "Is my soil moisture adequate for the CRI stage?",
        "context": {
            "crop": "Wheat",
            "soil_type": "Clay Loam",
            "land_area": 3.0,
            "soil_moisture": 32.5,
            "temperature": 24.0,
            "location": "Karnal, Haryana"
        },
        "history": [
            {"role": "user", "content": "I just sowed wheat 21 days ago."},
            {"role": "assistant", "content": "Congratulations on sowing. The CRI stage is around 21 days."}
        ]
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chat_message_alias_route():
    """Verify POST /api/chat/message alias subpath functions identically."""
    payload = {"message": "How much water does rice require?"}
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_openrouter_mock_successful_call():
    """Verify that when OpenRouter returns 200, the message is returned as expected."""
    mock_response = {
        "choices": [
            {"message": {"content": "For wheat, apply 120 kg N, 60 kg P2O5, and 40 kg K2O per hectare."}}
        ]
    }
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        # Set a test key temporarily
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key-mock"}):
            payload = {"message": "What fertilizer is needed for wheat?"}
            response = client.post("/api/chat", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "openrouter"
            assert "120 kg N" in data["reply"]


def test_openrouter_mock_timeout_fallback():
    """Verify graceful fallback when OpenRouter times out or errors."""
    import requests
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key-mock"}):
            payload = {"message": "What fertilizer is needed for wheat?"}
            response = client.post("/api/chat", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] in ("grounded_local_rag", "offline_knowledge_base")
            assert len(data["reply"]) > 10
