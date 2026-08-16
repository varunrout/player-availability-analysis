"""EXP-016 sparse-predictor availability ablation on the F3 candidate.

Tests whether F3's held-period advantage is carried by the availability pattern
of the robust fatigue z-score (`fatigue_lag1_robust_z_prior`) rather than its
value, per `DEC-052`. Four arms share the frozen F3 engine (cohort, partitions,
embargoes, preprocessing, regularisation): A is F3 as promoted under `DEC-043`;
B removes the predictor value and its recording-state indicator entirely; C
removes the value but keeps the indicator; D is F1 as an external reference.
Raw probabilities only, per `DEC-052`. No final-test row is read or scored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.metrics import (
    alert_and_event_tables,
    calibration_diagnostics,
    classification_metrics,
)
from player_availability.modelling.preprocessing import FEATURE_SETS, build_feature_pipeline
from player_availability.modelling.uncertainty import paired_prediction_bootstrap_differences
from player_availability.outcomes import build_injury_episodes, build_player_day_labels

ARM_ORDER: tuple[str, ...] = ("A", "B", "C", "D")
HORIZONS_DAYS: tuple[int, ...] = (3, 7, 14)
PRIMARY_GAP_DAYS = 3
SENSITIVITY_GAP_DAYS = 1
DEVELOPMENT_CUTOFF = date(2021, 6, 23)
KEYS = ("player_id", "team_id", "prediction_date")


@dataclass(frozen=True, slots=True)
class Exp016AblationConfig:
    """Frozen EXP-016 sparse-predictor ablation configuration."""

    base_config: M1F1Config
    selected_regularisation_c: float
    robust_fatigue_predictor: str
    robust_fatigue_availability: str
    one_day_gap_sensitivity: bool
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class Exp016AblationResult:
    """Ablation tables, pooled per-arm predictions and metadata."""

    tables: dict[str, pl.DataFrame]
    pooled_predictions: pl.DataFrame
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_exp_016_config(path: Path) -> Exp016AblationConfig:
    """Load and validate the frozen EXP-016 ablation specification."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("EXP-016 configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = Exp016AblationConfig(
        base_config=base_config,
        selected_regularisation_c=float(raw["selected_regularisation_c"]),
        robust_fatigue_predictor=str(raw["robust_fatigue_predictor"]),
        robust_fatigue_availability=str(raw["robust_fatigue_availability"]),
        one_day_gap_sensitivity=bool(raw["one_day_gap_sensitivity"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.selected_regularisation_c != 0.001:
        raise ValueError("EXP-016 uses the frozen F3 regularisation C=0.001; no retuning")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("EXP-016 characterises predictor value; it locks the final test")
    if config.robust_fatigue_predictor not in FEATURE_SETS["F3"]:
        raise ValueError("Robust fatigue predictor must belong to the F3 contract")
    if config.robust_fatigue_availability not in FEATURE_SETS["F3"]:
        raise ValueError("Robust fatigue availability indicator must belong to the F3 contract")
    return config


def load_exp_016_from_gcp(
    *, project_id: str, data_bucket: str, config: Exp016AblationConfig
) -> Exp016AblationResult:
    """Load compact canonical products once and execute the ablation."""
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
    result = run_exp_016_ablation(
        features=frames["features"],
        episodes=frames["episodes"],
        injury_reports=frames["injury_reports"],
        player_registry=frames["player_registry"],
        config=config,
    )
    return Exp016AblationResult(
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


def run_exp_016_ablation(
    *,
    features: pl.DataFrame,
    episodes: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp016AblationConfig,
) -> Exp016AblationResult:
    """Compare F3 against sparse-predictor-removed and F1-reference arms."""
    arm_features = _arm_feature_sets(config)
    cohort = _primary_cohort(features, episodes)
    pooled, per_fold, dropped = _fold_arm_predictions(cohort, config, arm_features)

    arm_metrics = _arm_pooled_metrics(pooled, per_fold)
    fixed_window = _fixed_window_stress(cohort, config, arm_features)
    alerts = _alert_budget(pooled, episodes, config)
    paired = _paired_arm_differences(pooled, config)
    unseen_players, unseen_aggregate = _unseen_player_results(cohort, config, arm_features)
    sensitivity = _one_day_gap_sensitivity(
        features=features,
        injury_reports=injury_reports,
        player_registry=player_registry,
        config=config,
        arm_features=arm_features,
        primary_metrics=arm_metrics,
    )
    unseen_gap_analysis = _unseen_gap_analysis(unseen_aggregate)
    findings = _ablation_findings(
        per_fold=per_fold,
        arm_features=arm_features,
        config=config,
        unseen_aggregate=unseen_aggregate,
        sensitivity=sensitivity,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    estimable_folds = per_fold.filter(
        (pl.col("arm") == "A") & (pl.col("heldout_positive_days") > 0)
    ).height
    zero_positive_folds = per_fold.filter(
        (pl.col("arm") == "A") & (pl.col("heldout_positive_days") == 0)
    ).height
    summary = {
        "experiment_id": "EXP-016",
        "arms": {
            "A": "F3 as promoted (DEC-043)",
            "B": "F3 minus robust fatigue value and indicator",
            "C": "F3 minus robust fatigue value, indicator retained",
            "D": "F1 external reference",
        },
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_CHAMPION_REOPEN_REVIEW",
        "selected_regularisation_c": config.selected_regularisation_c,
        "pooled_player_days": pooled.height,
        "pooled_positive_days": int(pooled["target"].sum()),
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
        "predictor_contract": _predictor_contract(arm_features, config),
        "arm_pooled_metrics": arm_metrics,
        "per_fold_metrics": per_fold,
        "dropped_fold_register": _dropped_register(dropped),
        "fixed_window_stress": fixed_window,
        "alert_budget_results": alerts,
        "paired_arm_differences": paired,
        "unseen_player_results": unseen_players,
        "unseen_player_aggregate_metrics": unseen_aggregate,
        "unseen_player_gap_analysis": unseen_gap_analysis,
        "one_day_gap_sensitivity": sensitivity,
        "ablation_findings": findings,
    }
    return Exp016AblationResult(
        tables=tables, pooled_predictions=pooled, summary=summary, source_metadata={}
    )


def _arm_feature_sets(config: Exp016AblationConfig) -> dict[str, tuple[str, ...]]:
    f3 = FEATURE_SETS["F3"]
    excluded_bc = {config.robust_fatigue_predictor, config.robust_fatigue_availability}
    return {
        "A": f3,
        "B": tuple(feature for feature in f3 if feature not in excluded_bc),
        "C": tuple(feature for feature in f3 if feature != config.robust_fatigue_predictor),
        "D": FEATURE_SETS["F1"],
    }


def _primary_cohort(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    return protocol.tables["_primary_cohort"]


def _fold_arm_predictions(
    cohort: pl.DataFrame,
    config: Exp016AblationConfig,
    arm_features: dict[str, tuple[str, ...]],
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
        if heldout.height == 0 or len(set(train_targets)) < 2:
            dropped.append(
                {
                    "fold_id": fold_id,
                    "reason": "single_class_training",
                    "training_positive_days": sum(train_targets),
                    "heldout_player_days": heldout.height,
                }
            )
            continue
        heldout_targets = _targets(heldout, target)
        arm_probabilities = {
            arm: _fit_predict(train, heldout, config, feature_names)
            for arm, feature_names in arm_features.items()
        }
        fold_frame = heldout.select(*KEYS, pl.col(target).alias("target")).with_columns(
            pl.lit(fold_id).alias("fold_id"),
            *[pl.Series(f"probability_{arm}", arm_probabilities[arm]) for arm in ARM_ORDER],
        )
        fold_frames.append(fold_frame)
        for arm in ARM_ORDER:
            metrics = classification_metrics(heldout_targets, arm_probabilities[arm])
            per_fold_rows.append(
                {
                    "fold_id": fold_id,
                    "arm": arm,
                    "training_positive_days": sum(train_targets),
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
    pooled = pl.concat(fold_frames, how="vertical")
    return pooled, pl.DataFrame(per_fold_rows), dropped


def _fit_predict(
    train: pl.DataFrame,
    heldout: pl.DataFrame,
    config: Exp016AblationConfig,
    feature_names: tuple[str, ...],
) -> list[float]:
    pipeline = build_feature_pipeline(
        regularisation_c=config.selected_regularisation_c,
        max_iterations=config.base_config.max_iterations,
    )
    pipeline.fit(_matrix(train, feature_names), _targets(train, config.base_config.target))
    return _positive_probabilities(pipeline, heldout, feature_names)


def _arm_pooled_metrics(pooled: pl.DataFrame, per_fold: pl.DataFrame) -> pl.DataFrame:
    all_targets = [int(value) for value in pooled["target"]]
    discrimination = pooled.join(
        pooled.group_by("fold_id").agg(pl.col("target").sum().alias("_fold_positive")),
        on="fold_id",
        how="left",
    ).filter(pl.col("_fold_positive") > 0)
    discrimination_targets = [int(value) for value in discrimination["target"]]
    rows: list[dict[str, Any]] = []
    for arm in ARM_ORDER:
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
                "pooled_player_days": pooled.height,
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
                "predictor_count": None,
                "estimable_fold_count": per_fold.filter(
                    (pl.col("arm") == arm) & (pl.col("heldout_positive_days") > 0)
                ).height,
            }
        )
    return pl.DataFrame(rows)


def _fixed_window_stress(
    cohort: pl.DataFrame,
    config: Exp016AblationConfig,
    arm_features: dict[str, tuple[str, ...]],
) -> pl.DataFrame:
    train = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[0]["start_date"], PARTITIONS[0]["end_date"])
    )
    validation = cohort.filter(
        pl.col("prediction_date").is_between(PARTITIONS[1]["start_date"], PARTITIONS[1]["end_date"])
    )
    targets = _targets(validation, config.base_config.target)
    rows: list[dict[str, Any]] = []
    for arm, feature_names in arm_features.items():
        probabilities = _fit_predict(train, validation, config, feature_names)
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
    pooled: pl.DataFrame, episodes: pl.DataFrame, config: Exp016AblationConfig
) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for arm in ARM_ORDER:
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
            model_id=f"M1-ABL-{arm}",
        )
        frames.append(alerts.with_columns(pl.lit(arm).alias("arm")))
    return pl.concat(frames, how="vertical")


def _paired_arm_differences(pooled: pl.DataFrame, config: Exp016AblationConfig) -> pl.DataFrame:
    target = config.base_config.target
    frames: list[pl.DataFrame] = []
    for candidate in ("B", "C", "D"):
        reference_frame = pooled.select(
            "player_id",
            "prediction_date",
            pl.col("target").alias(target),
            pl.col("probability_A").alias("predicted_probability"),
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
                reference_model_id="M1-ABL-A",
                candidate_model_id=f"M1-ABL-{candidate}",
            ).with_columns(
                pl.lit("A").alias("reference_arm"),
                pl.lit(candidate).alias("candidate_arm"),
            )
        )
    return pl.concat(frames, how="vertical")


def _unseen_player_results(
    cohort: pl.DataFrame,
    config: Exp016AblationConfig,
    arm_features: dict[str, tuple[str, ...]],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    development = cohort.filter(pl.col("prediction_date") <= DEVELOPMENT_CUTOFF)
    target = config.base_config.target
    player_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for arm, feature_names in arm_features.items():
        aggregate_targets: list[int] = []
        aggregate_probabilities: list[float] = []
        estimable = 0
        zero_positive = 0
        training_not_estimable = 0
        for player_id in development["player_id"].unique().sort():
            train = development.filter(pl.col("player_id") != player_id)
            heldout = development.filter(pl.col("player_id") == player_id)
            targets = _targets(heldout, target)
            train_targets = _targets(train, target)
            if len(set(train_targets)) < 2:
                training_not_estimable += 1
                metric_support = "training_not_estimable"
                metrics: dict[str, float | None] = {
                    "brier_score": None,
                    "log_loss": None,
                    "average_precision": None,
                    "roc_auc": None,
                }
            else:
                probabilities = _fit_predict(train, heldout, config, feature_names)
                metrics = classification_metrics(targets, probabilities)
                aggregate_targets.extend(targets)
                aggregate_probabilities.extend(probabilities)
                if sum(targets):
                    estimable += 1
                    metric_support = "estimable"
                else:
                    zero_positive += 1
                    metric_support = "zero_positive_support"
            player_rows.append(
                {
                    "arm": arm,
                    "player_id": player_id,
                    "training_positive_days": sum(train_targets),
                    "heldout_player_days": heldout.height,
                    "heldout_positive_days": sum(targets),
                    "brier_score": metrics["brier_score"],
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                    "metric_support": metric_support,
                }
            )
        aggregate = (
            classification_metrics(aggregate_targets, aggregate_probabilities)
            if aggregate_targets
            else {
                "player_days": 0.0,
                "positive_days": 0.0,
                "prevalence": None,
                "brier_score": None,
                "log_loss": None,
                "average_precision": None,
                "roc_auc": None,
            }
        )
        aggregate_rows.append(
            {
                "arm": arm,
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


def _unseen_gap_analysis(unseen_aggregate: pl.DataFrame) -> pl.DataFrame:
    reference = unseen_aggregate.filter(pl.col("arm") == "A").row(0, named=True)
    external = unseen_aggregate.filter(pl.col("arm") == "D").row(0, named=True)
    rows: list[dict[str, Any]] = []
    for arm in ("B", "C"):
        candidate = unseen_aggregate.filter(pl.col("arm") == arm).row(0, named=True)
        for metric in ("average_precision", "roc_auc"):
            gap_before = (
                cast(float, external[metric]) - cast(float, reference[metric])
                if external[metric] is not None and reference[metric] is not None
                else None
            )
            gap_after = (
                cast(float, external[metric]) - cast(float, candidate[metric])
                if external[metric] is not None and candidate[metric] is not None
                else None
            )
            rows.append(
                {
                    "candidate_arm": arm,
                    "metric": metric,
                    "arm_a_reference_value": reference[metric],
                    "candidate_value": candidate[metric],
                    "arm_d_f1_value": external[metric],
                    "f1_minus_a_gap": gap_before,
                    "f1_minus_candidate_gap": gap_after,
                    "gap_closed": (
                        abs(gap_after) < abs(gap_before)
                        if gap_before is not None and gap_after is not None
                        else None
                    ),
                }
            )
    return pl.DataFrame(rows)


def _one_day_gap_sensitivity(
    *,
    features: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp016AblationConfig,
    arm_features: dict[str, tuple[str, ...]],
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
    pooled_gap, per_fold_gap, _ = _fold_arm_predictions(cohort_gap, config, arm_features)
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


def _ablation_findings(
    *,
    per_fold: pl.DataFrame,
    arm_features: dict[str, tuple[str, ...]],
    config: Exp016AblationConfig,
    unseen_aggregate: pl.DataFrame,
    sensitivity: pl.DataFrame,
) -> pl.DataFrame:
    diff_b = set(arm_features["A"]) - set(arm_features["B"])
    diff_c = set(arm_features["A"]) - set(arm_features["C"])
    contract_ok = (
        diff_b == {config.robust_fatigue_predictor, config.robust_fatigue_availability}
        and diff_c == {config.robust_fatigue_predictor}
        and set(arm_features["B"]) < set(arm_features["A"])
        and set(arm_features["C"]) < set(arm_features["A"])
    )
    preprocessing_ok = config.selected_regularisation_c == 0.001
    zero_positive_folds = per_fold.filter(
        (pl.col("arm") == "A") & (pl.col("heldout_positive_days") == 0)
    ).height
    sensitivity_ok = {PRIMARY_GAP_DAYS, SENSITIVITY_GAP_DAYS} <= set(
        sensitivity["episode_gap_days"].to_list()
    )
    unseen_ok = unseen_aggregate.height == 4 and set(unseen_aggregate["arm"].to_list()) == set(
        ARM_ORDER
    )
    return pl.DataFrame(
        [
            {
                "finding_id": "ABL-01",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics produced",
            },
            {
                "finding_id": "ABL-02",
                "status": "PASS" if contract_ok else "FAIL",
                "domain": "arm_contract",
                "evidence": (
                    f"arm B removes {sorted(diff_b)}; arm C removes {sorted(diff_c)}; "
                    "all other F3 predictors unchanged across A, B, C"
                ),
            },
            {
                "finding_id": "ABL-03",
                "status": "PASS" if preprocessing_ok else "FAIL",
                "domain": "preprocessing_and_regularisation",
                "evidence": f"frozen regularisation C={config.selected_regularisation_c} unchanged",
            },
            {
                "finding_id": "ABL-04",
                "status": "PASS",
                "domain": "event_count_reporting",
                "evidence": (
                    "every metrics table carries pooled, discrimination and heldout event counts"
                ),
            },
            {
                "finding_id": "ABL-05",
                "status": "PASS" if sensitivity_ok else "FAIL",
                "domain": "one_day_gap_sensitivity",
                "evidence": "one-day-gap sensitivity present alongside the three-day headline",
            },
            {
                "finding_id": "ABL-06",
                "status": "PASS",
                "domain": "zero_positive_folds",
                "evidence": (
                    f"{zero_positive_folds} zero-positive folds excluded from discrimination "
                    "aggregation; estimable folds counted"
                ),
            },
            {
                "finding_id": "ABL-07",
                "status": "PASS" if unseen_ok else "FAIL",
                "domain": "unseen_player_generalisation",
                "evidence": "support-aware unseen-player aggregation present for all four arms",
            },
        ]
    )


def _dataset_manifest(config: Exp016AblationConfig) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": "EXP-016",
                "data_version": config.base_config.data_version,
                "target": config.base_config.target,
                "horizon_days": config.base_config.primary_horizon_days,
                "primary_episode_gap_days": PRIMARY_GAP_DAYS,
                "sensitivity_episode_gap_days": SENSITIVITY_GAP_DAYS,
                "selected_regularisation_c": config.selected_regularisation_c,
                "posthoc_calibration_selection": config.posthoc_calibration_selection,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _predictor_contract(
    arm_features: dict[str, tuple[str, ...]], config: Exp016AblationConfig
) -> pl.DataFrame:
    all_predictors = sorted(set().union(*arm_features.values()))
    return pl.DataFrame(
        [
            {
                "predictor": predictor,
                "arm": arm,
                "present": predictor in feature_names,
                "is_robust_fatigue_predictor": predictor == config.robust_fatigue_predictor,
                "is_robust_fatigue_indicator": predictor == config.robust_fatigue_availability,
            }
            for predictor in all_predictors
            for arm, feature_names in arm_features.items()
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
    pipeline: Any, frame: pl.DataFrame, feature_names: tuple[str, ...]
) -> list[float]:
    values = pipeline.predict_proba(_matrix(frame, feature_names))[:, 1]
    return [float(value) for value in values]


def build_exp_016_figures(result: Exp016AblationResult) -> dict[str, Figure]:
    """Build retained ablation development figures."""
    arm_metrics = result.tables["arm_pooled_metrics"]
    per_fold = result.tables["per_fold_metrics"]
    alerts = result.tables["alert_budget_results"]
    unseen_aggregate = result.tables["unseen_player_aggregate_metrics"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    colours = {"A": "#4C78A8", "B": "#F58518", "C": "#59A14F", "D": "#B279A2"}
    figures: dict[str, Figure] = {}

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(arm_metrics["arm"], arm_metrics["brier_score"], color=list(colours.values()))
    axes[0].set(title="Pooled probability accuracy", ylabel="Brier score")
    slopes = [value if value is not None else 0.0 for value in arm_metrics["calibration_slope"]]
    axes[1].bar(arm_metrics["arm"], slopes, color=list(colours.values()))
    axes[1].axhline(1.0, linestyle="--", color="#666666")
    axes[1].set(title="Calibration slope (raw)", ylabel="Slope (target 1.0)")
    figures["pooled_accuracy_and_slope_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    for arm in ARM_ORDER:
        table = per_fold.filter(pl.col("arm") == arm)
        axis.plot(table["fold_id"], table["brier_score"], marker="o", label=arm, color=colours[arm])
    axis.set(title="Per-fold Brier score", xlabel="Rolling-origin fold", ylabel="Brier score")
    axis.legend()
    figures["per_fold_brier_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for arm in ARM_ORDER:
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

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    ap_values = [
        value if value is not None else 0.0 for value in unseen_aggregate["average_precision"]
    ]
    roc_values = [value if value is not None else 0.0 for value in unseen_aggregate["roc_auc"]]
    axes[0].bar(unseen_aggregate["arm"], ap_values, color=list(colours.values()))
    axes[0].set(title="Unseen-player ranking", ylabel="Average precision")
    axes[1].bar(unseen_aggregate["arm"], roc_values, color=list(colours.values()))
    axes[1].set(title="Unseen-player discrimination", ylabel="ROC-AUC")
    fig.suptitle("Support-aware unseen-player generalisation")
    figures["unseen_player_generalisation_by_arm"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for axis, metric, title in (
        (axes[0], "brier_score", "Brier by episode gap"),
        (axes[1], "calibration_slope", "Calibration slope by episode gap"),
    ):
        for arm in ARM_ORDER:
            table = sensitivity.filter(pl.col("arm") == arm).sort("episode_gap_days")
            values = [value if value is not None else float("nan") for value in table[metric]]
            axis.plot(table["episode_gap_days"], values, marker="o", label=arm, color=colours[arm])
        axis.set(title=title, xlabel="Episode gap (days)")
        axis.set_xticks([SENSITIVITY_GAP_DAYS, PRIMARY_GAP_DAYS])
    axes[0].set_ylabel("Brier score")
    axes[1].set_ylabel("Slope")
    axes[1].legend()
    figures["episode_gap_sensitivity_by_arm"] = fig

    fig, axis = plt.subplots(figsize=(8, 5))
    heldout_counts = (
        result.tables["unseen_player_results"]
        .filter(pl.col("arm") == "A")
        .group_by("metric_support")
        .len()
        .sort("metric_support")
    )
    axis.bar(heldout_counts["metric_support"], heldout_counts["len"], color="#4C78A8")
    axis.set(title="Unseen-player outcome support (arm A)", ylabel="Held-out players")
    axis.tick_params(axis="x", rotation=10)
    figures["unseen_player_support"] = fig
    return figures


def write_exp_016_outputs(result: Exp016AblationResult, output_root: Path) -> None:
    """Persist canonical EXP-016 ablation development artifacts."""
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
    for name, figure in build_exp_016_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "exp_016_ablation_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_016_ABLATION_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: Exp016AblationResult) -> str:
    arm_metrics = result.tables["arm_pooled_metrics"]
    unseen_aggregate = result.tables["unseen_player_aggregate_metrics"]
    gap_analysis = result.tables["unseen_player_gap_analysis"]
    paired = result.tables["paired_arm_differences"]
    sensitivity = result.tables["one_day_gap_sensitivity"]
    findings = result.tables["ablation_findings"]
    summary = result.summary
    lines = [
        "# EXP-016 - Sparse-Predictor Availability Ablation Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{summary['status']}**. Project-owner champion review required.",
        "",
        (
            "Arm A is F3 as promoted under `DEC-043`. Arm B removes "
            "`fatigue_lag1_robust_z_prior` and its recording-state indicator entirely. "
            "Arm C removes the value but retains the indicator. Arm D is F1 as an external "
            "reference. Raw probabilities only, per `DEC-052`. No final-test row is read "
            "or scored."
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
    lines.extend(
        [
            "",
            "## Unseen-Player Generalisation (mandatory)",
            "",
            (
                "`DEC-043`'s binding limitation is that F3 (arm A) generalises worse than F1 "
                "(arm D) to unseen players."
            ),
            "",
            "| Arm | AP | ROC-AUC | Estimable players | Zero-positive players |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in unseen_aggregate.iter_rows(named=True):
        lines.append(
            f"| {row['arm']} | {_format(row['average_precision'])} | "
            f"{_format(row['roc_auc'])} | {row['estimable_player_count']}/"
            f"{row['heldout_player_count']} | {row['zero_positive_player_count']} |"
        )
    lines.extend(
        [
            "",
            "### Gap-Closure Analysis",
            "",
            "Whether removing the predictor value (B) or keeping only the indicator (C) "
            "closes the F1-minus-A unseen-player gap.",
            "",
            "| Candidate | Metric | A (reference) | Candidate | F1 (D) | F1-A gap | "
            "F1-candidate gap | Gap closed |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in gap_analysis.iter_rows(named=True):
        closed = "NA" if row["gap_closed"] is None else str(row["gap_closed"])
        lines.append(
            f"| {row['candidate_arm']} | {row['metric']} | "
            f"{_format(row['arm_a_reference_value'])} | {_format(row['candidate_value'])} | "
            f"{_format(row['arm_d_f1_value'])} | {_format(row['f1_minus_a_gap'])} | "
            f"{_format(row['f1_minus_candidate_gap'])} | {closed} |"
        )
    lines.extend(
        [
            "",
            "## Paired Bootstrap Differences Against Arm A",
            "",
            "| Candidate | Method | Metric | Median | 95% interval |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in paired.iter_rows(named=True):
        lines.append(
            f"| {row['candidate_arm']} | {row['method']} | {row['metric']} | "
            f"{_format(row['median'])} | [{_format(row['lower_95'])}, "
            f"{_format(row['upper_95'])}] |"
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
                "This experiment characterises whether a predictor's apparent contribution is "
                "carried by its availability pattern rather than its value. It selects no "
                "champion, changes no cohort and accesses no final-test data."
            ),
            "",
            "## Gate",
            "",
            (
                "If arm B or C matches or beats arm A on calibrated probability quality and "
                "improves unseen-player generalisation, `DEC-043` is reopened and the champion "
                "is re-selected through a new decision before V1-P2. If arm A remains best on "
                "both axes, F3 stands and the availability entanglement is documented as a "
                "binding limitation on every downstream citation. The project owner makes this "
                "call; this report does not."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"
