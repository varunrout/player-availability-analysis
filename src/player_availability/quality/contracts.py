"""Small, dependency-free data contracts for ingestion boundaries."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DataContract:
    """Structural checks that apply before a dataset moves beyond bronze."""

    name: str
    required_columns: tuple[str, ...]
    non_null_columns: tuple[str, ...] = ()
    unique_key: tuple[str, ...] = ()
    min_rows: int = 1

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.min_rows < 0:
            raise ValueError("min_rows must not be negative")
        if missing := set(self.non_null_columns) - set(self.required_columns):
            raise ValueError(f"non_null_columns must be required columns: {sorted(missing)}")
        if missing := set(self.unique_key) - set(self.required_columns):
            raise ValueError(f"unique_key must be required columns: {sorted(missing)}")


@dataclass(frozen=True, slots=True)
class QualityIssue:
    """One contract failure with a count suitable for reporting."""

    code: str
    message: str
    affected_rows: int


@dataclass(frozen=True, slots=True)
class QualityReport:
    """The complete outcome of evaluating one data contract."""

    contract_name: str
    row_count: int
    issues: tuple[QualityIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


def validate_records(records: Sequence[Mapping[str, Any]], contract: DataContract) -> QualityReport:
    """Validate generic records without making assumptions about source semantics."""
    issues: list[QualityIssue] = []
    if len(records) < contract.min_rows:
        issues.append(
            QualityIssue(
                code="minimum_row_count",
                message=f"Expected at least {contract.min_rows} rows, found {len(records)}",
                affected_rows=len(records),
            )
        )

    for column in contract.required_columns:
        missing_count = sum(column not in record for record in records)
        if missing_count:
            issues.append(
                QualityIssue(
                    code="missing_required_column",
                    message=f"Required column {column!r} is missing from {missing_count} row(s)",
                    affected_rows=missing_count,
                )
            )

    for column in contract.non_null_columns:
        null_count = sum(record.get(column) is None for record in records if column in record)
        if null_count:
            issues.append(
                QualityIssue(
                    code="null_required_value",
                    message=f"Required column {column!r} contains {null_count} null value(s)",
                    affected_rows=null_count,
                )
            )

    if contract.unique_key:
        key_counts = Counter(
            tuple(record.get(column) for column in contract.unique_key)
            for record in records
            if all(
                column in record and record[column] is not None for column in contract.unique_key
            )
        )
        duplicate_rows = sum(count for count in key_counts.values() if count > 1)
        if duplicate_rows:
            issues.append(
                QualityIssue(
                    code="duplicate_key",
                    message=f"Unique key {contract.unique_key!r} has duplicate rows",
                    affected_rows=duplicate_rows,
                )
            )

    return QualityReport(
        contract_name=contract.name,
        row_count=len(records),
        issues=tuple(issues),
    )
