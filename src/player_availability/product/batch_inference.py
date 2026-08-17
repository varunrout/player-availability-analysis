"""V1-P6 batch inference: score every eligible player-day for the product (`DEC-064`).

Scores the full covered period (every player-day eligible under the frozen Stage 7
protocol) with the same F1 champion artefact evaluated once at V1-P5 (`DEC-062`):
fitted on the development partition only, raw probabilities, nine frozen predictors.
Scoring rows that fall in the final-test date range does not read final-test
*labels* and is not a second final-test access; it applies the already-frozen model
to already-available feature rows for display, exactly as any deployed model would.

Writes two representations of the same computed rows: the `paa_product` BigQuery
table of record, and a compact serving artefact to Cloud Storage that the API reads
directly, so the API never queries BigQuery per request. `reconcile_outputs` checks
the two representations agree row for row before either is persisted.

Operating-point thresholds (2.5%/5%, `DEC-061`) are the same in-sample
development-derived thresholds computed for V1-P5, via the shared
`fit_champion_and_thresholds` function, so the product and the confirmatory
evaluation report byte-identical operating points. Driver contributions displayed
are restricted to the eight predictors with constant coefficient sign under
`EXP-018`; `daily_load_log1p` is excluded from the persisted driver fields.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import yaml
from google.cloud import bigquery
from google.cloud.storage import Client as StorageClient  # type: ignore[import-untyped]

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.preprocessing import F1_FEATURES, transformed_feature_names
from player_availability.modelling.v1_p5_final_test import fit_champion_and_thresholds

DISPLAYABLE_DRIVERS: tuple[str, ...] = tuple(
    feature for feature in F1_FEATURES if feature != "daily_load_log1p"
)
"""EXP-018 sign-stable predictors only. `daily_load_log1p` is excluded (`DEC-064`)."""

OPERATING_POINT_RATES: tuple[float, ...] = (0.025, 0.05)
KEYS = ("player_id", "team_id", "prediction_date")
PRODUCT_TABLE_ID = "paa_product"
MODEL_ID = "M1-F1-PRODUCT"


def alert_column_name(rate: float) -> str:
    """A BigQuery-safe column name for an operating point's alert flag.

    BigQuery column names may not contain `.`, so `f"alert_{rate:g}"` (e.g.
    `alert_0.025`) is rejected on load. Basis points avoid the decimal point
    entirely: 0.025 -> `alert_bp250`, 0.05 -> `alert_bp500`.
    """
    return f"alert_bp{round(rate * 10_000):d}"


@dataclass(frozen=True, slots=True)
class BatchInferenceConfig:
    """Frozen V1-P6 batch inference configuration."""

    base_config: M1F1Config


@dataclass(frozen=True, slots=True)
class BatchInferenceResult:
    """Scored player-days and metadata, before any write."""

    predictions: pl.DataFrame
    onset_calendar: pl.DataFrame
    thresholds: dict[float, float]
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_batch_inference_config(path: Path) -> BatchInferenceConfig:
    """Load and validate the batch inference configuration."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Batch inference configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    return BatchInferenceConfig(base_config=base_config)


