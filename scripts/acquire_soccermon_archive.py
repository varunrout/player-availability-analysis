"""Acquire SoccerMon source archives from Zenodo into a Google Drive folder.

The archive is downloaded directly to the mounted Drive destination. It is not
staged in Cloud Storage or BigQuery. Interrupted downloads can resume from
their ``.part`` files, and the script records SHA-256 values for provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_RECORD_ID = "10033832"
CHUNK_SIZE_BYTES = 8 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        required=True,
        help=(
            "Existing Google Drive destination folder, for example "
            "G:\\My Drive\\Projects\\PlayerAvailabilityAnalysis\\raw"
        ),
    )
    parser.add_argument(
        "--record-id",
        default=DEFAULT_RECORD_ID,
        help=f"Zenodo record ID (default: {DEFAULT_RECORD_ID}).",
    )
    parser.add_argument(
        "--filename",
        action="append",
        default=[],
        help=(
            "Exact Zenodo filename to acquire. Repeat to select multiple files. "
            "Defaults to every record file."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List selected files and sizes without downloading.",
    )
    return parser.parse_args()


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request) as response:  # noqa: S310 - source is fixed to Zenodo.
        return json.load(response)


def file_digests(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE_BYTES):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()


def verify_source_checksum(source_checksum: str | None, actual_md5: str) -> None:
    if source_checksum is None:
        return
    algorithm, _, expected_md5 = source_checksum.partition(":")
    if algorithm.lower() != "md5" or not expected_md5:
        raise RuntimeError(f"Unsupported source checksum format: {source_checksum}")
    if actual_md5.lower() != expected_md5.lower():
        raise RuntimeError("Downloaded file does not match Zenodo's published MD5 checksum.")


def download_file(file_metadata: dict[str, Any], destination: Path) -> dict[str, Any]:
    filename = file_metadata["key"]
    expected_size = int(file_metadata["size"])
    final_path = destination / filename
    partial_path = destination / f"{filename}.part"

    if final_path.exists():
        actual_size = final_path.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(
                f"Existing file has an unexpected size: {final_path} "
                f"({actual_size} bytes, expected {expected_size})."
            )
        sha256, actual_md5 = file_digests(final_path)
        verify_source_checksum(file_metadata.get("checksum"), actual_md5)
        return {
            "filename": filename,
            "size_bytes": expected_size,
            "source_md5": file_metadata.get("checksum"),
            "sha256": sha256,
            "verified_md5": actual_md5,
            "status": "already_present",
        }

    existing_bytes = partial_path.stat().st_size if partial_path.exists() else 0
    if existing_bytes > expected_size:
        raise RuntimeError(f"Partial file is larger than expected: {partial_path}")

    headers = {"Range": f"bytes={existing_bytes}-"} if existing_bytes else {}
    content_url = file_metadata["links"]["content"]
    request = Request(content_url, headers=headers)

    try:
        with (
            urlopen(  # noqa: S310 - URL comes from Zenodo metadata.
                request
            ) as response,
            partial_path.open("ab") as target,
        ):
            if existing_bytes and response.status != 206:
                raise RuntimeError(
                    "Zenodo did not honour the range request; refusing to corrupt the partial file."
                )
            while chunk := response.read(CHUNK_SIZE_BYTES):
                target.write(chunk)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Download failed for {filename}: {error}") from error

    actual_size = partial_path.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(
            f"Download is incomplete for {filename}: {actual_size} bytes received, "
            f"expected {expected_size}. "
            "Re-run the script to resume."
        )

    sha256, actual_md5 = file_digests(partial_path)
    verify_source_checksum(file_metadata.get("checksum"), actual_md5)
    partial_path.replace(final_path)
    return {
        "filename": filename,
        "size_bytes": expected_size,
        "source_md5": file_metadata.get("checksum"),
        "sha256": sha256,
        "verified_md5": actual_md5,
        "status": "downloaded",
    }


def main() -> int:
    args = parse_args()
    if not args.destination.is_dir():
        print(f"Destination must be an existing directory: {args.destination}", file=sys.stderr)
        return 2

    record_url = f"https://zenodo.org/api/records/{args.record_id}"
    try:
        record = fetch_json(record_url)
    except (HTTPError, URLError) as error:
        print(f"Could not retrieve Zenodo record {args.record_id}: {error}", file=sys.stderr)
        return 1

    files = record.get("files", [])
    requested = set(args.filename)
    selected = [entry for entry in files if not requested or entry["key"] in requested]
    missing = requested - {entry["key"] for entry in selected}
    if missing:
        print(f"Requested filename(s) not found: {', '.join(sorted(missing))}", file=sys.stderr)
        return 2
    if not selected:
        print("Zenodo record contains no downloadable files.", file=sys.stderr)
        return 1

    total_size = sum(int(entry["size"]) for entry in selected)
    print(f"Selected {len(selected)} file(s), {total_size / 1_000_000_000:.2f} GB total.")
    for entry in selected:
        print(f"  {entry['key']} ({int(entry['size']) / 1_000_000_000:.2f} GB)")
    if args.dry_run:
        return 0

    acquired = []
    for entry in selected:
        print(f"Acquiring {entry['key']}...")
        acquired.append(download_file(entry, args.destination))

    manifest = {
        "source": "Zenodo",
        "record_id": args.record_id,
        "record_url": record_url,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "files": acquired,
    }
    manifest_path = args.destination / "soccermon_acquisition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Acquisition complete. Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
