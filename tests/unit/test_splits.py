from __future__ import annotations

from datetime import date, timedelta

import polars as pl
import pytest

from player_availability.modelling import (
    PREDICTOR_ALLOWLIST,
    assign_primary_chronological_split,
    build_primary_split_manifest,
    validate_predictor_allowlist,
)


def test_primary_split_freezes_expected_dates_and_embargoes() -> None:
    manifest = build_primary_split_manifest(_features())

    assert manifest.train_start_date == "2020-01-28"
    assert manifest.train_end_date == "2021-03-16"
    assert manifest.validation_start_date == "2021-03-31"
    assert manifest.validation_end_date == "2021-08-15"
    assert manifest.test_start_date == "2021-08-30"
    assert manifest.test_end_date == "2021-12-17"
    assert manifest.partition_row_counts["embargo_train_validation"] == 14
    assert manifest.partition_row_counts["embargo_validation_test"] == 14


def test_assigned_partitions_do_not_cross_the_fourteen_day_embargo() -> None:
    assigned, manifest = assign_primary_chronological_split(_features())

    train_end = (
        assigned.filter(pl.col("chronological_partition") == "train")
        .get_column("prediction_date")
        .max()
    )
    validation_start = (
        assigned.filter(pl.col("chronological_partition") == "validation")
        .get_column("prediction_date")
        .min()
    )
    test_start = (
        assigned.filter(pl.col("chronological_partition") == "test")
        .get_column("prediction_date")
        .min()
    )
    validation_end = (
        assigned.filter(pl.col("chronological_partition") == "validation")
        .get_column("prediction_date")
        .max()
    )

    assert isinstance(train_end, date)
    assert isinstance(validation_start, date)
    assert isinstance(validation_end, date)
    assert isinstance(test_start, date)
    assert (validation_start - train_end).days == manifest.embargo_days + 1
    assert (test_start - validation_end).days == manifest.embargo_days + 1
    assert assigned.filter(pl.col("modelling_eligible_14d")).height == 662


def test_predictor_contract_rejects_missing_column() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_predictor_allowlist(_features().drop(PREDICTOR_ALLOWLIST[0]))


def _features() -> pl.DataFrame:
    start = date(2020, 1, 1)
    end = date(2021, 12, 31)
    days = (end - start).days + 1
    values: dict[str, list[object]] = {
        "player_id": ["TeamA-1"] * days,
        "prediction_date": [start + timedelta(days=index) for index in range(days)],
        "label_complete_14d": [index <= days - 15 for index in range(days)],
        "eligible_new_onset_14d": [True] * days,
    }
    for column in PREDICTOR_ALLOWLIST:
        values[column] = [1.0] * days
    return pl.DataFrame(values)
