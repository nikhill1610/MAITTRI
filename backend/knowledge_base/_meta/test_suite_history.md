# MAITTRI Test Suite History & Composition Audit

**Date**: 2026-09-22  
**Governing Standard**: MAITTRI Pre-Field-Pilot Integrity Gate  
**Total Active Regression Tests**: Exactly 55 tests collected and executed by Pytest  

---

## 1. Executive Summary & Verification Findings

### The Discrepancy Audited
- **Earlier Verified Baseline Layout**:
  - `backend/tests/test_rag_trustworthy.py`: 13 tests
  - `backend/tests/test_chat_rag.py`: 12 tests
  - `backend/tests/test_smart_rag_router.py`: 25 tests
  - `backend/tests/test_web_search_fallback.py`: 5 tests
  - **Total**: $13 + 12 + 25 + 5 = 55$ tests.

- **Current Reported Layout in Stage 12 Text**:
  - `backend/tests/test_rag_trustworthy.py`: 13 tests
  - `backend/tests/test_chat_rag.py`: 12 tests
  - `backend/tests/test_smart_rag_router.py`: 15 tests
  - `backend/tests/test_web_search_fallback.py`: 15 tests
  - **Total**: $13 + 12 + 15 + 15 = 55$ tests.

### Forensic Investigation & Git Diff Result
- Direct collection using `pytest --collect-only -q` on the codebase:
  - `tests/test_rag_trustworthy.py`: **13 tests collected**
  - `tests/test_chat_rag.py`: **12 tests collected**
  - `tests/test_smart_rag_router.py`: **25 tests collected**
  - `tests/test_web_search_fallback.py`: **5 tests collected**
  - **Total**: **55 tests collected** (100% pass rate).
- Git inspection (`git diff 0d8bb25845741eddbe4993cb486a268d4ea476a5 -- backend/tests/`):
  - `test_rag_trustworthy.py` and `test_chat_rag.py` are completely unmodified since initial commit.
  - `test_smart_rag_router.py` has always contained 25 tests since its initial creation.
  - `test_web_search_fallback.py` has always contained 5 tests since its initial creation.
- **Root Cause of the "25→15" and "5→15" Discrepancy**:
  The redistribution was an **inadvertent typographical reporting error in the summary markdown table** of the previous turn. The author split the 30 tests of the two newest suites ($25 + 5 = 30$) into $15 + 15 = 30$ in the report text. At no point were test cases moved between files, deleted, renamed, or modified on disk.

---

## 2. Complete 55-Test Itemized Mapping Table

