# Player Availability Analysis - Project State

State Version: 36
Last Updated UTC: 2026-08-15T02:24:45Z
Coordination Session ID: PAA-CTRL-20260815-01
Git Branch: main
Git HEAD: 9125b85d6e2f9c73cd719882b2b6e0ade04ef658 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: Pre-Model Analysis - Stage 7 Results Review
Current Phase Status: Stage 7 specification was approved and frozen under `DEC-036`, then implemented and executed. Automated protocol/leakage status is PASS with one warning and three review findings. Project-owner results interpretation is pending; Stage 8 is not yet authorised.

## Current Objective

Complete pre-model analysis through nine explicit stages, with project-owner approval after each specification and each result review. The immediate task is to review Stage 7's frozen protocol, leakage evidence and sparse-support limitations, then approve or revise the interpretation before Stage 8 specification review. No baseline model may be fitted before the Stage 8 readiness report is approved as `READY`.

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
- Project owner approved the Stage 3 results and recommended feature-handling policy on 2026-08-14.
- Accepted `DEC-032`: preserve raw values and statistical extremes, carry paired recording-state and `log1p` magnitude candidates, do not automatically transform discrete wellness, exclude unstable existing z-scores from the primary operational contract, and defer history thresholds to Stage 6 sensitivity.
- Project owner approved the Stage 4 specification on 2026-08-14.
- Implemented Stage 4 as shared analysis code, canonical script, matching output-free notebook, 12 retained tables, seven retained charts and three focused tests.
- Stage 4 analysed 33 source numeric features plus 16 target-blind derived candidates across 36,550 player-days; no outcome column entered the analysis frame and no player-day or source value was changed.
- All 15 `log1p` transformations preserve zero and rank exactly. The full target-blind contract contains 35 candidate representations; same-day/current-inclusive wellness remains outside it and all three existing z-scores remain excluded.
- Found 221 absolute-Spearman relationships at or above 0.90 and 36 near-deterministic pairs at or above 0.995. Fifteen near-deterministic pairs are the expected raw/`log1p` alternatives.
- Daily load and session sRPE are nearly duplicate representations: all-day Spearman is 0.999 and positive-recorded-day Spearman is 0.989. Daily load versus duration falls to 0.828 on positive recorded days, retaining more distinct magnitude information.
- Every adjacent 3/7, 7/14 and 14/28-day rolling-sum pair exceeds 0.92 Spearman. This supports a smaller operational window set while retaining the full set as target-blind alternatives pending owner review.
- Wellness report presence and wellness metric count are near-deterministic at Spearman 0.999; both remain descriptive-only under `DEC-031`.
- Executed the canonical Stage 4 script and notebook against the GCS gold product. Stage status is PASS with zero failures, zero warnings and three review findings; no cloud data was changed.
- Committed Stage 4 implementation and retained outputs at `93a95fc`. Full quality gate passes: lockfile, formatting, Ruff, strict mypy, pytest (`67 passed`, one expected ZIP duplicate-name warning), JSON notebook validation and notebook execution.
- Project owner approved the Stage 4 results and recommended target-blind feature-family policy on 2026-08-15 local time.
- Accepted `DEC-033`: retain the full contract as an alternatives catalogue; carry a compact provisional operational policy using recording state, `log1p` magnitudes, daily load as the primary internal-load family, session duration as distinct context, and 7/28-day anchors; defer session-sRPE duplication, 3/14-day windows, prior baselines and lagged wellness to explicit later sensitivities and controls.
- Project owner approved the Stage 5 descriptive outcome-context specification on 2026-08-15.
- Implemented Stage 5 as shared analysis code, canonical script, matching output-free notebook, ten retained tables, nine retained charts and four focused tests.
- Collapsed 147 location episodes to 73 distinct player-date onsets. Sixty-eight onsets have complete -28 through day-0 histories, and all 68 have clean same-player calendar and reporting-matched references.
- Primary matched summaries use only days -28 through -1; day 0 is displayed separately. No fixed-horizon labels entered feature measurement and no model was fitted.
- Fifty-three of 68 eligible onsets overlap another onset within plus/minus 28 days; only 15 are isolated. The 68 matched events come from 13 players, with the top five contributing 80.9%.
- Event windows generally show lower recorded-session rate, load and duration than calendar references. Player-equal intervals are wide and isolated-onset sensitivity commonly crosses zero, so these are unstable retrospective context patterns rather than predictive or causal evidence.
- Observed fatigue trends slightly higher and readiness lower near onsets, but wellness reporting itself differs between event and reference periods and same-day wellness remains descriptive-only under `DEC-031`.
- Executed the canonical script and notebook against GCS products; no cloud data was changed. Committed implementation and retained outputs at `e31e5ba`.
- Full quality gate passes: lockfile, formatting, Ruff, strict mypy and pytest (`71 passed`, one expected ZIP duplicate-name warning); notebook execution produced zero errors and the committed notebook remains output-free.
- Project owner approved the Stage 5 results and constrained interpretation on 2026-08-15.
- Accepted `DEC-034`: Stage 5 patterns remain non-predictive hypotheses; no predictor is promoted, removed or ranked from retrospective association; day-0 and same-day wellness remain descriptive-only; player concentration, overlap and isolated-event sensitivities remain required controls.
- Project owner approved the Stage 6 cohort and outcome sensitivity specification on 2026-08-15.
- Implemented Stage 6 as shared analysis code, canonical script, matching output-free notebook, 12 retained tables, nine retained charts and four focused tests.
- Rebuilt all nine combinations of 1/3/7-day episode-gap rules and 3/7/14-day horizons through production outcome functions. The accepted three-day labels reproduce all stored gold fields exactly across 36,550 player-days; horizon nesting has zero violations.
- Under the three-day gap, broad 7-day eligibility contains 35,992 player-days, 370 positive player-days and 71 represented onsets across 15 event-bearing players. The top five players contribute 74.6% of represented onsets.
- A 28-day burn-in retains 34,600 eligible days (96.1%) but 66 of 71 represented onsets and 13 of 15 event-bearing players. Fifty-six- and 90-day burn-ins retain 65 and 56 onsets respectively.
- Requiring seven strictly prior wellness reports retains 25,688 eligible days and 60 onsets; requiring seven reports within the prior 28 days retains 21,078 days and 56 onsets. These restrictions materially select the cohort.
- The robust load-baseline subset retains 25,951 eligible days and 55 onsets. The combined history subset retains 70.5% of broad eligible days and 54 onsets; it remains secondary rather than a primary-cohort default pending review.
- Isolated-onset status is implemented only as an outcome-support sensitivity and never as a prospective eligibility filter. No model or chronological split was created.
- Executed the canonical Stage 6 script and notebook against GCS products; no cloud data was changed. Committed implementation and retained outputs at `e719939`.
- Full quality gate passes: lockfile, formatting across 63 files, Ruff, strict mypy across 51 source files and pytest (`75 passed`, one expected ZIP duplicate-name warning); notebook execution produced zero errors and the committed notebook remains output-free.
- Project owner approved the Stage 6 results and recommended primary/secondary outcome-cohort policy on 2026-08-15.
- Accepted `DEC-035`: primary three-day episode gap, seven-day target and 28-day burn-in; no wellness or baseline eligibility gate; mandatory 3/14-day horizon, 1/7-day gap and broad no-burn-in sensitivities; isolated onset is never a prospective filter.
- Project owner approved the Stage 7 prospective protocol and leakage-audit specification on 2026-08-15; accepted `DEC-036`.
- Implemented shared Stage 7 code, canonical script, matching output-free notebook, 14 public tables, eight charts, report, manifest and four focused tests.
- Rebuilt 26 allowed prediction-time predictors across the F1-F3 ladder plus sRPE replacement sensitivity; F0 remains a no-predictor global-rate baseline.
- Strictly lagged wellness and prior robust features pass future-append invariance across 27,350 earlier rows; same-day wellness, identities, outcomes and future/follow-up fields are excluded.
- Frozen partitions contain 16,365 training, 8,690 validation and 8,845 final-test player-days, with 56, 5 and 5 represented onsets respectively; 700 player-days are deliberately embargoed.
- The final test was audited for support only and remains locked: no model, prediction, threshold or performance metric was produced.
- Stage 7 automated status is PASS with zero failures, one warning and three review findings: one rolling validation window has zero positives; two partitions have fewer than 10 represented onsets; 38 player holdouts have zero development positives; robust fatigue coverage is 8.4%.
- Executed canonical script and notebook against GCS; committed implementation and retained outputs at `9125b85`. Full gates pass: lock, 66-file formatting scope, Ruff, strict mypy across 29 source files and pytest (`79 passed`, one expected ZIP duplicate-name warning).

