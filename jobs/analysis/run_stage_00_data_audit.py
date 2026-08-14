"""Run the approved Stage 0 data inventory and audit against GCP products."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.analysis import load_stage_00_from_gcp, write_stage_00_outputs
from player_availability.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/analysis/00_data_audit"),
    )
    parser.add_argument(
        "--archive-bucket",
        default="paa-source-archives-979927072833",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    result = load_stage_00_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        archive_bucket=args.archive_bucket,
        core_dataset=settings.gcp.bq_core_dataset,
    )
    write_stage_00_outputs(result, args.output_root)
    print(
        f"Stage 0 {result.summary['status']}: "
        f"{result.summary['failure_count']} failures, "
        f"{result.summary['warning_count']} warnings"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
