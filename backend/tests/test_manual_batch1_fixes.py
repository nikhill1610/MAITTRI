"""
Regression Test Suite for MAITTRI Manual Test Batch-1 Remediation.

Tests all 9 single-turn defects and 3 multi-turn conversation context defects
discovered during real manual UI testing.
"""

import pytest
from app.services.smart_rag_router import (
    classify_query,
    extract_entities,
    detect_weather_time_scope,
    Intent,
    RouteAction
)
from app.services.chat_service import (
    process_chat_message,
    generate_weather_hybrid_reply,
    generate_grounded_offline_reply,
    classify_current_weather_evidence
)
from app.services.web_search_service import WebEvidence, SourceTier, SourceType


# ==============================================================================
# SECTION C: DIAGNOSIS / SYMPTOM QUESTIONS (Differential Diagnosis)
# ==============================================================================

def test_query_1_wheat_yellowing_differential():
    """
    Query 1: 'गेहूं की पत्तियां पीली क्यों हो रही हैं?'
    Must state 2-4 plausible causes (nitrogen, yellow rust, waterlogging, zinc),
    ask for discriminating details / checks, and not jump immediately to one disease.
    """
    query = "गेहूं की पत्तियां पीली क्यों हो रही हैं?"
    res = process_chat_message(query)

    reply = res["reply"]
    # Check that it provides differential causes rather than jumping to only one disease
    assert any(w in reply for w in ["संभावित", "कारण", "causes", "पीला रतुआ", "नाइट्रोजन", "जलभराव", "पोषक तत्व"])
    assert any(w in reply for w in ["नाइट्रोजन", "Nitrogen", "यूरिया"])
    assert any(w in reply for w in ["पीला रतुआ", "Yellow Rust", "रतुआ"])
    # Check that it asks or mentions simple observations farmer can check
    assert any(w in reply for w in ["जांचें", "चेक", "लक्षण", "check", "हाथ", "पाउडर"])
    assert res["route"] in ("RAG", "GENERAL")


def test_query_2_tomato_leaf_curl_differential():
    """
    Query 2: 'tamatar ke patte curl ho rahe hain, kya problem ho sakti hai?'
    Must state 2-4 plausible causes (leaf curl virus/whitefly, physiological curl/heat, mites/thrips, herbicide drift),
    mention simple field observations, and not jump to a single definitive diagnosis.
    """
    query = "tamatar ke patte curl ho rahe hain, kya problem ho sakti hai?"
    res = process_chat_message(query)

    reply = res["reply"].lower()
    # Check multiple causes mentioned
    assert any(w in reply for w in ["virus", "tlcv", "पर्ण कुंचन", "whitefly", "सफेद मक्खी"])
    assert any(w in reply for w in ["heat", "temperature", "dhoop", "physiological", "पानी", "moisture"])
    assert any(w in reply for w in ["mite", "thrips", "sucking", "कीट"])
    # Field observations to check
    assert any(w in reply for w in ["check", "जांचें", "लक्षण", "upar", "neeche", "curl"])


# ==============================================================================
# SECTION B: RESPONSE INTENT FIDELITY (Fertilizer, Frost, PM-KISAN)
# ==============================================================================

def test_query_3_wheat_urea_dosage():
    """
    Query 3: 'gehun me urea kitna dena chahiye?'
    Must answer exact amount based on ICAR-IIWBR package of practices (100 kg/acre total split into 28 basal + 36 CRI + 36 tillering),
    explicitly cite 45 kg bag weight (~2.2 bags of 45 kg), explain split application, and not invent random dosage.
    Prevents inconsistent conversions like '100–110 kg (2.5 to 3 bags)'.
    """
    query = "gehun me urea kitna dena chahiye?"
    res = process_chat_message(query)

    reply = res["reply"]
    reply_lower = reply.lower()

    # Must specify exact ICAR-IIWBR supported dosage for wheat
    assert "100 kg" in reply or "100 किग्रा" in reply
    assert "36 kg" in reply or "36 किग्रा" in reply
    assert "28 kg" in reply or "28 किग्रा" in reply
    assert any(w in reply_lower for w in ["split", "किस्तों", "टॉप-ड्रेसिंग", "top-dressing", "cri"])

    # Explicit bag weight and exact conversion
    assert "45 kg" in reply or "45 किग्रा" in reply
    assert "2.2" in reply

    # Regression assertions: Prevent inconsistent kg-to-bag conversions
    assert "2.5 to 3 bags" not in reply_lower
    assert "2.5 bags of 45 kg" not in reply_lower
    assert "3 bags" not in reply_lower

    # Conditioning factors mentioned
    assert any(w in reply_lower for w in ["soil", "mitti", "dap", "nitrogen", "irrigat", "sinchai"])
    assert "ICAR-IIWBR" in reply


