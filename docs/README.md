# AI-Powered Multilingual Smart Agriculture Decision Support System

This folder is the implementation baseline for a final-year B.Tech CSE/AI project focused on selected crops and districts in Uttar Pradesh, India.

The project is intentionally framed as an evaluated decision-support prototype, not as an autonomous agronomist, a guaranteed profit predictor, or a nationwide deployment. Its central research question is whether a transparent hybrid approach - agronomic rules, carefully validated predictive models, explicit uncertainty, and source-grounded bilingual explanations - is more defensible than an ML-only crop classifier.

## Document map

Read and use the files in this order:

1. `PROJECT_PRD.md` - authoritative scope, product requirements, research questions, safety boundaries, and definition of done.
2. `DATA_AND_EVIDENCE.md` - data-source rules, provenance gates, manifests, rule metadata, and privacy requirements.
3. `EVALUATION_PLAN.md` - frozen experiments, splits, metrics, acceptance thresholds, and reporting requirements.
4. `ARCHITECTURE.md` - component boundaries, decision paths, interfaces, and deployment shape.
5. `TECH_STACK.md` - approved technologies and the rationale for each choice.
6. `WORKFLOW.md` - phased build plan and gate-based execution process.
7. `AGENTS.md` - mandatory instructions for Codex or any other coding agent working in the repository.
8. `.env.example` - names of allowed runtime configuration values; it contains no secrets.

`PROJECT_PRD.md` is the source of truth. If another file conflicts with it, the PRD wins unless a dated decision is recorded and all affected documents are updated together.

## Frozen project boundary

### Evaluated MVP

- Uttar Pradesh only.
- Three to five districts selected after a documented completeness audit.
- Six to eight crops selected after the same audit.
- Seasons limited to those with adequate agronomic, production, weather, and price evidence.
- Farmer profile and explicit soil-information confidence tier.
- Rules-only, ML-only, and hybrid Top-3 crop recommendation comparison.
- District-season yield baseline with calibrated uncertainty.
- Mandi-linked gross-margin scenarios, never guaranteed profit.
- English and Hindi text interface, with Hinglish included in robustness testing.
- Source-grounded RAG explanations, evidence display, safe abstention, and expert evaluation.

### Future work, not MVP

- Disease-image diagnosis.
- Pesticide or chemical-dose generation.
- Remote sensing, IoT, drones, or satellite-image pipelines.
- Soil Health Card OCR.
- Voice input/output.
- Additional languages.
- WhatsApp/SMS integration.
- National-scale deployment.
- Field-level yield or guaranteed financial prediction.

## First execution gate

Before training a model or building the full UI, complete Phase 0:

- create a crop x district x year x source completeness matrix;
- fingerprint every candidate dataset and resolve or explicitly mark unknown units and provenance;
- obtain at least one relevant agronomy reviewer for rule and scenario review;
- freeze the supported districts, crops, seasons, and primary evaluation endpoints;
- record the ethical/privacy route for any expert or farmer study.

If the evidence is insufficient, reduce the scope. Do not fill missing laboratory NPK values with district averages and call them measured farmer inputs.

## Repository target structure

```text
ai-agriculture/
├── AGENTS.md
├── README.md
├── .env.example
├── apps/
│   ├── api/
│   └── web/
├── configs/
│   ├── data/
│   ├── experiments/
│   └── policies/
├── data/
│   ├── external/
│   ├── interim/
│   ├── processed/
│   ├── manifests/
│   └── splits/
├── docs/
├── knowledge/
│   ├── approved_sources/
│   ├── manifests/
│   └── glossaries/
├── models/
│   ├── cards/
│   └── registry/
├── notebooks/
├── outputs/
│   ├── evaluations/
│   ├── figures/
│   └── reports/
├── src/
│   └── agriculture/
└── tests/
    ├── integration/
    ├── safety/
    └── unit/
```

Notebooks are for exploration only. Reusable preprocessing, training, evaluation, and inference logic belongs in `src/` and must be callable from scripts or tests.

## Status

Documentation baseline: complete.

Synthetic teacher-demo implementation: complete. The backend, training pipelines, model artifacts,
tests, and React interface prove the software workflow using explicitly synthetic assets.

Scientific implementation status: Phase 0 not started. The next research task remains the evidence and
scope freeze described in `WORKFLOW.md`; synthetic demo metrics must not be presented as field results.
