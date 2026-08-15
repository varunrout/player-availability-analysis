"""Stage 8 pre-model readiness evidence consolidation and decision gate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.figure import Figure

RECOMMENDATIONS = ("READY", "REVISE", "DO NOT MODEL")

STAGE_SOURCES = (
    ("00", "00_data_audit", "audit_findings.csv", "data integrity", "foundation"),
    ("01", "01_outcome_eda", "outcome_quality_findings.csv", "outcome validity", "DEC-030"),
    (
        "02",
        "02_missingness_eda",
        "reporting_process_findings.csv",
        "missingness and reporting",
        "DEC-031",
    ),
    (
        "03",
        "03_feature_distribution_eda",
        "feature_distribution_findings.csv",
        "feature behaviour",
        "DEC-032",
    ),
    (
        "04",
        "04_feature_redundancy",
        "structural_findings.csv",
        "feature contract",
        "DEC-033",
    ),
    (
        "05",
        "05_outcome_context",
        "outcome_context_findings.csv",
        "descriptive context",
        "DEC-034",
    ),
    (
        "06",
        "06_cohort_outcome_sensitivity",
        "cohort_outcome_findings.csv",
        "cohort and support",
        "DEC-035",
    ),
    (
        "07",
        "07_prospective_protocol",
        "leakage_findings.csv",
        "prospective protocol",
        "DEC-036; DEC-037",
    ),
)


@dataclass(frozen=True, slots=True)
class Stage08ReadinessResult:
    """Retained Stage 8 tables and readiness recommendation."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def run_stage_08_pre_model_readiness(
    *, analysis_root: Path = Path("outputs/analysis"), repo_root: Path = Path(".")
) -> Stage08ReadinessResult:
    """Consolidate approved pre-model evidence without fitting or evaluating a model."""
    evidence, manifests, findings, artifact_inventory = _load_stage_evidence(analysis_root)
    support = _read_csv(analysis_root / "07_prospective_protocol/tables/partition_support.csv")
    feature_coverage = _read_csv(
        analysis_root / "07_prospective_protocol/tables/feature_coverage.csv"
    )
    rolling_folds = _read_csv(
        analysis_root / "07_prospective_protocol/tables/rolling_origin_folds.csv"
    )
    unseen_players = _read_csv(
        analysis_root / "07_prospective_protocol/tables/unseen_player_stress.csv"
    )
    notebook_audit = _audit_notebooks(repo_root)
    hard_gates = _build_hard_gates(
        analysis_root=analysis_root,
        repo_root=repo_root,
        manifests=manifests,
        findings=findings,
        support=support,
        notebook_audit=notebook_audit,
    )
    limitations = _build_limitation_controls(
        analysis_root=analysis_root,
        support=support,
        feature_coverage=feature_coverage,
        rolling_folds=rolling_folds,
        unseen_players=unseen_players,
    )
    hypotheses = _build_hypothesis_register()
    launch_contract = _build_launch_contract()
    final_test_checklist = _build_final_test_checklist()
    recommendation = _derive_recommendation(hard_gates)
    readiness_decision = _build_readiness_decision(
        recommendation=recommendation,
        hard_gates=hard_gates,
        limitations=limitations,
    )
    readiness_findings = _build_readiness_findings(
        evidence=evidence,
        hard_gates=hard_gates,
        limitations=limitations,
        notebook_audit=notebook_audit,
        recommendation=recommendation,
    )
    failures = readiness_findings.filter(pl.col("status") == "FAIL").height
    warnings = readiness_findings.filter(pl.col("status") == "WARNING").height
    reviews = readiness_findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "stage_evidence_register": evidence,
        "source_artifact_inventory": artifact_inventory,
        "hard_gate_matrix": hard_gates,
        "limitation_control_register": limitations,
        "hypothesis_register": hypotheses,
        "model_launch_contract": launch_contract,
        "final_test_access_checklist": final_test_checklist,
        "notebook_audit": notebook_audit,
        "readiness_decision": readiness_decision,
        "readiness_findings": readiness_findings,
    }
    return Stage08ReadinessResult(
        tables=tables,
        summary={
            "stage": "08_pre_model_readiness",
            "status": "PASS" if failures == 0 else "FAIL",
            "recommendation": recommendation,
            "source_stage_count": evidence.height,
            "source_artifact_count": artifact_inventory.height,
            "hard_gate_count": hard_gates.height,
            "hard_gate_failure_count": hard_gates.filter(pl.col("gate_status") == "FAIL").height,
            "mandatory_constraint_count": limitations.filter(pl.col("mandatory")).height,
            "model_count": 0,
            "prediction_count": 0,
            "performance_metric_count": 0,
            "final_test_performance_accessed": False,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def write_stage_08_outputs(result: Stage08ReadinessResult, output_root: Path) -> None:
    """Persist canonical Stage 8 readiness outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_08_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_08_PRE_MODEL_READINESS.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_08_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _load_stage_evidence(
    analysis_root: Path,
) -> tuple[pl.DataFrame, dict[str, dict[str, Any]], dict[str, pl.DataFrame], pl.DataFrame]:
    evidence_rows: list[dict[str, object]] = []
    artifact_rows: list[dict[str, object]] = []
    manifests: dict[str, dict[str, Any]] = {}
    findings: dict[str, pl.DataFrame] = {}
    for stage_id, folder, findings_name, domain, decision in STAGE_SOURCES:
        stage_root = analysis_root / folder
        manifest_path = stage_root / "metadata" / f"stage_{stage_id}_run_manifest.json"
        report_paths = sorted((stage_root / "reports").glob("*.md"))
        findings_path = stage_root / "tables" / findings_name
        required_paths = [manifest_path, findings_path, *report_paths]
        missing = [str(path) for path in required_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing Stage {stage_id} readiness evidence: {missing}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finding_table = pl.read_csv(findings_path)
        if "status" not in finding_table.columns:
            raise ValueError(f"Stage {stage_id} findings have no status column")
        manifests[stage_id] = manifest
        findings[stage_id] = finding_table
        counts = {
            status: finding_table.filter(pl.col("status") == status).height
            for status in ("PASS", "WARNING", "REVIEW", "FAIL")
        }
        evidence_rows.append(
            {
                "stage_id": stage_id,
                "stage": manifest.get("stage", folder),
                "domain": domain,
                "accepted_decision": decision,
                "manifest_status": manifest.get("status"),
                "failure_count": counts["FAIL"],
                "warning_count": counts["WARNING"],
                "review_count": counts["REVIEW"],
                "pass_count": counts["PASS"],
                "manifest_path": manifest_path.as_posix(),
                "findings_path": findings_path.as_posix(),
                "report_path": report_paths[0].as_posix(),
            }
        )
        for role, path in (
            ("manifest", manifest_path),
            ("findings", findings_path),
            ("report", report_paths[0]),
        ):
            artifact_rows.append(
                {
                    "stage_id": stage_id,
                    "artifact_role": role,
                    "path": path.as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    return (
        pl.DataFrame(evidence_rows).sort("stage_id"),
        manifests,
        findings,
        pl.DataFrame(artifact_rows).sort("stage_id", "artifact_role"),
    )


def _audit_notebooks(repo_root: Path) -> pl.DataFrame:
    rows = []
    for stage_id, folder, *_ in STAGE_SOURCES:
        notebook_name = folder.removeprefix(f"{stage_id}_")
        path = repo_root / "notebooks" / "analysis" / f"{stage_id}_{notebook_name}.ipynb"
        exists = path.is_file()
        output_cells = -1
        executed_cells = -1
        if exists:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            output_cells = sum(bool(cell.get("outputs")) for cell in notebook["cells"])
            executed_cells = sum(
                cell.get("execution_count") is not None
                for cell in notebook["cells"]
                if cell["cell_type"] == "code"
            )
        rows.append(
            {
                "stage_id": stage_id,
                "notebook_path": path.as_posix(),
                "exists": exists,
                "output_cell_count": output_cells,
                "executed_cell_count": executed_cells,
                "status": (
                    "PASS" if exists and output_cells == 0 and executed_cells == 0 else "FAIL"
                ),
            }
        )
    return pl.DataFrame(rows).sort("stage_id")


def _build_hard_gates(
    *,
    analysis_root: Path,
    repo_root: Path,
    manifests: dict[str, dict[str, Any]],
    findings: dict[str, pl.DataFrame],
    support: pl.DataFrame,
    notebook_audit: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []

    def gate(
        gate_id: str,
        domain: str,
        passed: bool,
        evidence: str,
        failure_disposition: str,
        constraint_required: bool = False,
    ) -> None:
        rows.append(
            {
                "gate_id": gate_id,
                "domain": domain,
                "gate_status": "PASS" if passed else "FAIL",
                "evidence": evidence,
                "failure_disposition": failure_disposition,
                "constraint_required": constraint_required,
            }
        )

    all_manifests_pass = all(item.get("status") == "PASS" for item in manifests.values())
    all_findings_no_fail = all(
        table.filter(pl.col("status") == "FAIL").is_empty() for table in findings.values()
    )
    gate(
        "G01",
        "evidence completeness",
        len(manifests) == 8,
        f"{len(manifests)}/8 stage manifests loaded with findings and reports",
        "REVISE",
    )
    gate(
        "G02",
        "stage integrity",
        all_manifests_pass and all_findings_no_fail,
        "all Stage 0-7 manifests PASS and no findings register contains FAIL",
        "REVISE",
    )
    outcome_ok = _finding_is_pass(
        findings["01"], "primary_episode_reproduction"
    ) and _finding_is_pass(findings["06"], "primary_label_reproduction")
    gate(
        "G03",
        "outcome validity",
        outcome_ok,
        "episode and primary player-day labels reproduce exactly",
        "DO NOT MODEL",
    )
    missingness_ok = _finding_is_pass(
        findings["02"], "wellness_presence_identity"
    ) and _finding_is_pass(findings["02"], "gold_completeness_reproduction")
    gate(
        "G04",
        "missingness semantics",
        missingness_ok,
        "wellness presence and gold completeness fields reconcile; missingness is explicit",
        "REVISE",
        True,
    )
    features_ok = _finding_is_pass(findings["03"], "feature_ranges") and _finding_is_pass(
        findings["04"], "outcome_isolation"
    )
    gate(
        "G05",
        "feature integrity",
        features_ok,
        "numeric ranges pass and target-blind feature analysis used no outcomes",
        "REVISE",
        True,
    )
    cohort_ok = (
        _finding_is_pass(findings["06"], "primary_label_reproduction") and support.height == 3
    )
    gate(
        "G06",
        "cohort and split contract",
        cohort_ok,
        "primary cohort reproduces and train/validation/test support is retained",
        "REVISE",
    )
    leakage_ok = findings["07"].filter(pl.col("status") == "FAIL").is_empty()
    gate(
        "G07",
        "leakage prevention",
        leakage_ok,
        "Stage 7 has zero leakage or protocol failures",
        "DO NOT MODEL",
    )
    test_locked = (
        manifests["07"].get("final_test_performance_accessed") is False
        and support.filter(pl.col("performance_inspected")).is_empty()
    )
    gate(
        "G08",
        "final-test governance",
        test_locked,
        "final-test support only; no performance inspection recorded",
        "DO NOT MODEL",
        True,
    )
    pre_model_clean = all(
        int(manifests[stage].get("model_count", 0)) == 0 for stage in ("05", "06", "07")
    )
    gate(
        "G09",
        "pre-model isolation",
        pre_model_clean,
        "Stages 5-7 contain zero fitted models",
        "DO NOT MODEL",
    )
    positive_support = support.filter(pl.col("represented_onset_count") <= 0).is_empty()
    minimum_support = cast(int, support["represented_onset_count"].min())
    gate(
        "G10",
        "exploratory outcome support",
        positive_support,
        f"all partitions have represented onsets; minimum partition support is {minimum_support}",
        "DO NOT MODEL",
        True,
    )
    protocol_files = (
        "predictor_contract.csv",
        "preprocessing_contract.csv",
        "evaluation_contract.csv",
        "alert_capacity_contract.csv",
        "uncertainty_contract.csv",
        "split_manifest.csv",
    )
    protocol_complete = all(
        (analysis_root / "07_prospective_protocol" / "tables" / name).is_file()
        for name in protocol_files
    )
    gate(
        "G11",
        "prospective protocol completeness",
        protocol_complete,
        f"{len(protocol_files)} frozen protocol tables present",
        "REVISE",
    )
    notebook_ok = notebook_audit.filter(pl.col("status") == "FAIL").is_empty()
    gate(
        "G12",
        "reproducibility",
        notebook_ok and (repo_root / "poetry.lock").is_file(),
        "all eight notebooks are output-free and poetry.lock is present",
        "REVISE",
    )
    return pl.DataFrame(rows)


def _build_limitation_controls(
    *,
    analysis_root: Path,
    support: pl.DataFrame,
    feature_coverage: pl.DataFrame,
    rolling_folds: pl.DataFrame,
    unseen_players: pl.DataFrame,
) -> pl.DataFrame:
    validation_onsets = _partition_value(support, "validation", "represented_onset_count")
    test_onsets = _partition_value(support, "test", "represented_onset_count")
    zero_folds = rolling_folds.filter(pl.col("validation_positive_player_days") == 0).height
    zero_players = unseen_players.filter(pl.col("heldout_positive_player_days") == 0).height
    fatigue_coverage = float(
        feature_coverage.filter(pl.col("predictor") == "fatigue_lag1_robust_z_prior").item(
            0, "coverage_rate"
        )
    )
    stage_01_manifest = json.loads(
        (analysis_root / "01_outcome_eda/metadata/stage_01_run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    rows = (
        (
            "L01",
            "critical",
            "Scope",
            "SoccerMon subjective data and self-reported outcomes do not establish "
            "medical validity",
            "Limit all modelling and reporting to exploratory practitioner-review decision support",
        ),
        (
            "L02",
            "high",
            "Sparse temporal support",
            f"Validation and test represent {validation_onsets} and {test_onsets} onsets",
            "Always disclose onset/player counts and wide uncertainty; avoid precise "
            "comparative claims",
        ),
        (
            "L03",
            "high",
            "Zero-positive temporal window",
            f"{zero_folds} rolling validation window has zero positive player-days",
            "Use that window as a stress period only, not for discrimination or "
            "calibration estimation",
        ),
        (
            "L04",
            "high",
            "Unseen-player support",
            f"{zero_players}/50 held-out players have zero positive development days",
            "Aggregate support-aware stress results; never average undefined player-level metrics",
        ),
        (
            "L05",
            "high",
            "Outcome concentration",
            f"Only {stage_01_manifest['primary_onset_day_count']} primary player-date onsets exist",
            "Use player-cluster and temporal-block uncertainty and disclose concentration",
        ),
        (
            "L06",
            "high",
            "Outcome semantics",
            "Outcome is self-reported recorded onset, not confirmed tissue injury or "
            "availability loss",
            "Use model-estimated availability-risk and review language; prohibit "
            "diagnosis/clearance claims",
        ),
        (
            "L07",
            "moderate",
            "Wellness missingness",
            "Wellness coverage and reporting process vary by player, team and proximity to onset",
            "Use lagged values, missing indicators, train-only imputation and "
            "missingness sensitivity",
        ),
        (
            "L08",
            "moderate",
            "Sparse robust fatigue",
            f"Robust fatigue coverage is {fatigue_coverage:.1%}",
            "Keep F3 incremental/secondary and report availability alongside any result",
        ),
        (
            "L09",
            "moderate",
            "Load representation redundancy",
            "Daily load and session sRPE are near duplicates",
            "Use sRPE only as a replacement sensitivity, never alongside daily load",
        ),
        (
            "L10",
            "critical",
            "Final-test multiplicity",
            "Final test is small and currently uninspected",
            "Access once only after feature, model, calibration and alert rules are frozen",
        ),
        (
            "L11",
            "moderate",
            "Outcome-definition uncertainty",
            "Episode gap and 3/14-day horizons change support and positive-row dependence",
            "Run pre-specified horizon/gap sensitivities without selecting a convenient winner",
        ),
        (
            "L12",
            "critical",
            "Deployment validity",
            "No prospective club deployment, external team transfer or clinical validation exists",
            "Do not claim operational deployment readiness, team transfer or medical utility",
        ),
    )
    return pl.DataFrame(
        {
            "limitation_id": item[0],
            "severity": item[1],
            "domain": item[2],
            "evidence": item[3],
            "mandatory_control": item[4],
            "mandatory": True,
        }
        for item in rows
    )


def _build_hypothesis_register() -> pl.DataFrame:
    rows = (
        (
            "H0",
            "F0 global prevalence is the minimum probability baseline",
            "Brier score and calibration against training prevalence",
            "M0",
        ),
        (
            "H1",
            "F1 absolute load and lagged wellness improve prospective utility over F0",
            "Development Brier, average precision, calibration and alert capture",
            "M1 primary",
        ),
        (
            "H2",
            "F2 session exposure and reporting context add value beyond F1",
            "Pre-specified incremental development comparison",
            "M1 primary",
        ),
        (
            "H3",
            "F3 prior player-relative features add transferable context beyond F2",
            "Development comparison plus support-aware unseen-player stress",
            "M1 secondary",
        ),
        (
            "H4",
            "sRPE replacement behaves similarly to the near-duplicate daily-load family",
            "Replacement-only sensitivity, never simultaneous inclusion",
            "M1 sensitivity",
        ),
        (
            "H5",
            "Operational conclusions remain directionally coherent at 3-day and 14-day horizons",
            "Pre-specified horizon sensitivity with matching embargoes",
            "M0/M1 sensitivity",
        ),
        (
            "H6",
            "Any useful ranking can be translated into calibrated, capacity-bounded review signals",
            "Calibration plus 1%, 2.5% and 5% review-rate metrics",
            "M0/M1 operational",
        ),
    )
    return pl.DataFrame(
        {
            "hypothesis_id": item[0],
            "hypothesis": item[1],
            "test_rule": item[2],
            "experiment_scope": item[3],
            "status": "FROZEN",
        }
        for item in rows
    )


def _build_launch_contract() -> pl.DataFrame:
    rows = (
        (1, "M0", "Global training prevalence", "Required first baseline"),
        (2, "M0", "Pre-specified simple operational heuristic", "Descriptive comparator only"),
        (3, "M1-F1", "Regularised logistic regression with F1", "Primary learned baseline"),
        (4, "M1-F2", "Regularised logistic regression with F2", "Primary incremental comparison"),
        (5, "M1-F3", "Regularised logistic regression with F3", "Secondary sensitivity only"),
        (6, "S-SRPE", "Replace daily-load family with sRPE", "Redundancy sensitivity"),
        (7, "S-HORIZON", "Repeat frozen 3-day and 14-day targets", "No winner selection"),
        (
            8,
            "M2+",
            "Tree and survival models",
            "Deferred until M0/M1 evidence justifies complexity",
        ),
    )
    return pl.DataFrame(
        {
            "sequence": item[0],
            "experiment": item[1],
            "description": item[2],
            "constraint": item[3],
            "authorised_after_owner_ready": item[0] <= 7,
        }
        for item in rows
    )


def _build_final_test_checklist() -> pl.DataFrame:
    rows = (
        ("T01", "Dataset and source-artifact hashes frozen"),
        ("T02", "Primary cohort, horizon, predictors and prohibitions frozen"),
        ("T03", "Model family and finite hyperparameter grid frozen"),
        ("T04", "Train-only preprocessing implementation verified"),
        ("T05", "Calibration method selected using development data only"),
        ("T06", "Alert-capacity thresholds selected using validation only"),
        ("T07", "Primary model and all labelled sensitivities frozen"),
        ("T08", "Evaluation code tested without final-test predictions"),
        ("T09", "One-time final-test access explicitly authorised and logged"),
        ("T10", "All metrics, uncertainty intervals and support counts reported together"),
    )
    return pl.DataFrame(
        {
            "check_id": item[0],
            "requirement": item[1],
            "current_status": "PENDING_MODEL_DEVELOPMENT",
            "required_before_test_access": True,
        }
        for item in rows
    )


def _derive_recommendation(hard_gates: pl.DataFrame) -> str:
    failed = hard_gates.filter(pl.col("gate_status") == "FAIL")
    if failed.is_empty():
        return "READY"
    if failed.filter(pl.col("failure_disposition") == "DO NOT MODEL").height:
        return "DO NOT MODEL"
    return "REVISE"


def _build_readiness_decision(
    *, recommendation: str, hard_gates: pl.DataFrame, limitations: pl.DataFrame
) -> pl.DataFrame:
    if recommendation not in RECOMMENDATIONS:
        raise ValueError(f"Invalid readiness recommendation: {recommendation}")
    return pl.DataFrame(
        [
            {
                "recommendation": recommendation,
                "scope": (
                    "Narrow exploratory M0/M1 subjective-data baseline programme"
                    if recommendation == "READY"
                    else "No modelling launch"
                ),
                "hard_gates_passed": hard_gates.filter(pl.col("gate_status") == "PASS").height,
                "hard_gates_failed": hard_gates.filter(pl.col("gate_status") == "FAIL").height,
                "mandatory_constraints": limitations.filter(pl.col("mandatory")).height,
                "owner_approval_required": True,
                "modelling_authorised_by_stage_run": False,
                "final_test_performance_accessed": False,
                "decision_basis": (
                    "All hard gates pass; limitations have explicit mandatory controls"
                    if recommendation == "READY"
                    else "One or more hard gates failed"
                ),
            }
        ]
    )


def _build_readiness_findings(
    *,
    evidence: pl.DataFrame,
    hard_gates: pl.DataFrame,
    limitations: pl.DataFrame,
    notebook_audit: pl.DataFrame,
    recommendation: str,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def add(check: str, status: str, evidence_text: str) -> None:
        rows.append({"check_id": check, "status": status, "evidence": evidence_text})

    add(
        "stage_evidence_complete",
        "PASS" if evidence.height == 8 else "FAIL",
        f"{evidence.height}/8 stages consolidated",
    )
    failed_gates = hard_gates.filter(pl.col("gate_status") == "FAIL").height
    add(
        "hard_gate_status",
        "PASS" if failed_gates == 0 else "FAIL",
        f"{failed_gates} failed hard gates",
    )
    failed_notebooks = notebook_audit.filter(pl.col("status") == "FAIL").height
    add(
        "notebook_reproducibility",
        "PASS" if failed_notebooks == 0 else "FAIL",
        f"{failed_notebooks} notebooks missing or carrying saved execution state",
    )
    unmapped = limitations.filter(
        ~pl.col("mandatory") | pl.col("mandatory_control").is_null()
    ).height
    add(
        "limitation_control_mapping",
        "PASS" if unmapped == 0 else "FAIL",
        f"{limitations.height - unmapped}/{limitations.height} limitations have mandatory controls",
    )
    high_constraints = limitations.filter(pl.col("severity").is_in(["critical", "high"])).height
    add(
        "material_limitations",
        "REVIEW",
        f"{high_constraints} critical/high limitations constrain modelling and claims",
    )
    add(
        "recommendation_enum",
        "PASS" if recommendation in RECOMMENDATIONS else "FAIL",
        f"exact recommendation is {recommendation}",
    )
    add(
        "model_free_readiness",
        "PASS",
        "zero models, predictions, thresholds, performance metrics or final-test access",
    )
    add(
        "owner_decision_gate",
        "REVIEW",
        "recommendation does not authorise modelling until separately approved by project owner",
    )
    return pl.DataFrame(rows)


def build_stage_08_figures(result: Stage08ReadinessResult) -> dict[str, Figure]:
    """Build Stage 8 evidence and readiness figures."""
    figures: dict[str, Figure] = {}
    evidence = result.tables["stage_evidence_register"]
    x = list(range(evidence.height))
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(x, evidence["pass_count"], label="Pass", color="#287271")
    axis.bar(
        x,
        evidence["review_count"],
        bottom=evidence["pass_count"],
        label="Review",
        color="#E9C46A",
    )
    prior = evidence["pass_count"] + evidence["review_count"]
    axis.bar(x, evidence["warning_count"], bottom=prior, label="Warning", color="#E76F51")
    axis.set_xticks(x, [f"Stage {value}" for value in evidence["stage_id"]])
    axis.set_ylabel("Findings")
    axis.set_title("Approved evidence carried into readiness")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["stage_evidence_status"] = fig

    gates = result.tables["hard_gate_matrix"].group_by("gate_status").len().sort("gate_status")
    palette = {"PASS": "#287271", "FAIL": "#B00020"}
    fig, axis = plt.subplots(figsize=(7, 4.8))
    axis.bar(
        gates["gate_status"], gates["len"], color=[palette[value] for value in gates["gate_status"]]
    )
    axis.set_ylabel("Hard gates")
    axis.set_title("Readiness hard-gate result")
    fig.tight_layout()
    figures["hard_gate_status"] = fig

    limits = result.tables["limitation_control_register"].group_by("severity").len()
    severity_order = [
        value for value in ("critical", "high", "moderate") if value in limits["severity"].to_list()
    ]
    counts = [limits.filter(pl.col("severity") == value).item(0, "len") for value in severity_order]
    fig, axis = plt.subplots(figsize=(7, 4.8))
    axis.bar(severity_order, counts, color=["#B00020", "#E76F51", "#E9C46A"][: len(counts)])
    axis.set_ylabel("Mandatory constraints")
    axis.set_title("Limitations retained as modelling controls")
    fig.tight_layout()
    figures["limitation_severity"] = fig

    launch = result.tables["model_launch_contract"]
    fig, axis = plt.subplots(figsize=(10, 5))
    colours = [
        "#287271" if bool(value) else "#B8B8B8" for value in launch["authorised_after_owner_ready"]
    ]
    labels = [
        f"{row['sequence']}  {row['experiment']}"
        for row in launch.select("sequence", "experiment").iter_rows(named=True)
    ]
    axis.barh(list(reversed(labels)), [1] * launch.height, color=list(reversed(colours)))
    axis.set_xlim(0, 1)
    axis.set_xticks([])
    axis.set_title("Frozen modelling launch sequence")
    axis.set_xlabel("M2+ remains deferred until baseline evidence earns complexity")
    fig.tight_layout()
    figures["model_launch_sequence"] = fig
    return figures


def _render_report(result: Stage08ReadinessResult) -> str:
    summary = result.summary
    decision = result.tables["readiness_decision"].row(0, named=True)
    gates = result.tables["hard_gate_matrix"]
    limitations = result.tables["limitation_control_register"]
    lines = [
        "# Stage 8 - Pre-Model Readiness Report",
        "",
        "## Provisional Recommendation",
        "",
        f"# {decision['recommendation']}",
        "",
        f"Scope: **{decision['scope']}**.",
        "",
        "This recommendation does not itself authorise modelling. Separate project-owner "
        "approval is required. No model, prediction, threshold, performance metric or "
        "final-test performance was produced in Stage 8.",
        "",
        "## Decision Basis",
        "",
        f"- Hard gates passed: `{decision['hard_gates_passed']}`; failed: "
        f"`{decision['hard_gates_failed']}`.",
        f"- Mandatory modelling and claim constraints: `{decision['mandatory_constraints']}`.",
        f"- Source stages consolidated: `{summary['source_stage_count']}`.",
        "- Readiness is binary by hard gate; passing checks are not averaged into a score.",
        "",
        "## Hard Gates",
        "",
        "| Gate | Domain | Status | Evidence | Constraint |",
        "|---|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['gate_id']} | {row['domain']} | {row['gate_status']} | "
        f"{row['evidence']} | {'required' if row['constraint_required'] else 'none'} |"
        for row in gates.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Mandatory Limitations and Controls",
            "",
            "| ID | Severity | Limitation evidence | Mandatory control |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {row['limitation_id']} | {row['severity']} | {row['evidence']} | "
        f"{row['mandatory_control']} |"
        for row in limitations.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Permitted Interpretation",
            "",
            "A `READY` recommendation permits only a narrow exploratory M0/M1 programme "
            "using subjective SoccerMon data. It does not establish medical validity, "
            "operational deployment readiness, causal effects, player clearance, team "
            "transfer or prospective club utility.",
            "",
            "## Figures",
            "",
            "![Stage evidence](../figures/stage_evidence_status.png)",
            "",
            "![Hard gates](../figures/hard_gate_status.png)",
            "",
            "![Limitations](../figures/limitation_severity.png)",
            "",
            "![Launch sequence](../figures/model_launch_sequence.png)",
            "",
            "## Owner Gate",
            "",
            "The project owner must approve exactly one decision: `READY`, `REVISE` or "
            "`DO NOT MODEL`. Until that decision is recorded, modelling and final-test "
            "performance access remain prohibited.",
        ]
    )
    return "\n".join(lines) + "\n"


def _finding_is_pass(table: pl.DataFrame, check_id: str) -> bool:
    matched = table.filter(pl.col("check_id") == check_id)
    return matched.height == 1 and matched.item(0, "status") == "PASS"


def _partition_value(table: pl.DataFrame, partition: str, column: str) -> int:
    return int(table.filter(pl.col("partition") == partition).item(0, column))


def _read_csv(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing Stage 8 evidence file: {path}")
    return pl.read_csv(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
