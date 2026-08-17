"""Shared classification, calibration and operational evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, cast

import polars as pl
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

EPSILON = 1e-12


def classification_metrics(
    targets: Sequence[int], probabilities: Sequence[float]
) -> dict[str, float | None]:
    """Calculate probability and ranking metrics with sparse-support guards."""
    if len(targets) != len(probabilities) or not targets:
        raise ValueError("Targets and probabilities must be non-empty and aligned")
    positive_count = sum(targets)
    negative_count = len(targets) - positive_count
    return {
        "player_days": float(len(targets)),
        "positive_days": float(positive_count),
        "prevalence": positive_count / len(targets),
        "brier_score": float(brier_score_loss(targets, probabilities)),
        "log_loss": float(log_loss(targets, probabilities, labels=[0, 1])),
        "average_precision": (
            float(average_precision_score(targets, probabilities)) if positive_count else None
        ),
        "roc_auc": (
            float(roc_auc_score(targets, probabilities))
            if positive_count and negative_count
            else None
        ),
    }


def calibration_diagnostics(
    targets: Sequence[int], probabilities: Sequence[float]
) -> dict[str, float | None]:
    """Estimate raw calibration-in-the-large and logistic intercept/slope diagnostics."""
    observed_rate = sum(targets) / len(targets)
    mean_prediction = sum(probabilities) / len(probabilities)
    if not sum(targets) or sum(targets) == len(targets):
        return {
            "observed_rate": observed_rate,
            "mean_prediction": mean_prediction,
            "mean_calibration_error": mean_prediction - observed_rate,
            "calibration_intercept": None,
            "calibration_slope": None,
        }
    logits = [
        [
            math.log(
                min(max(value, EPSILON), 1.0 - EPSILON)
                / (1.0 - min(max(value, EPSILON), 1.0 - EPSILON))
            )
        ]
        for value in probabilities
    ]
    diagnostic = LogisticRegression(C=math.inf, solver="lbfgs", max_iter=5000)
    diagnostic.fit(logits, targets)
    return {
        "observed_rate": observed_rate,
        "mean_prediction": mean_prediction,
        "mean_calibration_error": mean_prediction - observed_rate,
        "calibration_intercept": float(diagnostic.intercept_[0]),
        "calibration_slope": float(diagnostic.coef_[0][0]),
    }


def reliability_table(predictions: pl.DataFrame, *, target: str, bins: int) -> pl.DataFrame:
    """Create equal-count reliability bins without learning a calibrator."""
    ordered = predictions.sort("predicted_probability").with_row_index("rank")
    return (
        ordered.with_columns(
            ((pl.col("rank") * bins / ordered.height).floor().clip(upper_bound=bins - 1))
            .cast(pl.Int64)
            .alias("reliability_bin")
        )
        .group_by("reliability_bin")
        .agg(
            pl.len().alias("player_days"),
            pl.col(target).sum().alias("positive_days"),
            pl.col("predicted_probability").min().alias("minimum_prediction"),
            pl.col("predicted_probability").max().alias("maximum_prediction"),
            pl.col("predicted_probability").mean().alias("mean_prediction"),
            pl.col(target).mean().alias("observed_rate"),
        )
        .sort("reliability_bin")
    )


def alert_and_event_tables(
    *,
    predictions: pl.DataFrame,
    episodes: pl.DataFrame,
    target: str,
    horizon_days: int,
    review_rates: Sequence[float],
    model_id: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Evaluate exact player-day review budgets and represented onset capture."""
    alert_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for rate in review_rates:
        alert_count = max(1, math.ceil(predictions.height * rate))
        selected = predictions.sort(
            ["predicted_probability", "prediction_date", "player_id"],
            descending=[True, False, False],
        ).head(alert_count)
        events = _event_capture(
            selected=selected,
            validation=predictions,
            episodes=episodes,
            horizon_days=horizon_days,
            model_id=model_id,
            review_rate=rate,
        )
        event_rows.extend(events)
        captured = sum(int(row["captured"]) for row in events)
        positive_alerts = int(selected[target].sum())
        false_alerts = alert_count - positive_alerts
        alert_rows.append(
            {
                "model_id": model_id,
                "review_rate": rate,
                "eligible_player_days": predictions.height,
                "alert_count": alert_count,
                "alerts_per_100_player_days": 100 * alert_count / predictions.height,
                "positive_alert_days": positive_alerts,
                "represented_onsets": len(events),
                "captured_onsets": captured,
                "event_capture_rate": captured / len(events) if events else None,
                "false_alerts_per_captured_onset": (false_alerts / captured if captured else None),
            }
        )
    return pl.DataFrame(alert_rows), pl.DataFrame(event_rows)


