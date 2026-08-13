# Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the whitespace XY-cut yields ≤1 region, retry it on a paths-only ink map (text spans excluded) and re-attach text to the resulting regions, so text-bridged sheets like s15 split and region filtering activates.

**Architecture:** `segment_page` keeps its current text-inclusive cut as tier 1. Only when tier 1 produces ≤1 region AND the page has text spans does tier 2 rebuild the ink map without text and re-cut; if tier 2 finds ≥2 regions, each region is grown to absorb nearby text spans (caption-style, with the existing no-overlap-increase guard) so classification crops keep their titles. Healthy sheets are byte-identical — their region geometry, `source` strings, and cache keys never change. `pipeline.resolve_page_regions` is untouched: a tier-2 split simply stops matching its `len(regions) <= 1` fallback test.

**Tech Stack:** Python 3, PyMuPDF (fitz), `unittest`. No new dependencies.

**Spec:** `docs/backlog/step-3-s15-false-positive-diagnosis.md` (the investigation this fix closes out). The measured diagnosis is in the next section — there is no separate diagnosis doc; this plan carries it.

## Diagnosis (measured 2026-08-13, this is the evidence the plan argues from)

- s15 (`fixtures/sheets/s15-proposed-floor-plans-and-elevations.pdf`, 4967×3508px, 56,765 paths, 214 text spans) segments to **1 leaf at every gutter width tried (20/12/8px)** with the current ink map, so `resolve_page_regions` falls back to whole-page detection and elevations feed the room detector → 82 returned FPs (72 rooms, 9 windows, 1 door).
- With text spans excluded from the ink map, the sheet splits into **8 regions at the standard 20px gutter** (all ≥60px sides, all 56,765 paths center-assigned = 100% coverage). The blocker is `build_ink_map` stamping each span's full bbox (`layout/occupancy.py:64-69`) — the drawings' gutters are generous; text alone bridges them.
- Mapping `tests/ground_truth/s15.json` onto those 8 regions: 28 of 29 confirmed entities sit in R0 = (88, 84, 1776, 2688), the floor-plan column. **63/72 room FPs and 6/9 window FPs sit in R2–R5 (elevations) and R1** — killed by filtering if those regions classify non-floor_plan. Predicted kill: 59–69 of 82 FPs depending on how R1 (76, 2736, 1624, 3340) classifies.
- **Known casualty:** 1 confirmed window sits in R4 = (1916, 1804, 4888, 2520). If R4 classifies as elevation, the sweep reports a LOST confirmed and exits 1. That is a user verdict, not a code problem — surface it, never edit ground truth (see Task 6).
- Corpus survey (all 20 sheets): fallback sheets are s02, s12, s15; only s15 flips with a paths-only cut (s12 has zero text spans; s02 is path-blocked). Per-drawing /VP viewports and qualifying clip rects exist only on sheets that already split — 0 qualify on s15 — so the viewport idea is dead for this corpus and is not part of this plan.

## Global Constraints

- Python: always `.venv/bin/python` / `source .venv/bin/activate`; tests via `python -m unittest`.
- New branch off main: `fix/segmenter-text-bridged-gutters`. One commit per task, imperative subject with type prefix (`feat:`/`fix:`/`refactor:`/`test:`/`docs:`). NEVER a Co-Authored-By trailer.
- NEVER run `tools/review.py`; NEVER edit `tests/ground_truth/` or fixture bytes; no PDFs committed; no address-bearing text (sheet slugs only) in code, tests, comments, or commit messages.
- Coordinates stay in 150-DPI pixel space; regions filter, they never crop or translate (see `layout/filter.py` module docstring).
- After the last code change: `graphify update .` (CLAUDE.md rule).
- Golden tests skip when `fixtures/sheets/` is absent — verify fixtures first with `.venv/bin/python tools/fetch_fixtures.py`.
- The region cache (`fixtures/sheets/.regions_cache/`) is local-only. A tier-2 geometry change makes s15 a cache MISS by design; every other sheet's key must remain a HIT (their geometry is untouched — Task 5 locks this with goldens).

---

### Task 0: Branch setup

**Files:** none (git only)

- [ ] **Step 1: Create the branch**

```bash
cd /Users/nestimate/Documents/GitHub/agent
git checkout main && git pull --ff-only 2>/dev/null; git checkout -b fix/segmenter-text-bridged-gutters
```