## Current Repository State

```text
jobs/analysis/              approved-stage script runners
notebooks/analysis/         matching output-cleared notebooks
outputs/analysis/           retained script-generated analysis artifacts
src/player_availability/    ingestion, outcomes, features, quality and configuration
tests/                      79 passing tests, including Stage 0 through Stage 7 tests
docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
docs/PROJECT_STATE.md
docs/DECISION_LOG.md
```

Active Stage 0 through Stage 7 assets follow the shared module/script/notebook/output contract. All notebooks are committed with no outputs or execution counts. The Stage 7 split protocol is frozen as retained metadata; no split-assigned cloud dataset or model exists. Historical commits remain available locally by design.

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
- Stage 4 read the compact GCS gold feature product but made no cloud-data changes; retained analysis artifacts are local under `outputs/analysis/04_feature_redundancy/`.
- Stage 5 read compact GCS silver episode and gold feature products but made no cloud-data changes; retained analysis artifacts are local under `outputs/analysis/05_outcome_context/`.
- Stage 6 read compact GCS silver injury/registry and gold feature products but made no cloud-data changes; retained analysis artifacts are local under `outputs/analysis/06_cohort_outcome_sensitivity/`.
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
- Target-blind Stage 4 structure shows extensive representation redundancy: load/session current values form one high-correlation group, rolling load representations form another, and prior player baselines remain structurally separate.
- Daily load and session sRPE are near-duplicate current and rolling representations, while session duration retains more distinct positive-session information. Adjacent rolling windows are all strongly correlated.
- Stage 5 retains 68 complete-history matched onsets from 13 players. Fifty-three overlap another onset within plus/minus 28 days, only 15 are isolated, and the top five players contribute 80.9% of matched events.
- Retrospective event windows show lower recording/load/duration context than same-player calendar references, but player-cluster intervals are wide and isolated-onset sensitivity often includes zero. This does not establish predictive value, causality or a feature-selection mandate.
- Wellness values and reporting behavior vary around onsets; current/same-day wellness remains outcome-entangled and descriptive-only under `DEC-031`.
- Stage 6 confirms outcome definition has major support consequences: 1/3/7-day gap rules yield 108/73/55 onset dates, while represented 7-day-horizon support is 108/71/47 onsets.
- For the three-day rule, 3/7/14-day horizons yield 190/370/601 positive player-days and 68/71/71 represented onsets. The seven-day horizon remains the provisional balance of lead time and support.
- History restrictions preserve all 50 players at most tested thresholds but reduce event-bearing-player and onset support. Wellness-rich or robust-baseline subsets would materially alter the represented outcome cohort.
- Objective/GPS data remains archive-only under the subjective-first decision.

