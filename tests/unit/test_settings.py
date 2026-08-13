"""Tests for the layered configuration system.

The behaviour under test is the precedence contract: versioned YAML supplies
analytical behaviour, the environment supplies deployment identity, and the
environment always wins where both define a value. Deployments depend on that
rule, so it is asserted directly rather than assumed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from player_availability.config import yaml_source
from player_availability.config.settings import AnalysisSettings, GcpSettings, build_settings
from tests.conftest import BASE_ANALYSIS, GCP_ENVIRONMENT, write_layer


class TestYamlLayers:
    def test_base_layer_supplies_values(self, config_dir: Path) -> None:
        settings = AnalysisSettings()  # type: ignore[call-arg]

        assert settings.injury_episode_gap_days == BASE_ANALYSIS["injury_episode_gap_days"]
        assert settings.label_horizons_days == (3, 7, 14)
        assert settings.rolling_windows_days == (3, 7, 14, 28)
        assert settings.min_history_days == 28
        assert settings.exclude_active_episode_days is True

    def test_environment_layer_overrides_base(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_layer(config_dir, "dev", {"injury_episode_gap_days": 7})
        monkeypatch.setenv("PAA_ENV", "dev")

        settings = AnalysisSettings()  # type: ignore[call-arg]

        assert settings.injury_episode_gap_days == 7
        # Keys the environment layer does not mention still come from base.
        assert settings.min_history_days == 28

    def test_missing_environment_layer_is_not_an_error(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PAA_ENV", "does-not-exist")

        settings = AnalysisSettings()  # type: ignore[call-arg]

        assert settings.injury_episode_gap_days == 3

    def test_non_mapping_section_is_rejected(self, config_dir: Path) -> None:
        (config_dir / "base.yaml").write_text("analysis: [1, 2, 3]\n", encoding="utf-8")

        with pytest.raises(TypeError, match="must be a mapping"):
            yaml_source.load_section("analysis")

    def test_non_mapping_layer_is_rejected(self, config_dir: Path) -> None:
        (config_dir / "base.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")

        with pytest.raises(TypeError, match="mapping at the top level"):
            yaml_source.load_section("analysis")

    def test_blank_layer_is_tolerated(self, config_dir: Path) -> None:
        (config_dir / "base.yaml").write_text("", encoding="utf-8")

        assert yaml_source.load_section("analysis") == {}

    def test_active_environment_defaults_to_local(self, config_dir: Path) -> None:
        assert yaml_source.active_environment() == "local"

    def test_config_dir_honours_override(self, config_dir: Path) -> None:
        assert yaml_source.config_dir() == config_dir.resolve()


class TestEnvironmentPrecedence:
    def test_environment_variable_overrides_yaml(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PAA_ANALYSIS_INJURY_EPISODE_GAP_DAYS", "1")

        settings = AnalysisSettings()  # type: ignore[call-arg]

        assert settings.injury_episode_gap_days == 1

    def test_environment_variable_overrides_environment_layer(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_layer(config_dir, "dev", {"min_history_days": 14})
        monkeypatch.setenv("PAA_ENV", "dev")
        monkeypatch.setenv("PAA_ANALYSIS_MIN_HISTORY_DAYS", "56")

        settings = AnalysisSettings()  # type: ignore[call-arg]

        assert settings.min_history_days == 56


class TestValidation:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("injury_episode_gap_days", 0),
            ("injury_episode_gap_days", 31),
            ("min_history_days", -1),
        ],
    )
    def test_out_of_range_values_are_rejected(
        self, config_dir: Path, field: str, value: int
    ) -> None:
        overrides = dict(BASE_ANALYSIS)
        overrides[field] = value
        write_layer(config_dir, "base", overrides)

        with pytest.raises(ValidationError):
            AnalysisSettings()  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        ("windows", "message"),
        [
            ([], "at least one window"),
            ([7, 3], "ascending order"),
            ([3, 3, 7], "unique"),
            ([0, 7], "positive"),
        ],
    )
    def test_window_lists_are_validated(
        self, config_dir: Path, windows: list[int], message: str
    ) -> None:
        overrides = dict(BASE_ANALYSIS)
        overrides["rolling_windows_days"] = windows
        write_layer(config_dir, "base", overrides)

        with pytest.raises(ValidationError, match=message):
            AnalysisSettings()  # type: ignore[call-arg]

    def test_unknown_key_is_rejected(self, config_dir: Path) -> None:
        overrides = dict(BASE_ANALYSIS)
        overrides["unsupported_option"] = 1
        write_layer(config_dir, "base", overrides)

        with pytest.raises(ValidationError):
            AnalysisSettings()  # type: ignore[call-arg]

    def test_missing_required_value_is_rejected(self, config_dir: Path) -> None:
        overrides = dict(BASE_ANALYSIS)
        del overrides["injury_episode_gap_days"]
        write_layer(config_dir, "base", overrides)

        with pytest.raises(ValidationError):
            AnalysisSettings()  # type: ignore[call-arg]

    def test_analysis_settings_are_immutable(self, config_dir: Path) -> None:
        settings = AnalysisSettings()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            settings.min_history_days = 7


class TestGcpSettings:
    def test_loads_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key, value in GCP_ENVIRONMENT.items():
            monkeypatch.setenv(key, value)

        settings = GcpSettings()  # type: ignore[call-arg]

        assert settings.project_id == "test-project"
        assert settings.region == "europe-west2"
        assert settings.data_bucket == "test-data-bucket"
        assert settings.bq_core_dataset == "test_core"

    def test_settings_are_immutable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key, value in GCP_ENVIRONMENT.items():
            monkeypatch.setenv(key, value)

        settings = GcpSettings()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            settings.project_id = "changed"


class TestBuildSettings:
    def test_builds_a_complete_object(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key, value in GCP_ENVIRONMENT.items():
            monkeypatch.setenv(key, value)

        settings = build_settings()

        assert settings.environment == "local"
        assert settings.gcp.project_id == "test-project"
        assert settings.analysis.injury_episode_gap_days == 3
        assert settings.analysis.label_horizons_days == (3, 7, 14)
