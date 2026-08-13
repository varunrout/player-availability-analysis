"""Build leak-safe player-day injury-episode labels from silver relations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from player_availability.outcomes.labels import build_player_day_labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-registry", type=Path, required=True)
    parser.add_argument("--injury-episodes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    labels = build_player_day_labels(
        pl.read_parquet(args.player_registry), pl.read_parquet(args.injury_episodes)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    labels.write_parquet(args.output, compression="zstd")
    report = {
        "player_day_rows": labels.height,
        "active_episode_days": labels.filter(pl.col("active_injury_episode")).height,
        "eligible_new_onset_rows": {
            horizon: labels.filter(pl.col(f"eligible_new_onset_{horizon}d")).height
            for horizon in (3, 7, 14)
        },
        "positive_labels": {
            horizon: labels.filter(pl.col(f"injury_next_{horizon}d")).height
            for horizon in (3, 7, 14)
        },
    }
    args.quality_report.parent.mkdir(parents=True, exist_ok=True)
    args.quality_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {labels.height} player-day label rows")


if __name__ == "__main__":
    main()
