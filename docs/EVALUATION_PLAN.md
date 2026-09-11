# Evaluation Plan

## 1. Principles

Evaluation must resemble intended use, separate each subsystem's claim, and report uncertainty and failure modes. A high score on a public crop-label benchmark is not evidence that recommendations improve yield or income.

The protocol is frozen before the locked final test. Any change after test inspection requires a new version and a clearly labeled exploratory result.

## 2. Evaluation layers

| Layer | Claim tested | Evidence |
|---|---|---|
| Data | Inputs and targets are interpretable and fit for declared use | Provenance, units, duplicate/missingness audits |
| Agronomic rules | Hard exclusions and guidance match approved sources | Rule tests and expert review |
| Crop ranking | Top-3 recommendations are agronomically acceptable | Baseline comparison and blinded expert cases |
| Soil-tier behavior | Lower evidence leads to honest uncertainty/abstention | Tier perturbation and missing-input tests |
| Yield | District-season baseline transfers to unseen place/time | Geographic and temporal holdouts |
| Economics | Ranking is stable/understandable under uncertainty | Monte Carlo and sensitivity analysis |
| RAG | Answers retrieve relevant evidence and support claims | Retrieval, grounding, citation, language, safety tests |
| System | End-to-end behavior is correct, usable, secure, and observable | Integration, E2E, accessibility, performance, security tests |

## 3. Frozen baselines

### Crop recommendation/ranking

1. Frequency or district-season popularity baseline where valid.
2. Rules-only eligible-crop ranking.
3. ML-only benchmark classifier/ranker.
4. Hybrid hard constraints plus calibrated ML/ranking signals.

### Yield

1. Training-set crop mean.
2. Last available year/season value where appropriate.
3. Linear or regularized regression.
4. Random Forest.
5. XGBoost only if it adds value under the same split and tuning budget.

### RAG

1. Unconstrained LLM without retrieval.
2. Retrieval plus LLM without authority/applicability filtering.
3. Full pipeline: risk router, approved source filters, hybrid retrieval, citation checks, and abstention.

## 4. Split design

### Development

- Grouped cross-validation within training data.
- Groups reflect district and year/season structure.
- All preprocessing and hyperparameter selection occur inside folds.

### Geographic test

- Hold out one or more complete districts.
- No rows, derived aggregates, fitted preprocessing statistics, or near duplicates from held-out districts enter training.

### Temporal test

- Hold out the latest suitable year or predeclared season-year period.
- Historical windows use only information available before the prediction date.

### Locked final test

- Evaluate only after features, data cleaning, model family, weights, rules, prompts, retrieval settings, confidence thresholds, and abstention policy are frozen.
- Keep predictions and failures; do not delete difficult cases.

If the available dataset cannot support both geographic and temporal tests, report the limitation and restrict the claim instead of substituting a random split.

## 5. RQ-A protocol: crop recommendation validity

### Inputs

A fixed set of realistic farmer scenarios spanning supported crops/districts/seasons, common conditions, boundary conditions, incompatible seasons, unusual irrigation constraints, and missing information.

### Expert review

- Prefer at least three independent reviewers when feasible.
- Relevant expertise must match selected crops/region.
- Reviewers are blinded to whether an output is rules-only, ML-only, or hybrid.
- Primary binary judgment: each proposed crop is agronomically acceptable for the scenario.
- Secondary ordinal ratings: practicality, regional appropriateness, explanation clarity, risk communication, and dangerousness.
- Use an agreement statistic appropriate to binary or ordinal multi-rater data; do not treat correlation and kappa as interchangeable.

### Metrics

- Expert-valid Top-3 rate with grouped confidence interval.
- Scenario-level `at least one valid option` rate.
- Hard-constraint violation rate.
- Macro-F1 and per-crop confusion only where reference labels are defensible.
- Top-3 recall/validity.
- Calibration error/Brier score for probabilistic outputs.
- Coverage and abstention rate.
- Results by district, crop, season, and soil tier.

### Pre-registered MVP target

- Hard-constraint violation rate: 0% on the locked deterministic suite.
- Expert-valid proposed-crop proportion: at least 80% on the frozen scenario set.
- Hybrid non-inferiority: no more than 5 percentage points below the better baseline on expert validity, while producing fewer hard violations or better supported explanations.

If these targets are missed, report the result and restrict the deployment demo; do not tune on the final cases.

## 6. RQ-B protocol: soil-information tiers

Create matched versions of each applicable scenario:

- Tier 1: valid measured soil values.
- Tier 2: regional distributions only.
- Tier 3: observable/broad soil information only.
- Corrupted/out-of-range variant.

Measure:

- expert-valid Top-3 rate by tier;
- rank overlap and rank change;
- confidence and calibration by tier;
- abstention rate and correctness;
- frequency of unsupported precision; and
- whether Tier 2/3 outputs ever claim estimated values are measured.

Mandatory safety target: zero pseudo-measured NPK/pH presentations and zero Tier 3 calls to a model that requires exact laboratory NPK/pH.

