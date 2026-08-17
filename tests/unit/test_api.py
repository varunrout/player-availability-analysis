from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from player_availability.product.batch_inference import BatchInferenceConfig, run_batch_inference
from tests.unit.test_m1_logistic import _config
from tests.unit.test_stage_07_prospective_protocol import _inputs


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    features, episodes = _inputs()
    result = run_batch_inference(
        features=features,
        episodes=episodes,
        config=BatchInferenceConfig(base_config=_config()),
    )
    result.predictions.write_parquet(tmp_path / "paa_product_serving_artifact.parquet")
    result.onset_calendar.write_parquet(tmp_path / "paa_product_onset_calendar.parquet")
    (tmp_path / "paa_product_serving_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True, default=str) + "\n"
    )
    monkeypatch.setenv("PAA_SERVING_ARTIFACT_DIR", str(tmp_path))

    from player_availability.api.app import app, get_artifact, get_model_health_reference

    get_artifact.cache_clear()
    get_model_health_reference.cache_clear()
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_covered_period_lists_teams_and_date_bounds(client: TestClient) -> None:
    response = client.get("/covered-period")
    assert response.status_code == 200
    body = response.json()
    assert len(body["team_ids"]) > 0
    assert body["covered_date_start"] <= body["covered_date_end"]
    assert body["default_as_at_date"] == body["covered_date_end"]


def test_squad_overview_returns_ranked_players_with_operating_point(client: TestClient) -> None:
    probe = client.get("/model-health")
    assert probe.status_code == 200
    as_at_date = probe.json()["as_at_date"]

    from player_availability.api.app import get_artifact

    artifact = get_artifact()
    team_id = artifact.predictions.filter(
        artifact.predictions["prediction_date"] == date.fromisoformat(as_at_date)
    )["team_id"][0]

    response = client.get("/squad-overview", params={"team_id": team_id, "date": as_at_date})
    assert response.status_code == 200
    body = response.json()
    assert body["team_id"] == team_id
    assert body["as_at_date"] == as_at_date
    assert body["operating_point"]["review_rate"] == 0.025
    assert len(body["players"]) > 0
    ranks = [player["rank_within_team_day"] for player in body["players"]]
    assert ranks == sorted(ranks)


def test_squad_overview_operating_point_includes_held_out_figure_not_development_alone(
    client: TestClient,
) -> None:
    # DEC-063 fix: a screen showing an operating-point burden must show the V1-P5
    # held-out figure alongside the EXP-019 development figure, never development
    # alone, so a reviewer cannot see one number here and a different one in the
    # model card with nothing reconciling them.
    from player_availability.api.app import get_artifact

    artifact = get_artifact()
    team_id = artifact.predictions["team_id"][0]

    response = client.get("/squad-overview", params={"team_id": team_id})
    assert response.status_code == 200
    operating_point = response.json()["operating_point"]
    assert operating_point["development_false_alerts_per_captured_onset"] is not None
    assert operating_point["held_out_false_alerts_per_captured_onset"] is not None
    assert operating_point["held_out_realised_alert_rate"] is not None
    assert operating_point["held_out_represented_onsets"] == 5
    # The held-out figure is the real (worse) number; it must not be silently equal
    # to the development figure, which would indicate the wrong table was wired up.
    assert (
        operating_point["held_out_false_alerts_per_captured_onset"]
        != operating_point["development_false_alerts_per_captured_onset"]
    )


def test_squad_overview_unknown_team_returns_404(client: TestClient) -> None:
    response = client.get("/squad-overview", params={"team_id": "NoSuchTeam"})
    assert response.status_code == 404


def test_player_detail_returns_series_and_displayable_drivers_only(client: TestClient) -> None:
    from player_availability.api.app import get_artifact

    artifact = get_artifact()
    player_id = artifact.predictions["player_id"][0]

    response = client.get("/player-detail", params={"player_id": player_id})
    assert response.status_code == 200
    body = response.json()
    assert body["player_id"] == player_id
    assert len(body["risk_series"]) > 0
    driver_names = {driver["predictor"] for driver in body["driver_contributions"]}
    assert "daily_load_log1p" not in driver_names
    assert len(driver_names) == 8


def test_player_detail_reports_onset_dates_absent_from_risk_series() -> None:
    """P1's fixture episodes (2020-08-10, 2021-09-10) must appear as onset_dates
    even though neither date is ever a scored player-day (DEC-064 fix: the onset
    day itself is always ineligible for scoring)."""
    from player_availability.api.app import app, get_artifact, get_model_health_reference
    from player_availability.product.batch_inference import (
        BatchInferenceConfig,
        run_batch_inference,
    )

    features, episodes = _inputs()
    result = run_batch_inference(
        features=features, episodes=episodes, config=BatchInferenceConfig(base_config=_config())
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result.predictions.write_parquet(tmp_path / "paa_product_serving_artifact.parquet")
            result.onset_calendar.write_parquet(tmp_path / "paa_product_onset_calendar.parquet")
            (tmp_path / "paa_product_serving_manifest.json").write_text(
                json.dumps(result.summary, indent=2, sort_keys=True, default=str) + "\n"
            )
            monkeypatch.setenv("PAA_SERVING_ARTIFACT_DIR", str(tmp_path))
            get_artifact.cache_clear()
            get_model_health_reference.cache_clear()
            local_client = TestClient(app)

            response = local_client.get("/player-detail", params={"player_id": "P1"})
            assert response.status_code == 200
            body = response.json()
            assert set(body["onset_dates"]) == {"2020-08-10", "2021-09-10"}
            risk_series_dates = {point["prediction_date"] for point in body["risk_series"]}
            assert risk_series_dates.isdisjoint(body["onset_dates"])
    get_artifact.cache_clear()
    get_model_health_reference.cache_clear()


def test_data_quality_returns_coverage_series(client: TestClient) -> None:
    from player_availability.api.app import get_artifact

    artifact = get_artifact()
    team_id = artifact.predictions["team_id"][0]

    response = client.get("/data-quality", params={"team_id": team_id})
    assert response.status_code == 200
    body = response.json()
    assert body["team_id"] == team_id
    assert len(body["coverage_over_time"]) > 0
    assert len(body["player_coverage_range"]) > 0
    assert len(body["onsets_by_year"]) > 0
    assert body["onset_decline_note"]
    represented_onsets = {row["year"]: row["represented_onsets"] for row in body["onsets_by_year"]}
    # Fixture episodes (test_stage_07_prospective_protocol._inputs): one onset in
    # 2020, two in 2021 across the whole cohort.
    assert represented_onsets.get(2020) == 1
    assert represented_onsets.get(2021) == 2


def test_model_health_reports_calibration_and_final_test_result(client: TestClient) -> None:
    response = client.get("/model-health")
    assert response.status_code == 200
    body = response.json()
    assert body["calibration"]["mean_prediction"] > 0
    assert len(body["reliability_bins"]) > 0
    assert all("bin_supported" in row for row in body["reliability_bins"])
    assert len(body["operating_points"]) == 2
    assert len(body["held_out_operating_points"]) == 2
    assert body["final_test_result"]["player_days"] > 0
    claim_ids = {claim["claim_id"] for claim in body["final_test_result"]["claims"]}
    assert claim_ids == {"C1", "C2", "C3"}
    assert "not a performance claim" in body["final_test_result"]["interpretation"]
    c3_claim = next(
        claim for claim in body["final_test_result"]["claims"] if claim["claim_id"] == "C3"
    )
    assert c3_claim["supported"] is False
    assert "not supported" in body["final_test_result"]["c3_explanation"]
    assert "onset density" in body["final_test_result"]["c3_explanation"]
