"""Run the pipeline over corpus sheets and score the output.

Sheets are extracted with skip_gemini=True: the region-classification cache
ships with the bundle, so a sweep is offline and deterministic. A cache miss
means detection ran over the whole page instead of the floor-plan regions —
which changes what is detected — so it is surfaced per sheet.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline import run_extract
from regression.corpus import manifest_sheets, sha256_of, sheet_entry, sheet_path
from regression.ground_truth import PageTruth, load_truth
from regression.matching import match_entities
from regression.report import SheetResult


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


def sweep(slugs: list[str] | None = None) -> list[SheetResult]:
    wanted = slugs or [s["slug"] for s in manifest_sheets()
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
        with tempfile.TemporaryDirectory() as out_parent:
            run_dir = run_extract(str(path), list(range(entry["pages"])),
                                  out_parent=out_parent, skip_gemini=True)
            pages = _entities_by_page(run_dir)
            cache_miss = _cache_missed(run_dir)

        result = SheetResult(slug=slug,
                             status="unlabeled" if not truth.is_labeled else "ok",
                             region_cache_miss=cache_miss)
        for number, entities in sorted(pages.items()):
            scored = evaluate_page(truth.page(number), entities)
            result.lost += scored["lost"]
            result.returned_fps += scored["returned_fps"]
            result.closed_deferred += scored["closed_deferred"]
            result.unreviewed += scored["unreviewed"]
            for kind, (found, total) in scored["counts"].items():
                prev_found, prev_total = result.counts.get(kind, (0, 0))
                result.counts[kind] = (prev_found + found, prev_total + total)
        if result.is_regression:
            result.status = "regression"
        results.append(result)
    return results
