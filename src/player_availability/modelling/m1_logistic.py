"""EXP-003 M1-F1 development-only regularised logistic regression."""

from __future__ import annotations

import hashlib
import json
import math
import warnings
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import joblib  # type: ignore[import-untyped]
import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure
from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    PARTITIONS,
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
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
from player_availability.modelling.uncertainty import prediction_bootstrap_intervals


@dataclass(frozen=True, slots=True)
class M1F1Config:
    """Frozen EXP-003 M1-F1 configuration."""

    experiment_id: str
    model_id: str
    data_version: str
    target: str
    primary_horizon_days: int
    burn_in_days: int
    feature_set: str
    regularisation_c_grid: tuple[float, ...]
    solver: str
    penalty: str
    max_iterations: int
    class_weight: str | None
    alert_review_rates: tuple[float, ...]
    bootstrap_iterations: int
    random_seed: int
    reliability_bins: int
    m0_global_brier: float
    m0_global_log_loss: float
    m0_global_average_precision: float
    m0_global_roc_auc: float
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class M1F1Result:
    """M1-F1 tables, validation predictions, fitted candidate and metadata."""

    tables: dict[str, pl.DataFrame]
    predictions: pl.DataFrame
    model: Pipeline
    parameters: dict[str, Any]
    summary: dict[str, Any]


def load_m1_f1_config(path: Path) -> M1F1Config:
    """Load and validate the versioned F1 configuration."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("M1-F1 configuration must be a mapping")
    config = M1F1Config(
        experiment_id=str(raw["experiment_id"]),
        model_id=str(raw["model_id"]),
        data_version=str(raw["data_version"]),
        target=str(raw["target"]),
        primary_horizon_days=int(raw["primary_horizon_days"]),
        burn_in_days=int(raw["burn_in_days"]),
        feature_set=str(raw["feature_set"]),
        regularisation_c_grid=tuple(float(value) for value in raw["regularisation_c_grid"]),
        solver=str(raw["solver"]),
        penalty=str(raw["penalty"]),
        max_iterations=int(raw["max_iterations"]),
        class_weight=(None if raw["class_weight"] is None else str(raw["class_weight"])),
        alert_review_rates=tuple(float(value) for value in raw["alert_review_rates"]),
        bootstrap_iterations=int(raw["bootstrap_iterations"]),
        random_seed=int(raw["random_seed"]),
        reliability_bins=int(raw["reliability_bins"]),
        m0_global_brier=float(raw["m0_global_brier"]),
        m0_global_log_loss=float(raw["m0_global_log_loss"]),
        m0_global_average_precision=float(raw["m0_global_average_precision"]),
        m0_global_roc_auc=float(raw["m0_global_roc_auc"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.feature_set != "F1":
        raise ValueError("This experiment may fit F1 only")
    if config.solver != "lbfgs" or config.penalty != "l2" or config.class_weight is not None:
        raise ValueError("M1-F1 solver, penalty and unweighted primary model are frozen")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("M1-F1 cannot select post-hoc calibration or access final test")
    if config.regularisation_c_grid != (0.001, 0.01, 0.1, 1.0, 10.0):
        raise ValueError("M1-F1 regularisation grid differs from DEC-041")
    if any(not 0.0 < rate < 1.0 for rate in config.alert_review_rates):
        raise ValueError("Review rates must be between zero and one")
    return config


def load_m1_f1_from_gcp(*, project_id: str, data_bucket: str, config: M1F1Config) -> M1F1Result:
    """Load compact canonical products and execute M1-F1."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_m1_f1(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    return M1F1Result(
        tables=result.tables,
        predictions=result.predictions,
        model=result.model,
        parameters={
            **result.parameters,
            "source_paths": paths,
            "source_sha256": {
                name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()
            },
        },
        summary=result.summary,
    )


def run_m1_f1(*, features: pl.DataFrame, episodes: pl.DataFrame, config: M1F1Config) -> M1F1Result:
    """Fit and evaluate F1 on development data without final-test predictions."""
    return run_m1_feature_set(
        features=features,
        episodes=episodes,
        config=config,
        feature_names=F1_FEATURES,
    )


