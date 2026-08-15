from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from matplotlib import pyplot as plt

from player_availability.analysis.stage_08_pre_model_readiness import (
    _derive_recommendation,
    build_stage_08_figures,
    run_stage_08_pre_model_readiness,
)


def test_stage_08_consolidates_evidence_without_modelling() -> None:
    result = run_stage_08_pre_model_readiness()

    assert result.summary["status"] == "PASS"
    assert result.summary["recommendation"] == "READY"
    assert result.summary["source_stage_count"] == 8
    assert result.summary["hard_gate_failure_count"] == 0
    assert result.summary["model_count"] == 0
    assert result.summary["prediction_count"] == 0
    assert result.summary["performance_metric_count"] == 0
    assert result.summary["final_test_performance_accessed"] is False
    decision = result.tables["readiness_decision"].row(0, named=True)
    assert decision["owner_approval_required"] is True
    assert decision["modelling_authorised_by_stage_run"] is False
    assert result.tables["readiness_findings"].filter(pl.col("status") == "FAIL").is_empty()


def test_stage_08_retains_every_material_limitation_as_a_control() -> None:
    result = run_stage_08_pre_model_readiness()
    limitations = result.tables["limitation_control_register"]

    assert limitations.height == 12
    assert limitations.filter(~pl.col("mandatory")).is_empty()
    assert limitations["mandatory_control"].null_count() == 0
    assert {"critical", "high", "moderate"} == set(limitations["severity"].to_list())
    figures = build_stage_08_figures(result)
    assert len(figures) == 4
    for figure in figures.values():
        plt.close(figure)


def test_stage_08_recommendation_never_averages_away_a_hard_failure() -> None:
    gates = pl.DataFrame(
        {
            "gate_status": ["PASS", "FAIL"],
            "failure_disposition": ["REVISE", "REVISE"],
        }
    )
    assert _derive_recommendation(gates) == "REVISE"

    fatal = gates.with_columns(
        pl.when(pl.col("gate_status") == "FAIL")
        .then(pl.lit("DO NOT MODEL"))
        .otherwise(pl.col("failure_disposition"))
        .alias("failure_disposition")
    )
    assert _derive_recommendation(fatal) == "DO NOT MODEL"


def test_stage_08_notebook_contract_has_no_output_writer() -> None:
    path = Path("notebooks/analysis/08_pre_model_readiness.ipynb")
    notebook_text = path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)

    assert "write_stage_08_outputs" not in notebook_text
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert len(notebook["cells"]) == 7
