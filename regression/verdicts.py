"""Turning a human's selections into committed ground truth.

Pure and terminal-free on purpose. `tools/review.py` collects verdicts by
prompting; a future agent path collects them from flags. Both call
`record_verdicts`, so there is one writer and one set of invariants rather
than two code paths that drift.

The invariant that matters most: an entity id never reaches disk. Ids are
ordinal -- door_0015 becomes door_0014 the moment an earlier door stops being
detected -- so they identify a detection within one sweep's output and nothing
more. Ground truth is matched geometrically.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from regression.corpus import set_labeled, sheet_entry
from regression.ground_truth import (SHAPES, PageTruth, SheetTruth, TruthItem,
                                     dump_truth, load_truth)


@dataclass
class Verdict:
    """One decision about one detection.

    `entity` is the raw dict from a run's final_entities.json. `correct`
    is the reality axis (confirmed vs false positive); `shape` is the rooms-only
    second axis saying whether the stored polygon is the outline the user wants.
    """
    page: int
    entity: dict
    correct: bool
    shape: str | None = None
    note: str = ""


def _truth_item(verdict: Verdict) -> TruthItem:
    entity = verdict.entity
    is_room = entity["entity_type"] == "room"
    raw_polygon = (entity.get("attributes") or {}).get("polygon") if is_room else None
    polygon = ([[float(x), float(y)] for x, y in raw_polygon]
               if raw_polygon and len(raw_polygon) >= 3 else None)
    return TruthItem(type=entity["entity_type"],
                     bbox=tuple(float(v) for v in entity["bbox"]),
                     note=verdict.note,
                     polygon=polygon,
                     shape=verdict.shape)


def record_verdicts(slug: str, verdicts: list[Verdict],
                    today: str | None = None) -> Path | None:
    """Append verdicts to a sheet's ground truth and flag it labeled.

    Returns the ground-truth path, or None when there was nothing to record.

    Everything is validated before anything is written: a bad shape value or an
    unknown slug must not leave a half-written file behind, because a review
    session that dies mid-sheet would otherwise corrupt verdicts recorded
    months earlier.
    """
    if not verdicts:
        return None

    entry = sheet_entry(slug)
    if entry is None:
        raise ValueError(f"{slug} is not in fixtures/MANIFEST.json")
    for verdict in verdicts:
        entity = verdict.entity
        entity_type = entity.get("entity_type")
        if not entity_type:
            raise ValueError(f"{slug}: entity is missing entity_type: {entity!r}")
        bbox = entity.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError(f"{slug}: entity bbox must be four numbers, "
                             f"got {bbox!r} (entity_type={entity_type!r})")
        try:
            [float(v) for v in bbox]
        except (TypeError, ValueError):
            raise ValueError(f"{slug}: entity bbox must be four numbers, "
                             f"got {bbox!r} (entity_type={entity_type!r})")
        if verdict.shape is not None:
            if entity_type != "room":
                raise ValueError(
                    f"{slug}: shape is rooms-only, but entity_type is "
                    f"{entity_type!r}")
            if verdict.shape not in SHAPES:
                raise ValueError(f"{slug}: shape must be one of {list(SHAPES)}, "
                                 f"got {verdict.shape!r}")
        if verdict.page < 1:
            raise ValueError(f"{slug}: page numbers are 1-based, "
                             f"got {verdict.page}")

    truth: SheetTruth = load_truth(slug)
    # Refuse to mix two drawings' verdicts in one file. `or entry[...]` alone
    # would silently keep a stale hash, producing a truth file that sweep.py
    # rejects as sha_mismatch on its very next run. review_session.pending
    # blocks this earlier; the check is repeated here because this function is
    # the only writer and must hold the invariant on its own.
    if truth.pdf_sha256 and truth.pdf_sha256 != entry["sha256"]:
        raise ValueError(
            f"{slug}: ground truth was reviewed against a different PDF "
            f"({truth.pdf_sha256} vs the manifest's {entry['sha256']}). A "
            f"revised drawing is adopted as a NEW slug, never merged into an "
            f"existing one.")
    truth.slug = slug
    truth.pdf_sha256 = truth.pdf_sha256 or entry["sha256"]
    truth.reviewed = today or datetime.date.today().isoformat()

    for verdict in verdicts:
        page = truth.pages.setdefault(verdict.page, PageTruth())
        target = page.confirmed if verdict.correct else page.false_positives
        target.append(_truth_item(verdict))

    # Flag the manifest BEFORE writing the truth file, not after. If the
    # second write fails (disk full, a concurrent manifest edit, permissions),
    # this order leaves manifest-labeled + truth-unlabeled -- exactly the
    # combination sweep._labeled_but_unreviewed exists to catch, so the next
    # sweep exits 1 with an actionable message instead of staying quiet. The
    # reverse order fails silently: truth would hold the new verdicts with
    # reviewed set, but the durable "these verdicts existed" manifest marker
    # would never arm, and nothing checks for that combination. Do not
    # "tidy" this back.
    set_labeled(slug, True)
    return dump_truth(truth)
