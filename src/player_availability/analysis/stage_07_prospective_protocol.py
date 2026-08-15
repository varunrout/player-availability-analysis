"""Stage 7 prospective protocol freeze and leakage audit."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud.storage import Client  # type: ignore[import-untyped]
from matplotlib.figure import Figure

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX

PRIMARY_HORIZON_DAYS = 7
PRIMARY_BURN_IN_DAYS = 28
KEYS = ("player_id", "team_id", "prediction_date")

PARTITIONS: tuple[dict[str, Any], ...] = (
    {
        "partition": "train",
        "start_date": date(2020, 1, 29),
        "end_date": date(2020, 12, 24),
        "access_policy": "development",
    },
    {
        "partition": "validation",
        "start_date": date(2021, 1, 1),
        "end_date": date(2021, 6, 23),
        "access_policy": "development",
    },
    {
        "partition": "test",
        "start_date": date(2021, 7, 1),
        "end_date": date(2021, 12, 24),
        "access_policy": "locked_after_support_audit",
    },
)

ROLLING_FOLDS = (
    ("RO1", date(2020, 1, 29), date(2020, 6, 23), date(2020, 7, 1), date(2020, 9, 23)),
    ("RO2", date(2020, 1, 29), date(2020, 9, 23), date(2020, 10, 1), date(2020, 12, 24)),
    ("RO3", date(2020, 1, 29), date(2020, 12, 24), date(2021, 1, 1), date(2021, 3, 24)),
    ("RO4", date(2020, 1, 29), date(2021, 3, 24), date(2021, 4, 1), date(2021, 6, 23)),
)


@dataclass(frozen=True, slots=True)
class Stage07ProtocolResult:
    """Retained Stage 7 tables and summary values."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


