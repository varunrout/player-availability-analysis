# Player Availability Analysis - Project State

State Version: 28
Last Updated UTC: 2026-08-14T21:09:38Z
Coordination Session ID: PAA-CTRL-20260814-01
Git Branch: main
Git HEAD: 730b0dc9d178a1237b13bc061fda4a23b5a0651e (pre-state-update commit; see State Synchronisation Status)
Current Milestone: Pre-Model Analysis - Stage 3
Current Phase Status: Stage 3 feature-distribution and temporal EDA is implemented and passes its automated gate. Results and the resulting range/transformation/history policy await project-owner review; Stage 4 is not authorised.

## Current Objective

Complete pre-model analysis through nine explicit stages, with project-owner approval after each specification and each result review. The immediate task is to review Stage 3 evidence and decide credible ranges, justified transformations, reliable feature families and history requirements. No Stage 4 implementation may begin before Stage 3 results approval, and no baseline model may be fitted before the Stage 8 readiness report is approved as `READY`.

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
- Accepted `DEC-030`: retained the three-day location episode rule, defined player-date onset as the effective binary outcome event, accepted labels for continued EDA with explicit limitations, and mandated gap/concentration/generalisation sensitivities.
- Project owner approved the Stage 2 specification on 2026-08-14.
- Implemented Stage 2 as shared analysis code, canonical script, matching output-free notebook, 12 retained tables, nine retained charts and three focused tests.
- Executed the Stage 2 script and notebook against compact GCS bronze, silver and gold products; no cloud data was changed.
- Stage 2 automated integrity passes with zero failures: silver wellness presence flags are internally consistent and eight gold completeness/exposure fields reproduce exactly from silver.
- Stage 2 found 17,008 wellness-report days across 36,550 player-days (46.5%); 16,931 were complete seven-metric reports and 77 were partial.
- Wellness coverage ranges from 3.1% to 88.4% by player and is 55.9% for Team A versus 35.6% for Team B; the longest no-report run is 607 days.
- All eight training-load metrics are populated on every calendar row, but derived zeros are common; absence of a session record remains uninterpretable as either confirmed rest or missing exposure.
- Wellness reporting rises from a mean 62.9% over days -28 to -1 to 97.3% on injury-onset days, demonstrating outcome-entangled reporting-process risk. This is descriptive, not causal or predictive evidence.
- Committed Stage 2 implementation and retained outputs at `9d06935`. Full quality gate passes: lockfile, Ruff, strict mypy, pytest (`61 passed`, one expected ZIP duplicate-name warning), and notebook execution.
- Project owner approved the Stage 2 results and recommended missingness policy on 2026-08-14.
- Accepted `DEC-031`: preserve null/zero distinctions, prohibit blanket imputation, exclude same-day wellness/reporting fields from the primary predictor contract, permit lagged reporting candidates under later audit, retain unknown session-absence semantics and defer player exclusions to Stage 6.
- Project owner approved the Stage 3 specification on 2026-08-14.
- Implemented Stage 3 as shared analysis code, canonical script, matching output-free notebook, 13 retained tables, nine retained charts and three focused tests.
- Profiled 33 numeric gold features across all 36,550 player-days; all finite, non-negative, bounded-count and rolling-window integrity checks pass.
- Daily load is zero on 61.2% of player-days. These are almost exactly the 22,353 days without a recorded session; six recorded-session days have zero load and remain retained for review.
- Current fatigue uses observed values 1-5 and readiness 1-10. Wellness is discrete and current-day/current-inclusive versions remain ineligible for the primary contract under `DEC-031`.
- Within-player variation dominates all five core features, but between-player shares remain material: 14.5% for daily load, 28.2% for fatigue and 33.5% for readiness.
- Team and monthly means shift materially, reinforcing the need for chronological and team-aware validation rather than pooled random splitting.
- Prior z-scores are unstable when historical variance is tiny: maximum absolute values are 80.6 for daily load, 12.9 for fatigue and 21.0 for readiness. Z-score availability is conditional on non-zero prior variance, not calendar history alone.
- Statistical outer fences flag 979 rows across 14 features. The 250 highest-severity rows are retained in a review-only register capped at 20 per feature; no values were corrected or deleted.
- Executed the canonical script and notebook against the GCS gold product; committed implementation and retained outputs at `730b0dc`.
- Full quality gate passes: lockfile, Ruff, strict mypy, pytest (`64 passed`, one expected ZIP duplicate-name warning), JSON notebook validation and notebook execution.

