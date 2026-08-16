# EXP-016 - Sparse-Predictor Availability Ablation Report

## Automated Status

Development run: **PASS**. Project-owner champion review required.

Arm A is F3 as promoted under `DEC-043`. Arm B removes `fatigue_lag1_robust_z_prior` and its recording-state indicator entirely. Arm C removes the value but retains the indicator. Arm D is F1 as an external reference. Raw probabilities only, per `DEC-052`. No final-test row is read or scored.

## Pooled Rolling-Origin Comparison

| Arm | Pooled +days | Brier | Log loss | Calib. slope | Discrim. +days | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 104 | 0.006287 | 0.041467 | 2.222064 | 104 | 0.079067 | 0.852441 |
| B | 104 | 0.006333 | 0.042151 | 2.122823 | 104 | 0.096091 | 0.831426 |
| C | 104 | 0.006287 | 0.041534 | 2.322430 | 104 | 0.087691 | 0.858446 |
| D | 104 | 0.006325 | 0.042009 | 2.019474 | 104 | 0.096668 | 0.835537 |

## Unseen-Player Generalisation (mandatory)

`DEC-043`'s binding limitation is that F3 (arm A) generalises worse than F1 (arm D) to unseen players.

| Arm | AP | ROC-AUC | Estimable players | Zero-positive players |
|---|---:|---:|---:|---:|
| A | 0.022308 | 0.630928 | 12/50 | 38 |
| B | 0.020427 | 0.617042 | 12/50 | 38 |
| C | 0.022500 | 0.631222 | 12/50 | 38 |
| D | 0.023316 | 0.642578 | 12/50 | 38 |

### Gap-Closure Analysis

Whether removing the predictor value (B) or keeping only the indicator (C) closes the F1-minus-A unseen-player gap.

| Candidate | Metric | A (reference) | Candidate | F1 (D) | F1-A gap | F1-candidate gap | Gap closed |
|---|---|---:|---:|---:|---:|---:|---|
| B | average_precision | 0.022308 | 0.020427 | 0.023316 | 0.001008 | 0.002889 | False |
| B | roc_auc | 0.630928 | 0.617042 | 0.642578 | 0.011651 | 0.025537 | False |
| C | average_precision | 0.022308 | 0.022500 | 0.023316 | 0.001008 | 0.000816 | True |
| C | roc_auc | 0.630928 | 0.631222 | 0.642578 | 0.011651 | 0.011356 | True |

## Paired Bootstrap Differences Against Arm A

| Candidate | Method | Metric | Median | 95% interval |
|---|---|---|---:|---:|
| B | player_cluster_bootstrap | brier_score | 0.000045 | [-0.000043, 0.000132] |
| B | player_cluster_bootstrap | average_precision | -0.003076 | [-0.042704, 0.039332] |
| B | temporal_week_block_bootstrap | brier_score | 0.000045 | [-0.000010, 0.000098] |
| B | temporal_week_block_bootstrap | average_precision | -0.006373 | [-0.022630, 0.007113] |
| C | player_cluster_bootstrap | brier_score | 0.000002 | [-0.000034, 0.000028] |
| C | player_cluster_bootstrap | average_precision | 0.000843 | [-0.013595, 0.021315] |
| C | temporal_week_block_bootstrap | brier_score | 0.000001 | [-0.000017, 0.000020] |
| C | temporal_week_block_bootstrap | average_precision | 0.002489 | [-0.001879, 0.014144] |
| D | player_cluster_bootstrap | brier_score | 0.000034 | [-0.000061, 0.000142] |
| D | player_cluster_bootstrap | average_precision | -0.000327 | [-0.026910, 0.052168] |
| D | temporal_week_block_bootstrap | brier_score | 0.000036 | [-0.000026, 0.000099] |
| D | temporal_week_block_bootstrap | average_precision | 0.000220 | [-0.014769, 0.028053] |

## One-Day-Gap Sensitivity

| Gap (days) | Arm | Pooled +days | Brier | Calib. slope |
|---:|---|---:|---:|---:|
| 3 | A | 104 | 0.006287 | 2.222064 |
| 3 | B | 104 | 0.006333 | 2.122823 |
| 3 | C | 104 | 0.006287 | 2.322430 |
| 3 | D | 104 | 0.006325 | 2.019474 |
| 1 | A | 113 | 0.006980 | 1.981428 |
| 1 | B | 113 | 0.007052 | 1.874976 |
| 1 | C | 113 | 0.006972 | 2.055997 |
| 1 | D | 113 | 0.007040 | 1.804462 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| ABL-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| ABL-02 | PASS | arm_contract | arm B removes ['fatigue_lag1_robust_z_prior', 'fatigue_robust_available']; arm C removes ['fatigue_lag1_robust_z_prior']; all other F3 predictors unchanged across A, B, C |
| ABL-03 | PASS | preprocessing_and_regularisation | frozen regularisation C=0.001 unchanged |
| ABL-04 | PASS | event_count_reporting | every metrics table carries pooled, discrimination and heldout event counts |
| ABL-05 | PASS | one_day_gap_sensitivity | one-day-gap sensitivity present alongside the three-day headline |
| ABL-06 | PASS | zero_positive_folds | 1 zero-positive folds excluded from discrimination aggregation; estimable folds counted |
| ABL-07 | PASS | unseen_player_generalisation | support-aware unseen-player aggregation present for all four arms |

## Interpretation Boundary

This experiment characterises whether a predictor's apparent contribution is carried by its availability pattern rather than its value. It selects no champion, changes no cohort and accesses no final-test data.

## Gate

If arm B or C matches or beats arm A on calibrated probability quality and improves unseen-player generalisation, `DEC-043` is reopened and the champion is re-selected through a new decision before V1-P2. If arm A remains best on both axes, F3 stands and the availability entanglement is documented as a binding limitation on every downstream citation. The project owner makes this call; this report does not.
