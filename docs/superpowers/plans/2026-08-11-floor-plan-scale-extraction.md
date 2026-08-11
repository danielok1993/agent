# Floor Plan Scale Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve a drawing scale for each floor plan on a sheet and print it to the console.

**Architecture:** A new `scale/` package with one module per resolution tier — `viewport.py` reads the PDF's `/VP` → `/Measure` dictionaries, `text.py` reads `1:N` from text spans, `store.py` persists user-supplied values, `prompt.py` asks for them. `resolver.py` runs the tiers as a ladder and binds each result to a `floor_plan` region by bbox. `pipeline.run_extract` calls the resolver in a new stage after `resolve_page_regions` and prints a table. Nothing consumes the value yet.

**Tech Stack:** Python 3, PyMuPDF (`fitz`), `rich` for console output, `unittest` for tests.

**Spec:** `docs/superpowers/specs/2026-08-11-floor-plan-scale-extraction-design.md`

## Global Constraints

- **Tests use `unittest`, not pytest.** Run with `python -m unittest`. The whole suite must stay under ~10s; no new test may open a corpus PDF except in Task 10.
- **Activate the venv first:** `source .venv/bin/activate`.
- **All coordinates past `extraction/` are 150-DPI pixels, top-left origin, y-down.** `SCALE = 150/72`.
- **`/VP /BBox` is the one exception** — it is raw PDF, y-up, bottom-left. It must be flipped about the mediabox *before* `page_transform` is applied. Getting this backwards silently mis-binds every scale; see the spec's "The `/VP` bbox is y-up" section.
- **`MM_PER_PT = 25.4 / 72`** exactly. Scale denominator is `C / MM_PER_PT`.
- **Nothing may block an unattended run.** Prompting needs BOTH `allow_scale_prompt` (off for `regress.py` and `batch_extract.py`) and `sys.stdin.isatty()`. The tty check alone is insufficient — the sweep calls `run_extract` in-process and the batch children inherit stdin, so both see a real terminal. See Task 8.
- **Never commit an address.** Corpus data is keyed by slug (`s09`), never by filename.
- **Warning dicts** carry `page_number`, `warning_code` (SCREAMING_SNAKE_CASE), `severity`, `message`.
- **No `Co-Authored-By` trailer on commits.**

## File Structure

| File | Responsibility |
|---|---|
| `models.py` (modify) | Add the `ScaleInfo` dataclass beside the other shared types |
| `scale/__init__.py` (create) | Public facade — re-export `resolve_page_scales`, `ScaleInfo` helpers |
| `scale/units.py` (create) | `MM_PER_PT`, denominator arithmetic, standard-scale snapping |
| `scale/viewport.py` (create) | Tier 1 — parse `/VP` → `/Measure`, flip and transform bboxes |
| `scale/text.py` (create) | Tier 2 — find `1:N` in text spans |
| `scale/store.py` (create) | Tier 4 persistence — ground-truth back-end and local-cache back-end |
| `scale/prompt.py` (create) | Tier 4 input — tty-gated prompt |
| `scale/resolver.py` (create) | The ladder, region binding, conflict detection, warnings |
| `regression/corpus.py` (modify) | Add `slug_for_path` so the store can pick its back-end |
| `regression/ground_truth.py` (modify) | Carry a `scales` block through load/dump without dropping it |
| `pipeline.py` (modify) | New stage, console table, `summary.json` field, warning plumbing |
| `inspector.py` (modify) | Degraded unbound display for the `inspect` command |
| `app.py` (modify) | `--no-scale-prompt` on the `extract` subcommand |
| `regression/sweep.py` (modify) | Call `run_extract` with prompting disabled |
| `batch_extract.py` (modify) | Pass `--no-scale-prompt`, give the child no stdin |

---

### Task 1: Units and the `ScaleInfo` model

**Files:**
- Create: `scale/__init__.py`, `scale/units.py`
- Modify: `models.py` (append after the `Region` dataclass, around line 89)
- Test: `tests/test_scale_units.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `models.ScaleInfo`; `scale.units.MM_PER_PT: float`, `PAPER_SPACE_MAX_DENOMINATOR: float`, `denominator_from_c(c: float) -> float`, `snap_to_standard(denominator: float) -> Optional[float]`, `format_scale(denominator: float) -> str`, `AGREEMENT_TOLERANCE: float`, `cluster_denominators(denominators, tolerance=...) -> list[list[float]]`, `canonical_denominators(denominators, tolerance=...) -> list[float]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_units.py`:

```python
"""Scale arithmetic: PDF /Measure conversion factors to a 1:N denominator.

Every number here is measured from the regression corpus on 2026-08-11 and
recorded in the design spec. A failure means the conversion changed, not that
the expectations are stale.
"""
import unittest

from models import ScaleInfo
from scale.units import (
    MM_PER_PT,
    PAPER_SPACE_MAX_DENOMINATOR,
    canonical_denominators,
    cluster_denominators,
    denominator_from_c,
    format_scale,
    snap_to_standard,
)


class TestDenominatorFromC(unittest.TestCase):
    def test_mm_per_pt_is_exact(self):
        self.assertAlmostEqual(MM_PER_PT, 25.4 / 72, places=12)

    def test_s17_plan_viewport_is_1_to_100(self):
        self.assertAlmostEqual(denominator_from_c(35.27288), 99.99, places=2)

    def test_s17_plan_viewport_is_1_to_50(self):
        self.assertAlmostEqual(denominator_from_c(17.63849), 50.00, places=2)

    def test_s03_location_inset_is_1_to_500(self):
        self.assertAlmostEqual(denominator_from_c(176.35256), 499.9, places=1)

    def test_s17_location_inset_is_1_to_1250(self):
        self.assertAlmostEqual(denominator_from_c(440.67143), 1249.1, places=1)

    def test_paper_space_viewport_is_1_to_1(self):
        self.assertAlmostEqual(denominator_from_c(0.35279), 1.0, places=2)


class TestSnapToStandard(unittest.TestCase):
    def test_s06_inner_viewport_snaps_to_100(self):
        self.assertEqual(snap_to_standard(99.6), 100.0)

    def test_s17_inset_snaps_to_1250(self):
        self.assertEqual(snap_to_standard(1249.1), 1250.0)

    def test_s03_inset_snaps_to_500(self):
        self.assertEqual(snap_to_standard(499.9), 500.0)

    def test_s13_inner_viewport_snaps_to_nothing(self):
        # 136.4 is 36% from 100 and 32% from 200 — this is the one corpus
        # sheet whose measured scale is not a standard one.
        self.assertIsNone(snap_to_standard(136.4))

    def test_s06_outer_viewport_snaps_to_nothing(self):
        self.assertIsNone(snap_to_standard(146.0))


class TestClusterDenominators(unittest.TestCase):
    """CAD never writes the same scale as the same float, so every value here
    is a real corpus measurement rather than a round number."""

    def test_s04s_two_1_to_50_viewports_form_one_group(self):
        self.assertEqual(len(cluster_denominators([49.995, 50.001])), 1)

    def test_s17s_four_1_to_100_plans_form_one_group_of_four(self):
        groups = cluster_denominators([99.986, 99.988, 99.993, 99.995])
        self.assertEqual([len(g) for g in groups], [4])

    def test_s17s_full_sheet_reduces_to_three_scales(self):
        groups = cluster_denominators(
            [1249.147, 99.986, 99.988, 99.995, 99.993, 49.999])
        self.assertEqual([len(g) for g in groups], [1, 4, 1])

    def test_s03s_full_sheet_reduces_to_three_scales(self):
        self.assertEqual(
            len(cluster_denominators([499.897, 49.99, 99.993, 99.971])), 3)

    def test_genuinely_different_scales_stay_apart(self):
        # s06: an inner 1:99.6 and an outer 1:146 are two real readings.
        self.assertEqual(len(cluster_denominators([99.6, 146.0])), 2)

    def test_an_empty_input_yields_nothing(self):
        self.assertEqual(cluster_denominators([]), [])


class TestCanonicalDenominators(unittest.TestCase):
    def test_one_representative_per_group(self):
        self.assertEqual(
            len(canonical_denominators([99.986, 99.988, 99.993, 99.995])), 1)

    def test_empty_input(self):
        self.assertEqual(canonical_denominators([]), [])


class TestFormatScale(unittest.TestCase):
    def test_whole_number_has_no_decimal(self):
        self.assertEqual(format_scale(100.0), "1:100")

    def test_non_standard_keeps_one_decimal(self):
        self.assertEqual(format_scale(136.4), "1:136.4")


class TestScaleInfoDefaults(unittest.TestCase):
    def test_unresolved_needs_only_a_source(self):
        info = ScaleInfo(denominator=None, source="unresolved")
        self.assertIsNone(info.denominator)
        self.assertIsNone(info.bbox)
        self.assertIsNone(info.raw)
        self.assertIsNone(info.nominal)
        self.assertIsNone(info.conflict)

    def test_paper_space_threshold_excludes_one_to_one(self):
        self.assertLess(1.0, PAPER_SPACE_MAX_DENOMINATOR)
        self.assertGreater(20.0, PAPER_SPACE_MAX_DENOMINATOR)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_units -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale'`

- [ ] **Step 3: Write minimal implementation**

Append to `models.py` (after the `Region` dataclass):

```python
@dataclass
class ScaleInfo:
    """A drawing scale, and the evidence it came from.

    `denominator` 100.0 means 1:100. `bbox` is the extent of the evidence in
    150-DPI pixels — a viewport's rectangle or a text span's box — and is what
    binds a scale to a region. `nominal` is the nearest standard scale when the
    measured value is within tolerance, and None when it is not (s13 measures
    1:136.4 and snaps to nothing).
    """
    denominator: Optional[float]
    source: Literal["viewport", "text", "user", "unresolved"]
    bbox: Optional[BBox] = None
    raw: Optional[str] = None
    nominal: Optional[float] = None
    conflict: Optional[str] = None
```

Create `scale/units.py`:

```python
"""Scale arithmetic shared by every resolution tier.

A PDF /Measure dictionary states its conversion factor /C as real-world units
per PDF point. Every corpus sheet leaves /U blank, but the paper-space viewport
on each of them reads C = 0.35278 — exactly 1 mm/pt — which pins the unit to
millimetres. See the design spec for the measurements.
"""
from __future__ import annotations

from typing import Optional

MM_PER_PT = 25.4 / 72  # 0.352777...

# A viewport at 1:1 is the sheet of paper, not a drawing. Ten of the corpus
# sheets carry one; s03, s04, s08 and s17 span the whole page with it.
PAPER_SPACE_MAX_DENOMINATOR = 1.5

# UK architectural and OS map scales. Ordered small to large; the first match
# inside tolerance wins, and the bands never overlap at 2%.
STANDARD_SCALES = (1, 20, 25, 50, 100, 200, 500, 1000, 1250, 2500)

SNAP_TOLERANCE = 0.02

# Two readings of the same drawing closer than this are the same scale written
# differently, not a disagreement. s06 measures 99.6 against a printed 1:100.
AGREEMENT_TOLERANCE = 0.02


def cluster_denominators(
    denominators, tolerance: float = AGREEMENT_TOLERANCE
) -> list[list[float]]:
    """Group near-equal denominators, largest group first in input order.

    Lives here rather than in the resolver because the inspector needs the
    same grouping to count repeats, and two implementations would drift.

    CAD never writes the same scale as the same float: s04's two 1:50
    viewports measure 49.995 and 50.001, and s17's four 1:100 plans measure
    99.986, 99.988, 99.993 and 99.995. Anything keyed on the raw float reads a
    single-scale sheet as multi-scale, or prints one scale four times.
    """
    groups: list[list[float]] = []
    for value in sorted(denominators):
        if groups and abs(value - groups[-1][0]) <= tolerance * groups[-1][0]:
            groups[-1].append(value)
        else:
            groups.append([value])
    return groups


def canonical_denominators(
    denominators, tolerance: float = AGREEMENT_TOLERANCE
) -> list[float]:
    """One representative per cluster — how many DISTINCT scales are present."""
    return [group[0] for group in cluster_denominators(denominators, tolerance)]


def denominator_from_c(c: float) -> float:
    """The 1:N denominator for a /Measure /X conversion factor."""
    return c / MM_PER_PT


def snap_to_standard(
    denominator: float, tolerance: float = SNAP_TOLERANCE
) -> Optional[float]:
    """The nearest standard scale within tolerance, or None.

    None is a real answer, not a failure: s13 measures 1:136.4, and rounding
    that to 1:100 would invent precision the drawing does not have.
    """
    for standard in STANDARD_SCALES:
        if abs(denominator - standard) <= tolerance * standard:
            return float(standard)
    return None


def format_scale(denominator: float) -> str:
    """Render a denominator for display: 1:100, or 1:136.4 when it is not whole."""
    if abs(denominator - round(denominator)) < 0.05:
        return f"1:{int(round(denominator))}"
    return f"1:{denominator:.1f}"
```

Create `scale/__init__.py`:

```python
"""Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan."""
from scale.units import (
    AGREEMENT_TOLERANCE,
    MM_PER_PT,
    PAPER_SPACE_MAX_DENOMINATOR,
    canonical_denominators,
    cluster_denominators,
    denominator_from_c,
    format_scale,
    snap_to_standard,
)

__all__ = [
    "AGREEMENT_TOLERANCE",
    "MM_PER_PT",
    "PAPER_SPACE_MAX_DENOMINATOR",
    "canonical_denominators",
    "cluster_denominators",
    "denominator_from_c",
    "format_scale",
    "snap_to_standard",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_units -v`
Expected: PASS, 23 tests

- [ ] **Step 5: Commit**

