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
) -> pl.DataFrame:
    """Bootstrap frozen predictions by player and calendar week."""
    records = list(predictions.iter_rows(named=True))
    rows: list[dict[str, Any]] = []
    for method in ("player_cluster_bootstrap", "temporal_week_block_bootstrap"):
        estimates: dict[str, list[float]] = {
            "brier_score": [],
            "average_precision": [],
        }
        clusters = _clusters(records, method)
        cluster_names = list(clusters)
        rng = random.Random(f"{random_seed}:{model_id}:{method}")
        for _ in range(iterations):
            sampled: list[dict[str, Any]] = []
            for _ in cluster_names:
                sampled.extend(clusters[rng.choice(cluster_names)])
            targets = [int(row[target]) for row in sampled]
            probabilities = [float(row["predicted_probability"]) for row in sampled]
            metrics = classification_metrics(targets, probabilities)
            for metric in estimates:
                value = metrics[metric]
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
