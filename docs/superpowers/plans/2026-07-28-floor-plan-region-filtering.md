# Floor-Plan Region Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split each PDF page into its constituent drawings by whitespace, ask Gemini which of them are floor plans, and run detection only on those — replacing the per-candidate Gemini validation that does not work.

**Architecture:** A new deterministic `layout/` package cuts the page into regions using the vector ink's own coordinates (no AI, no bounding-box guessing). A new `gemini/classifier.py` sends one small crop per region in a single API call and gets back a drawing type for each. `pipeline.py` then filters `PageData` down to the union of the `floor_plan` regions and runs `run_heuristics` **once** over that union. All coordinates stay in page space — nothing is cropped or translated, so the `outputs/` JSON contract is unchanged.

**Tech Stack:** Python 3.14, PyMuPDF (`fitz`), Pillow, `google-genai` (Vertex AI), `unittest`.

## Global Constraints

- All coordinates are **150-DPI pixels, top-left origin, y-down**. `SCALE = 150/72` is applied in `extraction/extractor.py`; never reintroduce point-space downstream.
- `BBox` is a `(x0, y0, x1, y1)` tuple. Page numbers in serialized output are **1-based**; `page_indices` between functions are **0-based**.
- Detection runs **once over the union** of kept regions. Never call `run_heuristics` per region — measured to degrade room detection (see spec "Rejected alternatives").
- `filter_page_data` must preserve `width_px` / `height_px` at full page size. Room detection filters on page fraction and page-border contact; shrinking them changes results.
- Import detection code from the `detection` facade, not submodules.
- Tests use `unittest`, run via `python -m unittest discover tests`.
- Never add a `Co-Authored-By` trailer to commits.
- Work on branch `feat/floor-plan-region-filtering` (branch off `main`).

**Constant values (copy verbatim):**

| Constant | Value |
|---|---|
| `SEGMENT_BIN_PX` | `4` |
| `SEGMENT_MIN_GUTTER_PX` | `20` |
| `SEGMENT_SPAN_FRAC` | `0.90` |
| `SEGMENT_MAX_DEPTH` | `6` |
| `SEGMENT_MIN_REGION_SIDE_PX` | `60` |
| `CAPTION_MAX_H_PX` | `64` |
| `CAPTION_MAX_GAP_PX` | `64` |
| `CAPTION_MIN_OVERLAP_FRAC` | `0.5` |
| `CLIP_MIN_INK_FRAC` | `0.05` |
| `CLIP_MAX_PAGE_FRAC` | `0.80` |
| `CROP_TARGET_LONG_EDGE_PX` | `1536` |
| `CROP_MAX_ZOOM` | `10.0` |

---

## File Structure

**Created:**
- `layout/__init__.py` — public facade: `segment_page`, `page_fallback_region`, `filter_page_data`, `region_text_spans`, `qualifying_clip_rects`
- `layout/constants.py` — all `SEGMENT_*`, `CAPTION_*`, `CLIP_*` constants
- `layout/occupancy.py` — ink occupancy map + page-spanning-primitive filter
- `layout/segmenter.py` — recursive XY-cut, caption merge, `Region` construction
- `layout/clips.py` — qualifying clip-rect collection (cut hints)
- `layout/filter.py` — primitive assignment and filtered `PageData` construction
- `gemini/classifier.py` — crop rendering, prompt, one classification call, response parsing
- `gemini/region_cache.py` — on-disk classification cache keyed by page content hash
- `tests/test_layout_occupancy.py`, `tests/test_layout_segmenter.py`, `tests/test_layout_clips.py`, `tests/test_layout_filter.py`, `tests/test_layout_golden.py`, `tests/test_region_classifier.py`, `tests/test_region_cache.py`, `tests/test_merge_offline.py`

**Modified:**
- `models.py` — add `Region` dataclass
- `gemini/client.py` — delete the validation path, keep `init_client`
- `pipeline.py` — collapse `merge_gemini_and_heuristics`, wire stages 2a/2b/2c
- `detection/orchestrator.py` — add `schedule_text_spans` parameter
- `extraction/renderer.py` — draw region outlines on the overlay
- `app.py` — add `--refresh-regions`
- `CLAUDE.md` — document the new stage and module layout

---

### Task 1: Ink occupancy map

**Files:**
- Create: `layout/__init__.py` (empty for now), `layout/constants.py`, `layout/occupancy.py`
- Test: `tests/test_layout_occupancy.py`

**Interfaces:**
- Consumes: `models.PageData`, `models.PathPrimitive`, `models.TextSpan`
- Produces: `layout.occupancy.InkMap` (fields `bins: list[bytearray]`, `rows: int`, `cols: int`, `bin_px: int`); `build_ink_map(page_data: PageData, bin_px: int = SEGMENT_BIN_PX) -> InkMap`; `is_page_spanning(p: PathPrimitive, width_px: float, height_px: float, span_frac: float = SEGMENT_SPAN_FRAC) -> bool`

**Why the span filter matters:** a sheet border drawn as four individual full-width/full-height lines makes every whitespace gutter impossible. Measured: `LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241.pdf` found **0** regions without this filter and 12 with it. A 3508×1px border line has a tiny bbox *area*, so an area-based filter does not catch it — the test is per-axis extent.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_occupancy.py`:

```python
"""Ink occupancy map tests (layout/occupancy.py)."""
import unittest

from models import PageData, PathPrimitive, TextSpan
from layout.occupancy import InkMap, build_ink_map, is_page_spanning

PAGE_W, PAGE_H = 400.0, 300.0


def path(idx, points, item_type="l"):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=points,
    )


def span(text, bbox):
    return TextSpan(text=text, bbox=bbox, font="Helvetica", size=10.0,
                    color=0, block_no=0, line_no=0)


def page(paths=(), text_spans=()):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=list(paths), text_spans=list(text_spans))


class TestPageSpanning(unittest.TestCase):
    def test_full_width_hairline_is_page_spanning(self):
        border = path(0, [(0.0, 10.0), (PAGE_W, 10.0)])
        self.assertTrue(is_page_spanning(border, PAGE_W, PAGE_H))

    def test_full_height_hairline_is_page_spanning(self):
        border = path(0, [(10.0, 0.0), (10.0, PAGE_H)])
        self.assertTrue(is_page_spanning(border, PAGE_W, PAGE_H))

    def test_half_width_line_is_not_page_spanning(self):
        wall = path(0, [(0.0, 10.0), (PAGE_W / 2, 10.0)])
        self.assertFalse(is_page_spanning(wall, PAGE_W, PAGE_H))


