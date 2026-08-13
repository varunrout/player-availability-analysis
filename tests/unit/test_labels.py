from __future__ import annotations

from datetime import date

import polars as pl

from player_availability.outcomes.labels import build_player_day_labels


def test_player_day_labels_are_strictly_post_cutoff_and_right_censored() -> None:
    players = pl.DataFrame(
        {
            "player_id": ["TeamA-1"],
            "team_id": ["TeamA"],
            "observation_start": [date(2021, 1, 1)],
            "observation_end": [date(2021, 1, 10)],
        }
    )
    episodes = pl.DataFrame(
        {
            "player_id": ["TeamA-1"],
            "team_id": ["TeamA"],
            "raw_location": ["right_foot"],
            "episode_start": [date(2021, 1, 4)],
            "episode_end": [date(2021, 1, 5)],
            "component_report_count": [2],
            "max_severity": ["minor"],
            "episode_gap_days": [3],
            "episode_id": ["injury_episode_1"],
        }
    )

    labels = build_player_day_labels(players, episodes)

    day_one = labels.filter(pl.col("prediction_date") == date(2021, 1, 1)).row(0, named=True)
    day_four = labels.filter(pl.col("prediction_date") == date(2021, 1, 4)).row(0, named=True)
    day_seven = labels.filter(pl.col("prediction_date") == date(2021, 1, 7)).row(0, named=True)
    assert day_one["injury_next_3d"] is True
    assert day_four["injury_next_3d"] is False
    assert day_four["eligible_new_onset_3d"] is False
    assert day_seven["injury_next_7d"] is None
    assert day_seven["label_complete_7d"] is False
