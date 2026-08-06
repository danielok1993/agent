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

Review images (`review_<type>.png`) are drawn once, at sweep time, from that
sweep's full unreviewed set. If a session is interrupted partway through a
sheet and resumed later against the same sweep output, the picker correctly
shrinks to what is still actually unreviewed, but the image on disk still
shows every box from the original set, including ones already given a
verdict. The picker is always the authority; re-run
`python tools/regress.py --sheet <slug>` to redraw the images.
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

# Distinct from 130 (Ctrl-C, which stops the whole walk immediately): this is
# "the walk finished, but at least one sheet failed unexpectedly and was
# skipped" -- a scripted caller must not read a plain 0 as "all clean."
EXIT_SHEET_FAILED = 1

# A real entity id is always "<type>_<digits>" (door_0007, room_0012), so this
# can never collide with one. It is the first choice in every _pick() list and
# is authoritative: ticking it means "none of these", full stop, even if other
# choices are also ticked in the same pass. This is belt-and-braces on top of
# `inquirer.checkbox` already returning [] correctly on an empty Enter (see
# _pick's docstring) -- a second, visible way to say "postpone all", and a
# second layer of protection if that prompt behavior ever changes.
_SKIP_ALL = "__none__"
_SKIP_ALL_LABEL = "— none of these —"


def _centre(bbox) -> str:
    return f"({round((bbox[0] + bbox[2]) / 2)},{round((bbox[1] + bbox[3]) / 2)})"


def _choice(entity: dict) -> Choice:
    return Choice(entity["entity_id"],
                  name=f"{short_id(entity['entity_id']):<6} "
                       f"conf {entity.get('confidence', 0):.2f}  "
                       f"{_centre(entity['bbox'])}")


def _pick(message: str, entities: list[dict]) -> set[str]:
    """Multi-select over entities; returns the chosen entity ids.

    Uses `inquirer.checkbox`, NOT `inquirer.fuzzy(multiselect=True)`: the
    fuzzy prompt cannot express an empty selection -- pressing Enter with
    nothing ticked falls back to capturing whatever choice is currently
    highlighted (InquirerPy's own `_handle_enter` docstring says so), so a
    labeler who presses Enter to postpone a screen they cannot judge instead
    FABRICATES a verdict. `checkbox` returns `[]` on an empty Enter, which is
    the behavior this tool's whole "postponing costs nothing" design depends
    on.

    The `_SKIP_ALL` sentinel is a second, independent guarantee of the same
    thing: if it is ticked, the selection is empty, regardless of what else
    got ticked alongside it in the same pass.
    """
    if not entities:
        return set()
    choices = [Choice(_SKIP_ALL, name=_SKIP_ALL_LABEL)] + [_choice(e) for e in entities]
    chosen = set(inquirer.checkbox(
        message=message,
        choices=choices,
        border=True,
        instruction="(space to tick, enter to submit)",
        transformer=lambda picked: f"{len(picked)} selected",
    ).execute() or [])
    if _SKIP_ALL in chosen:
        return set()
    return chosen


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

    Handles sheet-level STATE problems only: missing sweep output, stale
    provenance, unreadable ground truth, and a rejected write are each
    printed and treated as "nothing recorded for this sheet" rather than
    raised. It does NOT guarantee immunity from every possible failure --
    an error from the interactive prompt layer itself (InquirerPy /
    prompt_toolkit erroring on a headless or unsupported terminal, for
    instance) propagates out of here. main()'s per-slug loop is what keeps
    one such failure from taking down the rest of a multi-sheet walk.
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
    if run is None:
        # pending() above read a run that existed a moment ago -- a
        # concurrent `regress.py --sheet <slug>` can wipe it
        # (run_dir.reset_slug_dir) in between. Nothing has been shown to the
        # user yet, so there is nothing unsafe about just stopping here.
        print(f"{slug}: SKIPPED — sweep output vanished mid-review (a concurrent "
              f"regress.py run?) — re-run: python tools/regress.py --sheet {slug}")
        return 0

    verdicts: list[Verdict] = []
    for number, by_type in sorted(by_page.items()):
        page_dir = run / "pages" / f"page_{number:02d}"
        for etype, entities in by_type.items():
            image = page_dir / f"review_{etype}.png"
            print(f"\n{slug} page {number} — {etype.upper()}S "
                  f"({len(entities)} unreviewed)")
            if image.exists():
                print(f"  open: {image}")
            else:
                # write_review_overlays skips a page with no render.png, but
                # pending() still offers its entities -- sending the user to a
                # path that was never written is worse than saying so plainly.
                print(f"  (no review image at {image} -- render.png was "
                      f"missing when the sweep ran; judge from memory or "
                      f"re-run python tools/regress.py --sheet {slug})")

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
    false_positives = len(verdicts) - confirmed
    print(f"\n{slug}: wrote {path} "
          f"(+{confirmed} confirmed, +{false_positives} false positives)")
    if false_positives:
        print(f"  by design: the next sweep will exit 1 on these {false_positives} "
              f"until the detector stops emitting them -- that's expected, the "
              f"queue of detector work these verdicts just created, not a break.")
    print(f"  commit: git add {path} fixtures/MANIFEST.json")
    return len(verdicts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*",
                        help="slugs to review; default is every corpus sheet")
    args = parser.parse_args()

    slugs = args.slugs or [s["slug"] for s in manifest_sheets()
                           if s.get("tier") != "retired"]
    failed = False
    for slug in slugs:
        try:
            review_sheet(slug)
        except KeyboardInterrupt:
            # Ctrl-C at a prompt abandons THIS sheet (nothing has been written
            # for it yet -- the write happens once, at the end) and stops the
            # walk. Verdicts recorded for earlier sheets are already on disk.
            print(f"\n{slug}: interrupted, nothing recorded for this sheet")
            return 130
        except Exception as exc:
            # Anything review_sheet doesn't already turn into a printed
            # skip (see its docstring) -- e.g. the interactive prompt layer
            # itself erroring on a headless or unsupported terminal -- must
            # still cost only this one sheet, not the rest of a 20-sheet
            # walk. It must also not report success: EXIT_SHEET_FAILED is
            # returned once the walk finishes so a scripted run notices.
            # repr(), not str(): a bare TypeError() or similar has an empty
            # str(), and this print is the ONLY thing that makes a failure
            # visible during an unattended multi-sheet walk.
            print(f"\n{slug}: FAILED — {exc!r}")
            failed = True
    return EXIT_SHEET_FAILED if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
