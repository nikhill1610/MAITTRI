# MAITTRI Knowledge Base — Pilot Period Change Log

All modifications made to the frozen 62-document / 559-chunk knowledge base during the Pilot Testing Phase must be documented here.

## Governance Rules
1. **Zero Automatic Expansions**: Broad crop or state expansions are prohibited during the pilot phase.
2. **Permitted Changes**:
   - **CRITICAL_SAFETY**: CIBRC/PPQS label updates, banned pesticide additions, toxicity warnings.
   - **FACTUAL_CORRECTION**: Errata verified by State Agricultural University or ICAR publications.
   - **EVALUATION_FIX**: Retrieval or chunking alignment triggered by documented failure in the Pilot Gold Set.
   - **PILOT_REQUIREMENT**: Approved extension requirement from pilot field feedback.
3. **Audit Requirement**: Any edit must preserve the 7-factor numerical provenance, maintain 100% frontmatter schema validity, and pass the 55-item automated regression suite before merge.

---

## Change Entries

### [1.0.0-FREEZE] — 2026-09-22
- **Baseline Established**: 62 Markdown documents, 6 category registries, 559 ChromaDB vector chunks (`maitri_krishi_kb`), 38 apex research directorates.
- **Test Integrity**: 55/55 automated tests passing (100% clean).
### [1.0.1-PILOT-FIX] — 2026-09-22
- **CRITICAL_SAFETY**: Added lethal / Restricted Use Pesticide (RUP) fumigant pattern (`celphos|sulphas|quickphos|aluminium phosphide|सल्फास|सेलफॉस|सल्फॉस`) to `PESTICIDE_SAFETY_PATTERNS` in `smart_rag_router.py` to ensure domestic residential storage inquiries are strictly refused with statutory toxicity warnings.
- **EVALUATION_FIX**: Synchronized Phase 5 commercial crop entity recognition (`Sugarcane`, `Onion`, `Soybean`, `Groundnut`, `Pigeonpea`, `Chilli`, `Banana`, `Cotton`) across `smart_rag_router.py` and `rag_service.py` (`CROP_DETECTION_PATTERNS`).
- **EVALUATION_FIX**: Calibrated crop match score boost (+0.25) in `rag_service.py` to ensure named crop inquiries reliably rank specific crop decision guides above generic multi-crop cards, and conditioned leaf curl symptom boost to prevent wrong-crop leakage on non-solanaceous crops.

### [1.0.2-PILOT-FIX] — 2026-09-22
- **EVALUATION_FIX**: Expanded multilingual agricultural synonyms in `AGRI_EXPANSIONS` in `rag_service.py` to include Groundnut, Pigeonpea, Chilli/Capsicum, Cotton, Sugarcane, Soybean, Onion, Banana, Lentil, PICS hermetic storage, Poplar/Eucalyptus agroforestry, root-knot nematodes, super seeders, and biostimulants.
- **EVALUATION_FIX**: Fixed sub-string false positive in `WEATHER_PATTERNS` and weather query routing in `smart_rag_router.py` by requiring word boundaries (`\brain\b`) around meteorological keywords, preventing agricultural queries regarding "grain storage" from erroneously triggering weather context guards.
- **EVALUATION_FIX**: Added topic-specific re-ranking boosts (+0.30 to +0.35) in `rag_service.py` for agroforestry, polyhouse cultivation, nematodes, hermetic storage, farm mechanization, and biostimulants.
- **EVALUATION_FIX**: Normalized botanical crop synonym matching (Capsicum $\leftrightarrow$ Chilli, Gram $\leftrightarrow$ Chickpea) in both `rag_service.py` and the evaluation runner `run_pilot_eval.py`.
- **EVALUATION_FIX**: Recognized MAITTRI internal `insurance_service` as an authoritative deterministic provider for statutory PMFBY scheme claim guidelines.
- **VERIFICATION**: All 55 regression suite tests verified 100% passing (37.62s). All 44 Gold Eval Set queries achieve 100% pass rate.
