"""Uploading a run's outputs to Cloud Storage.

Layout is customers/{customerId}/takeoffs/{takeoffId}/file_NN/page_NN/. The
file segment matters: a takeoff may carry several PDFs, and without it page 1
of the second drawing would overwrite page 1 of the first.

Content types are set explicitly. page.svg is loaded by the review UI as an
<img src>, and a browser will not render an SVG served as
application/octet-stream.
"""
from __future__ import annotations

import json
from pathlib import Path

from takeoff_fn import config

CONTENT_TYPES = {
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".png": "image/png",
    ".html": "text/html",
}
DEFAULT_CONTENT_TYPE = "application/octet-stream"


def run_prefix(customer_id: str, takeoff_id: str) -> str:
    return f"customers/{customer_id}/takeoffs/{takeoff_id}"


def page_prefix(prefix: str, file_index: int, page_number: int) -> str:
    return f"{prefix}/file_{file_index:02d}/page_{page_number:02d}"


def object_path(prefix: str, file_index: int, page_number: int,
                name: str) -> str:
    return f"{page_prefix(prefix, file_index, page_number)}/{name}"


def artifact_names(debug: bool) -> tuple[str, ...]:
    if debug:
        return config.STANDARD_ARTIFACTS + config.DEBUG_ARTIFACTS
    return config.STANDARD_ARTIFACTS


def _content_type(name: str) -> str:
    return CONTENT_TYPES.get(Path(name).suffix.lower(), DEFAULT_CONTENT_TYPE)


def _upload_file(bucket, local: Path, remote: str) -> None:
    bucket.blob(remote).upload_from_filename(
        str(local), content_type=_content_type(local.name))


def upload_page(bucket, page_dir: str, prefix: str, file_index: int,
                page_number: int, debug: bool) -> dict[str, str]:
    """Upload one page's artefacts. Absent files are skipped, not errors:
    page.svg only exists with write_svg, debug_* only with debug, and
    region_crops/ is absent on a classification cache hit."""
    uploaded: dict[str, str] = {}
    for name in artifact_names(debug):
        local = Path(page_dir) / name
        if not local.is_file():
            continue
        remote = object_path(prefix, file_index, page_number, name)
        _upload_file(bucket, local, remote)
        uploaded[name] = remote
    return uploaded


def upload_run_files(bucket, out_dir: str, prefix: str,
                     file_index: int) -> dict[str, str]:
    """summary.json and warnings.json live at the run root, and run_extract
    writes one run per source PDF, so they are stored under the file prefix."""
    uploaded: dict[str, str] = {}
    for name in config.RUN_ARTIFACTS:
        local = Path(out_dir) / name
        if not local.is_file():
            continue
        remote = f"{prefix}/file_{file_index:02d}/{name}"
        _upload_file(bucket, local, remote)
        uploaded[name] = remote
    return uploaded


def upload_json(bucket, prefix: str, name: str, payload) -> str:
    remote = f"{prefix}/{name}"
    bucket.blob(remote).upload_from_string(
        json.dumps(payload, indent=2, default=str),
        content_type="application/json")
    return remote
