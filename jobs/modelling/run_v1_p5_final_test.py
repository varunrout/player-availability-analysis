"""Run the V1-P5 final-test governance gate. Single-use: reads the final-test partition once.

Do not run this script more than once against live data without a superseding decision
authorising a second access (`DEC-062`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.modelling import (
    load_v1_p5_config,
    load_v1_p5_from_gcp,
    write_v1_p5_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/modelling/subjective_v1_p5_final_test.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/modelling/v1_p5_final_test"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_v1_p5_config(args.config)
    settings = get_settings()
    result = load_v1_p5_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    write_v1_p5_outputs(result, args.output_root)
    summary = result.summary
    print(
        f"V1-P5 final test {summary['status']}: preregistration={summary['preregistration_commit']}"
    )
    print(
        f"Final-test player-days={summary['final_test_rows_evaluated']}; "
        f"positive days={summary['final_test_positive_days']}; "
        f"represented onsets={summary['final_test_represented_onsets']}"
    )
    print(
        f"C1 ranking above chance={summary['c1_ranking_above_chance']}; "
        f"C2 overprediction in the large={summary['c2_overprediction_in_the_large']}; "
        f"C3 high false-alert burden={summary['c3_high_false_alert_burden']}"
    )
    print(f"Retained outputs: {args.output_root}")


if __name__ == "__main__":
    main()
