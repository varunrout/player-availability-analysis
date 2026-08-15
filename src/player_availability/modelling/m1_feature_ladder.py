"""EXP-003 cumulative M1-F1/F2/F3 development comparison."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import joblib  # type: ignore[import-untyped]
import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import (
    M1F1Config,
    M1F1Result,
    load_m1_f1_config,
    run_m1_feature_set,
)
from player_availability.modelling.preprocessing import (
    F1_FEATURES,
    F2_ADDITIONAL_FEATURES,
    F3_ADDITIONAL_FEATURES,
    FEATURE_SETS,
)
from player_availability.modelling.uncertainty import (
    paired_prediction_bootstrap_differences,
)


@dataclass(frozen=True, slots=True)
class M1FeatureLadderConfig:
    """Frozen cumulative feature-ladder configuration."""

    base_config: M1F1Config
    feature_sets: tuple[str, ...]
    include_f1_reference: bool
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class M1FeatureLadderResult:
    """Consolidated feature-ladder evidence and fitted development models."""

    model_results: dict[str, M1F1Result]
    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_m1_feature_ladder_config(path: Path) -> M1FeatureLadderConfig:
    """Load and validate the DEC-042 feature-ladder extension."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("M1 feature-ladder configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = M1FeatureLadderConfig(
        base_config=base_config,
        feature_sets=tuple(str(value) for value in raw["feature_sets"]),
        include_f1_reference=bool(raw["include_f1_reference"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.feature_sets != ("F2", "F3") or not config.include_f1_reference:
        raise ValueError("DEC-042 requires cumulative F1/F2/F3 comparison")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("Calibration selection and final-test access remain locked")
    return config


def load_m1_feature_ladder_from_gcp(
    *, project_id: str, data_bucket: str, config: M1FeatureLadderConfig
) -> M1FeatureLadderResult:
    """Load compact canonical products once and execute the feature ladder."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_m1_feature_ladder(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    return M1FeatureLadderResult(
        model_results=result.model_results,
        tables=result.tables,
        summary=result.summary,
        source_metadata={
            "source_paths": paths,
            "source_sha256": {
                name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()
            },
        },
    )


def run_m1_feature_ladder(
    *, features: pl.DataFrame, episodes: pl.DataFrame, config: M1FeatureLadderConfig
) -> M1FeatureLadderResult:
    """Fit F1, F2 and F3 independently on the frozen development protocol."""
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    cohort = protocol.tables["_primary_cohort"]
    feature_sets = ("F1", *config.feature_sets)
    results: dict[str, M1F1Result] = {}
    for feature_set in feature_sets:
        model_config = replace(
            config.base_config,
            model_id=f"M1-{feature_set}",
            feature_set=feature_set,
        )
        results[feature_set] = run_m1_feature_set(
            features=features,
            episodes=episodes,
            config=model_config,
            feature_names=FEATURE_SETS[feature_set],
            prepared_cohort=cohort,
        )

    comparison = _comparison_table(results)
    alerts = _stack_table(results, "alert_budget_results")
    rolling = _stack_table(results, "rolling_origin_results")
    unseen = _stack_table(results, "unseen_player_aggregate_metrics")
    uncertainty = _stack_table(results, "bootstrap_intervals")
    paired_uncertainty = pl.concat(
        [
            paired_prediction_bootstrap_differences(
                reference_predictions=results[reference].predictions,
                candidate_predictions=results[candidate].predictions,
                target=config.base_config.target,
                iterations=config.base_config.bootstrap_iterations,
                random_seed=config.base_config.random_seed,
                reference_model_id=f"M1-{reference}",
                candidate_model_id=f"M1-{candidate}",
            ).with_columns(
                pl.lit(reference).alias("reference_feature_set"),
                pl.lit(candidate).alias("candidate_feature_set"),
            )
            for reference, candidate in (("F1", "F2"), ("F2", "F3"))
        ]
    )
    availability = _feature_availability(cohort)
    incremental = _incremental_changes(comparison, alerts)
    findings = _ladder_findings(results, comparison, availability)
    failures = findings.filter(pl.col("status") == "FAIL").height
    summary = {
        "experiment_id": config.base_config.experiment_id,
        "model_ids": [f"M1-{feature_set}" for feature_set in feature_sets],
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "OWNER_RAW_CANDIDATE_AND_CALIBRATION_SCOPE_REVIEW",
        "feature_counts": {
            feature_set: len(FEATURE_SETS[feature_set]) for feature_set in feature_sets
        },
        "posthoc_calibration_selected": False,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    return M1FeatureLadderResult(
        model_results=results,
        tables={
            "feature_set_comparison": comparison,
            "alert_budget_comparison": alerts,
            "rolling_origin_comparison": rolling,
            "unseen_player_comparison": unseen,
            "bootstrap_interval_comparison": uncertainty,
            "paired_bootstrap_differences": paired_uncertainty,
            "feature_availability": availability,
            "incremental_metric_changes": incremental,
            "ladder_findings": findings,
        },
        summary=summary,
        source_metadata={},
    )


def write_m1_feature_ladder_outputs(result: M1FeatureLadderResult, output_root: Path) -> None:
    """Persist consolidated and per-feature-set development evidence."""
    directories = {
        name: output_root / name
        for name in ("figures", "tables", "predictions", "models", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    for feature_set, model_result in result.model_results.items():
        table_root = directories["tables"] / feature_set.lower()
        table_root.mkdir(parents=True, exist_ok=True)
        for name, table in model_result.tables.items():
            table.write_csv(table_root / f"{name}.csv")
        model_result.predictions.write_parquet(
            directories["predictions"] / f"{feature_set.lower()}_validation_predictions.parquet"
        )
        joblib.dump(
            model_result.model,
            directories["models"] / f"m1_{feature_set.lower()}_development_pipeline.joblib",
        )
    for name, figure in build_m1_feature_ladder_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {
        "summary": result.summary,
        **result.source_metadata,
        "model_parameters": {
            feature_set: model_result.parameters
            for feature_set, model_result in result.model_results.items()
        },
    }
    (directories["metadata"] / "exp_003_feature_ladder_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_003_M1_FEATURE_LADDER_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _comparison_table(results: dict[str, M1F1Result]) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for feature_set, result in results.items():
        metrics = result.tables["selected_validation_metrics"].row(0, named=True)
        calibration = result.tables["calibration_diagnostics"].row(0, named=True)
        rows.append(
            {
                "feature_set": feature_set,
                "model_id": result.summary["model_id"],
                "feature_count": result.summary["feature_count"],
                "selected_regularisation_c": result.summary["selected_regularisation_c"],
                "player_days": metrics["player_days"],
                "positive_days": metrics["positive_days"],
                "prevalence": metrics["prevalence"],
                "brier_score": metrics["brier_score"],
                "log_loss": metrics["log_loss"],
                "average_precision": metrics["average_precision"],
                "roc_auc": metrics["roc_auc"],
                "mean_prediction": calibration["mean_prediction"],
                "mean_calibration_error": calibration["mean_calibration_error"],
                "calibration_intercept": calibration["calibration_intercept"],
                "calibration_slope": calibration["calibration_slope"],
            }
        )
    return pl.DataFrame(rows)


def _stack_table(results: dict[str, M1F1Result], table_name: str) -> pl.DataFrame:
    return pl.concat(
        [
            result.tables[table_name].with_columns(pl.lit(feature_set).alias("feature_set"))
            for feature_set, result in results.items()
        ],
        how="diagonal_relaxed",
    )


def _feature_availability(cohort: pl.DataFrame) -> pl.DataFrame:
    rows = []
    introduced_features = {
        "F1": F1_FEATURES,
        "F2": F2_ADDITIONAL_FEATURES,
        "F3": F3_ADDITIONAL_FEATURES,
    }
    for feature_set, feature_names in introduced_features.items():
        for feature in feature_names:
            observed = cohort[feature].is_not_null().sum()
            rows.append(
                {
                    "feature_set": feature_set,
                    "predictor": feature,
                    "observed_player_days": observed,
                    "missing_player_days": cohort.height - observed,
                    "coverage_rate": observed / cohort.height,
                }
            )
    return pl.DataFrame(rows)


def _incremental_changes(comparison: pl.DataFrame, alerts: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for reference, candidate in (("F1", "F2"), ("F2", "F3")):
        before = comparison.filter(pl.col("feature_set") == reference).row(0, named=True)
        after = comparison.filter(pl.col("feature_set") == candidate).row(0, named=True)
        for metric in (
            "brier_score",
            "log_loss",
            "average_precision",
            "roc_auc",
            "mean_calibration_error",
        ):
            rows.append(
                {
                    "reference_feature_set": reference,
                    "candidate_feature_set": candidate,
                    "metric": metric,
                    "reference_value": before[metric],
                    "candidate_value": after[metric],
                    "candidate_minus_reference": after[metric] - before[metric],
                }
            )
        for rate in (0.01, 0.025, 0.05):
            before_alert = alerts.filter(
                (pl.col("feature_set") == reference) & (pl.col("review_rate") == rate)
            ).row(0, named=True)
            after_alert = alerts.filter(
                (pl.col("feature_set") == candidate) & (pl.col("review_rate") == rate)
            ).row(0, named=True)
            rows.append(
                {
                    "reference_feature_set": reference,
                    "candidate_feature_set": candidate,
                    "metric": f"captured_onsets_at_{rate:.3f}",
                    "reference_value": float(before_alert["captured_onsets"]),
                    "candidate_value": float(after_alert["captured_onsets"]),
                    "candidate_minus_reference": float(
                        after_alert["captured_onsets"] - before_alert["captured_onsets"]
                    ),
                }
            )
    return pl.DataFrame(rows)


def _ladder_findings(
    results: dict[str, M1F1Result], comparison: pl.DataFrame, availability: pl.DataFrame
) -> pl.DataFrame:
    child_failures = sum(
        result.tables["model_findings"].filter(pl.col("status") == "FAIL").height
        for result in results.values()
    )
    expected_counts = {"F1": 9, "F2": 17, "F3": 23}
    counts_match = all(
        result.summary["feature_count"] == expected_counts[feature_set]
        for feature_set, result in results.items()
    )
    final_test_isolated = all(
        result.summary["final_test_rows_evaluated"] == 0
        and not result.summary["final_test_predictions_created"]
        for result in results.values()
    )
    low_coverage = availability.filter(pl.col("coverage_rate") < 0.2).height
    best_brier = comparison.sort("brier_score").row(0, named=True)
    best_ap = comparison.sort("average_precision", descending=True).row(0, named=True)
    return pl.DataFrame(
        [
            {
                "finding_id": "LADDER-01",
                "status": "PASS" if child_failures == 0 else "FAIL",
                "domain": "model_integrity",
                "evidence": f"child model failure findings: {child_failures}",
            },
            {
                "finding_id": "LADDER-02",
                "status": "PASS" if counts_match else "FAIL",
                "domain": "predictor_contract",
                "evidence": "frozen cumulative counts expected F1=9, F2=17, F3=23",
            },
            {
                "finding_id": "LADDER-03",
                "status": "PASS" if final_test_isolated else "FAIL",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance across all feature sets",
            },
            {
                "finding_id": "LADDER-04",
                "status": "REVIEW",
                "domain": "raw_feature_set_selection",
                "evidence": (
                    f"lowest Brier={best_brier['feature_set']}; highest AP={best_ap['feature_set']}"
                ),
            },
            {
                "finding_id": "LADDER-05",
                "status": "REVIEW" if low_coverage else "PASS",
                "domain": "predictor_availability",
                "evidence": f"predictors below 20% observed coverage: {low_coverage}",
            },
            {
                "finding_id": "LADDER-06",
                "status": "REVIEW",
                "domain": "calibration_scope",
                "evidence": "raw comparison only; no post-hoc calibrator fitted or selected",
            },
        ]
    )


def build_m1_feature_ladder_figures(
    result: M1FeatureLadderResult,
) -> dict[str, Figure]:
    """Build consolidated feature-ladder development figures."""
    comparison = result.tables["feature_set_comparison"]
    alerts = result.tables["alert_budget_comparison"]
    availability = result.tables["feature_availability"]
    rolling = result.tables["rolling_origin_comparison"]
    figures: dict[str, Figure] = {}

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(comparison["feature_set"], comparison["brier_score"], color="#4C78A8")
    axes[0].set(title="Raw probability accuracy", ylabel="Brier score")
    axes[1].bar(comparison["feature_set"], comparison["log_loss"], color="#72B7B2")
    axes[1].set(title="Raw probability loss", ylabel="Log loss")
    figures["probability_accuracy_comparison"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(comparison["feature_set"], comparison["average_precision"], color="#F58518")
    axes[0].set(title="Rare-event ranking", ylabel="Average precision")
    axes[1].bar(comparison["feature_set"], comparison["roc_auc"], color="#E45756")
    axes[1].set(title="Pairwise ranking", ylabel="ROC-AUC", ylim=(0.5, 1.0))
    figures["ranking_comparison"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    width = 0.35
    positions = list(range(comparison.height))
    axis.bar(
        [value - width / 2 for value in positions],
        comparison["mean_prediction"],
        width,
        label="Mean prediction",
        color="#4C78A8",
    )
    axis.bar(
        [value + width / 2 for value in positions],
        comparison["prevalence"],
        width,
        label="Observed rate",
        color="#59A14F",
    )
    axis.set_xticks(positions, comparison["feature_set"])
    axis.set(title="Raw calibration in the large", ylabel="Probability")
    axis.legend()
    figures["calibration_in_the_large"] = fig

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True, sharey=True)
    upper = 0.0
    for axis, feature_set in zip(axes, ("F1", "F2", "F3"), strict=True):
        table = result.model_results[feature_set].tables["reliability_bins"]
        upper = max(
            upper,
            cast(float, table["mean_prediction"].max()),
            cast(float, table["observed_rate"].max()),
        )
        axis.plot(table["mean_prediction"], table["observed_rate"], marker="o")
        axis.set_title(feature_set)
        axis.set_xlabel("Mean prediction")
    upper = max(0.02, upper * 1.1)
    for axis in axes:
        axis.plot([0, upper], [0, upper], linestyle="--", color="#666666")
        axis.set_xlim(0, upper)
        axis.set_ylim(0, upper)
    axes[0].set_ylabel("Observed positive-day rate")
    fig.suptitle("Raw reliability by feature set")
    figures["raw_reliability_comparison"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for feature_set in ("F1", "F2", "F3"):
        table = alerts.filter(pl.col("feature_set") == feature_set)
        axis.plot(
            table["alerts_per_100_player_days"],
            table["event_capture_rate"],
            marker="o",
            label=feature_set,
        )
    axis.set(
        title="Review capacity and onset capture",
        xlabel="Alerts per 100 player-days",
        ylabel="Represented-onset capture rate",
        ylim=(0, 1),
    )
    axis.legend()
    figures["alert_capture_comparison"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for feature_set in ("F1", "F2", "F3"):
        table = alerts.filter(pl.col("feature_set") == feature_set).filter(
            pl.col("false_alerts_per_captured_onset").is_not_null()
        )
        axis.plot(
            table["alerts_per_100_player_days"],
            table["false_alerts_per_captured_onset"],
            marker="o",
            label=feature_set,
        )
    axis.set(
        title="False-alert burden where capture occurs",
        xlabel="Alerts per 100 player-days",
        ylabel="False alerts per captured onset",
    )
    axis.legend()
    figures["false_alert_burden_comparison"] = fig

    fig, axis = plt.subplots(figsize=(10, 6.5))
    added = availability.filter(pl.col("feature_set").is_in(["F2", "F3"]))
    axis.barh(added["predictor"], added["coverage_rate"], color="#287271")
    axis.axvline(0.2, linestyle="--", color="#E45756")
    axis.set(title="F2/F3 predictor availability", xlabel="Observed coverage", xlim=(0, 1))
    figures["added_predictor_availability"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    estimable = rolling.filter(pl.col("average_precision").is_not_null())
    for feature_set in ("F1", "F2", "F3"):
        table = estimable.filter(pl.col("feature_set") == feature_set)
        axis.plot(table["fold_id"], table["average_precision"], marker="o", label=feature_set)
    axis.set(title="Rolling-origin ranking", xlabel="Fold", ylabel="Average precision")
    axis.legend()
    figures["rolling_origin_ranking_comparison"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].plot(
        comparison["feature_count"], comparison["brier_score"], marker="o", color="#4C78A8"
    )
    axes[0].set(title="Complexity and Brier", xlabel="Predictors", ylabel="Brier score")
    axes[1].plot(
        comparison["feature_count"],
        comparison["average_precision"],
        marker="o",
        color="#F58518",
    )
    axes[1].set(title="Complexity and ranking", xlabel="Predictors", ylabel="Average precision")
    figures["complexity_tradeoff"] = fig
    return figures


def _render_report(result: M1FeatureLadderResult) -> str:
    comparison = result.tables["feature_set_comparison"]
    alerts = result.tables["alert_budget_comparison"]
    rolling = result.tables["rolling_origin_comparison"]
    unseen = result.tables["unseen_player_comparison"]
    paired = result.tables["paired_bootstrap_differences"]
    findings = result.tables["ladder_findings"]
    lines = [
        "# EXP-003 - M1 Feature-Ladder Development Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{result.summary['status']} WITH REVIEW**.",
        "",
        (
            "F1 is the promoted development reference. No post-hoc calibrator or "
            "final-test prediction/performance was created."
        ),
        "",
        "## Raw Validation Comparison",
        "",
        "| Feature set | Predictors | C | Brier | Log loss | AP | ROC-AUC | Mean prediction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in comparison.iter_rows(named=True):
        lines.append(
            f"| {row['feature_set']} | {row['feature_count']} | "
            f"{row['selected_regularisation_c']:.3g} | {row['brier_score']:.6f} | "
            f"{row['log_loss']:.6f} | {row['average_precision']:.6f} | "
            f"{row['roc_auc']:.6f} | {row['mean_prediction']:.6f} |"
        )
    lines.extend(
        [
            "",
            "Observed validation positive-day rate is 0.003222 for every feature set.",
            "",
            "## Alert-Budget Comparison",
            "",
            (
                "| Feature set | Review rate | Alerts | Captured onsets | Capture rate | "
                "False alerts/capture |"
            ),
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in alerts.iter_rows(named=True):
        burden = (
            "NA"
            if row["false_alerts_per_captured_onset"] is None
            else f"{row['false_alerts_per_captured_onset']:.2f}"
        )
        lines.append(
            f"| {row['feature_set']} | {row['review_rate']:.3f} | {row['alert_count']} | "
            f"{row['captured_onsets']}/{row['represented_onsets']} | "
            f"{row['event_capture_rate']:.3f} | {burden} |"
        )
    lines.extend(
        [
            "",
            "## Development Stress Evidence",
            "",
            "| Feature set | Unseen-player AP | Unseen-player ROC-AUC | Estimable players |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in unseen.iter_rows(named=True):
        lines.append(
            f"| {row['feature_set']} | {row['average_precision']:.6f} | "
            f"{row['roc_auc']:.6f} | {row['estimable_player_count']}/"
            f"{row['heldout_player_count']} |"
        )
    lines.extend(
        [
            "",
            "Rolling-origin average precision by estimable fold:",
            "",
            "| Feature set | RO1 | RO2 | RO3 |",
            "|---|---:|---:|---:|",
        ]
    )
    for feature_set in ("F1", "F2", "F3"):
        values = (
            rolling.filter(
                (pl.col("feature_set") == feature_set) & pl.col("average_precision").is_not_null()
            )
            .sort("fold_id")["average_precision"]
            .to_list()
        )
        lines.append(f"| {feature_set} | {values[0]:.6f} | {values[1]:.6f} | {values[2]:.6f} |")
    lines.extend(
        [
            "",
            "## Paired Bootstrap Differences",
            "",
            "Candidate-minus-reference intervals preserve identical resampled player-days.",
            "Negative Brier differences and positive AP differences favour the candidate.",
            "",
            "| Comparison | Method | Metric | Median | 95% interval |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in paired.iter_rows(named=True):
        lines.append(
            f"| {row['reference_feature_set']} to {row['candidate_feature_set']} | "
            f"{row['method']} | {row['metric']} | {row['median']:.6f} | "
            f"[{row['lower_95']:.6f}, {row['upper_95']:.6f}] |"
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
                "This is a controlled development feature-family ablation for "
                "practitioner-review prioritisation. It does not establish causality, "
                "diagnosis, medical clearance or deployment readiness."
            ),
            "",
            "## Gate",
            "",
            (
                "The project owner must select the raw feature-set candidate and approve a "
                "separate calibration experiment before any calibrator or final-test evaluation."
            ),
            "",
        ]
    )
    return "\n".join(lines)
