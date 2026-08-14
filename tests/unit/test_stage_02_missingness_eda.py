from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl

from player_availability.analysis.stage_02_missingness_eda import (
    build_stage_02_figures,
    run_stage_02_missingness_eda,
)
from player_availability.ingestion.silver import TRAINING_LOAD_METRICS, WELLNESS_METRICS


def test_stage_02_reconstructs_reporting_and_gold_completeness() -> None:
    inputs = _inputs()

    result = run_stage_02_missingness_eda(**inputs)

    assert result.summary["status"] == "PASS"
    assert result.summary["player_day_count"] == 92
    assert result.summary["partial_wellness_report_days"] == 1
    assert (
        result.tables["gold_completeness_reconciliation"]
        .filter(pl.col("status") == "FAIL")
        .is_empty()
    )
    assert result.tables["missing_runs"]["run_days"].max() == 5
    interpretations = result.tables["session_record_availability"]["interpretation"].unique()
    assert interpretations.to_list() == [
        "Absence of a session record is not confirmed rest and is not labelled missing"
    ]
    figures = build_stage_02_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        figure.clear()


def test_stage_02_fails_when_gold_completeness_differs() -> None:
    inputs = _inputs()
    gold = (
        inputs["gold_features"]
        .with_row_index()
        .with_columns(
            pl.when(pl.col("index") == 0)
            .then(~pl.col("wellness_report_present"))
            .otherwise(pl.col("wellness_report_present"))
            .alias("wellness_report_present")
        )
        .drop("index")
    )

    result = run_stage_02_missingness_eda(**{**inputs, "gold_features": gold})

    assert result.summary["status"] == "FAIL"
    mismatch = result.tables["gold_completeness_reconciliation"].filter(
        pl.col("field") == "wellness_report_present"
    )
    assert mismatch.item(0, "mismatch_count") == 1


def test_stage_02_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/02_missingness_eda.ipynb").read_text(encoding="utf-8")

    assert "write_stage_02_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _inputs() -> dict[str, pl.DataFrame]:
    start = date(2021, 1, 1)
    days = [start + timedelta(days=offset) for offset in range(46)]
    players = [("TeamA-1", "TeamA"), ("TeamB-1", "TeamB")]
    wellness_rows: list[dict[str, object]] = []
    load_rows: list[dict[str, object]] = []
    daily_rows: list[dict[str, object]] = []
    session_rows: list[dict[str, object]] = []
    gold_rows: list[dict[str, object]] = []

    for player_id, team_id in players:
        for offset, day in enumerate(days):
            missing = (player_id == "TeamA-1" and 5 <= offset <= 7) or (
                player_id == "TeamB-1" and offset < 5
            )
            partial = player_id == "TeamA-1" and offset == 10
            wellness_values = {
                metric: None if missing or (partial and metric != "fatigue") else float(offset % 5)
                for metric in WELLNESS_METRICS
            }
            metric_count = sum(value is not None for value in wellness_values.values())
            wellness_rows.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "report_date": day,
                    **wellness_values,
                    "wellness_metric_count": metric_count,
                    "wellness_report_present": metric_count > 0,
                }
            )
            load_values = {metric: float(offset % 4) for metric in TRAINING_LOAD_METRICS}
            load_rows.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "report_date": day,
                    **load_values,
                }
            )
            for metric, value in {**load_values, **wellness_values}.items():
                daily_rows.append(
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "observation_date": day,
                        "metric_name": metric,
                        "value": value,
                    }
                )
            has_session = offset % 3 == 0
            if has_session:
                session_rows.append(
                    {
                        "player_id": player_id,
                        "session_date": day,
                        "duration_minutes": 60.0,
                        "srpe": 300.0,
                    }
                )
            gold_rows.append(
                {
                    "player_id": player_id,
                    "prediction_date": day,
                    "wellness_report_present": metric_count > 0,
                    "wellness_metric_count": metric_count,
                    "fatigue": wellness_values["fatigue"],
                    "readiness": wellness_values["readiness"],
                    "daily_load": load_values["daily_load"],
                    "session_count": int(has_session),
                    "session_duration_minutes": 60.0 if has_session else 0.0,
                    "session_srpe": 300.0 if has_session else 0.0,
                }
            )

    registry = pl.DataFrame(
        {
            "player_id": [player for player, _ in players],
            "team_id": [team for _, team in players],
            "observation_start": [days[0]] * 2,
            "observation_end": [days[-1]] * 2,
        }
    )
    episodes = pl.DataFrame(
        {
            "player_id": ["TeamA-1", "TeamB-1"],
            "episode_start": [date(2021, 1, 29), date(2021, 1, 30)],
        }
    )
    return {
        "daily_metrics": pl.DataFrame(daily_rows),
        "training_load_daily": pl.DataFrame(load_rows),
        "wellness_daily": pl.DataFrame(wellness_rows),
        "training_sessions": pl.DataFrame(session_rows),
        "player_registry": registry,
        "injury_episodes": episodes,
        "gold_features": pl.DataFrame(gold_rows),
    }
