from __future__ import annotations

import json
from datetime import date

import pytest

from player_availability.ingestion.subjective import (
    normalise_daily_matrix,
    normalise_events,
    normalise_sessions,
    parse_source_date,
    team_id_from_player_id,
)


def test_normalise_daily_matrix_preserves_empty_source_cells_as_null() -> None:
    rows = [
        {"Fatigue Data": "01.01.2020", "TeamA-one": "3.0", "TeamB-two": ""},
        {"Fatigue Data": "02.01.2020", "TeamA-one": "", "TeamB-two": "4.0"},
    ]

    output = normalise_daily_matrix(rows, metric_name="fatigue", source_file="wellness/fatigue.csv")

    assert output == [
        {
            "player_id": "TeamA-one",
            "team_id": "TeamA",
            "observation_date": date(2020, 1, 1),
            "metric_name": "fatigue",
            "value": 3.0,
            "source_file": "wellness/fatigue.csv",
            "source_row_number": 2,
        },
        {
            "player_id": "TeamB-two",
            "team_id": "TeamB",
            "observation_date": date(2020, 1, 1),
            "metric_name": "fatigue",
            "value": None,
            "source_file": "wellness/fatigue.csv",
            "source_row_number": 2,
        },
        {
            "player_id": "TeamA-one",
            "team_id": "TeamA",
            "observation_date": date(2020, 1, 2),
            "metric_name": "fatigue",
            "value": None,
            "source_file": "wellness/fatigue.csv",
            "source_row_number": 3,
        },
        {
            "player_id": "TeamB-two",
            "team_id": "TeamB",
            "observation_date": date(2020, 1, 2),
            "metric_name": "fatigue",
            "value": 4.0,
            "source_file": "wellness/fatigue.csv",
            "source_row_number": 3,
        },
    ]


def test_normalise_sessions_preserves_multiple_sessions_on_same_day() -> None:
    output = normalise_sessions(
        {
            "TeamA-one": [
                {"date": "01.01.2020", "duration": 60, "rpe": 5, "srpe": 300},
                {"date": "01.01.2020", "duration": 40, "rpe": 4, "srpe": 160},
            ]
        }
    )

    assert [row["source_record_index"] for row in output] == [0, 1]
    assert {row["session_date"] for row in output} == {date(2020, 1, 1)}


def test_normalise_events_preserves_raw_source_payload() -> None:
    output = normalise_events(
        [{"player_name": "TeamB-two", "problems": '["coughing"]', "timestamp": "04.01.2021"}],
        source_file="illness/illness.csv",
        event_type="illness",
    )

    assert output[0]["event_date"] == date(2021, 1, 4)
    assert json.loads(output[0]["source_payload_json"])["problems"] == '["coughing"]'


@pytest.mark.parametrize("value", ["2020-01-01", "", "31.02.2020"])
def test_parse_source_date_rejects_non_source_formats(value: str) -> None:
    with pytest.raises(ValueError, match="Expected date"):
        parse_source_date(value)


def test_team_id_requires_team_prefixed_player_identifier() -> None:
    with pytest.raises(ValueError, match="team-prefixed"):
        team_id_from_player_id("unknown")
