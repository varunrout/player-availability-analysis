"""Frozen chronological splits and predictor controls for subjective model development."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import polars as pl

PRIMARY_HORIZON_DAYS = 14
HISTORY_DAYS = 28
EMBARGO_DAYS = 14
TRAIN_FRACTION = 0.60
VALIDATION_FRACTION = 0.20
MODEL_PARTITIONS = ("train", "validation", "test")

PREDICTOR_ALLOWLIST = (
    "daily_load",
    "fatigue",
    "readiness",
    "wellness_report_present",
    "wellness_metric_count",
    "session_count",
    "session_duration_minutes",
    "session_srpe",
    "daily_load_sum_3d",
    "session_duration_sum_3d",
    "session_srpe_sum_3d",
    "fatigue_mean_3d",
    "readiness_mean_3d",
    "daily_load_sum_7d",
    "session_duration_sum_7d",
    "session_srpe_sum_7d",
    "fatigue_mean_7d",
    "readiness_mean_7d",
    "daily_load_sum_14d",
    "session_duration_sum_14d",
    "session_srpe_sum_14d",
    "fatigue_mean_14d",
    "readiness_mean_14d",
    "daily_load_sum_28d",
    "session_duration_sum_28d",
    "session_srpe_sum_28d",
    "fatigue_mean_28d",
    "readiness_mean_28d",
    "daily_load_baseline_mean_prior",
    "daily_load_zscore_prior",
    "fatigue_baseline_mean_prior",
    "fatigue_zscore_prior",
    "readiness_baseline_mean_prior",
    "readiness_zscore_prior",
)


@dataclass(frozen=True, slots=True)
class SplitManifest:
    """The reproducible date boundaries for the primary subjective evaluation."""

    primary_horizon_days: int
    history_days: int
    embargo_days: int
    source_start_date: str
    source_end_date: str
    train_start_date: str
    train_end_date: str
    train_validation_embargo_start_date: str
    train_validation_embargo_end_date: str
    validation_start_date: str
    validation_end_date: str
    validation_test_embargo_start_date: str
    validation_test_embargo_end_date: str
    test_start_date: str
    test_end_date: str
    predictor_columns: tuple[str, ...]
    partition_row_counts: dict[str, int]
    partition_primary_eligible_row_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable manifest."""
        return asdict(self)


def build_primary_split_manifest(features: pl.DataFrame) -> SplitManifest:
    """Freeze the shared date split from the 28-day-history, complete-14-day cohort."""
    _require_columns(
        features,
        {
            "player_id",
            "prediction_date",
            "label_complete_14d",
            "eligible_new_onset_14d",
            *PREDICTOR_ALLOWLIST,
        },
    )
    dates = _primary_candidate_dates(features)
    start_date = dates.min()
    end_date = dates.max()
    assert isinstance(start_date, date)
    assert isinstance(end_date, date)
    boundaries = _build_boundaries(start_date, end_date)
    split_frame = _assign_partitions(features, boundaries)
    partition_counts = _counts(split_frame, "chronological_partition")
    primary_counts = _counts(
        split_frame.filter(pl.col("modelling_eligible_14d")), "chronological_partition"
    )
    return SplitManifest(
        primary_horizon_days=PRIMARY_HORIZON_DAYS,
        history_days=HISTORY_DAYS,
        embargo_days=EMBARGO_DAYS,
        source_start_date=start_date.isoformat(),
        source_end_date=end_date.isoformat(),
        train_start_date=boundaries["train_start"].isoformat(),
        train_end_date=boundaries["train_end"].isoformat(),
        train_validation_embargo_start_date=boundaries["train_embargo_start"].isoformat(),
        train_validation_embargo_end_date=boundaries["train_embargo_end"].isoformat(),
        validation_start_date=boundaries["validation_start"].isoformat(),
        validation_end_date=boundaries["validation_end"].isoformat(),
        validation_test_embargo_start_date=boundaries["validation_embargo_start"].isoformat(),
        validation_test_embargo_end_date=boundaries["validation_embargo_end"].isoformat(),
        test_start_date=boundaries["test_start"].isoformat(),
        test_end_date=boundaries["test_end"].isoformat(),
        predictor_columns=PREDICTOR_ALLOWLIST,
        partition_row_counts=partition_counts,
        partition_primary_eligible_row_counts=primary_counts,
    )


