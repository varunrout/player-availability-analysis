from __future__ import annotations

import pytest

from player_availability.quality import DataContract, validate_records


def test_validate_records_passes_for_valid_records() -> None:
    contract = DataContract(
        name="synthetic_reports",
        required_columns=("player_id", "date", "score"),
        non_null_columns=("player_id", "date"),
        unique_key=("player_id", "date"),
    )

    report = validate_records(
        [
            {"player_id": "p1", "date": "2021-01-01", "score": 7},
            {"player_id": "p2", "date": "2021-01-01", "score": None},
        ],
        contract,
    )

    assert report.passed
    assert report.row_count == 2


def test_validate_records_reports_structural_failures() -> None:
    contract = DataContract(
        name="synthetic_reports",
        required_columns=("player_id", "date"),
        non_null_columns=("player_id",),
        unique_key=("player_id", "date"),
        min_rows=3,
    )

    report = validate_records(
        [
            {"player_id": "p1", "date": "2021-01-01"},
            {"player_id": "p1", "date": "2021-01-01"},
            {"player_id": None},
        ],
        contract,
    )

    assert not report.passed
    assert {issue.code for issue in report.issues} == {
        "missing_required_column",
        "null_required_value",
        "duplicate_key",
    }


def test_data_contract_rejects_keys_outside_required_columns() -> None:
    with pytest.raises(ValueError, match="unique_key"):
        DataContract(name="invalid", required_columns=("player_id",), unique_key=("date",))
