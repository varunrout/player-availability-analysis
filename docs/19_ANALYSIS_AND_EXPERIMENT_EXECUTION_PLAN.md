# Analysis and Experiment Execution Plan

## Status and purpose

This document is the operational analysis runbook for Player Availability Analysis. It turns the project charter, feature strategy, outcome definition, validation plan and experiment backlog into a sequenced programme of analysis.

It is intended to prevent two failures:

1. Treating model fitting as the analysis.
2. Searching across algorithms, thresholds and labels until a flattering result appears.

The plan is hypothesis-led, chronological, reproducible and designed for practitioner decision support. A model output is an estimate that may warrant review; it is not a medical diagnosis, clearance decision or claim that injury is inevitable.

## 1. Analytical story

### 1.1 Operational problem

Practitioners receive daily athlete-monitoring information: training exposure, perceived load, wellness reports and, later, objective GNSS/GPS measurements. Raw values alone do not answer whether a player is in an unusual state, whether a recent pattern deserves extra review, or how confident anyone should be in that conclusion.

The system under study should help answer:

> Given information legitimately available for a player by the end of a given day, is there evidence that the player's short-term self-reported injury-episode risk is elevated relative to their own history, what signals contribute, and how uncertain is the estimate?

The target user is a practitioner who decides what to inspect next. The system does not decide training participation, medical treatment, selection or return to play.

### 1.2 Research objective

Establish whether longitudinal subjective athlete-monitoring signals can produce calibrated, explainable and operationally useful estimates of future self-reported injury-episode risk. Later stages test whether GPS-derived session summaries add value beyond the subjective foundation.

### 1.3 Data limitations that shape every conclusion

- Injury information is public, self-reported and not medically validated.
- The source reports calendar dates, not dependable intraday ordering.
- Player data comes from two elite women's football teams and must not be represented as evidence of performance in a men's first-team setting.
- Only 147 primary-rule self-reported episodes exist, so uncertainty and event concentration matter.
- Wellness reporting is incomplete. Missingness may represent process, availability or behaviour rather than physiology.

## 2. Current analytical assets

### 2.1 Versioned data products

| Product | Grain | Current state | Purpose |
|---|---:|---|---|
| Raw subjective staging | source file | complete | unchanged source preservation |
| Bronze subjective relations | daily metric, session, event | complete | source-grounded normalisation |
| Silver injury episodes | episode | 147 rows | self-reported outcome events |
| Gold player-day labels | player x date | 36,550 rows | censored 3/7/14-day targets |
| Gold subjective features v1 | player x date | 36,550 rows, 51 columns | M0 modelling input |

### 2.2 Frozen rules already accepted

- Primary unit: player x date.
- Prediction cutoff: end of calendar day.
- A future episode starts strictly after the prediction date.
- Incomplete future horizons are right-censored and represented as null labels.
- Active episode days are visible but excluded from primary new-onset modelling.
- Injury components are exact-deduplicated and merged by player plus raw location using a three-day gap.
- Feature windows use same-day-or-earlier values under the cutoff convention.
- Player baseline features use prior observations only.
- Random row-level splitting is prohibited for headline results.

### 2.3 Current M0 candidate predictors

The initial model must use an explicit allow-list. It must not select IDs, dates, labels, eligibility flags, episode-state fields or data provenance fields as predictors.

Candidate groups:

- Current state: `daily_load`, `fatigue`, `readiness`.
- Recent load: daily-load and session-duration/sRPE sums over 3, 7, 14 and 28 days.
- Recent wellness: fatigue and readiness means over 3, 7, 14 and 28 days.
- Data completeness: wellness report-present flag and wellness metric count.
- Personalisation: prior-only player baseline means and z-scores for daily load, fatigue and readiness.

The initial baseline should remove exact deterministic duplicates and heavily coupled variants where needed. For example, a model should not be judged on a feature set inflated by several near-identical load summaries.

## 3. Questions, hypotheses and evidence standard

### RQ1: Is there any useful prospective signal?

**Hypothesis H1:** A regularised subjective model improves on a naive event-rate benchmark for Brier score and PR-AUC under chronological evaluation.

Evidence needed:

- Improvement against the same held-out dates.
- Confidence intervals clustered by player where feasible.
- No suspicious feature or split leakage.
- Operational review metrics, not only discrimination.

Failure interpretation:

- If performance is indistinguishable from prevalence, report that the current subjective signals do not support useful prospective stratification in this cohort.

### RQ2: Does player-relative context help?

**Hypothesis H2:** Prior-only player-relative features improve prospective performance compared with absolute values alone.

Evidence needed:

- A pre-specified ablation with the same split, label, preprocessing and model family.
- Improvement in Brier score or PR-AUC that is stable across validation windows.
- No collapse in unseen-player evaluation.

