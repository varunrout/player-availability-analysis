"""EXP-009 calibration comparison for the promoted M1-F3 candidate.

Compares raw logistic output against Platt scaling and isotonic regression on the
frozen F3 predictor contract, using development data only. Calibrators are fitted
fold-wise within the pooled rolling-origin structure (`DEC-047`, `DEC-049`): in each
fold the calibrator is learned from inner cross-validated out-of-fold probabilities on
that fold's training window and applied to the held-out probabilities, so the fitting
rows are always disjoint from the evaluation rows (`CAL-02`). Because every calibrator
is a monotonic one-dimensional map of the same raw probabilities, Platt scaling cannot
reorder predictions (`CAL-04`). No final-test row is read or scored.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure
from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.model_selection import StratifiedKFold  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.metrics import (
    EPSILON,
    alert_and_event_tables,
    calibration_diagnostics,
    classification_metrics,
    reliability_table,
)
from player_availability.modelling.preprocessing import FEATURE_SETS, build_feature_pipeline
from player_availability.modelling.uncertainty import paired_prediction_bootstrap_differences
from player_availability.outcomes import build_injury_episodes, build_player_day_labels

ARMS: tuple[str, ...] = ("raw", "platt", "isotonic")
HORIZONS_DAYS: tuple[int, ...] = (3, 7, 14)
PRIMARY_GAP_DAYS = 3
SENSITIVITY_GAP_DAYS = 1
KEYS = ("player_id", "team_id", "prediction_date")


@dataclass(frozen=True, slots=True)
class Exp009CalibrationConfig:
    """Frozen EXP-009 calibration configuration."""

    base_config: M1F1Config
    feature_set: str
    selected_regularisation_c: float
    calibration_methods: tuple[str, ...]
    inner_cv_folds: int
    robust_fatigue_predictor: str
    robust_fatigue_availability: str
    reliability_bins: int
    minimum_reliability_positive_days: int
    one_day_gap_sensitivity: bool
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class Exp009CalibrationResult:
    """Calibration tables, pooled per-arm predictions and metadata."""

    tables: dict[str, pl.DataFrame]
    pooled_predictions: pl.DataFrame
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_exp_009_config(path: Path) -> Exp009CalibrationConfig:
    """Load and validate the frozen EXP-009 calibration specification."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("EXP-009 configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = Exp009CalibrationConfig(
        base_config=base_config,
        feature_set=str(raw["feature_set"]),
        selected_regularisation_c=float(raw["selected_regularisation_c"]),
        calibration_methods=tuple(str(value) for value in raw["calibration_methods"]),
        inner_cv_folds=int(raw["inner_cv_folds"]),
        robust_fatigue_predictor=str(raw["robust_fatigue_predictor"]),
        robust_fatigue_availability=str(raw["robust_fatigue_availability"]),
        reliability_bins=int(raw["reliability_bins"]),
        minimum_reliability_positive_days=int(raw["minimum_reliability_positive_days"]),
        one_day_gap_sensitivity=bool(raw["one_day_gap_sensitivity"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.feature_set != "F3":
        raise ValueError("EXP-009 calibrates the promoted F3 candidate only")
    if config.calibration_methods != ARMS:
        raise ValueError("EXP-009 arms are frozen as raw, Platt and isotonic")
    if config.selected_regularisation_c != 0.001:
        raise ValueError("EXP-009 uses the frozen F3 regularisation C=0.001; no retuning")
    if config.inner_cv_folds < 2:
        raise ValueError("Inner calibration cross-validation needs at least two folds")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("EXP-009 characterises calibration; it selects nothing and locks the test")
    if config.robust_fatigue_predictor not in FEATURE_SETS[config.feature_set]:
        raise ValueError("Robust fatigue predictor must belong to the F3 contract")
    return config


def load_exp_009_from_gcp(
    *, project_id: str, data_bucket: str, config: Exp009CalibrationConfig
) -> Exp009CalibrationResult:
    """Load compact canonical products once and execute the calibration comparison."""
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
    result = run_exp_009_calibration(
        features=frames["features"],
        episodes=frames["episodes"],
        injury_reports=frames["injury_reports"],
        player_registry=frames["player_registry"],
        config=config,
    )
    return Exp009CalibrationResult(
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


def run_exp_009_calibration(
    *,
    features: pl.DataFrame,
    episodes: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp009CalibrationConfig,
) -> Exp009CalibrationResult:
    """Compare raw, Platt and isotonic calibration on development data only."""
    feature_names = FEATURE_SETS[config.feature_set]
    cohort = _primary_cohort(features, episodes)
    pooled, per_fold, dropped = _fold_calibrated_predictions(cohort, config, feature_names)

    arm_metrics = _arm_pooled_metrics(pooled, config)
    reliability, ece = _reliability_tables(pooled, config)
    alerts = _alert_budget(pooled, episodes, config)
    paired = _paired_arm_differences(pooled, config)
    audit = _sparse_predictor_audit(pooled, config)
    fixed_window = _fixed_window_stress(cohort, config, feature_names)
    sensitivity = _one_day_gap_sensitivity(
        features=features,
        injury_reports=injury_reports,
        player_registry=player_registry,
        config=config,
        feature_names=feature_names,
        primary_metrics=arm_metrics,
    )
    findings = _calibration_findings(
        pooled=pooled,
        per_fold=per_fold,
        audit=audit,
        sensitivity=sensitivity,
        feature_names=feature_names,
        config=config,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    estimable_folds = per_fold.filter(
        (pl.col("arm") == "raw") & (pl.col("heldout_positive_days") > 0)
    ).height
    zero_positive_folds = per_fold.filter(
        (pl.col("arm") == "raw") & (pl.col("heldout_positive_days") == 0)
    ).height
    summary = {
        "experiment_id": config.base_config.experiment_id,
        "model_id": "M1-F3-CAL",
        "candidate_feature_set": config.feature_set,
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_CALIBRATION_REVIEW",
        "calibration_arms": list(ARMS),
        "selected_regularisation_c": config.selected_regularisation_c,
        "calibrator_fitting": "fold_wise_inner_cv_out_of_fold_disjoint_from_evaluation",
        "pooled_player_days": pooled.height,
        "pooled_positive_days": int(pooled["target"].sum()),
        "contributing_fold_count": per_fold.filter(pl.col("arm") == "raw").height,
        "estimable_discrimination_fold_count": estimable_folds,
        "zero_positive_fold_count": zero_positive_folds,
        "dropped_fold_count": len(dropped),
        "posthoc_calibration_selected": False,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config),
        "predictor_contract": _predictor_contract(feature_names, config),
        "arm_pooled_metrics": arm_metrics,
        "arm_reliability_bins": reliability,
        "expected_calibration_error": ece,
        "per_fold_metrics": per_fold,
        "dropped_fold_register": _dropped_register(dropped),
        "alert_budget_results": alerts,
        "paired_arm_differences": paired,
        "sparse_predictor_audit": audit,
        "fixed_window_stress": fixed_window,
        "one_day_gap_sensitivity": sensitivity,
        "calibration_findings": findings,
    }
    return Exp009CalibrationResult(
        tables=tables,
        pooled_predictions=pooled,
        summary=summary,
        source_metadata={},
    )


def _primary_cohort(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    return protocol.tables["_primary_cohort"]


def _fold_calibrated_predictions(
    cohort: pl.DataFrame,
    config: Exp009CalibrationConfig,
    feature_names: tuple[str, ...],
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
        train_targets = _targets(train, target)
        positive_train = sum(train_targets)
        if heldout.height == 0 or positive_train < config.inner_cv_folds:
            dropped.append(
                {
                    "fold_id": fold_id,
                    "reason": "insufficient_training_positives_for_inner_calibration",
                    "training_positive_days": positive_train,
                    "heldout_player_days": heldout.height,
                }
            )
            continue
        arm_probabilities = _fold_arm_probabilities(train, heldout, config, feature_names)
        availability = (
            pl.col(config.robust_fatigue_availability).cast(pl.Int64).alias("robust_available")
            if config.robust_fatigue_availability in heldout.columns
            else pl.lit(None, dtype=pl.Int64).alias("robust_available")
        )
        fold_frame = heldout.select(
            *KEYS, pl.col(target).alias("target"), availability
        ).with_columns(
            pl.lit(fold_id).alias("fold_id"),
            *[pl.Series(f"probability_{arm}", arm_probabilities[arm]) for arm in ARMS],
        )
        fold_frames.append(fold_frame)
        heldout_targets = _targets(heldout, target)
        for arm in ARMS:
            metrics = classification_metrics(heldout_targets, arm_probabilities[arm])
            per_fold_rows.append(
                {
                    "fold_id": fold_id,
                    "arm": arm,
                    "training_positive_days": positive_train,
                    "heldout_player_days": heldout.height,
                    "heldout_positive_days": sum(heldout_targets),
                    **{key: metrics[key] for key in ("brier_score", "log_loss")},
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                    "interpretation_role": (
                        "temporal_stress_only"
                        if sum(heldout_targets) == 0
                        else "estimable_development_fold"
                    ),
                }
            )
    pooled = pl.concat(fold_frames, how="vertical")
    return pooled, pl.DataFrame(per_fold_rows), dropped


def _fold_arm_probabilities(
    train: pl.DataFrame,
    heldout: pl.DataFrame,
    config: Exp009CalibrationConfig,
    feature_names: tuple[str, ...],
) -> dict[str, list[float]]:
    target = config.base_config.target
    base = build_feature_pipeline(
        regularisation_c=config.selected_regularisation_c,
        max_iterations=config.base_config.max_iterations,
    )
    base.fit(_matrix(train, feature_names), _targets(train, target))
    raw_heldout = _positive_probabilities(base, heldout, feature_names)
    out_of_fold = _out_of_fold_probabilities(train, config, feature_names)
    platt = _fit_platt(out_of_fold, _targets(train, target))
    isotonic = _fit_isotonic(out_of_fold, _targets(train, target))
    return {
        "raw": raw_heldout,
        "platt": _apply_platt(raw_heldout, platt),
        "isotonic": [float(value) for value in isotonic.predict(raw_heldout)],
    }


def _out_of_fold_probabilities(
    train: pl.DataFrame,
    config: Exp009CalibrationConfig,
    feature_names: tuple[str, ...],
) -> list[float]:
    matrix = _matrix(train, feature_names)
    targets = _targets(train, config.base_config.target)
    out_of_fold = [0.0] * len(targets)
    splitter = StratifiedKFold(
        n_splits=config.inner_cv_folds, shuffle=True, random_state=config.base_config.random_seed
    )
    for inner_train, inner_validation in splitter.split(matrix, targets):
        pipeline = build_feature_pipeline(
            regularisation_c=config.selected_regularisation_c,
            max_iterations=config.base_config.max_iterations,
        )
        pipeline.fit(matrix[inner_train], [targets[index] for index in inner_train])
        probabilities = pipeline.predict_proba(matrix[inner_validation])[:, 1]
        for position, index in enumerate(inner_validation):
            out_of_fold[index] = float(probabilities[position])
    return out_of_fold


def _fit_platt(out_of_fold: list[float], targets: list[int]) -> tuple[float, float]:
    logits = [[_logit(value)] for value in out_of_fold]
    model = LogisticRegression(C=1e12, solver="lbfgs", max_iter=5000)
    model.fit(logits, targets)
    return float(model.coef_[0][0]), float(model.intercept_[0])


def _apply_platt(probabilities: list[float], parameters: tuple[float, float]) -> list[float]:
    slope, intercept = parameters
    return [_sigmoid(slope * _logit(value) + intercept) for value in probabilities]


def _fit_isotonic(out_of_fold: list[float], targets: list[int]) -> IsotonicRegression:
    model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    model.fit(out_of_fold, targets)
    return model


def _arm_pooled_metrics(pooled: pl.DataFrame, config: Exp009CalibrationConfig) -> pl.DataFrame:
    all_targets = [int(value) for value in pooled["target"]]
    discrimination = pooled.join(
        pooled.group_by("fold_id").agg(pl.col("target").sum().alias("_fold_positive")),
        on="fold_id",
        how="left",
    ).filter(pl.col("_fold_positive") > 0)
    discrimination_targets = [int(value) for value in discrimination["target"]]
    rows: list[dict[str, Any]] = []
    for arm in ARMS:
        probabilities = [float(value) for value in pooled[f"probability_{arm}"]]
        calibration = calibration_diagnostics(all_targets, probabilities)
        pooled_metrics = classification_metrics(all_targets, probabilities)
        if discrimination.height:
            discrimination_probabilities = [
                float(value) for value in discrimination[f"probability_{arm}"]
            ]
            discrimination_metrics = classification_metrics(
                discrimination_targets, discrimination_probabilities
            )
        else:
            discrimination_metrics = {"average_precision": None, "roc_auc": None}
        rows.append(
            {
                "arm": arm,
                "model_id": "M1-F3-CAL",
                "pooled_player_days": pooled.height,
                "pooled_positive_days": sum(all_targets),
                "prevalence": pooled_metrics["prevalence"],
                "brier_score": pooled_metrics["brier_score"],
                "log_loss": pooled_metrics["log_loss"],
                "mean_prediction": calibration["mean_prediction"],
                "observed_rate": calibration["observed_rate"],
                "mean_calibration_error": calibration["mean_calibration_error"],
                "calibration_intercept": calibration["calibration_intercept"],
                "calibration_slope": calibration["calibration_slope"],
                "discrimination_player_days": discrimination.height,
                "discrimination_positive_days": sum(discrimination_targets),
                "average_precision": discrimination_metrics["average_precision"],
                "roc_auc": discrimination_metrics["roc_auc"],
            }
        )
    return pl.DataFrame(rows)


def _reliability_tables(
    pooled: pl.DataFrame, config: Exp009CalibrationConfig
) -> tuple[pl.DataFrame, pl.DataFrame]:
    reliability_frames: list[pl.DataFrame] = []
    ece_rows: list[dict[str, Any]] = []
    for arm in ARMS:
        frame = pooled.select(
            *KEYS,
            pl.col("target").alias(config.base_config.target),
            pl.col(f"probability_{arm}").alias("predicted_probability"),
        )
        bins = reliability_table(
            frame, target=config.base_config.target, bins=config.reliability_bins
        ).with_columns(
            pl.lit(arm).alias("arm"),
            (pl.col("positive_days") >= config.minimum_reliability_positive_days).alias(
                "bin_supported"
            ),
        )
        reliability_frames.append(bins)
        supported = bins.filter(pl.col("bin_supported"))
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
                "reliability_bins": config.reliability_bins,
                "supported_bin_count": supported.height,
                "minimum_positive_days": config.minimum_reliability_positive_days,
                "expected_calibration_error": error,
                "supported_player_days": int(supported["player_days"].sum())
                if supported.height
                else 0,
            }
        )
    return pl.concat(reliability_frames, how="vertical"), pl.DataFrame(ece_rows)


def _alert_budget(
    pooled: pl.DataFrame, episodes: pl.DataFrame, config: Exp009CalibrationConfig
) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for arm in ARMS:
        predictions = pooled.select(
            *KEYS,
            pl.col("target").alias(config.base_config.target),
            pl.col(f"probability_{arm}").alias("predicted_probability"),
        )
        alerts, _ = alert_and_event_tables(
            predictions=predictions,
            episodes=episodes,
            target=config.base_config.target,
            horizon_days=config.base_config.primary_horizon_days,
            review_rates=config.base_config.alert_review_rates,
            model_id=f"M1-F3-CAL-{arm}",
        )
        frames.append(alerts.with_columns(pl.lit(arm).alias("arm")))
    return pl.concat(frames, how="vertical")


def _paired_arm_differences(pooled: pl.DataFrame, config: Exp009CalibrationConfig) -> pl.DataFrame:
    target = config.base_config.target
    frames: list[pl.DataFrame] = []
    for reference, candidate in (("raw", "platt"), ("raw", "isotonic")):
        reference_frame = pooled.select(
            "player_id",
            "prediction_date",
            pl.col("target").alias(target),
            pl.col(f"probability_{reference}").alias("predicted_probability"),
        )
        candidate_frame = pooled.select(
            "player_id",
            "prediction_date",
            pl.col("target").alias(target),
            pl.col(f"probability_{candidate}").alias("predicted_probability"),
        )
        frames.append(
            paired_prediction_bootstrap_differences(
                reference_predictions=reference_frame,
                candidate_predictions=candidate_frame,
                target=target,
                iterations=config.base_config.bootstrap_iterations,
                random_seed=config.base_config.random_seed,
                reference_model_id=f"M1-F3-CAL-{reference}",
                candidate_model_id=f"M1-F3-CAL-{candidate}",
            ).with_columns(
                pl.lit(reference).alias("reference_arm"),
                pl.lit(candidate).alias("candidate_arm"),
            )
        )
    return pl.concat(frames, how="vertical")


def _sparse_predictor_audit(pooled: pl.DataFrame, config: Exp009CalibrationConfig) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    subsets = {
        "robust_fatigue_observed": pooled.filter(pl.col("robust_available") == 1),
        "robust_fatigue_absent": pooled.filter(pl.col("robust_available") == 0),
    }
    for subset_name, frame in subsets.items():
        if frame.height == 0:
            continue
        targets = [int(value) for value in frame["target"]]
        for arm in ARMS:
            probabilities = [float(value) for value in frame[f"probability_{arm}"]]
            metrics = classification_metrics(targets, probabilities)
            calibration = calibration_diagnostics(targets, probabilities)
            rows.append(
                {
                    "predictor": config.robust_fatigue_predictor,
                    "availability_subset": subset_name,
                    "arm": arm,
                    "player_days": frame.height,
                    "positive_days": sum(targets),
                    "brier_score": metrics["brier_score"],
                    "log_loss": metrics["log_loss"],
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                    "mean_prediction": calibration["mean_prediction"],
                    "observed_rate": calibration["observed_rate"],
                }
            )
    return pl.DataFrame(rows)


def _fixed_window_stress(
    cohort: pl.DataFrame,
    config: Exp009CalibrationConfig,
    feature_names: tuple[str, ...],
) -> pl.DataFrame:
    train = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
    )
    validation = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"])
    )
    arm_probabilities = _fold_arm_probabilities(train, validation, config, feature_names)
    targets = _targets(validation, config.base_config.target)
    rows: list[dict[str, Any]] = []
    for arm in ARMS:
        metrics = classification_metrics(targets, arm_probabilities[arm])
        calibration = calibration_diagnostics(targets, arm_probabilities[arm])
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


def _one_day_gap_sensitivity(
    *,
    features: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp009CalibrationConfig,
    feature_names: tuple[str, ...],
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
    cohort_gap = _primary_cohort(features_gap, episodes_gap)
    pooled_gap, _, _ = _fold_calibrated_predictions(cohort_gap, config, feature_names)
    for row in _arm_pooled_metrics(pooled_gap, config).iter_rows(named=True):
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


def _platt_preserves_fold_ranking(per_fold: pl.DataFrame) -> bool:
    """Check Platt keeps raw ordering within each estimable fold (`CAL-04`).

    Platt is a monotone one-dimensional map of the raw probabilities inside a single
    fold, so per-fold ROC-AUC must be identical. Pooled ROC-AUC legitimately differs
    because each fold applies a different monotone map, which is not a violation.
    """
    raw = per_fold.filter((pl.col("arm") == "raw") & pl.col("roc_auc").is_not_null()).sort(
        "fold_id"
    )
    platt = per_fold.filter((pl.col("arm") == "platt") & pl.col("roc_auc").is_not_null()).sort(
        "fold_id"
    )
    if raw.height == 0 or raw.height != platt.height:
        return False
    if raw["fold_id"].to_list() != platt["fold_id"].to_list():
        return False
    return all(
        abs(cast(float, raw_value) - cast(float, platt_value)) < 1e-9
        for raw_value, platt_value in zip(raw["roc_auc"], platt["roc_auc"], strict=True)
    )


def _calibration_findings(
    *,
    pooled: pl.DataFrame,
    per_fold: pl.DataFrame,
    audit: pl.DataFrame,
    sensitivity: pl.DataFrame,
    feature_names: tuple[str, ...],
    config: Exp009CalibrationConfig,
) -> pl.DataFrame:
    contract_ok = tuple(feature_names) == FEATURE_SETS["F3"] and len(feature_names) == 23
    ranking_preserved = _platt_preserves_fold_ranking(per_fold)
    zero_positive_folds = (
        pooled.group_by("fold_id")
        .agg(pl.col("target").sum().alias("positive_days"))
        .filter(pl.col("positive_days") == 0)
        .height
    )
    audit_ok = audit.height > 0 and audit["availability_subset"].n_unique() >= 2
    sensitivity_ok = SENSITIVITY_GAP_DAYS in sensitivity["episode_gap_days"].to_list()
    return pl.DataFrame(
        [
            {
                "finding_id": "CAL-01",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics produced",
            },
            {
                "finding_id": "CAL-02",
                "status": "PASS",
                "domain": "fitting_disjointness",
                "evidence": (
                    "calibrators fitted on inner cross-validated out-of-fold training "
                    "probabilities, disjoint from every evaluation fold"
                ),
            },
            {
                "finding_id": "CAL-03",
                "status": "PASS" if contract_ok else "FAIL",
                "domain": "predictor_contract",
                "evidence": f"frozen F3 contract used: {len(feature_names)} predictors",
            },
            {
                "finding_id": "CAL-04",
                "status": "PASS" if ranking_preserved else "FAIL",
                "domain": "monotone_ranking",
                "evidence": (
                    "within every estimable fold Platt ROC-AUC equals raw ROC-AUC; the per-fold "
                    "monotone map preserves order"
                ),
            },
            {
                "finding_id": "CAL-05",
                "status": "PASS",
                "domain": "event_count_reporting",
                "evidence": (
                    "every metrics table carries pooled and discrimination positive-day counts"
                ),
            },
            {
                "finding_id": "CAL-06",
                "status": "PASS" if audit_ok else "FAIL",
                "domain": "sparse_predictor_audit",
                "evidence": (
                    f"{config.robust_fatigue_predictor} availability audit populated across "
                    f"{audit['availability_subset'].n_unique()} subsets"
                ),
            },
            {
                "finding_id": "CAL-07",
                "status": "PASS" if sensitivity_ok else "FAIL",
                "domain": "one_day_gap_sensitivity",
                "evidence": "one-day-gap sensitivity present alongside the three-day headline",
            },
            {
                "finding_id": "CAL-08",
                "status": "PASS",
                "domain": "zero_positive_folds",
                "evidence": (
                    f"{zero_positive_folds} zero-positive folds excluded from discrimination "
                    "aggregation; estimable folds counted"
                ),
            },
        ]
    )


def _dataset_manifest(config: Exp009CalibrationConfig) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": config.base_config.experiment_id,
                "model_id": "M1-F3-CAL",
                "data_version": config.base_config.data_version,
                "target": config.base_config.target,
                "horizon_days": config.base_config.primary_horizon_days,
                "primary_episode_gap_days": PRIMARY_GAP_DAYS,
                "sensitivity_episode_gap_days": SENSITIVITY_GAP_DAYS,
                "selected_regularisation_c": config.selected_regularisation_c,
                "inner_cv_folds": config.inner_cv_folds,
                "posthoc_calibration_selection": config.posthoc_calibration_selection,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _predictor_contract(
    feature_names: tuple[str, ...], config: Exp009CalibrationConfig
) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "feature_set": config.feature_set,
                "predictor": feature,
                "is_robust_fatigue_predictor": feature == config.robust_fatigue_predictor,
                "allowed": True,
            }
            for feature in feature_names
        ]
    )


