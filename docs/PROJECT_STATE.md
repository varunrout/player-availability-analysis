# Player Availability Analysis - Project State

State Version: 60
Last Updated UTC: 2026-08-17T14:00:00Z
Coordination Session ID: PAA-IMPL-20260817-01
Git Branch: main
Git HEAD: 0955e86 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: V1 Delivery Programme - Phase V1-P6 Complete: Dashboard Deployed and Verified
Current Phase Status: `DEC-064` authorised the V1-P6 build (batch inference to `paa_product` plus a two-service Cloud Run dashboard). All four views are implemented, deployed and verified end to end against live data: squad overview, player detail, data quality and model health. Three post-deployment fixes were applied before the remaining views were built: the squad overview's operating-point banner was showing the flattering EXP-019 development burden without the worse V1-P5 held-out figure, now enforced by a copy-constraints test; the exposed review password was rotated via Secret Manager and the old version destroyed; the root `.gitignore` now explicitly covers Node build output. Verifying the redeployed dashboard end to end then surfaced a genuine data defect: the onsets-by-year table and player-detail onset markers showed zero onsets everywhere, because the frozen Stage 7 eligibility rule makes the onset day itself always ineligible for scoring, so a flag joined onto the scored predictions could never be true by construction. Fixed with a dedicated onset calendar read from `episode_start` directly, independent of scoring eligibility; both services were rebuilt and redeployed, and the fix was confirmed live (63 onsets in 2020 against 10 in 2021, matching `DEC-046`'s documented decline). No prior decision, champion, operating point or predictor contract changed. Phase V1-P7 is not begun.

## Current Objective

None outstanding. Phase V1-P6 is complete and deployed. Await direction on Phase V1-P7 (operationalisation) or the model card (V1-P8 groundwork).

## V1 Delivery Context

V1 is a complete subjective-data decision-support system whose primary evidence is methodological rigour and product completeness, not discrimination performance (`DEC-046`).

The binding constraint is outcome support: 66 represented onsets in the frozen cohort, split 56 in train, five in validation and five in final test, with 74.6% of onsets from five players and only 12 of 50 players carrying any event. Reported onsets fall roughly tenfold from 2020 to 2021 at flat player-days, tracking decaying self-report engagement rather than reduced injury incidence.

Phases, governed by section 5A of `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` and mapped onto experiment identifiers already registered there: V1-P1 calibration (EXP-009), V1-P2 Cox survival (EXP-007), V1-P3 boosted classification (EXP-008), V1-P4 champion selection, explanation stability and alert-budget utility (EXP-018 and EXP-019), V1-P5 pre-registration and single-use final test (governance gate), V1-P6 product, V1-P7 operationalisation, V1-P8 release evidence. No new experiment identifiers are allocated.

Deferred to V2: objective GPS ingestion (EXP-011, EXP-012), neural survival models (EXP-015), online serving, deriving operating-point probability thresholds from out-of-fold rather than in-sample predictions (`DEC-063`).

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
- Project owner approved the Stage 7 results interpretation on 2026-08-15; accepted `DEC-037` as `PASS WITH LIMITATIONS` and authorised Stage 8 specification review without authorising implementation or modelling.
- Project owner approved the Stage 8 readiness specification on 2026-08-15; accepted the binary hard-gate methodology under `DEC-038`.
- Implemented shared Stage 8 code, canonical script, matching output-free notebook, ten public tables, four charts, report, manifest and four focused tests.
- Consolidated 24 hashed evidence artifacts across Stages 0-7. All eight manifests are PASS, no retained findings register contains a failure and all eight notebooks are present and output-free.
- All 12 readiness hard gates pass. The report preserves 12 mandatory controls, including sparse temporal/player support, self-reported outcome semantics, missing wellness, F3 coverage, load/sRPE redundancy, one-time final-test access and non-deployment claims.
- Stage 8 provisionally recommends `READY` only for a narrow exploratory M0/M1 subjective-data baseline programme. The stage itself authorises no modelling and accessed no final-test performance.
- Executed canonical script and notebook locally against retained evidence; committed implementation and outputs at `7a17edd`. Full gates pass: lock, formatting across 69 Python files, Ruff, strict mypy across 30 source files and pytest (`83 passed`, one expected ZIP duplicate-name warning).

- Accepted the Stage 8 `READY` recommendation and M0 specification under `DEC-039`; synchronised local and Drive control documents before modelling.
- Added versioned M0 configuration, shared modelling code, canonical EXP-002 job, matching output-free notebook and four focused tests.
- Implemented global training-prevalence and training-only 95th-percentile seven-day recent-load baselines, with no arbitrary ranking for the constant baseline.
- Added validation Brier, log loss, average precision, ROC-AUC, 1%/2.5%/5% alert simulation, represented-onset capture, lead time and support-aware player/week bootstrap uncertainty.
- Executed EXP-002 against actual GCS gold/silver products: 16,365 training and 8,690 validation player-days; 28 validation positive days and five represented validation onsets.
- Global prevalence validation results: Brier 0.003405, log loss 0.030310, average precision 0.003222 and ROC-AUC 0.500000.
- Recent-load validation results: Brier 0.003544, log loss 0.032241, average precision 0.002934 and ROC-AUC 0.477210; zero of five onsets captured at all frozen alert budgets.
- Verified 500 player-cluster and 500 temporal-week bootstrap requests per baseline/metric; undefined zero-positive AP resamples are counted and excluded from interval estimation rather than silently scored.
- Visually reviewed all six retained charts and replaced empty zero-capture plots with explicit no-capture states.
- Committed implementation and retained outputs at `28a4b3b`. Final-test rows were support-counted only; zero final-test predictions or performance metrics were created.
- Full quality gate passes: lockfile check, Ruff, strict mypy across 58 source files, pytest (`87 passed`, one expected duplicate-ZIP-member warning), actual-data notebook execution and output-free notebook verification.
- Accepted the exact EXP-003 M1-F1 development specification under `DEC-041`.
- Added bounded scikit-learn/joblib dependencies, the frozen configuration, shared train-only preprocessing/evaluation modules, canonical job, matching output-free notebook and three focused tests.
- Executed M1-F1 against actual GCS gold/silver development data. The selected `C=0.001` model evaluates 8,690 validation player-days, 28 positive days and five represented onsets; zero final-test predictions or performance metrics were created.
- Validation M1-F1 results: Brier 0.003700, log loss 0.031272, average precision 0.016640 and ROC-AUC 0.807802. Ranking improves over M0, while probability accuracy is worse than M0 Brier 0.003405.
- Raw mean prediction is 2.005% versus 0.322% observed prevalence; calibration intercept is -0.374 and slope 1.422. No post-hoc calibrator was fitted or selected.
- Alert simulation captures 0/5, 2/5 and 4/5 represented onsets at 1%, 2.5% and 5% review rates. The latter two require approximately 107 false alerts per captured onset.
- Rolling-origin AP is 0.1994, 0.0310 and 0.0427 in three estimable folds; the fourth has zero positive validation days. Support-aware unseen-player aggregate AP is 0.0233, but only 12/50 held-out players contain positive days.
- Generated the retained report, 17 tables, nine visually reviewed figures, model/prediction artifacts and metadata. Committed public implementation and retained evidence at `146edcc`.
- Full quality gate passes: lockfile, formatting across 80 Python files, Ruff, strict mypy across 63 source files, pytest (`90 passed`, one expected duplicate-ZIP-member warning), actual-data notebook execution and output-free notebook verification.
- Owner selected `PROMOTE` for M1-F1 on 2026-08-15; accepted `DEC-042`. Promotion means reference-candidate advancement only, not deployment or acceptance of raw calibration.
- Authorised cumulative F2 (17 predictors) and F3 (23 predictors) development evaluation with unchanged cohort, partitions, preprocessing, logistic model, regularisation grid, metrics, stress tests and final-test lock.
- Generalised the proven F1 engine to exact cumulative 9/17/23-predictor F1/F2/F3 contracts while preserving F1 outputs and leakage controls.
- Added the canonical feature-ladder configuration/job, matching output-free notebook, consolidated report, nine reviewed charts, paired uncertainty and three focused tests.
- Executed the ladder against actual GCS development data. All three models selected `C=0.001`; zero final-test predictions or performance metrics were created.
- F2 does not improve F1: Brier 0.003713 versus 0.003700, log loss 0.031378 versus 0.031272, AP 0.016377 versus 0.016640 and identical onset capture at all frozen budgets. Paired Brier intervals consistently favour F1.
- F3 leads held-period point estimates: Brier 0.003613, log loss 0.030367, AP 0.019432 and ROC-AUC 0.851053. It captures 1/5 onsets at 1%, 2/5 at 2.5% and 4/5 at 5% review rates.
- F3 raw mean prediction remains high at 1.965% versus 0.322% observed; calibration intercept is -0.356 and slope 1.433. No calibrator was fitted or selected.
- F3 paired week-block Brier improvement over F2 excludes zero, but player-cluster Brier/AP and week-block AP intervals include zero. Rolling AP improves in RO1/RO3 but declines in RO2; one later fold has zero positives.
- Unseen-player aggregate ranking does not improve: F1 AP/ROC-AUC 0.023316/0.642578 versus F3 0.022308/0.630928, with only 12/50 estimable held-out players.
- Committed implementation and retained evidence at `226224c`. Full gates pass: lockfile, formatting across 83 Python files, Ruff, strict mypy across 65 source files, pytest (`93 passed`, one expected ZIP warning), actual-data notebook execution and output-free notebook verification.

State v45 to v46, under coordination session `PAA-CTRL-20260815-02`.

- Independently re-ran every quality gate from a clean Linux environment built to the declared constraints, rather than accepting the recorded status. All five reproduce exactly: Ruff clean, format clean across 83 files, strict mypy clean across 65 source files, `93 passed` with one expected ZIP warning, and `poetry check --lock` passing.
- Verified local and Drive control documents agree on state version, timestamp, coordination session, Git reference and decision range `DEC-001` to `DEC-042`. No reconciliation was required.
- Diagnosed 27 persistently modified files as pure CRLF churn: 1051 insertions against 1051 deletions with an end-of-line-insensitive diff returning empty. No content had changed and no work was at risk.
- Accepted `DEC-045`: adopted an explicit LF line-ending policy with binary protection for Parquet, model artefacts and images; renormalised the repository at `df735d5`, settling all 27 files with no content change.
- Accepted `DEC-043`: rejected F2 on evidence that its Brier intervals exclude zero in the wrong direction under both resampling schemes; promoted F3 as the raw M1 development candidate at owner direction.
- Recorded five binding limitations against the F3 promotion: five-onset support, the unseen-player reversal against F1, rolling-origin instability, only one of four paired intervals excluding zero, and the 8.4%-coverage robust fatigue predictor entangled with reporting structure. These must accompany every downstream citation of F3.
- Accepted `DEC-044`: authorised `EXP-009` raw/Platt/isotonic calibration on F3, development data only, with the power limitation binding and "no method distinguishable at this support" recorded in advance as an acceptable and expected result.

