"""Stage 4 target-blind feature redundancy and structural analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from math import isfinite
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_03_feature_distribution_eda import (
    BASELINE_FEATURES,
    NUMERIC_FEATURES,
    ROLLING_SUM_ROOTS,
)
from player_availability.features.subjective import WINDOWS_DAYS

IDENTIFIER_COLUMNS = ("player_id", "team_id", "prediction_date")
REPORTING_COLUMNS = ("wellness_report_present",)
PROHIBITED_OUTCOME_TOKENS = ("injury", "episode", "label", "target", "eligible", "censor")
CURRENT_MAGNITUDES = ("daily_load", "session_duration_minutes", "session_srpe")
ROLLING_SUM_FEATURES = tuple(
    f"{root}_sum_{window}d" for root in ROLLING_SUM_ROOTS for window in WINDOWS_DAYS
)
MAGNITUDE_FEATURES = CURRENT_MAGNITUDES + ROLLING_SUM_FEATURES
LOG_FEATURES = tuple(f"{feature}_log1p" for feature in MAGNITUDE_FEATURES)
DERIVED_FEATURES = ("session_recorded",) + LOG_FEATURES
ANALYSIS_FEATURES = NUMERIC_FEATURES + REPORTING_COLUMNS + DERIVED_FEATURES
CORRELATION_THRESHOLD = 0.90
NEAR_DETERMINISTIC_THRESHOLD = 0.995


@dataclass(frozen=True, slots=True)
class Stage04FeatureRedundancyResult:
    """Retained Stage 4 evidence and target-blind contract proposals."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_04_from_gcp(*, project_id: str, data_bucket: str) -> Stage04FeatureRedundancyResult:
    """Load the compact gold feature product from GCS and execute Stage 4."""
    client = Client(project=project_id)
    path = f"gold/{SOURCE_PREFIX}/player_day_features.parquet"
    features = pl.read_parquet(BytesIO(client.bucket(data_bucket).blob(path).download_as_bytes()))
    return run_stage_04_feature_redundancy(features)