def run_m1_feature_set(
    *,
    features: pl.DataFrame,
    episodes: pl.DataFrame,
    config: M1F1Config,
    feature_names: tuple[str, ...],
    prepared_cohort: pl.DataFrame | None = None,
) -> M1F1Result:
    """Fit one frozen cumulative M1 feature set on development data."""
    cohort = prepared_cohort
    if cohort is None:
        protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
        cohort = protocol.tables["_primary_cohort"]
    missing = sorted({config.target, *feature_names} - set(cohort.columns))
    if missing:
        raise ValueError(f"M1-{config.feature_set} cohort is missing frozen columns: {missing}")
    train = _partition(cohort, PARTITIONS[0])
    validation = _partition(cohort, PARTITIONS[1])
    test = _partition(cohort, PARTITIONS[2])

    candidate_rows: list[dict[str, Any]] = []
    candidate_models: dict[float, Pipeline] = {}
    for regularisation_c in config.regularisation_c_grid:
        pipeline, convergence_warnings = _fit_pipeline(
            train, config, regularisation_c, feature_names
        )
        probabilities = _predict_probabilities(pipeline, validation, feature_names)
        metrics = classification_metrics(_targets(validation, config.target), probabilities)
        candidate_rows.append(
            {
                "regularisation_c": regularisation_c,
                **metrics,
                "convergence_warning_count": convergence_warnings,
                "selected": False,
            }
        )
        candidate_models[regularisation_c] = pipeline
    selected_c = min(
        candidate_rows,
        key=lambda row: (
            cast(float, row["brier_score"]),
            -cast(float, row["average_precision"]),
            cast(float, row["regularisation_c"]),
        ),
    )["regularisation_c"]
    selected_c = float(selected_c)
    for row in candidate_rows:
        row["selected"] = row["regularisation_c"] == selected_c
    selected_model = candidate_models[selected_c]
    probabilities = _predict_probabilities(selected_model, validation, feature_names)
    predictions = _prediction_frame(validation, probabilities, config)
    selected_metrics = classification_metrics(_targets(validation, config.target), probabilities)
    calibration = calibration_diagnostics(_targets(validation, config.target), probabilities)
    calibration_table = pl.DataFrame([{"model_id": config.model_id, **calibration}])
    reliability = reliability_table(predictions, target=config.target, bins=config.reliability_bins)
    alerts, event_capture = alert_and_event_tables(
        predictions=predictions,
        episodes=episodes,
        target=config.target,
        horizon_days=config.primary_horizon_days,
        review_rates=config.alert_review_rates,
        model_id=config.model_id,
    )
    rolling = _rolling_origin_results(cohort, config, selected_c, feature_names)
    unseen_players, unseen_aggregate = _unseen_player_results(
        cohort, config, selected_c, feature_names
    )
    uncertainty = prediction_bootstrap_intervals(
        predictions=predictions,
        target=config.target,
        iterations=config.bootstrap_iterations,
        random_seed=config.random_seed,
        model_id=config.model_id,
    )
    coefficients, feature_context = _coefficient_tables(selected_model, feature_names)
    model_comparison = _model_comparison(config, selected_metrics)
    support = _support_table(train, validation, test, config)
    findings = _findings(
        config=config,
        candidate_rows=candidate_rows,
        predictions=predictions,
        selected_metrics=selected_metrics,
        calibration=calibration,
        alerts=alerts,
        event_capture=event_capture,
        rolling=rolling,
        feature_names=feature_names,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    reviews = findings.filter(pl.col("status") == "REVIEW").height
    parameters = {
        "selected_regularisation_c": selected_c,
        "selection_rule": "lowest validation Brier, then higher AP, then smaller C",
        "feature_set": config.feature_set,
        "features": list(feature_names),
        "preprocessing": "training-only median imputation with indicators and scaling",
        "posthoc_calibration_selected": False,
        "class_weight": None,
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config),
        "cohort_and_split_support": support,
        "feature_manifest": _feature_manifest(feature_names, config.feature_set),
        "hyperparameter_results": pl.DataFrame(candidate_rows),
        "selected_validation_metrics": pl.DataFrame(
            [{"model_id": config.model_id, **selected_metrics}]
        ),
        "model_comparison": model_comparison,
        "calibration_diagnostics": calibration_table,
        "reliability_bins": reliability,
        "coefficient_estimates": coefficients,
        "feature_preprocessing_context": feature_context,
        "alert_budget_results": alerts,
        "event_capture_results": event_capture,
        "rolling_origin_results": rolling,
        "unseen_player_results": unseen_players,
        "unseen_player_aggregate_metrics": unseen_aggregate,
        "bootstrap_intervals": uncertainty,
        "model_findings": findings,
    }
    represented_onsets = event_capture.select("onset_id").unique().height
    summary = {
        "experiment_id": config.experiment_id,
        "model_id": config.model_id,
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_PROMOTE_REVISE_REJECT",
        "data_version": config.data_version,
        "target": config.target,
        "feature_count": len(feature_names),
        "selected_regularisation_c": selected_c,
        "train_player_days": train.height,
        "validation_player_days": validation.height,
        "validation_positive_days": int(validation[config.target].sum()),
        "validation_represented_onsets": represented_onsets,
        "failure_count": failures,
        "review_count": reviews,
        "posthoc_calibration_selected": False,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    return M1F1Result(tables, predictions, selected_model, parameters, summary)


def write_m1_f1_outputs(result: M1F1Result, output_root: Path) -> None:
    """Persist canonical M1-F1 development artifacts."""
    directories = {
        name: output_root / name
        for name in ("figures", "tables", "predictions", "models", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    result.predictions.write_parquet(directories["predictions"] / "validation_predictions.parquet")
    joblib.dump(result.model, directories["models"] / "m1_f1_development_pipeline.joblib")
    for name, figure in build_m1_f1_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["metadata"] / "selected_model_parameters.json").write_text(
        json.dumps(result.parameters, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["metadata"] / "exp_003_f1_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_003_M1_F1_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _partition(frame: pl.DataFrame, specification: dict[str, Any]) -> pl.DataFrame:
    return frame.filter(
        pl.col("prediction_date").is_between(
            specification["start_date"], specification["end_date"], closed="both"
        )
    )


def _targets(frame: pl.DataFrame, target: str) -> list[int]:
    return [int(value) for value in frame[target]]


def _matrix(frame: pl.DataFrame, feature_names: tuple[str, ...]) -> Any:
    return frame.select(feature_names).to_numpy()


def _fit_pipeline(
    frame: pl.DataFrame,
    config: M1F1Config,
    regularisation_c: float,
    feature_names: tuple[str, ...],
) -> tuple[Pipeline, int]:
    pipeline = build_feature_pipeline(
        regularisation_c=regularisation_c,
        max_iterations=config.max_iterations,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        pipeline.fit(_matrix(frame, feature_names), _targets(frame, config.target))
    convergence_count = sum(issubclass(item.category, ConvergenceWarning) for item in caught)
    return pipeline, convergence_count


def _predict_probabilities(
    pipeline: Pipeline, frame: pl.DataFrame, feature_names: tuple[str, ...]
) -> list[float]:
    values = pipeline.predict_proba(_matrix(frame, feature_names))[:, 1]
    return [float(value) for value in values]


def _unsupported_metrics(targets: list[int]) -> dict[str, float | None]:
    positive_count = sum(targets)
    return {
        "player_days": float(len(targets)),
        "positive_days": float(positive_count),
        "prevalence": positive_count / len(targets) if targets else None,
        "brier_score": None,
        "log_loss": None,
        "average_precision": None,
        "roc_auc": None,
    }


def _prediction_frame(
    validation: pl.DataFrame, probabilities: list[float], config: M1F1Config
) -> pl.DataFrame:
    return validation.select("player_id", "team_id", "prediction_date", config.target).with_columns(
        pl.Series("predicted_probability", probabilities),
        pl.lit(config.model_id).alias("model_id"),
        pl.lit("validation").alias("partition"),
    )


def _rolling_origin_results(
    cohort: pl.DataFrame,
    config: M1F1Config,
    selected_c: float,
    feature_names: tuple[str, ...],
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for fold_id, train_start, train_end, validation_start, validation_end in ROLLING_FOLDS:
        train = cohort.filter(pl.col("prediction_date").is_between(train_start, train_end))
        validation = cohort.filter(
            pl.col("prediction_date").is_between(validation_start, validation_end)
        )
        train_targets = _targets(train, config.target)
        validation_targets = _targets(validation, config.target)
        if len(set(train_targets)) < 2:
            metrics = _unsupported_metrics(validation_targets)
            convergence_count = 0
            fit_status = "not_estimable_single_class_training"
        else:
            pipeline, convergence_count = _fit_pipeline(train, config, selected_c, feature_names)
            probabilities = _predict_probabilities(pipeline, validation, feature_names)
            metrics = classification_metrics(validation_targets, probabilities)
            fit_status = "fitted"
        rows.append(
            {
                "fold_id": fold_id,
                "train_start": train_start,
                "train_end": train_end,
                "validation_start": validation_start,
                "validation_end": validation_end,
                "training_positive_days": sum(train_targets),
                **metrics,
                "convergence_warning_count": convergence_count,
                "model_fit_status": fit_status,
                "interpretation_role": (
                    "not_estimable_training_support"
                    if fit_status != "fitted"
                    else "temporal_stress_only"
                    if metrics["positive_days"] == 0
                    else "estimable_development_fold"
                ),
            }
        )
    return pl.DataFrame(rows)


def _unseen_player_results(
    cohort: pl.DataFrame,
    config: M1F1Config,
    selected_c: float,
    feature_names: tuple[str, ...],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    development = cohort.filter(pl.col("prediction_date") <= date(2021, 6, 23))
    rows: list[dict[str, Any]] = []
    aggregate_targets: list[int] = []
    aggregate_probabilities: list[float] = []
    for player_id in development["player_id"].unique().sort():
        train = development.filter(pl.col("player_id") != player_id)
        heldout = development.filter(pl.col("player_id") == player_id)
        targets = _targets(heldout, config.target)
        train_targets = _targets(train, config.target)
        if len(set(train_targets)) < 2:
            metrics = _unsupported_metrics(targets)
            convergence_count = 0
            fit_status = "not_estimable_single_class_training"
        else:
            pipeline, convergence_count = _fit_pipeline(train, config, selected_c, feature_names)
            probabilities = _predict_probabilities(pipeline, heldout, feature_names)
            metrics = classification_metrics(targets, probabilities)
            aggregate_targets.extend(targets)
            aggregate_probabilities.extend(probabilities)
            fit_status = "fitted"
        rows.append(
            {
                "player_id": player_id,
                "team_id": heldout["team_id"][0],
                "training_positive_days": sum(train_targets),
                **metrics,
                "metric_support": (
                    "training_not_estimable"
                    if fit_status != "fitted"
                    else "estimable"
                    if metrics["positive_days"]
                    else "zero_positive_support"
                ),
                "model_fit_status": fit_status,
                "convergence_warning_count": convergence_count,
            }
        )
    aggregate = (
        classification_metrics(aggregate_targets, aggregate_probabilities)
        if aggregate_targets
        else _unsupported_metrics([])
    )
    summary = pl.DataFrame(
        [
            {
                "model_id": config.model_id,
                **aggregate,
                "heldout_player_count": len(rows),
                "estimable_player_count": sum(row["metric_support"] == "estimable" for row in rows),
                "zero_positive_player_count": sum(
                    row["metric_support"] == "zero_positive_support" for row in rows
                ),
                "training_not_estimable_player_count": sum(
                    row["metric_support"] == "training_not_estimable" for row in rows
                ),
            }
        ]
    )
    return pl.DataFrame(rows), summary


def _coefficient_tables(
    pipeline: Pipeline, feature_names: tuple[str, ...]
) -> tuple[pl.DataFrame, pl.DataFrame]:
    names = transformed_feature_names(pipeline, feature_names)
    classifier = pipeline.named_steps["classifier"]
    scaler = pipeline.named_steps["scaler"]
    coefficients = [float(value) for value in classifier.coef_[0]]
    coefficient_rows = [
        {
            "transformed_feature": "__intercept__",
            "standardised_coefficient": float(classifier.intercept_[0]),
            "odds_ratio_per_standard_deviation": math.exp(float(classifier.intercept_[0])),
            "coefficient_role": "intercept",
        }
    ]
    coefficient_rows.extend(
        {
            "transformed_feature": name,
            "standardised_coefficient": coefficient,
            "odds_ratio_per_standard_deviation": math.exp(coefficient),
            "coefficient_role": "predictor_or_missing_indicator",
        }
        for name, coefficient in zip(names, coefficients, strict=True)
    )
    context_rows = [
        {
            "transformed_feature": name,
            "training_mean_after_imputation": float(mean),
            "training_scale": float(scale),
        }
        for name, mean, scale in zip(names, scaler.mean_, scaler.scale_, strict=True)
    ]
    return pl.DataFrame(coefficient_rows), pl.DataFrame(context_rows)


def _model_comparison(
    config: M1F1Config, selected_metrics: dict[str, float | None]
) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "model_id": "M0_GLOBAL_PREVALENCE",
                "brier_score": config.m0_global_brier,
                "log_loss": config.m0_global_log_loss,
                "average_precision": config.m0_global_average_precision,
                "roc_auc": config.m0_global_roc_auc,
            },
            {
                "model_id": config.model_id,
                "brier_score": selected_metrics["brier_score"],
                "log_loss": selected_metrics["log_loss"],
                "average_precision": selected_metrics["average_precision"],
                "roc_auc": selected_metrics["roc_auc"],
            },
        ]
    )


def _support_table(
    train: pl.DataFrame, validation: pl.DataFrame, test: pl.DataFrame, config: M1F1Config
) -> pl.DataFrame:
    rows = []
    for partition, frame, evaluated in (
        ("train", train, True),
        ("validation", validation, True),
        ("test", test, False),
    ):
        rows.append(
            {
                "partition": partition,
                "player_days": frame.height,
                "positive_days": int(frame[config.target].sum()),
                "player_count": frame["player_id"].n_unique(),
                "performance_evaluated": evaluated,
                "predictions_persisted": partition == "validation",
            }
        )
    return pl.DataFrame(rows)


def _dataset_manifest(config: M1F1Config) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": config.experiment_id,
                "model_id": config.model_id,
                "data_version": config.data_version,
                "target": config.target,
                "horizon_days": config.primary_horizon_days,
                "burn_in_days": config.burn_in_days,
                "posthoc_calibration_selection": config.posthoc_calibration_selection,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _feature_manifest(feature_names: tuple[str, ...], feature_set: str) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "feature_set": feature_set,
                "predictor": feature,
                "same_day_wellness": False,
                "identity_feature": False,
                "allowed": True,
            }
            for feature in feature_names
        ]
    )


def _findings(
    *,
    config: M1F1Config,
    candidate_rows: list[dict[str, Any]],
    predictions: pl.DataFrame,
    selected_metrics: dict[str, float | None],
    calibration: dict[str, float | None],
    alerts: pl.DataFrame,
    event_capture: pl.DataFrame,
    rolling: pl.DataFrame,
    feature_names: tuple[str, ...],
) -> pl.DataFrame:
    captures = cast(int, alerts["captured_onsets"].max())
    zero_positive_folds = rolling.filter(pl.col("positive_days") == 0).height
    represented_onsets = event_capture.select("onset_id").unique().height
    return pl.DataFrame(
        [
            {
                "finding_id": f"{config.feature_set}-01",
                "status": "PASS",
                "domain": "predictor_contract",
                "evidence": (
                    f"exact frozen {config.feature_set} allow-list used: "
                    f"{len(feature_names)} predictors"
                ),
            },
            {
                "finding_id": f"{config.feature_set}-02",
                "status": "PASS"
                if sum(int(row["convergence_warning_count"]) for row in candidate_rows) == 0
                else "FAIL",
                "domain": "optimisation",
                "evidence": "finite grid fitted with convergence warnings counted",
            },
            {
                "finding_id": f"{config.feature_set}-03",
                "status": "PASS"
                if predictions["predicted_probability"].is_between(0.0, 1.0).all()
                else "FAIL",
                "domain": "prediction_validity",
                "evidence": "all validation probabilities are in [0, 1]",
            },
            {
                "finding_id": f"{config.feature_set}-04",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics",
            },
            {
                "finding_id": f"{config.feature_set}-05",
                "status": "REVIEW",
                "domain": "m0_comparison",
                "evidence": (
                    f"F1 Brier={cast(float, selected_metrics['brier_score']):.6f} vs "
                    f"M0={config.m0_global_brier:.6f}; F1 AP="
                    f"{cast(float, selected_metrics['average_precision']):.6f} vs "
                    f"M0={config.m0_global_average_precision:.6f}"
                ),
            },
            {
                "finding_id": f"{config.feature_set}-06",
                "status": "REVIEW",
                "domain": "operational_capture",
                "evidence": f"maximum captured onsets={captures}/{represented_onsets}",
            },
            {
                "finding_id": f"{config.feature_set}-07",
                "status": "REVIEW",
                "domain": "raw_calibration",
                "evidence": (
                    f"mean prediction={cast(float, calibration['mean_prediction']):.6f}; "
                    f"observed={cast(float, calibration['observed_rate']):.6f}; "
                    "post-hoc calibration not selected"
                ),
            },
            {
                "finding_id": f"{config.feature_set}-08",
                "status": "REVIEW",
                "domain": "temporal_support",
                "evidence": f"{zero_positive_folds} rolling folds have zero positive days",
            },
        ]
    )


def build_m1_f1_figures(result: M1F1Result) -> dict[str, Figure]:
    """Build retained F1 development figures."""
    candidates = result.tables["hyperparameter_results"].sort("regularisation_c")
    comparison = result.tables["model_comparison"]
    reliability = result.tables["reliability_bins"]
    coefficients = result.tables["coefficient_estimates"].filter(
        pl.col("coefficient_role") != "intercept"
    )
    alerts = result.tables["alert_budget_results"]
    rolling = result.tables["rolling_origin_results"]
    unseen = result.tables["unseen_player_results"]
    figures: dict[str, Figure] = {}

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(candidates["regularisation_c"], candidates["brier_score"], marker="o")
    axis.set_xscale("log")
    axis.set(title="F1 regularisation search", xlabel="C", ylabel="Validation Brier score")
    figures["regularisation_brier"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(candidates["regularisation_c"], candidates["average_precision"], marker="o")
    axis.axhline(
        float(
            comparison.filter(pl.col("model_id") == "M0_GLOBAL_PREVALENCE")["average_precision"][0]
        ),
        linestyle="--",
        color="#666666",
        label="M0 global prevalence",
    )
    axis.set_xscale("log")
    axis.set(title="F1 ranking across regularisation", xlabel="C", ylabel="Average precision")
    axis.legend()
    figures["regularisation_average_precision"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(comparison["model_id"], comparison["brier_score"], color=["#4C78A8", "#F58518"])
    axes[0].set(title="Probability accuracy", ylabel="Brier score")
    axes[1].bar(
        comparison["model_id"], comparison["average_precision"], color=["#4C78A8", "#F58518"]
    )
    axes[1].set(title="Rare-event ranking", ylabel="Average precision")
    for axis in axes:
        axis.tick_params(axis="x", rotation=12)
    figures["m0_f1_comparison"] = fig

    fig, axis = plt.subplots(figsize=(7, 5))
    axis.plot(
        reliability["mean_prediction"], reliability["observed_rate"], marker="o", color="#F58518"
    )
    upper = max(
        0.02,
        cast(float, reliability["mean_prediction"].max()) * 1.1,
        cast(float, reliability["observed_rate"].max()) * 1.1,
    )
    axis.plot([0, upper], [0, upper], linestyle="--", color="#666666")
    axis.set(
        title="F1 raw reliability",
        xlabel="Mean predicted probability",
        ylabel="Observed positive-day rate",
        xlim=(0, upper),
        ylim=(0, upper),
    )
    figures["raw_reliability"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True)
    negatives = result.predictions.filter(~pl.col("injury_next_7d"))["predicted_probability"]
    positives = result.predictions.filter(pl.col("injury_next_7d"))["predicted_probability"]
    upper = max(
        0.02,
        cast(float, result.predictions["predicted_probability"].max()) * 1.05,
    )
    axes[0].hist(
        negatives,
        bins=25,
        range=(0, upper),
        alpha=0.8,
        color="#4C78A8",
    )
    axes[1].hist(
        positives,
        bins=25,
        range=(0, upper),
        alpha=0.8,
        color="#E45756",
    )
    axes[0].set(title="Negative days", xlabel="Predicted probability", ylabel="Player-days")
    axes[1].set(title="Positive days", xlabel="Predicted probability", ylabel="Player-days")
    for axis in axes:
        axis.set_xlim(0, upper)
    fig.suptitle("Validation probability distribution by outcome")
    figures["validation_probability_by_outcome"] = fig

    fig, axis = plt.subplots(figsize=(9, 6))
    ordered = coefficients.sort("standardised_coefficient")
    colours = [
        "#4C78A8" if value < 0 else "#E45756" for value in ordered["standardised_coefficient"]
    ]
    axis.barh(ordered["transformed_feature"], ordered["standardised_coefficient"], color=colours)
    axis.axvline(0, color="#555555", linewidth=1)
    axis.set(title="F1 standardised coefficients", xlabel="Log-odds coefficient")
    figures["standardised_coefficients"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(
        alerts["alerts_per_100_player_days"],
        alerts["event_capture_rate"],
        marker="o",
        color="#2A9D8F",
    )
    for row in alerts.iter_rows(named=True):
        axis.annotate(
            f"{row['captured_onsets']}/{row['represented_onsets']}",
            (row["alerts_per_100_player_days"], row["event_capture_rate"]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
        )
    axis.set(
        title="F1 review capacity and onset capture",
        xlabel="Alerts per 100 player-days",
        ylabel="Represented-onset capture rate",
        ylim=(0, 1),
    )
    figures["alert_budget_event_capture"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    estimable = rolling.filter(pl.col("average_precision").is_not_null())
    axis.plot(estimable["fold_id"], estimable["average_precision"], marker="o", color="#F58518")
    axis.set(title="Rolling-origin F1 ranking", xlabel="Fold", ylabel="Average precision")
    figures["rolling_origin_average_precision"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    counts = unseen.group_by("metric_support").len().sort("metric_support")
    axis.bar(counts["metric_support"], counts["len"], color=["#59A14F", "#BAB0AC"])
    axis.set(title="Unseen-player outcome support", ylabel="Held-out players")
    axis.tick_params(axis="x", rotation=10)
    figures["unseen_player_support"] = fig
    return figures


def _render_report(result: M1F1Result) -> str:
    comparison = result.tables["model_comparison"]
    calibration = result.tables["calibration_diagnostics"].row(0, named=True)
    alerts = result.tables["alert_budget_results"]
    rolling = result.tables["rolling_origin_results"]
    unseen = result.tables["unseen_player_aggregate_metrics"].row(0, named=True)
    findings = result.tables["model_findings"]
    lines = [
        "# EXP-003 - M1-F1 Regularised Logistic Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{result.summary['status']}**. Owner `PROMOTE`, "
        "`REVISE` or `REJECT` review is required.",
        "",
        "No F2/F3 model, post-hoc calibrator or final-test prediction/performance was created.",
        "",
        "## Selected Configuration",
        "",
        f"- Feature set: F1 ({result.summary['feature_count']} predictors)",
        f"- Selected C: {result.summary['selected_regularisation_c']}",
        "- Pipeline: training-only median imputation with indicators, scaling and "
        "unweighted L2 logistic regression",
        "",
        "## Validation Comparison",
        "",
        "| Model | Brier | Log loss | Average precision | ROC-AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in comparison.iter_rows(named=True):
        lines.append(
            f"| {row['model_id']} | {row['brier_score']:.6f} | "
            f"{row['log_loss']:.6f} | {row['average_precision']:.6f} | "
            f"{row['roc_auc']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Raw Calibration Diagnostics",
            "",
            f"- Mean prediction: {calibration['mean_prediction']:.6f}",
            f"- Observed positive-day rate: {calibration['observed_rate']:.6f}",
            f"- Calibration intercept: {calibration['calibration_intercept']:.6f}",
            f"- Calibration slope: {calibration['calibration_slope']:.6f}",
            "- Post-hoc calibration selection: not performed",
            "",
            "## Alert-Budget Simulation",
            "",
            "| Review rate | Alerts | Captured onsets | Capture rate | "
            "False alerts/captured onset |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in alerts.iter_rows(named=True):
        false_alerts = (
            "NA"
            if row["false_alerts_per_captured_onset"] is None
            else f"{row['false_alerts_per_captured_onset']:.2f}"
        )
        lines.append(
            f"| {row['review_rate']:.3f} | {row['alert_count']} | "
            f"{row['captured_onsets']}/{row['represented_onsets']} | "
            f"{row['event_capture_rate']:.3f} | {false_alerts} |"
        )
    lines.extend(
        [
            "",
            "## Development Stress Evidence",
            "",
            f"Rolling folds: {rolling.height}; zero-positive stress folds: "
            f"{rolling.filter(pl.col('positive_days') == 0).height}.",
            f"Unseen-player aggregate AP: {unseen['average_precision']:.6f}; "
            f"estimable players: {unseen['estimable_player_count']}/"
            f"{unseen['heldout_player_count']}.",
            "",
            "## Findings",
            "",
            "| ID | Status | Domain | Evidence |",
            "|---|---|---|---|",
        ]
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
            "F1 estimates exploratory practitioner-review risk for recorded self-reported "
            "injury-related onsets. Coefficients are associations, not causal effects, "
            "medical thresholds or training recommendations.",
            "",
            "## Gate",
            "",
            "The project owner must decide `PROMOTE`, `REVISE` or `REJECT` before "
            "F2 implementation.",
            "",
        ]
    )
    return "\n".join(lines)
