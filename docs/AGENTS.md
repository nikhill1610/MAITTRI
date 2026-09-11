# Instructions for Coding Agents

## Mission

Build an academically defensible, bounded agricultural decision-support prototype for the scope defined in `PROJECT_PRD.md`. Optimize for evidence quality, safety, reproducibility, and completion - not feature count.

## Source precedence

When instructions conflict, follow this order:

1. Explicit user instruction.
2. `PROJECT_PRD.md`.
3. `DATA_AND_EVIDENCE.md` and `EVALUATION_PLAN.md`.
4. `ARCHITECTURE.md` and `TECH_STACK.md`.
5. `WORKFLOW.md`.

Do not silently resolve a material conflict. Explain it and propose the smallest consistent change.

## Mandatory behavior

- Read the relevant project documents before planning or editing.
- Work only within the current phase and gate.
- Preserve user changes and unrelated work.
- Keep changes small, testable, and linked to a requirement or research question.
- State assumptions. Mark unknown provenance, units, or semantics as unknown.
- Prefer a simple baseline before a complex model.
- Treat public NPK-climate crop data as benchmark-only until its audit passes.
- Fit every learned preprocessing step inside training folds.
- Preserve immutable raw data; transformations create new artifacts.
- Record dataset/split/config/code/model/rule/corpus versions for results.
- Add or update tests with implementation changes.
- Update affected documentation in the same change.
- Report failures and negative results honestly.

## Prohibited shortcuts

- Do not add out-of-scope features without an approved PRD change.
- Do not claim field validity from random-split benchmark accuracy.
- Do not impute district-average NPK/pH and present it as a farmer's measurement.
- Do not invoke an exact-NPK model for Tier 3 scenarios.
- Do not let an LLM decide hard crop constraints, compute scientific values, or invent evidence.
- Do not generate pesticide/chemical dosage in the MVP.
- Do not generate exact fertilizer advice without an approved applicable deterministic source path.
- Do not use arbitrary yield uncertainty bands.
- Do not call gross-margin scenarios `profit prediction` or provide guarantees.
- Do not cite a document unless the answer's claim is actually supported by it.
- Do not tune on locked test sets.
- Do not store secrets, raw personal data, or precise coordinates in source control/logs.
- Do not place reusable production logic only in notebooks.
- Do not introduce microservices, Kubernetes, a separate vector database, or a heavy agent framework without measured need and a recorded decision.

## Implementation conventions

- Use a modular monolith for the application and separate offline research pipelines.
- Keep domain logic out of HTTP controllers and UI components.
- Use typed schemas and explicit units at boundaries.
- Use provider adapters for weather, market, LLM, embeddings, and translation.
- Use configuration files for thresholds, freshness windows, score weights, and feature flags.
- Use stable IDs and immutable versions for data, sources, rules, models, and runs.
- Return structured error categories: invalid input, unsupported scope, insufficient evidence, stale/unavailable dependency, or internal failure.
- Make English/Hindi strings externalized and test critical number/unit/warning preservation.
- Make timestamps timezone-aware and store UTC.
- Seed stochastic experiments and record the seed.

## Required tests

At minimum, add tests for:

- schema, unit, and range validation;
- rule applicability and hard exclusions;
- soil-tier routing and absence of pseudo-measured inputs;
- score calculation and deterministic tie-breaking;
- yield applicability and interval output;
- gross-margin percentiles and assumptions;
- RAG source/applicability/freshness filters;
- citation support and abstention;
- high-risk query routing and prompt injection;
- database version/audit behavior;
- external-provider failure/degraded mode; and
- primary English/Hindi end-to-end journeys.

## Data and model completion checklist

Do not mark a data/model task complete unless:

- source/version/checksum/license are recorded;
- feature and target meanings/units are resolved or explicitly unknown;
- quality and duplicate reports exist;
- split IDs are immutable;
- leakage controls pass;
- baselines are included;
- geographic/temporal results are separated;
- uncertainty/calibration is evaluated where exposed;
- subgroup failures and limitations are recorded; and
- a model card or data report exists.

## Communication style

Lead with the result, then evidence and remaining risks. Do not hide limitations behind generic disclaimers. When blocked by missing evidence or an unapproved gate, stop the affected work and request the exact decision or artifact needed.