Failure interpretation:

- If player-relative features help only players seen in training, they may reflect individual memorisation rather than transferable context.

### RQ3: Which horizon is useful?

**Hypothesis H5:** The 3, 7 and 14-day horizons trade off actionability, event capture and alert burden.

Evidence needed:

- Prevalence, calibration, PR-AUC, recall at fixed review capacity and median lead time for each horizon.
- The primary dashboard horizon is selected for practical decision support, not highest AUROC alone.

### RQ4: Is missingness informative or a process artefact?

**Hypothesis H4:** Missingness indicators may contain signal but need cautious interpretation.

Evidence needed:

- Ablation with and without completeness fields.
- Missingness distributions by team, season and event history.
- Clear note that any signal can reflect reporting process rather than physiology.

### RQ5: How much generalisation remains for unseen players?

**Hypothesis H7:** Performance degrades under leave-one-player-out evaluation.

Evidence needed:

- Compare temporal within-player result with held-out-player result.
- Report distribution, not just mean performance.
- Investigate whether a small number of players dominate either outcome.

### Deferred questions

- GPS incremental value: deferred until a one-team/one-season objective pilot creates verified session summaries.
- Survival value: deferred until fixed-horizon baseline and cohort logic are stable.
- Deep models: deferred unless simpler models demonstrate a measurable limitation that event count can support.

## 4. Experiment operating rules

### 4.1 Experiment record

Every run receives an immutable experiment ID, for example `EXP-003-R01`. Record:

- objective and hypothesis;
- source, episode, label and feature versions;
- Git commit;
- cohort filters and row/event counts;
- predictor allow-list;
- train, validation and test date boundaries;
- preprocessing fit scope;
- model family, hyperparameters and random seed;
- calibration method and its fitting data;
- metrics and confidence intervals;
- alert-policy metrics;
- interpretation, limitations and next decision.

No experiment may overwrite a prior result. A revised implementation receives a new run ID and links back to the prior one.

### 4.2 Cohort eligibility

The primary fixed-horizon cohort includes a player-day only when:

1. the selected horizon label is complete, not null;
2. the day is eligible for new-onset modelling;
3. the required feature history is present under the chosen burn-in rule;
4. the player is in the observed player registry window.

The primary headline analysis uses a 28-day burn-in because the feature set contains 28-day windows. A sensitivity analysis may later allow partial history with explicit reliability indicators.

### 4.3 Preprocessing rules

- Fit imputation, scaling, feature selection and calibration only on the appropriate training or validation partition.
- No global whole-season standardisation.
- Do not one-hot encode `player_id` for headline models.
- Do not use injury episode attributes as predictors for a future injury target in M0.
- Missingness indicators may be predictors only when their definition uses data available at cutoff.
- Do not use random oversampling or SMOTE across player-days.

### 4.4 Decision gates

An experiment can be:

- **PROMOTE:** supports the next model or product step.
- **REVISE:** implementation, cohort or analysis needs correction; no performance claim is retained.
- **REJECT:** no sufficient incremental value, unstable result or unacceptable leakage/operational burden.

No algorithm advances merely because it has a higher AUROC.

## 5. Stage-gated pre-model analysis sequence

The former bundled "Phase A" report and "Phase B" split are withdrawn. Pre-model analysis now proceeds through the following explicit stages. Every stage follows the same gate: approve the specification, implement the script and notebook interfaces, run the script, inspect outputs, discuss findings, then approve or revise before continuing.

No baseline model may be fitted before Stage 8 receives a `READY` decision.

### Stage 0: Analysis inventory and data audit

- Verify analytical tables, grains, keys, schemas, row counts and date coverage.
- Reconcile raw, bronze, silver and gold counts relevant to analysis.
- Audit duplicate keys, player observation lengths, calendar continuity and unsupported fields.
- Produce dataset inventory, cohort-coverage figures, player observation-length figures and a data-quality exceptions table.

Gate: confirm that the analytical dataset is trustworthy enough for EDA.

### Stage 1: Injury episode and outcome EDA

- Analyse raw reports versus episodes, repeated reporting, episode duration, location and supported severity fields.
- Compare the pre-specified 1-, 3- and 7-day episode-gap rules.
- Measure active-episode days, right censoring, 3/7/14-day label prevalence and horizon overlap.
- Quantify how many distinct episodes sit behind positive player-days and how events are concentrated by player, team and calendar period.

Gate: approve the primary episode rule and confirm that outcome labels are credible enough to continue.

### Stage 2: Missingness and reporting-process EDA

- Measure feature coverage by player, team and calendar period.
- Analyse missing-run lengths, co-missingness and wellness-report frequency.
- Compare complete and incomplete reporting periods, including context around episode starts.
- Treat missingness as a possible process signal; do not automatically interpret it as physiology.

