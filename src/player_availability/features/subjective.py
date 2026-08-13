"""End-of-day, past-only subjective features for the player-day cohort."""

from __future__ import annotations

from collections import deque
from datetime import date
from math import sqrt
from typing import Any

import polars as pl

WINDOWS_DAYS = (3, 7, 14, 28)


def build_subjective_player_day_features(
    player_day_labels: pl.DataFrame,
    training_load_daily: pl.DataFrame,
    wellness_daily: pl.DataFrame,
    training_sessions: pl.DataFrame,
) -> pl.DataFrame:
    """Create features using data available on or before each end-of-day cutoff.

    Rolling values include the prediction date because the cutoff is end-of-day. Expanding
    player baselines intentionally exclude that date, so relative-state features cannot
    use the current observation to define its own baseline.
    """
    load_by_day = _rows_by_player_date(training_load_daily, "report_date")
    wellness_by_day = _rows_by_player_date(wellness_daily, "report_date")
    sessions_by_day = _aggregate_sessions(training_sessions)
    output: list[dict[str, object]] = []
    for player_id, player_days in player_day_labels.sort("player_id", "prediction_date").group_by(
        "player_id", maintain_order=True
    ):
        assert isinstance(player_id, tuple)
        player_key = str(player_id[0])
        load_history: deque[tuple[date, float]] = deque()
        session_history: deque[tuple[date, float, float]] = deque()
        wellness_history: dict[str, deque[tuple[date, float]]] = {
            metric: deque() for metric in ("fatigue", "readiness")
        }
        baselines: dict[str, _RunningStats] = {
            metric: _RunningStats() for metric in ("daily_load", "fatigue", "readiness")
        }
        for label in player_days.to_dicts():
            prediction_date = label["prediction_date"]
            assert isinstance(prediction_date, date)
            load = load_by_day.get((player_key, prediction_date), {})
            wellness = wellness_by_day.get((player_key, prediction_date), {})
            session = sessions_by_day.get((player_key, prediction_date), {})
            current_load = _as_float(load.get("daily_load"))
            current_fatigue = _as_float(wellness.get("fatigue"))
            current_readiness = _as_float(wellness.get("readiness"))
            row = dict(label)
            row.update(
                {
                    "feature_version": "subjective_v1",
                    "feature_timestamp": prediction_date,
                    "daily_load": current_load,
                    "fatigue": current_fatigue,
                    "readiness": current_readiness,
                    "wellness_report_present": wellness.get("wellness_report_present", False),
                    "wellness_metric_count": wellness.get("wellness_metric_count", 0),
                    "session_count": session.get("session_count", 0),
                    "session_duration_minutes": session.get("session_duration_minutes", 0.0),
                    "session_srpe": session.get("session_srpe", 0.0),
                }
            )
            _append_if_present(load_history, prediction_date, current_load)
            _append_if_present(
                session_history,
                prediction_date,
                _as_float(row["session_duration_minutes"]),
                _as_float(row["session_srpe"]),
            )
            _append_if_present(wellness_history["fatigue"], prediction_date, current_fatigue)
            _append_if_present(wellness_history["readiness"], prediction_date, current_readiness)
            for window in WINDOWS_DAYS:
                row[f"daily_load_sum_{window}d"] = _window_sum(
                    load_history, prediction_date, window
                )
                row[f"session_duration_sum_{window}d"] = _window_sum(
                    session_history, prediction_date, window, index=1
                )
                row[f"session_srpe_sum_{window}d"] = _window_sum(
                    session_history, prediction_date, window, index=2
                )
                row[f"fatigue_mean_{window}d"] = _window_mean(
                    wellness_history["fatigue"], prediction_date, window
                )
                row[f"readiness_mean_{window}d"] = _window_mean(
                    wellness_history["readiness"], prediction_date, window
                )
            for metric, value in (
                ("daily_load", current_load),
                ("fatigue", current_fatigue),
                ("readiness", current_readiness),
            ):
                row[f"{metric}_baseline_mean_prior"] = baselines[metric].mean
                row[f"{metric}_zscore_prior"] = baselines[metric].zscore(value)
                baselines[metric].add(value)
            output.append(row)
    return pl.DataFrame(output, infer_schema_length=None).sort("player_id", "prediction_date")


class _RunningStats:
    def __init__(self) -> None:
        self.count = 0
        self.total = 0.0
        self.total_squares = 0.0

    @property
    def mean(self) -> float | None:
        return self.total / self.count if self.count else None

    def zscore(self, value: float | None) -> float | None:
        if value is None or self.count < 2:
            return None
        mean = self.total / self.count
        variance = (self.total_squares / self.count) - mean**2
        return (value - mean) / sqrt(variance) if variance > 0 else None

    def add(self, value: float | None) -> None:
        if value is not None:
            self.count += 1
            self.total += value
            self.total_squares += value**2


def _rows_by_player_date(
    frame: pl.DataFrame, date_column: str
) -> dict[tuple[str, date], dict[str, Any]]:
    return {
        (str(row["player_id"]), row[date_column]): row
        for row in frame.to_dicts()
        if isinstance(row[date_column], date)
    }


def _aggregate_sessions(sessions: pl.DataFrame) -> dict[tuple[str, date], dict[str, float | int]]:
    aggregate = sessions.group_by("player_id", "session_date").agg(
        pl.len().alias("session_count"),
        pl.sum("duration_minutes").alias("session_duration_minutes"),
        pl.sum("srpe").alias("session_srpe"),
    )
    return {
        (str(row["player_id"]), row["session_date"]): row
        for row in aggregate.to_dicts()
        if isinstance(row["session_date"], date)
    }


def _append_if_present(history: deque[Any], prediction_date: date, *values: float | None) -> None:
    if all(value is not None for value in values):
        history.append((prediction_date, *values))


def _window_sum(
    history: deque[Any], prediction_date: date, window: int, *, index: int = 1
) -> float:
    return sum(
        float(item[index]) for item in history if 0 <= (prediction_date - item[0]).days < window
    )


def _window_mean(
    history: deque[tuple[date, float]], prediction_date: date, window: int
) -> float | None:
    values = [value for day, value in history if 0 <= (prediction_date - day).days < window]
    return sum(values) / len(values) if values else None


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None