```bash
git add models.py scale/__init__.py scale/units.py tests/test_scale_units.py
git commit -m "feat(scale): ScaleInfo model and scale arithmetic

denominator = C / (25.4/72), with standard-scale snapping at 2%.
Expectations are the corpus measurements from the design spec."
```

---

### Task 2: Tier 1 — viewport parsing

**Files:**
- Create: `scale/viewport.py`
- Test: `tests/test_scale_viewport.py`

**Interfaces:**
- Consumes: `models.ScaleInfo`; `scale.units.denominator_from_c`, `snap_to_standard`, `PAPER_SPACE_MAX_DENOMINATOR`; `extraction.extractor.page_transform`.
- Produces: `scale.viewport.split_pdf_dicts(array_text: str) -> list[str]`, `parse_measure_viewports(vp_array_text: str) -> list[tuple[tuple[float,float,float,float], float]]` returning `(bbox_pt_yup, c)` pairs, and `viewport_scales(doc, page) -> list[ScaleInfo]` sorted smallest-bbox-first.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_viewport.py`:

```python
"""Parsing /VP -> /Measure viewport dictionaries.

The array strings below are copied verbatim from corpus sheets via
doc.xref_get_key(page.xref, "VP"), so these tests exercise the real byte
shapes -- both the compact form AutoCAD writes and the pretty-printed form
that appears in xref_object output.
"""
import unittest

from scale.viewport import (
    parse_measure_viewports,
    split_pdf_dicts,
    viewport_bbox_to_px,
)

# s06, verbatim. Two nested viewports: the outer measures 1:146, the inner
# 1:99.6 -- and the inner is the one matching the sheet's own "SCALE 1:100".
S06_VP = (
    "[<</Type/Viewport/BBox[30 50 1159 791]/Measure<</Type/Measure/Subtype/RL"
    "/A[<</C 1/U( )>>]/D[<</C 1/U( )>>]/R( )/X[<</C 51.51447/U( )>>]>>>>"
    "<</Type/Viewport/BBox[30 172 1023 790]/Measure<</Type/Measure/Subtype/RL"
    "/A[<</C 1/U( )>>]/D[<</C 1/U( )>>]/R( )/X[<</C 35.13904/U( )>>]>>>>]"
)

# s03, pretty-printed with whitespace, and including its 1:1 paper-space
# viewport spanning the whole sheet.
S03_VP_PRETTY = (
    "[ << /Type /Viewport /BBox [ 34 72 2348 1610 ] /Measure << /Subtype /RL "
    "/A [ << /C 1 /U ( ) >> ] /X [ << /C .35279 /U ( ) >> ] >> >> "
    "<< /Type /Viewport /BBox [ 137 270 1492 891 ] /Measure << /Subtype /RL "
    "/X [ << /C 35.27546 /U ( ) >> ] >> >> ]"
)


class TestSplitPdfDicts(unittest.TestCase):
    def test_splits_two_adjacent_viewports(self):
        self.assertEqual(len(split_pdf_dicts(S06_VP)), 2)

    def test_nested_dicts_do_not_split(self):
        chunks = split_pdf_dicts(S06_VP)
        self.assertIn("/C 51.51447", chunks[0])
        self.assertNotIn("/C 35.13904", chunks[0])

    def test_empty_array_yields_nothing(self):
        self.assertEqual(split_pdf_dicts("[]"), [])

    def test_unbalanced_array_does_not_hang_or_raise(self):
        self.assertEqual(split_pdf_dicts("[<</BBox[1 2 3 4]"), [])


class TestParseMeasureViewports(unittest.TestCase):
    def test_s06_yields_both_viewports(self):
        self.assertEqual(len(parse_measure_viewports(S06_VP)), 2)

    def test_s06_inner_viewport_conversion_factor(self):
        found = {round(c, 5) for _, c in parse_measure_viewports(S06_VP)}
        self.assertEqual(found, {51.51447, 35.13904})

    def test_s06_bboxes_are_kept_with_their_own_factor(self):
        by_c = {round(c, 5): bbox for bbox, c in parse_measure_viewports(S06_VP)}
        self.assertEqual(by_c[35.13904], (30.0, 172.0, 1023.0, 790.0))

    def test_pretty_printed_whitespace_form_parses(self):
        found = {round(c, 5) for _, c in parse_measure_viewports(S03_VP_PRETTY)}
        self.assertIn(35.27546, found)

    def test_paper_space_viewport_is_dropped(self):
        # .35279 is 1:1 -- the sheet, not a drawing.
        found = {round(c, 5) for _, c in parse_measure_viewports(S03_VP_PRETTY)}
        self.assertNotIn(0.35279, found)

    def test_non_rectilinear_subtype_is_ignored(self):
        geo = ("[<</Type/Viewport/BBox[0 0 10 10]/Measure<</Subtype/GEO"
               "/X[<</C 35.0/U( )>>]>>>>]")
        self.assertEqual(parse_measure_viewports(geo), [])

    def test_viewport_without_measure_is_ignored(self):
        plain = "[<</Type/Viewport/BBox[0 0 10 10]>>]"
        self.assertEqual(parse_measure_viewports(plain), [])

    def test_area_factor_is_not_mistaken_for_the_axis_factor(self):
        # /A carries C 1; only /X states the drawing scale.
        by_c = {round(c, 5) for _, c in parse_measure_viewports(S06_VP)}
        self.assertNotIn(1.0, by_c)