def load_stage_07_from_gcp(*, project_id: str, data_bucket: str) -> Stage07ProtocolResult:
    """Load compact canonical products from GCS and execute Stage 7."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    frames = {
        name: pl.read_parquet(BytesIO(bucket.blob(path).download_as_bytes()))
        for name, path in paths.items()
    }
    return run_stage_07_prospective_protocol(**frames)


def run_stage_07_prospective_protocol(
    *, features: pl.DataFrame, episodes: pl.DataFrame
) -> Stage07ProtocolResult:
    """Freeze the prospective protocol and audit it without fitting a model."""
    prediction_features = _build_prediction_time_features(features)
    primary_cohort = prediction_features.filter(
        pl.col("eligible_new_onset_7d") & (pl.col("prior_calendar_days") >= PRIMARY_BURN_IN_DAYS)
    )
    predictor_contract = _predictor_contract()
    feature_set_ladder = _feature_set_ladder()
    prohibited_predictors = _prohibited_predictors()
    outcome_cohort_contract = _outcome_cohort_contract()
    split_manifest = _split_manifest()
    partition_support = _partition_support(primary_cohort, episodes)
    feature_coverage = _feature_coverage(primary_cohort, predictor_contract)
    rolling_origin_folds = _rolling_origin_support(primary_cohort)
    unseen_player_stress = _unseen_player_support(primary_cohort)
    preprocessing_contract = _preprocessing_contract()
    evaluation_contract = _evaluation_contract()
    alert_capacity_contract = _alert_capacity_contract()
    uncertainty_contract = _uncertainty_contract()
    leakage_findings = _leakage_findings(
        source=features,
        prediction_features=prediction_features,
        cohort=primary_cohort,
        predictor_contract=predictor_contract,
        prohibited=prohibited_predictors,
        partition_support=partition_support,
        feature_coverage=feature_coverage,
        rolling_origin_folds=rolling_origin_folds,
        unseen_player_stress=unseen_player_stress,
        preprocessing=preprocessing_contract,
    )
    failures = leakage_findings.filter(pl.col("status") == "FAIL").height
    warnings = leakage_findings.filter(pl.col("status") == "WARNING").height
    reviews = leakage_findings.filter(pl.col("status") == "REVIEW").height
    tables = {
        "outcome_cohort_contract": outcome_cohort_contract,
        "predictor_contract": predictor_contract,
        "feature_set_ladder": feature_set_ladder,
        "prohibited_predictors": prohibited_predictors,
        "split_manifest": split_manifest,
        "partition_support": partition_support,
        "feature_coverage": feature_coverage,
        "rolling_origin_folds": rolling_origin_folds,
        "unseen_player_stress": unseen_player_stress,
        "preprocessing_contract": preprocessing_contract,
        "evaluation_contract": evaluation_contract,
        "alert_capacity_contract": alert_capacity_contract,
        "uncertainty_contract": uncertainty_contract,
        "leakage_findings": leakage_findings,
        "_prediction_features": prediction_features,
        "_primary_cohort": primary_cohort,
    }
    return Stage07ProtocolResult(
        tables=tables,
        summary={
            "stage": "07_prospective_protocol",
            "status": "PASS" if failures == 0 else "FAIL",
            "primary_horizon_days": PRIMARY_HORIZON_DAYS,
            "primary_burn_in_days": PRIMARY_BURN_IN_DAYS,
            "eligible_player_days": primary_cohort.height,
            "eligible_player_count": primary_cohort["player_id"].n_unique(),
            "predictor_count": predictor_contract.filter(
                pl.col("contract_status") == "ALLOW"
            ).height,
            "partition_count": len(PARTITIONS),
            "rolling_origin_fold_count": len(ROLLING_FOLDS),
            "model_count": 0,
            "performance_metric_count": 0,
            "final_test_performance_accessed": False,
            "failure_count": failures,
            "warning_count": warnings,
            "review_count": reviews,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def write_stage_07_outputs(result: Stage07ProtocolResult, output_root: Path) -> None:
    """Persist canonical Stage 7 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if not name.startswith("_"):
            table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_07_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["reports"] / "STAGE_07_PROSPECTIVE_PROTOCOL.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    (directories["metadata"] / "stage_07_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_prediction_time_features(features: pl.DataFrame) -> pl.DataFrame:
    required = {
        *KEYS,
        "eligible_new_onset_7d",
        "injury_next_7d",
        "session_count",
        "daily_load",
        "session_duration_minutes",
        "session_srpe",
        "daily_load_sum_7d",
        "daily_load_sum_28d",
        "session_duration_sum_7d",
        "session_duration_sum_28d",
        "session_srpe_sum_7d",
        "session_srpe_sum_28d",
        "wellness_report_present",
        "fatigue",
        "readiness",
    }
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Missing Stage 7 feature columns: {missing}")
    rows: list[dict[str, object]] = []
    for _, group in features.sort("player_id", "prediction_date").group_by(
        "player_id", maintain_order=True
    ):
        history: list[dict[str, Any]] = []
        for source in group.iter_rows(named=True):
            previous = history[-1] if history else None
            prior_7 = history[-7:]
            prior_28 = history[-28:]
            prior_recorded = [
                math.log1p(float(row["daily_load"]))
                for row in prior_28
                if int(row["session_count"]) > 0
            ]
            fatigue_history = [
                float(row["fatigue"]) for row in history if row["fatigue"] is not None
            ]
            readiness_history = [
                float(row["readiness"]) for row in history if row["readiness"] is not None
            ]
            fatigue_lag1 = None if previous is None else previous["fatigue"]
            readiness_lag1 = None if previous is None else previous["readiness"]
            row = dict(source)
            row.update(
                {
                    "prior_calendar_days": len(history),
                    "session_recorded": int(source["session_count"]) > 0,
                    "daily_load_log1p": math.log1p(float(source["daily_load"])),
                    "session_duration_minutes_log1p": math.log1p(
                        float(source["session_duration_minutes"])
                    ),
                    "daily_load_sum_7d_log1p": math.log1p(float(source["daily_load_sum_7d"])),
                    "daily_load_sum_28d_log1p": math.log1p(float(source["daily_load_sum_28d"])),
                    "session_duration_sum_7d_log1p": math.log1p(
                        float(source["session_duration_sum_7d"])
                    ),
                    "session_duration_sum_28d_log1p": math.log1p(
                        float(source["session_duration_sum_28d"])
                    ),
                    "session_srpe_log1p": math.log1p(float(source["session_srpe"])),
                    "session_srpe_sum_7d_log1p": math.log1p(float(source["session_srpe_sum_7d"])),
                    "session_srpe_sum_28d_log1p": math.log1p(float(source["session_srpe_sum_28d"])),
                    "wellness_report_present_lag1": (
                        None if previous is None else bool(previous["wellness_report_present"])
                    ),
                    "fatigue_lag1": fatigue_lag1,
                    "readiness_lag1": readiness_lag1,
                    "wellness_report_count_prior_7d": sum(
                        int(bool(value["wellness_report_present"])) for value in prior_7
                    ),
                    "wellness_report_count_prior_28d": sum(
                        int(bool(value["wellness_report_present"])) for value in prior_28
                    ),
                    "fatigue_mean_prior_7d": _observed_mean(prior_7, "fatigue"),
                    "fatigue_mean_prior_28d": _observed_mean(prior_28, "fatigue"),
                    "readiness_mean_prior_7d": _observed_mean(prior_7, "readiness"),
                    "readiness_mean_prior_28d": _observed_mean(prior_28, "readiness"),
                    "daily_load_robust_z_prior28": _robust_z(
                        math.log1p(float(source["daily_load"])), prior_recorded
                    ),
                    "daily_load_robust_available": _robust_available(prior_recorded),
                    "fatigue_lag1_robust_z_prior": _robust_z_nullable(
                        fatigue_lag1, fatigue_history
                    ),
                    "fatigue_robust_available": _robust_available(fatigue_history),
                    "readiness_lag1_robust_z_prior": _robust_z_nullable(
                        readiness_lag1, readiness_history
                    ),
                    "readiness_robust_available": _robust_available(readiness_history),
                }
            )
            rows.append(row)
            history.append(source)
    return pl.DataFrame(rows, infer_schema_length=None).sort(*KEYS)


