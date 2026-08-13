# Player Availability Analysis - Project State

State Version: 7
Last Updated UTC: 2026-08-13T04:00:00Z
Coordination Session ID: PAA-CTRL-20260813-05
Git Branch: main
Git HEAD: abc9f4c5506a7afac4e6e34a35a3e0e6737d7d87 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: M0 - SoccerMon Archive Acquisition to Cloud Storage
Current Phase Status: One-time managed SoccerMon archive transfer is running in GCP. Source ZIPs are being copied directly from Zenodo into the dedicated archive-only bucket.

---

## Current Objective

Acquire and verify the complete SoccerMon source archive from Zenodo into `gs://paa-source-archives-979927072833/soccermon/zenodo-10033832/` through Storage Transfer Service, using a checksum-bearing URL list. The transfer is agentless and managed by GCP.

After acquisition and verification, deliver the SoccerMon subjective ingestion vertical slice. No modelling work begins until the ingestion foundation is trustworthy.

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

State v6 to v7, under coordination session `PAA-CTRL-20260813-05`.

- Accepted `DEC-021`: created dedicated archive-only bucket `gs://paa-source-archives-979927072833` in `europe-west2`, with uniform bucket-level access.
- Granted the Storage Transfer managed identity bucket metadata read, object viewer and object creator roles on the dedicated archive bucket only. Removed all attempted conditional transfer bindings from the shared `paa-data` bucket.
- Updated the acquisition script defaults to the dedicated bucket. The transfer manifest is at `gs://paa-source-archives-979927072833/transfer_manifests/soccermon/zenodo-10033832.tsv`.
- Created and started one-time job `transferJobs/3472342193733823656`, operation `transferOperations/transferJobs-3472342193733823656-16747793546306343886`.
- Latest operation check: `IN_PROGRESS`; 5 objects and 99,132,769,855 bytes found at source; 1 object and 940,229,866 bytes copied to the sink. The first archive object is now visible under the destination prefix.

State v5 to v6, under coordination session `PAA-CTRL-20260813-04`.

- Approved scoped Storage Transfer IAM was applied and tested. GCP rejected job creation because its preflight requires `storage.objects.list` and `storage.objects.create` at the bucket level; conditional prefix-only bindings do not satisfy that service validation.
- Set `player-availability-analysis` as the quota project for local ADC and corrected the submission script to call the Storage Transfer REST API with the required quota-project header.
- Uploaded the checksum-bearing URL list to `gs://paa-data-979927072833/metadata/transfer_manifests/soccermon/zenodo-10033832.tsv`. It is a small control artifact only.
- No transfer job was created and no SoccerMon archive ZIP has been copied. No 99 GB transfer charge has been incurred.
- Added `OD-09`: decide between an archive-only bucket, which is recommended, and broadening the transfer service identity to the shared data bucket, which is not approved.

State v4 to v5, under coordination session `PAA-CTRL-20260813-03`.

- Verified authenticated GCP access: active project `player-availability-analysis` and `gs://paa-data-979927072833` are accessible with the expected zones.
- Replaced mounted-Drive archive acquisition with GCP Storage Transfer Service (`DEC-019`), superseding `DEC-018`. The full archive remains storage-only and does not authorise objective/GPS ingestion.
- Replaced mounted-path control-document mirroring with in-place Drive connector updates (`DEC-020`), superseding `DEC-016`.
- Reworked `scripts/acquire_soccermon_archive.py` to generate a Zenodo URL-list TSV carrying expected size and MD5 checksums, upload that small manifest to `metadata/transfer_manifests/`, and submit a one-time managed transfer only with `--submit`.
- Enabled `storagetransfer.googleapis.com` and created its managed service identity. No transfer job or archive object has been created.
- Bucket IAM bindings for the managed identity are pending explicit approval because they include write capability under the dedicated SoccerMon archive prefix.

State v3 to v4, under coordination session `PAA-CTRL-20260813-02`.

