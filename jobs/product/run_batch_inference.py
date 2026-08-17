"""Run V1-P6 batch inference: score every eligible player-day and write the product.

Writes the paa_product BigQuery table of record and the compact serving artefact
that the API reads. Safe to re-run: both writes are full overwrites (`DEC-064`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from player_availability.config import get_settings
from player_availability.product.batch_inference import (
    load_batch_inference_config,
    load_batch_inference_from_gcp,
    write_batch_inference_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/product/batch_inference.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/product/batch_inference"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_batch_inference_config(args.config)
    settings = get_settings()
    result = load_batch_inference_from_gcp(
        project_id=settings.gcp.project_id,
        data_bucket=settings.gcp.data_bucket,
        config=config,
    )
    report = write_batch_inference_outputs(
        result,
        project_id=settings.gcp.project_id,
        bq_product_dataset=settings.gcp.bq_product_dataset,
        artifacts_bucket=settings.gcp.artifacts_bucket,
        output_root=args.output_root,
    )
    print(f"Batch inference: {result.summary['covered_player_days']} player-days scored")
    print(f"Covered {result.summary['covered_date_start']} to {result.summary['covered_date_end']}")
    print(f"Reconciliation: {report['reconciliation']}")
    print(f"BigQuery table: {report['bq_table_id']} ({report['bq_live_row_count']} rows)")
    print(f"Serving artefact: {report['gcs_artifact_uri']}")


if __name__ == "__main__":
    main()
