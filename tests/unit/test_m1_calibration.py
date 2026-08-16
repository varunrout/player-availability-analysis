from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp009CalibrationConfig,
    build_exp_009_figures,
    load_exp_009_config,
    run_exp_009_calibration,
)
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _calibration_config() -> Exp009CalibrationConfig:
    return Exp009CalibrationConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        feature_set="F3",
        selected_regularisation_c=0.001,
        calibration_methods=("raw", "platt", "isotonic"),
        inner_cv_folds=2,
        robust_fatigue_predictor="fatigue_lag1_robust_z_prior",
        robust_fatigue_availability="fatigue_robust_available",
        reliability_bins=5,
        minimum_reliability_positive_days=1,
        one_day_gap_sensitivity=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def _reports_and_registry() -> tuple[pl.DataFrame, pl.DataFrame]:
    registry = pl.DataFrame(
        [
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "observation_start": date(2020, 1, 1),
                "observation_end": date(2021, 12, 31),
            },
            {
                "player_id": "P2",
                "team_id": "TeamB",
                "observation_start": date(2020, 1, 1),
                "observation_end": date(2021, 12, 31),
            },
        ]
    )
    payload = json.dumps({"type": json.dumps({"knee": "minor"})})
    reports = pl.DataFrame(
        [
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "event_date": date(2020, 8, 10),
                "source_payload_json": payload,
            },
            {
                "player_id": "P2",
                "team_id": "TeamB",
                "event_date": date(2021, 3, 10),
                "source_payload_json": payload,
            },
            {
                "player_id": "P1",
                "team_id": "TeamA",
                "event_date": date(2021, 9, 10),
                "source_payload_json": payload,
            },
        ]
    )
    return reports, registry


def test_calibration_runs_frozen_three_arm_contract() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()

    result = run_exp_009_calibration(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_calibration_config(),
    )

    assert result.summary["status"] == "PASS"
    assert result.summary["calibration_arms"] == ["raw", "platt", "isotonic"]
    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    assert result.tables["arm_pooled_metrics"]["arm"].to_list() == ["raw", "platt", "isotonic"]
    assert result.tables["calibration_findings"].filter(pl.col("status") == "FAIL").is_empty()
    # Platt is a monotone map of the raw probabilities, so ranking is preserved (CAL-04).
    assert (
        result.tables["calibration_findings"]
        .filter(pl.col("finding_id") == "CAL-04")
        .item(0, "status")
        == "PASS"
    )
    # One-day-gap sensitivity present alongside the three-day headline (CAL-07, DEC-048).
    assert set(result.tables["one_day_gap_sensitivity"]["episode_gap_days"].to_list()) == {1, 3}
    assert result.tables["sparse_predictor_audit"].height > 0
    assert result.pooled_predictions.height > 0

    figures = build_exp_009_figures(result)
    assert len(figures) == 9
    for figure in figures.values():
        plt.close(figure)


def test_calibration_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_009_calibration(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_calibration_config(),
    )
    modified = run_exp_009_calibration(
        features=changed,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_calibration_config(),
    )

    assert original.pooled_predictions.equals(modified.pooled_predictions)
    assert original.tables["arm_pooled_metrics"].equals(modified.tables["arm_pooled_metrics"])


def test_calibration_config_and_notebook_contract() -> None:
    config = load_exp_009_config(Path("configs/modelling/subjective_v1_exp_009_calibration.yaml"))
    assert config.feature_set == "F3"
    assert config.selected_regularisation_c == 0.001
    assert config.calibration_methods == ("raw", "platt", "isotonic")
    assert config.final_test_access is False

    path = Path("notebooks/modelling/03_exp_009_calibration.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_009_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