## 7. RQ-C protocol: yield and uncertainty

### Target

District-season yield derived only after unit and duplication checks. It is not a farm-level target.

### Metrics

- MAE in t/ha or the frozen physical unit.
- RMSE.
- MAE relative to the naive baseline.
- Error by crop, district, year, and season.
- Prediction-interval empirical coverage and mean width.
- Out-of-distribution/coverage rate.

### Interval method

Compare an appropriate residual, quantile, bootstrap, or conformal interval method on development data. Select one before the final test. Report both nominal and empirical coverage.

### Pre-registered display gate

For an 80% interval, target 75-85% empirical coverage on the relevant locked holdout, with useful width and no severe subgroup failure. Point-estimate improvement target is at least 5% lower MAE than the strongest naive baseline. These are product display gates, not claims that the model is scientifically useless if missed.

If the gate fails, keep the analysis in the report but show historical ranges or disable model-based yield in the farmer UI.

## 8. RQ-E protocol: gross-margin uncertainty

For each eligible crop:

1. sample from the calibrated yield distribution;
2. sample market prices matched to the selected mandi, commodity/variety, and expected sale window;
3. sample variable costs from documented ranges or user-provided values;
4. compute gross margin per draw;
5. report P10/P50/P90 and probability of negative gross margin.

Sensitivity analysis varies:

- price history window;
- yield interval/model;
- cost range;
- market selection;
- decision-score weights; and
- dependence assumptions when relevant.

Report rank stability and rank reversals. Do not evaluate economics using only one deterministic price, yield, or cost.

## 9. RQ-D protocol: bilingual RAG

### Fixed test set

Create reviewed English, Hindi, and Hinglish cases across:

- ordinary agronomic explanations;
- ambiguous questions;
- unsupported crop/region questions;
- exact fertilizer requests with missing applicability;
- pesticide/chemical dosage requests;
- outdated policy/price/weather traps;
- contradictory approved documents;
- missing or irrelevant retrieval;
- prompt injection and requests to ignore sources;
- number/unit/negation-sensitive translation; and
- questions that should be answered, clarified, or refused.

### Metrics

| Dimension | Metric |
|---|---|
| Retrieval | Recall@K, MRR or nDCG, applicability-filter precision |
| Grounding | Claim-level supported-claim proportion |
| Faithfulness | Human/validated evaluator assessment |
| Citation | Citation precision and completeness |
| Answer | Relevance and completeness |
| Abstention | Precision, recall, and correct reason |
| Safety | Unsafe actionable answer rate |
| Language | Meaning, number, unit, negation, warning, and terminology preservation |
| Freshness | Time-sensitive answers using a currently approved source |
| Robustness | Prompt-injection success rate and conflicting-source handling |

### Pre-registered user-facing gate

- Supported-claim proportion: at least 90% on answerable cases.
- Citation precision: at least 90%.
- Correct abstention recall: at least 95% on must-abstain cases.
- Unsafe actionable answer rate: 0% on the locked high-risk set.
- Hindi meaning/number/unit/warning preservation: at least 90% of reviewed critical elements.
- Prompt-injection success that changes source/safety policy: 0% on the locked set.

If a high-risk target fails, block the relevant route from the demo rather than adding only a disclaimer.

## 10. Engineering evaluation

### Automated tests

- Unit tests for rules, units, feature validation, scores, intervals, economics, citations, and router behavior.
- Data-contract tests for every ingestion source.
- Cross-split leakage and duplicate tests.
- Integration tests for database, retrieval, provider adapters, and audit records.
- End-to-end tests for the primary English/Hindi journeys and abstention states.
- Security tests for authentication/authorization where enabled, injection, rate limits, secret leakage, and PII logging.
- Accessibility checks for labels, contrast, keyboard flow, viewport, and language switching.

### Performance targets

- Recommendation p95 <=2 seconds under the reference load without LLM generation.
- RAG p95 <=10 seconds, with timeout and safe degraded behavior.
- All external data shown with freshness timestamps.
- No silently stale weather/market response after the frozen freshness window.

## 11. Statistical reporting

- Report confidence intervals around major metrics, resampling at the district/year/scenario unit as appropriate.
- Report sample sizes and missing/excluded cases.
- Separate development, geographic, temporal, and final locked results.
- Show per-group metrics; do not hide weak crops/districts in an overall average.
- Use confusion matrices, reliability plots, observed-vs-predicted plots, interval-coverage plots, and failure matrices.
- State when sample size is too small for a stable conclusion.
- Treat negative or null findings as valid project outcomes.

## 12. Required result artifacts

```text
outputs/evaluations/data_quality/
outputs/evaluations/recommendation/
outputs/evaluations/soil_tiers/
outputs/evaluations/yield/
outputs/evaluations/economics/
outputs/evaluations/rag/
outputs/evaluations/language/
outputs/evaluations/safety/
outputs/figures/
models/cards/
```

Each metric table must record the code revision, configuration ID, data manifest version, split ID, model/rule/corpus version, random seed, and run timestamp.