def _observed_mean(rows: list[dict[str, Any]], column: str) -> float | None:
    values = [float(row[column]) for row in rows if row[column] is not None]
    return sum(values) / len(values) if values else None


def _robust_available(history: list[float]) -> bool:
    if len(history) < 7:
        return False
    centre = median(history)
    return median(abs(value - centre) for value in history) > 1e-9


def _robust_z(value: float, history: list[float]) -> float | None:
    if not _robust_available(history):
        return None
    centre = median(history)
    scale = 1.4826 * median(abs(item - centre) for item in history)
    return (value - centre) / scale


def _robust_z_nullable(value: Any, history: list[float]) -> float | None:
    return None if value is None else _robust_z(float(value), history)


def _predictor_contract() -> pl.DataFrame:
    rows: list[dict[str, object]] = []

    def add(
        feature_set: str, names: tuple[str, ...], family: str, timing: str, handling: str
    ) -> None:
        for name in names:
            rows.append(
                {
                    "feature_set": feature_set,
                    "predictor": name,
                    "family": family,
                    "prediction_time": timing,
                    "missing_value_rule": handling,
                    "contract_status": "ALLOW",
                }
            )

    add(
        "F1",
        (
            "daily_load_log1p",
            "daily_load_sum_7d_log1p",
            "daily_load_sum_28d_log1p",
        ),
        "absolute_load",
        "end_of_day_current_or_trailing",
        "observed_zero_preserved",
    )
    add(
        "F1",
        (
            "fatigue_lag1",
            "readiness_lag1",
            "fatigue_mean_prior_7d",
            "fatigue_mean_prior_28d",
            "readiness_mean_prior_7d",
            "readiness_mean_prior_28d",
        ),
        "lagged_wellness",
        "strictly_prior",
        "nullable_with_missing_indicator",
    )
    add(
        "F2",
        (
            "session_recorded",
            "session_count",
            "session_duration_minutes_log1p",
            "session_duration_sum_7d_log1p",
            "session_duration_sum_28d_log1p",
        ),
        "session_exposure",
        "end_of_day_current_or_trailing",
        "observed_zero_preserved",
    )
    add(
        "F2",
        (
            "wellness_report_present_lag1",
            "wellness_report_count_prior_7d",
            "wellness_report_count_prior_28d",
        ),
        "missingness_and_reporting",
        "strictly_prior",
        "explicit_process_indicators",
    )
    add(
        "F3",
        (
            "daily_load_robust_z_prior28",
            "daily_load_robust_available",
            "fatigue_lag1_robust_z_prior",
            "fatigue_robust_available",
            "readiness_lag1_robust_z_prior",
            "readiness_robust_available",
        ),
        "player_relative",
        "strictly_prior_baseline",
        "nullable_with_availability_indicator",
    )
    add(
        "S_SRPE",
        ("session_srpe_log1p", "session_srpe_sum_7d_log1p", "session_srpe_sum_28d_log1p"),
        "srpe_replacement",
        "end_of_day_current_or_trailing",
        "replace_daily_load_family_never_add",
    )
    return pl.DataFrame(rows)


def _feature_set_ladder() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "feature_set": "F0",
                "definition": "Global training prevalence only; no predictors",
                "comparison_role": "Operational baseline",
            },
            {
                "feature_set": "F1",
                "definition": "Absolute load plus strictly lagged absolute wellness",
                "comparison_role": "Subjective state baseline",
            },
            {
                "feature_set": "F2",
                "definition": "F1 plus session exposure and prior reporting/missingness",
                "comparison_role": "Operational context",
            },
            {
                "feature_set": "F3",
                "definition": "F2 plus strictly prior robust player-relative features",
                "comparison_role": "Personalisation hypothesis",
            },
            {
                "feature_set": "S_SRPE",
                "definition": "Replace the daily-load family with sRPE; never add both",
                "comparison_role": "Redundancy sensitivity",
            },
        ]
    )


