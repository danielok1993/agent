"""Recursive XY-cut: split a page into drawing regions at whitespace gutters."""
from __future__ import annotations

from typing import Optional

from models import BBox, PageData, Region
from layout.clips import clip_cut_positions
from layout.constants import (
    CAPTION_MAX_GAP_PX, CAPTION_MAX_H_PX, CAPTION_MIN_OVERLAP_FRAC,
    SEGMENT_BIN_PX, SEGMENT_MAX_DEPTH, SEGMENT_MIN_GUTTER_PX,
    SEGMENT_MIN_REGION_SIDE_PX, SEGMENT_OVERHANG_MAX_BINS,
    SEGMENT_OVERHANG_MIN_GAP_PX, SEGMENT_SHORT_INK_PX,
)
from layout.occupancy import InkMap, build_ink_map


def _row_profile(ink: InkMap, r0: int, r1: int, c0: int, c1: int) -> list[int]:
    return [sum(ink.bins[r][c0:c1]) for r in range(r0, r1)]


def _col_profile(ink: InkMap, r0: int, r1: int, c0: int, c1: int) -> list[int]:
    return [sum(ink.bins[r][c] for r in range(r0, r1)) for c in range(c0, c1)]


def _trim(profile: list[int], lo: int) -> tuple[int, int]:
    """Strip empty margins; returns absolute (start, end) bin indices."""
    a, b = 0, len(profile)
    while a < b and profile[a] == 0:
        a += 1
    while b > a and profile[b - 1] == 0:
        b -= 1
    return lo + a, lo + b


def _widest_gap(profile: list[int], offset: int, min_bins: int) -> Optional[tuple[int, int]]:
    """Widest fully-empty internal run of at least min_bins. Leading and
    trailing runs are margins, not gutters, and are ignored."""
    best: Optional[tuple[int, int]] = None
    i, n = 0, len(profile)
    while i < n:
        if profile[i] == 0:
            j = i
            while j < n and profile[j] == 0:
                j += 1
            if j - i >= min_bins and i > 0 and j < n:
                if best is None or (j - i) > (best[1] - best[0]):
                    best = (i, j)
            i = j
        else:
            i += 1
    return None if best is None else (offset + best[0], offset + best[1])


def _clip_cut(
    profile: list[int], offset: int,
    cuts: set[tuple[int, int, int]],
    perp_lo: int, perp_hi: int,
) -> Optional[int]:
    """First clip edge lying strictly inside the span with ink on both sides.

    An edge qualifies only where its donating rect actually is: its extent
    along the perpendicular axis must overlap the cell being cut. Without
    this, a clip edge is applied page-globally along its whole axis and cuts
    straight through drawings elsewhere on the sheet."""
    n = len(profile)
    for pos, lo, hi in sorted(cuts):
        idx = pos - offset
        if idx <= 0 or idx >= n:
            continue
        if min(hi, perp_hi) - max(lo, perp_lo) <= 0:
            continue
        if any(profile[:idx]) and any(profile[idx:]):
            return pos
    return None


def _chains_across(ink: InkMap, r0: int, r1: int, c0: int, c1: int, axis: str) -> bool:
    """True when an 8-connected component of inked bins inside the band
    touches both of the band's edges — a chain of short pieces (a dashed
    wall drawn as touching dashes, a run of hatch) that still crosses it.
    `axis` is "row" for a horizontal band (edges r0 and r1-1) and "col" for
    a vertical one (edges c0 and c1-1)."""
    seen: set[tuple[int, int]] = set()
    for r in range(r0, r1):
        row = ink.bins[r]
        for c in range(c0, c1):
            if not row[c] or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            lo = hi = r if axis == "row" else c
            while stack:
                rr, cc = stack.pop()
                v = rr if axis == "row" else cc
                lo, hi = min(lo, v), max(hi, v)
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = rr + dr, cc + dc
                        if r0 <= nr < r1 and c0 <= nc < c1 and ink.bins[nr][nc] \
                                and (nr, nc) not in seen:
                            seen.add((nr, nc))
                            stack.append((nr, nc))
            first, last = (r0, r1 - 1) if axis == "row" else (c0, c1 - 1)
            if lo == first and hi == last:
                return True
    return False


