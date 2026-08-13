"""Layered YAML configuration source for ``pydantic-settings``.

Configuration is split by responsibility:

* Versioned YAML holds analytical *behaviour* -- rolling windows, label horizons,
  episode-gap rules. These belong in Git because they change experiment results
  and must be reproducible from a commit hash alone.
* Environment variables hold deployment *identity* and secrets -- project IDs,
  bucket names, dataset names. These differ per environment and must never be
  committed.

Environment variables always take precedence over YAML, so a deployed job can
override any value without a code change.

Layers merge shallowly per section, in order:

    configs/base.yaml  ->  configs/<environment>.yaml  ->  environment variables

The active environment is read from ``PAA_ENV`` and defaults to ``local``.
The configuration directory is read from ``PAA_CONFIG_DIR`` and defaults to
``<repo root>/configs``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from player_availability.utils.paths import repo_root

DEFAULT_ENVIRONMENT = "local"
ENVIRONMENT_VARIABLE = "PAA_ENV"
CONFIG_DIR_VARIABLE = "PAA_CONFIG_DIR"
BASE_LAYER = "base"


def active_environment() -> str:
    """Return the configuration environment name currently in effect."""
    return os.environ.get(ENVIRONMENT_VARIABLE, DEFAULT_ENVIRONMENT).strip() or DEFAULT_ENVIRONMENT


def config_dir() -> Path:
    """Return the directory holding the YAML configuration layers."""
    override = os.environ.get(CONFIG_DIR_VARIABLE)
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "configs"


def _read_layer(path: Path) -> dict[str, Any]:
    """Read a single YAML layer, returning an empty mapping if it is absent or blank."""
    if not path.is_file():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise TypeError(f"Configuration layer {path} must contain a mapping at the top level.")
    return loaded


def load_section(section: str) -> dict[str, Any]:
    """Merge the base and environment layers and return one configuration section.

    Args:
        section: Top-level key to extract, for example ``"analysis"``.

    Returns:
        The merged mapping for that section. Empty if neither layer defines it.

    Raises:
        TypeError: If a layer is not a mapping, or the section is not a mapping.
    """
    directory = config_dir()
    merged: dict[str, Any] = {}
    for layer in (BASE_LAYER, active_environment()):
        layer_data = _read_layer(directory / f"{layer}.yaml")
        section_data = layer_data.get(section, {})
        if not isinstance(section_data, dict):
            raise TypeError(
                f"Section '{section}' in {directory / f'{layer}.yaml'} must be a mapping."
            )
        merged.update(section_data)
    return merged


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Supplies settings values from the merged YAML layers.

    Registered below the environment sources so that environment variables win.
    """

    section: str = ""

    def __init__(self, settings_cls: type[BaseSettings], section: str) -> None:
        super().__init__(settings_cls)
        self.section = section
        self._data: dict[str, Any] = load_section(section)

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return dict(self._data)
