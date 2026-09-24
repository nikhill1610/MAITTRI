# -*- coding: utf-8 -*-
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


def test_farmer_facing_response_formatting_and_no_markdown_leak(client):
    """
    Farmer-facing response quality verification:
    1. Answers the user's question directly in the first sentence (CRI / 20-25 days).
    2. Uses clean hyphen bullets (- ) without raw Markdown emphasis markers (**, *, __).
    3. Normal simple questions stay concise (~60-120 words).
    4. Does not include unrelated pesticide/chemical warnings for irrigation queries.
    5. Preserves source/citation metadata.
    """
    response = client.post("/api/chat", json={"message": "gehun me pehli sinchai kab karein?"})
    assert response.status_code == 200
    data = response.json()
    reply = data["reply"]

    # 1. No raw Markdown emphasis markers leak through
    assert "**" not in reply, f"Raw '**' found in farmer reply: {reply}"
    assert "__" not in reply, f"Raw '__' found in farmer reply: {reply}"
    assert "*" not in reply, f"Raw '*' found in farmer reply: {reply}"

    # 2. Simple formatting: clean hyphen bullets
    if "\n-" in reply or "\n -" in reply:
        assert "- " in reply, f"Bullet points should use clean hyphen formatting: {reply}"

    # 3. First sentence directly answers irrigation timing
    first_line = reply.strip().split("\n")[0]
    assert any(term in first_line.lower() for term in ["20–25", "20-25", "cri", "सिंचाई", "sinchai"]), (
        f"First sentence does not directly answer wheat first irrigation: {first_line}"
    )

    # 4. Concise response length (~60-120 words)
    words = reply.split()
    assert 20 <= len(words) <= 130, f"Response verbosity outside expected bounds ({len(words)} words): {reply}"

    # 5. Chemical/pesticide warnings should NOT appear for simple irrigation questions
    assert not any(w in reply.lower() for w in ["pesticide", "fungicide", "कीटनाशक", "फफूंदनाशक"]), (
        f"Unrelated chemical warning leaked into irrigation response: {reply}"
    )

    # 6. Preserves source/citation metadata
    assert data["retrieved_chunks"] > 0
    assert len(data["sources"]) > 0
    assert any("Wheat" in s["title"] or "Irrigation" in s["title"] for s in data["sources"])


def test_live_weather_hybrid_irrigation_meerut(client):
    """
    Focused regression test for:
    'Meerut mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?'

    Assert:
    - route is LIVE / WEATHER or equivalent live-weather route.
    - current-location intent is preserved (Meerut).
    - Tavily/weather service path is invoked or mocked.
    - response is not generated solely from static wheat KB.
    - if live lookup fails, response explicitly avoids claiming current conditions.
    """
    # 1. Successful Live Weather / Hybrid execution
    response = client.post(
        "/api/chat",
        json={"message": "Meerut mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?"}
    )
    assert response.status_code == 200
    data = response.json()
    reply = data["reply"]

    # Route assertion
    assert data["intent"] == "WEATHER"
    assert data["route"] == "WEATHER_SERVICE"
    assert data["provider"] in ("tavily_weather", "weather_service")

    # Location preservation
    assert "meerut" in reply.lower() or "मेरठ" in reply

    # Direct first sentence
    first_line = reply.strip().split("\n")[0]
    assert any(w in first_line.lower() for w in ["sinchai", "सिंचाई", "irrigation", "saaf", "साफ", "clear", "कर सकते हैं", "kar sakte hain", "टालें", "postpone"])

    # Not solely static wheat KB (contains weather source attribution)
    assert data["retrieved_chunks"] > 0
    assert len(data["sources"]) > 0

    # 2. Failure Case: When live lookup fails, explicitly avoids claiming current conditions
    from unittest.mock import patch
    from app.services.web_search_service import web_search_service
    with patch.object(web_search_service, "search", side_effect=RuntimeError("Tavily down")):
        fail_response = client.post(
            "/api/chat",
            json={"message": "Meerut mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?"}
        )
        assert fail_response.status_code == 200
        fail_data = fail_response.json()
        fail_reply = fail_data["reply"]

        assert fail_data["intent"] == "WEATHER"
        assert fail_data["route"] == "WEATHER_SERVICE"
        # Avoids claiming current weather conditions; states unverified
        assert any(
            phrase in fail_reply.lower()
            for phrase in ["verify nahi", "सत्यापित नहीं", "could not be verified", "unverified"]
        ), f"Failed lookup did not state unverified status: {fail_reply}"


