"""Run the approved Stage 8 pre-model readiness evidence gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.analysis import (
    run_stage_08_pre_model_readiness,
    write_stage_08_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-root",
        type=Path,
        default=Path("outputs/analysis"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/analysis/08_pre_model_readiness"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_stage_08_pre_model_readiness(
        analysis_root=args.analysis_root,
        repo_root=Path("."),
    )
    write_stage_08_outputs(result, args.output_root)
    print(
        f"Stage 8 {result.summary['status']}: "
        f"recommendation={result.summary['recommendation']}, "
        f"{result.summary['failure_count']} failures, "
        f"{result.summary['warning_count']} warnings, "
        f"{result.summary['review_count']} review findings"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
