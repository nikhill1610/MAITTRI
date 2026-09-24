"""
MAITTRI Trusted Live Web Search Fallback Service
------------------------------------------------
Provides controlled external agricultural retrieval via Tavily Search API
when internal deterministic services and curated RAG knowledge base lack
sufficient or recent evidence.

Strict Architecture Principles:
- Provider-agnostic abstraction (WebSearchService -> TavilySearchProvider).
- Two-stage retrieval: Stage 1 (Authoritative/Institutional Indian domains), Stage 2 (Reputable broader web).
- Strict low-trust exclusions (no Reddit, Quora, social media, blogs, SEO farms).
- Zero PII in search queries (sanitizes user names, phone, Aadhaar, private farm IDs).
- Resilient error handling (timeout, 401, 429, 500 degrade gracefully to empty evidence).
- In-memory TTL caching for public queries to minimize API cost and latency.
"""

import os
import re
import time
import threading
import logging
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("maitri.web_search_service")

# -----------------------------------------------------------------------------
# Enums & Data Models
# -----------------------------------------------------------------------------

class SourceTier(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"      # Tier 1: Official GoI, State Agri Depts, ICAR, IMD, PMFBY
    INSTITUTIONAL = "INSTITUTIONAL"      # Tier 2: State Agri Universities, KVKs, *.ac.in, Research Bodies
    GENERAL_WEB = "GENERAL_WEB"          # Tier 3: Reputable general web (subject to strict exclusion list)


class SourceType(str, Enum):
    LIVE_WEB_OFFICIAL = "LIVE_WEB_OFFICIAL"
    LIVE_WEB_INSTITUTIONAL = "LIVE_WEB_INSTITUTIONAL"
    LIVE_WEB_GENERAL = "LIVE_WEB_GENERAL"


@dataclass
class WebEvidence:
    title: str
    url: str
    domain: str
    content: str
    score: float
    source_tier: SourceTier
    source_type: SourceType
    published_date: Optional[str] = None
    retrieved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "domain": self.domain,
            "content": self.content,
            "score": round(self.score, 3),
            "source_tier": self.source_tier.value,
            "source_type": self.source_type.value,
            "published_date": self.published_date,
            "retrieved_at": self.retrieved_at,
            # Backward-compatible fields with MAITTRI SourceItem
            "source": self.domain,
            "organization": self.domain,
            "section": "Live Web Advisory" if self.source_tier == SourceTier.AUTHORITATIVE else "Web Evidence",
            "category": "Web Intelligence"
        }


# -----------------------------------------------------------------------------
# Domain Whitelists & Exclusion Lists
# -----------------------------------------------------------------------------

# Tier 1: Authoritative Government & ICAR Domains
TIER_1_AUTHORITATIVE_DOMAINS = [
    "icar.gov.in",
    "icar.org.in",
    "agriwelfare.gov.in",
    "agricoop.nic.in",
    "agriculture.gov.in",
    "egazette.gov.in",
    "imd.gov.in",
    "mausam.imd.gov.in",
    "agmarknet.gov.in",
    "pmfby.gov.in",
    "pmkisan.gov.in",
    "data.gov.in",
    "pib.gov.in",
    "enam.gov.in",
    "soilhealth.dac.gov.in",
    "seednet.gov.in",
    "upagripardarshi.gov.in",
    "krishi.up.gov.in",
    "mpkrishi.mp.gov.in",
    "agri.punjab.gov.in",
    "krishi.maharashtra.gov.in",
    "rkvy.nic.in",
    "iari.res.in",
    "crida.in",
    "iiwr.icar.gov.in",
    "cibrc.nic.in"
]

