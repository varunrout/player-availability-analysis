"""EXP-019 alert-budget simulation for the raw F1 champion (`DEC-060`).

Translates raw F1 champion probabilities (`DEC-058`, `DEC-059`) into review-workflow
operating points and quantifies their cost, on pooled rolling-origin predictions built
the same way as `EXP-009`: each fold refits F1 on its training window and scores its own
held-out window, so held-out predictions are never scored by a model that has seen them.

Two operating-point families are reported side by side from the same pooled predictions:

- Primary, product-facing: top 1, 3 and 5 players per team-day (`DEC-060`), ranked
  within each team-day group, never globally, since the cohort holds two squads and a
  global ranking could place every alert in one of them.
- Secondary, frozen comparison basis under `DEC-036`: the 1%, 2.5% and 5% review rates
  used in every experiment since `EXP-002`. `DEC-060` does not supersede `DEC-036`.
- Retained capacity sensitivity, never a headline: 5%, 10% and 20% review rates,
  carried over from the original section 5 D2 stub.

No final-test row is read or scored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
import yaml
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.metrics import (
    alert_and_event_tables,
    classification_metrics,
    top_n_per_team_day_alert_and_event_tables,
)
from player_availability.modelling.preprocessing import F1_FEATURES, build_feature_pipeline
from player_availability.outcomes import build_injury_episodes, build_player_day_labels

HORIZONS_DAYS: tuple[int, ...] = (3, 7, 14)
PRIMARY_GAP_DAYS = 3
SENSITIVITY_GAP_DAYS = 1
KEYS = ("player_id", "team_id", "prediction_date")


@dataclass(frozen=True, slots=True)
class Exp019AlertBudgetConfig:
    """Frozen EXP-019 alert-budget configuration."""

    base_config: M1F1Config
    selected_regularisation_c: float
    top_n_values: tuple[int, ...]
    capacity_sensitivity_rates: tuple[float, ...]
    one_day_gap_sensitivity: bool
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class Exp019AlertBudgetResult:
    """Alert-budget tables, pooled predictions and metadata."""

    tables: dict[str, pl.DataFrame]
    pooled_predictions: pl.DataFrame
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_exp_019_config(path: Path) -> Exp019AlertBudgetConfig:
    """Load and validate the frozen EXP-019 alert-budget specification."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("EXP-019 configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = Exp019AlertBudgetConfig(
        base_config=base_config,
        selected_regularisation_c=float(raw["selected_regularisation_c"]),
        top_n_values=tuple(int(value) for value in raw["top_n_values"]),
        capacity_sensitivity_rates=tuple(
            float(value) for value in raw["capacity_sensitivity_rates"]
        ),
        one_day_gap_sensitivity=bool(raw["one_day_gap_sensitivity"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.selected_regularisation_c != 0.001:
        raise ValueError("EXP-019 uses the frozen F1 regularisation C=0.001; no retuning")
    if config.top_n_values != (1, 3, 5):
        raise ValueError("EXP-019 top-N operating points are frozen at 1, 3 and 5 (DEC-060)")
    if config.base_config.alert_review_rates != (0.01, 0.025, 0.05):
        raise ValueError("EXP-019 percentile basis must match the frozen DEC-036 review rates")
    if config.capacity_sensitivity_rates != (0.05, 0.10, 0.20):
        raise ValueError("EXP-019 capacity sensitivity is frozen at 5%, 10% and 20%")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("EXP-019 selects no calibrator and accesses no final test")
    return config


def load_exp_019_from_gcp(
    *, project_id: str, data_bucket: str, config: Exp019AlertBudgetConfig
) -> Exp019AlertBudgetResult:
    """Load compact canonical products once and execute the alert-budget simulation."""
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
    result = run_exp_019_alert_budget(
        features=frames["features"],
        episodes=frames["episodes"],
        injury_reports=frames["injury_reports"],
        player_registry=frames["player_registry"],
        config=config,
    )
    return Exp019AlertBudgetResult(
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


def run_exp_019_alert_budget(
    *,
    features: pl.DataFrame,
    episodes: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp019AlertBudgetConfig,
) -> Exp019AlertBudgetResult:
    """Translate raw F1 pooled rolling-origin predictions into review operating points."""
    cohort = _primary_cohort(features, episodes)
    pooled, per_fold, dropped = _fold_predictions(cohort, config)

    operating_points, event_detail = _operating_points(pooled, episodes, config)
    persistence = _alert_persistence(pooled, episodes, config, operating_points)
    sensitivity = _one_day_gap_sensitivity(
        features=features,
        injury_reports=injury_reports,
        player_registry=player_registry,
        config=config,
    )
    findings = _alert_findings(
        pooled=pooled,
        per_fold=per_fold,
        operating_points=operating_points,
        sensitivity=sensitivity,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    estimable_folds = per_fold.filter(pl.col("heldout_positive_days") > 0).height
    zero_positive_folds = per_fold.filter(pl.col("heldout_positive_days") == 0).height
    summary = {
        "experiment_id": "EXP-019",
        "model_id": "M1-F1-ALERT",
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_OPERATING_POINT_SELECTION",
        "top_n_values": list(config.top_n_values),
        "percentile_review_rates": list(config.base_config.alert_review_rates),
        "capacity_sensitivity_rates": list(config.capacity_sensitivity_rates),
        "tie_break_rule": "predicted_probability descending, then player_id ascending",
        "pooled_player_days": pooled.height,
        "pooled_positive_days": int(pooled["target"].sum()),
        "contributing_fold_count": per_fold.height,
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
        "per_fold_metrics": per_fold,
        "dropped_fold_register": _dropped_register(dropped),
        "alert_budget_results": operating_points,
        "event_capture_detail": event_detail,
        "alert_persistence": persistence,
        "one_day_gap_sensitivity": sensitivity,
        "alert_findings": findings,
    }
    return Exp019AlertBudgetResult(
        tables=tables,
        pooled_predictions=pooled,
        summary=summary,
        source_metadata={},
    )


def _primary_cohort(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    return protocol.tables["_primary_cohort"]


def _fold_predictions(
    cohort: pl.DataFrame,
    config: Exp019AlertBudgetConfig,
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
                    "reason": "not_estimable_single_class_training",
                    "training_positive_days": sum(train_targets),
                    "heldout_player_days": heldout.height,
                }
            )
            continue
        pipeline = build_feature_pipeline(
            regularisation_c=config.selected_regularisation_c,
            max_iterations=config.base_config.max_iterations,
        )
        pipeline.fit(_matrix(train, F1_FEATURES), train_targets)
        probabilities = _positive_probabilities(pipeline, heldout, F1_FEATURES)
        fold_frame = heldout.select(*KEYS, pl.col(target).alias("target")).with_columns(
            pl.lit(fold_id).alias("fold_id"),
            pl.Series("predicted_probability", probabilities),
        )
        fold_frames.append(fold_frame)
        heldout_targets = _targets(heldout, target)
        metrics = classification_metrics(heldout_targets, probabilities)
        per_fold_rows.append(
            {
                "fold_id": fold_id,
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


def _operating_points(
    pooled: pl.DataFrame,
    episodes: pl.DataFrame,
    config: Exp019AlertBudgetConfig,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    target = config.base_config.target
    predictions = pooled.select(*KEYS, pl.col("target").alias(target), "predicted_probability")
    rows: list[dict[str, Any]] = []
    event_frames: list[pl.DataFrame] = []

    top_n_alerts, top_n_events = top_n_per_team_day_alert_and_event_tables(
        predictions=predictions,
        episodes=episodes,
        target=target,
        horizon_days=config.base_config.primary_horizon_days,
        top_n_values=config.top_n_values,
        model_id="M1-F1-ALERT",
    )
    for row in top_n_alerts.iter_rows(named=True):
        rows.append(_alert_row("top_n_per_team_day", float(row["top_n"]), row))
    event_frames.append(
        top_n_events.with_columns(
            pl.lit("top_n_per_team_day").alias("operating_point_type"),
            pl.col("top_n").cast(pl.Float64).alias("operating_point_value"),
        ).drop("top_n")
    )

    for point_type, rates in (
        ("percentile", config.base_config.alert_review_rates),
        ("capacity_sensitivity", config.capacity_sensitivity_rates),
    ):
        alerts, events = alert_and_event_tables(
            predictions=predictions,
            episodes=episodes,
            target=target,
            horizon_days=config.base_config.primary_horizon_days,
            review_rates=rates,
            model_id="M1-F1-ALERT",
        )
        for row in alerts.iter_rows(named=True):
            rows.append(_alert_row(point_type, float(row["review_rate"]), row))
        event_frames.append(
            events.with_columns(
                pl.lit(point_type).alias("operating_point_type"),
                pl.col("review_rate").alias("operating_point_value"),
            ).drop("review_rate")
        )
    return pl.DataFrame(rows), pl.concat(event_frames, how="vertical")


def _alert_row(point_type: str, value: float, row: dict[str, Any]) -> dict[str, Any]:
    alert_count = int(row["alert_count"])
    positive_alert_days = int(row["positive_alert_days"])
    return {
        "operating_point_type": point_type,
        "operating_point_value": value,
        "source_player_days": int(row["eligible_player_days"]),
        "eligible_player_days": int(row["eligible_player_days"]),
        "alert_count": alert_count,
        "alerts_per_100_player_days": row["alerts_per_100_player_days"],
        "positive_alert_days": positive_alert_days,
        "precision": positive_alert_days / alert_count if alert_count else None,
        "represented_onsets": int(row["represented_onsets"]),
        "captured_onsets": int(row["captured_onsets"]),
        "recall": row["event_capture_rate"],
        "false_alerts_per_captured_onset": row["false_alerts_per_captured_onset"],
    }


def _alert_persistence(
    pooled: pl.DataFrame,
    episodes: pl.DataFrame,
    config: Exp019AlertBudgetConfig,
    operating_points: pl.DataFrame,
) -> pl.DataFrame:
    """Distribution of consecutive-day alert runs for the same player, per operating point."""
    target = config.base_config.target
    predictions = pooled.select(*KEYS, pl.col("target").alias(target), "predicted_probability")
    rows: list[dict[str, Any]] = []
    for point_type, value in (
        operating_points.select("operating_point_type", "operating_point_value")
        .unique()
        .iter_rows()
    ):
        selected = _select_for_operating_point(predictions, point_type, value)
        for run_length in _consecutive_run_lengths(selected):
            rows.append(
                {
                    "operating_point_type": point_type,
                    "operating_point_value": value,
                    "run_length_days": run_length,
                }
            )
    if not rows:
        return pl.DataFrame(
            schema={
                "operating_point_type": pl.Utf8,
                "operating_point_value": pl.Float64,
                "run_length_days": pl.Int64,
            }
        )
    return (
        pl.DataFrame(rows)
        .group_by(["operating_point_type", "operating_point_value", "run_length_days"])
        .agg(pl.len().alias("run_count"))
        .sort(["operating_point_type", "operating_point_value", "run_length_days"])
    )


def _select_for_operating_point(
    predictions: pl.DataFrame, point_type: str, value: float
) -> pl.DataFrame:
    if point_type == "top_n_per_team_day":
        ranked = predictions.sort(
            ["team_id", "prediction_date", "predicted_probability", "player_id"],
            descending=[False, False, True, False],
        ).with_columns(pl.int_range(pl.len()).over(["team_id", "prediction_date"]).alias("_rank"))
        return ranked.filter(pl.col("_rank") < int(value)).drop("_rank")
    alert_count = max(1, round(predictions.height * value))
    return predictions.sort(
        ["predicted_probability", "prediction_date", "player_id"],
        descending=[True, False, False],
    ).head(alert_count)


def _consecutive_run_lengths(selected: pl.DataFrame) -> list[int]:
    runs: list[int] = []
    for player_id in selected["player_id"].unique():
        dates = sorted(selected.filter(pl.col("player_id") == player_id)["prediction_date"])
        run_length = 1
        for previous, current in zip(dates, dates[1:], strict=False):
            if (current - previous).days == 1:
                run_length += 1
            else:
                runs.append(run_length)
                run_length = 1
        runs.append(run_length)
    return runs


def _one_day_gap_sensitivity(
    *,
    features: pl.DataFrame,
    injury_reports: pl.DataFrame,
    player_registry: pl.DataFrame,
    config: Exp019AlertBudgetConfig,
) -> pl.DataFrame:
    if not config.one_day_gap_sensitivity:
        return pl.DataFrame()
    features_gap, episodes_gap = _rebuild_features_for_gap(
        features, injury_reports, player_registry, SENSITIVITY_GAP_DAYS
    )
    cohort_gap = _primary_cohort(features_gap, episodes_gap)
    pooled_gap, _, _ = _fold_predictions(cohort_gap, config)
    operating_points_gap, _ = _operating_points(pooled_gap, episodes_gap, config)
    return pl.DataFrame(
        [
            {"episode_gap_days": SENSITIVITY_GAP_DAYS, **row}
            for row in operating_points_gap.iter_rows(named=True)
        ]
    )


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


def _alert_findings(
    *,
    pooled: pl.DataFrame,
    per_fold: pl.DataFrame,
    operating_points: pl.DataFrame,
    sensitivity: pl.DataFrame,
) -> pl.DataFrame:
    top_n_ranks_bounded = _top_n_never_exceeds_team_day_size(pooled, operating_points)
    false_alert_reported = {"alert_count", "false_alerts_per_captured_onset"}.issubset(
        operating_points.columns
    )
    event_count_reported = {"represented_onsets", "eligible_player_days"}.issubset(
        operating_points.columns
    )
    sensitivity_ok = (
        sensitivity.height > 0 and SENSITIVITY_GAP_DAYS in sensitivity["episode_gap_days"].to_list()
    )
    same_source = (
        operating_points["source_player_days"].n_unique() == 1
        and int(operating_points["source_player_days"][0]) == pooled.height
    )
    return pl.DataFrame(
        [
            {
                "finding_id": "ALERT-01",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics produced",
            },
            {
                "finding_id": "ALERT-02",
                "status": "PASS" if top_n_ranks_bounded else "FAIL",
                "domain": "top_n_scope",
                "evidence": "top-N selection never exceeds N players within any team-day group",
            },
            {
                "finding_id": "ALERT-03",
                "status": "PASS" if false_alert_reported else "FAIL",
                "domain": "false_alert_burden",
                "evidence": "every operating point reports false alerts per captured onset inline",
            },
            {
                "finding_id": "ALERT-04",
                "status": "PASS" if event_count_reported else "FAIL",
                "domain": "event_count_reporting",
                "evidence": "every operating point carries represented-onset and player-day counts",
            },
            {
                "finding_id": "ALERT-05",
                "status": "PASS" if sensitivity_ok else "FAIL",
                "domain": "one_day_gap_sensitivity",
                "evidence": "one-day-gap sensitivity present alongside the three-day headline",
            },
            {
                "finding_id": "ALERT-06",
                "status": "PASS" if same_source else "FAIL",
                "domain": "shared_prediction_set",
                "evidence": (
                    "percentile and top-N views are generated from the same pooled prediction set"
                ),
            },
        ]
    )


def _top_n_never_exceeds_team_day_size(
    pooled: pl.DataFrame, operating_points: pl.DataFrame
) -> bool:
    top_n = operating_points.filter(pl.col("operating_point_type") == "top_n_per_team_day")
    if top_n.height == 0:
        return False
    team_day_sizes = pooled.group_by(["team_id", "prediction_date"]).agg(
        pl.len().alias("team_day_player_count")
    )
    for row in top_n.iter_rows(named=True):
        n = int(row["operating_point_value"])
        max_possible_alerts = int(team_day_sizes["team_day_player_count"].clip(upper_bound=n).sum())
        if row["alert_count"] > max_possible_alerts:
            return False
    return True


def _dataset_manifest(config: Exp019AlertBudgetConfig) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": "EXP-019",
                "model_id": "M1-F1-ALERT",
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


def _dropped_register(dropped: list[dict[str, Any]]) -> pl.DataFrame:
    if not dropped:
        return pl.DataFrame(
            schema={
                "fold_id": pl.Utf8,
                "reason": pl.Utf8,
                "training_positive_days": pl.Int64,
                "heldout_player_days": pl.Int64,
            }
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


def build_exp_019_figures(result: Exp019AlertBudgetResult) -> dict[str, Figure]:
    """Build retained alert-budget development figures."""
    operating_points = result.tables["alert_budget_results"]
    per_fold = result.tables["per_fold_metrics"]
    figures: dict[str, Figure] = {}
    colours = {
        "top_n_per_team_day": "#4C78A8",
        "percentile": "#F58518",
        "capacity_sensitivity": "#BAB0AC",
    }

    fig, axis = plt.subplots(figsize=(7.5, 5))
    for point_type in ("top_n_per_team_day", "percentile", "capacity_sensitivity"):
        table = operating_points.filter(pl.col("operating_point_type") == point_type).sort(
            "alerts_per_100_player_days"
        )
        axis.plot(
            table["alerts_per_100_player_days"],
            table["recall"],
            marker="o",
            label=point_type,
            color=colours[point_type],
        )
    axis.set(
        title="Review capacity and represented-onset capture",
        xlabel="Alerts per 100 player-days",
        ylabel="Recall over represented onsets",
        ylim=(0, 1),
    )
    axis.legend()
    figures["capacity_vs_capture"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    top_n = operating_points.filter(pl.col("operating_point_type") == "top_n_per_team_day").sort(
        "operating_point_value"
    )
    axis.bar(
        [str(int(value)) for value in top_n["operating_point_value"]],
        top_n["false_alerts_per_captured_onset"].fill_null(0.0),
        color="#E45756",
    )
    axis.set(
        title="Top-N false-alert burden",
        xlabel="Top N per team-day",
        ylabel="False alerts per captured onset",
    )
    figures["top_n_false_alert_burden"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    percentile = operating_points.filter(pl.col("operating_point_type") == "percentile").sort(
        "operating_point_value"
    )
    axis.bar(
        [f"{value:.1%}" for value in percentile["operating_point_value"]],
        percentile["false_alerts_per_captured_onset"].fill_null(0.0),
        color="#72B7B2",
    )
    axis.set(
        title="Percentile false-alert burden (DEC-036 basis)",
        xlabel="Review rate",
        ylabel="False alerts per captured onset",
    )
    figures["percentile_false_alert_burden"] = fig

    fig, axis = plt.subplots(figsize=(8, 4.5))
    estimable = per_fold.filter(pl.col("average_precision").is_not_null())
    axis.plot(estimable["fold_id"], estimable["average_precision"], marker="o", color="#59A14F")
    axis.set(
        title="Rolling-origin raw F1 ranking feeding the alert simulation",
        xlabel="Fold",
        ylabel="Average precision",
    )
    figures["per_fold_average_precision"] = fig

    fig, axis = plt.subplots(figsize=(7.5, 5))
    for point_type in ("top_n_per_team_day", "percentile"):
        table = operating_points.filter(pl.col("operating_point_type") == point_type).sort(
            "operating_point_value"
        )
        axis.plot(
            table["alerts_per_100_player_days"],
            table["precision"],
            marker="o",
            label=point_type,
            color=colours[point_type],
        )
    axis.set(
        title="Alert precision by operating point",
        xlabel="Alerts per 100 player-days",
        ylabel="Precision",
        ylim=(0, 1),
    )
    axis.legend()
    figures["precision_by_operating_point"] = fig
    return figures


def write_exp_019_outputs(result: Exp019AlertBudgetResult, output_root: Path) -> None:
    """Persist canonical EXP-019 alert-budget development artifacts."""
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
    for name, figure in build_exp_019_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "exp_019_alert_budget_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_019_ALERT_BUDGET_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: Exp019AlertBudgetResult) -> str:
    operating_points = result.tables["alert_budget_results"]
    findings = result.tables["alert_findings"]
    summary = result.summary
    lines = [
        "# EXP-019 - Alert-Budget Simulation Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{summary['status']}**. Project-owner operating-point review required.",
        "",
        (
            "Raw F1 champion probabilities (`DEC-058`, `DEC-059`) are translated into review "
            "operating points on pooled rolling-origin predictions: top 1, 3 and 5 players per "
            "team-day as the product-facing primary view (`DEC-060`), and the frozen 1%, 2.5% "
            "and 5% review rates as the `DEC-036` comparison basis, reported side by side from "
            "the same prediction set. A 5%/10%/20% capacity sensitivity is retained but is never "
            "a headline. No final-test prediction or performance is created."
        ),
        "",
        f"Tie-break rule: {summary['tie_break_rule']}.",
        "",
        "## Operating Points",
        "",
        (
            "| Type | Value | Alerts | Alerts/100 days | Precision | Represented onsets | "
            "Captured | Recall | False alerts/captured |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in operating_points.sort(["operating_point_type", "operating_point_value"]).iter_rows(
        named=True
    ):
        lines.append(
            f"| {row['operating_point_type']} | {row['operating_point_value']:g} | "
            f"{row['alert_count']} | {row['alerts_per_100_player_days']:.2f} | "
            f"{_format(row['precision'])} | {row['represented_onsets']} | "
            f"{row['captured_onsets']} | {_format(row['recall'])} | "
            f"{_format(row['false_alerts_per_captured_onset'])} |"
        )
    lines.extend(
        [
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
            (
                "The selected operating point is a review-prioritisation policy. It is never a "
                "medical threshold, a clearance decision or participation advice. If no operating "
                "point captures onsets at a burden a practitioner would accept, that is a valid "
                "and reportable finding."
            ),
            "",
            "## Gate",
            "",
            (
                "The project owner records which operating points the dashboard will offer, each "
                "with its false-alert burden stated."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"
