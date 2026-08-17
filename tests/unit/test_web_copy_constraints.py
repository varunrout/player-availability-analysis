"""Static scan enforcing DEC-064's copy constraints on the rendered web interface.

No diagnosis, clearance, fitness, injury-prediction or participation language may
appear anywhere in the rendered interface. This is a static text scan over the page
source rather than a rendered-DOM test, but it is automated and runs on every commit,
which is what `DEC-064` requires ("enforced by a test over the rendered copy, not by
review alone").

Also enforces the `DEC-063` fix: any screen displaying an operating-point burden must
display the held-out (`V1-P5`) figure alongside the development (`EXP-019`) figure,
never development alone.
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

WEB_SOURCE_ROOTS = (Path("web/app"), Path("web/components"))


def _page_source_files() -> list[Path]:
    files: list[Path] = []
    for root in WEB_SOURCE_ROOTS:
        if root.exists():
            files.extend(sorted(root.rglob("*.tsx")))
            files.extend(sorted(root.rglob("*.ts")))
    return files


def test_web_app_source_exists() -> None:
    files = _page_source_files()
    assert files, "expected web page source files to exist"


def test_no_prohibited_language_in_web_app_source() -> None:
    violations: list[str] = []
    for path in _page_source_files():
        text = path.read_text(encoding="utf-8").lower()
        for phrase in PROHIBITED_PHRASES:
            if phrase in text:
                violations.append(f"{path}: contains '{phrase}'")
    assert not violations, "\n".join(violations)


def test_operating_point_burden_never_shown_development_figure_alone() -> None:
    """DEC-063: any component rendering a development burden must also render the
    held-out (V1-P5) burden. Catches a regression that shows only the flattering
    development number without its held-out counterpart.
    """
    violations: list[str] = []
    for path in _page_source_files():
        text = path.read_text(encoding="utf-8")
        if "development_false_alerts_per_captured_onset" in text:
            if "held_out_false_alerts_per_captured_onset" not in text:
                violations.append(
                    f"{path}: renders the development burden without the held-out burden"
                )
    assert violations == [], "\n".join(violations)
