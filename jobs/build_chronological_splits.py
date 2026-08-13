"""Freeze chronological subjective-model partitions and write their audit artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from player_availability.modelling import (
    assign_primary_chronological_split,
    render_split_manifest_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assigned, manifest = assign_primary_chronological_split(pl.read_parquet(args.features))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assigned.write_parquet(args.output, compression="zstd")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_split_manifest_markdown(manifest), encoding="utf-8")
    print(f"Wrote {assigned.height} split-assigned player-day rows")


if __name__ == "__main__":
    main()
