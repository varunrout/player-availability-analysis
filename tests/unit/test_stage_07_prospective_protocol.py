from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_07_prospective_protocol import (
    build_stage_07_figures,
    run_stage_07_prospective_protocol,
)
from player_availability.outcomes import build_player_day_labels


def test_stage_07_freezes_protocol_without_model_performance() -> None:
    features, episodes = _inputs()

    result = run_stage_07_prospective_protocol(features=features, episodes=episodes)

    assert result.summary["status"] == "PASS"
    assert result.summary["model_count"] == 0
    assert result.summary["performance_metric_count"] == 0
    assert result.summary["final_test_performance_accessed"] is False
    assert result.tables["partition_support"]["partition"].to_list() == [
        "train",
        "validation",
        "test",
    ]
    assert result.tables["leakage_findings"].filter(pl.col("status") == "FAIL").is_empty()
    figures = build_stage_07_figures(result)
    assert len(figures) == 8
    for figure in figures.values():
        plt.close(figure)


def test_stage_07_lagged_features_are_strictly_prior_and_future_invariant() -> None:
    features, episodes = _inputs()
    result = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    rebuilt = result.tables["_prediction_features"]
    target_date = date(2020, 2, 10)
    source_prior = features.filter(
        (pl.col("player_id") == "P1")
        & (pl.col("prediction_date") == target_date - timedelta(days=1))
    ).row(0, named=True)
    row = rebuilt.filter(
        (pl.col("player_id") == "P1") & (pl.col("prediction_date") == target_date)
    ).row(0, named=True)

    assert row["fatigue_lag1"] == source_prior["fatigue"]
    assert row["readiness_lag1"] == source_prior["readiness"]
    finding = result.tables["leakage_findings"].filter(
        pl.col("check_id") == "future_append_invariance"
    )
    assert finding.item(0, "status") == "PASS"


def test_stage_07_contract_excludes_same_day_wellness_and_identity() -> None:
    features, episodes = _inputs()
    result = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    allowed = set(result.tables["predictor_contract"]["predictor"].to_list())

    assert not {"player_id", "team_id", "prediction_date", "fatigue", "readiness"} & allowed
    assert {"fatigue_lag1", "readiness_lag1", "session_recorded"} <= allowed
    assert (
        result.tables["split_manifest"]
        .filter(pl.col("model_performance_allowed_stage_07"))
        .is_empty()
    )


def test_stage_07_notebook_contract_has_no_output_writer() -> None:
    path = Path("notebooks/analysis/07_prospective_protocol.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)

    assert "write_stage_07_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert len(notebook["cells"]) == 7


def _inputs() -> tuple[pl.DataFrame, pl.DataFrame]:
    start = date(2020, 1, 1)
    end = date(2021, 12, 31)
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
    episodes = pl.DataFrame(
        [
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": date(2020, 8, 10),
                "episode_end": date(2020, 8, 12),
            },
            {
                "player_id": "P2",
                "team_id": "TeamB",
                "episode_start": date(2021, 3, 10),
                "episode_end": date(2021, 3, 12),
            },
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "episode_start": date(2021, 9, 10),
                "episode_end": date(2021, 9, 12),
            },
        ]
    )
    labels = build_player_day_labels(registry, episodes)
    rows = []
    for source in labels.iter_rows(named=True):
        day = source["prediction_date"]
        assert isinstance(day, date)
        offset = (day - start).days
        session_count = 1 if offset % 4 else 0
        load = float(100 + (offset % 17) * 20) if session_count else 0.0
        duration = float(40 + offset % 70) if session_count else 0.0
        srpe = load * 0.98 if session_count else 0.0
        prior = [max(offset - back, 0) for back in range(0, 28)]
        rows.append(
            {
                **source,
                "session_count": session_count,
                "daily_load": load,
                "session_duration_minutes": duration,
                "session_srpe": srpe,
                "daily_load_sum_7d": sum(
                    float(100 + (value % 17) * 20) if value % 4 else 0.0 for value in prior[:7]
                ),
                "daily_load_sum_28d": sum(
                    float(100 + (value % 17) * 20) if value % 4 else 0.0 for value in prior
                ),
                "session_duration_sum_7d": sum(
                    float(40 + value % 70) if value % 4 else 0.0 for value in prior[:7]
                ),
                "session_duration_sum_28d": sum(
                    float(40 + value % 70) if value % 4 else 0.0 for value in prior
                ),
                "session_srpe_sum_7d": sum(
                    (float(100 + (value % 17) * 20) * 0.98) if value % 4 else 0.0
                    for value in prior[:7]
                ),
                "session_srpe_sum_28d": sum(
                    (float(100 + (value % 17) * 20) * 0.98) if value % 4 else 0.0 for value in prior
                ),
                "wellness_report_present": offset % 3 != 0,
                "fatigue": float(2 + offset % 3) if offset % 3 != 0 else None,
                "readiness": float(6 + offset % 4) if offset % 3 != 0 else None,
            }
        )
    return pl.DataFrame(rows), episodes
