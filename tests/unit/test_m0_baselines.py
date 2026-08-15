from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import M0Config, build_m0_figures, run_m0_baselines
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _config() -> M0Config:
    return M0Config(
        experiment_id="EXP-002",
        data_version="subjective_v1",
        target="injury_next_7d",
        primary_horizon_days=7,
        burn_in_days=28,
        load_predictor="daily_load_sum_7d_log1p",
        load_threshold_quantile=0.95,
        alert_review_rates=(0.01, 0.025, 0.05),
        bootstrap_iterations=10,
        random_seed=20260815,
        final_test_access=False,
    )


def test_m0_runs_development_only_and_builds_expected_artifacts() -> None:
    features, episodes = _inputs()

    result = run_m0_baselines(features=features, episodes=episodes, config=_config())

    assert result.summary["status"] == "PASS"
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    support = result.tables["cohort_and_split_support"]
    test_support = support.filter(pl.col("partition") == "test").row(0, named=True)
    assert test_support["performance_evaluated"] is False
    assert test_support["predictions_persisted"] is False
    assert result.predictions["baseline_id"].n_unique() == 2
    assert result.predictions.height == 2 * result.summary["validation_player_days"]
    assert set(result.tables) == {
        "dataset_manifest",
        "cohort_and_split_support",
        "baseline_definitions",
        "validation_metrics",
        "alert_budget_results",
        "event_capture_results",
        "bootstrap_intervals",
        "baseline_findings",
    }
    intervals = result.tables["bootstrap_intervals"]
    assert intervals.filter(pl.col("valid_iterations") <= 0).is_empty()
    assert intervals["median"].is_nan().sum() == 0

    figures = build_m0_figures(result)
    assert len(figures) == 6
    for figure in figures.values():
        plt.close(figure)


def test_m0_global_score_is_constant_and_not_arbitrarily_ranked() -> None:
    features, episodes = _inputs()

    result = run_m0_baselines(features=features, episodes=episodes, config=_config())

    global_predictions = result.predictions.filter(pl.col("baseline_id") == "M0_GLOBAL_PREVALENCE")
    assert global_predictions["predicted_probability"].n_unique() == 1
    global_alerts = result.tables["alert_budget_results"].filter(
        pl.col("baseline_id") == "M0_GLOBAL_PREVALENCE"
    )
    assert set(global_alerts["status"]) == {"NOT_ESTIMABLE_CONSTANT_SCORE"}
    assert global_alerts["alert_count"].sum() == 0


def test_m0_parameters_do_not_change_when_locked_test_values_change() -> None:
    features, episodes = _inputs()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_m0_baselines(features=features, episodes=episodes, config=_config())
    modified = run_m0_baselines(features=changed, episodes=episodes, config=_config())

    assert original.parameters == modified.parameters
    assert original.predictions.equals(modified.predictions)


def test_m0_notebook_is_output_free_and_has_no_writer() -> None:
    path = Path("notebooks/modelling/00_m0_baselines.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)

    assert "write_m0_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