def _short_ink_gutter(
    ink: InkMap, long_ink: InkMap,
    r0: int, r1: int, c0: int, c1: int, min_bins: int,
) -> Optional[tuple[str, int]]:
    """Tier 3: the widest band empty on the LONG-ink map whose short ink does
    not chain across it. Returns ("row"|"col", cut bin) or None."""
    gap_r = _widest_gap(_row_profile(long_ink, r0, r1, c0, c1), r0, min_bins)
    gap_c = _widest_gap(_col_profile(long_ink, r0, r1, c0, c1), c0, min_bins)
    cands = []
    if gap_r is not None:
        cands.append(("row", gap_r))
    if gap_c is not None:
        cands.append(("col", gap_c))
    cands.sort(key=lambda t: t[1][1] - t[1][0], reverse=True)
    for axis, (g0, g1) in cands:
        blocked = (
            _chains_across(ink, g0, g1, c0, c1, "row") if axis == "row"
            else _chains_across(ink, r0, r1, g0, g1, "col")
        )
        if not blocked:
            return axis, (g0 + g1) // 2
    return None


def _sparse_bands(profile: list[int], offset: int, k: int, min_bins: int) -> list[tuple[int, int]]:
    """Internal runs of >= min_bins profile entries each <= k, widest first."""
    out: list[tuple[int, int]] = []
    i, n = 0, len(profile)
    while i < n:
        if profile[i] <= k:
            j = i
            while j < n and profile[j] <= k:
                j += 1
            if j - i >= min_bins and i > 0 and j < n:
                out.append((offset + i, offset + j))
            i = j
        else:
            i += 1
    out.sort(key=lambda g: g[1] - g[0], reverse=True)
    return out


def _widest_zero_run(profile: list[int], offset: int) -> Optional[tuple[int, int]]:
    """Widest run of zeros anywhere in the profile, edges included."""
    best: Optional[tuple[int, int]] = None
    i, n = 0, len(profile)
    while i < n:
        if profile[i] == 0:
            j = i
            while j < n and profile[j] == 0:
                j += 1
            if best is None or (j - i) > (best[1] - best[0]):
                best = (offset + i, offset + j)
            i = j
        else:
            i += 1
    return best


