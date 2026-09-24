import pytest
from unittest.mock import patch
from app.services.chat_service import (
    process_chat_message,
    extract_issuing_authority,
    extract_scheme_structured_evidence,
    compose_scheme_fallback_response,
    APPROVED_PMFBY_DOMAINS,
    FOREIGN_UNRELATED_PATTERNS,
)
from app.services.web_search_service import (
    web_search_service,
    _SEARCH_CACHE,
    WebEvidence,
    SourceTier,
    SourceType,
    is_scheme_policy_query,
)


REQUIRED_FALLBACK_SENTENCE = (
    "Mujhe official Indian government sources se 2026 ke specific naye PMFBY "
    "rule changes verify nahi mile. Main unrelated ya outdated documents ko "
    "latest PMFBY rules ke roop me present nahi karunga."
)


def test_scheme_gate_a_valid_dated_2026_notification_accepted():
    """
    Test A: PMFBY query + valid dated 2026 pmfby.gov.in notification -> accepted.
    """
    mock_ev = WebEvidence(
        title="PMFBY Revised Operational Guidelines 2026",
        url="https://pmfby.gov.in/files/guidelines_2026.pdf",
        domain="pmfby.gov.in",
        content=(
            "Ministry of Agriculture & Farmers Welfare notification dated 15-02-2026: "
            "Pradhan Mantri Fasal Bima Yojana (PMFBY) claim processing window reduced to 15 days "
            "post crop cutting experiments for Kharif 2026."
        ),
        score=0.96,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-02-15"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "tavily_scheme"
        assert res["live_lookup_result"] == "verified_scheme_rule_found"
        assert res["rejection_reason"] is None
        reply = res["reply"]
        assert "2026" in reply
        assert "pmfby.gov.in" in reply
        assert "Ministry of Agriculture" in reply
        assert "15 days" in reply or "claim" in reply.lower()


def test_scheme_gate_b_fedramp_gov_2026_rules_rejected():
    """
    Test B: PMFBY query + fedramp.gov 2026 rules -> rejected.
    """
    mock_ev = WebEvidence(
        title="FedRAMP Consolidated Rules for 2026",
        url="https://fedramp.gov/2026/rules",
        domain="fedramp.gov",
        content="General Services Administration: Updated cloud security baseline guidelines effective 2026.",
        score=0.92,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-10"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_result"] != "verified_scheme_rule_found"
        reply = res["reply"]
        assert "fedramp" not in reply.lower()
        assert "cloud security" not in reply.lower()
        assert REQUIRED_FALLBACK_SENTENCE in reply


def test_scheme_gate_c_hhs_2026_poverty_guidelines_rejected():
    """
    Test C: PMFBY query + HHS 2026 poverty guidelines -> rejected.
    """
    mock_ev = WebEvidence(
        title="2026 Poverty Guidelines",
        url="https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines",
        domain="aspe.hhs.gov",
        content="U.S. Department of Health and Human Services: 2026 poverty guidelines for federal programs and eligibility.",
        score=0.91,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-20"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_result"] != "verified_scheme_rule_found"
        reply = res["reply"]
        assert "hhs" not in reply.lower()
        assert "poverty" not in reply.lower()
        assert REQUIRED_FALLBACK_SENTENCE in reply


def test_scheme_gate_d_unrelated_indian_gov_page_rejected():
    """
    Test D: PMFBY query + unrelated Indian government 2026 page
    -> rejected unless PMFBY relevance is explicitly established.
    """
    # Case 1: Indian .gov.in domain but completely unrelated to PMFBY
    mock_ev_unrelated = WebEvidence(
        title="CBIC Customs Circular 2026",
        url="https://cbic.gov.in/circular_2026.pdf",
        domain="cbic.gov.in",
        content="Central Board of Indirect Taxes and Customs notification dated 05-01-2026: Revision of tariff values on edible oils.",
        score=0.88,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-05"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev_unrelated]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_result"] in ("unrelated_indian_gov_domain_rejected", "unrelated_scheme_evidence_rejected", "no_verified_2026_rule")
        reply = res["reply"]
        assert "CBIC" not in reply
        assert "edible oils" not in reply
        assert REQUIRED_FALLBACK_SENTENCE in reply

    # Case 2: Indian official domain (pib.gov.in) with explicit PMFBY relevance established
    mock_ev_pib_pmfby = WebEvidence(
        title="Cabinet approves revamped PMFBY norms for 2026",
        url="https://pib.gov.in/PressReleasePage.aspx?PRID=202601",
        domain="pib.gov.in",
        content="PIB Press Release dated 10-02-2026: Ministry of Agriculture and Farmers Welfare announces streamlined Pradhan Mantri Fasal Bima Yojana guidelines for digital claim processing.",
        score=0.95,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-02-10"
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev_pib_pmfby]):
        res2 = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res2["provider"] == "tavily_scheme"
        assert res2["live_lookup_result"] == "verified_scheme_rule_found"
        assert "pib.gov.in" in res2["reply"]
        assert "2026" in res2["reply"]


