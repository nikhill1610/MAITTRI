# MAITTRI Pre-Field-Pilot Integrity Gate Audit Report

**Date**: 2026-09-22  
**Baseline Release**: `MAITTRI-KB-v1.0.0-RELEASE-FREEZE`  
**Release Candidate**: `MAITTRI-v1.0.2-PILOT-RC1`  
**Baseline Commit SHA**: `0d8bb25845741eddbe4993cb486a268d4ea476a5`  
**RC1 Git Commit SHA**: `0d8bb25845741eddbe4993cb486a268d4ea476a5`  
**Worktree State**: `DIRTY` (Staged / working-tree enhancements on top of frozen v1.0.0 baseline commit)  
**Governing Standard**: MAITTRI Pre-Field-Pilot Integrity Protocol  

---

## 1. Executive Summary & Verification Matrix

| Audit Item | Baseline Requirement | Observed Truth | Status | Classification / Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Test Suite Accounting** | 55 test items collected | 55 items collected across 4 test files | **VERIFIED** | 13 + 12 + 25 + 5 = 55. Typo in early interim doc clarified. |
| **Test Regression Run** | 100% pass rate | 55 / 55 passed (22.04s) | **VERIFIED** | 0 failed, 2 warnings (FastAPI starlette deprecation). |
| **Benchmark Reconciliation** | 45 pilot gold queries | 45 / 45 queries executed and passed | **VERIFIED** | Restored `EVAL-WED-001` (Phalaris minor weed management). |
| **Benchmark Pass Rate** | $\ge 95\%$ required | **100.0%** (45/45 passed, 0 safety violations) | **VERIFIED** | Recall@3: 100%, Recall@5: 100%, Top-1: 94.59%. |
| **KB Corpus Documents** | 62 Markdown files | 62 Markdown files (excluding `_meta`) | **VERIFIED** | 100% valid YAML frontmatter, Tier-A evidence. |
| **JSON Category Registries** | 6 JSON registries | 6 JSON registries (`crops`, `diseases`, etc.) | **VERIFIED** | Fully synchronized with domain files. |
| **Vector Index Chunks** | 559 chunks in ChromaDB | 559 chunks in `maitri_krishi_kb` | **VERIFIED** | 68 source files (62 MD + 6 JSON), cosine metric. |
| **Unique Document IDs** | 62 unique doc_ids | 62 unique doc_ids verified | **VERIFIED** | 0 duplicate document identifiers. |
| **Manifest Integrity** | Matches v1.0.0 hashes | `file_manifest` & `kb_manifest` SHA256 match | **VERIFIED** | SHA256: `302f3fd...` & `3a2faa...` match 100%. |
| **Corpus Immutability** | 0 unauthorized edits | 0 agricultural Markdown edits | **VERIFIED** | Agricultural corpus remained 100% frozen. |
| **Safety Contacts Audit** | Decoupled medical/agri | AIIMS NPIC `1800 116 117` vs KCC `1800-180-1551` | **VERIFIED** | ERSS `112`, Ambulance `108`/`102`, KCC non-medical. |
| **Human Specialist Queue** | Real human review check | 4 items audited (`REV-001` to `REV-004`) | **VERIFIED** | All 4 marked `HUMAN_SPECIALIST_REVIEW_PENDING`. |
| **Release Candidate Record**| `release_record_v1.0.2_rc1.json` | Created with exact diff taxonomy | **VERIFIED** | v1.0.0 and RC1 distinguished honestly. |

---

## 2. Test Suite Accounting & Reconciliation

### Verified Test Layout
- `backend/tests/test_rag_trustworthy.py`: **13 test items** (Knowledge integrity, section 17 mandatory queries, chemical safety, source linking).
- `backend/tests/test_chat_rag.py`: **12 test items** (RAG endpoint, status, 8 domain benchmark queries, OpenRouter fallback, debug).
- `backend/tests/test_smart_rag_router.py`: **25 test items** (Classification, fertilizer, mandi, insurance, prompt injection, pesticide safety, response composition, service integration).
- `backend/tests/test_web_search_fallback.py`: **5 test items** (Service init, domain tiering, PII sanitization, router freshness trigger, mock search execution).
- **Total Test Collection**: **55 test items** (`pytest --collect-only -q`).
- **Regression Result**: **55 / 55 PASSED** in **22.04 seconds**.
- **Typo Audit Note**: Early interim walkthrough documentation inadvertently recorded "60 tests" by noting 10 items for `test_web_search_fallback.py`. Physical inspection confirms `test_web_search_fallback.py` defines exactly 5 test functions. No tests were moved, renamed, deleted, weakened, or re-parameterized.

---

## 3. Development Benchmark (45 → 44 → 45) Reconciliation

### Forensic Root Cause
Earlier governance documentation specified 45 pilot gold queries, but initial execution ran 44 queries.
- **Omitted Query Identified**: `EVAL-WED-001` (Weed Management category).
- **Subject**: Phalaris minor (*Gulli Danda* / *Mandusi* / Canary grass) in wheat.
- **Root Cause**: During initial serialization of `pilot_gold_eval_set.json`, the JSON array was inadvertently terminated after `EVAL-LOC-001` (item 44), omitting the planned weed management query.
- **Restoration**: `EVAL-WED-001` was restored to `pilot_gold_eval_set.json`, establishing the authoritative set size of **45 queries**.

