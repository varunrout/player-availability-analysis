from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp019AlertBudgetConfig,
    build_exp_019_figures,
    load_exp_019_config,
    run_exp_019_alert_budget,
)
from tests.unit.test_m1_calibration import _reports_and_registry
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _alert_budget_config() -> Exp019AlertBudgetConfig:
    return Exp019AlertBudgetConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        selected_regularisation_c=0.001,
        top_n_values=(1, 3, 5),
        capacity_sensitivity_rates=(0.05, 0.10, 0.20),
        one_day_gap_sensitivity=True,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_alert_budget_runs_frozen_operating_points() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()

    result = run_exp_019_alert_budget(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_alert_budget_config(),
    )

    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    operating_points = result.tables["alert_budget_results"]
    assert set(operating_points["operating_point_type"].unique().to_list()) == {
        "top_n_per_team_day",
        "percentile",
        "capacity_sensitivity",
    }
    assert set(
        operating_points.filter(pl.col("operating_point_type") == "top_n_per_team_day")[
            "operating_point_value"
        ].to_list()
    ) == {1.0, 3.0, 5.0}
    # Every operating point reports its false-alert burden and support counts inline (ALERT-03/04).
    for column in ("false_alerts_per_captured_onset", "represented_onsets", "eligible_player_days"):
        assert column in operating_points.columns
    # Top-N never exceeds team-day size (ALERT-02): alert count never exceeds N per squad per day.
    findings = result.tables["alert_findings"]
    non_gap_failures = findings.filter(pl.col("status") == "FAIL")
    assert non_gap_failures.is_empty(), non_gap_failures
    assert set(result.tables["one_day_gap_sensitivity"]["episode_gap_days"].to_list()) == {1}
    assert result.pooled_predictions.height > 0

    figures = build_exp_019_figures(result)
    assert len(figures) == 5
    for figure in figures.values():
        plt.close(figure)


def test_alert_budget_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    reports, registry = _reports_and_registry()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_019_alert_budget(
        features=features,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_alert_budget_config(),
    )
    modified = run_exp_019_alert_budget(
        features=changed,
        episodes=episodes,
        injury_reports=reports,
        player_registry=registry,
        config=_alert_budget_config(),
    )

    assert original.pooled_predictions.equals(modified.pooled_predictions)
    assert original.tables["alert_budget_results"].equals(modified.tables["alert_budget_results"])


def test_alert_budget_config_and_notebook_contract() -> None:
    config = load_exp_019_config(Path("configs/modelling/subjective_v1_exp_019_alert_budget.yaml"))
    assert config.top_n_values == (1, 3, 5)
    assert config.capacity_sensitivity_rates == (0.05, 0.10, 0.20)
    assert config.final_test_access is False

    path = Path("notebooks/modelling/07_exp_019_alert_budget.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_019_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
