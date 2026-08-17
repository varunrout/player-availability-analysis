"""EXP-018 explanation stability for the raw F1 champion (`DEC-060`).

Determines whether the champion's explanation is stable enough to display to a
practitioner, and which predictors may be shown as drivers. F1 is a nine-predictor
logistic model, so attribution is exact rather than approximated: a player-day's
predicted log-odds is exactly the intercept plus the sum of each transformed feature's
standardised value times its fitted coefficient (`EXPL-03` verifies this against the
model's own decision function). Where a predictor's imputer missingness indicator is
fitted (`SimpleImputer(add_indicator=True)`), its contribution is folded into that
predictor's own total, since the indicator only ever fires for that predictor's own
missing values and is not a separate predictor in the frozen F1 contract.

Coefficient sign, magnitude and rank stability are measured across every estimable
rolling-origin fold and every estimable leave-one-player-out fold on the nine raw
predictor value coefficients (`DEC-060`). "Flagged player-day" for the contributor-set
comparison is a player-day with an actual represented positive label (`target == 1`):
this is the one flagging criterion available identically under both fold structures,
since a leave-one-player-out fold holds out a single player's full history and has no
team-day group to rank within, unlike a rolling-origin fold. For each flagged player-day
that falls within an estimable window under both fold types, the top-3 positive
contributor sets from its rolling-origin model and its leave-one-player-out model are
compared by Jaccard overlap, since that is the only pairing where two different fitted
models ever score the same player-day.

No final-test row is read or scored. No model is refitted outside the existing fold
structure; attribution is read from the coefficients each fold already fits for its own
evaluation.
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
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from player_availability.analysis.stage_00_data_audit import SOURCE_PREFIX
from player_availability.analysis.stage_07_prospective_protocol import (
    ROLLING_FOLDS,
    run_stage_07_prospective_protocol,
)
from player_availability.modelling.m1_logistic import M1F1Config, load_m1_f1_config
from player_availability.modelling.preprocessing import (
    F1_FEATURES,
    build_feature_pipeline,
    transformed_feature_names,
)

DEVELOPMENT_CUTOFF = date(2021, 6, 23)
KEYS = ("player_id", "team_id", "prediction_date")


@dataclass(frozen=True, slots=True)
class Exp018ExplanationConfig:
    """Frozen EXP-018 explanation-stability configuration."""

    base_config: M1F1Config
    selected_regularisation_c: float
    posthoc_calibration_selection: bool
    final_test_access: bool


@dataclass(frozen=True, slots=True)
class Exp018ExplanationResult:
    """Explanation-stability tables and metadata."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]
    source_metadata: dict[str, Any]