State v46 to v47, under coordination session `PAA-CTRL-20260815-02`.

- Diagnosed the outcome-support constraint as a temporal property of the dataset rather than a split-design fault: onsets fall from 56 in 2020 to five and five in the two 2021 partitions while player-days remain flat, consistent with the Stage 2 reporting-engagement evidence.
- Established that no cohort adjustment resolves this. Moving to a one-day episode gap would raise total onsets from 73 to 108, which does not change the inferential situation materially.
- Accepted `DEC-046`: defined V1 as a complete subjective-data decision-support system whose headline evidence is methodological rigour and product completeness, not discrimination performance. Scope covers calibration, Cox survival, a gradient-boosting complexity test, explainability, batch inference, a Cloud Run dashboard, model card, CI, containerisation, one single-use final-test evaluation and portfolio artefacts. GPS, neural survival and online serving are deferred to V2.
- Accepted `DEC-047`: pooled rolling-origin evaluation becomes the headline, superseding `DEC-036` in respect of headline designation only. All frozen partitions, embargoes, contracts, preprocessing scope and the final-test lock remain in force.
- Accepted `DEC-048`: retained the three-day episode gap as primary and pre-registered the one-day gap as a mandatory sensitivity on every V1 headline result, rejecting a switch that would have been selection on the outcome.
- Specified the V1 delivery programme: eight phases with specification and results gates, an explicit definition of done, sequencing rules, scope-control cut order and a risk register.
- Specified the EXP-009 calibration experiment: raw against Platt against isotonic on F3, eight automated integrity checks, the mandatory sparse-predictor availability audit and binding power-limitation reporting rules.

State v47 to v48, under coordination session `PAA-CTRL-20260815-02`.

- Corrected a documentation-architecture error introduced in v47. The V1 plan and EXP-009 specification had been written as two new files and mirrored to Drive as non-numbered documents, breaking the established convention that specifications live inside `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`.
- Two concrete faults were identified: doc 19 section 5 D1 already specified EXP-009 with the same three calibration arms, creating a second source of truth; and the new phase plan allocated EXP-010 through EXP-013, all four of which were already assigned to leave-one-player-out, the GPS pilot, objective-data ablation and team transfer.
- Accepted `DEC-050`: folded the EXP-009 specification into doc 19 section 5 D1 and the V1 delivery programme into a new doc 19 section 5A; remapped V1 phases onto existing identifiers so none are newly allocated; deleted both files from the repository and trashed both Drive copies.
- Accepted `DEC-049`: calibrators are fitted fold-wise within the pooled rolling-origin structure, with fitting partitions always disjoint from evaluation partitions. This supersedes `DEC-036` in respect of the calibrator-fitting rule only and replaces doc 19's earlier validation-only rule, which predated `DEC-047` and would have fitted a calibrator on five onsets while reporting under a rolling-origin headline.
- Refreshed doc 19 section 8, which still carried the pre-Stage-0 checklist, to reflect the current position.
- Added doc 19 to the mirrored document set, since it now carries specification content that must stay synchronised.

State v48 to v49, under coordination session `PAA-IMPL-20260816-01`.

- Reconciled a stale reference in this document that survived the `DEC-050` cleanup: the V1-plan bullet still named a deleted file. Corrected it to describe the V1 delivery programme, committed alone at `76f4b08`, and re-verified that all three mirrored documents hash-match under LF normalisation.
- Reconciled the Git HEAD field. State v48 recorded `838ad00`; the tree had since advanced two commits through `2420e03` (doc-19 consolidation) and `c44dd69` (machine-local tool settings ignore), then `76f4b08` (the V1-plan reference correction). The state now records `76f4b08` as the pre-state-update tree.
- Project owner approved the V1 delivery programme in doc 19 section 5A and the `EXP-009` calibration specification in doc 19 section 5 D1, both as drafted with no amendments; accepted `DEC-051`. This closed the single open decision carried in state v48 and authorised phase V1-P1 implementation against development data only, with the final-test lock and V1-P2/V1-P3 authorisation explicitly unaffected.
- Recorded a known ordering conflict between doc 19 section 5 and section 5A on the placement of `EXP-007` and `EXP-008` relative to operational-utility analysis. It requires a superseding decision before phase V1-P2 and does not affect V1-P1.

State v49 to v50, under coordination session `PAA-IMPL-20260816-01`.

- Implemented and executed `EXP-009` at `fddb55e`: development-only raw, Platt and isotonic calibration comparison on F3, fitted fold-wise on inner cross-validated out-of-fold training probabilities disjoint from every evaluation fold. Pooled rolling-origin support was 104 positive player-days across three estimable folds, one zero-positive fold excluded. Raw led every pooled metric; paired Brier intervals excluded zero against both calibrated arms under both resampling schemes, unfavourable to calibration. The mandatory sparse-predictor audit found discrimination diverges sharply by availability of the robust fatigue z-score: ROC-AUC 0.732 observed against 0.908 absent.
- Project owner reviewed the `EXP-009` result and accepted `DEC-052`: selected raw probabilities for the M1 candidate, with no post-hoc calibrator adopted; separately authorised `EXP-016` to test whether F3's advantage is carried by the robust fatigue predictor's availability pattern rather than its value, to run before phase V1-P2. `DEC-052` does not reopen `DEC-043`.
- Project owner accepted `DEC-053`, resolving the doc 19 section 5 / section 5A ordering conflict: section 5A governs V1 sequencing, and `EXP-007`/`EXP-008` proceed at V1-P2/V1-P3 ahead of the V1-P4 operational-utility work.
- Expanded doc 19 section 5 E3 with the full `EXP-016` specification (four arms, evaluation protocol, `ABL-01` to `ABL-07` integrity checks, decision gate) and revised the section 5 "Model ladder advancement" intro to note the `DEC-053` supersession.
- Implemented and executed `EXP-016` at `e624ffe`: development-only four-arm ablation under the frozen F3 engine and raw probabilities. Arm A is F3 as promoted; arm B removes the robust fatigue value and its indicator entirely; arm C removes the value but retains the indicator; arm D is F1 as an external reference. Support-aware unseen-player generalisation was computed for every arm; arms A and D reproduce the `DEC-043` reference figures exactly (F3 AP 0.022308/ROC-AUC 0.630928; F1 AP 0.023316/ROC-AUC 0.642578), confirming correctness.
- `EXP-016` found: arm C (indicator retained, value removed) is not distinguishable from arm A on pooled metrics (paired intervals include zero) and narrows part of the unseen-player gap to F1 (AP gap 0.001008 to 0.000816; ROC-AUC gap 0.011651 to 0.011356). Arm B (predictor removed entirely) is worse than arm A on unseen-player generalisation (AP 0.020427, ROC-AUC 0.617042). Neither B nor C decisively closes the F1 gap or beats A on calibrated probability quality at this support. Whether `DEC-043` is reopened is recorded as a project-owner decision still pending, not resolved by this state revision.

State v50 to v51, under coordination session `PAA-IMPL-20260816-01`.

- Project owner reviewed the `EXP-016` tables directly and accepted `DEC-054`: reopened `DEC-043` in respect of candidate selection and selected F1 as the V1 champion. Arm C dominates arm A on Brier, average precision and ROC-AUC across the fixed window, pooled and unseen-player views while removing a predictor; the continuous robust fatigue z-score contributes nothing measurable beyond its availability indicator; and under `DEC-047`'s pooled rolling-origin headline F1 leads F3 on average precision (0.0967 against 0.0791) and on both unseen-player metrics, restating the reversal `DEC-043` had bound as a limitation. No arm difference is statistically distinguishable; the selection rests on dominance and the lapsed basis for F3's original promotion, not on significance.
- Expanded doc 19 section 5 "Model ladder advancement" with the `EXP-007` specification as F1: Andersen-Gill counting-process Cox model over the F1 champion's nine predictors, gap-time clock, Efron ties, Breslow baseline hazard converted to a seven-day probability, `COX-01` to `COX-08` integrity checks, decision gate requiring both resampling schemes to exclude zero before adoption.
- Implemented and executed `EXP-007` at `a73c46d`, adding a bounded `lifelines` dependency. The installed lifelines version implements neither cluster-robust sandwich variance nor Schoenfeld residuals for time-varying counting-process fits; this is disclosed rather than worked around, coefficient standard errors are model-based rather than cluster-robust, and a covariate-by-log-time interaction likelihood-ratio test substitutes for the Schoenfeld check. The paired bootstrap against F1 is treated as primary inferential evidence per the specification's own instruction for when methods disagree.
- `EXP-007` pooled rolling-origin result: Cox Brier 0.005929 against F1 0.006325 (paired interval excludes zero under temporal week-block resampling, [-0.000738, -0.000100], but not under player-cluster resampling, [-0.000728, 0.000028]); Cox average precision 0.0755 against F1 0.0967 and ROC-AUC 0.7113 against 0.8355, neither distinguishable (both paired intervals include zero). The pre-registered decision gate requires both schemes to exclude zero before adoption; Brier does not meet this bar.
- `EXP-007` unseen-player result, the axis `DEC-054` was decided on: Cox substantially leads F1, AP 0.104533 against 0.023316 and ROC-AUC 0.817861 against 0.642578, both computed on the same 12/50 estimable held-out players used throughout. This is not formally paired-bootstrapped per the specification, is reported at face value with the model-based-variance caveat, and is a material input to the V1-P2 gate review despite not meeting the pooled decision-gate bar on its own.

State v51 to v52, under coordination session `PAA-IMPL-20260816-01`.

