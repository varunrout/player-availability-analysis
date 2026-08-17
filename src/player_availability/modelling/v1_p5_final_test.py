"""V1-P5 final-test governance gate: the single-use confirmatory evaluation (`DEC-062`).

This is not an experiment; it is a governance gate, and it carries no `EXP-` identifier.
It evaluates the frozen V1 champion, F1 refit once on the full development partition
(train plus validation) reporting raw probabilities, against the final-test partition
that has been locked since `DEC-036` and read only for support counts until now.

Sequencing is the entire point and is enforced by construction:

1. The model is fit on development data only.
2. Operating-point probability thresholds for the `DEC-061` 2.5% and 5% rates are
   derived from that same fitted model's own predictions on development data
   (in-sample, the resolution the project owner selected when this ambiguity was
   raised before any final-test code was written) and are frozen at that point.
3. Only then is the final-test partition read, exactly once, and scored against the
   already-frozen model and already-frozen thresholds.

No fitting, tuning, feature selection or threshold adjustment occurs after step 3.
The claims C1-C3 and the power statement were registered in `DEC-062` before this
module existed; this module measures them and nothing else.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.metrics import (
    calibration_diagnostics,
    classification_metrics,
    reliability_table,
    threshold_alert_and_event_tables,
)
from player_availability.modelling.preprocessing import F1_FEATURES, build_feature_pipeline

PREREGISTRATION_COMMIT = "650f67e1883b655124324219c20cca09f19c3eba"
SELECTED_REGULARISATION_C = 0.001
OPERATING_POINT_RATES: tuple[float, ...] = (0.025, 0.05)
PRIMARY_GAP_DAYS = 3
KEYS = ("player_id", "team_id", "prediction_date")
MODEL_ID = "M1-F1-FINAL"

DEVELOPMENT_MEAN_PREDICTION_MULTIPLE = 3.7
"""Reference overprediction multiple observed in development, cited by claim C2."""

C3_LOWER_BOUND = 10.0
C3_UPPER_BOUND = 100.0
"""C3 reads "tens of false alerts per captured onset": the [10, 100) order of magnitude."""


@dataclass(frozen=True, slots=True)
class V1P5FinalTestConfig:
    """Frozen V1-P5 final-test governance configuration."""

    data_version: str
    target: str
    primary_horizon_days: int
    max_iterations: int
    reliability_bins: int
    preregistration_commit: str


@dataclass(frozen=True, slots=True)
class V1P5FinalTestResult:
    """Final-test tables and metadata. Exists once the final-test partition has been read."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_v1_p5_config(path: Path) -> V1P5FinalTestConfig:
    """Load and validate the frozen V1-P5 final-test configuration."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("V1-P5 configuration must be a mapping")
    config = V1P5FinalTestConfig(
        data_version=str(raw["data_version"]),
        target=str(raw["target"]),
        primary_horizon_days=int(raw["primary_horizon_days"]),
        max_iterations=int(raw["max_iterations"]),
        reliability_bins=int(raw["reliability_bins"]),
        preregistration_commit=str(raw["preregistration_commit"]),
    )
    if config.target != "injury_next_7d" or config.primary_horizon_days != 7:
        raise ValueError("V1-P5 evaluates the frozen 7-day horizon only (DEC-062)")
    if config.preregistration_commit != PREREGISTRATION_COMMIT:
        raise ValueError(
            "V1-P5 configuration does not match the registered DEC-062 pre-registration commit"
        )
    return config


def load_v1_p5_from_gcp(
    *, project_id: str, data_bucket: str, config: V1P5FinalTestConfig
) -> V1P5FinalTestResult:
    """Load compact canonical products once and execute the single-use final-test evaluation.

    This is the one call in the codebase that reads the final-test partition for
    performance evaluation. It must be invoked exactly once, per `DEC-062`.
    """
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_v1_p5_final_test(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    return V1P5FinalTestResult(
        tables=result.tables,
        summary=result.summary,
        source_metadata={
            "source_paths": paths,
            "source_sha256": {
                name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()
            },
        },
    )


def run_v1_p5_final_test(
    *, features: pl.DataFrame, episodes: pl.DataFrame, config: V1P5FinalTestConfig
) -> V1P5FinalTestResult:
    """Fit once on development, freeze thresholds, then read the final test exactly once."""
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    cohort = protocol.tables["_primary_cohort"]

    development = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
        | pl.col("prediction_date").is_between(
            PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"]
        )
    )
    test = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[2]["start_date"], PARTITIONS[2]["end_date"])
    )
    embargo_register = _embargo_register(cohort)

    # Step 1: fit once on development only (FINAL-03).
    development_targets = _targets(development, config.target)
    pipeline = build_feature_pipeline(
        regularisation_c=SELECTED_REGULARISATION_C, max_iterations=config.max_iterations
    )
    pipeline.fit(_matrix(development), development_targets)

    # Step 2: freeze operating-point thresholds from this model's own development
    # predictions, before the final test is read (FINAL-04).
    development_probabilities = _positive_probabilities(pipeline, development)
    development_series = pl.Series("predicted_probability", development_probabilities)
    thresholds = {
        rate: cast(float, development_series.quantile(1.0 - rate, "linear"))
        for rate in OPERATING_POINT_RATES
    }
    thresholds_frozen_at_utc = datetime.now(UTC).isoformat()

    # Step 3: read the final-test partition exactly once (FINAL-01). Nothing above
    # this line has touched `test`; nothing below refits, tunes or reselects.
    final_test_read_at_utc = datetime.now(UTC).isoformat()
    test_targets = _targets(test, config.target)
    test_probabilities = _positive_probabilities(pipeline, test)

    metrics = classification_metrics(test_targets, test_probabilities)
    calibration = calibration_diagnostics(test_targets, test_probabilities)
    test_predictions = test.select(*KEYS, pl.col(config.target).alias(config.target)).with_columns(
        pl.Series("predicted_probability", test_probabilities)
    )
    reliability = reliability_table(
        test_predictions, target=config.target, bins=config.reliability_bins
    )
    operating_points, event_detail = threshold_alert_and_event_tables(
        predictions=test_predictions,
        episodes=episodes,
        target=config.target,
        horizon_days=config.primary_horizon_days,
        thresholds=thresholds,
        model_id=MODEL_ID,
    )

    claims = _claims(metrics=metrics, calibration=calibration, operating_points=operating_points)
    findings = _final_test_findings(
        development=development,
        test=test,
        embargo_register=embargo_register,
        operating_points=operating_points,
        metrics=metrics,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    represented_onsets = (
        event_detail.select("onset_id").unique().height if event_detail.height else 0
    )
    summary = {
        "governance_gate": "V1-P5",
        "model_id": MODEL_ID,
        "preregistration_commit": config.preregistration_commit,
        "status": "PASS" if failures == 0 else "FAIL",
        "final_test_rows_evaluated": test.height,
        "final_test_predictions_created": True,
        "final_test_performance_accessed": True,
        "final_test_positive_days": sum(test_targets),
        "final_test_represented_onsets": represented_onsets,
        "development_player_days": development.height,
        "development_positive_days": sum(development_targets),
        "thresholds_frozen_at_utc": thresholds_frozen_at_utc,
        "final_test_read_at_utc": final_test_read_at_utc,
        "operating_point_thresholds": {f"{rate:g}": value for rate, value in thresholds.items()},
        "c1_ranking_above_chance": bool(claims.filter(pl.col("claim_id") == "C1")["supported"][0]),
        "c2_overprediction_in_the_large": bool(
            claims.filter(pl.col("claim_id") == "C2")["supported"][0]
        ),
        "c3_high_false_alert_burden": bool(
            claims.filter(pl.col("claim_id") == "C3")["supported"][0]
        ),
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config, development, test),
        "embargo_register": embargo_register,
        "development_thresholds": pl.DataFrame(
            [
                {"review_rate": rate, "probability_threshold": threshold}
                for rate, threshold in thresholds.items()
            ]
        ),
        "final_test_metrics": pl.DataFrame(
            [
                {
                    "model_id": MODEL_ID,
                    "player_days": test.height,
                    "positive_days": sum(test_targets),
                    **metrics,
                    "calibration_intercept": calibration["calibration_intercept"],
                    "calibration_slope": calibration["calibration_slope"],
                    "mean_prediction": calibration["mean_prediction"],
                    "observed_rate": calibration["observed_rate"],
                }
            ]
        ),
        "reliability_bins": reliability,
        "operating_point_results": operating_points,
        "event_capture_detail": event_detail,
        "claims": claims,
        "final_test_findings": findings,
    }
    return V1P5FinalTestResult(tables=tables, summary=summary, source_metadata={})


def _embargo_register(cohort: pl.DataFrame) -> pl.DataFrame:
    gaps = (
        ("train_to_validation", PARTITIONS[0]["end_date"], PARTITIONS[1]["start_date"]),
        ("validation_to_test", PARTITIONS[1]["end_date"], PARTITIONS[2]["start_date"]),
    )
    rows = []
    for name, before_end, after_start in gaps:
        gap = cohort.filter(
            (pl.col("prediction_date") > before_end) & (pl.col("prediction_date") < after_start)
        )
        rows.append(
            {
                "embargo_gap": name,
                "excluded_from": before_end,
                "excluded_to": after_start,
                "player_days_excluded": gap.height,
            }
        )
    return pl.DataFrame(rows)


def _claims(
    *,
    metrics: dict[str, float | None],
    calibration: dict[str, float | None],
    operating_points: pl.DataFrame,
) -> pl.DataFrame:
    roc_auc = metrics["roc_auc"]
    c1_supported = roc_auc is not None and roc_auc > 0.5
    mean_prediction = calibration["mean_prediction"]
    observed_rate = calibration["observed_rate"]
    c2_supported = (
        mean_prediction is not None
        and observed_rate is not None
        and mean_prediction > observed_rate
    )
    default_row = operating_points.filter(pl.col("review_rate") == 0.025)
    burden = default_row["false_alerts_per_captured_onset"][0] if default_row.height else None
    c3_supported = burden is not None and C3_LOWER_BOUND <= burden < C3_UPPER_BOUND
    return pl.DataFrame(
        [
            {
                "claim_id": "C1",
                "statement": (
                    "Ranking on unseen future data is better than chance (ROC-AUC above 0.5)"
                ),
                "supported": c1_supported,
                "evidence": f"ROC-AUC={_format(roc_auc)}",
            },
            {
                "claim_id": "C2",
                "statement": (
                    "The champion overpredicts risk in the large "
                    f"(development finding: roughly {DEVELOPMENT_MEAN_PREDICTION_MULTIPLE:g}x)"
                ),
                "supported": c2_supported,
                "evidence": (
                    f"mean prediction={_format(mean_prediction)} vs "
                    f"observed rate={_format(observed_rate)}"
                    + (
                        f" ({mean_prediction / observed_rate:.1f}x)"
                        if mean_prediction and observed_rate
                        else ""
                    )
                ),
            },
            {
                "claim_id": "C3",
                "statement": (
                    "At the 2.5% operating point the false-alert burden is high and of the "
                    "development order (tens of false alerts per captured onset)"
                ),
                "supported": c3_supported,
                "evidence": f"false alerts per captured onset at 2.5%={_format(burden)}",
            },
        ]
    )


def _final_test_findings(
    *,
    development: pl.DataFrame,
    test: pl.DataFrame,
    embargo_register: pl.DataFrame,
    operating_points: pl.DataFrame,
    metrics: dict[str, float | None],
) -> pl.DataFrame:
    event_count_reported = {
        "represented_onsets",
        "captured_onsets",
        "eligible_player_days",
    }.issubset(operating_points.columns)
    return pl.DataFrame(
        [
            {
                "finding_id": "FINAL-01",
                "status": "PASS",
                "domain": "single_read",
                "evidence": (
                    "final-test partition is read exactly once in this function, logged with "
                    "a timestamp"
                ),
            },
            {
                "finding_id": "FINAL-02",
                "status": "PASS"
                if development.columns and set(F1_FEATURES).issubset(development.columns)
                else "FAIL",
                "domain": "predictor_contract",
                "evidence": (
                    f"evaluated model uses exactly the {len(F1_FEATURES)} named F1 predictors"
                ),
            },
            {
                "finding_id": "FINAL-03",
                "status": "PASS",
                "domain": "preprocessing_scope",
                "evidence": "imputer and scaler are fitted on the development partition only",
            },
            {
                "finding_id": "FINAL-04",
                "status": "PASS",
                "domain": "threshold_freezing",
                "evidence": (
                    "operating-point thresholds are computed from the fitted model's own "
                    "development-partition predictions and recorded before the final-test read"
                ),
            },
            {
                "finding_id": "FINAL-05",
                "status": "PASS" if embargo_register.height == 2 else "FAIL",
                "domain": "embargo_exclusion",
                "evidence": (
                    f"{int(embargo_register['player_days_excluded'].sum())} embargoed player-days "
                    "excluded across two gaps"
                ),
            },
            {
                "finding_id": "FINAL-06",
                "status": "PASS" if event_count_reported else "FAIL",
                "domain": "event_count_reporting",
                "evidence": (
                    "every operating point carries its represented-onset and player-day counts"
                ),
            },
            {
                "finding_id": "FINAL-07",
                "status": "PASS",
                "domain": "no_post_read_adjustment",
                "evidence": (
                    "no fitting, tuning, selection or threshold-adjustment function is called "
                    "after the logged final-test read timestamp"
                ),
            },
        ]
    )


def _dataset_manifest(
    config: V1P5FinalTestConfig, development: pl.DataFrame, test: pl.DataFrame
) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "governance_gate": "V1-P5",
                "model_id": MODEL_ID,
                "data_version": config.data_version,
                "target": config.target,
                "horizon_days": config.primary_horizon_days,
                "episode_gap_days": PRIMARY_GAP_DAYS,
                "selected_regularisation_c": SELECTED_REGULARISATION_C,
                "development_player_days": development.height,
                "final_test_player_days": test.height,
                "preregistration_commit": config.preregistration_commit,
            }
        ]
    )


def _targets(frame: pl.DataFrame, target: str) -> list[int]:
    return [int(value) for value in frame[target]]


def _matrix(frame: pl.DataFrame) -> Any:
    return frame.select(F1_FEATURES).to_numpy()


def _positive_probabilities(pipeline: Any, frame: pl.DataFrame) -> list[float]:
    values = pipeline.predict_proba(_matrix(frame))[:, 1]
    return [float(value) for value in values]


def build_v1_p5_figures(result: V1P5FinalTestResult) -> dict[str, Figure]:
    """Build retained final-test governance figures."""
    reliability = result.tables["reliability_bins"]
    operating_points = result.tables["operating_point_results"]
    figures: dict[str, Figure] = {}

    fig, axis = plt.subplots(figsize=(7, 5))
    upper = max(
        0.02,
        cast(float, reliability["mean_prediction"].max()) * 1.1,
        cast(float, reliability["observed_rate"].max()) * 1.1,
    )
    axis.plot(
        reliability["mean_prediction"], reliability["observed_rate"], marker="o", color="#4C78A8"
    )
    axis.plot([0, upper], [0, upper], linestyle="--", color="#666666")
    axis.set(
        title="Final-test reliability (single confirmatory read)",
        xlabel="Mean predicted probability",
        ylabel="Observed positive-day rate",
        xlim=(0, upper),
        ylim=(0, upper),
    )
    figures["final_test_reliability"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.bar(
        [f"{value:.1%}" for value in operating_points["review_rate"]],
        operating_points["false_alerts_per_captured_onset"].fill_null(0.0),
        color="#E45756",
    )
    axis.set(
        title="Final-test false-alert burden by operating point",
        xlabel="Review rate",
        ylabel="False alerts per captured onset",
    )
    figures["final_test_false_alert_burden"] = fig
    return figures


def write_v1_p5_outputs(result: V1P5FinalTestResult, output_root: Path) -> None:
    """Persist the single-use V1-P5 final-test governance evidence."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_v1_p5_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "v1_p5_final_test_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "V1_P5_FINAL_TEST_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: V1P5FinalTestResult) -> str:
    summary = result.summary
    metrics = result.tables["final_test_metrics"].row(0, named=True)
    operating_points = result.tables["operating_point_results"]
    claims = result.tables["claims"]
    findings = result.tables["final_test_findings"]
    embargo = result.tables["embargo_register"]
    lines = [
        "# V1-P5 - Final-Test Governance Gate Report",
        "",
        f"Pre-registration commit: `{summary['preregistration_commit']}` (`DEC-062`).",
        "",
        "## Automated Status",
        "",
        f"**{summary['status']}**. This evaluation was executed exactly once. Thresholds were "
        f"frozen at {summary['thresholds_frozen_at_utc']}; the final-test partition was read at "
        f"{summary['final_test_read_at_utc']}.",
        "",
        "## Power Statement (registered in advance, verbatim)",
        "",
        (
            "> The final-test partition contains five represented onsets. This evaluation has "
            "almost no inferential power. A single onset falling either side of a threshold can "
            "halve or double average precision, and no interval computable on this partition "
            "will be narrow enough to support a comparison against any other model or operating "
            "point. This is a confirmatory sanity check that the champion behaves on unseen "
            "future data as it behaved in development. It is not a performance claim and must "
            "never be cited as one."
        ),
        "",
        (
            f"Observed support: {summary['final_test_rows_evaluated']} player-days, "
            f"{summary['final_test_positive_days']} positive days, "
            f"{summary['final_test_represented_onsets']} represented onsets."
        ),
        "",
        "## Registered Claims",
        "",
        "| Claim | Statement | Supported | Evidence |",
        "|---|---|---|---|",
    ]
    for row in claims.iter_rows(named=True):
        lines.append(
            f"| {row['claim_id']} | {row['statement']} | "
            f"{'YES' if row['supported'] else 'NO'} | {row['evidence']} |"
        )
    player_days_support = f"{metrics['player_days']} days"
    positive_days_support = f"{metrics['positive_days']} positive days"
    metric_rows = (
        ("Brier score", metrics["brier_score"], player_days_support),
        ("Log loss", metrics["log_loss"], player_days_support),
        ("Calibration intercept", metrics["calibration_intercept"], player_days_support),
        ("Calibration slope", metrics["calibration_slope"], player_days_support),
        ("Mean prediction", metrics["mean_prediction"], player_days_support),
        ("Observed rate", metrics["observed_rate"], positive_days_support),
        ("Average precision", metrics["average_precision"], positive_days_support),
        ("ROC-AUC", metrics["roc_auc"], positive_days_support),
    )
    lines.extend(
        [
            "",
            "## Final-Test Metrics",
            "",
            "| Metric | Value | Support |",
            "|---|---:|---:|",
        ]
    )
    for label, value, support in metric_rows:
        lines.append(f"| {label} | {_format(value)} | {support} |")
    lines.extend(
        [
            "",
            "## Operating Points",
            "",
            "| Rate | Threshold | Alerts | Alerts/100 days | Precision | Onsets | Captured "
            "| Recall | False/captured |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in operating_points.iter_rows(named=True):
        lines.append(
            f"| {row['review_rate']:.3%} | {_format(row['probability_threshold'])} | "
            f"{row['alert_count']} | {_format(row['alerts_per_100_player_days'])} | "
            f"{_format(row['precision'])} | {row['represented_onsets']} | "
            f"{row['captured_onsets']} | {_format(row['recall'])} | "
            f"{_format(row['false_alerts_per_captured_onset'])} |"
        )
    lines.extend(
        [
            "",
            "## Embargo Exclusion",
            "",
            "| Gap | Excluded from | Excluded to | Player-days excluded |",
            "|---|---|---|---:|",
        ]
    )
    for row in embargo.iter_rows(named=True):
        lines.append(
            f"| {row['embargo_gap']} | {row['excluded_from']} | {row['excluded_to']} | "
            f"{row['player_days_excluded']} |"
        )
    lines.extend(
        ["", "## Findings", "", "| ID | Status | Domain | Evidence |", "|---|---|---|---|"]
    )
    for row in findings.iter_rows(named=True):
        lines.append(
            f"| {row['finding_id']} | {row['status']} | {row['domain']} | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            (
                "This result is a confirmatory sanity check, not a performance claim. It may not "
                "be cited in the model card, README, case study, portfolio material or any "
                "interview narrative as a performance figure; it is cited with its five-onset "
                "support stated inline. No result changes the champion, the operating points, "
                "the predictor contract or any prior decision."
            ),
            "",
            "## Gate",
            "",
            (
                "This partition is now spent. A second access requires a superseding decision "
                "recorded before it occurs."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"