- [ ] **Step 2: Verify fixtures and baseline tests**

```bash
.venv/bin/python tools/fetch_fixtures.py
.venv/bin/python -m unittest discover tests
```

Expected: fixtures verify clean; full suite passes (~10s). If either fails, STOP and report — do not build on a red baseline.

---

### Task 1: `build_ink_map(include_text=...)`

**Files:**
- Modify: `layout/occupancy.py:34` (signature) and `layout/occupancy.py:64-69` (text loop)
- Test: `tests/test_layout_occupancy.py`

**Interfaces:**
- Produces: `build_ink_map(page_data: PageData, bin_px: int = SEGMENT_BIN_PX, include_text: bool = True) -> InkMap`. Default `True` keeps every existing caller byte-identical. Task 4 calls it with `include_text=False`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout_occupancy.py` (reuse that file's existing imports/helpers where they exist; the test below is self-contained either way):

```python
class TestIncludeTextFlag(unittest.TestCase):
    def _page(self):
        span = TextSpan(text="BRIDGE", bbox=(100.0, 100.0, 180.0, 120.0),
                        font="Helvetica", size=10.0, color=0,
                        block_no=0, line_no=0)
        return PageData(page_number=1, width_px=400.0, height_px=400.0,
                        paths=[], text_spans=[span])

    def test_text_spans_ink_by_default(self):
        ink = build_ink_map(self._page(), bin_px=4)
        self.assertEqual(ink.bins[int(110 / 4)][int(140 / 4)], 1)

    def test_include_text_false_leaves_text_bins_empty(self):
        ink = build_ink_map(self._page(), bin_px=4, include_text=False)
        self.assertEqual(sum(sum(row) for row in ink.bins), 0)
```

Add the imports the file is missing (likely `TextSpan`; check its header first).

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m unittest tests.test_layout_occupancy.TestIncludeTextFlag -v
```

Expected: ERROR — `build_ink_map() got an unexpected keyword argument 'include_text'`.

- [ ] **Step 3: Implement**

In `layout/occupancy.py`, change the signature and guard the text loop:

```python
def build_ink_map(
    page_data: PageData,
    bin_px: int = SEGMENT_BIN_PX,
    include_text: bool = True,
) -> InkMap:
```

and wrap the existing span loop (lines 64-69):

```python
    if include_text:
        for t in page_data.text_spans:
            x0, y0, x1, y1 = t.bbox
            for r in range(int(y0 / bin_px), int(y1 / bin_px) + 1):
                for c in range(int(x0 / bin_px), int(x1 / bin_px) + 1):
                    if 0 <= r < rows and 0 <= c < cols:
                        bins[r][c] = 1
```

- [ ] **Step 4: Run the full fast tier**

```bash
.venv/bin/python -m unittest discover tests
```

Expected: all pass (default `True` means no behavior change anywhere).

- [ ] **Step 5: Commit**

```bash
git add layout/occupancy.py tests/test_layout_occupancy.py
git commit -m "feat(layout): add include_text flag to build_ink_map"
```

---

### Task 2: Extract `_boxes_from_cut` (pure refactor)

**Files:**
- Modify: `layout/segmenter.py:227-273` (`segment_page`)

**Interfaces:**
- Produces: `_boxes_from_cut(page_data: PageData, ink: InkMap, min_bins: int, cut_rows: set[tuple[int, int, int]], cut_cols: set[tuple[int, int, int]]) -> list[BBox]` — the cut→captions→min-side→fold→sort pipeline currently inlined in `segment_page`, returning sorted kept boxes. Task 4 calls it twice (once per ink-map tier).

- [ ] **Step 1: Refactor**

In `layout/segmenter.py`, lift the body of `segment_page` between the `_xy_cut` call and the `Region(...)` construction into:

```python
def _boxes_from_cut(
    page_data: PageData,
    ink: InkMap,
    min_bins: int,
    cut_rows: set[tuple[int, int, int]],
    cut_cols: set[tuple[int, int, int]],
) -> list[BBox]:
    leaves: list[tuple[int, int, int, int]] = []
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, min_bins, cut_rows, cut_cols, 0, leaves)
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
```

and shrink `segment_page` to:

```python
def segment_page(page_data: PageData, clip_rects: list[BBox] | None = None) -> list[Region]:
    """Split a page into drawing regions. Returns [] for a page with no vector
    ink (a scanned raster page) — callers must handle that before classifying."""
    if not page_data.paths:
        return []

    ink = build_ink_map(page_data, bin_px=SEGMENT_BIN_PX)
    min_bins = max(1, SEGMENT_MIN_GUTTER_PX // ink.bin_px)
    cut_rows, cut_cols = clip_cut_positions(clip_rects or [], ink.bin_px)

    boxes = _boxes_from_cut(page_data, ink, min_bins, cut_rows, cut_cols)
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
```

(The two inline comments move with the code — they explain ordering, and `_boxes_from_cut` is where the ordering now lives.)

- [ ] **Step 2: Run the full fast tier — refactor must be invisible**

```bash
.venv/bin/python -m unittest discover tests
```

Expected: all pass, zero behavior change.

- [ ] **Step 3: Golden check on real sheets (fixtures present)**

```bash
.venv/bin/python -m unittest tests.test_layout_golden -v
```

Expected: all pass (s01=2 regions, s02=1, s11=13).

- [ ] **Step 4: Commit**

```bash
git add layout/segmenter.py
git commit -m "refactor(layout): extract _boxes_from_cut from segment_page"
```

---

### Task 3: `_attach_text_spans`

**Files:**
- Modify: `layout/segmenter.py` (new function next to `_fold_small_leaves`)
- Test: `tests/test_layout_segmenter.py`

**Interfaces:**
- Consumes: `_edge_gap_sq(a: BBox, b: BBox) -> float` and `_overlap_area(a: BBox, b: BBox) -> float` (both already in `layout/segmenter.py`), `CAPTION_MAX_GAP_PX` from `layout.constants`.
- Produces: `_attach_text_spans(page_data: PageData, boxes: list[BBox]) -> list[BBox]` — same-length list, each box grown to absorb nearby text spans. Task 4 calls it on tier-2 boxes only.

Semantics (mirrors `_fold_small_leaves`, but for spans):
- A span whose center already lies inside a box is skipped (nothing to grow).
- Otherwise try boxes nearest-edge-gap first; a candidate farther than `CAPTION_MAX_GAP_PX` ends the search (real captions measure 44-48px from their drawing — same measured basis the caption merge uses, so no new constant).
- A union that would increase overlap with any other box is rejected (the `_fold_small_leaves` leak guard, verbatim) and the next-nearest box is tried; a span that leaks everywhere stays unattached — coverage is path-based, so an orphan span costs nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_layout_segmenter.py`:

```python
from layout.segmenter import _attach_text_spans


def span(text, x0, y0, x1, y1):
    return TextSpan(text=text, bbox=(float(x0), float(y0), float(x1), float(y1)),
                    font="Helvetica", size=10.0, color=0, block_no=0, line_no=0)


