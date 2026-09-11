# Product and Research Requirements Document

## Document control

| Field | Value |
|---|---|
| Working title | AI-Powered Multilingual Smart Agriculture Decision Support System for Uttar Pradesh |
| Short name | Smart Agriculture DSS |
| Document role | Authoritative product and research source of truth |
| Version | 1.0 |
| Status | Approved baseline; district/crop scope pending Phase 0 evidence audit |
| Date | 2026-09-04 |
| Target | Final-year B.Tech CSE/AI project and research prototype |

## 1. Executive summary

This project will design and evaluate a hybrid, bilingual agricultural decision-support prototype for a constrained set of districts, crops, and seasons in Uttar Pradesh, India. It will help a farmer compare feasible crop options by combining authoritative agronomic constraints, evidence-quality-aware inputs, predictive baselines, historical weather and production data, economic uncertainty analysis, and source-grounded English/Hindi explanations.

The design addresses two practical problems. First, agricultural decisions depend on season, soil condition, irrigation, crop history, weather, and market uncertainty, while the relevant information is fragmented. Second, many public crop-recommendation models require exact N, P, K, and pH measurements that farmers may not possess. The system will therefore use three soil-information tiers and will change its inference path as evidence weakens. It will never invent laboratory-like values merely to satisfy a model schema.

Public NPK-climate crop datasets may be used as benchmark experiments only after provenance, feature meaning, units, licensing, duplicates, and synthetic/augmented status are audited. Strong benchmark accuracy will not be described as proof of field utility. Official district crop statistics may support district-season yield baselines; official wholesale mandi price histories may support gross-margin scenarios. Neither source supports guaranteed field yield or profit claims.

The primary contribution is an evaluated system architecture, not a novel ML algorithm. The project will compare rules-only, ML-only, and hybrid Top-3 recommendation paths; use geographic and temporal holdouts; measure uncertainty calibration; evaluate bilingual retrieval and generation separately; and enforce safe abstention for unsupported or high-risk requests.

## 2. Problem statement

Crop-selection support for smallholder farmers must operate under incomplete soil information, geographic heterogeneity, changing weather, price uncertainty, and multilingual communication needs. Public crop-classification benchmarks can be highly separable while lacking the provenance, variable semantics, and deployment-shaped validation needed for real regional recommendations. Unconstrained generative AI can also present unsupported agricultural instructions confidently.

This project investigates whether a region-constrained hybrid decision-support architecture can produce more transparent and defensible crop recommendations by combining:

- hard agronomic constraints;
- predictive models evaluated outside the locations and years used for training;
- explicit input and outcome uncertainty;
- market and cost scenarios instead of financial guarantees;
- versioned, authoritative retrieval for explanations; and
- deterministic safety routing and abstention.

## 3. Product vision

A farmer should be able to provide the information they genuinely know and receive up to three feasible crop options, each with:

- a clear suitability explanation;
- important constraints and missing information;
- an evidence/confidence tier;
- a district-season yield baseline and calibrated range when supported;
- a mandi-linked gross-margin scenario distribution when supported;
- source names, dates, and applicability; and
- a safe next action, such as obtaining a soil test or consulting a KVK/agronomist.

The product must make uncertainty visible. A cautious, source-backed partial answer or abstention is preferred to a precise-looking unsupported recommendation.

## 4. Users and stakeholders

| Role | Need | MVP interaction |
|---|---|---|
| Farmer/user | Compare feasible crops using information they have | Create a scenario, receive Top-3 options, ask English/Hindi questions |
| Agronomist/KVK reviewer | Verify regional suitability and safety | Review rules, test cases, recommendations, and explanations |
| Student researcher | Run reproducible experiments and error analysis | Manage datasets, splits, configurations, and reports |
| Project administrator | Curate sources and monitor system health | Approve documents/rules, inspect audit logs, disable stale sources |
| Academic evaluator | Verify claims and reproducibility | Re-run experiments and inspect evidence-to-result traceability |

## 5. Scope

### 5.1 Geographic and crop scope