- Project owner identified the `EXP-007` unseen-player advantage as internally inconsistent: leave-one-player-out is the hardest evaluation, yet Cox scored highest there while F1 showed the expected ordering. A pre-registered diagnostic reset the gap-time clock for every held-out player to post-burn-in study origin, holding the same fitted models, folds, cohort and predictors fixed. Unseen-player AP fell from 0.104533 to 0.019293 and ROC-AUC from 0.817861 to 0.576890, both below F1, and Cox's view ordering returned to the expected pattern. This confirmed the leakage hypothesis under the criterion specified in advance: the baseline hazard is highest at short gap times, so indexing a held-out player by their own onset history supplies outcome information a genuinely unseen player would never expose.
- Hardened the `EXP-007` evidence at `6dfd121`, folding the reset-clock evaluation into the module as a permanent second unseen-player arm rather than a scratchpad diagnostic. `reset_clock` is now reported as the valid leave-one-player-out result; `own_clock` is retained and explicitly labelled a leakage diagnostic contrast, never a competing headline figure. Added `COX-09`, requiring both clock variants be reported and neither use held-out outcome history in the time coordinate. Added a note to the doc 19 `EXP-007` specification recording the gap-time constraint for future survival work, including `EXP-014` in V2.
- Accepted `DEC-055`: rejected the survival framing for V1 on three grounds. First, the diagnostic collapse. Second, the pooled Brier advantage is an underprediction artefact, not better probability quality: Cox mean prediction 0.0026 against observed 0.0062 (under by 2.4x), log loss 0.1301 against F1's 0.0420 (three times worse). Third, the pre-registered gate was not met on its own terms: the paired Brier interval excludes zero under temporal week-block resampling only, not player-cluster; AP and ROC-AUC exclude zero under neither. `EXP-007` is closed with an evidence-backed negative conclusion; F1 remains champion. This is the second pre-registered audit in the V1 programme to overturn an apparently favourable result, after `EXP-016`.
- Expanded doc 19 section 5 "Model ladder advancement" with the `EXP-008` specification as F2: `HistGradientBoostingClassifier` over the F1 champion's nine predictors, pre-registered 16-point hyperparameter grid, iteration count selected by early stopping against the fixed chronological validation partition, `BST-01` to `BST-09` integrity checks (`BST-09` added given the `EXP-007` leakage class), decision gate requiring both resampling schemes to exclude zero before adoption.
- Implemented and executed `EXP-008` at `0044fe7`. Selected configuration: `max_leaf_nodes=7`, `learning_rate=0.01`, `min_samples_leaf=200`, `l2_regularization=10.0`, `max_iter=50` (early-stopped from a ceiling of 500). Primary preprocessing matches F1's median imputation exactly; a native-missing-handling arm is reported separately as a missingness sensitivity, not a complexity result.
- `EXP-008` pooled rolling-origin result: boosted Brier 0.006143 against F1 0.006325, paired interval excludes zero under both resampling schemes, player-cluster [-0.000365, -0.000046] and temporal week-block [-0.000274, -0.000096], favouring boosted. Boosted average precision 0.0861 against F1's 0.0967 and ROC-AUC 0.7887 against 0.8355; the paired AP interval excludes zero under temporal week-block resampling only, [0.002505, 0.055392], not under player-cluster resampling, [-0.031632, 0.094831]. The pre-registered gate requires both schemes to exclude zero; AP does not meet this bar, Brier does.
- `EXP-008` training-to-validation gap: training average precision 0.256236 against validation 0.013013, a roughly twentyfold drop and the clearer overfitting signature than the Brier-based flag alone, since Brier's absolute scale is not comparable across differently-prevalent train and validation periods. Unseen-player result: boosted AP 0.026889 against F1's 0.023316 (boosted ahead) but ROC-AUC 0.554999 against F1's 0.642578 (boosted behind), both on the same 12/50 estimable players; no inverted evaluation-view ordering of the kind found in `EXP-007`, consistent with `BST-09` since boosted classification has no time-coordinate concept for that leakage class to recur in.

State v52 to v53, under coordination session `PAA-IMPL-20260816-01`.

- During `EXP-008` gate review, identified a defect in the paired bootstrap for average precision: `paired_prediction_bootstrap_differences` resampled a single shared population for both Brier and average precision, but the average-precision point estimate is computed only on the discrimination-eligible subset with zero-positive folds excluded (per `CAL-08`). The mismatch let a bootstrap median contradict its own point-estimate difference, most visibly `EXP-008`'s boosted-vs-F1 average precision (point difference -0.010602 against a week-block median of +0.026475) and `EXP-009`'s isotonic-vs-raw claim cited in `DEC-052` (point difference -0.000349 against a week-block median of +0.019740). Brier intervals were unaffected throughout, since Brier's point estimate already uses the full pooled population.
- Corrected at `230a571`: added a `metrics` parameter to `prediction_bootstrap_intervals` and `paired_prediction_bootstrap_differences` so each metric bootstraps on the population matching its own point estimate, and added `paired_bootstrap_agrees_with_point_estimate` as a shared `BOOT-01` check with a small dead-zone epsilon so ordinary noise on a razor-thin, effectively-zero difference is not flagged as a mismatch. Applied across all four affected modules (calibration, ablation, survival, boosting) and added `BOOT-01` to each findings table. Regenerated retained evidence for `EXP-009`, `EXP-016`, `EXP-007` and `EXP-008` against live GCS; point estimates were unchanged throughout, since the defect was confined to the bootstrap.
- Checked the pre-registered stop condition before proceeding: corrected `EXP-008` average-precision intervals are player-cluster [-0.052406, 0.019850] and temporal week-block [-0.105518, 0.029223], both including zero. Neither excludes zero in boosted's favour under either scheme, so the stop condition did not trigger.
- Accepted `DEC-056`: rejected boosted classification for V1. Corrected pooled average precision is 0.086066 against F1's 0.096668, not distinguishable under either resampling scheme. Brier favours boosted with both intervals excluding zero, [-0.000365, -0.000046] and [-0.000274, -0.000096], and is judged a genuine edge rather than an `EXP-007`-style underprediction artefact, but it stands against a worse calibration slope (2.537922 against 2.019474) and worse discrimination on three of four views (pooled ROC-AUC 0.788733 against 0.835537; unseen-player ROC-AUC 0.554957 against 0.642578); the gate requires calibrated performance to improve, not one component of it. The training-to-validation average-precision gap (0.256 against 0.013) is the pre-registered expected overfitting signature. `EXP-008` is closed; F1 remains champion; phase V1-P4 is authorised.
- `DEC-056` superseded `DEC-052`'s average-precision claim: the corrected isotonic-vs-raw week-block interval is [-0.036918, 0.017755], including zero. `DEC-052`'s calibration selection, which rested on Brier and log loss, both sound, is unaffected. Neither `DEC-054` nor `DEC-055` depended on an average-precision interval and both stand unchanged.
- Noted, not yet resolved by a decision: regenerated `EXP-009` evidence now shows `BOOT-01` failing on the raw-vs-isotonic average-precision comparison under player-cluster resampling. The point difference is -0.000349, effectively zero, and the two resampling schemes disagree on its sign even on the corrected, population-matched estimator. This reads as "no calibration method distinguishable at this support", the pre-registered acceptable outcome under `DEC-044`, rather than a residual defect, but `EXP-009`'s automated status is presently `FAIL` on `BOOT-01` alone and this has not been recorded in a decision.

State v53 to v54, under coordination session `PAA-IMPL-20260816-01`.

- Accepted `DEC-057`: `BOOT-01`, introduced under `DEC-056`, required sign agreement even where the paired interval included zero, no direction claimed, treating an arbitrary sign on a razor-thin difference as a failure. Reformulated to require sign agreement only where the interval excludes zero; the dead-zone epsilon interim fix is removed as a tuned constant superseded by a principled interval condition. Kept the synthetic two-player fixture's `BOOT-01` exemption, with a comment recording that a two-cluster fixture cannot support the property, not that the check itself is unreliable.
- Separately, `DEC-057` extended `EXP-009` under its existing identifier with F1 raw, Platt and isotonic arms, since `DEC-054` replaced F3 with F1 as champion after `EXP-009` had already run, leaving F1's calibration claim untraceable to a measured result. F3's raw, Platt and isotonic arms are retained as historical reference; no new experiment identifier was allocated, per the `EXP-003` precedent of multiple feature sets under one identifier.
- Applied the `BOOT-01` reformulation across all four affected modules (calibration, ablation, survival, boosting) and regenerated retained evidence for `EXP-009`, `EXP-016`, `EXP-007` and `EXP-008` against live GCS at `78f579f`; all four pass `BOOT-01` under the reformulated wording. Point estimates were unaffected throughout, since the change is confined to the bootstrap sign-agreement check.
- `EXP-009` F1 result: raw Brier 0.006325, log loss 0.042009, calibration slope 2.019474, mirroring F1's earlier uncalibrated figures exactly. Platt Brier 0.007765 and isotonic Brier 0.007509, both worse than raw; log loss 0.044835 and 0.062091, both worse. Platt pulls calibration slope to 1.044271 and isotonic to 0.128850 (overshooting into under-confidence), but the Brier cost excludes zero under both resampling schemes for isotonic (player-cluster [0.000320, 0.002238], temporal week-block [0.000775, 0.001660]) and under temporal week-block resampling for Platt ([0.000844, 0.002004]; player-cluster includes zero, [-0.000004, 0.003681]). Average-precision intervals for both comparisons include zero under both schemes. `EXP-009`'s F3 conclusion is unchanged: no calibration method is distinguishable from raw at this support.
- Checked the pre-registered stop condition before proceeding: no F1 calibration method improved Brier or log loss at all (all four figures are worse than raw), so the interval-exclusion condition was moot and the stop condition did not trigger.
- Accepted `DEC-058`: selected raw probabilities for the F1 champion. No post-hoc calibrator is adopted for V1; the finding that no calibration method is distinguishable from raw at this support is now recorded against the champion itself rather than transferred by argument from the superseded F3 candidate. The binding constraint remains 104 pooled positive player-days fitted fold-wise, a property of the cohort rather than of any candidate, and the result reproduces the pattern already recorded for F3 under `DEC-052`. The probability transform is now frozen ahead of V1-P5. Phase V1-P4 begins against raw F1.

State v54 to v55, under coordination session `PAA-IMPL-20260816-01`.

