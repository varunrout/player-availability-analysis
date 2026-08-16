# EXP-009 - M1-F3 Calibration Comparison Report

## Automated Status

Development run: **FAIL**. Project-owner calibration review required.

Raw, Platt and isotonic calibration are compared on the frozen F3 candidate using development data only. Calibrators are fitted fold-wise on inner cross-validated out-of-fold training probabilities and applied to disjoint held-out probabilities, so each calibrated arm is a monotone map of the raw arm. No post-hoc calibrator is selected and no final-test prediction or performance is created.

## Power Limitation (binding)

Development support is 104 pooled positive player-days across 3 estimable rolling-origin folds; 1 fold(s) carry zero held-out positives and are excluded from discrimination aggregation. Every metric below is reported with its supporting event count. No calibration method is declared superior on point estimates alone; a difference is claimed only where a paired interval excludes zero. "No calibration method is distinguishable at this support" is a valid and expected result.

## Pooled Rolling-Origin Comparison

| Arm | Pooled +days | Brier | Log loss | Calib. intercept | Calib. slope | Mean pred | Observed | Discrim. +days | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 104 | 0.006287 | 0.041467 | 2.575652 | 2.222064 | 0.023049 | 0.006185 | 104 | 0.079067 | 0.852441 |
| platt | 104 | 0.007246 | 0.043001 | -1.012495 | 1.200236 | 0.026527 | 0.006185 | 104 | 0.075568 | 0.859785 |
| isotonic | 104 | 0.007402 | 0.052597 | -4.069015 | 0.225071 | 0.024226 | 0.006185 | 104 | 0.078718 | 0.864060 |

## Expected Calibration Error

Computed only over reliability bins meeting the minimum positive-day support.

| Arm | Supported bins | Supported player-days | Expected calibration error |
|---|---:|---:|---:|
| raw | 3 | 5045 | 0.022596 |
| platt | 5 | 8407 | 0.033940 |
| isotonic | 4 | 6727 | 0.034653 |

## Paired Arm Differences

Candidate-minus-reference on identical resampled player-days. Negative Brier differences favour the candidate calibration.

| Comparison | Method | Metric | Median | 95% interval |
|---|---|---|---:|---:|
| raw to platt | player_cluster_bootstrap | brier_score | 0.000862 | [0.000037, 0.002358] |
| raw to platt | temporal_week_block_bootstrap | brier_score | 0.000980 | [0.000553, 0.001306] |
| raw to platt | player_cluster_bootstrap | average_precision | -0.003503 | [-0.034174, 0.016505] |
| raw to platt | temporal_week_block_bootstrap | average_precision | -0.003047 | [-0.017679, 0.004635] |
| raw to isotonic | player_cluster_bootstrap | brier_score | 0.001027 | [0.000061, 0.002854] |
| raw to isotonic | temporal_week_block_bootstrap | brier_score | 0.001110 | [0.000606, 0.001778] |
| raw to isotonic | player_cluster_bootstrap | average_precision | 0.000994 | [-0.048312, 0.010887] |
| raw to isotonic | temporal_week_block_bootstrap | average_precision | -0.001945 | [-0.036918, 0.017755] |

## Sparse-Predictor Availability Audit

Robust fatigue predictor `fatigue_lag1_robust_z_prior` calibration split by availability. Materially different behaviour indicates a reporting-process artefact rather than physiology.

| Subset | Arm | Player-days | +days | Brier | Mean pred | Observed |
|---|---|---:|---:|---:|---:|---:|
| robust_fatigue_observed | raw | 2475 | 61 | 0.023581 | 0.037312 | 0.024646 |
| robust_fatigue_observed | platt | 2475 | 61 | 0.026041 | 0.056563 | 0.024646 |
| robust_fatigue_observed | isotonic | 2475 | 61 | 0.028487 | 0.057341 | 0.024646 |
| robust_fatigue_absent | raw | 14340 | 43 | 0.003302 | 0.020587 | 0.002999 |
| robust_fatigue_absent | platt | 14340 | 43 | 0.004002 | 0.021343 | 0.002999 |
| robust_fatigue_absent | isotonic | 14340 | 43 | 0.003763 | 0.018511 | 0.002999 |

## One-Day-Gap Sensitivity

Mandatory pre-registered sensitivity (`DEC-048`) alongside the three-day headline.

| Gap (days) | Arm | Pooled +days | Brier | Calib. slope | Mean pred | Observed |
|---:|---|---:|---:|---:|---:|---:|
| 3 | raw | 104 | 0.006287 | 2.222064 | 0.023049 | 0.006185 |
| 3 | platt | 104 | 0.007246 | 1.200236 | 0.026527 | 0.006185 |
| 3 | isotonic | 104 | 0.007402 | 0.225071 | 0.024226 | 0.006185 |
| 1 | raw | 113 | 0.006980 | 1.981428 | 0.027348 | 0.006717 |
| 1 | platt | 113 | 0.008436 | 1.148361 | 0.030685 | 0.006717 |
| 1 | isotonic | 113 | 0.008679 | 0.832585 | 0.029487 | 0.006717 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| CAL-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| CAL-02 | PASS | fitting_disjointness | calibrators fitted on inner cross-validated out-of-fold training probabilities, disjoint from every evaluation fold |
| CAL-03 | PASS | predictor_contract | frozen F3 contract used: 23 predictors |
| CAL-04 | PASS | monotone_ranking | within every estimable fold Platt ROC-AUC equals raw ROC-AUC; the per-fold monotone map preserves order |
| CAL-05 | PASS | event_count_reporting | every metrics table carries pooled and discrimination positive-day counts |
| CAL-06 | PASS | sparse_predictor_audit | fatigue_lag1_robust_z_prior availability audit populated across 2 subsets |
| CAL-07 | PASS | one_day_gap_sensitivity | one-day-gap sensitivity present alongside the three-day headline |
| CAL-08 | PASS | zero_positive_folds | 1 zero-positive folds excluded from discrimination aggregation; estimable folds counted |
| BOOT-01 | FAIL | paired_bootstrap_population_consistency | every paired-bootstrap median agrees in sign with its point-estimate difference; Brier and average precision are each bootstrapped on the population matching that metric's own point estimate |

## Interpretation Boundary

This experiment characterises the probability quality of a self-reported injury-related risk score for practitioner review. It selects no deployment threshold, changes no feature set or cohort, retunes no model and accesses no final-test data.

## Gate

The project owner selects the calibration approach, preferring the simplest method that improves calibration without unstable step-like behaviour. Characterising calibration honestly, including a "not distinguishable" outcome, satisfies the experiment.
