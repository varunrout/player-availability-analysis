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

## 5. Analysis sequence

### Phase A: Cohort and label exploratory analysis

This is mandatory before fitting any model.

#### A1. Cohort integrity

Questions:

- Are there exactly one player-day row per player and prediction date?
- What are player observation lengths and their overlap by team/season?
- Does the 28-day burn-in disproportionately remove a team, player or time period?
- How many rows, episodes and positives remain for each horizon?

Outputs:

- Cohort flow table: all player-days -> complete-label days -> inactive-episode days -> burn-in eligible days.
- Player-day and episode counts by team, year and player.
- Missingness and feature-coverage table.

Red flags:

- A single player or a few dates dominate positive labels.
- The final cohort has very few events after burn-in.
- Feature coverage differs dramatically between future test and training periods.

#### A2. Outcome analysis

Questions:

- How many raw reports map to each primary episode?
- What is the distribution of episode duration and episode gap?
- What is label prevalence for 3/7/14 days?
- How concentrated are episodes by player, team and calendar month?

Outputs:

- Raw-report-to-episode compression table.
- Episode count and duration distribution.
- Label-prevalence table by horizon.
- Event timeline and concentration summary.

Interpretation discipline:

Describe these as self-reported injury-related events. Do not infer incidence of medically diagnosed injuries.

#### A3. Feature analysis

Questions:

- Are predictor ranges plausible and stable over time?
- Which wellness fields are missing together?
- How correlated are daily load, session sRPE and rolling summaries?
- Are player-relative z-scores available only after enough past observations?
- Is reporting completeness associated with team or season?

Outputs:

- Distribution and missingness table per predictor.
- Correlation matrix for candidate numeric predictors.
- Feature coverage by split.
- Outlier register: values investigated, retained, corrected or excluded.

No action is taken solely because a value is statistically extreme; source validity must be checked first.

### Phase B: Split construction and leakage audit

#### B1. Primary chronological split

Create a date-based development design before looking at model performance:

- Training: earliest approximately 60% of eligible calendar time.
- Validation: next approximately 20%.
- Final test: most recent approximately 20%.

Exact boundaries must be chosen from observed coverage, recorded once and not moved to improve a result. Every player-day belongs to exactly one chronological partition based on prediction date.

Use training for fitting, validation for feature-set/model/calibration choices, and test once for final evaluation of a frozen candidate.

#### B2. Rolling-origin validation

Within the development period, create expanding windows where each train period precedes its validation block. Use this to establish stability rather than select the one most favourable period.

#### B3. Unseen-player validation

Run leave-one-player-out after a stable temporal baseline exists. Preserve chronology inside each training fold. This is a generalisation stress test, not the primary tuning loop.

#### B4. Leakage test checklist

- Historical feature values are unchanged when future rows are appended.
- Baseline normalisation has no current/future observation contribution.
- Train-fitted preprocessors never consume validation/test rows.
- Predictor allow-list excludes labels, outcomes, IDs and post-event fields.
- Split assignment is date based and mutually exclusive.
- Calibration is trained on validation, not test.

### Phase C: Baseline modelling

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

Primary first target: 7-day event risk, subject to Phase A prevalence and practitioner utility review. Run 3 and 14 days as pre-specified comparisons rather than opportunistically selecting a winner.

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

### Phase D: Calibration and operational utility

#### D1. EXP-009: Calibration comparison

Compare raw logistic output, Platt scaling and isotonic regression. Fit calibrators on validation predictions only. Freeze the selected calibration approach before final test evaluation.

Required metrics:

- Brier score;
- calibration intercept and slope;
- reliability curve;
- expected calibration error where stable enough for sample size.

Decision gate:

- Prefer the simplest calibration approach that improves validation calibration without unstable step-like behaviour.

#### D2. EXP-019: Alert-budget simulation

Translate probability estimates into review workflow simulations:

- top 1, 3 and 5 players per day where available;
- top 5%, 10% and 20% of eligible player-days;
- alerts per 100 player-days;
- episode starts captured;
- false alerts per captured episode;
- persistence of consecutive-day alerts.

The selected threshold is a review-prioritisation policy. It is never a medical threshold.

### Phase E: Robustness and ablations

#### E1. EXP-004: Personalisation ablation

Compare F2 and F3 under identical split/model settings. Answer whether player-relative context provides measurable value.

#### E2. EXP-005: Horizon comparison

Compare 3, 7 and 14 days using the frozen feature and validation approach. Choose a primary operational horizon based on calibration, lead time, event count and alert burden.

#### E3. EXP-016: Missingness ablation

Compare model performance with and without wellness-completeness variables. If predictive, document the process-confounding limitation prominently.

#### E4. EXP-010: Leave-one-player-out

Report average, spread and worst-case results. If performance collapses, the dashboard claim must be restricted to within-observed-player temporal stratification.

### Phase F: Model ladder advancement

Only after Phases A-E are complete:

- EXP-006 discrete-time hazard model;
- EXP-007 Cox proportional-hazards baseline;
- EXP-008 boosted classification;
- EXP-014 survival forest or boosted survival;
- EXP-011/012 GPS pilot and objective-data ablation.

Each challenger must use the same frozen data version, split logic, calibration evaluation and alert simulation as the current champion.

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

For each completed phase store:

- versioned cohort summary;
- feature dictionary and predictor allow-list;
- split manifest;
- experiment configuration;
- metrics table;
- calibration and operational plots;
- model artefact where applicable;
- short decision note with Promote/Revise/Reject outcome.

All public-facing figures and reports must name the outcome as a self-reported injury-related event and disclose the main data limitations.

## 8. Immediate execution checklist

Before the first model fit:

1. Generate the Phase A cohort, outcome and feature-quality report.
2. Freeze and commit exact primary chronological split boundaries.
3. Implement predictor allow-list validation and split-leakage tests.
4. Run EXP-002 naive baseline for all three horizons.
5. Review baseline report before fitting logistic regression.

The next implementation action is Phase A reporting and split construction, not model tuning.