def load_exp_018_config(path: Path) -> Exp018ExplanationConfig:
    """Load and validate the frozen EXP-018 explanation-stability specification."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("EXP-018 configuration must be a mapping")
    base_config = load_m1_f1_config(path.parent / str(raw["base_config"]))
    config = Exp018ExplanationConfig(
        base_config=base_config,
        selected_regularisation_c=float(raw["selected_regularisation_c"]),
        posthoc_calibration_selection=bool(raw["posthoc_calibration_selection"]),
        final_test_access=bool(raw["final_test_access"]),
    )
    if config.selected_regularisation_c != 0.001:
        raise ValueError("EXP-018 uses the frozen F1 regularisation C=0.001; no retuning")
    if config.posthoc_calibration_selection or config.final_test_access:
        raise ValueError("EXP-018 selects no calibrator and accesses no final test")
    return config


def load_exp_018_from_gcp(
    *, project_id: str, data_bucket: str, config: Exp018ExplanationConfig
) -> Exp018ExplanationResult:
    """Load compact canonical products once and execute the explanation-stability audit."""
    client = Client(project=project_id)
    bucket = client.bucket(data_bucket)
    paths = {
        "features": f"gold/{SOURCE_PREFIX}/player_day_features.parquet",
        "episodes": f"silver/{SOURCE_PREFIX}/injury_episodes.parquet",
    }
    blobs = {name: bucket.blob(path).download_as_bytes() for name, path in paths.items()}
    result = run_exp_018_explanation(
        features=pl.read_parquet(BytesIO(blobs["features"])),
        episodes=pl.read_parquet(BytesIO(blobs["episodes"])),
        config=config,
    )
    return Exp018ExplanationResult(
        tables=result.tables,
        summary=result.summary,
        source_metadata={
            "source_paths": paths,
            "source_sha256": {
                name: hashlib.sha256(value).hexdigest() for name, value in blobs.items()
            },
        },
    )


def run_exp_018_explanation(
    *, features: pl.DataFrame, episodes: pl.DataFrame, config: Exp018ExplanationConfig
) -> Exp018ExplanationResult:
    """Measure F1 coefficient and top-contributor stability across estimable folds."""
    cohort = _primary_cohort(features, episodes)
    development = cohort.filter(pl.col("prediction_date") <= DEVELOPMENT_CUTOFF)

    rolling_fits, rolling_dropped = _rolling_fold_fits(cohort, config)
    lopo_fits, lopo_dropped = _lopo_fold_fits(development, config)

    per_fold_coefficients = _per_fold_coefficient_table(rolling_fits, lopo_fits)
    stability = _coefficient_stability(per_fold_coefficients)
    exactness = _exactness_check(rolling_fits, lopo_fits)
    overlap, overlap_summary = _flagged_contributor_overlap(rolling_fits, lopo_fits, config)

    findings = _explanation_findings(
        per_fold_coefficients=per_fold_coefficients,
        stability=stability,
        exactness=exactness,
        overlap_summary=overlap_summary,
    )
    failures = findings.filter(pl.col("status") == "FAIL").height
    unstable_predictors = stability.filter(~pl.col("constant_sign"))["predictor"].to_list()
    stop_condition_triggered = len(unstable_predictors) > len(F1_FEATURES) // 2
    summary = {
        "experiment_id": "EXP-018",
        "model_id": "M1-F1",
        "status": "PASS" if failures == 0 else "FAIL",
        "decision_gate": "PROJECT_OWNER_DRIVER_DISPLAY_REVIEW",
        "flagging_criterion": "actual_represented_positive_label",
        "predictor_count": len(F1_FEATURES),
        "rolling_estimable_fold_count": len(rolling_fits),
        "rolling_dropped_fold_count": len(rolling_dropped),
        "lopo_estimable_fold_count": len(lopo_fits),
        "lopo_dropped_fold_count": len(lopo_dropped),
        "unstable_sign_predictor_count": len(unstable_predictors),
        "unstable_sign_predictors": sorted(unstable_predictors),
        "stop_condition_triggered": stop_condition_triggered,
        "flagged_player_day_overlap_count": overlap.height,
        "posthoc_calibration_selected": False,
        "final_test_rows_evaluated": 0,
        "final_test_predictions_created": False,
        "final_test_performance_accessed": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    tables = {
        "dataset_manifest": _dataset_manifest(config),
        "per_fold_coefficients": per_fold_coefficients,
        "coefficient_stability": stability,
        "dropped_fold_register": _dropped_register(rolling_dropped, lopo_dropped),
        "exactness_check": exactness,
        "flagged_contributor_overlap": overlap,
        "flagged_contributor_overlap_summary": overlap_summary,
        "explanation_findings": findings,
    }
    return Exp018ExplanationResult(tables=tables, summary=summary, source_metadata={})


@dataclass(frozen=True, slots=True)
class _FoldFit:
    fold_type: str
    fold_id: str
    pipeline: Pipeline
    heldout: pl.DataFrame


def _primary_cohort(features: pl.DataFrame, episodes: pl.DataFrame) -> pl.DataFrame:
    protocol = run_stage_07_prospective_protocol(features=features, episodes=episodes)
    return protocol.tables["_primary_cohort"]


def _rolling_fold_fits(
    cohort: pl.DataFrame, config: Exp018ExplanationConfig
) -> tuple[list[_FoldFit], list[dict[str, Any]]]:
    target = config.base_config.target
    fits: list[_FoldFit] = []
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
                    "fold_type": "rolling_origin",
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
        fits.append(_FoldFit("rolling_origin", fold_id, pipeline, heldout))
    return fits, dropped


def _lopo_fold_fits(
    development: pl.DataFrame, config: Exp018ExplanationConfig
) -> tuple[list[_FoldFit], list[dict[str, Any]]]:
    target = config.base_config.target
    fits: list[_FoldFit] = []
    dropped: list[dict[str, Any]] = []
    for player_id in development["player_id"].unique().sort():
        train = development.filter(pl.col("player_id") != player_id)
        heldout = development.filter(pl.col("player_id") == player_id)
        train_targets = _targets(train, target)
        if len(set(train_targets)) < 2:
            dropped.append(
                {
                    "fold_type": "leave_one_player_out",
                    "fold_id": str(player_id),
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
        fits.append(_FoldFit("leave_one_player_out", str(player_id), pipeline, heldout))
    return fits, dropped


def _predictor_coefficients(pipeline: Pipeline) -> dict[str, tuple[float, float | None]]:
    names = transformed_feature_names(pipeline, F1_FEATURES)
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    value_coefficient = {
        name: float(coef)
        for name, coef in zip(names, coefficients, strict=True)
        if not name.startswith("missingindicator_")
    }
    indicator_coefficient = {
        name.removeprefix("missingindicator_"): float(coef)
        for name, coef in zip(names, coefficients, strict=True)
        if name.startswith("missingindicator_")
    }
    return {
        predictor: (value_coefficient[predictor], indicator_coefficient.get(predictor))
        for predictor in F1_FEATURES
    }


def _row_contributions(pipeline: Pipeline, row: pl.DataFrame) -> dict[str, float]:
    names = transformed_feature_names(pipeline, F1_FEATURES)
    transformed = pipeline[:-1].transform(_matrix(row, F1_FEATURES))
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    by_transformed_name = {
        name: float(transformed[0, index] * coefficients[index]) for index, name in enumerate(names)
    }
    contributions = {
        predictor: by_transformed_name.get(predictor, 0.0) for predictor in F1_FEATURES
    }
    for name, value in by_transformed_name.items():
        if name.startswith("missingindicator_"):
            contributions[name.removeprefix("missingindicator_")] += value
    return contributions


def _per_fold_coefficient_table(
    rolling_fits: list[_FoldFit], lopo_fits: list[_FoldFit]
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for fits in (rolling_fits, lopo_fits):
        for fit in fits:
            coefficients = _predictor_coefficients(fit.pipeline)
            magnitudes = {predictor: abs(value) for predictor, (value, _) in coefficients.items()}
            ranked = sorted(magnitudes, key=lambda predictor: magnitudes[predictor], reverse=True)
            ranks = {predictor: position + 1 for position, predictor in enumerate(ranked)}
            for predictor, (value_coefficient, indicator_coefficient) in coefficients.items():
                rows.append(
                    {
                        "fold_type": fit.fold_type,
                        "fold_id": fit.fold_id,
                        "predictor": predictor,
                        "value_coefficient": value_coefficient,
                        "indicator_coefficient": indicator_coefficient,
                        "abs_value_coefficient": magnitudes[predictor],
                        "magnitude_rank": ranks[predictor],
                    }
                )
    return pl.DataFrame(rows)


def _coefficient_stability(per_fold_coefficients: pl.DataFrame) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for predictor in F1_FEATURES:
        table = per_fold_coefficients.filter(pl.col("predictor") == predictor)
        signs = {
            1 if value > 0 else (-1 if value < 0 else 0) for value in table["value_coefficient"]
        }
        constant_sign = len(signs) == 1
        magnitudes = table["abs_value_coefficient"].sort()
        rows.append(
            {
                "predictor": predictor,
                "estimable_fold_count": table.height,
                "constant_sign": constant_sign,
                "sign_when_constant": (
                    next(iter(signs)) if constant_sign and next(iter(signs)) != 0 else None
                ),
                "min_abs_coefficient": cast(float, magnitudes.min()) if table.height else None,
                "max_abs_coefficient": cast(float, magnitudes.max()) if table.height else None,
                "coefficient_iqr": (
                    cast(float, magnitudes.quantile(0.75, "linear"))
                    - cast(float, magnitudes.quantile(0.25, "linear"))
                    if table.height
                    else None
                ),
                "mean_magnitude_rank": (
                    cast(float, table["magnitude_rank"].mean()) if table.height else None
                ),
                "magnitude_rank_range": (
                    cast(int, table["magnitude_rank"].max())
                    - cast(int, table["magnitude_rank"].min())
                    if table.height
                    else None
                ),
            }
        )
    return pl.DataFrame(rows)


def _exactness_check(rolling_fits: list[_FoldFit], lopo_fits: list[_FoldFit]) -> pl.DataFrame:
    """Verify summed contributions plus intercept equal the model's own logit (`EXPL-03`)."""
    rows: list[dict[str, Any]] = []
    for fits in (rolling_fits, lopo_fits):
        for fit in fits[:1]:
            sample = fit.heldout.head(min(10, fit.heldout.height))
            intercept = float(fit.pipeline.named_steps["classifier"].intercept_[0])
            for row in sample.iter_rows(named=True):
                single = pl.DataFrame([row]).select(F1_FEATURES)
                contributions = _row_contributions(fit.pipeline, single)
                reconstructed = intercept + sum(contributions.values())
                true_logit = float(fit.pipeline.decision_function(_matrix(single, F1_FEATURES))[0])
                rows.append(
                    {
                        "fold_type": fit.fold_type,
                        "fold_id": fit.fold_id,
                        "reconstructed_logit": reconstructed,
                        "true_logit": true_logit,
                        "absolute_error": abs(reconstructed - true_logit),
                    }
                )
    return pl.DataFrame(rows)


