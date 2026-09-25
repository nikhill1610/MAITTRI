# MAITTRI Krishi Assistant — Pilot Governance, Quality Metrics & Acceptance Gates

**Status**: RELEASE FROZEN FOR PILOT TESTING  
**Release Identifier**: `MAITTRI-KB-v1.0.0-RELEASE-FREEZE`  
**Git Commit SHA**: `0d8bb25845741eddbe4993cb486a268d4ea476a5`  
**Date**: 2026-09-22  
**Baseline Artifacts**: 62 Markdown documents, 6 JSON registries, 559 ChromaDB vector chunks (`maitri_krishi_kb`), 38 Apex research directorates.

---

## 1. Release Baseline & Test History Reconciliation

### A. Core Corpus Baseline
- **62 Markdown Documents**: 100% valid Schema v1.0 YAML frontmatter; 0 duplicate `doc_id`s; 100% Tier A direct source provenance.
- **6 JSON Category Registries**: `crops.json`, `diseases.json`, `fertilizers.json`, `irrigation.json`, `parali.json`, and `schemes.json` strictly synchronized with filesystem paths.
- **559 ChromaDB Chunks**: Full vector collection rebuild in `backend/vector_store/` under collection name `maitri_krishi_kb`.
- **Manifest Fingerprints**:
  - `file_manifest.json` SHA256: `302f3fd759ef298d15a37fd00b038524d61f726121ba3580d8533ff02287c471`
  - `kb_manifest.json` SHA256: `3a2faa4fdd5a20dae0ff6c604513046fa0dc6a5af2d0bf7055d24db5938e4718`

### B. Audit of Test Count Discrepancy (60 vs 55 Tests)
- **Observed Pytest Result**: 55 passed in 1068.02s (100% pass rate).
- **Exact Per-Suite Item Count**:
  1. `backend/tests/test_rag_trustworthy.py`: **13 test methods**
  2. `backend/tests/test_chat_rag.py`: **12 test functions**
  3. `backend/tests/test_smart_rag_router.py`: **25 test methods**
  4. `backend/tests/test_web_search_fallback.py`: **5 test functions**
  - **Sum**: $13 + 12 + 25 + 5 = 55$ items.
- **Root Cause of Earlier "60" Reference**:
  An interim table in `walkthrough.md` typographically listed `test_web_search_fallback.py` as containing 10 tests instead of 5, resulting in an inflated sum ($13 + 12 + 25 + 10 = 60$). 
- **Integrity Confirmation**:
  Inspection of `backend/tests/test_web_search_fallback.py` confirms the file has always contained exactly 5 test functions:
  1. `test_web_search_service_initialization`
  2. `test_web_search_domain_tiering`
  3. `test_pii_sanitization`
  4. `test_smart_rag_router_explicit_freshness`
  5. `test_mock_tavily_search_execution`
  Zero tests have been deleted, altered, or skipped. Full regression coverage across all components is 100% active and passing.

---

## 2. Release Freeze & Change-Control Governance

The core knowledge base is now in **Release Freeze**. Broad expansions and exploratory edits are strictly halted.

### Change-Control Procedure
1. **Permitted Edits Only**:
   - **CRITICAL_SAFETY**: New pesticide bans or revised CIBRC restrictions.
   - **FACTUAL_CORRECTION**: Errata backed by State Agricultural University or ICAR publications.
   - **EVALUATION_FIX**: Vector chunking adjustments for documented failures in the Pilot Gold Set.
   - **PILOT_REQUIREMENT**: Critical extension requirements raised during field pilot testing.
2. **Audit Checkpoint Before Any Merge**:
   - Must run `audit_runner.py` (0 duplicate `doc_id`s, 100% valid YAML, 100% chemical safety gates).
   - Must execute `pytest` on all 55 regression tests.
   - Must log every edit in `backend/knowledge_base/_meta/PILOT_CHANGELOG.md`.

---

## 3. Pilot Quality Metrics

During the pilot, system performance is evaluated across four distinct quantitative dimensions:

### A. Retrieval Metrics
1. **Recall@k ($k=3, 5$)**: Percentage of queries where the canonical ground-truth document appears in the top-$k$ retrieved chunks. Target: $\ge 92\%$.
2. **Top-1 Document Accuracy**: Percentage of queries where chunk #1 belongs to the exact expected crop and topic. Target: $\ge 85\%$.
3. **Crop-Filter Precision**: Percentage of retrieved chunks belonging exclusively to the queried crop (zero wrong-crop leakage). Target: $\ge 98\%$.
4. **State / Agro-Zone Match Rate**: Rate at which state-specific recommendations match the farmer's geography. Target: $\ge 95\%$.
5. **Context Duplication Rate**: Percentage of retrieved chunks containing duplicate semantic sentences. Target: $< 5\%$.