def _overhang_gutter(
    ink: InkMap, long_ink: InkMap, overhang_ink: InkMap,
    r0: int, r1: int, c0: int, c1: int, min_bins: int,
) -> Optional[tuple[str, int]]:
    """Tier 4: the widest band sparse on the paths-only long map
    (overhang_ink — a caption in the band must not disqualify it) that
    nothing chains across on the full map (ink — a through line, short
    pieces forming one, overhangs from both sides that meet) and that keeps
    a sub-run of SEGMENT_OVERHANG_MIN_GAP_PX empty on the text+long map
    (long_ink — short annotation pieces do not count, exactly as in tier 3,
    but a caption or a long line does, so neither is ever sliced). Returns
    ("row"|"col", cut bin) or None."""
    gap_bins = max(1, SEGMENT_OVERHANG_MIN_GAP_PX // ink.bin_px)
    cands: list[tuple[str, tuple[int, int]]] = []
    for g in _sparse_bands(_row_profile(overhang_ink, r0, r1, c0, c1), r0,
                           SEGMENT_OVERHANG_MAX_BINS, min_bins):
        cands.append(("row", g))
    for g in _sparse_bands(_col_profile(overhang_ink, r0, r1, c0, c1), c0,
                           SEGMENT_OVERHANG_MAX_BINS, min_bins):
        cands.append(("col", g))
    cands.sort(key=lambda t: t[1][1] - t[1][0], reverse=True)
    for axis, (g0, g1) in cands:
        if axis == "row":
            if _chains_across(ink, g0, g1, c0, c1, "row"):
                continue
            run = _widest_zero_run(_row_profile(long_ink, g0, g1, c0, c1), g0)
        else:
            if _chains_across(ink, r0, r1, g0, g1, "col"):
                continue
            run = _widest_zero_run(_col_profile(long_ink, r0, r1, g0, g1), g0)
        if run is not None and run[1] - run[0] >= gap_bins:
            return axis, (run[0] + run[1]) // 2
    return None


def _xy_cut(
    ink: InkMap,
    r0: int, r1: int, c0: int, c1: int,
    min_bins: int,
    cut_rows: set[tuple[int, int, int]],
    cut_cols: set[tuple[int, int, int]],
    depth: int,
    out: list[tuple[int, int, int, int]],
    long_ink: InkMap | None = None,
    overhang_ink: InkMap | None = None,
) -> None:
    rows = _row_profile(ink, r0, r1, c0, c1)
    r0, r1 = _trim(rows, r0)
    cols = _col_profile(ink, r0, r1, c0, c1)
    c0, c1 = _trim(cols, c0)
    if r1 <= r0 or c1 <= c0:
        return
    if depth >= SEGMENT_MAX_DEPTH:
        out.append((r0, r1, c0, c1))
        return

    rows = _row_profile(ink, r0, r1, c0, c1)
    cols = _col_profile(ink, r0, r1, c0, c1)
    gap_r = _widest_gap(rows, r0, min_bins)
    gap_c = _widest_gap(cols, c0, min_bins)
    height_r = 0 if gap_r is None else gap_r[1] - gap_r[0]
    height_c = 0 if gap_c is None else gap_c[1] - gap_c[0]

    # A real gutter always beats a clip edge: a clip edge has zero width.
    if height_r or height_c:
        if height_r >= height_c:
            m = (gap_r[0] + gap_r[1]) // 2
            _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        else:
            m = (gap_c[0] + gap_c[1]) // 2
            _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        return

    m = _clip_cut(rows, r0, cut_rows, c0, c1)
    if m is not None:
        _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        return

    m = _clip_cut(cols, c0, cut_cols, r0, r1)
    if m is not None:
        _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
        return

    # Tier 3: a band only short annotation ink crosses (SEGMENT_SHORT_INK_PX).
    # Last resort so every cell a real gutter or a clip edge can split is
    # split exactly as before.
    if long_ink is not None:
        hit = _short_ink_gutter(ink, long_ink, r0, r1, c0, c1, min_bins)
        if hit is not None:
            axis, m = hit
            if axis == "row":
                _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
                _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            else:
                _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
                _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            return

        # Tier 4: a band only overhanging long ink enters
        # (SEGMENT_OVERHANG_MIN_GAP_PX) — after tier 3 so a band short ink
        # alone crosses is cut at its full width first.
        hit = None
        if overhang_ink is not None:
            hit = _overhang_gutter(ink, long_ink, overhang_ink, r0, r1, c0, c1, min_bins)
        if hit is not None:
            axis, m = hit
            if axis == "row":
                _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
                _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            else:
                _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
                _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out, long_ink, overhang_ink)
            return

    out.append((r0, r1, c0, c1))


def count_paths_in(page_data: PageData, box: BBox) -> int:
    return sum(1 for p in page_data.paths if _centre_in(p.bbox, box))


def _centre_in(bbox: BBox, box: BBox) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def _merge_captions(page_data: PageData, boxes: list[BBox]) -> list[BBox]:
    """Fold zero-path title strips into the drawing they belong to.

    A caption is a region with no vector ink at all, no taller than
    CAPTION_MAX_H_PX, overlapping a drawing horizontally by at least
    CAPTION_MIN_OVERLAP_FRAC of its own width, within CAPTION_MAX_GAP_PX
    vertically. A caption that matches nothing is kept as its own region so the
    sheet record stays complete.
    """
    drawings = [list(b) for b in boxes if count_paths_in(page_data, b) > 0]
    captions = [b for b in boxes if count_paths_in(page_data, b) == 0]
    unmerged: list[BBox] = []

    for c in captions:
        if (c[3] - c[1]) > CAPTION_MAX_H_PX:
            unmerged.append(c)
            continue
        caption_w = c[2] - c[0]
        best, best_gap = None, None
        for i, d in enumerate(drawings):
            overlap = min(c[2], d[2]) - max(c[0], d[0])
            if overlap < CAPTION_MIN_OVERLAP_FRAC * caption_w:
                continue
            gap = c[1] - d[3] if c[1] >= d[3] else d[1] - c[3]
            if gap < 0 or gap > CAPTION_MAX_GAP_PX:
                continue
            if best_gap is None or gap < best_gap:
                best, best_gap = i, gap
        if best is None:
            unmerged.append(c)
            continue
        d = drawings[best]
        d[0], d[1] = min(d[0], c[0]), min(d[1], c[1])
        d[2], d[3] = max(d[2], c[2]), max(d[3], c[3])

    return [tuple(b) for b in drawings] + unmerged


