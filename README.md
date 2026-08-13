# Player Availability Analysis

Longitudinal athlete-monitoring pipeline and player-availability risk stratification for elite football performance environments.

The system estimates how unusual a player's current state is relative to their own history, how that translates into availability risk over a defined horizon, which signals contribute, and how uncertain the estimate is. It is decision support for practitioners. It is not a diagnostic tool, it does not issue clearance decisions, and it makes no causal claims.

## Status

Foundation stage. The configuration layer and repository architecture are in place; the SoccerMon subjective ingestion vertical slice is the next deliverable. No modelling work begins until the ingestion foundation and outcome definitions are validated.

Current state and open decisions: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
Decision history: [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md)

## Approach

**Grain.** One row per player per date. Every feature must be computable from information available at that day's prediction cutoff.

**Validation.** Chronological holdout and rolling-window evaluation, plus leave-one-player-out to measure generalisation to unseen athletes. Random row-level splitting is not used, because it leaks future information and produces metrics that do not survive deployment conditions.

**Calibration.** Reported for every headline model. A stated 20% risk must mean approximately 20%, otherwise the output cannot support the decisions it is designed to inform.

**Model progression.** Operational baseline, logistic regression, gradient boosting, Cox proportional hazards, survival forest, boosted survival. Each step must demonstrate incremental value over the previous one. Complexity is not a success criterion.

**Staged ingestion.** Subjective data first, then a single team-season GPS pilot with measured runtime and cost, then full objective expansion. The objective archive is roughly 99 GB compressed, so it is not the first debugging environment.

## Requirements

- Python 3.12
- [Poetry](https://python-poetry.org/) 2.0 or later
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
make install    # install dependencies
make lint       # ruff check and format check
make typecheck  # mypy, strict
make test       # pytest with coverage
make check      # all of the above
```

Production logic lives under `src/`, `jobs/` and `pipelines/`. Notebooks are for exploration only and are not part of any pipeline.

## Layout

```
configs/    Layered YAML: analytical behaviour
docs/       Project state, decision log, architecture notes
infra/      Infrastructure as code
jobs/       Entry points for individual pipeline stages
notebooks/  Exploration only
scripts/    Operational helper scripts
src/player_availability/
  config/     Typed runtime settings
  ingestion/  Source discovery, provenance, deterministic parsing
  schemas/    Data contracts
  quality/    Data-quality gates and leakage controls
  utils/      Shared helpers
tests/
  unit/            Fast isolated tests
  data_contracts/  Schema conformance
  leakage/         Temporal and player-identity leakage checks
  smoke/           End-to-end pipeline runs
```

## Data

Source dataset: SoccerMon. A subjective archive of wellness, training-load, injury and illness reports, and an objective GNSS archive of approximately 99 GB compressed.

Source archives are not committed. Provenance, checksums and ingestion-run metadata are recorded for every ingested file so that any derived table can be traced back to its source.

## Limitations

The public injury data consists of repeated self-reported observations, not medically verified clinical episodes. Episode boundaries are reconstructed from reporting patterns and are sensitive to the gap rule chosen. Results describe self-reported injury-related events, not clinically confirmed injuries, and generalisation beyond the source cohort is not assumed.
