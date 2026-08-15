# EXP-002 - M0 Naive Baseline Report

## Automated Status

Development run: **PASS**. Project-owner benchmark review is required.

No final-test predictions or performance metrics were created.

## Partition Support

| Partition | Player-days | Positive days | Performance evaluated |
|---|---:|---:|---|
| train | 16365 | 280 | True |
| validation | 8690 | 28 | True |
| test | 8845 | 35 | False |

## Validation Metrics

| Baseline | Brier | Log loss | Average precision | ROC-AUC |
|---|---:|---:|---:|---:|
| M0_GLOBAL_PREVALENCE | 0.003405 | 0.030310 | 0.003222 | 0.500000 |
| M0_RECENT_LOAD | 0.003544 | 0.032241 | 0.002934 | 0.477210 |

The global baseline has no estimable ranking because every validation score is identical.

## Alert-Budget Simulation

| Baseline | Review rate | Status | Alerts/100 days | Captured onsets | Capture rate |
|---|---:|---|---:|---:|---:|
| M0_GLOBAL_PREVALENCE | 0.010 | NOT_ESTIMABLE_CONSTANT_SCORE | 0.000 | 0 | 0.000 |
| M0_GLOBAL_PREVALENCE | 0.025 | NOT_ESTIMABLE_CONSTANT_SCORE | 0.000 | 0 | 0.000 |
| M0_GLOBAL_PREVALENCE | 0.050 | NOT_ESTIMABLE_CONSTANT_SCORE | 0.000 | 0 | 0.000 |
| M0_RECENT_LOAD | 0.010 | ESTIMATED | 1.001 | 0 | 0.000 |
| M0_RECENT_LOAD | 0.025 | ESTIMATED | 2.509 | 0 | 0.000 |
| M0_RECENT_LOAD | 0.050 | ESTIMATED | 5.006 | 0 | 0.000 |

## Bootstrap Uncertainty

| Baseline | Method | Metric | Valid/Requested | 95% interval |
|---|---|---|---:|---:|
| M0_GLOBAL_PREVALENCE | player_cluster_bootstrap | brier_score | 500/500 | 0.000293 to 0.007308 |
| M0_GLOBAL_PREVALENCE | player_cluster_bootstrap | average_precision | 477/500 | 0.000805 to 0.007266 |
| M0_GLOBAL_PREVALENCE | temporal_week_block_bootstrap | brier_score | 500/500 | 0.001403 to 0.005618 |
| M0_GLOBAL_PREVALENCE | temporal_week_block_bootstrap | average_precision | 499/500 | 0.001204 to 0.005514 |
| M0_RECENT_LOAD | player_cluster_bootstrap | brier_score | 500/500 | 0.000442 to 0.007497 |
| M0_RECENT_LOAD | player_cluster_bootstrap | average_precision | 481/500 | 0.000728 to 0.007331 |
| M0_RECENT_LOAD | temporal_week_block_bootstrap | brier_score | 500/500 | 0.001459 to 0.005673 |
| M0_RECENT_LOAD | temporal_week_block_bootstrap | average_precision | 499/500 | 0.000986 to 0.005773 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| M0-01 | PASS | partition_integrity | 174 prediction dates are validation-only |
| M0-02 | PASS | training_scope | prevalence and 0.950 load quantile learned from 16365 training rows |
| M0-03 | PASS | prediction_validity | all probabilities lie in [0, 1] |
| M0-04 | REVIEW | prevalence_shift | train prevalence=0.017110; validation prevalence=0.003222 |
| M0-05 | REVIEW | benchmark_utility | load AP=0.002934; load Brier=0.003544 |
| M0-06 | REVIEW | outcome_support | 5 represented validation onsets |

## Interpretation Boundary

These are exploratory benchmarks for prioritising practitioner review of self-reported injury-related onset risk. They are not medical thresholds, causal workload rules, player-clearance outputs or deployment evidence.

## Gate

The project owner must decide `BENCHMARK ACCEPT` or `REVISE` before M1 implementation.
