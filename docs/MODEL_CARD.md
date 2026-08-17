# Model Card: Player Availability Analysis (V1, F1 champion)

Per `DEC-046`, this card leads with limitations. Nothing below the Limitations
section should be read without it.

Every numeric claim in this card cites the specific committed artefact that
measures it. `docs/CLAIM_TRACEABILITY.md` maps every one of them mechanically;
a test fails if a cited figure stops appearing in its source.

## Limitations (read this first)

**Outcome support is small and concentrated.** The frozen cohort represents
66 onsets across the three chronological partitions: 56 in training, 5 in
validation, 5 in the locked final test
(`outputs/analysis/07_prospective_protocol/tables/partition_support.csv`).
Only 12 of the 50 players in the roster carry any positive event in the
training partition (same table, `represented_event_player_count` for the
`train` row). Five players account for 74.6% of all represented onsets
(`outputs/analysis/06_cohort_outcome_sensitivity/tables/event_concentration.csv`,
cumulative share at rank 5). Every metric in this card is underpowered by
these numbers, not by a modelling failure — no cohort redefinition tested
during V1 changed this materially (`DEC-046`).

**The system is partly reading reporting behaviour, not injury incidence,
and this is disclosed rather than managed away.** Recorded episode starts
fall from 135 in 2020 to 12 in 2021 — roughly tenfold — while eligible
player-days stay flat (18,107 against 17,885)
(`outputs/analysis/01_outcome_eda/tables/episode_starts_by_month.csv`;
`outputs/analysis/06_cohort_outcome_sensitivity/tables/temporal_coverage.csv`,
`C0` scenario, summed by year). Over the same period, mean wellness-report
rate is 62.9% on ordinary days in the 28 days before an onset and 97.3% on
the onset day itself
(`outputs/analysis/02_missingness_eda/tables/reporting_process_findings.csv`,
`event_centered_reporting` row). Wellness reporting rising sharply on
injury-onset days, combined with a matching decline in recorded onsets, is
the signature of decaying self-report engagement, not declining injury
incidence. A model trained on this cohort is trained partly on *when
players report*, and no correction for this is applied — it is a property
of the source data, stated here rather than hidden inside a metric.

**The confirmatory final-test result is not a performance claim.** It rests
on five onsets. See below.

**Review access is shared-credential, not production authentication.** The
deployed dashboard uses one Basic-Auth credential distributed to reviewers,
never per-user accounts. This is a review-access control, not a
production-grade authentication model, and must not be represented as one
(`DEC-064`).

**Self-reported, not clinically verified.** Every outcome in this system is
a self-reported injury or illness event, not a medically confirmed
diagnosis. Episode boundaries are reconstructed from reporting patterns
under a fixed gap rule and are sensitive to that choice
(`DEC-030`).

## Intended use

Practitioner decision support: a ranked, explainable signal to help a
sports-science or medical staff triage where to look next, alongside their
own judgement and other information sources.

## Out-of-scope use

Never diagnosis. Never a clearance or return-to-play decision. Never a
standalone fitness or participation assessment. Never used to justify
withholding a player from participation without independent clinical
review. The dashboard's interface copy is held to this by an automated
test over the rendered text, not by review alone
(`tests/unit/test_web_copy_constraints.py`).

## Model

**Champion:** F1, a regularised logistic regression over nine frozen
predictors, reporting raw probabilities with no post-hoc calibrator
(`DEC-058`, `DEC-060`).

No calibrator was adopted because both alternatives evaluated against raw
degrade probability quality. Platt scaling and isotonic regression were
both compared to raw F1 probabilities over 16,815 pooled player-days and
104 positive days
(`outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv`,
`F1_raw`/`F1_platt`/`F1_isotonic` rows): raw Brier 0.006325 against Platt
0.007765 and isotonic 0.007509; raw log loss 0.042009 against Platt
0.044835 and isotonic 0.062091. Isotonic's Brier cost excludes zero under
both resampling schemes and is rejected on that basis alone. Platt's
rejection rests on different grounds under `DEC-059`, which corrects
`DEC-058`'s original reasoning: Platt's Brier cost excludes zero under
temporal week-block resampling only, not player-cluster resampling, so it
does not clear this project's own two-scheme bar for a cost claim. Platt is
instead rejected on calibration-in-the-large: its mean prediction moves
from 0.023012 to 0.027423 against an observed rate of 0.006185, so
overprediction rises from roughly 3.7x to roughly 4.4x, alongside the
unqualified log-loss degradation above.

## Operating points

The dashboard offers two review rates, 2.5% (default) and 5%, each
displaying both the pooled development burden that motivated the choice and
the measured held-out burden, side by side, never one without the other
(`DEC-061`, `DEC-063`, enforced by
`tests/unit/test_web_copy_constraints.py::test_operating_point_burden_never_shown_development_figure_alone`).

| | Development (pooled rolling-origin, 16,815 player-days, 18 represented onsets) | Held-out (V1-P5 final test, 8,845 player-days, 5 represented onsets) |
|---|---|---|
| Alert rate realised at 2.5% target | 2.504% | 4.737% |
| False alerts per captured onset at 2.5% | 34.8 | 135.0 |

Sources:
`outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv`
(`percentile`, `0.025` row) and
`outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv`
(`review_rate=0.025` row).

The in-sample-derived 2.5% probability threshold (0.033831) did not
transfer its target alert rate to held-out data — it realised 4.737%
instead of 2.5% — while recall transferred within one point (0.600 held-out
against 0.611 development). `DEC-063` attributes the resulting burden gap
to two compounding, non-champion causes: held-out onset density is roughly
half development's, and the threshold's calibration to a target rate did
not transfer even though ranking behaviour did. This is recorded as a V2
methodological finding: derive operating thresholds from out-of-fold
predictions, not a model's in-sample predictions on rows it was fitted on.

