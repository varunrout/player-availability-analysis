"""Run approved EXP-003 M1-F1 on development data only."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_m1_f1_config,
    load_m1_f1_from_gcp,
    write_m1_f1_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_m1_f1.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_003_m1_logistic/f1"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_m1_f1_config(args.config)
    settings = get_settings()
    result = load_m1_f1_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_m1_f1_outputs(result, args.output_root)
    print(
        f"{result.summary['experiment_id']} {result.summary['model_id']} "
        f"{result.summary['status']}: C={result.summary['selected_regularisation_c']}, "
        f"{result.summary['validation_represented_onsets']} represented onsets, "
        "final-test access=false"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
