# Phase B - Chronological Split Manifest

## Purpose

This document freezes the shared chronological partitions for subjective model development. It contains no fitted model and no performance claim.

## Leakage Controls

- Primary maximum horizon: `14` days.
- Feature-history requirement: `28` days.
- Boundary embargo: `14` calendar days, matching the maximum headline horizon.
- The predictor contract is an explicit allow-list; labels, eligibility, identifiers, dates, episode-state and provenance fields are not predictors.
- Imputation, scaling, feature selection and calibration must be fit within their permitted development partition only.

## Frozen Date Boundaries

| Segment | Start | End |
|---|---|---|
| Source dates eligible for split construction | 2020-01-28 | 2021-12-17 |
| Train | 2020-01-28 | 2021-03-16 |
| Train-validation embargo | 2021-03-17 | 2021-03-30 |
| Validation | 2021-03-31 | 2021-08-15 |
| Validation-test embargo | 2021-08-16 | 2021-08-29 |
| Test | 2021-08-30 | 2021-12-17 |

## Assigned Rows

| Partition | All player-days | 14-day primary eligible player-days |
|---|---:|---:|
| pre_history | 1,350 | 0 |
| train | 20,700 | 20,505 |
| embargo_train_validation | 700 | 0 |
| validation | 6,900 | 6,900 |
| embargo_validation_test | 700 | 0 |
| test | 5,500 | 5,495 |
| post_primary_horizon | 700 | 0 |

## Predictor Contract

The frozen `subjective_v1` contract contains `34` candidate predictors:

- `daily_load`
- `fatigue`
- `readiness`
- `wellness_report_present`
- `wellness_metric_count`
- `session_count`
- `session_duration_minutes`
- `session_srpe`
- `daily_load_sum_3d`
- `session_duration_sum_3d`
- `session_srpe_sum_3d`
- `fatigue_mean_3d`
- `readiness_mean_3d`
- `daily_load_sum_7d`
- `session_duration_sum_7d`
- `session_srpe_sum_7d`
- `fatigue_mean_7d`
- `readiness_mean_7d`
- `daily_load_sum_14d`
- `session_duration_sum_14d`
- `session_srpe_sum_14d`
- `fatigue_mean_14d`
- `readiness_mean_14d`
- `daily_load_sum_28d`
- `session_duration_sum_28d`
- `session_srpe_sum_28d`
- `fatigue_mean_28d`
- `readiness_mean_28d`
- `daily_load_baseline_mean_prior`
- `daily_load_zscore_prior`
- `fatigue_baseline_mean_prior`
- `fatigue_zscore_prior`
- `readiness_baseline_mean_prior`
- `readiness_zscore_prior`

## Next Gate

EXP-002 may now implement the naive prevalence baseline against these partitions. It must report the same fixed test partition only once, after development decisions are complete.