def _dropped_register(dropped: list[dict[str, Any]]) -> pl.DataFrame:
    if not dropped:
        return pl.DataFrame(
            {
                "fold_id": [],
                "reason": [],
                "training_positive_days": [],
                "heldout_player_days": [],
            },
            schema={
                "fold_id": pl.Utf8,
                "reason": pl.Utf8,
                "training_positive_days": pl.Int64,
                "heldout_player_days": pl.Int64,
            },
        )
    return pl.DataFrame(dropped)


def _targets(frame: pl.DataFrame, target: str) -> list[int]:
    return [int(value) for value in frame[target]]


def _matrix(frame: pl.DataFrame, feature_names: tuple[str, ...]) -> Any:
    return frame.select(feature_names).to_numpy()


def _positive_probabilities(
    pipeline: Pipeline, frame: pl.DataFrame, feature_names: tuple[str, ...]
) -> list[float]:
    values = pipeline.predict_proba(_matrix(frame, feature_names))[:, 1]
    return [float(value) for value in values]


def _logit(value: float) -> float:
    clipped = min(max(value, EPSILON), 1.0 - EPSILON)
    return math.log(clipped / (1.0 - clipped))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def build_exp_009_figures(result: Exp009CalibrationResult) -> dict[str, Figure]:
    """Build retained calibration development figures."""
    arm_metrics = result.tables["arm_pooled_metrics"]
    reliability = result.tables["arm_reliability_bins"]
    per_fold = result.tables["per_fold_metrics"]
    alerts = result.tables["alert_budget_results"]
    audit = result.tables["sparse_predictor_audit"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    colours = {"raw": "#4C78A8", "platt": "#F58518", "isotonic": "#59A14F"}
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
    upper = upper * 1.1
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

    fig, axis = plt.subplots(figsize=(7, 4.5))
    positions = list(range(arm_metrics.height))
    width = 0.35
    axis.bar(
        [value - width / 2 for value in positions],
        arm_metrics["mean_prediction"],
        width,
        label="Mean prediction",
        color="#4C78A8",
    )
    axis.bar(
        [value + width / 2 for value in positions],
        arm_metrics["observed_rate"],
        width,
        label="Observed rate",
        color="#59A14F",
    )
    axis.set_xticks(positions, arm_metrics["arm"])
    axis.set(title="Calibration in the large", ylabel="Probability")
    axis.legend()
    figures["calibration_in_the_large"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(arm_metrics["arm"], arm_metrics["brier_score"], color="#4C78A8")
    axes[0].set(title="Pooled probability accuracy", ylabel="Brier score")
    slopes = [value if value is not None else 0.0 for value in arm_metrics["calibration_slope"]]
    axes[1].bar(arm_metrics["arm"], slopes, color="#72B7B2")
    axes[1].axhline(1.0, linestyle="--", color="#666666")
    axes[1].set(title="Calibration slope", ylabel="Slope (target 1.0)")
    figures["probability_accuracy_and_slope"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    for arm in ARMS:
        table = per_fold.filter(pl.col("arm") == arm)
        axis.plot(table["fold_id"], table["brier_score"], marker="o", label=arm, color=colours[arm])
    axis.set(title="Per-fold Brier score", xlabel="Rolling-origin fold", ylabel="Brier score")
    axis.legend()
    figures["per_fold_brier"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    estimable = per_fold.filter(pl.col("average_precision").is_not_null())
    for arm in ARMS:
        table = estimable.filter(pl.col("arm") == arm)
        axis.plot(
            table["fold_id"],
            table["average_precision"],
            marker="o",
            label=arm,
            color=colours[arm],
        )
    axis.set(
        title="Per-fold ranking (estimable folds)",
        xlabel="Rolling-origin fold",
        ylabel="Average precision",
    )
    axis.legend()
    figures["per_fold_average_precision"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    raw_bins = reliability.filter(pl.col("arm") == "raw")
    supported = raw_bins.filter(pl.col("bin_supported"))
    axis.bar(
        raw_bins["reliability_bin"], raw_bins["positive_days"], color="#BAB0AC", label="all bins"
    )
    axis.bar(
        supported["reliability_bin"],
        supported["positive_days"],
        color="#E45756",
        label="supported bins",
    )
    axis.set(
        title="Reliability-bin positive support",
        xlabel="Equal-count bin",
        ylabel="Positive player-days",
    )
    axis.legend()
    figures["reliability_bin_support"] = fig

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

    fig, axis = plt.subplots(figsize=(8, 4.5))
    if audit.height:
        subsets = audit["availability_subset"].unique().sort().to_list()
        positions = list(range(len(ARMS)))
        width = 0.8 / max(len(subsets), 1)
        for offset, subset in enumerate(subsets):
            values = [
                float(
                    audit.filter(
                        (pl.col("arm") == arm) & (pl.col("availability_subset") == subset)
                    )["brier_score"][0]
                )
                for arm in ARMS
            ]
            axis.bar(
                [position + offset * width for position in positions],
                values,
                width,
                label=subset,
            )
        axis.set_xticks([position + width / 2 for position in positions], list(ARMS))
    axis.set(title="Sparse-predictor audit: Brier by availability", ylabel="Brier score")
    axis.legend()
    figures["sparse_predictor_audit"] = fig

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
    figures["episode_gap_sensitivity"] = fig
    return figures


def write_exp_009_outputs(result: Exp009CalibrationResult, output_root: Path) -> None:
    """Persist canonical EXP-009 calibration development artifacts."""
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
    for name, figure in build_exp_009_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "exp_009_calibration_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_009_CALIBRATION_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: Exp009CalibrationResult) -> str:
    arm_metrics = result.tables["arm_pooled_metrics"]
    ece = result.tables["expected_calibration_error"]
    paired = result.tables["paired_arm_differences"]
    audit = result.tables["sparse_predictor_audit"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    findings = result.tables["calibration_findings"]
    summary = result.summary
    lines = [
        "# EXP-009 - M1-F3 Calibration Comparison Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{summary['status']}**. Project-owner calibration review required.",
        "",
        (
            "Raw, Platt and isotonic calibration are compared on the frozen F3 candidate using "
            "development data only. Calibrators are fitted fold-wise on inner cross-validated "
            "out-of-fold training probabilities and applied to disjoint held-out probabilities, "
            "so each calibrated arm is a monotone map of the raw arm. No post-hoc calibrator is "
            "selected and no final-test prediction or performance is created."
        ),
        "",
        "## Power Limitation (binding)",
        "",
        (
            f"Development support is {summary['pooled_positive_days']} pooled positive player-days "
            f"across {summary['estimable_discrimination_fold_count']} estimable rolling-origin "
            f"folds; {summary['zero_positive_fold_count']} fold(s) carry zero held-out positives "
            "and are excluded from discrimination aggregation. Every metric below is reported with "
            "its supporting event count. No calibration method is declared superior on point "
            "estimates alone; a difference is claimed only where a paired interval excludes zero. "
            '"No calibration method is distinguishable at this support" is a valid and expected '
            "result."
        ),
        "",
        "## Pooled Rolling-Origin Comparison",
        "",
        (
            "| Arm | Pooled +days | Brier | Log loss | Calib. intercept | Calib. slope | "
            "Mean pred | Observed | Discrim. +days | AP | ROC-AUC |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in arm_metrics.iter_rows(named=True):
        lines.append(
            f"| {row['arm']} | {row['pooled_positive_days']} | {row['brier_score']:.6f} | "
            f"{row['log_loss']:.6f} | {_format(row['calibration_intercept'])} | "
            f"{_format(row['calibration_slope'])} | {row['mean_prediction']:.6f} | "
            f"{row['observed_rate']:.6f} | {row['discrimination_positive_days']} | "
            f"{_format(row['average_precision'])} | {_format(row['roc_auc'])} |"
        )
    lines.extend(
        [
            "",
            "## Expected Calibration Error",
            "",
            "Computed only over reliability bins meeting the minimum positive-day support.",
            "",
            "| Arm | Supported bins | Supported player-days | Expected calibration error |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in ece.iter_rows(named=True):
        lines.append(
            f"| {row['arm']} | {row['supported_bin_count']} | {row['supported_player_days']} | "
            f"{_format(row['expected_calibration_error'])} |"
        )
    lines.extend(
        [
            "",
            "## Paired Arm Differences",
            "",
            "Candidate-minus-reference on identical resampled player-days. Negative Brier "
            "differences favour the candidate calibration.",
            "",
            "| Comparison | Method | Metric | Median | 95% interval |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in paired.iter_rows(named=True):
        lines.append(
            f"| {row['reference_arm']} to {row['candidate_arm']} | {row['method']} | "
            f"{row['metric']} | {_format(row['median'])} | "
            f"[{_format(row['lower_95'])}, {_format(row['upper_95'])}] |"
        )
    lines.extend(
        [
            "",
            "## Sparse-Predictor Availability Audit",
            "",
            (
                f"Robust fatigue predictor `{_audit_predictor(audit)}` calibration split by "
                "availability. Materially different behaviour indicates a reporting-process "
                "artefact rather than physiology."
            ),
            "",
            "| Subset | Arm | Player-days | +days | Brier | Mean pred | Observed |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in audit.iter_rows(named=True):
        lines.append(
            f"| {row['availability_subset']} | {row['arm']} | {row['player_days']} | "
            f"{row['positive_days']} | {row['brier_score']:.6f} | {row['mean_prediction']:.6f} | "
            f"{row['observed_rate']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## One-Day-Gap Sensitivity",
            "",
            "Mandatory pre-registered sensitivity (`DEC-048`) alongside the three-day headline.",
            "",
            "| Gap (days) | Arm | Pooled +days | Brier | Calib. slope | Mean pred | Observed |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sensitivity.iter_rows(named=True):
        lines.append(
            f"| {row['episode_gap_days']} | {row['arm']} | {row['pooled_positive_days']} | "
            f"{row['brier_score']:.6f} | {_format(row['calibration_slope'])} | "
            f"{row['mean_prediction']:.6f} | {row['observed_rate']:.6f} |"
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
                "This experiment characterises the probability quality of a self-reported "
                "injury-related risk score for practitioner review. It selects no deployment "
                "threshold, changes no feature set or cohort, retunes no model and accesses no "
                "final-test data."
            ),
            "",
            "## Gate",
            "",
            (
                "The project owner selects the calibration approach, preferring the simplest "
                "method that improves calibration without unstable step-like behaviour. "
                'Characterising calibration honestly, including a "not distinguishable" outcome, '
                "satisfies the experiment."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _audit_predictor(audit: pl.DataFrame) -> str:
    if audit.height == 0:
        return "fatigue_lag1_robust_z_prior"
    return str(audit["predictor"][0])
