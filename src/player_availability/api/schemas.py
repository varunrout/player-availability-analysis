"""Typed API response models (`DEC-064`).

Every response that presents a risk figure or an operating point carries the "as at"
date and the operating point in force, per `DEC-064`'s copy constraints.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class OperatingPointInForce(BaseModel):
    """The alerting rule applied to this response, with both measured burdens.

    Development burden (`EXP-019`, 16,815 pooled rolling-origin player-days, 18
    represented onsets) and held-out burden (`DEC-062`/`DEC-063`, the V1-P5
    confirmatory result, 8,845 player-days, 5 represented onsets) are reported
    together, never the development figure alone: a reviewer who reads the model
    card and then opens the dashboard must not encounter two unreconciled numbers.
    """

    review_rate: float
    probability_threshold: float
    development_false_alerts_per_captured_onset: float | None
    held_out_realised_alert_rate: float | None
    held_out_false_alerts_per_captured_onset: float | None
    held_out_represented_onsets: int | None


class PlayerRiskRow(BaseModel):
    player_id: str
    predicted_probability: float
    rank_within_team_day: int
    alert: bool
    data_completeness: float


class SquadOverviewResponse(BaseModel):
    """A team's squad ranked by risk for one date. Not a live view (`DEC-064`)."""

    team_id: str
    as_at_date: date
    operating_point: OperatingPointInForce
    players: list[PlayerRiskRow]


class DriverContribution(BaseModel):
    predictor: str
    contribution: float


class RiskSeriesPoint(BaseModel):
    prediction_date: date
    predicted_probability: float
    alert: bool


class PlayerDetailResponse(BaseModel):
    """One player's risk history, drivers for the selected date, and completeness.

    `onset_dates` is carried separately from `risk_series` rather than as a
    per-point flag: an onset day is never itself a scored player-day (the frozen
    Stage 7 eligibility rule excludes any day within an active episode), so no
    point in `risk_series` could ever be flagged true.
    """

    player_id: str
    team_id: str
    as_at_date: date
    operating_point: OperatingPointInForce
    risk_series: list[RiskSeriesPoint]
    onset_dates: list[date]
    driver_contributions: list[DriverContribution]
    data_completeness: float


class TeamDataQualityPoint(BaseModel):
    prediction_date: date
    mean_data_completeness: float


class PlayerCoverage(BaseModel):
    player_id: str
    mean_data_completeness: float


class OnsetsByYear(BaseModel):
    year: int
    represented_onsets: int
    player_days: int


class DataQualityResponse(BaseModel):
    """Reporting coverage over time and across players for one team.

    Also carries the cohort-wide (not team-scoped) onset-decline finding: onsets fall
    roughly tenfold from 2020 to 2021 at flat player-days, tracking reporting
    engagement rather than injury incidence.
    """

    team_id: str
    as_at_date: date
    coverage_over_time: list[TeamDataQualityPoint]
    player_coverage_range: list[PlayerCoverage]
    onsets_by_year: list[OnsetsByYear]
    onset_decline_note: str
    onset_reconciliation_note: str


class CalibrationReference(BaseModel):
    """The champion's frozen development calibration (`EXP-009`, `DEC-058`/`DEC-059`)."""

    mean_prediction: float
    observed_rate: float
    calibration_intercept: float | None
    calibration_slope: float | None
    brier_score: float
    log_loss: float


class ReliabilityBin(BaseModel):
    reliability_bin: int
    player_days: int
    positive_days: int
    mean_prediction: float
    observed_rate: float
    bin_supported: bool


class OperatingPointBurden(BaseModel):
    review_rate: float
    alerts_per_100_player_days: float
    recall: float | None
    false_alerts_per_captured_onset: float | None


class FinalTestClaim(BaseModel):
    claim_id: str
    statement: str
    supported: bool
    evidence: str


class FinalTestResult(BaseModel):
    """The V1-P5 confirmatory result. Not a performance claim (`DEC-062`, `DEC-063`)."""

    player_days: int
    positive_days: int
    roc_auc: float | None
    claims: list[FinalTestClaim]
    interpretation: str
    c3_explanation: str


class ModelHealthResponse(BaseModel):
    """Calibration, operating-point burden (development and held-out) and the V1-P5
    confirmatory result."""

    as_at_date: date
    calibration: CalibrationReference
    reliability_bins: list[ReliabilityBin]
    operating_points: list[OperatingPointBurden]
    held_out_operating_points: list[OperatingPointBurden]
    final_test_result: FinalTestResult


class HealthResponse(BaseModel):
    status: str


class CoveredPeriodResponse(BaseModel):
    """Team identifiers and the date range available for the selectors."""

    team_ids: list[str]
    covered_date_start: date
    covered_date_end: date
    default_as_at_date: date