Gate: approve missing-value handling, reporting-indicator eligibility and any cohort exclusions.

### Stage 3: Feature distribution and temporal EDA

- Profile distributions, zeros, extreme values and plausible ranges for load, wellness and session variables.
- Separate within-player from between-player variation and compare supported team/calendar strata.
- Inspect rolling 3/7/14/28-day features, prior-only baselines and z-score stability.
- Maintain an outlier register; statistical extremeness alone never justifies correction or deletion.

Gate: approve valid ranges, transformations and reliable feature families.

### Stage 4: Feature redundancy and structural relationships

- Measure correlation and near-deterministic relationships among current, rolling and player-relative features.
- Audit coupling among daily load, duration and sRPE and among wellness/completeness variables.
- Define a full candidate contract and a smaller operational feature-family contract without using target performance.

Gate: approve the predictor contracts to carry into prospective testing.

### Stage 5: Descriptive outcome-context analysis

- Describe pre-episode feature trajectories and compare them with suitable non-event reference periods.
- Examine player-relative, player-stratified and team-stratified patterns.
- Determine whether apparent patterns are dominated by a few players or reporting behaviour.
- Make no predictive, causal or medical claim from these retrospective descriptions.

Gate: decide which descriptive patterns merit prospective testing.

### Stage 6: Cohort and outcome sensitivity analysis

- Compare episode-gap, prediction-horizon, burn-in and missingness-aware cohort choices.
- Quantify changes in sample size, positive counts, player/team representation and event concentration.
- Freeze primary and secondary analysis specifications only after reviewing these sensitivities.

Gate: approve the primary cohort, horizon, episode definition and required later sensitivities.

### Stage 7: Final pre-model protocol and leakage audit

- Freeze cohort eligibility, feature history, predictor contract, preprocessing, metrics, uncertainty and alert-capacity rules.
- Construct chronological train/validation/test boundaries only after the preceding EDA is approved.
- Audit boundary embargoes, future-append invariance, prior-only normalisation and train-only preprocessing.
- Define rolling-origin development and leave-one-player-out stress testing without inspecting final test performance.

Gate: approve the complete prospective evaluation protocol and lock final-test access.

### Stage 8: Pre-model readiness report

- Consolidate data strengths, limitations, outcome validity, missingness risks, feature behaviour, cohort decisions and leakage controls.
- Record the final hypotheses and modelling protocol.
- End with one explicit decision: `READY`, `REVISE` or `DO NOT MODEL`.

Only `READY` permits baseline modelling.

### Analysis implementation and output contract

- Shared reusable analysis logic belongs under `src/player_availability/analysis/`.
- Reproducible command-line runners belong under `jobs/analysis/` and are the canonical way to generate retained outputs.
- Retained outputs belong under `outputs/analysis/<stage>/`, using nested `figures/`, `tables/`, `reports/` and `metadata/` folders when applicable.
- A matching notebook belongs under `notebooks/analysis/` for quick inspection and explanation of each stage.
- Scripts and notebooks import the same shared analysis functions; analytical logic is not independently reimplemented in two places.
- Notebooks render tables and charts inline but do not write files to `outputs/` or another persistent output location.
- Committed notebooks are cleared of cell outputs and execution counts.
- Script-generated outputs are reviewed with the project owner before the next stage begins.

### Post-gate baseline modelling

### Baseline modelling

#### C1. EXP-002: Naive operational baselines

Purpose: establish the minimum performance that a learned model must beat.

Baselines:

1. Global training-period event prevalence.
2. Recent event-rate or recency heuristic only if the required past-event feature is introduced leak-safely.
3. Simple pre-specified recent-load review rule, presented as a descriptive heuristic rather than a causal threshold.

For every baseline report Brier score, PR-AUC where a score varies, prevalence, alert burden and recall at fixed review capacity.

Decision gate:

- A learned M1 model must improve calibration or operational capture relative to this benchmark under the same test dates.

#### C2. EXP-003: Regularised logistic regression

Purpose: interpretable fixed-horizon benchmark.

Primary first target: 7-day event risk, subject to Stage 1 outcome EDA and Stage 6 sensitivity approval. Run 3 and 14 days as pre-specified comparisons rather than opportunistically selecting a winner.

Feature sets:

- F0: global rate only.
- F1: absolute subjective load and wellness.
- F2: F1 plus session exposure and missingness.
- F3: F2 plus player-relative features.

Model rules:

- Regularisation strength selected only on chronological validation.
- Scaling learned only on training data.
- Class weighting considered only if validation metrics and calibration support it.
- No player identifier predictor.

Outputs:

