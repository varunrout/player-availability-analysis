"""Stage 3 feature-distribution and temporal exploratory analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from math import sqrt
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.features.subjective import WINDOWS_DAYS

CURRENT_NUMERIC_FEATURES = (
    "daily_load",
    "fatigue",
    "readiness",
    "wellness_metric_count",
    "session_count",
    "session_duration_minutes",
    "session_srpe",
)
ROLLING_SUM_ROOTS = ("daily_load", "session_duration", "session_srpe")
ROLLING_MEAN_ROOTS = ("fatigue", "readiness")
BASELINE_ROOTS = ("daily_load", "fatigue", "readiness")
ROLLING_FEATURES = tuple(
    [f"{root}_sum_{window}d" for root in ROLLING_SUM_ROOTS for window in WINDOWS_DAYS]
    + [f"{root}_mean_{window}d" for root in ROLLING_MEAN_ROOTS for window in WINDOWS_DAYS]
)
BASELINE_FEATURES = tuple(
    feature
    for root in BASELINE_ROOTS
    for feature in (f"{root}_baseline_mean_prior", f"{root}_zscore_prior")
)
NUMERIC_FEATURES = CURRENT_NUMERIC_FEATURES + ROLLING_FEATURES + BASELINE_FEATURES
CORE_CONTINUOUS_FEATURES = (
    "daily_load",
    "fatigue",
    "readiness",
    "session_duration_minutes",
    "session_srpe",
)


@dataclass(frozen=True, slots=True)
class Stage03FeatureDistributionResult:
    """Retained Stage 3 evidence and summary values."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_03_from_gcp(
    *, project_id: str, data_bucket: str
) -> Stage03FeatureDistributionResult:
    """Load the compact gold feature product from GCS and execute Stage 3."""
    client = Client(project=project_id)
    path = f"gold/{SOURCE_PREFIX}/player_day_features.parquet"
    features = pl.read_parquet(BytesIO(client.bucket(data_bucket).blob(path).download_as_bytes()))
    return run_stage_03_feature_distribution_eda(features)