def _flagged_contributor_overlap(
    rolling_fits: list[_FoldFit], lopo_fits: list[_FoldFit], config: Exp018ExplanationConfig
) -> tuple[pl.DataFrame, pl.DataFrame]:
    target = config.base_config.target
    rolling_contributors = _flagged_contributor_sets(rolling_fits, target)
    lopo_contributors = _flagged_contributor_sets(lopo_fits, target)
    rows: list[dict[str, Any]] = []
    for key, rolling_set in rolling_contributors.items():
        lopo_set = lopo_contributors.get(key)
        if lopo_set is None:
            continue
        union = rolling_set | lopo_set
        intersection = rolling_set & lopo_set
        jaccard = len(intersection) / len(union) if union else None
        player_id, prediction_date = key
        rows.append(
            {
                "player_id": player_id,
                "prediction_date": prediction_date,
                "rolling_top3_contributors": ", ".join(sorted(rolling_set)),
                "lopo_top3_contributors": ", ".join(sorted(lopo_set)),
                "jaccard_overlap": jaccard,
            }
        )
    overlap = pl.DataFrame(rows)
    if overlap.height:
        summary = pl.DataFrame(
            [
                {
                    "flagged_player_day_count": overlap.height,
                    "mean_jaccard_overlap": cast(float, overlap["jaccard_overlap"].mean()),
                    "min_jaccard_overlap": cast(float, overlap["jaccard_overlap"].min()),
                    "max_jaccard_overlap": cast(float, overlap["jaccard_overlap"].max()),
                }
            ]
        )
    else:
        summary = pl.DataFrame(
            [
                {
                    "flagged_player_day_count": 0,
                    "mean_jaccard_overlap": None,
                    "min_jaccard_overlap": None,
                    "max_jaccard_overlap": None,
                }
            ]
        )
    return overlap, summary