- Coefficients with training-only standardisation context.
- Validation and final test metrics.
- Reliability curve and calibration slope/intercept.
- Predictor availability report.

Decision gate:

- Promote F3 only if it beats F2 on pre-specified validation criteria without worse calibration or an unacceptable alert burden.

### Calibration and operational utility

#### D1. EXP-009: Calibration comparison

**Status:** specified, awaiting approval. Phase V1-P1. Authorised by `DEC-044`.

Compare raw logistic output, Platt scaling and isotonic regression on the F3 candidate promoted by `DEC-043`. Freeze the selected calibration approach before final-test evaluation.

**Why this experiment exists.** M1 raw probabilities are materially overestimated: mean prediction 1.965% against an observed positive-day rate of 0.322%, roughly a sixfold overstatement, with calibration intercept -0.356 and slope 1.433. M1 records worse Brier and log loss than the M0 baseline despite better ranking. Under `DEC-007` a ranking gain accompanied by degraded probability quality cannot be promoted.

**Arms.** Raw F3 as reference; Platt on the F3 log-odds; isotonic. F1 raw is carried as a secondary reference so the calibration question stays separable from the feature-set question settled in `DEC-043`. Isotonic is included despite being the method most likely to overfit at this support; demonstrating that it overfits here is itself a reportable result.

**Fitting discipline.** Calibrators are fitted fold-wise within the pooled rolling-origin structure: in each fold the calibrator is fitted on that fold's training portion and applied to its held-out portion, then metrics are pooled. Calibrator fitting partitions are always disjoint from evaluation partitions, because fitting a calibrator on the rows used to score it manufactures apparent improvement. This supersedes the earlier validation-only fitting rule under `DEC-049`. Development partitions only; final-test data is neither read nor scored. Preprocessing scope, cohort, predictor contract, partitions and embargoes are unchanged.

Required metrics, per arm, pooled rolling-origin:

- Brier score and log loss;
- calibration intercept and slope;
- reliability curve with bin counts shown rather than implied;
- expected calibration error, reported only where bin support permits;
- mean predicted risk against observed rate.

Secondary: the same metrics on the fixed chronological validation window as a temporal stress result; per-fold values for every pooled figure; the one-day-gap sensitivity required by `DEC-048`; alert-budget behaviour at the frozen 1%, 2.5% and 5% review rates. Uncertainty uses paired bootstrap intervals under both player-cluster and temporal week-block resampling, matching the EXP-003 protocol so results stay comparable.

**Mandatory sparse-predictor audit**, required by `DEC-043`. The robust fatigue z-score is observed on 8.4% of primary-cohort days. Report calibration metrics separately on days where it is observed against days where it is absent, and state whether calibrated performance depends on the predictor's availability pattern rather than its value. If behaviour differs materially, the predictor is acting as a proxy for reporting activity rather than physiology and becomes a removal candidate at V1-P4.

**Power limitation, binding on reporting.** Development support is 56 onsets in train and five in the validation window. Every conclusion states its supporting event count inline, not in a footnote. No method is declared superior on point estimates alone; a difference is claimed only where the paired interval excludes zero. "No calibration method is distinguishable at this support" is a valid, expected and complete result, and must be reported as such rather than resolved by selecting the best point estimate. Reliability bins holding fewer than five positive days are reported with counts and excluded from summary statistics that assume bin stability.

Automated integrity checks:

| ID | Check |
|---|---|
| CAL-01 | Zero final-test predictions or performance metrics produced |
| CAL-02 | Calibrator fitting partitions disjoint from evaluation partitions in every fold |
| CAL-03 | Predictor contract unchanged from the frozen F3 contract |
| CAL-04 | Ranking preserved under Platt, since a monotonic transform must not alter order |
| CAL-05 | Every reported metric carries its supporting event count |
| CAL-06 | Sparse-predictor availability audit present and populated |
| CAL-07 | One-day-gap sensitivity present for every headline figure |
| CAL-08 | Zero-positive folds identified and excluded from discrimination aggregation, with counts stated |

Decision gate:

- Prefer the simplest calibration approach that improves calibration without unstable step-like behaviour.
- Success does not require finding a method that improves calibration. The experiment succeeds if calibration behaviour is characterised honestly and the sparse-predictor audit is completed.
- Non-goals: selecting a deployment threshold, accessing final-test data, changing the feature set or cohort, retuning the model.

#### D2. EXP-019: Alert-budget simulation

Translate probability estimates into review workflow simulations:

- top 1, 3 and 5 players per day where available;
- top 5%, 10% and 20% of eligible player-days;
- alerts per 100 player-days;
- episode starts captured;
- false alerts per captured episode;
- persistence of consecutive-day alerts.

The selected threshold is a review-prioritisation policy. It is never a medical threshold.

### Robustness and ablations

