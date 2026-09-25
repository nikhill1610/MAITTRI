# MAITTRI Live Services & Dynamic Routing Specification

**Document Version**: 1.0.0  
**Status**: APPROVED & VERIFIED  
**Last Audit**: 2026-09-22  
**System**: MAITTRI Live Services & Fallback Architecture

---

## 1. Purpose & Anti-Hallucination Policy

Agricultural decisions frequently depend on real-time, time-sensitive parameters:
- **Commodity Prices** (Mandi Bhav / APMC market arrivals)
- **Weather Forecasts** (Rainfall probability, frost/cold wave alerts, heatwave warnings)
- **Government Portals** (Live DBT status, PMFBY claim submission)

> [!CRITICAL]
> **Anti-Hallucination Policy**: A frozen RAG knowledge base MUST NEVER invent or guess real-time market prices or dynamic daily weather forecasts from static text. All time-sensitive queries are strictly intercepted and routed to live data adapters or trusted web fallback, or provided with verified authoritative portal guidance.

---

## 2. Live Service Routing Matrix

| Intent Category | Trigger Patterns | Primary Route | Fallback / Intercept Behavior | Authoritative Live Source |
| :--- | :--- | :--- | :--- | :--- |
| **Live Mandi Prices** | `mandi bhav`, `आज का भाव`, `daily market rate`, `wheat price Kanpur` | `LIVE_SERVICE` / `FINANCIAL` | Anti-hallucination intercept redirects to live Agmarknet portal (`agmarknet.gov.in`) and internal Mandi dashboard | Directorate of Marketing & Inspection (DMI) / Agmarknet |
| **Live Weather Forecast** | `rain today`, `aaj barish hogi`, `mausam forecast`, `heatwave alert` | `WEATHER` (with location) | If location present: query IMD Agromet API / OpenWeatherMap; If location missing: `PROMPT_CONTEXT` | India Meteorological Department (IMD) / Mausam portal |
| **Crop Insurance (PMFBY)** | `claim insurance`, `hailstorm intimation`, `72 hours window` | `FINANCIAL_SERVICE` | Prescribes statutory 72-hour reporting rule, portal `pmfby.gov.in`, and toll-free helpline `14447` | Ministry of Agriculture & Farmers Welfare |
| **Web Search Fallback** | Dynamic current events, new scheme dates, live pest outbreak alerts | `SEARCH_FALLBACK` | Tavily API / Google CSE with Tier-1 domain filtering (`.gov.in`, `.nic.in`, `.icar.gov.in`) | Verified official domains only; PII scrubbed |

---

## 3. Web Search Fallback & Domain Tiering

When knowledge base confidence is low or explicit live freshness is required:
1. **PII Sanitization**: Strips phone numbers, Aadhaar numbers, and plot GPS coordinates before external search dispatch.
2. **Domain Tiering**:
   - **Tier 1 (Authoritative Govt / ICAR)**: `agricoop.nic.in`, `icar.org.in`, `pmkisan.gov.in`, `pmfby.gov.in`, `agmarknet.gov.in`, `cibrc.gov.in`.
   - **Tier 2 (State Agricultural Universities)**: `*.ac.in`, `*.edu.in` (e.g. PAU, GBPUAT, CSAU).
   - **Blocked**: Commercial sales sites, untrusted forums, unverified chemical retail blogs.

---

## 4. Verification & Automated Test Coverage

- `test_web_search_fallback.py`:
  - `test_web_search_service_initialization`: Verifies API key handling and timeouts.
  - `test_web_search_domain_tiering`: Verifies priority ranking of `.gov.in` over commercial blogs.
  - `test_pii_sanitization`: Verifies regex scrubbing of farmer phone numbers and Aadhaar.
  - `test_smart_rag_router_explicit_freshness`: Verifies query triggers `SEARCH_FALLBACK`.
  - `test_mock_tavily_search_execution`: Validates mock search fallback responses.
- `test_smart_rag_router.py`:
  - `test_integration_mandi_bhav_anti_hallucination`: Ensures zero invented numeric mandi rates.
  - `test_weather_with_location_context`: Validates route to weather service when location is present.
  - `test_weather_without_location_missing_context`: Verifies polite clarification when location is missing.