The evaluated MVP is limited to Uttar Pradesh. Three to five districts and six to eight crops will be frozen only after the Phase 0 completeness audit.

Candidate crops for the audit are wheat, rice, maize, mustard, chickpea, potato, and one additional crop only if evidence is complete. Candidate districts should span meaningfully different agro-climatic conditions, but no district is supported until the evidence matrix passes.

Inclusion requires all of the following:

1. traceable agronomic guidance applicable to the crop and region;
2. sufficient district/crop/season/year area and production history;
3. usable historical weather coverage with documented spatial limitations;
4. usable mandi price history aligned to commodity, market, and sale window;
5. a review path with a relevant agronomy expert; and
6. adequate sample support for the intended evaluation.

If fewer crops or districts pass, the MVP shrinks. No missing layer may be hidden behind a generic national average.

### 5.2 In scope

- Scenario-based farmer profile: district, season, land area, irrigation, previous crop, intended sowing period, optional cost assumptions, and soil information actually available.
- Three soil-information confidence tiers.
- Versioned agronomic rule engine with hard exclusions and soft preferences.
- Benchmark crop model, where scientifically justified.
- Rules-only, ML-only, and hybrid Top-3 comparison.
- District-season yield baselines with empirically calibrated prediction intervals.
- Gross-margin scenario simulation using yield, price, and variable-cost uncertainty.
- English/Hindi retrieval-grounded explanations and follow-up questions.
- Hinglish robustness test set.
- Source citations, timestamps, applicability, warnings, and abstention.
- Admin/research functions for source approval, rule versions, experiment configuration, and evaluation exports.
- Reproducible data, model, safety, and RAG evaluation.

### 5.3 Out of scope

- Autonomous agronomic decision-making.
- Guaranteed crop success, yield, sale price, or profit.
- Exact pesticide/chemical dose generation by an LLM.
- General fertilizer prescriptions without an approved region/crop/soil rule.
- Disease-image diagnosis, remote sensing, drones, IoT, or sensors.
- Voice, OCR, WhatsApp/SMS, and languages beyond English/Hindi.
- National coverage or extrapolation outside tested districts/crops/seasons.
- Field-level yield prediction without field-level outcome and management data.
- Automatic execution of purchases, loans, insurance, or market transactions.

## 6. Research questions and hypotheses

### RQ-A: Recommendation validity

Does a rule-constrained hybrid system improve agronomic validity over ML-only and rules-only baselines for the frozen UP scope?

- Primary endpoint: blinded expert-valid Top-3 recommendation rate.
- Secondary endpoints: hard-constraint violation rate, macro-F1 where labels are valid, Top-3 recall, calibration, and abstention rate.
- Hypothesis: the hybrid system will reduce hard-constraint violations and be non-inferior or better on expert-valid Top-3 recommendations.

### RQ-B: Missing soil evidence

How do recommendation quality, confidence, and abstention change from measured soil data to regional or observable-only information?

- Primary endpoint: degradation in expert-valid Top-3 rate across soil tiers.
- Secondary endpoints: confidence calibration, recommendation stability, and appropriate abstention.
- Hypothesis: uncertainty and abstention should increase as evidence weakens; the system must not create pseudo-laboratory values.

### RQ-C: Yield baseline transferability

How accurately can official historical data estimate district-season yield for unseen districts and years?

- Primary endpoint: MAE in physical units on geographic and temporal holdouts.
- Secondary endpoints: RMSE, improvement over naive baselines, interval coverage, interval width, and subgroup errors.
- Hypothesis: a tuned model may improve on naive baselines, but its value is accepted only if holdout performance and interval calibration are adequate.

### RQ-D: Bilingual grounded assistance

Does an authority-filtered RAG pipeline with deterministic routing and abstention produce more supported and safer English/Hindi answers than an unconstrained LLM?

- Primary endpoints: supported-claim proportion and unsafe actionable answer rate.
- Secondary endpoints: retrieval Recall@K/nDCG, citation precision/completeness, answer relevance, abstention precision/recall, and meaning preservation in Hindi/Hinglish.
- Hypothesis: the constrained pipeline will improve evidence support and reduce unsafe answers, although it cannot guarantee zero hallucination outside the fixed test set.

