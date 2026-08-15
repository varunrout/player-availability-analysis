"""EXP-002 development-only naive operational baselines."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    run_stage_07_prospective_protocol,
)

EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class M0Config:
    """Frozen EXP-002 configuration."""

    experiment_id: str
    data_version: str
    target: str
    primary_horizon_days: int
    burn_in_days: int
    load_predictor: str
    load_threshold_quantile: float
    alert_review_rates: tuple[float, ...]
    bootstrap_iterations: int
    random_seed: int
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class M0Result:
    """Retained M0 tables, development predictions and run metadata."""

    tables: dict[str, pl.DataFrame]
    predictions: pl.DataFrame
    parameters: dict[str, Any]
    summary: dict[str, Any]


def load_m0_config(path: Path) -> M0Config:
    """Load and validate the versioned M0 YAML configuration."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("M0 configuration must be a mapping")
    rates = tuple(float(value) for value in raw["alert_review_rates"])
    config = M0Config(
        experiment_id=str(raw["experiment_id"]),
        data_version=str(raw["data_version"]),
        target=str(raw["target"]),
        primary_horizon_days=int(raw["primary_horizon_days"]),
        burn_in_days=int(raw["burn_in_days"]),
        load_predictor=str(raw["load_predictor"]),
        load_threshold_quantile=float(raw["load_threshold_quantile"]),
        alert_review_rates=rates,
        bootstrap_iterations=int(raw["bootstrap_iterations"]),
        random_seed=int(raw["random_seed"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.final_test_access:
        raise ValueError("EXP-002 development configuration cannot enable final-test access")
    if not 0.0 < config.load_threshold_quantile < 1.0:
        raise ValueError("load_threshold_quantile must be between zero and one")
    if not config.alert_review_rates or any(not 0.0 < rate < 1.0 for rate in rates):
        raise ValueError("alert_review_rates must contain values between zero and one")
    if config.bootstrap_iterations < 1:
        raise ValueError("bootstrap_iterations must be positive")
    return config


def load_m0_from_gcp(*, project_id: str, data_bucket: str, config: M0Config) -> M0Result:
    """Load compact gold/silver products and execute M0 without test evaluation."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_m0_baselines(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()}
    return M0Result(
        tables=result.tables,
        predictions=result.predictions,
        parameters={**result.parameters, "source_paths": paths, "source_sha256": hashes},
        summary=result.summary,
    )


def run_m0_baselines(
    *, features: pl.DataFrame, episodes: pl.DataFrame, config: M0Config
) -> M0Result:
    """Fit M0 parameters on train and evaluate validation without touching test."""
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    cohort = protocol.tables["_primary_cohort"]
    train_spec, validation_spec, test_spec = PARTITIONS
    train = _partition(cohort, train_spec)
    validation = _partition(cohort, validation_spec)
    test = _partition(cohort, test_spec)
    if config.target not in cohort.columns or config.load_predictor not in cohort.columns:
        raise ValueError("Configured target or load predictor is absent from the frozen cohort")

    train_prevalence = cast(float, train[config.target].mean())
    threshold_value = cast(
        float,
        train[config.load_predictor].quantile(
            config.load_threshold_quantile, interpolation="linear"
        ),
    )
    train_flag = train[config.load_predictor] >= threshold_value
    high_rate = _group_rate(train, config.target, train_flag, True, train_prevalence)
    low_rate = _group_rate(train, config.target, train_flag, False, train_prevalence)

    predictions = _build_predictions(
        validation=validation,
        config=config,
        train_prevalence=train_prevalence,
        threshold_value=threshold_value,
        high_rate=high_rate,
        low_rate=low_rate,
    )
    metrics = _metric_table(predictions)
    alerts, event_capture = _alert_tables(predictions, episodes, config)
    uncertainty = _uncertainty_table(predictions, config)
    support = _support_table(train, validation, test, config)
    baseline_definitions = pl.DataFrame(
        [
            {
                "baseline_id": "M0_GLOBAL_PREVALENCE",
                "probability_definition": "constant training-period target prevalence",
                "ranking_definition": "none; all validation scores are identical",
                "training_only_parameters": True,
            },
            {
                "baseline_id": "M0_RECENT_LOAD",
                "probability_definition": (
                    "training target rate above/below the training-only load threshold"
                ),
                "ranking_definition": config.load_predictor,
                "training_only_parameters": True,
            },
        ]
    )
    findings = _findings(
        train=train,
        validation=validation,
        predictions=predictions,
        metrics=metrics,
        event_capture=event_capture,
        config=config,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    parameters = {
        "training_prevalence": train_prevalence,
        "load_threshold_quantile": config.load_threshold_quantile,
        "load_threshold_value": threshold_value,
        "load_high_group_probability": high_rate,
        "load_low_group_probability": low_rate,
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config),
        "cohort_and_split_support": support,
        "baseline_definitions": baseline_definitions,
        "validation_metrics": metrics,
        "alert_budget_results": alerts,
        "event_capture_results": event_capture,
        "bootstrap_intervals": uncertainty,
        "baseline_findings": findings,
    }
    summary = {
        "experiment_id": config.experiment_id,
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_REVIEW_REQUIRED",
        "data_version": config.data_version,
        "target": config.target,
        "train_player_days": train.height,
        "validation_player_days": validation.height,
        "validation_positive_days": int(validation[config.target].sum()),
        "validation_represented_onsets": int(event_capture.select("onset_id").unique().height),
        "baseline_count": 2,
        "failure_count": failures,
        "review_count": reviews,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    return M0Result(tables, predictions, parameters, summary)


def write_m0_outputs(result: M0Result, output_root: Path) -> None:
    """Persist canonical M0 development artifacts."""
    directories = {
        name: output_root / name
        for name in ("figures", "tables", "predictions", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    result.predictions.write_parquet(directories["predictions"] / "validation_predictions.parquet")
    for name, figure in build_m0_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["metadata"] / "baseline_parameters.json").write_text(
        json.dumps(result.parameters, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["metadata"] / "exp_002_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_002_M0_BASELINE_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _partition(frame: pl.DataFrame, specification: dict[str, Any]) -> pl.DataFrame:
    return frame.filter(
        pl.col("prediction_date").is_between(
            specification["start_date"], specification["end_date"], closed="both"
        )
    )


def _group_rate(
    frame: pl.DataFrame,
    target: str,
    mask: pl.Series,
    flag: bool,
    fallback: float,
) -> float:
    subset = frame.filter(mask if flag else ~mask)
    return fallback if subset.is_empty() else cast(float, subset[target].mean())


def _build_predictions(
    *,
    validation: pl.DataFrame,
    config: M0Config,
    train_prevalence: float,
    threshold_value: float,
    high_rate: float,
    low_rate: float,
) -> pl.DataFrame:
    base = validation.select(
        "player_id", "team_id", "prediction_date", config.target, config.load_predictor
    )
    global_rows = base.with_columns(
        pl.lit("M0_GLOBAL_PREVALENCE").alias("baseline_id"),
        pl.lit(train_prevalence).alias("predicted_probability"),
        pl.lit(train_prevalence).alias("ranking_score"),
        pl.lit(False).alias("load_threshold_flag"),
    )
    load_rows = base.with_columns(
        pl.lit("M0_RECENT_LOAD").alias("baseline_id"),
        pl.when(pl.col(config.load_predictor) >= threshold_value)
        .then(pl.lit(high_rate))
        .otherwise(pl.lit(low_rate))
        .alias("predicted_probability"),
        pl.col(config.load_predictor).cast(pl.Float64).alias("ranking_score"),
        (pl.col(config.load_predictor) >= threshold_value).alias("load_threshold_flag"),
    )
    return pl.concat([global_rows, load_rows]).sort("baseline_id", "prediction_date", "player_id")


def _metric_table(predictions: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in predictions.group_by("baseline_id", maintain_order=True):
        baseline_id = str(key[0])
        y = [int(value) for value in group["injury_next_7d"]]
        probability = [float(value) for value in group["predicted_probability"]]
        ranking = [float(value) for value in group["ranking_score"]]
        rows.append(
            {
                "baseline_id": baseline_id,
                "player_days": len(y),
                "positive_days": sum(y),
                "prevalence": sum(y) / len(y),
                "brier_score": _brier(y, probability),
                "log_loss": _log_loss(y, probability),
                "average_precision": _average_precision(y, ranking),
                "roc_auc": _roc_auc(y, ranking),
                "ranking_estimable": len(set(ranking)) > 1,
            }
        )
    return pl.DataFrame(rows)


def _alert_tables(
    predictions: pl.DataFrame, episodes: pl.DataFrame, config: M0Config
) -> tuple[pl.DataFrame, pl.DataFrame]:
    alert_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for key, group in predictions.group_by("baseline_id", maintain_order=True):
        baseline_id = str(key[0])
        scores = [float(value) for value in group["ranking_score"]]
        ranking_estimable = len(set(scores)) > 1
        for rate in config.alert_review_rates:
            if ranking_estimable:
                alert_count = max(1, math.ceil(group.height * rate))
                ordered = group.sort(
                    ["ranking_score", "prediction_date", "player_id"],
                    descending=[True, False, False],
                )
                selected = ordered.head(alert_count)
                status = "ESTIMATED"
            else:
                selected = group.head(0)
                alert_count = 0
                status = "NOT_ESTIMABLE_CONSTANT_SCORE"
            events = _event_capture(selected, group, episodes, config, baseline_id, rate)
            event_rows.extend(events)
            captured = sum(int(row["captured"]) for row in events)
            positive_alerts = int(selected[config.target].sum()) if alert_count else 0
            false_alerts = alert_count - positive_alerts
            alert_rows.append(
                {
                    "baseline_id": baseline_id,
                    "review_rate": rate,
                    "status": status,
                    "eligible_player_days": group.height,
                    "alert_count": alert_count,
                    "alerts_per_100_player_days": 100 * alert_count / group.height,
                    "positive_alert_days": positive_alerts,
                    "represented_onsets": len(events),
                    "captured_onsets": captured,
                    "event_capture_rate": captured / len(events) if events else None,
                    "false_alerts_per_captured_onset": (
                        false_alerts / captured if captured else None
                    ),
                }
            )
    return pl.DataFrame(alert_rows), pl.DataFrame(event_rows)


def _event_capture(
    selected: pl.DataFrame,
    validation: pl.DataFrame,
    episodes: pl.DataFrame,
    config: M0Config,
    baseline_id: str,
    review_rate: float,
) -> list[dict[str, Any]]:
    validation_start = cast(date, validation["prediction_date"].min())
    validation_end = cast(date, validation["prediction_date"].max())
    onsets = (
        episodes.select("player_id", "team_id", "episode_start")
        .unique()
        .filter(
            pl.col("episode_start").is_between(
                validation_start + timedelta(days=1),
                validation_end + timedelta(days=config.primary_horizon_days),
                closed="both",
            )
        )
    )
    rows: list[dict[str, Any]] = []
    validation_keys = set(validation.select("player_id", "prediction_date").iter_rows())
    selected_keys = set(selected.select("player_id", "prediction_date").iter_rows())
    for onset in onsets.iter_rows(named=True):
        onset_date = onset["episode_start"]
        player_id = onset["player_id"]
        candidate_dates = [
            onset_date - timedelta(days=lead)
            for lead in range(1, config.primary_horizon_days + 1)
            if (player_id, onset_date - timedelta(days=lead)) in validation_keys
        ]
        if not candidate_dates:
            continue
        alert_dates = [day for day in candidate_dates if (player_id, day) in selected_keys]
        lead_times = [(onset_date - day).days for day in alert_dates]
        rows.append(
            {
                "baseline_id": baseline_id,
                "review_rate": review_rate,
                "onset_id": f"{player_id}|{onset_date.isoformat()}",
                "player_id": player_id,
                "team_id": onset["team_id"],
                "onset_date": onset_date,
                "captured": bool(alert_dates),
                "first_alert_lead_days": max(lead_times) if lead_times else None,
                "last_alert_lead_days": min(lead_times) if lead_times else None,
                "alert_days_in_window": len(alert_dates),
            }
        )
    return rows


def _uncertainty_table(predictions: pl.DataFrame, config: M0Config) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in predictions.group_by("baseline_id", maintain_order=True):
        baseline_id = str(key[0])
        records = list(group.iter_rows(named=True))
        for method in ("player_cluster_bootstrap", "temporal_week_block_bootstrap"):
            estimates: dict[str, list[float]] = {"brier_score": [], "average_precision": []}
            rng = random.Random(f"{config.random_seed}:{baseline_id}:{method}")
            clusters = _clusters(records, method)
            cluster_names = list(clusters)
            for _ in range(config.bootstrap_iterations):
                sampled: list[dict[str, Any]] = []
                for _ in cluster_names:
                    sampled.extend(clusters[rng.choice(cluster_names)])
                y = [int(row[config.target]) for row in sampled]
                probability = [float(row["predicted_probability"]) for row in sampled]
                ranking = [float(row["ranking_score"]) for row in sampled]
                estimates["brier_score"].append(_brier(y, probability))
                average_precision = _average_precision(y, ranking)
                if math.isfinite(average_precision):
                    estimates["average_precision"].append(average_precision)
            for metric, values in estimates.items():
                values.sort()
                rows.append(
                    {
                        "baseline_id": baseline_id,
                        "method": method,
                        "metric": metric,
                        "requested_iterations": config.bootstrap_iterations,
                        "valid_iterations": len(values),
                        "undefined_iterations": config.bootstrap_iterations - len(values),
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
            day = row["prediction_date"]
            iso = day.isocalendar()
            key = f"{iso.year}-{iso.week:02d}"
        clusters[key].append(row)
    return dict(clusters)


def _support_table(
    train: pl.DataFrame, validation: pl.DataFrame, test: pl.DataFrame, config: M0Config
) -> pl.DataFrame:
    rows = []
    for name, frame, evaluated in (
        ("train", train, True),
        ("validation", validation, True),
        ("test", test, False),
    ):
        rows.append(
            {
                "partition": name,
                "player_days": frame.height,
                "positive_days": int(frame[config.target].sum()),
                "player_count": frame["player_id"].n_unique(),
                "performance_evaluated": evaluated,
                "predictions_persisted": name == "validation",
            }
        )
    return pl.DataFrame(rows)


def _dataset_manifest(config: M0Config) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": config.experiment_id,
                "data_version": config.data_version,
                "target": config.target,
                "horizon_days": config.primary_horizon_days,
                "burn_in_days": config.burn_in_days,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _findings(
    *,
    train: pl.DataFrame,
    validation: pl.DataFrame,
    predictions: pl.DataFrame,
    metrics: pl.DataFrame,
    event_capture: pl.DataFrame,
    config: M0Config,
) -> pl.DataFrame:
    validation_dates = set(validation["prediction_date"].to_list())
    prediction_dates = set(predictions["prediction_date"].to_list())
    load_metric = metrics.filter(pl.col("baseline_id") == "M0_RECENT_LOAD").row(0, named=True)
    onset_count = event_capture.select("onset_id").unique().height
    return pl.DataFrame(
        [
            {
                "finding_id": "M0-01",
                "status": "PASS" if prediction_dates == validation_dates else "FAIL",
                "domain": "partition_integrity",
                "evidence": f"{len(prediction_dates)} prediction dates are validation-only",
            },
            {
                "finding_id": "M0-02",
                "status": "PASS",
                "domain": "training_scope",
                "evidence": (
                    f"prevalence and {config.load_threshold_quantile:.3f} load quantile "
                    f"learned from {train.height} training rows"
                ),
            },
            {
                "finding_id": "M0-03",
                "status": "PASS"
                if predictions["predicted_probability"].is_between(0.0, 1.0).all()
                else "FAIL",
                "domain": "prediction_validity",
                "evidence": "all probabilities lie in [0, 1]",
            },
            {
                "finding_id": "M0-04",
                "status": "REVIEW",
                "domain": "prevalence_shift",
                "evidence": (
                    f"train prevalence={cast(float, train[config.target].mean()):.6f}; "
                    "validation prevalence="
                    f"{cast(float, validation[config.target].mean()):.6f}"
                ),
            },
            {
                "finding_id": "M0-05",
                "status": "REVIEW",
                "domain": "benchmark_utility",
                "evidence": (
                    f"load AP={float(load_metric['average_precision']):.6f}; "
                    f"load Brier={float(load_metric['brier_score']):.6f}"
                ),
            },
            {
                "finding_id": "M0-06",
                "status": "REVIEW" if onset_count < 10 else "PASS",
                "domain": "outcome_support",
                "evidence": f"{onset_count} represented validation onsets",
            },
        ]
    )


def _brier(y: Sequence[int], probabilities: Sequence[float]) -> float:
    return sum(
        (probability - target) ** 2 for target, probability in zip(y, probabilities, strict=True)
    ) / len(y)


def _log_loss(y: Sequence[int], probabilities: Sequence[float]) -> float:
    total = 0.0
    for target, probability in zip(y, probabilities, strict=True):
        bounded = min(max(probability, EPSILON), 1.0 - EPSILON)
        total -= target * math.log(bounded) + (1 - target) * math.log(1.0 - bounded)
    return total / len(y)


def _average_precision(y: Sequence[int], scores: Sequence[float]) -> float:
    positives = sum(y)
    if positives == 0:
        return float("nan")
    grouped: dict[float, list[int]] = defaultdict(list)
    for target, score in zip(y, scores, strict=True):
        grouped[score].append(target)
    true_positive = 0
    predicted_positive = 0
    previous_recall = 0.0
    area = 0.0
    for score in sorted(grouped, reverse=True):
        group = grouped[score]
        true_positive += sum(group)
        predicted_positive += len(group)
        recall = true_positive / positives
        precision = true_positive / predicted_positive
        area += (recall - previous_recall) * precision
        previous_recall = recall
    return area


def _roc_auc(y: Sequence[int], scores: Sequence[float]) -> float:
    positive_scores = [score for target, score in zip(y, scores, strict=True) if target]
    negative_scores = [score for target, score in zip(y, scores, strict=True) if not target]
    if not positive_scores or not negative_scores:
        return float("nan")
    wins = 0.0
    for positive in positive_scores:
        for negative in negative_scores:
            wins += float(positive > negative) + 0.5 * float(positive == negative)
    return wins / (len(positive_scores) * len(negative_scores))


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


def build_m0_figures(result: M0Result) -> dict[str, Figure]:
    """Build the retained M0 development figures."""
    predictions = result.predictions
    metrics = result.tables["validation_metrics"]
    alerts = result.tables["alert_budget_results"].filter(pl.col("status") == "ESTIMATED")
    events = result.tables["event_capture_results"].filter(pl.col("captured"))
    figures: dict[str, Figure] = {}

    fig, axis = plt.subplots(figsize=(8, 4.5))
    probability_upper = max(0.05, cast(float, predictions["predicted_probability"].max()) * 1.1)
    for baseline_id, colour in (("M0_GLOBAL_PREVALENCE", "#4C78A8"), ("M0_RECENT_LOAD", "#F58518")):
        values = predictions.filter(pl.col("baseline_id") == baseline_id)["predicted_probability"]
        axis.hist(
            values,
            bins=20,
            range=(0.0, probability_upper),
            alpha=0.65,
            label=baseline_id,
            color=colour,
        )
    axis.set(
        title="Validation probability distributions",
        xlabel="Predicted probability",
        ylabel="Player-days",
        xlim=(0.0, probability_upper),
    )
    axis.legend()
    figures["validation_probability_distribution"] = fig

    fig, axis = plt.subplots(figsize=(7, 5))
    for baseline_id, marker, colour in (
        ("M0_GLOBAL_PREVALENCE", "o", "#4C78A8"),
        ("M0_RECENT_LOAD", "s", "#F58518"),
    ):
        group = predictions.filter(pl.col("baseline_id") == baseline_id)
        reliability = (
            group.group_by("predicted_probability")
            .agg(pl.col("injury_next_7d").mean().alias("observed_rate"), pl.len().alias("rows"))
            .sort("predicted_probability")
        )
        axis.scatter(
            reliability["predicted_probability"],
            reliability["observed_rate"],
            label=baseline_id,
            marker=marker,
            color=colour,
            s=55,
        )
    upper = max(0.02, cast(float, predictions["predicted_probability"].max()) * 1.1)
    axis.plot([0, upper], [0, upper], linestyle="--", color="#666666")
    axis.set(
        title="Development reliability",
        xlabel="Predicted probability",
        ylabel="Observed positive-day rate",
        xlim=(0, upper),
        ylim=(0, upper),
    )
    axis.legend()
    figures["reliability"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.bar(metrics["baseline_id"], metrics["average_precision"], color=["#4C78A8", "#F58518"])
    axis.axhline(
        float(metrics["prevalence"][0]),
        linestyle="--",
        color="#666666",
        label="Validation prevalence",
    )
    axis.set(title="Rare-event ranking benchmark", ylabel="Average precision")
    axis.tick_params(axis="x", rotation=12)
    axis.legend()
    figures["average_precision"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    if not alerts.is_empty():
        axis.plot(
            alerts["alerts_per_100_player_days"],
            alerts["event_capture_rate"],
            marker="o",
            color="#2A9D8F",
        )
    axis.set(
        title="Review capacity and onset capture",
        xlabel="Alerts per 100 player-days",
        ylabel="Represented-onset capture rate",
        ylim=(0, 1),
    )
    figures["alert_budget_event_capture"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    burden = alerts.drop_nulls("false_alerts_per_captured_onset")
    if not burden.is_empty():
        axis.plot(
            burden["alerts_per_100_player_days"],
            burden["false_alerts_per_captured_onset"],
            marker="o",
            color="#E45756",
        )
    else:
        axis.text(
            0.5,
            0.5,
            "No represented onsets captured\nat the frozen review budgets",
            transform=axis.transAxes,
            ha="center",
            va="center",
            color="#555555",
        )
    axis.set(
        title="Review burden",
        xlabel="Alerts per 100 player-days",
        ylabel="False alert-days per captured onset",
        xlim=(0.0, 5.5),
        ylim=(0.0, 1.0 if burden.is_empty() else None),
    )
    figures["alert_burden"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    if not events.is_empty():
        axis.hist(
            events["first_alert_lead_days"].drop_nulls(),
            bins=range(1, 9),
            color="#59A14F",
            align="left",
        )
    else:
        axis.text(
            0.5,
            0.5,
            "No represented onsets captured\nat the frozen review budgets",
            transform=axis.transAxes,
            ha="center",
            va="center",
            color="#555555",
        )
    axis.set(
        title="Lead time among captured onsets",
        xlabel="First alert lead time (days)",
        ylabel="Captured onsets",
        xticks=range(1, 8),
    )
    figures["captured_onset_lead_time"] = fig
    return figures


def _render_report(result: M0Result) -> str:
    metrics = result.tables["validation_metrics"]
    support = result.tables["cohort_and_split_support"]
    alerts = result.tables["alert_budget_results"]
    uncertainty = result.tables["bootstrap_intervals"]
    findings = result.tables["baseline_findings"]
    lines = [
        "# EXP-002 - M0 Naive Baseline Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{result.summary['status']}**. "
        "Project-owner benchmark review is required.",
        "",
        "No final-test predictions or performance metrics were created.",
        "",
        "## Partition Support",
        "",
        "| Partition | Player-days | Positive days | Performance evaluated |",
        "|---|---:|---:|---|",
    ]
    for row in support.iter_rows(named=True):
        lines.append(
            f"| {row['partition']} | {row['player_days']} | {row['positive_days']} | "
            f"{row['performance_evaluated']} |"
        )
    lines.extend(
        [
            "",
            "## Validation Metrics",
            "",
            "| Baseline | Brier | Log loss | Average precision | ROC-AUC |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in metrics.iter_rows(named=True):
        lines.append(
            f"| {row['baseline_id']} | {row['brier_score']:.6f} | "
            f"{row['log_loss']:.6f} | {row['average_precision']:.6f} | "
            f"{row['roc_auc']:.6f} |"
        )
    lines.extend(
        [
            "",
            "The global baseline has no estimable ranking because every validation "
            "score is identical.",
            "",
            "## Alert-Budget Simulation",
            "",
            "| Baseline | Review rate | Status | Alerts/100 days | Captured onsets | "
            "Capture rate |",
            "|---|---:|---|---:|---:|---:|",
        ]
    )
    for row in alerts.iter_rows(named=True):
        capture = "NA" if row["event_capture_rate"] is None else f"{row['event_capture_rate']:.3f}"
        lines.append(
            f"| {row['baseline_id']} | {row['review_rate']:.3f} | {row['status']} | "
            f"{row['alerts_per_100_player_days']:.3f} | {row['captured_onsets']} | "
            f"{capture} |"
        )
    lines.extend(
        [
            "",
            "## Bootstrap Uncertainty",
            "",
            "| Baseline | Method | Metric | Valid/Requested | 95% interval |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in uncertainty.iter_rows(named=True):
        lines.append(
            f"| {row['baseline_id']} | {row['method']} | {row['metric']} | "
            f"{row['valid_iterations']}/{row['requested_iterations']} | "
            f"{row['lower_95']:.6f} to {row['upper_95']:.6f} |"
        )
    lines.extend(
        ["", "## Findings", "", "| ID | Status | Domain | Evidence |", "|---|---|---|---|"]
    )
    for row in findings.iter_rows(named=True):
        lines.append(
            f"| {row['finding_id']} | {row['status']} | {row['domain']} | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These are exploratory benchmarks for prioritising practitioner review of "
            "self-reported injury-related onset risk. They are not medical thresholds, "
            "causal workload rules, player-clearance outputs or deployment evidence.",
            "",
            "## Gate",
            "",
            "The project owner must decide `BENCHMARK ACCEPT` or `REVISE` before "
            "M1 implementation.",
            "",
        ]
    )
    return "\n".join(lines)
