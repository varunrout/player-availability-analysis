"""Source-grounded normalisation for the SoccerMon subjective archive."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import polars as pl

DATE_FORMAT = "%d.%m.%Y"

DAILY_METRICS: dict[str, str] = {
    "training-load/acwr.csv": "acwr",
    "training-load/atl.csv": "atl",
    "training-load/ctl28.csv": "ctl28",
    "training-load/ctl42.csv": "ctl42",
    "training-load/daily_load.csv": "daily_load",
    "training-load/monotony.csv": "monotony",
    "training-load/strain.csv": "strain",
    "training-load/weekly_load.csv": "weekly_load",
    "wellness/fatigue.csv": "fatigue",
    "wellness/mood.csv": "mood",
    "wellness/readiness.csv": "readiness",
    "wellness/sleep_duration.csv": "sleep_duration",
    "wellness/sleep_quality.csv": "sleep_quality",
    "wellness/soreness.csv": "soreness",
    "wellness/stress.csv": "stress",
}

EVENT_SOURCES: dict[str, str] = {
    "injury/injury.csv": "injury_reports",
    "illness/illness.csv": "illness_reports",
    "game-performance/game-performance.csv": "game_performance_reports",
}


@dataclass(frozen=True, slots=True)
class SubjectiveBronzeResult:
    """Paths and measured row counts produced by one bronze normalisation run."""

    output_paths: tuple[Path, ...]
    row_counts: dict[str, int]
    quality_report_path: Path


def parse_source_date(value: str) -> date:
    """Parse SoccerMon's observed day-first source date format."""
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as error:
        raise ValueError(f"Expected date in {DATE_FORMAT!r} format, got {value!r}") from error


def normalise_daily_matrix(
    rows: Iterable[Mapping[str, str]], *, metric_name: str, source_file: str
) -> list[dict[str, Any]]:
    """Convert one date-by-player matrix to long source-preserving bronze rows."""
    records = list(rows)
    if not records:
        raise ValueError(f"Daily matrix is empty: {source_file}")
    date_column = next(iter(records[0]))
    player_ids = tuple(column for column in records[0] if column != date_column)
    if not player_ids:
        raise ValueError(f"Daily matrix has no player columns: {source_file}")

    output: list[dict[str, Any]] = []
    for source_row_number, row in enumerate(records, start=2):
        if set(row) != {date_column, *player_ids}:
            raise ValueError(
                f"Daily matrix columns changed on row {source_row_number}: {source_file}"
            )
        observation_date = parse_source_date(row[date_column])
        for player_id in player_ids:
            raw_value = row[player_id].strip()
            output.append(
                {
                    "player_id": player_id,
                    "team_id": team_id_from_player_id(player_id),
                    "observation_date": observation_date,
                    "metric_name": metric_name,
                    "value": float(raw_value) if raw_value else None,
                    "source_file": source_file,
                    "source_row_number": source_row_number,
                }
            )
    return output


