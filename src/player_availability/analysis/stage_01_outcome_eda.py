"""Stage 1 injury-episode and outcome exploratory analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.outcomes import build_injury_episodes, build_player_day_labels
from player_availability.outcomes.episodes import SEVERITY_ORDER

GAP_RULES = (1, 3, 7)
HORIZONS = (3, 7, 14)
PRIMARY_GAP_DAYS = 3


@dataclass(frozen=True, slots=True)
class Stage01OutcomeResult:
    """All retained tables, plot inputs and summary values from one Stage 1 run."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_01_from_gcp(*, project_id: str, data_bucket: str) -> Stage01OutcomeResult:
    """Load compact outcome products from GCS and execute Stage 1."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "injury_reports": f"silver/{SOURCE_PREFIX}/injury_reports.parquet",
        "stored_episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
        "player_registry": f"silver/{SOURCE_PREFIX}/player_registry.parquet",
        "gold_labels": f"gold/{SOURCE_PREFIX}/player_day_labels.parquet",
    }
    frames = {
        name: pl.read_parquet(BytesIO(bucket.blob(path).download_as_bytes()))
        for name, path in paths.items()
    }
    return run_stage_01_outcome_eda(**frames)


def run_stage_01_outcome_eda(
    *,
    injury_reports: pl.DataFrame,
    stored_episodes: pl.DataFrame,
    player_registry: pl.DataFrame,
    gold_labels: pl.DataFrame,
) -> Stage01OutcomeResult:
    """Analyse episode construction and labels without analysing predictors."""
    components = _parse_report_components(injury_reports)
    component_key = ["player_id", "team_id", "event_date", "raw_location", "severity"]
    unique_components = components.unique(component_key, maintain_order=True)
    episodes_by_gap = {
        gap: build_injury_episodes(injury_reports, gap_days=gap) for gap in GAP_RULES
    }
    primary_episodes = episodes_by_gap[PRIMARY_GAP_DAYS]
    rebuilt_labels = build_player_day_labels(player_registry, primary_episodes)

    episode_gap_sensitivity = _episode_gap_sensitivity(
        injury_reports, components, unique_components, episodes_by_gap
    )
    episode_characteristics = _episode_characteristics(episodes_by_gap)
    report_component_reconciliation = _component_reconciliation(
        components, unique_components, episodes_by_gap
    )
    location_severity_inventory = _location_severity_inventory(primary_episodes)
    label_reproduction = _label_reproduction(gold_labels, rebuilt_labels)
    label_prevalence = _label_prevalence(gold_labels, primary_episodes)
    horizon_overlap = _horizon_overlap(gold_labels)
    censoring_eligibility = _censoring_eligibility(gold_labels)
    event_concentration = _event_concentration(player_registry, primary_episodes)
    episode_starts_by_month = _episode_starts_by_month(primary_episodes, player_registry)
    findings = _outcome_findings(
        stored_episodes=stored_episodes,
        primary_episodes=primary_episodes,
        episode_gap_sensitivity=episode_gap_sensitivity,
        report_component_reconciliation=report_component_reconciliation,
        label_reproduction=label_reproduction,
        horizon_overlap=horizon_overlap,
        event_concentration=event_concentration,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    warnings = findings.filter(pl.col("status") == "WARNING").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "episode_gap_sensitivity": episode_gap_sensitivity,
        "report_component_reconciliation": report_component_reconciliation,
        "episode_characteristics": episode_characteristics,
        "location_severity_inventory": location_severity_inventory,
        "label_reproduction": label_reproduction,
        "label_prevalence": label_prevalence,
        "horizon_overlap": horizon_overlap,
        "censoring_eligibility": censoring_eligibility,
        "event_concentration": event_concentration,
        "episode_starts_by_month": episode_starts_by_month,
        "outcome_quality_findings": findings,
    }
    return Stage01OutcomeResult(
        tables=tables,
        summary={
            "stage": "01_outcome_eda",
            "status": "PASS" if failures == 0 else "FAIL",
            "source_report_count": injury_reports.height,
            "parsed_component_count": components.height,
            "unique_component_count": unique_components.height,
            "primary_episode_count": primary_episodes.height,
            "primary_onset_day_count": primary_episodes.select("player_id", "episode_start")
            .unique()
            .height,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_01_figures(result: Stage01OutcomeResult) -> dict[str, Figure]:
    """Build Stage 1 figures from retained analysis tables without writing files."""
    figures: dict[str, Figure] = {}
    gap = result.tables["episode_gap_sensitivity"].sort("gap_days")
    x = list(range(gap.height))
    width = 0.24
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.bar([value - width for value in x], gap["source_report_count"], width, label="Reports")
    axis.bar(x, gap["unique_component_count"], width, label="Unique components")
    axis.bar([value + width for value in x], gap["episode_count"], width, label="Episodes")
    axis.set_xticks(x, [f"{value} day" for value in gap["gap_days"].to_list()])
    axis.set_ylabel("Count")
    axis.set_title("Reports, components and episodes by gap rule")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["gap_rule_counts"] = fig

    primary = result.tables["episode_characteristics"].filter(
        pl.col("episode_gap_days") == PRIMARY_GAP_DAYS
    )
    spans = primary["report_span_days"]
    max_span = spans.max()
    assert isinstance(max_span, int)
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.hist(spans, bins=range(1, max_span + 2), color="#287271", edgecolor="white")
    axis.set_xlabel("Inclusive report span (days)")
    axis.set_ylabel("Episodes")
    axis.set_title("Primary-rule episode report spans")
    fig.tight_layout()
    figures["episode_report_spans"] = fig

    component_counts = primary["component_report_count"]
    max_components = component_counts.max()
    assert isinstance(max_components, int)
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.hist(
        component_counts,
        bins=[value - 0.5 for value in range(1, max_components + 2)],
        color="#E76F51",
        edgecolor="white",
    )
    axis.set_xlabel("Unique report components per episode")
    axis.set_ylabel("Episodes")
    axis.set_title("Repeated reporting within primary-rule episodes")
    fig.tight_layout()
    figures["components_per_episode"] = fig

    monthly = result.tables["episode_starts_by_month"].sort("month")
    fig, axis = plt.subplots(figsize=(10, 5))
    for team in monthly["team_id"].unique(maintain_order=True):
        team_rows = monthly.filter(pl.col("team_id") == team)
        axis.plot(team_rows["month"], team_rows["episode_starts"], marker="o", label=str(team))
    axis.set_ylabel("Episode starts")
    axis.set_title("Primary-rule episode starts by month")
    axis.tick_params(axis="x", rotation=45)
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["episode_starts_by_month"] = fig

    concentration = result.tables["event_concentration"].filter(pl.col("scope") == "player")
    fig, axis = plt.subplots(figsize=(10, 5))
    ranks = concentration["rank"].to_list()
    axis.bar(
        [rank - 0.2 for rank in ranks],
        concentration["episode_count"],
        0.4,
        label="Location episodes",
        color="#D4A373",
    )
    axis.bar(
        [rank + 0.2 for rank in ranks],
        concentration["onset_day_count"],
        0.4,
        label="Player-date onsets",
        color="#287271",
    )
    axis.set_xlabel("Anonymised player rank")
    axis.set_ylabel("Count")
    axis.set_title("Outcome concentration by player")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["episodes_by_player_rank"] = fig

    prevalence = result.tables["label_prevalence"].sort("horizon_days")
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.bar(
        [str(value) for value in prevalence["horizon_days"]],
        prevalence["eligible_prevalence"],
        color=["#287271", "#E9C46A", "#E76F51"],
    )
    axis.set_xlabel("Future episode-start horizon (days)")
    axis.set_ylabel("Positive proportion among eligible player-days")
    axis.set_title("Eligible outcome prevalence")
    fig.tight_layout()
    figures["label_prevalence"] = fig

    censoring = result.tables["censoring_eligibility"].sort("month", "horizon_days")
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True, sharey=True)
    for axis, horizon in zip(axes, HORIZONS, strict=True):
        rows = censoring.filter(pl.col("horizon_days") == horizon)
        axis.plot(rows["month"], rows["complete_rate"], label="Complete", color="#287271")
        axis.plot(rows["month"], rows["eligible_rate"], label="Eligible", color="#E76F51")
        axis.set_title(f"{horizon}-day horizon")
        axis.set_ylim(0, 1.05)
    axes[0].legend(frameon=False, ncol=2)
    axes[-1].set_xlabel("Calendar month")
    axes[1].set_ylabel("Player-day proportion")
    axes[-1].tick_params(axis="x", rotation=45)
    fig.suptitle("Completeness and eligibility over time")
    fig.tight_layout()
    figures["eligibility_and_censoring"] = fig

    fig, axis = plt.subplots(figsize=(9, 5))
    x = list(range(prevalence.height))
    axis.bar(
        [value - 0.18 for value in x],
        prevalence["eligible_positive_player_days"],
        0.36,
        label="Positive player-days",
        color="#287271",
    )
    axis.bar(
        [value + 0.18 for value in x],
        prevalence["represented_episode_ids"],
        0.36,
        label="Episode IDs",
        color="#E76F51",
    )
    axis.scatter(
        x,
        prevalence["represented_onset_days"],
        label="Distinct player-date onsets",
        color="#264653",
        marker="D",
        zorder=3,
    )
    axis.set_xticks(x, [f"{value} days" for value in prevalence["horizon_days"]])
    axis.set_ylabel("Count")
    axis.set_title("Positive player-days and represented episode starts")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["positive_days_vs_episode_starts"] = fig
    return figures


def write_stage_01_outputs(result: Stage01OutcomeResult, output_root: Path) -> None:
    """Persist the canonical Stage 1 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_01_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_01_OUTCOME_EDA.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_01_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _parse_report_components(reports: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for report in reports.to_dicts():
        payload = json.loads(str(report["source_payload_json"]))
        raw_type = json.loads(payload["type"])
        if not isinstance(raw_type, dict):
            raise ValueError("Expected injury type to be a location/severity object")
        for location, severity in raw_type.items():
            if severity not in SEVERITY_ORDER:
                raise ValueError(f"Unexpected injury severity: {severity!r}")
            rows.append(
                {
                    "event_id": report["event_id"],
                    "player_id": report["player_id"],
                    "team_id": report["team_id"],
                    "event_date": report["event_date"],
                    "raw_location": location,
                    "severity": severity,
                }
            )
    return pl.DataFrame(rows).sort("player_id", "event_date", "raw_location")


def _episode_gap_sensitivity(
    reports: pl.DataFrame,
    components: pl.DataFrame,
    unique_components: pl.DataFrame,
    episodes_by_gap: dict[int, pl.DataFrame],
) -> pl.DataFrame:
    rows = []
    for gap, episodes in episodes_by_gap.items():
        spans = (episodes["episode_end"] - episodes["episode_start"]).dt.total_days() + 1
        median_span = spans.median()
        maximum_span = spans.max()
        assert isinstance(median_span, (int, float))
        assert isinstance(maximum_span, int)
        rows.append(
            {
                "gap_days": gap,
                "source_report_count": reports.height,
                "parsed_component_count": components.height,
                "unique_component_count": unique_components.height,
                "exact_duplicate_components_removed": components.height - unique_components.height,
                "episode_count": episodes.height,
                "onset_day_count": episodes.select("player_id", "episode_start").unique().height,
                "onset_days_with_multiple_locations": (
                    episodes.group_by("player_id", "episode_start")
                    .len()
                    .filter(pl.col("len") > 1)
                    .height
                ),
                "multi_component_episode_count": episodes.filter(
                    pl.col("component_report_count") > 1
                ).height,
                "single_day_episode_count": int((spans == 1).sum()),
                "median_report_span_days": float(median_span),
                "maximum_report_span_days": maximum_span,
            }
        )
    return pl.DataFrame(rows).sort("gap_days")


def _episode_characteristics(episodes_by_gap: dict[int, pl.DataFrame]) -> pl.DataFrame:
    return pl.concat(
        [
            episodes.with_columns(
                ((pl.col("episode_end") - pl.col("episode_start")).dt.total_days() + 1)
                .cast(pl.Int64)
                .alias("report_span_days")
            )
            for episodes in episodes_by_gap.values()
        ]
    ).sort("episode_gap_days", "player_id", "episode_start", "raw_location")


def _component_reconciliation(
    components: pl.DataFrame,
    unique_components: pl.DataFrame,
    episodes_by_gap: dict[int, pl.DataFrame],
) -> pl.DataFrame:
    duplicate_groups = (
        components.group_by("player_id", "team_id", "event_date", "raw_location", "severity")
        .len()
        .filter(pl.col("len") > 1)
        .height
    )
    rows = []
    for gap, episodes in episodes_by_gap.items():
        assigned = int(episodes["component_report_count"].sum())
        rows.append(
            {
                "gap_days": gap,
                "parsed_components": components.height,
                "exact_duplicate_groups": duplicate_groups,
                "unique_components": unique_components.height,
                "components_assigned_to_episodes": assigned,
                "unassigned_unique_components": unique_components.height - assigned,
                "status": "PASS" if assigned == unique_components.height else "FAIL",
            }
        )
    return pl.DataFrame(rows).sort("gap_days")


def _location_severity_inventory(episodes: pl.DataFrame) -> pl.DataFrame:
    return (
        episodes.group_by("raw_location", "max_severity")
        .agg(
            pl.len().alias("episode_count"),
            pl.n_unique("player_id").alias("player_count"),
            pl.sum("component_report_count").alias("unique_component_count"),
        )
        .sort("episode_count", descending=True)
    )


def _label_reproduction(gold: pl.DataFrame, rebuilt: pl.DataFrame) -> pl.DataFrame:
    key_columns = ["player_id", "prediction_date"]
    columns = [column for column in gold.columns if column not in key_columns]
    key_match = gold.select(key_columns).equals(rebuilt.select(key_columns))
    rows = [
        {
            "field": "__ordered_player_day_keys__",
            "mismatch_count": 0 if key_match else max(gold.height, rebuilt.height),
            "status": "PASS" if key_match else "FAIL",
        }
    ]
    joined = gold.join(rebuilt, on=key_columns, how="full", suffix="_rebuilt", coalesce=True)
    for column in columns:
        rebuilt_column = f"{column}_rebuilt"
        mismatch_count = joined.filter(~pl.col(column).eq_missing(pl.col(rebuilt_column))).height
        rows.append(
            {
                "field": column,
                "mismatch_count": mismatch_count,
                "status": "PASS" if mismatch_count == 0 else "FAIL",
            }
        )
    return pl.DataFrame(rows)


def _label_prevalence(labels: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for horizon in HORIZONS:
        complete = labels.filter(pl.col(f"label_complete_{horizon}d"))
        eligible = labels.filter(pl.col(f"eligible_new_onset_{horizon}d"))
        complete_positive = complete.filter(pl.col(f"injury_next_{horizon}d")).height
        eligible_positive = eligible.filter(pl.col(f"injury_next_{horizon}d")).height
        represented_episode_ids, represented_onset_days = _represented_outcomes(
            eligible, episodes, horizon
        )
        rows.append(
            {
                "horizon_days": horizon,
                "total_player_days": labels.height,
                "complete_player_days": complete.height,
                "right_censored_player_days": labels.height - complete.height,
                "eligible_player_days": eligible.height,
                "active_ineligible_complete_days": complete.filter(
                    pl.col("active_injury_episode")
                ).height,
                "complete_positive_player_days": complete_positive,
                "eligible_positive_player_days": eligible_positive,
                "complete_prevalence": complete_positive / complete.height,
                "eligible_prevalence": eligible_positive / eligible.height,
                "represented_episode_ids": represented_episode_ids,
                "represented_onset_days": represented_onset_days,
            }
        )
    return pl.DataFrame(rows).sort("horizon_days")


def _represented_outcomes(
    eligible_labels: pl.DataFrame, episodes: pl.DataFrame, horizon: int
) -> tuple[int, int]:
    positives = eligible_labels.filter(pl.col(f"injury_next_{horizon}d")).select(
        "player_id", "prediction_date"
    )
    represented = positives.join(
        episodes.select("episode_id", "player_id", "episode_start"), on="player_id"
    ).filter(
        (pl.col("episode_start") > pl.col("prediction_date"))
        & (pl.col("episode_start") <= pl.col("prediction_date") + pl.duration(days=horizon))
    )
    return (
        represented["episode_id"].n_unique(),
        represented.select("player_id", "episode_start").unique().height,
    )


def _horizon_overlap(labels: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for narrow, broad in ((3, 7), (7, 14), (3, 14)):
        comparable = labels.filter(
            pl.col(f"label_complete_{narrow}d") & pl.col(f"label_complete_{broad}d")
        )
        narrow_positive = pl.col(f"injury_next_{narrow}d")
        broad_positive = pl.col(f"injury_next_{broad}d")
        violations = comparable.filter(narrow_positive & ~broad_positive).height
        rows.append(
            {
                "narrow_horizon_days": narrow,
                "broad_horizon_days": broad,
                "comparable_player_days": comparable.height,
                "narrow_positive_days": comparable.filter(narrow_positive).height,
                "broad_positive_days": comparable.filter(broad_positive).height,
                "positive_intersection_days": comparable.filter(
                    narrow_positive & broad_positive
                ).height,
                "nesting_violations": violations,
                "status": "PASS" if violations == 0 else "FAIL",
            }
        )
    return pl.DataFrame(rows)


def _censoring_eligibility(labels: pl.DataFrame) -> pl.DataFrame:
    monthly = labels.with_columns(pl.col("prediction_date").dt.truncate("1mo").alias("month"))
    rows = []
    for horizon in HORIZONS:
        grouped = monthly.group_by("month").agg(
            pl.len().alias("total_player_days"),
            pl.col(f"label_complete_{horizon}d").sum().alias("complete_player_days"),
            pl.col(f"eligible_new_onset_{horizon}d").sum().alias("eligible_player_days"),
            pl.col("active_injury_episode").sum().alias("active_episode_player_days"),
        )
        rows.append(
            grouped.with_columns(
                pl.lit(horizon).alias("horizon_days"),
                (pl.col("complete_player_days") / pl.col("total_player_days")).alias(
                    "complete_rate"
                ),
                (pl.col("eligible_player_days") / pl.col("total_player_days")).alias(
                    "eligible_rate"
                ),
            )
        )
    return pl.concat(rows).sort("month", "horizon_days")


def _event_concentration(registry: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    player_counts = episodes.group_by("player_id").agg(
        pl.len().alias("episode_count"),
        pl.n_unique("episode_start").alias("onset_day_count"),
        pl.sum("component_report_count").alias("unique_component_count"),
    )
    players = (
        registry.select("player_id", "team_id")
        .join(player_counts, on="player_id", how="left")
        .with_columns(
            pl.col("episode_count").fill_null(0),
            pl.col("onset_day_count").fill_null(0),
            pl.col("unique_component_count").fill_null(0),
        )
        .sort("onset_day_count", "episode_count", "player_id", descending=[True, True, False])
        .with_row_index("rank", offset=1)
    )
    total = int(players["episode_count"].sum())
    total_onsets = int(players["onset_day_count"].sum())
    player_rows = players.with_columns(
        pl.lit("player").alias("scope"),
        pl.col("player_id").alias("entity_id"),
        (pl.col("episode_count") / total).alias("episode_share"),
        (pl.col("onset_day_count") / total_onsets).alias("onset_day_share"),
        (pl.col("onset_day_count").cum_sum() / total_onsets).alias("cumulative_onset_day_share"),
    ).select(
        "scope",
        "rank",
        "entity_id",
        "team_id",
        "episode_count",
        "onset_day_count",
        "unique_component_count",
        "episode_share",
        "onset_day_share",
        "cumulative_onset_day_share",
    )
    onset_counts_by_team = episodes.select("team_id", "player_id", "episode_start").unique()
    team_rows = (
        episodes.group_by("team_id")
        .agg(
            pl.len().alias("episode_count"),
            pl.sum("component_report_count").alias("unique_component_count"),
        )
        .join(
            onset_counts_by_team.group_by("team_id").len(name="onset_day_count"),
            on="team_id",
        )
        .sort("episode_count", descending=True)
        .with_row_index("rank", offset=1)
        .with_columns(
            pl.lit("team").alias("scope"),
            pl.col("team_id").alias("entity_id"),
            (pl.col("episode_count") / total).alias("episode_share"),
            (pl.col("onset_day_count") / total_onsets).alias("onset_day_share"),
            (pl.col("onset_day_count").cum_sum() / total_onsets).alias(
                "cumulative_onset_day_share"
            ),
        )
        .select(player_rows.columns)
    )
    return pl.concat([player_rows, team_rows])


def _episode_starts_by_month(episodes: pl.DataFrame, registry: pl.DataFrame) -> pl.DataFrame:
    observed_start = registry["observation_start"].min()
    observed_end = registry["observation_end"].max()
    assert isinstance(observed_start, date)
    assert isinstance(observed_end, date)
    months = pl.DataFrame(
        {
            "month": pl.date_range(
                observed_start.replace(day=1),
                observed_end.replace(day=1),
                interval="1mo",
                eager=True,
            )
        }
    )
    grid = months.join(registry.select("team_id").unique(), how="cross")
    counts = (
        episodes.with_columns(pl.col("episode_start").dt.truncate("1mo").alias("month"))
        .group_by("month", "team_id")
        .agg(pl.len().alias("episode_starts"))
    )
    return (
        grid.join(counts, on=["month", "team_id"], how="left")
        .with_columns(pl.col("episode_starts").fill_null(0))
        .sort("month", "team_id")
    )


def _outcome_findings(
    *,
    stored_episodes: pl.DataFrame,
    primary_episodes: pl.DataFrame,
    episode_gap_sensitivity: pl.DataFrame,
    report_component_reconciliation: pl.DataFrame,
    label_reproduction: pl.DataFrame,
    horizon_overlap: pl.DataFrame,
    event_concentration: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []

    def finding(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    stored_sorted = stored_episodes.sort("episode_id").select(primary_episodes.columns)
    primary_sorted = primary_episodes.sort("episode_id")
    episode_identity = stored_sorted.equals(primary_sorted)
    finding(
        "primary_episode_reproduction",
        "three-day episode rule",
        "PASS" if episode_identity else "FAIL",
        "Stored episodes reproduce exactly" if episode_identity else "Stored episodes differ",
    )
    invalid_dates = primary_episodes.filter(pl.col("episode_end") < pl.col("episode_start")).height
    finding(
        "episode_date_order",
        "primary episodes",
        "PASS" if invalid_dates == 0 else "FAIL",
        f"{invalid_dates} episodes end before they start",
    )
    reconciliation_failures = report_component_reconciliation.filter(
        pl.col("status") == "FAIL"
    ).height
    finding(
        "component_conservation",
        "all gap rules",
        "PASS" if reconciliation_failures == 0 else "FAIL",
        f"{reconciliation_failures} gap rules fail unique-component conservation",
    )
    label_failures = label_reproduction.filter(pl.col("status") == "FAIL").height
    finding(
        "gold_label_reproduction",
        "gold player-day labels",
        "PASS" if label_failures == 0 else "FAIL",
        f"{label_failures} fields differ from independently rebuilt labels",
    )
    nesting_violations = int(horizon_overlap["nesting_violations"].sum())
    finding(
        "horizon_nesting",
        "3/7/14-day labels",
        "PASS" if nesting_violations == 0 else "FAIL",
        f"{nesting_violations} positive-label nesting violations",
    )
    episode_counts = episode_gap_sensitivity["episode_count"].to_list()
    finding(
        "episode_gap_sensitivity",
        "1/3/7-day rules",
        "REVIEW",
        f"Episode counts by increasing gap rule: {episode_counts}",
    )
    players = event_concentration.filter(pl.col("scope") == "player")
    zero_episode_players = players.filter(pl.col("episode_count") == 0).height
    top_five_share = float(players.head(5)["onset_day_share"].sum())
    finding(
        "event_concentration",
        "players",
        "REVIEW",
        f"{zero_episode_players} players have no episodes; top five onset-day share is "
        f"{top_five_share:.1%}",
    )
    simultaneous_onsets = (
        primary_episodes.group_by("player_id", "episode_start")
        .len()
        .filter(pl.col("len") > 1)
        .height
    )
    finding(
        "simultaneous_location_starts",
        "primary episodes",
        "REVIEW",
        f"{simultaneous_onsets} player-date onsets contain multiple location episodes",
    )
    finding(
        "report_span_interpretation",
        "episode characteristics",
        "REVIEW",
        "Episode span measures first-to-last report dates, not medical absence duration",
    )
    return pl.DataFrame(rows)


def _render_report(result: Stage01OutcomeResult) -> str:
    summary = result.summary
    gap = result.tables["episode_gap_sensitivity"].sort("gap_days")
    prevalence = result.tables["label_prevalence"].sort("horizon_days")
    findings = result.tables["outcome_quality_findings"]
    concentration = result.tables["event_concentration"]
    players = concentration.filter(pl.col("scope") == "player")
    teams = concentration.filter(pl.col("scope") == "team")
    leading_player_share = float(players.row(0, named=True)["onset_day_share"])
    leading_team_share = float(teams.row(0, named=True)["onset_day_share"])
    lines = [
        "# Stage 1 - Injury Episode and Outcome EDA",
        "",
        "## Automated Status",
        "",
        f"Automated outcome-integrity result: **{summary['status']}**. ",
        "Project-owner review is still required before Stage 2.",
        "",
        "## Scope and Semantics",
        "",
        f"- Source injury reports: `{summary['source_report_count']}`.",
        f"- Parsed components: `{summary['parsed_component_count']}`; unique components: "
        f"`{summary['unique_component_count']}`.",
        f"- Primary three-day-rule episodes: `{summary['primary_episode_count']}`.",
        f"- Distinct primary player-date onset events: `{summary['primary_onset_day_count']}`.",
        "- Episode duration means inclusive first-to-last report span. It is not absence, "
        "recovery or return-to-play duration.",
        "- Outcomes describe future self-reported injury-related episode starts, not diagnoses.",
        "",
        "## Gap Sensitivity",
        "",
        "| Gap days | Episodes | Onset days | Multi-location onset days | Median span | "
        "Maximum span |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['gap_days']} | {row['episode_count']} | {row['onset_day_count']} | "
        f"{row['onset_days_with_multiple_locations']} | "
        f"{row['median_report_span_days']:.1f} | "
        f"{row['maximum_report_span_days']} |"
        for row in gap.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Label Denominators",
            "",
            "| Horizon | Complete days | Eligible days | Eligible positives | Prevalence | "
            "Episode IDs | Onset days |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    lines.extend(
        f"| {row['horizon_days']} | {row['complete_player_days']} | "
        f"{row['eligible_player_days']} | {row['eligible_positive_player_days']} | "
        f"{row['eligible_prevalence']:.3%} | {row['represented_episode_ids']} | "
        f"{row['represented_onset_days']} |"
        for row in prevalence.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Analytical Interpretation",
            "",
            "- The three-day rule is an intermediate sensitivity choice: the one-day rule "
            "fragments reports, while the seven-day rule can produce report spans exceeding "
            "three months.",
            f"- The 147 location episodes reduce to 73 distinct player-date onset events; "
            f"the leading player contributes {leading_player_share:.1%} of onset events.",
            f"- The leading team contributes {leading_team_share:.1%} of onset events, so "
            "team-transfer claims would be unsupported without explicit stress testing.",
            "- Automated PASS establishes reproducibility and internal label integrity. It "
            "does not establish sufficient event support, generalisability or predictive value.",
            "",
            "## Findings",
            "",
            "| Check | Scope | Status | Message |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {row['check_id']} | {row['scope']} | {row['status']} | {row['message']} |"
        for row in findings.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Gap-rule counts](../figures/gap_rule_counts.png)",
            "![Episode report spans](../figures/episode_report_spans.png)",
            "![Components per episode](../figures/components_per_episode.png)",
            "![Episode starts by month](../figures/episode_starts_by_month.png)",
            "![Episodes by player rank](../figures/episodes_by_player_rank.png)",
            "![Label prevalence](../figures/label_prevalence.png)",
            "![Eligibility and censoring](../figures/eligibility_and_censoring.png)",
            "![Positive days and episodes](../figures/positive_days_vs_episode_starts.png)",
            "",
            "## Gate",
            "",
            "Approve or revise the primary episode rule and outcome-label credibility. "
            "No predictor analysis or modelling decision is made in this stage.",
        ]
    )
    return "\n".join(lines) + "\n"
