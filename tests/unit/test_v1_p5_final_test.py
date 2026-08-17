from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    V1P5FinalTestConfig,
    build_v1_p5_figures,
    load_v1_p5_config,
    run_v1_p5_final_test,
)
from player_availability.modelling.v1_p5_final_test import PREREGISTRATION_COMMIT
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _v1_p5_config() -> V1P5FinalTestConfig:
    return V1P5FinalTestConfig(
        data_version="subjective_v1",
        target="injury_next_7d",
        primary_horizon_days=7,
        max_iterations=5000,
        reliability_bins=5,
        preregistration_commit=PREREGISTRATION_COMMIT,
    )


def test_v1_p5_runs_single_use_final_test_evaluation() -> None:
    features, episodes = _inputs()

    result = run_v1_p5_final_test(features=features, episodes=episodes, config=_v1_p5_config())

    assert result.summary["final_test_predictions_created"] is True
    assert result.summary["final_test_performance_accessed"] is True
    assert result.summary["preregistration_commit"] == PREREGISTRATION_COMMIT
    thresholds = result.tables["development_thresholds"]
    assert set(thresholds["review_rate"].to_list()) == {0.025, 0.05}
    operating_points = result.tables["operating_point_results"]
    assert set(operating_points["review_rate"].to_list()) == {0.025, 0.05}
    for column in ("probability_threshold", "represented_onsets", "eligible_player_days"):
        assert column in operating_points.columns
    claims = result.tables["claims"]
    assert set(claims["claim_id"].to_list()) == {"C1", "C2", "C3"}
    findings = result.tables["final_test_findings"]
    assert findings.filter(pl.col("status") == "FAIL").is_empty(), findings
    embargo = result.tables["embargo_register"]
    assert embargo.height == 2

    figures = build_v1_p5_figures(result)
    assert len(figures) == 2
    for figure in figures.values():
        plt.close(figure)


def test_v1_p5_config_and_notebook_contract() -> None:
    config = load_v1_p5_config(Path("configs/modelling/subjective_v1_p5_final_test.yaml"))
    assert config.preregistration_commit == PREREGISTRATION_COMMIT
    assert config.primary_horizon_days == 7

    path = Path("notebooks/modelling/09_v1_p5_final_test.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_v1_p5_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
