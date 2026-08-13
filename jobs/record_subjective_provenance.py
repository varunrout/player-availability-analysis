"""Persist verified SoccerMon subjective ingestion provenance in BigQuery."""

from __future__ import annotations

import argparse
from pathlib import Path

from google.cloud import bigquery

from player_availability.ingestion.provenance_store import (
    build_provenance_payload,
    persist_provenance,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--core-dataset", required=True)
    parser.add_argument("--pipeline-version", required=True)
    parser.add_argument("--extraction-manifest", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--source-archive-uri", required=True)
    parser.add_argument("--raw-staging-uri", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_provenance_payload(
        extraction_manifest_path=args.extraction_manifest,
        bronze_quality_report_path=args.quality_report,
        source_archive_uri=args.source_archive_uri,
        raw_staging_uri=args.raw_staging_uri,
        pipeline_version=args.pipeline_version,
    )
    persist_provenance(
        client=bigquery.Client(project=args.project_id),
        project_id=args.project_id,
        core_dataset=args.core_dataset,
        payload=payload,
    )
    print(
        f"Recorded provenance for run {payload.run_id} ({len(payload.source_files)} source files)"
    )


if __name__ == "__main__":
    main()