### Optional RQ-E: Economic rank stability

How stable are crop rankings under plausible yield, price, and variable-cost uncertainty?

This is secondary. It must not delay RQ-A through RQ-D.

## 7. Core concepts

### 7.1 Soil-information tiers

| Tier | Available evidence | Allowed inference | Required display behavior |
|---|---|---|---|
| Tier 1 - measured | Current, traceable soil test with defined method, units, date, and sample context | Validated model and rules may use measured values within their applicability | Show test date/source, model applicability, and remaining uncertainty |
| Tier 2 - regional | District/block-level summaries or mapped distributions; no current field test | Use distributions/priors and propagate uncertainty; apply regional rules | Label all values as regional estimates, reduce confidence, recommend testing |
| Tier 3 - observable | Soil type/texture/color/drainage, irrigation, district, season, crop history | Conservative rule/ranking path using only observed variables | Do not call an exact-NPK model; show low confidence and missing evidence |

Tier 2 values must never be rendered as the user's measured N/P/K/pH. Tier 3 must not invoke a pipeline that requires those exact values.

### 7.2 Recommendation score

Eligible crops may be ranked with a transparent score after hard constraints are applied:

\[
S(c)=w_AA_c+w_WW_c+w_II_c+w_RR_c+w_EE_c-w_QQ_c
\]

where agronomic suitability, weather compatibility, irrigation compatibility, rotation compatibility, economic attractiveness, and quantified risk are separately represented.

Weights require documented expert input and sensitivity analysis. Correlated criteria such as yield and gross margin must be checked for double-counting. A hard seasonal or safety constraint cannot be overcome by a high soft score.

### 7.3 Yield output

The system may report a district-season yield baseline only at the statistical level supported by the source data. Example wording:

> Historical-model district-season baseline: 3.4 t/ha. 80% calibrated prediction interval: 2.8-4.1 t/ha. Reliability: moderate. This is not a field-level guarantee.

Arbitrary fixed `+/-10-20%` bands are prohibited. Intervals must come from residual, quantile, bootstrap, or conformal methods and must be evaluated on locked holdouts.

### 7.4 Economic output

Unless complete cost accounting exists, the output is a gross-margin scenario:

\[
GM=(Y \times P)-C_{variable}
\]

For each crop, report P10/P50/P90 gross margin and probability of negative gross margin, with the market, commodity/variety when available, sale window, price-history period, yield basis, and user/default cost assumptions visible. Do not call this guaranteed profit.

## 8. Functional requirements

Requirements are labeled `FR-n` for traceability.

### 8.1 Profile and scenario input

- **FR-01:** The user can choose English or Hindi; the language can be changed without losing the scenario.
- **FR-02:** The user can create a recommendation scenario without creating a permanent personal account.
- **FR-03:** Required inputs are district, season/sowing window, irrigation availability, land area, and previous crop or `unknown`.
- **FR-04:** Soil inputs are collected through explicit Tier 1, Tier 2, or Tier 3 flows.
- **FR-05:** Units are displayed and validated at entry; the system stores normalized values plus original values/units.
- **FR-06:** Missing values remain missing unless a documented transformation creates an estimate; estimates carry source and uncertainty metadata.
- **FR-07:** Inputs outside supported range or geography trigger correction guidance or abstention, not silent clipping.

### 8.2 Recommendation

- **FR-08:** The system returns zero to three eligible crops after hard constraints.
- **FR-09:** Each crop displays rank, agronomic reasons, limiting factors, evidence tier, uncertainty, and source applicability.
- **FR-10:** If no crop meets the minimum evidence and safety criteria, the system abstains and explains what information or expert help is needed.
- **FR-11:** The inference record stores model/rule versions, source versions, inputs, outputs, confidence, and abstention reason.
- **FR-12:** The UI does not present ML probability as the probability that the crop will succeed or be profitable.
- **FR-13:** The user can compare the Top-3 options across water need, season fit, rotation fit, yield baseline, gross-margin scenarios, and risk.