- Confirmed the local Google Cloud SDK is installed (`580.0.0`), including `gcloud`, `gsutil` and `bq`. Its executable is not on the current shell `PATH`; invoke it from its installed location until the user chooses to update `PATH`.
- Clarified local-only Git policy (`DEC-017`): no remote is added, pushed to, or otherwise configured unless explicitly requested.
- Prioritised complete SoccerMon archive preservation in Google Drive before ingestion (`DEC-018`). The archive remains out of GCP during acquisition.
- Added `scripts/acquire_soccermon_archive.py`: a standard-library Zenodo downloader that discovers record files, supports exact-file selection, resumes interrupted downloads, validates expected byte size, and writes local SHA-256 provenance to `soccermon_acquisition_manifest.json`.

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
- No remote configured. Git is deliberately local-only unless explicitly requested (`DEC-017`).
- No CI workflow yet.
- Locked dependency versions include `google-cloud-storage 3.13.1`, `google-cloud-bigquery 3.43.0`, `pydantic 2.13.4`, `pydantic-settings 2.15.0`, `polars 1.43.2`, `pyarrow 25.0.1`, `pytest 9.1.1`, `ruff 0.16.2`, `mypy 2.3.0`.
- The repository intentionally does not yet contain doc 18's `pipelines/`, `app/` or `sql/` directories (`DEC-012`).

---

## Current GCP State

**Verification status: PROJECT, BUCKET AND STORAGE TRANSFER SERVICE VERIFIED; MANAGED ARCHIVE TRANSFER RUNNING.**

Google Cloud SDK `580.0.0` is installed locally, including `gcloud`, `gsutil` and `bq`, but is not on the current shell `PATH`. The active project is `player-availability-analysis`; the account and `gs://paa-data-979927072833` were successfully verified. Storage Transfer Service is enabled and its managed identity has the required bucket-level access only on the dedicated archive bucket.

```
Project ID:      player-availability-analysis
Project number:  979927072833
Region:          europe-west2

Storage:         gs://paa-data-979927072833
                 gs://paa-artifacts-979927072833
                 gs://paa-source-archives-979927072833
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

Verified bucket zones: `raw/`, `bronze/`, `silver/`, `gold/`, `metadata/`, `tmp/`.

Dedicated archive bucket: `gs://paa-source-archives-979927072833` (`europe-west2`, uniform bucket-level access). It contains the live transfer's URL-list manifest and is isolated from the analytical data lake.

Live transfer job: `transferJobs/3472342193733823656`. Live operation: `transferOperations/transferJobs-3472342193733823656-16747793546306343886`. Latest status: `IN_PROGRESS`, with 5 objects and 99,132,769,855 bytes found at source; 1 object and 940,229,866 bytes copied to the sink.

---

## Current Data State

- Source dataset: SoccerMon. Subjective archive small; objective GNSS archive approximately 99 GB compressed.
- Immediate source objective: complete the managed transfer into `gs://paa-source-archives-979927072833/soccermon/zenodo-10033832/`. `scripts/acquire_soccermon_archive.py` generates a URL list with Zenodo size and MD5 integrity values and submits the managed job only with `--submit`.
- **Locked sequence: subjective vertical slice first. Full GPS ingestion must not begin.**
- **Work in progress: managed archive transfer.** The source ZIPs remain unverified until the running operation completes successfully and object-level checksums are recorded (`OD-07`).
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
| DEC-017 | Git remains local-only unless explicitly requested |
| DEC-018 | Superseded: complete SoccerMon archive is preserved in Drive before ingestion |
| DEC-019 | Complete SoccerMon archive is acquired into GCS with Storage Transfer Service |
| DEC-020 | Control documents mirror through in-place Drive connector updates |
| DEC-021 | Dedicated archive-only bucket isolates Storage Transfer Service access |

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

---

## Known Issues / Technical Debt