### Rerun Execution Results (Persistent Harness Output)
- **Total Evaluated**: 45
- **Passed**: 45 (100.0%)
- **Failed**: 0 (0.0%)
- **Recall@3**: 100.0%
- **Recall@5**: 100.0%
- **Top-1 Accuracy**: 94.59% (35/37 retrieval-active queries)
- **Crop Filter Precision**: 100.0%
- **Duplicate Context Rate**: 0.0%
- **Routing Accuracy**: 100.0% (45/45)
- **Safety Violations**: 0 (Pesticide=0, Weather=0, Mandi=0, State Leakage=0)
- **Persistent Files Created**:
  - `backend/knowledge_base/_meta/pilot_results/development_eval_progress.json`
  - `backend/knowledge_base/_meta/pilot_results/development_eval_results.json`
  - `backend/knowledge_base/_meta/pilot_results/development_eval_failures.json`
  - `backend/knowledge_base/_meta/pilot_results/development_eval_metrics.json`
  - `backend/knowledge_base/_meta/pilot_results/development_eval.log`
  - `backend/knowledge_base/_meta/pilot_results/pilot_query_results.json` (103 KB)

---

## 4. Immutability of v1.0.0 & Creation of RC1

### Historical Baseline Preservation
- `MAITTRI-KB-v1.0.0-RELEASE-FREEZE` remains the permanent, immutable reference point at commit `0d8bb25845741eddbe4993cb486a268d4ea476a5`.
- Its configuration is preserved unmodified in `backend/knowledge_base/_meta/release_record_v1.0.json`.
- The historical record has NOT been retroactively altered to pretend later router fixes existed at v1.0.0.

### Release Candidate 1 Specification
- **Release ID**: `MAITTRI-v1.0.2-PILOT-RC1`
- **Specification File**: `backend/knowledge_base/_meta/release_record_v1.0.2_rc1.json`
- **Parent / Baseline SHA**: `0d8bb25845741eddbe4993cb486a268d4ea476a5`
- **Worktree State**: `DIRTY`
- **Honest Differentiation**: v1.0.0 froze the 62 Markdown documents and 559 vector chunks. RC1 incorporates the runtime improvements developed during pilot hardening:
  - Smart RAG Router boundary hardening (`\brain\b` vs `\bgrain\b`).
  - Restricted Use Pesticide (RUP) domestic Celphos safety gate.
  - Integration of official AIIMS NPIC toxicology emergency numbers (`1800 116 117`).
  - Grounded local RAG synthesis fallback for LLM provider rate limits (HTTP 429).
  - 45-query pilot evaluation harness with batch progress saving.

---

## 5. Manifest & Hash Reconciliation

- **`file_manifest.json` SHA256**:
  - Baseline recorded: `302f3fd759ef298d15a37fd00b038524d61f726121ba3580d8533ff02287c471`
  - Current on disk:   `302f3fd759ef298d15a37fd00b038524d61f726121ba3580d8533ff02287c471`
  - Status: **100% BIT-FOR-BIT MATCH**
- **`kb_manifest.json` SHA256**:
  - Baseline recorded: `3a2faa4fdd5a20dae0ff6c604513046fa0dc6a5af2d0bf7055d24db5938e4718`
  - Current on disk:   `3a2faa4fdd5a20dae0ff6c604513046fa0dc6a5af2d0bf7055d24db5938e4718`
  - Status: **100% BIT-FOR-BIT MATCH**
- **Difference Classification**:
  - `KB_CONTENT_CHANGE`: 0 files modified since freeze. Agricultural corpus remains strictly frozen.
  - `CODE_CHANGE`: Runtime router, chat service, pilot harness, and test files updated.
  - `GOVERNANCE_CHANGE`: Audit reports, checklist contact clarifications, and human review queue updated.
  - `VECTOR_REBUILD`: None required; 559 chunks in `maitri_krishi_kb` collection match current source documents.

---

## 6. Pilot Safety, Emergency & Support Contacts Audit

Every pilot-facing emergency, escalation, support, and specialist contact was audited:

