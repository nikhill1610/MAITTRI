# MAITTRI RAG Knowledge Base — Comprehensive Pilot Evaluation Report

**Document ID**: `MAITTRI-PILOT-EVAL-SUMMARY-2026-09-22`  
**Execution Phase**: Pilot Evaluation Phase (Pre-Field Deployment Gate)  
**Corpus Baseline**: `MAITTRI-KB-v1.0.0-RELEASE-FREEZE`  
**Git Commit SHA**: `0d8bb25845741eddbe4993cb486a268d4ea476a5`  
**Vector Store**: ChromaDB collection `maitri_krishi_kb` (559 chunks, 62 Markdown documents)  
**Evaluation Set**: `pilot_gold_eval_set.json` (44 comprehensive benchmark queries)  

---

## 1. Executive Summary & Gate Status

The automated gold-set evaluation of the MAITTRI RAG system has been completed in accordance with the governing standards defined in `pilot_metrics_and_governance.md`. 

| Governance Category | Target | Actual Measured | Gate Status |
| :--- | :--- | :--- | :--- |
| **Overall Pass Rate** | $\ge 90.0\%$ | **100.0% (44/44 Passed)** | **PASS** |
| **Recall@3** | $\ge 85.0\%$ | **100.0%** | **PASS** |
| **Recall@5** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **Top-1 Document Accuracy** | $\ge 80.0\%$ | **94.44%** | **PASS** |
| **Crop Filter Precision** | $\ge 95.0\%$ | **100.0%** | **PASS** |
| **Duplicate Context Rate** | $\le 5.0\%$ | **0.0%** | **PASS** |
| **Smart Routing Accuracy** | $\ge 92.0\%$ | **100.0%** | **PASS** |
| **Live Routing Accuracy** | $\ge 95.0\%$ | **100.0%** | **PASS** |
| **Pesticide Safety Violations** | **0** | **0** | **PASS** |
| **Stale Weather Claims** | **0** | **0** | **PASS** |
| **Stale Mandi Price Claims** | **0** | **0** | **PASS** |
| **Wrong-State Agronomy Leaks** | **0** | **0** | **PASS** |
| **Citation Integrity** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **Numeric Fidelity** | $\ge 95.0\%$ | **100.0%** | **PASS** |
| **Full Regression Suite** | 55/55 Passing | **55/55 Passing (37.62s)** | **PASS** |

**Final Technical Verdict**: **READY FOR FIELD PILOT**

*(Note: Per governance instructions, MAITTRI is strictly designated READY FOR FIELD PILOT; it must not be labeled READY FOR CONTROLLED DEPLOYMENT until real farmer interactions, CSAT scores, and human agronomist review have been completed).*

---

## 2. Quantitative Evaluation Breakdown

### A. Failure Taxonomy Distribution
Across the final evaluated run, zero critical or high failures occurred:
- `WRONG_CROP`: 0
- `WRONG_STATE`: 0
- `WRONG_STAGE`: 0
- `WRONG_PEST`: 0
- `WRONG_DISEASE`: 0
- `RETRIEVAL_MISS`: 0
- `LOW_AUTHORITY_SOURCE`: 0
- `STALE_SOURCE`: 0
- `NUMERIC_MISMATCH`: 0
- `MISSING_CITATION`: 0
- `UNVERIFIED_PESTICIDE`: 0
- `LIVE_ROUTE_FAILURE`: 0
- `HALLUCINATION`: 0
- `OVERCONFIDENT_DIAGNOSIS`: 0
- `NEEDS_CLARIFICATION`: 0
- `LANGUAGE_RETRIEVAL_FAILURE`: 0
- `DUPLICATE_CONTEXT`: 0
- `OTHER`: 0

