# MAITTRI CodeRabbit Remediation Ledger

**Milestone**: `MAITTRI_CODERABBIT_REMEDIATION`  
**Base Commit**: `dbda8af` (`manual-testing-snapshot`)  
**Status**: COMPLETED  
**Final Verdict**: CODERABBIT REMEDIATION COMPLETE — RESUME MANUAL TESTING

---

## 1. Remediation Findings Ledger

| ID | Category | Severity | File(s) | Summary | Classification | Status | Disposition / Evidence |
|---|---|---|---|---|---|---|---|
| CR-01 | Weather | BLOCKER | `backend/app/services/chat_service.py` | Weather Hybrid Hallucination: Claiming clear/dry weather or giving irrigation advice when web evidence doesn't verify it or is rain-warning/missing. Wheat CRI injected for non-wheat. | CODE_FIX | VERIFIED | Live evidence condition parsing, uncertainty fallback, crop-specific KB injection verified. 5 unit tests pass. |
| CR-02 | Evaluation | HIGH | `backend/scripts/run_pilot_eval.py` | Benchmark scoring integrity: Loose route checking, missing intent comparison, stale 44-query vs 45-query baseline. | TEST_FIX | VERIFIED | Strict `actual_intent == exp_intent` & `actual_action == exp_routing`. Superseded history archived. 45/45 queries pass (100%). |
| CR-03 | Router | HIGH | `backend/app/services/smart_rag_router.py` | PMFBY freshness: Latest/current PMFBY queries must route to WEB_SEARCH, static FINANCIAL only for non-freshness. | CODE_FIX | VERIFIED | Freshness patterns checked for PMFBY/scheme queries. |
| CR-04 | Web Search | MEDIUM | `backend/app/services/web_search_service.py` | Caching empty/failed Tavily search results. | CODE_FIX | VERIFIED | Only cache if `len(evidence) > 0`. |
| CR-05 | LLM Client | MEDIUM | `backend/app/services/chat_service.py` | Gemini duplicate retry after timeout/connection failure. | CODE_FIX | VERIFIED | Removed duplicate unthrottled retry block. |
| CR-06 | Market Price | HIGH | `backend/app/services/smart_rag_router.py`, `chat_service.py` | Live Mandi Defect: Aaj Jaipur mandi gehun bhav routed to static refusal instead of live web. | CODE_FIX | VERIFIED | Gated live interceptor active; verified in test suites. |
| CR-07 | Entity Detection | MEDIUM | `backend/app/services/smart_rag_router.py` | Crop regex substring false positives (`rai` in `rain`, `gram` in `program`, `corn` in `acorn`). | CODE_FIX | VERIFIED | Fixed-width Unicode word boundaries `(?<![\u0900-\u097Fa-zA-Z0-9])` and `(?![\u0900-\u097Fa-zA-Z0-9])`. |
| CR-08 | Entity Detection | MEDIUM | `backend/app/services/smart_rag_router.py` | Crop/stage words incorrectly treated as locations. | CODE_FIX | VERIFIED | Crop names and physiological stages added to `LOCATION_STOPWORDS`. |
| CR-09 | Safety / Filter | MEDIUM | `backend/app/services/smart_rag_router.py` | Gibberish detector rejects valid short Hinglish words (`is`, `me`, `ka`, `ki`, `ko`, `hai`). | CODE_FIX | VERIFIED | Multi-word gibberish detection threshold set to 0.5 with keyboard-mash heuristics and Hinglish whitelist. |
| CR-10 | Safety / Intent | MEDIUM | `backend/app/services/smart_rag_router.py` | Fertilizer dose questions triggering pesticide refusal solely on "dose". | CODE_FIX | VERIFIED | Fertilizer dose queries exempt from pesticide refusal unless chemical hazard term is present. |
| CR-11 | Security | HIGH | `backend/app/services/smart_rag_router.py` | Expand prompt injection patterns (e.g., "ignore all previous instructions"). | CODE_FIX | VERIFIED | Expanded jailbreak patterns, verified with resilience tests. |
| CR-12 | Router | MEDIUM | `backend/app/services/smart_rag_router.py` | Distinguish live weather forecast from static temperature/frost advisory. | CODE_FIX | VERIFIED | Separated live-time indicators from static agronomic threshold queries (`WEATHER_PATTERNS`). |
| CR-13 | Entity Detection | LOW | `backend/app/services/smart_rag_router.py` | "red gram" mapped to Chickpea instead of Pigeonpea/Arhar. | CODE_FIX | VERIFIED | Red gram explicitly mapped to Pigeonpea before Chickpea. |
| CR-14 | Privacy / Security | HIGH | `backend/app/services/web_search_service.py` | Aadhaar redaction: Support spaced, hyphenated, and contiguous 12-digit formats. | CODE_FIX | VERIFIED | Regex `\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b` verified with unit tests. |
| CR-15 | Concurrency | MEDIUM | `backend/app/services/web_search_service.py` | SafeSearchCache thread safety. | CODE_FIX | VERIFIED | Threading lock added across read, write, and purge operations. |
| CR-16 | Web Search | MEDIUM | `backend/app/services/web_search_service.py` | Tavily API key missing causes unnecessary failed provider requests. | CODE_FIX | VERIFIED | Checked key before making HTTP calls, gracefully defaults. |
| CR-17 | Web Search | LOW | `backend/app/services/web_search_service.py` | Hardcoded freshness year (2026). | CODE_FIX | VERIFIED | Uses `datetime.now().year`. |
| CR-18 | Safety / Grounding | MEDIUM | `backend/app/services/chat_service.py` | Chemical safety & non-definitive diagnosis rules in web-grounded prompt. | CODE_FIX | VERIFIED | CIBRC disclaimer and provisional diagnosis caveats in synthesis prompt and offline fallback. |
| CR-19 | Web Search | MEDIUM | `backend/app/services/web_search_service.py` | Reject/down-rank low authority web content for pest/disease queries. | CODE_FIX | VERIFIED | Authority domain ranking and blacklisted unverified sources. |
| CR-20 | Test Harness | HIGH | `backend/scripts/run_final_automated_regression.py` | Portability (`sys.executable`) and include `backend/tests/test_coderabbit_security_web_fixes.py`. | TEST_FIX | VERIFIED | Uses `sys.executable`, includes security web suite (86 passed). |
| CR-21 | Audit | HIGH | `backend/knowledge_base/_meta/audit_runner.py` | Relative KB_DIR, dynamic status based on errors, non-zero exit on failure, prevent manifest wipe. | GOVERNANCE_FIX | VERIFIED | Relative pathing, zero-manifest guard, clean exit code 0. |
| CR-22 | Governance | HIGH | `docs/PRODUCTION_DEPLOYMENT_READINESS.md`, `MAITTRI_PROJECT_AUDIT.md` | Reconcile evidence tiers, fix rollback SHA (note 0d8bb25 vs dbda8af frozen corpus), READY FOR PILOT. | GOVERNANCE_FIX | VERIFIED | Rollback governance section added; statuses reconciled to `READY FOR PILOT`. |
| CR-23 | Telemetry | MEDIUM | `backend/app/schemas.py` | Missing route actions in telemetry schema (`FINANCIAL_SERVICE`, `SAFE_REFUSAL`, `ASK_FOR_CONTEXT`). | CODE_FIX | VERIFIED | Added `FINANCIAL_SERVICE`, `MARKET_SERVICE`, `SAFE_REFUSAL`, `ASK_FOR_CONTEXT` to schema and telemetry validator. |
| CR-24 | Data Integrity | MEDIUM | `backend/knowledge_base/_meta/source_registry.json` | Reconcile source registry keys with source_org values. | DATA_INTEGRITY_FIX | VERIFIED | Added `ICAR-IISR`, `ICAR-NRCB`, `ICAR-CISH`, `ICAR-CIRB`, `ICAR-DPR`, `FRI` (43 verified institutions). |
| CR-25 | Documentation | LOW | `MAITTRI_PROJECT_AUDIT.md` | Fix broken AGMARKNET row (pasted shell code), replace absolute `file:///` URLs. | DOCUMENTATION_FIX | VERIFIED | Markdown table restored cleanly. |
| CR-26 | Agronomy | MEDIUM | `backend/knowledge_base/crops/banana_guide.md` | Banana density 1.8x1.5m math (3,703 vs 3,086 plants/ha). | AGRONOMIC_EVIDENCE_REQUIRED | VERIFIED | Documented standard 1.8x1.8m (3,086) vs high density 1.8x1.5m (3,703/ha). |
| CR-27 | Agronomy | MEDIUM | `backend/knowledge_base/Mountain_Farming/mountain_horticulture_temperate.md` | HRMN-99 chilling hours conflict (100-150 hrs vs 150-300 hrs). | AGRONOMIC_EVIDENCE_REQUIRED | VERIFIED | Standardized category chilling range to 100–300 hours with HRMN-99 specific low-chill note (100–150 hrs). |
| CR-28 | Agronomy | MEDIUM | `backend/knowledge_base/crops/rice_guide.md` | AWD tube insertion depth (15 cm vs 20 cm). | AGRONOMIC_EVIDENCE_REQUIRED | VERIFIED | Verified 15 cm below soil surface per IRRI/ICAR technical bulletin. |
| CR-29 | Agronomy / Safety | HIGH | `backend/knowledge_base/safety/pesticide_handling_ppe.md` | Stray `Chaos` artifact in pesticide dilution formula denominator. | CODE_FIX | VERIFIED | Removed stray `Chaos` token. |
| CR-30 | Governance | MEDIUM | `backend/knowledge_base/_meta/holdout_manifest.json` | Blind holdout path validation. | GOVERNANCE_FIX | VERIFIED | Corrected 7 invalid document paths in `create_blind_holdout.py` (0 missing). |

