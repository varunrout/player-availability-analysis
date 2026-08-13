"""Prepare and submit a managed SoccerMon archive transfer into Cloud Storage.

The script creates a checksum-bearing URL list for Storage Transfer Service.
The service then copies the public Zenodo files directly to Cloud Storage, so
the workstation does not need local disk capacity or a mounted Drive path.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_PROJECT_ID = "player-availability-analysis"
DEFAULT_BUCKET = "paa-data-979927072833"
DEFAULT_RECORD_ID = "10033832"
DEFAULT_DESTINATION_PREFIX = "raw/source_archives/soccermon/zenodo-10033832/"
DEFAULT_MANIFEST_OBJECT = "metadata/transfer_manifests/soccermon/zenodo-10033832.tsv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--record-id", default=DEFAULT_RECORD_ID)
    parser.add_argument("--destination-prefix", default=DEFAULT_DESTINATION_PREFIX)
    parser.add_argument("--manifest-object", default=DEFAULT_MANIFEST_OBJECT)
    parser.add_argument(
        "--filename",
        action="append",
        default=[],
        help="Exact Zenodo filename to transfer. Repeat to select multiple files.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Upload the URL list and create a one-time Storage Transfer Service job.",
    )
    parser.add_argument(
        "--gcloud-command",
        default="gcloud",
        help="Path or command name for gcloud. Defaults to gcloud on PATH.",
    )
    return parser.parse_args()


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request) as response:  # noqa: S310 - source is fixed to Zenodo.
        return json.load(response)


def select_files(record: dict[str, Any], filenames: list[str]) -> list[dict[str, Any]]:
    requested = set(filenames)
    selected = [
        entry for entry in record.get("files", []) if not requested or entry["key"] in requested
    ]
    missing = requested - {entry["key"] for entry in selected}
    if missing:
        raise ValueError(f"Requested filename(s) not found: {', '.join(sorted(missing))}")
    if not selected:
        raise ValueError("Zenodo record contains no downloadable files.")
    return selected


def zenodo_download_url(record_id: str, filename: str) -> str:
    return f"https://zenodo.org/records/{record_id}/files/{quote(filename)}?download=1"


def manifest_row(record_id: str, file_metadata: dict[str, Any]) -> tuple[str, int, str]:
    source_checksum = file_metadata.get("checksum", "")
    algorithm, _, hex_digest = source_checksum.partition(":")
    if algorithm.lower() != "md5" or len(hex_digest) != 32:
        raise ValueError(
            f"Unsupported Zenodo checksum format for {file_metadata['key']}: {source_checksum}"
        )
    md5_base64 = base64.b64encode(bytes.fromhex(hex_digest)).decode("ascii")
    return (
        zenodo_download_url(record_id, file_metadata["key"]),
        int(file_metadata["size"]),
        md5_base64,
    )


def write_url_list(path: Path, record_id: str, files: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(["TsvHttpData-1.0"])
        for file_metadata in sorted(
            files,
            key=lambda entry: zenodo_download_url(record_id, entry["key"]),
        ):
            writer.writerow(manifest_row(record_id, file_metadata))


def run(command: list[str]) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


def gcloud_access_token(gcloud_command: str) -> str:
    return subprocess.check_output(
        [gcloud_command, "auth", "print-access-token"],
        text=True,
    ).strip()


def post_json(
    url: str,
    payload: dict[str, Any],
    access_token: str,
    quota_project: str,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-goog-user-project": quota_project,
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:  # noqa: S310 - fixed Google API endpoint.
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Storage Transfer API returned HTTP {error.code}: {details}") from error


def main() -> int:
    args = parse_args()
    record_url = f"https://zenodo.org/api/records/{args.record_id}"
    try:
        files = select_files(fetch_json(record_url), args.filename)
    except (HTTPError, URLError, ValueError) as error:
        print(f"Could not prepare SoccerMon transfer: {error}", file=sys.stderr)
        return 1

    total_size = sum(int(entry["size"]) for entry in files)
    destination_uri = f"gs://{args.bucket}/{args.destination_prefix.lstrip('/')}"
    manifest_uri = f"gs://{args.bucket}/{args.manifest_object.lstrip('/')}"
    print(f"Selected {len(files)} file(s), {total_size / 1_000_000_000:.2f} GB total.")
    print(f"Destination: {destination_uri}")
    print(f"URL list: {manifest_uri}")
    for entry in files:
        print(f"  {entry['key']} ({int(entry['size']) / 1_000_000_000:.2f} GB)")

    if not args.submit:
        print("Dry run only. Re-run with --submit to create the managed transfer job.")
        return 0

    with tempfile.TemporaryDirectory(prefix="soccermon-transfer-") as temporary_directory:
        url_list = Path(temporary_directory) / "soccermon-url-list.tsv"
        write_url_list(url_list, args.record_id, files)
        try:
            run(
                [
                    args.gcloud_command,
                    "storage",
                    "cp",
                    str(url_list),
                    manifest_uri,
                    f"--project={args.project_id}",
                ]
            )
            access_token = gcloud_access_token(args.gcloud_command)
            job = post_json(
                "https://storagetransfer.googleapis.com/v1/transferJobs",
                {
                    "projectId": args.project_id,
                    "description": "One-time SoccerMon Zenodo archive acquisition",
                    "status": "ENABLED",
                    "transferSpec": {
                        "httpDataSource": {"listUrl": manifest_uri},
                        "gcsDataSink": {
                            "bucketName": args.bucket,
                            "path": args.destination_prefix.lstrip("/"),
                        },
                        "transferOptions": {"overwriteWhen": "NEVER"},
                    },
                },
                access_token,
                args.project_id,
            )
            operation = post_json(
                f"https://storagetransfer.googleapis.com/v1/{job['name']}:run",
                {"projectId": args.project_id},
                access_token,
                args.project_id,
            )
        except (RuntimeError, URLError, subprocess.CalledProcessError) as error:
            print(f"Transfer job submission failed: {error}", file=sys.stderr)
            return getattr(error, "returncode", 1) or 1

    print(f"Transfer job created: {job['name']}")
    print(f"Transfer operation started: {operation['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