class TestBuildInkMap(unittest.TestCase):
    def test_map_dimensions_follow_page_and_bin_size(self):
        ink = build_ink_map(page(), bin_px=4)
        self.assertEqual(ink.bin_px, 4)
        self.assertEqual(ink.cols, int(PAGE_W / 4) + 1)
        self.assertEqual(ink.rows, int(PAGE_H / 4) + 1)
        self.assertEqual(len(ink.bins), ink.rows)
        self.assertEqual(len(ink.bins[0]), ink.cols)

    def test_line_marks_bins_along_its_length(self):
        ink = build_ink_map(page([path(0, [(40.0, 100.0), (80.0, 100.0)])]), bin_px=4)
        row = 100 // 4
        self.assertEqual(ink.bins[row][40 // 4], 1)
        self.assertEqual(ink.bins[row][60 // 4], 1)
        self.assertEqual(ink.bins[row][80 // 4], 1)
        self.assertEqual(ink.bins[row][120 // 4], 0)

    def test_page_spanning_primitive_is_excluded_from_the_map(self):
        border = path(0, [(0.0, 100.0), (PAGE_W, 100.0)])
        ink = build_ink_map(page([border]), bin_px=4)
        self.assertEqual(sum(sum(r) for r in ink.bins), 0)

    def test_rect_closing_edge_is_marked(self):
        # points for a "re" run corner-to-corner without repeating the first
        pts = [(40.0, 40.0), (80.0, 40.0), (80.0, 80.0), (40.0, 80.0)]
        ink = build_ink_map(page([path(0, pts, item_type="re")]), bin_px=4)
        # the closing edge is the left side, x=40, between y=40 and y=80
        self.assertEqual(ink.bins[60 // 4][40 // 4], 1)

    def test_text_span_bbox_is_filled(self):
        ink = build_ink_map(page(text_spans=[span("PLAN", (100.0, 200.0, 140.0, 212.0))]),
                            bin_px=4)
        self.assertEqual(ink.bins[204 // 4][120 // 4], 1)

    def test_diagonal_line_is_sampled_not_bbox_filled(self):
        ink = build_ink_map(page([path(0, [(40.0, 40.0), (80.0, 80.0)])]), bin_px=4)
        self.assertEqual(ink.bins[60 // 4][60 // 4], 1)   # on the diagonal
        self.assertEqual(ink.bins[44 // 4][76 // 4], 0)   # bbox corner, off the line


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_occupancy -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'layout'`

- [ ] **Step 3: Create the package and constants**

Create `layout/__init__.py` as an empty file.

Create `layout/constants.py`:

```python
"""Tunable constants for page segmentation.

Values are measured, not guessed — see
docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md.
All lengths are 150-DPI pixels.
"""
from __future__ import annotations

# Occupancy resolution. Fine enough to resolve a SEGMENT_MIN_GUTTER_PX gap.
SEGMENT_BIN_PX = 4

# A fully-empty band must be at least this wide to be cut at. Measured
# insensitive: 12px, 20px and 28px give byte-identical splits on every
# reference sheet.
SEGMENT_MIN_GUTTER_PX = 20

# A primitive spanning this fraction of the page in either axis is sheet
# furniture (border rule, column divider), never drawing content. Load-bearing:
# without it a single border line makes every gutter impossible.
SEGMENT_SPAN_FRAC = 0.90

# Backstop against pathological recursion.
SEGMENT_MAX_DEPTH = 6

# Below this on either side a region cannot be a drawing.
SEGMENT_MIN_REGION_SIDE_PX = 60

# A caption is a zero-path strip no taller than this. Measured: real captions
# are 28px; the notes paragraph on 2557737 is 284px and must NOT merge.
CAPTION_MAX_H_PX = 64

# Vertical gap between a caption and its drawing. Measured 44-48px.
CAPTION_MAX_GAP_PX = 64

# A caption must overlap its drawing by this fraction of the caption's width.
CAPTION_MIN_OVERLAP_FRAC = 0.5

# A clip rect is a real drawing boundary only if it holds this share of the
# page's paths. Measured: text/annotation clips 0.0-1.3%, drawing clips
# 5.7-62.4% — no overlap between the bands.
CLIP_MIN_INK_FRAC = 0.05

# A clip covering this much of the page is the whole-sheet clip, not a drawing.
# Measured whole-sheet clips at 88-97%.
CLIP_MAX_PAGE_FRAC = 0.80
```

- [ ] **Step 4: Write the occupancy map**

Create `layout/occupancy.py`:

```python
"""Binary ink occupancy map over a page, used to find whitespace gutters."""
from __future__ import annotations

from dataclasses import dataclass

from models import PageData, PathPrimitive
from layout.constants import SEGMENT_BIN_PX, SEGMENT_SPAN_FRAC


@dataclass
class InkMap:
    """bins[row][col] is 1 where drawn ink falls, 0 elsewhere."""
    bins: list[bytearray]
    rows: int
    cols: int
    bin_px: int


def is_page_spanning(
    p: PathPrimitive,
    width_px: float,
    height_px: float,
    span_frac: float = SEGMENT_SPAN_FRAC,
) -> bool:
    """True for sheet furniture: a border rule or column divider that runs the
    length of the page. Tested per-axis, not by area — a 3508x1px border line
    has a negligible bbox area but blocks every vertical gutter."""
    return (
        (p.bbox[2] - p.bbox[0]) > span_frac * width_px
        or (p.bbox[3] - p.bbox[1]) > span_frac * height_px
    )


def build_ink_map(page_data: PageData, bin_px: int = SEGMENT_BIN_PX) -> InkMap:
    cols = int(page_data.width_px / bin_px) + 1
    rows = int(page_data.height_px / bin_px) + 1
    bins = [bytearray(cols) for _ in range(rows)]

    def plot(x: float, y: float) -> None:
        c, r = int(x / bin_px), int(y / bin_px)
        if 0 <= r < rows and 0 <= c < cols:
            bins[r][c] = 1

    def segment(p0: tuple[float, float], p1: tuple[float, float]) -> None:
        (x0, y0), (x1, y1) = p0, p1
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / bin_px) + 1)
        for i in range(steps + 1):
            t = i / steps
            plot(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    for p in page_data.paths:
        if is_page_spanning(p, page_data.width_px, page_data.height_px):
            continue
        pts = p.points
        if len(pts) >= 2:
            for a, b in zip(pts, pts[1:]):
                segment(a, b)
            # `re`/`qu` runs list corners without repeating the first point.
            if p.item_type in ("re", "qu") and len(pts) >= 3:
                segment(pts[-1], pts[0])
        elif pts:
            plot(*pts[0])

    for t in page_data.text_spans:
        x0, y0, x1, y1 = t.bbox
        for r in range(int(y0 / bin_px), int(y1 / bin_px) + 1):
            for c in range(int(x0 / bin_px), int(x1 / bin_px) + 1):
                if 0 <= r < rows and 0 <= c < cols:
                    bins[r][c] = 1

    return InkMap(bins=bins, rows=rows, cols=cols, bin_px=bin_px)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_occupancy -v`
Expected: PASS, 9 tests

- [ ] **Step 6: Commit**

```bash
git checkout -b feat/floor-plan-region-filtering
git add layout/__init__.py layout/constants.py layout/occupancy.py tests/test_layout_occupancy.py
git commit -m "feat(layout): ink occupancy map with page-spanning primitive filter"
```

---

### Task 2: Recursive XY-cut

**Files:**
- Create: `layout/segmenter.py`
- Test: `tests/test_layout_segmenter.py`

**Interfaces:**
- Consumes: `layout.occupancy.InkMap`, `layout.constants.SEGMENT_MAX_DEPTH`
- Produces: `_xy_cut(ink: InkMap, r0: int, r1: int, c0: int, c1: int, min_bins: int, cut_rows: set[int], cut_cols: set[int], depth: int, out: list[tuple[int, int, int, int]]) -> None` — appends `(r0, r1, c0, c1)` bin-space leaves to `out`. Also `_row_profile`, `_col_profile`, `_trim`, `_widest_gap`, `_clip_cut`.

Cut preference is: widest empty band first (rows vs columns, whichever band is thicker), then a clip edge if no band qualifies. A clip edge has zero width, so "cut at whichever is wider" always prefers a real gutter — this ordering *is* the spec's rule.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_segmenter.py`:

```python
"""Recursive XY-cut tests (layout/segmenter.py)."""
import unittest

from models import PageData, PathPrimitive
from layout.occupancy import build_ink_map
from layout.segmenter import _trim, _widest_gap, _clip_cut, _xy_cut

PAGE_W, PAGE_H = 400.0, 400.0
BIN = 4


def block(idx, x0, y0, x1, y1):
    """A solid-ish blob: a horizontal line every 4px so every bin row is inked."""
    return [
        PathPrimitive(
            path_index=idx + i, item_type="l",
            bbox=(x0, y, x1, y), color=(0.0, 0.0, 0.0), fill=None,
            stroke_width=1.5, dashes="", layer=None,
            points=[(x0, y), (x1, y)],
        )
        for i, y in enumerate(range(int(y0), int(y1), 4))
    ]


def page(paths):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=list(paths))


def cut(page_data, min_gutter_px=20, cut_rows=frozenset(), cut_cols=frozenset()):
    ink = build_ink_map(page_data, bin_px=BIN)
    out = []
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, max(1, min_gutter_px // BIN),
            set(cut_rows), set(cut_cols), 0, out)
    return [(c0 * BIN, r0 * BIN, c1 * BIN, r1 * BIN) for r0, r1, c0, c1 in out]


class TestProfileHelpers(unittest.TestCase):
    def test_trim_strips_leading_and_trailing_zeros(self):
        self.assertEqual(_trim([0, 0, 3, 4, 0], 10), (12, 14))

    def test_widest_gap_finds_the_longest_internal_run_of_zeros(self):
        self.assertEqual(_widest_gap([5, 0, 0, 5, 0, 0, 0, 5], 0, 2), (4, 7))

    def test_widest_gap_ignores_runs_shorter_than_min_bins(self):
        self.assertIsNone(_widest_gap([5, 0, 5], 0, 2))

    def test_widest_gap_ignores_leading_and_trailing_zeros(self):
        self.assertIsNone(_widest_gap([0, 0, 0, 5, 0, 0, 0], 0, 3))

    def test_clip_cut_returns_a_position_with_ink_on_both_sides(self):
        self.assertEqual(_clip_cut([5, 5, 5, 5], 0, {2}), 2)

    def test_clip_cut_rejects_a_position_with_ink_on_one_side_only(self):
        self.assertIsNone(_clip_cut([0, 0, 5, 5], 0, {1}))


class TestXYCut(unittest.TestCase):
    def test_single_blob_yields_one_region(self):
        boxes = cut(page(block(0, 40, 40, 200, 200)))
        self.assertEqual(len(boxes), 1)

    def test_two_blobs_split_by_a_wide_vertical_gutter(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 2)

    def test_two_blobs_split_by_a_wide_horizontal_gutter(self):
        paths = block(0, 40, 40, 200, 140) + block(500, 40, 250, 200, 360)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 2)

    def test_gap_narrower_than_the_threshold_does_not_split(self):
        # 8px gap between the two blobs, threshold 20px
        paths = block(0, 40, 40, 150, 200) + block(500, 158, 40, 300, 200)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 1)

    def test_regions_are_trimmed_to_their_ink(self):
        boxes = cut(page(block(0, 100, 100, 200, 200)))
        x0, y0, x1, y1 = boxes[0]
        self.assertGreaterEqual(x0, 96)
        self.assertLessEqual(x1, 208)
        self.assertGreaterEqual(y0, 96)
        self.assertLessEqual(y1, 208)

    def test_clip_edge_splits_when_no_gutter_exists(self):
        # One continuous blob: no gutter anywhere, so only a clip edge can cut it.
        paths = block(0, 40, 40, 360, 200)
        without = cut(page(paths))
        self.assertEqual(len(without), 1)
        with_clip = cut(page(paths), cut_cols={200 // BIN})
        self.assertEqual(len(with_clip), 2)

    def test_gutter_is_preferred_over_a_clip_edge(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        # A clip edge in a silly place must not win over the real gutter.
        boxes = cut(page(paths), cut_cols={100 // BIN})
        self.assertEqual(len(boxes), 2)
        xs = sorted(b[0] for b in boxes)
        self.assertGreater(xs[1], 200)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_segmenter -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'layout.segmenter'`

- [ ] **Step 3: Write the XY-cut**

Create `layout/segmenter.py`:

```python
"""Recursive XY-cut: split a page into drawing regions at whitespace gutters."""
from __future__ import annotations

from typing import Optional

from layout.constants import SEGMENT_MAX_DEPTH
from layout.occupancy import InkMap


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


def _clip_cut(profile: list[int], offset: int, cut_positions: set[int]) -> Optional[int]:
    """First clip edge lying strictly inside the span with ink on both sides."""
    n = len(profile)
    for pos in sorted(cut_positions):
        idx = pos - offset
        if idx <= 0 or idx >= n:
            continue
        if any(profile[:idx]) and any(profile[idx:]):
            return pos
    return None


def _xy_cut(
    ink: InkMap,
    r0: int, r1: int, c0: int, c1: int,
    min_bins: int,
    cut_rows: set[int],
    cut_cols: set[int],
    depth: int,
    out: list[tuple[int, int, int, int]],
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
            _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
            _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        else:
            m = (gap_c[0] + gap_c[1]) // 2
            _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out)
            _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    m = _clip_cut(rows, r0, cut_rows)
    if m is not None:
        _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    m = _clip_cut(cols, c0, cut_cols)
    if m is not None:
        _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out)
        _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    out.append((r0, r1, c0, c1))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_segmenter -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add layout/segmenter.py tests/test_layout_segmenter.py
git commit -m "feat(layout): recursive XY-cut with clip-edge fallback"
```

---

### Task 3: Qualifying clip rects

**Files:**
- Create: `layout/clips.py`
- Test: `tests/test_layout_clips.py`

**Interfaces:**
- Consumes: `models.PageData`, `layout.constants.CLIP_MIN_INK_FRAC`, `CLIP_MAX_PAGE_FRAC`
- Produces: `qualifying_clip_rects_from_boxes(boxes_px: list[BBox], page_data: PageData) -> list[BBox]`; `qualifying_clip_rects(page, page_data: PageData) -> list[BBox]` (thin `fitz` wrapper); `clip_cut_positions(clip_rects: list[BBox], bin_px: int) -> tuple[set[int], set[int]]`

The two-function split exists so the gating logic is testable without a real `fitz.Page`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_clips.py`:

```python
"""Clip-rect gating tests (layout/clips.py)."""
import unittest

from models import PageData, PathPrimitive
from layout.clips import qualifying_clip_rects_from_boxes, clip_cut_positions

PAGE_W, PAGE_H = 1000.0, 1000.0


def dot(idx, x, y):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x, y, x + 1, y + 1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.0,
        dashes="", layer=None, points=[(x, y), (x + 1, y + 1)],
    )


def page_with(paths):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=list(paths))


class TestClipGating(unittest.TestCase):
    def setUp(self):
        # 100 paths: 40 inside the drawing clip, 1 inside the annotation clip,
        # 59 elsewhere.
        paths = [dot(i, 110 + (i % 20), 110 + (i % 20)) for i in range(40)]
        paths += [dot(100, 700, 700)]
        paths += [dot(200 + i, 400 + (i % 30), 800) for i in range(59)]
        self.page = page_with(paths)

    def test_drawing_clip_qualifies(self):
        drawing = (100.0, 100.0, 300.0, 300.0)   # holds 40/100 paths = 40%
        self.assertIn(drawing, qualifying_clip_rects_from_boxes([drawing], self.page))

    def test_annotation_clip_is_rejected_on_ink_share(self):
        annot = (690.0, 690.0, 730.0, 730.0)     # holds 1/100 paths = 1%
        self.assertEqual(qualifying_clip_rects_from_boxes([annot], self.page), [])

    def test_whole_sheet_clip_is_rejected_on_page_area(self):
        sheet = (0.0, 0.0, 950.0, 950.0)         # 90% of the page
        self.assertEqual(qualifying_clip_rects_from_boxes([sheet], self.page), [])

    def test_duplicate_boxes_are_returned_once(self):
        drawing = (100.0, 100.0, 300.0, 300.0)
        got = qualifying_clip_rects_from_boxes([drawing, drawing, drawing], self.page)
        self.assertEqual(len(got), 1)

    def test_degenerate_box_is_rejected(self):
        self.assertEqual(
            qualifying_clip_rects_from_boxes([(100.0, 100.0, 100.0, 300.0)], self.page), [])

    def test_page_with_no_paths_qualifies_nothing(self):
        empty = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H)
        self.assertEqual(
            qualifying_clip_rects_from_boxes([(10.0, 10.0, 200.0, 200.0)], empty), [])


class TestClipCutPositions(unittest.TestCase):
    def test_edges_become_bin_indices_on_both_axes(self):
        rows, cols = clip_cut_positions([(40.0, 80.0, 200.0, 240.0)], bin_px=4)
        self.assertEqual(cols, {10, 50})
        self.assertEqual(rows, {20, 60})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_clips -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'layout.clips'`

- [ ] **Step 3: Write the clip collector**

Create `layout/clips.py`:

```python
"""Native PDF clip rects, used as extra cut hints for the segmenter.

Clip rects are NOT used as regions. They overlap and nest each other (five do
on REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461), so feeding them as cut
candidates is what preserves the invariant that segmentation yields a
partition. They are also absent on 13 of 20 sample files, so they can only ever
supplement the whitespace cut.
"""
from __future__ import annotations

from models import BBox, PageData
from layout.constants import CLIP_MAX_PAGE_FRAC, CLIP_MIN_INK_FRAC

SCALE = 150 / 72


def qualifying_clip_rects_from_boxes(
    boxes_px: list[BBox], page_data: PageData
) -> list[BBox]:
    """Keep only clips that look like real drawing boundaries.

    Measured on the sample set: text and annotation clips hold 0.0-1.3% of the
    page's paths, real drawing clips hold 5.7-62.4%, and whole-sheet clips
    cover 88-97% of the page area. The two gates separate cleanly.
    """
    centres = [
        ((p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2)
        for p in page_data.paths
    ]
    total = len(centres)
    if not total:
        return []

    page_area = page_data.width_px * page_data.height_px
    seen: set[BBox] = set()
    out: list[BBox] = []
    for box in boxes_px:
        if box in seen:
            continue
        seen.add(box)
        w, h = box[2] - box[0], box[3] - box[1]
        if w <= 0 or h <= 0:
            continue
        if (w * h) >= CLIP_MAX_PAGE_FRAC * page_area:
            continue
        inside = sum(
            1 for cx, cy in centres
            if box[0] <= cx <= box[2] and box[1] <= cy <= box[3]
        )
        if inside / total >= CLIP_MIN_INK_FRAC:
            out.append(box)
    return out


def qualifying_clip_rects(page, page_data: PageData) -> list[BBox]:
    """Read scissor rects off a fitz.Page and gate them. Returns [] if the
    PDF exposes none, which is the common case."""
    import fitz

    boxes: list[BBox] = []
    try:
        drawings = page.get_drawings(extended=True)
    except Exception:
        return []
    for d in drawings:
        s = d.get("scissor")
        if s is None:
            continue
        r = fitz.Rect(s)
        boxes.append((
            round(r.x0 * SCALE), round(r.y0 * SCALE),
            round(r.x1 * SCALE), round(r.y1 * SCALE),
        ))
    return qualifying_clip_rects_from_boxes(boxes, page_data)


def clip_cut_positions(
    clip_rects: list[BBox], bin_px: int
) -> tuple[set[int], set[int]]:
    """Convert clip edges to (row_bins, col_bins) cut candidates."""
    rows: set[int] = set()
    cols: set[int] = set()
    for x0, y0, x1, y1 in clip_rects:
        cols.add(int(x0 / bin_px))
        cols.add(int(x1 / bin_px))
        rows.add(int(y0 / bin_px))
        rows.add(int(y1 / bin_px))
    return rows, cols
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_clips -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add layout/clips.py tests/test_layout_clips.py
git commit -m "feat(layout): gate native clip rects by ink share and page area"
```

---

### Task 4: Region model, caption merge, `segment_page`

**Files:**
- Modify: `models.py` (append `Region` after `Entity`), `layout/segmenter.py`, `layout/__init__.py`
- Test: `tests/test_layout_segmenter.py` (append a new test class)

**Interfaces:**
- Consumes: `_xy_cut` (Task 2), `clip_cut_positions` (Task 3)
- Produces: `models.Region`; `layout.segmenter.segment_page(page_data: PageData, clip_rects: list[BBox] | None = None) -> list[Region]`; `layout.segmenter.page_fallback_region(page_data: PageData) -> Region`; `layout.segmenter.count_paths_in(page_data: PageData, box: BBox) -> int`

Captions must merge because drawing titles otherwise split off as their own zero-path regions — measured on `floor-plans.pdf`, where "PROPOSED GROUND FLOOR PLAN" and "PROPOSED FIRST FLOOR PLAN" each became a separate region. A caption that finds no drawing to merge into is **kept** as its own region so `regions.json` records the whole sheet (the 568×284px notes block on `2557737` is one of these).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout_segmenter.py` (before the `if __name__` block), and add `TextSpan`, `Region`, `segment_page`, `page_fallback_region` to the imports at the top:

```python
class TestSegmentPage(unittest.TestCase):
    def _page_with_caption(self, caption_gap, caption_h):
        paths = block(0, 100, 100, 300, 300)
        y0 = 300.0 + caption_gap
        spans = [TextSpan(text="GROUND FLOOR PLAN", bbox=(120.0, y0, 280.0, y0 + caption_h),
                          font="Helvetica", size=10.0, color=0, block_no=0, line_no=0)]
        return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                        paths=paths, text_spans=spans)

    def test_caption_merges_into_its_drawing(self):
        regions = segment_page(self._page_with_caption(caption_gap=40, caption_h=20))
        self.assertEqual(len(regions), 1)
        self.assertGreater(regions[0].bbox[3], 300.0)

    def test_tall_text_block_does_not_merge(self):
        regions = segment_page(self._page_with_caption(caption_gap=40, caption_h=200))
        self.assertEqual(len(regions), 2)

    def test_distant_caption_does_not_merge(self):
        regions = segment_page(self._page_with_caption(caption_gap=200, caption_h=20))
        self.assertEqual(len(regions), 2)

    def test_regions_get_sequential_ids_and_unclassified_type(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths))
        self.assertEqual([r.region_id for r in regions], ["region_0000", "region_0001"])
        self.assertTrue(all(r.region_type == "unclassified" for r in regions))
        self.assertTrue(all(r.source == "whitespace" for r in regions))
        self.assertTrue(all(r.path_count > 0 for r in regions))

    def test_source_records_clip_involvement(self):
        paths = block(0, 40, 40, 360, 200)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths),
                               clip_rects=[(40.0, 40.0, 200.0, 200.0)])
        self.assertTrue(all(r.source == "whitespace+clip" for r in regions))

    def test_tiny_regions_are_dropped(self):
        paths = block(0, 40, 40, 200, 200) + block(500, 300, 300, 330, 330)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths))
        self.assertEqual(len(regions), 1)

    def test_page_with_no_paths_yields_no_regions(self):
        self.assertEqual(segment_page(PageData(page_number=1, width_px=PAGE_W,
                                               height_px=PAGE_H)), [])

    def test_page_fallback_region_covers_the_whole_page(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 200, 200))
        r = page_fallback_region(pd)
        self.assertEqual(r.bbox, (0.0, 0.0, PAGE_W, PAGE_H))
        self.assertEqual(r.source, "page-fallback")
        self.assertEqual(r.path_count, len(pd.paths))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_segmenter -v`
Expected: FAIL with `ImportError: cannot import name 'segment_page'`

- [ ] **Step 3: Add the Region dataclass**

Append to `models.py` after the `Entity` dataclass:

```python
@dataclass
class Region:
    """One drawing on a sheet, found by whitespace segmentation.

    bbox is 150-DPI pixels in PAGE space — regions select which primitives
    detection sees, they never crop or translate coordinates.
    """
    region_id: str                     # "region_0000"
    bbox: BBox
    region_type: str = "unclassified"  # taxonomy value from the classifier
    title: Optional[str] = None
    confidence: float = 0.0
    contains_multiple: bool = False
    path_count: int = 0
    source: Literal["whitespace", "whitespace+clip", "page-fallback"] = "whitespace"
```

- [ ] **Step 4: Add caption merge and `segment_page`**

Append to `layout/segmenter.py`, and extend its imports to:

```python
from models import BBox, PageData, Region
from layout.clips import clip_cut_positions
from layout.constants import (
    CAPTION_MAX_GAP_PX, CAPTION_MAX_H_PX, CAPTION_MIN_OVERLAP_FRAC,
    SEGMENT_BIN_PX, SEGMENT_MAX_DEPTH, SEGMENT_MIN_GUTTER_PX,
    SEGMENT_MIN_REGION_SIDE_PX,
)
from layout.occupancy import InkMap, build_ink_map
```

```python
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


def segment_page(page_data: PageData, clip_rects: list[BBox] | None = None) -> list[Region]:
    """Split a page into drawing regions. Returns [] for a page with no vector
    ink (a scanned raster page) — callers must handle that before classifying."""
    if not page_data.paths:
        return []

    ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX)
    min_bins = max(1, SEGMENT_MIN_GUTTER_PX // ink.bin_px)
    cut_rows, cut_cols = clip_cut_positions(clip_rects or [], ink.bin_px)

    leaves: list[tuple[int, int, int, int]] = []
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, min_bins, cut_rows, cut_cols, 0, leaves)

    boxes = [
        (float(c0 * ink.bin_px), float(r0 * ink.bin_px),
         float(c1 * ink.bin_px), float(r1 * ink.bin_px))
        for r0, r1, c0, c1 in leaves
    ]
    boxes = [
        b for b in boxes
        if (b[2] - b[0]) >= SEGMENT_MIN_REGION_SIDE_PX
        and (b[3] - b[1]) >= SEGMENT_MIN_REGION_SIDE_PX
    ]
    boxes = _merge_captions(page_data, boxes)
    boxes.sort(key=lambda b: (b[1], b[0]))

    source = "whitespace+clip" if clip_rects else "whitespace"
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
```

- [ ] **Step 5: Export the facade**

Replace the contents of `layout/__init__.py`:

```python
"""Page segmentation: split a sheet into its constituent drawings."""
from layout.clips import clip_cut_positions, qualifying_clip_rects
from layout.segmenter import count_paths_in, page_fallback_region, segment_page

__all__ = [
    "clip_cut_positions",
    "count_paths_in",
    "page_fallback_region",
    "qualifying_clip_rects",
    "segment_page",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_segmenter -v`
Expected: PASS, 21 tests

- [ ] **Step 7: Commit**

```bash
git add models.py layout/segmenter.py layout/__init__.py tests/test_layout_segmenter.py
git commit -m "feat(layout): Region model, caption merge, segment_page entry point"
```

---

### Task 5: Primitive assignment and filtered PageData

**Files:**
- Create: `layout/filter.py`
- Modify: `layout/__init__.py`
- Test: `tests/test_layout_filter.py`

**Interfaces:**
- Consumes: `models.Region`, `models.PageData`
- Produces: `filter_page_data(page_data: PageData, regions: list[Region]) -> PageData`; `region_text_spans(page_data: PageData, regions: list[Region]) -> list[TextSpan]`

`filter_page_data` **must** keep `width_px` / `height_px` at full page size. Room detection filters components by page fraction and page-border contact; shrinking the page dimensions silently changes which rooms survive.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_filter.py`:

```python
"""Region filtering tests (layout/filter.py)."""
import unittest

from models import ImageRef, PageData, PathPrimitive, Region, TextSpan
from layout.filter import filter_page_data, region_text_spans

PAGE_W, PAGE_H = 1000.0, 800.0


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def span(text, x0, y0, x1, y1):
    return TextSpan(text=text, bbox=(x0, y0, x1, y1), font="Helvetica",
                    size=10.0, color=0, block_no=0, line_no=0)


def region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


class TestFilterPageData(unittest.TestCase):
    def setUp(self):
        self.left = path(0, 100.0, 100.0, 200.0, 200.0)     # centre (150,150)
        self.right = path(1, 600.0, 100.0, 700.0, 200.0)    # centre (650,150)
        self.outside = path(2, 800.0, 600.0, 900.0, 700.0)  # centre (850,650)
        self.page = PageData(
            page_number=1, width_px=PAGE_W, height_px=PAGE_H,
            paths=[self.left, self.right, self.outside],
            text_spans=[span("PLAN", 120.0, 220.0, 180.0, 232.0),
                        span("NOTES", 810.0, 610.0, 890.0, 622.0)],
            images=[ImageRef(xref=1, bbox=(110.0, 110.0, 190.0, 190.0),
                             width=80, height=80, colorspace="DeviceRGB",
                             pixel_area=0.01)],
            ocg_names=["walls"], page_type="vector-rich",
        )
        self.r0 = region("region_0000", (50.0, 50.0, 300.0, 300.0))
        self.r1 = region("region_0001", (550.0, 50.0, 750.0, 300.0))

    def test_keeps_only_primitives_whose_centre_is_in_a_region(self):
        out = filter_page_data(self.page, [self.r0, self.r1])
        self.assertEqual([p.path_index for p in out.paths], [0, 1])

    def test_page_dimensions_are_preserved(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual(out.width_px, PAGE_W)
        self.assertEqual(out.height_px, PAGE_H)

    def test_page_metadata_is_preserved(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual(out.page_number, 1)
        self.assertEqual(out.ocg_names, ["walls"])
        self.assertEqual(out.page_type, "vector-rich")

    def test_text_spans_and_images_are_filtered_too(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual([s.text for s in out.text_spans], ["PLAN"])
        self.assertEqual(len(out.images), 1)

    def test_original_page_data_is_not_mutated(self):
        filter_page_data(self.page, [self.r0])
        self.assertEqual(len(self.page.paths), 3)
        self.assertEqual(len(self.page.text_spans), 2)

    def test_regions_covering_everything_reproduce_the_original_path_set(self):
        whole = region("region_0000", (0.0, 0.0, PAGE_W, PAGE_H))
        out = filter_page_data(self.page, [whole])
        self.assertEqual([p.path_index for p in out.paths],
                         [p.path_index for p in self.page.paths])

    def test_empty_region_list_keeps_nothing(self):
        out = filter_page_data(self.page, [])
        self.assertEqual(out.paths, [])


class TestRegionTextSpans(unittest.TestCase):
    def test_returns_only_spans_inside_the_given_regions(self):
        page = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                        text_spans=[span("DOOR SCHEDULE", 600.0, 600.0, 750.0, 615.0),
                                    span("KITCHEN", 100.0, 100.0, 160.0, 112.0)])
        sched = region("region_0000", (550.0, 550.0, 800.0, 700.0), "schedule_table")
        self.assertEqual([s.text for s in region_text_spans(page, [sched])],
                         ["DOOR SCHEDULE"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_filter -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'layout.filter'`

- [ ] **Step 3: Write the filter**

Create `layout/filter.py`:

```python
"""Reduce a PageData to the primitives inside a set of regions.

This filters, it does not crop: every coordinate stays in page space and
width_px/height_px stay at full page size. Room detection filters components by
page fraction and by page-border contact, so shrinking the page dimensions
would silently change which rooms survive.
"""
from __future__ import annotations

import copy

from models import BBox, PageData, Region, TextSpan


def _centre_in_any(bbox: BBox, boxes: list[BBox]) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def filter_page_data(page_data: PageData, regions: list[Region]) -> PageData:
    """A copy of page_data holding only primitives whose bbox centre falls in
    one of the regions. Whole primitives are kept or dropped — nothing is
    sliced, because regions are derived from the ink itself."""
    boxes = [r.bbox for r in regions]
    out = copy.copy(page_data)
    out.paths = [p for p in page_data.paths if _centre_in_any(p.bbox, boxes)]
    out.text_spans = [t for t in page_data.text_spans if _centre_in_any(t.bbox, boxes)]
    out.images = [i for i in page_data.images if _centre_in_any(i.bbox, boxes)]
    return out


def region_text_spans(page_data: PageData, regions: list[Region]) -> list[TextSpan]:
    """Text spans inside the given regions. Used to scope schedule detection to
    schedule_table regions without touching geometry detection."""
    boxes = [r.bbox for r in regions]
    return [t for t in page_data.text_spans if _centre_in_any(t.bbox, boxes)]
```

- [ ] **Step 4: Export from the facade**

Edit `layout/__init__.py` to add the two new names:

```python
"""Page segmentation: split a sheet into its constituent drawings."""
from layout.clips import clip_cut_positions, qualifying_clip_rects
from layout.filter import filter_page_data, region_text_spans
from layout.segmenter import count_paths_in, page_fallback_region, segment_page

__all__ = [
    "clip_cut_positions",
    "count_paths_in",
    "filter_page_data",
    "page_fallback_region",
    "qualifying_clip_rects",
    "region_text_spans",
    "segment_page",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_filter -v`
Expected: PASS, 9 tests

- [ ] **Step 6: Commit**

```bash
git add layout/filter.py layout/__init__.py tests/test_layout_filter.py
git commit -m "feat(layout): filter PageData to a region set, preserving page dimensions"
```

---

### Task 6: Golden segmentation tests against the real PDFs

**Files:**
- Create: `tests/test_layout_golden.py`

**Interfaces:**
- Consumes: `layout.segment_page`, `layout.qualifying_clip_rects`, `extraction.extractor.extract_page`
- Produces: nothing — this task locks measured behaviour so later refactors cannot silently change it.

These numbers were measured on 2026-07-28. If a test here fails after a change, the change altered segmentation on a reference sheet — investigate before updating the number.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_golden.py`:

```python
"""Golden segmentation results on the checked-in reference PDFs.

Measured 2026-07-28. A failure here means segmentation behaviour changed on a
real sheet — investigate before touching the expected numbers.
"""
import os
import unittest

import fitz

from extraction.extractor import extract_page
from layout import qualifying_clip_rects, segment_page
from layout.occupancy import build_ink_map, is_page_spanning

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def segment(pdf_name, page_index=0, use_clips=True):
    path = os.path.join(REPO, pdf_name)
    doc = fitz.open(path)
    page_data = extract_page(doc, page_index)
    clips = qualifying_clip_rects(doc[page_index], page_data) if use_clips else []
    regions = segment_page(page_data, clips)
    doc.close()
    return page_data, regions


class TestGoldenSegmentation(unittest.TestCase):
    def test_floor_plans_splits_into_two_regions(self):
        page_data, regions = segment("floor-plans.pdf")
        self.assertEqual(len(regions), 2)

    def test_floor_plans_assigns_every_path(self):
        page_data, regions = segment("floor-plans.pdf")
        self.assertEqual(sum(r.path_count for r in regions), len(page_data.paths))

    def test_floor_plans_captions_merged_so_titles_are_inside_regions(self):
        page_data, regions = segment("floor-plans.pdf")
        titles = {"PROPOSED GROUND FLOOR PLAN", "PROPOSED FIRST FLOOR PLAN"}
        found = set()
        for span in page_data.text_spans:
            text = span.text.strip()
            if text not in titles:
                continue
            cx = (span.bbox[0] + span.bbox[2]) / 2
            cy = (span.bbox[1] + span.bbox[3]) / 2
            for r in regions:
                if r.bbox[0] <= cx <= r.bbox[2] and r.bbox[1] <= cy <= r.bbox[3]:
                    found.add(text)
        self.assertEqual(found, titles)

    def test_5_1133_is_too_dense_to_split(self):
        _, regions = segment("5-1133-WD03.pdf")
        self.assertLessEqual(len(regions), 1)


class TestSpanFilterIsLoadBearing(unittest.TestCase):
    """A single border rule spanning the sheet blocks every gutter. Measured:
    LOCATION_PLAN__BLOCK_PLAN...-2682241 finds 0 regions without the filter."""

    PDF = os.path.join(REPO, "plans",
                       "LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241.pdf")

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_sheet_has_page_spanning_primitives(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        spanning = [
            p for p in page_data.paths
            if is_page_spanning(p, page_data.width_px, page_data.height_px)
        ]
        self.assertGreater(len(spanning), 0)

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_sheet_splits_into_many_regions_with_the_filter(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        regions = segment_page(page_data)
        self.assertGreaterEqual(len(regions), 8)

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_ink_map_without_the_span_filter_leaves_no_gutter(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        ink = build_ink_map(page_data)
        spanning_rows = sum(
            1 for r in range(ink.rows) if sum(ink.bins[r]) > 0.9 * ink.cols
        )
        self.assertEqual(spanning_rows, 0,
                         "span filter should have removed full-width border rules")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_layout_golden -v`
Expected: PASS, 7 tests. If `test_floor_plans_splits_into_two_regions` reports a different count, stop and diagnose — do not edit the expected number without understanding why.

- [ ] **Step 3: Run the whole suite to check for regressions**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no failures

- [ ] **Step 4: Commit**

```bash
git add tests/test_layout_golden.py
git commit -m "test(layout): golden segmentation results on the reference PDFs"
```

---

### Task 7: Delete the per-candidate validation path

**Files:**
- Modify: `gemini/client.py`, `pipeline.py:117-231` (`merge_gemini_and_heuristics`), `pipeline.py:410-443` (the Gemini stage in `run_extract`), `pipeline.py:234-281` (`collect_warnings`)
- Test: `tests/test_merge_offline.py`

**Interfaces:**
- Consumes: `models.Candidate`, `models.Entity`
- Produces: `pipeline.finalize_candidates(candidates: list[Candidate]) -> tuple[list[Entity], list[dict]]` — replaces `merge_gemini_and_heuristics`. `gemini/client.py` keeps only `init_client()`.

Doing the deletion **before** wiring the new stage keeps the tree working at every commit: after this task the pipeline is heuristics-only with `OFFLINE_MIN_CONFIDENCE` applied unconditionally, which is exactly today's `--no-gemini` behaviour and what all existing tuning was measured against.

- [ ] **Step 1: Write the failing test**

Create `tests/test_merge_offline.py`:

```python
"""finalize_candidates applies the offline confidence floors unconditionally."""
import unittest

from models import Candidate
from pipeline import OFFLINE_MIN_CONFIDENCE, finalize_candidates


def cand(cid, etype, conf, **evidence):
    return Candidate(candidate_id=cid, entity_type=etype,
                     bbox=(10.0, 10.0, 50.0, 50.0), confidence=conf,
                     evidence=dict(evidence))


class TestFinalizeCandidates(unittest.TestCase):
    def test_candidate_above_threshold_becomes_an_entity(self):
        entities, rejected = finalize_candidates([cand("door_0001", "door", 0.80)])
        self.assertEqual([e.entity_id for e in entities], ["door_0001"])
        self.assertEqual(rejected, [])

    def test_candidate_below_threshold_is_rejected(self):
        entities, rejected = finalize_candidates([cand("door_0001", "door", 0.40)])
        self.assertEqual(entities, [])
        self.assertEqual(rejected[0]["candidate_id"], "door_0001")
        self.assertEqual(rejected[0]["source"], "offline_filter")

    def test_thresholds_are_per_type(self):
        # 0.52 clears window (0.50) but not door (0.55)
        entities, _ = finalize_candidates(
            [cand("door_0001", "door", 0.52), cand("window_0001", "window", 0.52)])
        self.assertEqual([e.entity_id for e in entities], ["window_0001"])

    def test_all_entities_are_sourced_heuristic(self):
        entities, _ = finalize_candidates([cand("door_0001", "door", 0.80)])
        self.assertEqual(entities[0].source, "heuristic")

    def test_rooms_bypass_the_thresholds(self):
        room = cand("room_0001", "room", 0.10, polygon=[[0, 0], [10, 0], [10, 10]])
        entities, rejected = finalize_candidates([room])
        self.assertEqual([e.entity_id for e in entities], ["room_0001"])
        self.assertEqual(rejected, [])

    def test_room_polygon_reaches_entity_attributes(self):
        room = cand("room_0001", "room", 0.85, polygon=[[0, 0], [10, 0], [10, 10]],
                    area_px2=50.0)
        entities, _ = finalize_candidates([room])
        self.assertEqual(entities[0].attributes["polygon"], [[0, 0], [10, 0], [10, 10]])
        self.assertEqual(entities[0].attributes["area_px2"], 50.0)

    def test_door_subtype_evidence_reaches_entity_attributes(self):
        d = cand("door_0001", "door", 0.80, assembly_type="sliding", swing_layout="garden")
        entities, _ = finalize_candidates([d])
        self.assertEqual(entities[0].attributes["assembly_type"], "sliding")
        self.assertEqual(entities[0].attributes["swing_layout"], "garden")

    def test_label_is_taken_from_evidence(self):
        d = cand("door_0001", "door", 0.80, nearby_label="D01")
        entities, _ = finalize_candidates([d])
        self.assertEqual(entities[0].label, "D01")

    def test_offline_thresholds_are_unchanged(self):
        self.assertEqual(OFFLINE_MIN_CONFIDENCE,
                         {"door": 0.55, "window": 0.50, "label": 0.65, "schedule": 0.50})


class TestValidationPathIsGone(unittest.TestCase):
    def test_gemini_client_no_longer_exposes_the_validation_helpers(self):
        from gemini import client
        for name in ("SYSTEM_PROMPT", "REQUIRED_KEYS", "build_user_message",
                     "_validate_response", "call_gemini", "_candidate_to_dict"):
            self.assertFalse(hasattr(client, name), f"{name} should be deleted")

    def test_pipeline_no_longer_exposes_the_merge_function(self):
        import pipeline
        self.assertFalse(hasattr(pipeline, "merge_gemini_and_heuristics"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_merge_offline -v`
Expected: FAIL with `ImportError: cannot import name 'finalize_candidates' from 'pipeline'`

- [ ] **Step 3: Strip `gemini/client.py` down to `init_client`**

Replace the entire contents of `gemini/client.py` with:

```python
"""Vertex AI client construction.

Per-candidate validation was removed on 2026-07-28: asking a vision model to
adjudicate hundreds of small symbols is spatial grounding, which it does poorly.
Gemini's role is now region classification — see gemini/classifier.py.
"""
from __future__ import annotations

import os

from google import genai


def init_client() -> genai.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, timeout=5,
            )
            project = result.stdout.strip() or None
        except Exception:
            pass
    if not project:
        raise EnvironmentError(
            "No GCP project found. Set GOOGLE_CLOUD_PROJECT or run:\n"
            "  gcloud config set project YOUR_PROJECT_ID\n"
            "Then authenticate with:\n"
            "  gcloud auth application-default login"
        )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)
```

- [ ] **Step 4: Replace `merge_gemini_and_heuristics` with `finalize_candidates`**

In `pipeline.py`, replace the whole `merge_gemini_and_heuristics` function (lines 117-231) with:

```python
def finalize_candidates(candidates: list[Candidate]) -> tuple[list[Entity], list[dict]]:
    """Promote candidates to entities, applying the offline confidence floors.

    Gemini no longer votes on individual candidates, so these floors always
    apply. Rooms bypass them: they are heuristic-only by design and carry their
    polygon into Entity.attributes.
    """
    rooms = [c for c in candidates if c.entity_type == "room"]
    others = [c for c in candidates if c.entity_type != "room"]

    entities: list[Entity] = []
    rejected_list: list[dict] = []
    for c in others:
        threshold = OFFLINE_MIN_CONFIDENCE.get(c.entity_type, 0.50)
        if c.confidence < threshold:
            rejected_list.append({
                "candidate_id": c.candidate_id,
                "entity_type": c.entity_type,
                "bbox": list(c.bbox),
                "reason": f"offline confidence {c.confidence:.3f} < threshold {threshold}",
                "source": "offline_filter",
            })
            continue
        entities.append(Entity(
            entity_id=c.candidate_id,
            entity_type=c.entity_type,
            bbox=c.bbox,
            confidence=c.confidence,
            source="heuristic",
            label=c.evidence.get("nearby_label") or c.evidence.get("text"),
            attributes={"heuristic_confidence": c.confidence, **_door_attribute_overlay(c)},
        ))

    entities.extend(_room_entity(c) for c in rooms)
    return entities, rejected_list
```

- [ ] **Step 5: Remove the Gemini stage from `run_extract`**

In `pipeline.py`, delete the whole block from `# 5. Gemini — rooms are heuristic-only...` through `write_json(str(Path(page_dir) / "gemini_result.json"), gemini_json)` (lines 410-439), and replace the merge call on line 443 with:

```python
            # 5. Finalize + overlay
            step("overlay")
            entities, rejected = finalize_candidates(candidates)
            total_entities += len(entities)
```

Then in the same function:
- Change `steps = ["extract", "render", "plumber", "heuristics", "gemini", "overlay", "save"]` to `steps = ["extract", "render", "plumber", "heuristics", "overlay", "save"]`.
- Delete the `gemini_client` initialisation block (lines 322-330) and the `total_gemini_calls` / `total_gemini_skipped` counters, plus their entries in the `summary.json` `"totals"` dict.
- Update the `collect_warnings(...)` call to drop the `gemini_result`, `gemini_skipped` and `gemini_warnings` arguments (see next step).
- Update the `_page_summary_dict(...)` call to drop `gemini_skipped`.
- Remove `from gemini import client as gc` from the imports.

Keep the `skip_gemini` parameter on `run_extract` — Task 10 gives it its new meaning.

- [ ] **Step 6: Simplify `collect_warnings` and `_page_summary_dict`**

In `pipeline.py`, change the `collect_warnings` signature and body:

```python
def collect_warnings(
    page_data: PageData,
    candidates: list[Candidate],
    comparison: dict,
    region_warnings: list[dict],
) -> list[dict]:
    warnings = []
    pn = page_data.page_number

    def warn(code, severity, msg, **extra):
        w = {"page_number": pn, "warning_code": code, "severity": severity, "message": msg}
        w.update(extra)
        warnings.append(w)

    if len(page_data.paths) > 1000:
        warn("HIGH_PATH_COUNT", "info", f"Page {pn} has {len(page_data.paths)} paths — extraction may be slow")

    if len(page_data.paths) == 0 and len(page_data.text_spans) == 0 and len(page_data.images) == 0:
        warn("EMPTY_PAGE", "warning", f"Page {pn} has zero paths, text spans, and images")
    elif len(page_data.paths) == 0 and page_data.page_type != "raster-heavy":
        warn("ZERO_PATHS", "warning", f"Page {pn} has no vector paths but is not classified raster-heavy")

    if not page_data.ocg_names:
        warn("MISSING_OCG_LAYER", "info", f"Page {pn}: no OCG layers found in document")

    if len(candidates) == 0:
        warn("NO_CANDIDATES", "warning", f"Page {pn} produced zero heuristic candidates")
    elif all(c.confidence < 0.40 for c in candidates):
        warn("LOW_HEURISTIC_CONFIDENCE", "info", f"Page {pn}: all candidates have confidence < 0.40")

    for any_img in page_data.images:
        if any_img.pixel_area > 0.80:
            warn("LARGE_IMAGE_COVERAGE", "info",
                 f"Page {pn}: image xref={any_img.xref} covers {any_img.pixel_area:.0%} of page (likely scanned)")

    warnings.extend(comparison.get("comparison_warnings", []))
    warnings.extend(region_warnings)

    return warnings
```

And drop `gemini_skipped` from `_page_summary_dict`, removing the `"gemini_skipped": gemini_skipped,` line from its returned dict.

Update the call site to `collect_warnings(page_data, candidates, comparison, [])` for now — Task 10 passes real region warnings.

- [ ] **Step 7: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_merge_offline -v`
Expected: PASS, 11 tests

- [ ] **Step 8: Verify the pipeline still runs end to end**

Run: `source .venv/bin/activate && python app.py extract floor-plans.pdf --no-gemini --out /tmp/regionplan-t7`
Expected: completes without error; `/tmp/regionplan-t7/*/pages/page_01/final_entities.json` exists and contains 13 room entities.

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no failures

- [ ] **Step 9: Commit**

```bash
git add gemini/client.py pipeline.py tests/test_merge_offline.py
git commit -m "refactor: delete per-candidate Gemini validation

The validation call asked a vision model to adjudicate hundreds of small
symbols, which is spatial grounding and does not work. merge_gemini_and_heuristics
collapses into finalize_candidates, applying OFFLINE_MIN_CONFIDENCE
unconditionally - today's --no-gemini behaviour, and what all existing
detection tuning was measured against."
```

---

### Task 8: Gemini region classifier

**Files:**
- Create: `gemini/classifier.py`
- Test: `tests/test_region_classifier.py`

**Interfaces:**
- Consumes: `models.Region`, `models.PageData`, `layout` (nothing directly)
- Produces:
  - `REGION_TYPES: list[str]`
  - `render_region_crop(page, bbox: BBox, out_path: str) -> tuple[int, int]`
  - `region_title_text(page_data: PageData, bbox: BBox, limit: int = 6) -> list[str]`
  - `build_request_parts(page, page_data: PageData, regions: list[Region], crop_dir: str) -> list`
  - `apply_classification(raw_text: str, regions: list[Region]) -> tuple[list[Region], list[dict]]`
  - `classify_regions(client, page, page_data: PageData, regions: list[Region], crop_dir: str, model: str = MODEL) -> tuple[list[Region], list[dict]]`

`apply_classification` is split out from the API call so the parsing, the taxonomy validation and the warning codes are all testable without credentials.

- [ ] **Step 1: Write the failing test**

Create `tests/test_region_classifier.py`:

```python
"""Region classification parsing tests (gemini/classifier.py).

No API calls: apply_classification is tested against recorded response text.
"""
import json
import unittest

from models import PageData, Region, TextSpan
from gemini.classifier import (
    REGION_TYPES, apply_classification, region_title_text,
)


def region(i):
    return Region(region_id=f"region_{i:04d}", bbox=(0.0, 0.0, 100.0, 100.0))


def response(entries):
    return json.dumps({"regions": entries})


class TestApplyClassification(unittest.TestCase):
    def test_types_titles_and_confidence_are_applied(self):
        regions = [region(0), region(1)]
        raw = response([
            {"id": 0, "type": "floor_plan", "title": "GROUND FLOOR PLAN",
             "confidence": 0.95, "contains_multiple": False, "notes": ""},
            {"id": 1, "type": "elevation", "title": "REAR ELEVATION",
             "confidence": 1.0, "contains_multiple": True, "notes": ""},
        ])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual([r.region_type for r in out], ["floor_plan", "elevation"])
        self.assertEqual(out[0].title, "GROUND FLOOR PLAN")
        self.assertEqual(out[0].confidence, 0.95)
        self.assertTrue(out[1].contains_multiple)
        self.assertEqual(warnings, [])

    def test_markdown_fences_are_stripped(self):
        regions = [region(0)]
        raw = "```json\n" + response(
            [{"id": 0, "type": "floor_plan", "title": None, "confidence": 1.0,
              "contains_multiple": False, "notes": ""}]) + "\n```"
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[0].region_type, "floor_plan")
        self.assertEqual(warnings, [])

    def test_missing_region_id_warns_and_stays_unclassified(self):
        regions = [region(0), region(1)]
        raw = response([{"id": 0, "type": "floor_plan", "title": None,
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[1].region_type, "unclassified")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_INCOMPLETE"])

    def test_invalid_json_warns_and_leaves_everything_unclassified(self):
        regions = [region(0)]
        out, warnings = apply_classification("not json at all", regions)
        self.assertEqual(out[0].region_type, "unclassified")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_PARSE_FAILURE"])
        self.assertEqual(warnings[0]["severity"], "error")

    def test_unknown_type_is_coerced_to_other_with_a_warning(self):
        regions = [region(0)]
        raw = response([{"id": 0, "type": "blueprint", "title": None,
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[0].region_type, "other")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_INCOMPLETE"])

    def test_unknown_region_id_in_response_is_ignored(self):
        regions = [region(0)]
        raw = response([
            {"id": 0, "type": "floor_plan", "title": None, "confidence": 1.0,
             "contains_multiple": False, "notes": ""},
            {"id": 99, "type": "elevation", "title": None, "confidence": 1.0,
             "contains_multiple": False, "notes": ""},
        ])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].region_type, "floor_plan")

    def test_original_regions_are_not_mutated(self):
        regions = [region(0)]
        raw = response([{"id": 0, "type": "floor_plan", "title": "X",
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        apply_classification(raw, regions)
        self.assertEqual(regions[0].region_type, "unclassified")

    def test_taxonomy_contains_the_types_the_pipeline_consumes(self):
        self.assertIn("floor_plan", REGION_TYPES)
        self.assertIn("schedule_table", REGION_TYPES)
        self.assertIn("other", REGION_TYPES)


class TestRegionTitleText(unittest.TestCase):
    def test_returns_largest_text_inside_the_box_first(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[
                TextSpan(text="KITCHEN", bbox=(60.0, 60.0, 120.0, 70.0),
                         font="H", size=6.0, color=0, block_no=0, line_no=0),
                TextSpan(text="GROUND FLOOR PLAN", bbox=(60.0, 150.0, 200.0, 170.0),
                         font="H", size=12.0, color=0, block_no=0, line_no=1),
            ],
        )
        got = region_title_text(page, (50.0, 50.0, 300.0, 300.0))
        self.assertEqual(got[0], "GROUND FLOOR PLAN")

    def test_text_outside_the_box_is_excluded(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[TextSpan(text="TITLE BLOCK", bbox=(400.0, 400.0, 480.0, 415.0),
                                 font="H", size=12.0, color=0, block_no=0, line_no=0)],
        )
        self.assertEqual(region_title_text(page, (50.0, 50.0, 300.0, 300.0)), [])

    def test_duplicate_strings_appear_once(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[
                TextSpan(text="BEDROOM", bbox=(60.0, 60.0, 120.0, 70.0), font="H",
                         size=6.0, color=0, block_no=0, line_no=0),
                TextSpan(text="BEDROOM", bbox=(60.0, 90.0, 120.0, 100.0), font="H",
                         size=6.0, color=0, block_no=0, line_no=1),
            ],
        )
        self.assertEqual(region_title_text(page, (50.0, 50.0, 300.0, 300.0)), ["BEDROOM"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_classifier -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gemini.classifier'`

- [ ] **Step 3: Write the classifier**

Create `gemini/classifier.py`:

```python
"""Ask Gemini what each segmented region is.

One call per page. Each region goes as its own crop rather than one full-page
image: Google's docs state images are "cropped and scaled into 768x768 pixel
tiles", and these sheets are A1 (3508x4967px at 150 DPI), so a whole-sheet image
loses the detail that distinguishes a floor plan from an elevation. A 1536px
crop is 2x2 tiles, roughly 1,000 tokens. The per-request limit is 3,600 images,
so region count is never a constraint.

Measured 2026-07-28 over 20 pages: 0 malformed responses, 0 missing region ids,
44,437 input tokens total; 58 regions scored by inspection with zero floor
plans missed and zero false positives.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
from typing import Optional

import fitz
from google.genai import types

from models import BBox, PageData, Region

MODEL = "gemini-2.5-flash"
SCALE = 150 / 72

# Each crop is scaled so its long edge hits this, regardless of its size on the
# sheet: a cramped location plan gets enlarged, a huge floor plan shrunk.
CROP_TARGET_LONG_EDGE_PX = 1536
CROP_MAX_ZOOM = 10.0

REGION_TYPES = [
    "floor_plan", "elevation", "section", "location_plan", "block_plan",
    "site_plan", "roof_plan", "schedule_table", "legend", "title_block",
    "detail", "other",
]

SYSTEM_PROMPT = f"""\
You are an expert reader of architectural drawing sheets (UK planning and
building-regulation drawings).

A single sheet has been mechanically split into separate drawing regions by
whitespace analysis. You will receive one cropped image per region, in order,
each preceded by its region number and any text found inside it.

For EACH region, identify what kind of drawing it is. Choose exactly one type:
{", ".join(REGION_TYPES)}

Guidance:
- floor_plan: a horizontal cut through a building showing rooms, wall thicknesses,
  door swings and window openings. This is the type that matters most - be precise.
- elevation: a vertical external face of the building - roof outline, windows drawn
  flat, ground line, often hatched brickwork. No door swing arcs, no room labels.
- section: a vertical cut, showing floor/roof build-ups and internal heights.
- location_plan / block_plan / site_plan: maps or site layouts, often with a red
  outline, street names, plot boundaries. Buildings appear as simple filled shapes
  with no internal room detail.
- roof_plan: a plan view showing roof pitches, ridges and hips, but no rooms.
- schedule_table: a table of doors, windows, or areas.
- title_block / legend / detail / other: sheet furniture, keys, construction
  details, or anything that fits nothing above.

A region may contain more than one drawing if the split was imperfect. If so, set
"contains_multiple": true and give the type of the dominant drawing.

Respond ONLY with valid JSON, no markdown fences:
{{"regions": [{{"id": <int>, "type": "<one of the list>", "title": "<drawing title or null>",
  "confidence": <float 0-1>, "contains_multiple": <bool>, "notes": "<short>"}}]}}
"""


def render_region_crop(page: fitz.Page, bbox: BBox, out_path: str) -> tuple[int, int]:
    """Render one region as its own PNG, scaled so its long edge is about
    CROP_TARGET_LONG_EDGE_PX. Returns the rendered (width, height)."""
    rect = fitz.Rect(bbox[0] / SCALE, bbox[1] / SCALE, bbox[2] / SCALE, bbox[3] / SCALE)
    long_edge_pt = max(rect.width, rect.height)
    zoom = min(CROP_MAX_ZOOM, CROP_TARGET_LONG_EDGE_PX / max(1.0, long_edge_pt))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
    pix.save(out_path)
    return pix.width, pix.height


def region_title_text(page_data: PageData, bbox: BBox, limit: int = 6) -> list[str]:
    """Distinct text inside a region, largest font first. Many CAD exports
    outline their text to curves, in which case this is empty and the model
    works from the image alone."""
    inside = [
        t for t in page_data.text_spans
        if t.bbox[0] >= bbox[0] - 2 and t.bbox[2] <= bbox[2] + 2
        and t.bbox[1] >= bbox[1] - 2 and t.bbox[3] <= bbox[3] + 2
        and t.text.strip()
    ]
    inside.sort(key=lambda t: -t.size)
    seen: set[str] = set()
    out: list[str] = []
    for t in inside:
        s = t.text.strip()
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
        if len(out) >= limit:
            break
    return out


def build_request_parts(
    page: fitz.Page, page_data: PageData, regions: list[Region], crop_dir: str
) -> list:
    os.makedirs(crop_dir, exist_ok=True)
    parts = [types.Part.from_text(
        text=f"This sheet was split into {len(regions)} regions. Classify every one.")]
    for i, region in enumerate(regions):
        crop_path = os.path.join(crop_dir, f"{region.region_id}.png")
        render_region_crop(page, region.bbox, crop_path)
        text = region_title_text(page_data, region.bbox)
        w = region.bbox[2] - region.bbox[0]
        h = region.bbox[3] - region.bbox[1]
        parts.append(types.Part.from_text(
            text=f"REGION {i} — {w:.0f}x{h:.0f}px on the sheet. "
                 f"Text found inside: {text if text else 'none (text is outlined to curves)'}"))
        with open(crop_path, "rb") as f:
            parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/png"))
    return parts


def apply_classification(
    raw_text: str, regions: list[Region]
) -> tuple[list[Region], list[dict]]:
    """Apply a classification response to a region list.

    Returns new Region objects — the inputs are not mutated. A region the model
    did not address, or gave a type outside the taxonomy, stays "unclassified"
    or becomes "other" respectively, and is reported.
    """
    warnings: list[dict] = []
    out = [dataclasses.replace(r) for r in regions]

    text = re.sub(r"^```(?:json)?", "", raw_text.strip())
    text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        warnings.append({
            "warning_code": "REGION_CLASSIFY_PARSE_FAILURE",
            "severity": "error",
            "message": f"Region classification response was not valid JSON: {e}",
            "raw_response_snippet": raw_text[:300],
        })
        return out, warnings

    by_id = {}
    for item in parsed.get("regions", []):
        try:
            by_id[int(item.get("id"))] = item
        except (TypeError, ValueError):
            continue

    unaddressed: list[str] = []
    coerced: list[str] = []
    for i, region in enumerate(out):
        item = by_id.get(i)
        if item is None:
            unaddressed.append(region.region_id)
            continue
        rtype = item.get("type")
        if rtype not in REGION_TYPES:
            coerced.append(f"{region.region_id}={rtype!r}")
            rtype = "other"
        region.region_type = rtype
        title = item.get("title")
        region.title = title.strip() if isinstance(title, str) and title.strip() else None
        try:
            region.confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            region.confidence = 0.0
        region.contains_multiple = bool(item.get("contains_multiple", False))

    if unaddressed or coerced:
        details = []
        if unaddressed:
            details.append(f"unaddressed: {unaddressed}")
        if coerced:
            details.append(f"unknown types coerced to 'other': {coerced}")
        warnings.append({
            "warning_code": "REGION_CLASSIFY_INCOMPLETE",
            "severity": "warning",
            "message": "Region classification incomplete — " + "; ".join(details),
        })

    return out, warnings


def classify_regions(
    client,
    page: fitz.Page,
    page_data: PageData,
    regions: list[Region],
    crop_dir: str,
    model: str = MODEL,
) -> tuple[list[Region], list[dict]]:
    """One API call for the whole page. Returns classified regions + warnings."""
    if not regions:
        return [], []

    parts = build_request_parts(page, page_data, regions, crop_dir)
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    return apply_classification(response.text, regions)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_classifier -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add gemini/classifier.py tests/test_region_classifier.py
git commit -m "feat(gemini): region classifier — one call of per-region crops per page"
```

---

### Task 9: Region classification cache

**Files:**
- Create: `gemini/region_cache.py`
- Test: `tests/test_region_cache.py`

**Interfaces:**
- Consumes: `models.Region`, `models.PageData`
- Produces:
  - `page_content_hash(page_data: PageData) -> str`
  - `cache_file(pdf_path: str, page_number: int, content_hash: str) -> Path`
  - `load_regions(pdf_path: str, page_number: int, content_hash: str) -> Optional[list[Region]]`
  - `save_regions(pdf_path: str, page_number: int, content_hash: str, regions: list[Region]) -> None`
  - `regions_to_dicts(regions: list[Region]) -> list[dict]` / `regions_from_dicts(data: list[dict]) -> list[Region]`

This cache exists because `--no-gemini` is the normal way this tool is run. Without it, that flag would silently disable region filtering and offline runs would disagree with online ones.

- [ ] **Step 1: Write the failing test**

Create `tests/test_region_cache.py`:

```python
"""Region cache tests (gemini/region_cache.py)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import PageData, PathPrimitive, Region
from gemini.region_cache import (
    cache_file, load_regions, page_content_hash, regions_from_dicts,
    regions_to_dicts, save_regions,
)


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def page(paths):
    return PageData(page_number=1, width_px=100.0, height_px=100.0, paths=list(paths))


def regions():
    return [
        Region(region_id="region_0000", bbox=(0.0, 0.0, 50.0, 50.0),
               region_type="floor_plan", title="GROUND FLOOR", confidence=0.95,
               contains_multiple=False, path_count=12, source="whitespace"),
        Region(region_id="region_0001", bbox=(50.0, 0.0, 100.0, 50.0),
               region_type="elevation", title=None, confidence=1.0,
               contains_multiple=True, path_count=8, source="whitespace+clip"),
    ]


class TestContentHash(unittest.TestCase):
    def test_same_content_gives_the_same_hash(self):
        a, b = page([path(0, 1, 2, 3, 4)]), page([path(0, 1, 2, 3, 4)])
        self.assertEqual(page_content_hash(a), page_content_hash(b))

    def test_different_geometry_gives_a_different_hash(self):
        a, b = page([path(0, 1, 2, 3, 4)]), page([path(0, 1, 2, 3, 9)])
        self.assertNotEqual(page_content_hash(a), page_content_hash(b))

    def test_different_path_count_gives_a_different_hash(self):
        a = page([path(0, 1, 2, 3, 4)])
        b = page([path(0, 1, 2, 3, 4), path(1, 5, 6, 7, 8)])
        self.assertNotEqual(page_content_hash(a), page_content_hash(b))


class TestRoundTrip(unittest.TestCase):
    def test_dict_round_trip_preserves_every_field(self):
        restored = regions_from_dicts(regions_to_dicts(regions()))
        self.assertEqual(restored, regions())

    def test_bbox_survives_as_a_tuple(self):
        restored = regions_from_dicts(regions_to_dicts(regions()))
        self.assertIsInstance(restored[0].bbox, tuple)


class TestCacheFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "drawing.pdf")
        Path(self.pdf).write_bytes(b"%PDF-1.4")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_then_load_returns_the_regions(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertEqual(load_regions(self.pdf, 1, "abc123"), regions())

    def test_load_with_a_different_hash_misses(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertIsNone(load_regions(self.pdf, 1, "different"))

    def test_load_with_a_different_page_misses(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertIsNone(load_regions(self.pdf, 2, "abc123"))

    def test_load_with_no_cache_returns_none(self):
        self.assertIsNone(load_regions(self.pdf, 1, "abc123"))

    def test_cache_lives_beside_the_pdf(self):
        target = cache_file(self.pdf, 1, "abc123")
        self.assertEqual(target.parent.parent, Path(self.tmp))
        self.assertEqual(target.parent.name, ".regions_cache")

    def test_corrupt_cache_file_returns_none_instead_of_raising(self):
        target = cache_file(self.pdf, 1, "abc123")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{ not json", encoding="utf-8")
        self.assertIsNone(load_regions(self.pdf, 1, "abc123"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_cache -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gemini.region_cache'`

- [ ] **Step 3: Write the cache**

Create `gemini/region_cache.py`:

```python
"""On-disk cache of region classifications, keyed by page content.

--no-gemini is the normal way this tool is run. Without a cache that flag would
silently disable region filtering, so offline runs would disagree with online
ones. With it, a page costs one real API call ever.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from models import PageData, Region

CACHE_DIR_NAME = ".regions_cache"


def page_content_hash(page_data: PageData) -> str:
    """Stable digest of a page's vector geometry and text. Changes if the PDF
    is edited, so a stale classification is never reused."""
    h = hashlib.sha256()
    h.update(f"{page_data.width_px:.2f}x{page_data.height_px:.2f}".encode())
    h.update(f"|paths={len(page_data.paths)}|spans={len(page_data.text_spans)}|".encode())
    for p in page_data.paths:
        h.update(f"{p.item_type}:{p.bbox[0]:.2f},{p.bbox[1]:.2f},"
                 f"{p.bbox[2]:.2f},{p.bbox[3]:.2f};".encode())
    for t in page_data.text_spans:
        h.update(f"{t.text}@{t.bbox[0]:.1f},{t.bbox[1]:.1f};".encode())
    return h.hexdigest()[:16]


def cache_file(pdf_path: str, page_number: int, content_hash: str) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}_{content_hash}.json"


def regions_to_dicts(regions: list[Region]) -> list[dict]:
    return [
        {
            "region_id": r.region_id,
            "bbox": list(r.bbox),
            "region_type": r.region_type,
            "title": r.title,
            "confidence": r.confidence,
            "contains_multiple": r.contains_multiple,
            "path_count": r.path_count,
            "source": r.source,
        }
        for r in regions
    ]


def regions_from_dicts(data: list[dict]) -> list[Region]:
    return [
        Region(
            region_id=d["region_id"],
            bbox=tuple(d["bbox"]),
            region_type=d.get("region_type", "unclassified"),
            title=d.get("title"),
            confidence=float(d.get("confidence", 0.0)),
            contains_multiple=bool(d.get("contains_multiple", False)),
            path_count=int(d.get("path_count", 0)),
            source=d.get("source", "whitespace"),
        )
        for d in data
    ]


def load_regions(pdf_path: str, page_number: int, content_hash: str) -> Optional[list[Region]]:
    target = cache_file(pdf_path, page_number, content_hash)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return regions_from_dicts(payload["regions"])
    except Exception:
        return None


def save_regions(
    pdf_path: str, page_number: int, content_hash: str, regions: list[Region]
) -> None:
    target = cache_file(pdf_path, page_number, content_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({
            "page_number": page_number,
            "content_hash": content_hash,
            "regions": regions_to_dicts(regions),
        }, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_cache -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Ignore the cache directory in git**

Append to `.gitignore`:

```
.regions_cache/
```

- [ ] **Step 6: Commit**

```bash
git add gemini/region_cache.py tests/test_region_cache.py .gitignore
git commit -m "feat(gemini): cache region classifications by page content hash"
```

---

### Task 10: Wire segmentation, classification and filtering into the pipeline

**Files:**
- Modify: `pipeline.py`, `detection/orchestrator.py`
- Test: `tests/test_region_pipeline.py` (create)

**Interfaces:**
- Consumes: `layout.segment_page`, `layout.page_fallback_region`, `layout.qualifying_clip_rects`, `layout.filter_page_data`, `layout.region_text_spans`, `gemini.classifier.classify_regions`, `gemini.region_cache.*`
- Produces: `pipeline.resolve_page_regions(...) -> PageRegionResult`, a dataclass with fields `regions: list[Region]`, `detection_page_data: PageData`, `schedule_spans: Optional[list[TextSpan]]`, `warnings: list[dict]`, `skip_detection: bool`. Also `detection.orchestrator.run_heuristics(..., schedule_text_spans: list[TextSpan] | None = None)`.

The four rules, restated so they can be implemented directly:

1. Page split into ≥2 regions with no `floor_plan` → `skip_detection=True`, warn `NO_FLOOR_PLAN_REGION`.
2. Page produced ≤1 region → one `page-fallback` region; classify it for the record, but **always** detect on the full page whatever the answer says.
3. Page has zero vector paths → no segmentation, no API call; warn `RASTER_PAGE_NO_VECTOR_INK`; detect on the full page (finding nothing, as today).
4. `--no-gemini` → load from cache; a cache miss means no filtering and warns `REGION_CACHE_MISS_OFFLINE`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_region_pipeline.py`:

```python
"""Region resolution rules (pipeline.resolve_page_regions).

A stub classifier stands in for the API so the four behaviour rules are tested
without credentials.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import PageData, PathPrimitive, Region
from pipeline import resolve_page_regions

PAGE_W, PAGE_H = 400.0, 400.0


def block(idx, x0, y0, x1, y1):
    return [
        PathPrimitive(
            path_index=idx + i, item_type="l", bbox=(x0, y, x1, y),
            color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
            dashes="", layer=None, points=[(x0, y), (x1, y)],
        )
        for i, y in enumerate(range(int(y0), int(y1), 4))
    ]


def two_blob_page():
    paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=paths)


def one_blob_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=block(0, 40, 40, 360, 360))


def raster_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    page_type="raster-heavy")


def stub_classifier(types_by_index):
    """Returns a callable matching classify_regions' signature."""
    def _classify(client, page, page_data, regions, crop_dir, **kwargs):
        out = []
        for i, r in enumerate(regions):
            out.append(Region(
                region_id=r.region_id, bbox=r.bbox,
                region_type=types_by_index.get(i, "other"),
                title=None, confidence=1.0, contains_multiple=False,
                path_count=r.path_count, source=r.source,
            ))
        return out, []
    return _classify


class RegionRuleTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "sheet.pdf")
        Path(self.pdf).write_bytes(b"%PDF-1.4")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def resolve(self, page_data, classifier, **kwargs):
        return resolve_page_regions(
            pdf_path=self.pdf, page=None, page_data=page_data,
            gemini_client=object(), skip_gemini=False, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=classifier, clip_fn=lambda page, pd: [],
            **kwargs,
        )


class TestRuleOneNoFloorPlan(RegionRuleTestCase):
    def test_split_page_with_no_floor_plan_skips_detection(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "elevation", 1: "elevation"}))
        self.assertTrue(result.skip_detection)
        self.assertIn("NO_FLOOR_PLAN_REGION",
                      [w["warning_code"] for w in result.warnings])

    def test_split_page_with_a_floor_plan_filters_to_it(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertFalse(result.skip_detection)
        page_data = two_blob_page()
        self.assertLess(len(result.detection_page_data.paths), len(page_data.paths))
        self.assertGreater(len(result.detection_page_data.paths), 0)

    def test_filtered_page_data_keeps_full_page_dimensions(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertEqual(result.detection_page_data.width_px, PAGE_W)
        self.assertEqual(result.detection_page_data.height_px, PAGE_H)

    def test_two_floor_plans_are_detected_as_one_union(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "floor_plan"}))
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))


class TestRuleTwoWholePageFallback(RegionRuleTestCase):
    def test_unsplit_page_detects_even_when_classified_as_elevation(self):
        result = self.resolve(one_blob_page(), stub_classifier({0: "elevation"}))
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(one_blob_page().paths))

    def test_unsplit_page_records_a_page_fallback_region(self):
        result = self.resolve(one_blob_page(), stub_classifier({0: "floor_plan"}))
        self.assertEqual(len(result.regions), 1)
        self.assertEqual(result.regions[0].source, "page-fallback")


class TestRuleThreeRasterPage(RegionRuleTestCase):
    def test_raster_page_is_not_classified_and_still_detects(self):
        calls = []

        def spy(*args, **kwargs):
            calls.append(1)
            return [], []

        result = self.resolve(raster_page(), spy)
        self.assertEqual(calls, [])
        self.assertFalse(result.skip_detection)
        self.assertEqual(result.regions, [])
        self.assertIn("RASTER_PAGE_NO_VECTOR_INK",
                      [w["warning_code"] for w in result.warnings])


class TestRuleFourOfflineCache(RegionRuleTestCase):
    def test_offline_without_a_cache_does_no_filtering_and_warns(self):
        result = resolve_page_regions(
            pdf_path=self.pdf, page=None, page_data=two_blob_page(),
            gemini_client=None, skip_gemini=True, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=stub_classifier({}), clip_fn=lambda page, pd: [],
        )
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))
        self.assertIn("REGION_CACHE_MISS_OFFLINE",
                      [w["warning_code"] for w in result.warnings])

    def test_offline_reuses_a_cached_classification(self):
        page_data = two_blob_page()
        first = self.resolve(page_data, stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertFalse(first.skip_detection)

        def exploding(*args, **kwargs):
            raise AssertionError("classifier must not be called when cached")

        second = resolve_page_regions(
            pdf_path=self.pdf, page=None, page_data=page_data,
            gemini_client=None, skip_gemini=True, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=exploding, clip_fn=lambda page, pd: [],
        )
        self.assertEqual([r.region_type for r in second.regions],
                         ["floor_plan", "elevation"])
        self.assertEqual(len(second.detection_page_data.paths),
                         len(first.detection_page_data.paths))

    def test_refresh_regions_bypasses_the_cache(self):
        page_data = two_blob_page()
        self.resolve(page_data, stub_classifier({0: "floor_plan", 1: "elevation"}))
        result = self.resolve(page_data,
                              stub_classifier({0: "elevation", 1: "elevation"}),
                              refresh_regions=True)
        self.assertTrue(result.skip_detection)


class TestScheduleScoping(RegionRuleTestCase):
    def test_schedule_regions_supply_their_own_text_spans(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "schedule_table"}))
        self.assertIsNotNone(result.schedule_spans)

    def test_no_schedule_region_means_no_scoping(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertIsNone(result.schedule_spans)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_pipeline -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_page_regions' from 'pipeline'`

- [ ] **Step 3: Add `schedule_text_spans` to `run_heuristics`**

In `detection/orchestrator.py`, change the signature and the schedule call:

```python
def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
    disable_walls: bool = False,   # deprecated alias for disable_rooms
    disable_windows: bool = False,
    collector: DebugTraceCollector | None = None,
    disable_rooms: bool = False,
    schedule_text_spans: list[TextSpan] | None = None,
) -> list[Candidate]:
```

Add `TextSpan` to the `models` import line, and change the schedules line at the end of the function:

```python
    # Schedules live outside the floor plans, so when the page carries
    # schedule_table regions their text is passed in separately rather than
    # coming from the (floor-plan-filtered) page_data.
    schedules = detect_schedules(
        page_data.text_spans if schedule_text_spans is None else schedule_text_spans,
        plumber_tables,
    )
```

- [ ] **Step 4: Write `resolve_page_regions`**

Add to `pipeline.py` — imports first:

```python
from models import PageData, Candidate, Entity, Region, TextSpan
from layout import (
    filter_page_data, page_fallback_region, qualifying_clip_rects,
    region_text_spans, segment_page,
)
from gemini import client as gc
from gemini.classifier import classify_regions
from gemini.region_cache import load_regions, page_content_hash, save_regions
```

Then the resolver, placed above `run_extract`:

```python
@dataclass
class PageRegionResult:
    regions: list[Region]
    detection_page_data: PageData
    schedule_spans: Optional[list[TextSpan]]
    warnings: list[dict]
    skip_detection: bool


def resolve_page_regions(
    pdf_path: str,
    page,
    page_data: PageData,
    gemini_client,
    skip_gemini: bool,
    refresh_regions: bool,
    crop_dir: str,
    classify_fn=classify_regions,
    clip_fn=qualifying_clip_rects,
) -> PageRegionResult:
    """Segment the page, classify its regions, and decide what detection sees.

    classify_fn and clip_fn are injectable so the behaviour rules can be tested
    without credentials or a real fitz.Page.
    """
    pn = page_data.page_number
    warnings: list[dict] = []

    def warn(code, severity, msg):
        warnings.append({"page_number": pn, "warning_code": code,
                         "severity": severity, "message": msg})

    def unfiltered(regions):
        return PageRegionResult(regions, page_data, None, warnings, False)

    # Rule 3: no vector ink at all — a scanned page. Nothing to segment or
    # classify, and calling Gemini would be a wasted request.
    if not page_data.paths:
        warn("RASTER_PAGE_NO_VECTOR_INK", "info",
             f"Page {pn} has no vector paths — segmentation and classification skipped")
        return unfiltered([])

    clip_rects = clip_fn(page, page_data) if page is not None else []
    regions = segment_page(page_data, clip_rects)
    fallback = len(regions) <= 1
    if fallback:
        regions = [page_fallback_region(page_data)]

    content_hash = page_content_hash(page_data)
    cached = None if refresh_regions else load_regions(pdf_path, pn, content_hash)

    if cached is not None and len(cached) == len(regions):
        regions = cached
    elif skip_gemini or gemini_client is None:
        # Rule 4: offline with no usable cache — record the regions but filter
        # nothing, so an offline run never silently differs from an online one.
        warn("REGION_CACHE_MISS_OFFLINE", "warning",
             f"Page {pn}: no cached region classification and Gemini is disabled — "
             f"no region filtering applied")
        return unfiltered(regions)
    else:
        try:
            regions, classify_warnings = classify_fn(
                gemini_client, page, page_data, regions, crop_dir)
            for w in classify_warnings:
                w.setdefault("page_number", pn)
            warnings.extend(classify_warnings)
            save_regions(pdf_path, pn, content_hash, regions)
        except Exception as e:
            warn("REGION_CLASSIFY_PARSE_FAILURE", "error",
                 f"Region classification failed for page {pn}: {e}")
            return unfiltered(regions)

    # Rule 2: the page never split. Classify for the record, but always detect.
    if fallback:
        return unfiltered(regions)

    floor_plans = [r for r in regions if r.region_type == "floor_plan"]
    schedules = [r for r in regions if r.region_type == "schedule_table"]

    # Rule 1: a split page with no floor plan has nothing worth detecting.
    if not floor_plans:
        kinds = sorted({r.region_type for r in regions})
        warn("NO_FLOOR_PLAN_REGION", "warning",
             f"Page {pn}: {len(regions)} regions found, none classified floor_plan "
             f"(saw {kinds}) — detection skipped")
        return PageRegionResult(regions, page_data, None, warnings, True)

    detection_page_data = filter_page_data(page_data, floor_plans)
    schedule_spans = region_text_spans(page_data, schedules) if schedules else None
    return PageRegionResult(regions, detection_page_data, schedule_spans, warnings, False)
```

Add `from dataclasses import dataclass` to the imports at the top of `pipeline.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_pipeline -v`
Expected: PASS, 12 tests

- [ ] **Step 6: Call the resolver from `run_extract`**

In `run_extract`, restore the Gemini client init (it was removed in Task 7) just after the `path.exists()` check:

```python
    gemini_client = None
    if not skip_gemini:
        try:
            gemini_client = gc.init_client()
        except EnvironmentError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Tip: run 'gcloud auth application-default login' to authenticate[/dim]")
            raise
```

Add `refresh_regions: bool = False` to the `run_extract` signature.

Change the step list to `steps = ["extract", "render", "regions", "plumber", "heuristics", "overlay", "save"]`.

Insert a new stage between the render step and the plumber step:

```python
            # 2a-2c. Segment, classify, filter
            step("regions")
            region_result = resolve_page_regions(
                pdf_path=str(path),
                page=doc[idx],
                page_data=page_data,
                gemini_client=gemini_client,
                skip_gemini=skip_gemini,
                refresh_regions=refresh_regions,
                crop_dir=str(Path(page_dir) / "region_crops"),
            )
            write_json(
                str(Path(page_dir) / "regions.json"),
                {
                    "page_number": page_num,
                    "skip_detection": region_result.skip_detection,
                    "regions": [
                        {
                            "region_id": r.region_id,
                            "bbox": list(r.bbox),
                            "region_type": r.region_type,
                            "title": r.title,
                            "confidence": r.confidence,
                            "contains_multiple": r.contains_multiple,
                            "path_count": r.path_count,
                            "source": r.source,
                        }
                        for r in region_result.regions
                    ],
                },
            )
```

Change the heuristics step to use the filtered data and honour `skip_detection`:

```python
            # 4. Heuristics — one pass over the union of the floor-plan regions
            step("heuristics")
            collector = DebugTraceCollector(page_num) if debug else None
            if region_result.skip_detection:
                candidates = []
            else:
                candidates = run_heuristics(
                    region_result.detection_page_data, plumber_page.get("tables", []),
                    disable_rooms=disable_rooms, disable_windows=disable_windows,
                    collector=collector,
                    schedule_text_spans=region_result.schedule_spans,
                )
```

Change the `collect_warnings` call to pass the region warnings:

```python
            page_warnings = collect_warnings(
                page_data, candidates, comparison, region_result.warnings,
            )
```

Add region counts to the page summary. In `_page_summary_dict`, add a `regions` parameter and these entries to the returned dict:

```python
        "region_count": len(regions),
        "floor_plan_region_count": sum(1 for r in regions if r.region_type == "floor_plan"),
```

Update its call site to `_page_summary_dict(page_data, candidates, entities, page_warnings, region_result.regions)`.

- [ ] **Step 7: Verify end to end offline**

Run: `source .venv/bin/activate && python app.py extract floor-plans.pdf --no-gemini --out /tmp/regionplan-t10`
Expected: completes; `pages/page_01/regions.json` lists 2 regions; `warnings.json` contains `REGION_CACHE_MISS_OFFLINE`; `final_entities.json` still holds 13 rooms (no cache, so no filtering).

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no failures

- [ ] **Step 8: Commit**

```bash
git add pipeline.py detection/orchestrator.py tests/test_region_pipeline.py
git commit -m "feat(pipeline): segment, classify and filter to floor-plan regions

Detection now runs once over the union of floor_plan regions. Adds the four
behaviour rules: skip a split page with no floor plan, always detect on an
unsplit page, skip raster pages before calling Gemini, and reuse the cached
classification when offline."
```

---

### Task 11: Overlay outlines, CLI flag, and docs

**Files:**
- Modify: `extraction/renderer.py`, `pipeline.py` (the `draw_overlay` call), `app.py`, `CLAUDE.md`
- Test: `tests/test_region_overlay.py` (create)

**Interfaces:**
- Consumes: `models.Region`
- Produces: `draw_overlay(render_png_path: str, entities: list[Entity], rejected: list[dict], out_path: str, regions: list[Region] | None = None) -> None`

`regions` is keyword-optional so existing call sites and tests keep working.

- [ ] **Step 1: Write the failing test**

Create `tests/test_region_overlay.py`:

```python
"""Region outlines on the overlay (extraction/renderer.py)."""
import os
import shutil
import tempfile
import unittest

from PIL import Image

from models import Entity, Region
from extraction.renderer import REGION_OUTLINE_COLORS, draw_overlay


class TestDrawOverlayWithRegions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.render = os.path.join(self.tmp, "render.png")
        Image.new("RGB", (400, 300), (255, 255, 255)).save(self.render)
        self.out = os.path.join(self.tmp, "overlay.png")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overlay_is_written_without_regions(self):
        draw_overlay(self.render, [], [], self.out)
        self.assertTrue(os.path.exists(self.out))

    def test_overlay_is_written_with_regions(self):
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [], [], self.out, regions=regions)
        self.assertTrue(os.path.exists(self.out))

    def test_region_outline_changes_pixels(self):
        draw_overlay(self.render, [], [], self.out)
        plain = list(Image.open(self.out).convert("RGB").getdata())
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [], [], self.out, regions=regions)
        with_regions = list(Image.open(self.out).convert("RGB").getdata())
        self.assertNotEqual(plain, with_regions)

    def test_entities_still_draw_alongside_regions(self):
        entity = Entity(entity_id="door_0001", entity_type="door",
                        bbox=(50.0, 50.0, 90.0, 90.0), confidence=0.8,
                        source="heuristic")
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [entity], [], self.out, regions=regions)
        self.assertTrue(os.path.exists(self.out))

    def test_floor_plan_and_other_types_use_different_colours(self):
        self.assertNotEqual(REGION_OUTLINE_COLORS["floor_plan"],
                            REGION_OUTLINE_COLORS["other"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_overlay -v`
Expected: FAIL with `ImportError: cannot import name 'REGION_OUTLINE_COLORS'`

- [ ] **Step 3: Draw region outlines**

In `extraction/renderer.py`, add `Region` to the `models` import, and add after `ROOM_COLORS`:

```python
# Kept regions are drawn bright, discarded ones muted, so a glance at the
# overlay shows what detection actually saw.
REGION_OUTLINE_COLORS: dict[str, tuple[int, int, int, int]] = {
    "floor_plan":     (255,   0,   0, 220),
    "schedule_table": (255, 165,   0, 200),
    "unclassified":   (120, 120, 120, 160),
    "other":          ( 90, 130, 160, 160),
}
REGION_LINE_WIDTH = 3
```

Add the drawing helper above `draw_overlay`:

```python
def _draw_regions(draw: ImageDraw.ImageDraw, regions: list[Region], font) -> None:
    for region in regions:
        color = REGION_OUTLINE_COLORS.get(
            region.region_type, REGION_OUTLINE_COLORS["other"])
        x0, y0, x1, y1 = [int(v) for v in region.bbox]
        _draw_dashed_rect(draw, (x0, y0, x1, y1), color, REGION_LINE_WIDTH, dash=14)
        if font:
            caption = f"{region.region_id}: {region.region_type}"
            if region.title:
                caption += f" — {region.title[:32]}"
            draw.text((x0 + 5, y0 + 3), caption, fill=(0, 0, 0, 200), font=font)
            draw.text((x0 + 4, y0 + 2), caption, fill=color, font=font)
```

Change the `draw_overlay` signature and call the helper before the entity loop:

```python
def draw_overlay(
    render_png_path: str,
    entities: list[Entity],
    rejected: list[dict],
    out_path: str,
    regions: list[Region] | None = None,
) -> None:
    base = Image.open(render_png_path).convert("RGBA")
    overlay = base.copy()
    draw = ImageDraw.Draw(overlay)
    font = _load_font(FONT_SIZE)

    if regions:
        _draw_regions(draw, regions, font)

    used_types: set[str] = set()
    room_index = 0
```

(the rest of the function is unchanged)

- [ ] **Step 4: Pass regions from the pipeline**

In `pipeline.py`, change the overlay call:

```python
            draw_overlay(render_path, entities, rejected, overlay_path,
                         regions=region_result.regions)
```

- [ ] **Step 5: Add the `--refresh-regions` flag**

In `app.py`, add to the extract parser after `--no-gemini`:

```python
    p_extract.add_argument(
        "--refresh-regions",
        action="store_true",
        dest="refresh_regions",
        help="Ignore the cached region classification and call Gemini again",
    )
```

And pass it through in `cmd_extract`:

```python
    run_extract(
        pdf_path=pdf_path,
        page_indices=page_indices,
        out_parent=args.out,
        skip_gemini=args.no_gemini,
        disable_rooms=args.disable_rooms,
        disable_windows=args.disable_windows,
        debug=args.debug,
        refresh_regions=args.refresh_regions,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_region_overlay -v`
Expected: PASS, 5 tests

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no failures

- [ ] **Step 7: Update CLAUDE.md**

In `CLAUDE.md`, under "Commands", add `--refresh-regions` to the `extract` usage block. Under "Module layout", add to the tree:

```
layout/            # page segmentation — splits a sheet into its drawings
  constants.py  occupancy.py  segmenter.py  clips.py  filter.py
gemini/classifier.py     # region classification (replaced candidate validation)
gemini/region_cache.py   # classification cache, keyed by page content hash
```

Replace the "Pipeline architecture" numbered stage 5 with:

```
5. `layout.segment_page` + `gemini.classifier.classify_regions` — the page is
   split into drawing regions at its whitespace gutters (deterministic, from the
   vector ink's own coordinates), and one Gemini call classifies every region
   from a per-region crop. Detection then runs ONCE over the union of the
   `floor_plan` regions, so elevations, location plans and title blocks never
   reach the detectors. Per-candidate Gemini validation was removed on
   2026-07-28 — see docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md.
```

Update the "Output layout" block to add `regions.json` and `region_crops/` under `pages/page_NN/`.

- [ ] **Step 8: Commit**

```bash
git add extraction/renderer.py pipeline.py app.py CLAUDE.md tests/test_region_overlay.py
git commit -m "feat: draw region outlines on the overlay, add --refresh-regions"
```

---

### Task 12: Regression verification on the reference PDFs

**Files:**
- Create: `tools/compare_entities.py`
- Test: manual verification runs (this task's deliverable is evidence, not code under test)

**Interfaces:**
- Consumes: `outputs/<run>/pages/page_NN/final_entities.json`
- Produces: `tools/compare_entities.py` — a CLI that diffs two run directories by entity type, id and bbox.

The spec commits to two claims that must be checked rather than assumed: `floor-plans.pdf` is unchanged (its regions cover all 3,764 paths), and `5-1133` is unchanged except for the effect of 77 off-page paths at x≈2495 on a 2480px-wide page.

- [ ] **Step 1: Write the comparison tool**

Create `tools/compare_entities.py`:

```python
"""Diff two extraction runs by their final entities.

Usage:
    python tools/compare_entities.py OLD_RUN_DIR NEW_RUN_DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(run_dir: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for page in sorted(Path(run_dir).glob("pages/page_*/final_entities.json")):
        payload = json.loads(page.read_text(encoding="utf-8"))
        out[page.parent.name] = payload.get("entities", [])
    return out


def key(e: dict) -> tuple:
    return (e["entity_type"], e["entity_id"],
            tuple(round(v, 2) for v in e["bbox"]), round(e["confidence"], 3))


def main(old_dir: str, new_dir: str) -> int:
    old, new = load(old_dir), load(new_dir)
    pages = sorted(set(old) | set(new))
    identical = True

    for page in pages:
        a = {key(e) for e in old.get(page, [])}
        b = {key(e) for e in new.get(page, [])}
        counts_a: dict[str, int] = {}
        counts_b: dict[str, int] = {}
        for e in old.get(page, []):
            counts_a[e["entity_type"]] = counts_a.get(e["entity_type"], 0) + 1
        for e in new.get(page, []):
            counts_b[e["entity_type"]] = counts_b.get(e["entity_type"], 0) + 1

        print(f"\n=== {page}")
        for etype in sorted(set(counts_a) | set(counts_b)):
            na, nb = counts_a.get(etype, 0), counts_b.get(etype, 0)
            flag = "" if na == nb else "   <== CHANGED"
            print(f"    {etype:10s} old={na:4d}  new={nb:4d}{flag}")

        only_old, only_new = a - b, b - a
        if only_old or only_new:
            identical = False
            print(f"    {len(only_old)} entities only in OLD, {len(only_new)} only in NEW")
            for k in sorted(only_old)[:8]:
                print(f"      OLD {k[0]:8s} {k[1]:14s} bbox={k[2]} conf={k[3]}")
            for k in sorted(only_new)[:8]:
                print(f"      NEW {k[0]:8s} {k[1]:14s} bbox={k[2]} conf={k[3]}")

    print("\nIDENTICAL" if identical else "\nDIFFERENCES FOUND")
    return 0 if identical else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 2: Capture the baseline from `main`**

```bash
source .venv/bin/activate
git stash list  # ensure a clean tree
git checkout main
python app.py extract floor-plans.pdf --no-gemini --out /tmp/regionplan-base
python app.py extract 5-1133-WD03.pdf --no-gemini --out /tmp/regionplan-base
git checkout feat/floor-plan-region-filtering
```

Expected: two run directories under `/tmp/regionplan-base/`.

- [ ] **Step 3: Produce the new runs with real classification**

```bash
source .venv/bin/activate
python app.py extract floor-plans.pdf --out /tmp/regionplan-new
python app.py extract 5-1133-WD03.pdf --out /tmp/regionplan-new
```

Expected: both complete. `floor-plans.pdf` should report 2 regions, both `floor_plan`. `5-1133` should report 1 `page-fallback` region.

- [ ] **Step 4: Compare `floor-plans.pdf`**

```bash
source .venv/bin/activate
python tools/compare_entities.py \
  "$(ls -d /tmp/regionplan-base/*/ | head -1)" \
  "$(ls -d /tmp/regionplan-new/*/ | head -1)"
```

Expected: `IDENTICAL` — 12 doors, 4 windows, 13 rooms both sides. The union of the two floor-plan regions is every path on the page, and a union pass was measured to reproduce the baseline exactly.

If this reports differences, **stop**. Either the caption merge changed a region boundary or a path fell outside both regions. Diagnose before continuing.

- [ ] **Step 5: Compare `5-1133-WD03.pdf` and account for the off-page paths**

```bash
source .venv/bin/activate
python tools/compare_entities.py \
  "$(ls -d /tmp/regionplan-base/*/ | tail -1)" \
  "$(ls -d /tmp/regionplan-new/*/ | tail -1)"
```

Expected: `IDENTICAL`. `5-1133` produces a single `page-fallback` region covering `(0, 0, width_px, height_px)`, so no path is excluded and the 77 off-page paths at x≈2495 are still included — the page-fallback region is the whole page, not the segmented bounds.

If differences appear, confirm the fallback region really is the full page by checking `regions.json`:

```bash
python -c "
import json,glob
p = sorted(glob.glob('/tmp/regionplan-new/*/pages/page_01/regions.json'))[-1]
print(json.dumps(json.load(open(p)), indent=2))
"
```

- [ ] **Step 6: Verify the cache makes offline runs match online ones**

```bash
source .venv/bin/activate
python app.py extract floor-plans.pdf --no-gemini --out /tmp/regionplan-cached
python tools/compare_entities.py \
  "$(ls -d /tmp/regionplan-new/*/ | head -1)" \
  "$(ls -d /tmp/regionplan-cached/*/ | head -1)"
```

Expected: `IDENTICAL`, and `warnings.json` must NOT contain `REGION_CACHE_MISS_OFFLINE` — the classification written in Step 3 is reused.

- [ ] **Step 7: Verify a true-negative page is skipped**

```bash
source .venv/bin/activate
python app.py extract "plans/PROPOSED_FLOOR_AND_ELEVATIONS-1326086.pdf" --out /tmp/regionplan-tn
python -c "
import json,glob
w = sorted(glob.glob('/tmp/regionplan-tn/*/warnings.json'))[-1]
codes = [x['warning_code'] for x in json.load(open(w))]
print('NO_FLOOR_PLAN_REGION' in codes, codes)
e = sorted(glob.glob('/tmp/regionplan-tn/*/pages/page_01/final_entities.json'))[-1]
print('entities:', len(json.load(open(e))['entities']))
"
```

Expected: `True`, and 0 entities. This page contains only elevations; today it produces phantom doors and rooms from elevation linework.

- [ ] **Step 8: Verify a raster page is skipped without an API call**

```bash
source .venv/bin/activate
python app.py extract "plans/FLOOR_PLAN_-_EXISTING-3565362.pdf" --out /tmp/regionplan-raster
python -c "
import json,glob
w = sorted(glob.glob('/tmp/regionplan-raster/*/warnings.json'))[-1]
codes = [x['warning_code'] for x in json.load(open(w))]
print('RASTER_PAGE_NO_VECTOR_INK' in codes, codes)
r = sorted(glob.glob('/tmp/regionplan-raster/*/pages/page_01/regions.json'))[-1]
print('regions:', len(json.load(open(r))['regions']))
"
```

Expected: `True`, and 0 regions. No `.regions_cache` entry should be written for this page.

- [ ] **Step 9: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no failures

- [ ] **Step 10: Commit**

```bash
git add tools/compare_entities.py
git commit -m "test: entity-diff tool for before/after regression runs

Verified on the reference PDFs: floor-plans.pdf is identical (12 doors,
4 windows, 13 rooms), 5-1133 is identical via the whole-page fallback
region, offline cached runs match online runs, 1326086 is correctly
skipped as having no floor plan, and the raster page skips segmentation
without an API call."
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| `layout/segmenter.py` steps 1-2 (ink map, span filter) | 1 |
| step 4 (recursive cut) | 2 |
| step 3 (clip rects) | 3 |
| steps 5-6 (min side, caption merge), `Region` model | 4 |
| step 7 (primitive assignment), `filter_page_data` | 5 |
| Testing → "Segmenter" golden results | 6 |
| Deletions (`gemini/client.py`, merge collapse, warning codes) | 7 |
| `gemini/classifier.py`, taxonomy, response schema | 8 |
| Caching | 9 |
| Filtering rules 1-4, schedule scoping | 10 |
| Outputs (`regions.json`, overlay, summary counts), CLI | 11 |
| Testing → "Regression gate" | 12 |

All five warning codes are implemented: `NO_FLOOR_PLAN_REGION` and `REGION_CACHE_MISS_OFFLINE` (Task 10), `RASTER_PAGE_NO_VECTOR_INK` (Task 10), `REGION_CLASSIFY_PARSE_FAILURE` and `REGION_CLASSIFY_INCOMPLETE` (Task 8, re-raised in Task 10).

**Deviations from the spec, deliberate:**

- The spec's `Region.source` is `Literal["whitespace", "whitespace+clip", "page-fallback"]`; the plan keeps that exactly.
- The spec says schedule regions "scope the pdfplumber tables passed to `detect_schedules`". pdfplumber tables in this codebase carry no bbox, so there is nothing to filter them by. The plan instead scopes the **text spans** `detect_schedules` reads (Task 10, `schedule_text_spans`) and passes tables through unchanged. Same outcome — schedules keep working when the page is filtered to floor plans — with no new bbox plumbing.
- `CAPTION_MIN_OVERLAP_FRAC` is added as a named constant; the spec states the 50% rule in prose only.

**Type consistency:** `Region` field names are identical across `models.py` (Task 4), `region_cache.py` (Task 9), `classifier.py` (Task 8), `regions.json` (Task 10) and the overlay (Task 11). `finalize_candidates` replaces `merge_gemini_and_heuristics` in Task 7 and is not referenced under the old name anywhere later. `run_heuristics`'s new `schedule_text_spans` parameter is keyword-only in every call site.

**Known gap, by design:** under-splitting on the 7 whole-page-fallback sheets is a spec non-goal (decided 2026-07-28) and has no task. Those pages degrade to today's behaviour.
