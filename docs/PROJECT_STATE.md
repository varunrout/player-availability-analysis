# Player Availability Analysis - Project State

State Version: 49
Last Updated UTC: 2026-08-16T13:59:36Z
Coordination Session ID: PAA-IMPL-20260816-01
Git Branch: main
Git HEAD: 76f4b08 (pre-state-update commit; see State Synchronisation Status)
Current Milestone: V1 Delivery Programme - Phase V1-P1 Calibration (`EXP-009`)
Current Phase Status: V1 scope is defined and accepted under `DEC-046`. Pooled rolling-origin becomes the headline evaluation under `DEC-047`; the three-day episode gap is retained with a mandatory one-day sensitivity under `DEC-048`. The V1 delivery plan and the `EXP-009` calibration specification are approved as drafted under `DEC-051`; phase V1-P1 implementation is authorised against development data only. Final-test performance remains locked and is spent once, in phase V1-P5.

## Current Objective

Implement and execute phase V1-P1 (`EXP-009`) against development data only, now that the specification is approved under `DEC-051`. Preserve the final-test lock.

## V1 Delivery Context

V1 is a complete subjective-data decision-support system whose primary evidence is methodological rigour and product completeness, not discrimination performance (`DEC-046`).

The binding constraint is outcome support: 66 represented onsets in the frozen cohort, split 56 in train, five in validation and five in final test, with 74.6% of onsets from five players and only 12 of 50 players carrying any event. Reported onsets fall roughly tenfold from 2020 to 2021 at flat player-days, tracking decaying self-report engagement rather than reduced injury incidence.

Phases, governed by section 5A of `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` and mapped onto experiment identifiers already registered there: V1-P1 calibration (EXP-009), V1-P2 Cox survival (EXP-007), V1-P3 boosted classification (EXP-008), V1-P4 champion selection, explanation stability and alert-budget utility (EXP-018 and EXP-019), V1-P5 pre-registration and single-use final test (governance gate), V1-P6 product, V1-P7 operationalisation, V1-P8 release evidence. No new experiment identifiers are allocated.

Deferred to V2: objective GPS ingestion (EXP-011, EXP-012), neural survival models (EXP-015), online serving.

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

## Current Repository State

