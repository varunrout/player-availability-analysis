"""Stage 5 retrospective descriptive outcome-context analysis."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from statistics import mean, median
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX

LOOKBACK_DAYS = 28
WINDOWS_DAYS = (3, 7, 14, 28)
REFERENCE_TYPES = ("calendar_reference", "reporting_reference")
BOOTSTRAP_REPLICATES = 500
BOOTSTRAP_SEED = 20260815
CONTEXT_FEATURES = (
    "session_recorded",
    "session_count",
    "daily_load_log1p",
    "session_duration_minutes_log1p",
    "daily_load_sum_7d_log1p",
    "daily_load_sum_28d_log1p",
    "session_duration_sum_7d_log1p",
    "session_duration_sum_28d_log1p",
    "fatigue",
    "readiness",
    "wellness_report_present",
    "wellness_metric_count",
)
PRIMARY_CONTEXT_FEATURES = (
    "session_recorded",
    "session_count",
    "daily_load_log1p",
    "session_duration_minutes_log1p",
    "daily_load_sum_7d_log1p",
    "daily_load_sum_28d_log1p",
    "session_duration_sum_7d_log1p",
    "session_duration_sum_28d_log1p",
)
DESCRIPTIVE_WELLNESS_FEATURES = (
    "fatigue",
    "readiness",
    "wellness_report_present",
    "wellness_metric_count",
)
SOURCE_FEATURES = (
    "session_count",
    "daily_load",
    "session_duration_minutes",
    "daily_load_sum_7d",
    "daily_load_sum_28d",
    "session_duration_sum_7d",
    "session_duration_sum_28d",
    "fatigue",
    "readiness",
    "wellness_report_present",
    "wellness_metric_count",
    "active_injury_episode",
)


@dataclass(frozen=True, slots=True)
class Stage05OutcomeContextResult:
    """Retained Stage 5 descriptive evidence and audit summaries."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_05_from_gcp(*, project_id: str, data_bucket: str) -> Stage05OutcomeContextResult:
    """Load compact gold features and primary episodes from GCS and execute Stage 5."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    features = pl.read_parquet(
        BytesIO(
            bucket.blob(f"gold/{SOURCE_PREFIX}/player_day_features.parquet").download_as_bytes()
        )
    )
    episodes = pl.read_parquet(
        BytesIO(bucket.blob(f"silver/{SOURCE_PREFIX}/injury_episodes.parquet").download_as_bytes())
    )
    return run_stage_05_outcome_context(features=features, episodes=episodes)


def run_stage_05_outcome_context(
    *, features: pl.DataFrame, episodes: pl.DataFrame
) -> Stage05OutcomeContextResult:
    """Describe pre-onset context without fitting or evaluating a predictive model."""
    required_features = {"player_id", "team_id", "prediction_date", *SOURCE_FEATURES}
    missing_features = sorted(required_features - set(features.columns))
    if missing_features:
        raise ValueError(f"Missing Stage 5 feature columns: {missing_features}")
    required_episodes = {"player_id", "team_id", "episode_start", "episode_id"}
    missing_episodes = sorted(required_episodes - set(episodes.columns))
    if missing_episodes:
        raise ValueError(f"Missing Stage 5 episode columns: {missing_episodes}")

    analysis = _build_analysis_frame(features)
    event_reference_register = _event_reference_register(analysis, episodes)
    event_window_audit = _event_window_audit(event_reference_register)
    timeline = _relative_day_timeline(analysis, event_reference_register)
    trajectory_summary = _trajectory_summary(timeline)
    matched_event_differences = _matched_event_differences(timeline)
    matched_difference_summary = _matched_difference_summary(matched_event_differences)
    reporting_process_summary = trajectory_summary.filter(
        pl.col("feature").is_in(DESCRIPTIVE_WELLNESS_FEATURES)
    )
    player_team_contribution = _player_team_contribution(event_reference_register)
    team_difference_summary = _team_difference_summary(matched_event_differences)
    sensitivity_summary = _sensitivity_summary(matched_event_differences, event_reference_register)
    findings = _outcome_context_findings(
        analysis=analysis,
        event_reference_register=event_reference_register,
        timeline=timeline,
        matched_event_differences=matched_event_differences,
        player_team_contribution=player_team_contribution,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    analyzable = event_reference_register.filter(pl.col("history_complete"))
    matched = analyzable.filter(pl.col("calendar_reference_date").is_not_null())
    tables = {
        "event_reference_register": event_reference_register,
        "event_window_audit": event_window_audit,
        "relative_day_trajectory_summary": trajectory_summary,
        "matched_event_differences": matched_event_differences,
        "matched_difference_summary": matched_difference_summary,
        "reporting_process_summary": reporting_process_summary,
        "player_team_contribution": player_team_contribution,
        "team_difference_summary": team_difference_summary,
        "sensitivity_summary": sensitivity_summary,
        "outcome_context_findings": findings,
        "_timeline": timeline,
    }
    return Stage05OutcomeContextResult(
        tables=tables,
        summary={
            "stage": "05_outcome_context",
            "status": "PASS" if failures == 0 else "FAIL",
            "player_day_count": analysis.height,
            "player_count": analysis["player_id"].n_unique(),
            "distinct_onset_count": event_reference_register.height,
            "history_complete_onset_count": analyzable.height,
            "calendar_matched_onset_count": matched.height,
            "isolated_onset_count": analyzable.filter(pl.col("isolated_onset")).height,
            "context_feature_count": len(CONTEXT_FEATURES),
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "model_count": 0,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_05_figures(result: Stage05OutcomeContextResult) -> dict[str, Figure]:
    """Build Stage 5 descriptive figures without writing files."""
    figures: dict[str, Figure] = {}
    audit = result.tables["event_window_audit"]
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.barh(audit["stage"], audit["event_count"], color="#287271")
    axis.set_xlabel("Distinct player-date onsets")
    axis.set_title("Event and reference selection flow")
    fig.tight_layout()
    figures["event_reference_selection_flow"] = fig

    trajectory = result.tables["relative_day_trajectory_summary"]
    figures["daily_load_pre_onset_trajectory"] = _trajectory_figure(
        trajectory, ("daily_load_log1p",), "Daily-load context before onset"
    )
    figures["session_duration_pre_onset_trajectory"] = _trajectory_figure(
        trajectory,
        ("session_duration_minutes_log1p",),
        "Session-duration context before onset",
    )
    figures["accumulated_load_trajectories"] = _trajectory_figure(
        trajectory,
        ("daily_load_sum_7d_log1p", "daily_load_sum_28d_log1p"),
        "Recent and longer accumulated load before onset",
    )

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    _plot_trajectory_axis(axes[0], trajectory, "session_recorded")
    axes[0].set_title("Recorded-session rate")
    _plot_trajectory_axis(axes[1], trajectory, "wellness_report_present")
    axes[1].set_title("Wellness-reporting rate")
    axes[1].set_xlabel("Days relative to anchor")
    fig.suptitle("Recording-process trajectories")
    fig.tight_layout()
    figures["recording_process_trajectories"] = fig

    figures["wellness_observed_trajectories"] = _trajectory_figure(
        trajectory,
        ("fatigue", "readiness"),
        "Observed wellness values before onset (descriptive only)",
    )

    team = result.tables["team_difference_summary"].filter(
        (pl.col("reference_type") == "calendar_reference")
        & (pl.col("window_days") == 7)
        & pl.col("feature").is_in(("daily_load_log1p", "session_duration_minutes_log1p"))
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    labels = [f"{row['team_id']} | {row['feature']}" for row in team.iter_rows(named=True)]
    axis.barh(labels, team["mean_difference"], color="#E9C46A")
    axis.axvline(0, color="#264653", linewidth=1)
    axis.set_xlabel("Event minus same-player calendar reference")
    axis.set_title("Seven-day matched differences by team")
    fig.tight_layout()
    figures["team_stratified_differences"] = fig

    players = result.tables["player_team_contribution"].filter(
        (pl.col("scope") == "player") & (pl.col("matched_count") > 0)
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(players["rank"], players["matched_count"], color="#E76F51")
    axis.set_xlabel("Anonymised player rank")
    axis.set_ylabel("Matched onset dates")
    axis.set_title("Stage 5 matched-event contribution by player")
    fig.tight_layout()
    figures["player_event_concentration"] = fig

    sensitivity = result.tables["sensitivity_summary"].filter(
        (pl.col("feature") == "daily_load_log1p") & (pl.col("window_days") == 7)
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    y = list(range(sensitivity.height))
    axis.errorbar(
        sensitivity["player_equal_mean_difference"],
        y,
        xerr=[
            (sensitivity["player_equal_mean_difference"] - sensitivity["cluster_ci_low"]).to_list(),
            (
                sensitivity["cluster_ci_high"] - sensitivity["player_equal_mean_difference"]
            ).to_list(),
        ],
        fmt="o",
        color="#287271",
        capsize=3,
    )
    axis.set_yticks(y, sensitivity["sensitivity_scope"])
    axis.axvline(0, color="#264653", linewidth=1)
    axis.set_xlabel("Player-equal event minus calendar-reference difference")
    axis.set_title("Seven-day daily-load sensitivity")
    fig.tight_layout()
    figures["event_concentration_sensitivity"] = fig
    return figures


def write_stage_05_outputs(result: Stage05OutcomeContextResult, output_root: Path) -> None:
    """Persist canonical Stage 5 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_05_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_05_OUTCOME_CONTEXT.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_05_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_analysis_frame(features: pl.DataFrame) -> pl.DataFrame:
    return features.select(
        "player_id",
        "team_id",
        "prediction_date",
        "active_injury_episode",
        pl.col("session_count").cast(pl.Float64),
        (pl.col("session_count") > 0).cast(pl.Float64).alias("session_recorded"),
        pl.col("daily_load").log1p().alias("daily_load_log1p"),
        pl.col("session_duration_minutes").log1p().alias("session_duration_minutes_log1p"),
        pl.col("daily_load_sum_7d").log1p().alias("daily_load_sum_7d_log1p"),
        pl.col("daily_load_sum_28d").log1p().alias("daily_load_sum_28d_log1p"),
        pl.col("session_duration_sum_7d").log1p().alias("session_duration_sum_7d_log1p"),
        pl.col("session_duration_sum_28d").log1p().alias("session_duration_sum_28d_log1p"),
        pl.col("fatigue").cast(pl.Float64),
        pl.col("readiness").cast(pl.Float64),
        pl.col("wellness_report_present").cast(pl.Float64),
        pl.col("wellness_metric_count").cast(pl.Float64),
    ).sort("player_id", "prediction_date")