def run_stage_03_feature_distribution_eda(
    features: pl.DataFrame,
) -> Stage03FeatureDistributionResult:
    """Profile feature behaviour without using outcome associations."""
    missing_columns = sorted(set(NUMERIC_FEATURES) - set(features.columns))
    if missing_columns:
        raise ValueError(f"Missing Stage 3 features: {missing_columns}")

    feature_eligibility = _feature_eligibility()
    feature_profile = _feature_profile(features, feature_eligibility)
    range_checks = _range_checks(features)
    zero_semantics = _zero_semantics(features)
    player_feature_summary = _player_feature_summary(features)
    within_between_variation = _within_between_variation(features)
    team_month_summary = _team_month_summary(features)
    rolling_window_summary = _rolling_window_summary(features)
    rolling_window_checks = _rolling_window_checks(features)
    baseline_stability = _baseline_stability(features)
    outlier_register = _outlier_register(features)
    outlier_summary = _outlier_summary(features, outlier_register)
    findings = _feature_findings(
        features=features,
        feature_profile=feature_profile,
        range_checks=range_checks,
        rolling_window_checks=rolling_window_checks,
        baseline_stability=baseline_stability,
        outlier_register=outlier_register,
        outlier_summary=outlier_summary,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "feature_eligibility": feature_eligibility,
        "feature_profile": feature_profile,
        "range_checks": range_checks,
        "zero_semantics": zero_semantics,
        "player_feature_summary": player_feature_summary,
        "within_between_variation": within_between_variation,
        "team_month_summary": team_month_summary,
        "rolling_window_summary": rolling_window_summary,
        "rolling_window_checks": rolling_window_checks,
        "baseline_stability": baseline_stability,
        "outlier_summary": outlier_summary,
        "outlier_register": outlier_register,
        "feature_distribution_findings": findings,
        "_features": features.select("player_id", "team_id", "prediction_date", *NUMERIC_FEATURES),
    }
    return Stage03FeatureDistributionResult(
        tables=tables,
        summary={
            "stage": "03_feature_distribution_eda",
            "status": "PASS" if failures == 0 else "FAIL",
            "player_day_count": features.height,
            "player_count": features["player_id"].n_unique(),
            "numeric_feature_count": len(NUMERIC_FEATURES),
            "range_failure_count": range_checks.filter(pl.col("status") == "FAIL").height,
            "outlier_register_count": outlier_register.height,
            "statistical_extreme_count": sum(
                int(value) for value in outlier_summary["extreme_count"].to_list()
            ),
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_03_figures(
    result: Stage03FeatureDistributionResult,
) -> dict[str, Figure]:
    """Build the approved Stage 3 figures without writing files."""
    figures: dict[str, Figure] = {}
    features = result.tables["_features"]

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for axis, feature in zip(axes.flat, CORE_CONTINUOUS_FEATURES, strict=False):
        values = _values(features, feature)
        axis.hist(values, bins=40, color="#287271", edgecolor="white")
        axis.set_title(feature.replace("_", " "))
        axis.set_ylabel("Player-days")
    axes.flat[-1].axis("off")
    fig.suptitle("Core feature distributions")
    fig.tight_layout()
    figures["core_feature_distributions"] = fig

    profile = result.tables["feature_profile"].filter(
        pl.col("feature").is_in(CURRENT_NUMERIC_FEATURES)
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.barh(profile["feature"], profile["zero_rate"], color="#D4A373")
    axis.set_xlim(0, 1)
    axis.set_xlabel("Zero proportion among all player-days")
    axis.set_title("Observed and derived zero prevalence")
    fig.tight_layout()
    figures["current_feature_zero_rates"] = fig

    zero = result.tables["zero_semantics"]
    fig, axis = plt.subplots(figsize=(8, 5))
    labels = [
        f"{'session' if row['session_recorded'] else 'no session'} / "
        f"{'zero load' if row['daily_load_zero'] else 'positive load'}"
        for row in zero.iter_rows(named=True)
    ]
    axis.bar(labels, zero["player_days"], color=["#287271", "#E9C46A", "#E76F51", "#6C757D"])
    axis.tick_params(axis="x", rotation=20)
    axis.set_ylabel("Player-days")
    axis.set_title("Session-record and daily-load zero combinations")
    fig.tight_layout()
    figures["session_load_zero_semantics"] = fig

    variation = result.tables["within_between_variation"]
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.barh(
        variation["feature"],
        variation["within_share"],
        label="Within player",
        color="#287271",
    )
    axis.barh(
        variation["feature"],
        variation["between_share"],
        left=variation["within_share"],
        label="Between players",
        color="#E76F51",
    )
    axis.set_xlim(0, 1)
    axis.set_xlabel("Share of observed sum-of-squares")
    axis.set_title("Within-player and between-player variation")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["within_between_variation"] = fig

    players = result.tables["player_feature_summary"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for axis, feature in zip(axes.flat, CORE_CONTINUOUS_FEATURES, strict=False):
        values = players.filter(pl.col("feature") == feature)["median"].drop_nulls().to_list()
        axis.boxplot(values, orientation="horizontal")
        axis.set_title(feature.replace("_", " "))
        axis.set_yticks([])
    axes.flat[-1].axis("off")
    fig.suptitle("Distribution of player-level medians")
    fig.tight_layout()
    figures["player_median_distributions"] = fig

    monthly = result.tables["team_month_summary"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for axis, feature in zip(axes, ("daily_load", "fatigue"), strict=True):
        rows = monthly.filter(pl.col("feature") == feature).sort("month")
        for team in rows["team_id"].unique(maintain_order=True):
            team_rows = rows.filter(pl.col("team_id") == team)
            axis.plot(team_rows["month"], team_rows["mean"], marker="o", label=str(team))
        axis.set_ylabel("Monthly mean")
        axis.set_title(feature.replace("_", " "))
        axis.legend(frameon=False)
    axes[-1].tick_params(axis="x", rotation=45)
    fig.suptitle("Team and calendar feature behaviour")
    fig.tight_layout()
    figures["team_month_feature_trends"] = fig

    rolling = result.tables["rolling_window_summary"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    roots = ROLLING_SUM_ROOTS + ROLLING_MEAN_ROOTS
    for axis, root in zip(axes.flat, roots, strict=False):
        rows = rolling.filter(pl.col("root") == root).sort("window_days")
        axis.plot(rows["window_days"], rows["p50"], marker="o", label="Median")
        axis.plot(rows["window_days"], rows["p95"], marker="o", label="95th percentile")
        axis.set_title(root.replace("_", " "))
        axis.set_xlabel("Window days")
        axis.legend(frameon=False)
    axes.flat[-1].axis("off")
    fig.suptitle("Rolling feature distributions by window")
    fig.tight_layout()
    figures["rolling_window_distributions"] = fig

    stability = result.tables["baseline_stability"]
    bands = stability["history_band"].unique(maintain_order=True).to_list()
    fig, axis = plt.subplots(figsize=(10, 5))
    for metric in BASELINE_ROOTS:
        rows = stability.filter(pl.col("metric") == metric)
        axis.plot(
            bands,
            rows["p95_abs_zscore"],
            marker="o",
            label=metric.replace("_", " "),
        )
    axis.set_ylabel("95th percentile absolute z-score")
    axis.set_title("Prior-baseline z-score stability by observed history")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["baseline_zscore_stability"] = fig

    outliers = result.tables["outlier_summary"].sort("extreme_count")
    fig, axis = plt.subplots(figsize=(11, 7))
    axis.barh(outliers["feature"], outliers["extreme_count"], color="#E76F51")
    axis.set_xlabel("Rows beyond the three-IQR outer fence")
    axis.set_title("Statistically extreme observations by feature")
    fig.tight_layout()
    fig.subplots_adjust(left=0.32)
    figures["outlier_register_counts"] = fig
    return figures


def write_stage_03_outputs(result: Stage03FeatureDistributionResult, output_root: Path) -> None:
    """Persist canonical Stage 3 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_03_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_03_FEATURE_DISTRIBUTION_EDA.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_03_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _feature_eligibility() -> pl.DataFrame:
    rows = []
    for feature in NUMERIC_FEATURES:
        if feature in {"fatigue", "readiness", "wellness_metric_count"}:
            eligibility = "descriptive_only_same_day"
            reason = "Same-day wellness/reporting field excluded under DEC-031"
        elif feature.startswith(("fatigue_mean_", "readiness_mean_")) or feature in {
            "fatigue_zscore_prior",
            "readiness_zscore_prior",
        }:
            eligibility = "requires_lagged_rebuild"
            reason = "Existing field includes the prediction-day wellness value"
        elif feature in {"fatigue_baseline_mean_prior", "readiness_baseline_mean_prior"}:
            eligibility = "primary_candidate_lagged"
            reason = "Prior-only wellness baseline excludes the prediction day"
        else:
            eligibility = "primary_candidate"
            reason = "No Stage 2 exclusion; later feature-contract review still required"
        rows.append(
            {
                "feature": feature,
                "family": _feature_family(feature),
                "eligibility": eligibility,
                "reason": reason,
            }
        )
    rows.append(
        {
            "feature": "wellness_report_present",
            "family": "reporting",
            "eligibility": "descriptive_only_same_day",
            "reason": "Same-day reporting indicator excluded under DEC-031",
        }
    )
    return pl.DataFrame(rows)


def _feature_family(feature: str) -> str:
    if "_sum_" in feature or "_mean_" in feature:
        return "rolling"
    if feature.endswith("_baseline_mean_prior"):
        return "prior_baseline"
    if feature.endswith("_zscore_prior"):
        return "player_relative"
    if feature.startswith("session_"):
        return "session"
    if feature in {"fatigue", "readiness", "wellness_metric_count"}:
        return "wellness"
    return "load"


def _feature_profile(features: pl.DataFrame, eligibility: pl.DataFrame) -> pl.DataFrame:
    eligibility_lookup = {str(row["feature"]): row for row in eligibility.to_dicts()}
    rows = []
    for feature in NUMERIC_FEATURES:
        values = _values(features, feature)
        metadata = eligibility_lookup[feature]
        rows.append(
            {
                "feature": feature,
                "family": metadata["family"],
                "eligibility": metadata["eligibility"],
                "player_days": features.height,
                "observed_count": len(values),
                "missing_count": features.height - len(values),
                "missing_rate": (features.height - len(values)) / features.height,
                "zero_count": sum(value == 0 for value in values),
                "zero_rate": sum(value == 0 for value in values) / features.height,
                "minimum": min(values) if values else None,
                "p01": _quantile(values, 0.01),
                "p05": _quantile(values, 0.05),
                "p25": _quantile(values, 0.25),
                "median": _quantile(values, 0.50),
                "p75": _quantile(values, 0.75),
                "p95": _quantile(values, 0.95),
                "p99": _quantile(values, 0.99),
                "maximum": max(values) if values else None,
                "mean": sum(values) / len(values) if values else None,
                "standard_deviation": _standard_deviation(values),
                "skewness": _skewness(values),
            }
        )
    return pl.DataFrame(rows)


def _range_checks(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    nonnegative = [feature for feature in NUMERIC_FEATURES if not feature.endswith("_zscore_prior")]
    for feature in NUMERIC_FEATURES:
        nonfinite = features.filter(
            pl.col(feature).is_not_null() & ~pl.col(feature).is_finite()
        ).height
        rows.append(
            _check_row(
                f"{feature}_finite",
                feature,
                "All observed values must be finite",
                nonfinite,
                "FAIL",
            )
        )
    for feature in nonnegative:
        negative = features.filter(pl.col(feature) < 0).height
        rows.append(
            _check_row(
                f"{feature}_nonnegative",
                feature,
                "Feature semantics require non-negative values",
                negative,
                "FAIL",
            )
        )
    metric_count_invalid = features.filter(~pl.col("wellness_metric_count").is_between(0, 7)).height
    rows.append(
        _check_row(
            "wellness_metric_count_range",
            "wellness_metric_count",
            "Completeness count must be between zero and seven",
            metric_count_invalid,
            "FAIL",
        )
    )
    return pl.DataFrame(rows)


def _check_row(
    check_id: str,
    feature: str,
    expectation: str,
    violation_count: int,
    severity: str,
) -> dict[str, object]:
    return {
        "check_id": check_id,
        "feature": feature,
        "expectation": expectation,
        "violation_count": violation_count,
        "status": "PASS" if violation_count == 0 else severity,
    }


def _zero_semantics(features: pl.DataFrame) -> pl.DataFrame:
    return (
        features.with_columns(
            (pl.col("session_count") > 0).alias("session_recorded"),
            (pl.col("daily_load") == 0).alias("daily_load_zero"),
        )
        .group_by("session_recorded", "daily_load_zero")
        .agg(
            pl.len().alias("player_days"),
            pl.median("daily_load").alias("median_daily_load"),
            pl.median("session_duration_minutes").alias("median_session_duration_minutes"),
            pl.median("session_srpe").alias("median_session_srpe"),
        )
        .with_columns(
            (pl.col("player_days") / features.height).alias("player_day_share"),
            pl.lit(
                "No recorded session remains unknown; daily-load zero is an observed derived value"
            ).alias("interpretation"),
        )
        .sort("session_recorded", "daily_load_zero")
    )


def _player_feature_summary(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for feature in CORE_CONTINUOUS_FEATURES:
        summary = features.group_by("player_id", "team_id").agg(
            pl.col(feature).count().alias("observed_count"),
            pl.col(feature).mean().alias("mean"),
            pl.col(feature).median().alias("median"),
            pl.col(feature).quantile(0.25).alias("p25"),
            pl.col(feature).quantile(0.75).alias("p75"),
            pl.col(feature).min().alias("minimum"),
            pl.col(feature).max().alias("maximum"),
        )
        rows.append(summary.with_columns(pl.lit(feature).alias("feature")))
    return pl.concat(rows).select(
        "player_id",
        "team_id",
        "feature",
        "observed_count",
        "mean",
        "median",
        "p25",
        "p75",
        "minimum",
        "maximum",
    )


def _within_between_variation(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for feature in CORE_CONTINUOUS_FEATURES:
        observed = features.select("player_id", feature).drop_nulls()
        values = _values(observed, feature)
        global_mean = sum(values) / len(values)
        player_means = observed.group_by("player_id").agg(
            pl.mean(feature).alias("player_mean"), pl.len().alias("count")
        )
        joined = observed.join(player_means, on="player_id")
        within_ss = sum(
            (float(row[feature]) - float(row["player_mean"])) ** 2
            for row in joined.iter_rows(named=True)
        )
        between_ss = sum(
            int(row["count"]) * (float(row["player_mean"]) - global_mean) ** 2
            for row in player_means.iter_rows(named=True)
        )
        total = within_ss + between_ss
        rows.append(
            {
                "feature": feature,
                "observed_count": len(values),
                "within_sum_squares": within_ss,
                "between_sum_squares": between_ss,
                "within_share": within_ss / total if total else None,
                "between_share": between_ss / total if total else None,
            }
        )
    return pl.DataFrame(rows)


def _team_month_summary(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    dated = features.with_columns(pl.col("prediction_date").dt.truncate("1mo").alias("month"))
    for feature in CORE_CONTINUOUS_FEATURES:
        rows.append(
            dated.group_by("team_id", "month")
            .agg(
                pl.col(feature).count().alias("observed_count"),
                pl.col(feature).mean().alias("mean"),
                pl.col(feature).median().alias("median"),
                pl.col(feature).quantile(0.95).alias("p95"),
            )
            .with_columns(pl.lit(feature).alias("feature"))
        )
    return pl.concat(rows).select(
        "team_id", "month", "feature", "observed_count", "mean", "median", "p95"
    )


def _rolling_window_summary(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for root in ROLLING_SUM_ROOTS + ROLLING_MEAN_ROOTS:
        operation = "sum" if root in ROLLING_SUM_ROOTS else "mean"
        for window in WINDOWS_DAYS:
            feature = f"{root}_{operation}_{window}d"
            values = _values(features, feature)
            rows.append(
                {
                    "root": root,
                    "operation": operation,
                    "window_days": window,
                    "feature": feature,
                    "observed_count": len(values),
                    "missing_rate": (features.height - len(values)) / features.height,
                    "p50": _quantile(values, 0.50),
                    "p95": _quantile(values, 0.95),
                    "p99": _quantile(values, 0.99),
                    "maximum": max(values) if values else None,
                }
            )
    return pl.DataFrame(rows)


def _rolling_window_checks(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for root in ROLLING_SUM_ROOTS:
        previous = None
        for window in WINDOWS_DAYS:
            feature = f"{root}_sum_{window}d"
            if previous is not None:
                violations = features.filter(pl.col(feature) < pl.col(previous)).height
                rows.append(
                    _check_row(
                        f"{root}_{previous}_le_{feature}",
                        feature,
                        "Non-negative rolling sums must not decrease as windows expand",
                        violations,
                        "FAIL",
                    )
                )
            previous = feature
    for root in ROLLING_MEAN_ROOTS:
        for window in WINDOWS_DAYS:
            feature = f"{root}_mean_{window}d"
            current_missing = features.filter(
                pl.col(root).is_not_null() & pl.col(feature).is_null()
            ).height
            rows.append(
                _check_row(
                    f"{feature}_present_with_current",
                    feature,
                    "Current observation must make its current-inclusive mean available",
                    current_missing,
                    "FAIL",
                )
            )
    return pl.DataFrame(rows)


def _baseline_stability(features: pl.DataFrame) -> pl.DataFrame:
    bands = (
        ("0-1", 0, 1),
        ("2-6", 2, 6),
        ("7-27", 7, 27),
        ("28-89", 28, 89),
        ("90+", 90, None),
    )
    rows = []
    sorted_features = features.sort("player_id", "prediction_date")
    for metric in BASELINE_ROOTS:
        frame = sorted_features.with_columns(
            (
                pl.col(metric).is_not_null().cast(pl.Int64).cum_sum().over("player_id")
                - pl.col(metric).is_not_null().cast(pl.Int64)
            ).alias("prior_observed_count"),
            pl.col(f"{metric}_zscore_prior").abs().alias("absolute_zscore"),
        )
        for label, lower, upper in bands:
            condition = (
                pl.col("prior_observed_count").is_between(lower, upper)
                if upper is not None
                else pl.col("prior_observed_count") >= lower
            )
            band = frame.filter(condition)
            current_observed_count = band[metric].drop_nulls().len()
            zscores = _values(band, "absolute_zscore")
            rows.append(
                {
                    "metric": metric,
                    "history_band": label,
                    "player_days": band.height,
                    "current_observed_count": current_observed_count,
                    "zscore_observed_count": len(zscores),
                    "zscore_available_rate": len(zscores) / band.height if band.height else None,
                    "zscore_available_given_current_rate": (
                        len(zscores) / current_observed_count if current_observed_count else None
                    ),
                    "median_abs_zscore": _quantile(zscores, 0.50),
                    "p95_abs_zscore": _quantile(zscores, 0.95),
                    "maximum_abs_zscore": max(zscores) if zscores else None,
                }
            )
    return pl.DataFrame(rows)


def _outlier_register(features: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for feature in NUMERIC_FEATURES:
        values = _values(features, feature)
        q25 = _quantile(values, 0.25)
        q75 = _quantile(values, 0.75)
        if q25 is None or q75 is None or q75 <= q25:
            continue
        spread = q75 - q25
        lower = q25 - 3 * spread
        upper = q75 + 3 * spread
        extremes = (
            features.filter(
                pl.col(feature).is_not_null()
                & ((pl.col(feature) < lower) | (pl.col(feature) > upper))
            )
            .select("player_id", "team_id", "prediction_date", feature)
            .with_columns(
                pl.when(pl.col(feature) < lower)
                .then(pl.lit("low"))
                .otherwise(pl.lit("high"))
                .alias("tail"),
                pl.when(pl.col(feature) < lower)
                .then((lower - pl.col(feature)) / spread)
                .otherwise((pl.col(feature) - upper) / spread)
                .alias("iqr_distance"),
            )
            .sort("iqr_distance", descending=True)
            .head(20)
        )
        for row in extremes.iter_rows(named=True):
            rows.append(
                {
                    "feature": feature,
                    "player_id": row["player_id"],
                    "team_id": row["team_id"],
                    "prediction_date": row["prediction_date"],
                    "observed_value": row[feature],
                    "tail": row["tail"],
                    "outer_fence": lower if row["tail"] == "low" else upper,
                    "iqr_distance": row["iqr_distance"],
                    "disposition": "REVIEW_ONLY",
                }
            )
    schema = {
        "feature": pl.String,
        "player_id": pl.String,
        "team_id": pl.String,
        "prediction_date": pl.Date,
        "observed_value": pl.Float64,
        "tail": pl.String,
        "outer_fence": pl.Float64,
        "iqr_distance": pl.Float64,
        "disposition": pl.String,
    }
    return pl.DataFrame(rows, schema=schema)


def _outlier_summary(features: pl.DataFrame, register: pl.DataFrame) -> pl.DataFrame:
    registered_counts = {
        str(row["feature"]): int(row["registered_count"])
        for row in register.group_by("feature").agg(pl.len().alias("registered_count")).to_dicts()
    }
    rows = []
    for feature in NUMERIC_FEATURES:
        values = _values(features, feature)
        q25 = _quantile(values, 0.25)
        q75 = _quantile(values, 0.75)
        if q25 is None or q75 is None or q75 <= q25:
            continue
        spread = q75 - q25
        lower = q25 - 3 * spread
        upper = q75 + 3 * spread
        extreme_count = features.filter(
            pl.col(feature).is_not_null() & ((pl.col(feature) < lower) | (pl.col(feature) > upper))
        ).height
        if extreme_count:
            rows.append(
                {
                    "feature": feature,
                    "lower_outer_fence": lower,
                    "upper_outer_fence": upper,
                    "extreme_count": extreme_count,
                    "extreme_rate": extreme_count / features.height,
                    "registered_count": registered_counts.get(feature, 0),
                    "register_cap_per_feature": 20,
                }
            )
    return pl.DataFrame(rows)


def _feature_findings(
    *,
    features: pl.DataFrame,
    feature_profile: pl.DataFrame,
    range_checks: pl.DataFrame,
    rolling_window_checks: pl.DataFrame,
    baseline_stability: pl.DataFrame,
    outlier_register: pl.DataFrame,
    outlier_summary: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []

    def finding(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    range_failures = range_checks.filter(pl.col("status") == "FAIL").height
    rolling_failures = rolling_window_checks.filter(pl.col("status") == "FAIL").height
    finding(
        "feature_ranges",
        "all numeric features",
        "PASS" if range_failures == 0 else "FAIL",
        f"{range_failures} finite, non-negative or bounded-count checks failed",
    )
    finding(
        "rolling_integrity",
        "rolling features",
        "PASS" if rolling_failures == 0 else "FAIL",
        f"{rolling_failures} rolling-window identities failed",
    )
    zero_load = feature_profile.filter(pl.col("feature") == "daily_load").item(0, "zero_rate")
    finding(
        "load_zero_prevalence",
        "daily load",
        "REVIEW",
        f"Daily load is zero on {float(zero_load):.1%} of player-days; zero is observed",
    )
    mature = baseline_stability.filter(
        (pl.col("metric") == "fatigue") & (pl.col("history_band") == "90+")
    )
    mature_rate = mature.item(0, "zscore_available_rate")
    mature_conditional_rate = mature.item(0, "zscore_available_given_current_rate")
    finding(
        "wellness_baseline_maturity",
        "fatigue prior baseline",
        "REVIEW",
        f"Fatigue z-score availability in the 90+ observed-history band is "
        f"{float(mature_rate):.1%} of calendar days and "
        f"{float(mature_conditional_rate):.1%} when current fatigue is observed",
    )
    maximum_zscores = {}
    for metric in BASELINE_ROOTS:
        row = feature_profile.filter(pl.col("feature") == f"{metric}_zscore_prior").row(
            0, named=True
        )
        maximum_zscores[metric] = max(abs(float(row["minimum"])), abs(float(row["maximum"])))
    finding(
        "zscore_tail_instability",
        "prior-relative features",
        "REVIEW",
        "Maximum absolute z-scores are "
        + ", ".join(f"{metric}={float(value):.1f}" for metric, value in maximum_zscores.items())
        + "; tiny prior variance can create unstable extremes",
    )
    finding(
        "outlier_register",
        "distribution tails",
        "REVIEW",
        f"{sum(int(value) for value in outlier_summary['extreme_count'].to_list())} rows "
        f"cross outer fences; {outlier_register.height} highest-severity rows retained "
        "for review, capped at 20 per feature",
    )
    finding(
        "same_day_wellness_boundary",
        "feature eligibility",
        "REVIEW",
        "Current wellness, current-inclusive wellness means and wellness z-scores remain "
        "descriptive-only or require lagged reconstruction under DEC-031",
    )
    finding(
        "session_absence_boundary",
        "session features",
        "REVIEW",
        f"{features.filter(pl.col('session_count') == 0).height} player-days have no "
        "recorded session; this is not confirmed rest",
    )
    return pl.DataFrame(rows)


def _render_report(result: Stage03FeatureDistributionResult) -> str:
    summary = result.summary
    profile = result.tables["feature_profile"]
    findings = result.tables["feature_distribution_findings"]
    variation = result.tables["within_between_variation"].sort("between_share", descending=True)
    highest_between = variation.row(0, named=True)
    load = profile.filter(pl.col("feature") == "daily_load").row(0, named=True)
    lines = [
        "# Stage 3 - Feature Distribution and Temporal EDA",
        "",
        "## Automated Status",
        "",
        f"Automated feature-integrity result: **{summary['status']}**. Project-owner "
        "review is required before Stage 4.",
        "",
        "## Scope",
        "",
        f"- Player-days: `{summary['player_day_count']}` across "
        f"`{summary['player_count']}` players.",
        f"- Numeric features profiled: `{summary['numeric_feature_count']}`.",
        f"- Review-only outlier rows retained: `{summary['outlier_register_count']}`.",
        f"- Statistical outer-fence crossings: `{summary['statistical_extreme_count']}`.",
        "",
        "## Decision Boundaries",
        "",
        "- Statistical extremeness alone does not justify correction or deletion.",
        "- Missing values and observed zeros remain distinct.",
        "- No recorded session is not interpreted as rest.",
        "- Current wellness, current-inclusive wellness means and wellness z-scores are "
        "not primary-model eligible under DEC-031.",
        "- No outcome association or model performance is analysed in this stage.",
        "",
        "## Distribution Highlights",
        "",
        f"- Daily load median: `{float(load['median']):.2f}`; 95th percentile: "
        f"`{float(load['p95']):.2f}`; zero rate: `{float(load['zero_rate']):.1%}`.",
        f"- Largest between-player variation share: `{highest_between['feature']}` at "
        f"`{float(highest_between['between_share']):.1%}`.",
        "",
        "## Findings",
        "",
        "| Check | Scope | Status | Message |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['check_id']} | {row['scope']} | {row['status']} | {row['message']} |"
        for row in findings.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Core distributions](../figures/core_feature_distributions.png)",
            "![Zero rates](../figures/current_feature_zero_rates.png)",
            "![Session/load semantics](../figures/session_load_zero_semantics.png)",
            "![Within/between variation](../figures/within_between_variation.png)",
            "![Player medians](../figures/player_median_distributions.png)",
            "![Team-month trends](../figures/team_month_feature_trends.png)",
            "![Rolling windows](../figures/rolling_window_distributions.png)",
            "![Baseline stability](../figures/baseline_zscore_stability.png)",
            "![Outlier register](../figures/outlier_register_counts.png)",
            "",
            "## Gate",
            "",
            "Approve credible ranges, any justified transformations, reliable feature "
            "families and history thresholds for later cohort sensitivity. Stage 3 does "
            "not delete observations or choose features from outcome performance.",
        ]
    )
    return "\n".join(lines) + "\n"


def _values(frame: pl.DataFrame, feature: str) -> list[float]:
    return [float(value) for value in frame[feature].drop_nulls().to_list()]


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _standard_deviation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _skewness(values: list[float]) -> float | None:
    standard_deviation = _standard_deviation(values)
    if standard_deviation is None or standard_deviation == 0:
        return None
    mean = sum(values) / len(values)
    return sum(((value - mean) / standard_deviation) ** 3 for value in values) / len(values)
