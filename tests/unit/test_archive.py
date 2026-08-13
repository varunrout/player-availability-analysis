from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from player_availability.ingestion import inspect_zip_archive


def write_zip(path: Path, members: list[tuple[str, str]]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members:
            archive.writestr(name, content)


def test_inspect_zip_archive_returns_members_in_path_order(tmp_path: Path) -> None:
    archive_path = tmp_path / "source.zip"
    write_zip(archive_path, [("z/report.csv", "z"), ("a/report.csv", "abc")])

    inventory = inspect_zip_archive(archive_path)

    assert [member.path for member in inventory.members] == ["a/report.csv", "z/report.csv"]
    assert inventory.members[0].size_bytes == 3
    assert inventory.archive_size_bytes == archive_path.stat().st_size


@pytest.mark.parametrize("member_name", ["../outside.csv", "/absolute.csv"])
def test_inspect_zip_archive_rejects_unsafe_member_paths(tmp_path: Path, member_name: str) -> None:
    archive_path = tmp_path / "unsafe.zip"
    write_zip(archive_path, [(member_name, "content")])

    with pytest.raises(ValueError, match="path|root"):
        inspect_zip_archive(archive_path)


def test_inspect_zip_archive_rejects_duplicate_member_paths(tmp_path: Path) -> None:
    archive_path = tmp_path / "duplicate.zip"
    write_zip(archive_path, [("report.csv", "first"), ("report.csv", "second")])

    with pytest.raises(ValueError, match="duplicate"):
        inspect_zip_archive(archive_path)


def test_inspect_zip_archive_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        inspect_zip_archive(tmp_path / "missing.zip")
