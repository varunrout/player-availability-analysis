"""Typed API response models (`DEC-064`).

Every response that presents a risk figure or an operating point carries the "as at"
date and the operating point in force, per `DEC-064`'s copy constraints.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class OperatingPointInForce(BaseModel):
    """The alerting rule applied to this response, with its measured burden."""

    review_rate: float
    probability_threshold: float
    false_alerts_per_captured_onset: float | None


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
    is_onset_date: bool


class PlayerDetailResponse(BaseModel):
    """One player's risk history, drivers for the selected date, and completeness."""

    player_id: str
    team_id: str
    as_at_date: date
    operating_point: OperatingPointInForce
    risk_series: list[RiskSeriesPoint]
    driver_contributions: list[DriverContribution]
    data_completeness: float


class TeamDataQualityPoint(BaseModel):
    prediction_date: date
    mean_data_completeness: float


class PlayerCoverage(BaseModel):
    player_id: str
    mean_data_completeness: float


class DataQualityResponse(BaseModel):
    """Reporting coverage over time and across players for one team."""

    team_id: str
    as_at_date: date
    coverage_over_time: list[TeamDataQualityPoint]
    player_coverage_range: list[PlayerCoverage]


class CalibrationReference(BaseModel):
    """The champion's frozen development calibration (`EXP-009`, `DEC-058`/`DEC-059`)."""

    mean_prediction: float
    observed_rate: float
    calibration_intercept: float | None
    calibration_slope: float | None
    brier_score: float
    log_loss: float


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


class ModelHealthResponse(BaseModel):
    """Calibration, operating-point burden and the V1-P5 confirmatory result."""

    as_at_date: date
    calibration: CalibrationReference
    operating_points: list[OperatingPointBurden]
    final_test_result: FinalTestResult


class HealthResponse(BaseModel):
    status: str


class CoveredPeriodResponse(BaseModel):
    """Team identifiers and the date range available for the selectors."""

    team_ids: list[str]
    covered_date_start: date
    covered_date_end: date
    default_as_at_date: date
