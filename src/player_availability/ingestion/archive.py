"""Safe, deterministic archive inventory helpers.

The archive acquisition step preserves source ZIPs unchanged. This module only
inspects their metadata; extraction and source-specific parsing remain separate
steps that begin after schema review.
"""

from __future__ import annotations

import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    """Metadata for one non-directory member of a ZIP archive."""

    path: str
    size_bytes: int
    compressed_size_bytes: int
    crc32: str


@dataclass(frozen=True, slots=True)
class ArchiveInventory:
    """A deterministic inventory of a source archive without extracting it."""

    archive_path: Path
    archive_size_bytes: int
    members: tuple[ArchiveMember, ...]


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """The outcome of idempotently staging an archive into a raw directory."""

    inventory: ArchiveInventory
    destination_directory: Path
    written_paths: tuple[Path, ...]


def inspect_zip_archive(archive_path: Path) -> ArchiveInventory:
    """Return a safe, sorted inventory of a local ZIP archive.

    Archive member paths are validated before any later extraction is permitted.
    Rejecting traversal paths, Windows separators, symbolic links and duplicate
    names prevents an archive from silently producing an ambiguous file layout.
    """
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")

    with zipfile.ZipFile(archive_path) as archive:
        members = tuple(_to_member(info) for info in archive.infolist() if not info.is_dir())

    paths = [member.path for member in members]
    if len(paths) != len(set(paths)):
        raise ValueError(f"Archive contains duplicate member paths: {archive_path}")

    return ArchiveInventory(
        archive_path=archive_path,
        archive_size_bytes=archive_path.stat().st_size,
        members=tuple(sorted(members, key=lambda member: member.path)),
    )


def extract_zip_archive(archive_path: Path, destination_directory: Path) -> ExtractionResult:
    """Safely extract a ZIP to a raw staging directory.

    Existing files are accepted only when their bytes exactly match the archive.
    This makes retries idempotent while preventing a partial or changed prior run
    from being silently reused.
    """
    inventory = inspect_zip_archive(archive_path)
    destination_directory.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    with zipfile.ZipFile(archive_path) as archive:
        for member in inventory.members:
            destination_path = destination_directory.joinpath(*PurePosixPath(member.path).parts)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            contents = archive.read(member.path)
            if destination_path.exists():
                if destination_path.read_bytes() != contents:
                    raise ValueError(
                        f"Existing raw file differs from archive member: {destination_path}"
                    )
            else:
                destination_path.write_bytes(contents)
            written_paths.append(destination_path)

    return ExtractionResult(
        inventory=inventory,
        destination_directory=destination_directory,
        written_paths=tuple(written_paths),
    )


def _to_member(info: zipfile.ZipInfo) -> ArchiveMember:
    path = _validated_member_path(info.filename)
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise ValueError(f"Archive member is a symbolic link: {info.filename}")
    return ArchiveMember(
        path=path,
        size_bytes=info.file_size,
        compressed_size_bytes=info.compress_size,
        crc32=f"{info.CRC:08x}",
    )


def _validated_member_path(member_name: str) -> str:
    if not member_name or "\\" in member_name:
        raise ValueError(f"Archive member has an invalid path: {member_name!r}")
    path = PurePosixPath(member_name)
    if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
        raise ValueError(f"Archive member escapes its extraction root: {member_name!r}")
    return path.as_posix()
