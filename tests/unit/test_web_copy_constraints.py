"""Static scan enforcing DEC-064's copy constraints on the rendered web interface.

No diagnosis, clearance, fitness, injury-prediction or participation language may
appear anywhere in the rendered interface. This is a static text scan over the page
source rather than a rendered-DOM test, but it is automated and runs on every commit,
which is what `DEC-064` requires ("enforced by a test over the rendered copy, not by
review alone").
"""

from __future__ import annotations

from pathlib import Path

PROHIBITED_PHRASES = (
    "diagnos",
    "clearance",
    "clear to play",
    "cleared to play",
    "fitness",
    "fit to play",
    "injury prediction",
    "predicts injury",
    "predicted injury",
    "participation advice",
    "return to play",
    "medical advice",
)

WEB_APP_ROOT = Path("web/app")


def _page_source_files() -> list[Path]:
    return sorted(WEB_APP_ROOT.rglob("*.tsx")) + sorted(WEB_APP_ROOT.rglob("*.ts"))


def test_web_app_source_exists() -> None:
    files = _page_source_files()
    assert files, "expected web/app page source files to exist"


def test_no_prohibited_language_in_web_app_source() -> None:
    violations: list[str] = []
    for path in _page_source_files():
        text = path.read_text(encoding="utf-8").lower()
        for phrase in PROHIBITED_PHRASES:
            if phrase in text:
                violations.append(f"{path}: contains '{phrase}'")
    assert not violations, "\n".join(violations)
