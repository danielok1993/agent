"""Fetching the drawings a takeoff points at.

The tenant boundary here is the same one rivet-mind enforces on downloads
(functions/src/estimates/attachment-download.ts:89-95): an object path is only
readable if it actually sits under the calling tenant's segment. The record
itself is tenant-checked before we get here, but a storageUrl is data a client
wrote, so it is checked again rather than trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from takeoff_fn.errors import InvalidArgument, PermissionDenied
from takeoff_fn.records import SourceFile

GS_SCHEME = "gs://"

# The tenant-scoped roots a source path may sit under. rivet-mind writes
# uploads under three roots — estimate_images/{customerId}/{estimateId}/…,
# estimate_documents/{customerId}/{estimateId}/… (its storage.rules home for
# application/pdf, the natural home for a drawing PDF) and
# estimate_videos/{customerId}/{estimateId}/… — plus customers/{customerId}/…,
# this function's OWN output prefix (customers/{customerId}/takeoffs/{takeoffId}/…).
# All four put the tenant in the SECOND segment. The allowlist is not just
# "does the tenant appear" — assert_customer_scoped anchors the tenant to the
# segment immediately after one of these roots, so a tenant id appearing
# anywhere else in the path (another tenant's subfolder, a filename, an
# unlisted root) cannot satisfy it.
CUSTOMER_PATH_PREFIXES = (
    "estimate_images", "estimate_documents", "estimate_videos", "customers")


@dataclass(frozen=True)
class DownloadedSource:
    index: int
    file_name: str
    local_path: str


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not isinstance(uri, str) or not uri.startswith(GS_SCHEME):
        raise InvalidArgument(f"Not a gs:// URI: {uri!r}")
    remainder = uri[len(GS_SCHEME):]
    bucket, _, object_path = remainder.partition("/")
    if not bucket or not object_path:
        raise InvalidArgument(f"Incomplete gs:// URI: {uri!r}")
    return bucket, object_path


def assert_customer_scoped(object_path: str, customer_id: str) -> None:
    """The tenant must own the path at the position tenants are written at.

    Anchored, not "appears somewhere": the tenant has to be the segment
    directly after one of CUSTOMER_PATH_PREFIXES. An unanchored membership
    test passes on a path that merely mentions the tenant elsewhere — as
    another tenant's sub-folder or as a file NAME — which is a boundary that
    only holds while nothing untrusted can shape the rest of the path.

    Segment equality, not a startswith: a prefix test lets customer "cus-1"
    reach "cus-10"'s objects. A ".." anywhere is refused outright rather than
    normalised, because normalising invites disagreement with the storage
    layer about what the path means.
    """
    segments = object_path.split("/")
    if ".." in segments:
        raise PermissionDenied("Source path contains a traversal segment")
    if len(segments) < 3 or segments[0] not in CUSTOMER_PATH_PREFIXES:
        raise PermissionDenied("Source file is not under a known prefix")
    if segments[1] != customer_id:
        raise PermissionDenied("Source file does not belong to this customer")


def _local_name(index: int, file_name: str) -> str:
    """A flat, collision-free name under our own working directory.

    The record's fileName is client-supplied, so only its suffix is trusted
    and even that is bounded; the stem is our index.
    """
    suffix = Path(str(file_name)).suffix.lower()
    if suffix != ".pdf":
        suffix = ".pdf"
    return f"file_{index:02d}{suffix}"


def download_sources(bucket, source_files, dest_dir: str,
                     customer_id: str) -> tuple[list[DownloadedSource], list[dict]]:
    """Download what we can. A file we cannot read warns and is skipped.

    One corrupt file in a three-file set must not lose the two good plans, so
    failure here is per-file and never raises.
    """
    downloaded: list[DownloadedSource] = []
    warnings: list[dict] = []
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    for source in source_files:
        try:
            _, object_path = parse_gs_uri(source.storage_url)
            assert_customer_scoped(object_path, customer_id)
        except PermissionDenied as exc:
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_FORBIDDEN", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue
        except InvalidArgument as exc:
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_UNREADABLE", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue

        local = str(Path(dest_dir) / _local_name(source.index, source.file_name))
        try:
            bucket.blob(object_path).download_to_filename(local)
        except Exception as exc:  # noqa: BLE001 - any storage failure is per-file
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_UNREADABLE", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue

        downloaded.append(DownloadedSource(
            index=source.index, file_name=source.file_name, local_path=local))

    return downloaded, warnings


def page_count(pdf_path: str) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()
