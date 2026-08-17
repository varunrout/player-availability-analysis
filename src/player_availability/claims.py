"""Claim traceability registry (V1-P8, `DEC-046` exit criterion).

Every entry maps one factual claim in `README.md`, `docs/MODEL_CARD.md` or a
hardcoded interface string to the specific committed artefact that measures
it. `tests/unit/test_claim_traceability.py` checks every entry mechanically:
a literal claim must appear verbatim in both its citing document and its
source artefact; a computed claim must reproduce its stated figure from the
source artefact's own values. `docs/CLAIM_TRACEABILITY.md` is the rendered
form of this table, not a second source of truth for it.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from player_availability.utils.paths import repo_root


@dataclass(frozen=True, slots=True)
class Claim:
    """One traceable claim.

    `source_text`, when set, must appear verbatim in `source` (a direct
    literal citation: a table cell, a written finding). `compute`, when set,
    is a zero-argument callable reading `source` and returning a float that
    must equal `expected` within `round_ndigits` (a derived figure: a sum,
    a ratio, a difference). Exactly one of the two must be set.
    """

    id: str
    claim: str
    location: str
    location_text: str
    source: str
    source_text: str | None = None
    compute: Callable[[Path], float] | None = None
    expected: float | None = None
    round_ndigits: int = 3


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sum_episode_starts(year: str) -> Callable[[Path], float]:
    def _compute(path: Path) -> float:
        return float(
            sum(int(row["episode_starts"]) for row in _rows(path) if row["month"].startswith(year))
        )

    return _compute


def _sum_eligible_player_days(year: str) -> Callable[[Path], float]:
    def _compute(path: Path) -> float:
        return float(
            sum(
                int(row["eligible_player_days"])
                for row in _rows(path)
                if row["scenario_id"] == "C0" and row["month"].startswith(year)
            )
        )

    return _compute


def _final_test_overprediction_ratio(path: Path) -> float:
    row = _rows(path)[0]
    return float(row["mean_prediction"]) / float(row["observed_rate"])


def _decision_count(path: Path) -> float:
    return float(
        sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## DEC-")
        )
    )


def _archive_bucket_gb(path: Path) -> float:
    text = path.read_text(encoding="utf-8")
    marker = "99,132,769,855 bytes"
    if marker not in text:
        raise AssertionError(f"{marker!r} not found in {path}")
    return 99_132_769_855 / 1e9


CLAIMS: tuple[Claim, ...] = (
    # --- README.md ---
    Claim(
        id="readme-final-test-roc-auc",
        claim="V1-P5 confirmatory ROC-AUC",
        location="README.md",
        location_text="ROC-AUC 0.827",
        source="outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv",
        source_text="0.8272044754337603",
    ),
    Claim(
        id="readme-overprediction-ratio",
        claim="V1-P5 confirmatory overprediction ratio (~3.7x)",
        location="README.md",
        location_text="3.7x overprediction",
        source="outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv",
        compute=_final_test_overprediction_ratio,
        expected=3.7,
        round_ndigits=1,
    ),
    Claim(
        id="readme-onsets-total",
        claim="73 recorded onsets under the primary 3-day gap rule",
        location="README.md",
        location_text="73 recorded onsets",
        source="outputs/analysis/01_outcome_eda/tables/episode_gap_sensitivity.csv",
        source_text="3,162,306,299,7,147,73,33,55,92,1.0,24",
    ),
    Claim(
        id="readme-onsets-pooled-development",
        claim="18 represented onsets in pooled rolling-origin development evidence",
        location="README.md",
        location_text="18 in the pooled rolling-origin development evidence",
        source="outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv",
        source_text="percentile,0.025,16815,16815,421,2.503716919417187,38,0.09026128266033254,18,11",
    ),
    Claim(
        id="readme-onsets-final-test",
        claim="5 represented onsets in the V1-P5 confirmatory final test",
        location="README.md",
        location_text="5 in the confirmatory final test",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="8845,419,4.737139626907857,14,0.03341288782816229,5,3,0.6,135.0",
    ),
    Claim(
        id="readme-decision-count",
        claim="66 recorded decisions",
        location="README.md",
        location_text="66 recorded decisions",
        source="docs/DECISION_LOG.md",
        compute=_decision_count,
        expected=66,
        round_ndigits=0,
    ),
    Claim(
        id="readme-archive-size",
        claim="~99 GB compressed source archive",
        location="README.md",
        location_text="99 GB compressed",
        source="docs/PROJECT_STATE.md",
        compute=_archive_bucket_gb,
        expected=99.1,
        round_ndigits=1,
    ),
    # --- docs/MODEL_CARD.md: outcome support ---
    Claim(
        id="card-train-onsets",
        claim="56 represented onsets in the training partition",
        location="docs/MODEL_CARD.md",
        location_text="56 in training",
        source="outputs/analysis/07_prospective_protocol/tables/partition_support.csv",
        source_text="train,2020-01-29,2020-12-24,16365,50,2,280,56,12,false",
    ),
    Claim(
        id="card-validation-onsets",
        claim="5 represented onsets in the validation partition",
        location="docs/MODEL_CARD.md",
        location_text="5 in validation",
        source="outputs/analysis/07_prospective_protocol/tables/partition_support.csv",
        source_text="validation,2021-01-01,2021-06-23,8690,50,2,28,5,3,false",
    ),
    Claim(
        id="card-final-test-onsets-frozen",
        claim="5 represented onsets in the locked final test partition",
        location="docs/MODEL_CARD.md",
        location_text="5 in the locked final test",
        source="outputs/analysis/07_prospective_protocol/tables/partition_support.csv",
        source_text="test,2021-07-01,2021-12-24,8845,50,2,35,5,4,false",
    ),
    Claim(
        id="card-dev-event-players",
        claim="12 of 50 players carry a development-partition event",
        location="docs/MODEL_CARD.md",
        location_text="Only 12 of the 50 players",
        source="outputs/analysis/07_prospective_protocol/tables/partition_support.csv",
        source_text="train,2020-01-29,2020-12-24,16365,50,2,280,56,12,false",
    ),
    Claim(
        id="card-five-player-concentration",
        claim="74.6% of onsets from five players",
        location="docs/MODEL_CARD.md",
        location_text="74.6% of all represented onsets",
        source="outputs/analysis/06_cohort_outcome_sensitivity/tables/event_concentration.csv",
        source_text="5,TeamA-c4ccf1a6-48c3-4a17-8d6c-eedd12e8680e,4,0.056338028169014086,0.7464788732394366",
    ),
    Claim(
        id="card-onsets-2020",
        claim="135 recorded episode starts in 2020",
        location="docs/MODEL_CARD.md",
        location_text="135 in 2020",
        source="outputs/analysis/01_outcome_eda/tables/episode_starts_by_month.csv",
        compute=_sum_episode_starts("2020"),
        expected=135,
        round_ndigits=0,
    ),
    Claim(
        id="card-onsets-2021",
        claim="12 recorded episode starts in 2021",
        location="docs/MODEL_CARD.md",
        location_text="to 12 in 2021",
        source="outputs/analysis/01_outcome_eda/tables/episode_starts_by_month.csv",
        compute=_sum_episode_starts("2021"),
        expected=12,
        round_ndigits=0,
    ),
    Claim(
        id="card-player-days-2020",
        claim="18,107 eligible player-days in 2020 (broad C0 scenario)",
        location="docs/MODEL_CARD.md",
        location_text="18,107 against 17,885",
        source="outputs/analysis/06_cohort_outcome_sensitivity/tables/temporal_coverage.csv",
        compute=_sum_eligible_player_days("2020"),
        expected=18107,
        round_ndigits=0,
    ),
    Claim(
        id="card-player-days-2021",
        claim="17,885 eligible player-days in 2021 (broad C0 scenario)",
        location="docs/MODEL_CARD.md",
        location_text="18,107 against 17,885",
        source="outputs/analysis/06_cohort_outcome_sensitivity/tables/temporal_coverage.csv",
        compute=_sum_eligible_player_days("2021"),
        expected=17885,
        round_ndigits=0,
    ),
    Claim(
        id="card-reporting-rates",
        claim="62.9% ordinary-day vs 97.3% onset-day wellness reporting",
        location="docs/MODEL_CARD.md",
        location_text="62.9% on ordinary days",
        source="outputs/analysis/02_missingness_eda/tables/reporting_process_findings.csv",
        source_text="Mean pre-onset wellness report rate is 62.9%; onset-day rate is 97.3%",
    ),
    Claim(
        id="card-shared-credential",
        claim="Review access is shared-credential, not production authentication",
        location="docs/MODEL_CARD.md",
        location_text="Review access is shared-credential",
        source="docs/DECISION_LOG.md",
        source_text="Authentication is shared-credential and is recorded as a review-access",
    ),
    # --- docs/MODEL_CARD.md: champion and calibration ---
    Claim(
        id="card-calibration-raw-brier",
        claim="F1 raw Brier score 0.006325",
        location="docs/MODEL_CARD.md",
        location_text="raw Brier 0.006325",
        source="outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv",
        source_text="F1_raw,F1,raw,M1-F1_raw-CAL,16815,104,0.006184953910199227,0.006324593504925363",
    ),
    Claim(
        id="card-calibration-platt-brier",
        claim="F1 Platt-scaled Brier score 0.007765",
        location="docs/MODEL_CARD.md",
        location_text="Platt 0.007765",
        source="outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv",
        source_text="0.007765206891149171",
    ),
    Claim(
        id="card-calibration-isotonic-brier",
        claim="F1 isotonic Brier score 0.007509",
        location="docs/MODEL_CARD.md",
        location_text="isotonic 0.007509",
        source="outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv",
        source_text="0.007508776628116689",
    ),
    Claim(
        id="card-platt-overprediction",
        claim="Platt mean prediction moves from 0.023012 to 0.027423",
        location="docs/MODEL_CARD.md",
        location_text="0.023012 to 0.027423",
        source="outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv",
        source_text="0.027422957961875",
    ),
    # --- docs/MODEL_CARD.md: operating points ---
    Claim(
        id="card-dev-alert-rate",
        claim="Development alert rate realised at 2.5% target: 2.504%",
        location="docs/MODEL_CARD.md",
        location_text="2.504%",
        source="outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv",
        source_text="2.503716919417187",
    ),
    Claim(
        id="card-held-out-alert-rate",
        claim="Held-out alert rate realised at 2.5% target: 4.737%",
        location="docs/MODEL_CARD.md",
        location_text="4.737%",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="4.737139626907857",
    ),
    Claim(
        id="card-dev-false-alerts",
        claim="Development false alerts per captured onset at 2.5%: 34.8",
        location="docs/MODEL_CARD.md",
        location_text="| 34.8 |",
        source="outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv",
        source_text="34.81818181818182",
    ),
    Claim(
        id="card-held-out-false-alerts",
        claim="Held-out false alerts per captured onset at 2.5%: 135.0",
        location="docs/MODEL_CARD.md",
        location_text="| 135.0 |",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="135.0",
    ),
    Claim(
        id="card-threshold-in-sample",
        claim="In-sample 2.5% probability threshold: 0.033831",
        location="docs/MODEL_CARD.md",
        location_text="0.033831",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="0.03383118401132315",
    ),
    Claim(
        id="card-recall-transfer",
        claim="Recall transferred within one point: 0.600 held-out against 0.611 development",
        location="docs/MODEL_CARD.md",
        location_text="0.600 held-out against 0.611 development",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="0.6",
    ),
    # --- docs/MODEL_CARD.md: V1-P5 confirmatory result ---
    Claim(
        id="card-c1-supported",
        claim="C1 (ranking better than chance) supported",
        location="docs/MODEL_CARD.md",
        location_text="ROC-AUC above 0.5) | Yes",
        source="outputs/modelling/v1_p5_final_test/tables/claims.csv",
        source_text="better than chance (ROC-AUC above 0.5),true",
    ),
    Claim(
        id="card-c2-supported",
        claim="C2 (overprediction pattern transfers) supported",
        location="docs/MODEL_CARD.md",
        location_text="roughly matching the development finding | Yes",
        source="outputs/modelling/v1_p5_final_test/tables/claims.csv",
        source_text="risk in the large (development finding: roughly 3.7x),true",
    ),
    Claim(
        id="card-c3-not-supported",
        claim="C3 (false-alert burden of development order) not supported",
        location="docs/MODEL_CARD.md",
        location_text="per captured onset) | No",
        source="outputs/modelling/v1_p5_final_test/tables/claims.csv",
        source_text="development order (tens of false alerts per captured onset),false",
    ),
    Claim(
        id="card-final-test-support",
        claim="Final-test support: 8,845 player-days, 35 positive days, 5 represented onsets",
        location="docs/MODEL_CARD.md",
        location_text="8,845 player-days, 35 positive days, 5",
        source="outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv",
        source_text="M1-F1-FINAL,8845.0,35.0",
    ),
    # --- docs/MODEL_CARD.md: explainability ---
    Claim(
        id="card-daily-load-unstable",
        claim="daily_load_log1p has unstable coefficient sign across 54 estimable folds",
        location="docs/MODEL_CARD.md",
        location_text="54 fold-fits",
        source="outputs/modelling/exp_018_explanation/tables/coefficient_stability.csv",
        source_text="daily_load_log1p,54,false,",
    ),
    Claim(
        id="card-attribution-exact",
        claim="Attribution reproduces the model's own logit to zero floating-point error",
        location="docs/MODEL_CARD.md",
        location_text="reproduce the model's own logit to zero floating-point error",
        source="outputs/modelling/exp_018_explanation/tables/explanation_findings.csv",
        source_text="reproduce the model's own logit to within 0.00e+00",
    ),
    # --- docs/MODEL_CARD.md: three overturning findings ---
    Claim(
        id="card-exp016-ap-gap-arm-a",
        claim="EXP-016 arm A vs F1 unseen-player AP gap: 0.001008",
        location="docs/MODEL_CARD.md",
        location_text="falls from 0.001008",
        source="outputs/modelling/exp_016_ablation/tables/unseen_player_aggregate_metrics.csv",
        source_text="A,0.022308170813787043",
    ),
    Claim(
        id="card-exp016-ap-gap-arm-c",
        claim="EXP-016 arm C vs F1 unseen-player AP gap: 0.000816",
        location="docs/MODEL_CARD.md",
        location_text="to 0.000816",
        source="outputs/modelling/exp_016_ablation/tables/unseen_player_aggregate_metrics.csv",
        source_text="C,0.02250006829102736",
    ),
    Claim(
        id="card-exp007-own-clock-ap",
        claim="EXP-007 own-clock (leakage) unseen-player AP: 0.104533",
        location="docs/MODEL_CARD.md",
        location_text="average precision 0.104533",
        source="outputs/modelling/exp_007_survival/tables/unseen_player_aggregate_metrics.csv",
        source_text="cox,own_clock,leakage_diagnostic_contrast,0.10453321537457046",
    ),
    Claim(
        id="card-exp007-reset-clock-ap",
        claim="EXP-007 reset-clock (valid) unseen-player AP: 0.019292",
        location="docs/MODEL_CARD.md",
        location_text="fell to 0.019292",
        source="outputs/modelling/exp_007_survival/tables/unseen_player_aggregate_metrics.csv",
        source_text="cox,reset_clock,primary_leave_one_player_out_result,0.019292591619845853",
    ),
    Claim(
        id="card-exp008-brier-interval",
        claim="EXP-008 Brier paired interval excludes zero under both resampling schemes",
        location="docs/MODEL_CARD.md",
        location_text="player-cluster [-0.000365, -0.000046]",
        source="outputs/modelling/exp_008_boosting/tables/paired_boosted_vs_f1_differences.csv",
        source_text="-0.00036519521651397706,-0.00017130659697680824,-0.00004634461716517757",
    ),
    Claim(
        id="card-exp008-calibration-slope",
        claim="EXP-008 boosted calibration slope 2.537922 against F1's 2.019474",
        location="docs/MODEL_CARD.md",
        location_text="2.537922",
        source="outputs/modelling/exp_008_boosting/tables/arm_pooled_metrics.csv",
        source_text="2.5379221107797747",
    ),
    Claim(
        id="card-exp008-training-validation-gap",
        claim="EXP-008 training AP 0.256236 against validation AP 0.013013",
        location="docs/MODEL_CARD.md",
        location_text="0.256236) against validation (0.013013)",
        source="outputs/modelling/exp_008_boosting/tables/training_validation_gap.csv",
        source_text="-0.012712511544389845,0.25623638233938656,0.013013461234069563",
    ),
    # --- dashboard interface (hardcoded interpretive text) ---
    Claim(
        id="interface-c3-explanation-onset-density",
        claim="Dashboard C3 explanation cites held-out onset density ratio 0.565 against 1.071",
        location="src/player_availability/api/app.py",
        location_text="0.565 against 1.071 onsets per thousand player-days",
        source="docs/PROJECT_STATE.md",
        source_text="0.565 against 1.071 per thousand player-days",
    ),
    Claim(
        id="interface-c3-explanation-alert-rate",
        claim="Dashboard C3 explanation cites the realised 4.737% held-out alert rate",
        location="src/player_availability/api/app.py",
        location_text="realised a 4.737% alert rate",
        source="outputs/modelling/v1_p5_final_test/tables/operating_point_results.csv",
        source_text="4.737139626907857",
    ),
)


def resolve(path_str: str) -> Path:
    return repo_root() / path_str
