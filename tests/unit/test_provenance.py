from __future__ import annotations

from datetime import UTC, datetime

import pytest

from player_availability.ingestion import SourceAsset, create_ingestion_run


def source_asset() -> SourceAsset:
    return SourceAsset(
        uri="gs://test-source/source.zip",
        size_bytes=123,
        checksum_algorithm="md5",
        checksum_value="example-checksum",
    )


def test_ingestion_run_id_is_stable_for_same_source_and_code_version() -> None:
    started_at = datetime(2026, 8, 13, tzinfo=UTC)

    first = create_ingestion_run(
        pipeline_name="subjective_ingestion",
        source=source_asset(),
        stage="inventory",
        code_version="abc123",
        started_at=started_at,
    )
    second = create_ingestion_run(
        pipeline_name="subjective_ingestion",
        source=source_asset(),
        stage="inventory",
        code_version="abc123",
        started_at=started_at,
    )

    assert first.run_id == second.run_id
    assert first.started_at == started_at


def test_ingestion_run_id_changes_when_source_or_code_changes() -> None:
    baseline = create_ingestion_run(
        pipeline_name="subjective_ingestion",
        source=source_asset(),
        stage="inventory",
        code_version="abc123",
    )
    changed_code = create_ingestion_run(
        pipeline_name="subjective_ingestion",
        source=source_asset(),
        stage="inventory",
        code_version="def456",
    )

    assert baseline.run_id != changed_code.run_id


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"uri": "", "size_bytes": 1, "checksum_algorithm": "md5", "checksum_value": "x"}, "uri"),
        (
            {"uri": "x", "size_bytes": -1, "checksum_algorithm": "md5", "checksum_value": "x"},
            "size",
        ),
    ],
)
def test_source_asset_rejects_invalid_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        SourceAsset(**kwargs)  # type: ignore[arg-type]
