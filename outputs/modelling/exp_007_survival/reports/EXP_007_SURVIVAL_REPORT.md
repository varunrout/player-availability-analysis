# EXP-007 - Cox Proportional-Hazards Survival Report

## Automated Status

Development run: **PASS**. Project-owner survival-framing review required.

Andersen-Gill counting-process Cox model over the F1 champion's nine predictors (`DEC-054`), gap-time clock, Efron ties, Breslow baseline hazard converted to a seven-day probability. Raw probabilities only, per `DEC-052`. No final-test row is read or scored.

## Library Constraint (disclosed, not worked around silently)

The installed lifelines `CoxTimeVaryingFitter` does not implement cluster-robust sandwich variance or scaled Schoenfeld residuals for time-varying counting-process fits. Coefficient standard errors below are model-based (naive), not cluster-robust. The player-cluster and temporal week-block paired bootstrap against F1 is the primary inferential evidence, per the specification's own instruction for when methods disagree. The proportional-hazards check below uses a covariate-by-log-time interaction likelihood-ratio test as a substitute for Schoenfeld residuals.

## Pooled Rolling-Origin Comparison

| Arm | Pooled +days | Brier | Log loss | Calib. slope | Discrim. +days | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| cox | 104 | 0.005929 | 0.130114 | 0.120283 | 104 | 0.075470 | 0.711325 |
| f1_logistic | 104 | 0.006325 | 0.042009 | 2.019474 | 104 | 0.096668 | 0.835537 |

## Unseen-Player Generalisation (mandatory)

Leave-one-player-out is evaluated in two clock variants for the Cox arm, using the identical fitted model in both cases. **`reset_clock` is the valid leave-one-player-out result**: it treats the held-out player as having no prior onset, entering at post-burn-in study origin, matching the premise that nothing about a genuinely unseen player may be assumed known. **`own_clock` is retained only as a leakage diagnostic contrast**, not a competing headline figure: it uses the held-out player's own gap-time clock, derived from that player's own onset history. F1 has no time-coordinate concept and is evaluated once.

| Arm | Clock | Role | AP | ROC-AUC | Estimable players | Zero-positive players |
|---|---|---|---:|---:|---:|---:|
| cox | reset_clock | primary_leave_one_player_out_result | 0.019293 | 0.576890 | 12/50 | 38 |
| cox | own_clock | leakage_diagnostic_contrast | 0.104533 | 0.817861 | 12/50 | 38 |
| f1_logistic | not_applicable | primary_leave_one_player_out_result | 0.023316 | 0.642578 | 12/50 | 38 |

### Mechanism (leakage diagnostic)

Under `own_clock`, Cox recorded AP 0.104533 and ROC-AUC 0.817861 on leave-one-player-out, the hardest evaluation in the protocol, exceeding both its pooled rolling-origin and fixed-window results by a wide margin — an inverted ordering that does not occur for F1. The baseline cumulative hazard is highest at short gap times, so indexing a held-out player by their own time since previous onset supplies outcome information about that player that a genuinely unseen player would never expose; F1 has no equivalent access. Resetting the clock collapses the result to AP 0.019293 and ROC-AUC 0.576890, both below F1's 0.023316 and 0.642578, and restores the expected ordering in which leave-one-player-out is Cox's weakest view, matching F1's pattern. This confirms the leakage hypothesis under the criterion specified in advance of the diagnostic. A gap-time origin derived from a player's own onset history is legitimate under temporal evaluation, where that history is genuinely known at prediction time, but breaches the premise of leave-one-player-out evaluation, where nothing about the held-out player may be assumed known. This constraint binds all future survival work, including `EXP-014` deferred to V2.

## Paired Bootstrap: Cox versus F1

| Method | Metric | Median | 95% interval |
|---|---|---:|---:|
| player_cluster_bootstrap | brier_score | -0.000402 | [-0.000728, 0.000028] |
| player_cluster_bootstrap | average_precision | 0.008282 | [-0.087592, 0.099320] |
| temporal_week_block_bootstrap | brier_score | -0.000393 | [-0.000738, -0.000100] |
| temporal_week_block_bootstrap | average_precision | 0.014320 | [-0.043905, 0.097603] |

## One-Day-Gap Sensitivity

| Gap (days) | Arm | Pooled +days | Brier | Calib. slope |
|---:|---|---:|---:|---:|
| 3 | cox | 104 | 0.005929 | 0.120283 |
| 3 | f1_logistic | 104 | 0.006325 | 2.019474 |
| 1 | cox | 113 | 0.006179 | 0.128341 |
| 1 | f1_logistic | 113 | 0.007040 | 1.804462 |

## Coefficients (model-based, not cluster-robust)

