# Player Availability Analysis - Project State

State Version: 20
Last Updated UTC: 2026-08-13T22:00:00Z
Coordination Session ID: PAA-CTRL-20260813-18
Git Branch: main
Git HEAD: cc06aebbb6a0383ffb898ed170f437bc58a324c0 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: M1 - Subjective Modelling Baseline
Current Phase Status: Subjective data engineering, Phase A reporting and Phase B chronological split construction are complete and validated. EXP-002 naive operational baseline is next.

---

## Current Objective

Run the subjective modelling programme through the approved analysis execution plan, starting with EXP-002 naive operational baselines on the frozen chronological partitions.

After acquisition and verification, deliver the SoccerMon subjective ingestion vertical slice. No modelling work begins until the ingestion foundation is trustworthy.

---

## Completed Foundation

**Planning corpus (Google Drive, folder `1SABJ8ya7T89Eji5SJwRLuEGt814D9dxU`)**
- 20 planning documents, `00_PROJECT_CHARTER.md` through `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`.
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

State v19 to v20, under coordination session `PAA-CTRL-20260813-18`.

- Accepted `DEC-027`: a shared chronological 60/20/final-period split with 14-day embargoes is the frozen development and headline-evaluation protocol for the 14-day primary horizon.
- Implemented and committed reusable chronological split controls, predictor allow-list validation and three focused split tests at `cc06aeb`.
- Produced and staged `player_day_features_with_splits.parquet` (36,550 player-days), a JSON manifest and the Phase B audit report. The 34-predictor contract excludes labels, eligibility, identifiers, dates, episode-state and provenance fields.
- Frozen model partitions contain 20,505 primary-eligible train rows, 6,900 validation rows and 5,495 test rows. No model has been fitted and the test partition has not been inspected for model performance.

State v18 to v19, under coordination session `PAA-CTRL-20260813-17`.

- Added locked development dependency `matplotlib 3.11.1` and extended the reusable Phase A analysis job to generate three reproducible charts: label prevalence by horizon, feature coverage after burn-in, and 7-day positive-label concentration.
- Added chart links to the Phase A report. The report and figures are committed locally, updated in Drive, and staged under the GCS metadata analysis-report prefix.
- Performed visual inspection of all three rendered figures. Full quality gate passes: Ruff, strict mypy and pytest (`52 passed`, one expected ZIP duplicate-name warning).

State v17 to v18, under coordination session `PAA-CTRL-20260813-16`.

- Implemented a reusable Phase A cohort-analysis job and generated `docs/reports/PHASE_A_SUBJECTIVE_COHORT_REPORT.md`, mirrored in Drive and staged with its JSON summary under the GCS metadata analysis-report prefix.
- Measured the 28-day-history new-onset cohort: 34,849/34,649/34,299 eligible player-days and 178/343/554 positives for 3/7/14-day labels, respectively (0.51%/0.99%/1.62% prevalence). The primary 7-day outcome is highly imbalanced and concentrated in a small number of players.
- Confirmed feature coverage after burn-in: daily load and session aggregates are complete; wellness fatigue/readiness are available on approximately 48% of eligible days; prior-only daily-load z-scores on 78%. The report treats missingness as a process/completeness signal, not physiology.
- Phase A decision: **PROMOTE to Phase B**. No model was fitted. Full quality gate passes: Ruff, strict mypy and pytest (`52 passed`, one expected ZIP duplicate-name warning).

State v16 to v17, under coordination session `PAA-CTRL-20260813-15`.

- Created `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` locally and in Drive. It integrates the charter, hypotheses, outcome rules, feature strategy, validation requirements and experiment backlog into one 296-line modelling runbook.
- The runbook specifies cohort/label/feature analysis, split and leakage gates, naive and logistic baselines, calibration, alert-budget simulation, ablations, unseen-player stress testing, model-promotion criteria and required evidence for each experiment.
- No modelling design decision changed; the runbook operationalises existing accepted decisions and documents the required experiment order.

State v15 to v16, under coordination session `PAA-CTRL-20260813-14`.

