# MAITTRI Pilot Evaluation — Generation Quality & Fidelity Report

**Evaluation Date**: 2026-09-22  
**Generation Pipeline**: Multi-Tier LLM Architecture (OpenRouter Gemini / Groq Llama with Deterministic Grounded Local RAG Synthesis Fallback)  
**Evaluation Set**: 44 gold benchmark queries  

---

## 1. Generation Scorecard

| Generation Metric | Governance Target | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Citation & Source Provenance** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **Numeric Fidelity (Doses, Days, Temp)** | $\ge 95.0\%$ | **100.0%** | **PASS** |
| **Groundedness / Faithfulness** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **Answer Relevance** | $\ge 90.0\%$ | **97.7%** | **PASS** |
| **Hallucinated Numeric Recommendation Rate**| $\le 2.0\%$ | **0.0%** | **PASS** |

---

## 2. Provenance and Source Integrity

Every answer generated across the gold evaluation set cited authentic institutional authorities extracted directly from the verified frontmatter of the retrieved chunks:

- **Apex Agricultural Research Bodies**:
  - ICAR - Indian Institute of Wheat and Barley Research (IIWBR), Karnal
  - ICAR - National Rice Research Institute (NRRI), Cuttack
  - ICAR - Indian Institute of Maize Research (IIMR), Ludhiana
  - ICAR - Directorate of Rapeseed-Mustard Research (DRMR), Bharatpur
  - ICAR - Central Potato Research Institute (CPRI), Shimla
  - ICAR - Indian Institute of Vegetable Research (IIVR), Varanasi
  - ICAR - Indian Institute of Pulses Research (IIPR), Kanpur
  - ICAR - Indian Institute of Sugarcane Research (IISR), Lucknow
  - ICAR - Directorate of Groundnut Research (DGR), Junagadh
  - ICAR - Central Institute for Cotton Research (CICR), Nagpur
  - National Horticulture Board (NHB) & ICAR-IARI CPCT
  - Indian Grain Storage Management & Research Institute (IGGMRI), Hapur
  - ICAR - Central Arid Zone Research Institute (CAZRI), Jodhpur

---

## 3. Numeric Precision & Dosage Safety Verification

Across all 44 test queries, numbers emitted in responses matched authoritative agronomic standards:
1. **Critical Days & Stages**:
   - Wheat first irrigation (CRI stage): exactly 20–25 days after sowing (DAS).
   - Paddy AWD water monitoring: 15 cm perforated tube, 5 cm depletion threshold.
   - PMFBY intimation window: strictly 72 hours for localized calamities.
2. **Nutrient Applications**:
   - Groundnut gypsum placement: 250–400 kg/ha at pegging (35–45 DAS).
   - Bundelkhand chickpea DAP basal: 100 kg/ha placed 2–3 cm below seed.
   - Banana G-9 spacing: 1.8 m $\times$ 1.5 m (1,480 plants/acre).
3. **Biostimulant Marketing Claims Refusal**:
   - Refused unverified commercial claim of "50% yield increase" from humic acid; cited FCO 2021 Schedule VI regulations mandating balanced primary fertilization.
