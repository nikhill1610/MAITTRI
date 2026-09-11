# Data and Evidence Plan

## 1. Purpose

This file defines what evidence may enter the system and what claims it may support. No dataset, agronomic rule, RAG document, model, or external API response may be used in user-facing decisions without traceable provenance and an explicit applicability statement.

## 2. Evidence hierarchy

| Tier | Evidence | Permitted use |
|---|---|---|
| A | Government/official datasets; ICAR, state agriculture university, KVK, or other authoritative agronomic publication; peer-reviewed original empirical research | Rules, regional context, model targets/covariates, and evaluation when fit for purpose |
| B | Dataset repositories with clear provenance/license; credible technical reports; peer-reviewed secondary research | Benchmarking or supporting evidence with limitations |
| C | Kaggle uploads with incomplete lineage, GitHub repositories, student projects, commercial descriptions, blogs | Discovery and engineering comparison only; never sole agronomic authority |

Source authority does not remove the need to check unit, geography, date, sampling, missingness, and statistical level.

## 3. Initial source registry

| Domain | Candidate source | Intended use | Known limitation/status |
|---|---|---|---|
| Crop production | Government of India district-wise crop production data | Derive district/crop/season/year yield as production divided by area after unit QA | Aggregate district outcome, not field yield |
| Mandi prices | AGMARKNET-generated daily price resource via data.gov.in | Historical min/max/modal wholesale price distributions aligned to market and sale window | Wholesale is not guaranteed farmgate realization; variety/quality coverage varies |
| Historical weather | NASA POWER Daily API | District-level historical meteorological covariates and reproducible fallback | Approximately 0.5 degree grid for relevant products; not plot-level weather |
| Current weather | Provider selected during implementation spike | Display current conditions and timestamped warning inputs | Provider/license/coverage/freshness must be frozen before use |
| Soil/agronomic rules | ICAR/state agriculture university/KVK/official state material | Crop feasibility, soil interpretation, crop calendar, approved nutrient rules | Applicability may be crop-, soil-method-, region-, and edition-specific |
| Regional soil information | Soil Health Card/open official summaries where legally and technically available | Tier 2 distributions/priors and coverage analysis | Never present as the farmer's measured field values |
| Crop benchmark | Public NPK-climate crop recommendation dataset | Algorithm benchmark and missing-input stress experiment | Provenance, feature semantics, units, label construction, and synthetic status unresolved until audit |
| RAG corpus | Approved authoritative English/Hindi documents | Explanations and general guidance | Must be versioned, parsed, reviewed, and filtered by applicability/freshness |

## 4. Mandatory dataset manifest

Create `data/manifests/DATA_MANIFEST.csv`. One row represents one immutable raw artifact or API snapshot.

Required columns:

```text
dataset_id
artifact_name
source_organization
source_url_or_resource_id
retrieved_at_utc
published_or_updated_date
version
sha256
license_name
license_url_or_file
raw_format
record_count
field_count
geographic_unit
geographic_coverage
temporal_granularity
temporal_coverage
target_definition
feature_semantics_status
units_status
observed_or_synthetic
personal_data_present
intended_use
prohibited_use
quality_report_path
notes
```

Unknown values must be written as `unknown`, not guessed. A dataset cannot pass Gate G1 while target construction, critical feature semantics, or units are unknown for the claimed use.

## 5. Data dictionary

Create `data/manifests/DATA_DICTIONARY.md` after acquisition. For every variable record:

- canonical field name and source field name;
- definition and allowed meaning;
- unit and conversion formula;
- type, valid range, missing-value codes, and category mapping;
- measurement/aggregation method;
- spatial and temporal level;
- leakage risk;
- personally identifying or sensitive status;
- transformations and source citation.

N, P, and K require special scrutiny. The project must determine whether each field represents soil concentration/status, nutrient ratio, externally applied fertilizer quantity, or a synthetic/normalized value. These meanings are not interchangeable.

## 6. Provenance audit procedure

For every candidate source:

1. Download or snapshot through a reproducible command/client.
2. Preserve the raw artifact unchanged.
3. Record URL/resource ID, retrieval timestamp, source update/version, and SHA-256.
4. Preserve license/terms and citation metadata.
5. Verify schema, row count, units, geographic level, temporal coverage, missingness, invalid ranges, exact duplicates, and likely near duplicates.
6. Trace target labels or derived targets to their construction method.
7. Determine whether records are observed, simulated, synthetic, or augmented.
8. Write a quality report and intended/prohibited-use statement.
9. Obtain domain review for variables used in agronomic decisions.
10. Assign status: `approved`, `benchmark_only`, `quarantined`, or `rejected`.

