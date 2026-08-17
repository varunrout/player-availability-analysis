"""Loads the batch-inference serving artefact and static reference evidence (`DEC-064`).

The API reads the compact serving artefact `batch_inference` writes to Cloud
Storage; it never queries BigQuery per request. Model-health reference data
(calibration, `EXP-019` operating-point burden, the V1-P5 confirmatory result) is
read from the already-committed, already-decided evidence tables rather than
recomputed, since those are the numbers the governing decisions actually rest on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import polars as pl
from google.cloud.storage import Client as StorageClient  # type: ignore[import-untyped]

from player_availability.utils.paths import repo_root

OFFERED_REVIEW_RATES: tuple[float, ...] = (0.025, 0.05)
"""The two operating points DEC-061 offers. 1%/10%/20% are evidence-only, never product."""

DEFAULT_REVIEW_RATE = 0.025


@dataclass(frozen=True, slots=True)
class ServingArtifact:
    """The scored predictions plus the metadata needed to serve them."""

    predictions: pl.DataFrame
    thresholds: dict[float, float]
    covered_date_start: date
    covered_date_end: date
    generated_at_utc: str


@dataclass(frozen=True, slots=True)
class ModelHealthReference:
    """Static evidence for the model-health view, read from committed tables."""

    calibration: dict[str, Any]
    operating_points: list[dict[str, Any]]
    final_test_metrics: dict[str, Any]
    final_test_claims: list[dict[str, Any]]


def load_serving_artifact_from_path(directory: Path) -> ServingArtifact:
    """Load the artefact and its manifest from a local directory (tests, local dev)."""
    predictions = pl.read_parquet(directory / "paa_product_serving_artifact.parquet")
    manifest = json.loads((directory / "paa_product_serving_manifest.json").read_text())
    return _build_artifact(predictions, manifest)


def load_serving_artifact_from_gcs(*, project_id: str, bucket_name: str) -> ServingArtifact:
    """Load the artefact and its manifest from Cloud Storage (deployed API)."""
    client = StorageClient(project=project_id)
    bucket = client.bucket(bucket_name)
    predictions_bytes = bucket.blob(
        "product/paa_product_serving_artifact.parquet"
    ).download_as_bytes()
    manifest_bytes = bucket.blob("product/paa_product_serving_manifest.json").download_as_bytes()
    predictions = pl.read_parquet(BytesIO(predictions_bytes))
    manifest = json.loads(manifest_bytes)
    return _build_artifact(predictions, manifest)


def _build_artifact(predictions: pl.DataFrame, manifest: dict[str, Any]) -> ServingArtifact:
    thresholds = {
        float(rate): float(value) for rate, value in manifest["operating_point_thresholds"].items()
    }
    return ServingArtifact(
        predictions=predictions,
        thresholds=thresholds,
        covered_date_start=_parse_date(manifest["covered_date_start"]),
        covered_date_end=_parse_date(manifest["covered_date_end"]),
        generated_at_utc=str(manifest["generated_at_utc"]),
    )


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def load_model_health_reference(reference_root: Path | None = None) -> ModelHealthReference:
    """Load the committed evidence tables the model-health view presents."""
    root = reference_root or (repo_root() / "outputs" / "modelling")
    calibration = pl.read_csv(
        root / "exp_009_calibration" / "tables" / "arm_pooled_metrics.csv"
    ).filter(pl.col("arm") == "F1_raw")
    operating_points = pl.read_csv(
        root / "exp_019_alert_budget" / "tables" / "alert_budget_results.csv"
    ).filter(
        (pl.col("operating_point_type") == "percentile")
        & (pl.col("operating_point_value").is_in(list(OFFERED_REVIEW_RATES)))
    )
    final_test_metrics = pl.read_csv(
        root / "v1_p5_final_test" / "tables" / "final_test_metrics.csv"
    )
    final_test_claims = pl.read_csv(root / "v1_p5_final_test" / "tables" / "claims.csv")
    return ModelHealthReference(
        calibration=calibration.row(0, named=True),
        operating_points=operating_points.sort("operating_point_value").to_dicts(),
        final_test_metrics=final_test_metrics.row(0, named=True),
        final_test_claims=final_test_claims.to_dicts(),
    )
