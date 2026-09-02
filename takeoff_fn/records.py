"""The takeoffs/{takeoffId} record: reading it, guarding it, moving its status.

Reading the record is also the authorization check — the caller names a
takeoffId, and the record says which tenant owns it. This mirrors rivet-mind's
own pattern in functions/src/estimates/attachment-download.ts:136.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from takeoff_fn import config
from takeoff_fn.errors import FailedPrecondition, NotFound

logger = logging.getLogger(__name__)

# Firestore rejects documents over 1 MB; an error string is never worth a
# meaningful fraction of that budget.
MAX_ERROR_CHARS = 2000

# A missing record and another tenant's record are indistinguishable to the
# caller: the exception type IS the callable error code, so raising different
# types would let anyone probe which takeoff ids exist. The real reason is
# logged instead. Same pattern as a 404 for a private repository.
NO_SUCH_TAKEOFF = "No such takeoff"


@dataclass(frozen=True)
class SourceFile:
    index: int
    file_name: str
    storage_url: str


@dataclass(frozen=True)
class TakeoffRecord:
    takeoff_id: str
    customer_id: str
    status: str
    estimate_id: Optional[str]
    source_files: list[SourceFile]


def _doc(db, takeoff_id: str):
    return db.collection(config.TAKEOFF_COLLECTION).document(takeoff_id)


def _source_files(raw) -> list[SourceFile]:
    """Index is assigned over the SURVIVING files, so it always matches the
    position used to build a storage path and can never leave a gap."""
    out: list[SourceFile] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        url = item.get("storageUrl")
        if not isinstance(url, str) or not url.strip():
            continue
        out.append(SourceFile(index=len(out),
                              file_name=str(item.get("fileName") or f"file_{len(out)}"),
                              storage_url=url.strip()))
    return out


def load_record(db, takeoff_id: str, customer_id: str,
                now_epoch_ms: int) -> TakeoffRecord:
    snapshot = _doc(db, takeoff_id).get()
    if not snapshot.exists:
        logger.warning("takeoff %s does not exist", takeoff_id)
        raise NotFound(NO_SUCH_TAKEOFF)

    data = snapshot.to_dict() or {}
    owner = data.get("customerId")
    if owner != customer_id:
        logger.warning(
            "takeoff %s belongs to customer %s, not %s",
            takeoff_id, owner, customer_id)
        raise NotFound(NO_SUCH_TAKEOFF)

    status = str(data.get("status") or "")
    if status == config.STATUS_APPROVED:
        raise FailedPrecondition("Takeoff is already approved")
    if status == config.STATUS_PROCESSING:
        updated_at = data.get("updatedAt") or 0
        age_ms = now_epoch_ms - int(updated_at)
        if age_ms < config.STALE_PROCESSING_SECONDS * 1000:
            raise FailedPrecondition("Takeoff is already being measured")

    source_files = _source_files(data.get("sourceFiles"))
    if not source_files:
        raise FailedPrecondition("Takeoff has no source files to measure")

    estimate_id = data.get("estimateId")
    return TakeoffRecord(
        takeoff_id=takeoff_id,
        customer_id=str(owner),
        status=status,
        estimate_id=str(estimate_id) if estimate_id else None,
        source_files=source_files,
    )


def mark_processing(db, takeoff_id: str, now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_PROCESSING,
        "startedAt": now_epoch_ms,
        "updatedAt": now_epoch_ms,
        "error": None,
    })


def mark_awaiting_review(db, takeoff_id: str, document_json: str,
                         now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_AWAITING_REVIEW,
        "document": document_json,
        "error": None,
        "updatedAt": now_epoch_ms,
    })


def mark_awaiting_scale(db, takeoff_id: str, document_json: str,
                        now_epoch_ms: int) -> None:
    """Measured, but nothing on the run carried a readable scale.

    The document is still written: the page artefacts are already in Storage
    and the scale prompt needs the plan SVG to show the user what they are
    being asked about.
    """
    _doc(db, takeoff_id).update({
        "status": config.STATUS_AWAITING_SCALE,
        "document": document_json,
        "error": None,
        "updatedAt": now_epoch_ms,
    })


def mark_failed(db, takeoff_id: str, message: str, now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_FAILED,
        "error": str(message)[:MAX_ERROR_CHARS],
        "updatedAt": now_epoch_ms,
    })