#### E1. EXP-004: Personalisation ablation

Compare F2 and F3 under identical split/model settings. Answer whether player-relative context provides measurable value.

#### E2. EXP-005: Horizon comparison

Compare 3, 7 and 14 days using the frozen feature and validation approach. Choose a primary operational horizon based on calibration, lead time, event count and alert burden.

#### E3. EXP-016: Sparse-predictor availability ablation

**Status:** specified, authorised by `DEC-052`. Must complete before phase V1-P2.

Determine whether the contribution of `fatigue_lag1_robust_z_prior` to F3 is carried by its availability pattern rather than its value.

**Why this experiment exists.** The `EXP-009` mandatory sparse-predictor audit found that F3's discrimination differs sharply by whether the robust fatigue z-score is observed: ROC-AUC 0.732 on the 2,475 player-days where it is present (2.46% prevalence) against 0.908 on the 14,340 player-days where it is absent (0.30% prevalence). A predictor carrying physiological signal would be expected to discriminate at least as well where observed. This pattern, together with the Stage 2 finding that wellness reporting rises from 62.9% to 97.3% around onset days, raises a direct question over whether F3's held-period advantage under `DEC-043` is a reporting artefact rather than a physiological signal, and every phase from V1-P2 onward is built on F3.

**Arms.** All under the frozen F3 engine: unchanged cohort, partitions, embargoes, preprocessing scope and regularisation grid.

- **A.** F3 exactly as promoted under `DEC-043`. Reference.
- **B.** F3 with `fatigue_lag1_robust_z_prior` removed entirely, both the value and its paired recording-state indicator (`fatigue_robust_available`).
- **C.** F3 with the value removed but the recording-state indicator retained.
- **D.** F1 carried forward as external reference.

Arm C is the discriminating arm and must not be dropped. If C is indistinguishable from A, the value contributes nothing and availability is doing the work. If C is indistinguishable from B, the indicator contributes nothing either. These are different conclusions with different consequences for predictor design.

**Evaluation**, identical to `EXP-009` so results are comparable:

- Pooled rolling-origin headline using raw probabilities per `DEC-052`, with estimable-fold counts and per-fold values.
- Brier score, log loss, calibration intercept and slope, average precision, ROC-AUC.
- Fixed chronological window as a temporal stress result.
- One-day-gap sensitivity on every headline figure, per `DEC-048`.
- Alert-budget behaviour at the frozen 1%, 2.5% and 5% review rates.
- Paired bootstrap intervals for B, C and D against arm A under both player-cluster and temporal week-block resampling.

**Mandatory and non-negotiable.** Support-aware unseen-player generalisation is reported for every arm, including A. `DEC-043`'s binding limitation is that F3 generalises worse than F1 to unseen players (AP 0.022308 against 0.023316; ROC-AUC 0.630928 against 0.642578). If B or C closes that gap, that is the decisive result of this experiment and must be reported as such, not folded into the general metrics table.

**Power limitation, binding on reporting.** Development support is unchanged from `EXP-009`: 104 pooled positive player-days across three estimable rolling-origin folds under the primary three-day gap. Every conclusion states its supporting event count inline. "Not distinguishable at this support" is a valid and expected result for any pairwise arm comparison.

Automated integrity checks:

| ID | Check |
|---|---|
| ABL-01 | Zero final-test predictions or performance metrics produced |
| ABL-02 | Arm contracts differ only in `fatigue_lag1_robust_z_prior` and its recording-state indicator; all other predictors identical across A, B, C |
| ABL-03 | Preprocessing and regularisation grid unchanged across all four arms |
| ABL-04 | Every reported metric carries its supporting event count |
| ABL-05 | One-day-gap sensitivity present for every headline figure |
| ABL-06 | Zero-positive folds identified, excluded from discrimination aggregation and counted |
| ABL-07 | Support-aware unseen-player aggregation present for all four arms |

Decision gate:

- If B or C matches or beats A on calibrated probability quality and improves unseen-player generalisation, `DEC-043` is reopened and the champion is re-selected through a new decision before V1-P2 begins.
- If A remains best on both axes, F3 stands and the availability entanglement is documented as a binding limitation on every downstream citation, alongside the five limitations already bound by `DEC-043`.
- "Not distinguishable at this support" remains a valid and expected result.
- Non-goals: final-test access, new features, retuning beyond the frozen grid, threshold selection, champion replacement without a decision record.

#### E4. EXP-010: Leave-one-player-out

Report average, spread and worst-case results. If performance collapses, the dashboard claim must be restricted to within-observed-player temporal stratification.

### Model ladder advancement

