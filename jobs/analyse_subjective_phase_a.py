"""Generate Phase A subjective cohort, outcome and feature-quality evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from player_availability.analysis import build_phase_a_cohort_report
from player_availability.analysis.plots import render_phase_a_charts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--episodes", type=Path, required=True)
    parser.add_argument("--raw-injury-reports", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--charts-directory", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = pl.read_parquet(args.features)
    result = build_phase_a_cohort_report(
        features,
        pl.read_parquet(args.episodes),
        pl.read_parquet(args.raw_injury_reports),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(result.markdown, encoding="utf-8")
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    chart_paths = render_phase_a_charts(features, output_directory=args.charts_directory)
    print(f"Wrote Phase A report: {args.report}")
    print(f"Wrote {len(chart_paths)} Phase A charts")


if __name__ == "__main__":
    main()