def _event_reference_register(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    onsets = (
        episodes.group_by("player_id", "team_id", "episode_start")
        .agg(
            pl.len().alias("location_episode_count"),
            pl.col("episode_id").sort().str.join(";").alias("episode_ids"),
        )
        .sort("player_id", "episode_start")
    )
    rows_by_key = {
        (str(row["player_id"]), row["prediction_date"]): row for row in features.to_dicts()
    }
    dates_by_player = {
        str(player_id[0]): [row["prediction_date"] for row in group.to_dicts()]
        for player_id, group in features.group_by("player_id", maintain_order=True)
    }
    onsets_by_player: dict[str, set[date]] = {}
    for row in onsets.iter_rows(named=True):
        onsets_by_player.setdefault(str(row["player_id"]), set()).add(row["episode_start"])

    rows = []
    for onset in onsets.iter_rows(named=True):
        player_id = str(onset["player_id"])
        onset_date = onset["episode_start"]
        assert isinstance(onset_date, date)
        player_dates = dates_by_player[player_id]
        player_onsets = onsets_by_player[player_id]
        history_complete = _window_complete(rows_by_key, player_id, onset_date, include_anchor=True)
        nearby_onsets = sorted(
            other
            for other in player_onsets
            if other != onset_date and abs((other - onset_date).days) <= LOOKBACK_DAYS
        )
        event_reporting_count = _prior_reporting_count(rows_by_key, player_id, onset_date)
        candidates = (
            [
                candidate
                for candidate in player_dates
                if _valid_reference(
                    rows_by_key=rows_by_key,
                    player_id=player_id,
                    anchor_date=candidate,
                    onset_dates=player_onsets,
                )
            ]
            if history_complete
            else []
        )
        calendar_reference = min(
            candidates,
            key=lambda candidate: (
                candidate.weekday() != onset_date.weekday(),
                candidate.month != onset_date.month,
                abs((candidate - onset_date).days),
                candidate,
            ),
            default=None,
        )
        reporting_reference = min(
            candidates,
            key=lambda candidate: (
                abs(
                    _prior_reporting_count(rows_by_key, player_id, candidate)
                    - event_reporting_count
                ),
                candidate.weekday() != onset_date.weekday(),
                candidate.month != onset_date.month,
                abs((candidate - onset_date).days),
                candidate,
            ),
            default=None,
        )
        rows.append(
            {
                "event_id": f"{player_id}|{onset_date.isoformat()}",
                "player_id": player_id,
                "team_id": onset["team_id"],
                "onset_date": onset_date,
                "location_episode_count": onset["location_episode_count"],
                "episode_ids": onset["episode_ids"],
                "history_complete": history_complete,
                "nearby_onset_count_28d": len(nearby_onsets),
                "isolated_onset": len(nearby_onsets) == 0,
                "candidate_reference_count": len(candidates),
                "event_prior_7d_reporting_count": event_reporting_count,
                "calendar_reference_date": calendar_reference,
                "calendar_reference_day_distance": (
                    abs((calendar_reference - onset_date).days)
                    if calendar_reference is not None
                    else None
                ),
                "reporting_reference_date": reporting_reference,
                "reporting_reference_prior_7d_count": (
                    _prior_reporting_count(rows_by_key, player_id, reporting_reference)
                    if reporting_reference is not None
                    else None
                ),
            }
        )
    return pl.DataFrame(rows).sort("player_id", "onset_date")


def _window_complete(
    rows_by_key: dict[tuple[str, date], dict[str, Any]],
    player_id: str,
    anchor_date: date,
    *,
    include_anchor: bool,
) -> bool:
    end = 0 if include_anchor else -1
    return all(
        (player_id, anchor_date + timedelta(days=offset)) in rows_by_key
        for offset in range(-LOOKBACK_DAYS, end + 1)
    )


def _valid_reference(
    *,
    rows_by_key: dict[tuple[str, date], dict[str, Any]],
    player_id: str,
    anchor_date: date,
    onset_dates: set[date],
) -> bool:
    if not _window_complete(rows_by_key, player_id, anchor_date, include_anchor=True):
        return False
    window_dates = [anchor_date + timedelta(days=offset) for offset in range(-LOOKBACK_DAYS, 1)]
    if any(
        any(abs((day - onset).days) <= LOOKBACK_DAYS for onset in onset_dates)
        for day in window_dates
    ):
        return False
    return not any(
        bool(rows_by_key[(player_id, day)]["active_injury_episode"]) for day in window_dates
    )


def _prior_reporting_count(
    rows_by_key: dict[tuple[str, date], dict[str, Any]], player_id: str, anchor_date: date
) -> int:
    return sum(
        bool(
            rows_by_key.get((player_id, anchor_date + timedelta(days=offset)), {}).get(
                "wellness_report_present", False
            )
        )
        for offset in range(-7, 0)
    )


def _event_window_audit(register: pl.DataFrame) -> pl.DataFrame:
    total = register.height
    history = register.filter(pl.col("history_complete")).height
    matched = register.filter(pl.col("calendar_reference_date").is_not_null()).height
    reporting_matched = register.filter(pl.col("reporting_reference_date").is_not_null()).height
    isolated = register.filter(pl.col("history_complete") & pl.col("isolated_onset")).height
    return pl.DataFrame(
        {
            "stage": [
                "distinct onsets",
                "complete -28..0 history",
                "calendar reference available",
                "reporting reference available",
                "isolated onset sensitivity",
            ],
            "event_count": [total, history, matched, reporting_matched, isolated],
            "excluded_from_previous": [
                0,
                total - history,
                history - matched,
                history - reporting_matched,
                history - isolated,
            ],
        }
    )


def _relative_day_timeline(features: pl.DataFrame, register: pl.DataFrame) -> pl.DataFrame:
    lookup = {(str(row["player_id"]), row["prediction_date"]): row for row in features.to_dicts()}
    rows: list[dict[str, object]] = []
    for event in register.filter(pl.col("history_complete")).iter_rows(named=True):
        anchors = [("event", event["onset_date"])]
        anchors.extend(
            (reference_type, event[f"{reference_type}_date"]) for reference_type in REFERENCE_TYPES
        )
        for index_type, anchor_date in anchors:
            if anchor_date is None:
                continue
            assert isinstance(anchor_date, date)
            for relative_day in range(-LOOKBACK_DAYS, 1):
                observation_date = anchor_date + timedelta(days=relative_day)
                source = lookup[(str(event["player_id"]), observation_date)]
                for feature in CONTEXT_FEATURES:
                    rows.append(
                        {
                            "event_id": event["event_id"],
                            "player_id": event["player_id"],
                            "team_id": event["team_id"],
                            "onset_date": event["onset_date"],
                            "index_type": index_type,
                            "anchor_date": anchor_date,
                            "relative_day": relative_day,
                            "observation_date": observation_date,
                            "feature": feature,
                            "value": source[feature],
                            "primary_pre_onset": relative_day < 0,
                        }
                    )
    return pl.DataFrame(rows).sort("event_id", "index_type", "relative_day", "feature")


def _trajectory_summary(timeline: pl.DataFrame) -> pl.DataFrame:
    observed = timeline.filter(pl.col("value").is_not_null())
    ordinary = observed.group_by("index_type", "relative_day", "feature").agg(
        pl.len().alias("observed_count"),
        pl.n_unique("event_id").alias("anchor_count"),
        pl.n_unique("player_id").alias("player_count"),
        pl.mean("value").alias("event_weighted_mean"),
        pl.median("value").alias("median"),
    )
    player_means = observed.group_by("index_type", "relative_day", "feature", "player_id").agg(
        pl.mean("value").alias("player_mean")
    )
    player_equal = player_means.group_by("index_type", "relative_day", "feature").agg(
        pl.mean("player_mean").alias("player_equal_mean")
    )
    return ordinary.join(
        player_equal, on=["index_type", "relative_day", "feature"], how="left"
    ).sort("feature", "index_type", "relative_day")


def _matched_event_differences(timeline: pl.DataFrame) -> pl.DataFrame:
    pre = timeline.filter(pl.col("relative_day") < 0)
    rows: list[dict[str, object]] = []
    grouped = {
        (str(event_id), str(index_type), str(feature)): group
        for (event_id, index_type, feature), group in pre.group_by(
            "event_id", "index_type", "feature", maintain_order=True
        )
    }
    event_metadata = pre.select("event_id", "player_id", "team_id").unique()
    metadata_lookup = {str(row["event_id"]): row for row in event_metadata.to_dicts()}
    for event_id in sorted(metadata_lookup):
        for reference_type in REFERENCE_TYPES:
            for feature in CONTEXT_FEATURES:
                event_group = grouped.get((event_id, "event", feature))
                reference_group = grouped.get((event_id, reference_type, feature))
                if event_group is None or reference_group is None:
                    continue
                for window in WINDOWS_DAYS:
                    event_values = _window_values(event_group, window)
                    reference_values = _window_values(reference_group, window)
                    if not event_values or not reference_values:
                        continue
                    event_mean = mean(event_values)
                    reference_mean = mean(reference_values)
                    rows.append(
                        {
                            "event_id": event_id,
                            "player_id": metadata_lookup[event_id]["player_id"],
                            "team_id": metadata_lookup[event_id]["team_id"],
                            "reference_type": reference_type,
                            "feature": feature,
                            "window_days": window,
                            "event_observed_days": len(event_values),
                            "reference_observed_days": len(reference_values),
                            "event_mean": event_mean,
                            "reference_mean": reference_mean,
                            "difference": event_mean - reference_mean,
                        }
                    )
    return pl.DataFrame(rows).sort("feature", "reference_type", "window_days", "event_id")


def _window_values(group: pl.DataFrame, window: int) -> list[float]:
    return [
        float(value)
        for value in group.filter(pl.col("relative_day") >= -window)["value"].drop_nulls().to_list()
    ]


def _matched_difference_summary(differences: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for key, group in differences.group_by(
        "reference_type", "feature", "window_days", maintain_order=True
    ):
        reference_type, feature, window_days = key
        values = [float(value) for value in group["difference"].to_list()]
        player_means = _player_means(group)
        lower, upper = _cluster_bootstrap_interval(player_means)
        rows.append(
            {
                "reference_type": reference_type,
                "feature": feature,
                "window_days": window_days,
                "matched_event_count": group["event_id"].n_unique(),
                "player_count": group["player_id"].n_unique(),
                "event_weighted_mean_difference": mean(values),
                "median_difference": median(values),
                "player_equal_mean_difference": mean(player_means.values()),
                "cluster_ci_low": lower,
                "cluster_ci_high": upper,
            }
        )
    return pl.DataFrame(rows).sort("feature", "reference_type", "window_days")


def _player_means(group: pl.DataFrame) -> dict[str, float]:
    player_means: dict[str, float] = {}
    for player_id, player_group in group.group_by("player_id", maintain_order=True):
        difference_mean = player_group["difference"].mean()
        if not isinstance(difference_mean, (int, float)):
            raise TypeError("Expected a numeric matched-difference mean")
        player_means[str(player_id[0])] = float(difference_mean)
    return player_means


def _cluster_bootstrap_interval(player_means: dict[str, float]) -> tuple[float, float]:
    values = list(player_means.values())
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(BOOTSTRAP_SEED + len(values))
    estimates = [mean(rng.choices(values, k=len(values))) for _ in range(BOOTSTRAP_REPLICATES)]
    estimates.sort()
    return (_quantile(estimates, 0.025), _quantile(estimates, 0.975))


def _quantile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + fraction * (values[upper] - values[lower])


def _player_team_contribution(register: pl.DataFrame) -> pl.DataFrame:
    player = (
        register.group_by("player_id", "team_id")
        .agg(
            pl.len().alias("onset_count"),
            pl.col("history_complete").sum().alias("history_complete_count"),
            pl.col("calendar_reference_date").is_not_null().sum().alias("matched_count"),
            pl.col("isolated_onset").sum().alias("isolated_onset_count"),
        )
        .sort("matched_count", "player_id", descending=[True, False])
        .with_row_index("rank", offset=1)
        .with_columns(pl.lit("player").alias("scope"), pl.col("player_id").alias("entity_id"))
    )
    team = (
        register.group_by("team_id")
        .agg(
            pl.len().alias("onset_count"),
            pl.col("history_complete").sum().alias("history_complete_count"),
            pl.col("calendar_reference_date").is_not_null().sum().alias("matched_count"),
            pl.col("isolated_onset").sum().alias("isolated_onset_count"),
        )
        .sort("matched_count", descending=True)
        .with_row_index("rank", offset=1)
        .with_columns(pl.lit("team").alias("scope"), pl.col("team_id").alias("entity_id"))
    )
    columns = (
        "scope",
        "rank",
        "entity_id",
        "team_id",
        "onset_count",
        "history_complete_count",
        "matched_count",
        "isolated_onset_count",
    )
    return pl.concat([player.select(*columns), team.select(*columns)])


def _team_difference_summary(differences: pl.DataFrame) -> pl.DataFrame:
    return (
        differences.group_by("team_id", "reference_type", "feature", "window_days")
        .agg(
            pl.n_unique("event_id").alias("matched_event_count"),
            pl.n_unique("player_id").alias("player_count"),
            pl.mean("difference").alias("mean_difference"),
            pl.median("difference").alias("median_difference"),
        )
        .sort("feature", "reference_type", "window_days", "team_id")
    )


def _sensitivity_summary(differences: pl.DataFrame, register: pl.DataFrame) -> pl.DataFrame:
    player_ranks = (
        register.filter(pl.col("calendar_reference_date").is_not_null())
        .group_by("player_id")
        .len(name="matched_count")
        .sort("matched_count", "player_id", descending=[True, False])
        .with_row_index("rank", offset=1)
    )
    top_one = set(player_ranks.head(1)["player_id"].to_list())
    top_five = set(player_ranks.head(5)["player_id"].to_list())
    isolated_events = set(register.filter(pl.col("isolated_onset"))["event_id"].to_list())
    calendar = differences.filter(pl.col("reference_type") == "calendar_reference")
    scopes = {
        "all_matched_events": calendar,
        "isolated_onsets": calendar.filter(pl.col("event_id").is_in(isolated_events)),
        "exclude_top_player": calendar.filter(~pl.col("player_id").is_in(top_one)),
        "exclude_top_five_players": calendar.filter(~pl.col("player_id").is_in(top_five)),
    }
    rows = []
    for scope, frame in scopes.items():
        for key, group in frame.group_by("feature", "window_days", maintain_order=True):
            feature, window_days = key
            player_means = _player_means(group)
            if not player_means:
                continue
            lower, upper = _cluster_bootstrap_interval(player_means)
            rows.append(
                {
                    "sensitivity_scope": scope,
                    "feature": feature,
                    "window_days": window_days,
                    "matched_event_count": group["event_id"].n_unique(),
                    "player_count": len(player_means),
                    "player_equal_mean_difference": mean(player_means.values()),
                    "cluster_ci_low": lower,
                    "cluster_ci_high": upper,
                }
            )
    return pl.DataFrame(rows).sort("feature", "window_days", "sensitivity_scope")


def _outcome_context_findings(
    *,
    analysis: pl.DataFrame,
    event_reference_register: pl.DataFrame,
    timeline: pl.DataFrame,
    matched_event_differences: pl.DataFrame,
    player_team_contribution: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def add(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    prohibited = [
        column
        for column in analysis.columns
        if column.startswith("injury_next_") or column.startswith("label_complete_")
    ]
    add(
        "predictive_label_isolation",
        "analysis frame",
        "PASS" if not prohibited else "FAIL",
        f"{len(prohibited)} fixed-horizon label columns entered feature measurement",
    )
    duplicate_onsets = (
        event_reference_register.select("player_id", "onset_date").is_duplicated().sum()
    )
    add(
        "distinct_onset_index",
        "event register",
        "PASS" if duplicate_onsets == 0 else "FAIL",
        f"{duplicate_onsets} duplicate player-date onsets remain",
    )
    date_violations = timeline.filter(
        pl.col("observation_date")
        != pl.col("anchor_date") + pl.duration(days=pl.col("relative_day"))
    ).height
    add(
        "relative_day_identity",
        "event/reference timeline",
        "PASS" if date_violations == 0 else "FAIL",
        f"{date_violations} relative-day rows have inconsistent dates",
    )
    day_zero_primary = timeline.filter(
        pl.col("primary_pre_onset") & (pl.col("relative_day") >= 0)
    ).height
    add(
        "day_zero_exclusion",
        "primary pre-onset summaries",
        "PASS" if day_zero_primary == 0 else "FAIL",
        f"{day_zero_primary} day-zero/post-anchor rows entered the primary flag",
    )
    eligible_events = event_reference_register.filter(pl.col("history_complete")).height
    matched_events = event_reference_register.filter(
        pl.col("history_complete") & pl.col("calendar_reference_date").is_not_null()
    ).height
    add(
        "reference_availability",
        "same-player references",
        "PASS" if matched_events > 0 else "FAIL",
        f"{matched_events} of {eligible_events} complete-history onsets have clean "
        "calendar references",
    )
    eligible_register = event_reference_register.filter(pl.col("history_complete"))
    add(
        "overlapping_event_windows",
        "event context",
        "REVIEW",
        f"{eligible_register.filter(~pl.col('isolated_onset')).height} complete-history onsets "
        "have another onset within plus/minus 28 days; isolated sensitivity is retained",
    )
    players = player_team_contribution.filter(
        (pl.col("scope") == "player") & (pl.col("matched_count") > 0)
    )
    top_five_share = float(players.head(5)["matched_count"].sum()) / float(
        players["matched_count"].sum()
    )
    add(
        "player_concentration",
        "matched descriptive evidence",
        "REVIEW",
        f"Top five players contribute {top_five_share:.1%} of matched onset dates; "
        "player-equal and "
        "exclusion sensitivities are required",
    )
    reporting_rows = matched_event_differences.filter(
        pl.col("feature") == "wellness_report_present"
    ).height
    add(
        "reporting_process_boundary",
        "wellness context",
        "REVIEW",
        f"{reporting_rows} event-level reporting differences are descriptive-only under DEC-031",
    )
    add(
        "non_predictive_boundary",
        "Stage 5 interpretation",
        "PASS",
        "No model, discrimination metric, feature selection or causal test is performed",
    )
    return pl.DataFrame(rows)


def _trajectory_figure(trajectory: pl.DataFrame, features: tuple[str, ...], title: str) -> Figure:
    fig, axes = plt.subplots(len(features), 1, figsize=(11, 5 * len(features)), squeeze=False)
    for axis, feature in zip(axes.flat, features, strict=True):
        _plot_trajectory_axis(axis, trajectory, feature)
        axis.set_title(feature.replace("_", " "))
        axis.set_xlabel("Days relative to anchor")
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def _plot_trajectory_axis(axis: Any, trajectory: pl.DataFrame, feature: str) -> None:
    colors = {
        "event": "#E76F51",
        "calendar_reference": "#287271",
        "reporting_reference": "#457B9D",
    }
    rows = trajectory.filter(pl.col("feature") == feature).sort("relative_day")
    for index_type in ("event", *REFERENCE_TYPES):
        selected = rows.filter(pl.col("index_type") == index_type)
        axis.plot(
            selected["relative_day"],
            selected["player_equal_mean"],
            label=index_type.replace("_", " "),
            color=colors[index_type],
        )
    axis.axvline(0, color="#264653", linestyle="--", linewidth=1)
    axis.legend(frameon=False)


def _render_report(result: Stage05OutcomeContextResult) -> str:
    summary = result.summary
    findings = result.tables["outcome_context_findings"]
    lines = [
        "# Stage 5 - Descriptive Outcome-Context Analysis",
        "",
        "## Automated Status",
        "",
        f"Automated context-integrity result: **{summary['status']}**. Project-owner review is "
        "required before Stage 6.",
        "",
        "## Scope",
        "",
        f"- Distinct player-date onsets: `{summary['distinct_onset_count']}`.",
        f"- Onsets with complete -28 through day-0 history: "
        f"`{summary['history_complete_onset_count']}`.",
        f"- Onsets with clean same-player calendar references: "
        f"`{summary['calendar_matched_onset_count']}`.",
        f"- Isolated onset sensitivity events: `{summary['isolated_onset_count']}`.",
        f"- Context features: `{summary['context_feature_count']}`.",
        f"- Predictive models fitted: `{summary['model_count']}`.",
        "",
        "## Interpretation Boundaries",
        "",
        "- Primary summaries use relative days -28 through -1; day 0 is shown separately.",
        "- Same-day wellness and reporting remain descriptive-only under DEC-031.",
        "- No-session remains unknown recording/exposure state, not confirmed rest.",
        "- Matched differences are retrospective descriptions, not predictive, causal or "
        "medical evidence.",
        "- Player-cluster bootstrap intervals reflect player concentration but do not solve "
        "limited support.",
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
            "![Selection flow](../figures/event_reference_selection_flow.png)",
            "![Daily load](../figures/daily_load_pre_onset_trajectory.png)",
            "![Session duration](../figures/session_duration_pre_onset_trajectory.png)",
            "![Accumulated load](../figures/accumulated_load_trajectories.png)",
            "![Recording process](../figures/recording_process_trajectories.png)",
            "![Wellness](../figures/wellness_observed_trajectories.png)",
            "![Team differences](../figures/team_stratified_differences.png)",
            "![Player concentration](../figures/player_event_concentration.png)",
            "![Sensitivity](../figures/event_concentration_sensitivity.png)",
            "",
            "## Gate",
            "",
            "Decide which descriptive patterns merit later prospective testing. Stage 5 evidence "
            "must not silently expand the operational feature contract or support causal claims.",
        ]
    )
    return "\n".join(lines) + "\n"
