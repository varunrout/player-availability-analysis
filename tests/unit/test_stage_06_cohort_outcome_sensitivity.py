from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_06_cohort_outcome_sensitivity import (
    build_stage_06_figures,
    run_stage_06_cohort_outcome_sensitivity,
)
from player_availability.outcomes import build_injury_episodes, build_player_day_labels


def test_stage_06_builds_nested_cohorts_without_models_or_splits() -> None:
    reports, registry, features = _inputs()

    result = run_stage_06_cohort_outcome_sensitivity(
        injury_reports=reports,
        player_registry=registry,
        features=features,
    )

    assert result.summary["status"] == "PASS"
    assert result.summary["model_count"] == 0
    assert result.summary["split_count"] == 0
    scenarios = result.tables["cohort_scenario_summary"]
    counts = dict(scenarios.select("scenario_id", "eligible_player_days").iter_rows())
    assert counts["C0"] >= counts["C1"] >= counts["C2"] >= counts["C3"]
    registry_table = result.tables["scenario_registry"]
    assert (
        registry_table.filter(pl.col("scenario_id") == "C6").item(0, "scenario_type")
        == "event_support_sensitivity"
    )
    assert result.tables["cohort_outcome_findings"].filter(pl.col("status") == "FAIL").is_empty()
    figures = build_stage_06_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_stage_06_history_is_strictly_prior_to_prediction_date() -> None:
    reports, registry, features = _inputs()
    result = run_stage_06_cohort_outcome_sensitivity(
        injury_reports=reports,
        player_registry=registry,
        features=features,
    )
    history = result.tables["_history"]
    target_date = date(2021, 1, 9)
    row = history.filter(
        (pl.col("player_id") == "P1") & (pl.col("prediction_date") == target_date)
    ).row(0, named=True)

    expected_reports = features.filter(
        (pl.col("player_id") == "P1") & (pl.col("prediction_date") < target_date)
    )["wellness_report_present"].sum()
    assert row["prior_calendar_days"] == 8
    assert row["prior_wellness_reports_total"] == expected_reports


def test_stage_06_rebuilds_all_gap_horizon_combinations() -> None:
    reports, registry, features = _inputs()
    result = run_stage_06_cohort_outcome_sensitivity(
        injury_reports=reports,
        player_registry=registry,
        features=features,
    )
    summary = result.tables["episode_gap_horizon_summary"]

    assert summary.select("gap_days", "horizon_days").unique().height == 9
    assert summary["gap_days"].unique().sort().to_list() == [1, 3, 7]
    assert summary["horizon_days"].unique().sort().to_list() == [3, 7, 14]


def test_stage_06_notebook_contract_has_no_output_writer() -> None:
    path = Path("notebooks/analysis/06_cohort_outcome_sensitivity.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)

    assert "write_stage_06_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert len(notebook["cells"]) == 7


def _inputs() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    start = date(2021, 1, 1)
    end = start + timedelta(days=159)
    registry = pl.DataFrame(
        [
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "observation_start": start,
                "observation_end": end,
            },
            {
                "player_id": "P2",
                "team_id": "TeamB",
                "observation_start": start,
                "observation_end": end,
            },
        ]
    )
    reports = pl.DataFrame(
        [
            _report("R1", "P1", "TeamA", start + timedelta(days=60), "Knee"),
            _report("R2", "P1", "TeamA", start + timedelta(days=62), "Knee"),
            _report("R3", "P1", "TeamA", start + timedelta(days=110), "Ankle"),
            _report("R4", "P2", "TeamB", start + timedelta(days=90), "Hip"),
        ]
    )
    primary_episodes = build_injury_episodes(reports, gap_days=3)
    labels = build_player_day_labels(registry, primary_episodes)
    rows = []
    for source in labels.iter_rows(named=True):
        day = source["prediction_date"]
        assert isinstance(day, date)
        offset = (day - start).days
        rows.append(
            {
                **source,
                "wellness_report_present": offset % 3 != 0,
                "session_count": 1 if offset % 4 else 0,
                "daily_load": float(100 + offset % 20) if offset % 4 else 0.0,
            }
        )
    return reports, registry, pl.DataFrame(rows)


def _report(
    report_id: str, player_id: str, team_id: str, event_date: date, location: str
) -> dict[str, object]:
    payload = {"type": json.dumps({location: "minor"})}
    return {
        "report_id": report_id,
        "player_id": player_id,
        "team_id": team_id,
        "event_date": event_date,
        "source_payload_json": json.dumps(payload),
    }
