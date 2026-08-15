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
from player_availability.analysis.stage_02_missingness_eda import (
    Stage02MissingnessResult,
    build_stage_02_figures,
    load_stage_02_from_gcp,
    run_stage_02_missingness_eda,
    write_stage_02_outputs,
)
from player_availability.analysis.stage_03_feature_distribution_eda import (
    Stage03FeatureDistributionResult,
    build_stage_03_figures,
    load_stage_03_from_gcp,
    run_stage_03_feature_distribution_eda,
    write_stage_03_outputs,
)
from player_availability.analysis.stage_04_feature_redundancy import (
    Stage04FeatureRedundancyResult,
    build_stage_04_figures,
    load_stage_04_from_gcp,
    run_stage_04_feature_redundancy,
    write_stage_04_outputs,
)
from player_availability.analysis.stage_05_outcome_context import (
    Stage05OutcomeContextResult,
    build_stage_05_figures,
    load_stage_05_from_gcp,
    run_stage_05_outcome_context,
    write_stage_05_outputs,
)
from player_availability.analysis.stage_06_cohort_outcome_sensitivity import (
    Stage06CohortOutcomeResult,
    build_stage_06_figures,
    load_stage_06_from_gcp,
    run_stage_06_cohort_outcome_sensitivity,
    write_stage_06_outputs,
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
    "Stage02MissingnessResult",
    "build_stage_02_figures",
    "load_stage_02_from_gcp",
    "run_stage_02_missingness_eda",
    "write_stage_02_outputs",
    "Stage03FeatureDistributionResult",
    "build_stage_03_figures",
    "load_stage_03_from_gcp",
    "run_stage_03_feature_distribution_eda",
    "write_stage_03_outputs",
    "Stage04FeatureRedundancyResult",
    "build_stage_04_figures",
    "load_stage_04_from_gcp",
    "run_stage_04_feature_redundancy",
    "write_stage_04_outputs",
    "Stage05OutcomeContextResult",
    "build_stage_05_figures",
    "load_stage_05_from_gcp",
    "run_stage_05_outcome_context",
    "write_stage_05_outputs",
    "Stage06CohortOutcomeResult",
    "build_stage_06_figures",
    "load_stage_06_from_gcp",
    "run_stage_06_cohort_outcome_sensitivity",
    "write_stage_06_outputs",
]