For the general experiment backlog: only after the baseline, calibration, operational-utility and required robustness analyses are complete. **For the V1 programme, this ordering is superseded by section 5A under `DEC-053`**: `EXP-007` (V1-P2) and `EXP-008` (V1-P3) proceed ahead of the V1-P4 operational-utility work, not after it. Section 5A is the sequencing authority for V1.

- EXP-006 discrete-time hazard model;
- EXP-007 Cox proportional-hazards baseline;
- EXP-008 boosted classification;
- EXP-014 survival forest or boosted survival;
- EXP-011/012 GPS pilot and objective-data ablation.

Each challenger must use the same frozen data version, split logic, calibration evaluation and alert simulation as the current champion.

#### F1. EXP-007: Cox proportional-hazards survival

**Status:** specified, authorised by `DEC-054`. Phase V1-P2.

Test whether a time-to-event framing adds practitioner value over the fixed-horizon F1 champion selected under `DEC-054`.

**Why this experiment exists.** The charter requires an explicit conclusion on whether survival framing adds value; `EXP-006`/`EXP-007` are the modelling response most appropriate to sparse support, since time-to-event framing uses censoring and the full event set rather than a fixed seven-day window. `DEC-054` reopened `DEC-043` and selected F1, with no reporting-derived predictor, as the champion; this experiment tests the framing question against that champion, not against F3.

**Data structure.** Counting-process start-stop format over the frozen player-day panel: one interval per eligible player-day, time-varying covariates at the prediction cutoff. Recurrent onsets are modelled under Andersen-Gill with variance clustered on player. The at-risk definition follows the frozen cohort exactly; active-episode days remain ineligible; the 28-day burn-in is unchanged. Right-censoring occurs at partition boundaries; no interval crosses a partition. The time scale is gap time since the previous onset, with post-burn-in study entry as origin for players with no prior onset. Ties are handled by the Efron approximation.

**Gap-time constraint, binding on all future survival work including `EXP-014` in V2.** Under leave-one-player-out evaluation, a gap-time origin derived from the held-out player's own onsets breaches the premise of the evaluation and inflates it: the baseline hazard is highest at short gap times, so indexing a held-out player by their own onset history supplies outcome information a genuinely unseen player would never expose. Gap time remains legitimate under temporal evaluation, since time since a player's last injury is genuinely known at prediction time. Leave-one-player-out survival evaluation must reset the clock for every held-out player to post-burn-in study origin, treating them as having no prior onset. This was discovered as an executed finding in `EXP-007` and is recorded here so it is not repeated in `EXP-014`.

**Predictors.** Exactly F1's nine predictors per `DEC-054`, unchanged: `daily_load_log1p`, `daily_load_sum_7d_log1p`, `daily_load_sum_28d_log1p`, `fatigue_lag1`, `fatigue_mean_prior_7d`, `fatigue_mean_prior_28d`, `readiness_lag1`, `readiness_mean_prior_7d`, `readiness_mean_prior_28d`. A ridge penalty is selected only on chronological validation folds, mirroring the C-selection discipline in `EXP-003`.

**Missing data.** F1 contains no sparse availability-driven predictor, so the asymmetry that motivated `EXP-016` does not arise here. Lagged wellness terms are present on roughly 46.5% of player-days; their treatment must match exactly what F1 already uses in `EXP-003`. Any deviation is reported explicitly.

**Comparability, the critical step.** A Cox fit yields a hazard, not a seven-day probability. Convert with the Breslow baseline cumulative hazard, `P(event within 7 days) = 1 - exp(-(H0(t+7) - H0(t)) * exp(X'b))`, with the baseline estimated on training portions only, fold-wise, never on evaluation rows. Evaluate the resulting probability with exactly the metrics used in `EXP-003`, `EXP-009` and `EXP-016`. Raw probabilities per `DEC-052`; no calibrator.

Required outputs: coefficients with hazard ratios and intervals; pooled rolling-origin Brier, log loss, calibration intercept and slope, reliability with bin counts, average precision, ROC-AUC; per-fold values and estimable-fold counts; fixed window as temporal stress; one-day-gap sensitivity on every headline figure; alert budgets at 1%, 2.5% and 5%; support-aware unseen-player aggregation; paired bootstrap against F1 under both player-cluster and temporal week-block resampling; scaled Schoenfeld residuals, global and per covariate.

**Two binding reporting limitations.** Cluster-robust variance rests on roughly 12 event-bearing player clusters; sandwich estimators are anti-conservative well above that count, so a player-cluster bootstrap is reported alongside and the bootstrap is treated as primary where they disagree. Proportional-hazards tests have very low power at 66 onsets; a non-significant Schoenfeld result is not evidence the assumption holds and must not be reported as though it were.

Automated integrity checks:

