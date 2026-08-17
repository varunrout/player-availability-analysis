"""Mechanised claim-traceability gate (V1-P8, `DEC-046` exit criterion).

Every claim in `player_availability.claims.CLAIMS` must appear, verbatim
after whitespace normalisation, in both its citing document and its source
artefact (or reproduce its stated figure by computation from the source).
If a figure changes in either place without the other being updated, this
fails.
"""

from __future__ import annotations

import math

import pytest

from player_availability.claims import CLAIMS, Claim, resolve


def _normalized(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.parametrize("entry", CLAIMS, ids=[c.id for c in CLAIMS])
def test_claim_is_traceable(entry: Claim) -> None:
    location_path = resolve(entry.location)
    source_path = resolve(entry.source)

    assert location_path.is_file(), f"{entry.id}: citing file {entry.location} does not exist"
    assert source_path.is_file(), f"{entry.id}: source artefact {entry.source} does not exist"

    location_content = _normalized(location_path.read_text(encoding="utf-8"))
    assert _normalized(entry.location_text) in location_content, (
        f"{entry.id}: {entry.location_text!r} not found in {entry.location}"
    )

    if entry.source_text is not None:
        source_content = _normalized(source_path.read_text(encoding="utf-8"))
        assert _normalized(entry.source_text) in source_content, (
            f"{entry.id}: {entry.source_text!r} not found in {entry.source}"
        )
    else:
        assert entry.compute is not None, f"{entry.id}: neither source_text nor compute set"
        assert entry.expected is not None, f"{entry.id}: compute set without expected"
        actual = entry.compute(source_path)
        assert math.isclose(round(actual, entry.round_ndigits), entry.expected, rel_tol=1e-9), (
            f"{entry.id}: computed {actual} (rounded {round(actual, entry.round_ndigits)}) "
            f"!= expected {entry.expected} from {entry.source}"
        )


def test_every_claim_id_is_unique() -> None:
    ids = [entry.id for entry in CLAIMS]
    assert len(ids) == len(set(ids))


def test_claim_registry_is_nonempty() -> None:
    assert len(CLAIMS) >= 30