# Tier 2: State Agricultural Universities & Research Institutes
TIER_2_INSTITUTIONAL_DOMAINS = [
    "pau.edu",
    "hau.ac.in",
    "gbpuat.ac.in",
    "tnau.ac.in",
    "angrau.ac.in",
    "bau.edu.in",
    "sknau.ac.in",
    "uasbangalore.edu.in",
    "csauk.ac.in",
    "nduat.org",
    "kau.in",
    "icar-iari.res.in",
    "iisr.icar.gov.in",
    "dwr.icar.gov.in"
]

# Default Low-Trust & Non-Authoritative Exclusions
LOW_TRUST_DOMAINS = {
    "reddit.com",
    "quora.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "tiktok.com",
    "medium.com",
    "blogspot.com",
    "wordpress.com",
    "amazon.in",
    "amazon.com",
    "flipkart.com",
    "indiamart.com",
    "tradeindia.com",
    "wikipedia.org",  # Helpful for definitions, but not primary source for official govt rules
    "alibaba.com"
}


def extract_domain(url: str) -> str:
    """Extracts lowercase clean domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def classify_domain_tier(domain: str) -> Optional[SourceTier]:
    """Classifies domain into Authoritative, Institutional, General, or Excluded."""
    clean = domain.lower().strip()
    if not clean:
        return None

    # Check low-trust exclusions first
    for bad in LOW_TRUST_DOMAINS:
        if clean == bad or clean.endswith("." + bad):
            return None

    # Tier 1: Check explicit authoritative domains or .gov.in / .nic.in
    for auth in TIER_1_AUTHORITATIVE_DOMAINS:
        if clean == auth or clean.endswith("." + auth):
            return SourceTier.AUTHORITATIVE
    if clean.endswith(".gov.in") or clean.endswith(".nic.in"):
        return SourceTier.AUTHORITATIVE

    # Tier 2: Check institutional domains or *.ac.in / educational agriculture
    for inst in TIER_2_INSTITUTIONAL_DOMAINS:
        if clean == inst or clean.endswith("." + inst):
            return SourceTier.INSTITUTIONAL
    if clean.endswith(".ac.in") or clean.endswith(".edu.in") or clean.endswith(".res.in"):
        return SourceTier.INSTITUTIONAL

    # Tier 3: Reputable general web
    return SourceTier.GENERAL_WEB


# -----------------------------------------------------------------------------
# Query Sanitization & PII Removal (Section 14 & 15)
# -----------------------------------------------------------------------------

def sanitize_and_enrich_query(
    user_query: str,
    crop: Optional[str] = None,
    location: Optional[str] = None,
    freshness_needed: bool = True
) -> str:
    """
    Strips farmer PII (name, phone, Aadhaar, IDs, JWT) and builds a focused,
    concise, India-targeted search query.
    """
    clean = user_query.strip()

    # 1. Strip phone numbers (10 digits with optional +91 or dashes)
    clean = re.sub(r"(?:\+91[\-\s]?)?[6-9]\d{9}", "", clean)

    # 2. Strip Aadhaar patterns (spaced, hyphenated, or contiguous 12-digit)
    clean = re.sub(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b", "", clean)

    # 3. Strip JWT tokens or hex IDs
    clean = re.sub(r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+", "", clean)
    clean = re.sub(r"\b[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}", "", clean)

    # 4. Strip introductory farmer PII phrases (ensuring agricultural schemes like PM-KISAN are preserved)
    clean = re.sub(r"(?<!pm[\-\s])\b(?:my name is|mera naam|farmer)\s+[A-Za-z\u0900-\u097F]+[\s,.]*", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bkisan\s+naam\s*[:=]?\s*[A-Za-z\u0900-\u097F]+", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"(?:farm id|user id|account)\s*[:=]?\s*\w+", " ", clean, flags=re.IGNORECASE)

    # 5. Clean excess whitespace
    clean = " ".join(clean.split()).strip()

    # 6. Deterministic Query Enrichment
    terms = [clean]

    # Add crop context if known and not already present
    if crop and crop.lower() not in clean.lower():
        terms.append(crop)

    # Add location (District / State) if known and not already present
    if location and location.lower() not in clean.lower():
        # Keep only district/state part if full address
        loc_part = location.split(",")[0].strip()
        if loc_part:
            terms.append(loc_part)

    # Add India & year context if freshness requested
    if freshness_needed:
        current_year = str(datetime.now().year)
        if current_year not in clean:
            terms.append(current_year)
        if not any(k in clean.lower() for k in ["india", "up", "uttar pradesh", "haryana", "punjab", "mp", "maharashtra", "bihar"]):
            terms.append("India")
        if "government" not in clean.lower() and "sarkar" not in clean.lower():
            terms.append("government agriculture")

    return " ".join(terms)


# -----------------------------------------------------------------------------
# In-Memory Query Cache (Section 30)
# -----------------------------------------------------------------------------

class SafeSearchCache:
    """Thread-safe in-memory cache with TTL to avoid redundant web API queries."""
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[float, List[WebEvidence]]] = {}

    def get(self, key: str) -> Optional[List[WebEvidence]]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            cached_time, results = entry
            if time.time() - cached_time > self.ttl:
                del self._store[key]
                return None
            return results

    def set(self, key: str, results: List[WebEvidence]):
        with self._lock:
            # Limit cache size to prevent memory bloat
            if len(self._store) > 500:
                # Evict oldest 100 entries
                sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k][0])
                for old_k in sorted_keys[:100]:
                    self._store.pop(old_k, None)
            self._store[key] = (time.time(), results)

    def clear(self):
        with self._lock:
            self._store.clear()


_SEARCH_CACHE = SafeSearchCache(ttl_seconds=3600)  # 1 hour cache


# -----------------------------------------------------------------------------
# Search Provider Interface & Tavily Implementation (Sections 4, 5, 13)
# -----------------------------------------------------------------------------

class BaseSearchProvider:
    """Abstract base class for search providers."""
    def search(
        self,
        query: str,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        timeout: float = 6.0
    ) -> List[WebEvidence]:
        raise NotImplementedError


class TavilySearchProvider(BaseSearchProvider):
    """
    Direct HTTP client for the Tavily Search API (https://api.tavily.com/search).
    No LangChain, no third-party wrapper dependencies.
    """
    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = (api_key or "").strip()

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        return os.getenv("TAVILY_API_KEY", "").strip()

    @api_key.setter
    def api_key(self, val: str):
        self._api_key = val

    def search(
        self,
        query: str,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        timeout: float = 6.0
    ) -> List[WebEvidence]:
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not configured. Web search unavailable.")
            return []

        payload: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False
        }
        if include_domains:
            payload["include_domains"] = include_domains

        headers = {
            "Content-Type": "application/json"
        }

        try:
            # Use httpx if available, fallback to requests
            try:
                import httpx
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(self.ENDPOINT, json=payload, headers=headers)
            except ImportError:
                import requests
                resp = requests.post(self.ENDPOINT, json=payload, headers=headers, timeout=timeout)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                evidence_list: List[WebEvidence] = []
                now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

                for r in results:
                    url = r.get("url", "")
                    title = (r.get("title") or "Agricultural Advisory").strip()
                    content = (r.get("content") or "").strip()
                    score = float(r.get("score", 0.5))
                    published_date = r.get("published_date")

                    domain = extract_domain(url)
                    tier = classify_domain_tier(domain)

                    # Strictly discard domains on low-trust list
                    if not tier:
                        continue

                    source_type = (
                        SourceType.LIVE_WEB_OFFICIAL if tier == SourceTier.AUTHORITATIVE
                        else SourceType.LIVE_WEB_INSTITUTIONAL if tier == SourceTier.INSTITUTIONAL
                        else SourceType.LIVE_WEB_GENERAL
                    )

                    evidence_list.append(WebEvidence(
                        title=title,
                        url=url,
                        domain=domain,
                        content=content,
                        score=score,
                        source_tier=tier,
                        source_type=source_type,
                        published_date=published_date,
                        retrieved_at=now_str
                    ))

                return evidence_list

            elif resp.status_code == 401:
                logger.error("Tavily API returned 401 Unauthorized. Verify TAVILY_API_KEY.")
            elif resp.status_code == 429:
                logger.warning("Tavily API rate limit reached (429).")
            else:
                logger.error(f"Tavily API returned HTTP {resp.status_code}: {resp.text[:200]}")

        except Exception as e:
            err_name = type(e).__name__
            if "Timeout" in err_name or "timed out" in str(e).lower():
                logger.warning(f"Tavily API request timed out after {timeout}s.")
            else:
                logger.error(f"Tavily API request exception: {e}")

        return []


# -----------------------------------------------------------------------------
# High-Level Web Search Orchestrator (Sections 5, 11, 13, 19, 21)
# -----------------------------------------------------------------------------

class WebSearchService:
    """
    Manages two-stage search strategy, caching, source prioritization,
    and evidence sufficiency checks.
    """
    def __init__(self, provider: Optional[BaseSearchProvider] = None, enabled: Optional[bool] = None):
        self._enabled = enabled
        self.provider = provider or TavilySearchProvider()
        self.timeout = float(os.getenv("WEB_SEARCH_TIMEOUT_SECONDS", "6.0"))
        self.max_results = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))

    @property
    def enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        is_flag_enabled = os.getenv("WEB_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
        if not is_flag_enabled:
            return False
        # If using Tavily, ensure api_key is configured; otherwise do not make pointless provider calls
        if isinstance(self.provider, TavilySearchProvider) and not self.provider.api_key:
            return False
        return True

    @enabled.setter
    def enabled(self, val: bool):
        self._enabled = val

    def search(
        self,
        query: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
        freshness_needed: bool = True
    ) -> List[WebEvidence]:
        """
        Executes Two-Stage Search:
        Stage 1: Official & Institutional Indian Agriculture Domains
        Stage 2: Reputable Broader Search (if Stage 1 yields < 2 evidence items)
        """
        if not self.enabled:
            logger.info("WebSearchService is disabled via WEB_SEARCH_ENABLED flag or missing API key.")
            return []

        # Sanitize query (remove PII, enrich with technical context)
        enriched_query = sanitize_and_enrich_query(
            user_query=query,
            crop=crop,
            location=location,
            freshness_needed=freshness_needed
        )

        # Check in-memory cache
        cache_key = f"{enriched_query}|{freshness_needed}"
        cached = _SEARCH_CACHE.get(cache_key)
        if cached is not None:
            logger.info(f"WebSearchService: Cache hit for '{enriched_query}' ({len(cached)} items)")
            return cached

        logger.info(f"WebSearchService: Initiating search for sanitized query: '{enriched_query}'")

        # ---------------------------------------------------------------------
        # STAGE 1: AUTHORITATIVE & INSTITUTIONAL SEARCH
        # ---------------------------------------------------------------------
        stage_1_domains = list(TIER_1_AUTHORITATIVE_DOMAINS[:15] + TIER_2_INSTITUTIONAL_DOMAINS[:10])
        q_low = query.lower()
        if any(term in q_low for term in ["pmfby", "bima", "crop insurance", "insurance"]):
            scheme_pref = ["pmfby.gov.in", "agriwelfare.gov.in", "agricoop.nic.in", "pib.gov.in", "egazette.gov.in"]
            stage_1_domains = list(dict.fromkeys(scheme_pref + stage_1_domains))
        results_stage_1 = self.provider.search(
            query=enriched_query,
            max_results=self.max_results,
            include_domains=stage_1_domains,
            timeout=self.timeout
        )

        evidence: List[WebEvidence] = list(results_stage_1)

        # ---------------------------------------------------------------------
        # STAGE 2: REPUTABLE BROADER SEARCH (Fallback if Stage 1 is insufficient)
        # ---------------------------------------------------------------------
        if len(evidence) < 2:
            logger.info("Stage 1 yielded insufficient evidence (<2 items). Initiating Stage 2 reputable broader search.")
            try:
                results_stage_2 = self.provider.search(
                    query=enriched_query,
                    max_results=self.max_results,
                    include_domains=None,  # Broader search, filtered server-side by classify_domain_tier
                    timeout=self.timeout
                )
                # Deduplicate by URL
                seen_urls = {item.url for item in evidence}
                for item in results_stage_2:
                    if item.url not in seen_urls:
                        evidence.append(item)
                        seen_urls.add(item.url)
            except Exception as e:
                logger.warning(f"Stage 2 broader search error: {e}")

        # Scheme policy gate: strictly reject foreign or non-Indian domains for scheme queries
        is_scheme_query = bool(re.search(r"\b(pmfby|pm-?kisan|pmksy|kcc|fasal\s*bima|crop\s*insurance)\b", query.lower()))
        if is_scheme_query:
            scheme_allowed = []
            for ev in evidence:
                d = (ev.domain or "").lower().strip()
                if d.startswith("www."):
                    d = d[4:]
                # Strictly reject foreign .gov (e.g. fedramp.gov, hhs.gov)
                if d.endswith(".gov") and not d.endswith(".gov.in"):
                    continue
                if d.endswith(".gov.in") or d.endswith(".nic.in") or d in TIER_1_AUTHORITATIVE_DOMAINS or any(d.endswith("." + auth) for auth in TIER_1_AUTHORITATIVE_DOMAINS):
                    scheme_allowed.append(ev)
            evidence = scheme_allowed

        # Safety-critical Pest / Disease query gate (down-rank / reject low-authority General Web)
        is_pest_or_disease = bool(re.search(
            r"\b(disease|pest|insect|fungus|blight|rust|rot|bacteri|caterpillar|borer|कीट|रोग|बीमारी|कीड़ा|fungicide|pesticide|कीटनाशक)\b",
            query.lower()
        ))
        if is_pest_or_disease:
            authoritative_only = [ev for ev in evidence if ev.source_tier in (SourceTier.AUTHORITATIVE, SourceTier.INSTITUTIONAL)]
            if authoritative_only:
                evidence = authoritative_only

        # ---------------------------------------------------------------------
        # SOURCE TRUST SCORING & HIERARCHICAL SORTING (Section 19)
        # Priority: AUTHORITATIVE (Tier 1) > INSTITUTIONAL (Tier 2) > GENERAL_WEB (Tier 3)
        # Within the same tier, sort by search relevance score.
        # ---------------------------------------------------------------------
        def sort_key(ev: WebEvidence) -> Tuple[int, float]:
            tier_rank = {
                SourceTier.AUTHORITATIVE: 3,
                SourceTier.INSTITUTIONAL: 2,
                SourceTier.GENERAL_WEB: 1
            }.get(ev.source_tier, 0)
            return (tier_rank, ev.score)

        evidence.sort(key=sort_key, reverse=True)

        # Truncate to max_results
        final_evidence = evidence[:self.max_results]

        # Save to cache ONLY if evidence is non-empty (never cache empty / failed results)
        if final_evidence:
            _SEARCH_CACHE.set(cache_key, final_evidence)

        return final_evidence

    def is_evidence_sufficient(self, evidence: List[WebEvidence], min_content_length: int = 50) -> bool:
        """
        Determines whether retrieved web evidence contains substantive content
        to reliably answer the question (Section 21).
        """
        if not evidence:
            return False
        total_substantive = sum(
            1 for e in evidence if e.content and len(e.content.strip()) >= min_content_length
        )
        return total_substantive >= 1


# Default singleton instance
web_search_service = WebSearchService()
