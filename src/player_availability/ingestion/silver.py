"""Canonical silver relations for the verified SoccerMon subjective bronze layer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

TRAINING_LOAD_METRICS = (
    "acwr",
    "atl",
    "ctl28",
    "ctl42",
    "daily_load",
    "monotony",
    "strain",
    "weekly_load",
)
WELLNESS_METRICS = (
    "fatigue",
    "mood",
    "readiness",
    "sleep_duration",
    "sleep_quality",
    "soreness",
    "stress",
)
EVENT_RELATIONS = ("injury_reports", "illness_reports", "game_performance_reports")


@dataclass(frozen=True, slots=True)
class SubjectiveSilverResult:
    """Paths and row counts produced by one silver transformation."""

    output_paths: tuple[Path, ...]
    row_counts: dict[str, int]
    quality_report_path: Path


def build_subjective_silver(
    *, bronze_root: Path, silver_root: Path, quality_report_path: Path
) -> SubjectiveSilverResult:
    """Build canonical player, daily, session and event relations from bronze inputs."""
    daily = pl.read_parquet(bronze_root / "daily_metrics.parquet")
    sessions = pl.read_parquet(bronze_root / "training_sessions.parquet")
    events = {
        relation: pl.read_parquet(bronze_root / f"{relation}.parquet")
        for relation in EVENT_RELATIONS
    }
    _require_unique(daily, ["player_id", "observation_date", "metric_name"], "daily metrics")
    _require_expected_metrics(daily)
    _require_unique(sessions, ["player_id", "source_file", "source_record_index"], "sessions")

    training_load_daily = _pivot_daily(daily, TRAINING_LOAD_METRICS).rename(
        {"observation_date": "report_date"}
    )
    wellness_daily = (
        _pivot_daily(daily, WELLNESS_METRICS)
        .rename({"observation_date": "report_date"})
        .with_columns(
            pl.sum_horizontal(
                [pl.col(metric).is_not_null().cast(pl.Int8) for metric in WELLNESS_METRICS]
            ).alias("wellness_metric_count")
        )
        .with_columns((pl.col("wellness_metric_count") > 0).alias("wellness_report_present"))
    )
    silver_sessions = sessions.with_columns(
        pl.struct(["player_id", "source_file", "source_record_index"])
        .map_elements(_session_id, return_dtype=pl.String)
        .alias("session_id")
    ).select(
        "session_id",
        "player_id",
        "team_id",
        "session_date",
        "duration_minutes",
        "rpe",
        "srpe",
        "source_file",
        "source_record_index",
    )
    silver_events = {
        relation: frame.with_columns(
            pl.struct(["event_type", "source_file", "source_row_number"])
            .map_elements(_event_id, return_dtype=pl.String)
            .alias("event_id")
        ).select(
            "event_id",
            "player_id",
            "team_id",
            "event_date",
            "event_type",
            "source_file",
            "source_row_number",
            "source_payload_json",
        )
        for relation, frame in events.items()
    }
    outputs = {
        "player_registry": _build_player_registry(daily, sessions, events),
        "training_load_daily": training_load_daily,
        "wellness_daily": wellness_daily,
        "training_sessions": silver_sessions,
        **silver_events,
    }
    silver_root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for relation, frame in outputs.items():
        output_path = silver_root / f"{relation}.parquet"
        frame.write_parquet(output_path, compression="zstd")
        paths.append(output_path)
    row_counts: dict[str, int] = {relation: frame.height for relation, frame in outputs.items()}
    report = {
        "source": "soccermon-subjective-zenodo-10033832",
        "row_counts": row_counts,
        "wellness": {
            "report_present_rows": wellness_daily.filter(pl.col("wellness_report_present")).height,
            "all_metrics_missing_rows": wellness_daily.filter(
                ~pl.col("wellness_report_present")
            ).height,
        },
        "quality_checks": {
            "daily_primary_key_unique": True,
            "session_source_key_unique": True,
            "event_source_keys_unique": {
                relation: _is_unique(frame, ["source_file", "source_row_number"])
                for relation, frame in events.items()
            },
        },
    }
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return SubjectiveSilverResult(tuple(paths), row_counts, quality_report_path)


def _pivot_daily(daily: pl.DataFrame, metrics: tuple[str, ...]) -> pl.DataFrame:
    return (
        daily.filter(pl.col("metric_name").is_in(metrics))
        .group_by("player_id", "team_id", "observation_date", maintain_order=True)
        .agg(
            [
                pl.col("value").filter(pl.col("metric_name") == metric).first().alias(metric)
                for metric in metrics
            ]
        )
        .sort("player_id", "observation_date")
    )


def _build_player_registry(
    daily: pl.DataFrame, sessions: pl.DataFrame, events: dict[str, pl.DataFrame]
) -> pl.DataFrame:
    observation = daily.group_by("player_id", "team_id").agg(
        pl.min("observation_date").alias("observation_start"),
        pl.max("observation_date").alias("observation_end"),
        pl.n_unique("observation_date").alias("observed_day_count"),
    )
    session_bounds = sessions.group_by("player_id").agg(
        pl.min("session_date").alias("first_session_date"),
        pl.max("session_date").alias("last_session_date"),
        pl.len().alias("session_count"),
    )
    all_events = pl.concat(list(events.values()))
    event_bounds = all_events.group_by("player_id").agg(
        pl.min("event_date").alias("first_event_date"),
        pl.max("event_date").alias("last_event_date"),
        pl.len().alias("event_count"),
    )
    return (
        observation.join(session_bounds, on="player_id", how="left")
        .join(event_bounds, on="player_id", how="left")
        .with_columns(pl.col("session_count", "event_count").fill_null(0))
        .sort("player_id")
    )


def _require_expected_metrics(daily: pl.DataFrame) -> None:
    observed = set(daily.get_column("metric_name").unique().to_list())
    expected = set(TRAINING_LOAD_METRICS) | set(WELLNESS_METRICS)
    if observed != expected:
        raise ValueError(f"Unexpected daily metrics: {sorted(observed ^ expected)}")


def _require_unique(frame: pl.DataFrame, columns: list[str], relation: str) -> None:
    if not _is_unique(frame, columns):
        raise ValueError(f"Duplicate {relation} key: {columns}")


def _is_unique(frame: pl.DataFrame, columns: list[str]) -> bool:
    return frame.group_by(columns).len().filter(pl.col("len") > 1).is_empty()


def _session_id(values: dict[str, object]) -> str:
    return _stable_id("session", values)


def _event_id(values: dict[str, object]) -> str:
    return _stable_id("event", values)


def _stable_id(prefix: str, values: dict[str, object]) -> str:
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:20]}"
