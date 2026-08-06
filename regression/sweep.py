"""Run the pipeline over corpus sheets and score the output.

Sheets are extracted with skip_gemini=True: the region-classification cache
ships with the bundle, so a sweep is offline and deterministic. A cache miss
means detection ran over the whole page instead of the floor-plan regions —
which changes what is detected — so it is surfaced per sheet.

Output is persisted under outputs/regress/<slug>/ (gitignored) rather than a
temp directory: the render, the overlay and the per-category review images are
what a human needs in order to act on a REVIEW line, and they used to be
deleted the instant scoring finished. The per-primitive debug trace
(debug_trace.json + debug_viewer.html) is opt-in (`debug_traces=True`), not
unconditional: it scales with primitive count rather than page count, and on
the corpus's heavier sheets (s16, s18) it added 200-300MB per sheet -- far
past the +100MB-per-sheet threshold that keeps it off by default. Measured on
the reference sheet s01 alone it looked cheap (+11.1MB); it is not cheap on
the corpus as a whole. See tools/regress.py's --debug flag.

Persisting also surfaced a second cost: `pipeline.run_extract` always writes
several page-level files (primitives.json, candidates.json,
pdfplumber_comparison.json, regions.json, region_crops/) that nothing in this
package reads back and no review step opens -- 139MB for primitives.json
alone on one page of s18. `_prune_unread_page_output` deletes them from the
sweep's own copy after scoring and after the review images are drawn; see
that function's docstring for the measured numbers and the escape hatch.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline import run_extract
from regression.corpus import manifest_sheets, sha256_of, sheet_entry, sheet_path
from regression.ground_truth import PageTruth, SheetTruth, load_truth
from regression.matching import match_entities
from regression.report import SheetResult
from regression.review_render import write_review_overlays
from regression.run_dir import latest_run, reset_slug_dir

# Page-level entries a sweep never reads back and a human never opens while
# giving verdicts: nothing in regression/, tools/, or tests/ reads
# primitives.json, candidates.json, pdfplumber_comparison.json, regions.json,
# or region_crops/ (verified by grep before this constant was written). Kept
# as a module constant so it stays greppable and easy to amend if a future
# reader is added for one of them.
PRUNE_PAGE_ENTRIES = ("primitives.json", "candidates.json",
                     "pdfplumber_comparison.json", "regions.json",
                     "region_crops")


def evaluate_page(truth_page: PageTruth, entities: list[dict]) -> dict:
    """Score one page's entities against its three verdict lists."""
    confirmed = match_entities(truth_page.confirmed, entities)
    remaining = confirmed.unmatched_actual

    fps = match_entities(truth_page.false_positives, remaining)
    remaining = fps.unmatched_actual

    gaps = match_entities(truth_page.deferred, remaining)
    remaining = gaps.unmatched_actual

    counts: dict[str, tuple[int, int]] = {}
    for item in truth_page.confirmed:
        found, total = counts.get(item.type, (0, 0))
        counts[item.type] = (found, total + 1)
    for item, _ent in confirmed.matched:
        found, total = counts[item.type]
        counts[item.type] = (found + 1, total)

    return {
        "lost": confirmed.unmatched_truth,
        "returned_fps": [t for t, _ in fps.matched],
        "closed_deferred": [t for t, _ in gaps.matched],
        "unreviewed": remaining,
        "counts": counts,
    }


def _entities_by_page(run_dir: str) -> dict[int, list[dict]]:
    pages: dict[int, list[dict]] = {}
    for path in sorted(Path(run_dir).glob("pages/page_*/final_entities.json")):
        number = int(path.parent.name.split("_")[1])
        pages[number] = json.loads(path.read_text(encoding="utf-8")).get("entities", [])
    return pages


def _cache_missed(run_dir: str) -> bool:
    warnings_path = Path(run_dir) / "warnings.json"
    if not warnings_path.exists():
        return False
    payload = json.loads(warnings_path.read_text(encoding="utf-8"))
    # warnings.json is {"total_warnings": N, "warnings": [...]} at the run
    # root (pipeline.run_extract), not a bare flat list.
    codes = {w.get("warning_code") for w in payload.get("warnings", [])}
    return "REGION_CACHE_MISS_OFFLINE" in codes


def _prune_unread_page_output(run: Path) -> None:
    """Delete the page-level files a sweep persists but never uses.

    Making sweep output persistent (instead of a `tempfile.TemporaryDirectory`
    deleted within milliseconds of scoring) surfaced a cost that always
    existed but was previously invisible: `primitives.json` alone measured
    139MB on a single page for s18, a 1.3MB PDF -- and s18/s16 together left
    over 300MB of page output EACH with the debug trace off. None of
    PRUNE_PAGE_ENTRIES is read by anything in regression/, tools/, or tests/
    (grepped before adding this function); they exist only because
    `pipeline.run_extract` always writes the full per-page contract for
    `app.py extract`, which this sweep does not get to change (`pipeline.py`
    is read-only in this plan). The sweep prunes its OWN copy after scoring
    and after `write_review_overlays` has drawn from `render.png` --
    `pipeline.py`'s output contract for ordinary `app.py extract` runs is
    untouched.

    Anyone who needs `primitives.json` (or another pruned file) for a
    specific sheet still has the escape hatch: run
    `python app.py extract fixtures/sheets/<file>` directly and it will be
    right there, unpruned.
    """
    for page_dir in run.glob("pages/page_*"):
        for name in PRUNE_PAGE_ENTRIES:
            target = page_dir / name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink()