---

## 2. GSD Stage Tracking Checkpoints

- [x] **Stage 0 — Protect Current State**: Pre-remediation patch saved to scratchpad.
- [x] **Stage 1 — Findings Ledger**: `docs/MAITTRI_CODERABBIT_REMEDIATION.md` initialized.
- [x] **Stage 2 — Critical Live-Data / Routing Correctness**: Weather hallucination blocker, PMFBY freshness, Tavily empty caching, Gemini duplicate retry, Live Mandi verification.
- [x] **Stage 3 — Router / Entity / Intent Correctness**: Crop regex boundaries, red gram, location extraction, gibberish whitelist, fertilizer dose, prompt injection, forecast vs frost.
- [x] **Stage 4 — Web-Search Safety & Stability**: Aadhaar redaction (12-digit variants), thread-safe cache, disabled Tavily handling, runtime year, chemical safety prompts, domain authority.
- [x] **Stage 5 — Benchmark / Evaluation Integrity**: Scorer logic fix in `run_pilot_eval.py`, rerun 45 queries (100% passed), regenerated reports, archived superseded history.
- [x] **Stage 6 — Final Regression Gate**: Portable runner (`sys.executable`), included security web suite, all 86 regression tests passed in 56s.
- [x] **Stage 7 — Audit / Manifest Correctness**: Relative pathing, dynamic status, exit code 0, manifest verified (62/62 docs).
- [x] **Stage 8 — Release / Rollback Governance**: Evidence tiers, rollback SHA clarification (`0d8bb25` vs `dbda8af`), pilot readiness declaration.
- [x] **Stage 9 — Telemetry / Registry / Path Integrity**: Schema route actions, source registry keys reconciliation (43 institutions).
- [x] **Stage 10 — Documentation Cleanup**: Repaired AGMARKNET table row, removed `Chaos` formula artifact.
- [x] **Stage 11 — Agronomic Evidence Review**: Created `docs/MAITTRI_AGRONOMIC_EVIDENCE_REVIEW.md`, audited banana, HRMN-99, AWD, pesticide.
- [x] **Stage 12 — Blind-Holdout Script Hygiene**: Corrected expected document paths in `create_blind_holdout.py` (0 missing).
- [x] **Stage 13 — Re-run CodeRabbit / Self-Audit**: Full regression gate and audit runner executed with zero failures.
- [x] **Stage 14 — Final Remediation Report**: Concluding remediation summary and verdict.
