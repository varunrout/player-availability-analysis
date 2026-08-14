from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from player_availability.analysis.stage_01_outcome_eda import (
    build_stage_01_figures,
    run_stage_01_outcome_eda,
)
from player_availability.outcomes import build_injury_episodes, build_player_day_labels


def test_stage_01_reproduces_primary_episodes_and_labels() -> None:
    reports = _reports()
    registry = _registry()
    episodes = build_injury_episodes(reports, gap_days=3)
    labels = build_player_day_labels(registry, episodes)

    result = run_stage_01_outcome_eda(
        injury_reports=reports,
        stored_episodes=episodes,
        player_registry=registry,
        gold_labels=labels,
    )

    assert result.summary["status"] == "PASS"
    sensitivity = result.tables["episode_gap_sensitivity"]
    assert sensitivity["episode_count"].to_list() == [4, 3, 2]
    assert sensitivity["onset_day_count"].to_list() == [4, 3, 2]
    assert result.tables["label_reproduction"].filter(pl.col("status") == "FAIL").is_empty()
    assert result.tables["horizon_overlap"].filter(pl.col("status") == "FAIL").is_empty()
    figures = build_stage_01_figures(result)
    assert len(figures) == 8
    for figure in figures.values():
        figure.clear()


def test_stage_01_fails_when_gold_label_differs() -> None:
    reports = _reports()
    registry = _registry()
    episodes = build_injury_episodes(reports, gap_days=3)
    labels = build_player_day_labels(registry, episodes).with_columns(
        pl.when(
            (pl.col("player_id") == "TeamA-1") & (pl.col("prediction_date") == date(2021, 1, 1))
        )
        .then(~pl.col("injury_next_3d"))
        .otherwise(pl.col("injury_next_3d"))
        .alias("injury_next_3d")
    )

    result = run_stage_01_outcome_eda(
        injury_reports=reports,
        stored_episodes=episodes,
        player_registry=registry,
        gold_labels=labels,
    )

    assert result.summary["status"] == "FAIL"
    mismatch = result.tables["label_reproduction"].filter(pl.col("field") == "injury_next_3d")
    assert mismatch.item(0, "mismatch_count") == 1


def test_stage_01_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/01_outcome_eda.ipynb").read_text(encoding="utf-8")

    assert "write_stage_01_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _reports() -> pl.DataFrame:
    rows = [
        _report("event-1", "TeamA-1", "TeamA", date(2021, 1, 2), {"ankle": "minor"}),
        _report("event-2", "TeamA-1", "TeamA", date(2021, 1, 4), {"ankle": "major"}),
        _report("event-3", "TeamA-1", "TeamA", date(2021, 1, 9), {"ankle": "minor"}),
        _report("event-4", "TeamA-2", "TeamA", date(2021, 1, 5), {"knee": "minor"}),
    ]
    return pl.DataFrame(rows).with_columns(pl.col("event_date").cast(pl.Date))


def _report(
    event_id: str,
    player_id: str,
    team_id: str,
    event_date: date,
    injury_type: dict[str, str],
) -> dict[str, object]:
    payload = {"type": json.dumps(injury_type)}
    return {
        "event_id": event_id,
        "player_id": player_id,
        "team_id": team_id,
        "event_date": event_date,
        "event_type": "injury",
        "source_file": "injury.json",
        "source_row_number": int(event_id.split("-")[-1]),
        "source_payload_json": json.dumps(payload),
    }


def _registry() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player_id": ["TeamA-1", "TeamA-2", "TeamA-3"],
            "team_id": ["TeamA", "TeamA", "TeamA"],
            "observation_start": [date(2021, 1, 1)] * 3,
            "observation_end": [date(2021, 1, 20)] * 3,
        }
    ).with_columns(
        pl.col("observation_start").cast(pl.Date),
        pl.col("observation_end").cast(pl.Date),
    )