- Accepted `DEC-026`: subjective feature version 1 uses end-of-day current values, trailing 3/7/14/28-day summaries, session exposure aggregates, wellness completeness and strictly prior-only player baselines. Labels and eligibility fields remain in the data product but must never be selected as predictors.
- Built and staged `player_day_features.parquet` at `gs://paa-data-979927072833/gold/subjective/soccermon/zenodo-10033832/`, containing 36,550 rows and 51 metadata, label and feature columns.
- Added future-append invariance and prior-baseline tests. The quality report measures 36,550 non-null daily-load values and 17,008 wellness-report-present days. Full quality gate passes: Ruff, strict mypy and pytest (`52 passed`, one expected ZIP duplicate-name warning).

State v14 to v15, under coordination session `PAA-CTRL-20260813-13`.

- Accepted `DEC-025`: define prediction time as the end of each calendar day because the source has no reliable intraday timestamps. Future labels use strictly post-cutoff episode starts; labels whose full horizon exceeds the player observation end are null and explicitly marked incomplete.
- Built and staged `player_day_labels.parquet` under `gs://paa-data-979927072833/gold/subjective/soccermon/zenodo-10033832/`, with 36,550 observed player-days and a quality report in GCS metadata.
- Measured cohort: 208 active-episode days; eligible new-onset rows are 36,192/35,992/35,642 and positive labels 213/448/755 at 3/7/14 days. Full quality gate passes: Ruff, strict mypy and pytest (`50 passed`, one expected ZIP duplicate-name warning).

State v13 to v14, under coordination session `PAA-CTRL-20260813-12`.

- Accepted `DEC-024`: parse source injury payloads into location/severity components, deduplicate exact same-player/same-date/same-component reports, and merge components by player and raw location across gaps of at most three days. The 1- and 7-day rules remain sensitivity analyses.
- Profiled 162 source reports: 68 contained multiple location components; six exact duplicate rows exist. The exact-deduplicated component count is 299; sensitivity produces 232/147/101 episodes at 1/3/7-day gaps respectively.
- Implemented and staged `injury_episodes.parquet` with 147 self-reported episodes and a quality report in the canonical GCS silver/metadata paths. Full quality gate passes: Ruff, strict mypy and pytest (`49 passed`, one expected ZIP duplicate-name warning).

State v12 to v13, under coordination session `PAA-CTRL-20260813-11`.

- Accepted `DEC-023`: the silver layer has separate canonical player registry, training-load daily, wellness daily, training-session and preserved event-report relations. It deliberately does not infer injury episodes, availability or labels.
- Implemented `build_subjective_silver.py`; staged seven compact Parquet outputs at `gs://paa-data-979927072833/silver/subjective/soccermon/zenodo-10033832/` and its quality report under `metadata/data_quality_reports/`.
- Measured outputs: 50 player-registry rows, 36,550 training-load daily rows, 36,550 wellness daily rows, 16,265 retained sessions, and 162/15/248 injury/illness/game event reports. Wellness missingness is explicit through `wellness_report_present` and `wellness_metric_count`.
- Added a focused silver transformation test. Full quality gate passes: Ruff lint and format, strict mypy, and pytest (`48 passed`, with one expected ZIP duplicate-name warning).

State v11 to v12, under coordination session `PAA-CTRL-20260813-10`.

- Implemented and tested an idempotent BigQuery provenance writer for the subjective bronze run. It records one deterministic ingestion-run identity and source-file records derived from the verified extraction manifest, without fabricating per-member SHA-256 values.
- Registered and read-back verified run `d4b0a71cdfc8d87e7431` in `paa_core.ingestion_runs`, with `27,655` source records read, `564,940` bronze records written and zero errors. All 19 source members are linked in `paa_core.source_files`.
- Added three unit tests for payload construction, complete rerun idempotency and recovery from a partial source-file insertion. Full quality gate passes: `poetry check --lock`, Ruff lint and format, strict mypy, and pytest (`47 passed`, with one expected ZIP duplicate-name warning).

