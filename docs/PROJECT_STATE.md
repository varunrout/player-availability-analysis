# Player Availability Analysis - Project State

State Version: 3
Last Updated UTC: 2026-08-13T01:30:00Z
Coordination Session ID: PAA-CTRL-20260813-01
Git Branch: main
Git HEAD: 12e541582ee10258652e546bfae206f8c5c7f453 (foundation commit; see State Synchronisation Status)
Current Milestone: M1 - SoccerMon Subjective Ingestion Vertical Slice
Current Phase Status: Foundation complete and committed; ingestion not started, blocked on source-archive provenance

---

## Current Objective

Deliver the SoccerMon subjective ingestion vertical slice: source discovery, archive inspection, checksums, provenance records, deterministic parsing, schema validation, bronze representation, data-quality reporting, idempotency and tests.

No modelling work begins until the ingestion foundation is trustworthy.

---

## Completed Foundation

**Planning corpus (Google Drive, folder `1SABJ8ya7T89Eji5SJwRLuEGt814D9dxU`)**
- 19 planning documents, `00_PROJECT_CHARTER.md` through `18_GCP_ARCHITECTURE_AND_DEVELOPMENT_OPERATING_MODEL.md`.
- `18_GCP_ARCHITECTURE_AND_DEVELOPMENT_OPERATING_MODEL.md` is the architecture baseline.
- `PROJECT_STATE.md` and `DECISION_LOG.md` mirrored alongside them.

**Repository foundation (committed)**
- Import package `player_availability` under `src/`, distribution `player-availability-analysis`.
- Poetry build and dependency management with a committed `poetry.lock` pinning 50 packages.
- Layered configuration system with enforced YAML-then-environment precedence.
- Typed, validated, immutable runtime settings.
- 23 unit tests covering the configuration contract.
- `README.md`, `Makefile`, `.env.example`, `.gitignore`.
- Quality gates configured and passing: ruff lint, ruff format, mypy strict, pytest.

---

## Completed Since Previous State

State v1 to v2, under coordination session `PAA-CTRL-20260813-01`.

- Resolved six of the seven open decisions (`DEC-010` to `DEC-015`).
- Renamed the import package from `player_availability_analysis` to `player_availability`; removed the old package directory and stale `egg-info` metadata.
- Migrated the build backend from setuptools to `poetry-core`; added bounded dependency constraints and generated `poetry.lock`.
- Created the slice-scoped directory structure, including the four test categories.
- Implemented the layered configuration system: `configs/*.yaml` for analytical behaviour, environment variables for deployment identity, environment taking precedence, everything validated at process start.
- Added `README.md` and a `Makefile` exposing `install`, `lint`, `format`, `typecheck`, `test`, `check`.
- Ran all quality gates from a clean environment; all pass.
- Made the initial commit, establishing the first recovery point.

**Measured finding.** Dependency resolution with unbounded lower bounds did not converge in over twelve minutes. Tightening the lower bounds to current releases reduced it to under a minute. Recorded in `DEC-011`.

State v2 to v3: mounted the Drive folder and switched the mirror to in-place writes (`DEC-016`); deleted the duplicate Drive copies left by the create-only connector.

---

## Current Repository State

```
player-availability-analysis/
  README.md
  Makefile
  pyproject.toml
  poetry.lock                 50 packages pinned
  .env / .env.example / .gitignore
  configs/                    base.yaml, local.yaml, dev.yaml, prod.yaml
  docs/                       PROJECT_STATE.md, DECISION_LOG.md, architecture/, decisions/
  infra/                      empty
  jobs/                       empty
  notebooks/                  empty
  scripts/                    empty
  src/player_availability/
    __init__.py  py.typed
    config/      settings.py, yaml_source.py
    ingestion/   empty
    schemas/     empty
    quality/     empty
    utils/       paths.py
  tests/
    conftest.py
    unit/            test_settings.py (23 tests)
    data_contracts/  empty
    leakage/         empty
    smoke/           empty
```

**Facts:**
- Branch `main`. Foundation committed. `.env` correctly excluded from version control.
- No remote configured. Work exists on one machine only (`OD-08`).
- No CI workflow yet.
- Locked dependency versions include `google-cloud-storage 3.13.1`, `google-cloud-bigquery 3.43.0`, `pydantic 2.13.4`, `pydantic-settings 2.15.0`, `polars 1.43.2`, `pyarrow 25.0.1`, `pytest 9.1.1`, `ruff 0.16.2`, `mypy 2.3.0`.
- The repository intentionally does not yet contain doc 18's `pipelines/`, `app/` or `sql/` directories (`DEC-012`).

