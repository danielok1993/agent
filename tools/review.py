#!/usr/bin/env python3
# tools/review.py
"""Record verdicts on a sweep's new detections, by ticking a list.

Usage:
    python tools/review.py            # every sheet with unreviewed detections
    python tools/review.py s01        # one sheet
    python tools/review.py s01 s07    # several

Reads the output `python tools/regress.py` persisted under
outputs/regress/<slug>/. It never re-runs detection: run the sweep first.

The walk is sheet -> page -> category. Each category prints the path to its
review image, then asks twice: which are CORRECT, then which of the rest are
WRONG. Anything ticked in neither stays unreviewed and comes back next sweep,
so "I cannot tell from this image" costs nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from InquirerPy import inquirer  # noqa: E402
from InquirerPy.base.control import Choice  # noqa: E402

from regression.corpus import manifest_sheets  # noqa: E402
from regression.review_render import short_id  # noqa: E402
from regression.review_session import ReviewBlocked, pending  # noqa: E402
from regression.run_dir import latest_run  # noqa: E402
from regression.verdicts import Verdict, record_verdicts  # noqa: E402


def _centre(bbox) -> str:
    return f"({round((bbox[0] + bbox[2]) / 2)},{round((bbox[1] + bbox[3]) / 2)})"


def _choice(entity: dict) -> Choice:
    return Choice(entity["entity_id"],
                  name=f"{short_id(entity['entity_id']):<6} "
                       f"conf {entity.get('confidence', 0):.2f}  "
                       f"{_centre(entity['bbox'])}")


def _pick(message: str, entities: list[dict]) -> set[str]:
    """Multi-select over entities; returns the chosen entity ids."""
    if not entities:
        return set()
    chosen = inquirer.fuzzy(
        message=message,
        choices=[_choice(e) for e in entities],
        multiselect=True,
        border=True,
        instruction="(type to filter, tab to tick, enter to submit)",
        transformer=lambda picked: f"{len(picked)} selected",
    ).execute()
    return set(chosen or [])


def _shape_and_note(entity: dict) -> tuple[str, str]:
    shape = inquirer.select(
        message=f"  {short_id(entity['entity_id'])} — is this polygon the "
                f"shape you want?",
        choices=[
            Choice("partial", name="partial  — real room, shape not right yet"),
            Choice("approved", name="approved — this shape is correct"),
        ],
        default="partial",
    ).execute()
    note = inquirer.text(message="  note (optional):").execute()
    return shape, note.strip()


def review_sheet(slug: str) -> int:
    """Walk one sheet's pending detections. Returns how many were recorded.

    Never raises for a sheet-level problem: a bad state is printed and the
    sheet is skipped, so a 20-sheet walk survives one broken sheet.
    """
    try:
        by_page = pending(slug)
    except ReviewBlocked as exc:
        print(f"{slug}: SKIPPED — {exc}")
        return 0

    if not by_page:
        print(f"{slug}: nothing to review")
        return 0

    run = latest_run(slug)
    verdicts: list[Verdict] = []
    for number, by_type in sorted(by_page.items()):
        page_dir = run / "pages" / f"page_{number:02d}"
        for etype, entities in by_type.items():
            image = page_dir / f"review_{etype}.png"
            print(f"\n{slug} page {number} — {etype.upper()}S "
                  f"({len(entities)} unreviewed)")
            print(f"  open: {image}")

            correct = _pick(f"Select CORRECT {etype}s", entities)
            leftovers = [e for e in entities if e["entity_id"] not in correct]
            wrong = _pick(f"Of the remaining {len(leftovers)} — select the ones "
                          f"that are WRONG (leave unticked to postpone)",
                          leftovers)

            for entity in entities:
                entity_id = entity["entity_id"]
                if entity_id in correct:
                    shape, note = (_shape_and_note(entity)
                                   if etype == "room" else (None, ""))
                    verdicts.append(Verdict(page=number, entity=entity,
                                            correct=True, shape=shape, note=note))
                elif entity_id in wrong:
                    verdicts.append(Verdict(page=number, entity=entity,
                                            correct=False))

    if not verdicts:
        print(f"\n{slug}: nothing recorded — every detection postponed")
        return 0

    # Written once, after the whole sheet: an interrupted session loses at most
    # the sheet in progress rather than half-writing a page.
    try:
        path = record_verdicts(slug, verdicts)
    except ValueError as exc:
        # record_verdicts validates before writing anything, so the ground
        # truth on disk is untouched here. Losing this sheet's answers is
        # bad; writing them somewhere wrong would be worse.
        print(f"\n{slug}: NOT RECORDED — {exc}")
        return 0
    confirmed = sum(1 for v in verdicts if v.correct)
    print(f"\n{slug}: wrote {path} "
          f"(+{confirmed} confirmed, +{len(verdicts) - confirmed} false positives)")
    print(f"  commit: git add {path} fixtures/MANIFEST.json")
    return len(verdicts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*",
                        help="slugs to review; default is every corpus sheet")
    args = parser.parse_args()

    slugs = args.slugs or [s["slug"] for s in manifest_sheets()
                           if s.get("tier") != "retired"]
    for slug in slugs:
        try:
            review_sheet(slug)
        except KeyboardInterrupt:
            # Ctrl-C at a prompt abandons THIS sheet (nothing has been written
            # for it yet -- the write happens once, at the end) and stops the
            # walk. Verdicts recorded for earlier sheets are already on disk.
            print(f"\n{slug}: interrupted, nothing recorded for this sheet")
            return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
