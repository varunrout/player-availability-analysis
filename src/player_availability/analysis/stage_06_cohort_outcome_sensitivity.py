"""Stage 6 cohort and outcome sensitivity analysis."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.outcomes import build_injury_episodes, build_player_day_labels

GAP_RULES = (1, 3, 7)
HORIZONS = (3, 7, 14)
PRIMARY_GAP_DAYS = 3
PRIMARY_HORIZON_DAYS = 7
BURN_IN_DAYS = (0, 28, 56, 90)

SCENARIOS = (
    {
        "scenario_id": "C0",
        "scenario_name": "broad_eligible",
        "scenario_type": "player_day_cohort",
        "rule": "Production horizon eligibility only",
    },
    {
        "scenario_id": "C1",
        "scenario_name": "burn_in_28d",
        "scenario_type": "player_day_cohort",
        "rule": "At least 28 strictly prior calendar days",
    },
    {
        "scenario_id": "C2",
        "scenario_name": "burn_in_56d",
        "scenario_type": "player_day_cohort",
        "rule": "At least 56 strictly prior calendar days",
    },
    {
        "scenario_id": "C3",
        "scenario_name": "burn_in_90d",
        "scenario_type": "player_day_cohort",
        "rule": "At least 90 strictly prior calendar days",
    },
    {
        "scenario_id": "C4",
        "scenario_name": "burn_28d_wellness_7",
        "scenario_type": "player_day_cohort",
        "rule": "28 prior days and at least 7 strictly prior wellness reports",
    },
    {
        "scenario_id": "C5",
        "scenario_name": "robust_load_baseline",
        "scenario_type": "player_day_cohort",
        "rule": "28 prior days, 7 recorded-session days and positive prior load variance",
    },
    {
        "scenario_id": "C6",
        "scenario_name": "isolated_onset_support",
        "scenario_type": "event_support_sensitivity",
        "rule": "Outcome-support audit only; never a prospective cohort filter",
    },
    {
        "scenario_id": "C7",
        "scenario_name": "combined_history_subset",
        "scenario_type": "player_day_cohort",
        "rule": "Robust load baseline and at least 7 strictly prior wellness reports",
    },
)


@dataclass(frozen=True, slots=True)
class Stage06CohortOutcomeResult:
    """Retained Stage 6 tables and summary values."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_06_from_gcp(*, project_id: str, data_bucket: str) -> Stage06CohortOutcomeResult:
    """Load compact canonical products from GCS and execute Stage 6."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "injury_reports": f"silver/{SOURCE_PREFIX}/injury_reports.parquet",
        "player_registry": f"silver/{SOURCE_PREFIX}/player_registry.parquet",
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
    }
    frames = {
        name: pl.read_parquet(BytesIO(bucket.blob(path).download_as_bytes()))
        for name, path in paths.items()
    }
    return run_stage_06_cohort_outcome_sensitivity(**frames)


def run_stage_06_cohort_outcome_sensitivity(
    *,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    features: pl.DataFrame,
) -> Stage06CohortOutcomeResult:
    """Compare outcome and prediction-time cohort choices without fitting a model."""
    history = _build_strict_prior_history(features)
    episodes_by_gap = {
        gap: build_injury_episodes(injury_reports, gap_days=gap) for gap in GAP_RULES
    }
    labels_by_gap = {
        gap: build_player_day_labels(
            player_registry,
            episodes,
            horizons_days=HORIZONS,
        ).join(history, on=["player_id", "team_id", "prediction_date"], how="left")
        for gap, episodes in episodes_by_gap.items()
    }
    primary_labels = labels_by_gap[PRIMARY_GAP_DAYS]
    primary_episodes = episodes_by_gap[PRIMARY_GAP_DAYS]

    scenario_registry = pl.DataFrame(SCENARIOS)
    episode_gap_horizon_summary = _episode_gap_horizon_summary(labels_by_gap, episodes_by_gap)
    cohort_scenario_summary = _cohort_scenario_summary(primary_labels, primary_episodes)
    cohort_waterfall = _cohort_waterfall(primary_labels, primary_episodes)
    history_availability = _history_availability(primary_labels, primary_episodes)
    player_representation = _player_representation(
        primary_labels, primary_episodes, player_registry
    )
    team_representation = _team_representation(player_representation)
    temporal_coverage = _temporal_coverage(primary_labels)
    event_overlap_sensitivity = _event_overlap_sensitivity(episodes_by_gap)
    event_concentration = _event_concentration(primary_labels, primary_episodes)
    recommendation_candidates = _recommendation_candidates()
    findings = _integrity_findings(
        features=features,
        labels_by_gap=labels_by_gap,
        episodes_by_gap=episodes_by_gap,
        scenario_summary=cohort_scenario_summary,
        scenario_registry=scenario_registry,
        player_representation=player_representation,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "scenario_registry": scenario_registry,
        "episode_gap_horizon_summary": episode_gap_horizon_summary,
        "cohort_scenario_summary": cohort_scenario_summary,
        "cohort_waterfall": cohort_waterfall,
        "history_availability": history_availability,
        "player_representation": player_representation,
        "team_representation": team_representation,
        "temporal_coverage": temporal_coverage,
        "event_overlap_sensitivity": event_overlap_sensitivity,
        "event_concentration": event_concentration,
        "recommendation_candidates": recommendation_candidates,
        "cohort_outcome_findings": findings,
        "_history": history,
    }
    broad = cohort_scenario_summary.filter(pl.col("scenario_id") == "C0").row(0, named=True)
    return Stage06CohortOutcomeResult(
        tables=tables,
        summary={
            "stage": "06_cohort_outcome_sensitivity",
            "status": "PASS" if failures == 0 else "FAIL",
            "player_day_count": features.height,
            "player_count": features["player_id"].n_unique(),
            "gap_rule_count": len(GAP_RULES),
            "horizon_count": len(HORIZONS),
            "scenario_count": len(SCENARIOS),
            "broad_eligible_player_days": broad["eligible_player_days"],
            "broad_positive_player_days": broad["positive_player_days"],
            "broad_represented_onsets": broad["represented_onset_count"],
            "model_count": 0,
            "split_count": 0,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_06_figures(result: Stage06CohortOutcomeResult) -> dict[str, Figure]:
    """Build Stage 6 figures from retained tables."""
    figures: dict[str, Figure] = {}
    gap_horizon = result.tables["episode_gap_horizon_summary"]

    by_gap = gap_horizon.filter(pl.col("horizon_days") == PRIMARY_HORIZON_DAYS).sort("gap_days")
    fig, axis = plt.subplots(figsize=(9, 5))
    x = list(range(by_gap.height))
    axis.bar(
        [value - 0.18 for value in x],
        by_gap["distinct_onset_count"],
        0.36,
        label="All onsets",
        color="#287271",
    )
    axis.bar(
        [value + 0.18 for value in x],
        by_gap["represented_onset_count"],
        0.36,
        label="Represented onsets",
        color="#E76F51",
    )
    axis.set_xticks(x, [f"{gap} day" for gap in by_gap["gap_days"]])
    axis.set_ylabel("Distinct player-date onsets")
    axis.set_title("Outcome support by episode-gap rule")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["episode_gap_onset_support"] = fig

    primary_gap = gap_horizon.filter(pl.col("gap_days") == PRIMARY_GAP_DAYS).sort("horizon_days")
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.bar(
        [str(value) for value in primary_gap["horizon_days"]],
        primary_gap["eligible_prevalence"],
        color=["#287271", "#E9C46A", "#E76F51"],
    )
    axis.set_xlabel("Prediction horizon (days)")
    axis.set_ylabel("Positive share of eligible player-days")
    axis.set_title("Primary-gap outcome prevalence")
    fig.tight_layout()
    figures["horizon_prevalence"] = fig

    scenarios = result.tables["cohort_scenario_summary"]
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(scenarios["scenario_id"], scenarios["eligible_player_days"], color="#287271")
    axis.set_xlabel("Cohort scenario")
    axis.set_ylabel("Eligible player-days")
    axis.set_title("Player-day retention by cohort scenario")
    fig.tight_layout()
    figures["cohort_eligible_days"] = fig

    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(scenarios["scenario_id"], scenarios["represented_onset_count"], color="#E76F51")
    axis.set_xlabel("Cohort scenario")
    axis.set_ylabel("Represented player-date onsets")
    axis.set_title("Outcome support retained by cohort scenario")
    fig.tight_layout()
    figures["cohort_onset_support"] = fig

    history = result.tables["history_availability"]
    label_prefixes = {
        "calendar_burn_in": "Burn-in",
        "prior_wellness_total": "Prior wellness total",
        "prior_28d_wellness": "Prior-28d wellness",
        "robust_load_baseline": "Robust load baseline",
    }
    labels = [
        f"{label_prefixes[str(row['history_dimension'])]} {row['threshold']}"
        for row in history.to_dicts()
    ]
    y = list(range(history.height))
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=True, squeeze=False)
    axes[0, 0].barh(y, history["eligible_player_days"], color="#457B9D")
    axes[0, 0].set_yticks(y, labels)
    axes[0, 0].set_xlabel("Eligible player-days")
    axes[0, 0].invert_yaxis()
    axes[0, 1].barh(y, history["represented_onset_count"], color="#E9C46A")
    axes[0, 1].set_xlabel("Represented onsets")
    fig.suptitle("History requirement trade-offs")
    fig.tight_layout()
    figures["history_requirement_tradeoffs"] = fig

    player = result.tables["player_representation"]
    player_counts = (
        player.group_by("scenario_id")
        .agg(
            (pl.col("eligible_player_days") > 0).sum().alias("retained_players"),
            (pl.col("represented_onset_count") > 0).sum().alias("event_players"),
        )
        .sort("scenario_id")
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    x = list(range(player_counts.height))
    axis.bar(
        [value - 0.18 for value in x],
        player_counts["retained_players"],
        0.36,
        label="Retained players",
        color="#287271",
    )
    axis.bar(
        [value + 0.18 for value in x],
        player_counts["event_players"],
        0.36,
        label="Players with represented onsets",
        color="#E76F51",
    )
    axis.set_xticks(x, player_counts["scenario_id"])
    axis.set_title("Player representation by cohort")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["player_retention"] = fig

    team = result.tables["team_representation"].sort("scenario_id", "team_id")
    fig, axis = plt.subplots(figsize=(10, 5))
    for team_id in team["team_id"].unique(maintain_order=True):
        rows = team.filter(pl.col("team_id") == team_id)
        axis.plot(
            rows["scenario_id"],
            rows["eligible_player_days"],
            marker="o",
            label=str(team_id),
        )
    axis.set_ylabel("Eligible player-days")
    axis.set_title("Team representation by cohort")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["team_cohort_representation"] = fig

    concentration = result.tables["event_concentration"].sort("rank")
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(concentration["rank"], concentration["represented_onset_count"], color="#E76F51")
    axis.set_xlabel("Anonymised player rank")
    axis.set_ylabel("Represented onset dates")
    axis.set_title("Primary-cohort event concentration")
    fig.tight_layout()
    figures["primary_event_concentration"] = fig

    temporal = result.tables["temporal_coverage"].filter(pl.col("scenario_id") == "C0")
    fig, axis = plt.subplots(figsize=(11, 5))
    for team_id in temporal["team_id"].unique(maintain_order=True):
        rows = temporal.filter(pl.col("team_id") == team_id).sort("month")
        axis.plot(rows["month"], rows["positive_player_days"], marker="o", label=str(team_id))
    axis.set_ylabel("Positive player-days")
    axis.set_title("Broad-cohort positive support over time")
    axis.tick_params(axis="x", rotation=45)
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["temporal_positive_support"] = fig
    return figures


def write_stage_06_outputs(result: Stage06CohortOutcomeResult, output_root: Path) -> None:
    """Persist canonical Stage 6 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_06_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_06_COHORT_OUTCOME_SENSITIVITY.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_06_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_strict_prior_history(features: pl.DataFrame) -> pl.DataFrame:
    required = {
        "player_id",
        "team_id",
        "prediction_date",
        "wellness_report_present",
        "session_count",
        "daily_load",
    }
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Missing Stage 6 feature columns: {missing}")
    rows: list[dict[str, object]] = []
    for player_key, group in features.sort("player_id", "prediction_date").group_by(
        "player_id", maintain_order=True
    ):
        player_id = str(player_key[0])
        reports: list[int] = []
        prior_recorded_sessions = 0
        load_count = 0
        load_sum = 0.0
        load_sum_squares = 0.0
        for index, source in enumerate(group.iter_rows(named=True)):
            variance = None
            if load_count > 1:
                numerator = load_sum_squares - (load_sum * load_sum / load_count)
                variance = max(numerator / (load_count - 1), 0.0)
            prior_std = math.sqrt(variance) if variance is not None else None
            rows.append(
                {
                    "player_id": player_id,
                    "team_id": source["team_id"],
                    "prediction_date": source["prediction_date"],
                    "prior_calendar_days": index,
                    "prior_wellness_reports_total": sum(reports),
                    "prior_wellness_reports_28d": sum(reports[-28:]),
                    "prior_recorded_session_days": prior_recorded_sessions,
                    "daily_load_prior_std": prior_std,
                    "robust_load_baseline_eligible": (
                        index >= 28
                        and prior_recorded_sessions >= 7
                        and prior_std is not None
                        and prior_std > 0
                    ),
                }
            )
            reports.append(int(bool(source["wellness_report_present"])))
            prior_recorded_sessions += int(int(source["session_count"]) > 0)
            load = float(source["daily_load"])
            load_count += 1
            load_sum += load
            load_sum_squares += load * load
    return pl.DataFrame(rows).sort("player_id", "prediction_date")


