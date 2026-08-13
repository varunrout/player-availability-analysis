"""Build self-reported injury episodes from the subjective silver injury reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from player_availability.outcomes import build_injury_episodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--injury-reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--gap-days", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reports = pl.read_parquet(args.injury_reports)
    episodes = build_injury_episodes(reports, gap_days=args.gap_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    episodes.write_parquet(args.output, compression="zstd")
    report = {
        "source_reports": reports.height,
        "episode_count": episodes.height,
        "episode_gap_days": args.gap_days,
    }
    args.quality_report.parent.mkdir(parents=True, exist_ok=True)
    args.quality_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {episodes.height} injury episodes")


if __name__ == "__main__":
    main()
