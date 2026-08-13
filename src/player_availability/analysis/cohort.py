"""Phase A cohort, outcome and feature-quality reporting."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import polars as pl

HORIZONS_DAYS = (3, 7, 14)
CORE_FEATURES = (
    "daily_load",
    "fatigue",
    "readiness",
    "wellness_report_present",
    "session_duration_sum_7d",
    "session_srpe_sum_7d",
    "daily_load_zscore_prior",
    "fatigue_zscore_prior",
    "readiness_zscore_prior",
)


@dataclass(frozen=True, slots=True)
class PhaseACohortReport:
    """Measured Phase A evidence and its rendered Markdown report."""

    markdown: str
    summary: dict[str, int | float | str]


def build_phase_a_cohort_report(
    features: pl.DataFrame, episodes: pl.DataFrame, raw_injury_reports: pl.DataFrame
) -> PhaseACohortReport:
    """Measure model-readiness without fitting a predictive model."""
    _require_unique(features, ["player_id", "prediction_date"], "player-day")
    _require_columns(features, CORE_FEATURES)
    total_rows = features.height
    players = features.get_column("player_id").n_unique()
    teams = features.get_column("team_id").n_unique()
    start_date = features.get_column("prediction_date").min()
    end_date = features.get_column("prediction_date").max()
    assert isinstance(start_date, date)
    assert isinstance(end_date, date)
    history_eligible = _history_eligible(features, burn_in_days=28)
    cohort_rows = [_cohort_row(features, history_eligible, horizon) for horizon in HORIZONS_DAYS]
    episode_summary = _episode_summary(episodes, raw_injury_reports)
    feature_coverage = _feature_coverage(features, history_eligible)
    positive_concentration = _positive_concentration(features, history_eligible, horizon=7)
    correlations = _descriptive_correlations(features, history_eligible)
    markdown = _render_markdown(
        total_rows=total_rows,
        players=players,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        cohort_rows=cohort_rows,
        episode_summary=episode_summary,
        feature_coverage=feature_coverage,
        positive_concentration=positive_concentration,
        correlations=correlations,
    )
    return PhaseACohortReport(
        markdown=markdown,
        summary={
            "player_day_rows": total_rows,
            "players": players,
            "teams": teams,
            "primary_7d_eligible_rows": int(cohort_rows[1]["eligible_rows"]),
            "primary_7d_positive_rows": int(cohort_rows[1]["positive_rows"]),
        },
    )


def _history_eligible(features: pl.DataFrame, *, burn_in_days: int) -> pl.DataFrame:
    starts = features.group_by("player_id").agg(pl.min("prediction_date").alias("start"))
    return (
        features.join(starts, on="player_id")
        .with_columns(
            (pl.col("prediction_date") >= pl.col("start") + timedelta(days=burn_in_days - 1)).alias(
                "history_eligible"
            )
        )
        .drop("start")
    )


def _cohort_row(
    features: pl.DataFrame, history_eligible: pl.DataFrame, horizon: int
) -> dict[str, Any]:
    label_complete = f"label_complete_{horizon}d"
    eligible = f"eligible_new_onset_{horizon}d"
    target = f"injury_next_{horizon}d"
    complete = history_eligible.filter(pl.col(label_complete))
    onset_eligible = history_eligible.filter(pl.col("history_eligible") & pl.col(eligible))
    positives = onset_eligible.filter(pl.col(target))
    return {
        "horizon": horizon,
        "complete_label_rows": complete.height,
        "eligible_rows": onset_eligible.height,
        "positive_rows": positives.height,
        "prevalence_percent": _percentage(positives.height, onset_eligible.height),
    }


def _episode_summary(episodes: pl.DataFrame, raw_reports: pl.DataFrame) -> dict[str, Any]:
    durations = episodes.with_columns(
        (pl.col("episode_end") - pl.col("episode_start")).dt.total_days().alias("duration_days")
    )
    return {
        "raw_reports": raw_reports.height,
        "episodes": episodes.height,
        "reports_per_episode": round(raw_reports.height / episodes.height, 2),
        "median_duration_days": _numeric(durations.get_column("duration_days").median()),
        "max_duration_days": int(_numeric(durations.get_column("duration_days").max())),
        "players_with_episodes": episodes.get_column("player_id").n_unique(),
    }


def _feature_coverage(
    features: pl.DataFrame, history_eligible: pl.DataFrame
) -> list[dict[str, Any]]:
    cohort = history_eligible.filter(pl.col("history_eligible"))
    rows: list[dict[str, Any]] = []
    for feature in CORE_FEATURES:
        non_null = int(_numeric(cohort.get_column(feature).is_not_null().sum()))
        rows.append(
            {
                "feature": feature,
                "non_null_rows": non_null,
                "coverage_percent": _percentage(non_null, cohort.height),
            }
        )
    return rows


def _positive_concentration(
    features: pl.DataFrame, history_eligible: pl.DataFrame, *, horizon: int
) -> list[dict[str, Any]]:
    target = f"injury_next_{horizon}d"
    eligible = f"eligible_new_onset_{horizon}d"
    return (
        history_eligible.filter(pl.col("history_eligible") & pl.col(eligible) & pl.col(target))
        .group_by("player_id", "team_id")
        .len()
        .sort("len", descending=True)
        .head(10)
        .rename({"len": "positive_player_days"})
        .to_dicts()
    )


def _descriptive_correlations(
    features: pl.DataFrame, history_eligible: pl.DataFrame
) -> list[dict[str, Any]]:
    cohort = history_eligible.filter(pl.col("history_eligible") & pl.col("eligible_new_onset_7d"))
    rows: list[dict[str, Any]] = []
    for feature in CORE_FEATURES:
        correlation = cohort.select(
            pl.corr(pl.col(feature).cast(pl.Float64), pl.col("injury_next_7d").cast(pl.Float64))
        ).item()
        rows.append({"feature": feature, "pearson_correlation": round(_numeric(correlation), 4)})
    return sorted(rows, key=lambda row: abs(float(row["pearson_correlation"])), reverse=True)


def _render_markdown(
    *,
    total_rows: int,
    players: int,
    teams: int,
    start_date: date,
    end_date: date,
    cohort_rows: list[dict[str, Any]],
    episode_summary: dict[str, Any],
    feature_coverage: list[dict[str, Any]],
    positive_concentration: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
) -> str:
    lines = [
        "# Phase A - Subjective Cohort, Outcome and Feature Quality Report",
        "",
        "## Scope",
        "",
        "This report is descriptive model-readiness analysis for the `subjective_v1` player-day product. It does not fit or evaluate a predictive model. Its purpose is to verify cohort size, outcome prevalence, episode concentration and predictor availability before chronological split selection.",
        "",
        "## Dataset Snapshot",
        "",
        f"- Observation window: `{start_date.isoformat()}` to `{end_date.isoformat()}`.",
        f"- Observed player-days: `{total_rows:,}`.",
        f"- Players: `{players}` across `{teams}` teams.",
        "- Burn-in rule for headline analysis: first 27 calendar days per player excluded from the 28-day-feature cohort.",
        "- Outcome: future self-reported injury-episode start; same-day episodes are excluded from future labels under the accepted end-of-day cutoff.",
        "",
        "## Cohort Flow and Label Prevalence",
        "",
        "| Horizon | Complete-label rows | 28-day-history and new-onset eligible rows | Positive player-days | Prevalence |",
        "|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        "| {horizon} days | {complete_label_rows:,} | {eligible_rows:,} | {positive_rows:,} | {prevalence_percent:.2f}% |".format(
            **row
        )
        for row in cohort_rows
    )
    lines.extend(
        [
            "",
            "Interpretation: a positive player-day is not an independent medically verified injury. Several days can precede the same episode, which is expected for overlapping fixed-horizon labels.",
            "",
            "## Episode Construction Summary",
            "",
            f"- Raw injury reports: `{episode_summary['raw_reports']}`.",
            f"- Primary 3-day-gap self-reported episodes: `{episode_summary['episodes']}`.",
            f"- Raw reports per episode: `{episode_summary['reports_per_episode']}`.",
            f"- Players with at least one episode: `{episode_summary['players_with_episodes']}`.",
            f"- Episode duration: median `{episode_summary['median_duration_days']:.1f}` days; maximum `{episode_summary['max_duration_days']}` days.",
            "",
            "## Predictor Coverage After Burn-In",
            "",
            "| Predictor | Non-null rows | Coverage |",
            "|---|---:|---:|",
        ]
    )
    lines.extend(
        "| {feature} | {non_null_rows:,} | {coverage_percent:.2f}% |".format(**row)
        for row in feature_coverage
    )
    lines.extend(
        [
            "",
            "`wellness_report_present` is a process/completeness field. Any predictive value must be interpreted as potentially reflecting reporting behaviour rather than physiology.",
            "",
            "## 7-Day Positive-Label Concentration",
            "",
            "| Player | Team | Positive player-days |",
            "|---|---|---:|",
        ]
    )
    lines.extend(
        "| {player_id} | {team_id} | {positive_player_days:,} |".format(**row)
        for row in positive_concentration
    )
    lines.extend(
        [
            "",
            "Concentration is reported before fitting because repeated player-days are dependent. Later uncertainty intervals must be clustered by player, and leave-one-player-out analysis is mandatory before generalisation claims.",
            "",
            "## Descriptive 7-Day Associations",
            "",
            "These univariate Pearson correlations are descriptive only. They are not feature-selection evidence, causal evidence or model performance. They use the 28-day-history, new-onset-eligible cohort and are included to detect extreme or surprising associations before fitting.",
            "",
            "| Predictor | Correlation with 7-day label |",
            "|---|---:|",
        ]
    )
    lines.extend("| {feature} | {pearson_correlation:.4f} |".format(**row) for row in correlations)
    lines.extend(
        [
            "",
            "## Phase A Decision",
            "",
            "**PROMOTE to Phase B.** The cohort, censored labels and feature product are available for chronological split construction. No model conclusion is made in this report. Before fitting EXP-002, freeze date boundaries, implement a predictor allow-list and verify that preprocessing is fit only on the training partition.",
            "",
            "## Limitations",
            "",
            "- Labels describe self-reported injury-related episodes, not clinical diagnoses.",
            "- Fixed-horizon positive player-days overlap by construction.",
            "- The modest number of episodes and player-level dependence limit precision.",
            "- Descriptive association cannot establish that load, wellness or missingness caused an event.",
        ]
    )
    return "\n".join(lines) + "\n"


def _percentage(numerator: int, denominator: int) -> float:
    return 100 * numerator / denominator if denominator else 0.0


def _numeric(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    raise ValueError(f"Expected numeric aggregate, got {value!r}")


def _require_unique(frame: pl.DataFrame, columns: list[str], relation: str) -> None:
    duplicates = frame.group_by(columns).len().filter(pl.col("len") > 1)
    if not duplicates.is_empty():
        raise ValueError(f"Duplicate {relation} keys: {columns}")


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...]) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")