def _flagged_contributor_sets(
    fits: list[_FoldFit], target: str
) -> dict[tuple[str, date], frozenset[str]]:
    result: dict[tuple[str, date], frozenset[str]] = {}
    for fit in fits:
        flagged = fit.heldout.filter(pl.col(target) == 1)
        for row in flagged.iter_rows(named=True):
            single = pl.DataFrame([row]).select(F1_FEATURES)
            contributions = _row_contributions(fit.pipeline, single)
            positive = sorted(
                ((name, value) for name, value in contributions.items() if value > 0),
                key=lambda pair: pair[1],
                reverse=True,
            )
            top3 = frozenset(name for name, _ in positive[:3])
            key = (str(row["player_id"]), row["prediction_date"])
            result[key] = top3
    return result


def _explanation_findings(
    *,
    per_fold_coefficients: pl.DataFrame,
    stability: pl.DataFrame,
    exactness: pl.DataFrame,
    overlap_summary: pl.DataFrame,
) -> pl.DataFrame:
    unstable = stability.filter(~pl.col("constant_sign"))["predictor"].to_list()
    exactness_ok = exactness.height > 0 and cast(float, exactness["absolute_error"].max()) < 1e-8
    stability_supported = bool((stability["estimable_fold_count"] > 0).all())
    return pl.DataFrame(
        [
            {
                "finding_id": "EXPL-01",
                "status": "PASS",
                "domain": "final_test_isolation",
                "evidence": "zero final-test predictions or performance metrics produced",
            },
            {
                "finding_id": "EXPL-02",
                "status": "PASS",
                "domain": "standardisation_scope",
                "evidence": (
                    "each fold's imputer and scaler are fitted on that fold's own training "
                    "portion only, matching the frozen F1 pipeline"
                ),
            },
            {
                "finding_id": "EXPL-03",
                "status": "PASS" if exactness_ok else "FAIL",
                "domain": "attribution_exactness",
                "evidence": (
                    f"summed per-predictor contributions plus intercept reproduce the model's "
                    f"own logit to within "
                    f"{cast(float, exactness['absolute_error'].max()):.2e}"
                    if exactness.height
                    else "no sampled rows available"
                ),
            },
            {
                "finding_id": "EXPL-04",
                "status": "PASS" if stability_supported else "FAIL",
                "domain": "stability_support_reporting",
                "evidence": (
                    f"every stability figure states its estimable-fold count "
                    f"({int(per_fold_coefficients['fold_id'].n_unique())} distinct fold fits)"
                ),
            },
            {
                "finding_id": "EXPL-05",
                "status": "PASS",
                "domain": "sign_unstable_disclosure",
                "evidence": (
                    f"{len(unstable)} of {stability.height} predictors have unstable sign: "
                    f"{', '.join(sorted(unstable)) if unstable else 'none'}"
                ),
            },
        ]
    )