def _prohibited_predictors() -> pl.DataFrame:
    groups = (
        ("identity", "player_id; team_id; report_id; episode_id"),
        ("same_day_wellness", "fatigue; readiness; wellness_report_present; wellness_metric_count"),
        (
            "outcome",
            "injury_next_*; eligible_new_onset_*; active_injury_episode; days_to_next_injury",
        ),
        ("future_or_followup", "observation_end; episode_start; episode_end; recovery fields"),
        (
            "unstable_relative",
            "daily_load_zscore_prior; fatigue_zscore_prior; readiness_zscore_prior",
        ),
        ("memorisation", "prediction_date raw value; source row identifiers"),
        (
            "redundant_primary",
            "session_srpe family alongside daily_load family; 3d/14d rolling windows",
        ),
    )
    return pl.DataFrame(
        {
            "prohibition_group": group,
            "prohibited_fields_or_pattern": fields,
            "reason": "Excluded by the frozen prediction-time, leakage or redundancy contract",
        }
        for group, fields in groups
    )


def _outcome_cohort_contract() -> pl.DataFrame:
    rows = [
        ("primary", "episode_gap_days", "3", "DEC-035 primary episode construction"),
        ("primary", "prediction_horizon_days", "7", "Future player-date onset target"),
        ("primary", "burn_in_days", "28", "Strictly prior calendar history"),
        ("primary", "eligibility", "complete horizon; outside active episode", "Production labels"),
        ("secondary", "prediction_horizons_days", "3; 14", "Lead-time sensitivity"),
        ("sensitivity", "episode_gap_days", "1; 7", "Outcome-definition sensitivity"),
        ("sensitivity", "cohort", "broad no-burn-in", "Mandatory support sensitivity"),
        ("prohibited_filter", "isolated_onset", "never", "Retrospective outcome information"),
    ]
    return pl.DataFrame(
        {
            "contract_role": role,
            "parameter": parameter,
            "value": value,
            "rationale": rationale,
        }
        for role, parameter, value, rationale in rows
    )


def _split_manifest() -> pl.DataFrame:
    rows = []
    for rank, item in enumerate(PARTITIONS, start=1):
        rows.append(
            {
                "partition_rank": rank,
                **item,
                "horizon_days": PRIMARY_HORIZON_DAYS,
                "next_partition_embargo_days": 0 if item["partition"] == "test" else 7,
                "model_performance_allowed_stage_07": False,
            }
        )
    return pl.DataFrame(rows)