def _scenario_mask(scenario_id: str) -> pl.Expr:
    if scenario_id == "C0":
        return pl.lit(True)
    if scenario_id == "C1":
        return pl.col("prior_calendar_days") >= 28
    if scenario_id == "C2":
        return pl.col("prior_calendar_days") >= 56
    if scenario_id == "C3":
        return pl.col("prior_calendar_days") >= 90
    if scenario_id == "C4":
        return (pl.col("prior_calendar_days") >= 28) & (pl.col("prior_wellness_reports_total") >= 7)
    if scenario_id == "C5":
        return pl.col("robust_load_baseline_eligible")
    if scenario_id == "C7":
        return pl.col("robust_load_baseline_eligible") & (
            pl.col("prior_wellness_reports_total") >= 7
        )
    raise ValueError(f"Scenario {scenario_id} is not a prospective player-day cohort")


def _episode_gap_horizon_summary(
    labels_by_gap: dict[int, pl.DataFrame], episodes_by_gap: dict[int, pl.DataFrame]
) -> pl.DataFrame:
    rows = []
    for gap in GAP_RULES:
        labels = labels_by_gap[gap]
        episodes = episodes_by_gap[gap]
        distinct_onsets = episodes.select("player_id", "episode_start").unique()
        for horizon in HORIZONS:
            eligible = labels.filter(pl.col(f"eligible_new_onset_{horizon}d"))
            positive = eligible.filter(pl.col(f"injury_next_{horizon}d"))
            represented = _represented_onsets(eligible, distinct_onsets, horizon)
            rows.append(
                {
                    "gap_days": gap,
                    "horizon_days": horizon,
                    "location_episode_count": episodes.height,
                    "distinct_onset_count": distinct_onsets.height,
                    "eligible_player_days": eligible.height,
                    "positive_player_days": positive.height,
                    "eligible_prevalence": positive.height / eligible.height,
                    "represented_onset_count": represented.height,
                    "represented_event_player_count": represented["player_id"].n_unique(),
                    "right_censored_player_days": labels.filter(
                        ~pl.col(f"label_complete_{horizon}d")
                    ).height,
                    "active_episode_player_days": labels.filter(
                        pl.col(f"label_complete_{horizon}d") & pl.col("active_injury_episode")
                    ).height,
                }
            )
    return pl.DataFrame(rows).sort("gap_days", "horizon_days")


