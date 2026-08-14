# Player Availability Analysis - Project State

State Version: 24
Last Updated UTC: 2026-08-14T15:51:29Z
Coordination Session ID: PAA-CTRL-20260814-01
Git Branch: main
Git HEAD: 42463175d3c55645dcf409df89d5d0ea8e2aebb8 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: Pre-Model Analysis - Stage 1
Current Phase Status: Stage 1 implementation and real-data outcome EDA are complete with automated `PASS`. Awaiting project-owner methodological review; Stage 2 is not authorised.

## Current Objective

Complete pre-model analysis through nine explicit stages, with project-owner approval after each specification and each result review. The immediate task is to review Stage 1 evidence, approve or revise the primary episode rule and decide whether outcome labels are credible enough for Stage 2. No baseline model may be fitted before the Stage 8 readiness report is approved as `READY`.

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
- Project owner approved the Stage 1 specification on 2026-08-14.
- Implemented Stage 1 as shared analysis code, canonical script, matching output-free notebook, 11 retained tables, eight retained charts and three focused tests.
- Rebuilt 1/3/7-day episode sensitivities through the production episode function and independently regenerated every gold label field through the production label function.
- Stage 1 automated integrity checks pass: all 299 unique report components reconcile, stored three-day episodes reproduce exactly, gold labels reproduce exactly and horizon nesting has zero violations.
- Executed the canonical script and notebook against GCP products; committed implementation and retained outputs at `4246317`.
- Full quality gate passes: lockfile, Ruff, strict mypy and pytest (`58 passed`, one expected ZIP duplicate-name warning).

## Current Repository State

```text
jobs/analysis/              approved-stage script runners
notebooks/analysis/         matching output-cleared notebooks
outputs/analysis/           retained script-generated analysis artifacts
src/player_availability/    ingestion, outcomes, features, quality and configuration
tests/                      58 passing tests, including Stage 0 and Stage 1 tests
docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
docs/PROJECT_STATE.md
docs/DECISION_LOG.md
```

Active Stage 0 and Stage 1 assets follow the shared module/script/notebook/output contract. Both notebooks are committed with no outputs or execution counts. There is no active split implementation, split-assigned dataset or model. Historical commits remain available locally by design.

## Current GCP State

- Project: `player-availability-analysis`; primary region: `europe-west2`.
- Archive bucket: `gs://paa-source-archives-979927072833`; verified transfer remains complete at 99,132,769,855 bytes.
- Analytical bucket: `gs://paa-data-979927072833` with raw, bronze, silver, gold and metadata zones.
- Gold subjective prefix retains only `player_day_labels.parquet` and unsplit `player_day_features.parquet`.
- The former Phase A/Phase B analysis-report prefix has no objects.
- BigQuery provenance remains registered in `paa_core.ingestion_runs` and `paa_core.source_files`.
- Stage 0 read and reconciled GCS and BigQuery products but made no cloud-data changes.
- Stage 1 read compact GCS outcome products but made no cloud-data changes.
- No objective/GPS archive has been extracted or processed.

## Current Data State

- Source: SoccerMon subjective data from 50 players across two teams and 731 calendar dates.
- Silver: player registry, daily load, daily wellness, sessions, source event reports and 147 three-day-gap injury episodes.
- Gold labels: 36,550 player-days with censored 3/7/14-day future episode-start labels.
- Gold features: 36,550 unsplit `subjective_v1` player-days with current, rolling and prior-only player-relative features.
- Episode-gap, horizon, burn-in, missingness and final cohort choices must be reviewed in the new staged analysis before modelling protocol freeze.
- The 162 injury reports contain 306 parsed components and 299 unique components. Under the current three-day rule these form 147 location episodes but only 73 distinct player-date onset events.
- Gap sensitivity is substantial: 1/3/7-day rules produce 232/147/101 location episodes and 108/73/55 distinct onset days respectively.
- Outcome support is highly concentrated: 35 of 50 players have no episode, the top five players account for 75.3% of onset days, and the leading team accounts for 90.4%.
- Eligible prevalence is 0.525%, 1.028% and 1.686% for 3/7/14-day horizons. The effective represented onset-day counts are 68, 71 and 71 respectively.
- Objective/GPS data remains archive-only under the subjective-first decision.