class TestViewportBboxToPx(unittest.TestCase):
    """The /VP bbox is raw PDF: y-up, bottom-left origin. Everything else in
    the pipeline is y-down, top-left. Verified by rendering both readings --
    see the spec's "The /VP bbox is y-up" section."""

    IDENTITY = (150 / 72, 0.0, 0.0, 150 / 72, 0.0, 0.0)

    def test_y_is_flipped_about_the_mediabox(self):
        # s17's 1:1250 inset on a 2384x1684pt sheet sits near the TOP.
        px = viewport_bbox_to_px(
            (2100.0, 1267.0, 2296.0, 1519.0),
            mediabox=(0.0, 0.0, 2384.0, 1684.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[1], (1684.0 - 1519.0) * s, places=3)
        self.assertAlmostEqual(px[3], (1684.0 - 1267.0) * s, places=3)

    def test_x_is_offset_by_the_mediabox_origin(self):
        px = viewport_bbox_to_px(
            (10.0, 0.0, 20.0, 100.0),
            mediabox=(5.0, 0.0, 105.0, 100.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[0], 5.0 * s, places=3)
        self.assertAlmostEqual(px[2], 15.0 * s, places=3)

    def test_result_is_ordered_x0_y0_x1_y1(self):
        px = viewport_bbox_to_px(
            (10.0, 20.0, 30.0, 40.0),
            mediabox=(0.0, 0.0, 100.0, 100.0),
            transform=self.IDENTITY,
        )
        self.assertLess(px[0], px[2])
        self.assertLess(px[1], px[3])

    def test_rotated_page_transform_is_applied(self):
        # /Rotate 270 on a 100x200pt page: rotation_matrix maps unrotated
        # coords into the rotated frame, so the box must land inside the
        # rotated page extent rather than the unrotated one.
        rot270 = (0.0, -1.0, 1.0, 0.0, 0.0, 200.0)
        px = viewport_bbox_to_px(
            (10.0, 20.0, 30.0, 40.0),
            mediabox=(0.0, 0.0, 100.0, 200.0),
            transform=rot270,
        )
        self.assertLess(px[0], px[2])
        self.assertLess(px[1], px[3])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_viewport -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale.viewport'`

- [ ] **Step 3: Write minimal implementation**

Create `scale/viewport.py`:

```python
"""Tier 1 — the scale the PDF states in its own viewport measure dictionaries.

A CAD exporter writes /VP entries (ISO 32000-1 §12.9) so a reader's measure
tool can report real lengths. Ten of the twenty corpus sheets carry them, and
where a sheet also prints its scale the two agree on all but s13.

Two structural rules the corpus forces:

  * A viewport at 1:1 is the sheet of paper. s03, s04, s08 and s17 each have
    one spanning the whole page.
  * Viewports NEST, and the innermost containing a point governs. s06 carries
    an outer 1:146 and an inner 1:99.6; the inner is what its "SCALE 1:100"
    caption refers to.

PyMuPDF cannot index into the array (xref_get_key(xref, "VP[0]") returns null),
so the whole array comes back as one string and is split here. A regex sweeping
the raw string is NOT safe: it will happily pair one viewport's /C with
another's /BBox, which is exactly the error that produced a phantom scale
mismatch on s06 during design research.
"""
from __future__ import annotations

import re
from typing import Optional

from extraction.extractor import page_transform
from models import BBox, ScaleInfo
from scale.units import (
    PAPER_SPACE_MAX_DENOMINATOR,
    denominator_from_c,
    snap_to_standard,
)

_BBOX_RE = re.compile(r"/BBox\s*\[([-\d.\s]+)\]")
# Anchored on /X so the /A (area) and /D (distance) factors, which are both
# C 1 on every corpus sheet, can never be read as the drawing scale.
_X_FACTOR_RE = re.compile(r"/X\s*\[\s*<<[^>]*?/C\s*([-\d.eE+]+)")
_RECTILINEAR_RE = re.compile(r"/Subtype\s*/RL\b")


def split_pdf_dicts(array_text: str) -> list[str]:
    """Split a PDF array string into its top-level ``<< >>`` dictionaries.

    Depth-counted rather than regexed, so a nested /Measure never terminates
    its parent viewport early. Malformed input yields whatever completed
    cleanly rather than raising.
    """
    out: list[str] = []
    depth = 0
    start: Optional[int] = None
    i = 0
    while i < len(array_text) - 1:
        pair = array_text[i:i + 2]
        if pair == "<<":
            if depth == 0:
                start = i
            depth += 1
            i += 2
            continue
        if pair == ">>":
            depth -= 1
            i += 2
            if depth < 0:
                return out
            if depth == 0 and start is not None:
                out.append(array_text[start:i])
                start = None
            continue
        i += 1
    return out


def parse_measure_viewports(
    vp_array_text: str,
) -> list[tuple[tuple[float, float, float, float], float]]:
    """Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.

    The bbox is left in raw PDF coordinates — y-up, bottom-left origin.
    Paper-space (1:1) viewports are dropped here.
    """
    out: list[tuple[tuple[float, float, float, float], float]] = []
    for chunk in split_pdf_dicts(vp_array_text):
        if "/Measure" not in chunk or not _RECTILINEAR_RE.search(chunk):
            continue
        bbox_match = _BBOX_RE.search(chunk)
        factor_match = _X_FACTOR_RE.search(chunk)
        if not (bbox_match and factor_match):
            continue
        numbers = [float(v) for v in bbox_match.group(1).split()]
        if len(numbers) != 4:
            continue
        try:
            c = float(factor_match.group(1))
        except ValueError:
            continue
        if denominator_from_c(c) < PAPER_SPACE_MAX_DENOMINATOR:
            continue
        x0, y0, x1, y1 = numbers
        out.append(((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), c))
    return out


def viewport_bbox_to_px(
    bbox_pt_yup: tuple[float, float, float, float],
    mediabox: tuple[float, float, float, float],
    transform: tuple[float, float, float, float, float, float],
) -> BBox:
    """Convert a raw /VP bbox into 150-DPI pixel space.

    Two steps, in this order. First flip y about the mediabox, because
    xref_get_key returns PDF-native coordinates (y-up, bottom-left) while
    get_drawings() and everything downstream are y-down, top-left. Then apply
    the page transform, which carries SCALE and any /Rotate.
    """
    mx0, _my0, _mx1, my1 = mediabox
    x0 = bbox_pt_yup[0] - mx0
    x1 = bbox_pt_yup[2] - mx0
    y0 = my1 - bbox_pt_yup[3]
    y1 = my1 - bbox_pt_yup[1]

    a, b, c, d, e, f = transform
    corners = [
        (a * px + c * py + e, b * px + d * py + f)
        for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
    ]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def viewport_scales(doc, page) -> list[ScaleInfo]:
    """Every drawing scale this page's viewports state, smallest bbox first.

    Smallest-first is the nesting rule: the first viewport whose bbox contains
    a point is the innermost one, and that is the scale governing it.
    """
    try:
        kind, value = doc.xref_get_key(page.xref, "VP")
    except Exception:
        return []
    if kind != "array":
        return []

    mediabox = (page.mediabox.x0, page.mediabox.y0,
                page.mediabox.x1, page.mediabox.y1)
    transform = page_transform(page)

    out: list[ScaleInfo] = []
    for bbox_pt, c in parse_measure_viewports(value):
        denominator = denominator_from_c(c)
        out.append(ScaleInfo(
            denominator=denominator,
            source="viewport",
            bbox=viewport_bbox_to_px(bbox_pt, mediabox, transform),
            raw=f"C={c:g}",
            nominal=snap_to_standard(denominator),
        ))
    out.sort(key=lambda s: (s.bbox[2] - s.bbox[0]) * (s.bbox[3] - s.bbox[1]))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_viewport -v`
Expected: PASS, 16 tests

- [ ] **Step 5: Commit**

```bash
git add scale/viewport.py tests/test_scale_viewport.py
git commit -m "feat(scale): parse /VP measure viewports

Depth-counted dict split rather than a regex sweep -- a raw regex pairs
one viewport's /C with another's /BBox, which is how s06 appeared to
contradict its own printed scale during design research.

The /VP bbox is y-up bottom-left and is flipped about the mediabox
before page_transform."
```

---

### Task 3: Tier 2 — text parsing

**Files:**
- Create: `scale/text.py`
- Test: `tests/test_scale_text.py`

**Interfaces:**
- Consumes: `models.ScaleInfo`, `models.TextSpan`; `scale.units.snap_to_standard`, `PAPER_SPACE_MAX_DENOMINATOR`.
- Produces: `scale.text.scales_in_text(text: str) -> list[float]`, `text_scales(page_data) -> list[ScaleInfo]`.

**Deviation from the spec, deliberate:** the spec calls for joining a bare `Scale:` label span to its value span. That is dropped. On every corpus sheet the *value* span carries the `1:N` itself (s20's is `1:50  & 1:100`), so the join finds nothing the plain scan misses — and s03's `Scale:` pairs with `As Shown @ A1`, which states no ratio at all. Reinstate it only if a sheet appears that needs it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_text.py`:

```python
"""Reading a 1:N scale out of text spans.

Every string below is copied verbatim from a corpus sheet. The negations are
the important cases: two sheets tell the reader NOT to scale from the drawing,
and matching on the word "scale" would turn both into a scale annotation.
"""
import unittest

from models import PageData, TextSpan
from scale.text import scales_in_text, text_scales


def span(text, bbox=(0.0, 0.0, 10.0, 10.0)):
    return TextSpan(text=text, bbox=bbox, font="Arial", size=10.0,
                    color=0, block_no=0, line_no=0)


class TestScalesInText(unittest.TestCase):
    def test_s03_caption(self):
        self.assertEqual(scales_in_text("SCALE 1:100"), [100.0])

    def test_s06_caption_with_padding(self):
        self.assertEqual(scales_in_text("SCALE        1:100"), [100.0])

    def test_s04_paper_size_suffix(self):
        self.assertEqual(scales_in_text("1:50@A3"), [50.0])

    def test_s02_scale_bar_layer_label(self):
        self.assertEqual(scales_in_text("scale bar - metric - 1:50@A3"), [50.0])

    def test_s20_title_block_states_two_scales(self):
        self.assertEqual(scales_in_text("1:50  & 1:100"), [50.0, 100.0])

    def test_s14_negation_is_not_a_scale(self):
        self.assertEqual(scales_in_text("PLEASE DO NOT SCALE FROM THIS DRAWING"), [])

    def test_s15_negation_is_not_a_scale(self):
        self.assertEqual(scales_in_text(
            "3. DO NOT SCALE THIS DRAWING.ANY DISCREPANCIES TO BE REPORTED "
            "TO THE PROJECT CO-ORDINATOR"), [])

    def test_s03_as_shown_states_no_ratio(self):
        self.assertEqual(scales_in_text("As Shown @ A1"), [])

    def test_bare_label_states_no_ratio(self):
        self.assertEqual(scales_in_text("Scale:"), [])

    def test_one_to_one_is_not_a_drawing_scale(self):
        self.assertEqual(scales_in_text("1:1"), [])

    def test_slash_form_is_not_matched_so_dates_cannot_match(self):
        # "1/5/2024" would otherwise read as 1:5. No corpus sheet uses a
        # slash, so the separator stays a colon.
        self.assertEqual(scales_in_text("Issued 1/5/2024"), [])

    def test_room_dimensions_are_not_scales(self):
        self.assertEqual(scales_in_text("3600 x 4200"), [])

    def test_decimal_denominator_survives(self):
        # This grammar also parses stored user answers back. prompt.py accepts
        # decimals, so an integer-only pattern would reload "1:136.4" as 136.
        self.assertEqual(scales_in_text("1:136.4"), [136.4])

    def test_decimal_below_the_paper_space_floor_is_still_rejected(self):
        self.assertEqual(scales_in_text("1:1.2"), [])


class TestTextScales(unittest.TestCase):
    def test_span_bbox_is_carried_through(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("SCALE 1:100", (10.0, 20.0, 60.0, 30.0))])
        found = text_scales(page)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].bbox, (10.0, 20.0, 60.0, 30.0))

    def test_source_is_text_and_raw_is_the_span(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("SCALE 1:100")])
        found = text_scales(page)
        self.assertEqual(found[0].source, "text")
        self.assertEqual(found[0].raw, "SCALE 1:100")

    def test_nominal_is_snapped(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("1:50@A3")])
        self.assertEqual(text_scales(page)[0].nominal, 50.0)

    def test_two_scales_in_one_span_yield_two_results_sharing_a_bbox(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("1:50  & 1:100", (1.0, 2.0, 3.0, 4.0))])
        found = text_scales(page)
        self.assertEqual([f.denominator for f in found], [50.0, 100.0])
        self.assertEqual({f.bbox for f in found}, {(1.0, 2.0, 3.0, 4.0)})

    def test_page_with_no_text_yields_nothing(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0)
        self.assertEqual(text_scales(page), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_text -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale.text'`

- [ ] **Step 3: Write minimal implementation**

Create `scale/text.py`:

```python
"""Tier 2 — the scale a sheet prints as text.

Three corpus sheets carry no viewport but state a scale in words: s02
("1:50@A3"), s14 ("1:50@A1") and s20 ("1:50  & 1:100"). Two traps:

  * Two sheets print DO NOT SCALE FROM THIS DRAWING. Matching the word
    "scale" turns a warning into an annotation, so only a 1:N ratio counts.
  * The separator is a colon, never a slash. "1/5/2024" would read as 1:5,
    and no corpus sheet writes a scale with a slash.

A span keeps its own bbox, which is what binds "SCALE 1:100" printed beneath a
plan to that plan.

The denominator accepts a decimal part even though no sheet prints one. This
is the SAME grammar the store parses a user-typed scale back with, and the
prompt accepts decimals so a measured value like 1:136.4 can be recorded — an
integer-only pattern here would silently reload that as 1:136.
"""
from __future__ import annotations

import re

from models import PageData, ScaleInfo
from scale.units import PAPER_SPACE_MAX_DENOMINATOR, snap_to_standard

_SCALE_RE = re.compile(r"\b1\s*:\s*(\d{1,4}(?:\.\d+)?)\b")


def scales_in_text(text: str) -> list[float]:
    """Every 1:N denominator stated in one string, in the order written."""
    out: list[float] = []
    for match in _SCALE_RE.finditer(text):
        denominator = float(match.group(1))
        if denominator < PAPER_SPACE_MAX_DENOMINATOR:
            continue
        out.append(denominator)
    return out


def text_scales(page_data: PageData) -> list[ScaleInfo]:
    """Every scale printed on the page, each carrying its span's bbox."""
    out: list[ScaleInfo] = []
    for span in page_data.text_spans:
        for denominator in scales_in_text(span.text):
            out.append(ScaleInfo(
                denominator=denominator,
                source="text",
                bbox=span.bbox,
                raw=span.text.strip(),
                nominal=snap_to_standard(denominator),
            ))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_text -v`
Expected: PASS, 19 tests

- [ ] **Step 5: Commit**

```bash
git add scale/text.py tests/test_scale_text.py
git commit -m "feat(scale): read 1:N scales from text spans

Ratio-only matching, so the DO NOT SCALE warnings on s14 and s15 are not
read as annotations. Colon separator only, so dates cannot match."
```

---

### Task 4: Tier 4 storage

**Files:**
- Modify: `regression/corpus.py` (append after `sheet_path`, around line 45)
- Modify: `regression/ground_truth.py` (`SheetTruth`, `load_truth`, `dumps_truth`, `write_empty_truth`)
- Create: `scale/store.py`
- Test: `tests/test_scale_store.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `regression.corpus.slug_for_path(path) -> Optional[str]`; `regression.ground_truth.SheetTruth.scales: dict[int, list[dict]]`; `scale.store.StoredScale` (dataclass with `bbox: BBox`, `scale: str`), `load_stored(pdf_path: str, page_number: int) -> list[StoredScale]`, `save_stored(pdf_path: str, page_number: int, entries: list[StoredScale]) -> None`, `match_stored(region_bbox: BBox, stored: list[StoredScale]) -> Optional[StoredScale]`. Stored values are the literal string the user typed, e.g. `"1:100"`.

**Why entries are keyed by geometry, not by `region_id`:** region ids are ordinal — `layout/segmenter.py:266` numbers them `region_{i:04d}` over a sorted box list — so any change to segmentation renumbers them. A scale stored against `region_0002` would then silently attach to a different drawing and, because stored values sit at the top of the ladder, **override the correct viewport scale**. This is the same hazard `tests/ground_truth/` already solves for detections by matching on type + IoU rather than on entity id. Stored scales carry the region bbox and match at IoU ≥ 0.5, reusing `regression.matching.iou`.

**Why the ground-truth change is load-bearing:** `dumps_truth` rebuilds the file from a fixed set of keys. A `scales` block added to the JSON but not to the dataclass would be **silently erased** the next time `tools/review.py` writes verdicts for that sheet. `SheetTruth` must carry it and `dumps_truth` must re-emit it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_store.py`:

```python
"""Persistence of a user-supplied scale.

Two back-ends, mirroring the split the repo already uses for verdicts versus
caches: a corpus sheet writes into its committed ground truth, anything else
into a gitignored sidecar. Both are read before the user is ever prompted.
"""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as corpus
import regression.ground_truth as gt
from regression.ground_truth import SheetTruth, dumps_truth, load_truth
from scale.store import StoredScale, load_stored, match_stored, save_stored


class TestGroundTruthCarriesScales(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = gt.TRUTH_DIR
        gt.TRUTH_DIR = Path(self.tmp.name)

    def tearDown(self):
        gt.TRUTH_DIR = self._saved
        self.tmp.cleanup()

    def test_scales_survive_a_load_dump_round_trip(self):
        (gt.TRUTH_DIR / "s09.json").write_text(json.dumps({
            "sheet": "s09", "pdf_sha256": "abc", "reviewed": None,
            "scales": {"1": [{"bbox": [10.0, 20.0, 30.0, 40.0],
                              "scale": "1:100"}]},
            "pages": {},
        }, indent=2) + "\n", encoding="utf-8")
        truth = load_truth("s09")
        self.assertEqual(truth.scales,
                         {1: [{"bbox": [10.0, 20.0, 30.0, 40.0],
                               "scale": "1:100"}]})
        self.assertIn("1:100", dumps_truth(truth))

    def test_a_stored_bbox_stays_on_one_line_in_the_diff(self):
        truth = SheetTruth(slug="s09", pdf_sha256="abc", scales={
            1: [{"bbox": [10.0, 20.0, 30.0, 40.0], "scale": "1:100"}]})
        self.assertIn("[10.0, 20.0, 30.0, 40.0]", dumps_truth(truth))

    def test_a_sheet_without_scales_round_trips_byte_identically(self):
        original = json.dumps({
            "sheet": "s01", "pdf_sha256": "abc", "reviewed": None, "pages": {},
        }, indent=2) + "\n"
        (gt.TRUTH_DIR / "s01.json").write_text(original, encoding="utf-8")
        self.assertEqual(dumps_truth(load_truth("s01")), original)

    def test_empty_scales_block_is_omitted_from_output(self):
        truth = SheetTruth(slug="s01", pdf_sha256="abc")
        self.assertNotIn("scales", dumps_truth(truth))


class TestSlugForPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "sheets" / "s09-floor-plan.pdf").write_bytes(b"%PDF-1.4")
        (root / "MANIFEST.json").write_text(json.dumps(
            {"sheets": [{"slug": "s09", "file": "s09-floor-plan.pdf"}]}),
            encoding="utf-8")
        self._saved = (corpus.FIXTURES_DIR, corpus.SHEETS_DIR, corpus.MANIFEST_PATH)
        corpus.FIXTURES_DIR = root
        corpus.SHEETS_DIR = root / "sheets"
        corpus.MANIFEST_PATH = root / "MANIFEST.json"

    def tearDown(self):
        (corpus.FIXTURES_DIR, corpus.SHEETS_DIR,
         corpus.MANIFEST_PATH) = self._saved
        self.tmp.cleanup()

    def test_corpus_sheet_resolves_to_its_slug(self):
        path = corpus.SHEETS_DIR / "s09-floor-plan.pdf"
        self.assertEqual(corpus.slug_for_path(path), "s09")

    def test_outside_pdf_has_no_slug(self):
        self.assertIsNone(corpus.slug_for_path(Path(self.tmp.name) / "other.pdf"))


class TestLocalCacheBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = Path(self.tmp.name) / "drawing.pdf"
        self.pdf.write_bytes(b"%PDF-1.4")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_cache_reads_as_empty(self):
        self.assertEqual(load_stored(str(self.pdf), 1), [])

    def test_saved_entries_read_back(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        found = load_stored(str(self.pdf), 1)
        self.assertEqual([(e.bbox, e.scale) for e in found],
                         [((0.0, 0.0, 10.0, 10.0), "1:50")])

    def test_pages_are_kept_apart(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 2, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:100")])
        self.assertEqual(load_stored(str(self.pdf), 1)[0].scale, "1:50")
        self.assertEqual(load_stored(str(self.pdf), 2)[0].scale, "1:100")

    def test_save_appends_a_disjoint_region(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 1, [StoredScale((50.0, 50.0, 60.0, 60.0), "1:100")])
        self.assertEqual(len(load_stored(str(self.pdf), 1)), 2)

    def test_save_replaces_an_overlapping_region_rather_than_duplicating(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.2, 10.2), "1:100")])
        found = load_stored(str(self.pdf), 1)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].scale, "1:100")

    def test_cache_lands_in_a_gitignored_sidecar_dir(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        self.assertTrue((self.pdf.parent / ".scale_cache").is_dir())

    def test_corrupt_cache_reads_as_empty_rather_than_raising(self):
        cache = self.pdf.parent / ".scale_cache"
        cache.mkdir()
        (cache / "drawing_p01.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(load_stored(str(self.pdf), 1), [])


class TestMatchStored(unittest.TestCase):
    """Matching is geometric because region ids are ordinal.

    layout/segmenter.py numbers regions region_0000, region_0001, ... over a
    sorted box list, so any change to segmentation renumbers them. A stored
    scale keyed by id would then attach to a different drawing and, since
    stored values sit at the top of the ladder, override the correct one.
    """

    def test_the_same_region_matches(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertEqual(match_stored((0.0, 0.0, 100.0, 100.0), stored).scale, "1:50")

    def test_a_slightly_shifted_region_still_matches(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNotNone(match_stored((2.0, 2.0, 102.0, 102.0), stored))

    def test_a_different_drawing_does_not_match(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNone(match_stored((500.0, 500.0, 600.0, 600.0), stored))

    def test_a_region_overlapping_below_the_threshold_does_not_match(self):
        # IoU 0.25 -- half-overlap in each axis. Renumbering must not be able
        # to smuggle a stale scale onto a neighbouring drawing.
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNone(match_stored((50.0, 50.0, 150.0, 150.0), stored))

    def test_the_best_overlap_wins_when_several_could_match(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50"),
                  StoredScale((0.0, 0.0, 104.0, 104.0), "1:100")]
        self.assertEqual(match_stored((0.0, 0.0, 103.0, 103.0), stored).scale,
                         "1:100")

    def test_an_empty_store_matches_nothing(self):
        self.assertIsNone(match_stored((0.0, 0.0, 100.0, 100.0), []))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_store -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale.store'`

- [ ] **Step 3: Write minimal implementation**

Append to `regression/corpus.py`:

```python
def slug_for_path(path) -> str | None:
    """The corpus slug for a PDF path, or None if it is not a corpus sheet.

    Compared by resolved path so a relative argument and an absolute one agree.
    """
    target = Path(path).resolve()
    if target.parent != SHEETS_DIR.resolve():
        return None
    for entry in manifest_sheets():
        if entry.get("file") == target.name:
            return entry.get("slug")
    return None
```

In `regression/ground_truth.py`, add the field to `SheetTruth`:

```python
@dataclass
class SheetTruth:
    slug: str
    pdf_sha256: str | None = None
    reviewed: str | None = None
    pages: dict[int, PageTruth] = field(default_factory=dict)
    # page number -> [{"bbox": [...], "scale": "1:100"}, ...].
    #
    # Keyed by the region's geometry, not its id: region ids are ordinal and
    # renumber whenever segmentation changes, and a stored scale outranks
    # every detected one, so a mis-attached entry would override a correct
    # reading. Same reason the verdict lists match on bbox rather than on
    # entity id. Carried through load and dump so tools/review.py cannot
    # erase it when it rewrites a sheet's verdicts.
    scales: dict[int, list[dict]] = field(default_factory=dict)
```

In `load_truth`, before the `return`:

```python
    scales = {
        int(number): [
            {"bbox": [float(v) for v in item["bbox"]],
             "scale": str(item["scale"])}
            for item in entries
            if isinstance(item.get("bbox"), list) and len(item["bbox"]) == 4
            and item.get("scale")
        ]
        for number, entries in (payload.get("scales") or {}).items()
    }
```

and pass `scales=scales` to the `SheetTruth(...)` constructor call.

In `dumps_truth`, replace the `json.dumps({...})` payload construction with:

```python
    payload: dict = {"sheet": truth.slug,
                     "pdf_sha256": truth.pdf_sha256,
                     "reviewed": truth.reviewed}
    # Omitted when empty so every existing ground-truth file re-serializes
    # byte-identically — the round-trip guarantee dump_truth documents.
    if truth.scales:
        payload["scales"] = {
            str(number): [
                # Same one-line bbox treatment verdict items get, so a
                # re-segmentation shows as one changed line, not four.
                {"bbox": _inline_number_array(item["bbox"], inline),
                 "scale": item["scale"]}
                for item in truth.scales[number]
            ]
            for number in sorted(truth.scales)
        }
    payload["pages"] = pages
    text = json.dumps(payload, indent=2)
```

Create `scale/store.py`:

```python
"""Tier 4 persistence — where a scale the user typed is kept.

Two back-ends, mirroring the split this repo already uses for verdicts versus
caches:

  * A corpus sheet writes into tests/ground_truth/<slug>.json, which is
    committed. That is the only place a scale survives a fresh clone, and an
    unattended regress sweep needs it to.
  * Anything else writes a gitignored .scale_cache/ sidecar beside the PDF,
    exactly as gemini/region_cache.py does for classifications.

Values are stored as the literal string the user typed ("1:100") and parsed
back with the tier-2 reader, so there is one scale grammar rather than two.

Entries are keyed by GEOMETRY, never by region_id. Region ids are ordinal
(layout/segmenter.py numbers them over a sorted box list), so a change to
segmentation renumbers them — and a stored scale sits at the TOP of the
resolution ladder, so a mis-attached one would override a correct viewport
reading rather than merely being ignored. tests/ground_truth/ already solves
exactly this for detections by matching on type + IoU instead of entity id;
this follows it, reusing regression.matching.iou.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from models import BBox
from regression import corpus
from regression.ground_truth import dump_truth, load_truth
from regression.matching import iou

CACHE_DIR_NAME = ".scale_cache"

# The same threshold tests/ground_truth/ matches detections at.
STORED_MATCH_MIN_IOU = 0.5


@dataclass
class StoredScale:
    bbox: BBox        # the region this scale was entered for, 150-DPI px
    scale: str        # the literal string the user typed, e.g. "1:100"


def _cache_file(pdf_path: str, page_number: int) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}.json"


def _from_dicts(raw) -> list[StoredScale]:
    out: list[StoredScale] = []
    for item in raw or []:
        bbox = item.get("bbox")
        scale = item.get("scale")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or not scale:
            continue
        out.append(StoredScale(tuple(float(v) for v in bbox), str(scale)))
    return out


def _to_dicts(entries: list[StoredScale]) -> list[dict]:
    return [{"bbox": [float(v) for v in e.bbox], "scale": e.scale}
            for e in entries]


def match_stored(
    region_bbox: BBox, stored: list[StoredScale]
) -> Optional[StoredScale]:
    """The stored entry for this region, matched geometrically. Best overlap
    wins; anything under STORED_MATCH_MIN_IOU is a different drawing."""
    best: Optional[StoredScale] = None
    best_iou = STORED_MATCH_MIN_IOU
    for entry in stored:
        overlap = iou(region_bbox, entry.bbox)
        if overlap >= best_iou:
            best, best_iou = entry, overlap
    return best


def load_stored(pdf_path: str, page_number: int) -> list[StoredScale]:
    """Stored scales for one page.

    A missing or unreadable store reads as empty — an absent scale is a prompt,
    never an error.
    """
    slug = corpus.slug_for_path(pdf_path)
    if slug is not None:
        try:
            return _from_dicts(load_truth(slug).scales.get(page_number, []))
        except Exception:
            return []

    target = _cache_file(pdf_path, page_number)
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return _from_dicts(payload.get("scales"))
    except Exception:
        return []


def _merge(existing: list[StoredScale],
           incoming: list[StoredScale]) -> list[StoredScale]:
    """Add entries, replacing any that describe the same region.

    Overlap-based rather than equality-based: the same plan re-segmented
    shifts its box by a pixel or two, and appending would leave two entries
    competing for one drawing.
    """
    merged = list(existing)
    for entry in incoming:
        previous = match_stored(entry.bbox, merged)
        if previous is not None:
            merged[merged.index(previous)] = entry
        else:
            merged.append(entry)
    return merged


def save_stored(
    pdf_path: str, page_number: int, entries: list[StoredScale]
) -> None:
    """Merge entries into the store for one page. Never touches other pages."""
    if not entries:
        return

    merged = _merge(load_stored(pdf_path, page_number), entries)

    slug = corpus.slug_for_path(pdf_path)
    if slug is not None:
        truth = load_truth(slug)
        truth.scales[page_number] = _to_dicts(merged)
        dump_truth(truth)
        return

    target = _cache_file(pdf_path, page_number)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"page_number": page_number, "scales": _to_dicts(merged)},
                   indent=2),
        encoding="utf-8",
    )
```

Add to `.gitignore`, after the `.regions_cache/` line:

```
.scale_cache/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_store tests.test_ground_truth -v`
Expected: PASS. The existing ground-truth tests must still pass — the round-trip guarantee is what protects committed verdicts.

- [ ] **Step 5: Commit**

```bash
git add regression/corpus.py regression/ground_truth.py scale/store.py tests/test_scale_store.py .gitignore
git commit -m "feat(scale): persist user-supplied scales

Corpus sheets store into committed ground truth so an unattended sweep
can reuse them; other PDFs get a gitignored sidecar.

SheetTruth carries the block explicitly -- dumps_truth rebuilds files
from a fixed key set, so a scales block it did not know about would be
erased the next time review.py wrote verdicts for that sheet."
```

---

### Task 5: Tier 4 prompt

**Files:**
- Create: `scale/prompt.py`
- Test: `tests/test_scale_prompt.py`

**Interfaces:**
- Consumes: `models.ScaleInfo`; `scale.text.scales_in_text`.
- Produces: `scale.prompt.can_prompt(stream=None) -> bool`, `parse_answer(answer: str) -> Optional[float]`, `prompt_for_scale(region_id: str, crop_hint: str, input_fn=input, output_fn=print) -> Optional[str]` returning the literal string entered (e.g. `"1:100"`) or `None` if skipped.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_prompt.py`:

```python
"""The interactive scale prompt.

The prompt must never run in batch_extract (ProcessPoolExecutor, no tty) or
tools/regress.py (unattended sweep of 20 sheets), so the tty gate is the
load-bearing behaviour here.
"""
import io
import unittest

from scale.prompt import can_prompt, parse_answer, prompt_for_scale


class FakeStream(io.StringIO):
    def __init__(self, tty):
        super().__init__()
        self._tty = tty

    def isatty(self):
        return self._tty


class TestCanPrompt(unittest.TestCase):
    def test_tty_allows_prompting(self):
        self.assertTrue(can_prompt(FakeStream(tty=True)))

    def test_pipe_forbids_prompting(self):
        self.assertFalse(can_prompt(FakeStream(tty=False)))

    def test_stream_without_isatty_forbids_prompting(self):
        self.assertFalse(can_prompt(object()))


class TestParseAnswer(unittest.TestCase):
    def test_full_ratio(self):
        self.assertEqual(parse_answer("1:100"), 100.0)

    def test_bare_denominator(self):
        self.assertEqual(parse_answer("100"), 100.0)

    def test_whitespace_is_tolerated(self):
        self.assertEqual(parse_answer("  1 : 50 "), 50.0)

    def test_empty_answer_is_a_skip(self):
        self.assertIsNone(parse_answer(""))

    def test_nonsense_is_a_skip(self):
        self.assertIsNone(parse_answer("dunno"))

    def test_one_to_one_is_rejected(self):
        self.assertIsNone(parse_answer("1:1"))


class TestPromptForScale(unittest.TestCase):
    def test_returns_the_normalised_ratio(self):
        answers = iter(["1:50"])
        result = prompt_for_scale("region_0002", "crop.png",
                                  input_fn=lambda _: next(answers),
                                  output_fn=lambda *_: None)
        self.assertEqual(result, "1:50")

    def test_bare_number_is_normalised_to_a_ratio(self):
        answers = iter(["100"])
        result = prompt_for_scale("region_0002", "crop.png",
                                  input_fn=lambda _: next(answers),
                                  output_fn=lambda *_: None)
        self.assertEqual(result, "1:100")

    def test_empty_answer_skips_without_reprompting(self):
        calls = []

        def record(_):
            calls.append(1)
            return ""

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=record,
                                           output_fn=lambda *_: None))
        self.assertEqual(len(calls), 1)

    def test_the_crop_path_is_shown_so_the_user_can_look(self):
        shown = []
        prompt_for_scale("region_0002", "pages/page_01/region_crops/x.png",
                         input_fn=lambda _: "",
                         output_fn=lambda *a: shown.append(" ".join(str(x) for x in a)))
        self.assertTrue(any("region_crops" in line for line in shown))

    def test_eof_is_a_skip_not_a_crash(self):
        def raise_eof(_):
            raise EOFError

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=raise_eof,
                                           output_fn=lambda *_: None))

    def test_interrupt_is_a_skip_not_a_crash(self):
        def raise_interrupt(_):
            raise KeyboardInterrupt

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=raise_interrupt,
                                           output_fn=lambda *_: None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_prompt -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale.prompt'`