class TestAttachTextSpans(unittest.TestCase):
    def test_nearby_span_grows_its_nearest_box(self):
        # Caption 40px below box A: within CAPTION_MAX_GAP_PX, attaches.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("GROUND FLOOR PLAN", 60, 240, 180, 260)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 260.0)])

    def test_span_already_inside_a_box_changes_nothing(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("KITCHEN", 100, 100, 140, 112)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 200.0)])

    def test_distant_span_stays_unattached(self):
        # 160px below the box: past CAPTION_MAX_GAP_PX, box must not stretch.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("NOTES", 60, 360, 180, 380)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 200.0)])

    def test_union_never_leaks_another_box(self):
        # Span 50px right of tall box A; union(A, span) would sweep over B's
        # column. B itself is 90px below the span — past the gap cap. The span
        # must attach nowhere and both boxes stay untouched.
        a = (40.0, 40.0, 100.0, 340.0)
        b = (150.0, 150.0, 250.0, 230.0)
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("LABEL", 150, 40, 200, 60)])
        out = _attach_text_spans(pd, [a, b])
        self.assertEqual(out, [a, b])

    def test_tie_breaks_to_first_box_and_does_not_double_attach(self):
        # Span dead-centre in a 100px gutter between two boxes: attaches to
        # exactly one (the first in kept order); the other must not grow.
        boxes = [(40.0, 40.0, 150.0, 200.0), (250.0, 40.0, 360.0, 200.0)]
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("BRIDGE", 160, 100, 240, 120)])
        out = _attach_text_spans(pd, boxes)
        grew = [o for o, b in zip(out, boxes) if o != b]
        self.assertEqual(len(grew), 1)
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m unittest tests.test_layout_segmenter.TestAttachTextSpans -v
```

Expected: ImportError — `cannot import name '_attach_text_spans'`.

- [ ] **Step 3: Implement**

In `layout/segmenter.py`, after `_fold_small_leaves` (import `CAPTION_MAX_GAP_PX` is already in the file's constants import):

```python
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
```

- [ ] **Step 4: Run to verify they pass**

```bash
.venv/bin/python -m unittest tests.test_layout_segmenter.TestAttachTextSpans -v
.venv/bin/python -m unittest discover tests
```

Expected: PASS, full suite green.

- [ ] **Step 5: Commit**

```bash
git add layout/segmenter.py tests/test_layout_segmenter.py
git commit -m "feat(layout): add _attach_text_spans for paths-only regions"
```

---

### Task 4: The tier-2 retry in `segment_page` + `Region.source` widening

**Files:**
- Modify: `layout/segmenter.py` (`segment_page`)
- Modify: `models.py:88` (`Region.source` Literal)
- Test: `tests/test_layout_segmenter.py`

**Interfaces:**
- Consumes: `build_ink_map(..., include_text=False)` (Task 1), `_boxes_from_cut(...)` (Task 2), `_attach_text_spans(...)` (Task 3).
- Produces: `segment_page` unchanged signature; tier-2 regions carry `source="paths-only"` (or `"paths-only+clip"` when clip rects were passed). `models.Region.source` becomes `Literal["whitespace", "whitespace+clip", "paths-only", "paths-only+clip", "page-fallback"]`.

Trigger rules (all three needed):
1. Tier 1 produced ≤1 box — the same predicate `resolve_page_regions` uses for fallback, so tier 2 fires exactly where whole-page detection would have.
2. The page HAS text spans — with none, the tier-2 ink map is identical to tier 1's and the re-cut is a wasted rebuild (s12: 40k paths, 0 spans, stays fallback).
3. Tier 2 found ≥2 boxes — otherwise keep the tier-1 result untouched (s02 stays a 1-region sheet and its golden keeps passing).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_layout_segmenter.py`:

```python
class TestPathsOnlyRetry(unittest.TestCase):
    def _bridged_page(self, extra_spans=()):
        # Two drawings with a 100px gutter; one span's bbox stamps the ink map
        # across x=160..240, leaving <20px of empty run on each side — tier 1
        # cannot split this page, exactly the measured s15 mechanism.
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        spans = [span("BRIDGING LABEL", 160, 100, 240, 120), *extra_spans]
        return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                        paths=paths, text_spans=spans)

    def test_text_bridged_gutter_splits_via_retry(self):
        regions = segment_page(self._bridged_page())
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "paths-only" for r in regions))

    def test_retry_reattaches_the_bridging_span_to_one_region(self):
        regions = segment_page(self._bridged_page())
        cx, cy = 200.0, 110.0  # bridging span centre
        holders = [r for r in regions
                   if r.bbox[0] <= cx <= r.bbox[2] and r.bbox[1] <= cy <= r.bbox[3]]
        self.assertEqual(len(holders), 1)

    def test_retry_reattaches_captions_for_classification_crops(self):
        caption = span("GROUND FLOOR PLAN", 50, 240, 140, 260)  # 40px below left blob
        regions = segment_page(self._bridged_page(extra_spans=(caption,)))
        self.assertEqual(len(regions), 2)
        left = min(regions, key=lambda r: r.bbox[0])
        self.assertGreaterEqual(left.bbox[3], 260.0)

    def test_healthy_page_never_retries(self):
        # Splits fine with text included: source must stay "whitespace".
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=paths,
                      text_spans=[span("KITCHEN", 60, 100, 100, 112)])
        regions = segment_page(pd)
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "whitespace" for r in regions))

    def test_dense_blob_still_yields_one_region(self):
        # No gutter even without text: tier 2 also finds 1 box, so the result
        # stays a single tier-1 region and the pipeline falls back as today.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 360, 200),
                      text_spans=[span("ELEVATION", 100, 100, 180, 112)])
        regions = segment_page(pd)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].source, "whitespace")

    def test_textless_page_skips_the_retry(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 360, 200))
        regions = segment_page(pd)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].source, "whitespace")

    def test_retry_source_records_clip_involvement(self):
        # The clip's edges sit at the ink's outer bounds, so its cut positions
        # land where _clip_cut skips them (no ink on both sides) — tier 1
        # still cannot split and the retry runs; source records the clips.
        # (A clip edge BETWEEN the blobs would rescue tier 1 by itself and
        # the retry would never fire — that path is the existing
        # test_clip_edge_splits_when_no_gutter_exists.)
        regions = segment_page(self._bridged_page(),
                               clip_rects=[(40.0, 40.0, 360.0, 200.0)])
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "paths-only+clip" for r in regions))
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m unittest tests.test_layout_segmenter.TestPathsOnlyRetry -v
```

