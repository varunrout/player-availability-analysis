"""Evidence-led construction of self-reported injury episodes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import date
from typing import Any

import polars as pl

SEVERITY_ORDER = {"minor": 1, "major": 2}


def build_injury_episodes(reports: pl.DataFrame, *, gap_days: int) -> pl.DataFrame:
    """Group parsed injury components by player, raw location and event-free gap.

    Input reports are preserved elsewhere. This function treats source ``type`` values as
    self-reported location/severity components, removes exact duplicate components, and
    never turns illness or unparsed values into injury episodes.
    """
    if gap_days < 0:
        raise ValueError("gap_days must not be negative")
    components = list(_iter_components(reports.to_dicts()))
    unique_components = sorted(
        {
            (
                item["player_id"],
                item["team_id"],
                item["event_date"],
                item["raw_location"],
                item["severity"],
            )
            for item in components
        }
    )
    grouped: list[dict[str, Any]] = []
    active: dict[tuple[str, str], dict[str, Any]] = {}
    for player_id, team_id, event_date, raw_location, severity in unique_components:
        key = (player_id, raw_location)
        current = active.get(key)
        if current is None or (event_date - current["episode_end"]).days > gap_days:
            current = {
                "player_id": player_id,
                "team_id": team_id,
                "raw_location": raw_location,
                "episode_start": event_date,
                "episode_end": event_date,
                "component_report_count": 1,
                "max_severity": severity,
            }
            active[key] = current
            grouped.append(current)
        else:
            current["episode_end"] = event_date
            current["component_report_count"] += 1
            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[current["max_severity"]]:
                current["max_severity"] = severity
    output_rows = [{**row, "episode_gap_days": gap_days} for row in grouped]
    return pl.DataFrame([{"episode_id": _episode_id(row), **row} for row in output_rows]).sort(
        "player_id", "episode_start", "raw_location"
    )


def _iter_components(reports: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for report in reports:
        payload = json.loads(str(report["source_payload_json"]))
        raw_type = json.loads(payload["type"])
        if not isinstance(raw_type, dict):
            raise ValueError("Expected injury type to be a location/severity object")
        for raw_location, severity in raw_type.items():
            if severity not in SEVERITY_ORDER:
                raise ValueError(f"Unexpected injury severity: {severity!r}")
            event_date = report["event_date"]
            if not isinstance(event_date, date):
                raise ValueError("Expected parsed injury event_date")
            yield {
                "player_id": report["player_id"],
                "team_id": report["team_id"],
                "event_date": event_date,
                "raw_location": raw_location,
                "severity": severity,
            }


def _episode_id(row: dict[str, Any]) -> str:
    identity = {
        key: row[key]
        for key in ("player_id", "raw_location", "episode_start", "episode_gap_days")
        if key in row
    }
    encoded = json.dumps(identity, sort_keys=True, default=str, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"injury_episode_{hashlib.sha256(encoded).hexdigest()[:20]}"