def _cohort_scenario_summary(labels: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    onset_dates = episodes.select("player_id", "episode_start").unique()
    rows = []
    for scenario in SCENARIOS:
        scenario_id = str(scenario["scenario_id"])
        if scenario["scenario_type"] != "player_day_cohort":
            continue
        eligible = labels.filter(
            pl.col(f"eligible_new_onset_{PRIMARY_HORIZON_DAYS}d") & _scenario_mask(scenario_id)
        )
        positive = eligible.filter(pl.col(f"injury_next_{PRIMARY_HORIZON_DAYS}d"))
        represented = _represented_onsets(eligible, onset_dates, PRIMARY_HORIZON_DAYS)
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": scenario["scenario_name"],
                "eligible_player_days": eligible.height,
                "retained_player_count": eligible["player_id"].n_unique(),
                "retained_team_count": eligible["team_id"].n_unique(),
                "positive_player_days": positive.height,
                "eligible_prevalence": positive.height / eligible.height,
                "represented_onset_count": represented.height,
                "represented_event_player_count": represented["player_id"].n_unique(),
                "first_prediction_date": eligible["prediction_date"].min(),
                "last_prediction_date": eligible["prediction_date"].max(),
            }
        )
    return pl.DataFrame(rows).sort("scenario_id")


def _cohort_waterfall(labels: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    onset_dates = episodes.select("player_id", "episode_start").unique()
    steps = (
        ("all player-days", pl.lit(True)),
        ("complete 7-day horizon", pl.col("label_complete_7d")),
        ("new-onset eligible", pl.col("eligible_new_onset_7d")),
        (
            "28-day burn-in",
            pl.col("eligible_new_onset_7d") & (pl.col("prior_calendar_days") >= 28),
        ),
        (
            "7 prior wellness reports",
            pl.col("eligible_new_onset_7d")
            & (pl.col("prior_calendar_days") >= 28)
            & (pl.col("prior_wellness_reports_total") >= 7),
        ),
        (
            "combined robust history",
            pl.col("eligible_new_onset_7d") & _scenario_mask("C7"),
        ),
    )
    rows = []
    previous = labels.height
    for rank, (step, mask) in enumerate(steps, start=1):
        cohort = labels.filter(mask)
        represented = _represented_onsets(cohort, onset_dates, PRIMARY_HORIZON_DAYS)
        rows.append(
            {
                "step_rank": rank,
                "step": step,
                "player_days": cohort.height,
                "excluded_from_previous": previous - cohort.height,
                "player_count": cohort["player_id"].n_unique(),
                "represented_onset_count": represented.height,
            }
        )
        previous = cohort.height
    return pl.DataFrame(rows)


def _history_availability(labels: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    onset_dates = episodes.select("player_id", "episode_start").unique()
    base = pl.col("eligible_new_onset_7d")
    rules: list[tuple[str, str, pl.Expr]] = [
        ("calendar_burn_in", str(days), pl.col("prior_calendar_days") >= days)
        for days in BURN_IN_DAYS
    ]
    rules.extend(
        ("prior_wellness_total", str(count), pl.col("prior_wellness_reports_total") >= count)
        for count in (1, 7)
    )
    rules.extend(
        (
            "prior_28d_wellness",
            str(count),
            pl.col("prior_wellness_reports_28d") >= count,
        )
        for count in (1, 7, 14)
    )
    rules.append(
        (
            "robust_load_baseline",
            "eligible",
            pl.col("robust_load_baseline_eligible"),
        )
    )
    rows = []
    for dimension, threshold, rule in rules:
        cohort = labels.filter(base & rule)
        positive = cohort.filter(pl.col("injury_next_7d"))
        represented = _represented_onsets(cohort, onset_dates, 7)
        rows.append(
            {
                "history_dimension": dimension,
                "threshold": threshold,
                "eligible_player_days": cohort.height,
                "retained_player_count": cohort["player_id"].n_unique(),
                "positive_player_days": positive.height,
                "represented_onset_count": represented.height,
                "represented_event_player_count": represented["player_id"].n_unique(),
            }
        )
    return pl.DataFrame(rows)


def _player_representation(
    labels: pl.DataFrame, episodes: pl.DataFrame, registry: pl.DataFrame
) -> pl.DataFrame:
    onset_dates = episodes.select("player_id", "episode_start").unique()
    players = registry.select("player_id", "team_id").unique()
    outputs = []
    for scenario in SCENARIOS:
        scenario_id = str(scenario["scenario_id"])
        if scenario["scenario_type"] != "player_day_cohort":
            continue
        eligible = labels.filter(pl.col("eligible_new_onset_7d") & _scenario_mask(scenario_id))
        represented = _represented_onsets(eligible, onset_dates, 7)
        counts = eligible.group_by("player_id", "team_id").agg(
            pl.len().alias("eligible_player_days"),
            pl.col("injury_next_7d").sum().alias("positive_player_days"),
        )
        onset_counts = represented.group_by("player_id").len(name="represented_onset_count")
        outputs.append(
            players.join(counts, on=["player_id", "team_id"], how="left")
            .join(onset_counts, on="player_id", how="left")
            .with_columns(
                pl.col("eligible_player_days").fill_null(0),
                pl.col("positive_player_days").fill_null(0),
                pl.col("represented_onset_count").fill_null(0),
                pl.lit(scenario_id).alias("scenario_id"),
            )
        )
    return (
        pl.concat(outputs)
        .select(
            "scenario_id",
            "player_id",
            "team_id",
            "eligible_player_days",
            "positive_player_days",
            "represented_onset_count",
        )
        .sort("scenario_id", "team_id", "player_id")
    )


def _team_representation(player: pl.DataFrame) -> pl.DataFrame:
    return (
        player.group_by("scenario_id", "team_id")
        .agg(
            pl.sum("eligible_player_days").alias("eligible_player_days"),
            pl.sum("positive_player_days").alias("positive_player_days"),
            pl.sum("represented_onset_count").alias("represented_onset_count"),
            (pl.col("eligible_player_days") > 0).sum().alias("retained_player_count"),
            (pl.col("represented_onset_count") > 0).sum().alias("event_player_count"),
        )
        .sort("scenario_id", "team_id")
    )


def _temporal_coverage(labels: pl.DataFrame) -> pl.DataFrame:
    outputs = []
    for scenario in SCENARIOS:
        scenario_id = str(scenario["scenario_id"])
        if scenario["scenario_type"] != "player_day_cohort":
            continue
        outputs.append(
            labels.filter(pl.col("eligible_new_onset_7d") & _scenario_mask(scenario_id))
            .with_columns(pl.col("prediction_date").dt.truncate("1mo").alias("month"))
            .group_by("month", "team_id")
            .agg(
                pl.len().alias("eligible_player_days"),
                pl.col("injury_next_7d").sum().alias("positive_player_days"),
                pl.n_unique("player_id").alias("player_count"),
            )
            .with_columns(pl.lit(scenario_id).alias("scenario_id"))
        )
    return (
        pl.concat(outputs)
        .select(
            "scenario_id",
            "month",
            "team_id",
            "eligible_player_days",
            "positive_player_days",
            "player_count",
        )
        .sort("scenario_id", "month", "team_id")
    )


def _event_overlap_sensitivity(episodes_by_gap: dict[int, pl.DataFrame]) -> pl.DataFrame:
    rows = []
    for gap, episodes in episodes_by_gap.items():
        onsets = (
            episodes.select("player_id", "episode_start")
            .unique()
            .sort("player_id", "episode_start")
        )
        onset_map: dict[str, list[date]] = {}
        for row in onsets.iter_rows(named=True):
            onset_map.setdefault(str(row["player_id"]), []).append(row["episode_start"])
        overlap_counts = []
        for row in onsets.iter_rows(named=True):
            onset = row["episode_start"]
            assert isinstance(onset, date)
            overlap_counts.append(
                sum(
                    other != onset and abs((other - onset).days) <= 28
                    for other in onset_map[str(row["player_id"])]
                )
            )
        rows.append(
            {
                "gap_days": gap,
                "distinct_onset_count": onsets.height,
                "isolated_onset_count": sum(count == 0 for count in overlap_counts),
                "overlapping_onset_count": sum(count > 0 for count in overlap_counts),
                "maximum_nearby_onset_count": max(overlap_counts, default=0),
            }
        )
    return pl.DataFrame(rows).sort("gap_days")


def _event_concentration(labels: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    eligible = labels.filter(pl.col("eligible_new_onset_7d"))
    onsets = episodes.select("player_id", "episode_start").unique()
    represented = _represented_onsets(eligible, onsets, 7)
    counts = (
        represented.group_by("player_id")
        .len(name="represented_onset_count")
        .sort("represented_onset_count", "player_id", descending=[True, False])
    )
    total = represented.height
    return counts.with_row_index("rank", offset=1).with_columns(
        (pl.col("represented_onset_count") / total).alias("event_share"),
        pl.col("represented_onset_count").cum_sum().truediv(total).alias("cumulative_event_share"),
    )


def _represented_onsets(
    eligible: pl.DataFrame, onset_dates: pl.DataFrame, horizon: int
) -> pl.DataFrame:
    eligible_keys = set(eligible.select("player_id", "prediction_date").iter_rows())
    rows = []
    for onset in onset_dates.iter_rows(named=True):
        onset_date = onset["episode_start"]
        assert isinstance(onset_date, date)
        player_id = onset["player_id"]
        if any(
            (player_id, onset_date - timedelta(days=offset)) in eligible_keys
            for offset in range(1, horizon + 1)
        ):
            rows.append(onset)
    if rows:
        return pl.DataFrame(rows).sort("player_id", "episode_start")
    return onset_dates.head(0)


def _recommendation_candidates() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "dimension": "episode gap",
                "provisional_primary": "3 days",
                "required_secondary": "1 and 7 days",
                "status": "REVIEW",
                "rationale": "Accepted intermediate rule; support sensitivity remains material",
            },
            {
                "dimension": "prediction horizon",
                "provisional_primary": "7 days",
                "required_secondary": "3 and 14 days",
                "status": "REVIEW",
                "rationale": "Balances practitioner lead time with sparse event support",
            },
            {
                "dimension": "burn-in",
                "provisional_primary": "28 prior calendar days",
                "required_secondary": "0, 56 and 90 days",
                "status": "REVIEW",
                "rationale": "Matches the longest compact operational accumulation window",
            },
            {
                "dimension": "wellness history",
                "provisional_primary": "no exclusion",
                "required_secondary": "at least 7 strictly prior reports",
                "status": "REVIEW",
                "rationale": "Avoids selecting a reporting-rich and outcome-concentrated cohort",
            },
            {
                "dimension": "player baseline",
                "provisional_primary": "not required for cohort entry",
                "required_secondary": "robust-load-baseline eligible subset",
                "status": "REVIEW",
                "rationale": "Baseline availability should not silently define the full cohort",
            },
        ]
    )


