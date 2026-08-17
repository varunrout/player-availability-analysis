"""FastAPI service reading only the batch-inference serving artefact (`DEC-064`).

Internal ingress: reachable only by the web service's identity in deployment. No
endpoint queries BigQuery. Every data response carries the "as at" date and the
operating point in force.
"""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import polars as pl
from fastapi import FastAPI, HTTPException, Query

from player_availability.api.artifact import (
    DEFAULT_REVIEW_RATE,
    ModelHealthReference,
    ServingArtifact,
    load_model_health_reference,
    load_serving_artifact_from_gcs,
    load_serving_artifact_from_path,
)
from player_availability.api.schemas import (
    CalibrationReference,
    DataQualityResponse,
    DriverContribution,
    FinalTestClaim,
    FinalTestResult,
    HealthResponse,
    ModelHealthResponse,
    OperatingPointBurden,
    OperatingPointInForce,
    PlayerCoverage,
    PlayerDetailResponse,
    PlayerRiskRow,
    RiskSeriesPoint,
    SquadOverviewResponse,
    TeamDataQualityPoint,
)
from player_availability.config import get_settings
from player_availability.product.batch_inference import DISPLAYABLE_DRIVERS

app = FastAPI(
    title="Player Availability Analysis - Product API",
    description=(
        "Internal-ingress API for the V1 dashboard. Read-only over the batch-inference "
        "serving artefact. Not a live system: the covered period ends in 2021."
    ),
)


@lru_cache(maxsize=1)
def get_artifact() -> ServingArtifact:
    """Load the serving artefact once per process, from GCS or a local path."""
    local_path = os.environ.get("PAA_SERVING_ARTIFACT_DIR")
    if local_path:
        return load_serving_artifact_from_path(Path(local_path))
    settings = get_settings()
    return load_serving_artifact_from_gcs(
        project_id=settings.gcp.project_id, bucket_name=settings.gcp.artifacts_bucket
    )


@lru_cache(maxsize=1)
def get_model_health_reference() -> ModelHealthReference:
    return load_model_health_reference()


def _operating_point_in_force(artifact: ServingArtifact, rate: float) -> OperatingPointInForce:
    threshold = artifact.thresholds.get(rate)
    if threshold is None:
        raise HTTPException(status_code=400, detail=f"Unsupported review rate: {rate}")
    reference = get_model_health_reference()
    burden = next(
        (
            row["false_alerts_per_captured_onset"]
            for row in reference.operating_points
            if abs(float(row["operating_point_value"]) - rate) < 1e-9
        ),
        None,
    )
    return OperatingPointInForce(
        review_rate=rate, probability_threshold=threshold, false_alerts_per_captured_onset=burden
    )


def _resolve_date(artifact: ServingArtifact, requested: date | None) -> date:
    if requested is None:
        return artifact.covered_date_end
    if not (artifact.covered_date_start <= requested <= artifact.covered_date_end):
        raise HTTPException(
            status_code=400,
            detail=f"Date {requested} is outside the covered period "
            f"{artifact.covered_date_start} to {artifact.covered_date_end}",
        )
    return requested


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/squad-overview", response_model=SquadOverviewResponse)
def squad_overview(
    team_id: str,
    as_of: date | None = Query(default=None, alias="date"),
    review_rate: float = Query(default=DEFAULT_REVIEW_RATE),
) -> SquadOverviewResponse:
    artifact = get_artifact()
    as_at_date = _resolve_date(artifact, as_of)
    operating_point = _operating_point_in_force(artifact, review_rate)
    alert_column = f"alert_{review_rate:g}"
    rows = artifact.predictions.filter(
        (pl.col("team_id") == team_id) & (pl.col("prediction_date") == as_at_date)
    ).sort("rank_within_team_day")
    if rows.height == 0:
        raise HTTPException(status_code=404, detail=f"No data for team {team_id} on {as_at_date}")
    players = [
        PlayerRiskRow(
            player_id=row["player_id"],
            predicted_probability=row["predicted_probability"],
            rank_within_team_day=row["rank_within_team_day"],
            alert=bool(row[alert_column]),
            data_completeness=row["data_completeness"],
        )
        for row in rows.iter_rows(named=True)
    ]
    return SquadOverviewResponse(
        team_id=team_id, as_at_date=as_at_date, operating_point=operating_point, players=players
    )