def assign_primary_chronological_split(
    features: pl.DataFrame,
) -> tuple[pl.DataFrame, SplitManifest]:
    """Assign all player-days to a frozen partition and primary 14-day eligibility flag."""
    manifest = build_primary_split_manifest(features)
    boundaries = {
        "train_start": _parse_date(manifest.train_start_date),
        "train_end": _parse_date(manifest.train_end_date),
        "train_embargo_start": _parse_date(manifest.train_validation_embargo_start_date),
        "train_embargo_end": _parse_date(manifest.train_validation_embargo_end_date),
        "validation_start": _parse_date(manifest.validation_start_date),
        "validation_end": _parse_date(manifest.validation_end_date),
        "validation_embargo_start": _parse_date(manifest.validation_test_embargo_start_date),
        "validation_embargo_end": _parse_date(manifest.validation_test_embargo_end_date),
        "test_start": _parse_date(manifest.test_start_date),
        "test_end": _parse_date(manifest.test_end_date),
    }
    assigned = _assign_partitions(features, boundaries)
    _validate_split(assigned, manifest)
    return assigned, manifest


def validate_predictor_allowlist(features: pl.DataFrame) -> tuple[str, ...]:
    """Verify all approved predictors exist and that no target or identifier slipped in."""
    _require_columns(features, set(PREDICTOR_ALLOWLIST))
    forbidden = [
        column
        for column in PREDICTOR_ALLOWLIST
        if column.startswith(("injury_", "label_", "eligible_"))
        or column in {"player_id", "team_id", "prediction_date", "feature_timestamp"}
    ]
    if forbidden:
        raise ValueError(f"Predictor allow-list contains forbidden columns: {forbidden}")
    return PREDICTOR_ALLOWLIST


def render_split_manifest_markdown(manifest: SplitManifest) -> str:
    """Render a concise Phase B audit record; this is not model performance evidence."""
    lines = [
        "# Phase B - Chronological Split Manifest",
        "",
        "## Purpose",
        "",
        "This document freezes the shared chronological partitions for subjective model "
        "development. It contains no fitted model and no performance claim.",
        "",
        "## Leakage Controls",
        "",
        f"- Primary maximum horizon: `{manifest.primary_horizon_days}` days.",
        f"- Feature-history requirement: `{manifest.history_days}` days.",
        f"- Boundary embargo: `{manifest.embargo_days}` calendar days, "
        "matching the maximum headline horizon.",
        "- The predictor contract is an explicit allow-list; labels, eligibility, identifiers, "
        "dates, episode-state and provenance fields are not predictors.",
        "- Imputation, scaling, feature selection and calibration must be fit within their "
        "permitted development partition only.",
        "",
        "## Frozen Date Boundaries",
        "",
        "| Segment | Start | End |",
        "|---|---|---|",
        "| Source dates eligible for split construction | "
        f"{manifest.source_start_date} | {manifest.source_end_date} |",
        f"| Train | {manifest.train_start_date} | {manifest.train_end_date} |",
        "| Train-validation embargo | "
        f"{manifest.train_validation_embargo_start_date} | "
        f"{manifest.train_validation_embargo_end_date} |",
        f"| Validation | {manifest.validation_start_date} | {manifest.validation_end_date} |",
        "| Validation-test embargo | "
        f"{manifest.validation_test_embargo_start_date} | "
        f"{manifest.validation_test_embargo_end_date} |",
        f"| Test | {manifest.test_start_date} | {manifest.test_end_date} |",
        "",
        "## Assigned Rows",
        "",
        "| Partition | All player-days | 14-day primary eligible player-days |",
        "|---|---:|---:|",
    ]
    for partition in (
        "pre_history",
        "train",
        "embargo_train_validation",
        "validation",
        "embargo_validation_test",
        "test",
        "post_primary_horizon",
    ):
        lines.append(
            f"| {partition} | {manifest.partition_row_counts.get(partition, 0):,} | "
            f"{manifest.partition_primary_eligible_row_counts.get(partition, 0):,} |"
        )
    lines.extend(
        [
            "",
            "## Predictor Contract",
            "",
            "The frozen `subjective_v1` contract contains "
            f"`{len(manifest.predictor_columns)}` candidate predictors:",
            "",
        ]
    )
    lines.extend(f"- `{column}`" for column in manifest.predictor_columns)
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "EXP-002 may now implement the naive prevalence baseline against these partitions. "
            "It must report the same fixed test partition only once, after development decisions "
            "are complete.",
        ]
    )
    return "\n".join(lines) + "\n"


def _primary_candidate_dates(features: pl.DataFrame) -> pl.Series:
    with_history = _add_history_eligibility(features)
    dates = (
        with_history.filter(pl.col("history_eligible") & pl.col("label_complete_14d"))
        .get_column("prediction_date")
        .unique()
        .sort()
    )
    if dates.is_empty():
        raise ValueError(
            "No 28-day-history, complete-14-day dates available for chronological split"
        )
    return dates


