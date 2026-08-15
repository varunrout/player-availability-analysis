"""Run approved Stage 6 cohort and outcome sensitivity analysis against GCP."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.analysis import load_stage_06_from_gcp, write_stage_06_outputs
from player_availability.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/analysis/06_cohort_outcome_sensitivity"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    result = load_stage_06_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
    )
    write_stage_06_outputs(result, args.output_root)
    print(
        f"Stage 6 {result.summary['status']}: "
        f"{result.summary['failure_count']} failures, "
        f"{result.summary['warning_count']} warnings, "
        f"{result.summary['review_count']} review findings"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
