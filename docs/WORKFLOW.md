# Project Workflow and Roadmap

## 1. Operating rule

The critical path is evidence provenance -> scope freeze -> reviewed agronomic rules -> baseline experiments -> locked validation -> expert/safety review -> integration. Frontend polish cannot bypass these gates.

## 2. Fourteen-week research-first plan

| Week | Focus | Required outputs | Exit gate |
|---|---|---|---|
| 1 | Scope and research freeze | PRD review, candidate crops/districts, RQ endpoints, risk register | Supervisor agrees to research boundary |
| 2 | Literature and evidence reconstruction | Source registry, corrected bibliography, evidence hierarchy | Claims map to traceable sources |
| 3 | Data acquisition and provenance | Raw snapshots, manifests, checksums, licenses, initial dictionaries | Candidate data assigned status |
| 4 | Completeness and quality audit | Crop x district x season matrix, quality reports, final supported scope | Gate G0: districts/crops/seasons frozen |
| 5 | Agronomic rule base | Machine-readable rules, source/applicability metadata, rule tests | Relevant expert review path confirmed |
| 6 | Recommendation baselines | Rules-only and ML-only benchmark pipelines, cards/logs | Gate G1: benchmark use approved |
| 7 | Hybrid ranking | Hard constraints, weight rationale, Tier 1/2/3 behavior | Gate G2: hybrid integration approved |
| 8 | Spatial/temporal validation | Frozen splits, grouped CV, locked prediction artifacts | No leakage; primary metrics generated |
| 9 | Yield uncertainty | Naive/models comparison, calibrated interval analysis | Gate G3: display enabled or disabled |
| 10 | Economics | Matched price windows, cost assumptions, Monte Carlo, sensitivity | Gate G4: ranking use enabled or secondary only |
| 11 | RAG corpus and pipeline | Approved corpus manifest, retrieval, citations, risk router | Corpus and policies versioned |
| 12 | Bilingual and safety evaluation | English/Hindi/Hinglish set, grounding, abstention, injection results | Gate G5: allowed user-facing routes frozen |
| 13 | Application integration | Mobile UI, API, database, audits, automated tests, internal demo | End-to-end critical paths pass |
| 14 | Expert review and final package | Blinded evaluation, error analysis, figures, model cards, reproducibility run | Gate G6: final claims frozen |

If time slips, remove optional modules. Do not compress provenance, locked evaluation, or safety testing.

## 3. Work item template

Every task should state:

- purpose and linked requirement/RQ;
- inputs and source/version;
- outputs and exact paths;
- assumptions and prohibited shortcuts;
- tests/validation;
- acceptance criteria;
- expected documentation updates; and
- whether it changes a frozen decision.

## 4. Phase gate checklist

### Before acquiring data

- Source is legally/technically accessible.
- Intended use and expected statistical level are stated.
- Raw destination and naming convention are defined.

### Before training

- Manifest, checksum, license, units, semantics, duplicates, missingness, and target construction are audited.
- Exact split strategy and evaluation metrics are frozen.
- Preprocessing is implemented as a fold-contained pipeline.
- Simple baselines are defined.

### Before registering a model

- Development and locked tests are clearly separated.
- Geographic/temporal results and subgroup failures are reported.
- Calibration/interval behavior is evaluated where exposed.
- Model card includes intended use, exclusions, inputs, metrics, and failure modes.

### Before adding a RAG document

- Authority, date/version, language, applicability, checksum, and review status exist.
- Parsing quality is checked.
- Risk classes the source may support are explicit.
- Staleness/review policy is set.

### Before a user-facing demo

- High-risk routes and abstention tests pass.
- Every result displays limitations, evidence tier, and freshness.
- Error/degraded states are tested.
- No secrets or personal data are exposed.
- Demo claims match locked results.

## 5. Git and change control

- Protect the main branch; merge reviewed, tested changes.
- Prefer small changes tied to one requirement or experiment.
- Do not commit raw secrets, `.env`, personal participant data, large untracked datasets, or generated caches.
- Commit manifests, small metadata, configurations, split definitions, rule sources, tests, model cards, and reproducible reports.
- Tag frozen evaluation releases.
- Record any material scope, metric, source, safety-policy, or architecture change in the PR description and update affected documents in the same change.

Suggested branch prefixes:

```text
docs/
data/
feat/
experiment/
fix/
safety/
```

## 6. Experiment workflow

1. Write the hypothesis and linked RQ.
2. Freeze dataset manifest and split ID.
3. Define baselines, metrics, and decision threshold.
4. Create a configuration with seed and feature contract.
5. Run development experiments only.
6. Select/freeze the pipeline without viewing the locked test.
7. Run locked geographic/temporal/final tests once per registered version.
8. Store predictions, metrics, figures, environment, and code revision.
9. Write model card and error analysis.
10. Decide whether the module is allowed in the user-facing demo.

## 7. Review roles

| Review | Minimum owner |
|---|---|
| Product/scope | Student + supervisor |
| Data provenance/units | Student + source documentation; domain review for agronomic meaning |
| Agronomic rules | Relevant agriculture faculty/KVK/agronomist |
| ML/statistics | Student + technical supervisor/reviewer |
| Hindi terminology | Fluent reviewer with agricultural context |
| Safety/privacy | Supervisor/institutional route; legal review if moving beyond academic demo |
| Human study | Institution's ethics process before recruitment or recording |

## 8. Definition of a completed task

A task is complete when its output exists, validation passes, provenance and configuration are recorded, related documents are updated, and the result is reproducible by someone other than the author. A screenshot or successful manual run alone is not completion.

## 9. Immediate next tasks

1. Create the repository skeleton and copy these documents to the repository root/docs as indicated.
2. Obtain supervisor confirmation of RQ-A through RQ-D and the excluded-feature list.
3. Identify candidate UP districts/crops and build `SCOPE_COMPLETENESS.csv`.
4. Acquire immutable snapshots of candidate official production, mandi, weather, soil/agronomic, and benchmark sources.
5. Create `DATA_MANIFEST.csv`, `DATA_DICTIONARY.md`, and per-source quality reports.
6. Identify an agronomy reviewer before encoding high-risk rules.
7. Freeze Gate G0; only then begin the production scaffold and baseline experiments.

