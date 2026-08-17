from __future__ import annotations

from pathlib import Path

import polars as pl

from player_availability.modelling.preprocessing import F1_FEATURES
from player_availability.product.batch_inference import (
    DISPLAYABLE_DRIVERS,
    BatchInferenceConfig,
    load_batch_inference_config,
    reconcile_outputs,
    run_batch_inference,
)
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


def _batch_inference_config() -> BatchInferenceConfig:
    return BatchInferenceConfig(base_config=_config())


def test_batch_inference_scores_every_eligible_player_day() -> None:
    features, episodes = _inputs()

    result = run_batch_inference(
        features=features, episodes=episodes, config=_batch_inference_config()
    )

    predictions = result.predictions
    assert predictions.height > 0
    assert predictions["predicted_probability"].is_between(0.0, 1.0).all()
    assert set(DISPLAYABLE_DRIVERS) == set(F1_FEATURES) - {"daily_load_log1p"}
    for driver in DISPLAYABLE_DRIVERS:
        assert f"driver_{driver}" in predictions.columns
    assert "driver_daily_load_log1p" not in predictions.columns
    assert predictions["data_completeness"].is_between(0.0, 1.0).all()
    assert (predictions["rank_within_team_day"] >= 1).all()
    assert "alert_0.025" in predictions.columns
    assert "alert_0.05" in predictions.columns
    assert "is_onset_date" in predictions.columns
    assert predictions["is_onset_date"].dtype == pl.Boolean
    # Rank within team-day never exceeds the number of players in that team-day.
    team_day_sizes = predictions.group_by(["team_id", "prediction_date"]).agg(
        pl.len().alias("size")
    )
    joined = predictions.join(team_day_sizes, on=["team_id", "prediction_date"])
    assert (joined["rank_within_team_day"] <= joined["size"]).all()


def test_batch_inference_reconciliation_passes_for_identical_frames() -> None:
    features, episodes = _inputs()
    result = run_batch_inference(
        features=features, episodes=episodes, config=_batch_inference_config()
    )

    reconciliation = reconcile_outputs(result.predictions, result.predictions)

    assert reconciliation["reconciled"] is True
    assert reconciliation["row_count_matches"] is True
    assert reconciliation["key_sets_match"] is True
    assert reconciliation["value_mismatch_count"] == 0


def test_batch_inference_reconciliation_fails_on_divergence() -> None:
    features, episodes = _inputs()
    result = run_batch_inference(
        features=features, episodes=episodes, config=_batch_inference_config()
    )

    truncated = result.predictions.head(result.predictions.height - 1)

    reconciliation = reconcile_outputs(result.predictions, truncated)

    assert reconciliation["reconciled"] is False
    assert reconciliation["row_count_matches"] is False


def test_batch_inference_config_contract() -> None:
    config = load_batch_inference_config(Path("configs/product/batch_inference.yaml"))
    assert config.base_config.feature_set == "F1"