def test_fertilizer_numeric_fidelity_and_bag_consistency_multilingual():
    """
    Regression assertion verifying strict numeric fidelity and bag weight consistency
    across Hindi, Hinglish, and English for Wheat Urea and DAP recommendations.
    Ensures 45 kg bag standard for Urea and 50 kg bag standard for DAP.
    """
    # 1. Urea queries in Hindi, Hinglish, English
    queries_urea = [
        "गेहूं में यूरिया की मात्रा कितनी होनी चाहिए?",
        "gehun me urea kitna dena chahiye?",
        "How much urea should be applied for wheat crop?"
    ]
    for q in queries_urea:
        res = process_chat_message(q)
        rep = res["reply"]
        rep_l = rep.lower()

        # Numeric fidelity: 100 kg/acre, 28 basal, 36 CRI, 36 tillering
        assert "100" in rep
        assert "28" in rep
        assert "36" in rep

        # Bag weight explicitly stated as 45 kg
        assert "45 kg" in rep or "45 किग्रा" in rep
        assert "2.2" in rep or "२.२" in rep

        # Regression prevention: No inconsistent 2.5 to 3 bags
        assert "2.5 to 3 bags" not in rep_l
        assert "2.5 bags of 45 kg" not in rep_l

        # Source support
        assert "ICAR-IIWBR" in rep

    # 2. DAP query: check 50–55 kg/acre and explicit 50 kg bag weight
    res_dap = process_chat_message("DAP ka double dose de sakte hain?")
    rep_dap = res_dap["reply"]
    assert "50–55" in rep_dap or "50-55" in rep_dap
    assert "50 kg" in rep_dap or "50 किग्रा" in rep_dap
    assert "1 bag" in rep_dap.lower() or "1 बैग" in rep_dap



def test_query_4_dap_double_dose_refusal_and_no_pesticide_boilerplate():
    """
    Query 4: 'DAP ka double dose de sakte hain?'
    Must open with clear refusal: 'No, DAP ka double dose bina soil-test/recommendation ke na dein.'
    Must NOT append pesticide/CIBRC spray boilerplate to fertilizer queries.
    """
    query = "DAP ka double dose de sakte hain?"
    res = process_chat_message(query)

    reply = res["reply"]
    # Required opening or strong refusal
    assert any(phrase in reply for phrase in [
        "No, DAP ka double dose",
        "नहीं, डीएपी की दोगुनी खुराक",
        "dost na dein",
        "double dose na dein",
        "दोगुनी खुराक न दें",
        "bina soil-test"
    ])
    # Crucial: Must NOT contain pesticide/CIBRC spray boilerplate
    assert "CIBRC" not in reply
    assert "कीटनाशक लेबल" not in reply
    assert "chemical spray se pehle mandatory CIBRC" not in reply


def test_query_5_wheat_frost_protection():
    """
    Query 5: 'wheat me pala se bachav kaise kare?'
    Must give actionable frost-protection measures first (light irrigation, smoke/dhuan).
    """
    query = "wheat me pala se bachav kaise kare?"
    res = process_chat_message(query)

    reply = res["reply"].lower()
    # Actionable measures first
    assert any(w in reply for w in ["sinchai", "सिंचाई", "irrigation", "halki sinchai", "हल्की सिंचाई", "light irrigation"])
    assert any(w in reply for w in ["dhuan", "धुआं", "smoke", "मेड़ों", "medo", "borders"])


def test_query_9_pm_kisan_definition_and_eligibility():
    """
    Query 9: 'PM Kisan kya hai aur eligibility kya hai?'
    Must directly explain what PM-KISAN is (Rs 6000/yr in 3 installments),
    main eligibility conditions (landholding farmer families, eKYC, Aadhaar-seed),
    and exclusions. Must not substitute payment-delay troubleshooting.
    """
    query = "PM Kisan kya hai aur eligibility kya hai?"
    res = process_chat_message(query)

    reply = res["reply"]
    # Explains what PM-KISAN is
    assert any(num in reply for num in ["6,000", "6000", "2,000", "2000", "3 किस्त", "3 installment", "तीन किस्तों"])
    # Explains eligibility conditions
    assert any(w in reply.lower() for w in ["eligible", "patrata", "पात्रता", "ekyc", "aadhaar", "आधार", "landholding", "भूमि"])
    # Not just a payment delay FAQ dump
    assert "पात्रता" in reply or "Eligibility" in reply or "eligibility" in reply.lower()


