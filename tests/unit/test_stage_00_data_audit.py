from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from player_availability.analysis.stage_00_data_audit import (
    RELATION_CONTRACTS,
    run_stage_00_audit,
)


def test_stage_00_passes_for_contract_conforming_relations() -> None:
    frames = _contract_frames()
    result = run_stage_00_audit(
        frames=frames,
        object_inventory=_objects(),
        quality_reports=_quality_reports(frames),
        provenance=_provenance(frames),
    )

    assert result.summary["status"] == "PASS"
    assert result.summary["failure_count"] == 0
    assert result.tables["key_integrity"].filter(pl.col("status") == "FAIL").is_empty()
    registry_inventory = result.tables["relation_inventory"].filter(
        pl.col("relation") == "player_registry"
    )
    assert registry_inventory.item(0, "max_date") == date(2021, 1, 3)
    registry_coverage = result.tables["temporal_coverage"].filter(
        pl.col("relation") == "player_registry"
    )
    assert registry_coverage.item(0, "span_days") == 3
    assert registry_coverage.item(0, "unobserved_span_days") == 0


def test_stage_00_fails_for_duplicate_gold_key() -> None:
    frames = _contract_frames()
    frames["gold.player_day_features"] = pl.concat(
        [frames["gold.player_day_features"], frames["gold.player_day_features"].head(1)]
    )
    reports = _quality_reports(frames)
    reports["player_day_features"]["row_count"] = 2

    result = run_stage_00_audit(
        frames=frames,
        object_inventory=_objects(),
        quality_reports=reports,
        provenance=_provenance(frames),
    )

    assert result.summary["status"] == "FAIL"
    failed = result.tables["key_integrity"].filter(
        (pl.col("relation") == "player_day_features") & (pl.col("status") == "FAIL")
    )
    assert failed.height == 1


def test_stage_00_notebook_contract_has_no_output_writer() -> None:
    notebook_text = Path("notebooks/analysis/00_data_audit.ipynb").read_text(encoding="utf-8")

    assert "write_stage_00_outputs" not in notebook_text
    assert '"outputs": []' in notebook_text
    assert '"execution_count": null' in notebook_text
    assert notebook_text.count('"id":') == 7


def _contract_frames() -> dict[str, pl.DataFrame]:
    frames: dict[str, pl.DataFrame] = {}
    for contract in RELATION_CONTRACTS:
        values: dict[str, pl.Series] = {}
        for column, dtype_name in contract.columns:
            value: object
            if dtype_name == "String":
                value = _string_value(column)
            elif dtype_name == "Date":
                value = date(2021, 1, 1)
            elif dtype_name == "Boolean":
                value = False
            else:
                value = 1
            values[column] = pl.Series(column, [value], dtype=_dtype(dtype_name))
        frames[f"{contract.layer}.{contract.name}"] = pl.DataFrame(values)
    frames["silver.player_registry"] = frames["silver.player_registry"].with_columns(
        pl.lit(date(2021, 1, 3)).alias("observation_end"),
        pl.lit(3, dtype=pl.UInt32).alias("observed_day_count"),
    )
    labels = frames["gold.player_day_labels"]
    features = frames["gold.player_day_features"]
    for column in labels.columns:
        features = features.with_columns(labels.get_column(column))
    frames["gold.player_day_features"] = features
    return frames


def _objects() -> pl.DataFrame:
    rows = [
        {
            "bucket": "data",
            "object_name": contract.object_name,
            "gcs_uri": f"gs://data/{contract.object_name}",
            "size_bytes": 1,
            "generation": "1",
            "md5_hash": "x",
            "crc32c": "y",
            "updated": "2021-01-01T00:00:00Z",
        }
        for contract in RELATION_CONTRACTS
    ]
    rows.extend(
        {
            "bucket": "data",
            "object_name": f"raw/subjective/soccermon/zenodo-10033832/member-{index}",
            "gcs_uri": f"gs://data/raw/member-{index}",
            "size_bytes": 1,
            "generation": "1",
            "md5_hash": "x",
            "crc32c": "y",
            "updated": "2021-01-01T00:00:00Z",
        }
        for index in range(20)
    )
    return pl.DataFrame(rows)


def _quality_reports(frames: dict[str, pl.DataFrame]) -> dict[str, Any]:
    bronze_names = [
        "daily_metrics",
        "training_sessions",
        "injury_reports",
        "illness_reports",
        "game_performance_reports",
    ]
    silver_names = [
        "player_registry",
        "training_load_daily",
        "wellness_daily",
        "training_sessions",
        "injury_reports",
        "illness_reports",
        "game_performance_reports",
    ]
    return {
        "bronze_ingestion": {
            "row_counts": {name: frames[f"bronze.{name}"].height for name in bronze_names}
        },
        "silver_transformation": {
            "row_counts": {name: frames[f"silver.{name}"].height for name in silver_names}
        },
        "injury_episodes": {"episode_count": frames["silver.injury_episodes"].height},
        "player_day_labels": {"player_day_rows": frames["gold.player_day_labels"].height},
        "player_day_features": {"row_count": frames["gold.player_day_features"].height},
    }


def _provenance(frames: dict[str, pl.DataFrame]) -> dict[str, object]:
    bronze_rows = sum(frame.height for name, frame in frames.items() if name.startswith("bronze."))
    return {
        "status": "SUCCESS",
        "error_count": 0,
        "source_file_count": 19,
        "records_written": bronze_rows,
    }


def _dtype(name: str) -> Any:
    return {
        "String": pl.String,
        "Date": pl.Date,
        "Boolean": pl.Boolean,
        "Float64": pl.Float64,
        "Int64": pl.Int64,
        "Int8": pl.Int8,
        "UInt32": pl.UInt32,
    }[name]


def _string_value(column: str) -> str:
    if column == "player_id":
        return "TeamA-1"
    if column == "team_id":
        return "TeamA"
    if column == "feature_version":
        return "subjective_v1"
    return column
