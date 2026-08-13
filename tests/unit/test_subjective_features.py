from __future__ import annotations

from datetime import date

import polars as pl

from player_availability.features import build_subjective_player_day_features


def test_features_do_not_change_when_future_data_is_appended() -> None:
    labels = _labels(3)
    training_load = _load(3)
    wellness = _wellness(3)
    sessions = _sessions(3)
    baseline = build_subjective_player_day_features(
        labels.head(2), training_load.head(2), wellness.head(2), sessions.head(2)
    )
    extended = build_subjective_player_day_features(labels, training_load, wellness, sessions).head(
        2
    )

    assert (
        baseline.select(_feature_columns(baseline)).to_dicts()
        == extended.select(_feature_columns(extended)).to_dicts()
    )


def test_player_baseline_excludes_current_value() -> None:
    features = build_subjective_player_day_features(
        _labels(3), _load(3), _wellness(3), _sessions(3)
    )

    third_day = features.row(2, named=True)
    assert third_day["daily_load_baseline_mean_prior"] == 15.0
    assert third_day["daily_load_zscore_prior"] > 0


def _labels(days: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player_id": ["TeamA-1"] * days,
            "team_id": ["TeamA"] * days,
            "prediction_date": [date(2021, 1, day) for day in range(1, days + 1)],
            "prediction_cutoff": ["end_of_calendar_day"] * days,
        }
    )


def _load(days: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player_id": ["TeamA-1"] * days,
            "report_date": [date(2021, 1, day) for day in range(1, days + 1)],
            "daily_load": [10.0 * day for day in range(1, days + 1)],
        }
    )


def _wellness(days: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player_id": ["TeamA-1"] * days,
            "report_date": [date(2021, 1, day) for day in range(1, days + 1)],
            "fatigue": [2.0] * days,
            "readiness": [4.0] * days,
            "wellness_report_present": [True] * days,
            "wellness_metric_count": [7] * days,
        }
    )


def _sessions(days: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player_id": ["TeamA-1"] * days,
            "session_date": [date(2021, 1, day) for day in range(1, days + 1)],
            "duration_minutes": [60.0] * days,
            "srpe": [300.0] * days,
        }
    )


def _feature_columns(frame: pl.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in {"prediction_date"}]
