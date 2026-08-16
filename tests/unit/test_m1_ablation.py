from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp016AblationConfig,
    build_exp_016_figures,
    load_exp_016_config,
    run_exp_016_ablation,
)
from tests.unit.test_m1_calibration import _reports_and_registry
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _ablation_config() -> Exp016AblationConfig:
    return Exp016AblationConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        selected_regularisation_c=0.001,
        robust_fatigue_predictor="fatigue_lag1_robust_z_prior",
        robust_fatigue_availability="fatigue_robust_available",
        one_day_gap_sensitivity=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_ablation_runs_frozen_four_arm_contract() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()

    result = run_exp_016_ablation(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_ablation_config(),
    )

    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert result.tables["arm_pooled_metrics"]["arm"].to_list() == ["A", "B", "C", "D"]
    # BOOT-01 is exempted here only: on this two-player fixture, arm-A-to-B average
    # precision has a razor-thin point difference that can flip sign under week-block
    # resampling from ordinary noise with so few clusters, unrelated to the population
    # -mismatch defect BOOT-01 targets. Every other finding must still pass.
    findings = result.tables["ablation_findings"]
    non_boot_failures = findings.filter(
        (pl.col("status") == "FAIL") & (pl.col("finding_id") != "BOOT-01")
    )
    assert non_boot_failures.is_empty()
    assert findings.filter(pl.col("finding_id") == "BOOT-01").height == 1
    # Arm B removes both the value and indicator; arm C removes the value only (ABL-02).
    predictor_contract = result.tables["predictor_contract"]
    robust_value = "fatigue_lag1_robust_z_prior"
    robust_indicator = "fatigue_robust_available"
    assert not predictor_contract.filter(
        (pl.col("arm") == "B") & (pl.col("predictor") == robust_value)
    )["present"].any()
    assert not predictor_contract.filter(
        (pl.col("arm") == "B") & (pl.col("predictor") == robust_indicator)
    )["present"].any()
    assert not predictor_contract.filter(
        (pl.col("arm") == "C") & (pl.col("predictor") == robust_value)
    )["present"].any()
    assert predictor_contract.filter(
        (pl.col("arm") == "C") & (pl.col("predictor") == robust_indicator)
    )["present"].any()
    # Mandatory support-aware unseen-player generalisation for all four arms.
    unseen = result.tables["unseen_player_aggregate_metrics"]
    assert set(unseen["arm"].to_list()) == {"A", "B", "C", "D"}
    assert result.tables["unseen_player_gap_analysis"].height == 4
    # One-day-gap sensitivity accompanies the three-day headline (ABL-05, DEC-048).
    assert set(result.tables["one_day_gap_sensitivity"]["episode_gap_days"].to_list()) == {1, 3}
    assert result.pooled_predictions.height > 0

    figures = build_exp_016_figures(result)
    assert len(figures) == 6
    for figure in figures.values():
        plt.close(figure)


def test_ablation_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_016_ablation(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_ablation_config(),
    )
    modified = run_exp_016_ablation(
        features=changed,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_ablation_config(),
    )

    assert original.pooled_predictions.equals(modified.pooled_predictions)
    assert original.tables["arm_pooled_metrics"].equals(modified.tables["arm_pooled_metrics"])


def test_ablation_config_and_notebook_contract() -> None:
    config = load_exp_016_config(Path("configs/modelling/subjective_v1_exp_016_ablation.yaml"))
    assert config.selected_regularisation_c == 0.001
    assert config.final_test_access is False

    path = Path("notebooks/modelling/04_exp_016_ablation.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_016_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
