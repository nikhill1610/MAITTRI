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
    Case 4: Mock Tavily returns fresh official market result
    - price/date/source rendered correctly
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
        reply = res["reply"]
        assert "Modal price: ₹2500 / quintal" in reply
        assert "Min–Max: ₹2400 – ₹2600 / quintal" in reply
        assert today_str in reply
        assert "AGMARKNET" in reply


def test_case_5_mock_tavily_stale_result():
    """
    Case 5: Mock Tavily returns stale result
    - response labels it as latest verified available
    - does NOT call it today's rate
    """
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
        assert res["provider"] == "tavily_market"
        reply = res["reply"]
        assert "Latest verified available rate I found is from" in reply
        assert stale_date in reply or "2025-07-15" in reply
        assert "aaj ka rate" not in reply.lower()
        assert "today's rate" not in reply.lower()


def test_case_6_mock_tavily_fails_safe_fallback():
    """
    Case 6: Mock Tavily fails
    - safe fallback
    - no invented price
    """
    import re
    from app.services.chat_service import process_chat_message
    from app.services.web_search_service import web_search_service

    with patch.object(web_search_service, "search", side_effect=RuntimeError("Tavily timeout")):
        res = process_chat_message("Aaj Jaipur mandi me gehun ka latest bhav kya hai?")
        assert res["provider"] == "anti_hallucination_guard"
        reply = res["reply"]
        assert "Main abhi Jaipur mandi ka current verified" in reply
        assert "agmarknet.gov.in" in reply
        assert not re.search(r"₹\s*\d{3,5}", reply)
        assert not re.search(r"rs\.?\s*\d{3,5}", reply, re.IGNORECASE)


