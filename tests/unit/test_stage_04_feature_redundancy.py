from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_04_feature_redundancy import (
    LOG_FEATURES,
    build_stage_04_figures,
    run_stage_04_feature_redundancy,
)
from player_availability.features import build_subjective_player_day_features


def test_stage_04_builds_target_blind_structural_contracts() -> None:
    features = _features().with_columns(pl.lit(True).alias("injury_next_14d"))

    result = run_stage_04_feature_redundancy(features)

    assert result.summary["status"] == "PASS"
    assert result.summary["player_day_count"] == 240
    assert result.summary["source_numeric_feature_count"] == 33
    assert result.summary["derived_candidate_count"] == 16
    assert result.summary["outcome_columns_used"] == 0
    assert result.tables["transformation_checks"].filter(pl.col("status") == "FAIL").is_empty()
    assert set(LOG_FEATURES).issubset(set(result.tables["full_candidate_contract"]["feature"]))
    assert "injury_next_14d" not in result.tables["_analysis"].columns
    assert result.tables["structural_findings"].filter(pl.col("status") == "FAIL").is_empty()
    figures = build_stage_04_figures(result)
    assert len(figures) == 7
    for figure in figures.values():
        plt.close(figure)


def test_stage_04_preserves_zero_and_rank_under_log1p() -> None:
    result = run_stage_04_feature_redundancy(_features())
    checks = result.tables["transformation_checks"]

    assert checks["zero_preservation_violation_count"].sum() == 0
    assert checks["invalid_value_count"].sum() == 0
    assert checks["spearman_raw_vs_log1p"].min() == 1.0


def test_stage_04_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/04_feature_redundancy.ipynb").read_text(
        encoding="utf-8"
    )

    assert "write_stage_04_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _features() -> pl.DataFrame:
    start = date(2021, 1, 1)
    days = [start + timedelta(days=offset) for offset in range(120)]
    players = [("TeamA-1", "TeamA"), ("TeamB-1", "TeamB")]
    labels: list[dict[str, object]] = []
    load: list[dict[str, object]] = []
    wellness: list[dict[str, object]] = []
    sessions: list[dict[str, object]] = []
    for player_id, team_id in players:
        for offset, day in enumerate(days):
            labels.append({"player_id": player_id, "team_id": team_id, "prediction_date": day})
            daily_load = 0.0 if offset % 4 == 0 else float(90 + offset * 3)
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
                    "readiness": None if missing_wellness else float(5 + offset % 5),
                    "wellness_report_present": not missing_wellness,
                    "wellness_metric_count": 0 if missing_wellness else 7,
                }
            )
            if offset % 3 == 0:
                sessions.append(
                    {
                        "player_id": player_id,
                        "session_date": day,
                        "duration_minutes": float(45 + offset % 30),
                        "srpe": float(180 + offset * 2),
                    }
                )
    return build_subjective_player_day_features(
        pl.DataFrame(labels),
        pl.DataFrame(load),
        pl.DataFrame(wellness),
        pl.DataFrame(sessions),
    )
