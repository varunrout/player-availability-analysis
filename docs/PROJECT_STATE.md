# Player Availability Analysis - Project State

State Version: 23
Last Updated UTC: 2026-08-14T13:47:32Z
Coordination Session ID: PAA-CTRL-20260814-01
Git Branch: main
Git HEAD: 037bc402c346f9188ecb21218a6e732a3dc91700 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: Pre-Model Analysis - Stage 1
Current Phase Status: Stage 0 results are approved. Stage 1 injury-episode and outcome EDA is at specification review; implementation is not yet authorised.

## Current Objective

Complete pre-model analysis through nine explicit stages, with project-owner approval after each specification and each result review. The immediate task is to agree the Stage 1 injury-episode and outcome EDA specification. No Stage 1 implementation may begin before specification approval, and no baseline model may be fitted before the Stage 8 readiness report is approved as `READY`.

## Completed Foundation

- Verified SoccerMon archive preserved in the dedicated GCS archive bucket.
- Subjective raw extraction, bronze normalisation and BigQuery provenance registration complete.
- Canonical subjective silver relations complete, including 147 primary-rule self-reported injury episodes.
- Gold player-day labels and unsplit `subjective_v1` feature table complete at 36,550 player-days.
- End-of-day prediction cutoff, right-censoring, active-episode eligibility and prior-only feature rules remain accepted.
- Poetry environment, configuration, quality gates and local-only Git repository are operational.

## Completed Since Previous State

- Accepted `DEC-028`: withdrew the former Phase A report and Phase B split from active use, superseded `DEC-027`, and restarted pre-model analysis at Stage 0.
- Deleted former Phase A/Phase B code, tests, reports and charts locally; deleted their five Drive files; deleted seven GCS report/figure objects and `player_day_features_with_splits.parquet`.
- Preserved the trusted unsplit `player_day_features.parquet`, player-day labels and all source, bronze and silver data products.
- Accepted `DEC-029`: shared analysis functions support both a script and a matching notebook; scripts alone persist outputs under `outputs/analysis/<stage>/`; notebooks render inline and are committed without outputs.
- Replaced the bundled Phase A/Phase B workflow in the analysis runbook with Stages 0 through 8 and explicit owner-approval gates.
- Committed the clean reset and filesystem contract at `5c76cc0`. Full remaining quality gate passes: Ruff, strict mypy, lockfile check and pytest (`52 passed`, one expected ZIP duplicate-name warning).
- Implemented Stage 0 once as shared analysis code, with a script runner, matching output-free notebook, retained tables/report/charts and focused tests.
- Added JupyterLab and IPython kernel dependencies to the Poetry development group and refreshed `poetry.lock`.
- Executed both the notebook and canonical script against the actual GCS and BigQuery products through ADC.
- Stage 0 audited 15 compact relations and 45 relevant cloud objects with zero failures and one expected sparse-session warning.
- Verified 15 schema contracts, all primary keys, raw-to-gold row-count reconciliation, BigQuery provenance, registry membership, label/feature identity and complete 50-player by 731-day gold coverage.
- Committed the implementation and retained outputs at `e35bc34`. Full quality gate passes: Ruff, strict mypy, lockfile check and pytest (`55 passed`, one expected ZIP duplicate-name warning).
- Project owner approved the Stage 0 results on 2026-08-14, closing the data-foundation gate and authorising Stage 1 specification review.

## Current Repository State

```text
jobs/analysis/              approved-stage script runners
notebooks/analysis/         matching output-cleared notebooks
outputs/analysis/           retained script-generated analysis artifacts
src/player_availability/    ingestion, outcomes, features, quality and configuration
tests/                      55 passing tests, including three Stage 0 tests
docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
docs/PROJECT_STATE.md
docs/DECISION_LOG.md
```

Active Stage 0 assets are under `src/player_availability/analysis/`, `jobs/analysis/`, `notebooks/analysis/` and `outputs/analysis/00_data_audit/`. The notebook is committed with no outputs or execution counts. There is no active split implementation, split-assigned dataset or model. Historical commits remain available locally by design.

## Current GCP State

- Project: `player-availability-analysis`; primary region: `europe-west2`.
- Archive bucket: `gs://paa-source-archives-979927072833`; verified transfer remains complete at 99,132,769,855 bytes.
- Analytical bucket: `gs://paa-data-979927072833` with raw, bronze, silver, gold and metadata zones.
- Gold subjective prefix retains only `player_day_labels.parquet` and unsplit `player_day_features.parquet`.
- The former Phase A/Phase B analysis-report prefix has no objects.
- BigQuery provenance remains registered in `paa_core.ingestion_runs` and `paa_core.source_files`.
- Stage 0 read and reconciled GCS and BigQuery products but made no cloud-data changes.
- No objective/GPS archive has been extracted or processed.