| Predictor | Hazard ratio | 95% interval | p-value |
|---|---:|---:|---:|
| daily_load_log1p | 1.0001 | [0.9962, 1.0040] | 0.9610 |
| daily_load_sum_7d_log1p | 1.0001 | [0.9963, 1.0040] | 0.9425 |
| daily_load_sum_28d_log1p | 1.0001 | [0.9963, 1.0040] | 0.9401 |
| fatigue_lag1 | 1.0000 | [0.9961, 1.0039] | 0.9942 |
| readiness_lag1 | 0.9999 | [0.9960, 1.0038] | 0.9500 |
| fatigue_mean_prior_7d | 1.0000 | [0.9961, 1.0039] | 0.9968 |
| fatigue_mean_prior_28d | 0.9999 | [0.9961, 1.0038] | 0.9789 |
| readiness_mean_prior_7d | 0.9998 | [0.9959, 1.0037] | 0.9295 |
| readiness_mean_prior_28d | 0.9998 | [0.9960, 1.0037] | 0.9333 |
| missingindicator_fatigue_lag1 | 0.9999 | [0.9960, 1.0038] | 0.9527 |
| missingindicator_readiness_lag1 | 0.9999 | [0.9960, 1.0038] | 0.9496 |
| missingindicator_fatigue_mean_prior_7d | 0.9998 | [0.9960, 1.0037] | 0.9378 |
| missingindicator_fatigue_mean_prior_28d | 0.9999 | [0.9960, 1.0037] | 0.9402 |
| missingindicator_readiness_mean_prior_7d | 0.9998 | [0.9960, 1.0037] | 0.9377 |
| missingindicator_readiness_mean_prior_28d | 0.9999 | [0.9960, 1.0037] | 0.9402 |

## Proportional-Hazards Check (interaction-term substitute for Schoenfeld residuals)

Global likelihood-ratio test: statistic 0.0159, df 15, p-value 1.0000. non-significant result is not evidence the assumption holds; support is 66 onsets.

| Predictor | Interaction coefficient | p-value |
|---|---:|---:|
| daily_load_log1p | 0.0000 | 0.9812 |
| daily_load_sum_7d_log1p | 0.0000 | 0.9741 |
| daily_load_sum_28d_log1p | 0.0000 | 0.9711 |
| fatigue_lag1 | 0.0000 | 0.9934 |
| readiness_lag1 | -0.0000 | 0.9707 |
| fatigue_mean_prior_7d | 0.0000 | 0.9999 |
| fatigue_mean_prior_28d | -0.0000 | 0.9918 |
| readiness_mean_prior_7d | -0.0000 | 0.9604 |
| readiness_mean_prior_28d | -0.0000 | 0.9669 |
| missingindicator_fatigue_lag1 | -0.0000 | 0.9751 |
| missingindicator_readiness_lag1 | -0.0000 | 0.9741 |
| missingindicator_fatigue_mean_prior_7d | -0.0000 | 0.9705 |
| missingindicator_fatigue_mean_prior_28d | -0.0000 | 0.9720 |
| missingindicator_readiness_mean_prior_7d | -0.0000 | 0.9704 |
| missingindicator_readiness_mean_prior_28d | -0.0000 | 0.9720 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| COX-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| COX-02 | PASS | risk_set_construction | counting-process rows constructed one-to-one from the frozen cohort's 34600 player-days |
| COX-03 | PASS | interval_partition_isolation | each interval represents exactly one calendar day mapped to a single prediction_date; no interval can span two partitions by construction |
| COX-04 | PASS | predictor_contract | frozen F1 contract used: 9 predictors |
| COX-05 | PASS | baseline_hazard_disjointness | baseline cumulative hazard fitted only on each fold's training rows |
| COX-06 | PASS | probability_validity | all converted probabilities lie in [0, 1]; 1-exp(-delta*hazard) is monotone increasing in the partial hazard by construction |
| COX-07 | PASS | event_count_reporting | every metrics table carries pooled and discrimination event counts |
| COX-08 | PASS | sensitivity_and_zero_positive_folds | one-day-gap sensitivity present; 1 zero-positive folds excluded from discrimination aggregation and counted |
| COX-09 | PASS | leave_one_player_out_time_coordinate | leave-one-player-out evaluation reports both clock variants; reset_clock (no assumed prior onset) is labelled the primary result and own_clock (held-out player's own onset history) is labelled a leakage diagnostic contrast, not a competing headline figure |

## Interpretation Boundary

This experiment characterises whether time-to-event framing adds practitioner value over the fixed-horizon F1 champion. It selects no champion, changes no cohort and accesses no final-test data.

## Gate

Adopt survival framing only if probability quality or operational capture improves over F1 with paired intervals excluding zero under both resampling schemes. Explicit rejection with evidence is a successful outcome. "Not distinguishable at this support" is valid and expected.