State v10 to v11, under coordination session `PAA-CTRL-20260813-09`.

- Implemented `jobs/ingest_subjective_bronze.py` and source-grounded normalisers for daily matrices, player-keyed session JSON, and injury, illness and game-performance event CSVs.
- Wrote and staged five bronze Parquet datasets at `gs://paa-data-979927072833/bronze/subjective/soccermon/zenodo-10033832/` (714,336 bytes total), plus the quality report at `gs://paa-data-979927072833/metadata/data_quality_reports/subjective/soccermon/zenodo-10033832/bronze_ingestion.json`.
- Measured bronze output: 548,250 daily metric rows (50 players, 731 dates, 15 metrics, 136,891 null values preserved); 16,265 training-session rows; 162 injury reports; 15 illness reports; 248 game-performance reports.
- Confirmed 4,036 session rows belong to player-dates with multiple sessions; session grain is retained using `source_record_index` rather than collapsed.
- Added seven source-specific normalisation tests. Full quality gate passes: `poetry check --lock`, Ruff lint and format, strict mypy, and pytest (`44 passed`, with one expected ZIP duplicate-name test warning).
- Confirmed idempotency: a full rerun produced byte-identical SHA-256 digests for all five local bronze Parquet outputs.

State v9 to v10, under coordination session `PAA-CTRL-20260813-08`.

- Implemented `jobs/extract_subjective_archive.py` and safe, idempotent ZIP extraction. Existing raw files are accepted only when their bytes match the verified archive member.
- Extracted the verified subjective archive to ignored local raw staging and mirrored its 19 unchanged source files plus `_extraction_manifest.json` to `gs://paa-data-979927072833/raw/subjective/soccermon/zenodo-10033832/`.
- Verified the staged `session.json` (1,029,120 bytes) and extraction manifest (3,328 bytes) in Cloud Storage. The raw prefix contains 20 objects totalling 3,715,017 bytes.
- Added two extraction idempotency tests. Full quality gate passes: `poetry check --lock`, Ruff lint and format, strict mypy, and pytest (`37 passed`, with one expected ZIP duplicate-name test warning).
- The archive bucket remains immutable source preservation; no objective archive has been extracted, copied into raw staging, or processed.

State v8 to v9, under coordination session `PAA-CTRL-20260813-07`.

- Verified successful one-time transfer operation `transferOperations/transferJobs-3472342193733823656-16747793546306343886`: 5 of 5 objects and 99,132,769,855 bytes copied; source and sink totals match.
- Registered exact archive object locations. The verified subjective ZIP is 705,770 bytes at `gs://paa-source-archives-979927072833/soccermon/zenodo-10033832/zenodo.org/records/10033832/files/subjective.zip`, generation `1786585914896704`.
- Verified the subjective archive MD5 `o+hq7KYR93yTMaU16uAL9w==` against the checksum-bearing Zenodo transfer manifest, and computed local SHA-256 `338e9878fbed1f941cfc37b3f012cb356f97cc0f726e80a79aa5c8e67cc2a87c` for the downloaded audit copy.
- Performed read-only schema discovery on the 19-file subjective archive. It contains wide daily training-load and wellness matrices (731 dates, 50 player columns), per-player session lists in JSON, and event-style injury, illness and game-performance CSVs.
- Accepted `DEC-022`: bronze ingestion will normalise the observed wide daily matrices to long records while preserving session and event grain. No source files have been extracted into a project data layer or transformed into bronze yet.

State v7 to v8, under coordination session `PAA-CTRL-20260813-06`.

