"""FastAPI service reading only the batch-inference serving artefact (`DEC-064`).

Reachable only by the web service's identity in deployment: the service is deployed
with `--no-allow-unauthenticated` and an IAM `run.invoker` binding restricted to the
web service's own service account, which is what Cloud Run same-project
service-to-service calls actually check (network-level `--ingress internal` requires
Direct VPC egress on the caller, which this project does not provision; IAM
authentication delivers the same "reachable only by this identity" property without
that infrastructure). No endpoint queries BigQuery. Every data response carries the
"as at" date and the operating point in force.
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
    CoveredPeriodResponse,
    DataQualityResponse,
    DriverContribution,
    FinalTestClaim,
    FinalTestResult,
    HealthResponse,
    ModelHealthResponse,
    OnsetsByYear,
    OperatingPointBurden,
    OperatingPointInForce,
    PlayerCoverage,
    PlayerDetailResponse,
    PlayerRiskRow,
    ReliabilityBin,
    RiskSeriesPoint,
    SquadOverviewResponse,
    TeamDataQualityPoint,
)
from player_availability.config import get_settings
from player_availability.product.batch_inference import DISPLAYABLE_DRIVERS, alert_column_name

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
    development_burden = next(
        (
            row["false_alerts_per_captured_onset"]
            for row in reference.operating_points
            if abs(float(row["operating_point_value"]) - rate) < 1e-9
        ),
        None,
    )
    held_out = next(
        (
            row
            for held_out_rate, row in reference.held_out_operating_points.items()
            if abs(held_out_rate - rate) < 1e-9
        ),
        None,
    )
    return OperatingPointInForce(
        review_rate=rate,
        probability_threshold=threshold,
        development_false_alerts_per_captured_onset=development_burden,
        held_out_realised_alert_rate=(
            held_out["alerts_per_100_player_days"] / 100 if held_out else None
        ),
        held_out_false_alerts_per_captured_onset=(
            held_out["false_alerts_per_captured_onset"] if held_out else None
        ),
        held_out_represented_onsets=(held_out["represented_onsets"] if held_out else None),
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


@app.get("/covered-period", response_model=CoveredPeriodResponse)
def covered_period() -> CoveredPeriodResponse:
    """Team identifiers and the date range available, for the web selectors."""
    artifact = get_artifact()
    team_ids = sorted(artifact.predictions["team_id"].unique().to_list())
    return CoveredPeriodResponse(
        team_ids=team_ids,
        covered_date_start=artifact.covered_date_start,
        covered_date_end=artifact.covered_date_end,
        default_as_at_date=artifact.covered_date_end,
    )


@app.get("/squad-overview", response_model=SquadOverviewResponse)
def squad_overview(
    team_id: str,
    as_of: date | None = Query(default=None, alias="date"),
    review_rate: float = Query(default=DEFAULT_REVIEW_RATE),
) -> SquadOverviewResponse:
    artifact = get_artifact()
    as_at_date = _resolve_date(artifact, as_of)
    operating_point = _operating_point_in_force(artifact, review_rate)
    alert_column = alert_column_name(review_rate)
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
    alert_column = alert_column_name(review_rate)
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
        )
        for row in history.iter_rows(named=True)
    ]
    onset_dates = sorted(
        artifact.onset_calendar.filter(pl.col("player_id") == player_id)["onset_date"].to_list()
    )
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
        onset_dates=onset_dates,
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
    onsets_per_year = (
        artifact.onset_calendar.with_columns(pl.col("onset_date").dt.year().alias("year"))
        .group_by("year")
        .agg(pl.len().alias("represented_onsets"))
    )
    player_days_per_year = (
        artifact.predictions.with_columns(pl.col("prediction_date").dt.year().alias("year"))
        .group_by("year")
        .agg(pl.len().alias("player_days"))
    )
    onsets_by_year_table = (
        player_days_per_year.join(onsets_per_year, on="year", how="left")
        .with_columns(pl.col("represented_onsets").fill_null(0))
        .sort("year")
    )
    onsets_by_year = [OnsetsByYear(**row) for row in onsets_by_year_table.iter_rows(named=True)]
    onset_decline_note = _onset_decline_note(onsets_by_year)
    reference = get_model_health_reference()
    onset_reconciliation_note = _onset_reconciliation_note(onsets_by_year, reference)
    return DataQualityResponse(
        team_id=team_id,
        as_at_date=as_at_date,
        coverage_over_time=[
            TeamDataQualityPoint(**row) for row in coverage_over_time.iter_rows(named=True)
        ],
        player_coverage_range=[
            PlayerCoverage(**row) for row in player_coverage.iter_rows(named=True)
        ],
        onsets_by_year=onsets_by_year,
        onset_decline_note=onset_decline_note,
        onset_reconciliation_note=onset_reconciliation_note,
    )


def _onset_decline_note(onsets_by_year: list[OnsetsByYear]) -> str:
    if len(onsets_by_year) < 2:
        return (
            "Insufficient year coverage to compute the onset-decline finding. "
            "The 2020-to-2021 decline is documented in the project decision log "
            "(DEC-046) and tracks reporting engagement rather than injury incidence."
        )
    first, last = onsets_by_year[0], onsets_by_year[-1]
    ratio = first.represented_onsets / last.represented_onsets if last.represented_onsets else None
    ratio_text = f"roughly {ratio:.0f}-fold" if ratio else "a large factor"
    return (
        f"Represented onsets fell from {first.represented_onsets} in {first.year} to "
        f"{last.represented_onsets} in {last.year} ({ratio_text}), while player-days "
        f"stayed roughly flat ({first.player_days} against {last.player_days}). This "
        "decline tracks reporting engagement, not injury incidence (DEC-046): "
        "wellness reporting rises sharply on injury-onset days relative to ordinary "
        "days, so a decline in reported onsets reflects fewer players reporting, not "
        "fewer injuries occurring."
    )


def _onset_reconciliation_note(
    onsets_by_year: list[OnsetsByYear], reference: ModelHealthReference
) -> str:
    """Reconcile the onset counts a reviewer sees across different screens.

    Data quality, model health's EXP-019 evidence and model health's V1-P5
    result each report a true but different onset count, since each describes
    a different population after eligibility, burn-in and partitioning. Left
    unreconciled, a reviewer moving between views sees two numbers with
    nothing explaining the gap (`DEC-065` review finding).
    """
    total_onsets = sum(row.represented_onsets for row in onsets_by_year)
    pooled_onsets = int(reference.operating_points[0]["represented_onsets"])
    final_test_onsets = int(
        next(iter(reference.held_out_operating_points.values()))["represented_onsets"]
    )
    return (
        f"These are all {total_onsets} recorded onsets across the full period. "
        "Evaluated subsets are smaller, "
        f"{pooled_onsets} in the pooled rolling-origin evidence and {final_test_onsets} "
        "in the final test, after eligibility, burn-in and partitioning. The decline "
        "measured on frozen cohort partitions is steeper than the decline in the full "
        "calendar shown here."
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
    reliability_bins = [
        ReliabilityBin(
            reliability_bin=int(row["reliability_bin"]),
            player_days=int(row["player_days"]),
            positive_days=int(row["positive_days"]),
            mean_prediction=row["mean_prediction"],
            observed_rate=row["observed_rate"],
            bin_supported=bool(row["bin_supported"]),
        )
        for row in reference.reliability_bins
    ]
    operating_points = [
        OperatingPointBurden(
            review_rate=float(row["operating_point_value"]),
            alerts_per_100_player_days=row["alerts_per_100_player_days"],
            recall=row["recall"],
            false_alerts_per_captured_onset=row["false_alerts_per_captured_onset"],
        )
        for row in reference.operating_points
    ]
    held_out_operating_points = [
        OperatingPointBurden(
            review_rate=rate,
            alerts_per_100_player_days=row["alerts_per_100_player_days"],
            recall=row["recall"],
            false_alerts_per_captured_onset=row["false_alerts_per_captured_onset"],
        )
        for rate, row in sorted(reference.held_out_operating_points.items())
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
        c3_explanation=(
            "C3 (false-alert burden of development order) was not supported: at the "
            "2.5% operating point the held-out burden was 135.0 false alerts per "
            "captured onset against a development figure of 34.8. DEC-063 attributes "
            "this to two compounding, non-champion causes rather than a champion "
            "deficiency: the held-out partition's onset density is roughly half "
            "development's (0.565 against 1.071 onsets per thousand player-days), and "
            "the in-sample-derived threshold realised a 4.737% alert rate rather than "
            "the intended 2.5%. The two factors multiply to approximately 3.6x, closely "
            "reproducing the observed burden, while recall transferred within one "
            "percentage point (0.600 against 0.611 in development), confirming the "
            "champion's ranking behaviour held even though the threshold's calibration "
            "to a target rate did not."
        ),
    )
    return ModelHealthResponse(
        as_at_date=artifact.covered_date_end,
        calibration=calibration,
        reliability_bins=reliability_bins,
        operating_points=operating_points,
        held_out_operating_points=held_out_operating_points,
        final_test_result=final_test_result,
    )
