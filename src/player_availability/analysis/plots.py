"""Reproducible Phase A figures for subjective model-readiness analysis."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import matplotlib
import polars as pl

from player_availability.analysis.cohort import CORE_FEATURES, HORIZONS_DAYS

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


def render_phase_a_charts(features: pl.DataFrame, *, output_directory: Path) -> tuple[Path, ...]:
    """Render prevalence, coverage and positive-concentration figures from gold features."""
    output_directory.mkdir(parents=True, exist_ok=True)
    burn_in = _with_burn_in(features)
    return (
        _plot_label_prevalence(burn_in, output_directory / "label_prevalence_by_horizon.png"),
        _plot_feature_coverage(burn_in, output_directory / "feature_coverage_after_burn_in.png"),
        _plot_positive_concentration(
            burn_in, output_directory / "positive_7d_label_concentration.png"
        ),
    )


def _with_burn_in(features: pl.DataFrame) -> pl.DataFrame:
    starts = features.group_by("player_id").agg(pl.min("prediction_date").alias("start"))
    return (
        features.join(starts, on="player_id")
        .with_columns(
            (pl.col("prediction_date") >= pl.col("start") + timedelta(days=27)).alias(
                "history_eligible"
            )
        )
        .drop("start")
    )


def _plot_label_prevalence(features: pl.DataFrame, path: Path) -> Path:
    horizons: list[str] = []
    prevalence: list[float] = []
    positives: list[int] = []
    for horizon in HORIZONS_DAYS:
        cohort = features.filter(
            pl.col("history_eligible") & pl.col(f"eligible_new_onset_{horizon}d")
        )
        positive_count = cohort.filter(pl.col(f"injury_next_{horizon}d")).height
        horizons.append(f"{horizon} days")
        prevalence.append(100 * positive_count / cohort.height)
        positives.append(positive_count)
    figure, axis = plt.subplots(figsize=(7, 4.5), layout="constrained")
    bars = axis.bar(horizons, prevalence, color=["#2a9d8f", "#457b9d", "#e76f51"])
    axis.set_ylabel("Positive player-days (%)")
    axis.set_title("New-Onset Label Prevalence After 28-Day Burn-In")
    for bar, count, value in zip(bars, positives, prevalence, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            f"{count} ({value:.2f}%)",
            ha="center",
            va="bottom",
        )
    axis.set_ylim(0, max(prevalence) * 1.3)
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_feature_coverage(features: pl.DataFrame, path: Path) -> Path:
    cohort = features.filter(pl.col("history_eligible"))
    coverage = [
        float(100 * cohort.get_column(feature).is_not_null().sum() / cohort.height)
        for feature in CORE_FEATURES
    ]
    figure, axis = plt.subplots(figsize=(9, 5.5), layout="constrained")
    axis.barh(list(reversed(CORE_FEATURES)), list(reversed(coverage)), color="#457b9d")
    axis.set_xlim(0, 100)
    axis.set_xlabel("Non-null coverage (%)")
    axis.set_title("Feature Coverage After 28-Day Burn-In")
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_positive_concentration(features: pl.DataFrame, path: Path) -> Path:
    concentration = (
        features.filter(
            pl.col("history_eligible") & pl.col("eligible_new_onset_7d") & pl.col("injury_next_7d")
        )
        .group_by("player_id")
        .len()
        .sort("len", descending=True)
        .head(10)
    )
    labels = [f"player {index + 1}" for index in range(concentration.height)]
    counts = concentration.get_column("len").to_list()
    figure, axis = plt.subplots(figsize=(9, 4.5), layout="constrained")
    axis.bar(labels, counts, color="#e76f51")
    axis.set_ylabel("Positive 7-day player-days")
    axis.set_title("Positive 7-Day Labels Are Concentrated by Player")
    axis.tick_params(axis="x", rotation=35)
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path