- Implemented ingestion foundations only: safe, deterministic ZIP inventory; immutable source-asset provenance; deterministic ingestion-run identities; and generic structural data contracts with reportable quality issues.
- Added 12 synthetic unit tests covering archive safety, provenance idempotency and contract failures. No SoccerMon archive was extracted, parsed or assumed to contain a particular schema.
- Restored the repository-local Poetry environment from the committed `poetry.lock` after the prior virtual environment was found incomplete. The restored environment is `C:\Users\USER\Documents\Projects\player-availability-analysis\.venv`.
- Full quality gate passes: `poetry check --lock`, Ruff lint and format, strict mypy, and pytest (`35 passed`, with one expected ZIP duplicate-name test warning).
- Latest archive-transfer check: `IN_PROGRESS`; 5 source objects / 99,132,769,855 bytes discovered, with 1 object / 8,255,096,042 bytes copied to the archive bucket.

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
  docs/                       PROJECT_STATE.md, DECISION_LOG.md, architecture/, decisions/, reports/
                              19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
  infra/                      empty
  jobs/                       extract_subjective_archive.py, ingest_subjective_bronze.py, build_subjective_silver.py, record_subjective_provenance.py
  notebooks/                  empty
  scripts/                    acquire_soccermon_archive.py
  src/player_availability/
    __init__.py  py.typed
    config/      settings.py, yaml_source.py
    ingestion/   archive.py, provenance.py, provenance_store.py, subjective.py, silver.py
    schemas/     empty
    analysis/    cohort.py, plots.py
    quality/     contracts.py
    utils/       paths.py
  tests/
    conftest.py
    unit/            settings, archive, provenance, contract and subjective-ingestion tests (47 tests)
    data_contracts/  empty
    leakage/         empty
    smoke/           empty
```

**Facts:**
- Branch `main`. Foundation committed. `.env` correctly excluded from version control.
- No remote configured. Git is deliberately local-only unless explicitly requested (`DEC-017`).
- No CI workflow yet.
- Locked dependency versions include `google-cloud-storage 3.13.1`, `google-cloud-bigquery 3.43.0`, `pydantic 2.13.4`, `pydantic-settings 2.15.0`, `polars 1.43.2`, `pyarrow 25.0.1`, `matplotlib 3.11.1`, `pytest 9.1.1`, `ruff 0.16.2`, `mypy 2.3.0`.
- The repository intentionally does not yet contain doc 18's `pipelines/`, `app/` or `sql/` directories (`DEC-012`).

---

## Current GCP State

**Verification status: PROJECT, BUCKET AND STORAGE TRANSFER SERVICE VERIFIED; ARCHIVE TRANSFER SUCCESSFUL.**

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

Live transfer job: `transferJobs/3472342193733823656`. Completed operation: `transferOperations/transferJobs-3472342193733823656-16747793546306343886`, status `SUCCESS`, with 5 objects and 99,132,769,855 bytes found at source and copied to the sink.

---

## Current Data State

- Source dataset: SoccerMon. Subjective archive small; objective GNSS archive approximately 99 GB compressed.
- Verified subjective source: MD5 `o+hq7KYR93yTMaU16uAL9w==`, SHA-256 `338e9878fbed1f941cfc37b3f012cb356f97cc0f726e80a79aa5c8e67cc2a87c`, CC BY 4.0. The local audit copy is ignored under `data/tmp/archive_audit/`.
- Raw staging is complete at `gs://paa-data-979927072833/raw/subjective/soccermon/zenodo-10033832/`: 19 unchanged source files and `_extraction_manifest.json`, 20 objects / 3,715,017 bytes.
- Bronze staging is complete at `gs://paa-data-979927072833/bronze/subjective/soccermon/zenodo-10033832/`: five normalised Parquet datasets / 714,336 bytes. The quality report is stored under `metadata/data_quality_reports/`.
- Silver staging is complete at `gs://paa-data-979927072833/silver/subjective/soccermon/zenodo-10033832/`: player registry, training-load daily, wellness daily, training sessions and preserved event-report relations. No injury episode or label table exists.
- The same silver prefix now also contains 147 self-reported injury episodes; labels and availability states do not yet exist.
- Gold staging contains the 36,550-row player-day labels table. Labels are not features and have no rolling or normalised predictors yet.
- Gold staging also contains the `subjective_v1` 36,550-row player-day feature table. It includes labels for cohort convenience, but model code must use an explicit predictor list.
- Gold staging contains `player_day_features_with_splits.parquet`, which preserves the source feature columns and adds history eligibility, a chronological partition and primary 14-day modelling eligibility.
- The frozen Phase B manifest and report are stored under `metadata/analysis_reports/subjective/soccermon/zenodo-10033832/` and the report is mirrored in Drive.
- BigQuery provenance is registered: run `d4b0a71cdfc8d87e7431` in `paa_core.ingestion_runs` and 19 linked source-file rows in `paa_core.source_files`. The per-member SHA-256 column is deliberately null because only the enclosing ZIP was independently SHA-256 verified; ZIP CRC32 values are retained in source-file notes.
- Observed layouts: 731-day by 50-player daily metric matrices, 50 per-player session lists with `date`, `duration`, `rpe` and `srpe`, and timestamped injury, illness and game-performance events.
- **Locked sequence: subjective vertical slice first. Full GPS ingestion must not begin.**
- Objective/GPS data remains archive-only and unprocessed.