## Current Modelling State

No model has been fitted. No chronological split is currently frozen. `DEC-027` is superseded by `DEC-028`. Stages 1 through 6 establish outcome, reporting-process, numerical-feature, structural-contract, retrospective-context and cohort-sensitivity integrity, while revealing low and concentrated event support, overlapping onsets, non-random reporting, zero inflation, calendar/team shifts, unstable z-score tails and substantial feature redundancy. They do not establish predictive value or generalisability. Baseline modelling is blocked until Stages 0 through 8 are completed and approved.

## Current Product State

No API, dashboard, product table or inference service is implemented. The intended product remains practitioner decision support, never diagnosis, clearance or participation advice.

## Locked Decisions

- `DEC-001` to `DEC-026` remain the accepted foundation except where explicitly superseded in the decision log.
- `DEC-027` is superseded and its former split is not active.
- `DEC-028` resets pre-model analysis to Stage 0 while preserving trusted data engineering and history.
- `DEC-029` defines the shared script/notebook implementation and output-storage contract.
- `DEC-030` defines player-date onset as the effective binary outcome event and constrains sensitivity, validation and claims.
- `DEC-031` defines missing-value semantics and a conservative lagged-only wellness/reporting policy for the primary predictor contract.
- `DEC-032` defines Stage 3 feature handling: preserve extremes, separate recording state from magnitude, carry justified `log1p` candidates, and exclude unstable existing z-scores from the primary operational contract.
- `DEC-033` defines the target-blind full-contract catalogue and compact provisional operational feature-family policy; the exact predictor allow-list remains unfrozen until Stage 7.
- `DEC-034` accepts Stage 5 only as constrained retrospective context evidence and authorises Stage 6 specification review without authorising implementation.
- `DEC-035` freezes the primary and secondary Stage 6 outcome/cohort policy and authorises Stage 7 specification review without authorising implementation.
- `DEC-036` freezes the Stage 7 predictor ladder, prohibited fields, chronological partitions and embargoes, development stress tests, train-only preprocessing, metrics, uncertainty and alert-capacity rules.
- Git remains local-only unless the project owner explicitly requests otherwise.
- Random row-level splitting is prohibited for headline evaluation.
- No objective/GPS processing begins during the subjective pre-model analysis programme.

## Open Decisions

- Approve or revise the Stage 7 results interpretation, including sparse temporal and unseen-player support limitations.
- Approve the Stage 8 pre-model readiness specification before implementation.

## Known Issues / Technical Debt

