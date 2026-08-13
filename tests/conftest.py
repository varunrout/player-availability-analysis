"""Shared test fixtures.

Tests must never depend on the developer's local ``.env`` or on the repository's
own ``configs/`` directory, otherwise a local change silently changes test
outcomes. The fixtures here supply an isolated configuration environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

GCP_ENVIRONMENT: dict[str, str] = {
    "GCP_PROJECT_ID": "test-project",
    "GCP_REGION": "europe-west2",
    "GCS_DATA_BUCKET": "test-data-bucket",
    "GCS_ARTIFACTS_BUCKET": "test-artifacts-bucket",
    "BQ_CORE_DATASET": "test_core",
    "BQ_ML_DATASET": "test_ml",
    "BQ_PRODUCT_DATASET": "test_product",
    "ARTIFACT_REGISTRY_REPOSITORY": "test-containers",
}

BASE_ANALYSIS: dict[str, Any] = {
    "injury_episode_gap_days": 3,
    "label_horizons_days": [3, 7, 14],
    "rolling_windows_days": [3, 7, 14, 28],
    "min_history_days": 28,
    "exclude_active_episode_days": True,
}


def write_layer(directory: Path, name: str, analysis: dict[str, Any]) -> Path:
    """Write a single YAML configuration layer and return its path."""
    path = directory / f"{name}.yaml"
    path.write_text(yaml.safe_dump({"analysis": analysis}), encoding="utf-8")
    return path


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated configuration directory containing only a base layer.

    Also clears any inherited ``PAA_ANALYSIS_*`` overrides and ``PAA_ENV`` so that
    YAML precedence can be asserted deterministically.
    """
    for key in [name for name in os.environ if name.startswith("PAA_ANALYSIS_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("PAA_ENV", raising=False)

    directory = tmp_path / "configs"
    directory.mkdir()
    write_layer(directory, "base", dict(BASE_ANALYSIS))
    monkeypatch.setenv("PAA_CONFIG_DIR", str(directory))
    return directory