---

## Current Modelling State

Phase B controls are implemented. `DEC-027` freezes chronological boundaries with 14-day embargoes, based on the 28-day-history and complete-14-day-label period. The training, validation and test periods are respectively `2020-01-28` to `2021-03-16`, `2021-03-31` to `2021-08-15` and `2021-08-30` to `2021-12-17`.

| ID | Model | Status |
|----|-------|--------|
| M0 | Operational baseline | Next: EXP-002 naive prevalence baseline |
| M1 | Logistic regression | Not started |
| M2 | Gradient boosting | Not started |
| M3 | Cox proportional hazards | Not started |
| M4 | Random survival forest | Not started |
| M5 | Boosted survival | Not started |
| M6 | Neural survival | Not started; only if evidence justifies |

Grain: `player x date`. Candidate outcomes: `injury_next_3d`, `injury_next_7d`, `injury_next_14d`, and time to next injury episode with right censoring.

The primary M0 cohort and split are frozen for this feature version. `injury_episode_gap_days: 3` remains a sensitivity-analysis requirement and must not be used for a causal or medical claim.

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
| DEC-022 | Normalise verified subjective source layouts by their native grain |
| DEC-023 | Canonical subjective silver relations preserve daily, session and event grain |
| DEC-024 | Self-reported injury episodes use raw location and a 3-day gap |
| DEC-025 | End-of-day prediction cutoff and censored post-cutoff player-day labels |
| DEC-026 | Subjective v1 features are trailing and player-baseline features with explicit leakage controls |
| DEC-027 | Shared chronological split, 14-day embargo and explicit M0 predictor contract |

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
| None | No open design decision blocks EXP-002 naive baseline |

---

## Known Issues / Technical Debt

- No remote. This is intentional local-only Git policy (`DEC-017`), so the repository still has no off-machine version-control backup.
- No CI workflow. `poetry check --lock`, ruff, mypy and pytest all run locally via `make check` but are not enforced automatically.
- Service-account naming unreconciled: `paa-build-sa` (handoff) versus `paa-ci-sa` (doc 18).
- Repository structure intentionally incomplete against doc 18 (`DEC-012`). Deliberate, not drift.
- `injury_episode_gap_days: 3` is provisional pending EXP-001 and must not be used for a headline result.
- Git identity is set at repository level rather than inherited from a global configuration.
- Event payloads remain preserved as source JSON; injury episodes, availability status and modelling labels are intentionally not inferred yet.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.

---

## Blockers

None. The next phase has normal data-quality gates rather than an acquisition blocker.

---

## Work In Progress

Phase B split construction is complete. EXP-002 will calculate only naive operational benchmarks; no fitted predictive model or test-set performance review has occurred. No objective archive processing is authorised. No other control session is known to be editing this working tree.

---

## Immediate Next Actions

1. Run `EXP-002` naive operational baselines on the frozen chronological partitions.
2. Review the baseline report before implementing `EXP-003` regularised logistic regression.
3. Confirm archive-bucket lifecycle rules and billing-budget alerts before broader processing.
4. Reconcile the `paa-build-sa` / `paa-ci-sa` naming.
5. Add a CI workflow running `poetry check --lock`, ruff, mypy strict and pytest on every push. It remains local only until the user explicitly requests a remote.

