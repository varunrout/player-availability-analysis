from __future__ import annotations

import json
from datetime import date

import polars as pl

from player_availability.outcomes.episodes import build_injury_episodes


def test_build_injury_episodes_deduplicates_components_and_respects_gap() -> None:
    reports = pl.DataFrame(
        {
            "player_id": ["TeamA-1", "TeamA-1", "TeamA-1", "TeamA-1"],
            "team_id": ["TeamA"] * 4,
            "event_date": [date(2021, 1, 1), date(2021, 1, 1), date(2021, 1, 3), date(2021, 1, 8)],
            "source_payload_json": [
                json.dumps({"type": json.dumps({"right_foot": "minor"})}),
                json.dumps({"type": json.dumps({"right_foot": "minor"})}),
                json.dumps({"type": json.dumps({"right_foot": "major", "left_knee": "minor"})}),
                json.dumps({"type": json.dumps({"right_foot": "minor"})}),
            ],
        }
    )

    episodes = build_injury_episodes(reports, gap_days=3)

    assert episodes.height == 3
    right_foot = episodes.filter(pl.col("raw_location") == "right_foot")
    assert right_foot.height == 2
    assert right_foot.row(0, named=True)["max_severity"] == "major"
    assert right_foot.row(0, named=True)["component_report_count"] == 2
