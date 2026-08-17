"""Run the approved EXP-018 explanation-stability audit on the raw F1 champion."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_exp_018_config,
    load_exp_018_from_gcp,
    write_exp_018_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_exp_018_explanation.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/exp_018_explanation"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_exp_018_config(args.config)
    settings = get_settings()
    result = load_exp_018_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_exp_018_outputs(result, args.output_root)
    summary = result.summary
    print(
        f"EXP-018 explanation stability {summary['status']}: "
        f"final-test access={str(config.final_test_access).lower()}"
    )
    print(
        f"Rolling folds={summary['rolling_estimable_fold_count']}; "
        f"LOPO folds={summary['lopo_estimable_fold_count']}; "
        f"unstable-sign predictors={summary['unstable_sign_predictor_count']}/"
        f"{summary['predictor_count']}"
    )
    if summary["stop_condition_triggered"]:
        print(
            "STOP CONDITION TRIGGERED: majority of predictors show unstable sign: "
            f"{', '.join(summary['unstable_sign_predictors'])}"
        )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