# ==============================================================================
# SECTION D & E: TEMPORAL WEATHER SEMANTICS & CURRENT WEATHER ROUTING
# ==============================================================================

def test_query_6_jaipur_tomorrow_weather():
    """
    Query 6: 'Jaipur me kal barish hogi?'
    Must route to WEATHER_SERVICE with Jaipur and TOMORROW time_scope.
    Must preserve TOMORROW horizon and not silently substitute today.
    """
    query = "Jaipur me kal barish hogi?"
    route = classify_query(query)
    assert route.action == RouteAction.WEATHER_SERVICE
    assert route.intent == Intent.WEATHER
    assert route.detected_entities.get("location") == "Jaipur"
    assert route.detected_entities.get("time_scope") == "TOMORROW"

    # Response verification
    res = process_chat_message(query)
    assert res["route"] == "WEATHER_SERVICE"
    reply = res["reply"].lower()
    # Must preserve 'kal' or 'tomorrow'
    assert "kal" in reply or "कल" in reply or "tomorrow" in reply


def test_query_7_lucknow_tomorrow_weather():
    """
    Query 7: 'Lucknow me kal barish hogi?'
    Must route to WEATHER_SERVICE with Lucknow and TOMORROW time_scope.
    """
    query = "Lucknow me kal barish hogi?"
    route = classify_query(query)
    assert route.action == RouteAction.WEATHER_SERVICE
    assert route.intent == Intent.WEATHER
    assert route.detected_entities.get("location") == "Lucknow"
    assert route.detected_entities.get("time_scope") == "TOMORROW"

    res = process_chat_message(query)
    assert res["route"] == "WEATHER_SERVICE"
    reply = res["reply"].lower()
    assert "kal" in reply or "कल" in reply or "tomorrow" in reply


def test_query_8_meerut_current_weather_no_crop_asked():
    """
    Query 8: 'meerut mein kya abhi baarish ho rhi hai?'
    Must NOT ask for crop/state/growth stage clarification!
    Must route to WEATHER_SERVICE with Meerut and CURRENT time_scope.
    Must not conflate states with 'ya immediate alert' or 'ya cloud alert'.
    """
    query = "meerut mein kya abhi baarish ho rhi hai?"
    route = classify_query(query)
    assert route.action == RouteAction.WEATHER_SERVICE
    assert route.intent == Intent.WEATHER
    assert route.detected_entities.get("location") == "Meerut"
    assert route.detected_entities.get("time_scope") == "CURRENT"

    res = process_chat_message(query)
    assert res["route"] == "WEATHER_SERVICE"
    reply = res["reply"]
    # Must NOT ask for crop or crop age!
    assert "फसल का नाम" not in reply
    assert "Crop name" not in reply
    assert "Crop age" not in reply
    # Must NOT conflate states!
    assert "ya immediate alert" not in reply
    assert "ya cloud alert" not in reply
    assert "possibly raining" not in reply
    assert "baarish ho rahi hai ya alert" not in reply
    # Must match one of the supported 4-state responses
    assert any(phrase in reply for phrase in [
        "Meerut me abhi baarish ho rahi hai.",
        "Meerut me abhi baarish nahi ho rahi hai.",
        "Meerut me abhi baarish confirm nahi hai, lekin rain alert/forecast active hai.",
        "Main Meerut me abhi baarish ho rahi hai ya nahi, ise live source se verify nahi kar pa raha hoon."
    ])


def test_current_weather_rain_confirmed():
    """
    Focused test for CURRENT_RAIN_CONFIRMED state:
    When evidence confirms active ongoing rain in Meerut, response must state
    'Meerut me abhi baarish ho rahi hai.' and not conflate with alert/cloud.
    """
    evidence = [
        WebEvidence(
            title="Local Weather Observation for Meerut",
            url="https://city.imd.gov.in/meerut",
            domain="city.imd.gov.in",
            content="Currently raining with light drizzle in Meerut right now. Present weather: Light rain. Temperature 27C.",
            score=0.95,
            source_tier=SourceTier.AUTHORITATIVE,
            source_type=SourceType.LIVE_WEB_OFFICIAL
        )
    ]
    state = classify_current_weather_evidence(" ".join([f"{e.title} {e.content}" for e in evidence]), live_verified=True)
    assert state == "CURRENT_RAIN_CONFIRMED"

    reply = generate_weather_hybrid_reply(
        query="Meerut mein kya abhi baarish ho rhi hai?",
        language="hinglish",
        location="Meerut",
        live_verified=True,
        weather_evidence=evidence,
        time_scope="CURRENT"
    )
    assert "Meerut me abhi baarish ho rahi hai." in reply
    assert "ya immediate alert" not in reply
    assert "ya cloud alert" not in reply
    assert "possibly raining" not in reply
    assert "baarish ho rahi hai ya alert" not in reply


