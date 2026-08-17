# EXP-018 - Explanation Stability Report

## Automated Status

Development run: **PASS**. Project-owner driver-display review required.

F1's attribution is exact: a player-day's predicted log-odds equals its intercept plus the sum of each transformed feature's standardised value times its fitted coefficient. Coefficient sign, magnitude and rank are measured across every estimable rolling-origin and leave-one-player-out fold. No final-test row is read or scored, and no model is refitted outside the existing fold structure.

## Coefficient Stability

| Predictor | Folds | Sign | Min |coef| | Max |coef| | IQR | Mean rank | Rank range |
|---|---:|---|---:|---:|---:|---:|---:|
| daily_load_log1p | 54 | NO | 0.000567 | 0.025022 | 0.002089 | 8.851852 | 4 |
| daily_load_sum_7d_log1p | 54 | yes | 0.021798 | 0.042557 | 0.002802 | 5.444444 | 1 |
| daily_load_sum_28d_log1p | 54 | yes | 0.020869 | 0.042946 | 0.002906 | 6.814815 | 3 |
| fatigue_lag1 | 54 | yes | 0.006944 | 0.030777 | 0.001524 | 8.000000 | 5 |
| readiness_lag1 | 54 | yes | 0.064100 | 0.117916 | 0.001811 | 3.000000 | 0 |
| fatigue_mean_prior_7d | 54 | yes | 0.009104 | 0.044084 | 0.002334 | 5.777778 | 4 |
| fatigue_mean_prior_28d | 54 | yes | 0.016813 | 0.070505 | 0.002826 | 4.111111 | 4 |
| readiness_mean_prior_7d | 54 | yes | 0.119102 | 0.187875 | 0.001735 | 1.000000 | 0 |
| readiness_mean_prior_28d | 54 | yes | 0.086610 | 0.167081 | 0.003384 | 2.000000 | 0 |

## Flagged-Player-Day Contributor Overlap

Flagged: 104 player-days with an actual represented positive label, evaluable under both a rolling-origin fold and a leave-one-player-out fold. Mean top-3 positive-contributor Jaccard overlap: 0.898980 (range 0.200000 to 1.000000).

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| EXPL-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| EXPL-02 | PASS | standardisation_scope | each fold's imputer and scaler are fitted on that fold's own training portion only, matching the frozen F1 pipeline |
| EXPL-03 | PASS | attribution_exactness | summed per-predictor contributions plus intercept reproduce the model's own logit to within 0.00e+00 |
| EXPL-04 | PASS | stability_support_reporting | every stability figure states its estimable-fold count (54 distinct fold fits) |
| EXPL-05 | PASS | sign_unstable_disclosure | 1 of 9 predictors have unstable sign: daily_load_log1p |

## Interpretation Boundary

Predictors with constant sign across all estimable folds are eligible for display as drivers in the dashboard. Predictors with unstable sign are not, and are recorded as such. Low attribution stability is a valid finding and constrains the product rather than invalidating the model.

## Gate

The project owner selects which stable predictors are displayed as drivers. If the stop condition triggers, no driver-display recommendation is made here.
