# V1-P5 - Final-Test Governance Gate Report

Pre-registration commit: `650f67e1883b655124324219c20cca09f19c3eba` (`DEC-062`).

## Automated Status

**PASS**. This evaluation was executed exactly once. Thresholds were frozen at 2026-08-17T13:17:38.037821+00:00; the final-test partition was read at 2026-08-17T13:17:38.037821+00:00.

## Power Statement (registered in advance, verbatim)

> The final-test partition contains five represented onsets. This evaluation has almost no inferential power. A single onset falling either side of a threshold can halve or double average precision, and no interval computable on this partition will be narrow enough to support a comparison against any other model or operating point. This is a confirmatory sanity check that the champion behaves on unseen future data as it behaved in development. It is not a performance claim and must never be cited as one.

Observed support: 8845 player-days, 35 positive days, 5 represented onsets.

## Registered Claims

| Claim | Statement | Supported | Evidence |
|---|---|---|---|
| C1 | Ranking on unseen future data is better than chance (ROC-AUC above 0.5) | YES | ROC-AUC=0.827204 |
| C2 | The champion overpredicts risk in the large (development finding: roughly 3.7x) | YES | mean prediction=0.014824 vs observed rate=0.003957 (3.7x) |
| C3 | At the 2.5% operating point the false-alert burden is high and of the development order (tens of false alerts per captured onset) | NO | false alerts per captured onset at 2.5%=135.000000 |

## Final-Test Metrics

| Metric | Value | Support |
|---|---:|---:|
| Brier score | 0.004144 | 8845.0 days |
| Log loss | 0.029314 | 8845.0 days |
| Calibration intercept | -0.297569 | 8845.0 days |
| Calibration slope | 1.278808 | 8845.0 days |
| Mean prediction | 0.014824 | 8845.0 days |
| Observed rate | 0.003957 | 35.0 positive days |
| Average precision | 0.021076 | 35.0 positive days |
| ROC-AUC | 0.827204 | 35.0 positive days |

## Operating Points

| Rate | Threshold | Alerts | Alerts/100 days | Precision | Onsets | Captured | Recall | False/captured |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.500% | 0.033831 | 419 | 4.737140 | 0.033413 | 5 | 3 | 0.600000 | 135.000000 |
| 5.000% | 0.026711 | 534 | 6.037309 | 0.026217 | 5 | 3 | 0.600000 | 173.333333 |

## Embargo Exclusion

| Gap | Excluded from | Excluded to | Player-days excluded |
|---|---|---|---:|
| train_to_validation | 2020-12-24 | 2021-01-01 | 350 |
| validation_to_test | 2021-06-23 | 2021-07-01 | 350 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| FINAL-01 | PASS | single_read | final-test partition is read exactly once in this function, logged with a timestamp |
| FINAL-02 | PASS | predictor_contract | evaluated model uses exactly the 9 named F1 predictors |
| FINAL-03 | PASS | preprocessing_scope | imputer and scaler are fitted on the development partition only |
| FINAL-04 | PASS | threshold_freezing | operating-point thresholds are computed from the fitted model's own development-partition predictions and recorded before the final-test read |
| FINAL-05 | PASS | embargo_exclusion | 700 embargoed player-days excluded across two gaps |
| FINAL-06 | PASS | event_count_reporting | every operating point carries its represented-onset and player-day counts |
| FINAL-07 | PASS | no_post_read_adjustment | no fitting, tuning, selection or threshold-adjustment function is called after the logged final-test read timestamp |

## Interpretation Boundary

This result is a confirmatory sanity check, not a performance claim. It may not be cited in the model card, README, case study, portfolio material or any interview narrative as a performance figure; it is cited with its five-onset support stated inline. No result changes the champion, the operating points, the predictor contract or any prior decision.

## Gate

This partition is now spent. A second access requires a superseding decision recorded before it occurs.