- No remote. This is intentional local-only Git policy (`DEC-017`), so the repository still has no off-machine version-control backup.
- No CI workflow. `poetry check --lock`, ruff, mypy and pytest all run locally via `make check` but are not enforced automatically.
- Service-account naming unreconciled: `paa-build-sa` (handoff) versus `paa-ci-sa` (doc 18).
- Repository structure intentionally incomplete against doc 18 (`DEC-012`). Deliberate, not drift.
- `injury_episode_gap_days: 3` is provisional pending EXP-001 and must not be used for a headline result.
- Git identity is set at repository level rather than inherited from a global configuration.
- The archive transfer is in progress. Its completion status, destination object names and checksums still require verification before ingestion begins.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.

---

## Blockers

1. **Source data provenance unverified (`OD-07`).** The archive transfer is running, but no destination object location or completed transfer checksum has yet been confirmed. This is the single blocker on the current milestone.

---

## Work In Progress

One-time Storage Transfer Service job `transferJobs/3472342193733823656` is running. Its live operation is `transferOperations/transferJobs-3472342193733823656-16747793546306343886`. No other control session is known to be editing this working tree.

---

## Immediate Next Actions

1. Monitor job `transferJobs/3472342193733823656` until it reaches a terminal status.
2. Resolve `OD-07`: register the destination object names, sizes, MD5 checksums, transfer result and CC BY 4.0 licence in source provenance; establish whether a separate SHA-256 computation is needed.
3. Confirm archive-bucket lifecycle rules and billing-budget alerts before processing begins.
4. Reconcile the `paa-build-sa` / `paa-ci-sa` naming.
5. Add a CI workflow running `poetry check --lock`, ruff, mypy strict and pytest on every push. It remains local only until the user explicitly requests a remote.
6. Implement the subjective ingestion vertical slice, in order: source discovery and manifest, archive inspection, provenance records into `paa_core.source_files` and `paa_core.ingestion_runs`, deterministic parsing, schema discovery, schema validation as data contracts, raw staging, bronze representation, data-quality reporting, structured logging, idempotency, tests.
7. Run EXP-001 (episode-gap sensitivity) before any label is treated as settled, then freeze `injury_episode_gap_days` and record the decision.

---

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|------|--------|----------|
| Lint (ruff) | PASS | `ruff check src tests jobs`, all checks passed |
| Format (ruff) | PASS | 13 files already formatted |
| Type check (mypy strict) | PASS | 16 source files, no issues |
| Unit tests | PASS | 23 passed |
| Lockfile integrity | PASS | `poetry check --lock`, all set |
| Cloud Storage access | PASS | Active project and `gs://paa-data-979927072833` verified; expected zones listed |
| Archive acquisition preflight | PASS | Zenodo record `10033832` returned 5 files totalling 99.13 GB; managed-transfer script dry run, compilation and Ruff checks pass; it made no cloud writes |
| Storage Transfer Service | IN PROGRESS | Job `transferJobs/3472342193733823656`; operation `transferOperations/transferJobs-3472342193733823656-16747793546306343886` found 5 source objects totalling 99,132,769,855 bytes; 1 object / 940,229,866 bytes copied |
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
| `PROJECT_STATE.md` | v7, 2026-08-13T04:00:00Z | v7, 2026-08-13T04:00:00Z |
| `DECISION_LOG.md` | DEC-001 to DEC-021, with DEC-021 accepted | DEC-001 to DEC-021, with DEC-021 accepted |

Status: **SYNCHRONISED**

**Mirror method (`DEC-020`).** The Drive connector updates the existing raw Markdown files in place using their stable Drive IDs. The project does not rely on a mounted `G:` path. The folder holds exactly one of each control document.

**Note on Git HEAD.** This document describes the tree as of commit `abc9f4c` on `main`. It is itself committed immediately afterwards, so the commit containing this file is one ahead of the commit it describes. This is a deliberate convention, not drift: a state document cannot record the hash of the commit that contains it.