- Identified that `DEC-058`'s rejection of Platt scaling was internally inconsistent with the record's own stated inferential rule: a difference is claimed only where the paired interval excludes zero under both resampling schemes, but Platt's Brier cost was cited without meeting that bar. The player-cluster interval [-0.000004, 0.003681] includes zero; only the temporal week-block interval [0.000844, 0.002004] excludes it. F3's equivalent Platt-vs-raw Brier intervals, by contrast, cleared both schemes ([0.000037, 0.002358] and [0.000553, 0.001306]), which is why `DEC-052`'s parallel reasoning was sound. Isotonic's rejection is unaffected: its Brier degradation excludes zero under both schemes.
- Accepted `DEC-059`: the selection made in `DEC-058` stands unchanged, raw F1 probabilities with no post-hoc calibrator, but its rationale is superseded. The corrected grounds are calibration-in-the-large: Platt's mean prediction moves from 0.023012 to 0.027420 against an observed rate of 0.006185, so overprediction rises from roughly 3.7x to roughly 4.4x, and log loss degrades from 0.042009 to 0.044835, an unqualified point difference since log loss is not bootstrapped anywhere in this experiment suite. No code, evidence, figure or report was regenerated; this is a rationale correction recorded against already-measured figures.
- `DEC-059` records a standing symmetry rule: the two-scheme interval-exclusion requirement applies equally to costs and to benefits, so a cost may not be treated as established on weaker evidence than a benefit would require for adoption. It also records the absence of uncertainty intervals for log loss, calibration slope and calibration intercept as a known limitation of the current uncertainty suite, to be stated in the model card.
- Process note: `DEC-057` was committed alongside its implementation and regenerated evidence at `78f579f` rather than in a control-only commit; going forward, decision records and `PROJECT_STATE.md` updates are committed in the control-update commit only, separate from implementation and evidence commits.

State v55 to v56, under coordination session `PAA-IMPL-20260816-01`.

