from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from player_availability.ingestion.provenance_store import (
    build_provenance_payload,
    persist_provenance,
)


class FakeQueryResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def result(self) -> list[dict[str, Any]]:
        return self.rows


class FakeBigQueryClient:
    def __init__(
        self, existing_count: int = 0, existing_source_paths: tuple[str, ...] = ()
    ) -> None:
        self.existing_count = existing_count
        self.existing_source_paths = existing_source_paths
        self.inserted: list[tuple[str, list[dict[str, Any]]]] = []

    def query(self, query: str, job_config: Any) -> FakeQueryResult:
        if "archive_member_path" in query:
            return FakeQueryResult(
                [{"archive_member_path": path} for path in self.existing_source_paths]
            )
        return FakeQueryResult([{"count": self.existing_count}])

    def insert_rows_json(self, table: str, json_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.inserted.append((table, json_rows))
        return []


def write_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    manifest_path = tmp_path / "manifest.json"
    quality_path = tmp_path / "quality.json"
    manifest_path.write_text(
        json.dumps(
            {
                "archive_size_bytes": 10,
                "archive_sha256": "archive-checksum",
                "members": [
                    {"path": "subjective/wellness/fatigue.csv", "size_bytes": 1, "crc32": "one"},
                    {
                        "path": "subjective/training-load/session.json",
                        "size_bytes": 2,
                        "crc32": "two",
                    },
                    {"path": "subjective/injury/injury.csv", "size_bytes": 3, "crc32": "three"},
                ],
            }
        ),
        encoding="utf-8",
    )
    quality_path.write_text(
        json.dumps(
            {
                "row_counts": {
                    "daily_metrics": 36550,
                    "training_sessions": 10,
                    "injury_reports": 3,
                    "illness_reports": 0,
                    "game_performance_reports": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    return manifest_path, quality_path


def test_build_provenance_payload_links_members_to_one_deterministic_run(tmp_path: Path) -> None:
    manifest_path, quality_path = write_artifacts(tmp_path)

    payload = build_provenance_payload(
        extraction_manifest_path=manifest_path,
        bronze_quality_report_path=quality_path,
        source_archive_uri="gs://archive/subjective.zip",
        raw_staging_uri="gs://data/raw/subjective",
        pipeline_version="abc123",
    )

    assert payload.ingestion_run["records_read"] == 744
    assert payload.ingestion_run["records_written"] == 36563
    assert {row["run_id"] for row in payload.source_files} == {payload.run_id}
    assert (
        payload.source_files[0]["staged_gcs_uri"]
        == "gs://data/raw/subjective/subjective/wellness/fatigue.csv"
    )


def test_persist_provenance_is_idempotent_for_complete_existing_run(tmp_path: Path) -> None:
    manifest_path, quality_path = write_artifacts(tmp_path)
    payload = build_provenance_payload(
        extraction_manifest_path=manifest_path,
        bronze_quality_report_path=quality_path,
        source_archive_uri="gs://archive/subjective.zip",
        raw_staging_uri="gs://data/raw/subjective",
        pipeline_version="abc123",
    )
    client = FakeBigQueryClient(
        existing_count=1,
        existing_source_paths=tuple(row["archive_member_path"] for row in payload.source_files),
    )

    persist_provenance(
        client=client,
        project_id="test-project",
        core_dataset="core",
        payload=payload,
    )

    assert client.inserted == []


def test_persist_provenance_recovers_missing_source_files(tmp_path: Path) -> None:
    manifest_path, quality_path = write_artifacts(tmp_path)
    payload = build_provenance_payload(
        extraction_manifest_path=manifest_path,
        bronze_quality_report_path=quality_path,
        source_archive_uri="gs://archive/subjective.zip",
        raw_staging_uri="gs://data/raw/subjective",
        pipeline_version="abc123",
    )
    client = FakeBigQueryClient(
        existing_count=1,
        existing_source_paths=(payload.source_files[0]["archive_member_path"],),
    )

    persist_provenance(
        client=client,
        project_id="test-project",
        core_dataset="core",
        payload=payload,
    )

    assert len(client.inserted) == 1
    assert len(client.inserted[0][1]) == 2
