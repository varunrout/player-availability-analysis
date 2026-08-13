"""Build canonical SoccerMon subjective silver relations from bronze Parquet."""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.ingestion.silver import build_subjective_silver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bronze-root", type=Path, required=True)
    parser.add_argument("--silver-root", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_subjective_silver(
        bronze_root=args.bronze_root,
        silver_root=args.silver_root,
        quality_report_path=args.quality_report,
    )
    print(f"Wrote {len(result.output_paths)} silver datasets")
    for name, count in sorted(result.row_counts.items()):
        print(f"{name}: {count}")
    print(f"Quality report: {result.quality_report_path}")


if __name__ == "__main__":
    main()