## Current Data State

- Source: SoccerMon subjective data from 50 players across two teams and 731 calendar dates.
- Silver: player registry, daily load, daily wellness, sessions, source event reports and 147 three-day-gap injury episodes.
- Gold labels: 36,550 player-days with censored 3/7/14-day future episode-start labels.
- Gold features: 36,550 unsplit `subjective_v1` player-days with current, rolling and prior-only player-relative features.
- Episode-gap, horizon, burn-in, missingness and final cohort choices must be reviewed in the new staged analysis before modelling protocol freeze.
- Objective/GPS data remains archive-only under the subjective-first decision.

## Current Modelling State

No model has been fitted. No chronological split is currently frozen. `DEC-027` is superseded by `DEC-028`. Stage 0 contains no prevalence, feature-distribution, correlation, split or model analysis. Baseline modelling is blocked by process until Stages 0 through 8 are completed and approved.

## Current Product State

No API, dashboard, product table or inference service is implemented. The intended product remains practitioner decision support, never diagnosis, clearance or participation advice.

## Locked Decisions

- `DEC-001` to `DEC-026` remain the accepted foundation except where explicitly superseded in the decision log.
- `DEC-027` is superseded and its former split is not active.
- `DEC-028` resets pre-model analysis to Stage 0 while preserving trusted data engineering and history.
- `DEC-029` defines the shared script/notebook implementation and output-storage contract.
- Git remains local-only unless the project owner explicitly requests otherwise.
- Random row-level splitting is prohibited for headline evaluation.
- No objective/GPS processing begins during the subjective pre-model analysis programme.

## Open Decisions

- Approve or revise the detailed Stage 1 injury-episode and outcome EDA specification.
- Later stages must approve the primary episode rule, horizon, cohort, missingness policy, predictor contract and chronological validation protocol before modelling.

## Known Issues / Technical Debt

- No remote or CI workflow; this is consistent with the current local-only Git policy.
- Service-account naming remains unreconciled: `paa-build-sa` versus `paa-ci-sa` in older architecture text.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.
- Full objective/GPS ingestion remains deliberately deferred.

## Blockers

No technical blocker. Stage 1 implementation is process-blocked until the project owner approves its specification.

## Work In Progress

Stage 1 specification review is open. No Stage 1 code is in progress, and no other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Present the exact Stage 1 questions, episode-rule sensitivities, outcome checks, tables, charts and acceptance criteria.
2. Obtain project-owner approval or revision of that specification.
3. After approval only, implement the shared Stage 1 module, script, output-free notebook and focused tests.
4. Run Stage 1, inspect the retained results together and obtain results approval before Stage 2.

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Lockfile integrity | PASS | `poetry check --lock` |
| Lint | PASS | Ruff, all checks passed |
| Format | PASS | Stage 0 files formatted; repository format check clean |
| Type check | PASS | strict mypy, 39 source files |
| Tests | PASS | 55 passed; one expected duplicate-ZIP-member warning |
| Analysis reset - local | PASS | former Phase A/Phase B code and outputs removed |
| Analysis reset - Drive | PASS | five former report/chart files removed |
| Analysis reset - GCS | PASS | report prefix empty; split-assigned dataset removed |
| Trusted gold foundation | PASS | unsplit labels and features remain in GCS |
| Stage 0 specification | PASS | approved before implementation |
| Stage 0 implementation | PASS | shared module, script, notebook, outputs and tests committed at `e35bc34` |
| Stage 0 automated audit | PASS | 15 relations; 45 objects; zero failures; one expected warning |
| Stage 0 results review | PASS | project-owner approval received 2026-08-14 |
| Stage 1 specification | PENDING OWNER APPROVAL | no Stage 1 implementation started |
| Leakage/split gate | NOT ACTIVE | no split currently frozen |
| Modelling | NOT STARTED | no model fitted |

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v23, 2026-08-14T13:47:32Z | v23, 2026-08-14T13:47:32Z |
| `DECISION_LOG.md` | DEC-001 to DEC-029 | DEC-001 to DEC-029 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | stage-gated revision | stage-gated revision |

Status: **SYNCHRONISED**

Drive mirrors use stable file IDs and in-place updates. The state records `037bc40`, the committed tree before this control-document update; the commit containing the control update will be one commit later by design.