### 8.3 Yield and economics

- **FR-14:** Yield is shown only when the crop/district/season combination passes model applicability and data-quality checks.
- **FR-15:** The yield card displays geographic level, data period, interval level, interval, reliability, and limitations.
- **FR-16:** Economic scenarios use a selected or clearly defaulted mandi, expected sale window, price distribution, yield distribution, and cost range.
- **FR-17:** The user may override costs, and the output distinguishes user values from defaults.
- **FR-18:** Economic rankings include sensitivity or rank-stability information when used in the final recommendation score.

### 8.4 Bilingual RAG assistant

- **FR-19:** Every answer is routed by risk class before retrieval or generation.
- **FR-20:** General explanatory answers use only approved corpus sources and show claim-linked citations.
- **FR-21:** Time-sensitive answers display source date/version and retrieval timestamp.
- **FR-22:** Exact fertilizer guidance is allowed only through an approved deterministic rule/document pathway whose crop, region, soil-test method, unit, and validity match the scenario.
- **FR-23:** Pesticide/chemical dose requests abstain unless a separately approved current authoritative pathway is implemented; no such pathway is part of MVP.
- **FR-24:** The assistant preserves numbers, units, warnings, and negation when answering in Hindi.
- **FR-25:** Unsupported crops, regions, conflicting evidence, stale sources, prompt injection, or inadequate retrieval trigger an explicit abstention template.
- **FR-26:** Each RAG interaction logs the query, risk route, retrieved chunk IDs/scores, source versions, answer, citations, and abstention status without storing unnecessary personal data.

### 8.5 Administration and reproducibility

- **FR-27:** Only approved sources and rule versions may be active in user-facing inference.
- **FR-28:** Updating a rule/source creates a new version and does not rewrite prior inference history.
- **FR-29:** An administrator can disable a stale or unsafe source without redeploying the entire application.
- **FR-30:** Each reported experiment is reproducible from a data manifest, split file, configuration, seed, environment lock, code revision, and output record.
- **FR-31:** The project can export the tables and figures used in the final report from clean inputs through one documented command/workflow.

## 9. Safety policy

| Query type | Mechanism | Response policy |
|---|---|---|
| General crop explanation | Approved RAG plus LLM | Answer with evidence and limitations |
| Crop calendar | Versioned authoritative rule/document | Translate or summarize without changing dates/units |
| Weather warning | Timestamped weather plus validated threshold | Show source, location level, and timestamp |
| Soil-test interpretation | Applicable deterministic rule plus explanation | Require units/method where relevant; show uncertainty |
| Exact fertilizer dose | Approved crop-region-soil rule only | Abstain if any applicability field is missing |
| Pesticide/chemical treatment | Outside MVP | Refuse actionable dosage and direct to official/local expert help |
| Financial guarantee | Never allowed | Present scenario distribution and assumptions |
| Unsupported crop/region | No inference | Abstain explicitly |

The system reduces hallucination risk; it does not claim to eliminate hallucinations. Safety claims must be tied to measured test-set behavior.

## 10. Non-functional requirements

- **NFR-01 - Traceability:** Every user-facing recommendation is traceable to input, code/model/rule version, and evidence versions.
- **NFR-02 - Reproducibility:** A clean environment can regenerate primary results using pinned dependencies and frozen data/splits.
- **NFR-03 - Reliability:** External API failure produces cached/stale labeling, degraded mode, or abstention; it never fabricates fresh data.
- **NFR-04 - Performance:** On the reference deployment, non-LLM recommendation p95 latency target is <=2 seconds and RAG answer p95 target is <=10 seconds, excluding documented cold-start/provider outages.
- **NFR-05 - Accessibility:** Mobile-first interface, readable contrast, simple language, keyboard support, clear units, and no meaning conveyed by color alone.
- **NFR-06 - Localization:** All static user-facing text is externalized; English/Hindi parity is tested.
- **NFR-07 - Security:** Least privilege, encrypted transport, protected secrets, input validation, rate limits, dependency scanning, and PII-redacted logs.
- **NFR-08 - Privacy:** Collect the minimum data for a stated purpose, support consent withdrawal/correction/erasure flows where applicable, and use defined retention.
- **NFR-09 - Auditability:** High-risk routing, source selection, and abstention decisions are inspectable.
- **NFR-10 - Cost control:** Provider calls are budgeted, cached where appropriate, and observable; core recommendation remains functional without an LLM.