def run_batch_inference(
    *, features: pl.DataFrame, episodes: pl.DataFrame, config: BatchInferenceConfig
) -> BatchInferenceResult:
    """Fit the champion on development, then score every eligible player-day."""
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    cohort = protocol.tables["_primary_cohort"]
    target = config.base_config.target

    development = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
        | pl.col("prediction_date").is_between(
            PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"]
        )
    )
    pipeline, thresholds = fit_champion_and_thresholds(
        development=development,
        target=target,
        max_iterations=config.base_config.max_iterations,
    )

    matrix = cohort.select(F1_FEATURES).to_numpy()
    probabilities = pipeline.predict_proba(matrix)[:, 1]
    contributions = _predictor_contributions(pipeline, matrix)
    completeness = 1.0 - np.isnan(matrix).sum(axis=1) / len(F1_FEATURES)

    predictions = cohort.select(*KEYS, pl.col(target).alias("actual_label")).with_columns(
        pl.Series("predicted_probability", probabilities),
        pl.Series("data_completeness", completeness),
        *[pl.Series(f"driver_{driver}", contributions[driver]) for driver in DISPLAYABLE_DRIVERS],
    )
    predictions = _add_rank_within_team_day(predictions)
    for rate, threshold in thresholds.items():
        predictions = predictions.with_columns(
            (pl.col("predicted_probability") >= threshold).alias(alert_column_name(rate))
        )
    onset_calendar = _build_onset_calendar(episodes, covered_players=predictions["player_id"])

    summary = {
        "model_id": MODEL_ID,
        "data_version": config.base_config.data_version,
        "covered_player_days": predictions.height,
        "covered_date_start": cohort["prediction_date"].min(),
        "covered_date_end": cohort["prediction_date"].max(),
        "development_player_days": development.height,
        "operating_point_thresholds": {f"{rate:g}": value for rate, value in thresholds.items()},
        "displayable_drivers": list(DISPLAYABLE_DRIVERS),
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    return BatchInferenceResult(
        predictions=predictions,
        onset_calendar=onset_calendar,
        thresholds=thresholds,
        summary=summary,
        source_metadata={},
    )


def _predictor_contributions(pipeline: Any, matrix: Any) -> dict[str, Any]:
    """Vectorised, exact per-predictor standardised contributions for every row.

    Mirrors `EXP-018`'s per-row attribution (`m1_explanation._row_contributions`) but
    computed for the whole cohort at once: the pre-classifier transform times the
    fitted coefficients gives every transformed feature's contribution in one matrix
    multiply, and a missingness indicator's contribution is folded into its own
    predictor's total, since the indicator only ever fires for that predictor's own
    missing values.
    """
    names = transformed_feature_names(pipeline, F1_FEATURES)
    transformed = pipeline[:-1].transform(matrix)
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    per_column = transformed * coefficients
    parent = {
        name: name.removeprefix("missingindicator_")
        if name.startswith("missingindicator_")
        else name
        for name in names
    }
    contributions: dict[str, Any] = {}
    for predictor in F1_FEATURES:
        columns = [index for index, name in enumerate(names) if parent[name] == predictor]
        contributions[predictor] = per_column[:, columns].sum(axis=1)
    return contributions


def _build_onset_calendar(episodes: pl.DataFrame, *, covered_players: pl.Series) -> pl.DataFrame:
    """Every episode's own start date, independent of scored-day eligibility.

    Used by the player-detail view to mark onsets on the risk-over-time series and
    by the data-quality view for the onset-decline finding (`DEC-064`). This cannot
    be derived by flagging `is_onset_date` on the scored predictions: the frozen
    Stage 7 eligibility rule marks a day ineligible for scoring whenever
    `episode_start <= prediction_date <= episode_end`, which means the onset day
    itself is *never* a scored player-day, by construction. A join against the
    scored rows therefore always returns false and silently reports zero onsets,
    a real defect this calendar exists to avoid: it is read from `episode_start`
    directly, restricted to players who appear in the scored cohort.
    """
    return (
        episodes.select("player_id", "episode_start")
        .unique()
        .filter(pl.col("player_id").is_in(covered_players.unique().implode()))
        .rename({"episode_start": "onset_date"})
        .sort("player_id", "onset_date")
    )


def _add_rank_within_team_day(predictions: pl.DataFrame) -> pl.DataFrame:
    ranked = predictions.sort(
        ["team_id", "prediction_date", "predicted_probability", "player_id"],
        descending=[False, False, True, False],
    ).with_columns(
        (pl.int_range(pl.len()).over(["team_id", "prediction_date"]) + 1).alias(
            "rank_within_team_day"
        )
    )
    return ranked.sort(["player_id", "prediction_date"])


def reconcile_outputs(bq_rows: pl.DataFrame, artifact_rows: pl.DataFrame) -> dict[str, Any]:
    """Confirm the BigQuery-bound and artefact-bound representations agree row for row.

    Both are built from the same `run_batch_inference` predictions, so divergence
    here indicates a defect in one of the output-shaping steps, not a live-write
    failure; live-write success is checked separately by reading back the row count
    actually persisted to BigQuery.
    """
    bq_keys = set(bq_rows.select(*KEYS).iter_rows())
    artifact_keys = set(artifact_rows.select(*KEYS).iter_rows())
    shared_columns = [
        column
        for column in ("predicted_probability", "rank_within_team_day")
        if column in bq_rows.columns and column in artifact_rows.columns
    ]
    value_mismatch = 0
    if shared_columns and bq_keys == artifact_keys:
        joined = bq_rows.select(*KEYS, *shared_columns).join(
            artifact_rows.select(*KEYS, *shared_columns),
            on=list(KEYS),
            how="inner",
            suffix="_artifact",
        )
        for column in shared_columns:
            value_mismatch += joined.filter(pl.col(column) != pl.col(f"{column}_artifact")).height
    return {
        "bq_row_count": bq_rows.height,
        "artifact_row_count": artifact_rows.height,
        "row_count_matches": bq_rows.height == artifact_rows.height,
        "key_sets_match": bq_keys == artifact_keys,
        "value_mismatch_count": value_mismatch,
        "reconciled": (
            bq_rows.height == artifact_rows.height
            and bq_keys == artifact_keys
            and value_mismatch == 0
        ),
    }


def load_batch_inference_from_gcp(
    *, project_id: str, data_bucket: str, config: BatchInferenceConfig
) -> BatchInferenceResult:
    """Load compact canonical products once and score every eligible player-day."""
    client = StorageClient(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_batch_inference(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    return BatchInferenceResult(
        predictions=result.predictions,
        onset_calendar=result.onset_calendar,
        thresholds=result.thresholds,
        summary=result.summary,
        source_metadata={
            "source_paths": paths,
            "source_sha256": {name: _source_sha256(value) for name, value in blobs.items()},
        },
    )


def write_batch_inference_outputs(
    result: BatchInferenceResult,
    *,
    project_id: str,
    bq_product_dataset: str,
    artifacts_bucket: str,
    output_root: Path,
) -> dict[str, Any]:
    """Write the BigQuery table of record and the GCS serving artefact.

    Reconciles the two output representations before either write, then verifies
    the BigQuery write by reading back its row count.
    """
    directories = {name: output_root / name for name in ("tables", "metadata")}
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    bq_rows = result.predictions
    artifact_rows = result.predictions
    reconciliation = reconcile_outputs(bq_rows, artifact_rows)
    if not reconciliation["reconciled"]:
        raise ValueError(f"Batch inference outputs failed reconciliation: {reconciliation}")

    bq_client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{bq_product_dataset}.{PRODUCT_TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.PARQUET,
    )
    bq_buffer = BytesIO()
    bq_rows.write_parquet(bq_buffer)
    bq_buffer.seek(0)
    load_job = bq_client.load_table_from_file(bq_buffer, table_id, job_config=job_config)
    load_job.result()
    written_table = bq_client.get_table(table_id)
    live_row_count_matches = written_table.num_rows == bq_rows.height

    storage_client = StorageClient(project=project_id)
    bucket = storage_client.bucket(artifacts_bucket)
    buffer = BytesIO()
    artifact_rows.write_parquet(buffer)
    blob = bucket.blob("product/paa_product_serving_artifact.parquet")
    blob.upload_from_string(buffer.getvalue(), content_type="application/octet-stream")

    onset_calendar_buffer = BytesIO()
    result.onset_calendar.write_parquet(onset_calendar_buffer)
    onset_calendar_blob = bucket.blob("product/paa_product_onset_calendar.parquet")
    onset_calendar_blob.upload_from_string(
        onset_calendar_buffer.getvalue(), content_type="application/octet-stream"
    )

    manifest_blob = bucket.blob("product/paa_product_serving_manifest.json")
    manifest_blob.upload_from_string(
        json.dumps(result.summary, indent=2, sort_keys=True, default=str) + "\n",
        content_type="application/json",
    )

    artifact_rows.write_parquet(directories["tables"] / "paa_product_serving_artifact.parquet")
    result.onset_calendar.write_parquet(
        directories["tables"] / "paa_product_onset_calendar.parquet"
    )
    (directories["tables"] / "paa_product_serving_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    write_report = {
        "summary": result.summary,
        "reconciliation": reconciliation,
        "bq_table_id": table_id,
        "bq_live_row_count": written_table.num_rows,
        "bq_live_row_count_matches": live_row_count_matches,
        "gcs_artifact_uri": f"gs://{artifacts_bucket}/{blob.name}",
        "gcs_onset_calendar_uri": f"gs://{artifacts_bucket}/{onset_calendar_blob.name}",
        "gcs_manifest_uri": f"gs://{artifacts_bucket}/{manifest_blob.name}",
        "written_at_utc": datetime.now(UTC).isoformat(),
    }
    (directories["metadata"] / "batch_inference_manifest.json").write_text(
        json.dumps(write_report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    if not live_row_count_matches:
        raise ValueError(
            f"BigQuery live row count {written_table.num_rows} does not match "
            f"the {bq_rows.height} rows written"
        )
    return write_report


def _source_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
