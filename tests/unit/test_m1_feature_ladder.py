from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    M1FeatureLadderConfig,
    build_m1_feature_ladder_figures,
    load_m1_feature_ladder_config,
    run_m1_feature_ladder,
)
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _ladder_config() -> M1FeatureLadderConfig:
    return M1FeatureLadderConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        feature_sets=("F2", "F3"),
        include_f1_reference=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_feature_ladder_runs_frozen_cumulative_contract() -> None:
    features, episodes = _inputs()

    result = run_m1_feature_ladder(features=features, episodes=episodes, config=_ladder_config())

    assert result.summary["status"] == "PASS"
    assert result.summary["feature_counts"] == {"F1": 9, "F2": 17, "F3": 23}
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert result.tables["feature_set_comparison"]["feature_set"].to_list() == [
        "F1",
        "F2",
        "F3",
    ]
    assert result.tables["feature_availability"].height == 23
    assert result.tables["paired_bootstrap_differences"].height == 8
    assert result.tables["ladder_findings"].filter(pl.col("status") == "FAIL").is_empty()
    for feature_set, model_result in result.model_results.items():
        assert model_result.predictions["partition"].unique().to_list() == ["validation"]
        assert model_result.summary["feature_count"] == len(model_result.parameters["features"])
        assert feature_set == model_result.summary["model_id"].removeprefix("M1-")

    figures = build_m1_feature_ladder_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_feature_ladder_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_m1_feature_ladder(features=features, episodes=episodes, config=_ladder_config())
    modified = run_m1_feature_ladder(features=changed, episodes=episodes, config=_ladder_config())

    for feature_set in ("F1", "F2", "F3"):
        assert (
            original.model_results[feature_set].parameters
            == modified.model_results[feature_set].parameters
        )
        assert original.model_results[feature_set].predictions.equals(
            modified.model_results[feature_set].predictions
        )


def test_feature_ladder_config_and_notebook_contract() -> None:
    config = load_m1_feature_ladder_config(
        Path("configs/modelling/subjective_v1_m1_feature_ladder.yaml")
    )
    assert config.feature_sets == ("F2", "F3")
    assert config.final_test_access is False

    path = Path("notebooks/modelling/02_m1_feature_ladder.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_m1_feature_ladder_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
