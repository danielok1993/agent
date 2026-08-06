"""Sweep results, their rendering, and the exit-code contract.

Exit codes:
  0  clean, or REVIEW items only (new detections, closed gaps)
  1  a regression: a confirmed entity vanished, a known false positive came
     back, a sheet's bytes no longer match the manifest (or no longer match
     what its ground truth was reviewed against), a page named in ground
     truth was never scored, or a manifest entry marked `"labeled": true`
     has ground truth that is missing or reverted to `reviewed: null`
  2  the corpus is incomplete — some manifest sheets are not downloaded

New detections never fail the sweep. Improving detection must not turn the
suite red; it queues review instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from regression.ground_truth import TruthItem

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_INCOMPLETE = 2


@dataclass
class SheetResult:
    slug: str
    status: str = "ok"
    lost: list[TruthItem] = field(default_factory=list)
    returned_fps: list[TruthItem] = field(default_factory=list)
    unreviewed: list[dict] = field(default_factory=list)
    closed_deferred: list[TruthItem] = field(default_factory=list)
    counts: dict[str, tuple[int, int]] = field(default_factory=dict)
    region_cache_miss: bool = False
    unscored_pages: list[int] = field(default_factory=list)

    @property
    def is_regression(self) -> bool:
        return (bool(self.lost or self.returned_fps or self.unscored_pages)
                or self.status in ("sha_mismatch", "labeled_but_unreviewed"))


def _centre(bbox) -> str:
    return f"({round((bbox[0] + bbox[2]) / 2)},{round((bbox[1] + bbox[3]) / 2)})"


def render(results: list[SheetResult]) -> str:
    lines = []
    for r in results:
        if r.status == "missing":
            lines.append(f"{r.slug}  SKIPPED — not downloaded")
            continue
        if r.status == "sha_mismatch":
            lines.append(f"{r.slug}  ✗ content changed since ground truth was recorded")
            continue
        if r.status == "labeled_but_unreviewed":
            lines.append(f"{r.slug}  ✗ manifest claims this sheet is labeled "
                         f"(\"labeled\": true), but its ground truth is missing or "
                         f"unlabeled (reviewed: null) — restore "
                         f"tests/ground_truth/{r.slug}.json")
            continue
        counts = "  ".join(f"{kind} {found}/{total}"
                           for kind, (found, total) in sorted(r.counts.items()))
        tail = []
        if r.unreviewed:
            tail.append(f"unreviewed {len(r.unreviewed)}")
        if r.closed_deferred:
            tail.append(f"gaps CLOSED {len(r.closed_deferred)}")
        if r.status == "unlabeled":
            # status=="unlabeled" only means `reviewed` is unset; it does not
            # mean the file has no verdict lists (a hand-edited truth file
            # can carry `confirmed`/`deferred` entries under a null
            # `reviewed`). r.lost/r.returned_fps are always empty here (they
            # would have promoted status to "regression"), but r.counts and
            # r.closed_deferred are not -- claiming "every detection is
            # unreviewed" while those are non-empty would contradict the
            # counts and REVIEW lines printed right below it.
            if r.counts or r.closed_deferred:
                tail.append("unlabeled (reviewed not set), but this sheet has "
                            "recorded verdicts — scored anyway")
            else:
                tail.append("unlabeled — every detection is unreviewed")
        lines.append(f"{r.slug}  {counts}  {'  '.join(tail)}".rstrip())
        for item in r.lost:
            lines.append(f"    ✗ LOST {item.type} @ {_centre(item.bbox)}"
                         f"{'  ' + item.note if item.note else ''}")
        for item in r.returned_fps:
            lines.append(f"    ✗ FALSE POSITIVE RETURNED {item.type} @ {_centre(item.bbox)}"
                         f"{'  ' + item.note if item.note else ''}")
        if r.unscored_pages:
            pages = ", ".join(str(p) for p in r.unscored_pages)
            lines.append(f"    ✗ UNSCORED PAGE(S) {pages} — ground truth exists for "
                         f"{'this page' if len(r.unscored_pages) == 1 else 'these pages'} "
                         f"but the run produced no output for {'it' if len(r.unscored_pages) == 1 else 'them'}")
        for item in r.closed_deferred:
            lines.append(f"    REVIEW gap closed: {item.type} @ {_centre(item.bbox)} — "
                         f"confirm it, then promote it to `confirmed`")
        for ent in r.unreviewed:
            lines.append(f"    REVIEW new {ent['entity_type']} @ {_centre(ent['bbox'])} "
                         f"conf {ent.get('confidence', 0):.2f}")
        if r.region_cache_miss:
            lines.append("    REGION CACHE MISS — classification fell back to the whole "
                         "page; detection scope differs from the labeled run")
    return "\n".join(lines)


def exit_code(results: list[SheetResult]) -> int:
    if any(r.is_regression for r in results):
        return EXIT_REGRESSION
    if any(r.status == "missing" for r in results):
        return EXIT_INCOMPLETE
    return EXIT_OK
