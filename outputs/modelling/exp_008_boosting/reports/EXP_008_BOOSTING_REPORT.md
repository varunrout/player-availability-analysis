# EXP-008 - Boosted Classification Complexity Test Report

## Automated Status

Development run: **PASS**. Project-owner complexity-verdict review required.

`HistGradientBoostingClassifier` over the F1 champion's nine predictors (`DEC-054`), pre-registered 16-point hyperparameter grid, iteration count selected by early stopping against the fixed chronological validation partition. Raw probabilities only, per `DEC-052`. No final-test row is read or scored.

## Selected Configuration

- `max_leaf_nodes`: 7.0
- `learning_rate`: 0.01
- `min_samples_leaf`: 200.0
- `l2_regularization`: 10.0
- `max_iter` (early-stopped): 50

## Pooled Rolling-Origin Comparison

| Arm | Pooled +days | Brier | Log loss | Discrim. +days | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| boosted | 104 | 0.006143 | 0.040309 | 104 | 0.086066 | 0.788733 |
| f1_logistic | 104 | 0.006325 | 0.042009 | 104 | 0.096668 | 0.835537 |

## Training-to-Validation Gap (overfitting signature)

Training Brier 0.016124, validation Brier 0.003411, gap -0.012713. Overfitting signature present: False.

## Unseen-Player Generalisation (mandatory)

| Arm | AP | ROC-AUC | Estimable players | Zero-positive players |
|---|---:|---:|---:|---:|
| boosted | 0.026889 | 0.554999 | 12/50 | 38 |
| f1_logistic | 0.023316 | 0.642578 | 12/50 | 38 |

## Paired Bootstrap: Boosted versus F1

| Method | Metric | Median | 95% interval |
|---|---|---:|---:|
| player_cluster_bootstrap | brier_score | -0.000171 | [-0.000365, -0.000046] |
| temporal_week_block_bootstrap | brier_score | -0.000188 | [-0.000274, -0.000096] |
| player_cluster_bootstrap | average_precision | -0.006290 | [-0.052406, 0.019850] |
| temporal_week_block_bootstrap | average_precision | -0.006523 | [-0.105518, 0.029223] |

## One-Day-Gap Sensitivity

| Gap (days) | Arm | Pooled +days | Brier | AP |
|---:|---|---:|---:|---:|
| 3 | boosted | 104 | 0.006143 | 0.086066 |
| 3 | f1_logistic | 104 | 0.006325 | 0.096668 |
| 1 | boosted | 113 | 0.006690 | 0.085566 |
| 1 | f1_logistic | 113 | 0.007040 | 0.108138 |

## Missingness Sensitivity (native NaN handling, reported separately)

Fixed validation window only, reusing the primary arm's selected hyperparameters. Not a complexity result.

| Treatment | Role | Brier | AP | ROC-AUC |
|---|---|---:|---:|---:|
| imputed_matches_f1 | primary_arm_reference | 0.003411 | 0.013013 | 0.708357 |
| native_missing_handling | missingness_sensitivity | 0.003414 | 0.015358 | 0.750689 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| BST-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| BST-02 | PASS | pre_registered_grid | 16 pre-registered grid combinations evaluated |
| BST-03 | PASS | predictor_contract | frozen F1 contract used: 9 predictors |
| BST-04 | PASS | early_stopping_selection | iteration count selected via staged prediction on the fixed chronological validation partition, same criterion as F1's C selection |
| BST-05 | PASS | missing_data_treatment | primary arm matches F1's median-imputation preprocessing; native-handling arm reported separately as missingness_sensitivity_native_handling |
| BST-06 | PASS | event_count_reporting | every metrics table carries pooled and discrimination event counts |
| BST-07 | PASS | one_day_gap_sensitivity | one-day-gap sensitivity present alongside the three-day headline |
| BST-08 | PASS | training_validation_gap_and_zero_positive_folds | training-to-validation gap reported; 1 zero-positive folds excluded from discrimination aggregation and counted |
| BST-09 | PASS | held_out_outcome_history_isolation | no evaluation coordinate, index or derived feature is computed from held-out outcome history in any evaluation view; boosted classification has no time-coordinate concept for the EXP-007 leakage class to recur in |
| BOOT-01 | PASS | paired_bootstrap_population_consistency | every paired-bootstrap median agrees in sign with its point-estimate difference; Brier and average precision are each bootstrapped on the population matching that metric's own point estimate |

## Interpretation Boundary

This experiment characterises whether nonlinearity and interaction structure earn their place at this sample size. It selects no champion, changes no cohort and accesses no final-test data.

## Gate

Nonlinearity earns its place only if calibrated performance improves over F1 with paired intervals excluding zero under both resampling schemes. A negative result is reported as-is, without softening and without searching for a configuration that reverses it.