def test_current_weather_no_rain_confirmed():
    """
    Focused test for CURRENT_NO_RAIN_CONFIRMED state:
    When evidence confirms clear/dry conditions with no rain, response must state
    'Meerut me abhi baarish nahi ho rahi hai.'
    """
    evidence = [
        WebEvidence(
            title="Meerut Current Weather Observation",
            url="https://city.imd.gov.in/meerut",
            domain="city.imd.gov.in",
            content="Current weather for Meerut: Clear skies, sunny and dry weather, temperature 32C, no rain observed.",
            score=0.95,
            source_tier=SourceTier.AUTHORITATIVE,
            source_type=SourceType.LIVE_WEB_OFFICIAL
        )
    ]
    state = classify_current_weather_evidence(" ".join([f"{e.title} {e.content}" for e in evidence]), live_verified=True)
    assert state == "CURRENT_NO_RAIN_CONFIRMED"

    reply = generate_weather_hybrid_reply(
        query="Meerut mein kya abhi baarish ho rhi hai?",
        language="hinglish",
        location="Meerut",
        live_verified=True,
        weather_evidence=evidence,
        time_scope="CURRENT"
    )
    assert "Meerut me abhi baarish nahi ho rahi hai." in reply
    assert "ya immediate alert" not in reply
    assert "ya cloud alert" not in reply
    assert "possibly raining" not in reply


def test_current_weather_forecast_alert_only():
    """
    Focused test for FORECAST_OR_ALERT_ONLY state:
    When evidence mentions a rain warning, thunderstorm alert, or precipitation forecast
    active for Meerut, but active current rain is not confirmed, response must state
    'Meerut me abhi baarish confirm nahi hai, lekin rain alert/forecast active hai.'
    """
    evidence = [
        WebEvidence(
            title="IMD Weather Warning Bulletin",
            url="https://city.imd.gov.in/meerut",
            domain="city.imd.gov.in",
            content="Yellow alert for heavy rain and thunderstorm issued for Meerut district today. Precipitation forecast active.",
            score=0.95,
            source_tier=SourceTier.AUTHORITATIVE,
            source_type=SourceType.LIVE_WEB_OFFICIAL
        )
    ]
    state = classify_current_weather_evidence(" ".join([f"{e.title} {e.content}" for e in evidence]), live_verified=True)
    assert state == "FORECAST_OR_ALERT_ONLY"

    reply = generate_weather_hybrid_reply(
        query="Meerut mein kya abhi baarish ho rhi hai?",
        language="hinglish",
        location="Meerut",
        live_verified=True,
        weather_evidence=evidence,
        time_scope="CURRENT"
    )
    assert "Meerut me abhi baarish confirm nahi hai, lekin rain alert/forecast active hai." in reply
    assert "ya immediate alert" not in reply
    assert "ya cloud alert" not in reply
    assert "possibly raining" not in reply


def test_current_weather_condition_unverified():
    """
    Focused test for CURRENT_CONDITION_UNVERIFIED state:
    When live weather evidence is absent, failed, or cannot distinguish current conditions
    (e.g., generic IMD web portal with no live telemetry), response must state
    'Main Meerut me abhi baarish ho rahi hai ya nahi, ise live source se verify nahi kar pa raha hoon.'
    """
    # 1. Unverified because live_verified=False
    reply_unverified = generate_weather_hybrid_reply(
        query="Meerut mein kya abhi baarish ho rhi hai?",
        language="hinglish",
        location="Meerut",
        live_verified=False,
        weather_evidence=[],
        time_scope="CURRENT"
    )
    assert "Main Meerut me abhi baarish ho rahi hai ya nahi, ise live source se verify nahi kar pa raha hoon." in reply_unverified
    assert "ya immediate alert" not in reply_unverified
    assert "possibly raining" not in reply_unverified

    # 2. Unverified because evidence is a generic portal without current observation
    generic_evidence = [
        WebEvidence(
            title="National Weather Forecasting Centre",
            url="https://mausam.imd.gov.in",
            domain="mausam.imd.gov.in",
            content="India Meteorological Department city forecast links, radar maps, and regional center directory.",
            score=0.95,
            source_tier=SourceTier.AUTHORITATIVE,
            source_type=SourceType.LIVE_WEB_OFFICIAL
        )
    ]
    reply_generic = generate_weather_hybrid_reply(
        query="Meerut mein kya abhi baarish ho rhi hai?",
        language="hinglish",
        location="Meerut",
        live_verified=True,
        weather_evidence=generic_evidence,
        time_scope="CURRENT"
    )
    assert "Main Meerut me abhi baarish ho rahi hai ya nahi, ise live source se verify nahi kar pa raha hoon." in reply_generic
    assert "ya immediate alert" not in reply_generic