- [ ] **Step 3: Write minimal implementation**

Create `scale/prompt.py`:

```python
"""Tier 4 input — ask the user, but only when someone is there to answer.

batch_extract.py runs five sheets in parallel through a ProcessPoolExecutor
with no tty, and tools/regress.py sweeps twenty sheets unattended. A blocking
prompt would hang both, so every path here is gated on a real terminal and
every failure mode (EOF, interrupt, nonsense) is a skip rather than a retry.
"""
from __future__ import annotations

import re
import sys
from typing import Optional

from scale.units import PAPER_SPACE_MAX_DENOMINATOR, format_scale

_ANSWER_RE = re.compile(r"^\s*(?:1\s*:\s*)?(\d{1,4}(?:\.\d+)?)\s*$")


def can_prompt(stream=None) -> bool:
    """True only when stdin is a real terminal."""
    stream = sys.stdin if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    if isatty is None:
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


def parse_answer(answer: str) -> Optional[float]:
    """The denominator in an answer, accepting "1:100" or "100". None to skip."""
    match = _ANSWER_RE.match(answer or "")
    if not match:
        return None
    denominator = float(match.group(1))
    if denominator < PAPER_SPACE_MAX_DENOMINATOR:
        return None
    return denominator


def prompt_for_scale(
    region_id: str,
    crop_hint: str,
    input_fn=input,
    output_fn=print,
) -> Optional[str]:
    """Ask once for one region's scale. Returns "1:100", or None if skipped.

    Asked once, not until valid: a user who does not know the scale must be
    able to move on, and the region simply stays unresolved.
    """
    output_fn(f"No scale found for {region_id}.")
    output_fn(f"  Look at: {crop_hint}")
    try:
        answer = input_fn("  Scale (e.g. 1:100, blank to skip): ")
    except (EOFError, KeyboardInterrupt):
        return None
    denominator = parse_answer(answer)
    if denominator is None:
        return None
    return format_scale(denominator)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_prompt -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Commit**

```bash
git add scale/prompt.py tests/test_scale_prompt.py
git commit -m "feat(scale): tty-gated prompt for an unresolved scale