Expected: the bridged/retry/caption/clip tests FAIL (1 region, or source "whitespace"); the healthy/dense/textless tests may already pass — that is fine, they pin the no-change contract.

- [ ] **Step 3: Implement**

In `models.py:88`:

```python
    source: Literal["whitespace", "whitespace+clip", "paths-only",
                    "paths-only+clip", "page-fallback"] = "whitespace"
```

In `layout/segmenter.py`, insert between the tier-1 `_boxes_from_cut` call and the `Region(...)` return (Task 2's version of `segment_page`):

```python
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
        retry = _boxes_from_cut(page_data, retry_ink, min_bins, cut_rows, cut_cols)
        if len(retry) >= 2:
            boxes = _attach_text_spans(page_data, retry)
            source = "paths-only+clip" if clip_rects else "paths-only"
```

- [ ] **Step 4: Run to verify they pass, then the whole fast tier**

```bash
.venv/bin/python -m unittest tests.test_layout_segmenter -v
.venv/bin/python -m unittest discover tests
```

Expected: all pass. Any existing segmenter test that breaks means the trigger leaked into healthy pages — fix the trigger, not the test.

- [ ] **Step 5: Commit**

```bash
git add layout/segmenter.py models.py tests/test_layout_segmenter.py
git commit -m "feat(layout): retry the XY-cut on a paths-only ink map when a page cannot split"
```

---

### Task 5: Golden lock on s15 + healthy-sheet stability

**Files:**
- Test: `tests/test_layout_golden.py`

**Interfaces:**
- Consumes: the `segment(test_case, slug)` helper already in that file (`tests/test_layout_golden.py:18`); `assigned_path_fraction` from `layout.filter`.

- [ ] **Step 1: Write the golden tests (fixtures required)**

Append to `tests/test_layout_golden.py`:

```python
class TestS15PathsOnlyRetry(unittest.TestCase):
    """s15 measured 2026-08-13: 214 text spans bridge every gutter, so the
    text-inclusive cut yields 1 leaf and the sheet fell back to whole-page
    detection (82 returned FPs, 63 of 72 phantom rooms fenced in elevation
    regions). The paths-only retry splits it into 8 regions with full path
    coverage."""

    def test_s15_splits_into_eight_regions_via_retry(self):
        _, regions = segment(self, "s15")
        self.assertEqual(len(regions), 8)
        self.assertTrue(all(r.source == "paths-only" for r in regions))

    def test_s15_every_path_stays_assigned(self):
        from layout.filter import assigned_path_fraction
        page_data, regions = segment(self, "s15")
        self.assertEqual(assigned_path_fraction(page_data, regions), 1.0)

    def test_s15_floor_plans_and_elevations_split_apart(self):
        # (900, 1400) sits inside the floor-plan column (R0 in the diagnosis
        # mapping, which held all 28 in-plan confirmed entities); (3000, 1400)
        # sits inside an elevation region (R3). The point of the retry is that
        # these end up in DIFFERENT regions; exact grown bboxes are not pinned
        # because _attach_text_spans legitimately widens them.
        _, regions = segment(self, "s15")

        def holder(x, y):
            return next(r for r in regions
                        if r.bbox[0] <= x <= r.bbox[2]
                        and r.bbox[1] <= y <= r.bbox[3])

        self.assertIsNot(holder(900.0, 1400.0), holder(3000.0, 1400.0))
```

- [ ] **Step 2: Run the goldens**

```bash
.venv/bin/python -m unittest tests.test_layout_golden -v
```

Expected: new s15 tests pass AND the existing goldens still pass unchanged — s01=2 (`whitespace`), s02=1, s11=13. s02 passing proves trigger rule 3 (retry found ≤1, tier-1 result kept). If s15 yields a different region count, STOP: re-measure with the diagnosis script before touching the expected number (the count is measured, not negotiable by test-editing).

- [ ] **Step 3: Commit**

```bash
git add tests/test_layout_golden.py
git commit -m "test(layout): golden-lock the s15 paths-only retry split"
```

---

### Task 6: End-to-end verification on the corpus + docs

**Files:**
- Modify: `CLAUDE.md` (stage-3 bullet, one sentence)
- No detection code changes in this task.

- [ ] **Step 1: Offline sweep first (proves no regression before the cache exists)**

```bash
.venv/bin/python tools/regress.py --sheet s15
```

Expected: s15's new geometry is a region-cache MISS, so the run warns `REGION_CACHE_MISS_OFFLINE`, detects the whole page, and the sweep result is IDENTICAL to baseline (82 FPs). This is the designed offline behavior, not a bug.

- [ ] **Step 2: Populate the region cache for the new geometry (one Gemini call)**

Requires GCP auth (`gcloud auth application-default login` — if it fails, ask the user to run it with the `!` prefix). Then:

```bash
.venv/bin/python app.py extract fixtures/sheets/s15-proposed-floor-plans-and-elevations.pdf --pages 1
```

Inspect the newest `outputs/<timestamp>/pages/page_01/regions.json`: expect 8 regions, and record each `region_type`. The floor-plan column (bbox ≈ 88, 84, 1776, 2688 before text growth) must classify `floor_plan`. If it classifies as anything else, STOP and report — filtering would erase all 28 confirmed entities, and that is a classifier problem to surface, not to code around.

- [ ] **Step 3: The payoff sweep**

```bash
.venv/bin/python tools/regress.py --sheet s15
```

Expected: returned false positives drop from 82 to roughly 13–23 (13 sit inside the floor-plan column; R1's 4 room FPs survive only if R1 classifies floor_plan; elevation-region FPs die). Likely exit 1 with ONE lost confirmed: the window in the R4 elevation region (bbox region ≈ 1916, 1804, 4888, 2520). Record the exact numbers.

- [ ] **Step 4: Full-corpus sweep — every other sheet must be byte-stable**

```bash
.venv/bin/python tools/regress.py
```

Expected: no sheet other than s15 changes in any way (their region geometry is untouched, so their caches hit). Any drift on another sheet is a bug in the trigger rules — STOP and diagnose.

- [ ] **Step 5: Update CLAUDE.md's stage-3 description**

In the stage-3 bullet of "Pipeline architecture" (after "split into drawing regions at its whitespace gutters (deterministic, from the vector ink's own coordinates)"), add one sentence:

```
A page the cut cannot split at all is retried once with text spans excluded
from the ink map (text bboxes bridge otherwise-generous gutters — measured on
s15: 1 leaf with text, 8 regions without), and the resulting regions are grown
to re-absorb nearby text so classification crops keep their captions
(source: "paths-only").
```

- [ ] **Step 6: Regenerate the knowledge graph and commit**

```bash
graphify update .
git add CLAUDE.md graphify-out
git commit -m "docs: describe the paths-only segmentation retry tier"
```

- [ ] **Step 7: Report to the user (do not act on these yourself)**

Present: the s15 before/after FP counts, the per-region classifications from Step 2, and the expected LOST confirmed window in R4. The user decides its ground-truth fate (re-verdict/deferral is a user-only edit — NEVER touch `tests/ground_truth/s15.json`). Only after their verdict does the branch merge; a red sweep entry is a work queue item, never a signal to soften.

---

## Self-Review

- **Spec coverage:** the backlog step's diagnosis deliverable is embedded in this plan's Diagnosis section; the fix implements the dominant mechanism (segmentation fallback). The 13 in-plan residual FPs are explicitly OUT of scope — single-mechanism branch, per repo convention.
- **Placeholder scan:** every step carries runnable code/commands; no TBDs.
- **Type consistency:** `_boxes_from_cut(page_data, ink, min_bins, cut_rows, cut_cols)` is defined in Task 2 and called with the same shape in Task 4; `_attach_text_spans(page_data, boxes)` defined in Task 3, called in Task 4; `include_text` keyword defined in Task 1, used in Task 4; `span()` test helper defined in Task 3's test block and reused in Task 4's (same file, defined above).
- **Known risks, stated:** R4 confirmed-window loss (user verdict, Task 6 Step 7); Gemini misclassifying the floor-plan column (Task 6 Step 2 STOP rule); s02/s12 intentionally unchanged (out of scope — s12 has no text to exclude, s02 is path-blocked).