def _integrity_findings(
    *,
    features: pl.DataFrame,
    labels_by_gap: dict[int, pl.DataFrame],
    episodes_by_gap: dict[int, pl.DataFrame],
    scenario_summary: pl.DataFrame,
    scenario_registry: pl.DataFrame,
    player_representation: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def add(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    rebuilt = labels_by_gap[PRIMARY_GAP_DAYS]
    keys = ["player_id", "team_id", "prediction_date"]
    comparison_columns = [
        *(f"label_complete_{horizon}d" for horizon in HORIZONS),
        *(f"injury_next_{horizon}d" for horizon in HORIZONS),
        *(f"eligible_new_onset_{horizon}d" for horizon in HORIZONS),
        "active_injury_episode",
    ]
    joined = features.select(*keys, *comparison_columns).join(
        rebuilt.select(*keys, *comparison_columns),
        on=keys,
        how="inner",
        suffix="_rebuilt",
    )
    mismatches = sum(
        joined.filter(
            pl.col(column).fill_null(False) != pl.col(f"{column}_rebuilt").fill_null(False)
        ).height
        for column in comparison_columns
    )
    add(
        "primary_label_reproduction",
        "3-day episode rule",
        "PASS" if mismatches == 0 and joined.height == features.height else "FAIL",
        f"{mismatches} field mismatches across {joined.height} rebuilt player-days",
    )
    nesting_violations = 0
    for labels in labels_by_gap.values():
        nesting_violations += labels.filter(
            pl.col("label_complete_14d")
            & (
                (pl.col("injury_next_3d") & ~pl.col("injury_next_7d"))
                | (pl.col("injury_next_7d") & ~pl.col("injury_next_14d"))
            )
        ).height
    add(
        "horizon_nesting",
        "all gap rules",
        "PASS" if nesting_violations == 0 else "FAIL",
        f"{nesting_violations} nested-label violations",
    )
    onset_counts = [
        episodes_by_gap[gap].select("player_id", "episode_start").unique().height
        for gap in GAP_RULES
    ]
    add(
        "gap_support_order",
        "episode sensitivity",
        "PASS" if onset_counts == sorted(onset_counts, reverse=True) else "FAIL",
        f"Distinct onset support by 1/3/7-day gap is {onset_counts}",
    )
    scenario_days = dict(scenario_summary.select("scenario_id", "eligible_player_days").iter_rows())
    nested_ok = (
        scenario_days["C0"] >= scenario_days["C1"] >= scenario_days["C2"] >= scenario_days["C3"]
    )
    add(
        "burn_in_nesting",
        "cohort scenarios",
        "PASS" if nested_ok else "FAIL",
        "0/28/56/90-day burn-in cohorts are monotonically nested",
    )
    c6_type = scenario_registry.filter(pl.col("scenario_id") == "C6").item(0, "scenario_type")
    add(
        "future_outcome_cohort_isolation",
        "isolated-onset sensitivity",
        "PASS" if c6_type == "event_support_sensitivity" else "FAIL",
        "Isolated-onset status is not used as a prospective player-day eligibility filter",
    )
    broad_players = player_representation.filter(
        (pl.col("scenario_id") == "C0") & (pl.col("represented_onset_count") > 0)
    ).sort("represented_onset_count", descending=True)
    top_five_share = float(broad_players.head(5)["represented_onset_count"].sum()) / float(
        broad_players["represented_onset_count"].sum()
    )
    add(
        "event_concentration",
        "primary candidate cohort",
        "REVIEW",
        f"Top five players contribute {top_five_share:.1%} of represented onsets",
    )
    combined = scenario_summary.filter(pl.col("scenario_id") == "C7").row(0, named=True)
    broad = scenario_summary.filter(pl.col("scenario_id") == "C0").row(0, named=True)
    add(
        "combined_history_attrition",
        "history-sensitive cohort",
        "REVIEW",
        "Combined history retains "
        f"{combined['eligible_player_days'] / broad['eligible_player_days']:.1%} "
        f"of broad eligible days and {combined['represented_onset_count']} represented onsets",
    )
    add(
        "non_modelling_boundary",
        "Stage 6",
        "PASS",
        "No model, split, feature ranking or discrimination metric is produced",
    )
    return pl.DataFrame(rows)


def _render_report(result: Stage06CohortOutcomeResult) -> str:
    summary = result.summary
    findings = result.tables["cohort_outcome_findings"]
    recommendations = result.tables["recommendation_candidates"]
    lines = [
        "# Stage 6 - Cohort and Outcome Sensitivity Analysis",
        "",
        "## Automated Status",
        "",
        f"Automated integrity result: **{summary['status']}**. Project-owner review is required "
        "before any cohort or outcome rule is frozen.",
        "",
        "## Scope",
        "",
        f"- Source player-days: `{summary['player_day_count']}` across "
        f"`{summary['player_count']}` players.",
        f"- Episode-gap rules: `{summary['gap_rule_count']}`; prediction horizons: "
        f"`{summary['horizon_count']}`.",
        f"- Registered scenarios: `{summary['scenario_count']}`.",
        f"- Broad primary-candidate support: `{summary['broad_eligible_player_days']}` eligible "
        f"days, `{summary['broad_positive_player_days']}` positive days and "
        f"`{summary['broad_represented_onsets']}` represented onsets.",
        f"- Predictive models fitted: `{summary['model_count']}`; splits created: "
        f"`{summary['split_count']}`.",
        "",
        "## Interpretation Boundaries",
        "",
        "- All history requirements use information strictly before the prediction date.",
        "- Isolated-onset status is an outcome-support sensitivity, never a prospective "
        "cohort filter.",
        "- Scenario comparisons quantify support and representation; they do not optimise "
        "model performance.",
        "- Candidate recommendations remain provisional until project-owner results approval.",
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
            "## Provisional Decision Candidates",
            "",
            "| Dimension | Provisional primary | Required secondary | Status |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {row['dimension']} | {row['provisional_primary']} | "
        f"{row['required_secondary']} | {row['status']} |"
        for row in recommendations.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Gap support](../figures/episode_gap_onset_support.png)",
            "![Horizon prevalence](../figures/horizon_prevalence.png)",
            "![Eligible days](../figures/cohort_eligible_days.png)",
            "![Onset support](../figures/cohort_onset_support.png)",
            "![History trade-offs](../figures/history_requirement_tradeoffs.png)",
            "![Player retention](../figures/player_retention.png)",
            "![Team representation](../figures/team_cohort_representation.png)",
            "![Event concentration](../figures/primary_event_concentration.png)",
            "![Temporal support](../figures/temporal_positive_support.png)",
            "",
            "## Gate",
            "",
            "Approve or revise the primary episode gap, prediction horizon, cohort eligibility, "
            "history requirements and mandatory secondary sensitivities before Stage 7.",
        ]
    )
    return "\n".join(lines) + "\n"
