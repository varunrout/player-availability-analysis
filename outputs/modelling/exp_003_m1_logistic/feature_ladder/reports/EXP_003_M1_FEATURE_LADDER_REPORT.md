# EXP-003 - M1 Feature-Ladder Development Report

## Automated Status

Development run: **PASS WITH REVIEW**.

F1 is the promoted development reference. No post-hoc calibrator or final-test prediction/performance was created.

## Raw Validation Comparison

| Feature set | Predictors | C | Brier | Log loss | AP | ROC-AUC | Mean prediction |
|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | 9 | 0.001 | 0.003700 | 0.031272 | 0.016640 | 0.807802 | 0.020048 |
| F2 | 17 | 0.001 | 0.003713 | 0.031378 | 0.016377 | 0.807892 | 0.020186 |
| F3 | 23 | 0.001 | 0.003613 | 0.030367 | 0.019432 | 0.851053 | 0.019650 |

Observed validation positive-day rate is 0.003222 for every feature set.

## Alert-Budget Comparison

| Feature set | Review rate | Alerts | Captured onsets | Capture rate | False alerts/capture |
|---|---:|---:|---:|---:|---:|
| F1 | 0.010 | 87 | 0/5 | 0.000 | NA |
| F1 | 0.025 | 218 | 2/5 | 0.400 | 107.00 |
| F1 | 0.050 | 435 | 4/5 | 0.800 | 106.25 |
| F2 | 0.010 | 87 | 0/5 | 0.000 | NA |
| F2 | 0.025 | 218 | 2/5 | 0.400 | 107.00 |
| F2 | 0.050 | 435 | 4/5 | 0.800 | 106.25 |
| F3 | 0.010 | 87 | 1/5 | 0.200 | 86.00 |
| F3 | 0.025 | 218 | 2/5 | 0.400 | 107.00 |
| F3 | 0.050 | 435 | 4/5 | 0.800 | 105.75 |

## Development Stress Evidence

| Feature set | Unseen-player AP | Unseen-player ROC-AUC | Estimable players |
|---|---:|---:|---:|
| F1 | 0.023316 | 0.642578 | 12/50 |
| F2 | 0.021857 | 0.626257 | 12/50 |
| F3 | 0.022308 | 0.630928 | 12/50 |

Rolling-origin average precision by estimable fold:

| Feature set | RO1 | RO2 | RO3 |
|---|---:|---:|---:|
| F1 | 0.199427 | 0.030987 | 0.042688 |
| F2 | 0.202967 | 0.033113 | 0.040283 |
| F3 | 0.232634 | 0.016345 | 0.047624 |

## Paired Bootstrap Differences

Candidate-minus-reference intervals preserve identical resampled player-days.
Negative Brier differences and positive AP differences favour the candidate.

| Comparison | Method | Metric | Median | 95% interval |
|---|---|---|---:|---:|
| F1 to F2 | player_cluster_bootstrap | brier_score | 0.000012 | [0.000000, 0.000029] |
| F1 to F2 | player_cluster_bootstrap | average_precision | -0.000194 | [-0.000726, 0.001690] |
| F1 to F2 | temporal_week_block_bootstrap | brier_score | 0.000013 | [0.000007, 0.000017] |
| F1 to F2 | temporal_week_block_bootstrap | average_precision | -0.000231 | [-0.000873, 0.000090] |
| F2 to F3 | player_cluster_bootstrap | brier_score | -0.000083 | [-0.000313, 0.000067] |
| F2 to F3 | player_cluster_bootstrap | average_precision | 0.003506 | [-0.001805, 0.047714] |
| F2 to F3 | temporal_week_block_bootstrap | brier_score | -0.000099 | [-0.000151, -0.000044] |
| F2 to F3 | temporal_week_block_bootstrap | average_precision | 0.003127 | [-0.000230, 0.009095] |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| LADDER-01 | PASS | model_integrity | child model failure findings: 0 |
| LADDER-02 | PASS | predictor_contract | frozen cumulative counts expected F1=9, F2=17, F3=23 |
| LADDER-03 | PASS | final_test_isolation | zero final-test predictions or performance across all feature sets |
| LADDER-04 | REVIEW | raw_feature_set_selection | lowest Brier=F3; highest AP=F3 |
| LADDER-05 | REVIEW | predictor_availability | predictors below 20% observed coverage: 1 |
| LADDER-06 | REVIEW | calibration_scope | raw comparison only; no post-hoc calibrator fitted or selected |

## Interpretation Boundary

This is a controlled development feature-family ablation for practitioner-review prioritisation. It does not establish causality, diagnosis, medical clearance or deployment readiness.

## Gate

The project owner must select the raw feature-set candidate and approve a separate calibration experiment before any calibrator or final-test evaluation.
