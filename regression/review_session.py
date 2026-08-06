"""What a persisted sweep still needs verdicts on.

Reads the run output the sweep left behind and the ground truth recorded so
far, and reports what matched neither -- per page, grouped by entity type in
review order. Deliberately re-scores rather than serializing sweep state: the
sweep and the review session then agree by construction, and a review session
started days later still sees exactly what the report printed.

No detection is re-run. A sweep must have been run first.

Every unreviewable state raises ReviewBlocked rather than propagating. A
review walk covers all 20 corpus sheets by default, so one unreadable ground
truth file must cost that one sheet, not the whole session.
"""
from __future__ import annotations

import json

from regression.corpus import sha256_of, sheet_entry, sheet_path
from regression.ground_truth import load_truth
from regression.run_dir import latest_run
from regression.sweep import _entities_by_page, evaluate_page

# Doors first because they are the most numerous and the most often wrong;
# rooms last because judging a room is slower than judging a door and the
# earlier passes warm up the eye on the same drawing.
CATEGORY_ORDER = ("door", "window", "room", "label", "schedule")


class ReviewBlocked(RuntimeError):
    """This sheet cannot be reviewed right now. Report it and move on."""


class SweepOutputMissing(ReviewBlocked):
    """No persisted sweep output for this slug."""


class SweepOutputStale(ReviewBlocked):
    """The persisted output does not describe the PDF now on disk."""


def _ordered(types: list[str]) -> list[str]:
    known = [t for t in CATEGORY_ORDER if t in types]
    unknown = sorted(t for t in types if t not in CATEGORY_ORDER)
    return known + unknown


def _check_provenance(slug: str, run) -> dict:
    """Refuse to review output that does not describe the current drawing.

    Two independent ways the images can lie about what they show:

      * the PDF on disk no longer hashes to what the manifest records -- the
        drawing was revised in place, which the corpus rules forbid (a revision
        is adopted as a NEW slug) but which a stray copy can still cause;
      * the run was produced from a different sha than the manifest now holds
        -- someone swept, then swapped the PDF and updated the manifest.

    Either way the review image shows one drawing while ground truth would be
    pinned to another, and the verdicts would be silently wrong forever.

    Returns the manifest entry so `pending()` doesn't re-parse the manifest
    a second time just to read the same sha back.
    """
    entry = sheet_entry(slug)
    if entry is None:
        raise ReviewBlocked(f"{slug} is not in fixtures/MANIFEST.json")

    path = sheet_path(slug)
    if path is None:
        raise ReviewBlocked(f"{slug} is not downloaded — "
                            f"run: python tools/fetch_fixtures.py")

    if sha256_of(path) != entry["sha256"]:
        raise SweepOutputStale(
            f"{slug}: the PDF on disk no longer matches fixtures/MANIFEST.json. "
            f"A revised drawing is adopted as a NEW slug "
            f"(python tools/add_sheet.py), never dropped over an existing one.")

    meta_path = run / "sweep_meta.json"
    if not meta_path.exists():
        # Unknown provenance, not legacy tolerance: every sweep since the
        # stamp was introduced writes it, so a run without one is either from
        # before this tooling existed or was assembled by hand. Either way
        # there is no way to tell which drawing the images show, and a wrong
        # verdict is permanent. Cheap to fix: re-sweep.
        raise SweepOutputStale(
            f"{slug}: sweep output carries no sweep_meta.json, so the drawing "
            f"it was produced from is unknown — "
            f"re-run: python tools/regress.py --sheet {slug}")
    try:
        swept_sha = json.loads(meta_path.read_text(encoding="utf-8"))["sha256"]
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        raise ReviewBlocked(f"{slug}: {meta_path} is unreadable — {exc}") from exc
    if swept_sha != entry["sha256"]:
        raise SweepOutputStale(
            f"{slug}: this sweep output was produced from a different PDF — "
            f"re-run: python tools/regress.py --sheet {slug}")

    return entry


def pending(slug: str) -> dict[int, dict[str, list[dict]]]:
    """Unreviewed detections, keyed by 1-based page then entity type.

    Pages and types with nothing left to review are omitted entirely, so an
    empty return means the sheet is fully reviewed.

    Raises ReviewBlocked (or a subclass) for every state that makes reviewing
    this sheet unsafe; callers report and skip rather than crashing.
    """
    run = latest_run(slug)
    if run is None:
        raise SweepOutputMissing(
            f"no persisted sweep output for {slug} — "
            f"run: python tools/regress.py --sheet {slug}")

    entry = _check_provenance(slug, run)

    try:
        truth = load_truth(slug)
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        raise ReviewBlocked(
            f"{slug}: tests/ground_truth/{slug}.json is unreadable — {exc}"
        ) from exc

    # The existing verdicts were reviewed against a different drawing.
    # sweep.py already refuses to score this state (status "sha_mismatch",
    # exit 1), so appending here would write verdicts the very next sweep
    # rejects -- and would mix two drawings' verdicts in one file while doing
    # it. Blocked at the door instead.
    if truth.pdf_sha256 and truth.pdf_sha256 != entry["sha256"]:
        raise SweepOutputStale(
            f"{slug}: tests/ground_truth/{slug}.json was reviewed against a "
            f"different PDF ({truth.pdf_sha256[:12]}… vs the manifest's "
            f"{entry['sha256'][:12]}…). A revised drawing is adopted as a NEW "
            f"slug (python tools/add_sheet.py); its verdicts are never merged "
            f"into the old one.")

    result: dict[int, dict[str, list[dict]]] = {}
    for number, entities in sorted(_entities_by_page(str(run)).items()):
        unreviewed = evaluate_page(truth.page(number), entities)["unreviewed"]
        if not unreviewed:
            continue
        by_type: dict[str, list[dict]] = {}
        for entity in unreviewed:
            by_type.setdefault(entity["entity_type"], []).append(entity)
        result[number] = {t: by_type[t] for t in _ordered(list(by_type))}
    return result