## 11. Data governance summary

| Data | Default policy |
|---|---|
| Permanent farmer identity | Not required for MVP; use pseudonymous scenario ID |
| Precise coordinates | Do not collect unless a frozen requirement proves necessity; district is the default resolution |
| Soil-test record | Store only with purpose and consent; restrict access; keep method/unit/date |
| Financial inputs | Optional and user-controlled; do not send to external LLMs |
| Chat logs | Off by default for research reuse; de-identify and obtain appropriate consent if retained |
| API/application logs | Exclude raw sensitive payloads; rotate on a defined schedule |
| Expert/farmer study data | Require institutional ethics determination and understandable consent before collection |

The design must be reviewed against the Digital Personal Data Protection Act, 2023 and the notified Digital Personal Data Protection Rules, 2025, including their staged commencement. This document is an engineering baseline, not legal advice.

## 12. UX requirements

The recommendation journey should use progressive disclosure:

1. language and supported-location check;
2. season, irrigation, land, and crop-history questions;
3. soil-evidence tier selection;
4. review of normalized inputs and missing evidence;
5. Top-3 or abstention result;
6. side-by-side comparison;
7. evidence-grounded follow-up questions.

Every result screen must visibly state:

- `Decision support, not a guarantee`;
- the supported location/crop/season boundary;
- evidence tier and important missing inputs;
- when weather, price, or source information was last updated; and
- when local expert or soil-test confirmation is recommended.

## 13. Acceptance criteria

The evaluated MVP is accepted only when all mandatory conditions pass:

### Evidence and scope

- Every active dataset has a manifest with checksum, source/version, license, semantics, units, geography, time span, and limitations.
- Unresolved benchmark provenance is explicitly labeled `unknown`; it is not represented as Indian field evidence.
- Supported districts/crops/seasons are frozen from a completed coverage matrix.
- Every active agronomic rule has source, applicability, version/date, and reviewer status.

### Recommendation

- Zero hard-constraint violations on the locked deterministic constraint suite.
- Blinded expert-valid Top-3 rate meets the pre-registered target in `EVALUATION_PLAN.md`.
- Tier 2/3 results never display estimated regional NPK as measured farmer data.
- Out-of-domain and unsupported scenarios abstain according to the frozen policy.

### Yield and economics

- Yield is evaluated on both unseen-location and unseen-time tests where the data permit.
- Prediction interval coverage is reported; no arbitrary interval is used.
- Economic results are labeled gross-margin scenarios with P10/P50/P90, loss probability, and visible assumptions.

### RAG and language

- The locked bilingual safety set has zero actionable pesticide-dose generation and zero unsupported exact fertilizer-dose generation.
- Claim support, citation, abstention, and Hindi meaning-preservation metrics meet the pre-registered thresholds or the feature is restricted/disabled.
- Prompt-injection and conflicting-source cases are included in the final failure report.

### Engineering and research

- Unit, integration, data-contract, safety, and end-to-end critical-path tests pass.
- No secrets or personal data appear in source control, logs, test fixtures, or model artifacts.
- Primary results can be regenerated from a documented clean run.
- Limitations and negative results are reported; failed hypotheses are not hidden.

## 14. Success measures

The project is successful if it demonstrates an honest, traceable evaluation of the hybrid design, even if a sophisticated model fails to beat a simple baseline. Feature count and benchmark accuracy alone are not success measures.

Primary project outcomes:

- defensible evidence and provenance package;
- measured comparison of rules-only, ML-only, and hybrid recommendations;
- deployment-shaped spatial/temporal evaluation;
- calibrated uncertainty or a documented decision not to expose an unreliable module;
- bilingual, cited assistance with measurable abstention and safety behavior;
- reproducible code, reports, and artifacts; and
- credible explanation of limitations in the final dissertation/viva.

## 15. Risks and mitigations

| Risk | Impact | Mitigation/decision |
|---|---|---|
| Benchmark NPK data has unknown provenance or semantics | Invalid field interpretation | Restrict to benchmark; do not use for deployment claims |
| Official sources are incomplete or inconsistent | Reduced crop/district scope | Freeze scope after completeness audit; preserve raw snapshots and QA logs |
| Random splitting inflates metrics | False confidence | Grouped development CV plus locked district and year holdouts |
| Too few observations for a crop/district | Unstable estimates | Merge only when scientifically justified or remove that slice |
| No agronomy reviewer | Weak validity and unsafe rules | Make reviewer access a gate; reduce project to research benchmark if unavailable |
| RAG cites but does not support claims | Misleading explanation | Claim-level evidence checks and human review sample |
| Hindi translation changes dosage/unit/negation | Safety error | Protected numeric tokens, glossary, bilingual gold set, abstention |
| Market price differs from farmgate price | Misleading economics | Label wholesale source; show assumptions and scenarios, not profit promise |
| External API/model outage | Broken or stale output | Cache with timestamps, retry safely, degraded mode, abstain when freshness matters |
| Scope creep | Incomplete research | Enforce out-of-scope list and gated change control |

## 16. Required deliverables

1. Version-controlled application and pipeline code.
2. Data manifests, dictionaries, licenses, quality reports, and frozen splits.
3. Versioned agronomic rules and reviewer record.
4. Model cards and experiment logs for every reported model.
5. Approved RAG corpus manifest, Hindi glossary, and fixed evaluation set.
6. Recommendation, yield, economics, RAG, language, and safety results.
7. Architecture and API documentation.
8. Privacy/data-governance record and study consent/ethics documentation if humans participate.
9. Final dissertation/report with limitations and reproducibility appendix.
10. Demonstration deployment or local reproducible demo.

## 17. Decision gates

| Gate | Decision | Evidence required |
|---|---|---|
| G0 | Freeze districts/crops/seasons | Completeness matrix, expert route, data manifests |
| G1 | Permit benchmark model training | Provenance/semantics/license audit; intended-use statement |
| G2 | Permit hybrid recommendation integration | Reviewed rules; baseline evaluations; no leakage |
| G3 | Permit yield display | Holdout errors and interval coverage acceptable for declared use |
| G4 | Permit economic ranking | Source alignment, cost assumptions, Monte Carlo and sensitivity review |
| G5 | Permit RAG user testing | Approved corpus, router, citations, safety suite |
| G6 | Permit final claims | Locked evaluation complete; negative results and limitations included |

## 18. Definition of done

The project is done when the frozen MVP works end to end, every claim is backed by an auditable experiment or source, every high-risk path behaves according to policy, and the final report can be reproduced. It is not done merely because the interface can produce recommendations.

## 19. Foundational sources

This PRD operationalizes the attached 2026 deep-research review and uses the following public sources as initial anchors. Each source must still be captured in a project manifest with access date and exact artifact/version before use:

- [District-wise, season-wise crop production statistics - Open Government Data Platform India](https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0)
- [Current daily mandi prices - Open Government Data Platform India](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)
- [NASA POWER Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [ICAR soil test and target yield approach](https://www.icar.gov.in/en/node/1463)
- [Digital Personal Data Protection Act, 2023](https://www.meity.gov.in/content/digital-personal-data-protection-act-2023)
- [Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa)
- [ARES: evaluation of retrieval-augmented generation systems](https://aclanthology.org/2024.naacl-long.20/)
- [Spatial validation reveals poor predictive performance of large-scale ecological mapping models](https://www.nature.com/articles/s41467-020-18321-y)
- [Crop Recommendation Dataset data card - benchmark candidate only](https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data)

