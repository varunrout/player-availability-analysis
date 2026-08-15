"""Run the approved EXP-003 M1 F1/F2/F3 development feature ladder."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_m1_feature_ladder_config,
    load_m1_feature_ladder_from_gcp,
    write_m1_feature_ladder_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_m1_feature_ladder.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_003_m1_logistic/feature_ladder"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_m1_feature_ladder_config(args.config)
    settings = get_settings()
    result = load_m1_feature_ladder_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_m1_feature_ladder_outputs(result, args.output_root)
    comparison = result.tables["feature_set_comparison"]
    print(f"EXP-003 feature ladder {result.summary['status']}: final-test access=false")
    for row in comparison.iter_rows(named=True):
        print(
            f"{row['feature_set']}: C={row['selected_regularisation_c']}, "
            f"Brier={row['brier_score']:.6f}, AP={row['average_precision']:.6f}, "
            f"ROC-AUC={row['roc_auc']:.6f}"
        )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
