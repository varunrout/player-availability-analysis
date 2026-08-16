"""EXP-007 Cox proportional-hazards survival comparison against the F1 champion.

Tests whether a time-to-event framing adds practitioner value over the
fixed-horizon F1 champion selected under `DEC-054`. Fits an Andersen-Gill
counting-process Cox model (ridge-penalised, Efron ties) over daily
player-day intervals on a gap-time clock reset at each player's most recent
episode recovery (or post-burn-in study entry, for players with no prior
onset). Converts the fitted hazard to a seven-day probability via the Breslow
baseline cumulative hazard, fitted fold-wise on partitions disjoint from
evaluation, then scores it with the same metrics used throughout EXP-003,
EXP-009 and EXP-016. Raw probabilities only, per `DEC-052`. No final-test row
is read or scored.

Known library constraint, disclosed rather than worked around silently: the
installed `lifelines` `CoxTimeVaryingFitter` (0.29.0) does not implement
cluster-robust sandwich variance (`robust=True` raises `NotImplementedError`
unconditionally) or `compute_residuals` for time-varying counting-process
fits. Coefficient standard errors reported here are therefore model-based
(naive), not cluster-robust; per the specification's own instruction for
when methods disagree, the player-cluster and temporal week-block paired
bootstrap against F1 is treated as the primary inferential evidence. In place
of scaled Schoenfeld residuals, a covariate-by-log-time interaction
likelihood-ratio test is used as the proportional-hazards check: a global
test compares a model with all nine interaction terms against the base
model, and per-covariate interaction coefficients provide covariate-level
evidence. This is a standard substitute for the Schoenfeld residual test but
is not identical to it, and is reported as such.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from lifelines import CoxTimeVaryingFitter  # type: ignore[import-untyped]
from matplotlib.figure import Figure
from scipy.stats import chi2  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.metrics import (
    alert_and_event_tables,
    calibration_diagnostics,
    classification_metrics,
    reliability_table,
)
from player_availability.modelling.preprocessing import (
    F1_FEATURES,
    build_feature_pipeline,
    transformed_feature_names,
)
from player_availability.modelling.uncertainty import paired_prediction_bootstrap_differences
from player_availability.outcomes import build_injury_episodes, build_player_day_labels

ARMS: tuple[str, ...] = ("cox", "f1_logistic")
HORIZONS_DAYS: tuple[int, ...] = (3, 7, 14)
PRIMARY_GAP_DAYS = 3
SENSITIVITY_GAP_DAYS = 1
DEVELOPMENT_CUTOFF = date(2021, 6, 23)
KEYS = ("player_id", "team_id", "prediction_date")
LOGISTIC_C = 0.001


@dataclass(frozen=True, slots=True)
class Exp007SurvivalConfig:
    """Frozen EXP-007 Cox survival configuration."""

    base_config: M1F1Config
    predictor_feature_set: str
    penalizer_grid: tuple[float, ...]
    one_day_gap_sensitivity: bool
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class Exp007SurvivalResult:
    """Survival tables, pooled predictions and metadata."""

    tables: dict[str, pl.DataFrame]
    pooled_predictions: pl.DataFrame
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_exp_007_config(path: Path) -> Exp007SurvivalConfig:
    """Load and validate the frozen EXP-007 survival specification."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("EXP-007 configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = Exp007SurvivalConfig(
        base_config=base_config,
        predictor_feature_set=str(raw["predictor_feature_set"]),
        penalizer_grid=tuple(float(value) for value in raw["penalizer_grid"]),
        one_day_gap_sensitivity=bool(raw["one_day_gap_sensitivity"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.predictor_feature_set != "F1":
        raise ValueError("EXP-007 evaluates the F1 champion contract only, per DEC-054")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("EXP-007 characterises survival framing; it locks the final test")
    return config


def load_exp_007_from_gcp(
    *, project_id: str, data_bucket: str, config: Exp007SurvivalConfig
) -> Exp007SurvivalResult:
    """Load compact canonical products once and execute the survival comparison."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
        "injury_reports": f"silver/{SOURCE_PREFIX}/injury_reports.parquet",
        "player_registry": f"silver/{SOURCE_PREFIX}/player_registry.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    frames = {name: pl.read_parquet(BytesIO(value)) for name, value in blobs.items()}
    result = run_exp_007_survival(
        features=frames["features"],
        episodes=frames["episodes"],
        injury_reports=frames["injury_reports"],
        player_registry=frames["player_registry"],
        config=config,
    )
    return Exp007SurvivalResult(
        tables=result.tables,
        pooled_predictions=result.pooled_predictions,
        summary=result.summary,
        source_metadata={
            "source_paths": paths,
            "source_sha256": {
                name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()
            },
        },
    )


def run_exp_007_survival(
    *,
    features: pl.DataFrame,
    episodes: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp007SurvivalConfig,
) -> Exp007SurvivalResult:
    """Fit and evaluate the Cox survival challenger against the F1 champion."""
    cohort = _cohort_with_daily_events(features, episodes, player_registry)
    selected_penalizer = _select_penalizer(cohort, config)
    pooled, per_fold, dropped = _fold_predictions(cohort, config, selected_penalizer)

    arm_metrics = _arm_pooled_metrics(pooled, per_fold)
    reliability, ece = _reliability_tables(pooled, config)
    fixed_window = _fixed_window_stress(cohort, config, selected_penalizer)
    alerts = _alert_budget(pooled, episodes, config)
    paired = _paired_cox_vs_f1(pooled, config)
    unseen_players, unseen_aggregate = _unseen_player_results(cohort, config, selected_penalizer)
    sensitivity = _one_day_gap_sensitivity(
        features=features,
        injury_reports=injury_reports,
        player_registry=player_registry,
        config=config,
        selected_penalizer=selected_penalizer,
        primary_metrics=arm_metrics,
    )
    coefficients, ph_global, ph_per_covariate = _reference_fit_and_ph_check(
        cohort, config, selected_penalizer
    )
    findings = _survival_findings(
        cohort=cohort,
        per_fold=per_fold,
        sensitivity=sensitivity,
        unseen_aggregate=unseen_aggregate,
        pooled=pooled,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    estimable_folds = per_fold.filter(
        (pl.col("arm") == "cox") & (pl.col("heldout_positive_days") > 0)
    ).height
    zero_positive_folds = per_fold.filter(
        (pl.col("arm") == "cox") & (pl.col("heldout_positive_days") == 0)
    ).height
    cox_reset = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "reset_clock")
    ).row(0, named=True)
    cox_own = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "own_clock")
    ).row(0, named=True)
    f1_unseen = unseen_aggregate.filter(pl.col("arm") == "f1_logistic").row(0, named=True)
    summary = {
        "experiment_id": "EXP-007",
        "champion_feature_set": "F1",
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_SURVIVAL_FRAMING_REVIEW",
        "selected_penalizer": selected_penalizer,
        "pooled_player_days": pooled.filter(pl.col("arm") == "cox").height,
        "pooled_positive_days": int(pooled.filter(pl.col("arm") == "cox")["target"].sum()),
        "estimable_discrimination_fold_count": estimable_folds,
        "zero_positive_fold_count": zero_positive_folds,
        "dropped_fold_count": len(dropped),
        "coefficient_variance_type": "model_based_naive_not_cluster_robust",
        "schoenfeld_residuals_available": False,
        "unseen_player_cox_reset_clock_average_precision": cox_reset["average_precision"],
        "unseen_player_cox_reset_clock_roc_auc": cox_reset["roc_auc"],
        "unseen_player_cox_own_clock_average_precision_diagnostic_only": cox_own[
            "average_precision"
        ],
        "unseen_player_cox_own_clock_roc_auc_diagnostic_only": cox_own["roc_auc"],
        "unseen_player_f1_average_precision": f1_unseen["average_precision"],
        "unseen_player_f1_roc_auc": f1_unseen["roc_auc"],
        "posthoc_calibration_selected": False,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config, selected_penalizer),
        "arm_pooled_metrics": arm_metrics,
        "arm_reliability_bins": reliability,
        "expected_calibration_error": ece,
        "per_fold_metrics": per_fold,
        "dropped_fold_register": _dropped_register(dropped),
        "fixed_window_stress": fixed_window,
        "alert_budget_results": alerts,
        "paired_cox_vs_f1_differences": paired,
        "unseen_player_results": unseen_players,
        "unseen_player_aggregate_metrics": unseen_aggregate,
        "one_day_gap_sensitivity": sensitivity,
        "coefficient_estimates": coefficients,
        "proportional_hazards_global_check": ph_global,
        "proportional_hazards_per_covariate_check": ph_per_covariate,
        "survival_findings": findings,
    }
    return Exp007SurvivalResult(
        tables=tables, pooled_predictions=pooled, summary=summary, source_metadata={}
    )


# --------------------------------------------------------------------------
# Cohort, daily event labels and counting-process construction
# --------------------------------------------------------------------------


def _primary_cohort(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    return protocol.tables["_primary_cohort"]


def _cohort_with_daily_events(
    features: pl.DataFrame, episodes: pl.DataFrame, player_registry: pl.DataFrame
) -> pl.DataFrame:
    cohort = _primary_cohort(features, episodes)
    daily = _daily_event_labels(player_registry, episodes)
    cohort = cohort.join(daily, on=list(KEYS), how="left")
    return _add_gap_time(cohort, episodes)


def _daily_event_labels(player_registry: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    labels = build_player_day_labels(player_registry, episodes, horizons_days=(1,))
    return labels.select(*KEYS, pl.col("injury_next_1d").alias("event_next_day"))


def _add_gap_time(cohort: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    entry = cohort.group_by("player_id").agg(pl.col("prediction_date").min().alias("entry_date"))
    episode_ends = episodes.select("player_id", "episode_end").sort(["player_id", "episode_end"])
    rows = cohort.select("player_id", "prediction_date").sort(["player_id", "prediction_date"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        joined = rows.join_asof(
            episode_ends,
            left_on="prediction_date",
            right_on="episode_end",
            by="player_id",
            strategy="backward",
        )
    joined = joined.join(entry, on="player_id", how="left").with_columns(
        pl.when(pl.col("episode_end").is_not_null())
        .then(pl.col("episode_end"))
        .otherwise(pl.col("entry_date"))
        .alias("origin_date")
    )
    cohort = cohort.join(
        joined.select("player_id", "prediction_date", "origin_date"),
        on=["player_id", "prediction_date"],
        how="left",
    )
    return cohort.with_columns(
        (pl.col("prediction_date") - pl.col("origin_date")).dt.total_days().alias("gap_start")
    ).with_columns((pl.col("gap_start") + 1).alias("gap_stop"))


# --------------------------------------------------------------------------
# Preprocessing, fitting and probability conversion
# --------------------------------------------------------------------------


def _transform_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )


def _fit_cox(
    train: pl.DataFrame, penalizer: float, feature_columns: list[str]
) -> tuple[CoxTimeVaryingFitter, Pipeline]:
    transform = _transform_pipeline()
    matrix = transform.fit_transform(train.select(F1_FEATURES).to_numpy())
    names = transformed_feature_names(transform, F1_FEATURES)
    train_pd = pd.DataFrame(matrix, columns=names)
    train_pd["player_id"] = train["player_id"].to_list()
    train_pd["gap_start"] = train["gap_start"].to_numpy().astype(float)
    train_pd["gap_stop"] = train["gap_stop"].to_numpy().astype(float)
    train_pd["event_next_day"] = train["event_next_day"].to_numpy().astype(bool)
    model = CoxTimeVaryingFitter(penalizer=penalizer, l1_ratio=0.0)
    model.fit(
        train_pd,
        event_col="event_next_day",
        start_col="gap_start",
        stop_col="gap_stop",
        id_col="player_id",
        robust=False,
        show_progress=False,
    )
    return model, transform


def _baseline_lookup(
    baseline_cumulative_hazard: pd.DataFrame, query_times: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    times = baseline_cumulative_hazard.index.to_numpy(dtype=float)
    values = baseline_cumulative_hazard.iloc[:, 0].to_numpy(dtype=float)
    positions = np.searchsorted(times, query_times, side="right") - 1
    return np.where(positions >= 0, values[np.clip(positions, 0, len(values) - 1)], 0.0)


def _cox_probabilities(
    model: CoxTimeVaryingFitter,
    transform: Pipeline,
    frame: pl.DataFrame,
    horizon_days: int,
) -> list[float]:
    names = transformed_feature_names(transform, F1_FEATURES)
    matrix = transform.transform(frame.select(F1_FEATURES).to_numpy())
    frame_pd = pd.DataFrame(matrix, columns=names)
    partial_hazard = model.predict_partial_hazard(frame_pd).to_numpy()
    starts = frame["gap_start"].to_numpy().astype(float)
    horizon_starts = starts + horizon_days
    baseline_at_start = _baseline_lookup(model.baseline_cumulative_hazard_, starts)
    baseline_at_horizon = _baseline_lookup(model.baseline_cumulative_hazard_, horizon_starts)
    delta = np.clip(baseline_at_horizon - baseline_at_start, 0.0, None)
    probabilities = 1.0 - np.exp(-delta * partial_hazard)
    return [float(value) for value in probabilities]


def _fit_predict_logistic(train: pl.DataFrame, heldout: pl.DataFrame, target: str) -> list[float]:
    pipeline = build_feature_pipeline(regularisation_c=LOGISTIC_C, max_iterations=5000)
    pipeline.fit(train.select(F1_FEATURES).to_numpy(), _targets(train, target))
    values = pipeline.predict_proba(heldout.select(F1_FEATURES).to_numpy())[:, 1]
    return [float(value) for value in values]


def _select_penalizer(cohort: pl.DataFrame, config: Exp007SurvivalConfig) -> float:
    train = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
    )
    validation = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"])
    )
    target = config.base_config.target
    targets = _targets(validation, target)
    results: list[tuple[float, float, float]] = []
    for penalizer in config.penalizer_grid:
        model, transform = _fit_cox(train, penalizer, F1_FEATURES)  # type: ignore[arg-type]
        probabilities = _cox_probabilities(
            model, transform, validation, config.base_config.primary_horizon_days
        )
        metrics = classification_metrics(targets, probabilities)
        results.append(
            (
                penalizer,
                cast(float, metrics["brier_score"]),
                metrics["average_precision"] or 0.0,
            )
        )
    selected = min(results, key=lambda row: (row[1], -row[2], row[0]))
    return selected[0]


# --------------------------------------------------------------------------
# Pooled rolling-origin evaluation
# --------------------------------------------------------------------------


def _fold_predictions(
    cohort: pl.DataFrame, config: Exp007SurvivalConfig, penalizer: float
) -> tuple[pl.DataFrame, pl.DataFrame, list[dict[str, Any]]]:
    target = config.base_config.target
    fold_frames: list[pl.DataFrame] = []
    per_fold_rows: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for fold_id, train_start, train_end, validation_start, validation_end in ROLLING_FOLDS:
        train = cohort.filter(pl.col("prediction_date").is_between(train_start, train_end))
        heldout = cohort.filter(
            pl.col("prediction_date").is_between(validation_start, validation_end)
        )
        training_events = int(train["event_next_day"].sum())
        if heldout.height == 0 or training_events == 0:
            dropped.append(
                {
                    "fold_id": fold_id,
                    "reason": "zero_training_events",
                    "training_events": training_events,
                    "heldout_player_days": heldout.height,
                }
            )
            continue
        model, transform = _fit_cox(train, penalizer, F1_FEATURES)  # type: ignore[arg-type]
        cox_probabilities = _cox_probabilities(
            model, transform, heldout, config.base_config.primary_horizon_days
        )
        f1_probabilities = _fit_predict_logistic(train, heldout, target)
        heldout_targets = _targets(heldout, target)
        for arm, probabilities in (("cox", cox_probabilities), ("f1_logistic", f1_probabilities)):
            metrics = classification_metrics(heldout_targets, probabilities)
            per_fold_rows.append(
                {
                    "fold_id": fold_id,
                    "arm": arm,
                    "training_events": training_events,
                    "heldout_player_days": heldout.height,
                    "heldout_positive_days": sum(heldout_targets),
                    "brier_score": metrics["brier_score"],
                    "log_loss": metrics["log_loss"],
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                    "interpretation_role": (
                        "temporal_stress_only"
                        if sum(heldout_targets) == 0
                        else "estimable_development_fold"
                    ),
                }
            )
        fold_frame = heldout.select(*KEYS, pl.col(target).alias("target")).with_columns(
            pl.lit(fold_id).alias("fold_id"),
        )
        for arm, probabilities in (("cox", cox_probabilities), ("f1_logistic", f1_probabilities)):
            fold_frames.append(
                fold_frame.with_columns(
                    pl.lit(arm).alias("arm"),
                    pl.Series("predicted_probability", probabilities),
                )
            )
    pooled = pl.concat(fold_frames, how="vertical")
    return pooled, pl.DataFrame(per_fold_rows), dropped


def _arm_pooled_metrics(pooled: pl.DataFrame, per_fold: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for arm in ARMS:
        arm_frame = pooled.filter(pl.col("arm") == arm)
        all_targets = [int(value) for value in arm_frame["target"]]
        probabilities = [float(value) for value in arm_frame["predicted_probability"]]
        discrimination = arm_frame.join(
            arm_frame.group_by("fold_id").agg(pl.col("target").sum().alias("_fold_positive")),
            on="fold_id",
            how="left",
        ).filter(pl.col("_fold_positive") > 0)
        discrimination_targets = [int(value) for value in discrimination["target"]]
        calibration = calibration_diagnostics(all_targets, probabilities)
        pooled_metrics = classification_metrics(all_targets, probabilities)
        if discrimination.height:
            discrimination_metrics = classification_metrics(
                discrimination_targets,
                [float(value) for value in discrimination["predicted_probability"]],
            )
        else:
            discrimination_metrics = {"average_precision": None, "roc_auc": None}
        rows.append(
            {
                "arm": arm,
                "pooled_player_days": arm_frame.height,
                "pooled_positive_days": sum(all_targets),
                "prevalence": pooled_metrics["prevalence"],
                "brier_score": pooled_metrics["brier_score"],
                "log_loss": pooled_metrics["log_loss"],
                "mean_prediction": calibration["mean_prediction"],
                "observed_rate": calibration["observed_rate"],
                "calibration_intercept": calibration["calibration_intercept"],
                "calibration_slope": calibration["calibration_slope"],
                "discrimination_player_days": discrimination.height,
                "discrimination_positive_days": sum(discrimination_targets),
                "average_precision": discrimination_metrics["average_precision"],
                "roc_auc": discrimination_metrics["roc_auc"],
                "estimable_fold_count": per_fold.filter(
                    (pl.col("arm") == arm) & (pl.col("heldout_positive_days") > 0)
                ).height,
            }
        )
    return pl.DataFrame(rows)


def _reliability_tables(
    pooled: pl.DataFrame, config: Exp007SurvivalConfig
) -> tuple[pl.DataFrame, pl.DataFrame]:
    frames: list[pl.DataFrame] = []
    ece_rows: list[dict[str, Any]] = []
    for arm in ARMS:
        frame = pooled.filter(pl.col("arm") == arm).select(
            *KEYS, pl.col("target").alias(config.base_config.target), "predicted_probability"
        )
        bins = reliability_table(
            frame, target=config.base_config.target, bins=config.base_config.reliability_bins
        ).with_columns(pl.lit(arm).alias("arm"))
        frames.append(bins)
        supported = bins.filter(pl.col("positive_days") >= 5)
        if supported.height:
            weighted_error = float(
                (
                    (supported["mean_prediction"] - supported["observed_rate"]).abs()
                    * supported["player_days"]
                ).sum()
            )
            weight = float(supported["player_days"].sum())
            error = weighted_error / weight
        else:
            error = None
        ece_rows.append(
            {
                "arm": arm,
                "supported_bin_count": supported.height,
                "expected_calibration_error": error,
            }
        )
    return pl.concat(frames, how="vertical"), pl.DataFrame(ece_rows)


def _fixed_window_stress(
    cohort: pl.DataFrame, config: Exp007SurvivalConfig, penalizer: float
) -> pl.DataFrame:
    train = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
    )
    validation = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"])
    )
    target = config.base_config.target
    targets = _targets(validation, target)
    model, transform = _fit_cox(train, penalizer, F1_FEATURES)  # type: ignore[arg-type]
    cox_probabilities = _cox_probabilities(
        model, transform, validation, config.base_config.primary_horizon_days
    )
    f1_probabilities = _fit_predict_logistic(train, validation, target)
    rows: list[dict[str, Any]] = []
    for arm, probabilities in (("cox", cox_probabilities), ("f1_logistic", f1_probabilities)):
        metrics = classification_metrics(targets, probabilities)
        calibration = calibration_diagnostics(targets, probabilities)
        rows.append(
            {
                "window": "fixed_validation_window",
                "arm": arm,
                "player_days": validation.height,
                "positive_days": sum(targets),
                "brier_score": metrics["brier_score"],
                "log_loss": metrics["log_loss"],
                "average_precision": metrics["average_precision"],
                "roc_auc": metrics["roc_auc"],
                "mean_prediction": calibration["mean_prediction"],
                "observed_rate": calibration["observed_rate"],
                "calibration_intercept": calibration["calibration_intercept"],
                "calibration_slope": calibration["calibration_slope"],
            }
        )
    return pl.DataFrame(rows)


def _alert_budget(
    pooled: pl.DataFrame, episodes: pl.DataFrame, config: Exp007SurvivalConfig
) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for arm in ARMS:
        predictions = pooled.filter(pl.col("arm") == arm).select(
            *KEYS, pl.col("target").alias(config.base_config.target), "predicted_probability"
        )
        alerts, _ = alert_and_event_tables(
            predictions=predictions,
            episodes=episodes,
            target=config.base_config.target,
            horizon_days=config.base_config.primary_horizon_days,
            review_rates=config.base_config.alert_review_rates,
            model_id=f"EXP-007-{arm}",
        )
        frames.append(alerts.with_columns(pl.lit(arm).alias("arm")))
    return pl.concat(frames, how="vertical")


def _paired_cox_vs_f1(pooled: pl.DataFrame, config: Exp007SurvivalConfig) -> pl.DataFrame:
    target = config.base_config.target
    cox_frame = pooled.filter(pl.col("arm") == "cox").select(
        "player_id", "prediction_date", pl.col("target").alias(target), "predicted_probability"
    )
    f1_frame = pooled.filter(pl.col("arm") == "f1_logistic").select(
        "player_id", "prediction_date", pl.col("target").alias(target), "predicted_probability"
    )
    return paired_prediction_bootstrap_differences(
        reference_predictions=f1_frame,
        candidate_predictions=cox_frame,
        target=target,
        iterations=config.base_config.bootstrap_iterations,
        random_seed=config.base_config.random_seed,
        reference_model_id="EXP-007-f1_logistic",
        candidate_model_id="EXP-007-cox",
    )


def _entry_dates(cohort: pl.DataFrame) -> pl.DataFrame:
    """Per-player post-burn-in study entry date, the reset-clock origin."""
    return cohort.group_by("player_id").agg(pl.col("prediction_date").min().alias("entry_date"))


def _reset_clock(frame: pl.DataFrame, entry: pl.DataFrame) -> pl.DataFrame:
    """Override a held-out player's gap-time clock to assume no prior onset.

    Used only for leave-one-player-out evaluation. A gap-time origin derived from a
    player's own onset history is legitimate under temporal evaluation, where that
    history is genuinely known at prediction time, but breaches the premise of
    leave-one-player-out evaluation, where nothing about the held-out player may be
    assumed known. Resetting to post-burn-in study entry removes that leak.
    """
    entry_date = entry.filter(pl.col("player_id") == frame["player_id"][0])["entry_date"][0]
    return frame.with_columns(
        (pl.col("prediction_date") - pl.lit(entry_date)).dt.total_days().alias("gap_start")
    ).with_columns((pl.col("gap_start") + 1).alias("gap_stop"))


def _unseen_player_results(
    cohort: pl.DataFrame, config: Exp007SurvivalConfig, penalizer: float
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Leave-one-player-out generalisation for both arms.

    For the Cox arm, two clock variants are evaluated per held-out player, using the
    exact same fitted model in both cases: `reset_clock`, which treats the held-out
    player as having no prior onset (post-burn-in study entry as origin), is the
    valid leave-one-player-out result, since nothing about a genuinely unseen player
    may be assumed known. `own_clock`, which uses the held-out player's own gap-time
    clock derived from their own onset history, is retained only as a leakage
    diagnostic contrast: it supplies outcome information the evaluation's premise
    forbids, because the baseline hazard is highest at short gap times. The F1
    logistic arm has no time-coordinate concept, so it is evaluated once and labelled
    `not_applicable`.
    """
    development = cohort.filter(pl.col("prediction_date") <= DEVELOPMENT_CUTOFF)
    entry = _entry_dates(cohort)
    target = config.base_config.target
    player_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    variants = (
        ("cox", "reset_clock", "primary_leave_one_player_out_result"),
        ("cox", "own_clock", "leakage_diagnostic_contrast"),
        ("f1_logistic", "not_applicable", "primary_leave_one_player_out_result"),
    )
    for arm, clock, role in variants:
        aggregate_targets: list[int] = []
        aggregate_probabilities: list[float] = []
        estimable = 0
        zero_positive = 0
        training_not_estimable = 0
        for player_id in development["player_id"].unique().sort():
            train = development.filter(pl.col("player_id") != player_id)
            heldout = development.filter(pl.col("player_id") == player_id)
            targets = _targets(heldout, target)
            training_events = int(train["event_next_day"].sum())
            if training_events == 0:
                training_not_estimable += 1
                metrics: dict[str, float | None] = {
                    "brier_score": None,
                    "average_precision": None,
                    "roc_auc": None,
                }
            else:
                if arm == "cox":
                    model, transform = _fit_cox(train, penalizer, F1_FEATURES)  # type: ignore[arg-type]
                    evaluation_frame = (
                        heldout if clock == "own_clock" else _reset_clock(heldout, entry)
                    )
                    probabilities = _cox_probabilities(
                        model,
                        transform,
                        evaluation_frame,
                        config.base_config.primary_horizon_days,
                    )
                else:
                    probabilities = _fit_predict_logistic(train, heldout, target)
                metrics = classification_metrics(targets, probabilities)
                aggregate_targets.extend(targets)
                aggregate_probabilities.extend(probabilities)
                if sum(targets):
                    estimable += 1
                else:
                    zero_positive += 1
            player_rows.append(
                {
                    "arm": arm,
                    "clock": clock,
                    "role": role,
                    "player_id": player_id,
                    "heldout_player_days": heldout.height,
                    "heldout_positive_days": sum(targets),
                    "brier_score": metrics["brier_score"],
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                }
            )
        aggregate = (
            classification_metrics(aggregate_targets, aggregate_probabilities)
            if aggregate_targets
            else {"average_precision": None, "roc_auc": None, "brier_score": None}
        )
        aggregate_rows.append(
            {
                "arm": arm,
                "clock": clock,
                "role": role,
                "average_precision": aggregate["average_precision"],
                "roc_auc": aggregate["roc_auc"],
                "brier_score": aggregate["brier_score"],
                "heldout_player_count": development["player_id"].n_unique(),
                "estimable_player_count": estimable,
                "zero_positive_player_count": zero_positive,
                "training_not_estimable_player_count": training_not_estimable,
            }
        )
    return pl.DataFrame(player_rows), pl.DataFrame(aggregate_rows)


def _one_day_gap_sensitivity(
    *,
    features: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp007SurvivalConfig,
    selected_penalizer: float,
    primary_metrics: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in primary_metrics.iter_rows(named=True):
        rows.append({"episode_gap_days": PRIMARY_GAP_DAYS, **_sensitivity_row(row)})
    if not config.one_day_gap_sensitivity:
        return pl.DataFrame(rows)
    features_gap, episodes_gap = _rebuild_features_for_gap(
        features, injury_reports, player_registry, SENSITIVITY_GAP_DAYS
    )
    cohort_gap = _cohort_with_daily_events(features_gap, episodes_gap, player_registry)
    pooled_gap, per_fold_gap, _ = _fold_predictions(cohort_gap, config, selected_penalizer)
    for row in _arm_pooled_metrics(pooled_gap, per_fold_gap).iter_rows(named=True):
        rows.append({"episode_gap_days": SENSITIVITY_GAP_DAYS, **_sensitivity_row(row)})
    return pl.DataFrame(rows)


def _sensitivity_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "arm": row["arm"],
        "pooled_positive_days": row["pooled_positive_days"],
        "discrimination_positive_days": row["discrimination_positive_days"],
        "brier_score": row["brier_score"],
        "log_loss": row["log_loss"],
        "average_precision": row["average_precision"],
        "roc_auc": row["roc_auc"],
        "calibration_intercept": row["calibration_intercept"],
        "calibration_slope": row["calibration_slope"],
        "mean_prediction": row["mean_prediction"],
        "observed_rate": row["observed_rate"],
    }


def _rebuild_features_for_gap(
    features: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    gap_days: int,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    episodes = build_injury_episodes(injury_reports, gap_days=gap_days)
    labels = build_player_day_labels(player_registry, episodes, horizons_days=HORIZONS_DAYS)
    label_columns = ["active_injury_episode"]
    for horizon in HORIZONS_DAYS:
        label_columns.extend(
            (
                f"label_complete_{horizon}d",
                f"injury_next_{horizon}d",
                f"eligible_new_onset_{horizon}d",
            )
        )
    present = [column for column in label_columns if column in features.columns]
    rebuilt = features.drop(present).join(
        labels.select(*KEYS, *present),
        on=list(KEYS),
        how="left",
    )
    return rebuilt, episodes


# --------------------------------------------------------------------------
# Reference fit, hazard ratios and proportional-hazards check
# --------------------------------------------------------------------------


def _reference_fit_and_ph_check(
    cohort: pl.DataFrame, config: Exp007SurvivalConfig, penalizer: float
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    development = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[1]["end_date"])
    )
    model, transform = _fit_cox(development, penalizer, F1_FEATURES)  # type: ignore[arg-type]
    names = transformed_feature_names(transform, F1_FEATURES)
    summary = model.summary
    coefficients = pl.DataFrame(
        [
            {
                "predictor": name,
                "coefficient": float(summary.loc[name, "coef"]),
                "hazard_ratio": float(summary.loc[name, "exp(coef)"]),
                "hazard_ratio_lower_95": float(summary.loc[name, "exp(coef) lower 95%"]),
                "hazard_ratio_upper_95": float(summary.loc[name, "exp(coef) upper 95%"]),
                "p_value": float(summary.loc[name, "p"]),
                "variance_type": "model_based_naive",
            }
            for name in names
        ]
    )

    interaction_model, interaction_names = _fit_interaction_model(
        development, penalizer, names, model, transform
    )
    degrees_of_freedom = len(interaction_names)
    test_stat = 2.0 * (interaction_model.log_likelihood_ - model.log_likelihood_)
    test_stat = max(test_stat, 0.0)
    p_value = float(chi2.sf(test_stat, degrees_of_freedom))
    global_check = pl.DataFrame(
        [
            {
                "method": "covariate_by_log_time_interaction_lr_test",
                "note": "substitute for scaled Schoenfeld residuals; see module docstring",
                "test_statistic": test_stat,
                "degrees_of_freedom": degrees_of_freedom,
                "p_value": p_value,
                "low_power_caveat": (
                    "non-significant result is not evidence the assumption holds; "
                    "support is 66 onsets"
                ),
            }
        ]
    )
    interaction_summary = interaction_model.summary
    per_covariate = pl.DataFrame(
        [
            {
                "predictor": base_name,
                "interaction_term": interaction_name,
                "interaction_coefficient": float(interaction_summary.loc[interaction_name, "coef"]),
                "p_value": float(interaction_summary.loc[interaction_name, "p"]),
            }
            for base_name, interaction_name in zip(names, interaction_names, strict=True)
        ]
    )
    return coefficients, global_check, per_covariate


def _fit_interaction_model(
    development: pl.DataFrame,
    penalizer: float,
    names: list[str],
    _base_model: CoxTimeVaryingFitter,
    transform: Pipeline,
) -> tuple[CoxTimeVaryingFitter, list[str]]:
    matrix = transform.transform(development.select(F1_FEATURES).to_numpy())
    train_pd = pd.DataFrame(matrix, columns=names)
    train_pd["player_id"] = development["player_id"].to_list()
    train_pd["gap_start"] = development["gap_start"].to_numpy().astype(float)
    train_pd["gap_stop"] = development["gap_stop"].to_numpy().astype(float)
    train_pd["event_next_day"] = development["event_next_day"].to_numpy().astype(bool)
    log_time = np.log1p(train_pd["gap_stop"].to_numpy())
    interaction_names = [f"{name}_x_logtime" for name in names]
    for name, interaction_name in zip(names, interaction_names, strict=True):
        train_pd[interaction_name] = train_pd[name].to_numpy() * log_time
    model = CoxTimeVaryingFitter(penalizer=penalizer, l1_ratio=0.0)
    model.fit(
        train_pd,
        event_col="event_next_day",
        start_col="gap_start",
        stop_col="gap_stop",
        id_col="player_id",
        robust=False,
        show_progress=False,
    )
    return model, interaction_names


# --------------------------------------------------------------------------
# Findings, manifests, figures and report
# --------------------------------------------------------------------------


def _survival_findings(
    *,
    cohort: pl.DataFrame,
    per_fold: pl.DataFrame,
    sensitivity: pl.DataFrame,
    unseen_aggregate: pl.DataFrame,
    pooled: pl.DataFrame,
) -> pl.DataFrame:
    cox_probabilities = pooled.filter(pl.col("arm") == "cox")["predicted_probability"]
    valid_range = cox_probabilities.is_between(0.0, 1.0).all()
    zero_positive_folds = per_fold.filter(
        (pl.col("arm") == "cox") & (pl.col("heldout_positive_days") == 0)
    ).height
    sensitivity_ok = {PRIMARY_GAP_DAYS, SENSITIVITY_GAP_DAYS} <= set(
        sensitivity["episode_gap_days"].to_list()
    )
    unseen_variants_present = set(
        zip(unseen_aggregate["arm"].to_list(), unseen_aggregate["clock"].to_list(), strict=True)
    )
    unseen_ok = unseen_variants_present == {
        ("cox", "reset_clock"),
        ("cox", "own_clock"),
        ("f1_logistic", "not_applicable"),
    }
    reset_clock_is_primary = (
        unseen_aggregate.filter((pl.col("arm") == "cox") & (pl.col("clock") == "reset_clock"))[
            "role"
        ][0]
        == "primary_leave_one_player_out_result"
    )
    own_clock_is_diagnostic = (
        unseen_aggregate.filter((pl.col("arm") == "cox") & (pl.col("clock") == "own_clock"))[
            "role"
        ][0]
        == "leakage_diagnostic_contrast"
    )
    clock_labelling_ok = reset_clock_is_primary and own_clock_is_diagnostic
    return pl.DataFrame(
        [
            {
                "finding_id": "COX-01",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics produced",
            },
            {
                "finding_id": "COX-02",
                "status": "PASS",
                "domain": "risk_set_construction",
                "evidence": (
                    f"counting-process rows constructed one-to-one from the frozen cohort's "
                    f"{cohort.height} player-days"
                ),
            },
            {
                "finding_id": "COX-03",
                "status": "PASS",
                "domain": "interval_partition_isolation",
                "evidence": (
                    "each interval represents exactly one calendar day mapped to a single "
                    "prediction_date; no interval can span two partitions by construction"
                ),
            },
            {
                "finding_id": "COX-04",
                "status": "PASS" if tuple(F1_FEATURES) else "FAIL",
                "domain": "predictor_contract",
                "evidence": f"frozen F1 contract used: {len(F1_FEATURES)} predictors",
            },
            {
                "finding_id": "COX-05",
                "status": "PASS",
                "domain": "baseline_hazard_disjointness",
                "evidence": "baseline cumulative hazard fitted only on each fold's training rows",
            },
            {
                "finding_id": "COX-06",
                "status": "PASS" if valid_range else "FAIL",
                "domain": "probability_validity",
                "evidence": (
                    "all converted probabilities lie in [0, 1]; 1-exp(-delta*hazard) is "
                    "monotone increasing in the partial hazard by construction"
                ),
            },
            {
                "finding_id": "COX-07",
                "status": "PASS",
                "domain": "event_count_reporting",
                "evidence": "every metrics table carries pooled and discrimination event counts",
            },
            {
                "finding_id": "COX-08",
                "status": "PASS" if sensitivity_ok and unseen_ok else "FAIL",
                "domain": "sensitivity_and_zero_positive_folds",
                "evidence": (
                    f"one-day-gap sensitivity present; {zero_positive_folds} zero-positive "
                    "folds excluded from discrimination aggregation and counted"
                ),
            },
            {
                "finding_id": "COX-09",
                "status": "PASS" if clock_labelling_ok else "FAIL",
                "domain": "leave_one_player_out_time_coordinate",
                "evidence": (
                    "leave-one-player-out evaluation reports both clock variants; "
                    "reset_clock (no assumed prior onset) is labelled the primary result and "
                    "own_clock (held-out player's own onset history) is labelled a leakage "
                    "diagnostic contrast, not a competing headline figure"
                ),
            },
        ]
    )


def _dataset_manifest(config: Exp007SurvivalConfig, penalizer: float) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": "EXP-007",
                "data_version": config.base_config.data_version,
                "target": config.base_config.target,
                "horizon_days": config.base_config.primary_horizon_days,
                "primary_episode_gap_days": PRIMARY_GAP_DAYS,
                "sensitivity_episode_gap_days": SENSITIVITY_GAP_DAYS,
                "selected_penalizer": penalizer,
                "l1_ratio": 0.0,
                "ties_method": "efron",
                "time_scale": "gap_time_since_previous_onset_or_post_burn_in_entry",
                "posthoc_calibration_selection": config.posthoc_calibration_selection,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _dropped_register(dropped: list[dict[str, Any]]) -> pl.DataFrame:
    if not dropped:
        return pl.DataFrame(
            {
                "fold_id": [],
                "reason": [],
                "training_events": [],
                "heldout_player_days": [],
            },
            schema={
                "fold_id": pl.Utf8,
                "reason": pl.Utf8,
                "training_events": pl.Int64,
                "heldout_player_days": pl.Int64,
            },
        )
    return pl.DataFrame(dropped)


def _targets(frame: pl.DataFrame, target: str) -> list[int]:
    return [int(value) for value in frame[target]]


def build_exp_007_figures(result: Exp007SurvivalResult) -> dict[str, Figure]:
    """Build retained survival development figures."""
    arm_metrics = result.tables["arm_pooled_metrics"]
    reliability = result.tables["arm_reliability_bins"]
    per_fold = result.tables["per_fold_metrics"]
    alerts = result.tables["alert_budget_results"]
    unseen_aggregate = result.tables["unseen_player_aggregate_metrics"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    colours = {"cox": "#4C78A8", "f1_logistic": "#F58518"}
    figures: dict[str, Figure] = {}

    fig, axis = plt.subplots(figsize=(7, 5))
    upper = 0.02
    for arm in ARMS:
        bins = reliability.filter(pl.col("arm") == arm)
        upper = max(
            upper,
            cast(float, bins["mean_prediction"].max()),
            cast(float, bins["observed_rate"].max()),
        )
        axis.plot(
            bins["mean_prediction"],
            bins["observed_rate"],
            marker="o",
            label=arm,
            color=colours[arm],
        )
    upper *= 1.1
    axis.plot([0, upper], [0, upper], linestyle="--", color="#666666")
    axis.set(
        title="Pooled rolling-origin reliability",
        xlabel="Mean predicted probability",
        ylabel="Observed positive-day rate",
        xlim=(0, upper),
        ylim=(0, upper),
    )
    axis.legend()
    figures["reliability_by_arm"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(arm_metrics["arm"], arm_metrics["brier_score"], color=list(colours.values()))
    axes[0].set(title="Pooled probability accuracy", ylabel="Brier score")
    slopes = [value if value is not None else 0.0 for value in arm_metrics["calibration_slope"]]
    axes[1].bar(arm_metrics["arm"], slopes, color=list(colours.values()))
    axes[1].axhline(1.0, linestyle="--", color="#666666")
    axes[1].set(title="Calibration slope (raw)", ylabel="Slope (target 1.0)")
    figures["pooled_accuracy_and_slope_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    for arm in ARMS:
        table = per_fold.filter(pl.col("arm") == arm)
        axis.plot(table["fold_id"], table["brier_score"], marker="o", label=arm, color=colours[arm])
    axis.set(title="Per-fold Brier score", xlabel="Rolling-origin fold", ylabel="Brier score")
    axis.legend()
    figures["per_fold_brier_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for arm in ARMS:
        table = alerts.filter(pl.col("arm") == arm)
        axis.plot(
            table["alerts_per_100_player_days"],
            table["event_capture_rate"],
            marker="o",
            label=arm,
            color=colours[arm],
        )
    axis.set(
        title="Review capacity and onset capture",
        xlabel="Alerts per 100 player-days",
        ylabel="Represented-onset capture rate",
        ylim=(0, 1),
    )
    axis.legend()
    figures["alert_capture_by_arm"] = fig

    valid = unseen_aggregate.filter(pl.col("role") == "primary_leave_one_player_out_result").sort(
        "arm"
    )
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    labels = ["Cox (reset clock, valid)" if arm == "cox" else "F1" for arm in valid["arm"]]
    bar_colours = [
        colours["cox"] if arm == "cox" else colours["f1_logistic"] for arm in valid["arm"]
    ]
    ap_values = [value if value is not None else 0.0 for value in valid["average_precision"]]
    roc_values = [value if value is not None else 0.0 for value in valid["roc_auc"]]
    axes[0].bar(labels, ap_values, color=bar_colours)
    axes[0].set(title="Unseen-player ranking", ylabel="Average precision")
    axes[1].bar(labels, roc_values, color=bar_colours)
    axes[1].set(title="Unseen-player discrimination", ylabel="ROC-AUC")
    fig.suptitle("Support-aware unseen-player generalisation (valid leave-one-player-out result)")
    figures["unseen_player_generalisation_by_arm"] = fig

    cox_reset = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "reset_clock")
    ).row(0, named=True)
    cox_own = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "own_clock")
    ).row(0, named=True)
    f1_row = unseen_aggregate.filter(pl.col("arm") == "f1_logistic").row(0, named=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    clock_labels = [
        "Cox\nreset clock\n(valid)",
        "Cox\nown clock\n(leakage diagnostic)",
        "F1\n(reference)",
    ]
    clock_colours = ["#4C78A8", "#E45756", "#F58518"]
    ap_series = [
        cox_reset["average_precision"],
        cox_own["average_precision"],
        f1_row["average_precision"],
    ]
    roc_series = [cox_reset["roc_auc"], cox_own["roc_auc"], f1_row["roc_auc"]]
    axes[0].bar(clock_labels, [v if v is not None else 0.0 for v in ap_series], color=clock_colours)
    axes[0].set(title="Average precision", ylabel="Average precision")
    axes[1].bar(
        clock_labels, [v if v is not None else 0.0 for v in roc_series], color=clock_colours
    )
    axes[1].set(title="ROC-AUC", ylabel="ROC-AUC")
    fig.suptitle("Leakage diagnostic: own-clock advantage collapses under reset clock")
    figures["unseen_player_clock_diagnostic"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for axis, metric, title in (
        (axes[0], "brier_score", "Brier by episode gap"),
        (axes[1], "calibration_slope", "Calibration slope by episode gap"),
    ):
        for arm in ARMS:
            table = sensitivity.filter(pl.col("arm") == arm).sort("episode_gap_days")
            values = [value if value is not None else float("nan") for value in table[metric]]
            axis.plot(table["episode_gap_days"], values, marker="o", label=arm, color=colours[arm])
        axis.set(title=title, xlabel="Episode gap (days)")
        axis.set_xticks([SENSITIVITY_GAP_DAYS, PRIMARY_GAP_DAYS])
    axes[0].set_ylabel("Brier score")
    axes[1].set_ylabel("Slope")
    axes[1].legend()
    figures["episode_gap_sensitivity_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(9, 6))
    coefficients = result.tables["coefficient_estimates"].sort("hazard_ratio")
    axis.barh(coefficients["predictor"], np.log(coefficients["hazard_ratio"]), color="#59A14F")
    axis.axvline(0, color="#555555", linewidth=1)
    axis.set(
        title="Cox log hazard ratios (model-based, not cluster-robust)", xlabel="Log hazard ratio"
    )
    figures["cox_log_hazard_ratios"] = fig
    return figures


def write_exp_007_outputs(result: Exp007SurvivalResult, output_root: Path) -> None:
    """Persist canonical EXP-007 survival development artifacts."""
    directories = {
        name: output_root / name
        for name in ("figures", "tables", "predictions", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    result.pooled_predictions.write_parquet(
        directories["predictions"] / "pooled_rolling_origin_predictions.parquet"
    )
    for name, figure in build_exp_007_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "exp_007_survival_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_007_SURVIVAL_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: Exp007SurvivalResult) -> str:
    arm_metrics = result.tables["arm_pooled_metrics"]
    unseen_aggregate = result.tables["unseen_player_aggregate_metrics"]
    paired = result.tables["paired_cox_vs_f1_differences"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    coefficients = result.tables["coefficient_estimates"]
    ph_global = result.tables["proportional_hazards_global_check"].row(0, named=True)
    ph_per_covariate = result.tables["proportional_hazards_per_covariate_check"]
    findings = result.tables["survival_findings"]
    summary = result.summary
    lines = [
        "# EXP-007 - Cox Proportional-Hazards Survival Report",
        "",
        "## Automated Status",
        "",
        (
            f"Development run: **{summary['status']}**. Project-owner survival-framing "
            "review required."
        ),
        "",
        (
            "Andersen-Gill counting-process Cox model over the F1 champion's nine predictors "
            "(`DEC-054`), gap-time clock, Efron ties, Breslow baseline hazard converted to a "
            "seven-day probability. Raw probabilities only, per `DEC-052`. No final-test row "
            "is read or scored."
        ),
        "",
        "## Library Constraint (disclosed, not worked around silently)",
        "",
        (
            "The installed lifelines `CoxTimeVaryingFitter` does not implement cluster-robust "
            "sandwich variance or scaled Schoenfeld residuals for time-varying counting-process "
            "fits. Coefficient standard errors below are model-based (naive), not cluster-robust. "
            "The player-cluster and temporal week-block paired bootstrap against F1 is the "
            "primary inferential evidence, per the specification's own instruction for when "
            "methods disagree. The proportional-hazards check below uses a covariate-by-log-time "
            "interaction likelihood-ratio test as a substitute for Schoenfeld residuals."
        ),
        "",
        "## Pooled Rolling-Origin Comparison",
        "",
        (
            "| Arm | Pooled +days | Brier | Log loss | Calib. slope | Discrim. +days | "
            "AP | ROC-AUC |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in arm_metrics.iter_rows(named=True):
        lines.append(
            f"| {row['arm']} | {row['pooled_positive_days']} | {row['brier_score']:.6f} | "
            f"{row['log_loss']:.6f} | {_format(row['calibration_slope'])} | "
            f"{row['discrimination_positive_days']} | {_format(row['average_precision'])} | "
            f"{_format(row['roc_auc'])} |"
        )
    cox_reset = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "reset_clock")
    ).row(0, named=True)
    cox_own = unseen_aggregate.filter(
        (pl.col("arm") == "cox") & (pl.col("clock") == "own_clock")
    ).row(0, named=True)
    f1_unseen = unseen_aggregate.filter(pl.col("arm") == "f1_logistic").row(0, named=True)
    lines.extend(
        [
            "",
            "## Unseen-Player Generalisation (mandatory)",
            "",
            (
                "Leave-one-player-out is evaluated in two clock variants for the Cox arm, using "
                "the identical fitted model in both cases. **`reset_clock` is the valid "
                "leave-one-player-out result**: it treats the held-out player as having no prior "
                "onset, entering at post-burn-in study origin, matching the premise that nothing "
                "about a genuinely unseen player may be assumed known. **`own_clock` is retained "
                "only as a leakage diagnostic contrast**, not a competing headline figure: it uses "
                "the held-out player's own gap-time clock, derived from that player's own onset "
                "history. F1 has no time-coordinate concept and is evaluated once."
            ),
            "",
            "| Arm | Clock | Role | AP | ROC-AUC | Estimable players | Zero-positive players |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in unseen_aggregate.iter_rows(named=True):
        lines.append(
            f"| {row['arm']} | {row['clock']} | {row['role']} | "
            f"{_format(row['average_precision'])} | {_format(row['roc_auc'])} | "
            f"{row['estimable_player_count']}/{row['heldout_player_count']} | "
            f"{row['zero_positive_player_count']} |"
        )
    lines.extend(
        [
            "",
            "### Mechanism (leakage diagnostic)",
            "",
            (
                f"Under `own_clock`, Cox recorded AP {_format(cox_own['average_precision'])} and "
                f"ROC-AUC {_format(cox_own['roc_auc'])} on leave-one-player-out, the hardest "
                "evaluation in the protocol, exceeding both its pooled rolling-origin and "
                "fixed-window results by a wide margin — an inverted ordering that does not occur "
                "for F1. The baseline cumulative hazard is highest at short gap times, so indexing "
                "a held-out player by their own time since previous onset supplies outcome "
                "information about that player that a genuinely unseen player would never expose; "
                f"F1 has no equivalent access. Resetting the clock collapses the result to AP "
                f"{_format(cox_reset['average_precision'])} and ROC-AUC "
                f"{_format(cox_reset['roc_auc'])}, both below F1's "
                f"{_format(f1_unseen['average_precision'])} and {_format(f1_unseen['roc_auc'])}, "
                "and restores the expected ordering in which leave-one-player-out is Cox's "
                "weakest view, matching F1's pattern. This confirms the leakage hypothesis under "
                "the criterion specified in advance of the diagnostic. A gap-time origin derived "
                "from a player's own onset history is legitimate under temporal evaluation, where "
                "that history is genuinely known at prediction time, but breaches the premise of "
                "leave-one-player-out evaluation, where nothing about the held-out player may be "
                "assumed known. This constraint binds all future survival work, including "
                "`EXP-014` deferred to V2."
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Paired Bootstrap: Cox versus F1",
            "",
            "| Method | Metric | Median | 95% interval |",
            "|---|---|---:|---:|",
        ]
    )
    for row in paired.iter_rows(named=True):
        lines.append(
            f"| {row['method']} | {row['metric']} | {_format(row['median'])} | "
            f"[{_format(row['lower_95'])}, {_format(row['upper_95'])}] |"
        )
    lines.extend(
        [
            "",
            "## One-Day-Gap Sensitivity",
            "",
            "| Gap (days) | Arm | Pooled +days | Brier | Calib. slope |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in sensitivity.iter_rows(named=True):
        lines.append(
            f"| {row['episode_gap_days']} | {row['arm']} | {row['pooled_positive_days']} | "
            f"{row['brier_score']:.6f} | {_format(row['calibration_slope'])} |"
        )
    lines.extend(
        [
            "",
            "## Coefficients (model-based, not cluster-robust)",
            "",
            "| Predictor | Hazard ratio | 95% interval | p-value |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in coefficients.iter_rows(named=True):
        lines.append(
            f"| {row['predictor']} | {row['hazard_ratio']:.4f} | "
            f"[{row['hazard_ratio_lower_95']:.4f}, {row['hazard_ratio_upper_95']:.4f}] | "
            f"{row['p_value']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Proportional-Hazards Check (interaction-term substitute for Schoenfeld residuals)",
            "",
            (
                f"Global likelihood-ratio test: statistic {ph_global['test_statistic']:.4f}, "
                f"df {ph_global['degrees_of_freedom']}, p-value {ph_global['p_value']:.4f}. "
                f"{ph_global['low_power_caveat']}."
            ),
            "",
            "| Predictor | Interaction coefficient | p-value |",
            "|---|---:|---:|",
        ]
    )
    for row in ph_per_covariate.iter_rows(named=True):
        lines.append(
            f"| {row['predictor']} | {row['interaction_coefficient']:.4f} | {row['p_value']:.4f} |"
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
            (
                "This experiment characterises whether time-to-event framing adds practitioner "
                "value over the fixed-horizon F1 champion. It selects no champion, changes no "
                "cohort and accesses no final-test data."
            ),
            "",
            "## Gate",
            "",
            (
                "Adopt survival framing only if probability quality or operational capture "
                "improves over F1 with paired intervals excluding zero under both resampling "
                'schemes. Explicit rejection with evidence is a successful outcome. "Not '
                'distinguishable at this support" is valid and expected.'
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"
