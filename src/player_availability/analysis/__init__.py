"""Shared, stage-gated pre-model analysis interfaces."""

from player_availability.analysis.stage_00_data_audit import (
    Stage00AuditResult,
    build_stage_00_figures,
    load_stage_00_from_gcp,
    run_stage_00_audit,
    write_stage_00_outputs,
)
from player_availability.analysis.stage_01_outcome_eda import (
    Stage01OutcomeResult,
    build_stage_01_figures,
    load_stage_01_from_gcp,
    run_stage_01_outcome_eda,
    write_stage_01_outputs,
)

__all__ = [
    "Stage00AuditResult",
    "build_stage_00_figures",
    "load_stage_00_from_gcp",
    "run_stage_00_audit",
    "write_stage_00_outputs",
    "Stage01OutcomeResult",
    "build_stage_01_figures",
    "load_stage_01_from_gcp",
    "run_stage_01_outcome_eda",
    "write_stage_01_outputs",
]
