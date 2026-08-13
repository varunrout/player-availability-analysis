"""Source provenance and idempotent ingestion-run identities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SourceAsset:
    """An immutable reference to one acquired source object."""

    uri: str
    size_bytes: int
    checksum_algorithm: str
    checksum_value: str

    def __post_init__(self) -> None:
        if not self.uri:
            raise ValueError("uri must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")
        if not self.checksum_algorithm:
            raise ValueError("checksum_algorithm must not be empty")
        if not self.checksum_value:
            raise ValueError("checksum_value must not be empty")


@dataclass(frozen=True, slots=True)
class IngestionRun:
    """A reproducible identity for one source-to-stage transformation."""

    run_id: str
    pipeline_name: str
    source: SourceAsset
    stage: str
    code_version: str
    started_at: datetime


def create_ingestion_run(
    *,
    pipeline_name: str,
    source: SourceAsset,
    stage: str,
    code_version: str,
    started_at: datetime | None = None,
) -> IngestionRun:
    """Create a stable run identity from the source, target stage and code version."""
    if not pipeline_name or not stage or not code_version:
        raise ValueError("pipeline_name, stage and code_version must not be empty")

    identity = {
        "pipeline_name": pipeline_name,
        "source": asdict(source),
        "stage": stage,
        "code_version": code_version,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    run_id = hashlib.sha256(encoded).hexdigest()[:20]
    return IngestionRun(
        run_id=run_id,
        pipeline_name=pipeline_name,
        source=source,
        stage=stage,
        code_version=code_version,
        started_at=started_at or datetime.now(UTC),
    )