Cleaning never overwrites raw files. Every processed artifact records its parent IDs and transformation version.

## 7. Phase 0 completeness matrix

Create `data/manifests/SCOPE_COMPLETENESS.csv` with one row per candidate crop-district-season combination:

```text
crop
district
season
production_years_count
production_missing_rate
weather_coverage_status
price_market
price_years_count
price_match_quality
agronomic_rule_source_count
soil_information_status
expert_review_available
sample_size_estimate
known_unit_or_mapping_issues
include_decision
decision_reason
```

A combination is included only if agronomic guidance, outcome history, weather coverage, usable market data, and an expert-review path are all adequate for the claims planned. The chosen scope and exclusions must be documented before final experiments.

## 8. Derived targets and unit control

District yield may be derived as:

\[
Yield_{d,c,s,t}=\frac{Production_{d,c,s,t}}{Area_{d,c,s,t}}
\]

This derivation is permitted only after validating area and production units, nonzero area, duplicates, administrative-boundary changes, crop naming, season naming, and missing/suppressed values. The result must remain labeled `district-season yield`.

Price processing must record market, commodity, variety when available, grade/quality when available, date, min/max/modal value, and unit. Unit conversion must be explicit and tested. Price history must be aligned to a declared expected harvest/sale window; arbitrary full-year averages are not the default.

## 9. Agronomic rule registry

Store rules in a machine-readable, version-controlled form. Every rule must include:

```text
rule_id
rule_version
status
risk_class
crop
state
district_or_zone_applicability
season
soil_test_method
input_variable
operator_or_equation
threshold_or_parameters
unit
target_yield_if_applicable
recommendation_or_constraint
source_organization
source_title
source_url
publication_or_edition_date
effective_from
reviewed_at
reviewer_role
supersedes_rule_id
notes
```

Rules with missing applicability or unit information cannot generate exact high-risk guidance. A deterministic engine can still be unsafe if its rules are stale or regionally wrong, so review and versioning are mandatory.

## 10. RAG corpus manifest

Every ingested document must have:

- stable document ID and content checksum;
- source authority tier and organization;
- title, URL, edition/version, publication date, and retrieval date;
- language;
- applicable crop, state/district/zone, season, growth stage, and topic;
- risk classes the document may support;
- expiration/review date for time-sensitive content;
- parsing/OCR method and quality status;
- chunking configuration and embedding version;
- approval status and reviewer role.

Retrieved chunks must retain document/page/section identity. The system must filter by status, applicability, language, and freshness before vector/keyword ranking. Citation presence alone is not evidence of claim support; evaluation is claim-level.

## 11. Split and leakage rules

- Freeze exact split files in `data/splits/`.
- Use grouped development cross-validation; do not randomly mix near-identical district/year observations across folds.
- Maintain a fully unseen geographic test and a fully unseen temporal test when scientifically possible.
- Fit imputation, scaling, encoding, feature selection, resampling, and calibration inside training folds only.
- Run exact and near-duplicate checks before splitting and again across split boundaries.
- Do not tune thresholds, weights, rules, prompts, or retrievers on the locked final test.
- If data cannot support a district/year holdout, narrow the claim and state that limitation.

## 12. Personal-data inventory

| Field | Needed in MVP? | Default storage | External model exposure | Retention |
|---|---|---|---|---|
| Name/mobile/email | No for anonymous demo | Do not collect | Never | None |
| Pseudonymous scenario ID | Yes | Database | Not needed | Defined project period |
| District | Yes | Scenario record | Only if necessary for question context | Defined project period |
| Precise coordinates | No | Do not collect | Never | None |
| Soil-test data | Optional Tier 1 | Restricted structured record | Redacted/minimized if needed | User-controlled/defined |
| Land area/crop history | Scenario inputs | Restricted scenario record | Avoid unless required | Defined project period |
| Cost/financial assumptions | Optional | User-controlled scenario | Never by default | Short/defined |
| Chat content | Optional for operation; separate consent for research reuse | De-identify and restrict | Processor-specific minimum | Short/defined |
| Operational logs | Yes | PII-redacted | Not applicable | Rotated schedule |

Before human studies, obtain the university's ethics determination and use understandable English/Hindi consent covering recordings, withdrawal, compensation, retention, and contacts.

## 13. Artifact lineage

Every reported result must link:

```text
raw artifact -> manifest -> quality report -> transformation config -> processed artifact
-> frozen split -> experiment config -> environment/code revision -> predictions
-> metric table/figure -> reported claim
```

If any link is missing, the claim is not reproducible and must not appear as a final result.