def _dataset_manifest(config: Exp018ExplanationConfig) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": "EXP-018",
                "model_id": "M1-F1",
                "data_version": config.base_config.data_version,
                "target": config.base_config.target,
                "development_cutoff": DEVELOPMENT_CUTOFF,
                "selected_regularisation_c": config.selected_regularisation_c,
                "posthoc_calibration_selection": config.posthoc_calibration_selection,
                "final_test_access": config.final_test_access,
            }
        ]
    )


def _dropped_register(
    rolling_dropped: list[dict[str, Any]], lopo_dropped: list[dict[str, Any]]
) -> pl.DataFrame:
    combined = rolling_dropped + lopo_dropped
    if not combined:
        return pl.DataFrame(
            schema={
                "fold_type": pl.Utf8,
                "fold_id": pl.Utf8,
                "reason": pl.Utf8,
                "training_positive_days": pl.Int64,
                "heldout_player_days": pl.Int64,
            }
        )
    return pl.DataFrame(combined)


def _targets(frame: pl.DataFrame, target: str) -> list[int]:
    return [int(value) for value in frame[target]]


def _matrix(frame: pl.DataFrame, feature_names: tuple[str, ...]) -> Any:
    return frame.select(feature_names).to_numpy()


def build_exp_018_figures(result: Exp018ExplanationResult) -> dict[str, Figure]:
    """Build retained explanation-stability development figures."""
    stability = result.tables["coefficient_stability"].sort("mean_magnitude_rank")
    per_fold = result.tables["per_fold_coefficients"]
    overlap = result.tables["flagged_contributor_overlap"]
    figures: dict[str, Figure] = {}

    fig, axis = plt.subplots(figsize=(8, 5))
    colours = ["#59A14F" if value else "#E45756" for value in stability["constant_sign"]]
    axis.barh(stability["predictor"], stability["max_abs_coefficient"], color=colours)
    axis.set(
        title="Predictor coefficient magnitude (green = constant sign)",
        xlabel="Max |standardised coefficient| across estimable folds",
    )
    figures["coefficient_magnitude_and_sign_stability"] = fig

    fig, axis = plt.subplots(figsize=(8, 5))
    for predictor in stability["predictor"]:
        table = per_fold.filter(pl.col("predictor") == predictor)
        axis.scatter([predictor] * table.height, table["value_coefficient"], alpha=0.6)
    axis.axhline(0, color="#555555", linewidth=1)
    axis.tick_params(axis="x", rotation=45)
    axis.set(title="Per-fold coefficient spread by predictor", ylabel="Standardised coefficient")
    figures["per_fold_coefficient_spread"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.bar(stability["predictor"], stability["magnitude_rank_range"], color="#4C78A8")
    axis.tick_params(axis="x", rotation=45)
    axis.set(title="Magnitude rank instability", ylabel="Rank range across estimable folds")
    figures["magnitude_rank_instability"] = fig

    fig, axis = plt.subplots(figsize=(7, 4.5))
    if overlap.height:
        axis.hist(overlap["jaccard_overlap"], bins=4, range=(0, 1), color="#F58518")
    axis.set(
        title="Rolling-vs-LOPO top-3 contributor overlap on flagged days",
        xlabel="Jaccard overlap",
        ylabel="Flagged player-days",
    )
    figures["contributor_overlap_distribution"] = fig
    return figures


def write_exp_018_outputs(result: Exp018ExplanationResult, output_root: Path) -> None:
    """Persist canonical EXP-018 explanation-stability development artifacts."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_exp_018_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    metadata = {"summary": result.summary, **result.source_metadata}
    (directories["metadata"] / "exp_018_explanation_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "EXP_018_EXPLANATION_REPORT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _render_report(result: Exp018ExplanationResult) -> str:
    stability = result.tables["coefficient_stability"]
    overlap_summary = result.tables["flagged_contributor_overlap_summary"].row(0, named=True)
    findings = result.tables["explanation_findings"]
    summary = result.summary
    lines = [
        "# EXP-018 - Explanation Stability Report",
        "",
        "## Automated Status",
        "",
        f"Development run: **{summary['status']}**. Project-owner driver-display review required.",
        "",
        (
            "F1's attribution is exact: a player-day's predicted log-odds equals its intercept "
            "plus the sum of each transformed feature's standardised value times its fitted "
            "coefficient. Coefficient sign, magnitude and rank are measured across every "
            "estimable rolling-origin and leave-one-player-out fold. No final-test row is read "
            "or scored, and no model is refitted outside the existing fold structure."
        ),
        "",
    ]
    if summary["stop_condition_triggered"]:
        lines.extend(
            [
                "## STOP CONDITION TRIGGERED",
                "",
                (
                    f"A majority of the nine predictors ({summary['unstable_sign_predictor_count']}"
                    f"/{summary['predictor_count']}) show unstable sign across estimable folds: "
                    f"{', '.join(summary['unstable_sign_predictors'])}. Per the pre-registered "
                    "stop condition, this is reported to the project owner rather than proceeding "
                    "to a driver-display recommendation."
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Coefficient Stability",
            "",
            "| Predictor | Folds | Sign | Min |coef| | Max |coef| | IQR | Mean rank | Rank range |",
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in stability.iter_rows(named=True):
        lines.append(
            f"| {row['predictor']} | {row['estimable_fold_count']} | "
            f"{'yes' if row['constant_sign'] else 'NO'} | "
            f"{_format(row['min_abs_coefficient'])} | {_format(row['max_abs_coefficient'])} | "
            f"{_format(row['coefficient_iqr'])} | {_format(row['mean_magnitude_rank'])} | "
            f"{row['magnitude_rank_range']} |"
        )
    lines.extend(
        [
            "",
            "## Flagged-Player-Day Contributor Overlap",
            "",
            (
                f"Flagged: {overlap_summary['flagged_player_day_count']} player-days with an "
                "actual represented positive label, evaluable under both a rolling-origin fold "
                "and a leave-one-player-out fold. Mean top-3 positive-contributor Jaccard "
                f"overlap: {_format(overlap_summary['mean_jaccard_overlap'])} "
                f"(range {_format(overlap_summary['min_jaccard_overlap'])} to "
                f"{_format(overlap_summary['max_jaccard_overlap'])})."
            ),
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
                "Predictors with constant sign across all estimable folds are eligible for "
                "display as drivers in the dashboard. Predictors with unstable sign are not, "
                "and are recorded as such. Low attribution stability is a valid finding and "
                "constrains the product rather than invalidating the model."
            ),
            "",
            "## Gate",
            "",
            (
                "The project owner selects which stable predictors are displayed as drivers. "
                "If the stop condition triggers, no driver-display recommendation is made here."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"