def run_stage_04_feature_redundancy(
    features: pl.DataFrame,
) -> Stage04FeatureRedundancyResult:
    """Measure predictor structure without reading or evaluating outcomes."""
    required = set(IDENTIFIER_COLUMNS + REPORTING_COLUMNS + NUMERIC_FEATURES)
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Missing Stage 4 columns: {missing}")

    analysis = _build_analysis_frame(features)
    inventory = _feature_contract_inventory()
    correlations = _correlation_register(analysis, ANALYSIS_FEATURES)
    high_correlations = correlations.filter(
        (pl.col("feature_left") < pl.col("feature_right"))
        & (pl.col("spearman").abs() >= CORRELATION_THRESHOLD)
    ).sort("abs_spearman", descending=True)
    within_player = _within_player_correlations(analysis, _eligible_features(inventory))
    deterministic = _near_deterministic_checks(analysis, correlations)
    load_coupling = _load_coupling_summary(analysis)
    rolling_redundancy = _rolling_redundancy(correlations)
    transform_checks = _transformation_checks(analysis)
    feature_clusters = _feature_clusters(inventory, correlations)
    full_contract = inventory.filter(pl.col("contract_status") == "full_candidate").select(
        "feature",
        "source_feature",
        "family",
        "representation",
        "timing",
        "reason",
    )
    operational_contract = _operational_feature_family_contract()
    findings = _structural_findings(
        features=features,
        analysis=analysis,
        correlations=correlations,
        high_correlations=high_correlations,
        deterministic=deterministic,
        load_coupling=load_coupling,
        transform_checks=transform_checks,
        full_contract=full_contract,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "feature_contract_inventory": inventory,
        "correlation_register": correlations,
        "high_correlation_pairs": high_correlations,
        "within_player_correlations": within_player,
        "near_deterministic_checks": deterministic,
        "load_coupling_summary": load_coupling,
        "rolling_window_redundancy": rolling_redundancy,
        "transformation_checks": transform_checks,
        "feature_clusters": feature_clusters,
        "full_candidate_contract": full_contract,
        "operational_feature_family_contract": operational_contract,
        "structural_findings": findings,
        "_analysis": analysis,
    }
    return Stage04FeatureRedundancyResult(
        tables=tables,
        summary={
            "stage": "04_feature_redundancy",
            "status": "PASS" if failures == 0 else "FAIL",
            "player_day_count": analysis.height,
            "player_count": analysis["player_id"].n_unique(),
            "source_numeric_feature_count": len(NUMERIC_FEATURES),
            "derived_candidate_count": len(DERIVED_FEATURES),
            "full_candidate_count": full_contract.height,
            "high_correlation_pair_count": high_correlations.height,
            "near_deterministic_pair_count": deterministic.filter(
                pl.col("classification") == "near_deterministic"
            ).height,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "outcome_columns_used": 0,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_04_figures(result: Stage04FeatureRedundancyResult) -> dict[str, Figure]:
    """Build the approved Stage 4 figures without writing files."""
    figures: dict[str, Figure] = {}
    inventory = result.tables["feature_contract_inventory"]
    eligible = _eligible_features(inventory)
    correlations = result.tables["correlation_register"]

    figures["candidate_spearman_heatmap"] = _correlation_figure(
        correlations,
        eligible,
        "spearman",
        "Target-blind candidate Spearman correlations",
    )
    within = result.tables["within_player_correlations"]
    figures["within_player_correlation_heatmap"] = _correlation_figure(
        within,
        eligible,
        "within_player_pearson",
        "Within-player candidate correlations",
    )

    rolling = result.tables["rolling_window_redundancy"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for axis, root in zip(axes, ROLLING_SUM_ROOTS, strict=True):
        rows = rolling.filter(pl.col("root") == root).sort("short_window_days")
        labels = [
            f"{row['short_window_days']}:{row['long_window_days']}"
            for row in rows.iter_rows(named=True)
        ]
        axis.plot(labels, rows["spearman"], marker="o", color="#287271")
        axis.axhline(CORRELATION_THRESHOLD, color="#E76F51", linestyle="--")
        axis.set_ylim(0, 1.02)
        axis.set_title(root.replace("_", " "))
        axis.set_xlabel("Window pair (days)")
    axes[0].set_ylabel("Spearman correlation")
    fig.suptitle("Adjacent rolling-window redundancy")
    fig.tight_layout()
    figures["rolling_window_redundancy"] = fig

    coupling = result.tables["load_coupling_summary"]
    fig, axis = plt.subplots(figsize=(10, 5))
    positions = list(range(coupling.height))
    width = 0.36
    axis.bar(
        [position - width / 2 for position in positions],
        coupling["spearman_all_days"],
        width,
        label="All calendar days",
        color="#287271",
    )
    axis.bar(
        [position + width / 2 for position in positions],
        coupling["spearman_positive_recorded_days"],
        width,
        label="Recorded positive days",
        color="#E9C46A",
    )
    axis.set_xticks(positions, coupling["pair_label"], rotation=15, ha="right")
    axis.set_ylim(-1, 1)
    axis.set_ylabel("Spearman correlation")
    axis.set_title("Load-system coupling with and without structural zeros")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["load_system_coupling"] = fig

    transform_rows = correlations.filter(
        pl.col("feature_right") == (pl.col("feature_left") + pl.lit("_log1p"))
    ).sort("feature_left")
    fig, axis = plt.subplots(figsize=(11, 6))
    axis.barh(transform_rows["feature_left"], transform_rows["pearson"], color="#457B9D")
    axis.set_xlim(0, 1)
    axis.set_xlabel("Pearson correlation between raw and log1p")
    axis.set_title("Effect of log1p on magnitude geometry")
    fig.tight_layout()
    fig.subplots_adjust(left=0.34)
    figures["raw_log1p_relationships"] = fig

    wellness = (
        "fatigue",
        "readiness",
        "wellness_report_present",
        "wellness_metric_count",
        "fatigue_mean_7d",
        "readiness_mean_7d",
        "fatigue_baseline_mean_prior",
        "readiness_baseline_mean_prior",
    )
    figures["wellness_reporting_heatmap"] = _correlation_figure(
        correlations,
        wellness,
        "spearman",
        "Descriptive wellness and reporting structure",
    )

    dispositions = (
        inventory.group_by("contract_status")
        .agg(pl.len().alias("feature_count"))
        .sort("feature_count")
    )
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.barh(dispositions["contract_status"], dispositions["feature_count"], color="#E76F51")
    axis.set_xlabel("Feature representations")
    axis.set_title("Target-blind feature-contract disposition")
    fig.tight_layout()
    figures["feature_contract_disposition"] = fig
    return figures


def write_stage_04_outputs(result: Stage04FeatureRedundancyResult, output_root: Path) -> None:
    """Persist canonical Stage 4 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_04_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_04_FEATURE_REDUNDANCY.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_04_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_analysis_frame(features: pl.DataFrame) -> pl.DataFrame:
    selected = features.select(*IDENTIFIER_COLUMNS, *REPORTING_COLUMNS, *NUMERIC_FEATURES)
    expressions = [
        pl.col("wellness_report_present").cast(pl.Int8),
        (pl.col("session_count") > 0).cast(pl.Int8).alias("session_recorded"),
    ]
    expressions.extend(
        pl.col(feature).log1p().alias(f"{feature}_log1p") for feature in MAGNITUDE_FEATURES
    )
    return selected.with_columns(expressions)


def _feature_contract_inventory() -> pl.DataFrame:
    rows: list[dict[str, str]] = []
    for feature in NUMERIC_FEATURES:
        family = _feature_family(feature)
        if feature in {"fatigue", "readiness", "wellness_metric_count"}:
            status = "descriptive_only"
            timing = "same_day"
            reason = "Same-day wellness/reporting is excluded under DEC-031"
        elif feature.startswith(("fatigue_mean_", "readiness_mean_")):
            status = "requires_lagged_rebuild"
            timing = "current_inclusive"
            reason = "Current-inclusive wellness rolling mean is ineligible under DEC-031"
        elif feature.endswith("_zscore_prior"):
            status = "excluded_unstable"
            timing = "prior_baseline_plus_current"
            reason = "Existing z-score has unstable tails under DEC-032"
        else:
            status = "full_candidate"
            timing = "prior_only" if feature.endswith("_baseline_mean_prior") else "end_of_day"
            reason = "Target-blind candidate retained for structural review"
        rows.append(
            {
                "feature": feature,
                "source_feature": feature,
                "family": family,
                "representation": "raw",
                "timing": timing,
                "contract_status": status,
                "reason": reason,
            }
        )
    rows.append(
        {
            "feature": "wellness_report_present",
            "source_feature": "wellness_report_present",
            "family": "reporting_state",
            "representation": "binary_indicator",
            "timing": "same_day",
            "contract_status": "descriptive_only",
            "reason": "Same-day reporting indicator is excluded under DEC-031",
        }
    )
    rows.append(
        {
            "feature": "session_recorded",
            "source_feature": "session_count",
            "family": "recording_state",
            "representation": "binary_indicator",
            "timing": "end_of_day",
            "contract_status": "full_candidate",
            "reason": "Separates recording state from exposure magnitude under DEC-032",
        }
    )
    for feature in MAGNITUDE_FEATURES:
        rows.append(
            {
                "feature": f"{feature}_log1p",
                "source_feature": feature,
                "family": _feature_family(feature),
                "representation": "log1p",
                "timing": "end_of_day",
                "contract_status": "full_candidate",
                "reason": "Skew-resistant magnitude candidate accepted under DEC-032",
            }
        )
    return pl.DataFrame(rows)


def _feature_family(feature: str) -> str:
    base = feature.removesuffix("_log1p")
    if base.endswith("_baseline_mean_prior"):
        return "prior_baseline"
    if base.endswith("_zscore_prior"):
        return "player_relative"
    if "_sum_" in base:
        return "rolling_load"
    if "_mean_" in base:
        return "rolling_wellness"
    if base.startswith("session_"):
        return "session"
    if base in {"fatigue", "readiness", "wellness_metric_count"}:
        return "wellness"
    return "load"


def _eligible_features(inventory: pl.DataFrame) -> tuple[str, ...]:
    return tuple(
        str(value)
        for value in inventory.filter(pl.col("contract_status") == "full_candidate")[
            "feature"
        ].to_list()
    )


def _correlation_register(frame: pl.DataFrame, features: tuple[str, ...]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for left_index, left in enumerate(features):
        for right in features[left_index:]:
            pair = (
                frame.select(left).drop_nulls()
                if left == right
                else frame.select(left, right).drop_nulls()
            )
            pearson = _correlation(pair, left, right, "pearson")
            spearman = _correlation(pair, left, right, "spearman")
            rows.append(
                {
                    "feature_left": left,
                    "feature_right": right,
                    "pairwise_count": pair.height,
                    "pearson": pearson,
                    "spearman": spearman,
                    "abs_spearman": abs(spearman) if spearman is not None else None,
                }
            )
            if left != right:
                rows.append(
                    {
                        "feature_left": right,
                        "feature_right": left,
                        "pairwise_count": pair.height,
                        "pearson": pearson,
                        "spearman": spearman,
                        "abs_spearman": abs(spearman) if spearman is not None else None,
                    }
                )
    return pl.DataFrame(rows)


def _correlation(
    pair: pl.DataFrame,
    left: str,
    right: str,
    method: Literal["pearson", "spearman"],
) -> float | None:
    if pair.height < 2:
        return None
    if left == right:
        return 1.0
    value = pair.select(pl.corr(left, right, method=method)).item()
    if value is None:
        return None
    number = float(value)
    if not isfinite(number):
        return None
    if abs(number) <= 1.0 + 1e-12:
        return max(-1.0, min(1.0, number))
    return number


def _within_player_correlations(frame: pl.DataFrame, features: tuple[str, ...]) -> pl.DataFrame:
    centered = frame.select(
        "player_id",
        *(
            (pl.col(feature) - pl.col(feature).mean().over("player_id")).alias(feature)
            for feature in features
        ),
    )
    rows: list[dict[str, object]] = []
    for left_index, left in enumerate(features):
        for right in features[left_index:]:
            pair = (
                centered.select(left).drop_nulls()
                if left == right
                else centered.select(left, right).drop_nulls()
            )
            value = _correlation(pair, left, right, "pearson")
            for first, second in ((left, right), (right, left)):
                if first == second and first != left:
                    continue
                rows.append(
                    {
                        "feature_left": first,
                        "feature_right": second,
                        "pairwise_count": pair.height,
                        "within_player_pearson": value,
                    }
                )
    return pl.DataFrame(rows)


def _near_deterministic_checks(frame: pl.DataFrame, correlations: pl.DataFrame) -> pl.DataFrame:
    pairs = correlations.filter(
        (pl.col("feature_left") < pl.col("feature_right"))
        & (pl.col("abs_spearman") >= NEAR_DETERMINISTIC_THRESHOLD)
    )
    rows: list[dict[str, object]] = []
    for row in pairs.iter_rows(named=True):
        left = str(row["feature_left"])
        right = str(row["feature_right"])
        pair = frame.select(left, right).drop_nulls()
        exact_equal = pair.filter(pl.col(left) != pl.col(right)).is_empty()
        transform_pair = right == f"{left}_log1p" or left == f"{right}_log1p"
        rows.append(
            {
                "feature_left": left,
                "feature_right": right,
                "pairwise_count": pair.height,
                "pearson": row["pearson"],
                "spearman": row["spearman"],
                "exact_equal": exact_equal,
                "expected_transform_pair": transform_pair,
                "classification": "near_deterministic",
                "disposition": "REVIEW_REPRESENTATION_REDUNDANCY",
            }
        )
    schema = {
        "feature_left": pl.String,
        "feature_right": pl.String,
        "pairwise_count": pl.Int64,
        "pearson": pl.Float64,
        "spearman": pl.Float64,
        "exact_equal": pl.Boolean,
        "expected_transform_pair": pl.Boolean,
        "classification": pl.String,
        "disposition": pl.String,
    }
    return pl.DataFrame(rows, schema=schema)


def _load_coupling_summary(frame: pl.DataFrame) -> pl.DataFrame:
    pairs = (
        ("daily_load", "session_duration_minutes"),
        ("daily_load", "session_srpe"),
        ("session_duration_minutes", "session_srpe"),
    )
    positive = frame.filter(
        (pl.col("session_recorded") == 1)
        & (pl.col("daily_load") > 0)
        & (pl.col("session_duration_minutes") > 0)
        & (pl.col("session_srpe") > 0)
    )
    rows = []
    for left, right in pairs:
        all_pair = frame.select(left, right).drop_nulls()
        positive_pair = positive.select(left, right).drop_nulls()
        zero_agreement = frame.select((pl.col(left) == 0) == (pl.col(right) == 0)).to_series()
        zero_agreement_rate = sum(bool(value) for value in zero_agreement.to_list()) / frame.height
        rows.append(
            {
                "pair_label": f"{left} vs {right}",
                "feature_left": left,
                "feature_right": right,
                "all_day_count": all_pair.height,
                "positive_recorded_day_count": positive_pair.height,
                "zero_state_agreement_rate": zero_agreement_rate,
                "pearson_all_days": _correlation(all_pair, left, right, "pearson"),
                "spearman_all_days": _correlation(all_pair, left, right, "spearman"),
                "pearson_positive_recorded_days": _correlation(
                    positive_pair, left, right, "pearson"
                ),
                "spearman_positive_recorded_days": _correlation(
                    positive_pair, left, right, "spearman"
                ),
            }
        )
    return pl.DataFrame(rows)


def _rolling_redundancy(correlations: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for root in ROLLING_SUM_ROOTS:
        for short, long in zip(WINDOWS_DAYS[:-1], WINDOWS_DAYS[1:], strict=True):
            left = f"{root}_sum_{short}d_log1p"
            right = f"{root}_sum_{long}d_log1p"
            row = correlations.filter(
                (pl.col("feature_left") == left) & (pl.col("feature_right") == right)
            ).row(0, named=True)
            rows.append(
                {
                    "root": root,
                    "short_window_days": short,
                    "long_window_days": long,
                    "pairwise_count": row["pairwise_count"],
                    "pearson": row["pearson"],
                    "spearman": row["spearman"],
                    "above_redundancy_threshold": abs(float(row["spearman"]))
                    >= CORRELATION_THRESHOLD,
                }
            )
    return pl.DataFrame(rows)


def _transformation_checks(frame: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for feature in MAGNITUDE_FEATURES:
        transformed = f"{feature}_log1p"
        invalid = frame.filter(
            pl.col(transformed).is_null()
            | ~pl.col(transformed).is_finite()
            | (pl.col(transformed) < 0)
        ).height
        zero_mismatch = frame.filter((pl.col(feature) == 0) != (pl.col(transformed) == 0)).height
        rank_pair = frame.select(feature, transformed).drop_nulls()
        rank_correlation = _correlation(rank_pair, feature, transformed, "spearman")
        rows.append(
            {
                "feature": feature,
                "transformed_feature": transformed,
                "invalid_value_count": invalid,
                "zero_preservation_violation_count": zero_mismatch,
                "spearman_raw_vs_log1p": rank_correlation,
                "status": "PASS"
                if invalid == 0 and zero_mismatch == 0 and rank_correlation == 1.0
                else "FAIL",
            }
        )
    return pl.DataFrame(rows)


def _feature_clusters(inventory: pl.DataFrame, correlations: pl.DataFrame) -> pl.DataFrame:
    features = _eligible_features(inventory)
    parent = {feature: feature for feature in features}

    def find(feature: str) -> str:
        while parent[feature] != feature:
            parent[feature] = parent[parent[feature]]
            feature = parent[feature]
        return feature

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    eligible_set = set(features)
    pairs = correlations.filter(
        (pl.col("feature_left") < pl.col("feature_right"))
        & (pl.col("abs_spearman") >= CORRELATION_THRESHOLD)
    )
    for row in pairs.iter_rows(named=True):
        left = str(row["feature_left"])
        right = str(row["feature_right"])
        if left in eligible_set and right in eligible_set:
            union(left, right)
    roots = {root: index + 1 for index, root in enumerate(sorted({find(f) for f in features}))}
    metadata = {str(row["feature"]): row for row in inventory.iter_rows(named=True)}
    rows = []
    for feature in features:
        root = find(feature)
        rows.append(
            {
                "cluster_id": f"CLU-{roots[root]:02d}",
                "feature": feature,
                "family": metadata[feature]["family"],
                "representation": metadata[feature]["representation"],
                "cluster_threshold_abs_spearman": CORRELATION_THRESHOLD,
            }
        )
    return pl.DataFrame(rows).sort("cluster_id", "feature")


def _operational_feature_family_contract() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "family_role": "recording_state",
                "candidate_features": "session_recorded; session_count",
                "proposal": "PROPOSED_INCLUDE",
                "reason": "Retains whether and how many sessions were recorded",
            },
            {
                "family_role": "current_load_magnitude",
                "candidate_features": "; ".join(f"{name}_log1p" for name in CURRENT_MAGNITUDES),
                "proposal": "REVIEW_COUPLING",
                "reason": "Select structurally distinct magnitude representations after review",
            },
            {
                "family_role": "recent_accumulated_load",
                "candidate_features": "; ".join(
                    f"{root}_sum_7d_log1p" for root in ROLLING_SUM_ROOTS
                ),
                "proposal": "PROPOSED_INCLUDE",
                "reason": "Seven-day operational context; target-blind domain anchor",
            },
            {
                "family_role": "longer_accumulated_load",
                "candidate_features": "; ".join(
                    f"{root}_sum_28d_log1p" for root in ROLLING_SUM_ROOTS
                ),
                "proposal": "PROPOSED_INCLUDE",
                "reason": "Twenty-eight-day context; history impact remains Stage 6 sensitivity",
            },
            {
                "family_role": "intermediate_rolling_windows",
                "candidate_features": "3d and 14d log1p rolling sums",
                "proposal": "PROPOSED_DEFER",
                "reason": (
                    "Retain in full contract; operational inclusion depends on redundancy review"
                ),
            },
            {
                "family_role": "prior_player_baselines",
                "candidate_features": "; ".join(
                    feature for feature in BASELINE_FEATURES if feature.endswith("_mean_prior")
                ),
                "proposal": "PROPOSED_DEFER",
                "reason": "History and representation effects require Stage 6 and Stage 7 controls",
            },
            {
                "family_role": "wellness_state",
                "candidate_features": "lagged fatigue/readiness/reporting features not yet built",
                "proposal": "REQUIRES_LAGGED_REBUILD",
                "reason": "Same-day/current-inclusive fields remain ineligible under DEC-031",
            },
            {
                "family_role": "existing_zscores",
                "candidate_features": (
                    "daily_load_zscore_prior; fatigue_zscore_prior; readiness_zscore_prior"
                ),
                "proposal": "EXCLUDE",
                "reason": "Unstable denominator behaviour under DEC-032",
            },
        ]
    )


def _structural_findings(
    *,
    features: pl.DataFrame,
    analysis: pl.DataFrame,
    correlations: pl.DataFrame,
    high_correlations: pl.DataFrame,
    deterministic: pl.DataFrame,
    load_coupling: pl.DataFrame,
    transform_checks: pl.DataFrame,
    full_contract: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def add(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    analysis_outcomes = [
        column
        for column in analysis.columns
        if any(token in column.lower() for token in PROHIBITED_OUTCOME_TOKENS)
    ]
    add(
        "outcome_isolation",
        "analysis frame",
        "PASS" if not analysis_outcomes else "FAIL",
        f"{len(analysis_outcomes)} prohibited outcome-like columns entered the analysis frame",
    )
    transform_failures = transform_checks.filter(pl.col("status") == "FAIL").height
    add(
        "transform_integrity",
        "log1p candidates",
        "PASS" if transform_failures == 0 else "FAIL",
        f"{transform_failures} transformation checks failed",
    )
    invalid_correlations = correlations.filter(
        pl.col("pearson").is_not_null() & ((pl.col("pearson") < -1) | (pl.col("pearson") > 1))
        | pl.col("spearman").is_not_null() & ((pl.col("spearman") < -1) | (pl.col("spearman") > 1))
    ).height
    add(
        "correlation_bounds",
        "correlation register",
        "PASS" if invalid_correlations == 0 else "FAIL",
        f"{invalid_correlations} coefficients fall outside [-1, 1]",
    )
    constant_candidates = []
    for feature in full_contract["feature"].to_list():
        if analysis[str(feature)].drop_nulls().n_unique() <= 1:
            constant_candidates.append(str(feature))
    add(
        "candidate_variation",
        "full candidate contract",
        "PASS" if not constant_candidates else "FAIL",
        f"{len(constant_candidates)} candidates are constant or empty",
    )
    add(
        "high_correlation_review",
        "candidate representations",
        "REVIEW",
        f"{high_correlations.height} feature pairs have absolute Spearman correlation at least "
        f"{CORRELATION_THRESHOLD:.2f}",
    )
    add(
        "near_deterministic_review",
        "candidate representations",
        "REVIEW",
        f"{deterministic.height} pairs reach the near-deterministic threshold; expected raw/log "
        "pairs remain alternatives, not independent evidence",
    )
    strongest = load_coupling.sort("spearman_positive_recorded_days", descending=True).row(
        0, named=True
    )
    add(
        "load_coupling_review",
        "load system",
        "REVIEW",
        f"Strongest positive-recorded-day coupling is {strongest['pair_label']} at Spearman "
        f"{float(strongest['spearman_positive_recorded_days']):.3f}",
    )
    add(
        "same_day_wellness_boundary",
        "wellness features",
        "PASS",
        "Same-day and current-inclusive wellness fields are absent from the full "
        "candidate contract",
    )
    add(
        "source_preservation",
        "canonical features",
        "PASS" if features.height == analysis.height else "FAIL",
        "Stage 4 adds target-blind representations without dropping player-days or "
        "modifying source values",
    )
    return pl.DataFrame(rows)


def _correlation_figure(
    register: pl.DataFrame,
    features: tuple[str, ...],
    value_column: str,
    title: str,
) -> Figure:
    lookup = {
        (str(row["feature_left"]), str(row["feature_right"])): row[value_column]
        for row in register.iter_rows(named=True)
    }
    matrix = [[float(lookup.get((left, right)) or 0.0) for right in features] for left in features]
    size = max(8.0, len(features) * 0.28)
    fig, axis = plt.subplots(figsize=(size, size))
    image = axis.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    axis.set_xticks(range(len(features)), features, rotation=90, fontsize=7)
    axis.set_yticks(range(len(features)), features, fontsize=7)
    axis.set_title(title)
    fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def _render_report(result: Stage04FeatureRedundancyResult) -> str:
    summary = result.summary
    findings = result.tables["structural_findings"]
    coupling = result.tables["load_coupling_summary"].sort(
        "spearman_positive_recorded_days", descending=True
    )
    strongest = coupling.row(0, named=True)
    lines = [
        "# Stage 4 - Feature Redundancy and Structural Relationships",
        "",
        "## Automated Status",
        "",
        f"Automated structural-integrity result: **{summary['status']}**. Project-owner review "
        "is required before Stage 5.",
        "",
        "## Scope",
        "",
        f"- Player-days: `{summary['player_day_count']}` across "
        f"`{summary['player_count']}` players.",
        f"- Source numeric features: `{summary['source_numeric_feature_count']}`.",
        f"- Derived target-blind candidates: `{summary['derived_candidate_count']}`.",
        f"- Full-contract candidates: `{summary['full_candidate_count']}`.",
        f"- Outcome columns used: `{summary['outcome_columns_used']}`.",
        "",
        "## Decision Boundaries",
        "",
        "- Correlation and deterministic structure do not establish predictive value.",
        "- High correlation does not automatically remove a feature; it identifies alternatives.",
        "- Same-day/current-inclusive wellness remains outside the primary contract under DEC-031.",
        "- Existing z-scores remain excluded under DEC-032.",
        "- Raw source values and all player-days remain unchanged.",
        "",
        "## Structural Highlights",
        "",
        f"- `{summary['high_correlation_pair_count']}` pairs cross the absolute Spearman "
        f"threshold of `{CORRELATION_THRESHOLD:.2f}`.",
        f"- `{summary['near_deterministic_pair_count']}` pairs cross the near-deterministic "
        f"threshold of `{NEAR_DETERMINISTIC_THRESHOLD:.3f}`.",
        f"- Strongest positive-recorded-day load coupling: `{strongest['pair_label']}` at "
        f"Spearman `{float(strongest['spearman_positive_recorded_days']):.3f}`.",
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
            "![Candidate correlations](../figures/candidate_spearman_heatmap.png)",
            "![Within-player correlations](../figures/within_player_correlation_heatmap.png)",
            "![Rolling redundancy](../figures/rolling_window_redundancy.png)",
            "![Load coupling](../figures/load_system_coupling.png)",
            "![Raw and log1p](../figures/raw_log1p_relationships.png)",
            "![Wellness structure](../figures/wellness_reporting_heatmap.png)",
            "![Contract disposition](../figures/feature_contract_disposition.png)",
            "",
            "## Gate",
            "",
            "Approve or revise the full candidate contract and the smaller operational "
            "feature-family proposal. Stage 4 does not use outcomes or model performance.",
        ]
    )
    return "\n".join(lines) + "\n"