def _labeled_but_unreviewed(entry: dict, truth: SheetTruth) -> bool:
    """True when the manifest claims this sheet has been labeled but its
    ground truth says otherwise.

    `fixtures/MANIFEST.json` entries carry an optional `"labeled": true` --
    a durable, diffable claim set once a human has recorded verdicts for a
    sheet (see tools such as regress.py's labeling loop). Ground truth itself
    lives in a separate file (tests/ground_truth/<slug>.json) that can vanish
    independently -- a forgotten commit, a stray `git rm`, a bad merge -- and
    `load_truth` reads a missing file exactly the same as a present one with
    `reviewed: null` (SheetTruth.is_labeled is False either way). Without this
    check that loss is invisible: the sweep would print "unlabeled" among 19
    other clean lines and exit 0, and every verdict a human recorded for that
    sheet would have evaporated with no failing signal.
    """
    return bool(entry.get("labeled")) and not truth.is_labeled


def score_sheet(slug: str, truth: SheetTruth, pages: dict[int, list[dict]],
                cache_miss: bool = False) -> SheetResult:
    """Score one sheet's per-page pipeline output against its ground truth.

    `pages` is what the run actually produced (keyed by 1-based page number,
    the same convention `truth.pages` uses). Every page named in the ground
    truth must be present here — a page the run never emitted output for
    (a hand-edited ground-truth file pointing at a page the sheet does not
    have, or a trimmed `pages` count in the manifest) would otherwise make
    every `confirmed` item on it silently unreachable: it can never match,
    never gets scored, and the sweep would print a clean line and exit 0
    despite covering none of that page's verdicts. `unscored_pages` surfaces
    that gap explicitly and is regression-class (see `SheetResult.is_regression`).
    """
    result = SheetResult(slug=slug,
                         status="unlabeled" if not truth.is_labeled else "ok",
                         region_cache_miss=cache_miss)
    for number, entities in sorted(pages.items()):
        scored = evaluate_page(truth.page(number), entities)
        result.lost += scored["lost"]
        result.returned_fps += scored["returned_fps"]
        result.closed_deferred += scored["closed_deferred"]
        result.unreviewed += scored["unreviewed"]
        if scored["unreviewed"]:
            result.unreviewed_by_page[number] = scored["unreviewed"]
        for kind, (found, total) in scored["counts"].items():
            prev_found, prev_total = result.counts.get(kind, (0, 0))
            result.counts[kind] = (prev_found + found, prev_total + total)

    result.unscored_pages = sorted(set(truth.pages) - set(pages))
    if result.is_regression:
        result.status = "regression"
    return result


def sweep(slugs: list[str] | None = None, debug_traces: bool = False) -> list[SheetResult]:
    # slugs=[] is a deliberate "sweep nothing" request and must stay empty --
    # `or` would treat it the same as slugs=None ("sweep everything").
    wanted = slugs if slugs is not None else [s["slug"] for s in manifest_sheets()
                                              if s.get("tier") != "retired"]
    results: list[SheetResult] = []
    for slug in wanted:
        entry = sheet_entry(slug)
        if entry is None:
            results.append(SheetResult(slug=slug, status="missing"))
            continue
        path = sheet_path(slug)
        if path is None:
            results.append(SheetResult(slug=slug, status="missing"))
            continue
        if sha256_of(path) != entry["sha256"]:
            results.append(SheetResult(slug=slug, status="sha_mismatch"))
            continue

        truth = load_truth(slug)
        if _labeled_but_unreviewed(entry, truth):
            results.append(SheetResult(slug=slug, status="labeled_but_unreviewed"))
            continue

        # The manifest's sha256 is what's on disk NOW; truth.pdf_sha256 is
        # what the ground truth was reviewed against. An operator who pastes
        # a fresh hash into the manifest instead of adopting a new slug would
        # pass the check above (disk now matches the manifest) while silently
        # scoring stale verdicts against a drawing nobody reviewed.
        if truth.pdf_sha256 and truth.pdf_sha256 != entry["sha256"]:
            results.append(SheetResult(slug=slug, status="sha_mismatch"))
            continue

        # Output is persisted, not thrown away: the render, the overlay and the
        # debug viewer are what the human needs to judge REVIEW items, and a
        # TemporaryDirectory deleted all three microseconds after writing them.
        # reset_slug_dir is called exactly once -- it wipes the previous sweep,
        # so a second call would delete the run that just finished.
        out_parent = reset_slug_dir(slug)
        run_extract(str(path), list(range(entry["pages"])),
                    out_parent=str(out_parent), skip_gemini=True, debug=debug_traces)
        run = latest_run(slug)
        pages = _entities_by_page(str(run)) if run else {}
        cache_miss = _cache_missed(str(run)) if run else False

        result = score_sheet(slug, truth, pages, cache_miss=cache_miss)
        if run is not None:
            result.run_dir = str(run)
            # Stamp the run with the sha it was produced from. A review session
            # can start days later; without this it cannot tell whether the
            # images it is showing came from the PDF currently on disk, and
            # would happily record verdicts against a superseded drawing.
            (run / "sweep_meta.json").write_text(
                json.dumps({"slug": slug, "sha256": entry["sha256"]}, indent=2)
                + "\n", encoding="utf-8")
            for number, unreviewed in result.unreviewed_by_page.items():
                write_review_overlays(run / "pages" / f"page_{number:02d}",
                                      unreviewed)
            # Prune after scoring AND after write_review_overlays -- both
            # already read what they need (final_entities.json, render.png)
            # before anything here is deleted.
            _prune_unread_page_output(run)
        results.append(result)
    return results