- No remote or CI workflow; this is consistent with the current local-only Git policy.
- Service-account naming remains unreconciled: `paa-build-sa` versus `paa-ci-sa` in older architecture text.
- Archive-bucket lifecycle rules and billing-budget alerts have not yet been verified.
- Effective outcome support is limited and highly concentrated by player, team and period; later protocol gates must constrain claims and stress-test generalisation.
- Prior-relative z-scores can become extreme when historical variance is near zero; the current fields must not enter a primary contract without an explicit robustness rule.
- Feature magnitudes and recording intensity differ by team and calendar period; later validation must measure temporal and player/team transfer sensitivity.
- The current and rolling daily-load and session-sRPE fields are near duplicates; carrying both as independent operational signals would inflate dimensionality without independent information.
- Full objective/GPS ingestion remains deliberately deferred.
- Validation and final-test partitions each represent only five onsets; inferential precision and model-selection capacity will be limited.
- One rolling-origin validation window has zero positive player-days, so it cannot support discrimination or calibration estimation and must remain a temporal stress window.
- Thirty-eight of 50 leave-one-player-out development folds have zero positive held-out days; unseen-player metrics require support-aware aggregation and cautious claims.
- The robust fatigue predictor is available on only 8.4% of primary-cohort days because discrete prior scores often have zero robust scale; F3 must remain an incremental sensitivity unless Stage 8 revises it.

## Blockers

No technical blocker. Stage 8 is process-blocked until the project owner approves the Stage 7 results interpretation and then approves the Stage 8 specification.

## Work In Progress

Stage 7 results review is open. Implementation and retained outputs are committed at `9125b85`; no other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Present and discuss Stage 7 protocol, leakage checks, predictor coverage and temporal/player support limitations.
2. Obtain project-owner approval, revision or rejection of the Stage 7 results interpretation.
3. If approved, present the Stage 8 pre-model readiness-report specification.
4. Do not implement Stage 8 before specification approval and do not fit a model before Stage 8 returns `READY`.

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Lockfile integrity | PASS | `poetry check --lock` |
| Lint | PASS | Ruff, all checks passed |
| Format | PASS | format check clean across 66 Python files |
| Type check | PASS | strict mypy, 29 source files |
| Tests | PASS | 79 passed; one expected duplicate-ZIP-member warning |
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
| Stage 3 results review | PASS | project-owner approval received 2026-08-14; policy accepted under `DEC-032` |
| Stage 4 specification | PASS | project-owner approval received 2026-08-14 |
| Stage 4 implementation | PASS | shared module, script, notebook, outputs and tests committed at `93a95fc` |
| Stage 4 automated integrity | PASS | 0 outcome columns used; 15 transforms valid; 0 hard failures |
| Stage 4 notebook execution | PASS | 4/4 code cells executed against GCS with zero errors; committed notebook remains output-free |
| Stage 4 results review | PASS | project-owner approval received 2026-08-15 local time; policy accepted under `DEC-033` |
| Stage 5 specification | PASS | project-owner approval received 2026-08-15 |
| Stage 5 implementation | PASS | shared module, script, notebook, outputs and tests committed at `e31e5ba` |
| Stage 5 automated integrity | PASS | 68/68 eligible onsets matched; zero failures or warnings; three review findings |
| Stage 5 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| Stage 5 results review | PASS | project-owner approval received 2026-08-15; interpretation accepted under `DEC-034` |
| Stage 6 specification | PASS | project-owner approval received 2026-08-15 |
| Stage 6 implementation | PASS | shared module, script, notebook, outputs and tests committed at `e719939` |
| Stage 6 automated integrity | PASS | all nine gap/horizon combinations rebuilt; zero failures or warnings; two review findings |
| Stage 6 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| Stage 6 results review | PASS | project-owner approval received 2026-08-15; policy accepted under `DEC-035` |
| Stage 7 specification | PASS | project-owner approval received 2026-08-15; protocol accepted under `DEC-036` |
| Stage 7 implementation | PASS | shared module, script, notebook, outputs and tests committed at `9125b85` |
| Stage 7 automated protocol/leakage audit | PASS WITH LIMITATIONS | zero failures, one warning, three review findings |
| Stage 7 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| Stage 7 results review | PENDING OWNER APPROVAL | sparse temporal, player and robust-feature support requires interpretation |
| Leakage/split gate | FROZEN PENDING RESULTS APPROVAL | exact partitions and embargoes retained; final-test performance locked |
| Modelling | NOT STARTED | no model fitted |

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v36, 2026-08-15T02:24:45Z | v36, 2026-08-15T02:24:45Z |
| `DECISION_LOG.md` | DEC-001 to DEC-036 | DEC-001 to DEC-036 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | stage-gated revision | stage-gated revision |

Status: **SYNCHRONISED**

Drive mirrors use stable file IDs and in-place updates. The state records `9125b85`, the committed tree before this control-document update; the commit containing the control update will be one commit later by design.
