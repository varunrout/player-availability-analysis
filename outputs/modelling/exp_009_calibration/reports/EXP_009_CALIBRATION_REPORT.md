# EXP-009 - M1 Calibration Comparison Report

## Automated Status

Development run: **PASS**. Project-owner calibration review required.

Raw, Platt and isotonic calibration are compared on the frozen F1 champion predictor contract (`DEC-054`), the primary evaluation, with the frozen F3 predictor contract retained as historical reference only (the superseded candidate under `DEC-054`), using development data only. Calibrators are fitted fold-wise on inner cross-validated out-of-fold training probabilities and applied to disjoint held-out probabilities, so each calibrated arm is a monotone map of its own raw arm. No post-hoc calibrator is selected and no final-test prediction or performance is created.

## Power Limitation (binding)

Development support is 104 pooled positive player-days across 3 estimable rolling-origin folds; 1 fold(s) carry zero held-out positives and are excluded from discrimination aggregation. Every metric below is reported with its supporting event count. No calibration method is declared superior on point estimates alone; a difference is claimed only where a paired interval excludes zero. "No calibration method is distinguishable at this support" is a valid and expected result.

## Pooled Rolling-Origin Comparison

| Arm | Pooled +days | Brier | Log loss | Calib. intercept | Calib. slope | Mean pred | Observed | Discrim. +days | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1_raw | 104 | 0.006325 | 0.042009 | 2.007319 | 2.019474 | 0.023012 | 0.006185 | 104 | 0.096668 | 0.835537 |
| F1_platt | 104 | 0.007765 | 0.044835 | -1.482620 | 1.044271 | 0.027423 | 0.006185 | 104 | 0.095012 | 0.838287 |
| F1_isotonic | 104 | 0.007509 | 0.062091 | -4.435530 | 0.128850 | 0.025880 | 0.006185 | 104 | 0.071853 | 0.824284 |
| F3_raw | 104 | 0.006287 | 0.041467 | 2.575652 | 2.222064 | 0.023049 | 0.006185 | 104 | 0.079067 | 0.852441 |
| F3_platt | 104 | 0.007246 | 0.043001 | -1.012495 | 1.200236 | 0.026527 | 0.006185 | 104 | 0.075568 | 0.859785 |
| F3_isotonic | 104 | 0.007402 | 0.052597 | -4.069015 | 0.225071 | 0.024226 | 0.006185 | 104 | 0.078718 | 0.864060 |

## Expected Calibration Error

Computed only over reliability bins meeting the minimum positive-day support.

| Arm | Supported bins | Supported player-days | Expected calibration error |
|---|---:|---:|---:|
| F1_raw | 5 | 8408 | 0.019486 |
| F1_platt | 4 | 6725 | 0.038915 |
| F1_isotonic | 5 | 8407 | 0.032480 |
| F3_raw | 3 | 5045 | 0.022596 |
| F3_platt | 5 | 8407 | 0.033940 |
| F3_isotonic | 4 | 6727 | 0.034653 |

## Paired Arm Differences

Candidate-minus-reference on identical resampled player-days. Negative Brier differences favour the candidate calibration.

| Comparison | Method | Metric | Median | 95% interval |
|---|---|---|---:|---:|
| F1_raw to F1_platt | player_cluster_bootstrap | brier_score | 0.001335 | [-0.000004, 0.003681] |
| F1_raw to F1_platt | temporal_week_block_bootstrap | brier_score | 0.001431 | [0.000844, 0.002004] |
| F1_raw to F1_platt | player_cluster_bootstrap | average_precision | -0.001843 | [-0.013357, 0.009155] |
| F1_raw to F1_platt | temporal_week_block_bootstrap | average_precision | -0.001550 | [-0.007955, 0.003785] |
| F1_raw to F1_isotonic | player_cluster_bootstrap | brier_score | 0.001179 | [0.000320, 0.002238] |
| F1_raw to F1_isotonic | temporal_week_block_bootstrap | brier_score | 0.001189 | [0.000775, 0.001660] |
| F1_raw to F1_isotonic | player_cluster_bootstrap | average_precision | -0.013535 | [-0.075069, 0.017100] |
| F1_raw to F1_isotonic | temporal_week_block_bootstrap | average_precision | -0.024035 | [-0.145000, 0.018394] |
| F3_raw to F3_platt | player_cluster_bootstrap | brier_score | 0.000962 | [0.000052, 0.002356] |
| F3_raw to F3_platt | temporal_week_block_bootstrap | brier_score | 0.000983 | [0.000583, 0.001327] |
| F3_raw to F3_platt | player_cluster_bootstrap | average_precision | -0.002968 | [-0.035832, 0.015417] |
| F3_raw to F3_platt | temporal_week_block_bootstrap | average_precision | -0.003124 | [-0.019917, 0.005125] |
| F3_raw to F3_isotonic | player_cluster_bootstrap | brier_score | 0.001068 | [-0.000003, 0.002587] |
| F3_raw to F3_isotonic | temporal_week_block_bootstrap | brier_score | 0.001106 | [0.000575, 0.001683] |
| F3_raw to F3_isotonic | player_cluster_bootstrap | average_precision | 0.001352 | [-0.043414, 0.011788] |
| F3_raw to F3_isotonic | temporal_week_block_bootstrap | average_precision | -0.000888 | [-0.031114, 0.016341] |

