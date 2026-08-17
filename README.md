# Player Availability Analysis

An injury-risk decision-support dashboard for elite football performance environments, built end to end from a public subjective-data source: ingestion, outcome definition, leakage-audited modelling, a governed champion selection, one single-use confirmatory final test, and a deployed two-service product.

The system estimates how unusual a player's current state is relative to their own history, translates that into a probability of an injury onset within the next seven days, and surfaces which signals drive the estimate. It is decision support for practitioners. It is not a diagnostic tool, it does not issue clearance or return-to-play decisions, and it makes no causal claims.

## Status

V1 is complete and deployed. Its headline evidence is methodological rigour and product completeness, not discrimination performance — the dataset supports at most a handful of injury onsets in any evaluation partition, and every claim in this project is scoped to that limitation rather than around it.

**Deployed dashboard:** https://paa-web-979927072833.europe-west2.run.app (shared review credential; ask the project owner for access — no credential is ever committed to this repository).

Current state and open items: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
Full decision history (65 recorded decisions): [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md)
Analysis and experiment execution plan: [`docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`](docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md)

## What is actually true about this model

- **Champion:** a regularised logistic regression (nine frozen predictors, raw probabilities, no post-hoc calibrator) selected after a Cox proportional-hazards model was rejected on a pre-registered leakage diagnostic and a gradient-boosted classifier was rejected on generalisation grounds, not on a single headline metric.
- **Confirmatory final test:** pre-registered before any evaluation code existed, spent exactly once. ROC-AUC 0.827 and a 3.7x overprediction pattern both transferred from development to the held-out partition; the false-alert burden did not, and that gap was diagnosed from already-committed evidence as two compounding, non-champion causes (halved onset density and an in-sample threshold that did not transfer its target alert rate), not remediated by a second access.
- **Outcome support is small and stated everywhere it matters.** 73 recorded onsets across the full source period; 18 in the pooled rolling-origin development evidence after eligibility and burn-in; 5 in the confirmatory final test after partitioning. All three are correct and describe different populations — the dashboard's data-quality view reconciles them explicitly rather than leaving a reviewer to guess.
- **The dashboard never shows a development figure without its held-out counterpart**, enforced by an automated test, not by review alone.

## Product

Two Cloud Run services, deployed independently:

- **API** (`src/player_availability/api/`, `docker/api/`): FastAPI, reads only a compact serving artefact from Cloud Storage written by batch inference — never queries BigQuery per request. Reachable only by the web service's own identity (IAM `run.invoker`, no public ingress).
- **Web** (`web/`): Next.js, four server-rendered views — squad overview, player detail, data quality, model health — each carrying an explicit "as at" date. Behind a shared review credential.

Batch inference (`src/player_availability/product/batch_inference.py`, `jobs/product/run_batch_inference.py`) scores every eligible player-day with the frozen champion, writes the `paa_product` BigQuery table of record and the GCS serving artefact the API reads, and reconciles the two representations row for row before either write.

Interface copy constraints (no diagnosis, clearance, fitness, injury-prediction or participation language; no operating-point burden shown without its held-out counterpart) are enforced by an automated source-text scan (`tests/unit/test_web_copy_constraints.py`), not by review alone.

## Requirements

- Python 3.12
- [Poetry](https://python-poetry.org/) 2.0 or later
- Node.js 20+ (for the `web/` dashboard)
- Google Cloud SDK with Application Default Credentials, for cloud-backed work

## Setup

```bash
poetry install
cp .env.example .env    # then fill in deployment identity
```

Authentication uses Application Default Credentials:

```bash
gcloud auth application-default login
```

Service-account key files are not used and must never be created for this project.

For the web dashboard:

```bash
cd web
npm install
cp .env.example .env    # PAA_API_BASE_URL and friends
npm run dev
```

## Configuration

Configuration is split by responsibility.

| Source | Holds | Committed |
|--------|-------|-----------|
| `configs/base.yaml`, `configs/<env>.yaml` | Analytical behaviour: rolling windows, label horizons, episode-gap rules | Yes |
| Environment variables / `.env` | Deployment identity and secrets: project ID, buckets, datasets | No |

Layers merge in order, each overriding the last:

```
configs/base.yaml  ->  configs/<PAA_ENV>.yaml  ->  environment variables
```

`PAA_ENV` selects the environment layer and defaults to `local`. Any analytical value can be overridden without a code change using the `PAA_ANALYSIS_` prefix, so a deployed job never needs a rebuild to change a window size.

Analytical parameters live in version control because they change experiment results. A run must be reproducible from a commit hash alone.

```python
from player_availability.config import get_settings

settings = get_settings()
settings.analysis.rolling_windows_days   # (3, 7, 14, 28)
settings.gcp.data_bucket
```

Everything is validated at process start, so a misconfigured job fails immediately rather than part-way through a run that has already written data.

## Development

```bash
make install         # install dependencies
make lint             # ruff check and format check
make typecheck        # mypy, strict
make test             # pytest with coverage
make check            # lint, typecheck and test
poetry check --lock   # lockfile in sync with pyproject.toml (run alongside make check)
```

All five gates above run in CI on every push and pull request; a red pipeline blocks merge.

Production logic lives under `src/`, `jobs/` and `web/`. Notebooks are for exploration only and are not part of any pipeline.

## Layout

```
configs/                      Layered YAML: analytical behaviour
docker/api/, docker/web/      Cloud Run container definitions
docs/                         Project state, decision log, architecture and execution plan
infra/                        Infrastructure as code
jobs/                         Entry points for individual pipeline stages
  analysis/                   Stage 0-8 script runners
  modelling/                  M0/M1 experiment jobs
  product/                    Batch inference CLI entrypoint
notebooks/                    Exploration only, committed output-free
scripts/                      Operational helper scripts
src/player_availability/
  analysis/    Stage 0-8 shared analysis code
  api/         FastAPI service and the serving-artefact reader
  config/      Typed runtime settings
  features/    Feature engineering
  ingestion/   Source discovery, provenance, deterministic parsing
  modelling/   M0/M1 models, calibration, alert-budget and explanation modules
  outcomes/    Leak-safe player-day cohort and label construction
  product/     V1-P6 batch inference
  quality/     Data-quality gates and leakage controls
  schemas/     Data contracts
  utils/       Shared helpers
tests/         Fast isolated tests, plus API, batch-inference and web copy-constraint tests
web/           Next.js dashboard
```

## Data

Source dataset: SoccerMon. A public subjective archive of wellness, training-load, injury and illness self-reports, and an objective GNSS archive of approximately 99 GB compressed. V1 uses the subjective archive only; the objective archive is deferred to V2.

Source archives are not committed. Provenance, checksums and ingestion-run metadata are recorded for every ingested file so that any derived table can be traced back to its source.

## Limitations

The injury data consists of repeated self-reported observations, not medically verified clinical episodes. Episode boundaries are reconstructed from reporting patterns and are sensitive to the gap rule chosen. Results describe self-reported injury-related events, not clinically confirmed injuries, and generalisation beyond the source cohort is not assumed.

Outcome support is small and concentrated: a handful of onsets carry most of the evaluable signal in every partition, and five players account for the majority of recorded onsets across the whole period. Every headline figure in the decision log and the dashboard is reported with its support stated alongside it for exactly this reason.

Reporting behaviour, not injury incidence, drives most of the temporal variation in recorded onsets: self-reporting decays sharply over the covered period, and wellness-report rates spike on injury-onset days relative to ordinary days. The data-quality view states this explicitly rather than leaving a reader to infer a causal story that is not there.
