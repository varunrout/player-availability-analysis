# EXP-003 - M1-F1 Regularised Logistic Report

## Automated Status

Development run: **PASS**. Owner `PROMOTE`, `REVISE` or `REJECT` review is required.

No F2/F3 model, post-hoc calibrator or final-test prediction/performance was created.

## Selected Configuration

- Feature set: F1 (9 predictors)
- Selected C: 0.001
- Pipeline: training-only median imputation with indicators, scaling and unweighted L2 logistic regression

## Validation Comparison

| Model | Brier | Log loss | Average precision | ROC-AUC |
|---|---:|---:|---:|---:|
| M0_GLOBAL_PREVALENCE | 0.003405 | 0.030310 | 0.003222 | 0.500000 |
| M1-F1 | 0.003700 | 0.031272 | 0.016640 | 0.807802 |

## Raw Calibration Diagnostics

- Mean prediction: 0.020048
- Observed positive-day rate: 0.003222
- Calibration intercept: -0.373677
- Calibration slope: 1.422205
- Post-hoc calibration selection: not performed

## Alert-Budget Simulation

| Review rate | Alerts | Captured onsets | Capture rate | False alerts/captured onset |
|---:|---:|---:|---:|---:|
| 0.010 | 87 | 0/5 | 0.000 | NA |
| 0.025 | 218 | 2/5 | 0.400 | 107.00 |
| 0.050 | 435 | 4/5 | 0.800 | 106.25 |

## Development Stress Evidence

Rolling folds: 4; zero-positive stress folds: 1.
Unseen-player aggregate AP: 0.023316; estimable players: 12/50.

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| F1-01 | PASS | predictor_contract | exact frozen F1 allow-list used: 9 predictors |
| F1-02 | PASS | optimisation | finite grid fitted with convergence warnings counted |
| F1-03 | PASS | prediction_validity | all validation probabilities are in [0, 1] |
| F1-04 | PASS | final_test_isolation | zero final-test predictions or performance metrics |
| F1-05 | REVIEW | m0_comparison | F1 Brier=0.003700 vs M0=0.003405; F1 AP=0.016640 vs M0=0.003222 |
| F1-06 | REVIEW | operational_capture | maximum captured onsets=4/5 |
| F1-07 | REVIEW | raw_calibration | mean prediction=0.020048; observed=0.003222; post-hoc calibration not selected |
| F1-08 | REVIEW | temporal_support | 1 rolling folds have zero positive days |

## Interpretation Boundary

F1 estimates exploratory practitioner-review risk for recorded self-reported injury-related onsets. Coefficients are associations, not causal effects, medical thresholds or training recommendations.

## Gate

The project owner must decide `PROMOTE`, `REVISE` or `REJECT` before F2 implementation.