def _partition_support(cohort: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    onsets = episodes.select("player_id", pl.col("episode_start").alias("onset_date")).unique()
    rows = []
    for item in PARTITIONS:
        partition = cohort.filter(
            pl.col("prediction_date").is_between(item["start_date"], item["end_date"])
        )
        represented = _represented_onsets(partition, onsets, PRIMARY_HORIZON_DAYS)
        rows.append(
            {
                "partition": item["partition"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "player_days": partition.height,
                "player_count": partition["player_id"].n_unique(),
                "team_count": partition["team_id"].n_unique(),
                "positive_player_days": partition.filter(pl.col("injury_next_7d")).height,
                "represented_onset_count": represented.height,
                "represented_event_player_count": represented["player_id"].n_unique(),
                "performance_inspected": False,
            }
        )
    return pl.DataFrame(rows)


def _represented_onsets(cohort: pl.DataFrame, onsets: pl.DataFrame, horizon: int) -> pl.DataFrame:
    keys = set(cohort.select("player_id", "prediction_date").iter_rows())
    rows = []
    for onset in onsets.iter_rows(named=True):
        onset_date = onset["onset_date"]
        assert isinstance(onset_date, date)
        if any(
            (onset["player_id"], onset_date - timedelta(days=offset)) in keys
            for offset in range(1, horizon + 1)
        ):
            rows.append(onset)
    return pl.DataFrame(rows, schema=onsets.schema) if rows else onsets.head(0)


def _feature_coverage(cohort: pl.DataFrame, contract: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for item in contract.iter_rows(named=True):
        feature = str(item["predictor"])
        observed = cohort[feature].is_not_null().sum()
        rows.append(
            {
                "feature_set": item["feature_set"],
                "predictor": feature,
                "observed_player_days": observed,
                "missing_player_days": cohort.height - observed,
                "coverage_rate": observed / cohort.height,
            }
        )
    return pl.DataFrame(rows)


def _rolling_origin_support(cohort: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for fold, train_start, train_end, validation_start, validation_end in ROLLING_FOLDS:
        train = cohort.filter(pl.col("prediction_date").is_between(train_start, train_end))
        validation = cohort.filter(
            pl.col("prediction_date").is_between(validation_start, validation_end)
        )
        rows.append(
            {
                "fold_id": fold,
                "train_start": train_start,
                "train_end": train_end,
                "validation_start": validation_start,
                "validation_end": validation_end,
                "embargo_days": 7,
                "train_player_days": train.height,
                "train_positive_player_days": train.filter(pl.col("injury_next_7d")).height,
                "validation_player_days": validation.height,
                "validation_positive_player_days": validation.filter(
                    pl.col("injury_next_7d")
                ).height,
                "performance_inspected": False,
            }
        )
    return pl.DataFrame(rows)


def _unseen_player_support(cohort: pl.DataFrame) -> pl.DataFrame:
    development = cohort.filter(pl.col("prediction_date") <= date(2021, 6, 23))
    return (
        development.group_by("player_id", "team_id")
        .agg(
            pl.len().alias("heldout_player_days"),
            pl.col("injury_next_7d").sum().alias("heldout_positive_player_days"),
        )
        .with_columns(
            (pl.lit(development.height) - pl.col("heldout_player_days")).alias(
                "development_training_player_days"
            ),
            pl.lit("stress_test_only").alias("protocol_role"),
            pl.lit(False).alias("performance_inspected"),
        )
        .sort("heldout_positive_player_days", descending=True)
    )


def _preprocessing_contract() -> pl.DataFrame:
    rows = (
        ("numeric_missing", "median imputation", "fit on training partition only"),
        ("missingness", "explicit indicators", "preserve reporting and baseline availability"),
        ("scaling", "standard scaling for scale-sensitive models", "fit on training only"),
        ("tree_models", "native missing handling where supported", "no global pre-imputation"),
        (
            "feature_selection",
            "frozen sets then training-only selection",
            "validation comparison only",
        ),
        ("calibration", "post-model calibration", "fit on validation or nested development fold"),
        ("class_weighting", "candidate sensitivity", "select using development data only"),
    )
    return pl.DataFrame(
        {"component": component, "rule": rule, "fit_scope": scope}
        for component, rule, scope in rows
    )


def _evaluation_contract() -> pl.DataFrame:
    rows = (
        ("primary", "brier_score", "lower", "probability accuracy and calibration"),
        ("primary", "average_precision", "higher", "rare-outcome ranking"),
        ("secondary", "log_loss", "lower", "penalises overconfident probabilities"),
        ("secondary", "roc_auc", "higher", "reported with imbalance caveat"),
        ("calibration", "calibration_intercept", "near_zero", "systematic risk bias"),
        ("calibration", "calibration_slope", "near_one", "probability spread"),
        ("operational", "event_capture", "higher", "represented onsets preceded by an alert"),
        ("operational", "lead_time_days", "higher", "time available for practitioner review"),
        ("operational", "alerts_per_100_player_days", "capacity_bound", "review burden"),
    )
    return pl.DataFrame(
        {"metric_role": role, "metric": metric, "direction": direction, "purpose": purpose}
        for role, metric, direction, purpose in rows
    )


def _alert_capacity_contract() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "review_rate": rate,
            "alerts_per_100_player_days": rate * 100,
            "threshold_fit_scope": "validation_only",
            "reporting_rule": "report precision, sensitivity, event capture and lead time",
        }
        for rate in (0.01, 0.025, 0.05)
    )


def _uncertainty_contract() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "method": "player_cluster_bootstrap",
                "unit": "player",
                "interval": "95% percentile",
                "purpose": "repeated player-day dependence",
            },
            {
                "method": "temporal_block_bootstrap",
                "unit": "calendar week",
                "interval": "95% percentile",
                "purpose": "calendar dependence and event clustering",
            },
            {
                "method": "point_estimate_plus_support",
                "unit": "represented onset and event player",
                "interval": "always disclose counts",
                "purpose": "prevent precise-looking sparse estimates",
            },
        ]
    )