| ID | Check |
|---|---|
| COX-01 | Zero final-test access |
| COX-02 | Risk-set construction matches the frozen cohort day for day |
| COX-03 | No interval crosses a partition or embargo |
| COX-04 | Predictor contract identical to F1 |
| COX-05 | Baseline hazard fitted only on partitions disjoint from evaluation |
| COX-06 | Converted probabilities in [0, 1] and monotone in the linear predictor |
| COX-07 | Every reported metric carries its supporting event count |
| COX-08 | One-day-gap sensitivity present; zero-positive folds identified, excluded and counted |
| COX-09 | Leave-one-player-out evaluation does not use held-out player outcome history in the time coordinate; both clock variants are reported |

Decision gate:

- Adopt the survival framing only if probability quality or operational capture improves over F1 with paired intervals excluding zero under both resampling schemes.
- Explicit rejection with evidence is a successful outcome and closes the phase.
- "Not distinguishable at this support" is valid and expected.
- Non-goals: final-test access, feature or cohort change, threshold selection, champion replacement outside V1-P4.

## 5A. V1 delivery programme

Governing decision: `DEC-046`. Evaluation protocol: `DEC-047`. Outcome sensitivity: `DEC-048`.

This section sequences the experiments above into a shippable V1. It allocates no new experiment identifiers; every phase maps onto an experiment already registered in this document and in `13_EXPERIMENT_BACKLOG_AND_DECISION_LOG.md`.

### What V1 is

A complete subjective-data decision-support system, released as an operable product with an honest account of what it can and cannot support. **The headline evidence is methodological, not performance.** No V1 artefact presents discrimination as the primary result.

### Why the goal is framed this way

Effective outcome support is the binding constraint on everything downstream.

| Measure | Value |
|---|---|
| Represented onsets, frozen cohort | 66 |
| Onsets in train / validation / final test | 56 / 5 / 5 |
| Share of onsets from top five players | 74.6% |
| Players with any event, development | 12 of 50 |
| Onset decline, 2020 to 2021 | roughly tenfold, at flat player-days |

The 2021 collapse tracks reporting engagement rather than injury incidence, consistent with the Stage 2 finding that wellness reporting rises from 62.9% on ordinary days to 97.3% on onset days. The dataset supports a well-built system and an honest uncertainty account. It does not support a claim that injuries are predicted.

### Phases

Each phase carries an owner approval gate on its specification before implementation, and on its results before the next phase begins, exactly as Stages 0 to 8 did.

| Phase | Work | Experiment ID | Exit criterion |
|---|---|---|---|
| V1-P1 | Calibration | EXP-009 | Calibration characterised; sparse-predictor audit complete; "not distinguishable" accepted in advance as valid |
| V1-P2 | Cox survival | EXP-007 | Explicit evidence-backed conclusion on whether time-to-event framing adds practitioner value; rejection with evidence is a successful outcome |
| V1-P3 | Boosted classification | EXP-008 | Recorded verdict on whether nonlinearity earns its place at this sample size; a negative result is expected and reportable as-is |
| V1-P4 | Champion selection, explainability, operational utility | EXP-018 explanation stability, EXP-019 alert-budget simulation; selection itself is a gate, not an experiment | Champion recorded with rationale; explanation stability measured; no final-test access |
| V1-P5 | Pre-registration and final test | Governance gate, no experiment identifier | Final test executed once against pre-registered claims, results reported whether favourable or not |
| V1-P6 | Product: batch inference and dashboard | Not an experiment | A reviewer can operate the product and correctly understand both output and limits without reading code |
| V1-P7 | Operationalisation: containers, CI, monitoring, cost | Not an experiment | Reproducible from a clean clone; CI enforcing gates currently run by hand |
| V1-P8 | Release evidence | Not an experiment | Every external claim traceable to a measured result |

Robustness experiments already registered here, principally EXP-004 personalisation, EXP-005 horizon, EXP-010 leave-one-player-out and EXP-016 missingness, are executed within the phase whose conclusion depends on them rather than as a separate phase.

Deferred to V2: EXP-011 and EXP-012 GPS work, EXP-015 neural survival, and online serving.

### V1 definition of done

**Methodology**
- Calibration characterised for the champion, with reliability curve, slope, intercept and expected calibration error.
- Pooled rolling-origin reported as primary, with estimable-fold counts stated and per-fold results shown.
- Unseen-player generalisation reported with support-aware aggregation.
- One-day-gap sensitivity reported for every headline result.
- Leakage suite passing, including future-append invariance.
- Survival framing either adopted or explicitly rejected with evidence.
- Complexity verdict recorded for boosted classification.

**Product**
- Batch inference writing to `paa_product`.
- Dashboard covering squad overview, player detail, data quality and model health.
- Every risk figure displayed with uncertainty and data-completeness context.
- No prohibited language anywhere in the interface.