---

## Current GCP State

**Verification status: ASSERTED FROM HANDOFF, NOT VERIFIED.**

No authenticated GCP access from this control session. Carried forward from the handoff and `.env.example`, not confirmed against the live project.

```
Project ID:      player-availability-analysis
Project number:  979927072833
Region:          europe-west2

Storage:         gs://paa-data-979927072833
                 gs://paa-artifacts-979927072833
Zones:           raw/subjective/, raw/objective/, bronze/, silver/, gold/, metadata/, tmp/

BigQuery:        paa_core, paa_ml, paa_product
Provenance:      paa_core.ingestion_runs, paa_core.source_files

Artifact Registry:
  europe-west2-docker.pkg.dev/player-availability-analysis/paa-containers

Service accounts: paa-ingestion-sa, paa-training-sa, paa-api-sa,
                  paa-dashboard-sa, paa-build-sa
```

Authentication: Application Default Credentials. No service-account JSON keys.

Unreconciled: the handoff names `paa-build-sa`; doc 18 section 26 names `paa-ci-sa`.

Unverified: billing budget and alerts, enabled API set, GCS lifecycle rules, IAM bindings.

No cloud resource has been written to by this project's code. Nothing has been spent.

---

## Current Data State

- Source dataset: SoccerMon. Subjective archive small; objective GNSS archive approximately 99 GB compressed.
- **Locked sequence: subjective vertical slice first. Full GPS ingestion must not begin.**
- **Blocker: no SoccerMon archive was located in the searchable Drive account.** Location, licence record and SHA-256 checksum are unverified (`OD-07`).
- No data ingested. No bronze, silver or gold artefacts exist.
- No schema audit against real files, so no field-level assertions are made anywhere in this project.

---

## Current Modelling State

Nothing implemented.

| ID | Model | Status |
|----|-------|--------|
| M0 | Operational baseline | Not started |
| M1 | Logistic regression | Not started |
| M2 | Gradient boosting | Not started |
| M3 | Cox proportional hazards | Not started |
| M4 | Random survival forest | Not started |
| M5 | Boosted survival | Not started |
| M6 | Neural survival | Not started; only if evidence justifies |

Grain: `player x date`. Candidate outcomes: `injury_next_3d`, `injury_next_7d`, `injury_next_14d`, and time to next injury episode with right censoring.

Cohort rules are **not frozen**. `injury_episode_gap_days` is set to 3 in `configs/base.yaml` and is explicitly provisional pending EXP-001.

---

## Current Product State

Nothing implemented. No API, no dashboard, no product tables.

Target remains batch inference into `paa_product`, surfaced through a Cloud Run API and practitioner dashboard. No online serving planned.

---

## Locked Decisions

Full records in `DECISION_LOG.md`.

| ID | Decision |
|----|----------|
| DEC-001 | Player-day is the primary prediction unit |
| DEC-002 | Injury is a risk-stratification target, not a diagnosis |
| DEC-003 | Chronological validation is mandatory |
| DEC-004 | Leave-one-player-out validation is mandatory |
| DEC-005 | Subjective data first; GPS ingestion deferred |
| DEC-006 | Model complexity follows the ladder |
| DEC-007 | Calibration is a first-class metric |
| DEC-008 | Accuracy is not a headline metric |
| DEC-009 | `docs/DECISION_LOG.md` is the canonical decision record, mirrored to Drive |
| DEC-010 | Import package `player_availability`; distribution `player-availability-analysis` |
| DEC-011 | Poetry with committed lockfile; constraints bounded on both sides |
| DEC-012 | Slice-scoped repository structure |
| DEC-013 | Layered config: YAML for behaviour, environment for identity, environment wins |
| DEC-014 | Subjective vertical slice runs local-first, cloud as sink |
| DEC-015 | Commit locally now; remote hosting deferred |
| DEC-016 | Mirror control docs in place via the mounted Drive folder |

Standing constraints from the architecture baseline, treated as binding:
- Random row-level splitting is not acceptable as the primary evaluation approach.
- Every feature must satisfy `feature_timestamp <= prediction_cutoff`.
- No always-on compute; Cloud Run minimum instances zero unless justified.
- The raw point-level GPS layer is not loaded into BigQuery by default.
- No service-account JSON keys.
- Project artifacts are tool-agnostic.
- Practitioner-facing language is decision support, never medical clearance.

