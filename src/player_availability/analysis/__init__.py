"""Reproducible descriptive analysis for model-readiness decisions."""

from player_availability.analysis.cohort import build_phase_a_cohort_report
from player_availability.analysis.plots import render_phase_a_charts

__all__ = ["build_phase_a_cohort_report", "render_phase_a_charts"]