```text
jobs/analysis/              approved-stage script runners
notebooks/analysis/         matching output-cleared notebooks
outputs/analysis/           retained script-generated analysis artifacts
src/player_availability/    ingestion, outcomes, features, quality and configuration
tests/                      93 passing tests, including Stage 0-8 and M0/M1 ladder tests
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

EXP-002 M0 remains the minimum benchmark. The full raw M1 feature ladder is complete. F2 is not supported as an improvement over F1. F3 is the leading held-period raw candidate with `C=0.001`, Brier 0.003613, log loss 0.030367, AP 0.019432 and ROC-AUC 0.851053, plus one onset captured at the tight 1% budget. However, it still overpredicts risk by about 6.1 times, player-bootstrap improvements include zero, temporal performance varies and unseen-player ranking remains below F1. Raw-candidate owner selection is pending; calibration selection, M2+ and final-test performance remain blocked.

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
- Git remains local-only unless the project owner explicitly requests otherwise.
- Random row-level splitting is prohibited for headline evaluation.
- No objective/GPS processing begins during the subjective pre-model analysis programme.
- F3 held-period metrics may not be reported without the unseen-player reversal and the five-onset support stated alongside them.

## Open Decisions

None blocking phase V1-P1. Owner approval of the V1 delivery programme and the `EXP-009` specification was granted under `DEC-051`, closing the single open decision carried in state v48.

Recorded for a future revision, not blocking V1-P1: doc 19 sections 5 and 5A conflict on whether `EXP-007` and `EXP-008` precede or follow operational-utility analysis. A superseding decision is required before phase V1-P2 begins.

Resolved since the previous revision: owner approval of the V1 delivery programme and the `EXP-009` specification (`DEC-051`). The outcome-support limitation remains an accepted, quantified dataset property that constrains every V1 claim and is designed around rather than resolved.

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
- The F3 fatigue robust z-score has only 8.4% coverage, so its coefficient and apparent contribution are entangled with availability and missingness structure. F3 is now the promoted candidate under `DEC-043`, so this predictor is under explicit audit in `EXP-009` and is a removal candidate if calibration proves sensitive to its availability pattern.
- F3 was promoted despite recording weaker unseen-player generalisation than F1 (AP 0.022308 versus 0.023316; ROC-AUC 0.630928 versus 0.642578). This is an accepted, documented trade-off under `DEC-043`, not an oversight, and must be restated wherever F3 performance is cited.
- Line-ending policy is now fixed by `.gitattributes` under `DEC-045`. Contributors on Windows should confirm their editor honours it, since the previous churn recurred silently on every write.

## Blockers

No technical blocker. The raw-candidate gate is closed by `DEC-043`, calibration scope is authorised by `DEC-044`, and the `EXP-009` specification is approved under `DEC-051`. Phase V1-P1 implementation is authorised against development data only. Final-test performance remains blocked until the frozen checklist is completed and one-time access is explicitly authorised at phase V1-P5.

Standing analytical constraint, not a blocker: effective outcome support is five onsets per evaluation partition. This limits the inferential capacity of every comparison made at this stage, including the calibration comparison now authorised.

## Work In Progress

The V1 delivery plan and the `EXP-009` specification are approved under `DEC-051`. Phase V1-P1 implementation is authorised and beginning. No other control session is known to be modifying the working tree.

## Immediate Next Actions

1. Implement V1-P1 (`EXP-009`) as shared analysis code, canonical script, matching output-free notebook, retained tables and figures, and focused tests, per `DEC-029`, matching the `exp_002`/`exp_003` layout.
2. Execute against development data only. Fit calibrators fold-wise on partitions disjoint from evaluation, per `DEC-049` and `CAL-02`.
3. Report pooled rolling-origin as primary with estimable-fold counts and per-fold values, plus the one-day-gap sensitivity, per `DEC-047` and `DEC-048`.
4. Complete the mandatory sparse-predictor availability audit for the 8.4%-coverage robust fatigue z-score, per `DEC-043` and `CAL-06`.
5. Verify integrity checks `CAL-01` to `CAL-08`; keep final-test predictions and performance locked until V1-P5.
6. Review results at the V1-P1 gate. Before V1-P2, obtain a superseding decision resolving the doc 19 section 5 / section 5A ordering conflict.

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
| Modelling | V1-P1 AUTHORISED | `EXP-009` development-only under `DEC-051`; final test locked until V1-P5 |

Gate results recorded in this revision were reproduced independently rather than carried forward: Ruff clean, format clean across 83 files, strict mypy clean across 65 source files, `93 passed` with one expected ZIP warning, and `poetry check --lock` passing.

## State Synchronisation Status

| Item | Local | Drive |
|---|---|---|
| `PROJECT_STATE.md` | v49, 2026-08-16T13:59:36Z | v49, 2026-08-16T13:59:36Z |
| `DECISION_LOG.md` | DEC-001 to DEC-051 | DEC-001 to DEC-051 |
| `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` | sections 5 D1, 5A and 8 revised | sections 5 D1, 5A and 8 revised |

Mirrored document set, per `DEC-050`: the two control documents plus doc 19, which now carries specification content. Drive holds the numbered planning corpus plus these three; no non-numbered documents beyond the two control files.

Status: **SYNCHRONISED**

Both copies were reconciled during session `PAA-IMPL-20260816-01`. `DECISION_LOG.md` gains `DEC-051` and its Open Decisions section is updated; `PROJECT_STATE.md` advances to v49; doc 19 is unchanged this revision. All three pairs hash-match under LF normalisation. Drive mirrors are written in place at the mounted folder under `DEC-016`. The state records `76f4b08`, the committed tree before this control-document update; the commit containing the control update will be one commit later by design.
