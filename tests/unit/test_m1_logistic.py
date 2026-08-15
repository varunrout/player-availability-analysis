from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    M1F1Config,
    build_m1_f1_figures,
    run_m1_f1,
)
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _config() -> M1F1Config:
    return M1F1Config(
        experiment_id="EXP-003",
        model_id="M1-F1",
        data_version="subjective_v1",
        target="injury_next_7d",
        primary_horizon_days=7,
        burn_in_days=28,
        feature_set="F1",
        regularisation_c_grid=(0.001, 0.01, 0.1, 1.0, 10.0),
        solver="lbfgs",
        penalty="l2",
        max_iterations=5000,
        class_weight=None,
        alert_review_rates=(0.01, 0.025, 0.05),
        bootstrap_iterations=10,
        random_seed=20260815,
        reliability_bins=5,
        m0_global_brier=0.003405,
        m0_global_log_loss=0.030310,
        m0_global_average_precision=0.003222,
        m0_global_roc_auc=0.5,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_m1_f1_runs_full_development_contract_without_test_access() -> None:
    features, episodes = _inputs()

    result = run_m1_f1(features=features, episodes=episodes, config=_config())

    assert result.summary["status"] == "PASS"
    assert result.summary["feature_count"] == 9
    assert result.summary["selected_regularisation_c"] in _config().regularisation_c_grid
    assert result.summary["posthoc_calibration_selected"] is False
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert result.predictions["partition"].unique().to_list() == ["validation"]
    assert result.predictions["predicted_probability"].is_between(0.0, 1.0).all()
    support = result.tables["cohort_and_split_support"]
    test_support = support.filter(pl.col("partition") == "test").row(0, named=True)
    assert test_support["performance_evaluated"] is False
    assert test_support["predictions_persisted"] is False
    assert result.tables["hyperparameter_results"].height == 5
    assert result.tables["coefficient_estimates"].height > 10
    assert result.tables["rolling_origin_results"].height == 4
    assert result.tables["unseen_player_results"].height == 2
    assert result.tables["model_findings"].filter(pl.col("status") == "FAIL").is_empty()

    figures = build_m1_f1_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_m1_f1_is_invariant_to_locked_test_feature_changes() -> None:
    features, episodes = _inputs()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_m1_f1(features=features, episodes=episodes, config=_config())
    modified = run_m1_f1(features=changed, episodes=episodes, config=_config())

    assert original.parameters == modified.parameters
    assert original.predictions.equals(modified.predictions)
    assert original.tables["hyperparameter_results"].equals(
        modified.tables["hyperparameter_results"]
    )


def test_m1_f1_notebook_is_output_free_and_has_no_writer() -> None:
    path = Path("notebooks/modelling/01_m1_f1_logistic.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)

    assert "write_m1_f1_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
