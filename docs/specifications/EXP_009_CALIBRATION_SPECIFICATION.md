# EXP-009 - Calibration Specification

**Status:** PROPOSED, awaiting project-owner approval
**Phase:** V1-P1
**Authorised in scope by:** `DEC-044`
**Candidate under test:** M1 F3, promoted by `DEC-043`
**Final-test access:** PROHIBITED

---

## 1. Question

Does post-hoc calibration materially improve the probability quality of the M1 F3 candidate, and can any calibration method be distinguished from another at the available support?

The second half of that question is not rhetorical. It is a permitted and expected answer.

## 2. Why this experiment exists

M1 raw probabilities are materially overestimated: mean prediction 1.965% against an observed positive-day rate of 0.322%, roughly a sixfold overstatement, with calibration intercept -0.356 and slope 1.433. M1 records worse Brier and log loss than the M0 operational baseline despite better ranking.

Under `DEC-007` calibration is a first-class metric, so a ranking gain accompanied by degraded probability quality cannot be promoted. A practitioner told a player carries 2% risk when the underlying rate is 0.3% will misallocate review capacity.

## 3. Methods compared

| Arm | Method | Notes |
|---|---|---|
| A | Raw | Uncalibrated F3 output, the reference |
| B | Platt | Logistic regression on the F3 log-odds |
| C | Isotonic | Non-parametric monotonic fit |

F1 raw is carried as a secondary reference so the calibration question stays separable from the feature-set question settled in `DEC-043`.

Isotonic is included despite being the method most likely to overfit at this support. Demonstrating that it overfits here is itself a useful and reportable result.

## 4. Data and fitting discipline

- **Development partitions only.** Final-test data is neither read nor scored.
- Calibrators are fitted **only** on development data, never on the data used to report calibrated performance. Fitting a calibrator on the same rows used to evaluate it would manufacture apparent improvement.
- Fitting follows the pooled rolling-origin structure established as headline by `DEC-047`: within each fold, the calibrator is fitted on that fold's training portion and applied to its held-out portion. Calibrated metrics are then pooled across folds.
- Preprocessing scope is unchanged and remains train-only, per `DEC-036`.
- The cohort, predictor contract, partitions and embargoes are unchanged.

## 5. Outputs

Primary, per arm, pooled rolling-origin:

- Reliability curve, with bin counts shown rather than implied
- Calibration slope and intercept
- Expected calibration error
- Brier score and log loss
- Mean predicted risk against observed rate

Secondary:

- Same metrics on the fixed chronological validation window, as a temporal stress result
- Per-fold values for every pooled figure, so instability stays visible
- One-day-gap sensitivity for every headline figure, per `DEC-048`
- Alert-budget behaviour at the frozen 1%, 2.5% and 5% review rates, since calibration changes probabilities but should leave ranking unchanged for Platt

Uncertainty:

- Paired bootstrap intervals under both player-cluster and temporal week-block resampling, matching the EXP-003 protocol so results remain comparable

## 6. Mandatory audit: sparse predictor sensitivity

Required by `DEC-043`.

The robust fatigue z-score is observed on 8.4% of primary-cohort days. The audit must report:

1. Calibration metrics computed separately on days where this predictor is observed against days where it is absent.
2. Whether calibrated performance depends on the predictor's availability pattern rather than its value.

If calibration behaviour is materially different across those two groups, the predictor is behaving as a proxy for reporting activity rather than physiology, and it becomes a removal candidate carried into V1-P4.

## 7. Power limitation, binding

Development support is 56 onsets in train and five in the validation window. Reliability curves estimated at this support carry very wide uncertainty, and expected calibration error is badly behaved when bins contain almost no positives.

The following are binding on reporting:

- Every conclusion states the supporting event count inline, not in a footnote.
- No method is declared superior on point estimates alone. A difference is claimed only where the paired interval excludes zero.
- **"No calibration method is distinguishable at this support" is a valid, expected and complete result.** It must be reported as such rather than resolved by selecting the best point estimate.
- Reliability bins containing fewer than five positive days are reported with counts and excluded from any summary statistic that assumes bin stability.

## 8. Success criteria

The experiment succeeds if the calibration behaviour of F3 is characterised honestly and the sparse-predictor audit is completed. It does not require finding a method that improves calibration.

Explicit non-goals: selecting a deployment threshold, accessing final-test data, changing the feature set, changing the cohort, or retuning the model.

## 9. Automated integrity checks

| ID | Check |
|---|---|
| CAL-01 | Zero final-test predictions or performance metrics produced |
| CAL-02 | Calibrator fitting partitions disjoint from evaluation partitions in every fold |
| CAL-03 | Predictor contract unchanged from the frozen F3 contract |
| CAL-04 | Ranking preserved under Platt, since a monotonic transform must not alter order |
| CAL-05 | Every reported metric carries its supporting event count |
| CAL-06 | Sparse-predictor availability audit present and populated |
| CAL-07 | One-day-gap sensitivity present for every headline figure |
| CAL-08 | Zero-positive folds identified and excluded from discrimination aggregation, with counts stated |

## 10. Deliverables

Following the `DEC-029` contract: shared analysis functions, a canonical script persisting outputs under `outputs/modelling/exp_009_calibration/`, a matching output-free notebook, retained tables and figures, and focused tests.

## 11. Gate

The project owner approves this specification before implementation. On completion, the owner reviews results before V1-P2 begins.
