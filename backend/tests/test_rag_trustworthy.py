"""
Maitri Krishi Assistant - Phase 4 Trustworthy RAG Test Suite
-------------------------------------------------------------
Validates:
1. All 8 Mandatory Test Queries (A through H from Section 17):
   - A: "गेहूं के पत्ते पीले क्यों हो रहे हैं?" -> Wheat yellow rust / N deficiency, diagnostic safety
   - B: "धान में सिंचाई कब करनी चाहिए?" -> Rice irrigation, zero wheat contamination
   - C: "मेरी मक्का की फसल में कीड़े लग गए हैं" -> Maize pest / Fall armyworm
   - D: "मिट्टी में nitrogen की कमी कैसे पहचानें?" -> Soil / nitrogen deficiency
   - E: "टमाटर में पत्ते मुड़ रहे हैं" -> Tomato leaf curl / whitefly
   - F: "आज गेहूं का मंडी भाव क्या है?" -> Anti-hallucination intercept: no invented prices
   - G: "कल मेरे खेत में मौसम कैसा रहेगा?" -> Anti-hallucination intercept: no invented forecast
   - H: "asdfghjkl" -> Meaningful question guard
2. Chemical advice guardrails (unsupported chemical treatment referral)
3. Dynamic source linking (1 to 3 sources, exact match, metadata integrity)
4. Official vs Curated classification integrity
"""

import pytest
from app.services.rag_service import query_knowledge_base, is_gibberish
from app.services.chat_service import process_chat_message, check_anti_hallucination_intercept


class TestPhase4KnowledgeIntegrity:
    """Validates source metadata and attribution truthfulness."""

    def test_official_source_metadata_retrieval(self):
        """PM-KISAN query must retrieve official_verified source with official URL."""
        res = query_knowledge_base("PM-KISAN scheme eligibility guidelines", top_k=3)
        assert len(res["chunks"]) > 0
        top_chunk = res["chunks"][0]
        assert top_chunk["source_type"] == "official_verified"
        assert "pmkisan.gov.in" in top_chunk.get("url", "")
        assert "Ministry of Agriculture" in top_chunk["source"]

    def test_curated_source_metadata_retrieval(self):
        """Agronomy guide must be marked curated_reference and NOT claim official ICAR authorship."""
        res = query_knowledge_base("wheat crop production guide", top_k=3)
        assert len(res["chunks"]) > 0
        curated_chunks = [c for c in res["chunks"] if c["crop"] == "Wheat"]
        assert len(curated_chunks) > 0
        top_c = curated_chunks[0]
        assert top_c["source_type"] == "curated_reference"
        assert "Maitri Agronomy Reference Desk" in top_c["source"]


