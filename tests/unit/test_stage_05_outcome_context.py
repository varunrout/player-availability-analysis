from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_05_outcome_context import (
    build_stage_05_figures,
    run_stage_05_outcome_context,
)


def test_stage_05_builds_distinct_events_and_clean_references() -> None:
    features, episodes = _inputs()
    features = features.with_columns(pl.lit(True).alias("injury_next_14d"))

    result = run_stage_05_outcome_context(features=features, episodes=episodes)

    assert result.summary["status"] == "PASS"
    assert result.summary["distinct_onset_count"] == 3
    assert result.summary["history_complete_onset_count"] == 3
    assert result.summary["calendar_matched_onset_count"] == 3
    assert result.summary["model_count"] == 0
    register = result.tables["event_reference_register"]
    assert register.select("player_id", "onset_date").is_duplicated().sum() == 0
    assert register.filter(pl.col("calendar_reference_date").is_null()).is_empty()
    contributions = result.tables["player_team_contribution"].filter(pl.col("scope") == "player")
    assert contributions["matched_count"].to_list() == [2, 1]
    timeline = result.tables["_timeline"]
    assert timeline.filter(pl.col("primary_pre_onset") & (pl.col("relative_day") >= 0)).is_empty()
    assert result.tables["outcome_context_findings"].filter(pl.col("status") == "FAIL").is_empty()
    figures = build_stage_05_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_stage_05_primary_differences_never_use_day_zero() -> None:
    features, episodes = _inputs()
    result = run_stage_05_outcome_context(features=features, episodes=episodes)
    differences = result.tables["matched_event_differences"]

    assert differences["window_days"].unique().sort().to_list() == [3, 7, 14, 28]
    event_observed_days = differences["event_observed_days"].max()
    reference_observed_days = differences["reference_observed_days"].max()
    assert isinstance(event_observed_days, int)
    assert isinstance(reference_observed_days, int)
    assert event_observed_days <= 28
    assert reference_observed_days <= 28
    reporting = differences.filter(pl.col("feature") == "wellness_report_present")
    assert not reporting.is_empty()


def test_stage_05_does_not_match_incomplete_event_history() -> None:
    features, episodes = _inputs()
    incomplete_episode = pl.DataFrame(
        [
            {
                "episode_id": "E0",
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": date(2021, 1, 11),
            }
        ]
    )

    result = run_stage_05_outcome_context(
        features=features,
        episodes=pl.concat([episodes, incomplete_episode]),
    )

    register = result.tables["event_reference_register"]
    incomplete = register.filter(pl.col("event_id") == "P1|2021-01-11").row(0, named=True)
    assert incomplete["history_complete"] is False
    assert incomplete["candidate_reference_count"] == 0
    assert incomplete["calendar_reference_date"] is None
    assert result.summary["distinct_onset_count"] == 4
    assert result.summary["history_complete_onset_count"] == 3
    assert result.summary["calendar_matched_onset_count"] == 3


def test_stage_05_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/05_outcome_context.ipynb").read_text(encoding="utf-8")

    assert "write_stage_05_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _inputs() -> tuple[pl.DataFrame, pl.DataFrame]:
    start = date(2021, 1, 1)
    rows: list[dict[str, object]] = []
    players = (("P1", "TeamA"), ("P2", "TeamB"))
    onset_offsets = {"P1": (100, 180), "P2": (120,)}
    for player_id, team_id in players:
        for offset in range(320):
            day = start + timedelta(days=offset)
            near_onset = any(0 < onset - offset <= 7 for onset in onset_offsets[player_id])
            load = float(150 + offset % 20 + (80 if near_onset else 0))
            duration = float(55 + offset % 15 + (10 if near_onset else 0))
            wellness_present = offset % 5 != 0
            rows.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "prediction_date": day,
                    "active_injury_episode": False,
                    "session_count": 1 if offset % 4 else 0,
                    "daily_load": load if offset % 4 else 0.0,
                    "session_duration_minutes": duration if offset % 4 else 0.0,
                    "daily_load_sum_7d": load * 5,
                    "daily_load_sum_28d": load * 20,
                    "session_duration_sum_7d": duration * 5,
                    "session_duration_sum_28d": duration * 20,
                    "fatigue": float(2 + offset % 3) if wellness_present else None,
                    "readiness": float(6 + offset % 3) if wellness_present else None,
                    "wellness_report_present": wellness_present,
                    "wellness_metric_count": 7 if wellness_present else 0,
                }
            )
    episodes = pl.DataFrame(
        [
            {
                "episode_id": "E1",
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": start + timedelta(days=100),
            },
            {
                "episode_id": "E1b",
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": start + timedelta(days=100),
            },
            {
                "episode_id": "E2",
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": start + timedelta(days=180),
            },
            {
                "episode_id": "E3",
                "player_id": "P2",
                "team_id": "TeamB",
                "episode_start": start + timedelta(days=120),
            },
        ]
    )
    return pl.DataFrame(rows), episodes