def _edge_gap_sq(a: BBox, b: BBox) -> float:
    """Squared gap between two boxes' nearest edges (0 when they touch)."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return dx * dx + dy * dy


def _overlap_area(a: BBox, b: BBox) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if (w > 0 and h > 0) else 0.0


def _fold_small_leaves(
    page_data: PageData, kept: list[BBox], small: list[BBox]
) -> list[BBox]:
    """Union each path-bearing sub-min-side leaf into its nearest kept box.

    Dropping the leaf drops its paths from coverage, and on dense sheets the
    dropped leaves are anything but empty: s11's skinny scale-bar strips
    (24x348px, 8,134 paths each) held 34.5% of the sheet's paths, pushing
    assigned_path_fraction to 0.655 — under REGION_MIN_COVERAGE_FRAC, so
    region filtering never activated and detection saw all 148k paths.

    Two leaves never fold: zero-path leaves (unmerged text fragments — no
    coverage to recover, folding only grows a region's classification crop),
    and leaves whose union would INCREASE the grown box's overlap with any
    other kept box. The union is a full rectangle, so folding a leaf that
    sits diagonal to its host annexes the space in between — a page-wide
    980x4 border fragment (s11, 1 path) folded into a tall region would
    stretch it across its neighbours' columns and feed their ink to whatever
    the host region classifies as. Such a leaf tries the next-nearest box,
    and drops (the pre-fold behaviour) when every candidate would leak.
    """
    kept = [list(b) for b in sorted(kept, key=lambda b: (b[1], b[0]))]
    eps = 1e-6
    for s in sorted(small, key=lambda b: (b[1], b[0])):
        if count_paths_in(page_data, s) == 0:
            continue
        for k in sorted(kept, key=lambda k: _edge_gap_sq(s, tuple(k))):
            union = (min(k[0], s[0]), min(k[1], s[1]),
                     max(k[2], s[2]), max(k[3], s[3]))
            if any(_overlap_area(union, tuple(o)) >
                   _overlap_area(tuple(k), tuple(o)) + eps
                   for o in kept if o is not k):
                continue
            k[0], k[1], k[2], k[3] = union
            break
    return [tuple(b) for b in kept]


def _attach_text_spans(page_data: PageData, boxes: list[BBox]) -> list[BBox]:
    """Grow paths-only boxes to absorb the text spans beside them.

    The tier-2 cut (see segment_page) finds boxes with text excluded from the
    ink map, so captions and labels land OUTSIDE every box — and classification
    crops without their titles lose the classifier's best signal. Each span
    folds into its nearest box under the same two rules _fold_small_leaves
    uses: never farther than CAPTION_MAX_GAP_PX (real captions measure
    44-48px), and never when the union would increase overlap with another
    box — a span in a shared gutter grows exactly one box, and one that leaks
    everywhere stays outside (coverage is path-based, so it costs nothing).
    """
    kept = [list(b) for b in boxes]
    eps = 1e-6
    max_gap_sq = float(CAPTION_MAX_GAP_PX) ** 2
    for t in sorted(page_data.text_spans, key=lambda t: (t.bbox[1], t.bbox[0])):
        s = t.bbox
        cx, cy = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        if any(k[0] <= cx <= k[2] and k[1] <= cy <= k[3] for k in kept):
            continue
        for k in sorted(kept, key=lambda k: _edge_gap_sq(s, tuple(k))):
            if _edge_gap_sq(s, tuple(k)) > max_gap_sq:
                break
            union = (min(k[0], s[0]), min(k[1], s[1]),
                     max(k[2], s[2]), max(k[3], s[3]))
            if any(_overlap_area(union, tuple(o)) >
                   _overlap_area(tuple(k), tuple(o)) + eps
                   for o in kept if o is not k):
                continue
            k[0], k[1], k[2], k[3] = union
            break
    return [tuple(b) for b in kept]


def _boxes_from_cut(
    page_data: PageData,
    ink: InkMap,
    min_bins: int,
    cut_rows: set[tuple[int, int, int]],
    cut_cols: set[tuple[int, int, int]],
    long_ink: InkMap | None = None,
    overhang_ink: InkMap | None = None,
) -> list[BBox]:
    leaves: list[tuple[int, int, int, int]] = []
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, min_bins, cut_rows, cut_cols, 0,
            leaves, long_ink, overhang_ink)
    boxes = [
        (float(c0 * ink.bin_px), float(r0 * ink.bin_px),
         float(c1 * ink.bin_px), float(r1 * ink.bin_px))
        for r0, r1, c0, c1 in leaves
    ]
    # Captions merge BEFORE the min-side filter: a real caption strip is
    # ~28px tall (measured on floor-plans.pdf: 380x28 and 356x28), well under
    # SEGMENT_MIN_REGION_SIDE_PX, so filtering first would drop every caption
    # before it could be folded into the drawing it titles.
    boxes = _merge_captions(page_data, boxes)
    kept, small = [], []
    for b in boxes:
        if (b[2] - b[0]) >= SEGMENT_MIN_REGION_SIDE_PX \
                and (b[3] - b[1]) >= SEGMENT_MIN_REGION_SIDE_PX:
            kept.append(b)
        else:
            small.append(b)
    # Path-bearing small leaves fold into their nearest kept region instead of
    # dropping — see _fold_small_leaves. With no kept region at all the page
    # falls back to whole-page detection anyway, so nothing needs folding.
    boxes = _fold_small_leaves(page_data, kept, small) if kept else []
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def segment_page(page_data: PageData, clip_rects: list[BBox] | None = None) -> list[Region]:
    """Split a page into drawing regions. Returns [] for a page with no vector
    ink (a scanned raster page) — callers must handle that before classifying."""
    if not page_data.paths:
        return []

    ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX)
    min_bins = max(1, SEGMENT_MIN_GUTTER_PX // ink.bin_px)
    cut_rows, cut_cols = clip_cut_positions(clip_rects or [], ink.bin_px)

    long_ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX,
                             min_path_len=SEGMENT_SHORT_INK_PX)
    # Tier 4 reads a PATHS-ONLY long map: text is never a drawing's edge, and
    # the caption lying in the band between an elevation and the plan below
    # it (s13, s17) would otherwise disqualify the band as sparse. The full
    # map keeps text for the chain check and for the empty sub-run the cut
    # goes through, so a caption is never sliced.
    overhang_ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX,
                                 include_text=False,
                                 min_path_len=SEGMENT_SHORT_INK_PX)
    boxes = _boxes_from_cut(page_data, ink, min_bins, cut_rows, cut_cols,
                            long_ink, overhang_ink)
    source = "whitespace+clip" if clip_rects else "whitespace"

    # Tier 2: a page the cut could not split at all gets one retry with text
    # excluded from the ink map. Text spans are stamped as FULL bboxes, so a
    # sheet whose drawings have generous gutters can still read as one blob —
    # measured on s15 (56,765 paths, 214 spans): 1 leaf at every gutter width
    # with text, 8 clean regions at the standard 20px gutter without it, and
    # whole-page fallback fed six elevations to the room detector (63 of 72
    # phantom rooms). Healthy sheets never reach this branch, so their region
    # geometry and cache keys are untouched; a textless page skips it (the
    # retry ink map would be identical); and a page that still will not split
    # keeps the tier-1 result so the pipeline falls back exactly as before.
    if len(boxes) <= 1 and page_data.text_spans:
        retry_ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX,
                                  include_text=False)
        retry_long = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX,
                                   include_text=False,
                                   min_path_len=SEGMENT_SHORT_INK_PX)
        retry = _boxes_from_cut(page_data, retry_ink, min_bins, cut_rows,
                                cut_cols, retry_long, retry_long)
        if len(retry) >= 2:
            boxes = _attach_text_spans(page_data, retry)
            source = "paths-only+clip" if clip_rects else "paths-only"

    return [
        Region(
            region_id=f"region_{i:04d}",
            bbox=b,
            region_type="unclassified",
            path_count=count_paths_in(page_data, b),
            source=source,
        )
        for i, b in enumerate(boxes)
    ]


def page_fallback_region(page_data: PageData) -> Region:
    """The whole page as a single region, for sheets too dense to split."""
    return Region(
        region_id="region_0000",
        bbox=(0.0, 0.0, page_data.width_px, page_data.height_px),
        region_type="unclassified",
        path_count=len(page_data.paths),
        source="page-fallback",
    )