class TestSection17MandatoryQueries:
    """Tests all 8 mandatory queries specified in Phase 4 Section 17."""

    def test_query_a_wheat_yellow_leaves(self):
        """
        Query A: 'गेहूं के पत्ते पीले क्यों हो रहे हैं?'
        Must retrieve Wheat chunks (Yellow Rust and/or Nitrogen deficiency).
        Must reflect diagnostic safety ('संभावित' or 'Possible causes').
        """
        query = "गेहूं के पत्ते पीले क्यों हो रहे हैं?"
        res = process_chat_message(query)

        assert res is not None
        assert res["language"] == "hi"
        assert res["retrieved_chunks"] >= 1
        assert len(res["sources"]) >= 1

        # Must retrieve wheat-specific knowledge
        source_crops = [s.get("crop", "") for s in res["sources"]]
        assert any("wheat" in c.lower() or "general" in c.lower() for c in source_crops)

        # Must not retrieve rice
        assert not any(c.lower() == "rice" for c in source_crops)

        # Response must include diagnostic safety terms
        reply = res["reply"]
        assert any(term in reply for term in ["संभावित", "कारण", "जांचें", "लक्षण", "पीला", "रतुआ", "नाइट्रोजन"])

    def test_query_b_rice_irrigation(self):
        """
        Query B: 'धान में सिंचाई कब करनी चाहिए?'
        Must retrieve Rice irrigation chunks. Must NOT contain wheat/maize contamination.
        """
        query = "धान में सिंचाई कब करनी चाहिए?"
        res = process_chat_message(query)

        assert res["language"] == "hi"
        assert res["retrieved_chunks"] >= 1
        assert len(res["sources"]) >= 1

        # Sources must be Rice
        for s in res["sources"]:
            assert "rice" in s.get("crop", "").lower() or "general" in s.get("crop", "").lower()
            assert "wheat" not in s.get("crop", "").lower()

        # Text must discuss rice water management
        reply = res["reply"].lower()
        assert any(term in reply for term in ["धान", "सिंचाई", "पानी", "कल्ले", "नमी", "कंस"])

    def test_query_c_maize_pests(self):
        """
        Query C: 'मेरी मक्का की फसल में कीड़े लग गए हैं'
        Must retrieve Maize pest / Fall armyworm chunks.
        """
        query = "मेरी मक्का की फसल में कीड़े लग गए हैं"
        res = process_chat_message(query)

        assert res["retrieved_chunks"] >= 1
        assert len(res["sources"]) >= 1

        source_crops = [s.get("crop", "").lower() for s in res["sources"]]
        assert any("maize" in sc or "general" in sc for sc in source_crops)

        reply = res["reply"].lower()
        assert any(term in reply for term in ["मक्का", "फॉल आर्मीवर्म", "सुंडी", "कीट", "पत्ती", "कीड़ा"])

    def test_query_d_soil_nitrogen_deficiency(self):
        """
        Query D: 'मिट्टी में nitrogen की कमी कैसे पहचानें?'
        Must retrieve Soil / Nitrogen deficiency knowledge.
        """
        query = "मिट्टी में nitrogen की कमी कैसे पहचानें?"
        res = process_chat_message(query)

        assert res["retrieved_chunks"] >= 1
        source_categories = [s.get("category", "").lower() for s in res["sources"]]
        assert any(cat in ("soil", "fertilizers", "crops") for cat in source_categories)

        reply = res["reply"].lower()
        assert any(term in reply for term in ["नाइट्रोजन", "nitrogen", "मिट्टी", "सॉइल", "पत्ती", "यूरिया", "जांच"])

    def test_query_e_tomato_leaf_curling(self):
        """
        Query E: 'टमाटर में पत्ते मुड़ रहे हैं'
        Must retrieve Tomato leaf curl virus / whitefly knowledge.
        """
        query = "टमाटर में पत्ते मुड़ रहे हैं"
        res = process_chat_message(query)

        assert res["retrieved_chunks"] >= 1
        source_crops = [s.get("crop", "").lower() for s in res["sources"]]
        assert any("tomato" in sc for sc in source_crops)

        reply = res["reply"].lower()
        assert any(term in reply for term in ["टमाटर", "मरोड़", "सफेद मक्खी", "वायरस", "पर्ण कुंचन", "leaf curl"])

    def test_query_f_mandi_price_anti_hallucination(self):
        """
        Query F: 'आज गेहूं का मंडी भाव क्या है?'
        Must NOT invent live prices. Must intercept and direct to Agmarknet / Mandi Prices tab.
        """
        query = "आज गेहूं का मंडी भाव क्या है?"
        res = process_chat_message(query)

        assert res["provider"] == "anti_hallucination_guard"
        assert res["retrieved_chunks"] == 0
        reply = res["reply"]
        assert "Agmarknet" in reply or "agmarknet.gov.in" in reply or "मंडी भाव" in reply
        # Must not contain fabricated prices like "₹2350/quintal"
        assert "क्विंटल" not in reply or "पोर्टल" in reply

    def test_query_g_weather_forecast_anti_hallucination(self):
        """
        Query G: 'कल मेरे खेत में मौसम कैसा रहेगा?'
        Must NOT invent tomorrow's temperature or weather. Must intercept and direct to IMD / Weather tab.
        """
        query = "कल मेरे खेत में मौसम कैसा रहेगा?"
        res = process_chat_message(query)

        assert res["provider"] == "anti_hallucination_guard"
        assert res["retrieved_chunks"] == 0
        reply = res["reply"]
        assert "IMD" in reply or "मौसम" in reply or "mausam.imd.gov.in" in reply

    def test_query_h_gibberish_guard(self):
        """
        Query H: 'asdfghjkl'
        Must detect gibberish and prompt for a meaningful agriculture question.
        """
        query = "asdfghjkl"
        assert is_gibberish(query) is True

        res = process_chat_message(query)
        assert res["provider"] == "low_confidence_guard"
        assert res["retrieved_chunks"] == 0
        reply = res["reply"]
        assert "पर्याप्त" in reply or "reliable" in reply or "information" in reply

    def test_query_mountain_farming_multilingual(self):
        """
        Urgent Bug Fix Verification:
        Ensures mountain_farming.md is properly retrieved across Hinglish, Hindi, and English
        without contamination from PM-KISAN, Potato, or unrelated documents.
        Also validates that thinking process artifacts are not present.
        """
        queries = [
            "main apne pahadi khet mein kaunsi fasal uga skta hun",
            "मैं अपने पहाड़ी खेत में कौन सी फसल उगा सकता हूं",
            "What crops can I grow in my hilly field?"
        ]

        for q in queries:
            res = query_knowledge_base(q, top_k=3)
            assert len(res["chunks"]) > 0, f"Failed for query: {q}"
            top_chunk = res["chunks"][0]
            # Top chunk MUST be from mountain_farming.md
            assert "पहाड़ी" in top_chunk.get("title", "") or top_chunk.get("category") == "Mountain Farming"
            # Section title should be Best Crops for Mountain Farming
            assert any(term in top_chunk.get("section", "") for term in ["फसलें", "Crops", "खेती", "Farming"])

            # Verify no PM-KISAN or potato contamination in top chunk
            assert "pmkisan" not in top_chunk.get("title", "").lower()
            assert "potato" not in top_chunk.get("title", "").lower()

        # End-to-end test
        chat_res = process_chat_message("main apne pahadi khet mein kaunsi fasal uga skta hun")
        assert chat_res["retrieved_chunks"] >= 1
        assert len(chat_res["sources"]) >= 1
        assert any("पहाड़ी" in s.get("title", "") or "mountain" in s.get("title", "").lower() for s in chat_res["sources"])

        reply = chat_res["reply"]
        assert "Here's a thinking process" not in reply
        assert "Analyze User Input" not in reply
        assert "Identify Key Elements" not in reply
        assert "<think>" not in reply
        assert any(term in reply for term in ["मक्का", "राजमा", "जौ", "रागी", "गेहूं", "ऊँचाई", "फसल"])



class TestChemicalSafetyGuard:
    """Validates Section 6 chemical advice safeguards."""

    def test_unsupported_unknown_pesticide_query(self):
        """Query asking for pesticide for an unknown disease must return KVK referral warning."""
        query = "What exact pesticide should I use for an unknown disease in my crop?"
        res = process_chat_message(query)

        assert res["provider"] == "chemical_safety_guard"
        reply = res["reply"]
        assert "I don't have enough verified information to recommend a specific chemical treatment safely" in reply
        assert "KVK" in reply or "agriculture officer" in reply


class TestSourceLinking:
    """Validates Section 9 and 10 exact source-to-answer linking."""

    def test_source_count_matches_retrieval(self):
        """Only retrieved, relevant sources should be returned (1 to 3 items)."""
        res = process_chat_message("धान में सिंचाई कब करनी चाहिए?")
        sources = res.get("sources", [])
        assert 1 <= len(sources) <= 3
        # Check that metadata fields are preserved
        for s in sources:
            assert "title" in s
            assert "organization" in s
            assert "source_type" in s