- Accepted `DEC-060`: closed the V1-P4 champion selection gate. The V1 champion is F1 reporting raw probabilities across its nine frozen predictors; no further candidate is evaluated in V1. Authorised `EXP-018` (explanation stability) and `EXP-019` (alert-budget simulation), development data only. Adopted top-N-per-team-day as the product-facing dashboard operating point; the frozen `DEC-036` 1%/2.5%/5% review rates remain the cross-experiment comparison basis and are not superseded, and both views are reported side by side from the same predictions. Doc 19 section 5 D2 was replaced with the full `EXP-019` specification and section 5 D3 added the new `EXP-018` specification.
- Implemented and executed `EXP-019` at `a66e812`: raw F1 pooled rolling-origin predictions (support 104 pooled positive days, three estimable folds, one zero-positive fold, matching `EXP-009`'s F1 support exactly) translated into top 1/3/5-per-team-day, 1%/2.5%/5% and a 5%/10%/20% capacity-sensitivity view, all from the same prediction set. Live results: top-3-per-team-day and the 5% percentile view both capture 72.2% of represented onsets (recall) at 2,022 and 841 alerts respectively; top-1-per-team-day captures 50.0% at 674 alerts; the 1% percentile view captures only 11.1% at 169 alerts. False-alert burden rises steeply with N and with review rate, from 34.8 false alerts per captured onset at 2.5% to 253.9 at top-5-per-team-day. `ALERT-01` to `ALERT-06` all pass; one-day-gap sensitivity is present.
- Implemented and executed `EXP-018` at `a66e812`: F1 coefficient sign, magnitude and rank stability measured across 4 estimable rolling-origin folds and 50 estimable leave-one-player-out folds (54 total fold-fits). Attribution is exact: summed per-predictor contributions plus intercept reproduce the model's own logit to zero floating-point error (`EXPL-03`). 8 of 9 predictors hold constant coefficient sign across every estimable fold; only `daily_load_log1p` does not, and it also carries the smallest coefficient magnitude of the nine. For 104 flagged (actually positive) player-days evaluable under both a rolling-origin and a leave-one-player-out fit, the top-3 positive-contributor sets agree with mean Jaccard overlap 0.899 (range 0.2 to 1.0). `EXPL-01` to `EXPL-05` all pass.
- Checked the pre-registered stop condition: a majority of the nine predictors (5 or more) would need unstable sign to trigger it; only 1 does, so the stop condition did not trigger. No further decision record is required for either result, per the standing instruction that these are measurements feeding V1-P6, not adopt-or-reject gates.
- Noted, not load-bearing: `DEC-059` was recorded with a Date field of 2026-08-16; it was in fact recorded on 2026-08-17. The date is not load-bearing to the decision's content and no superseding record is required.

State v56 to v57, under coordination session `PAA-IMPL-20260816-01`.

- Accepted `DEC-061`: project-owner review of the already-measured `EXP-019` evidence found every top-N-per-team-day operating point dominated by a percentile point over 16,815 pooled rolling-origin player-days and 18 represented onsets. Top-1 (674 alerts, 9 captured, 71.1 false/captured) is beaten on both axes by the 2.5% rate (421 alerts, 11 captured, 34.8 false/captured). Top-3 and top-5 (2,022 and 3,370 alerts) capture the same 13 onsets as the 5% rate (841 alerts) at 2.4x and 4.0x its false-alert burden respectively.
- `DEC-061` supersedes `DEC-060` in respect of the product-facing operating point only; the champion freeze and the `EXP-018`/`EXP-019` authorisations stand. The dashboard now separates display from alerting: a daily ranked squad view per team (display ordering, issues no alert) and a percentile alerting rule (2.5% default, 5% selectable, both display their measured false-alert burden inline). Top-N is retained nowhere as an alerting rule. The 1% rate is not offered: its 80.5 false-alerts-per-captured-onset burden exceeds the 2.5% rate's, a non-monotonicity attributed to the 18-onset support rather than to the ranking itself.
- No code, evidence, figure or report was regenerated; `EXP-019`'s existing measurements already covered every operating point named in `DEC-061`.

State v57 to v58, under coordination session `PAA-IMPL-20260816-01`.

- Accepted `DEC-062`: pre-registered the V1-P5 final-test specification and committed it alone at `650f67e1883b655124324219c20cca09f19c3eba`, before any evaluation code existed, so that the commit history is itself the evidence the claims predated the numbers. Registered: the model artefact (F1 refit once on the full development partition, raw probabilities, nine frozen predictors), exactly eight metrics, the `DEC-061` 2.5%/5% operating points with thresholds to be derived from development and frozen before the final-test read, three falsifiable claims (C1 ranking above chance, C2 overprediction in the large of roughly the development order, C3 high false-alert burden of the development order), and a power statement stating this is a confirmatory sanity check on five represented onsets, not a performance claim, before any result existed.
- Before writing any final-test code, raised one genuine ambiguity the pre-registration left open — whether the frozen operating-point thresholds should come from the final artefact's own in-sample development predictions or from `EXP-019`'s existing out-of-fold pooled predictions — and stopped to ask rather than resolve it. The project owner selected in-sample: the final artefact's own predictions on the development rows it was fit on.
- Implemented the V1-P5 governance gate (no `EXP-` identifier; a governance gate, not an experiment) per `DEC-029`, matching the `exp_009` layout. Development-only unit tests (113 passing) exercised the full code path against synthetic fixtures before any live read.
- Executed once against live GCS at `a27eced`: fit F1 on the 25,055-player-day development partition (train plus validation, respecting the existing embargo), froze the 2.5%/5% thresholds from that model's own in-sample development predictions, then read the final-test partition exactly once. Final-test support: 8,845 player-days, 35 positive days, 5 represented onsets, matching `DEC-062`'s stated context exactly.
- Result: ROC-AUC 0.827204 (**C1 supported**); mean prediction 0.014824 against observed rate 0.003957, a 3.7x overprediction reproducing the development finding exactly (**C2 supported**); false alerts per captured onset at the 2.5% rate is 135.0, outside the registered "tens" order and worse than development, not better (**C3 not supported**). `FINAL-01` to `FINAL-07` all pass; the notebook is committed output-free and was deliberately not executed against live GCS, since doing so would read the final-test partition a second time without a superseding decision — its logic is instead verified by the unit test against the identical code path on development-only fixtures.
- No result changes the champion, the operating points, the predictor contract or any prior decision, per `DEC-062`. The result is a confirmatory sanity check and may not be cited as a performance claim in the model card, README, case study, portfolio material or interview narrative.

State v58 to v59, under coordination session `PAA-IMPL-20260816-01`.

- Accepted `DEC-063`: diagnosed the V1-P5 C3 shortfall entirely from evidence already committed, no re-run or second final-test access. Two compounding, non-champion causes account for it arithmetically. First, onset density on the final-test partition (5 onsets across 8,845 player-days, 0.565 per thousand) is roughly half development's (18 across 16,815, 1.071 per thousand) — the same reporting-engagement decay documented since Stage 2 and quantified under `DEC-046`. Second, the in-sample-derived probability threshold (0.033831) realised a 4.737% alert rate on held-out data rather than the intended 2.5%, issuing 419 alerts where 221 would have matched the target rate. The two factors multiply to roughly 3.6x; 34.8 x 3.6 ≈ 125 against the observed 135, with the remainder from positive-alert-day differences. Recall transferred essentially unchanged (0.600 against 0.611 in development), confirming the ranking behaviour held; only the threshold's calibration to a target rate did not transfer.
- Ratified the implementation session's decision not to execute the V1-P5 notebook against live GCS: doing so would be a second final-test access for no information gain, exactly the failure mode the single-use rule exists to prevent. The notebook remains committed and unexecuted, verified by its focused test.
- Recorded a V2 methodological finding: operating-point thresholds must be derived from out-of-fold predictions, not in-sample predictions from the rows a model was fitted on, since in-sample predictions do not transfer reliably to held-out behaviour. This is the same threshold-source ambiguity flagged before `EXP-019`'s corresponding module ran; the project owner's in-sample choice for V1-P5 is now understood, with evidence, to have been the less transferable of the two options.
- Authorised phase V1-P6: batch inference writing to `paa_product`, and the dashboard covering squad overview, player detail, data quality and model health, per `DEC-046` and `DEC-061`. V1-P6 itself is not begun in this revision; its specification follows separately.
- No code, evidence, figure or report was regenerated; the final-test partition was not read a second time.

State v59 to v60, under coordination session `PAA-IMPL-20260817-01`.

- Accepted `DEC-064`: authorised the V1-P6 build specification (doc 19 section 5A) — a FastAPI service and a Next.js web service, each its own Cloud Run deployment, batch inference writing `paa_product` and a compact GCS serving artefact the API reads directly (never BigQuery per request), four views each carrying an explicit "as at" date, drivers restricted to `EXP-018`'s eight sign-stable predictors (`daily_load_log1p` excluded per `DEC-060`), shared-credential authentication, and copy constraints (no diagnosis, clearance, fitness, injury-prediction or participation language) enforced by an automated test rather than review alone. Registered and committed alone at `5efc48e`.
- Implemented and executed batch inference (`8435f39`): fits the frozen champion on the development partition via a function shared with the V1-P5 governance gate, guaranteeing byte-identical operating-point thresholds; scores the full covered cohort (34,600 player-days, 2020-01-29 to 2021-12-24); writes `paa_product` and the GCS serving artefact; reconciles the two representations row for row before either write.
- Implemented the FastAPI service (`a4d732f`) reading only the serving artefact, and the Next.js squad-overview view (`a41e88e`), authenticated service-to-service via a Cloud Run identity token fetched from the metadata server (`7d7e6c1`).
- Found and fixed two genuine infrastructure defects rather than working around them, both live BigQuery/Cloud-Run issues invisible to unit tests: BigQuery-invalid column names on the per-rate alert flags, `alert_0.025` rejected for containing a period, fixed via basis-points naming (`e6ad840`); and literal `--ingress internal` blocking same-project Cloud Run-to-Cloud Run calls, since this project provisions no Direct VPC egress on the caller, fixed by switching the API to `--ingress all` while keeping `--no-allow-unauthenticated` and an IAM `run.invoker` binding restricted to the web service's identity, which delivers the same "reachable only by this identity" property (`347dfd9`). Documentation (code docstrings, Dockerfile comment, doc 19) was corrected to describe the mechanism actually running rather than the one originally specified.
- Deployed both services and verified authentication end to end against real data; reported to the project owner, who accepted the deployment and identified three fixes before the remaining views: FIX 1, the squad overview's operating-point banner showed only the flattering EXP-019 development burden (34.8 false alerts per captured onset) without the V1-P5 held-out figure (135.0), creating an unreconciled discrepancy with the model card; fixed by displaying both with the held-out figure at least equally prominent, and added a structural test requiring any screen showing a development burden to also show the held-out figure (`e1c8703`). FIX 2, the review password had been printed in plain text in a prior report and pasted into other transcripts; rotated via a new Secret Manager version, both services redeployed, the old exposed version destroyed after confirming it no longer authenticates; not disclosed again in any summary after the one permitted report. FIX 3, the root `.gitignore` relied implicitly on `web/.gitignore`'s nested rules to keep `node_modules`/`.next` untracked rather than stating this at the root policy-file level; added explicit root-level entries, committed alone (`b7130b2`).
- Implemented the three remaining views. Player detail (`web/app/player/page.tsx`): risk over time with onset dates marked, the eight sign-stable driver contributions for the selected date, and reporting completeness. Data quality (`web/app/quality/page.tsx`): reporting coverage over time, the onset-decline finding by year with a dynamically computed narrative sentence, and coverage range across players. Model health (`web/app/health/page.tsx`): reliability curve with bin counts (a `ReliabilityBin` schema and `arm_reliability_bins.csv` source added for this), the operating-point table with development and held-out burden together, and the V1-P5 confirmatory result with its five-onset support and an explicit C3-not-supported explanation stated inline (fielded as `c3_explanation` rather than `c3_diagnosis`, since the literal substring "diagnos" trips the copy-constraints scanner even inside an ordinary field name). Backend committed at `f24bc25`, frontend at `0c2f22d`.
- Verifying the redeployed dashboard end to end surfaced two further defects, both found by testing the live path rather than trusting the local test suite. First, the API Dockerfile never copied `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` into the image, even though the API had read it since the FIX-1 held-out-burden work; local tests read `outputs/` directly and never exercised the container's file layout. Fixed alongside adding the new reliability-bins table to the image's allow-list (`c2f2b2a`).
- Second, and more substantial: the onsets-by-year table and every player-detail onset marker showed zero onsets everywhere in the live deployment, contradicting `DEC-046`'s documented tenfold 2020-to-2021 decline and the nonzero onset counts `EXP-019` and V1-P5 report elsewhere. Root cause: the frozen Stage 7 eligibility rule marks a player-day ineligible for scoring whenever it falls within an active episode (`episode_start <= prediction_date <= episode_end`), so the onset day itself can never be a scored row — the `is_onset_date` flag, joined onto the scored predictions, was therefore always false by construction, not by data sparsity. Fixed by replacing that join with a dedicated onset calendar read directly from `episode_start`, independent of scoring eligibility, written as a companion serving artefact; the data-quality onset table now reads from it, and player-detail carries onset dates as a top-level list rather than a per-point flag, with the risk-over-time chart repositioned to place onset markers by calendar date rather than series index, since no scored series point can ever coincide with one. Committed at `e35df94`.
- Re-ran batch inference against live GCS after the fix; confirmed live: 63 onsets in 2020 against 10 in 2021 (roughly six-fold, consistent with `DEC-046`'s qualitative "roughly tenfold" claim measured against the full, unrestricted episode set) across the covered-player subset, reproducing `DEC-030`'s "73 distinct onsets" figure under the three-day gap rule exactly (63 + 10 = 73). Rebuilt and redeployed both Cloud Run images; re-verified all four views live, including onset markers rendering correctly on a player with a known September 2021 onset.
- Full quality gate passes throughout this revision: lockfile, Ruff, format, strict mypy and pytest (`130 passed`, one expected ZIP duplicate-name warning), plus `npm run build` succeeding for all four Next.js routes at every checkpoint. No `Co-Authored-By` trailer and no credential appear in any diff or commit from this revision.

## Current Repository State

```text
jobs/analysis/               approved-stage script runners
jobs/product/                V1-P6 batch inference CLI entrypoint
notebooks/analysis/          matching output-cleared notebooks
outputs/analysis/            retained script-generated analysis artifacts
src/player_availability/     ingestion, outcomes, features, quality, configuration,
                              modelling, product (batch inference) and api (FastAPI)
web/                         Next.js dashboard (squad, player, quality, health views)
docker/api/, docker/web/     Cloud Run container definitions
tests/                       130 passing tests, including Stage 0-8, M0/M1 ladder,
                              V1-P5, V1-P6 batch inference, API and web copy-constraint tests
docs/19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md
docs/PROJECT_STATE.md
docs/DECISION_LOG.md
```

Active Stage 0 through Stage 8 and M0/M1 assets follow the shared module/script/notebook/output contract. All notebooks are committed with no outputs or execution counts. The Stage 7 split protocol and Stage 8 launch controls remain frozen; M1 development predictions/model artifacts exist locally under ignored output subdirectories, while public retained evidence is committed. Historical commits remain available locally by design.

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
- EXP-003 read compact gold features and silver episodes from GCS but made no cloud-data changes; retained F1 and feature-ladder evidence is local under `outputs/modelling/exp_003_m1_logistic/`.
- No objective/GPS archive has been extracted or processed.
- V1-P6 (this revision): `paa_product.paa_product` BigQuery table of record (34,600 rows, live-verified). GCS serving artefact, onset calendar and manifest at `gs://paa-artifacts-979927072833/product/`. Two Cloud Run services live in `europe-west2`: `paa-api` (`paa-api-sa`, `--no-allow-unauthenticated`, IAM `run.invoker` restricted to `paa-dashboard-sa`) and `paa-web` (`paa-dashboard-sa`, Basic-Auth-gated, credentials in Secret Manager `paa-web-username`/`paa-web-password`). Deployed URL: `https://paa-web-979927072833.europe-west2.run.app`.

## Current Data State

- Source: SoccerMon subjective data from 50 players across two teams and 731 calendar dates.
- Silver: player registry, daily load, daily wellness, sessions, source event reports and 147 three-day-gap injury episodes.
- Gold labels: 36,550 player-days with censored 3/7/14-day future episode-start labels.
- Gold features: 36,550 unsplit `subjective_v1` player-days with current, rolling and prior-only player-relative features.
- Episode-gap, horizon, burn-in, missingness and primary cohort choices are frozen for the baseline programme under `DEC-030` to `DEC-038`.
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

EXP-002 M0 remains the minimum benchmark. The full raw M1 feature ladder is complete. `DEC-043` is superseded in respect of candidate selection by `DEC-054`: **F1 is the V1 champion**, selected on `EXP-016` dominance evidence and its unseen-player lead over F3, not on statistical significance. F3 and arm C are not carried forward. `EXP-009` originally selected raw F3 probabilities per `DEC-052`; its average-precision claim was superseded by `DEC-056`'s bootstrap correction and its razor-thin `BOOT-01` failure was resolved by `DEC-057`'s interval-exclusion reformulation. `EXP-009` was then extended with F1 raw/Platt/isotonic arms and, under `DEC-058`, **raw F1 probabilities are selected for V1**: no post-hoc calibrator is adopted and the probability transform is now frozen ahead of V1-P5. `DEC-059` corrects `DEC-058`'s rationale: isotonic's Brier cost excludes zero under both resampling schemes and stands, but Platt's Brier cost excludes zero under temporal week-block resampling only and does not meet the record's own two-scheme bar, so Platt's rejection instead rests on calibration-in-the-large deterioration (overprediction rising from roughly 3.7x to roughly 4.4x) and an unbootstrapped log loss degradation; the selection itself is unchanged. **`EXP-007` survival framing is rejected for V1 under `DEC-055`**: the apparent unseen-player lead (AP 0.1045, ROC-AUC 0.8179) was a gap-time-clock leakage artefact that collapsed to AP 0.0193/ROC-AUC 0.5769, both below F1, under a pre-registered reset-clock diagnostic. **`EXP-008` boosted classification is rejected for V1 under `DEC-056`**: Brier favours boosted with both paired intervals excluding zero, but AP and ROC-AUC favour F1 on three of four views and the corrected AP intervals now include zero under both schemes; the training-to-validation AP gap (0.256 against 0.013) is the pre-registered overfitting signature. **Phase V1-P4 is closed under `DEC-060`/`DEC-061`**: the champion selection gate is closed on F1 raw; `EXP-018` found 8 of 9 predictors eligible for driver display with `daily_load_log1p` excluded; `EXP-019`'s measurements led `DEC-061` to move the product-facing alerting rule from top-N to percentile (2.5% default, 5% selectable). **Phase V1-P5 is complete under `DEC-062`**: the final test was spent exactly once. F1 refit once on the full 25,055-player-day development partition scored 0.827204 ROC-AUC, a 3.7x overprediction (matching development exactly) and a 135.0 false-alerts-per-captured-onset burden at the 2.5% rate on the 8,845-player-day, 5-onset final-test partition. C1 and C2 are supported; C3 is not. **`DEC-063` diagnoses C3 from committed evidence alone**, no second access: the final-test onset density is roughly half development's and the in-sample-derived threshold realised a 4.737% alert rate rather than the intended 2.5%, together accounting for the shortfall while recall transferred within one point; neither is a champion deficiency. This is a confirmatory sanity check, not a performance claim, and changes no prior decision. Final-test performance is now spent; a second access requires a superseding decision, and none is sought. **Phase V1-P6 is complete under `DEC-064`**: batch inference to `paa_product`, the FastAPI/Next.js dashboard across all four views, and both Cloud Run services deployed and verified end to end against live data.

## Current Product State

V1-P6 is complete and deployed under `DEC-064`. Batch inference writes the `paa_product` BigQuery table of record and a compact serving artefact to Cloud Storage that the API reads directly; the API never queries BigQuery per request. Two Cloud Run services are live: `paa-api` (`--no-allow-unauthenticated`, reachable only by the web service's IAM identity) and `paa-web` (Basic-Auth-gated, shared review credential). Four web views are implemented and verified against live data: squad overview (daily ranked display, percentile alerting per `DEC-061`), player detail (risk over time with onset dates marked and the eight `EXP-018` sign-stable drivers), data quality (reporting coverage and the onset-decline finding by year) and model health (reliability curve, operating-point table with development and held-out burden together, and the V1-P5 confirmatory result with its C3 explanation). Every operating-point display carries the held-out (V1-P5) figure alongside the development (EXP-019) figure, enforced by a structural test, never the development figure alone. Copy constraints (no diagnosis, clearance, fitness, injury-prediction or participation language) are enforced by an automated source-text scan. The intended product remains practitioner decision support, never diagnosis, clearance or participation advice.

## Locked Decisions

- `DEC-001` to `DEC-026` remain the accepted foundation except where explicitly superseded in the decision log.
- `DEC-027` is superseded and its former split is not active.
- `DEC-028` resets pre-model analysis to Stage 0 while preserving trusted data engineering and history.
- `DEC-029` defines the shared script/notebook implementation and output-storage contract.
- `DEC-030` defines player-date onset as the effective binary outcome event and constrains sensitivity, validation and claims.
- `DEC-031` defines missing-value semantics and a conservative lagged-only wellness/reporting policy for the primary predictor contract.
- `DEC-032` defines Stage 3 feature handling: preserve extremes, separate recording state from magnitude, carry justified `log1p` candidates, and exclude unstable existing z-scores from the primary operational contract.
- `DEC-033` defines the target-blind full-contract catalogue and provisional operational feature-family policy; `DEC-036` finalises the predictor allow-list.
- `DEC-034` accepts Stage 5 only as constrained retrospective context evidence and authorises Stage 6 specification review without authorising implementation.
- `DEC-035` freezes the primary and secondary Stage 6 outcome/cohort policy and authorises Stage 7 specification review without authorising implementation.
- `DEC-036` freezes the Stage 7 predictor ladder, prohibited fields, chronological partitions and embargoes, development stress tests, train-only preprocessing, metrics, uncertainty and alert-capacity rules.
- `DEC-037` accepts Stage 7 as `PASS WITH LIMITATIONS`, preserves the frozen protocol, constrains sparse-support interpretation and authorises Stage 8 specification review only.
- `DEC-038` freezes the Stage 8 binary hard-gate readiness method, evidence provenance, mandatory limitation controls, hypothesis register, M0/M1-first launch sequence and owner decision gate.
- `DEC-039` accepts the Stage 8 `READY` recommendation, authorises development-only EXP-002 M0 under the approved output contract, keeps M1 pending M0 review and preserves the final-test lock.
- `DEC-040` accepts EXP-002 M0, freezes global training prevalence as the official minimum probability benchmark, retains recent load as a failed descriptive comparator and authorises M1 specification review only.
- `DEC-041` authorises development-only M1-F1 regularised logistic regression, freezes predictors, preprocessing, tuning, diagnostics, stress tests and output contract, and keeps F2/F3, calibration selection and final test blocked.
- `DEC-042` promotes F1 as the development reference and authorises cumulative F2/F3 controlled ablation under unchanged model and validation settings; it does not authorise deployment, calibration selection or final-test access.
- `DEC-043` rejects F2, promotes F3 as the raw M1 development candidate, and binds five limitations to every downstream citation of F3; it authorises no deployment, no performance claim outside those limitations and no final-test access.
- `DEC-044` authorises `EXP-009` raw/Platt/isotonic calibration on F3 using development data only, with the five-onset power limitation binding on every reported conclusion.
- `DEC-045` fixes LF line endings in the repository and working tree, with explicit binary protection for Parquet, model artefacts and images.
- `DEC-046` defines V1 scope and definition of done; no V1 artefact may present discrimination performance as the headline result, and the final test is spent exactly once.
- `DEC-047` makes pooled rolling-origin the headline evaluation, superseding `DEC-036` in respect of headline designation only; zero-positive folds must be reported and excluded from discrimination aggregation with counts stated.
- `DEC-048` retains the three-day episode gap as primary with the one-day gap as a mandatory pre-registered sensitivity on every V1 headline result.
- `DEC-057` reformulates `BOOT-01` to require paired-bootstrap sign agreement only where the interval excludes zero, and extends `EXP-009` with F1 raw/Platt/isotonic arms under the existing identifier, retaining F3 as historical reference.
- `DEC-058` selects raw probabilities for the F1 champion; no post-hoc calibrator is adopted for V1, and the probability transform is frozen ahead of V1-P5.
- `DEC-059` supersedes `DEC-058`'s rationale only, grounding the raw-F1 selection in calibration-in-the-large and log loss rather than an unestablished Brier cost; the two-scheme interval-exclusion requirement applies symmetrically to costs and benefits in every future gate.
- `DEC-060` closes the V1-P4 champion selection gate on F1 raw; authorises `EXP-018` and `EXP-019`. Its product-facing operating-point choice is superseded by `DEC-061`.
- `DEC-061` supersedes `DEC-060`'s operating-point choice only: the dashboard's alerting rule is percentile-based (2.5% default, 5% selectable, frozen `DEC-036` basis), separated from a daily ranked-squad display view; top-N is retained nowhere as an alerting rule.
- `DEC-062` pre-registers and authorises exactly one V1-P5 final-test evaluation; the final test is now spent. No result may change the champion, the operating points, the predictor contract or any prior decision, and a second access requires a superseding decision.
- `DEC-063` diagnoses the V1-P5 C3 shortfall from committed evidence alone (no re-run); ratifies the V1-P5 notebook's non-execution against live GCS; records the in-sample-threshold finding for V2; authorises phase V1-P6.
- `DEC-064` authorises and specifies the V1-P6 build: FastAPI plus Next.js, two Cloud Run services, batch inference to `paa_product` and a GCS serving artefact, four dashboard views each carrying an explicit "as at" date, drivers restricted to `EXP-018`'s sign-stable predictors, shared-credential authentication, and copy constraints enforced by an automated test.
- Git remains local-only unless the project owner explicitly requests otherwise.
- Random row-level splitting is prohibited for headline evaluation.
- No objective/GPS processing begins during the subjective pre-model analysis programme.
- F3 held-period metrics may not be reported without the unseen-player reversal and the five-onset support stated alongside them.

## Open Decisions

None outstanding from this revision. Phase V1-P6 is complete and deployed. Phase V1-P7 (operationalisation) is not begun and has no open specification.

Resolved since the previous revision: the V1-P6 build specification (`DEC-064`, authorised and implemented in full — batch inference, API, all four dashboard views, both services deployed to Cloud Run and verified end to end). Resolved previously: the V1-P5 C3 shortfall (`DEC-063`, diagnosed from committed evidence alone as onset-density decay and in-sample-threshold non-transfer, both non-champion causes; no further final-test access); the V1-P5 final-test evaluation (`DEC-062`, pre-registered then spent exactly once; C1 and C2 supported); the dashboard operating-point choice (`DEC-061`); the champion selection gate (`DEC-060`, F1 raw, closed; no further V1 candidate); the `EXP-018` explanation-stability question (measured — 1 of 9 predictors unstable, stop condition not triggered). The outcome-support limitation remains an accepted, quantified dataset property that constrains every V1 claim and is designed around rather than resolved.

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
- M1-F1 raw probabilities are materially overestimated on validation and have worse Brier/log loss than M0 despite better ranking; calibration strategy requires a separate owner-approved specification if M1-F1 is promoted.
- Alert capture is based on only five represented validation onsets and approximately 107 false alerts per captured onset at the two non-zero-capture budgets; operational conclusions remain highly uncertain.
- F3 improves held-period point estimates but not unseen-player aggregate ranking; its incremental player-cluster intervals include zero and one rolling fold degrades materially.
- Resolved by `DEC-054`: the F3 fatigue robust z-score's 8.4%-coverage entanglement with availability and missingness structure, investigated by `EXP-016`, was the deciding factor in F3's replacement by F1 as champion. F3 and the audited predictor are no longer in the champion contract; retained here for the historical record.
- Resolved by `DEC-054`: F3's weaker unseen-player generalisation than F1 (AP 0.022308 versus 0.023316; ROC-AUC 0.630928 versus 0.642578), previously an accepted trade-off under `DEC-043`, is superseded now that F1 is champion.
- Line-ending policy is now fixed by `.gitattributes` under `DEC-045`. Contributors on Windows should confirm their editor honours it, since the previous churn recurred silently on every write.
- The installed `lifelines` `CoxTimeVaryingFitter` (0.29.0) implements neither cluster-robust sandwich variance nor Schoenfeld residuals for time-varying counting-process fits. `EXP-007` coefficient standard errors are model-based, not cluster-robust; the player-cluster and temporal week-block paired bootstrap against F1 is the primary inferential evidence, and a covariate-by-log-time interaction likelihood-ratio test substitutes for the Schoenfeld proportional-hazards check.
- Resolved by `DEC-055`: survival framing rejected for V1. The gap-time constraint recorded — a gap-time origin derived from a player's own onset history is legitimate under temporal evaluation but breaches the premise of leave-one-player-out evaluation — binds all future survival work, including `EXP-014` in V2, and is recorded in doc 19 so it is not repeated there.
- Noted, no action required until V1-P7 containerisation: the `lifelines` dependency added for `EXP-007` constrains numpy to 1.26 (down from 2.5) and scipy to 1.17 (down from 1.18). It is a removal candidate now that survival framing is rejected for V1, since `EXP-014` in V2 would need to re-add it regardless.
- `EXP-008`'s training average precision (0.256) is roughly twenty times its validation average precision (0.013) for the selected boosted configuration, a clearer overfitting signature than the Brier-based flag alone, since Brier's absolute scale is not comparable across differently-prevalent train and validation periods.
- Resolved by `DEC-056`: the paired-bootstrap population mismatch for average precision. `paired_prediction_bootstrap_differences` resampled the full pooled population while the point estimate uses only the discrimination-eligible subset; corrected across all four affected modules with `BOOT-01` added, retained evidence regenerated. `DEC-052`'s isotonic-vs-raw claim, the case that surfaced the defect, is superseded; the corrected week-block interval is [-0.036918, 0.017755], including zero.
- Resolved by `DEC-057`: `BOOT-01`'s razor-thin raw-vs-isotonic average-precision failure was a specification defect, not an estimator defect. `BOOT-01` required sign agreement even where the interval included zero and no direction was claimed; reformulated to check sign only where the interval excludes zero, and the epsilon-based interim fix is removed.
- Resolved by `DEC-058`: F1's calibration was previously untraceable to a measured result, since `DEC-054` promoted F1 to champion after `EXP-009` had only run F3's arms. `EXP-009` now carries F1 raw/Platt/isotonic arms; both Platt and isotonic degrade Brier and log loss relative to raw, and no calibrator is adopted.
- Not remediated by design, recorded under `DEC-059`: log loss, calibration slope and calibration intercept carry no uncertainty interval anywhere in the current bootstrap suite, which is built only for Brier score and average precision. V1 conclusions do not rest on these unbootstrapped metrics, but the limitation must be stated in the model card whenever they are cited as evidence.
- `daily_load_log1p` is the one F1 predictor with unstable coefficient sign across estimable folds (`EXP-018`) and also carries the smallest coefficient magnitude of the nine; it may not be displayed as a driver in the dashboard, per `DEC-060`'s gate. The other eight predictors are eligible.
- False-alert burden is high at every measured operating point (`EXP-019`): 34.8 false alerts per captured onset at the `DEC-061` default 2.5% rate, rising to 60.4 at the selectable 5% rate. This is a property of the cohort's outcome support (104 positive player-days, 18 represented onsets), not of the operating-point rule, and must be stated plainly in the interface and the model card.
- The 1% review rate is not offered as a dashboard operating point (`DEC-061`): its false-alert burden (80.5 per captured onset) exceeds the 2.5% rate's despite the narrower alert volume, a non-monotonicity attributed to the 18-onset support rather than to the ranking. It remains in experiment evidence as the `DEC-036` comparison basis.
- The V1-P5 final-test false-alert burden (135.0 per captured onset at 2.5%, 5 represented onsets) is materially worse than the development figure (34.8) that motivated `DEC-061`. This is reported as a confirmatory result, not a performance claim (`DEC-062`), and must not be read as evidence against the operating-point choice, whose comparison basis is the pooled rolling-origin `EXP-019` evidence, not this five-onset partition.
- Resolved by `DEC-063`: the V1-P5 C3 shortfall diagnosed as two compounding, non-champion causes rather than a champion deficiency — final-test onset density roughly half development's (0.565 against 1.071 per thousand player-days), and the 2.5%-target threshold realising a 4.737% alert rate on held-out data. The two factors multiply to approximately 3.6x, closely reproducing the observed burden; recall transferred within one percentage point (0.600 against 0.611).
- Not remediated, recorded under `DEC-063` for V2: probability thresholds for operating points must be derived from out-of-fold predictions, not from a model's in-sample predictions on the rows it was fitted on. The V1-P5 threshold (in-sample, the only choice available given the champion is a single refit rather than a fold ensemble) did not transfer its target alert rate to held-out data, though ranking behaviour (recall) did transfer. This finding governs any V2 work deriving operating thresholds.
- Final-test performance is now spent under `DEC-062`. A second access requires a superseding decision recorded before it occurs; none has been sought, and `DEC-063` explicitly declines to seek one to improve the C3 outcome.
- Resolved by the V1-P6 build (this revision): the `is_onset_date` flag as originally joined onto scored predictions was always false by construction, since the frozen Stage 7 eligibility rule excludes the onset day itself from the scored cohort. A dedicated onset calendar, read from `episode_start` independent of scoring eligibility, now backs both the data-quality onset table and the player-detail onset markers. This was a display-layer defect, not a modelling or eligibility-rule defect; the eligibility rule itself is unchanged and correct.
- Not remediated, informational only: the onset calendar's 73-onset total (63 in 2020, 10 in 2021) is restricted to players present in the scored cohort, which differs from the raw 147-episode source count (135 in 2020, 12 in 2021) before that restriction. Both are legitimate figures for different questions; the dashboard's data-quality view reports the cohort-restricted figure, matching `DEC-030`'s "73 distinct onsets under the three-day gap rule."

## Blockers

None. Phase V1-P6 is complete and deployed. The final test has been spent exactly once; a second access requires a superseding decision.

Standing analytical constraint, not a blocker: effective outcome support is 104 pooled positive player-days under rolling-origin development, and 5 represented onsets on the final-test partition. This limits the inferential capacity of every comparison made at this stage, including the V1-P5 confirmatory result, which is explicitly not a performance claim for exactly this reason.

## Work In Progress

No implementation is in progress. `EXP-009`, `EXP-016`, `EXP-007`, `EXP-008`, `EXP-018`, `EXP-019`, the V1-P5 final-test governance gate and the V1-P6 dashboard are all implemented, executed, deployed and committed. Phase V1-P5 is closed under `DEC-062`/`DEC-063`; phase V1-P6 is complete under `DEC-064`. Phase V1-P7 is not begun. No other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Write the model card, citing the V1-P5 result as a confirmatory check with its five-onset support stated inline, stating the C3 diagnosis (`DEC-063`) explicitly, and never as a performance claim.
2. Carry the `DEC-063` out-of-fold-threshold finding into any V2 work that derives operating thresholds.
3. Before V1-P7 containerisation work beyond the already-deployed V1-P6 services, record and act on the `lifelines`/numpy/scipy dependency constraint; it is a removal candidate now that survival framing is rejected for V1.
4. Await direction on Phase V1-P7 (operationalisation) or V1-P8 (release evidence, model card, CI). Neither has an open specification in this revision.
5. The final test is spent. Any further access requires a superseding decision recorded before it occurs.

## Validation / Quality Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Lockfile integrity | PASS | `poetry check --lock` |
| Lint | PASS | Ruff, all checks passed |
| Format | PASS | format check clean across 83 Python files |
| Type check | PASS | strict mypy, 65 source files |
| Tests | PASS | 93 passed; one expected duplicate-ZIP-member warning |
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
| Stage 7 results review | PASS WITH LIMITATIONS | project-owner approval received 2026-08-15; interpretation accepted under `DEC-037` |
| Leakage/split gate | FROZEN | exact partitions and embargoes retained; final-test performance locked |
| Stage 8 specification | PASS | project-owner approval received 2026-08-15; method accepted under `DEC-038` |
| Stage 8 implementation | PASS | shared module, script, notebook, outputs and tests committed at `7a17edd` |
| Stage 8 evidence and hard gates | PASS | 8 stages, 24 hashed artifacts, 12/12 hard gates and 12 mapped constraints |
| Stage 8 notebook execution | PASS | executed against retained evidence with zero errors; committed notebook remains output-free |
| Stage 8 provisional recommendation | READY | narrow exploratory M0/M1 scope accepted by the project owner under `DEC-039` |
| Stage 8 results review | PASS | owner `READY` approval received 2026-08-15 |
| EXP-002 M0 specification | APPROVED | global prevalence plus pre-specified recent-load heuristic; development only |
| EXP-002 M0 implementation | PASS | shared module, canonical job, notebook, retained outputs and four tests committed at `28a4b3b` |
| EXP-002 M0 development run | PASS WITH REVIEW | 8,690 validation days, 28 positive days, five onsets; zero failures and three review findings |
| EXP-002 M0 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-002 M0 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-002 M0 results review | PASS | project-owner `BENCHMARK ACCEPT` received 2026-08-15; decision recorded under `DEC-040` |
| EXP-003 M1-F1 specification | APPROVED | development-only contract accepted under `DEC-041` |
| EXP-003 M1-F1 implementation | PASS | committed at `146edcc`; report, 17 tables and nine reviewed figures retained |
| EXP-003 M1-F1 development run | PASS WITH REVIEW | ranking improves; Brier/log loss and raw calibration require owner review |
| EXP-003 M1-F1 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-003 M1-F1 notebook execution | PASS | executed against GCS; committed notebook remains output-free |
| EXP-003 M1-F1 results review | PROMOTE | development reference advancement accepted under `DEC-042`; not operational |
| EXP-003 M1-F2/F3 specification | APPROVED | cumulative frozen contracts under unchanged model/evaluation settings |
| EXP-003 M1-F2/F3 implementation | PASS | committed at `226224c`; consolidated and per-set evidence retained |
| EXP-003 M1 feature-ladder run | PASS WITH REVIEW | F2 non-improvement; F3 leads held-period metrics with material limitations |
| EXP-003 feature-ladder final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-003 feature-ladder notebook execution | PASS | executed against GCS; committed notebook remains output-free |
| EXP-003 raw-candidate review | CLOSED | F2 rejected; F3 promoted with five binding limitations under `DEC-043` |
| EXP-009 calibration scope | AUTHORISED | raw/Platt/isotonic on F3, development data only, under `DEC-044` |
| EXP-009 specification | APPROVED | owner approval received 2026-08-16; accepted under `DEC-051` |
| Line-ending policy | PASS | `.gitattributes` added and repository renormalised at `df735d5` under `DEC-045` |
| Independent gate re-verification | PASS | all five gates reproduced from a clean environment in session `PAA-CTRL-20260815-02` |
| V1 scope definition | ACCEPTED | `DEC-046`; definition of done recorded in doc 19 section 5A |
| Documentation architecture | CORRECTED | `DEC-050`; specifications live in doc 19; out-of-convention files removed from repository and Drive |
| Calibrator fitting rule | ACCEPTED | `DEC-049`; fold-wise, disjoint from evaluation, enforced by `CAL-02` |
| V1 headline evaluation protocol | ACCEPTED | `DEC-047`; pooled rolling-origin primary, fixed window as temporal stress |
| V1 outcome sensitivity policy | ACCEPTED | `DEC-048`; three-day gap primary, one-day gap mandatory sensitivity |
| V1 delivery plan | APPROVED | `DEC-051`; eight phases, gates, definition of done, risk register |
| EXP-009 specification | APPROVED | `DEC-051`; methods, fitting discipline, eight integrity checks, sparse-predictor audit |
| EXP-009 implementation | PASS | committed at `fddb55e`; shared module, canonical job, notebook, retained evidence, tests |
| EXP-009 development run | PASS | 104 pooled positive days, three estimable folds, one zero-positive fold; `CAL-01` to `CAL-08` all PASS |
| EXP-009 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-009 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-009 results review | PASS | project-owner review received 2026-08-16; raw selected, calibration rejected under `DEC-052` |
| EXP-016 specification | APPROVED | doc 19 section 5 E3, authorised under `DEC-052` |
| EXP-016 implementation | PASS | committed at `e624ffe`; shared module, canonical job, notebook, retained evidence, tests |
| EXP-016 development run | PASS | four arms; arms A and D reproduce `DEC-043` unseen-player reference figures exactly; `ABL-01` to `ABL-07` all PASS |
| EXP-016 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-016 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-016 results review | RESOLVED | `DEC-054`; F1 selected as V1 champion, superseding `DEC-043` in respect of candidate selection |
| V1-P1 / section 5A ordering conflict | RESOLVED | `DEC-053`; section 5A governs, `EXP-007`/`EXP-008` proceed at V1-P2/V1-P3 |
| EXP-007 specification | APPROVED | doc 19 section 5 as F1, authorised under `DEC-054` |
| EXP-007 implementation | PASS | committed at `a73c46d`; shared module, canonical job, notebook, retained evidence, tests; adds bounded `lifelines` dependency |
| EXP-007 development run | PASS | Andersen-Gill Cox vs F1; `COX-01` to `COX-08` all PASS; coefficient variance model-based, not cluster-robust (disclosed) |
| EXP-007 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-007 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-007 gap-time-clock diagnostic | PASS | pre-registered reset-clock re-run collapsed the unseen-player advantage below F1, confirming leakage |
| EXP-007 evidence hardening | PASS | committed at `6dfd121`; reset_clock reported as valid result, own_clock as leakage diagnostic contrast; `COX-09` added |
| EXP-007 results review | RESOLVED | `DEC-055`; survival framing rejected for V1 on evidence-backed diagnostic grounds; F1 remains champion |
| EXP-008 specification | APPROVED | doc 19 section 5 as F2 |
| EXP-008 implementation | PASS | committed at `0044fe7`; shared module, canonical job, notebook, retained evidence, tests |
| EXP-008 development run | PASS | `HistGradientBoostingClassifier` vs F1; `BST-01` to `BST-09` all PASS |
| EXP-008 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-008 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-008 results review | RESOLVED | `DEC-056`; boosted classification rejected for V1, F1 remains champion |
| Paired-bootstrap population defect | RESOLVED | `DEC-056`; corrected at `230a571` across CAL/ABL/COX/BST; `BOOT-01` added; evidence regenerated for four experiments |
| DEC-052 average-precision claim | SUPERSEDED | `DEC-056`; corrected week-block interval [-0.036918, 0.017755] includes zero; calibration selection unaffected |
| BOOT-01 interval-exclusion reformulation | RESOLVED | `DEC-057`; committed at `78f579f`; regenerated for CAL/ABL/COX/BST, all four PASS |
| EXP-009 F1 calibration arms | PASS | committed at `78f579f`; F1 raw/Platt/isotonic added under the existing identifier, F3 retained as historical reference |
| EXP-009 F1 results review | RESOLVED | `DEC-058`; raw selected, no post-hoc calibrator adopted, probability transform frozen ahead of V1-P5 |
| DEC-058 rationale correction | RESOLVED | `DEC-059`; Platt's rejection rests on calibration-in-the-large and log loss, not an unestablished Brier cost; selection unchanged; symmetry rule recorded |
| Champion selection gate | CLOSED | `DEC-060`; F1 raw is the V1 champion; no further candidate evaluated in V1 |
| EXP-019 specification | AUTHORISED | doc 19 section 5 D2, full specification replacing the stub; authorised under `DEC-060` |
| EXP-019 implementation | PASS | committed at `a66e812`; shared module, canonical job, notebook, retained evidence, tests |
| EXP-019 development run | PASS | 104 pooled positive days; top-N and percentile operating points from the same predictions; `ALERT-01` to `ALERT-06` all PASS |
| EXP-019 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-019 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-019 results | MEASURED | operating points and false-alert burdens recorded |
| Dashboard operating-point choice | RESOLVED | `DEC-061`; percentile alerting (2.5% default, 5% selectable) supersedes `DEC-060`'s top-N choice on measured dominance; no regeneration required |
| V1-P5 pre-registration | REGISTERED | `DEC-062`; committed alone at `650f67e1883b655124324219c20cca09f19c3eba`, before any evaluation code existed |
| V1-P5 threshold-source ambiguity | RESOLVED | raised before any final-test code was written; project owner selected in-sample (final artefact's own development predictions) |
| V1-P5 implementation | PASS | committed at `a27eced`; shared module, canonical job, notebook (committed output-free, not executed live), retained evidence, tests |
| V1-P5 development-only tests | PASS | 113 passed against synthetic fixtures; final-test partition not touched before the live read |
| V1-P5 final-test execution | PASS | executed exactly once against live GCS at `a27eced`; 8,845 player-days, 35 positive days, 5 represented onsets; `FINAL-01` to `FINAL-07` all PASS |
| V1-P5 claims | C1 YES / C2 YES / C3 NO | ROC-AUC 0.827204; 3.7x overprediction matches development; 135.0 false alerts/captured onset at 2.5% exceeds the registered "tens" order |
| V1-P5 C3 diagnosis | RESOLVED | `DEC-063`; onset-density decay and in-sample-threshold non-transfer account for the shortfall arithmetically; no re-run, no second final-test access |
| V1-P6 authorisation | AUTHORISED | `DEC-063`; batch inference to `paa_product` and the dashboard, per `DEC-046`/`DEC-061`; specification follows separately, not yet begun |
| EXP-018 specification | AUTHORISED | doc 19 section 5 D3, new specification; authorised under `DEC-060` |
| EXP-018 implementation | PASS | committed at `a66e812`; shared module, canonical job, notebook, retained evidence, tests |
| EXP-018 development run | PASS | 4 rolling-origin + 50 leave-one-player-out estimable folds; exact attribution (`EXPL-03` zero error); `EXPL-01` to `EXPL-05` all PASS |
| EXP-018 final-test isolation | PASS | zero final-test predictions and zero performance access |
| EXP-018 notebook execution | PASS | executed against GCS with zero errors; committed notebook remains output-free |
| EXP-018 results | MEASURED | 1 of 9 predictors (`daily_load_log1p`) unstable sign; stop condition (majority unstable) not triggered; no decision record required |
| Modelling | V1-P6 COMPLETE | F1 is champion (`DEC-054`/`DEC-055`/`DEC-056`/`DEC-058`/`DEC-059`/`DEC-060`); dashboard alerting is percentile-based (`DEC-061`); final test spent exactly once under `DEC-062`, C3 diagnosed under `DEC-063`; V1-P6 complete and deployed under `DEC-064` |
| V1-P6 specification | APPROVED | `DEC-064`; committed alone at `5efc48e` |
| V1-P6 batch inference | PASS | committed at `8435f39`; 34,600 player-days scored live, reconciled row for row, thresholds byte-identical to V1-P5 |
| V1-P6 API implementation | PASS | committed at `a4d732f`; reads only the GCS serving artefact, never BigQuery per request |
| V1-P6 web (squad overview) | PASS | committed at `a41e88e`/`7d7e6c1`; service-to-service auth via Cloud Run identity token |
| V1-P6 deployment (squad only) | PASS | committed at `347dfd9`; both Cloud Run services live, IAM auth verified end to end; two live infrastructure defects found and fixed (BigQuery column naming, ingress-vs-IAM mechanics) |
| FIX 1 (held-out burden) | RESOLVED | committed at `e1c8703`; held-out figure now shown alongside development figure everywhere, enforced by a structural test |
| FIX 2 (password rotation) | RESOLVED | new Secret Manager version issued, both services redeployed, old exposed version destroyed and confirmed non-authenticating |
| FIX 3 (.gitignore Node coverage) | RESOLVED | committed alone at `b7130b2` |
| V1-P6 remaining views (player detail, data quality, model health) | PASS | backend committed at `f24bc25`, frontend at `0c2f22d` |
| V1-P6 Docker image completeness | RESOLVED | committed at `c2f2b2a`; API image was missing `operating_point_results.csv`, invisible to local tests, found only by testing the deployed container |
| V1-P6 onset-date reporting defect | RESOLVED | committed at `e35df94`; onset day is structurally never a scored player-day, fixed via a dedicated onset calendar independent of scoring eligibility; confirmed live (63 onsets 2020, 10 onsets 2021) |
| V1-P6 redeployment and end-to-end verification | PASS | both Cloud Run images rebuilt and redeployed after the onset-date fix; all four views verified live against real data, including onset markers |
| V1-P6 copy constraints | PASS | automated source-text scan; no prohibited language; held-out-burden structural test passes |

Gate results recorded in this revision were reproduced independently rather than carried forward: Ruff clean, format clean across 114 files, strict mypy clean across 88 source files, `130 passed` with one expected ZIP warning, `poetry check --lock` passing, and `npm run build` succeeding for all four Next.js routes.

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v60, 2026-08-17T14:00:00Z | v60, 2026-08-17T14:00:00Z |
| `DECISION_LOG.md` | DEC-001 to DEC-064 | DEC-001 to DEC-064 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | section 5A gains the V1-P6 build specification; the API/ingress subsection corrected to describe the deployed IAM-authentication mechanism | section 5A gains the V1-P6 build specification; the API/ingress subsection corrected to describe the deployed IAM-authentication mechanism |

Mirrored document set, per `DEC-050`: the two control documents plus doc 19, which now carries specification content. Drive holds the numbered planning corpus plus these three; no non-numbered documents beyond the two control files.

Status: **SYNCHRONISED**

Both copies were reconciled during session `PAA-IMPL-20260817-01`. `DECISION_LOG.md` gains `DEC-064`, authorising and specifying the V1-P6 build; doc 19 section 5A gains the full build specification and a corrected description of the API's deployed authentication mechanism; `PROJECT_STATE.md` advances to v60, covering V1-P6's full implementation, deployment, three post-acceptance fixes, the onset-date reporting defect and its fix, and end-to-end verification of all four dashboard views against live data. All three pairs hash-match under LF normalisation. Drive mirrors are written in place at the mounted folder under `DEC-016`. The state records `0955e86`, the committed tree before this control-document update (the onset-date fix at `e35df94` plus the regenerated batch-inference evidence at `0955e86`); the commit containing the control update will be one commit later by design.