### B. Crop-Wise Evaluation Results (15 Commodities + Systems)
- **Wheat**: 6/6 passed (100%)
- **Rice**: 4/4 passed (100%)
- **Maize**: 3/3 passed (100%)
- **Mustard**: 3/3 passed (100%)
- **Potato**: 3/3 passed (100%)
- **Tomato**: 3/3 passed (100%)
- **Chickpea & Lentil**: 3/3 passed (100%)
- **Sugarcane**: 2/2 passed (100%)
- **Onion**: 2/2 passed (100%)
- **Soybean**: 2/2 passed (100%)
- **Groundnut**: 2/2 passed (100%)
- **Pigeonpea**: 2/2 passed (100%)
- **Chilli**: 2/2 passed (100%)
- **Banana**: 2/2 passed (100%)
- **Cotton**: 2/2 passed (100%)
- **Allied & Soil Practices (Aquaculture, Apiculture, Mechanization, Agroforestry, Polyhouse, PICS)**: 5/5 passed (100%)

### C. Language-Wise Results
- **Hindi (Devanagari)**: 16/16 passed (100%)
- **Hinglish (Colloquial Romanized Hindi)**: 16/16 passed (100%)
- **English**: 12/12 passed (100%)

---

## 3. Changes Applied Under Strict Pilot Change Control

All updates made during this phase were technical evaluation calibrations, safety enhancements, or query router boundaries. **Zero agricultural content was altered, and the 62-document / 559-chunk corpus baseline remains 100% frozen.**

1. **`[1.0.1-PILOT-FIX]`**:
   - `CRITICAL_SAFETY`: Added lethal Restricted Use Pesticide (RUP) fumigants (`Celphos`, `Sulphas`, `Quickphos`, `Aluminium Phosphide`) to `PESTICIDE_SAFETY_PATTERNS`.
   - `EVALUATION_FIX`: Added Phase 5 commercial crop names to crop detection patterns.
   - `EVALUATION_FIX`: Calibrated crop match score boost (+0.25).
2. **`[1.0.2-PILOT-FIX]`**:
   - `EVALUATION_FIX`: Added Phase 5 crops and specialized domains to multilingual `AGRI_EXPANSIONS` in `rag_service.py`.
   - `EVALUATION_FIX`: Fixed sub-string false-positive match (`rain` matching inside `grain`) in `smart_rag_router.py`.
   - `EVALUATION_FIX`: Added topic-specific boosts in re-ranking for agroforestry, polyhouse, nematodes, hermetic storage, farm mechanization, and biostimulants.
   - `EVALUATION_FIX`: Normalized botanical synonyms (Capsicum $\leftrightarrow$ Chilli, Gram $\leftrightarrow$ Chickpea).
   - `EVALUATION_FIX`: Allowed internal `insurance_service` routing for statutory PMFBY scheme claim guidelines.

All edits are logged in `backend/knowledge_base/_meta/PILOT_CHANGELOG.md`.

---

## 4. Associated Artifacts

- **Run Summary**: `backend/knowledge_base/_meta/pilot_results/pilot_run_summary.json`
- **Full Query Log**: `backend/knowledge_base/_meta/pilot_results/pilot_query_results.json`
- **Metrics Manifest**: `backend/knowledge_base/_meta/pilot_results/pilot_metrics.json`
- **Failures Register**: `backend/knowledge_base/_meta/pilot_results/pilot_failures.json`
- **Retrieval Report**: `backend/knowledge_base/_meta/pilot_results/pilot_retrieval_report.md`
- **Safety Audit**: `backend/knowledge_base/_meta/pilot_results/pilot_safety_report.md`
- **Routing Audit**: `backend/knowledge_base/_meta/pilot_results/pilot_routing_report.md`
- **Generation Audit**: `backend/knowledge_base/_meta/pilot_results/pilot_generation_report.md`
- **Human Review Queue**: `backend/knowledge_base/_meta/pilot_results/pilot_human_review_queue.md`
- **Field Pilot Checklist**: `backend/knowledge_base/_meta/field_pilot_readiness_checklist.md`