def test_weather_distinction_three_cases(client):
    """
    Verify distinction between:
    1. 'aaj Meerut me barish hogi?' -> LIVE WEATHER
    2. 'today weather ke hisaab se spray karu?' -> LIVE WEATHER + context
    3. 'gehun ki pehli sinchai kab karein?' -> STATIC RAG
    """
    # 1. 'aaj Meerut me barish hogi?' -> LIVE WEATHER
    r1 = client.post("/api/chat", json={"message": "aaj Meerut me barish hogi?"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["intent"] == "WEATHER"
    assert d1["route"] == "WEATHER_SERVICE"

    # 2. 'today weather ke hisaab se spray karu?' -> LIVE WEATHER + agronomic/safety context
    r2 = client.post(
        "/api/chat",
        json={"message": "today weather ke hisaab se spray karu?", "context": {"location": "Meerut"}}
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "WEATHER"
    assert d2["route"] == "WEATHER_SERVICE"
    assert any(w in d2["reply"].lower() for w in ["spray", "हवा", "wind", "rain", "बारिश", "छिड़काव"])

    # 3. 'gehun ki pehli sinchai kab karein?' -> STATIC RAG
    r3 = client.post("/api/chat", json={"message": "gehun ki pehli sinchai kab karein?"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["intent"] in ("CALENDAR", "GENERAL")
    assert d3["route"] in ("CALENDAR_SERVICE", "RAG")
    assert d3["provider"] in ("calendar_service", "grounded_local_rag", "local_rag")


def test_explicit_location_precedence_e2e_four_cases(client):
    """
    Focused regression coverage for explicit-location precedence bug:
    Stored context: location = Meerut

    Case 1: 'Delhi mein aaj mausam kaisa hai?' -> location = Delhi
    Case 2: 'Lucknow me kal barish hogi?' -> location = Lucknow
    Case 3: 'aaj mausam kaisa hai?' -> inherited location = Meerut
    Case 4: 'Delhi mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?'
            - WEATHER_SERVICE
            - Delhi
            - Wheat
            - live weather query built for Delhi
            - no Meerut leakage in final answer
    """
    from unittest.mock import patch
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType
    from app.services.chat_service import process_chat_message

    stored_context = {"location": "Meerut"}

    captured_calls = []

    def mock_search(query, crop=None, location=None, freshness_needed=True):
        captured_calls.append({"query": query, "crop": crop, "location": location})
        return [
            WebEvidence(
                title=f"IMD Weather Bulletin for {location}",
                content=f"Weather forecast for {location}: mainly clear sky, no rain expected today.",
                url="https://mausam.imd.gov.in/forecast",
                domain="mausam.imd.gov.in",
                score=0.95,
                source_tier=SourceTier.AUTHORITATIVE,
                source_type=SourceType.LIVE_WEB_OFFICIAL,
                published_date="2026-09-23"
            )
        ]

    with patch.object(web_search_service, "search", side_effect=mock_search), \
         patch.object(web_search_service, "_enabled", True):

        # Case 1: "Delhi mein aaj mausam kaisa hai?" with stored context Meerut
        r1 = process_chat_message("Delhi mein aaj mausam kaisa hai?", context=stored_context)
        assert r1["intent"] == "WEATHER"
        assert r1["route"] == "WEATHER_SERVICE"
        assert r1["detected_entities"]["location"] == "Delhi"
        assert "Delhi" in r1["reply"]
        assert "Meerut" not in r1["reply"]

        # Case 2: "Lucknow me kal barish hogi?" with stored context Meerut
        r2 = process_chat_message("Lucknow me kal barish hogi?", context=stored_context)
        assert r2["intent"] == "WEATHER"
        assert r2["route"] == "WEATHER_SERVICE"
        assert r2["detected_entities"]["location"] == "Lucknow"
        assert "Lucknow" in r2["reply"]
        assert "Meerut" not in r2["reply"]

        # Case 3: "aaj mausam kaisa hai?" with stored context Meerut
        r3 = process_chat_message("aaj mausam kaisa hai?", context=stored_context)
        assert r3["intent"] == "WEATHER"
        assert r3["route"] == "WEATHER_SERVICE"
        assert r3["detected_entities"]["location"] == "Meerut"
        assert "Meerut" in r3["reply"]

        # Case 4: "Delhi mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?"
        captured_calls.clear()
        r4 = process_chat_message(
            "Delhi mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?",
            context=stored_context
        )
        assert r4["intent"] == "WEATHER"
        assert r4["route"] == "WEATHER_SERVICE"
        assert r4["detected_entities"]["location"] == "Delhi"
        assert r4["detected_entities"]["crop"] == "Wheat"
        assert r4["provider"] == "tavily_weather"

        # Verify live weather query was built for Delhi, not Meerut
        assert len(captured_calls) == 1
        assert "Delhi" in captured_calls[0]["query"]
        assert "Meerut" not in captured_calls[0]["query"]
        assert captured_calls[0]["location"] == "Delhi"
        assert captured_calls[0]["crop"] == "Wheat"

        # Verify final answer mentions Delhi and has zero leakage of Meerut
        reply4 = r4["reply"]
        assert "Delhi" in reply4
        assert "Meerut" not in reply4

        # Also verify via HTTP API endpoint
        api_res = client.post(
            "/api/chat",
            json={
                "message": "Delhi mein aaj ke mausam ke hisaab se kya mujhe gehun ki sinchai karni chahiye?",
                "context": stored_context
            }
        )
        assert api_res.status_code == 200
        api_data = api_res.json()
        assert api_data["intent"] == "WEATHER"
        assert api_data["route"] == "WEATHER_SERVICE"
        assert "Delhi" in api_data["reply"]
        assert "Meerut" not in api_data["reply"]


def test_conversation_history_location_e2e(client):
    """
    Query 1: 'Delhi ka weather batao'
    followed by
    Query 2: 'kal barish hogi?'
    Conversation location remains Delhi for that thread even with stored context Meerut.
    """
    from app.services.chat_service import process_chat_message

    stored_context = {"location": "Meerut"}
    history = [
        {"role": "user", "content": "Delhi ka weather batao"},
        {"role": "assistant", "content": "Delhi me weather saaf hai."}
    ]
    r = process_chat_message(
        "kal barish hogi?",
        context=stored_context,
        history=history
    )
    assert r["intent"] == "WEATHER"
    assert r["route"] == "WEATHER_SERVICE"
    assert r["detected_entities"]["location"] == "Delhi"
    assert "Delhi" in r["reply"]
    assert "Meerut" not in r["reply"]

    # Verify via HTTP API endpoint
    api_res = client.post(
        "/api/chat",
        json={"message": "kal barish hogi?", "context": stored_context, "history": history}
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["intent"] == "WEATHER"
    assert api_data["route"] == "WEATHER_SERVICE"
    assert "Delhi" in api_data["reply"]
    assert "Meerut" not in api_data["reply"]


def test_case_1_jaipur_wheat_mandi_live_route_and_location():
    """
    Case 1: 'Aaj Jaipur mandi me gehun ka latest bhav kya hai?'
    - intent = MARKET/MANDI
    - location = Jaipur
    - commodity = Wheat
    - live web service invoked
    - no static-only response
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType
    from datetime import date

    today_str = date.today().strftime("%d-%m-%Y")
    mock_ev = WebEvidence(
        title="Jaipur Mandi Wheat Bhav Today - AGMARKNET",
        url="https://agmarknet.gov.in/price/jaipur-wheat",
        domain="agmarknet.gov.in",
        content=f"Wheat modal price Rs 2550 per quintal with min Rs 2450 and max Rs 2650 reported on {today_str} in Jaipur Mandi.",
        score=0.98,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=today_str
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]) as mock_search:
        res = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert res["intent"] in ("MARKET", "FINANCIAL")
        assert res["route"] == "MARKET_SERVICE"
        assert res["detected_entities"]["location"] == "Jaipur"
        assert res["detected_entities"]["crop"] == "Wheat"
        assert res["provider"] == "tavily_market"
        mock_search.assert_called_once()
        call_args = mock_search.call_args[1]
        assert "Jaipur" in call_args["query"]
        assert "wheat" in call_args["query"].lower()
        assert "AGMARKNET" in call_args["query"]
        assert call_args["crop"] == "Wheat"
        assert call_args["location"] == "Jaipur"
        # No static-only response
        assert "live data feed connected nahi hai" not in res["reply"]
        assert "Jaipur" in res["reply"]
        assert "2550" in res["reply"]


def test_case_2_meerut_mandi_live_route():
    """
    Case 2: 'Meerut mandi ka aaj ka gehu rate?'
    - Expected location = Meerut
    - Expected commodity = Wheat
    - Expected live route
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType
    from datetime import date

    today_str = date.today().strftime("%d-%m-%Y")
    mock_ev = WebEvidence(
        title="Meerut Mandi Wheat Daily Rates - AGMARKNET",
        url="https://agmarknet.gov.in/price/meerut-wheat",
        domain="agmarknet.gov.in",
        content=f"Meerut mandi wheat arrival modal price Rs 2420, min 2350, max 2480 on {today_str}.",
        score=0.96,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=today_str
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]) as mock_search:
        res = process_chat_message("Meerut mandi ka aaj ka gehu rate?")
        assert res["intent"] in ("MARKET", "FINANCIAL")
        assert res["route"] == "MARKET_SERVICE"
        assert res["detected_entities"]["location"] == "Meerut"
        assert res["detected_entities"]["crop"] == "Wheat"
        assert res["provider"] == "tavily_market"
        assert mock_search.called
        assert "Meerut" in res["reply"]
        assert "2420" in res["reply"]


def test_case_3_static_rag_not_market_route():
    """
    Case 3: 'gehu ki kheti kaise kare?'
    - Expected static RAG
    - NOT market route
    """
    from app.services.smart_rag_router import classify_query, Intent, RouteAction
    res = classify_query("gehu ki kheti kaise kare?")
    assert res.intent == Intent.GENERAL
    assert res.action == RouteAction.RAG
    assert res.action != RouteAction.MARKET_SERVICE


def test_case_4_mock_tavily_fresh_official_result():
    """
    Case 4 (Test A): Mock Tavily returns fresh official market result
    - price/date/source rendered correctly
    - metadata exposes live lookup audit fields
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType
    from datetime import date

    today_str = date.today().strftime("%d-%m-%Y")
    mock_ev = WebEvidence(
        title="Jaipur APMC Wheat Rates",
        url="https://agmarknet.gov.in/jaipur",
        domain="agmarknet.gov.in",
        content=f"Modal price: Rs 2500 per quintal, Min: Rs 2400, Max: Rs 2600 reported on {today_str}.",
        score=0.99,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=today_str
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("Jaipur mandi me wheat ka latest modal price kya hai?")
        assert res["provider"] == "tavily_market"
        assert res["intent"] == "MARKET"
        assert res["route"] == "MARKET_SERVICE"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "verified_rate_found"
        assert res["rejection_reason"] is None
        assert res["retrieved_chunks"] >= 1
        reply = res["reply"]
        assert "Modal price: ₹2500 / quintal" in reply
        assert "Min–Max: ₹2400 – ₹2600 / quintal" in reply
        assert today_str in reply
        assert "AGMARKNET" in reply


def test_case_5_mock_tavily_stale_result():
    """
    Case 5 (Test B): Mock Tavily returns stale result
    - stale market rate rejected
    - anti_hallucination_guard returns safe fallback
    - no invented price or obsolete rate presented as current
    """
    import re
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    stale_date = "15-07-2025"
    mock_ev = WebEvidence(
        title="Jaipur Mandi Previous Wheat Rates",
        url="https://agmarknet.gov.in/jaipur/archive",
        domain="agmarknet.gov.in",
        content=f"Wheat arrival modal price Rs 2350, min Rs 2250, max Rs 2450 per quintal reported on {stale_date}.",
        score=0.90,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2025-07-15"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["intent"] == "MARKET"
        assert res["route"] == "MARKET_SERVICE"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "stale_rate_rejected"
        assert res["rejection_reason"] == "stale_market_rate_rejected"
        reply = res["reply"]
        assert "Main abhi Jaipur mandi ka current verified" in reply
        assert "agmarknet.gov.in" in reply
        assert "2350" not in reply
        assert not re.search(r"₹\s*\d{3,5}", reply)


def test_case_6_mock_tavily_fails_safe_fallback():
    """
    Case 6 (Test D): Mock Tavily fails with exception/timeout
    - safe fallback
    - live_lookup_result = 'provider_error'
    - no invented price
    """
    import re
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service

    with patch.object(web_search_service, "search", side_effect=RuntimeError("Tavily timeout")):
        res = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["intent"] == "MARKET"
        assert res["route"] == "MARKET_SERVICE"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "provider_error"
        assert "Provider exception" in (res.get("rejection_reason") or "")
        reply = res["reply"]
        assert "Main abhi Jaipur mandi ka current verified" in reply
        assert "agmarknet.gov.in" in reply
        assert not re.search(r"₹\s*\d{3,5}", reply)
        assert not re.search(r"rs\.?\s*\d{3,5}", reply, re.IGNORECASE)


def test_case_7_no_trustworthy_result_safe_fallback():
    """
    Case 7 (Test C): Live lookup returns results without trustworthy prices
    - safe fallback returned by anti_hallucination_guard
    - live_lookup_result = 'no_verified_rate'
    - rejection_reason = 'no_price_in_evidence'
    """
    import re
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    mock_ev = WebEvidence(
        title="Department of Agriculture Annual Report",
        url="https://agriwelfare.gov.in/report.pdf",
        domain="agriwelfare.gov.in",
        content="General overview of mandi operations and APMC guidelines across northern states.",
        score=0.75,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "no_verified_rate"
        assert res["rejection_reason"] == "no_price_in_evidence"
        assert not re.search(r"₹\s*\d{3,5}", res["reply"])


def test_case_8_price_cannot_appear_without_source_and_freshness():
    """
    Case 8 (Test E): Invariant that specific ₹ value can NEVER appear without
    an authoritative source and explicit reported date/freshness.
    """
    import re
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType
    from datetime import date

    # 1. Fallback case: absolutely no ₹ value
    with patch.object(web_search_service, "search", return_value=[]):
        res_fb = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert not re.search(r"₹\s*\d{3,5}", res_fb["reply"])
        assert not re.search(r"rs\.?\s*\d{3,5}", res_fb["reply"], re.IGNORECASE)

    # 2. Verified case: ₹ value MUST have date, source, and sources array
    today_str = date.today().strftime("%d-%m-%Y")
    mock_ev = WebEvidence(
        title="Jaipur Mandi Daily Wheat Rate",
        url="https://agmarknet.gov.in/jaipur",
        domain="agmarknet.gov.in",
        content=f"Modal price: Rs 2550 per quintal reported on {today_str}.",
        score=0.98,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=today_str
    )
    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res_ver = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        if re.search(r"₹\s*\d{3,5}", res_ver["reply"]):
            assert today_str in res_ver["reply"]
            assert any(s in res_ver["reply"] for s in ["AGMARKNET", "eNAM", "gov.in"])
            assert len(res_ver["sources"]) > 0
            assert res_ver["sources"][0]["source"]


def test_scheme_case_a_verified_2026_notification_found():
    """
    Scheme Test A: Verified 2026 official notification found.
    - direct answer first
    - max 3-5 bullets
    - includes date for claimed change
    - source line at end
    - no raw snippets dumped
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    mock_ev = WebEvidence(
        title="PMFBY Revised Operational Guidelines 2026",
        url="https://pmfby.gov.in/files/guidelines_2026.pdf",
        domain="pmfby.gov.in",
        content="Ministry of Agriculture notification dated 15-01-2026: Mandatory electronic claim transfer within 15 days of CCE completion. State subsidy release deadline tightened for Kharif 2026.",
        score=0.96,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-15"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "tavily_scheme"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "verified_scheme_rule_found"
        assert res["rejection_reason"] is None
        reply = res["reply"]
        assert "2026" in reply
        assert "15-01-2026" in reply
        assert "pmfby.gov.in" in reply
        assert "Ministry of Agriculture" in reply
        # Verify bullet structure
        assert "\n-" in reply
        lines = [line.strip() for line in reply.split("\n") if line.strip().startswith("-")]
        assert 1 <= len(lines) <= 5
        # Ensure no raw snippet dump artifacts
        assert "..." not in reply or len(reply) < 500


def test_scheme_case_b_only_old_official_documents_found():
    """
    Scheme Test B: Only old official documents found.
    - rejects stale documents from past years as 2026 rules
    - safe fallback returned
    - exact required sentence present
    - stable scheme information summarized separately as general/background info
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    mock_ev = WebEvidence(
        title="Standing Committee Report on PMFBY 2021",
        url="https://pmfby.gov.in/report_2021.pdf",
        domain="pmfby.gov.in",
        content="Report on PMFBY implementation across states in 2020-21. Premium shares 1.5% and 2%.",
        score=0.88,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2021-03-15"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "stale_documents_rejected"
        assert res["rejection_reason"] == "old_documents_rejected"
        reply = res["reply"]
        assert "Mujhe official sources se 2026 ke specific naye PMFBY rule changes verify nahi mile. Main outdated information ko latest ke roop me present nahi karunga." in reply
        assert "General/Background Information" in reply
        assert "1.5%" in reply


def test_scheme_case_c_official_page_with_no_publication_date():
    """
    Scheme Test C: Official page with no publication date.
    - rejects undated page as unverified for 2026 rules
    - safe fallback returned
    - exact required sentence present
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    mock_ev = WebEvidence(
        title="PMFBY Scheme Details",
        url="https://pmfby.gov.in/details",
        domain="pmfby.gov.in",
        content="Pradhan Mantri Fasal Bima Yojana offers comprehensive risk insurance for notified crops across states.",
        score=0.82,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=None
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "undated_page_rejected"
        assert res["rejection_reason"] == "undated_evidence_rejected"
        reply = res["reply"]
        assert "Mujhe official sources se 2026 ke specific naye PMFBY rule changes verify nahi mile. Main outdated information ko latest ke roop me present nahi karunga." in reply
        assert "General/Background Information" in reply


def test_scheme_case_d_web_search_returns_generic_homepage_or_lms():
    """
    Scheme Test D: Web search returns generic PMFBY homepage or LMS training page.
    - never infers policy change from homepage or LMS training
    - safe fallback returned
    - exact required sentence present
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service, WebEvidence, SourceTier, SourceType

    mock_ev_lms = WebEvidence(
        title="PMFBY Learning Management System | Farmer Training Courses",
        url="https://pmfby.gov.in/lms/wim",
        domain="pmfby.gov.in",
        content="PMFBY LMS portal for insurance training and capacity building of bank officials.",
        score=0.85,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=None
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev_lms]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "training_lms_excluded"
        reply = res["reply"]
        assert "Mujhe official sources se 2026 ke specific naye PMFBY rule changes verify nahi mile. Main outdated information ko latest ke roop me present nahi karunga." in reply
        assert "LMS" not in reply
        assert "training" not in reply.lower()


def test_scheme_case_e_provider_failure():
    """
    Scheme Test E: Web search provider failure / timeout.
    - handles exception gracefully
    - live_lookup_result = 'provider_error'
    - safe fallback returned
    - exact required sentence present
    """
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service

    with patch.object(web_search_service, "search", side_effect=RuntimeError("Tavily gateway timeout")):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_attempted"] is True
        assert res["live_lookup_provider"] == "tavily"
        assert res["live_lookup_result"] == "provider_error"
        assert "Provider exception" in (res.get("rejection_reason") or "")
        reply = res["reply"]
        assert "Mujhe official sources se 2026 ke specific naye PMFBY rule changes verify nahi mile. Main outdated information ko latest ke roop me present nahi karunga." in reply
        assert "General/Background Information" in reply


def test_diagnostic_confidence_calibration_tomato_leaf_curl_followup():
    """
    Regression Test: Diagnostic Confidence Calibration for Symptom-Based Crop Disease Follow-Up.
    1. Initial ambiguous tomato curl query:
       'tamatar ke patte curl ho rahe hain, kya problem ho sakti hai?'
       -> Must return differential diagnosis with multiple potential causes.
    2. Follow-up symptom narrowing query:
       'patte upar ki taraf mud rahe hain aur whitefly bhi dikh rahi hai'
       -> Must narrow strongly toward ToLCV using calibrated language:
          - 'ToLCV ka strong suspicion hai'
          - 'ToLCV ki sambhavna kaafi badh jaati hai'
          - 'Symptoms ToLCV se strongly match karte hain'
       -> Must NOT claim definitive / laboratory-confirmed diagnosis.
       -> Clearly separates:
          - likely diagnosis
          - what farmer should check next
          - immediate low-risk management (rogueing, yellow sticky traps, neem oil, no chemical cures virus)
          - when expert/lab confirmation is useful
       -> Includes relevant ICAR-IIVR source line.
    """
    from app.services.chat_service import process_chat_message

    # Turn 1: Ambiguous initial query
    q1 = "tamatar ke patte curl ho rahe hain, kya problem ho sakti hai?"
    res1 = process_chat_message(q1)
    reply1 = res1.get("reply", "")

    # Must present differential diagnosis across multiple causes
    assert any(term in reply1 for term in ["causes", "कारण", "TLCV", "Leaf Curl Virus"])
    assert any(term in reply1 for term in ["Physiological", "Mites", "Thrips", "Herbicide"])

    # Turn 2: Follow-up symptom narrowing with history
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": reply1}
    ]
    q2 = "patte upar ki taraf mud rahe hain aur whitefly bhi dikh rahi hai"
    res2 = process_chat_message(q2, history=history)
    reply2 = res2.get("reply", "")

    # 1. Calibrated language checks
    assert "ToLCV" in reply2
    assert "ToLCV ka strong suspicion hai" in reply2
    assert "ToLCV ki sambhavna kaafi badh jaati hai" in reply2
    assert "Symptoms ToLCV se strongly match karte hain" in reply2

    # 2. Must NOT claim definitive / absolute confirmation without lab testing
    assert "definitive confirmation nahi hai" in reply2
    assert "Tomato me leaf curl disease aur whitefly control ke liye key advisory:" not in reply2

    # 3. Clearly separated sections
    assert "Likely Diagnosis:" in reply2
    assert "What to check next:" in reply2
    assert "Immediate Low-risk Management:" in reply2
    assert "When Expert" in reply2

    # 4. Preserved safety & agronomic guidance
    assert "vector" in reply2.lower() or "vahak" in reply2.lower()
    assert "rogue out" in reply2 or "ukhaadkar" in reply2
    assert "Yellow Sticky Traps" in reply2
    assert "Neem oil" in reply2 or "neem" in reply2.lower()
    assert "cure" in reply2.lower() or "theek" in reply2.lower()

    # 5. Relevant source line
    assert "ICAR-IIVR" in reply2


def test_crop_age_action_query_synthesis_wheat_cri():
    """
    Regression Test: Single-turn crop-age + action-query synthesis.
    A. 'mere gehun ko 22 din hue hain, ab kya karu?'
       -> identifies CRI stage, first irrigation due, waterlogging prevention, urea top-dressing.
    B. 'wheat 22 days old hai, next kya karna chahiye?'
       -> first sentence directly answers 'ab kya karu?'.
    C. nearby age outside CRI range:
       - 12 days: explains irrigation not yet due, wait for 20-25 days CRI stage.
       - 45 days: explains tillering stage 2nd irrigation & final urea split.
    D. no raw 'A:' / FAQ fragments appear in the final reply.
    """
    import re
    from app.services.chat_service import process_chat_message

    # Test A: "mere gehun ko 22 din hue hain, ab kya karu?"
    res_a = process_chat_message("mere gehun ko 22 din hue hain, ab kya karu?")
    reply_a = res_a.get("reply", "")

    # First sentence directly answers "ab kya karu?" and identifies CRI stage
    assert "CRI" in reply_a
    assert "sinchai" in reply_a.lower() or "irrigation" in reply_a.lower()
    assert "First Irrigation" in reply_a or "पहली सिंचाई" in reply_a
    assert "Urea" in reply_a or "यूरिया" in reply_a
    assert "Waterlogging" in reply_a or "जलभराव" in reply_a or "suffocate" in reply_a
    assert "ICAR-IIWBR" in reply_a

    # Test B: "wheat 22 days old hai, next kya karna chahiye?"
    res_b = process_chat_message("wheat 22 days old hai, next kya karna chahiye?")
    reply_b = res_b.get("reply", "")
    assert "CRI" in reply_b
    assert "sinchai" in reply_b.lower() or "irrigation" in reply_b.lower()
    assert "ICAR-IIWBR" in reply_b

    # Test C: Nearby age outside CRI range (12 days & 45 days)
    # C1: 12 days -> irrigation NOT due yet, wait for CRI
    res_c1 = process_chat_message("mere gehun ko 12 din hue hain, ab kya karu?")
    reply_c1 = res_c1.get("reply", "")
    assert "zaroorat nahi hai" in reply_c1 or "not yet due" in reply_c1 or "आवश्यकता नहीं" in reply_c1
    assert "20–25" in reply_c1 or "20-25" in reply_c1

    # C2: 45 days -> Tillering stage, second irrigation
    res_c2 = process_chat_message("wheat 45 days old hai, next kya karna chahiye?")
    reply_c2 = res_c2.get("reply", "")
    assert "Tillering" in reply_c2 or "tillering" in reply_c2.lower() or "कल्ले" in reply_c2
    assert "Second Irrigation" in reply_c2 or "second irrigation" in reply_c2.lower() or "दूसरी सिंचाई" in reply_c2

    # Test D: No raw "A:" / FAQ fragments in any replies
    for rep in [reply_a, reply_b, reply_c1, reply_c2]:
        assert not re.search(r"^[-•*\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)", rep, re.MULTILINE | re.I)
        assert not re.search(r"^[-•*\s]*(?:Q\s*:|Question\s*:|प्रश्न\s*:)", rep, re.MULTILINE | re.I)
        assert "A: Due to" not in rep
        assert "A: Only if" not in rep