**Engineering**
- Containerised and reproducible from a clean clone.
- CI running lockfile, lint, types, tests and leakage checks.
- Cost recorded and within envelope.

**Evidence**
- Model card leading with limitations.
- Final test spent exactly once against pre-registered claims.
- README, architecture diagram, case study, interview narrative.

### Sequencing rules

1. Specification approved before implementation; results approved before the next phase. No exceptions.
2. The final test is touched only in V1-P5, once. This is irreversible: no tuning, feature change or model change may follow, and any second access requires a new superseding decision.
3. No GPS or objective processing during V1.
4. Any material design change requires a decision record before the work, not after.
5. V1-P1 through V1-P3 may be reordered if evidence justifies it; V1-P4 onwards is strictly ordered.

### Scope control

If time pressure rises, cut in this order: the boosted-classification complexity test, recording the omission; then the API layer, keeping the dashboard; then monitoring depth, keeping data-quality surfaces.

Never cut: leak-safe validation, calibration, the limitations account, the model card, the dashboard, or single-use final-test discipline.

### Risks

| Risk | Mitigation |
|---|---|
| Sparse events make every comparison inconclusive | Pooled rolling-origin under `DEC-047`; "not distinguishable" pre-accepted as a valid finding |
| Event concentration in five players | Support-aware unseen-player aggregation; concentration restated wherever performance is cited |
| Reporting engagement decays over time | Documented dataset property; reporting-derived predictors remain under audit per `DEC-031` |
| Sparse robust-fatigue predictor drives apparent F3 gain | Explicit audit in V1-P1; removal candidate at V1-P4 |
| Temptation to revisit the final test | Single-use rule; second access requires a superseding decision |
| Overclaiming in portfolio material | Every external claim traced to a measured result before release |

## 6. Metrics and interpretation

### 6.1 Required classification metrics

| Metric | What it answers | Limitation |
|---|---|---|
| Prevalence | How common are positives? | Not predictive performance |
| PR-AUC | How useful is ranking among rare events? | Can be unstable with few events |
| ROC-AUC | Broad ranking ability | Can look optimistic in rare events |
| Brier score | Probability accuracy | Depends on baseline prevalence |
| Log loss | Penalised probability accuracy | Sensitive to extreme predictions |
| Calibration slope/intercept | Are probabilities too extreme or shifted? | Needs adequate event count |
| Recall at review capacity | How many later episodes enter review? | Depends on policy |
| False alerts per captured event | Review burden | Does not quantify clinical cost |

Accuracy is not a headline metric.

### 6.2 Confidence and uncertainty

Use player-clustered bootstrap intervals where sample size permits. Do not bootstrap individual player-days independently because repeated daily observations are dependent.

If intervals are very wide, that is a finding. Avoid confident language when the outcome count cannot support it.

### 6.3 Model acceptance criteria

A candidate is not accepted as champion if:

- chronological benefit disappears or reverses on the final test;
- calibration is poor and cannot be stably corrected;
- observed performance is driven by one player, one team or one time block;
- unseen-player results are near chance;
- alert volume is impractical for review;
- a forbidden predictor or leakage issue is found;
- explanation changes materially with trivial input variation.

## 7. Required artefacts

For each completed stage or modelling experiment, the script stores retained artifacts under `outputs/analysis/<stage>/` or the corresponding later experiment folder:

- versioned cohort summary;
- feature dictionary and predictor allow-list;
- split manifest;
- experiment configuration;
- metrics table;
- calibration and operational plots;
- model artefact where applicable;
- short decision note with Promote/Revise/Reject outcome.

Notebook-rendered outputs are exploratory views and are not stored. All public-facing figures and reports must name the outcome as a self-reported injury-related event and disclose the main data limitations.

## 8. Immediate execution checklist

Completed: Stages 0 through 8 approved sequentially; Stage 8 returned `READY`; EXP-002 naive baselines accepted under `DEC-040`; EXP-003 M1 logistic and the F1/F2/F3 feature ladder completed, with F2 rejected and F3 promoted as the raw candidate under `DEC-043`.

Current position: phase V1-P1, EXP-009 calibration. The specification is section 5 D1 of this document and awaits project-owner approval.

Next actions:

1. Approve the EXP-009 specification and the V1 delivery programme in section 5A.
2. Implement EXP-009 as shared analysis code, canonical script, matching output-free notebook, retained tables and figures, and focused tests, per `DEC-029`.
3. Execute against development data only, fitting calibrators fold-wise on partitions disjoint from evaluation.
4. Complete the mandatory sparse-predictor availability audit.
5. Review results at the V1-P1 gate, then proceed to V1-P2 Cox survival under EXP-007.

Final-test predictions and performance remain locked until V1-P5. No analysis script is built until the relevant specification is approved.