def top_n_per_team_day_alert_and_event_tables(
    *,
    predictions: pl.DataFrame,
    episodes: pl.DataFrame,
    target: str,
    horizon_days: int,
    top_n_values: Sequence[int],
    model_id: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Evaluate top-N-per-team-day review budgets and represented onset capture (`DEC-060`).

    Ranking and selection happen within each team-day group, never globally, since the
    cohort holds two squads and a global ranking could place every alert in one of them.
    Ties are broken deterministically: predicted probability descending, then `player_id`
    ascending. `alerts_per_100_player_days` is normalised against the same pooled
    player-day count used by the percentile view, so both views are directly comparable.
    """
    alert_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    ranked = predictions.sort(
        ["team_id", "prediction_date", "predicted_probability", "player_id"],
        descending=[False, False, True, False],
    ).with_columns(pl.int_range(pl.len()).over(["team_id", "prediction_date"]).alias("_rank"))
    for n in top_n_values:
        selected = ranked.filter(pl.col("_rank") < n).drop("_rank")
        events = _event_capture(
            selected=selected,
            validation=predictions,
            episodes=episodes,
            horizon_days=horizon_days,
            model_id=model_id,
            review_rate=float(n),
        )
        for row in events:
            row["top_n"] = n
            del row["review_rate"]
        event_rows.extend(events)
        captured = sum(int(row["captured"]) for row in events)
        positive_alerts = int(selected[target].sum())
        alert_count = selected.height
        false_alerts = alert_count - positive_alerts
        alert_rows.append(
            {
                "model_id": model_id,
                "top_n": n,
                "eligible_player_days": predictions.height,
                "alert_count": alert_count,
                "alerts_per_100_player_days": 100 * alert_count / predictions.height,
                "positive_alert_days": positive_alerts,
                "represented_onsets": len(events),
                "captured_onsets": captured,
                "event_capture_rate": captured / len(events) if events else None,
                "false_alerts_per_captured_onset": (false_alerts / captured if captured else None),
            }
        )
    return pl.DataFrame(alert_rows), pl.DataFrame(event_rows)


def _event_capture(
    *,
    selected: pl.DataFrame,
    validation: pl.DataFrame,
    episodes: pl.DataFrame,
    horizon_days: int,
    model_id: str,
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
                validation_end + timedelta(days=horizon_days),
                closed="both",
            )
        )
    )
    validation_keys = set(validation.select("player_id", "prediction_date").iter_rows())
    selected_keys = set(selected.select("player_id", "prediction_date").iter_rows())
    rows: list[dict[str, Any]] = []
    for onset in onsets.iter_rows(named=True):
        onset_date = cast(date, onset["episode_start"])
        player_id = str(onset["player_id"])
        candidate_dates = [
            onset_date - timedelta(days=lead)
            for lead in range(1, horizon_days + 1)
            if (player_id, onset_date - timedelta(days=lead)) in validation_keys
        ]
        if not candidate_dates:
            continue
        alert_dates = [day for day in candidate_dates if (player_id, day) in selected_keys]
        lead_times = [(onset_date - day).days for day in alert_dates]
        rows.append(
            {
                "model_id": model_id,
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
