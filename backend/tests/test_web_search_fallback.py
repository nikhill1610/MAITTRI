import pytest
from unittest.mock import MagicMock, patch
from app.services.web_search_service import (
    WebSearchService,
    TavilySearchProvider,
    WebEvidence,
    SourceTier,
    SourceType,
    classify_domain_tier,
    sanitize_and_enrich_query,
)
from app.services.smart_rag_router import classify_query, RouteAction, Intent


def test_web_search_service_initialization():
    service = WebSearchService()
    assert service.enabled is True
    assert isinstance(service.provider, TavilySearchProvider)


def test_web_search_domain_tiering():
    # Tier 1 domain
    assert classify_domain_tier("agricoop.gov.in") == SourceTier.AUTHORITATIVE
    # Tier 2 domain
    assert classify_domain_tier("icar.org.in") == SourceTier.AUTHORITATIVE
    assert classify_domain_tier("pau.edu") == SourceTier.INSTITUTIONAL
    assert classify_domain_tier("hau.ac.in") == SourceTier.INSTITUTIONAL
    # Excluded low-trust domains
    assert classify_domain_tier("wikipedia.org") is None
    assert classify_domain_tier("quora.com") is None
    assert classify_domain_tier("reddit.com") is None


def test_pii_sanitization():
    clean = sanitize_and_enrich_query(
        "Mera naam Ramesh Patel hai phone 9876543210 what is wheat MSP?",
        crop="wheat",
        location="Varanasi",
        freshness_needed=True
    )
    assert "9876543210" not in clean
    assert "Ramesh Patel" not in clean
    assert "wheat" in clean.lower()
    assert "2026" in clean


def test_smart_rag_router_explicit_freshness():
    decision = classify_query("what is the latest yellow rust disease advisory for punjab today?")
    assert decision.action in (RouteAction.WEB_SEARCH, RouteAction.RAG_WEB_FALLBACK)


def test_mock_tavily_search_execution():
    provider = TavilySearchProvider(api_key="dummy_key")
    mock_response = {
        "results": [
            {
                "title": "Wheat MSP Announcement 2025-26",
                "url": "https://agricoop.gov.in/wheat-msp",
                "content": "Government has declared wheat MSP at Rs 2425 per quintal.",
                "score": 0.95,
                "published_date": "2025-10-15"
            }
        ]
    }
    with patch("httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_instance.post.return_value = mock_resp
        mock_instance.__enter__.return_value = mock_instance
        mock_client.return_value = mock_instance

        results = provider.search("wheat MSP 2025")
        assert len(results) == 1
        assert results[0].source_tier == SourceTier.AUTHORITATIVE
        assert results[0].source_type == SourceType.LIVE_WEB_OFFICIAL
        assert "2425" in results[0].content
