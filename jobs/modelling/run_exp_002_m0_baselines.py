"""Run approved EXP-002 M0 baselines on development data only."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import load_m0_config, load_m0_from_gcp, write_m0_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_m0.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_002_m0_baselines"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_m0_config(args.config)
    settings = get_settings()
    result = load_m0_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_m0_outputs(result, args.output_root)
    print(
        f"{result.summary['experiment_id']} {result.summary['status']}: "
        f"{result.summary['validation_player_days']} validation player-days, "
        f"{result.summary['validation_represented_onsets']} represented onsets, "
        "final-test access=false"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