---

## Open Decisions

| ID | Question | Blocks |
|----|----------|--------|
| OD-07 | Confirmed location, licence and SHA-256 checksum of the SoccerMon subjective archive | All ingestion work |
| OD-08 | Remote hosting, visibility, and branch and review policy | Off-machine backup, review process, CI |

---

## Known Issues / Technical Debt

- No remote. The repository exists on one machine only (`OD-08`).
- No CI workflow. `poetry check --lock`, ruff, mypy and pytest all run locally via `make check` but are not enforced automatically.
- Service-account naming unreconciled: `paa-build-sa` (handoff) versus `paa-ci-sa` (doc 18).
- Repository structure intentionally incomplete against doc 18 (`DEC-012`). Deliberate, not drift.
- `injury_episode_gap_days: 3` is provisional pending EXP-001 and must not be used for a headline result.
- Git identity is set at repository level rather than inherited from a global configuration.

---

## Blockers

1. **Source data provenance unverified (`OD-07`).** No SoccerMon archive located in Drive. Ingestion cannot begin without a confirmed, checksummed source. This is the single blocker on the current milestone.
2. **GCP state unverified.** Cloud resources are asserted, not confirmed. Must be re-verified from an authenticated environment before any cloud write.

---

## Work In Progress

None in flight. No other control session is known to be editing this working tree.

---

## Immediate Next Actions

1. Resolve `OD-07`: locate the SoccerMon subjective archive, record its licence, compute and store its SHA-256.
2. Resolve `OD-08`: choose remote hosting and visibility; push; add branch policy.
3. Add a CI workflow running `poetry check --lock`, ruff, mypy strict and pytest on every push.
4. Verify GCP state from an authenticated environment; reconcile the `paa-build-sa` / `paa-ci-sa` naming; confirm budget alerts exist before any processing.
5. Implement the subjective ingestion vertical slice, in order: source discovery and manifest, archive inspection, SHA-256 and provenance records into `paa_core.source_files` and `paa_core.ingestion_runs`, deterministic parsing, schema discovery, schema validation as data contracts, raw staging, bronze representation, data-quality reporting, structured logging, idempotency, tests.
6. Run EXP-001 (episode-gap sensitivity) before any label is treated as settled, then freeze `injury_episode_gap_days` and record the decision.

---

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|------|--------|----------|
| Lint (ruff) | PASS | `ruff check src tests jobs`, all checks passed |
| Format (ruff) | PASS | 13 files already formatted |
| Type check (mypy strict) | PASS | 16 source files, no issues |
| Unit tests | PASS | 23 passed |
| Lockfile integrity | PASS | `poetry check --lock`, all set |
| Schema / data-contract tests | Not implemented | Directory exists, no data to contract against |
| Leakage tests | Not implemented | Directory exists, no features to test |
| Smoke tests | Not implemented | Directory exists, no pipeline to run |
| CI | Not implemented | Gates run locally only |

Gates were run from a clean environment with no inherited path or configuration, so the results reflect a fresh checkout rather than a primed local setup.

Test coverage is limited to the configuration layer, which is the only substantive code that exists.

---

## State Synchronisation Status

| Item | Local | Drive |
|------|-------|-------|
| `PROJECT_STATE.md` | v3, 2026-08-13T01:30:00Z | v3, 2026-08-13T01:30:00Z |
| `DECISION_LOG.md` | DEC-001 to DEC-016 | DEC-001 to DEC-016 |

Status: **SYNCHRONISED**

**Mirror method (`DEC-016`).** The Drive folder is now mounted, so both mirrors are written in place at `G:\My Drive\Projects\PlayerAvailabilityAnalysis` and synced by Google Drive Desktop. The earlier duplicate copies produced by the create-only connector have been deleted; the folder holds exactly one of each control document. If the Drive folder is ever unmounted, mirroring will be reported as `STATE SYNC INCOMPLETE` rather than silently skipped.

**Note on Git HEAD.** This document describes the tree as of foundation commit `12e5415` on `main`. It is itself committed immediately afterwards, so the commit containing this file is one ahead of the commit it describes. This is a deliberate convention, not drift: a state document cannot record the hash of the commit that contains it.
