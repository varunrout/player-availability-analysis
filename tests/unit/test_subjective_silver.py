from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from player_availability.ingestion.silver import (
    EVENT_RELATIONS,
    TRAINING_LOAD_METRICS,
    WELLNESS_METRICS,
    build_subjective_silver,
)


def test_build_subjective_silver_preserves_sessions_and_missing_wellness(tmp_path: Path) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_root.mkdir()
    rows = [
        {
            "player_id": "TeamA-1",
            "team_id": "TeamA",
            "observation_date": day,
            "metric_name": metric,
            "value": None if day.day == 2 and metric in WELLNESS_METRICS else 1.0,
            "source_file": "source.csv",
            "source_row_number": day.day + 1,
        }
        for day in (date(2021, 1, 1), date(2021, 1, 2))
        for metric in (*TRAINING_LOAD_METRICS, *WELLNESS_METRICS)
    ]
    pl.DataFrame(rows).write_parquet(bronze_root / "daily_metrics.parquet")
    pl.DataFrame(
        {
            "player_id": ["TeamA-1", "TeamA-1"],
            "team_id": ["TeamA", "TeamA"],
            "session_date": [date(2021, 1, 1), date(2021, 1, 1)],
            "duration_minutes": [30.0, 60.0],
            "rpe": [4.0, 6.0],
            "srpe": [120.0, 360.0],
            "source_file": ["training-load/session.json"] * 2,
            "source_record_index": [0, 1],
        }
    ).write_parquet(bronze_root / "training_sessions.parquet")
    for relation in EVENT_RELATIONS:
        pl.DataFrame(
            {
                "player_id": ["TeamA-1"],
                "team_id": ["TeamA"],
                "event_date": [date(2021, 1, 1)],
                "event_type": [relation.removesuffix("_reports")],
                "source_file": [f"{relation}.csv"],
                "source_row_number": [2],
                "source_payload_json": ["{}"],
            }
        ).write_parquet(bronze_root / f"{relation}.parquet")

    result = build_subjective_silver(
        bronze_root=bronze_root,
        silver_root=tmp_path / "silver",
        quality_report_path=tmp_path / "report.json",
    )

    wellness = pl.read_parquet(tmp_path / "silver" / "wellness_daily.parquet")
    sessions = pl.read_parquet(tmp_path / "silver" / "training_sessions.parquet")
    assert result.row_counts["player_registry"] == 1
    assert wellness.filter(~pl.col("wellness_report_present")).height == 1
    assert sessions.height == 2
    assert sessions.get_column("session_id").n_unique() == 2
