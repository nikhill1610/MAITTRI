# Approved Technology Stack

## 1. Selection principles

The stack is optimized for a small research team, tabular ML, reproducibility, auditability, and a mobile-first bilingual web interface. Exact package versions must be pinned after the initial compatibility spike; use maintained stable releases, not unbounded `latest` dependencies.

## 2. Core stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + TypeScript + Vite | Simple client application, mature ecosystem, fast local workflow |
| Styling/UI | Tailwind CSS plus a small accessible component layer | Responsive/mobile-first UI without a heavy design system |
| Forms/validation | React Hook Form + schema validation | Explicit unit/tier-aware forms and shared error behavior |
| Internationalization | i18next/react-i18next | English/Hindi resource files and testable language parity |
| API | Python 3.12 + FastAPI + Pydantic | Typed request contracts and alignment with ML code |
| Persistence | PostgreSQL + SQLAlchemy + Alembic | Relational provenance, versions, experiments, and audit records |
| Vector retrieval | `pgvector` plus PostgreSQL full-text search | Hybrid retrieval in one operational database for MVP |
| Tabular ML | scikit-learn; XGBoost only when justified | Strong baselines, pipelines, calibration, and interpretable evaluation |
| Data processing | pandas or Polars, NumPy, Pandera | Reproducible transforms and schema/range checks |
| Statistical uncertainty | SciPy/statsmodels plus conformal/quantile implementation as selected | Intervals, resampling, and sensitivity analysis |
| Experiment tracking | MLflow locally or on the project server | Parameters, metrics, artifacts, and model lineage |
| Data versioning | Immutable raw snapshots + DVC where storage workflow supports it | Dataset/artifact traceability without committing large data to Git |
| RAG ingestion | PyMuPDF/pdfplumber and explicit parsing/chunking modules | Page-aware traceability and controllable transformations |
| LLM/embeddings | Provider adapter with one configured provider; direct SDK or thin internal interface | Avoid framework lock-in and preserve audit control |
| Background work | FastAPI background jobs for tiny tasks; a worker queue only if measured need appears | Keep MVP operational complexity low |
| Cache/rate limit | In-memory locally; Redis for multi-instance deployment | Introduce only when deployment requires shared state |
| Packaging | `uv`/locked Python environment; npm/pnpm lockfile | Repeatable installs |
| Containers | Docker + Docker Compose | Consistent local/demo environments |

## 3. Testing and quality

| Concern | Tooling |
|---|---|
| Python tests | pytest, pytest-cov |
| API tests | FastAPI test client/httpx |
| Data checks | Pandera plus custom unit/provenance tests |
| Frontend unit/component | Vitest + Testing Library |
| End to end | Playwright |
| Python lint/format | Ruff |
| Python typing | mypy or Pyright, frozen during scaffold |
| Web lint/format | ESLint + Prettier |
| Security | Dependabot/Renovate, `pip-audit`, npm audit, secret scanning |
| CI | GitHub Actions or institution-approved equivalent |

Coverage percentage is not the only quality signal. Critical rule, unit, safety-router, abstention, and data-leakage paths require explicit tests regardless of aggregate coverage.

## 4. Visualization and reporting

- Matplotlib/Seaborn for static research figures.
- Plotly only when an interactive chart adds real value.
- Jupyter notebooks for exploration and narrative inspection only.
- Quarto, MkDocs, or a scripted Markdown/PDF route may be added for reproducible reporting; do not make report tooling block core experiments.

Required figures include data coverage, per-crop confusion, calibration, yield observed-vs-predicted, prediction-interval coverage, subgroup error, gross-margin uncertainty, and RAG failure categories.

## 5. Authentication

Anonymous scenarios are sufficient for the MVP farmer journey. Do not build a full user-account system unless persistence across devices is a frozen requirement.

Admin endpoints require authenticated role-based access. Use a maintained identity provider or a small, well-tested server-side authentication mechanism; do not implement custom cryptography. Passwords, if introduced, use a maintained password-hashing library and never appear in logs.

## 6. Provider decisions

### Weather

- Historical baseline: NASA POWER, with its spatial-resolution limitation displayed in documentation.
- Current weather: select one provider after testing UP coverage, terms, rate limits, timestamp semantics, missingness, and cost.

### Market data

- Prefer the official data.gov.in AGMARKNET-generated resource/API or reproducible official snapshots.
- Do not scrape a website when an adequate authorized data endpoint exists.
- Cache raw responses and preserve resource/version/retrieval metadata.

### Translation and LLM

- English/Hindi quality must be evaluated; provider brand is not itself evidence of quality.
- BHASHINI may be benchmarked as an India-focused translation/language option if access and terms permit.
- Hide providers behind adapters and log model/version/configuration.
- The rule/recommendation core must still function if the LLM is unavailable.

## 7. Deliberately excluded technology

- No MongoDB: the MVP's provenance, time/district/crop joins, rule versions, and audits fit relational storage better.
- No separate vector database: `pgvector` is adequate for the expected corpus size and reduces operations.
- No Kubernetes: unnecessary for a final-year pilot.
- No Kafka/event platform: unnecessary until measured scale requires it.
- No microservice split: begin as a modular monolith plus offline pipelines.
- No heavy agent framework for RAG by default: explicit routing and retrieval code is easier to audit.
- No GPU dependency for tabular MVP; CPU training is expected to be adequate.

These decisions may change only after a measured limitation and a recorded architecture decision.

## 8. Deployment recommendation

- Web: static hosting/CDN.
- API: container-capable service with predictable request duration and background-job support.
- Database: managed PostgreSQL with `pgvector`, backups, TLS, and restricted network access.
- Artifacts: private versioned object storage or institution-approved equivalent.
- Observability: structured logs, health checks, error reporting, latency/provider-cost metrics, and PII redaction.

Do not deploy the long-running ML/RAG API as a constrained serverless function until cold starts, execution limits, filesystem behavior, and background work are shown to meet requirements.

## 9. Environment policy

- Copy `.env.example` to an ignored local `.env`.
- Commit only placeholder names and safe defaults.
- Use separate development/test/deployment values.
- Rotate any key accidentally exposed; removing it from the latest commit is not sufficient.
- Production secrets belong in managed secret storage, not a repository or frontend build.
- Pin dependencies and record the runtime in every experiment.