## Current Repository State

```text
jobs/analysis/              approved-stage script runners
notebooks/analysis/         matching output-cleared notebooks
outputs/analysis/           retained script-generated analysis artifacts
src/player_availability/    ingestion, outcomes, features, quality and configuration
tests/                      64 passing tests, including Stage 0 through Stage 3 tests
docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
docs/PROJECT_STATE.md
docs/DECISION_LOG.md
```

Active Stage 0 through Stage 3 assets follow the shared module/script/notebook/output contract. All notebooks are committed with no outputs or execution counts. There is no active split implementation, split-assigned dataset or model. Historical commits remain available locally by design.

## Current GCP State

- Project: `player-availability-analysis`; primary region: `europe-west2`.
- Archive bucket: `gs://paa-source-archives-979927072833`; verified transfer remains complete at 99,132,769,855 bytes.
- Analytical bucket: `gs://paa-data-979927072833` with raw, bronze, silver, gold and metadata zones.
- Gold subjective prefix retains only `player_day_labels.parquet` and unsplit `player_day_features.parquet`.
- The former Phase A/Phase B analysis-report prefix has no objects.
- BigQuery provenance remains registered in `paa_core.ingestion_runs` and `paa_core.source_files`.
- Stage 0 read and reconciled GCS and BigQuery products but made no cloud-data changes.
- Stage 1 read compact GCS outcome products but made no cloud-data changes.
- Stage 2 read compact GCS reporting and feature products but made no cloud-data changes; retained analysis artifacts are local under `outputs/analysis/02_missingness_eda/`.
- Stage 3 read the compact GCS gold feature product but made no cloud-data changes; retained analysis artifacts are local under `outputs/analysis/03_feature_distribution_eda/`.
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
- Wellness reports exist on 46.5% of player-days and are almost always all-or-none: 16,931 complete reports, 77 partial reports and 19,542 no-report days.
- Reporting coverage varies materially by player, team and calendar period. The 607-day maximum no-report run and 3.1%-88.4% player range preclude treating wellness absence as random noise.
- Injury-onset-day wellness reporting is 97.3%, compared with 62.9% averaged over the preceding 28 days. Any same-day reporting indicator or wellness value requires prediction-time and outcome-entanglement controls before predictor eligibility.
- Gold feature distributions are internally valid but strongly zero-inflated and right-skewed for load/session magnitudes. Team/calendar shifts and material between-player wellness variation are present.
- Existing rolling sums are internally nested and current-inclusive wellness means reproduce their intended construction; the latter require lagged rebuilding before primary-model eligibility.
- Existing prior z-scores can be extreme under near-zero historical variance and require a later robustness decision; statistical extremeness alone is not a deletion rule.
- Objective/GPS data remains archive-only under the subjective-first decision.

## Current Modelling State

No model has been fitted. No chronological split is currently frozen. `DEC-027` is superseded by `DEC-028`. Stages 1 through 3 establish outcome, reporting-process and numerical-feature integrity but reveal low event support, non-random reporting, zero inflation, calendar/team shifts and unstable z-score tails. They do not establish predictive value or generalisability. Baseline modelling is blocked until Stages 0 through 8 are completed and approved.

## Current Product State

No API, dashboard, product table or inference service is implemented. The intended product remains practitioner decision support, never diagnosis, clearance or participation advice.

## Locked Decisions

- `DEC-001` to `DEC-026` remain the accepted foundation except where explicitly superseded in the decision log.
- `DEC-027` is superseded and its former split is not active.
- `DEC-028` resets pre-model analysis to Stage 0 while preserving trusted data engineering and history.
- `DEC-029` defines the shared script/notebook implementation and output-storage contract.
- `DEC-030` defines player-date onset as the effective binary outcome event and constrains sensitivity, validation and claims.
- `DEC-031` defines missing-value semantics and a conservative lagged-only wellness/reporting policy for the primary predictor contract.
- Git remains local-only unless the project owner explicitly requests otherwise.
- Random row-level splitting is prohibited for headline evaluation.
- No objective/GPS processing begins during the subjective pre-model analysis programme.

## Open Decisions

- Approve or revise Stage 3 results and decide credible ranges, transformation candidates, reliable feature families and history/variance requirements.
- Later stages must approve the primary horizon/cohort, complete predictor contract and chronological validation protocol before modelling.

## Known Issues / Technical Debt

- No remote or CI workflow; this is consistent with the current local-only Git policy.
- Service-account naming remains unreconciled: `paa-build-sa` versus `paa-ci-sa` in older architecture text.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.
- Effective outcome support is limited and highly concentrated by player, team and period; later protocol gates must constrain claims and stress-test generalisation.
- Prior-relative z-scores can become extreme when historical variance is near zero; the current fields must not enter a primary contract without an explicit robustness rule.
- Feature magnitudes and recording intensity differ by team and calendar period; later validation must measure temporal and player/team transfer sensitivity.
- Full objective/GPS ingestion remains deliberately deferred.

## Blockers

No technical blocker. Stage 4 is process-blocked until the project owner approves Stage 3 results and the associated methodological decision is recorded.

## Work In Progress

Stage 3 results review is open. No Stage 4 code is in progress, and no other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Explain the Stage 3 results, especially zero inflation, team/calendar shifts, current-inclusive wellness ineligibility and z-score tail instability.
2. Obtain project-owner approval or revision of the Stage 3 results and recommended feature-handling policy.
3. After approval, append the material decision as `DEC-032` and present the Stage 4 redundancy/structural-relationship specification.
4. Do not implement Stage 4 until its specification is separately approved.

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Lockfile integrity | PASS | `poetry check --lock` |
| Lint | PASS | Ruff, all checks passed |
| Format | PASS | Stage 2 files formatted; repository format check clean |
| Type check | PASS | strict mypy, 45 source files |
| Tests | PASS | 64 passed; one expected duplicate-ZIP-member warning |
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
| Stage 1 methodological review | PASS | accepted under `DEC-030` |
| Stage 2 specification | PASS | project-owner approval received 2026-08-14 |
| Stage 2 implementation | PASS | shared module, script, notebook, outputs and tests committed at `9d06935` |
| Stage 2 automated integrity | PASS | zero failures; wellness flags and eight gold fields reproduce exactly |
| Stage 2 notebook execution | PASS | executed against GCS; committed notebook remains output-free |
| Stage 2 results review | PASS | project-owner approval received 2026-08-14; policy accepted under `DEC-031` |
| Stage 3 specification | PASS | project-owner approval received 2026-08-14 |
| Stage 3 implementation | PASS | shared module, script, notebook, outputs and tests committed at `730b0dc` |
| Stage 3 automated integrity | PASS | 33 numeric features; zero hard failures; rolling identities pass |
| Stage 3 notebook execution | PASS | executed against GCS; committed notebook remains output-free |
| Stage 3 results review | PENDING OWNER APPROVAL | range, transformation, feature-family and history decisions required |
| Leakage/split gate | NOT ACTIVE | no split currently frozen |
| Modelling | NOT STARTED | no model fitted |

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v28, 2026-08-14T21:09:38Z | v28, 2026-08-14T21:09:38Z |
| `DECISION_LOG.md` | DEC-001 to DEC-031 | DEC-001 to DEC-031 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | stage-gated revision | stage-gated revision |

Status: **SYNCHRONISED**

Drive mirrors use stable file IDs and in-place updates. The state records `730b0dc`, the committed tree before this control-document update; the commit containing the control update will be one commit later by design.