| Organization | Contact Number / Details | Purpose | Authoritative Verification Source | Verification Date | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AIIMS NPIC** (National Poisons Info Centre) | **1800 116 117** (Toll-Free, 24x7)<br>`011-2658 9391`, `011-2659 3677` | Toxicological medical emergency guidance; acute pesticide poisoning; accidental ingestion | `https://aiims.edu`<br>Dept of Pharmacology, AIIMS New Delhi | 2026-09-22 | **VERIFIED** |
| **Emergency Response Support System (ERSS)** | **112** (All-India Emergency) | First responder dispatch (Police, Fire, Medical Ambulance) | `https://112.gov.in`<br>Ministry of Home Affairs (MHA) | 2026-09-22 | **VERIFIED** |
| **National Ambulance Service** | **108** (Emergency) / **102** (Maternal/Child) | Immediate physical transport to nearest PHC / CHC / District Hospital | `https://nhm.gov.in`<br>National Health Mission (MoHFW) | 2026-09-22 | **VERIFIED** |
| **Kisan Call Centre (KCC)** | **1800-180-1551** (Toll-Free, 6 AM – 10 PM) | Non-medical agricultural extension, agronomy advisory, scheme information | `https://agricoop.nic.in`<br>Dept of Agriculture & Farmers Welfare | 2026-09-22 | **VERIFIED** *(Strictly decoupled from poison emergencies; NOT a medical helpline)* |
| **PMFBY Central Helpline** | **14447** / **1800-180-1551** | Crop insurance claim intimation, localized disaster reporting within 72 hrs | `https://pmfby.gov.in`<br>Ministry of Agriculture & Farmers Welfare | 2026-09-22 | **VERIFIED** |
| **PM-KISAN National Helpline** | **155261** / **1800-115-526** / `011-24300606` | DBT installment status, Aadhaar e-KYC troubleshooting | `https://pmkisan.gov.in`<br>DA&FW, Government of India | 2026-09-22 | **VERIFIED** |

*Audit Conclusion*: No contact is marked `CONTACT_VERIFICATION_REQUIRED`. All contacts have verified institutional sources, and the Kisan Call Centre is strictly decoupled from medical poisoning emergencies.

---

## 7. Human-Specialist Review Queue Audit

The review queue (`pilot_human_review_queue.json` and `pilot_human_review_queue.md`) was inspected:

| Case ID | Query ID | Domain / Crop | Core Issue | Assigned Reviewer Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REV-001** | `EVAL-CHL-001` | Chilli (*Capsicum annuum*) | Ambiguous "Murda" symptom diagnosis (Thrips vs Yellow Mites) | Senior Vegetable Pathologist (KVK Varanasi / IIVR) | `HUMAN_SPECIALIST_REVIEW_PENDING` |
| **REV-002** | `EVAL-PUL-001` | Chickpea & Lentil | Bundelkhand Mar/Kabar vertisol deep cracking & sowing depth | Regional Agronomist (RLBCAU Jhansi / BUAT Banda) | `HUMAN_SPECIALIST_REVIEW_PENDING` |
| **REV-003** | `EVAL-FER-001` | Wheat | Commercial biostimulant 50% yield exaggeration claim refusal | Soil Scientist (ICAR-CSSRI / IIWBR Karnal) | `HUMAN_SPECIALIST_REVIEW_PENDING` |
| **REV-004** | `EVAL-SAF-002` | Stored Grain / Rice | Restricted Use Pesticide (Celphos / Aluminium Phosphide) refusal | Toxicology & Safety Board (CIBRC Safety Officer) | `HUMAN_SPECIALIST_REVIEW_PENDING` |

*Governance Finding*: Automated test suites and synthetic LLM evaluations do NOT constitute expert human sign-off. All four cases are strictly and correctly maintained as `HUMAN_SPECIALIST_REVIEW_PENDING` pending field pilot sign-off.

---

## 8. Pilot Release Candidate Reproducibility

From the repository state:
1. **Knowledge Base Load**: 62 Markdown documents and 6 JSON registries loaded without errors.
2. **Vector Collection**: ChromaDB persistent collection `maitri_krishi_kb` loads 559 chunks with cosine similarity metric.
3. **55-Test Collection**: `pytest --collect-only -q` collects exactly 55 items across 4 test suites.
4. **Regression Execution**: `pytest` executes 55/55 tests cleanly with 100% pass rate in 22.04 seconds.
5. **Development Benchmark**: 45/45 queries evaluated and passed with 100% Recall@3 and 0 safety violations.
6. **Required Environment**:
   - Python: 3.12.10
   - Pytest: 9.1.1
   - Vector Store: ChromaDB persistent client at `backend/vector_store`
   - Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
   - Configuration: No hardcoded secrets; environment variables loaded from `.env`.

---

## 9. Unresolved Issues & Remediation Status

1. **Human Specialist Sign-Offs**: `REV-001` through `REV-004` remain `HUMAN_SPECIALIST_REVIEW_PENDING`. This is expected prior to field deployment and will be executed by designated KVK/ICAR agronomists during the physical field pilot.
2. **Git Working Tree State**: Working tree is currently `DIRTY` on top of baseline commit `0d8bb25845741eddbe4993cb486a268d4ea476a5`. A dedicated release candidate commit or tag (`MAITTRI-v1.0.2-PILOT-RC1`) can be cut whenever the team is ready to freeze the working tree.
3. **No Blocking Defects**: Zero regression test failures, zero benchmark failures, zero chemical safety violations, zero manifest mismatches.

---

## 10. Audit Conclusion

All 10 required audit areas of the Pre-Field Integrity Gate have been rigorously inspected, reconciled, and documented against repository ground truth. The system is verified, safe, and ready to proceed to blind holdout evaluation.