def normalise_sessions(payload: Mapping[str, list[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Convert the observed player-keyed session JSON into player-session records."""
    output: list[dict[str, Any]] = []
    expected_fields = {"date", "duration", "rpe", "srpe"}
    for player_id in sorted(payload):
        records = payload[player_id]
        for source_record_index, record in enumerate(records):
            if set(record) != expected_fields:
                raise ValueError(
                    "Unexpected session fields for "
                    f"{player_id} record {source_record_index}: {sorted(record)}"
                )
            output.append(
                {
                    "player_id": player_id,
                    "team_id": team_id_from_player_id(player_id),
                    "session_date": parse_source_date(str(record["date"])),
                    "duration_minutes": float(record["duration"]),
                    "rpe": float(record["rpe"]),
                    "srpe": float(record["srpe"]),
                    "source_file": "training-load/session.json",
                    "source_record_index": source_record_index,
                }
            )
    return output


def normalise_events(
    rows: Iterable[Mapping[str, str]], *, source_file: str, event_type: str
) -> list[dict[str, Any]]:
    """Preserve event rows while parsing their player identity and event date."""
    output: list[dict[str, Any]] = []
    for source_row_number, row in enumerate(rows, start=2):
        if "player_name" not in row or "timestamp" not in row:
            raise ValueError(f"Event source lacks player_name or timestamp: {source_file}")
        player_id = row["player_name"]
        output.append(
            {
                "player_id": player_id,
                "team_id": team_id_from_player_id(player_id),
                "event_date": parse_source_date(row["timestamp"]),
                "event_type": event_type,
                "source_file": source_file,
                "source_row_number": source_row_number,
                "source_payload_json": json.dumps(dict(row), sort_keys=True, separators=(",", ":")),
            }
        )
    return output


def build_subjective_bronze(
    *, raw_root: Path, bronze_root: Path, quality_report_path: Path
) -> SubjectiveBronzeResult:
    """Normalise the verified raw subjective source into bronze Parquet datasets."""
    subjective_root = raw_root / "subjective"
    daily_rows: list[dict[str, Any]] = []
    metric_row_counts: dict[str, int] = {}
    daily_player_columns: set[str] | None = None

    for relative_path, metric_name in DAILY_METRICS.items():
        source_path = subjective_root / relative_path
        rows = read_csv_rows(source_path)
        current_player_columns = set(rows[0]) - {next(iter(rows[0]))}
        if daily_player_columns is None:
            daily_player_columns = current_player_columns
        elif daily_player_columns != current_player_columns:
            raise ValueError(f"Player columns differ in daily matrix: {relative_path}")
        normalised = normalise_daily_matrix(
            rows, metric_name=metric_name, source_file=relative_path
        )
        daily_rows.extend(normalised)
        metric_row_counts[metric_name] = len(normalised)

    session_path = subjective_root / "training-load/session.json"
    sessions = normalise_sessions(read_session_payload(session_path))

    event_rows: dict[str, list[dict[str, Any]]] = {}
    for relative_path, output_name in EVENT_SOURCES.items():
        event_rows[output_name] = normalise_events(
            read_csv_rows(subjective_root / relative_path),
            source_file=relative_path,
            event_type=output_name.removesuffix("_reports"),
        )

    bronze_root.mkdir(parents=True, exist_ok=True)
    daily_path = bronze_root / "daily_metrics.parquet"
    session_output_path = bronze_root / "training_sessions.parquet"
    write_parquet(daily_rows, daily_path)
    write_parquet(sessions, session_output_path)
    output_paths = [daily_path, session_output_path]
    for output_name, rows in event_rows.items():
        output_path = bronze_root / f"{output_name}.parquet"
        write_parquet(rows, output_path)
        output_paths.append(output_path)

    row_counts = {
        "daily_metrics": len(daily_rows),
        "training_sessions": len(sessions),
        **{output_name: len(rows) for output_name, rows in event_rows.items()},
    }
    report = {
        "source": "soccermon-subjective-zenodo-10033832",
        "daily_metrics": metric_row_counts,
        "daily_player_columns": len(daily_player_columns or set()),
        "row_counts": row_counts,
    }
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return SubjectiveBronzeResult(
        output_paths=tuple(output_paths),
        row_counts=row_counts,
        quality_report_path=quality_report_path,
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV source and require it to contain a header and rows."""
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f"CSV source has no rows: {path}")
    return rows


def read_session_payload(path: Path) -> dict[str, list[Mapping[str, Any]]]:
    """Read and validate the observed player-keyed session JSON container."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(rows, list) for rows in payload.values()
    ):
        raise ValueError(f"Expected player-keyed session JSON object: {path}")
    return payload


def team_id_from_player_id(player_id: str) -> str:
    """Extract the observed TeamA/TeamB prefix without changing the player identifier."""
    team_id, separator, _ = player_id.partition("-")
    if not separator or not team_id:
        raise ValueError(f"Expected team-prefixed player identifier, got {player_id!r}")
    return team_id


def write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    """Write a deterministic, compact Parquet file for a non-empty bronze relation."""
    if not rows:
        raise ValueError(f"Cannot write an empty bronze relation: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(path, compression="zstd")
