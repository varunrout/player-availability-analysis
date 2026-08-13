"""Typed runtime settings.

All configuration is validated at process start so that a misconfigured job
fails immediately with a clear message rather than part-way through a pipeline
run that has already written data.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from player_availability.config.yaml_source import YamlSettingsSource, active_environment
from player_availability.utils.paths import repo_root


class GcpSettings(BaseSettings):
    """Cloud deployment identity, supplied entirely by the environment.

    Values are never committed. Authentication uses Application Default
    Credentials; no service-account key material is read or written here.
    """

    model_config = SettingsConfigDict(
        env_file=repo_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    project_id: str = Field(alias="GCP_PROJECT_ID", min_length=1)
    region: str = Field(alias="GCP_REGION", min_length=1)
    data_bucket: str = Field(alias="GCS_DATA_BUCKET", min_length=1)
    artifacts_bucket: str = Field(alias="GCS_ARTIFACTS_BUCKET", min_length=1)
    bq_core_dataset: str = Field(alias="BQ_CORE_DATASET", min_length=1)
    bq_ml_dataset: str = Field(alias="BQ_ML_DATASET", min_length=1)
    bq_product_dataset: str = Field(alias="BQ_PRODUCT_DATASET", min_length=1)
    artifact_registry_repository: str = Field(alias="ARTIFACT_REGISTRY_REPOSITORY", min_length=1)


class AnalysisSettings(BaseSettings):
    """Analytical behaviour, supplied by versioned YAML and overridable by the environment.

    These values change experiment results, so they are held in Git and recorded
    against every run. Provisional values are marked in ``configs/base.yaml`` and
    are frozen only once the corresponding sensitivity experiment has been run.
    """

    model_config = SettingsConfigDict(
        env_prefix="PAA_ANALYSIS_",
        extra="forbid",
        frozen=True,
    )

    injury_episode_gap_days: int = Field(
        ge=1,
        le=30,
        description="Event-free days required before a new injury episode is counted.",
    )
    label_horizons_days: tuple[int, ...] = Field(
        description="Forward windows, in days, for new-onset classification labels."
    )
    rolling_windows_days: tuple[int, ...] = Field(
        description="Trailing windows, in days, for rolling load and wellness features."
    )
    min_history_days: int = Field(
        ge=0,
        description="Minimum observed history before a player-day is eligible for modelling.",
    )
    exclude_active_episode_days: bool = Field(
        description="Whether player-days inside an active injury episode are excluded "
        "from the new-onset model."
    )

    @field_validator("label_horizons_days", "rolling_windows_days")
    @classmethod
    def _positive_and_ascending(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value:
            raise ValueError("must contain at least one window")
        if any(window <= 0 for window in value):
            raise ValueError("all windows must be positive")
        if list(value) != sorted(value):
            raise ValueError("windows must be listed in ascending order")
        if len(set(value)) != len(value):
            raise ValueError("windows must be unique")
        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order sources by descending priority: explicit arguments, environment, then YAML."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlSettingsSource(settings_cls, section="analysis"),
        )


class Settings(BaseModel):
    """Fully validated runtime configuration for a single process."""

    model_config = {"frozen": True}

    environment: str
    gcp: GcpSettings
    analysis: AnalysisSettings


def build_settings() -> Settings:
    """Construct and validate settings from the environment and YAML layers."""
    return Settings(
        environment=active_environment(),
        gcp=GcpSettings(),  # type: ignore[call-arg]
        analysis=AnalysisSettings(),  # type: ignore[call-arg]
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, constructing them on first use."""
    return build_settings()