Asked once, never retried, and every failure mode is a skip -- batch and
regress runs have no tty and must never block."
```

---

### Task 6: The resolver

**Files:**
- Create: `scale/resolver.py`
- Modify: `scale/__init__.py` (re-export `resolve_page_scales`, `PageScales`)
- Test: `tests/test_scale_resolver.py`

**Interfaces:**
- Consumes: `models.ScaleInfo`, `models.Region`, `models.PageData`; `scale.viewport.viewport_scales`; `scale.text.text_scales`, `scales_in_text`; `scale.store.StoredScale`, `match_stored`, `save_stored`; `scale.prompt.can_prompt`, `prompt_for_scale`; `scale.units.snap_to_standard`.
- Produces: `scale.resolver.PageScales` (dataclass with `by_region: dict[str, ScaleInfo]`, `page_scale: Optional[ScaleInfo]`, `warnings: list[dict]`), `binding_texts(region, texts) -> list[ScaleInfo]`, `bind_scale(region, viewports, texts) -> Optional[ScaleInfo]`, `resolve_page_scales(page_data, regions, viewports, stored, pdf_path=None, crop_fn=None, allow_prompt=False) -> PageScales`. `crop_fn` renders a region crop on demand and returns its path — the resolver never assumes one already exists.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_resolver.py`:

```python
"""The resolution ladder and how a scale binds to a floor plan.

Region binding is the whole point of scenario 3: one sheet, several plans,
different scales. s17 carries 1:50, four 1:100s, 1:500 and 1:1250 at once.
"""
import unittest

from models import PageData, Region, ScaleInfo, TextSpan
from scale.resolver import bind_scale, binding_texts, resolve_page_scales
from scale.store import StoredScale


def region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


def viewport(denominator, bbox):
    return ScaleInfo(denominator=denominator, source="viewport", bbox=bbox,
                     raw=f"C={denominator:g}", nominal=denominator)


def text(denominator, bbox):
    return ScaleInfo(denominator=denominator, source="text", bbox=bbox,
                     raw=f"SCALE 1:{denominator:g}", nominal=denominator)


def span(text_value, bbox):
    return TextSpan(text=text_value, bbox=bbox, font="Arial", size=10.0,
                    color=0, block_no=0, line_no=0)


class TestBindScale(unittest.TestCase):
    def test_viewport_containing_the_region_centroid_wins(self):
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(50.0, (0.0, 0.0, 100.0, 100.0))], [])
        self.assertEqual(found.denominator, 50.0)

    def test_innermost_viewport_wins_when_they_nest(self):
        # Passed smallest-first, as viewport_scales returns them.
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(100.0, (0.0, 0.0, 50.0, 50.0)),
                            viewport(146.0, (0.0, 0.0, 200.0, 200.0))], [])
        self.assertEqual(found.denominator, 100.0)

    def test_viewport_not_containing_the_centroid_does_not_bind(self):
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(50.0, (500.0, 500.0, 600.0, 600.0))], [])
        self.assertIsNone(found)

    def test_text_inside_the_region_binds_when_no_viewport_does(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(50.0, (10.0, 80.0, 40.0, 90.0))])
        self.assertEqual(found.denominator, 50.0)
        self.assertEqual(found.source, "text")

    def test_text_just_below_the_region_binds(self):
        # Captions are drawn beneath the plan, outside the region box.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 105.0, 40.0, 115.0))])
        self.assertEqual(found.denominator, 100.0)

    def test_a_caption_191px_below_still_binds(self):
        # Measured on s13, whose SCALE 1:100 sits 191px below its viewport.
        # This is the gap that makes the corpus's one conflict detectable.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 291.0, 40.0, 301.0))])
        self.assertEqual(found.denominator, 100.0)

    def test_a_caption_beyond_reach_does_not_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 400.0, 40.0, 410.0))])
        self.assertIsNone(found)

    def test_far_away_text_does_not_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 900.0, 40.0, 910.0))])
        self.assertIsNone(found)

    def test_viewport_beats_text_when_both_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertEqual(found.denominator, 136.4)

    def test_disagreement_beyond_tolerance_records_a_conflict(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertIsNotNone(found.conflict)
        self.assertIn("1:100", found.conflict)

    def test_agreement_within_tolerance_records_no_conflict(self):
        # s06: viewport 99.6, printed 1:100.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(99.6, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertIsNone(found.conflict)


class TestBindingTexts(unittest.TestCase):
    def test_returns_every_candidate_nearest_first(self):
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (10.0, 140.0, 40.0, 150.0)),
                               text(50.0, (10.0, 105.0, 40.0, 115.0))])
        self.assertEqual([f.denominator for f in found], [50.0, 100.0])

    def test_excludes_candidates_out_of_reach(self):
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (10.0, 900.0, 40.0, 910.0))])
        self.assertEqual(found, [])

    def test_excludes_candidates_with_no_horizontal_overlap(self):
        # A caption beside a plan belongs to its neighbour, not to this one.
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (500.0, 105.0, 540.0, 115.0))])
        self.assertEqual(found, [])


class TestResolvePageScales(unittest.TestCase):
    def blank_page(self, spans=()):
        return PageData(page_number=1, width_px=200.0, height_px=200.0,
                        text_spans=list(spans))

    def test_stored_value_beats_every_detected_tier(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")],
        )
        self.assertEqual(result.by_region["region_0000"].denominator, 20.0)
        self.assertEqual(result.by_region["region_0000"].source, "user")

    def test_unresolved_region_emits_a_warning(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertEqual([w["warning_code"] for w in result.warnings],
                         ["SCALE_UNRESOLVED"])

    def test_only_floor_plan_regions_are_bound(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0), "elevation")],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertEqual(result.by_region, {})

    def test_conflict_emits_a_warning(self):
        page = self.blank_page([span("SCALE 1:100", (10.0, 50.0, 40.0, 60.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIn("SCALE_SOURCE_CONFLICT",
                      [w["warning_code"] for w in result.warnings])

    def test_sole_page_candidate_binds_a_region_it_does_not_geometrically_reach(self):
        page = self.blank_page([span("1:50@A3", (900.0, 900.0, 950.0, 910.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 50.0)

    def test_two_unbindable_candidates_warn_rather_than_guess(self):
        page = self.blank_page([span("1:50  & 1:100", (900.0, 900.0, 950.0, 910.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("SCALE_MULTIPLE_UNBOUND",
                      [w["warning_code"] for w in result.warnings])

    def test_page_scale_is_reported_when_there_are_no_regions(self):
        page = self.blank_page([span("1:50@A3", (10.0, 10.0, 60.0, 20.0))])
        result = resolve_page_scales(page_data=page, regions=[],
                                     viewports=[], stored=[])
        self.assertEqual(result.page_scale.denominator, 50.0)

    def test_a_multi_scale_sheet_has_no_page_scale(self):
        # s17 states 1:50, 1:100, 1:500 and 1:1250 at once. No single number
        # describes the sheet, so summary.json must not publish one.
        result = resolve_page_scales(
            page_data=self.blank_page(), regions=[],
            viewports=[viewport(50.0, (0.0, 0.0, 50.0, 50.0)),
                       viewport(100.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIsNone(result.page_scale)

    def test_two_viewports_of_the_same_scale_yield_one_page_scale(self):
        # The REAL floats from s04's two 1:50 viewports. CAD never writes a
        # scale as the same float twice, so 100.0/100.0 would not test this.
        result = resolve_page_scales(
            page_data=self.blank_page(), regions=[],
            viewports=[viewport(49.995, (0.0, 0.0, 50.0, 50.0)),
                       viewport(50.001, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIsNotNone(result.page_scale)

    def test_s04s_real_floats_do_not_warn_about_multiple_scales(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (10.0, 10.0, 40.0, 40.0))],
            viewports=[viewport(49.995, (0.0, 0.0, 50.0, 50.0)),
                       viewport(50.001, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertNotIn("SCALE_MULTIPLE_UNBOUND",
                         [w["warning_code"] for w in result.warnings])

    def test_two_captions_disagreeing_over_one_plan_resolve_to_nothing(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("SCALE_MULTIPLE_UNBOUND",
                      [w["warning_code"] for w in result.warnings])

    def test_ambiguity_is_reported_once_not_twice(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        codes = [w["warning_code"] for w in result.warnings]
        self.assertEqual(codes.count("SCALE_MULTIPLE_UNBOUND"), 1)

    def test_repeated_captions_of_the_same_scale_are_not_ambiguous(self):
        # s03 prints SCALE 1:100 under every plan; agreement is not conflict.
        page = self.blank_page([span("SCALE 1:100", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (50.0, 105.0, 80.0, 115.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 100.0)

    def test_viewport_binding_overrides_text_ambiguity(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 50.0)

    def test_stored_decimal_scale_round_trips_exactly(self):
        # prompt.py accepts decimals; the stored string must reload unchanged.
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:136.4")])
        self.assertEqual(result.by_region["region_0000"].denominator, 136.4)

    def test_crop_is_rendered_on_demand_before_prompting(self):
        from unittest import mock
        rendered = []
        with mock.patch("scale.resolver.can_prompt", return_value=True), \
             mock.patch("scale.resolver.prompt_for_scale", return_value="1:100"):
            resolve_page_scales(
                page_data=self.blank_page(),
                regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
                viewports=[], stored=[],
                crop_fn=lambda r: rendered.append(r.region_id) or "crop.png",
                allow_prompt=True)
        self.assertEqual(rendered, ["region_0000"])

    def test_a_crop_that_cannot_be_rendered_still_prompts(self):
        from unittest import mock

        def boom(_region):
            raise OSError("cannot render")

        with mock.patch("scale.resolver.can_prompt", return_value=True), \
             mock.patch("scale.resolver.prompt_for_scale",
                        return_value=None) as ask:
            result = resolve_page_scales(
                page_data=self.blank_page(),
                regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
                viewports=[], stored=[], crop_fn=boom, allow_prompt=True)
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("no crop available", ask.call_args[0][1])

    def test_a_stored_scale_for_a_different_drawing_does_not_apply(self):
        """The renumbering hazard, end to end.

        A scale stored against what used to be region_0000 must not attach to
        a re-segmented region_0000 covering a different drawing — stored
        values outrank detected ones, so this would override a correct
        viewport reading, not merely add a wrong one.
        """
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (500.0, 500.0, 600.0, 600.0))],
            viewports=[viewport(100.0, (400.0, 400.0, 700.0, 700.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")])
        self.assertEqual(result.by_region["region_0000"].denominator, 100.0)
        self.assertEqual(result.by_region["region_0000"].source, "viewport")

    def test_a_stored_scale_survives_a_small_region_shift(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0009", (2.0, 2.0, 102.0, 102.0))],
            viewports=[viewport(100.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")])
        self.assertEqual(result.by_region["region_0009"].denominator, 20.0)
        self.assertEqual(result.by_region["region_0009"].source, "user")

    def test_every_warning_carries_the_page_number(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertTrue(all(w["page_number"] == 1 for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_resolver -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scale.resolver'`

- [ ] **Step 3: Write minimal implementation**

Create `scale/resolver.py`:

```python
"""The resolution ladder, and how a scale binds to a floor plan.

Binding is what makes scenario 3 work: s17 carries 1:50, four 1:100s, 1:500
and 1:1250 on one sheet, and each is only meaningful against the drawing it
covers. Both parsing tiers carry a bbox, so binding is geometric and needs no
model call.

Order, first hit wins: stored, viewport, text, sole page-level candidate,
prompt. Where viewport and text both bind and disagree, the viewport wins and
the loser is recorded — /Measure describes the PDF as it is, the caption
describes what was intended, and on s13 those differ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from models import PageData, Region, ScaleInfo
from scale.prompt import can_prompt, prompt_for_scale
from scale.store import StoredScale, match_stored, save_stored
from scale.text import scales_in_text, text_scales
from scale.units import (
    AGREEMENT_TOLERANCE, canonical_denominators, format_scale, snap_to_standard,
)

# A caption is drawn beneath its plan, outside the viewport that measures it.
# Measured against each sheet's own measuring viewport: s03's SCALE 1:50 sits
# 60px below, s13's SCALE 1:100 sits 191px below. 240px (1.6in at 150 DPI,
# ~41mm on the sheet) clears both with margin and is still far shorter than any
# plan, so a caption cannot reach past its own drawing to the one above.
#
# Set from BOTH measurements deliberately. At 160 the s13 caption falls out of
# reach, and the one viewport/text conflict in the corpus stops being detected.
CAPTION_REACH_PX = 240.0

@dataclass
class PageScales:
    by_region: dict[str, ScaleInfo] = field(default_factory=dict)
    page_scale: Optional[ScaleInfo] = None
    warnings: list[dict] = field(default_factory=list)


def _centroid(bbox) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _contains(outer, x: float, y: float) -> bool:
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _caption_distance(region_bbox, span_bbox) -> Optional[float]:
    """How far a text span sits from a region, or None if it is not near it.

    Horizontal overlap is required: a caption belongs to the plan above it,
    not to one beside it.
    """
    if span_bbox[2] < region_bbox[0] or span_bbox[0] > region_bbox[2]:
        return None
    cx, cy = _centroid(span_bbox)
    if _contains(region_bbox, cx, cy):
        return 0.0
    below = span_bbox[1] - region_bbox[3]
    if 0.0 <= below <= CAPTION_REACH_PX:
        return below
    return None


def binding_texts(region: Region, texts: list[ScaleInfo]) -> list[ScaleInfo]:
    """Every text scale near enough to this region to be about it, nearest first.

    Exposed separately from bind_scale so the resolver can see when two
    DIFFERENT denominators both reach one plan. Picking the nearest of those
    silently would be a guess dressed as a measurement.
    """
    scored: list[tuple[float, ScaleInfo]] = []
    for candidate in texts:
        if candidate.bbox is None:
            continue
        distance = _caption_distance(region.bbox, candidate.bbox)
        if distance is None:
            continue
        scored.append((distance, candidate))
    scored.sort(key=lambda pair: pair[0])
    return [candidate for _distance, candidate in scored]


def bind_scale(
    region: Region,
    viewports: list[ScaleInfo],
    texts: list[ScaleInfo],
) -> Optional[ScaleInfo]:
    """The scale governing one region, or None.

    `viewports` must arrive smallest-bbox-first, which is how
    viewport.viewport_scales returns them — that ordering IS the nesting rule.
    """
    cx, cy = _centroid(region.bbox)

    chosen: Optional[ScaleInfo] = None
    for candidate in viewports:
        if candidate.bbox is not None and _contains(candidate.bbox, cx, cy):
            chosen = candidate
            break

    nearby = binding_texts(region, texts)
    nearest_text = nearby[0] if nearby else None

    if chosen is None:
        return nearest_text

    if (nearest_text is not None
            and nearest_text.denominator is not None
            and chosen.denominator is not None
            and abs(nearest_text.denominator - chosen.denominator)
            > AGREEMENT_TOLERANCE * chosen.denominator):
        return ScaleInfo(
            denominator=chosen.denominator,
            source=chosen.source,
            bbox=chosen.bbox,
            raw=chosen.raw,
            nominal=chosen.nominal,
            conflict=f"text nearby says {format_scale(nearest_text.denominator)}",
        )
    return chosen


def _stored_info(entry: str) -> Optional[ScaleInfo]:
    found = scales_in_text(entry)
    if not found:
        return None
    return ScaleInfo(denominator=found[0], source="user", raw=entry,
                     nominal=snap_to_standard(found[0]))


def resolve_page_scales(
    page_data: PageData,
    regions: list[Region],
    viewports: list[ScaleInfo],
    stored: list[StoredScale],
    pdf_path: Optional[str] = None,
    crop_fn: Optional[Callable[[Region], Optional[str]]] = None,
    allow_prompt: bool = False,
) -> PageScales:
    """Resolve a scale for every floor-plan region on one page."""
    result = PageScales()
    page_number = page_data.page_number

    def warn(code: str, severity: str, message: str) -> None:
        result.warnings.append({"page_number": page_number,
                                "warning_code": code,
                                "severity": severity,
                                "message": message})

    texts = text_scales(page_data)

    # The sheet-level fallback: one distinct scale stated anywhere, with no
    # geometry tying it to a plan. s02 and s14 resolve here.
    #
    # Clustered, not counted as raw floats — s04's two 1:50 viewports measure
    # 49.995 and 50.001, which as distinct floats would make a single-scale
    # sheet look multi-scale.
    distinct = canonical_denominators(
        info.denominator for info in list(viewports) + texts
        if info.denominator is not None)
    sole_candidate: Optional[ScaleInfo] = None
    if len(distinct) == 1:
        sole_candidate = (viewports + texts)[0]
    # page_scale is only ever set when the sheet states ONE scale. A sheet
    # carrying several has no scale "as a whole" — s17 states 1:50, 1:100,
    # 1:500 and 1:1250 at once, and picking any of them for summary.json
    # would publish a number that is wrong for most of the sheet.
    result.page_scale = sole_candidate

    floor_plans = [r for r in regions if r.region_type == "floor_plan"]
    unresolved: list[str] = []
    newly_entered: list[StoredScale] = []

    for region in floor_plans:
        # Matched on geometry, not on region_id: ids are ordinal and renumber
        # when segmentation changes, and a stored value outranks every
        # detected one, so a mis-attached entry would override a correct
        # viewport reading rather than merely being ignored.
        entry = match_stored(region.bbox, stored)
        if entry is not None:
            info = _stored_info(entry.scale)
            if info is not None:
                result.by_region[region.region_id] = info
                continue

        info = bind_scale(region, viewports, texts)

        # Two different printed scales both reaching one plan is ambiguity, not
        # a near miss — refuse it rather than taking whichever sits closer. A
        # viewport binding overrides this, since it beats text outright.
        ambiguous = False
        if info is not None and info.source == "text":
            nearby = canonical_denominators(
                c.denominator for c in binding_texts(region, texts)
                if c.denominator is not None)
            if len(nearby) > 1:
                warn("SCALE_MULTIPLE_UNBOUND", "warning",
                     f"Page {page_number}: {len(nearby)} different scales are "
                     f"printed near {region.region_id} — none chosen")
                info = None
                ambiguous = True

        if info is None and not ambiguous and sole_candidate is not None:
            info = sole_candidate
        if info is None and not ambiguous and len(distinct) > 1:
            # One warning per region, so an ambiguous binding is not reported
            # twice under the same code.
            warn("SCALE_MULTIPLE_UNBOUND", "warning",
                 f"Page {page_number}: {len(distinct)} scales found on the sheet "
                 f"and none binds to {region.region_id}")

        if info is None and allow_prompt and can_prompt():
            # Rendered on demand, not looked up. region_crops/ is written only
            # by the Gemini classification call, so on a cache hit or with
            # --no-gemini the directory is empty and a bare path would send
            # the user to a file that does not exist.
            crop_hint = None
            if crop_fn is not None:
                try:
                    crop_hint = crop_fn(region)
                except Exception:
                    crop_hint = None
            typed = prompt_for_scale(region.region_id,
                                     crop_hint or "(no crop available)")
            if typed:
                newly_entered.append(StoredScale(region.bbox, typed))
                info = _stored_info(typed)

        if info is None:
            unresolved.append(region.region_id)
            result.by_region[region.region_id] = ScaleInfo(
                denominator=None, source="unresolved")
            continue

        result.by_region[region.region_id] = info
        if info.conflict:
            warn("SCALE_SOURCE_CONFLICT", "warning",
                 f"Page {page_number}: {region.region_id} measures "
                 f"{format_scale(info.denominator)} but {info.conflict}")

    if unresolved:
        warn("SCALE_UNRESOLVED", "warning",
             f"Page {page_number}: no scale resolved for {', '.join(unresolved)}")

    if newly_entered and pdf_path:
        try:
            save_stored(pdf_path, page_number, newly_entered)
        except Exception as e:
            warn("SCALE_STORE_WRITE_FAILED", "warning",
                 f"Page {page_number}: scale entered but not saved ({e})")

    return result
```

Extend `scale/__init__.py`:

```python
from models import ScaleInfo
from scale.resolver import PageScales, bind_scale, binding_texts, resolve_page_scales
from scale.text import scales_in_text, text_scales
from scale.viewport import viewport_scales
```

and add `"ScaleInfo"`, `"PageScales"`, `"bind_scale"`, `"binding_texts"`, `"resolve_page_scales"`, `"scales_in_text"`, `"text_scales"`, `"viewport_scales"` to `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_resolver -v`
Expected: PASS, 34 tests

- [ ] **Step 5: Commit**

```bash
git add scale/resolver.py scale/__init__.py tests/test_scale_resolver.py
git commit -m "feat(scale): resolution ladder with geometric region binding

Stored, viewport, text, sole page candidate, prompt. Viewport wins a
disagreement and records the loser; s13 is the one corpus sheet where
that matters."
```

---

### Task 7: Pipeline integration and console output

**Files:**
- Modify: `pipeline.py` — imports, `_page_summary_dict` (line ~213), `collect_warnings` (line ~172), the page loop (after the `regions` step, line ~447), `run_extract` signature
- Test: `tests/test_scale_pipeline.py`

**Interfaces:**
- Consumes: `scale.resolver.resolve_page_scales`, `PageScales`; `scale.viewport.viewport_scales`; `scale.store.load_stored`; `scale.units.format_scale`.
- Produces: `pipeline.scale_table(page_scales: PageScales, regions: list[Region]) -> Table`, and a `scales` key in each page's `summary.json` entry.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_pipeline.py`:

```python
"""Scale reporting inside the pipeline: the console table and summary.json."""
import unittest

from models import Region, ScaleInfo
from pipeline import scale_summary_dict, scale_table
from scale.resolver import PageScales


def region(rid, rtype="floor_plan"):
    return Region(region_id=rid, bbox=(0.0, 0.0, 10.0, 10.0), region_type=rtype)


class TestScaleTable(unittest.TestCase):
    def render(self, page_scales, regions):
        from rich.console import Console
        console = Console(record=True, width=120)
        console.print(scale_table(page_scales, regions))
        return console.export_text()

    def test_resolved_scale_is_shown_with_its_source(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport", raw="C=35.27546",
            nominal=100.0)})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:100", out)
        self.assertIn("viewport", out)

    def test_unresolved_region_is_shown_as_unknown(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=None, source="unresolved")})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("UNKNOWN", out.upper())

    def test_conflict_is_surfaced_in_the_table(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=136.4, source="viewport",
            conflict="text nearby says 1:100")})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:136.4", out)
        self.assertIn("CONFLICT", out.upper())

    def test_non_standard_measurement_shows_its_nearest_standard(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=99.6, source="viewport", nominal=100.0)})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:100", out)


class TestScaleSummaryDict(unittest.TestCase):
    def test_shape_is_json_serialisable(self):
        import json
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport", bbox=(1.0, 2.0, 3.0, 4.0),
            raw="C=35.27546", nominal=100.0)})
        json.dumps(scale_summary_dict(scales))

    def test_denominator_and_source_are_recorded(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport")})
        payload = scale_summary_dict(scales)
        self.assertEqual(payload["by_region"]["region_0002"]["denominator"], 100.0)
        self.assertEqual(payload["by_region"]["region_0002"]["source"], "viewport")

    def test_unresolved_records_a_null_denominator(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=None, source="unresolved")})
        payload = scale_summary_dict(scales)
        self.assertIsNone(payload["by_region"]["region_0002"]["denominator"])


class TestWarningCountIncludesScaleWarnings(unittest.TestCase):
    """warning_count comes from page_warnings, not all_warnings.

    A scale warning appended straight to all_warnings would show up in
    warnings.json but be missing from the per-page count in summary.json.
    """

    def test_scale_warnings_are_counted(self):
        from models import PageData
        from pipeline import _page_summary_dict

        page_data = PageData(page_number=1, width_px=10.0, height_px=10.0)
        scale_warning = {"page_number": 1, "warning_code": "SCALE_UNRESOLVED",
                         "severity": "warning", "message": "no scale"}
        summary = _page_summary_dict(
            page_data, [], [], [scale_warning], [], PageScales())
        self.assertEqual(summary["warning_count"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_pipeline -v`
Expected: FAIL with `ImportError: cannot import name 'scale_summary_dict' from 'pipeline'`

- [ ] **Step 3: Write minimal implementation**

Add to `pipeline.py` imports. **`Table` and `rich_box` are not currently
imported there** — `pipeline.py` pulls in only `Console` and the `Progress`
columns, so `scale_table` raises `NameError` without these two lines:

```python
from rich.table import Table
from rich import box as rich_box

from scale.resolver import PageScales, resolve_page_scales
from scale.store import load_stored
from scale.units import format_scale
from scale.viewport import viewport_scales
```

Add two module-level functions to `pipeline.py`, next to `_page_summary_dict`:

```python
def scale_table(page_scales: PageScales, regions: list[Region]) -> Table:
    """The per-region scale table printed after each page."""
    types = {r.region_id: r.region_type for r in regions}
    table = Table(title="Scales", box=rich_box.SIMPLE_HEAVY)
    table.add_column("Region")
    table.add_column("Type")
    table.add_column("Scale", justify="right")
    table.add_column("Source")
    table.add_column("Evidence")

    for region_id in sorted(page_scales.by_region):
        info = page_scales.by_region[region_id]
        if info.denominator is None:
            shown, style = "UNKNOWN", "yellow"
        else:
            shown, style = format_scale(info.denominator), "green"
        evidence = info.raw or ""
        if info.conflict:
            evidence = f"CONFLICT — {info.conflict}"
            style = "red"
        elif info.nominal is not None and info.denominator is not None \
                and abs(info.nominal - info.denominator) > 0.05:
            evidence = f"{evidence} → nearest standard {format_scale(info.nominal)}"
        table.add_row(region_id, types.get(region_id, "—"),
                      f"[{style}]{shown}[/{style}]", info.source, evidence)

    if not page_scales.by_region and page_scales.page_scale is not None:
        info = page_scales.page_scale
        table.add_row("(page)", "—",
                      f"[green]{format_scale(info.denominator)}[/green]",
                      info.source, info.raw or "")
    return table


def scale_summary_dict(page_scales: PageScales) -> dict:
    """The scales block written into each page's summary.json entry."""
    def one(info):
        return {"denominator": info.denominator, "source": info.source,
                "raw": info.raw, "nominal": info.nominal,
                "conflict": info.conflict,
                "bbox": list(info.bbox) if info.bbox else None}

    return {
        "by_region": {rid: one(info) for rid, info in page_scales.by_region.items()},
        "page_scale": one(page_scales.page_scale) if page_scales.page_scale else None,
    }
```

