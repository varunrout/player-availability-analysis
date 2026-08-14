from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_03_feature_distribution_eda import (
    build_stage_03_figures,
    run_stage_03_feature_distribution_eda,
)
from player_availability.features import build_subjective_player_day_features


def test_stage_03_profiles_ranges_and_temporal_features() -> None:
    features = _features()

    result = run_stage_03_feature_distribution_eda(features)

    assert result.summary["status"] == "PASS"
    assert result.summary["player_day_count"] == 240
    assert result.summary["numeric_feature_count"] == 33
    assert result.tables["range_checks"].filter(pl.col("status") == "FAIL").is_empty()
    assert result.tables["rolling_window_checks"].filter(pl.col("status") == "FAIL").is_empty()
    eligibility = result.tables["feature_eligibility"]
    fatigue_mean = eligibility.filter(pl.col("feature") == "fatigue_mean_7d")
    assert fatigue_mean.item(0, "eligibility") == "requires_lagged_rebuild"
    fatigue_baseline = eligibility.filter(pl.col("feature") == "fatigue_baseline_mean_prior")
    assert fatigue_baseline.item(0, "eligibility") == "primary_candidate_lagged"
    plt.close("all")
    figures = build_stage_03_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_stage_03_fails_for_negative_nonnegative_feature() -> None:
    features = (
        _features()
        .with_row_index()
        .with_columns(
            pl.when(pl.col("index") == 0)
            .then(pl.lit(-1.0))
            .otherwise(pl.col("daily_load"))
            .alias("daily_load")
        )
        .drop("index")
    )

    result = run_stage_03_feature_distribution_eda(features)

    assert result.summary["status"] == "FAIL"
    check = result.tables["range_checks"].filter(pl.col("check_id") == "daily_load_nonnegative")
    assert check.item(0, "violation_count") == 1


def test_stage_03_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/03_feature_distribution_eda.ipynb").read_text(
        encoding="utf-8"
    )

    assert "write_stage_03_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _features() -> pl.DataFrame:
    start = date(2021, 1, 1)
    days = [start + timedelta(days=offset) for offset in range(120)]
    players = [("TeamA-1", "TeamA"), ("TeamB-1", "TeamB")]
    labels = []
    load = []
    wellness = []
    sessions = []
    for player_id, team_id in players:
        for offset, day in enumerate(days):
            labels.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "prediction_date": day,
                }
            )
            daily_load = 0.0 if offset % 4 == 0 else float(100 + offset)
            load.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "report_date": day,
                    "daily_load": daily_load,
                }
            )
            missing_wellness = player_id == "TeamB-1" and offset % 5 == 0
            wellness.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "report_date": day,
                    "fatigue": None if missing_wellness else float(1 + offset % 5),
                    "readiness": None if missing_wellness else float(5 - offset % 5),
                    "wellness_report_present": not missing_wellness,
                    "wellness_metric_count": 0 if missing_wellness else 7,
                }
            )
            if offset % 3 == 0:
                sessions.append(
                    {
                        "player_id": player_id,
                        "session_date": day,
                        "duration_minutes": 60.0,
                        "srpe": 300.0,
                    }
                )
    return build_subjective_player_day_features(
        pl.DataFrame(labels),
        pl.DataFrame(load),
        pl.DataFrame(wellness),
        pl.DataFrame(sessions),
    )