@app.get("/player-detail", response_model=PlayerDetailResponse)
def player_detail(
    player_id: str,
    as_of: date | None = Query(default=None, alias="date"),
    review_rate: float = Query(default=DEFAULT_REVIEW_RATE),
) -> PlayerDetailResponse:
    artifact = get_artifact()
    as_at_date = _resolve_date(artifact, as_of)
    operating_point = _operating_point_in_force(artifact, review_rate)
    alert_column = f"alert_{review_rate:g}"
    history = artifact.predictions.filter(pl.col("player_id") == player_id).sort("prediction_date")
    if history.height == 0:
        raise HTTPException(status_code=404, detail=f"No data for player {player_id}")
    team_id = history["team_id"][0]
    selected = history.filter(pl.col("prediction_date") == as_at_date)
    if selected.height == 0:
        raise HTTPException(
            status_code=404, detail=f"No data for player {player_id} on {as_at_date}"
        )
    selected_row = selected.row(0, named=True)
    risk_series = [
        RiskSeriesPoint(
            prediction_date=row["prediction_date"],
            predicted_probability=row["predicted_probability"],
            alert=bool(row[alert_column]),
            is_onset_date=bool(row["is_onset_date"]),
        )
        for row in history.iter_rows(named=True)
    ]
    driver_contributions = [
        DriverContribution(predictor=driver, contribution=selected_row[f"driver_{driver}"])
        for driver in DISPLAYABLE_DRIVERS
    ]
    return PlayerDetailResponse(
        player_id=player_id,
        team_id=team_id,
        as_at_date=as_at_date,
        operating_point=operating_point,
        risk_series=risk_series,
        driver_contributions=driver_contributions,
        data_completeness=selected_row["data_completeness"],
    )


@app.get("/data-quality", response_model=DataQualityResponse)
def data_quality(
    team_id: str, as_of: date | None = Query(default=None, alias="date")
) -> DataQualityResponse:
    artifact = get_artifact()
    as_at_date = _resolve_date(artifact, as_of)
    team_rows = artifact.predictions.filter(pl.col("team_id") == team_id)
    if team_rows.height == 0:
        raise HTTPException(status_code=404, detail=f"No data for team {team_id}")
    coverage_over_time = (
        team_rows.group_by("prediction_date")
        .agg(pl.col("data_completeness").mean().alias("mean_data_completeness"))
        .sort("prediction_date")
    )
    player_coverage = (
        team_rows.group_by("player_id")
        .agg(pl.col("data_completeness").mean().alias("mean_data_completeness"))
        .sort("player_id")
    )
    return DataQualityResponse(
        team_id=team_id,
        as_at_date=as_at_date,
        coverage_over_time=[
            TeamDataQualityPoint(**row) for row in coverage_over_time.iter_rows(named=True)
        ],
        player_coverage_range=[
            PlayerCoverage(**row) for row in player_coverage.iter_rows(named=True)
        ],
    )


@app.get("/model-health", response_model=ModelHealthResponse)
def model_health() -> ModelHealthResponse:
    artifact = get_artifact()
    reference = get_model_health_reference()
    calibration = CalibrationReference(
        mean_prediction=reference.calibration["mean_prediction"],
        observed_rate=reference.calibration["observed_rate"],
        calibration_intercept=reference.calibration["calibration_intercept"],
        calibration_slope=reference.calibration["calibration_slope"],
        brier_score=reference.calibration["brier_score"],
        log_loss=reference.calibration["log_loss"],
    )
    operating_points = [
        OperatingPointBurden(
            review_rate=float(row["operating_point_value"]),
            alerts_per_100_player_days=row["alerts_per_100_player_days"],
            recall=row["recall"],
            false_alerts_per_captured_onset=row["false_alerts_per_captured_onset"],
        )
        for row in reference.operating_points
    ]
    final_test_result = FinalTestResult(
        player_days=int(reference.final_test_metrics["player_days"]),
        positive_days=int(reference.final_test_metrics["positive_days"]),
        roc_auc=reference.final_test_metrics["roc_auc"],
        claims=[FinalTestClaim(**claim) for claim in reference.final_test_claims],
        interpretation=(
            "Confirmatory sanity check on five represented onsets, not a performance "
            "claim (DEC-062, DEC-063)."
        ),
    )
    return ModelHealthResponse(
        as_at_date=artifact.covered_date_end,
        calibration=calibration,
        operating_points=operating_points,
        final_test_result=final_test_result,
    )
