"""Run the approved EXP-019 alert-budget simulation on the raw F1 champion."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_exp_019_config,
    load_exp_019_from_gcp,
    write_exp_019_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_exp_019_alert_budget.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_019_alert_budget"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_exp_019_config(args.config)
    settings = get_settings()
    result = load_exp_019_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_exp_019_outputs(result, args.output_root)
    summary = result.summary
    print(
        f"EXP-019 alert budget {summary['status']}: "
        f"final-test access={str(config.final_test_access).lower()}"
    )
    print(
        f"Pooled positive days={summary['pooled_positive_days']}; "
        f"estimable folds={summary['estimable_discrimination_fold_count']}; "
        f"zero-positive folds={summary['zero_positive_fold_count']}"
    )
    for row in (
        result.tables["alert_budget_results"]
        .sort(["operating_point_type", "operating_point_value"])
        .iter_rows(named=True)
    ):
        print(
            f"{row['operating_point_type']}={row['operating_point_value']:g}: "
            f"alerts={row['alert_count']}, recall={_format(row['recall'])}, "
            f"false/captured={_format(row['false_alerts_per_captured_onset'])}"
        )
    print(f"Retained outputs: {args.output_root}")


def _format(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    main()
