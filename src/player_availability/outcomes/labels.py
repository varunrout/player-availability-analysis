"""Leak-safe player-day cohort and future self-reported injury-episode labels."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import polars as pl

DEFAULT_HORIZONS_DAYS = (3, 7, 14)
CUTOFF_CONVENTION = "end_of_calendar_day"


def build_player_day_labels(
    player_registry: pl.DataFrame,
    injury_episodes: pl.DataFrame,
    *,
    horizons_days: tuple[int, ...] = DEFAULT_HORIZONS_DAYS,
) -> pl.DataFrame:
    """Build observed player-days with complete-horizon, post-cutoff episode labels.

    Same-day data is assumed known at the end-of-day cutoff. An episode beginning on
    ``prediction_date`` is therefore not a future label. Labels are null when a horizon
    reaches beyond the player's observed end date; active-episode days remain visible but
    are marked ineligible for new-onset modelling.
    """
    if not horizons_days or any(horizon <= 0 for horizon in horizons_days):
        raise ValueError("horizons_days must contain positive integers")
    players = player_registry.select(
        "player_id", "team_id", "observation_start", "observation_end"
    ).sort("player_id")
    days = _expand_player_days(players)
    episodes_by_player: dict[str, list[dict[str, Any]]] = {}
    for episode in injury_episodes.sort("episode_start").to_dicts():
        episodes_by_player.setdefault(str(episode["player_id"]), []).append(episode)
    rows: list[dict[str, object]] = []
    for player in players.to_dicts():
        player_id = str(player["player_id"])
        observation_end = player["observation_end"]
        assert isinstance(observation_end, date)
        episodes = episodes_by_player.get(player_id, [])
        prediction_dates = days.filter(pl.col("player_id") == player_id).get_column(
            "prediction_date"
        )
        for prediction_date in prediction_dates:
            assert isinstance(prediction_date, date)
            active_episode = any(
                _episode_active_on(episode, prediction_date) for episode in episodes
            )
            row: dict[str, object] = {
                "player_id": player_id,
                "team_id": player["team_id"],
                "prediction_date": prediction_date,
                "prediction_cutoff": CUTOFF_CONVENTION,
                "observation_end": observation_end,
                "active_injury_episode": active_episode,
            }
            for horizon in horizons_days:
                horizon_end = prediction_date + timedelta(days=horizon)
                complete = horizon_end <= observation_end
                row[f"label_complete_{horizon}d"] = complete
                row[f"injury_next_{horizon}d"] = (
                    any(
                        _episode_starts_within(episode, prediction_date, horizon_end)
                        for episode in episodes
                    )
                    if complete
                    else None
                )
                row[f"eligible_new_onset_{horizon}d"] = complete and not active_episode
            rows.append(row)
    return pl.DataFrame(rows).sort("player_id", "prediction_date")


def _expand_player_days(players: pl.DataFrame) -> pl.DataFrame:
    return players.select(
        "player_id",
        pl.date_ranges("observation_start", "observation_end", interval="1d", closed="both").alias(
            "prediction_date"
        ),
    ).explode("prediction_date", empty_as_null=True)


def _episode_active_on(episode: dict[str, Any], prediction_date: date) -> bool:
    episode_start = episode["episode_start"]
    episode_end = episode["episode_end"]
    assert isinstance(episode_start, date)
    assert isinstance(episode_end, date)
    return episode_start <= prediction_date <= episode_end


def _episode_starts_within(
    episode: dict[str, Any], prediction_date: date, horizon_end: date
) -> bool:
    episode_start = episode["episode_start"]
    assert isinstance(episode_start, date)
    return prediction_date < episode_start <= horizon_end
