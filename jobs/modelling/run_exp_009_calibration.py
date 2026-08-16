"""Run the approved EXP-009 raw/Platt/isotonic calibration comparison on F3."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_exp_009_config,
    load_exp_009_from_gcp,
    write_exp_009_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_exp_009_calibration.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_009_calibration"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_exp_009_config(args.config)
    settings = get_settings()
    result = load_exp_009_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_exp_009_outputs(result, args.output_root)
    summary = result.summary
    print(
        f"EXP-009 calibration {summary['status']}: "
        f"final-test access={str(config.final_test_access).lower()}"
    )
    print(
        f"Pooled positive days={summary['pooled_positive_days']}; "
        f"estimable folds={summary['estimable_discrimination_fold_count']}; "
        f"zero-positive folds={summary['zero_positive_fold_count']}"
    )
    for row in result.tables["arm_pooled_metrics"].iter_rows(named=True):
        print(
            f"{row['arm']}: Brier={row['brier_score']:.6f}, "
            f"slope={_format(row['calibration_slope'])}, "
            f"mean_pred={row['mean_prediction']:.6f}, observed={row['observed_rate']:.6f}"
        )
    print(f"Retained outputs: {args.output_root}")


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