| old_test_id | current_test_id | old_file | current_file | status |
| :--- | :--- | :--- | :--- | :--- |
| `TestPhase4KnowledgeIntegrity::test_official_source_metadata_retrieval` | `TestPhase4KnowledgeIntegrity::test_official_source_metadata_retrieval` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestPhase4KnowledgeIntegrity::test_curated_source_metadata_retrieval` | `TestPhase4KnowledgeIntegrity::test_curated_source_metadata_retrieval` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_a_wheat_yellow_leaves` | `TestSection17MandatoryQueries::test_query_a_wheat_yellow_leaves` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_b_rice_irrigation` | `TestSection17MandatoryQueries::test_query_b_rice_irrigation` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_c_maize_pests` | `TestSection17MandatoryQueries::test_query_c_maize_pests` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_d_soil_nitrogen_deficiency` | `TestSection17MandatoryQueries::test_query_d_soil_nitrogen_deficiency` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_e_tomato_leaf_curling` | `TestSection17MandatoryQueries::test_query_e_tomato_leaf_curling` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_f_mandi_price_anti_hallucination` | `TestSection17MandatoryQueries::test_query_f_mandi_price_anti_hallucination` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_g_weather_forecast_anti_hallucination` | `TestSection17MandatoryQueries::test_query_g_weather_forecast_anti_hallucination` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_h_gibberish_guard` | `TestSection17MandatoryQueries::test_query_h_gibberish_guard` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSection17MandatoryQueries::test_query_mountain_farming_multilingual` | `TestSection17MandatoryQueries::test_query_mountain_farming_multilingual` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestChemicalSafetyGuard::test_unsupported_unknown_pesticide_query` | `TestChemicalSafetyGuard::test_unsupported_unknown_pesticide_query` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `TestSourceLinking::test_source_count_matches_retrieval` | `TestSourceLinking::test_source_count_matches_retrieval` | `tests/test_rag_trustworthy.py` | `tests/test_rag_trustworthy.py` | unchanged |
| `test_rag_status_endpoint` | `test_rag_status_endpoint` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_retrieval_distinction_question_a_vs_b` | `test_rag_retrieval_distinction_question_a_vs_b` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_1_wheat_yellow_leaves` | `test_rag_query_1_wheat_yellow_leaves` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_2_hindi_wheat_first_irrigation` | `test_rag_query_2_hindi_wheat_first_irrigation` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_3_hinglish_maize_pests` | `test_rag_query_3_hinglish_maize_pests` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_4_rice_fertilizer` | `test_rag_query_4_rice_fertilizer` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_5_soil_nitrogen_deficiency` | `test_rag_query_5_soil_nitrogen_deficiency` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_6_pm_kisan_scheme` | `test_rag_query_6_pm_kisan_scheme` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_7_out_of_domain_france` | `test_rag_query_7_out_of_domain_france` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_query_8_gibberish_low_confidence` | `test_rag_query_8_gibberish_low_confidence` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_openrouter_mocked_success` | `test_rag_openrouter_mocked_success` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `test_rag_debug_endpoint` | `test_rag_debug_endpoint` | `tests/test_chat_rag.py` | `tests/test_chat_rag.py` | unchanged |
| `TestSmartRAGRouterClassification::test_fertilizer_dap_use` | `TestSmartRAGRouterClassification::test_fertilizer_dap_use` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_fertilizer_urea_timing` | `TestSmartRAGRouterClassification::test_fertilizer_urea_timing` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_financial_mandi_bhav` | `TestSmartRAGRouterClassification::test_financial_mandi_bhav` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_financial_pmfby_insurance` | `TestSmartRAGRouterClassification::test_financial_pmfby_insurance` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_general_agriculture_english` | `TestSmartRAGRouterClassification::test_general_agriculture_english` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_general_agriculture_hindi` | `TestSmartRAGRouterClassification::test_general_agriculture_hindi` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_gibberish_random_mashing` | `TestSmartRAGRouterClassification::test_gibberish_random_mashing` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_hindi_calendar_query` | `TestSmartRAGRouterClassification::test_hindi_calendar_query` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_hinglish_calendar_query` | `TestSmartRAGRouterClassification::test_hinglish_calendar_query` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_non_agriculture_programming` | `TestSmartRAGRouterClassification::test_non_agriculture_programming` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_pesticide_safety_double_dose_tank` | `TestSmartRAGRouterClassification::test_pesticide_safety_double_dose_tank` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_pesticide_safety_mixing_chemicals` | `TestSmartRAGRouterClassification::test_pesticide_safety_mixing_chemicals` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_prompt_injection_pesticide_bypass_resistance` | `TestSmartRAGRouterClassification::test_prompt_injection_pesticide_bypass_resistance` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_prompt_injection_rule_bypass_resistance` | `TestSmartRAGRouterClassification::test_prompt_injection_rule_bypass_resistance` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_soil_ph_query` | `TestSmartRAGRouterClassification::test_soil_ph_query` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_soil_zinc_deficiency_hindi` | `TestSmartRAGRouterClassification::test_soil_zinc_deficiency_hindi` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_weather_with_location_context` | `TestSmartRAGRouterClassification::test_weather_with_location_context` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGRouterClassification::test_weather_without_location_missing_context` | `TestSmartRAGRouterClassification::test_weather_without_location_missing_context` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGResponseComposition::test_missing_context_location_prompt` | `TestSmartRAGResponseComposition::test_missing_context_location_prompt` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGResponseComposition::test_pesticide_refusal_content` | `TestSmartRAGResponseComposition::test_pesticide_refusal_content` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGChatServiceIntegration::test_integration_mandi_bhav_anti_hallucination` | `TestSmartRAGChatServiceIntegration::test_integration_mandi_bhav_anti_hallucination` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGChatServiceIntegration::test_integration_non_agricultural_scope` | `TestSmartRAGChatServiceIntegration::test_integration_non_agricultural_scope` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGChatServiceIntegration::test_integration_pesticide_refusal` | `TestSmartRAGChatServiceIntegration::test_integration_pesticide_refusal` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGChatServiceIntegration::test_integration_pmfby_guidance` | `TestSmartRAGChatServiceIntegration::test_integration_pmfby_guidance` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `TestSmartRAGChatServiceIntegration::test_integration_weather_missing_context` | `TestSmartRAGChatServiceIntegration::test_integration_weather_missing_context` | `tests/test_smart_rag_router.py` | `tests/test_smart_rag_router.py` | unchanged |
| `test_web_search_service_initialization` | `test_web_search_service_initialization` | `tests/test_web_search_fallback.py` | `tests/test_web_search_fallback.py` | unchanged |
| `test_web_search_domain_tiering` | `test_web_search_domain_tiering` | `tests/test_web_search_fallback.py` | `tests/test_web_search_fallback.py` | unchanged |
| `test_pii_sanitization` | `test_pii_sanitization` | `tests/test_web_search_fallback.py` | `tests/test_web_search_fallback.py` | unchanged |
| `test_smart_rag_router_explicit_freshness` | `test_smart_rag_router_explicit_freshness` | `tests/test_web_search_fallback.py` | `tests/test_web_search_fallback.py` | unchanged |
| `test_mock_tavily_search_execution` | `test_mock_tavily_search_execution` | `tests/test_web_search_fallback.py` | `tests/test_web_search_fallback.py` | unchanged |

---

## 3. Regression Coverage Equivalence Assessment

1. **Test Item Count**:
   - Exactly **55 tests** collected by Pytest across the 4 files.
   - Breakdown: 13 (`test_rag_trustworthy.py`) + 12 (`test_chat_rag.py`) + 25 (`test_smart_rag_router.py`) + 5 (`test_web_search_fallback.py`) = 55.
2. **Assertion and Invariant Verification**:
   - Zero tests were deleted or skipped.
   - Zero test assertions were relaxed or weakened.
   - Zero test functions were renamed or moved across module boundaries.
   - All 55 tests assert strict agricultural invariants: CIBRC pesticide gates, prompt injection resistance, zero hallucinations on live mandi/weather, PII scrubbers, and CRI irrigation timing.
3. **Execution Result**:
   - Command: `pytest tests/test_rag_trustworthy.py tests/test_chat_rag.py tests/test_smart_rag_router.py tests/test_web_search_fallback.py -q`
   - Result: **55 passed, 0 failed, 2 deprecation warnings** (fastapi/starlette testclient deprecation) in **59.95 seconds**.
   - **Conclusion**: Full regression coverage is 100% equivalent, completely intact, and active.