# ==============================================================================
# SECTION F & G: MULTI-TURN CONVERSATION CONTEXT & ELLIPSIS / PRONOUNS
# ==============================================================================

def test_query_10_multiturn_wheat_context_retention():
    """
    Multi-turn Test 10:
    Turn 1: 'mere gehun ko 22 din hue hain'
    Turn 2: 'sinchai kab karu?'
    Assert second turn inherits Wheat + 22 days, responds with Wheat CRI guidance,
    and MUST NOT retrieve or respond with Rice irrigation.
    """
    turn1_user = "mere gehun ko 22 din hue hain"
    res1 = process_chat_message(turn1_user)

    history = [
        {"role": "user", "content": turn1_user},
        {"role": "assistant", "content": res1["reply"]}
    ]

    turn2_user = "sinchai kab karu?"
    res2 = process_chat_message(turn2_user, history=history)

    reply2 = res2["reply"]
    # Second turn must be for Wheat (CRI stage, ~20-25 days)
    assert any(w in reply2.lower() for w in ["cri", "crown root", "ताज मूल", "20–25", "20-25", "22 din", "gehun", "गेहूं", "wheat"])
    # Second turn MUST NOT be about Rice
    assert "धान" not in reply2
    assert "rice" not in reply2.lower()
    assert "awd" not in reply2.lower()


def test_query_11_multiturn_pronoun_red_gram_pod_borer():
    """
    Multi-turn Test 11:
    Turn 1: 'red gram pod borer ka management kya hai?'
    Turn 2: 'is ka ilaj?'
    Assert second turn resolves 'is' to Pigeonpea/Red Gram + Pod Borer (IPM, pheromone, neem/HaNPV).
    Must not perform broad search for unrelated sugarcane/rice borers.
    """
    turn1_user = "red gram pod borer ka management kya hai?"
    res1 = process_chat_message(turn1_user)

    history = [
        {"role": "user", "content": turn1_user},
        {"role": "assistant", "content": res1["reply"]}
    ]

    turn2_user = "is ka ilaj?"
    res2 = process_chat_message(turn2_user, history=history)

    reply2 = res2["reply"]
    # Must refer to Red Gram / Arhar / Pod Borer / IPM
    assert any(w in reply2.lower() for w in ["pod borer", "फली छेदक", "arhar", "red gram", "pigeonpea", "pheromone", "neem", "hanpv"])
    # Must NOT discuss sugarcane or rice stem borer
    assert "sugarcane" not in reply2.lower()
    assert "ganna" not in reply2.lower()
    assert "dhan" not in reply2.lower()


def test_query_12_multiturn_crop_topic_override():
    """
    Multi-turn Test 12:
    Turn 1: 'mere gehun ko 22 din hue hain'
    Turn 2: 'sinchai kab karu?'
    Turn 3: 'ab tomato me leaf curl ke bare me batao'
    Assert explicit Tomato in Turn 3 strictly overrides previous Wheat context.
    """
    history = [
        {"role": "user", "content": "mere gehun ko 22 din hue hain"},
        {"role": "assistant", "content": "Gehun me 20-25 din par CRI stage me pehli sinchai karein."},
        {"role": "user", "content": "sinchai kab karu?"},
        {"role": "assistant", "content": "CRI stage par halki sinchai karein."}
    ]

    turn3_user = "ab tomato me leaf curl ke bare me batao"
    res3 = process_chat_message(turn3_user, history=history)

    reply3 = res3["reply"]
    # Must be about Tomato and Leaf Curl
    assert any(w in reply3.lower() for w in ["tomato", "tamatar", "टमाटर", "leaf curl", "whitefly", "पर्ण कुंचन"])
    assert res3["detected_entities"].get("crop") == "Tomato"
    # Stale wheat context must not dominate
    assert "cri" not in reply3.lower()
    assert "crown root" not in reply3.lower()