### B. Generation Metrics
1. **Groundedness Score**: Percentage of claims in the generated response directly traceable to the retrieved chunks. Target: $\ge 96\%$.
2. **Answer Relevance**: Semantic similarity between farmer question intent and generated reply. Target: $\ge 92\%$.
3. **Citation & Source Integrity**: Proportion of generated responses displaying valid, clickable source badges with verified institutions. Target: $100\%$.
4. **Numerical Fidelity**: Exact preservation of numerical doses, units, and dilution ratios without truncation or arithmetic alteration. Target: $100\%$.
5. **Applicability Correctness**: Verifying that advice fits the crop stage and production system. Target: $\ge 95\%$.

### C. Safety & Guardrail Metrics
1. **Unverified Pesticide Recommendation Rate**: Target: **$0.0\%$ (Zero Tolerance)**. Every chemical mention must include the CIBRC statutory gate.
2. **Stale Weather Response Rate**: Target: **$0.0\%$**. Static weather documents must never masquerade as today's live forecast.
3. **Stale Mandi-Price Response Rate**: Target: **$0.0\%$**. Static guides must never state volatile commodity prices as live quotes.
4. **Wrong-State Agronomy Leakage**: Target: **$0.0\%$**. High-chilling northern varieties must not be recommended for southern tropical zones.
5. **Correct Abstention Rate**: Percentage of gibberish, prompt injections, or chemical cocktails correctly refused or routed to low-confidence guards. Target: $100\%$.

### D. Routing Metrics
1. **KB Routing Accuracy**: Correct classification of agronomic queries to RAG retrieval. Target: $\ge 95\%$.
2. **Live-Data Routing Accuracy**: Classification of weather, mandi, and scheme status to dynamic live services. Target: $\ge 98\%$.
3. **Clarification Trigger Accuracy**: Prompting farmers for crop, state, or symptoms on ambiguous single-word questions. Target: $\ge 90\%$.

---

## 4. Privacy-Safe Farmer Telemetry & Feedback Design

All live pilot query logging conforms to `backend/knowledge_base/_meta/pilot_telemetry_schema.json`.

### Privacy Invariants
1. **PII Masking**: Regular expressions strip phone numbers (10-digit mobile patterns), personal names, Aadhaar numbers, and bank account numbers prior to logging.
2. **Session Hash**: Conversations use a salted, one-way SHA256 hash.
3. **Voluntary Geography Only**: State and district are recorded only when explicitly stated in the query or user profile; no raw GPS coordinates are captured.
4. **Minimal Retention**: Only the sanitized query text, detected intent, retrieved doc IDs, route action, response latency, and user feedback rating are persisted.

---

## 5. Standardized Failure Taxonomy (18 Tags)

When a pilot interaction fails an automated check or human expert review, it must be assigned exactly one primary tag from the standard taxonomy:

| Failure Tag | Definition | Diagnostic Indicator |
|---|---|---|
| `WRONG_CROP` | Retrieval or generation mentions an incorrect crop | Rice question returns wheat guide chunk |
| `WRONG_STATE` | Recommendation is invalid for the specified agro-climatic zone | North-Western Plain wheat variety advised for Tamil Nadu |
| `WRONG_STAGE` | Advice is inappropriate for current crop growth stage | Pre-emergence herbicide recommended at flowering |
| `WRONG_PEST` | Pest identification is incorrect | Aphid infestation diagnosed as stem borer |
| `WRONG_DISEASE` | Disease identification is incorrect | Late blight diagnosed as potassium deficiency |
| `RETRIEVAL_MISS` | ChromaDB failed to return the relevant canonical chunk in top-k | Broad bed furrow guide not retrieved for Bundelkhand chickpea |
| `LOW_AUTHORITY_SOURCE` | Retrieved chunk lacks Tier A institutional backing | Unverified blog or commercial forum chunk retrieved |
| `STALE_SOURCE` | Outdated package of practices or expired registration used | Withdrawn chemical or obsolete variety recommended |
| `NUMERIC_MISMATCH` | Number, unit, or dilution ratio corrupted | 2 ml/L stated as 20 ml/L or kg/ha substituted for g/ha |
| `MISSING_CITATION` | Response failed to render source provenance badge | Generated text omits clickable ICAR / SAU citation |
| `UNVERIFIED_PESTICIDE` | Chemical advice missing statutory CIBRC safety gate | Pesticide recommended without label verification notice |
| `LIVE_ROUTE_FAILURE` | Query for live weather or mandi price served from static KB | Static document cited for today's market price |
| `HALLUCINATION` | Model invented facts not present in retrieved context | Model invents a non-existent pesticide or biological agent |
| `OVERCONFIDENT_DIAGNOSIS`| Ambiguous symptom diagnosed without requesting details | Single leaf yellowing diagnosed definitively as virus |
| `NEEDS_CLARIFICATION` | System answered an under-specified query without asking crop/state | Query "keeda laga hai" answered without knowing crop |
| `LANGUAGE_RETRIEVAL_FAILURE`| Hindi or Hinglish query failed to retrieve relevant English/Hindi doc | Devanagari query failed semantic match against KB chunk |
| `DUPLICATE_CONTEXT` | Redundant chunks consumed prompt context budget | Top 3 chunks contain identical paragraph |
| `OTHER` | Unclassified infrastructure or timeout exception | HTTP 504 gateway timeout during LLM call |