## Current Modelling State

No model has been fitted. No chronological split is currently frozen. `DEC-027` is superseded by `DEC-028`. Stage 1 establishes internal outcome integrity but reveals low and concentrated effective event support; it does not establish predictive value or generalisability. Baseline modelling is blocked until Stages 0 through 8 are completed and approved.

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

- Approve or revise the current three-day episode rule after reviewing 1/3/7-day sensitivity.
- Approve or reject Stage 1 outcome-label credibility for progression to Stage 2.
- Later stages must approve the primary episode rule, horizon, cohort, missingness policy, predictor contract and chronological validation protocol before modelling.

## Known Issues / Technical Debt

- No remote or CI workflow; this is consistent with the current local-only Git policy.
- Service-account naming remains unreconciled: `paa-build-sa` versus `paa-ci-sa` in older architecture text.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.
- Effective outcome support is limited and highly concentrated by player, team and period; later protocol gates must constrain claims and stress-test generalisation.
- Full objective/GPS ingestion remains deliberately deferred.

## Blockers

No technical blocker. Stage 2 is process-blocked until the project owner reviews and approves or revises the Stage 1 methodological findings.

## Work In Progress

Stage 1 results review is open. No Stage 2 code is in progress, and no other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Review `outputs/analysis/01_outcome_eda/reports/STAGE_01_OUTCOME_EDA.md`, its 11 tables and eight figures with the project owner.
2. Decide whether to retain the three-day location-specific episode rule and accept the labels as credible but materially limited.
3. After explicit results approval only, present the detailed Stage 2 missingness and reporting-process EDA specification.

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Lockfile integrity | PASS | `poetry check --lock` |
| Lint | PASS | Ruff, all checks passed |
| Format | PASS | Stage 0 files formatted; repository format check clean |
| Type check | PASS | strict mypy, 41 source files |
| Tests | PASS | 58 passed; one expected duplicate-ZIP-member warning |
| Analysis reset - local | PASS | former Phase A/Phase B code and outputs removed |
| Analysis reset - Drive | PASS | five former report/chart files removed |
| Analysis reset - GCS | PASS | report prefix empty; split-assigned dataset removed |
| Trusted gold foundation | PASS | unsplit labels and features remain in GCS |
| Stage 0 specification | PASS | approved before implementation |
| Stage 0 implementation | PASS | shared module, script, notebook, outputs and tests committed at `e35bc34` |
| Stage 0 automated audit | PASS | 15 relations; 45 objects; zero failures; one expected warning |
| Stage 0 results review | PASS | project-owner approval received 2026-08-14 |
| Stage 1 specification | PASS | approved before implementation |
| Stage 1 implementation | PASS | shared module, script, notebook, outputs and tests committed at `4246317` |
| Stage 1 automated integrity | PASS | component, episode, label and horizon checks have zero failures |
| Stage 1 methodological review | PENDING OWNER APPROVAL | episode-rule and outcome-credibility decision open |
| Leakage/split gate | NOT ACTIVE | no split currently frozen |
| Modelling | NOT STARTED | no model fitted |

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v24, 2026-08-14T15:51:29Z | v24, 2026-08-14T15:51:29Z |
| `DECISION_LOG.md` | DEC-001 to DEC-029 | DEC-001 to DEC-029 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | stage-gated revision | stage-gated revision |

Status: **SYNCHRONISED**

Drive mirrors use stable file IDs and in-place updates. The state records `4246317`, the committed tree before this control-document update; the commit containing the control update will be one commit later by design.
