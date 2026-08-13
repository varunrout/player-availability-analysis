"""Idempotent BigQuery persistence for ingestion provenance."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from player_availability.ingestion.provenance import SourceAsset, create_ingestion_run

SOURCE_NAME = "soccermon"
SOURCE_VERSION = "zenodo-10033832"


class BigQueryClient(Protocol):
    """The small BigQuery client surface required by provenance persistence."""

    def query(self, query: str, job_config: Any) -> Any: ...

    def insert_rows_json(
        self, table: str, json_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class ProvenancePayload:
    """Prepared rows for the two provenance tables."""

    run_id: str
    ingestion_run: dict[str, Any]
    source_files: tuple[dict[str, Any], ...]


def build_provenance_payload(
    *,
    extraction_manifest_path: Path,
    bronze_quality_report_path: Path,
    source_archive_uri: str,
    raw_staging_uri: str,
    pipeline_version: str,
    completed_at: datetime | None = None,
) -> ProvenancePayload:
    """Build source and run records from verified local ingestion artifacts."""
    manifest = json.loads(extraction_manifest_path.read_text(encoding="utf-8"))
    quality_report = json.loads(bronze_quality_report_path.read_text(encoding="utf-8"))
    source = SourceAsset(
        uri=source_archive_uri,
        size_bytes=int(manifest["archive_size_bytes"]),
        checksum_algorithm="sha256",
        checksum_value=str(manifest["archive_sha256"]),
    )
    run = create_ingestion_run(
        pipeline_name="subjective_bronze_ingestion",
        source=source,
        stage="bronze",
        code_version=pipeline_version,
        started_at=completed_at or datetime.now(UTC),
    )
    row_counts = quality_report["row_counts"]
    records_written = sum(int(value) for value in row_counts.values())
    ingestion_run = {
        "run_id": run.run_id,
        "source_name": SOURCE_NAME,
        "source_version": SOURCE_VERSION,
        "source_archive_uri": source_archive_uri,
        "started_at": run.started_at.isoformat(),
        "completed_at": (completed_at or run.started_at).isoformat(),
        "status": "SUCCESS",
        "pipeline_version": pipeline_version,
        "records_read": _source_records_read(manifest, quality_report),
        "records_written": records_written,
        "error_count": 0,
        "notes": "Verified archive; raw staging and bronze normalisation completed locally.",
    }
    source_files = tuple(
        {
            "run_id": run.run_id,
            "source_name": SOURCE_NAME,
            "file_name": Path(member["path"]).name,
            "archive_member_path": member["path"],
            "source_archive_uri": source_archive_uri,
            "staged_gcs_uri": f"{raw_staging_uri.rstrip('/')}/{member['path']}",
            "sha256": None,
            "size_bytes": int(member["size_bytes"]),
            "row_count": _member_row_count(member["path"], quality_report),
            "notes": _member_note(member),
        }
        for member in manifest["members"]
    )
    return ProvenancePayload(
        run_id=run.run_id, ingestion_run=ingestion_run, source_files=source_files
    )


def persist_provenance(
    *,
    client: BigQueryClient,
    project_id: str,
    core_dataset: str,
    payload: ProvenancePayload,
) -> None:
    """Insert provenance once, rejecting conflicting prior records for the same run."""
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

    run_table = f"{project_id}.{core_dataset}.ingestion_runs"
    source_table = f"{project_id}.{core_dataset}.source_files"
    query = f"SELECT COUNT(*) AS count FROM `{run_table}` WHERE run_id = @run_id"
    job_config = QueryJobConfig(
        query_parameters=[ScalarQueryParameter("run_id", "STRING", payload.run_id)]
    )
    existing_count = next(iter(client.query(query, job_config=job_config).result()))["count"]
    if not existing_count:
        run_errors = client.insert_rows_json(run_table, [payload.ingestion_run])
        if run_errors:
            raise RuntimeError(f"Could not insert ingestion run provenance: {run_errors}")

    existing_paths_query = (
        f"SELECT archive_member_path FROM `{source_table}` WHERE run_id = @run_id"
    )
    existing_paths = {
        row["archive_member_path"]
        for row in client.query(existing_paths_query, job_config=job_config).result()
    }
    missing_source_files = [
        row for row in payload.source_files if row["archive_member_path"] not in existing_paths
    ]
    if not missing_source_files:
        return

    source_errors = client.insert_rows_json(source_table, missing_source_files)
    if source_errors:
        raise RuntimeError(f"Could not insert source file provenance: {source_errors}")


def _source_records_read(manifest: dict[str, Any], quality_report: dict[str, Any]) -> int:
    session_records = int(quality_report["row_counts"]["training_sessions"])
    event_records = sum(
        int(quality_report["row_counts"][name])
        for name in ("injury_reports", "illness_reports", "game_performance_reports")
    )
    daily_source_rows = sum(
        1
        for member in manifest["members"]
        if member["path"].startswith(("subjective/training-load/", "subjective/wellness/"))
        and member["path"].endswith(".csv")
    )
    return session_records + event_records + daily_source_rows * 731


def _member_row_count(path: str, quality_report: dict[str, Any]) -> int:
    if path == "subjective/training-load/session.json":
        return int(quality_report["row_counts"]["training_sessions"])
    mapping = {
        "subjective/injury/injury.csv": "injury_reports",
        "subjective/illness/illness.csv": "illness_reports",
        "subjective/game-performance/game-performance.csv": "game_performance_reports",
    }
    if path in mapping:
        return int(quality_report["row_counts"][mapping[path]])
    return 731


def _member_note(member: Mapping[str, Any]) -> str:
    return f"ZIP CRC32: {member['crc32']}; SHA-256 applies to enclosing verified archive."