Add `scales` to `_page_summary_dict` — change its signature to accept
`page_scales: PageScales` and add to the returned dict:

```python
        "scales": scale_summary_dict(page_scales),
```

In the page loop, immediately after the `regions.json` write and before the
`plumber` step, add:

```python
            # 2d. Scale — needs the classified regions to bind against.
            def scale_crop(region, _page_dir=page_dir, _idx=idx):
                """A crop of one region, rendered if it is not already there.

                region_crops/ is written only by the Gemini classification
                call, so on a cache hit, with --no-gemini, or on a raster page
                the directory is empty. The prompt must not send the user to a
                path that does not exist.
                """
                target = Path(_page_dir) / "region_crops" / f"{region.region_id}.png"
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    render_region_crop(doc[_idx], region.bbox, str(target))
                return str(target)

            page_scales = resolve_page_scales(
                page_data=page_data,
                regions=region_result.regions,
                viewports=viewport_scales(doc, doc[idx]),
                stored=load_stored(str(path), page_num),
                pdf_path=str(path),
                crop_fn=scale_crop,
                # Task 8 replaces this literal with the run_extract parameter.
                # It must NOT stay True: regress.py calls run_extract
                # in-process and would inherit a real terminal.
                allow_prompt=True,
            )
```

`render_region_crop` comes from the classifier, which already owns region
rendering — add it to the import that is there:

```python
from gemini.classifier import classify_regions, render_region_crop
```

Do **not** extend `all_warnings` here. `_page_summary_dict` derives each page's
`warning_count` from `page_warnings`, so a scale warning added straight to
`all_warnings` would appear in `warnings.json` but be missing from the count in
`summary.json`. Fold it into the per-page list instead — modify the existing
block at `pipeline.py:579`:

```python
            page_warnings = collect_warnings(
                page_data, candidates, comparison, region_result.warnings,
            )
            page_warnings.extend(page_scales.warnings)
            for w in page_warnings:
                w.setdefault("page_number", page_num)
            all_warnings.extend(page_warnings)
```

Print the table after the progress bar closes for that page — add just before
`all_page_summaries.append(...)`:

```python
            console.print(scale_table(page_scales, region_result.regions))
```

and pass `page_scales` into the `_page_summary_dict(...)` call.

Add `"scale"` to the `steps` list so the progress bar total stays correct:

```python
    steps = ["extract", "render", "regions", "scale", "plumber", "heuristics",
             "overlay", "save"]
```

and call `step("scale")` immediately before `resolve_page_scales`.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_pipeline -v`
Expected: PASS, 8 tests

Then confirm nothing else broke:

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no new failures

- [ ] **Step 5: Record the new warning source in `CLAUDE.md`**

`CLAUDE.md`'s "Warning codes" section names three emit points —
`pipeline.collect_warnings`, `extraction.plumber.compare_counts` and
`gemini.client._validate_response`. The resolver is now a fourth, and it is the
only one that can explain why a scale did not resolve. Add it:

```markdown
Warnings are structured dicts with `warning_code`, `severity`, `message`,
`page_number`. The set is intentionally small — when adding a new warning,
follow the existing `SCREAMING_SNAKE_CASE` convention and emit from
`pipeline.collect_warnings`, `extraction.plumber.compare_counts`,
`gemini.client._validate_response`, or `scale.resolver.resolve_page_scales`
(which returns them on `PageScales.warnings` for `run_extract` to fold into
the page's warning list — only the resolver knows which tier resolved a
region, so only it can say why one did not).
```

Also add `scale/` to the "Module layout" tree, after `gemini/`:

```
scale/            # drawing-scale resolution: /VP measure viewports, scale text,
                  # a tty-gated prompt, and geometric binding to floor_plan regions
```

- [ ] **Step 6: Commit**

```bash
git add pipeline.py tests/test_scale_pipeline.py CLAUDE.md
git commit -m "feat(scale): resolve and display scales in the extract pipeline

New stage after region classification, since binding needs the
floor_plan regions. Prints a per-region table and records the result in
summary.json. Nothing consumes the value yet."
```

---

### Task 8: Unattended runs never prompt

**Files:**
- Modify: `pipeline.py` — `run_extract` signature, pass-through to the resolver
- Modify: `app.py` — `--no-scale-prompt` on the `extract` subcommand (args at line ~122)
- Modify: `regression/sweep.py` — extract the `run_extract` call at line 222 into a helper
- Modify: `batch_extract.py` — `build_extract_command` (line 41), `_run_with_group_kill` (line 58)
- Test: `tests/test_scale_no_prompt.py`

**Interfaces:**
- Consumes: `pipeline.run_extract`.
- Produces: `run_extract(..., allow_scale_prompt: bool = True)`; `regression.sweep._extract_for_sweep(path, page_count, out_parent, debug_traces)`.

**Why the tty gate is not enough.** `scale.prompt.can_prompt()` checks
`sys.stdin.isatty()`, which is correct but insufficient, because both
unattended callers can still be attached to a terminal:

- `regression/sweep.py:222` calls `run_extract` **in-process**. A `regress.py`
  run started from a terminal inherits that terminal's stdin, so `isatty()` is
  `True` and a sheet with no detectable scale would stop a 20-sheet unattended
  sweep to ask a question.
- `batch_extract.py:67` spawns `app.py extract` with `Popen(stdout=PIPE,
  stderr=PIPE)` — **stdin is not redirected**, so the child inherits the
  terminal too, and five parallel children would contend for it.

Seven of the twenty corpus sheets resolve no scale, so this is the common path
on a sweep, not an edge case. The tty gate stays as defence in depth; this task
adds the explicit control that actually carries the guarantee.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_no_prompt.py`:

```python
"""Unattended runs must never stop to ask for a scale.

sys.stdin.isatty() cannot carry this guarantee on its own: regress.py calls
run_extract in-process and batch_extract spawns a child without redirecting
stdin, so both inherit a real terminal when started from one.
"""
import inspect
import subprocess
import unittest
from unittest import mock

import batch_extract
import regression.sweep as sweep
from pipeline import run_extract


class TestRunExtractDefault(unittest.TestCase):
    def test_prompting_is_on_by_default(self):
        # An interactive `app.py extract` is the one caller that should ask.
        default = inspect.signature(run_extract).parameters["allow_scale_prompt"].default
        self.assertIs(default, True)


class TestSweepNeverPrompts(unittest.TestCase):
    def test_sweep_disables_scale_prompting(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 1, "out", False)
        self.assertIs(fake.call_args.kwargs["allow_scale_prompt"], False)

    def test_sweep_still_runs_offline(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 1, "out", False)
        self.assertIs(fake.call_args.kwargs["skip_gemini"], True)

    def test_sweep_passes_every_page(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 3, "out", False)
        self.assertEqual(fake.call_args.args[1], [0, 1, 2])


class TestBatchNeverPrompts(unittest.TestCase):
    def test_the_argv_disables_scale_prompting(self):
        cmd = batch_extract.build_extract_command(
            "a.pdf", enable_windows=True, enable_walls=True, use_gemini=False)
        self.assertIn("--no-scale-prompt", cmd)

    def test_the_flag_is_present_regardless_of_other_options(self):
        cmd = batch_extract.build_extract_command(
            "a.pdf", enable_windows=False, enable_walls=False, use_gemini=True)
        self.assertIn("--no-scale-prompt", cmd)

    def test_the_child_gets_no_stdin(self):
        # Belt and braces: even if a future prompt escapes the flag, a child
        # with no stdin fails the tty gate instead of hanging the batch.
        captured = {}

        class FakeProc:
            returncode = 0

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def communicate(self, timeout=None):
                return ("", "")

        def fake_popen(cmd, **kwargs):
            captured.update(kwargs)
            return FakeProc()

        with mock.patch.object(subprocess, "Popen", fake_popen):
            batch_extract._run_with_group_kill(["true"], 1.0)
        self.assertIs(captured.get("stdin"), subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_no_prompt -v`
Expected: FAIL — `KeyError: 'allow_scale_prompt'` and `AttributeError: module 'regression.sweep' has no attribute '_extract_for_sweep'`

- [ ] **Step 3: Write minimal implementation**

In `pipeline.py`, add the parameter to `run_extract` and thread it through:

```python
def run_extract(
    pdf_path: str,
    page_indices: list[int],
    out_parent: str = "outputs",
    skip_gemini: bool = False,
    disable_walls: bool = False,   # deprecated alias for disable_rooms
    disable_windows: bool = False,
    debug: bool = False,
    disable_rooms: bool = False,
    refresh_regions: bool = False,
    allow_scale_prompt: bool = True,
) -> str:
```

and change the resolver call added in Task 7:

```python
                allow_prompt=allow_scale_prompt,
```

In `app.py`, add the flag to the `extract` subcommand:

```python
    p_extract.add_argument(
        "--no-scale-prompt",
        action="store_true",
        help="Never ask for a drawing scale; record it as unresolved instead. "
             "Set automatically by batch_extract and regress.py, which run "
             "unattended but may still inherit a terminal.",
    )
```

and pass it through where `run_extract` is called (line ~91):

```python
        allow_scale_prompt=not args.no_scale_prompt,
```

In `regression/sweep.py`, replace the call at line 222 with a helper defined
above `sweep()`:

```python
def _extract_for_sweep(path, page_count: int, out_parent, debug_traces: bool) -> None:
    """run_extract as the sweep needs it: offline, and never interactive.

    allow_scale_prompt=False is NOT redundant with the tty gate. The sweep
    calls run_extract in-process, so a regress run started from a terminal
    inherits that terminal's stdin and sys.stdin.isatty() is True. Seven of
    the twenty corpus sheets resolve no scale, so without this a sweep would
    stop and wait for input on the common path.
    """
    run_extract(str(path), list(range(page_count)),
                out_parent=str(out_parent), skip_gemini=True,
                debug=debug_traces, allow_scale_prompt=False)
```

and the call site becomes:

```python
        _extract_for_sweep(path, entry["pages"], out_parent, debug_traces)
```

In `batch_extract.py`, add the flag unconditionally in `build_extract_command`:

```python
    # Unconditional: batch is never interactive, and the child inherits this
    # terminal's stdin, so the tty gate alone would not stop it prompting.
    cmd.append("--no-scale-prompt")
    return cmd
```

and close stdin on the child in `_run_with_group_kill`:

```python
    with subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        start_new_session=True,
    ) as proc:
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_no_prompt -v`
Expected: PASS, 7 tests

Then confirm the sweep still works end to end:

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no new failures

- [ ] **Step 5: Commit**

```bash
git add pipeline.py app.py regression/sweep.py batch_extract.py tests/test_scale_no_prompt.py
git commit -m "feat(scale): unattended runs never prompt for a scale

The tty gate cannot carry this on its own. regress.py calls run_extract
in-process and batch_extract spawns a child without redirecting stdin,
so both inherit a real terminal when started from one -- and seven of
the twenty corpus sheets resolve no scale, making this the common path
on a sweep rather than an edge case."
```

---

### Task 9: `inspect` degraded display

**Files:**
- Modify: `inspector.py` — imports, `print_page_summary` (line ~43), `inspect_pdf` (line ~126)
- Test: `tests/test_scale_inspector.py`

**Interfaces:**
- Consumes: `scale.viewport.viewport_scales`, `scale.text.text_scales`, `scale.units.format_scale`, `cluster_denominators`.
- Produces: `inspector.unbound_scale_lines(viewports: list[ScaleInfo], texts: list[ScaleInfo]) -> list[str]`.

`inspect` never segments regions, so it cannot bind. It lists what the sheet states and prompts for nothing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_inspector.py`:

```python
"""The inspect command's unbound scale listing.

inspect never segments regions, so it cannot bind a scale to a plan. It lists
what the sheet states and stops there -- and it never prompts.
"""
import unittest

from inspector import unbound_scale_lines
from models import ScaleInfo


def viewport(denominator):
    return ScaleInfo(denominator=denominator, source="viewport",
                     bbox=(0.0, 0.0, 10.0, 10.0), raw=f"C={denominator:g}")


def text(denominator, raw):
    return ScaleInfo(denominator=denominator, source="text",
                     bbox=(0.0, 0.0, 10.0, 10.0), raw=raw)