## Sparse-Predictor Availability Audit

Robust fatigue predictor `fatigue_lag1_robust_z_prior` calibration split by availability, scoped to the F3 reference arms only (this predictor is absent from F1's contract). Materially different behaviour indicates a reporting-process artefact rather than physiology.

| Subset | Arm | Player-days | +days | Brier | Mean pred | Observed |
|---|---|---:|---:|---:|---:|---:|
| robust_fatigue_observed | F3_raw | 2475 | 61 | 0.023581 | 0.037312 | 0.024646 |
| robust_fatigue_observed | F3_platt | 2475 | 61 | 0.026041 | 0.056563 | 0.024646 |
| robust_fatigue_observed | F3_isotonic | 2475 | 61 | 0.028487 | 0.057341 | 0.024646 |
| robust_fatigue_absent | F3_raw | 14340 | 43 | 0.003302 | 0.020587 | 0.002999 |
| robust_fatigue_absent | F3_platt | 14340 | 43 | 0.004002 | 0.021343 | 0.002999 |
| robust_fatigue_absent | F3_isotonic | 14340 | 43 | 0.003763 | 0.018511 | 0.002999 |

## One-Day-Gap Sensitivity

Mandatory pre-registered sensitivity (`DEC-048`) alongside the three-day headline.

| Gap (days) | Arm | Pooled +days | Brier | Calib. slope | Mean pred | Observed |
|---:|---|---:|---:|---:|---:|---:|
| 3 | F1_raw | 104 | 0.006325 | 2.019474 | 0.023012 | 0.006185 |
| 3 | F1_platt | 104 | 0.007765 | 1.044271 | 0.027423 | 0.006185 |
| 3 | F1_isotonic | 104 | 0.007509 | 0.128850 | 0.025880 | 0.006185 |
| 3 | F3_raw | 104 | 0.006287 | 2.222064 | 0.023049 | 0.006185 |
| 3 | F3_platt | 104 | 0.007246 | 1.200236 | 0.026527 | 0.006185 |
| 3 | F3_isotonic | 104 | 0.007402 | 0.225071 | 0.024226 | 0.006185 |
| 1 | F1_raw | 113 | 0.007040 | 1.804462 | 0.027463 | 0.006717 |
| 1 | F1_platt | 113 | 0.009035 | 1.022766 | 0.031855 | 0.006717 |
| 1 | F1_isotonic | 113 | 0.009225 | 0.160803 | 0.030579 | 0.006717 |
| 1 | F3_raw | 113 | 0.006980 | 1.981428 | 0.027348 | 0.006717 |
| 1 | F3_platt | 113 | 0.008436 | 1.148361 | 0.030685 | 0.006717 |
| 1 | F3_isotonic | 113 | 0.008679 | 0.832585 | 0.029487 | 0.006717 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| CAL-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| CAL-02 | PASS | fitting_disjointness | calibrators fitted on inner cross-validated out-of-fold training probabilities, disjoint from every evaluation fold |
| CAL-03 | PASS | predictor_contract | frozen contracts used: F1 champion 9 predictors, F3 reference 23 predictors |
| CAL-04 | PASS | monotone_ranking | within every estimable fold Platt ROC-AUC equals raw ROC-AUC; the per-fold monotone map preserves order |
| CAL-05 | PASS | event_count_reporting | every metrics table carries pooled and discrimination positive-day counts |
| CAL-06 | PASS | sparse_predictor_audit | fatigue_lag1_robust_z_prior availability audit populated across 2 subsets |
| CAL-07 | PASS | one_day_gap_sensitivity | one-day-gap sensitivity present alongside the three-day headline |
| CAL-08 | PASS | zero_positive_folds | 1 zero-positive folds excluded from discrimination aggregation; estimable folds counted |
| BOOT-01 | PASS | paired_bootstrap_population_consistency | every paired-bootstrap median agrees in sign with its point-estimate difference; Brier and average precision are each bootstrapped on the population matching that metric's own point estimate |

## Interpretation Boundary

This experiment characterises the probability quality of a self-reported injury-related risk score for practitioner review. It selects no deployment threshold, changes no feature set or cohort, retunes no model and accesses no final-test data.

## Gate

The project owner selects the calibration approach, preferring the simplest method that improves calibration without unstable step-like behaviour. Characterising calibration honestly, including a "not distinguishable" outcome, satisfies the experiment.