def _build_boundaries(start_date: date, end_date: date) -> dict[str, date]:
    total_days = (end_date - start_date).days + 1
    train_days = int(total_days * TRAIN_FRACTION)
    validation_days = int(total_days * VALIDATION_FRACTION)
    if train_days < 1 or validation_days < 1:
        raise ValueError("Chronological split requires non-empty train and validation windows")
    train_end = start_date + timedelta(days=train_days - 1)
    train_embargo_start = train_end + timedelta(days=1)
    train_embargo_end = train_embargo_start + timedelta(days=EMBARGO_DAYS - 1)
    validation_start = train_embargo_end + timedelta(days=1)
    validation_end = validation_start + timedelta(days=validation_days - 1)
    validation_embargo_start = validation_end + timedelta(days=1)
    validation_embargo_end = validation_embargo_start + timedelta(days=EMBARGO_DAYS - 1)
    test_start = validation_embargo_end + timedelta(days=1)
    if test_start > end_date:
        raise ValueError("Chronological split leaves no test window after embargoes")
    return {
        "train_start": start_date,
        "train_end": train_end,
        "train_embargo_start": train_embargo_start,
        "train_embargo_end": train_embargo_end,
        "validation_start": validation_start,
        "validation_end": validation_end,
        "validation_embargo_start": validation_embargo_start,
        "validation_embargo_end": validation_embargo_end,
        "test_start": test_start,
        "test_end": end_date,
    }


def _assign_partitions(features: pl.DataFrame, boundaries: dict[str, date]) -> pl.DataFrame:
    with_history = _add_history_eligibility(features)
    partition = (
        pl.when(~pl.col("history_eligible"))
        .then(pl.lit("pre_history"))
        .when(pl.col("prediction_date") < boundaries["train_start"])
        .then(pl.lit("pre_history"))
        .when(pl.col("prediction_date") <= boundaries["train_end"])
        .then(pl.lit("train"))
        .when(pl.col("prediction_date") <= boundaries["train_embargo_end"])
        .then(pl.lit("embargo_train_validation"))
        .when(pl.col("prediction_date") <= boundaries["validation_end"])
        .then(pl.lit("validation"))
        .when(pl.col("prediction_date") <= boundaries["validation_embargo_end"])
        .then(pl.lit("embargo_validation_test"))
        .when(pl.col("prediction_date") <= boundaries["test_end"])
        .then(pl.lit("test"))
        .otherwise(pl.lit("post_primary_horizon"))
        .alias("chronological_partition")
    )
    return with_history.with_columns(partition).with_columns(
        (
            pl.col("chronological_partition").is_in(MODEL_PARTITIONS)
            & pl.col("label_complete_14d")
            & pl.col("eligible_new_onset_14d")
        ).alias("modelling_eligible_14d")
    )


def _add_history_eligibility(features: pl.DataFrame) -> pl.DataFrame:
    starts = features.group_by("player_id").agg(
        pl.min("prediction_date").alias("player_start_date")
    )
    return (
        features.join(starts, on="player_id")
        .with_columns(
            (
                pl.col("prediction_date")
                >= pl.col("player_start_date") + timedelta(days=HISTORY_DAYS - 1)
            ).alias("history_eligible")
        )
        .drop("player_start_date")
    )


def _counts(frame: pl.DataFrame, column: str) -> dict[str, int]:
    return {str(row[column]): int(row["len"]) for row in frame.group_by(column).len().to_dicts()}


def _validate_split(assigned: pl.DataFrame, manifest: SplitManifest) -> None:
    validation_start = _parse_date(manifest.validation_start_date)
    test_start = _parse_date(manifest.test_start_date)
    train_max = (
        assigned.filter(pl.col("chronological_partition") == "train")
        .get_column("prediction_date")
        .max()
    )
    validation_max = (
        assigned.filter(pl.col("chronological_partition") == "validation")
        .get_column("prediction_date")
        .max()
    )
    assert isinstance(train_max, date)
    assert isinstance(validation_max, date)
    if (validation_start - train_max).days <= EMBARGO_DAYS:
        raise ValueError("Train-validation boundary does not satisfy the required embargo")
    if (test_start - validation_max).days <= EMBARGO_DAYS:
        raise ValueError("Validation-test boundary does not satisfy the required embargo")
    validate_predictor_allowlist(assigned)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _require_columns(frame: pl.DataFrame, required: set[str]) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
