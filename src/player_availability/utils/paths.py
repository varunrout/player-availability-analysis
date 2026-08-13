"""Filesystem location helpers.

Configuration and data paths must resolve identically regardless of the working
directory a job is launched from, so nothing here depends on ``os.getcwd()``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ROOT_MARKER = "pyproject.toml"


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root, located by walking up to the project marker.

    Raises:
        RuntimeError: If no ``pyproject.toml`` is found in any parent directory,
            which means the package is installed outside a source checkout and
            the caller must supply paths explicitly.
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / _ROOT_MARKER).is_file():
            return candidate
    raise RuntimeError(
        f"Could not locate {_ROOT_MARKER} in any parent of {Path(__file__).resolve()}. "
        "Supply configuration and data paths explicitly when running outside a source checkout."
    )
