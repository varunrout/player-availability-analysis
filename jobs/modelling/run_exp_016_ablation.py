"""Run the approved EXP-016 sparse-predictor availability ablation on F3."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_exp_016_config,
    load_exp_016_from_gcp,
    write_exp_016_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_exp_016_ablation.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_016_ablation"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_exp_016_config(args.config)
    settings = get_settings()
    result = load_exp_016_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_exp_016_outputs(result, args.output_root)
    summary = result.summary
    print(
        f"EXP-016 ablation {summary['status']}: "
        f"final-test access={str(config.final_test_access).lower()}"
    )
    for row in result.tables["arm_pooled_metrics"].iter_rows(named=True):
        print(
            f"{row['arm']}: Brier={row['brier_score']:.6f}, "
            f"AP={_format(row['average_precision'])}, ROC-AUC={_format(row['roc_auc'])}"
        )
    for row in result.tables["unseen_player_aggregate_metrics"].iter_rows(named=True):
        print(
            f"unseen[{row['arm']}]: AP={_format(row['average_precision'])}, "
            f"ROC-AUC={_format(row['roc_auc'])}, "
            f"estimable={row['estimable_player_count']}/{row['heldout_player_count']}"
        )
    print(f"Retained outputs: {args.output_root}")


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