## V1-P5 confirmatory result

Pre-registered before any evaluation code existed (`DEC-062`, committed at
`650f67e1883b655124324219c20cca09f19c3eba`) and spent exactly once. **This
is a confirmatory sanity check on five represented onsets, not a
performance claim**, and may not be cited as one in any external material.

| Claim | Statement | Supported | Evidence |
|---|---|---|---|
| C1 | Ranking on unseen future data is better than chance (ROC-AUC above 0.5) | Yes | ROC-AUC = 0.827204 |
| C2 | The champion overpredicts risk in the large, roughly matching the development finding | Yes | mean prediction 0.014824 vs observed rate 0.003957 (3.7x) |
| C3 | False-alert burden at the 2.5% operating point is of the development order (tens per captured onset) | No | 135.0 false alerts per captured onset |

Source: `outputs/modelling/v1_p5_final_test/tables/claims.csv`,
`final_test_metrics.csv`. Support: 8,845 player-days, 35 positive days, 5
represented onsets — stated here, and stated inline on the dashboard's
model-health view, every time this result is cited.

## Explainability

Driver contributions restrict to the eight predictors with constant
coefficient sign across every estimable fold (54 fold-fits: 4 rolling-origin
plus 50 leave-one-player-out). `daily_load_log1p` is the one predictor with
unstable sign and is excluded from the displayed driver set
(`DEC-060`; `outputs/modelling/exp_018_explanation/tables/coefficient_stability.csv`,
`constant_sign=false` row). It also carries the smallest coefficient
magnitude of the nine predictors in that same table (mean magnitude rank
8.85 of 9).

Attribution is exact: summed per-predictor contributions plus intercept
reproduce the model's own logit to zero floating-point error
(`outputs/modelling/exp_018_explanation/tables/explanation_findings.csv`,
`EXPL-03`).

## Findings that overturned an initially favourable result

Three results looked favourable on a first read and were overturned by a
pre-registered check before being adopted. Each is recorded here because a
model card that only shows the surviving conclusion hides the process that
makes the surviving conclusion trustworthy.

**EXP-016 — the robust-fatigue predictor was an availability artefact, not
a value effect.** Removing the continuous robust-fatigue z-score but
keeping its missingness indicator (arm C) is statistically indistinguishable
from the full F3 candidate (arm A) on pooled metrics — both paired-bootstrap
intervals for Brier and average precision include zero
(`outputs/modelling/exp_016_ablation/tables/paired_arm_differences.csv`,
arm A vs C rows) — while narrowing part of F3's unseen-player gap to F1:
average-precision gap falls from 0.001008 (arm A vs F1) to 0.000816 (arm C
vs F1), ROC-AUC gap from 0.011651 to 0.011356
(`outputs/modelling/exp_016_ablation/tables/unseen_player_aggregate_metrics.csv`).
The predictor's apparent value was carried by *whether it was reported*, not
by its magnitude. This directly motivated `DEC-054`'s selection of F1 over
F3 as champion.

**EXP-007 — the Cox survival model's unseen-player advantage was
gap-time-clock leakage.** Evaluated with each held-out player's gap-time
clock reset to their own onset history (`own_clock`), the Cox model
appeared to dominate: average precision 0.104533, ROC-AUC 0.817861. A
pre-registered diagnostic re-ran the identical fitted models with the clock
reset to post-burn-in study origin instead (`reset_clock`, the valid
leave-one-player-out result): average precision fell to 0.019292, ROC-AUC
to 0.576890 — both below F1's 0.023316 / 0.642578
(`outputs/modelling/exp_007_survival/tables/unseen_player_aggregate_metrics.csv`).
Indexing a held-out player by their own onset history had supplied outcome
information a genuinely unseen player would never expose. Survival framing
was rejected for V1 under `DEC-055` on this evidence, not on a raw metric
comparison.

**EXP-008 — gradient boosting won on one metric and failed the adoption
gate on the others.** Boosted classification's Brier score beats F1 with
both paired-bootstrap intervals excluding zero: player-cluster
[-0.000365, -0.000046], temporal week-block [-0.000274, -0.000096]
(`outputs/modelling/exp_008_boosting/tables/paired_boosted_vs_f1_differences.csv`).
On every other axis it does not: calibration slope is worse (2.537922
against F1's 2.019474) and ROC-AUC is worse both pooled (0.788733 against
0.835537) and unseen-player (0.554999 against 0.642578)
(`outputs/modelling/exp_008_boosting/tables/arm_pooled_metrics.csv`,
`unseen_player_aggregate_metrics.csv`). Training average precision (0.256236)
against validation (0.013013) — a roughly twentyfold gap — is the
pre-registered overfitting signature
(`outputs/modelling/exp_008_boosting/tables/training_validation_gap.csv`).
The adoption gate required calibrated performance to improve overall, not
one component of it in isolation; boosted classification was rejected under
`DEC-056` on that basis.

## Governance references

Full decision history: [`DECISION_LOG.md`](DECISION_LOG.md) (`DEC-001`
through `DEC-066`). Current project state: [`PROJECT_STATE.md`](PROJECT_STATE.md).
Analysis and experiment specifications: [`19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`](19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md).
Claim-by-claim source mapping: [`CLAIM_TRACEABILITY.md`](CLAIM_TRACEABILITY.md).