def test_scheme_gate_e_valid_pmfby_page_no_date_not_called_latest():
    """
    Test E: PMFBY query + valid PMFBY page but no date -> not called latest 2026.
    """
    mock_ev = WebEvidence(
        title="PMFBY Coverage and Eligibility",
        url="https://pmfby.gov.in/coverage",
        domain="pmfby.gov.in",
        content="Pradhan Mantri Fasal Bima Yojana covers all food and oilseeds crops with comprehensive loss indemnity.",
        score=0.89,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date=None
    )

    with patch.object(web_search_service, "search", return_value=[mock_ev]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_result"] == "undated_page_rejected"
        assert res["rejection_reason"] == "undated_evidence_rejected"
        reply = res["reply"]
        assert REQUIRED_FALLBACK_SENTENCE in reply
        assert "General/Background Information" in reply


def test_scheme_gate_f_fedramp_gov_never_labeled_ministry_of_agriculture():
    """
    Test F: source domain says fedramp.gov but generated authority says
    Ministry of Agriculture -> hard test failure.
    Ensures domain and issuing authority are never mismatched or fabricated.
    """
    # Direct authority extraction check:
    # Foreign domains must never receive Ministry of Agriculture & Farmers Welfare attribution
    text_with_fake_mention = (
        "FedRAMP cloud rules 2026. Some text mentioning Ministry of Agriculture & Farmers Welfare."
    )
    auth_foreign = extract_issuing_authority(text_with_fake_mention, "fedramp.gov")
    assert auth_foreign != "Ministry of Agriculture & Farmers Welfare, GoI"
    assert auth_foreign != "Ministry of Agriculture and Farmers Welfare"

    # End-to-end check:
    mock_ev_sneaky = WebEvidence(
        title="Rules 2026",
        url="https://fedramp.gov/pmfby_fake",
        domain="fedramp.gov",
        content="Pradhan Mantri Fasal Bima Yojana rules 2026 from Ministry of Agriculture & Farmers Welfare.",
        score=0.99,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-01"
    )

    notifs, rej_code, rej_reason = extract_scheme_structured_evidence(
        [mock_ev_sneaky], scheme="PMFBY", target_year="2026"
    )
    # Must be completely rejected by Gate 1 (Strict Source Authority Gate)
    assert len(notifs) == 0
    assert rej_code in ("unauthorized_domain_rejected", "foreign_or_unauthorized_domain_rejected")

    # Full chat service check:
    with patch.object(web_search_service, "search", return_value=[mock_ev_sneaky]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        reply = res["reply"]
        # Under no circumstance should fedramp be accepted or attributed
        assert "fedramp.gov" not in reply or "General/Background" in reply
        assert REQUIRED_FALLBACK_SENTENCE in reply


def test_scheme_gate_g_no_valid_current_evidence_safe_fallback():
    """
    Test G: No valid current evidence
    -> safe fallback with exact sentence and no fabricated policy update.
    """
    with patch.object(web_search_service, "search", return_value=[]):
        res = process_chat_message("PMFBY ke latest rules 2026 kya hain?")
        assert res["provider"] == "anti_hallucination_guard"
        assert res["live_lookup_result"] in ("no_results_found", "no_verified_2026_rule")
        reply = res["reply"]
        assert REQUIRED_FALLBACK_SENTENCE in reply
        assert "General/Background Information" in reply
        # Verify stable premium rates are present without fabricating 2026 rule changes
        assert "1.5%" in reply
        assert "2.0%" in reply
        assert "5.0%" in reply
        # No fake new 2026 rule bullet
        assert "Verified Updates" not in reply


def test_pm_kisan_query_variants_scheme_gate_and_authority_validation():
    """
    Focused Regression Test: PM-KISAN query variants ('pm kisan', 'pm-kisan', 'pmkisan')
    must all enter the government-scheme freshness/security gate and strictly filter out
    foreign/unauthorized domains (e.g., fedramp.gov, aspe.hhs.gov).
    """
    ev_fedramp = WebEvidence(
        title="FedRAMP Rules 2026",
        url="https://fedramp.gov/2026/rules",
        domain="fedramp.gov",
        content="FedRAMP cloud security rules 2026",
        score=0.92,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-10"
    )
    ev_hhs = WebEvidence(
        title="HHS Guidelines 2026",
        url="https://aspe.hhs.gov/guidelines",
        domain="aspe.hhs.gov",
        content="HHS federal poverty guidelines 2026",
        score=0.91,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-20"
    )
    ev_pmkisan = WebEvidence(
        title="PM-Kisan Operational Guidelines 2026",
        url="https://pmkisan.gov.in/guidelines_2026.pdf",
        domain="pmkisan.gov.in",
        content="Ministry of Agriculture: PM-Kisan Samman Nidhi revised guidelines 2026",
        score=0.96,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-02-01"
    )

    queries = [
        "pm kisan latest rules 2026",
        "pm-kisan latest rules 2026",
        "pmkisan latest rules 2026"
    ]

    for q in queries:
        _SEARCH_CACHE.clear()
        with patch.object(web_search_service.provider, "search", return_value=[ev_fedramp, ev_hhs, ev_pmkisan]):
            results = web_search_service.search(query=q, freshness_needed=True)
            domains = [r.domain for r in results]
            # All three variants must activate the scheme gate
            assert "fedramp.gov" not in domains
            assert "aspe.hhs.gov" not in domains
            assert "pmkisan.gov.in" in domains

    # Verify foreign .gov result cannot bypass authority gate for 'pm kisan latest rules 2026'
    _SEARCH_CACHE.clear()
    with patch.object(web_search_service.provider, "search", return_value=[ev_fedramp]):
        results_foreign = web_search_service.search(query="pm kisan latest rules 2026", freshness_needed=True)
        # Foreign domain must be completely rejected by the scheme policy gate
        assert len(results_foreign) == 0


def test_all_scheme_query_variants_hindi_and_latin_enter_secure_authority_gate():
    """
    Verify all Latin and Hindi scheme query variants enter the SAME secure scheme authority gate:
    A. 'pm kisan latest rules 2026'
    B. 'pm-kisan latest rules 2026'
    C. 'pmkisan latest rules 2026'
    D. 'kisan credit card latest rules 2026'
    E. 'फसल बीमा के नए नियम 2026 क्या हैं?'
    F. 'पीएम किसान के नए नियम 2026 क्या हैं?'
    G. 'किसान क्रेडिट कार्ड के latest rules क्या हैं?'

    For D-G (and all A-G):
    - foreign .gov evidence such as fedramp.gov / hhs.gov must be rejected
    - approved Indian government evidence may proceed through the existing relevance/date gates
    - no foreign result may bypass the authority filter
    """
    queries = [
        "pm kisan latest rules 2026",
        "pm-kisan latest rules 2026",
        "pmkisan latest rules 2026",
        "kisan credit card latest rules 2026",
        "फसल बीमा के नए नियम 2026 क्या हैं?",
        "पीएम किसान के नए नियम 2026 क्या हैं?",
        "किसान क्रेडिट कार्ड के latest rules क्या हैं?",
    ]

    ev_fedramp = WebEvidence(
        title="FedRAMP Cloud Security Guidelines 2026",
        url="https://fedramp.gov/2026/rules",
        domain="fedramp.gov",
        content="FedRAMP cloud security baseline rules 2026",
        score=0.92,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-10"
    )
    ev_hhs = WebEvidence(
        title="HHS Poverty Guidelines 2026",
        url="https://aspe.hhs.gov/guidelines",
        domain="aspe.hhs.gov",
        content="HHS federal poverty guidelines 2026",
        score=0.91,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-01-20"
    )
    ev_approved_gov = WebEvidence(
        title="Official Government Scheme Notification 2026",
        url="https://pmfby.gov.in/guidelines_2026.pdf",
        domain="pmfby.gov.in",
        content="Official scheme notification guidelines 2026",
        score=0.96,
        source_tier=SourceTier.AUTHORITATIVE,
        source_type=SourceType.LIVE_WEB_OFFICIAL,
        published_date="2026-02-01"
    )

    for q in queries:
        assert is_scheme_policy_query(q) is True, f"Query '{q}' must be recognized as a scheme policy query"
        _SEARCH_CACHE.clear()
        with patch.object(web_search_service.provider, "search", return_value=[ev_fedramp, ev_hhs, ev_approved_gov]):
            results = web_search_service.search(query=q, freshness_needed=True)
            domains = [r.domain for r in results]
            # Foreign .gov domains must be rejected by the scheme policy gate
            assert "fedramp.gov" not in domains, f"fedramp.gov should have been rejected for '{q}'"
            assert "aspe.hhs.gov" not in domains, f"aspe.hhs.gov should have been rejected for '{q}'"
            # Approved Indian government domain must proceed
            assert "pmfby.gov.in" in domains, f"pmfby.gov.in should have been preserved for '{q}'"

    # Verify foreign result cannot bypass the authority filter when returned alone for D-G
    for q in [
        "kisan credit card latest rules 2026",
        "फसल बीमा के नए नियम 2026 क्या हैं?",
        "पीएम किसान के नए नियम 2026 क्या हैं?",
        "किसान क्रेडिट कार्ड के latest rules क्या हैं?",
    ]:
        _SEARCH_CACHE.clear()
        with patch.object(web_search_service.provider, "search", return_value=[ev_fedramp]):
            results = web_search_service.search(query=q, freshness_needed=True)
            assert len(results) == 0, f"Foreign result bypassed authority gate for '{q}'"


def test_unrelated_hindi_sentence_with_kisan_does_not_trigger_scheme_gate():
    """
    Negative test proving an unrelated Hindi sentence containing 'किसान' alone
    does NOT automatically become a scheme-freshness query.
    """
    unrelated_queries = [
        "किसान खेत में हल चला रहा है",
        "किसान भाई आज कौन सी फसल बोएं?",
        "एक किसान अपनी फसल को पानी कैसे दे?",
        "किसान के पास 5 एकड़ जमीन है",
    ]
    for q in unrelated_queries:
        assert is_scheme_policy_query(q) is False, f"Unrelated query '{q}' should NOT match scheme query pattern"


