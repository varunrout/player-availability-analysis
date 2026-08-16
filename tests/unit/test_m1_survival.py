from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp007SurvivalConfig,
    build_exp_007_figures,
    load_exp_007_config,
    run_exp_007_survival,
)
from tests.unit.test_m1_calibration import _reports_and_registry
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _survival_config() -> Exp007SurvivalConfig:
    return Exp007SurvivalConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        predictor_feature_set="F1",
        penalizer_grid=(0.001, 0.1, 1.0),
        one_day_gap_sensitivity=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_survival_runs_frozen_cox_vs_f1_contract() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()

    result = run_exp_007_survival(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_survival_config(),
    )

    assert result.summary["status"] == "PASS"
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert result.summary["coefficient_variance_type"] == "model_based_naive_not_cluster_robust"
    assert set(result.tables["arm_pooled_metrics"]["arm"].to_list()) == {"cox", "f1_logistic"}
    assert result.tables["survival_findings"].filter(pl.col("status") == "FAIL").is_empty()
    # Converted probabilities lie in [0, 1] for every pooled row (COX-06).
    assert (
        result.pooled_predictions.filter(pl.col("arm") == "cox")["predicted_probability"]
        .is_between(0.0, 1.0)
        .all()
    )
    # Mandatory support-aware unseen-player generalisation, both clock variants for Cox
    # (COX-09): reset_clock is the valid leave-one-player-out result, own_clock is
    # retained only as a leakage diagnostic contrast, never a competing headline figure.
    unseen = result.tables["unseen_player_aggregate_metrics"]
    variants = set(zip(unseen["arm"].to_list(), unseen["clock"].to_list(), strict=True))
    assert variants == {
        ("cox", "reset_clock"),
        ("cox", "own_clock"),
        ("f1_logistic", "not_applicable"),
    }
    assert (
        unseen.filter((pl.col("arm") == "cox") & (pl.col("clock") == "reset_clock")).row(
            0, named=True
        )["role"]
        == "primary_leave_one_player_out_result"
    )
    assert (
        unseen.filter((pl.col("arm") == "cox") & (pl.col("clock") == "own_clock")).row(
            0, named=True
        )["role"]
        == "leakage_diagnostic_contrast"
    )
    assert (
        result.tables["survival_findings"]
        .filter(pl.col("finding_id") == "COX-09")
        .row(0, named=True)["status"]
        == "PASS"
    )
    # One-day-gap sensitivity accompanies the three-day headline (COX-08, DEC-048).
    assert set(result.tables["one_day_gap_sensitivity"]["episode_gap_days"].to_list()) == {1, 3}
    # Coefficients cover the frozen F1 predictor contract, plus any missing-indicator
    # columns the shared imputer adds when a fold's training data has missing values.
    assert result.tables["coefficient_estimates"].height >= 9
    assert result.tables["proportional_hazards_per_covariate_check"].height == (
        result.tables["coefficient_estimates"].height
    )

    figures = build_exp_007_figures(result)
    assert len(figures) == 8
    for figure in figures.values():
        plt.close(figure)


def test_survival_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_007_survival(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_survival_config(),
    )
    modified = run_exp_007_survival(
        features=changed,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_survival_config(),
    )

    assert original.pooled_predictions.equals(modified.pooled_predictions)
    assert original.tables["arm_pooled_metrics"].equals(modified.tables["arm_pooled_metrics"])


def test_survival_config_and_notebook_contract() -> None:
    config = load_exp_007_config(Path("configs/modelling/subjective_v1_exp_007_survival.yaml"))
    assert config.predictor_feature_set == "F1"
    assert config.final_test_access is False

    path = Path("notebooks/modelling/05_exp_007_survival.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_007_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