---

## 6. Pilot Acceptance Gates & Transition Thresholds

To prevent premature claims of national readiness, MAITTRI enforces three distinct validation stages:

```
[ PHASE 1-6 RELEASE FREEZE ] ──► [ GATE 1: READY FOR PILOT ]
                                          │ (Pass Gold Set ≥ 90%, 0 Critical Safety Leaks)
                                          ▼
                                 [ GATE 2: CONTROLLED DEPLOYMENT ]
                                          │ (500+ Real Farmer Interactions, CSAT ≥ 85%, Fallback < 8%)
                                          ▼
                                 [ GATE 3: WIDER NATIONAL DEPLOYMENT ]
```

### Stage 1: READY FOR PILOT (Current Achieved Baseline)
- **Criteria**:
  - 62 Markdown documents + 6 synchronized JSON registries.
  - 55/55 automated regression tests passing.
  - 100% CIBRC safety gate compliance across all chemical documents.
  - Pilot Gold Set (45 items) passes with $\ge 90\%$ accuracy and zero safety violations.
- **Status**: **ACHIEVED & VERIFIED**.

### Stage 2: READY FOR CONTROLLED DEPLOYMENT (Field Pilot Validation)
- **Criteria**:
  - Minimum 500 real farmer interactions recorded through the privacy-safe telemetry schema across pilot districts (e.g. Varanasi, Kanpur, Jhansi, Meerut).
  - Overall Farmer Satisfaction (CSAT): $\ge 85\%$ thumbs-up.
  - Critical Safety Failures (`UNVERIFIED_PESTICIDE`, `WRONG_STATE`): **Exactly 0 instances**.
  - Hallucination Rate: $< 2.0\%$.
  - Low-confidence / unhandled fallback rate: $< 8.0\%$.

### Stage 3: READY FOR WIDER / NATIONAL DEPLOYMENT
- **Criteria**:
  - Demonstrated multi-state pilot success across at least 3 distinct agro-climatic zones.
  - Zero unresolved items in `conflicts_and_gaps.md`.
  - Multilingual evaluation across regional dialects (Bhojpuri, Bundeli, Khari Boli, Hindi, English).
  - Formal sign-off from agricultural extension review panel.

---

## 7. Pilot Artifact Inventory

The following governance files define and enforce the pilot baseline:

| File Path | Description |
|:---|:---|
| [`backend/knowledge_base/_meta/release_record_v1.0.json`](file:///C:/Users/HP/Desktop/MAITTRI/backend/knowledge_base/_meta/release_record_v1.0.json) | Machine-readable release baseline, metadata, SHA256 fingerprints, and test audit. |
| [`backend/knowledge_base/_meta/PILOT_CHANGELOG.md`](file:///C:/Users/HP/Desktop/MAITTRI/backend/knowledge_base/_meta/PILOT_CHANGELOG.md) | Change control ledger for any authorized pilot-period corrections. |
| [`backend/knowledge_base/_meta/pilot_gold_eval_set.json`](file:///C:/Users/HP/Desktop/MAITTRI/backend/knowledge_base/_meta/pilot_gold_eval_set.json) | 45-item structured benchmark evaluation set across 15 crops and cross-cutting domains. |
| [`backend/knowledge_base/_meta/pilot_telemetry_schema.json`](file:///C:/Users/HP/Desktop/MAITTRI/backend/knowledge_base/_meta/pilot_telemetry_schema.json) | Privacy-safe, PII-masked farmer interaction telemetry and feedback JSON schema. |
| [`backend/knowledge_base/_meta/pilot_metrics_and_governance.md`](file:///C:/Users/HP/Desktop/MAITTRI/backend/knowledge_base/_meta/pilot_metrics_and_governance.md) | Quality metrics, failure taxonomy, change control procedures, and acceptance gates. |

---

$$\textbf{\Huge MAITTRI KB RELEASE FROZEN — READY FOR PILOT}$$
