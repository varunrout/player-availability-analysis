from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import polars as pl
from matplotlib import pyplot as plt

from player_availability.modelling import (
    Exp018ExplanationConfig,
    build_exp_018_figures,
    load_exp_018_config,
    run_exp_018_explanation,
)
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _explanation_config() -> Exp018ExplanationConfig:
    return Exp018ExplanationConfig(
        base_config=replace(_config(), bootstrap_iterations=5),
        selected_regularisation_c=0.001,
        posthoc_calibration_selection=False,
        final_test_access=False,
    )


def test_explanation_runs_frozen_stability_audit() -> None:
    features, episodes = _inputs()

    result = run_exp_018_explanation(
        features=features, episodes=episodes, config=_explanation_config()
    )

    assert result.summary["final_test_rows_evaluated"] == 0
    assert result.summary["final_test_predictions_created"] is False
    stability = result.tables["coefficient_stability"]
    assert stability.height == 9
    # Attribution reconstructs the model's own logit exactly (EXPL-03).
    exactness = result.tables["exactness_check"]
    assert exactness.height > 0
    assert cast(float, exactness["absolute_error"].max()) < 1e-8
    findings = result.tables["explanation_findings"]
    assert findings.filter(pl.col("status") == "FAIL").is_empty()

    figures = build_exp_018_figures(result)
    assert len(figures) == 4
    for figure in figures.values():
        plt.close(figure)


def test_explanation_is_invariant_to_locked_test_changes() -> None:
    features, episodes = _inputs()
    changed = features.with_columns(
        pl.when(pl.col("prediction_date") >= pl.date(2021, 7, 1))
        .then(pl.lit(999999.0))
        .otherwise(pl.col("daily_load_sum_7d"))
        .alias("daily_load_sum_7d")
    )

    original = run_exp_018_explanation(
        features=features, episodes=episodes, config=_explanation_config()
    )
    modified = run_exp_018_explanation(
        features=changed, episodes=episodes, config=_explanation_config()
    )

    assert original.tables["coefficient_stability"].equals(modified.tables["coefficient_stability"])


def test_explanation_config_and_notebook_contract() -> None:
    config = load_exp_018_config(Path("configs/modelling/subjective_v1_exp_018_explanation.yaml"))
    assert config.selected_regularisation_c == 0.001
    assert config.final_test_access is False

    path = Path("notebooks/modelling/08_exp_018_explanation.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    assert "write_exp_018_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
