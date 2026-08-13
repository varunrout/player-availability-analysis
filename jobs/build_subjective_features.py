"""Build leak-safe subjective player-day features from gold and silver relations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from player_availability.features import build_subjective_player_day_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-day-labels", type=Path, required=True)
    parser.add_argument("--training-load-daily", type=Path, required=True)
    parser.add_argument("--wellness-daily", type=Path, required=True)
    parser.add_argument("--training-sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = build_subjective_player_day_features(
        pl.read_parquet(args.player_day_labels),
        pl.read_parquet(args.training_load_daily),
        pl.read_parquet(args.wellness_daily),
        pl.read_parquet(args.training_sessions),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features.write_parquet(args.output, compression="zstd")
    report = {
        "row_count": features.height,
        "feature_version": "subjective_v1",
        "daily_load_non_null": features.get_column("daily_load").is_not_null().sum(),
        "wellness_report_present": features.get_column("wellness_report_present").sum(),
    }
    args.quality_report.parent.mkdir(parents=True, exist_ok=True)
    args.quality_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {features.height} subjective player-day feature rows")


if __name__ == "__main__":
    main()
