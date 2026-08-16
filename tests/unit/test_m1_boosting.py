from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp008BoostingConfig,
    build_exp_008_figures,
    load_exp_008_config,
    run_exp_008_boosting,
)
from tests.unit.test_m1_calibration import _reports_and_registry
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _boosting_config() -> Exp008BoostingConfig:
    grid = tuple(
        {
            "max_leaf_nodes": max_leaf_nodes,
            "learning_rate": learning_rate,
            "min_samples_leaf": min_samples_leaf,
            "l2_regularization": l2_regularization,
        }
        for max_leaf_nodes in (3, 7)
        for learning_rate in (0.01, 0.05)
        for min_samples_leaf in (5, 10)
        for l2_regularization in (1.0, 10.0)
    )
    return Exp008BoostingConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        predictor_feature_set="F1",
        grid_combinations=grid,
        max_iter_ceiling=20,
        early_stopping_checkpoint_step=5,
        one_day_gap_sensitivity=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_boosting_runs_frozen_boosted_vs_f1_contract() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()

    result = run_exp_008_boosting(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_boosting_config(),
    )

    assert result.summary["status"] == "PASS"
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert set(result.tables["arm_pooled_metrics"]["arm"].to_list()) == {"boosted", "f1_logistic"}
    assert result.tables["boosting_findings"].filter(pl.col("status") == "FAIL").is_empty()
    assert result.tables["hyperparameter_selection_records"].height == 16 * (20 // 5)
    assert (
        result.pooled_predictions.filter(pl.col("arm") == "boosted")["predicted_probability"]
        .is_between(0.0, 1.0)
        .all()
    )
    assert set(result.tables["unseen_player_aggregate_metrics"]["arm"].to_list()) == {
        "boosted",
        "f1_logistic",
    }
    assert set(result.tables["one_day_gap_sensitivity"]["episode_gap_days"].to_list()) == {1, 3}
    assert result.tables["training_validation_gap"].height == 1
    assert set(
        result.tables["missingness_sensitivity_native_handling"]["missing_data_treatment"].to_list()
    ) == {"imputed_matches_f1", "native_missing_handling"}

    figures = build_exp_008_figures(result)
    assert len(figures) == 7
    for figure in figures.values():
        plt.close(figure)


def test_boosting_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_008_boosting(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_boosting_config(),
    )
    modified = run_exp_008_boosting(
        features=changed,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_boosting_config(),
    )

    assert original.pooled_predictions.equals(modified.pooled_predictions)
    assert original.tables["arm_pooled_metrics"].equals(modified.tables["arm_pooled_metrics"])


def test_boosting_config_and_notebook_contract() -> None:
    config = load_exp_008_config(Path("configs/modelling/subjective_v1_exp_008_boosting.yaml"))
    assert config.predictor_feature_set == "F1"
    assert len(config.grid_combinations) == 16
    assert config.final_test_access is False

    path = Path("notebooks/modelling/06_exp_008_boosting.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_008_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
