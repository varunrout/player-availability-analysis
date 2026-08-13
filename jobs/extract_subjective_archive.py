"""Safely stage the verified SoccerMon subjective ZIP into a local raw directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from player_availability.ingestion import extract_zip_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, required=True, help="Verified local subjective ZIP path"
    )
    parser.add_argument(
        "--destination", type=Path, required=True, help="Local raw staging directory"
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    result = extract_zip_archive(args.archive, args.destination)
    manifest = {
        "archive_path": str(result.inventory.archive_path),
        "archive_sha256": sha256(result.inventory.archive_path),
        "archive_size_bytes": result.inventory.archive_size_bytes,
        "member_count": len(result.inventory.members),
        "members": [
            {
                "path": member.path,
                "size_bytes": member.size_bytes,
                "compressed_size_bytes": member.compressed_size_bytes,
                "crc32": member.crc32,
            }
            for member in result.inventory.members
        ],
    }
    manifest_path = result.destination_directory / "_extraction_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Extracted {len(result.written_paths)} files to {result.destination_directory}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
