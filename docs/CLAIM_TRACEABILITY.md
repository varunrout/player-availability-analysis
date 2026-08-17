# Claim Traceability

Every factual claim in `README.md`, `docs/MODEL_CARD.md`, and the hardcoded interpretive text in the dashboard's API layer, mapped to the committed artefact that measures it. This table is generated from `src/player_availability/claims.py`; `tests/unit/test_claim_traceability.py` checks every row mechanically on every test run — a literal claim must appear verbatim (whitespace-normalised) in both its citing document and its source artefact, and a computed claim must reproduce its stated figure from the source artefact's own values. If a figure changes in either place without the other being updated, the gate fails.

**Coverage: 42 claims, 42 traced, 0 untraceable.**

| Claim | Stated in | Source artefact | Figure |
|---|---|---|---|
| V1-P5 confirmatory overprediction ratio (~3.7x) | `README.md` | `outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv` | `computed = 3.7 (rounded to 1 dp)` |
| 73 recorded onsets under the primary 3-day gap rule | `README.md` | `outputs/analysis/01_outcome_eda/tables/episode_gap_sensitivity.csv` | `3,162,306,299,7,147,73,33,55,92,1.0,24` |
| 18 represented onsets in pooled rolling-origin development evidence | `README.md` | `outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv` | `percentile,0.025,16815,16815,421,2.503716919417187,38,0.0...` |
| 5 represented onsets in the V1-P5 confirmatory final test | `README.md` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `8845,419,4.737139626907857,14,0.03341288782816229,5,3,0.6...` |
| 66 recorded decisions | `README.md` | `docs/DECISION_LOG.md` | `computed = 66 (rounded to 0 dp)` |
| ~99 GB compressed source archive | `README.md` | `docs/PROJECT_STATE.md` | `computed = 99.1 (rounded to 1 dp)` |
| 56 represented onsets in the training partition | `docs/MODEL_CARD.md` | `outputs/analysis/07_prospective_protocol/tables/partition_support.csv` | `train,2020-01-29,2020-12-24,16365,50,2,280,56,12,false` |
| 5 represented onsets in the validation partition | `docs/MODEL_CARD.md` | `outputs/analysis/07_prospective_protocol/tables/partition_support.csv` | `validation,2021-01-01,2021-06-23,8690,50,2,28,5,3,false` |
| 5 represented onsets in the locked final test partition | `docs/MODEL_CARD.md` | `outputs/analysis/07_prospective_protocol/tables/partition_support.csv` | `test,2021-07-01,2021-12-24,8845,50,2,35,5,4,false` |
| 12 of 50 players carry a development-partition event | `docs/MODEL_CARD.md` | `outputs/analysis/07_prospective_protocol/tables/partition_support.csv` | `train,2020-01-29,2020-12-24,16365,50,2,280,56,12,false` |
| 74.6% of onsets from five players | `docs/MODEL_CARD.md` | `outputs/analysis/06_cohort_outcome_sensitivity/tables/event_concentration.csv` | `5,TeamA-c4ccf1a6-48c3-4a17-8d6c-eedd12e8680e,4,0.05633802...` |
| 135 recorded episode starts in 2020 | `docs/MODEL_CARD.md` | `outputs/analysis/01_outcome_eda/tables/episode_starts_by_month.csv` | `computed = 135 (rounded to 0 dp)` |
| 12 recorded episode starts in 2021 | `docs/MODEL_CARD.md` | `outputs/analysis/01_outcome_eda/tables/episode_starts_by_month.csv` | `computed = 12 (rounded to 0 dp)` |
| 18,107 eligible player-days in 2020 (broad C0 scenario) | `docs/MODEL_CARD.md` | `outputs/analysis/06_cohort_outcome_sensitivity/tables/temporal_coverage.csv` | `computed = 18107 (rounded to 0 dp)` |
| 17,885 eligible player-days in 2021 (broad C0 scenario) | `docs/MODEL_CARD.md` | `outputs/analysis/06_cohort_outcome_sensitivity/tables/temporal_coverage.csv` | `computed = 17885 (rounded to 0 dp)` |
| 62.9% ordinary-day vs 97.3% onset-day wellness reporting | `docs/MODEL_CARD.md` | `outputs/analysis/02_missingness_eda/tables/reporting_process_findings.csv` | `Mean pre-onset wellness report rate is 62.9%; onset-day r...` |
| Review access is shared-credential, not production authentication | `docs/MODEL_CARD.md` | `docs/DECISION_LOG.md` | `Authentication is shared-credential and is recorded as a ...` |
| F1 raw Brier score 0.006325 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv` | `F1_raw,F1,raw,M1-F1_raw-CAL,16815,104,0.00618495391019922...` |
| F1 Platt-scaled Brier score 0.007765 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv` | `0.007765206891149171` |
| F1 isotonic Brier score 0.007509 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv` | `0.007508776628116689` |
| Platt mean prediction moves from 0.023012 to 0.027423 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv` | `0.027422957961875` |
| Development alert rate realised at 2.5% target: 2.504% | `docs/MODEL_CARD.md` | `outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv` | `2.503716919417187` |
| Held-out alert rate realised at 2.5% target: 4.737% | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `4.737139626907857` |
| Development false alerts per captured onset at 2.5%: 34.8 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv` | `34.81818181818182` |
| Held-out false alerts per captured onset at 2.5%: 135.0 | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `135.0` |
| In-sample 2.5% probability threshold: 0.033831 | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `0.03383118401132315` |
| Recall transferred within one point: 0.600 held-out against 0.611 development | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `0.6` |
| C1 (ranking better than chance) supported | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/claims.csv` | `better than chance (ROC-AUC above 0.5),true` |
| C2 (overprediction pattern transfers) supported | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/claims.csv` | `risk in the large (development finding: roughly 3.7x),true` |
| C3 (false-alert burden of development order) not supported | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/claims.csv` | `development order (tens of false alerts per captured onse...` |
| Final-test support: 8,845 player-days, 35 positive days, 5 represented onsets | `docs/MODEL_CARD.md` | `outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv` | `M1-F1-FINAL,8845.0,35.0` |
| daily_load_log1p has unstable coefficient sign across 54 estimable folds | `docs/MODEL_CARD.md` | `outputs/modelling/exp_018_explanation/tables/coefficient_stability.csv` | `daily_load_log1p,54,false,` |
| Attribution reproduces the model's own logit to zero floating-point error | `docs/MODEL_CARD.md` | `outputs/modelling/exp_018_explanation/tables/explanation_findings.csv` | `reproduce the model's own logit to within 0.00e+00` |
| EXP-016 arm A vs F1 unseen-player AP gap: 0.001008 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_016_ablation/tables/unseen_player_aggregate_metrics.csv` | `A,0.022308170813787043` |
| EXP-016 arm C vs F1 unseen-player AP gap: 0.000816 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_016_ablation/tables/unseen_player_aggregate_metrics.csv` | `C,0.02250006829102736` |
| EXP-007 own-clock (leakage) unseen-player AP: 0.104533 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_007_survival/tables/unseen_player_aggregate_metrics.csv` | `cox,own_clock,leakage_diagnostic_contrast,0.1045332153745...` |
| EXP-007 reset-clock (valid) unseen-player AP: 0.019292 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_007_survival/tables/unseen_player_aggregate_metrics.csv` | `cox,reset_clock,primary_leave_one_player_out_result,0.019...` |
| EXP-008 Brier paired interval excludes zero under both resampling schemes | `docs/MODEL_CARD.md` | `outputs/modelling/exp_008_boosting/tables/paired_boosted_vs_f1_differences.csv` | `-0.00036519521651397706,-0.00017130659697680824,-0.000046...` |
| EXP-008 boosted calibration slope 2.537922 against F1's 2.019474 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_008_boosting/tables/arm_pooled_metrics.csv` | `2.5379221107797747` |
| EXP-008 training AP 0.256236 against validation AP 0.013013 | `docs/MODEL_CARD.md` | `outputs/modelling/exp_008_boosting/tables/training_validation_gap.csv` | `-0.012712511544389845,0.25623638233938656,0.0130134612340...` |
| Dashboard C3 explanation cites held-out onset density ratio 0.565 against 1.071 | `src/player_availability/api/app.py` | `docs/PROJECT_STATE.md` | `0.565 against 1.071 per thousand player-days` |
| Dashboard C3 explanation cites the realised 4.737% held-out alert rate | `src/player_availability/api/app.py` | `outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv` | `4.737139626907857` |

Entries with a computed figure (sums, ratios, differences) are not a literal substring in the source artefact; the test derives the value from the source's own columns and checks it against the stated figure.

## Forbidden claims

Figures that must never appear bare, without their governing context, in a given document. Checked by the same test suite (`test_forbidden_claim_does_not_appear`).

| Guard | Location | Forbidden text | Reason |
|---|---|---|---|
| `readme-no-bare-final-test-roc-auc` | `README.md` | `0.827` | DEC-063 permits the V1-P5 confirmatory ROC-AUC only reported alongside its five-onset support. README.md is prose, not the model card's table, so the figure is described qualitatively there instead and must not reappear bare. |
