"""Stage 2 missingness and reporting-process exploratory analysis."""

from __future__ import annotations

import json
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
from player_availability.ingestion.silver import WELLNESS_METRICS

EVENT_WINDOW = tuple(range(-28, 15))


@dataclass(frozen=True, slots=True)
class Stage02MissingnessResult:
    """All retained tables, plot inputs and summary values from one Stage 2 run."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_02_from_gcp(*, project_id: str, data_bucket: str) -> Stage02MissingnessResult:
    """Load compact reporting-process products from GCS and execute Stage 2."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "daily_metrics": f"bronze/{SOURCE_PREFIX}/daily_metrics.parquet",
        "training_load_daily": f"silver/{SOURCE_PREFIX}/training_load_daily.parquet",
        "wellness_daily": f"silver/{SOURCE_PREFIX}/wellness_daily.parquet",
        "training_sessions": f"silver/{SOURCE_PREFIX}/training_sessions.parquet",
        "player_registry": f"silver/{SOURCE_PREFIX}/player_registry.parquet",
        "injury_episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
        "gold_features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
    }
    frames = {
        name: pl.read_parquet(BytesIO(bucket.blob(path).download_as_bytes()))
        for name, path in paths.items()
    }
    return run_stage_02_missingness_eda(**frames)


def run_stage_02_missingness_eda(
    *,
    daily_metrics: pl.DataFrame,
    training_load_daily: pl.DataFrame,
    wellness_daily: pl.DataFrame,
    training_sessions: pl.DataFrame,
    player_registry: pl.DataFrame,
    injury_episodes: pl.DataFrame,
    gold_features: pl.DataFrame,
) -> Stage02MissingnessResult:
    """Analyse measurement and reporting availability without imputing values."""
    session_calendar = _session_calendar(wellness_daily, training_sessions)
    variable_coverage = _variable_coverage(daily_metrics)
    player_coverage = _player_coverage(wellness_daily, session_calendar)
    team_month_coverage = _team_month_coverage(wellness_daily, session_calendar)
    day_of_week_reporting = _day_of_week_reporting(wellness_daily)
    missing_runs = _missing_runs(wellness_daily)
    missing_run_summary = _missing_run_summary(player_registry, missing_runs)
    partial_report_patterns = _partial_report_patterns(wellness_daily)
    co_missingness = _co_missingness(wellness_daily)
    session_record_availability = _session_record_availability(session_calendar)
    event_centered_reporting = _event_centered_reporting(
        wellness_daily, training_load_daily, session_calendar, player_registry, injury_episodes
    )
    gold_reconciliation = _gold_reconciliation(
        gold_features, wellness_daily, training_load_daily, session_calendar
    )
    findings = _reporting_findings(
        wellness_daily=wellness_daily,
        player_coverage=player_coverage,
        team_month_coverage=team_month_coverage,
        missing_runs=missing_runs,
        gold_reconciliation=gold_reconciliation,
        event_centered_reporting=event_centered_reporting,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    tables = {
        "variable_coverage": variable_coverage,
        "player_coverage": player_coverage,
        "team_month_coverage": team_month_coverage,
        "day_of_week_reporting": day_of_week_reporting,
        "missing_runs": missing_runs,
        "missing_run_summary": missing_run_summary,
        "partial_report_patterns": partial_report_patterns,
        "co_missingness": co_missingness,
        "session_record_availability": session_record_availability,
        "event_centered_reporting": event_centered_reporting,
        "gold_completeness_reconciliation": gold_reconciliation,
        "reporting_process_findings": findings,
        "_wellness_calendar": wellness_daily.select(
            "player_id", "team_id", "report_date", "wellness_report_present"
        ),
    }
    return Stage02MissingnessResult(
        tables=tables,
        summary={
            "stage": "02_missingness_eda",
            "status": "PASS" if failures == 0 else "FAIL",
            "player_day_count": wellness_daily.height,
            "wellness_report_days": wellness_daily.filter(pl.col("wellness_report_present")).height,
            "full_wellness_report_days": wellness_daily.filter(
                pl.col("wellness_metric_count") == len(WELLNESS_METRICS)
            ).height,
            "partial_wellness_report_days": wellness_daily.filter(
                pl.col("wellness_metric_count").is_between(1, len(WELLNESS_METRICS) - 1)
            ).height,
            "recorded_session_days": session_calendar.filter(
                pl.col("session_record_present")
            ).height,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_02_figures(result: Stage02MissingnessResult) -> dict[str, Figure]:
    """Build Stage 2 figures without writing files."""
    figures: dict[str, Figure] = {}
    coverage = result.tables["variable_coverage"].sort("observed_rate")
    fig, axis = plt.subplots(figsize=(10, 7))
    labels = [
        f"{group}/{metric}" for group, metric in coverage.select("group", "metric").iter_rows()
    ]
    axis.barh(labels, coverage["observed_rate"], color="#287271")
    axis.set_xlim(0, 1)
    axis.set_xlabel("Observed player-date proportion")
    axis.set_title("Daily metric coverage")
    fig.tight_layout()
    figures["variable_coverage"] = fig

    players = result.tables["player_coverage"].sort("wellness_report_rate")
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(range(1, players.height + 1), players["wellness_report_rate"], color="#E76F51")
    axis.set_ylim(0, 1)
    axis.set_xlabel("Player rank by reporting coverage")
    axis.set_ylabel("Wellness report rate")
    axis.set_title("Player-level wellness reporting coverage")
    fig.tight_layout()
    figures["player_wellness_coverage"] = fig

    monthly = result.tables["team_month_coverage"].sort("month")
    fig, axis = plt.subplots(figsize=(11, 5))
    for team in monthly["team_id"].unique(maintain_order=True):
        rows = monthly.filter(pl.col("team_id") == team)
        axis.plot(rows["month"], rows["wellness_report_rate"], marker="o", label=str(team))
    axis.set_ylim(0, 1.05)
    axis.set_ylabel("Wellness report rate")
    axis.set_title("Team wellness reporting by month")
    axis.tick_params(axis="x", rotation=45)
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["team_month_reporting"] = fig

    calendar = result.tables["_wellness_calendar"]
    player_ids = calendar["player_id"].unique(maintain_order=True).to_list()
    dates = calendar["report_date"].unique().sort().to_list()
    player_index = {player: index for index, player in enumerate(player_ids)}
    date_index = {day: index for index, day in enumerate(dates)}
    matrix = [[0 for _ in dates] for _ in player_ids]
    for row in calendar.iter_rows(named=True):
        matrix[player_index[row["player_id"]]][date_index[row["report_date"]]] = int(
            row["wellness_report_present"]
        )
    fig, axis = plt.subplots(figsize=(12, 6))
    axis.imshow(matrix, aspect="auto", interpolation="nearest", cmap="Greys", vmin=0, vmax=1)
    axis.set_xlabel("Calendar day index")
    axis.set_ylabel("Player index")
    axis.set_title("Wellness reporting calendar")
    fig.tight_layout()
    figures["wellness_reporting_heatmap"] = fig

    runs = result.tables["missing_runs"]
    run_bands = (
        ("1", 1, 1),
        ("2-3", 2, 3),
        ("4-7", 4, 7),
        ("8-14", 8, 14),
        ("15-30", 15, 30),
        ("31-90", 31, 90),
        ("91-180", 91, 180),
        ("181-365", 181, 365),
        ("366+", 366, None),
    )
    run_counts = [
        runs.filter(
            pl.col("run_days").is_between(lower, upper)
            if upper is not None
            else pl.col("run_days") >= lower
        ).height
        for _, lower, upper in run_bands
    ]
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.bar([label for label, _, _ in run_bands], run_counts, color="#D4A373")
    axis.set_yscale("log")
    axis.set_xlabel("Consecutive no-report days (band)")
    axis.set_ylabel("Run count (log scale)")
    axis.set_title("Wellness no-report run lengths")
    fig.tight_layout()
    figures["missing_run_lengths"] = fig

    patterns = result.tables["partial_report_patterns"].sort("wellness_metric_count")
    count_by_metrics = patterns.group_by("wellness_metric_count").agg(
        pl.sum("player_days").alias("days")
    )
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.bar(
        count_by_metrics["wellness_metric_count"],
        count_by_metrics["days"],
        color="#E9C46A",
    )
    axis.set_xlabel("Wellness metrics present")
    axis.set_ylabel("Player-days")
    axis.set_title("Wellness report completeness")
    fig.tight_layout()
    figures["wellness_metric_counts"] = fig

    co_missing = result.tables["co_missingness"]
    matrix = []
    for metric_a in WELLNESS_METRICS:
        matrix.append(
            [
                co_missing.filter(
                    (pl.col("metric_a") == metric_a) & (pl.col("metric_b") == metric_b)
                ).item(0, "joint_missing_rate")
                for metric_b in WELLNESS_METRICS
            ]
        )
    fig, axis = plt.subplots(figsize=(8, 7))
    image = axis.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1)
    axis.set_xticks(range(len(WELLNESS_METRICS)), WELLNESS_METRICS, rotation=45, ha="right")
    axis.set_yticks(range(len(WELLNESS_METRICS)), WELLNESS_METRICS)
    axis.set_title("Joint wellness-metric missingness")
    fig.colorbar(image, ax=axis, label="Both metrics missing")
    fig.tight_layout()
    figures["co_missingness_heatmap"] = fig

    weekday = result.tables["day_of_week_reporting"].sort("weekday_number", "team_id")
    fig, axis = plt.subplots(figsize=(10, 5))
    teams = weekday["team_id"].unique(maintain_order=True).to_list()
    width = 0.35
    x = list(range(7))
    for index, team in enumerate(teams):
        rows = weekday.filter(pl.col("team_id") == team)
        offset = (index - (len(teams) - 1) / 2) * width
        axis.bar([value + offset for value in x], rows["report_rate"], width, label=str(team))
    axis.set_xticks(x, weekday.filter(pl.col("team_id") == teams[0])["weekday_name"])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Wellness report rate")
    axis.set_title("Wellness reporting by day of week")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["weekday_reporting"] = fig

    event_profile = result.tables["event_centered_reporting"].sort("relative_day")
    fig, axis = plt.subplots(figsize=(11, 5))
    axis.plot(
        event_profile["relative_day"],
        event_profile["wellness_report_rate"],
        label="Wellness report",
        color="#287271",
    )
    axis.plot(
        event_profile["relative_day"],
        event_profile["session_record_rate"],
        label="Recorded session",
        color="#E76F51",
    )
    axis.axvline(0, color="black", linestyle="--", linewidth=1, label="Onset date")
    axis.set_ylim(0, 1)
    axis.set_xlabel("Days relative to player-date onset")
    axis.set_ylabel("Available-record proportion")
    axis.set_title("Reporting process around onset dates")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["event_centered_reporting"] = fig
    return figures


def write_stage_02_outputs(result: Stage02MissingnessResult, output_root: Path) -> None:
    """Persist the canonical Stage 2 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_02_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_02_MISSINGNESS_EDA.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_02_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _session_calendar(wellness: pl.DataFrame, sessions: pl.DataFrame) -> pl.DataFrame:
    daily_sessions = sessions.group_by("player_id", "session_date").agg(
        pl.len().alias("recorded_session_count"),
        pl.sum("duration_minutes").alias("recorded_session_duration"),
        pl.sum("srpe").alias("recorded_session_srpe"),
    )
    return (
        wellness.select("player_id", "team_id", pl.col("report_date").alias("calendar_date"))
        .join(
            daily_sessions,
            left_on=["player_id", "calendar_date"],
            right_on=["player_id", "session_date"],
            how="left",
        )
        .with_columns(
            pl.col("recorded_session_count").fill_null(0),
            pl.col("recorded_session_duration").fill_null(0.0),
            pl.col("recorded_session_srpe").fill_null(0.0),
        )
        .with_columns((pl.col("recorded_session_count") > 0).alias("session_record_present"))
    )


def _variable_coverage(daily: pl.DataFrame) -> pl.DataFrame:
    return (
        daily.group_by("metric_name")
        .agg(
            pl.len().alias("calendar_cells"),
            pl.col("value").is_not_null().sum().alias("observed_cells"),
            pl.col("value").is_null().sum().alias("missing_cells"),
            (pl.col("value") == 0).sum().alias("zero_cells"),
        )
        .with_columns(
            pl.when(pl.col("metric_name").is_in(WELLNESS_METRICS))
            .then(pl.lit("wellness"))
            .otherwise(pl.lit("training_load"))
            .alias("group"),
            pl.col("metric_name").alias("metric"),
            (pl.col("observed_cells") / pl.col("calendar_cells")).alias("observed_rate"),
            (pl.col("zero_cells") / pl.col("observed_cells")).alias("zero_given_observed_rate"),
        )
        .select(
            "group",
            "metric",
            "calendar_cells",
            "observed_cells",
            "missing_cells",
            "zero_cells",
            "observed_rate",
            "zero_given_observed_rate",
        )
        .sort("group", "metric")
    )


def _player_coverage(wellness: pl.DataFrame, session_calendar: pl.DataFrame) -> pl.DataFrame:
    wellness_summary = wellness.group_by("player_id", "team_id").agg(
        pl.len().alias("calendar_days"),
        pl.col("wellness_report_present").sum().alias("wellness_report_days"),
        (pl.col("wellness_metric_count") == len(WELLNESS_METRICS)).sum().alias("full_report_days"),
        pl.col("wellness_metric_count")
        .is_between(1, len(WELLNESS_METRICS) - 1)
        .sum()
        .alias("partial_report_days"),
        pl.mean("wellness_metric_count").alias("mean_metric_count"),
    )
    session_summary = session_calendar.group_by("player_id").agg(
        pl.col("session_record_present").sum().alias("recorded_session_days"),
        pl.sum("recorded_session_count").alias("recorded_session_count"),
    )
    return (
        wellness_summary.join(session_summary, on="player_id")
        .with_columns(
            (pl.col("calendar_days") - pl.col("wellness_report_days")).alias("no_report_days"),
            (pl.col("wellness_report_days") / pl.col("calendar_days")).alias(
                "wellness_report_rate"
            ),
            (pl.col("full_report_days") / pl.col("calendar_days")).alias("full_report_rate"),
            (pl.col("partial_report_days") / pl.col("calendar_days")).alias("partial_report_rate"),
            (pl.col("recorded_session_days") / pl.col("calendar_days")).alias(
                "recorded_session_day_rate"
            ),
        )
        .sort("wellness_report_rate", "player_id")
    )


def _team_month_coverage(wellness: pl.DataFrame, session_calendar: pl.DataFrame) -> pl.DataFrame:
    wellness_monthly = (
        wellness.with_columns(pl.col("report_date").dt.truncate("1mo").alias("month"))
        .group_by("team_id", "month")
        .agg(
            pl.len().alias("calendar_days"),
            pl.col("wellness_report_present").sum().alias("wellness_report_days"),
            (pl.col("wellness_metric_count") == len(WELLNESS_METRICS))
            .sum()
            .alias("full_report_days"),
            pl.mean("wellness_metric_count").alias("mean_metric_count"),
        )
    )
    sessions_monthly = (
        session_calendar.with_columns(pl.col("calendar_date").dt.truncate("1mo").alias("month"))
        .group_by("team_id", "month")
        .agg(pl.col("session_record_present").sum().alias("recorded_session_days"))
    )
    return (
        wellness_monthly.join(sessions_monthly, on=["team_id", "month"])
        .with_columns(
            (pl.col("wellness_report_days") / pl.col("calendar_days")).alias(
                "wellness_report_rate"
            ),
            (pl.col("full_report_days") / pl.col("calendar_days")).alias("full_report_rate"),
            (pl.col("recorded_session_days") / pl.col("calendar_days")).alias(
                "recorded_session_day_rate"
            ),
        )
        .sort("month", "team_id")
    )


def _day_of_week_reporting(wellness: pl.DataFrame) -> pl.DataFrame:
    names = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }
    return (
        wellness.with_columns(pl.col("report_date").dt.weekday().alias("weekday_number"))
        .group_by("team_id", "weekday_number")
        .agg(
            pl.len().alias("calendar_days"),
            pl.col("wellness_report_present").sum().alias("report_days"),
        )
        .with_columns(
            pl.col("weekday_number").replace_strict(names).alias("weekday_name"),
            (pl.col("report_days") / pl.col("calendar_days")).alias("report_rate"),
        )
        .sort("weekday_number", "team_id")
    )


def _missing_runs(wellness: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for player_key, frame in wellness.sort("player_id", "report_date").group_by(
        "player_id", maintain_order=True
    ):
        assert isinstance(player_key, tuple)
        start: date | None = None
        end: date | None = None
        team_id = str(frame["team_id"][0])
        for row in frame.select("report_date", "wellness_report_present").iter_rows(named=True):
            day = row["report_date"]
            assert isinstance(day, date)
            if not row["wellness_report_present"]:
                start = day if start is None else start
                end = day
            elif start is not None and end is not None:
                rows.append(_run_row(str(player_key[0]), team_id, start, end))
                start = None
                end = None
        if start is not None and end is not None:
            rows.append(_run_row(str(player_key[0]), team_id, start, end))
    return pl.DataFrame(rows).sort("run_days", descending=True)


def _run_row(player_id: str, team_id: str, start: date, end: date) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "team_id": team_id,
        "run_start": start,
        "run_end": end,
        "run_days": (end - start).days + 1,
    }


def _missing_run_summary(registry: pl.DataFrame, runs: pl.DataFrame) -> pl.DataFrame:
    summary = runs.group_by("player_id").agg(
        pl.len().alias("no_report_run_count"),
        pl.max("run_days").alias("longest_no_report_run_days"),
        pl.median("run_days").alias("median_no_report_run_days"),
        pl.sum("run_days").alias("total_no_report_days"),
    )
    return (
        registry.select("player_id", "team_id")
        .join(summary, on="player_id", how="left")
        .with_columns(
            pl.col(
                "no_report_run_count", "longest_no_report_run_days", "total_no_report_days"
            ).fill_null(0),
            pl.col("median_no_report_run_days").fill_null(0.0),
        )
        .sort("longest_no_report_run_days", descending=True)
    )


def _partial_report_patterns(wellness: pl.DataFrame) -> pl.DataFrame:
    pattern = (
        pl.concat_str(
            [
                pl.when(pl.col(metric).is_not_null()).then(pl.lit(metric)).otherwise(pl.lit(""))
                for metric in WELLNESS_METRICS
            ],
            separator="|",
        )
        .str.replace_all(r"\|+", "|")
        .str.strip_chars("|")
    )
    return (
        wellness.with_columns(pattern.alias("observed_metric_pattern"))
        .group_by("wellness_metric_count", "observed_metric_pattern")
        .agg(pl.len().alias("player_days"), pl.n_unique("player_id").alias("player_count"))
        .with_columns((pl.col("player_days") / wellness.height).alias("player_day_share"))
        .sort("player_days", descending=True)
    )


def _co_missingness(wellness: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for metric_a in WELLNESS_METRICS:
        for metric_b in WELLNESS_METRICS:
            a = pl.col(metric_a).is_not_null()
            b = pl.col(metric_b).is_not_null()
            rows.append(
                {
                    "metric_a": metric_a,
                    "metric_b": metric_b,
                    "both_observed": wellness.filter(a & b).height,
                    "only_a_observed": wellness.filter(a & ~b).height,
                    "only_b_observed": wellness.filter(~a & b).height,
                    "both_missing": wellness.filter(~a & ~b).height,
                    "joint_missing_rate": wellness.filter(~a & ~b).height / wellness.height,
                }
            )
    return pl.DataFrame(rows)


def _session_record_availability(calendar: pl.DataFrame) -> pl.DataFrame:
    return (
        calendar.group_by("player_id", "team_id")
        .agg(
            pl.len().alias("calendar_days"),
            pl.col("session_record_present").sum().alias("recorded_session_days"),
            pl.sum("recorded_session_count").alias("recorded_sessions"),
            pl.sum("recorded_session_duration").alias("recorded_duration_minutes"),
            pl.sum("recorded_session_srpe").alias("recorded_srpe"),
        )
        .with_columns(
            (pl.col("recorded_session_days") / pl.col("calendar_days")).alias(
                "recorded_session_day_rate"
            ),
            pl.lit(
                "Absence of a session record is not confirmed rest and is not labelled missing"
            ).alias("interpretation"),
        )
        .sort("recorded_session_day_rate")
    )


def _event_centered_reporting(
    wellness: pl.DataFrame,
    load: pl.DataFrame,
    sessions: pl.DataFrame,
    registry: pl.DataFrame,
    episodes: pl.DataFrame,
) -> pl.DataFrame:
    wellness_lookup = {
        (str(row["player_id"]), row["report_date"]): row for row in wellness.to_dicts()
    }
    load_lookup = {(str(row["player_id"]), row["report_date"]): row for row in load.to_dicts()}
    session_lookup = {
        (str(row["player_id"]), row["calendar_date"]): row for row in sessions.to_dicts()
    }
    bounds = {
        str(row["player_id"]): (row["observation_start"], row["observation_end"])
        for row in registry.to_dicts()
    }
    onsets = episodes.select("player_id", pl.col("episode_start").alias("onset_date")).unique()
    rows = []
    for relative_day in EVENT_WINDOW:
        available = 0
        report_count = 0
        full_count = 0
        metric_total = 0
        load_count = 0
        session_count = 0
        for onset in onsets.iter_rows(named=True):
            player_id = str(onset["player_id"])
            onset_date = onset["onset_date"]
            assert isinstance(onset_date, date)
            day = onset_date + timedelta(days=relative_day)
            observation_start, observation_end = bounds[player_id]
            assert isinstance(observation_start, date)
            assert isinstance(observation_end, date)
            if not observation_start <= day <= observation_end:
                continue
            available += 1
            wellness_row = wellness_lookup[(player_id, day)]
            metric_count = int(wellness_row["wellness_metric_count"])
            report_count += int(wellness_row["wellness_report_present"])
            full_count += int(metric_count == len(WELLNESS_METRICS))
            metric_total += metric_count
            load_count += int(load_lookup[(player_id, day)]["daily_load"] is not None)
            session_count += int(session_lookup[(player_id, day)]["session_record_present"])
        rows.append(
            {
                "relative_day": relative_day,
                "available_onsets": available,
                "wellness_report_rate": report_count / available if available else None,
                "full_wellness_report_rate": full_count / available if available else None,
                "mean_wellness_metric_count": metric_total / available if available else None,
                "daily_load_observed_rate": load_count / available if available else None,
                "session_record_rate": session_count / available if available else None,
            }
        )
    return pl.DataFrame(rows)


def _gold_reconciliation(
    gold: pl.DataFrame,
    wellness: pl.DataFrame,
    load: pl.DataFrame,
    sessions: pl.DataFrame,
) -> pl.DataFrame:
    expected = (
        wellness.select(
            "player_id",
            pl.col("report_date").alias("prediction_date"),
            "wellness_report_present",
            "wellness_metric_count",
            "fatigue",
            "readiness",
        )
        .join(
            load.select("player_id", pl.col("report_date").alias("prediction_date"), "daily_load"),
            on=["player_id", "prediction_date"],
        )
        .join(
            sessions.select(
                "player_id",
                pl.col("calendar_date").alias("prediction_date"),
                pl.col("recorded_session_count").alias("session_count"),
                pl.col("recorded_session_duration").alias("session_duration_minutes"),
                pl.col("recorded_session_srpe").alias("session_srpe"),
            ),
            on=["player_id", "prediction_date"],
        )
    )
    fields = [
        "wellness_report_present",
        "wellness_metric_count",
        "fatigue",
        "readiness",
        "daily_load",
        "session_count",
        "session_duration_minutes",
        "session_srpe",
    ]
    joined = gold.select("player_id", "prediction_date", *fields).join(
        expected, on=["player_id", "prediction_date"], suffix="_expected"
    )
    rows = []
    for field in fields:
        mismatches = joined.filter(~pl.col(field).eq_missing(pl.col(f"{field}_expected"))).height
        rows.append(
            {
                "field": field,
                "mismatch_count": mismatches,
                "status": "PASS" if mismatches == 0 else "FAIL",
            }
        )
    return pl.DataFrame(rows)


def _reporting_findings(
    *,
    wellness_daily: pl.DataFrame,
    player_coverage: pl.DataFrame,
    team_month_coverage: pl.DataFrame,
    missing_runs: pl.DataFrame,
    gold_reconciliation: pl.DataFrame,
    event_centered_reporting: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []

    def finding(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    flag_mismatches = wellness_daily.filter(
        pl.col("wellness_report_present") != (pl.col("wellness_metric_count") > 0)
    ).height
    finding(
        "wellness_presence_identity",
        "silver wellness",
        "PASS" if flag_mismatches == 0 else "FAIL",
        f"{flag_mismatches} presence flags disagree with metric count",
    )
    reconciliation_failures = gold_reconciliation.filter(pl.col("status") == "FAIL").height
    finding(
        "gold_completeness_reproduction",
        "gold features",
        "PASS" if reconciliation_failures == 0 else "FAIL",
        f"{reconciliation_failures} fields differ from silver-derived values",
    )
    lowest = player_coverage.row(0, named=True)
    highest = player_coverage.row(-1, named=True)
    finding(
        "player_reporting_variation",
        "players",
        "REVIEW",
        f"Player wellness coverage ranges from {lowest['wellness_report_rate']:.1%} to "
        f"{highest['wellness_report_rate']:.1%}",
    )
    team_summary = (
        team_month_coverage.group_by("team_id")
        .agg(
            pl.sum("wellness_report_days").alias("reports"),
            pl.sum("calendar_days").alias("days"),
        )
        .with_columns((pl.col("reports") / pl.col("days")).alias("rate"))
    )
    rates = team_summary.sort("rate")["rate"].to_list()
    finding(
        "team_reporting_variation",
        "teams",
        "REVIEW",
        f"Team wellness coverage rates are {[round(float(value), 4) for value in rates]}",
    )
    longest_value = missing_runs["run_days"].max()
    assert isinstance(longest_value, int)
    longest = longest_value
    finding(
        "longest_no_report_run",
        "wellness",
        "REVIEW",
        f"Longest consecutive no-report run is {longest} days",
    )
    pre = event_centered_reporting.filter(pl.col("relative_day").is_between(-28, -1))
    onset = event_centered_reporting.filter(pl.col("relative_day") == 0)
    pre_rate_value = pre["wellness_report_rate"].mean()
    onset_rate_value = onset.item(0, "wellness_report_rate")
    assert isinstance(pre_rate_value, (int, float))
    assert isinstance(onset_rate_value, (int, float))
    pre_rate = float(pre_rate_value)
    onset_rate = float(onset_rate_value)
    finding(
        "event_centered_reporting",
        "onset context",
        "REVIEW",
        f"Mean pre-onset wellness report rate is {pre_rate:.1%}; onset-day rate is "
        f"{onset_rate:.1%}; this is descriptive process evidence only",
    )
    finding(
        "session_absence_semantics",
        "training sessions",
        "REVIEW",
        "No recorded session is not interpreted as confirmed rest or missing exposure",
    )
    return pl.DataFrame(rows)


def _render_report(result: Stage02MissingnessResult) -> str:
    summary = result.summary
    players = result.tables["player_coverage"]
    variable = result.tables["variable_coverage"]
    findings = result.tables["reporting_process_findings"]
    wellness_rate = summary["wellness_report_days"] / summary["player_day_count"]
    load_rates = variable.filter(pl.col("group") == "training_load")["observed_rate"]
    minimum_load_rate_value = load_rates.min()
    player_minimum_value = players["wellness_report_rate"].min()
    player_maximum_value = players["wellness_report_rate"].max()
    assert isinstance(minimum_load_rate_value, (int, float))
    assert isinstance(player_minimum_value, (int, float))
    assert isinstance(player_maximum_value, (int, float))
    minimum_load_rate = float(minimum_load_rate_value)
    player_minimum = float(player_minimum_value)
    player_maximum = float(player_maximum_value)
    lines = [
        "# Stage 2 - Missingness and Reporting-Process EDA",
        "",
        "## Automated Status",
        "",
        f"Automated reporting-integrity result: **{summary['status']}**. Project-owner "
        "review is required before Stage 3.",
        "",
        "## Scope",
        "",
        f"- Calendar player-days: `{summary['player_day_count']}`.",
        f"- Wellness report days: `{summary['wellness_report_days']}` ({wellness_rate:.1%}).",
        f"- Full wellness report days: `{summary['full_wellness_report_days']}`; partial "
        f"report days: `{summary['partial_wellness_report_days']}`.",
        f"- Days with at least one recorded session: `{summary['recorded_session_days']}`.",
        f"- Minimum training-load metric coverage: `{minimum_load_rate:.1%}`.",
        "",
        "## Interpretation Boundaries",
        "",
        "- Calendar presence, report submission and individual metric availability are "
        "separate concepts.",
        "- No recorded session is not confirmed rest and is not automatically missing data.",
        "- Zero is retained as an observed value; no source blank is converted to zero here.",
        "- Event-centred patterns describe reporting process and are not predictive or causal.",
        "",
        "## Player Coverage",
        "",
        f"Player wellness-report coverage ranges from `{player_minimum:.1%}` to "
        f"`{player_maximum:.1%}`.",
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
            "![Variable coverage](../figures/variable_coverage.png)",
            "![Player wellness coverage](../figures/player_wellness_coverage.png)",
            "![Team-month reporting](../figures/team_month_reporting.png)",
            "![Wellness reporting calendar](../figures/wellness_reporting_heatmap.png)",
            "![Missing run lengths](../figures/missing_run_lengths.png)",
            "![Wellness metric counts](../figures/wellness_metric_counts.png)",
            "![Co-missingness](../figures/co_missingness_heatmap.png)",
            "![Weekday reporting](../figures/weekday_reporting.png)",
            "![Event-centred reporting](../figures/event_centered_reporting.png)",
            "",
            "## Gate",
            "",
            "Approve missing-value handling principles, reporting-indicator eligibility and "
            "any required cohort exclusions. No imputation or model-performance decision is "
            "made in this stage.",
        ]
    )
    return "\n".join(lines) + "\n"