class TestUnboundScaleLines(unittest.TestCase):
    def test_no_scales_says_so(self):
        lines = unbound_scale_lines([], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("none found", lines[0].lower())

    def test_viewport_scales_are_listed(self):
        lines = unbound_scale_lines([viewport(100.0)], [])
        self.assertTrue(any("1:100" in line for line in lines))

    def test_text_scales_are_listed_with_their_span(self):
        lines = unbound_scale_lines([], [text(50.0, "1:50@A3")])
        self.assertTrue(any("1:50@A3" in line for line in lines))

    def test_repeated_viewport_scales_are_counted_not_repeated(self):
        # s17's four 1:100 viewports, at their REAL measured values. CAD never
        # writes a scale as the same float twice, so [viewport(100.0)] * 4
        # would pass while the grouping bug it targets was live.
        lines = unbound_scale_lines(
            [viewport(d) for d in (99.986, 99.988, 99.993, 99.995)], [])
        joined = " ".join(lines)
        self.assertEqual(joined.count("1:100"), 1)
        self.assertIn("4", joined)

    def test_a_span_stating_two_scales_lists_both(self):
        # s20's title block reads "1:50  & 1:100" — text_scales emits two
        # ScaleInfos sharing one raw string, and both must be listed.
        raw = "1:50  & 1:100"
        lines = unbound_scale_lines([], [text(50.0, raw), text(100.0, raw)])
        joined = " ".join(lines)
        self.assertIn("1:50", joined)
        self.assertIn("1:100", joined)

    def test_the_same_scale_repeated_in_one_span_is_listed_once(self):
        raw = "SCALE 1:100"
        lines = unbound_scale_lines([], [text(100.0, raw), text(100.0, raw)])
        self.assertEqual(len(lines), 1)

    def test_both_sources_appear(self):
        lines = unbound_scale_lines([viewport(100.0)], [text(50.0, "1:50@A3")])
        joined = " ".join(lines)
        self.assertIn("1:100", joined)
        self.assertIn("1:50", joined)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_inspector -v`
Expected: FAIL with `ImportError: cannot import name 'unbound_scale_lines' from 'inspector'`

- [ ] **Step 3: Write minimal implementation**

Add to `inspector.py` imports:

```python
from typing import Optional

from models import ScaleInfo
from scale.text import text_scales
from scale.units import cluster_denominators, format_scale
from scale.viewport import viewport_scales
```

Add the function to `inspector.py`:

```python
def unbound_scale_lines(
    viewports: list[ScaleInfo], texts: list[ScaleInfo]
) -> list[str]:
    """Scales stated on the sheet, unbound to any drawing.

    inspect does not segment regions, so there is nothing to bind to. Repeated
    viewport scales are counted rather than repeated — s17 states 1:100 four
    times, once per plan.
    """
    if not viewports and not texts:
        return ["[dim]Scales: none found in viewports or text[/dim]"]

    lines: list[str] = []

    # Grouped with cluster_denominators, not counted by raw float. s17's four
    # 1:100 viewports measure 99.986, 99.988, 99.993 and 99.995 — keying on
    # the float prints four identical "1:100" lines instead of one "(×4)".
    groups = cluster_denominators(
        info.denominator for info in viewports if info.denominator is not None)
    for group in groups:
        suffix = f" (×{len(group)})" if len(group) > 1 else ""
        lines.append(f"[bold]Scale (viewport):[/bold] "
                     f"{format_scale(group[0])}{suffix}")

    # Keyed on (raw, denominator), not raw alone: one span can state several
    # scales. s20's title block reads "1:50  & 1:100" and text_scales emits
    # two ScaleInfos sharing that raw string — deduping on raw would list
    # 1:50 and silently drop 1:100, on one of only three sheets that resolve
    # by text at all.
    seen: set[tuple[str, Optional[float]]] = set()
    for info in texts:
        raw = (info.raw or "").strip()
        key = (raw.lower(), info.denominator)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"[bold]Scale (text):[/bold] "
                     f"{format_scale(info.denominator)} — {raw!r}")
    return lines
```

Change `print_page_summary` to accept `scale_lines: list[str]` as its final
parameter and append them to `meta_lines` just before `console.print(Panel(...))`:

```python
    meta_lines.extend(scale_lines)
```

In `inspect_pdf`, inside the page loop, before `print_page_summary(...)`:

```python
        scale_lines = unbound_scale_lines(
            viewport_scales(doc, doc[idx]), text_scales(page_data))
```

and pass `scale_lines` to `print_page_summary`.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_inspector -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add inspector.py tests/test_scale_inspector.py
git commit -m "feat(scale): list sheet scales in the inspect command

Unbound by design -- inspect never segments regions, so there is no
plan to bind to, and it never prompts."
```

---

### Task 10: Corpus expectations

**Files:**
- Create: `tests/test_scale_corpus.py`
- Test: itself

**Interfaces:**
- Consumes: `scale.viewport.viewport_scales`, `scale.text.text_scales`; `tests.fixtures.require_sheet`.
- Produces: nothing.

This is the only test that opens a real PDF. It skips via `require_sheet` when the corpus is not downloaded, exactly as `tests/test_layout_golden.py` does.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_corpus.py`:

```python
"""Measured scale expectations across the regression corpus.

Every number was measured on 2026-08-11 and is recorded in the design spec. A
failure here means scale reading changed on a real sheet -- investigate before
touching the expectations. The sheets are NDA-covered and gitignored, so these
tests skip when the corpus is not downloaded.
"""
import unittest

import fitz

from extraction.extractor import extract_page
from scale.text import text_scales
from scale.viewport import viewport_scales
from tests.fixtures import require_sheet

# slug -> the set of viewport denominators, rounded, with paper space excluded.
VIEWPORT_EXPECTATIONS = {
    "s03": {100, 50, 500},
    "s04": {50},
    "s05": {100},
    "s06": {100, 146},
    "s07": {100},
    "s08": {50},
    "s12": {100},
    "s13": {136, 146},
    "s15": {50},
    "s17": {100, 50, 1249},
}

# slug -> the set of denominators stated in text.
TEXT_EXPECTATIONS = {
    "s02": {50},
    "s14": {50},
    "s20": {50, 100},
}

# Neither tier resolves these. Six of the seven have zero text spans -- their
# text is outlined to curves -- which is what a future vision tier is for.
NO_SCALE_SLUGS = ["s01", "s09", "s10", "s11", "s16", "s18", "s19"]


def read(test_case, slug):
    path = require_sheet(test_case, slug)
    doc = fitz.open(path)
    page_data = extract_page(doc, 0)
    viewports = viewport_scales(doc, doc[0])
    texts = text_scales(page_data)
    doc.close()
    return viewports, texts


class TestViewportScales(unittest.TestCase):
    def test_measured_viewport_denominators(self):
        for slug, expected in VIEWPORT_EXPECTATIONS.items():
            with self.subTest(slug=slug):
                viewports, _ = read(self, slug)
                found = {int(round(v.denominator)) for v in viewports}
                self.assertEqual(found, expected)

    def test_viewports_are_ordered_smallest_bbox_first(self):
        # The nesting rule depends on this ordering: s06's inner 1:100 must be
        # offered before its outer 1:146.
        viewports, _ = read(self, "s06")
        areas = [(v.bbox[2] - v.bbox[0]) * (v.bbox[3] - v.bbox[1])
                 for v in viewports]
        self.assertEqual(areas, sorted(areas))
        self.assertEqual(int(round(viewports[0].denominator)), 100)

    def test_paper_space_viewport_is_never_reported(self):
        for slug in ("s03", "s04", "s08", "s17"):
            with self.subTest(slug=slug):
                viewports, _ = read(self, slug)
                self.assertTrue(all(v.denominator > 1.5 for v in viewports))


class TestTextScales(unittest.TestCase):
    def test_measured_text_denominators(self):
        for slug, expected in TEXT_EXPECTATIONS.items():
            with self.subTest(slug=slug):
                _, texts = read(self, slug)
                found = {int(round(t.denominator)) for t in texts}
                self.assertEqual(found, expected)

    def test_do_not_scale_notices_are_not_read_as_scales(self):
        for slug in ("s14", "s15"):
            with self.subTest(slug=slug):
                _, texts = read(self, slug)
                self.assertTrue(all("DO NOT SCALE" not in (t.raw or "").upper()
                                    for t in texts))


class TestSheetsWithNoRecoverableScale(unittest.TestCase):
    def test_neither_tier_resolves_them(self):
        for slug in NO_SCALE_SLUGS:
            with self.subTest(slug=slug):
                viewports, texts = read(self, slug)
                self.assertEqual(viewports, [])
                self.assertEqual(texts, [])


class TestKnownConflict(unittest.TestCase):
    """s13 is the one corpus sheet whose viewport and printed scale disagree.

    It measures 1:136.4 but prints SCALE 1:100, and its room geometry is the
    same magnitude as s06's 1:100 plans. Which is right is unresolved; the
    pipeline flags it rather than guessing.

    Both sides are asserted. Pinning only the viewport would let the conflict
    evaporate silently if text parsing regressed and stopped finding the
    caption — the test would still pass while the warning stopped firing.
    """

    def test_s13_viewport_measures_136(self):
        viewports, _ = read(self, "s13")
        self.assertEqual(min(int(round(v.denominator)) for v in viewports), 136)

    def test_s13_prints_1_to_100(self):
        _, texts = read(self, "s13")
        self.assertIn(100, {int(round(t.denominator)) for t in texts})

    def test_the_two_readings_are_far_enough_apart_to_conflict(self):
        from scale.resolver import AGREEMENT_TOLERANCE
        viewports, texts = read(self, "s13")
        measured = min(v.denominator for v in viewports)
        printed = min(t.denominator for t in texts)
        self.assertGreater(abs(measured - printed),
                           AGREEMENT_TOLERANCE * measured)

    def test_binding_a_region_over_the_plan_records_the_conflict(self):
        """The resolver-level assertion: a region sitting inside the measuring
        viewport, with the caption beneath it, must come back flagged."""
        from models import Region
        from scale.resolver import bind_scale

        viewports, texts = read(self, "s13")
        inner = viewports[0]
        x0, y0, x1, y1 = inner.bbox
        probe = Region(region_id="probe",
                       bbox=(x0 + 1.0, y0 + 1.0, x1 - 1.0, y1 - 1.0),
                       region_type="floor_plan")
        found = bind_scale(probe, viewports, texts)
        self.assertIsNotNone(found)
        self.assertEqual(int(round(found.denominator)), 136)
        self.assertIsNotNone(found.conflict)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_scale_corpus -v`
Expected: PASS if Tasks 2 and 3 are correct, or SKIP if the corpus is absent. If any expectation fails, **do not edit the expectation** — read the spec's Evidence section and find the parsing bug.

- [ ] **Step 3: Verify the corpus is present**

Run: `source .venv/bin/activate && python tools/fetch_fixtures.py`
Expected: reports all 20 sheets present. If it does not, the test skips and Task 9 cannot be validated — say so rather than marking it done.

- [ ] **Step 4: Run the whole suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, and the run stays around 10s.

- [ ] **Step 5: Commit**

```bash
git add tests/test_scale_corpus.py
git commit -m "test(scale): corpus expectations for all 20 sheets

Ten viewport sheets, three text sheets, seven with nothing to read.
Pins the s13 viewport/text disagreement so it cannot be silenced."
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| `/VP` → `/Measure`, `C / MM_PER_PT` | 1, 2 |
| Paper-space exclusion | 1 (constant), 2 (filter), 9 (corpus check) |
| Nesting, innermost wins | 2 (sort), 6 (bind), 9 (ordering check) |
| y-up bbox flip | 2 (`viewport_bbox_to_px`) |
| Text tier, negation trap | 3 |
| Split-span joining | 3 — dropped; the spec now records why |
| Region binding | 6 |
| Conflict, viewport wins | 6, 9 |
| Prompt, tty gate | 5, 6 |
| Unattended runs never prompt | 8 |
| Store: ground truth + local cache | 4 |
| Pipeline stage, console, summary.json | 7 |
| `inspect` degraded mode | 9 |
| `SCALE_UNRESOLVED` / `SCALE_SOURCE_CONFLICT` / `SCALE_MULTIPLE_UNBOUND` | 6 |
| Fast synthetic tests | 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| Corpus expectation table | 10 |

**Deviations from the approved spec, both deliberate:**

1. **Split-span label joining is dropped** (Task 3). No corpus sheet needs it — the value span always carries the `1:N` itself. The spec's Evidence section now records this, so it does not get re-litigated.
2. **One extra warning code, `SCALE_STORE_WRITE_FAILED`** (Task 6). A read-only directory must not throw away a scale the user just typed, matching how `REGION_CACHE_WRITE_FAILED` is handled in `resolve_page_regions`.

**Type consistency:** `ScaleInfo` fields are used identically in Tasks 2, 3, 6, 7, 8. `bind_scale(region, viewports, texts)`, `binding_texts(region, texts)`, `canonical_denominators(denominators)` and `resolve_page_scales(page_data, regions, viewports, stored, pdf_path, crop_fn, allow_prompt)` match between Tasks 6, 7 and 9. `load_stored`/`save_stored`/`match_stored` all speak `list[StoredScale]` across Tasks 4, 6 and 7. Stored values are the string form (`"1:100"`) everywhere, and `scales_in_text` — the one grammar that parses them back — accepts a decimal denominator so `"1:136.4"` survives the round trip.

**Known risks:**

- Task 7 edits `_page_summary_dict`'s signature (its only caller is `pipeline.run_extract`) and Task 8 edits `print_page_summary`'s (its only caller is `inspect_pdf`). Both are single-caller changes; run the full suite after each.
- `CAPTION_REACH_PX = 240.0` is set from two measurements (s03 at 60px, s13 at 191px). If a corpus sheet turns up whose caption sits further from its viewport, its conflict goes undetected rather than misreported — check this before widening the constant, since a longer reach lets a caption claim the plan above its own.
- `page_scale` is `None` on any sheet stating more than one scale, so `scale_table` prints an empty table for a multi-scale sheet with no `floor_plan` regions. That is correct — no single number describes such a sheet — and `inspect` is the command that lists them unbound.
- Test counts in each task's Step 4 were verified by counting `def test_` in the task's own file rather than by hand; re-count after adding a test rather than incrementing.
- Synthetic test values must not use round numbers where real data never produces them. `100.0` twice is not a valid stand-in for s17's four 1:100 viewports (99.986, 99.988, 99.993, 99.995) — an earlier draft of `canonical_denominators`' test did exactly that and would have passed while the bug it targeted was live. Corpus floats are in Task 9's expectation table.