def _leakage_findings(
    *,
    source: pl.DataFrame,
    prediction_features: pl.DataFrame,
    cohort: pl.DataFrame,
    predictor_contract: pl.DataFrame,
    prohibited: pl.DataFrame,
    partition_support: pl.DataFrame,
    feature_coverage: pl.DataFrame,
    rolling_origin_folds: pl.DataFrame,
    unseen_player_stress: pl.DataFrame,
    preprocessing: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def finding(check: str, status: str, evidence: str) -> None:
        rows.append({"check_id": check, "status": status, "evidence": evidence})

    duplicate_count = prediction_features.height - prediction_features.unique(KEYS).height
    finding(
        "player_date_uniqueness",
        "PASS" if duplicate_count == 0 else "FAIL",
        f"{duplicate_count} duplicate keys",
    )
    allowed = set(predictor_contract["predictor"].to_list())
    forbidden_exact = {
        "player_id",
        "team_id",
        "prediction_date",
        "fatigue",
        "readiness",
        "wellness_report_present",
        "wellness_metric_count",
        "daily_load_zscore_prior",
        "fatigue_zscore_prior",
        "readiness_zscore_prior",
        "active_injury_episode",
        "injury_next_7d",
        "eligible_new_onset_7d",
        "observation_end",
    }
    overlap = sorted(allowed & forbidden_exact)
    finding(
        "forbidden_predictor_exclusion",
        "PASS" if not overlap else "FAIL",
        f"forbidden allow-list overlap: {overlap}",
    )
    same_day = sorted({"fatigue", "readiness", "wellness_report_present"} & allowed)
    finding(
        "same_day_wellness_exclusion",
        "PASS" if not same_day else "FAIL",
        f"same-day wellness predictors: {same_day}",
    )
    missing_allowed = sorted(allowed - set(prediction_features.columns))
    finding(
        "predictor_materialisation",
        "PASS" if not missing_allowed else "FAIL",
        f"missing predictors: {missing_allowed}",
    )
    expected_cohort = (
        source.filter(pl.col("eligible_new_onset_7d"))
        .join(prediction_features.select(*KEYS, "prior_calendar_days"), on=list(KEYS), how="inner")
        .filter(pl.col("prior_calendar_days") >= 28)
    )
    finding(
        "primary_cohort_reproduction",
        "PASS" if expected_cohort.height == cohort.height else "FAIL",
        f"expected {expected_cohort.height}, observed {cohort.height}",
    )
    assigned = 0
    for item in PARTITIONS:
        assigned += cohort.filter(
            pl.col("prediction_date").is_between(item["start_date"], item["end_date"])
        ).height
    embargo_rows = cohort.filter(
        pl.col("prediction_date").is_between(date(2020, 12, 25), date(2020, 12, 31))
        | pl.col("prediction_date").is_between(date(2021, 6, 24), date(2021, 6, 30))
    ).height
    unexplained_rows = cohort.height - assigned - embargo_rows
    finding(
        "partition_and_embargo_accounting",
        "PASS" if unexplained_rows == 0 else "FAIL",
        f"{assigned} assigned, {embargo_rows} embargoed, {unexplained_rows} unexplained",
    )
    embargo_ok = all(
        item["end_date"] + timedelta(days=7) < PARTITIONS[index + 1]["start_date"]
        for index, item in enumerate(PARTITIONS[:-1])
    )
    finding(
        "seven_day_embargo",
        "PASS" if embargo_ok else "FAIL",
        "target windows end before the next partition starts",
    )
    cutoff = date(2021, 7, 1)
    truncated = source.filter(pl.col("prediction_date") < cutoff)
    rebuilt = _build_prediction_time_features(truncated)
    comparison_columns = sorted(allowed | set(KEYS) | {"prior_calendar_days"})
    full_prior = prediction_features.filter(pl.col("prediction_date") < cutoff).select(
        comparison_columns
    )
    append_invariant = rebuilt.select(comparison_columns).equals(full_prior)
    finding(
        "future_append_invariance",
        "PASS" if append_invariant else "FAIL",
        f"{rebuilt.height} earlier rows unchanged after future append",
    )
    lag_mismatch = (
        prediction_features.with_columns(
            pl.col("fatigue").shift(1).over("player_id").alias("_expected_fatigue_lag1"),
            pl.col("readiness").shift(1).over("player_id").alias("_expected_readiness_lag1"),
        )
        .filter(
            ~pl.col("fatigue_lag1").eq_missing(pl.col("_expected_fatigue_lag1"))
            | ~pl.col("readiness_lag1").eq_missing(pl.col("_expected_readiness_lag1"))
        )
        .height
    )
    finding(
        "strictly_prior_wellness",
        "PASS" if lag_mismatch == 0 else "FAIL",
        f"{lag_mismatch} lag mismatches",
    )
    unsafe_fit_scope = preprocessing.filter(
        pl.col("fit_scope").str.contains("full data|test partition|all partitions")
    ).height
    train_only = unsafe_fit_scope == 0
    finding(
        "preprocessing_fit_scope",
        "PASS" if train_only else "FAIL",
        "all learned preprocessing is restricted to development partitions",
    )
    final_test_accessed = partition_support.filter(pl.col("performance_inspected")).height
    finding(
        "final_test_lock",
        "PASS" if final_test_accessed == 0 else "FAIL",
        "support only; no prediction or performance metric exists",
    )
    finding(
        "prohibition_register",
        "PASS" if prohibited.height >= 7 else "FAIL",
        f"{prohibited.height} prohibition groups documented",
    )
    zero_event_partitions = partition_support.filter(pl.col("represented_onset_count") == 0).height
    finding(
        "partition_event_support",
        "PASS" if zero_event_partitions == 0 else "WARNING",
        f"{zero_event_partitions} partitions have no represented onsets",
    )
    sparse_partitions = partition_support.filter(pl.col("represented_onset_count") < 10).height
    finding(
        "sparse_partition_support",
        "REVIEW" if sparse_partitions else "PASS",
        f"{sparse_partitions} partitions have fewer than 10 represented onsets",
    )
    zero_positive_folds = rolling_origin_folds.filter(
        pl.col("validation_positive_player_days") == 0
    ).height
    finding(
        "rolling_origin_positive_support",
        "WARNING" if zero_positive_folds else "PASS",
        f"{zero_positive_folds} validation folds have zero positive player-days",
    )
    zero_positive_players = unseen_player_stress.filter(
        pl.col("heldout_positive_player_days") == 0
    ).height
    finding(
        "unseen_player_positive_support",
        "REVIEW" if zero_positive_players else "PASS",
        f"{zero_positive_players} held-out players have zero positive development days",
    )
    low_coverage = feature_coverage.filter(pl.col("coverage_rate") < 0.20).height
    finding(
        "low_coverage_predictors",
        "REVIEW" if low_coverage else "PASS",
        f"{low_coverage} allowed predictors have less than 20% primary-cohort coverage",
    )
    finding(
        "model_free_stage",
        "PASS",
        "zero fitted models, predictions, thresholds or performance estimates",
    )
    return pl.DataFrame(rows)


def build_stage_07_figures(result: Stage07ProtocolResult) -> dict[str, Figure]:
    """Build Stage 7 protocol and support figures."""
    figures: dict[str, Figure] = {}
    support = result.tables["partition_support"]
    colours = ["#287271", "#E9C46A", "#E76F51"]

    fig, axis = plt.subplots(figsize=(9, 4.8))
    axis.bar(support["partition"], support["player_days"], color=colours)
    axis.set_ylabel("Eligible player-days")
    axis.set_title("Frozen chronological partition support")
    fig.tight_layout()
    figures["partition_player_days"] = fig

    fig, axis = plt.subplots(figsize=(9, 4.8))
    axis.bar(support["partition"], support["represented_onset_count"], color=colours)
    axis.set_ylabel("Represented onset dates")
    axis.set_title("Outcome support audit only, no performance inspection")
    fig.tight_layout()
    figures["partition_onset_support"] = fig

    coverage = result.tables["feature_coverage"].sort("coverage_rate")
    fig, axis = plt.subplots(figsize=(10, 7))
    axis.barh(coverage["predictor"], coverage["coverage_rate"], color="#287271")
    axis.set_xlim(0, 1.02)
    axis.set_xlabel("Observed share of primary cohort")
    axis.set_title("Frozen predictor availability")
    fig.tight_layout()
    figures["predictor_coverage"] = fig

    contract = result.tables["predictor_contract"].group_by("feature_set").len().sort("feature_set")
    fig, axis = plt.subplots(figsize=(8, 4.8))
    axis.bar(
        contract["feature_set"], contract["len"], color=["#287271", "#E9C46A", "#4C78A8", "#E76F51"]
    )
    axis.set_ylabel("Predictors")
    axis.set_title("Feature-set contract size")
    fig.tight_layout()
    figures["feature_set_size"] = fig

    folds = result.tables["rolling_origin_folds"]
    fig, axis = plt.subplots(figsize=(9, 4.8))
    x = list(range(folds.height))
    axis.bar(
        [value - 0.18 for value in x],
        folds["train_positive_player_days"],
        0.36,
        label="Train",
        color="#287271",
    )
    axis.bar(
        [value + 0.18 for value in x],
        folds["validation_positive_player_days"],
        0.36,
        label="Validation",
        color="#E76F51",
    )
    axis.set_xticks(x, folds["fold_id"])
    axis.set_ylabel("Positive player-days")
    axis.set_title("Rolling-origin outcome support")
    axis.legend(frameon=False)
    fig.tight_layout()
    figures["rolling_origin_support"] = fig

    unseen = result.tables["unseen_player_stress"].sort(
        "heldout_positive_player_days", descending=True
    )
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.bar(range(unseen.height), unseen["heldout_positive_player_days"], color="#4C78A8")
    axis.set_xlabel("Held-out player, ordered by positive support")
    axis.set_ylabel("Positive player-days")
    axis.set_title("Leave-one-player-out support concentration")
    fig.tight_layout()
    figures["unseen_player_support"] = fig

    findings = result.tables["leakage_findings"].group_by("status").len()
    fig, axis = plt.subplots(figsize=(7, 4.8))
    palette = {"PASS": "#287271", "REVIEW": "#E9C46A", "WARNING": "#E76F51", "FAIL": "#B00020"}
    axis.bar(
        findings["status"], findings["len"], color=[palette[value] for value in findings["status"]]
    )
    axis.set_ylabel("Checks")
    axis.set_title("Stage 7 leakage and protocol checks")
    fig.tight_layout()
    figures["leakage_check_status"] = fig

    alerts = result.tables["alert_capacity_contract"]
    fig, axis = plt.subplots(figsize=(7, 4.8))
    axis.bar(
        [f"{rate * 100:g}%" for rate in alerts["review_rate"]],
        alerts["alerts_per_100_player_days"],
        color="#E9C46A",
    )
    axis.set_xlabel("Review-rate budget")
    axis.set_ylabel("Alerts per 100 player-days")
    axis.set_title("Pre-specified practitioner review capacity")
    fig.tight_layout()
    figures["alert_capacity"] = fig
    return figures


def _render_report(result: Stage07ProtocolResult) -> str:
    summary = result.summary
    support = result.tables["partition_support"]
    findings = result.tables["leakage_findings"]
    lines = [
        "# Stage 7 - Prospective Protocol and Leakage Audit",
        "",
        "## Automated Status",
        "",
        f"Protocol audit: **{summary['status']}** with `{summary['failure_count']}` failures, "
        f"`{summary['warning_count']}` warnings and `{summary['review_count']}` review findings.",
        "",
        "This stage freezes evaluation rules. It fits no model, creates no predictions, "
        "selects no threshold and inspects no final-test performance.",
        "",
        "## Frozen Primary Contract",
        "",
        "- Three-day episode gap and seven-day future onset target.",
        "- Twenty-eight strictly prior calendar-day burn-in.",
        "- Complete target horizon and exclusion while inside an active episode.",
        "- Same-day wellness, identities, outcomes and future/follow-up fields are prohibited.",
        "- Missingness and robust-baseline availability remain explicit; neither "
        "restricts cohort entry.",
        "",
        "## Chronological Support",
        "",
        "| Partition | Dates | Player-days | Positive days | Represented onsets | Event players |",
        "|---|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['partition']} | {row['start_date']} to {row['end_date']} | "
        f"{row['player_days']} | {row['positive_player_days']} | "
        f"{row['represented_onset_count']} | {row['represented_event_player_count']} |"
        for row in support.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "Seven-day embargoes separate train from validation and validation from test. "
            "The final test partition is locked after this support audit.",
            "",
            "## Leakage Findings",
            "",
            "| Check | Status | Evidence |",
            "|---|---|---|",
        ]
    )
    lines.extend(
        f"| {row['check_id']} | {row['status']} | {row['evidence']} |"
        for row in findings.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Partition support](../figures/partition_player_days.png)",
            "",
            "![Onset support](../figures/partition_onset_support.png)",
            "",
            "![Predictor coverage](../figures/predictor_coverage.png)",
            "",
            "![Rolling-origin support](../figures/rolling_origin_support.png)",
            "",
            "![Unseen-player support](../figures/unseen_player_support.png)",
            "",
            "![Leakage checks](../figures/leakage_check_status.png)",
            "",
            "## Gate",
            "",
            "Project-owner review is required. Stage 8 may consolidate readiness only after "
            "this protocol and its leakage evidence are approved. Modelling remains prohibited.",
        ]
    )
    return "\n".join(lines) + "\n"