---

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|------|--------|----------|
| Lint (ruff) | PASS | `ruff check src tests jobs`, all checks passed |
| Format (ruff) | PASS | 26 files already formatted |
| Type check (mypy strict) | PASS | 26 source files, no issues |
| Unit tests | PASS | 47 passed; one expected `zipfile` duplicate-name warning in the archive-safety test |
| Lockfile integrity | PASS | `poetry check --lock`, all set |
| Cloud Storage access | PASS | Active project and `gs://paa-data-979927072833` verified; expected zones listed |
| Archive acquisition preflight | PASS | Zenodo record `10033832` returned 5 files totalling 99.13 GB; managed-transfer script dry run, compilation and Ruff checks pass; it made no cloud writes |
| Storage Transfer Service | PASS | Operation completed successfully: 5 objects / 99,132,769,855 bytes copied, matching the source total |
| Subjective raw staging | PASS | 19 unchanged source members and extraction manifest staged to GCS; object spot checks and 37-test quality suite pass |
| Subjective bronze normalisation | PASS | 5 Parquet outputs, compact GCS staging, quality report and byte-identical rerun; 44-test quality suite pass |
| Subjective BigQuery provenance | PASS | One registered ingestion run with 19 linked source files; read-back totals reconcile (27,655 read / 564,940 written) |
| Subjective silver transformation | PASS | 7 canonical Parquet relations staged in GCS; quality report and 48-test suite pass |
| Injury-episode construction | PASS | 147 3-day-gap episodes staged in GCS; 1/3/7-day sensitivity documented and 49-test suite pass |
| Player-day labels | PASS | 36,550 gold player-day rows; post-cutoff 3/7/14-day labels, active-episode eligibility and right-censoring validated |
| Subjective v1 features | PASS | 36,550 gold rows / 51 columns; future-append and prior-only baseline tests pass |
| Analysis execution plan | PASS | Local and Drive runbook created; 296 lines covering analysis sequence, hypotheses, gates and required artefacts |
| Phase A cohort report | PASS | Reproducible local, Drive and GCS report; 28-day cohort, prevalence, event concentration and feature coverage measured |
| Phase A charts | PASS | Three reproducible and visually inspected PNG figures published locally, in Drive and in GCS metadata |
| Phase B split controls | PASS | Frozen dates, two 14-day embargoes, 34-column predictor allow-list, 36,550-row split product and focused tests pass |
| Ingestion foundation tests | PASS | Synthetic archive safety, provenance and generic contract tests; no real source schema asserted |
| Schema / data-contract tests | Partially implemented | Generic structural contracts exist; source-specific contracts await schema audit |
| Leakage tests | Not implemented | Directory exists, no features to test |
| Smoke tests | Not implemented | Directory exists, no pipeline to run |
| CI | Not implemented | Gates run locally only |

Gates were run from a clean environment with no inherited path or configuration, so the results reflect a fresh checkout rather than a primed local setup.

Test coverage covers configuration, archive safety, generic contracts, source-specific subjective normalisation and BigQuery provenance persistence. Silver, leakage and smoke coverage are not yet implemented.

---

## State Synchronisation Status

| Item | Local | Drive |
|------|-------|-------|
| `PROJECT_STATE.md` | v20, 2026-08-13T22:00:00Z | v20, 2026-08-13T22:00:00Z |
| `DECISION_LOG.md` | DEC-001 to DEC-027 | DEC-001 to DEC-027 |

Status: **SYNCHRONISED**

**Mirror method (`DEC-020`).** The Drive connector updates the existing raw Markdown files in place using their stable Drive IDs. The project does not rely on a mounted `G:` path. The folder holds exactly one of each control document.

**Note on Git HEAD.** This document describes the tree as of commit `cc06aeb` on `main`. It is itself committed immediately afterwards, so the commit containing this file is one ahead of the commit it describes. This is a deliberate convention, not drift: a state document cannot record the hash of the commit that contains it.
