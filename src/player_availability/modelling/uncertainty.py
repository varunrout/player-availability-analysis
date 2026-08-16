"""Dependence-aware uncertainty for frozen development predictions."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import polars as pl

from player_availability.modelling.metrics import classification_metrics


def prediction_bootstrap_intervals(
    *,
    predictions: pl.DataFrame,
    target: str,
    iterations: int,
    random_seed: int,
    model_id: str,
    metrics: tuple[str, ...] = ("brier_score", "average_precision"),
) -> pl.DataFrame:
    """Bootstrap frozen predictions by player and calendar week.

    `metrics` restricts which metrics are estimated from the population passed as
    `predictions`. Callers whose point estimate for a metric is computed on a
    different row population than another metric (for example, average precision
    computed only on discrimination-eligible rows while Brier uses the full pooled
    population, per `CAL-08`-style zero-positive-fold exclusion) must call this
    function once per population and pass the matching `metrics` subset, rather than
    bootstrapping every metric from a single population that may not match every
    metric's own point-estimate population. See `BOOT-01`.
    """
    records = list(predictions.iter_rows(named=True))
    rows: list[dict[str, Any]] = []
    for method in ("player_cluster_bootstrap", "temporal_week_block_bootstrap"):
        estimates: dict[str, list[float]] = {metric: [] for metric in metrics}
        clusters = _clusters(records, method)
        cluster_names = list(clusters)
        rng = random.Random(f"{random_seed}:{model_id}:{method}")
        for _ in range(iterations):
            sampled: list[dict[str, Any]] = []
            for _ in cluster_names:
                sampled.extend(clusters[rng.choice(cluster_names)])
            targets = [int(row[target]) for row in sampled]
            probabilities = [float(row["predicted_probability"]) for row in sampled]
            resampled_metrics = classification_metrics(targets, probabilities)
            for metric in estimates:
                value = resampled_metrics[metric]
                if value is not None and math.isfinite(value):
                    estimates[metric].append(value)
        for metric, values in estimates.items():
            values.sort()
            rows.append(
                {
                    "model_id": model_id,
                    "method": method,
                    "metric": metric,
                    "requested_iterations": iterations,
                    "valid_iterations": len(values),
                    "undefined_iterations": iterations - len(values),
                    "lower_95": _percentile(values, 0.025),
                    "median": _percentile(values, 0.5),
                    "upper_95": _percentile(values, 0.975),
                }
            )
    return pl.DataFrame(rows)


def paired_prediction_bootstrap_differences(
    *,
    reference_predictions: pl.DataFrame,
    candidate_predictions: pl.DataFrame,
    target: str,
    iterations: int,
    random_seed: int,
    reference_model_id: str,
    candidate_model_id: str,
    metrics: tuple[str, ...] = ("brier_score", "average_precision"),
) -> pl.DataFrame:
    """Bootstrap paired candidate-minus-reference metric differences.

    `metrics` restricts which metrics are estimated from the population passed via
    `reference_predictions`/`candidate_predictions`. Callers whose point-estimate
    population differs by metric (Brier over the full pooled population, average
    precision over the discrimination-eligible subset with zero-positive folds
    excluded, per `CAL-08`) must call this function once per population and pass the
    matching `metrics` subset. Bootstrapping average precision over a population that
    includes zero-positive-fold rows the point estimate excludes produces a median
    whose sign can contradict the point-estimate difference; see `BOOT-01`.
    """
    keys = ["player_id", "prediction_date", target]
    paired = reference_predictions.select(
        *keys, pl.col("predicted_probability").alias("reference_probability")
    ).join(
        candidate_predictions.select(
            *keys, pl.col("predicted_probability").alias("candidate_probability")
        ),
        on=keys,
        how="inner",
        validate="1:1",
    )
    if (
        paired.height != reference_predictions.height
        or paired.height != candidate_predictions.height
    ):
        raise ValueError("Paired predictions must contain identical player-day target rows")
    records = list(paired.iter_rows(named=True))
    rows: list[dict[str, Any]] = []
    for method in ("player_cluster_bootstrap", "temporal_week_block_bootstrap"):
        estimates: dict[str, list[float]] = {metric: [] for metric in metrics}
        clusters = _clusters(records, method)
        cluster_names = list(clusters)
        rng = random.Random(f"{random_seed}:{reference_model_id}:{candidate_model_id}:{method}")
        for _ in range(iterations):
            sampled: list[dict[str, Any]] = []
            for _ in cluster_names:
                sampled.extend(clusters[rng.choice(cluster_names)])
            targets = [int(row[target]) for row in sampled]
            reference = [float(row["reference_probability"]) for row in sampled]
            candidate = [float(row["candidate_probability"]) for row in sampled]
            reference_metrics = classification_metrics(targets, reference)
            candidate_metrics = classification_metrics(targets, candidate)
            for metric in estimates:
                before = reference_metrics[metric]
                after = candidate_metrics[metric]
                if before is not None and after is not None:
                    difference = after - before
                    if math.isfinite(difference):
                        estimates[metric].append(difference)
        for metric, values in estimates.items():
            values.sort()
            rows.append(
                {
                    "reference_model_id": reference_model_id,
                    "candidate_model_id": candidate_model_id,
                    "method": method,
                    "metric": metric,
                    "difference_direction": "candidate_minus_reference",
                    "requested_iterations": iterations,
                    "valid_iterations": len(values),
                    "undefined_iterations": iterations - len(values),
                    "lower_95": _percentile(values, 0.025),
                    "median": _percentile(values, 0.5),
                    "upper_95": _percentile(values, 0.975),
                }
            )
    return pl.DataFrame(rows)


def paired_bootstrap_agrees_with_point_estimate(
    paired: pl.DataFrame,
    point_estimate_differences: dict[str, float],
    *,
    negligible_difference: float = 1e-5,
) -> bool:
    """Check every paired-bootstrap median shares its point estimate's sign (`BOOT-01`).

    `point_estimate_differences` maps metric name to the candidate-minus-reference
    point-estimate difference, computed on the same population as that metric's
    bootstrap (see `paired_prediction_bootstrap_differences`). A defined median whose
    sign contradicts a point-estimate difference larger than `negligible_difference`
    indicates a population mismatch between the point estimate and the bootstrap.
    Differences at or below `negligible_difference` are exempt: with very few clusters
    (as few as two players), ordinary resampling noise can flip the sign of a
    razor-thin, effectively-zero difference without any population mismatch, and that
    is not the failure this check exists to catch.
    """
    for metric, point_difference in point_estimate_differences.items():
        if abs(point_difference) <= negligible_difference:
            continue
        for median in paired.filter(pl.col("metric") == metric)["median"]:
            if median is None or not math.isfinite(median) or median == 0.0:
                continue
            if (median > 0) != (point_difference > 0):
                return False
    return True


def _clusters(records: list[dict[str, Any]], method: str) -> dict[str, list[dict[str, Any]]]:
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if method == "player_cluster_bootstrap":
            key = str(row["player_id"])
        else:
            iso = row["prediction_date"].isocalendar()
            key = f"{iso.year}-{iso.week:02d}"
        clusters[key].append(row)
    return dict(clusters)


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return float("nan")
    position = (len(values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction
