# Scale-Aware Door Detection Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make door detection scale-aware — world-space `DOOR_*` and door-side `CROSS_*` gates scale with the page's resolved drawing scale, while paper-space and dimensionless gates stay fixed.

**Architecture:** A frozen `DoorGates` dataclass (one field per scaled constant, named identically to the constant) is built once per `detect_doors` call from the `scale_factor` that `run_heuristics` already receives, and threaded explicitly down the doors package's acyclic import chain. Paper-space and dimensionless constants deliberately have **no field**, so "this one does not scale" is visible in review. `CrossGates` does the same for `detection/postprocess.py`. At `factor = 1.0` every field equals its constant exactly, so 1:50 and unresolved-scale sheets are bit-identical.

**Tech Stack:** Python 3, `dataclasses`, `unittest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md`
**Precedent to mirror:** `detection/walls.py:237` (`WallGates`), `detection/rooms.py:282` (`RoomGates`), `tests/test_scale_gates.py`.

## Global Constraints

- **Branch:** `feat/scale-aware-door-gates` (already created, off `main` at `48f19dd`). Never commit to `main`.
- **Commit style:** imperative, type-prefixed (`feat:`, `test:`, `fix:`, `docs:`, `refactor:`). **Never add a `Co-Authored-By` trailer.**
- **Baseline:** `python -m unittest discover tests` is **810 tests, OK** at the start. It must stay green after every task. A pre-existing test failing means identity broke — **fix the code, never the test**.
- **Exact identity at f = 1.0** is the load-bearing invariant. Every scaled field is `CONSTANT * factor`; at 1.0 that is the constant itself.
- **No default `gates` parameters.** Every helper consuming a scaled constant takes `*, gates: DoorGates` — keyword-only, **no default**. A missing argument must raise `TypeError`, never silently fall back to unscaled. (Findings §4(b): a single defaulted parameter ran `_bridge_white_runs` unscaled on every sheet and no name-grep could find it.)
- **Paper-space constants must keep working as bare module constants.** `DOOR_LEAF_COMPANION_PERP_PX` (`leaves.py:528`) and `DOOR_FOLD_LEAF_LINE_SEP_MIN/MAX_PX` (`folding.py:251`) are **P** — if any task turns one into a gates field, that is a bug the tests must catch.
- **Corpus rules:** `fixtures/sheets/` is NDA'd and never committed. Never run `tools/review.py`. Never edit `tests/ground_truth/*.json` or fixture bytes. New detections are the user's to verdict.
- **Regression protocol:** one fix + one sweep per iteration, then stop and ask the user. `python tools/regress.py` is the arbiter — never a side harness alone.
- **Out of scope:** `DOOR_BBOX_ASPECT_MIN/MAX` (dimensionless; the deferred aspect-gate branch), `WINDOW_*`, labels, schedules, the s11 assembly-merge defect.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `detection/doors/constants.py` | Modify | Add `DoorGates`, `DoorGates.at()`, `DOOR_GATES_UNSCALED`. Existing constants keep their 1:50 values and stay importable. |
| `detection/doors/arcs.py` | Modify | `_is_arc_like`, `_detect_polyline_arc_bboxes`, `_collect_door_swings` take `gates`. |
| `detection/doors/leaves.py` | Modify | `_collect_door_leaves`, `_is_door_leaf`, `_find_anchored_leaf_line` take `gates`. |
| `detection/doors/sliding.py` | Modify | `_collect_slide_panels`, `_detect_sliding_doors` take `gates`. |
| `detection/doors/folding.py` | Modify | `_double_line_leaves`, `_detect_folding_doors` take `gates`. |
| `detection/doors/assembly.py` | Modify | `_pair_door_assemblies`, `_merge_double_door_assemblies` take `gates`. |
| `detection/doors/detect.py` | Modify | `detect_doors` gains `scale_factor`, builds gates, threads down. |
| `detection/orchestrator.py:45` | Modify | Pass `scale_factor` to `detect_doors`. |
| `detection/postprocess.py` | Modify | Add `CrossGates`; `_cross_validate` gains `scale_factor`. |
| `tests/test_scale_door_gates.py` | Create | Gates construction, per-module threading, no-default enforcement. |
| `tests/test_scale_door_endtoend.py` | Create | Faithful-1:100 fixtures, identity, negative controls, paper-space invariance. |
| `docs/scale-normalization-findings.md` | Modify | §4c harness trap, §4d frozen door table, §6 deferred entries. |

---

## Task 1: `DoorGates` dataclass

**Files:**
- Modify: `detection/doors/constants.py` (append after the existing constants)
- Test: `tests/test_scale_door_gates.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `DoorGates` (frozen dataclass, fields listed below, all `float` except `factor`), `DoorGates.at(factor: float) -> DoorGates`, `DOOR_GATES_UNSCALED: DoorGates`. Every later task consumes these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_door_gates.py`:

```python
"""Scale-factor behavior of the door gates: identity at 1.0, linear at 0.5.

A "faithful 1:100 export" scales EXTENTS and keeps PAPER quantities — pen
widths and drawn ink separations — unchanged. See
docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md §1/§2.
"""
import unittest

from detection.doors.constants import (
    DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_FOLD_LEAF_LINE_SEP_MAX_PX,
    DOOR_LEAF_COMPANION_PERP_PX, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_SLIDE_PANEL_MIN_THICKNESS_PX, DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
    DOOR_GATES_UNSCALED, DoorGates,
)


class TestDoorGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = DoorGates.at(1.0)
        self.assertEqual(g.DOOR_MIN_SIZE_PX, DOOR_MIN_SIZE_PX)
        self.assertEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX)
        self.assertEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_ASSEMBLY_CONNECT_TOL_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX)
        self.assertEqual(g, DOOR_GATES_UNSCALED)

    def test_world_gates_scale_linearly(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX,
                               DOOR_ASSEMBLY_CONNECT_TOL_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
                               DOOR_SLIDE_PANEL_MAX_THICKNESS_PX * 0.5)

    def test_min_size_floored_at_one_pixel(self):
        # Floor is a backstop: at the f=0.25 clamp the raw product is 5.0px,
        # so it is inert on the calibrated domain.
        self.assertAlmostEqual(DoorGates.at(0.25).DOOR_MIN_SIZE_PX,
                               DOOR_MIN_SIZE_PX * 0.25)
        self.assertEqual(DoorGates.at(0.001).DOOR_MIN_SIZE_PX, 1.0)

    def test_rejects_non_positive_factor(self):
        # The ONLY assertion: factor-independent, so a failure is a bug.
        with self.assertRaises(AssertionError):
            DoorGates.at(0.0)
        with self.assertRaises(AssertionError):
            DoorGates.at(-1.0)

    def test_paper_space_constants_have_no_field(self):
        # Absence from the dataclass is what makes "does not scale" reviewable.
        g = DoorGates.at(0.5)
        for name in ("DOOR_LEAF_COMPANION_PERP_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MIN_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MAX_PX",
                     "DOOR_POLYLINE_ENDPOINT_TOL",
                     "DOOR_LABEL_SEARCH_RADIUS_PX",
                     "DOOR_FOLD_HINGE_TOL_PX",
                     "DOOR_BBOX_ASPECT_MIN", "DOOR_BBOX_ASPECT_MAX"):
            self.assertFalse(hasattr(g, name), f"{name} is P or D — must not be a gates field")

    def test_cross_class_inversion_is_a_no_op_not_a_crash(self):
        # DOOR_FOLD_LEAF_LINE_SEP_MAX_PX (P, 4.0) vs
        # DOOR_SLIDE_PANEL_MIN_THICKNESS_PX (W, 3.0*f) invert below f=0.75 —
        # every 1:100 sheet. They gate DIFFERENT detectors and are never
        # compared, so nothing may assert or clamp the ordering. This test
        # exists so nobody "fixes" the crossing later.
        g = DoorGates.at(0.5)
        self.assertLess(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                        DOOR_FOLD_LEAF_LINE_SEP_MAX_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX * 0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates -v`
Expected: FAIL — `ImportError: cannot import name 'DoorGates' from 'detection.doors.constants'`

- [ ] **Step 3: Write minimal implementation**

Append to `detection/doors/constants.py` (the `from dataclasses import dataclass` import goes at the top, beside `import re`):

```python
@dataclass(frozen=True)
class DoorGates:
    """World-space door gates, pre-multiplied by the detection factor.

    Fields keep the exact names of the module constants they scale, so a use
    site reads `gates.DOOR_MIN_SIZE_PX` where it read the module constant.
    Paper-space constants (drawn ink separations, CAD-precision snap
    tolerances, the label search radius) and dimensionless ones (ratios,
    angles, counts, confidences) deliberately have NO field here — they never
    scale. At factor 1.0 every field equals its constant exactly.

    Classification and its measurements:
    docs/scale-normalization-findings.md §4d.
    """
    factor: float
    # --- arc / swing extents -------------------------------------------
    DOOR_MIN_SIZE_PX: float
    DOOR_MAX_SIZE_PX: float
    DOOR_SWING_LINE_DIST_PX: float
    DOOR_POLYLINE_MAX_SEG_PX: float
    # --- leaf / assembly extents ---------------------------------------
    DOOR_ASSEMBLY_CONNECT_TOL_PX: float
    DOOR_LEAF_LINE_ENDPOINT_TOL_PX: float
    DOOR_THRESHOLD_ENDPOINT_TOL_PX: float
    DOOR_DOUBLE_LEAF_GAP_PX: float
    DOOR_DOUBLE_LEAF_OVERLAP_PX: float
    DOOR_DOUBLE_LEAF_CENTER_TOL_PX: float
    # --- sliding ---------------------------------------------------------
    DOOR_SLIDE_PANEL_MIN_THICKNESS_PX: float
    DOOR_SLIDE_PANEL_MAX_THICKNESS_PX: float
    DOOR_SLIDE_FLANK_GAP_MIN_PX: float
    DOOR_SLIDE_FLANK_GAP_MAX_PX: float
    DOOR_SLIDE_PARK_GAP_MAX_PX: float
    DOOR_SLIDE_PARK_BAND_MIN_TH_PX: float
    DOOR_SLIDE_PARK_BAND_MAX_TH_PX: float
    DOOR_SLIDE_PARK_JAMB_TOL_PX: float
    # --- folding ---------------------------------------------------------
    DOOR_FOLD_JAMB_ANCHOR_TOL_PX: float
    DOOR_FOLD_JAMB_LINE_MIN_LEN_PX: float
    DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX: float

    @classmethod
    def at(cls, factor: float) -> "DoorGates":
        assert factor > 0, "scale factor must be positive"
        return cls(
            factor=factor,
            # Floor: a swing smaller than a pixel is not a door. Inert on the
            # calibrated domain (5.0px at the f=0.25 clamp); a backstop only.
            DOOR_MIN_SIZE_PX=max(1.0, DOOR_MIN_SIZE_PX * factor),
            DOOR_MAX_SIZE_PX=DOOR_MAX_SIZE_PX * factor,
            DOOR_SWING_LINE_DIST_PX=DOOR_SWING_LINE_DIST_PX * factor,
            # A tessellated arc segment is r*dtheta; r is world-space
            # (measured ratio 0.496) and dtheta is a fixed exporter setting.
            # Caveat: fixed-CHORD-ERROR exporters give ~sqrt(r) instead —
            # unmeasurable here (every 1:100 sheet draws native Beziers).
            DOOR_POLYLINE_MAX_SEG_PX=DOOR_POLYLINE_MAX_SEG_PX * factor,
            DOOR_ASSEMBLY_CONNECT_TOL_PX=DOOR_ASSEMBLY_CONNECT_TOL_PX * factor,
            DOOR_LEAF_LINE_ENDPOINT_TOL_PX=DOOR_LEAF_LINE_ENDPOINT_TOL_PX * factor,
            DOOR_THRESHOLD_ENDPOINT_TOL_PX=DOOR_THRESHOLD_ENDPOINT_TOL_PX * factor,
            DOOR_DOUBLE_LEAF_GAP_PX=DOOR_DOUBLE_LEAF_GAP_PX * factor,
            DOOR_DOUBLE_LEAF_OVERLAP_PX=DOOR_DOUBLE_LEAF_OVERLAP_PX * factor,
            DOOR_DOUBLE_LEAF_CENTER_TOL_PX=DOOR_DOUBLE_LEAF_CENTER_TOL_PX * factor,
            # Weakest row in the table: a drawn panel thickness. Scaled on the
            # mm argument (7.83px at 1:50 ~ 66mm, a real panel), NOT on the
            # shrunk-world test, which assumes the class under test. Revisit
            # trigger: shower screens / glazing strips appearing as sliding
            # doors on a 1:100 sheet. See spec §4.
            DOOR_SLIDE_PANEL_MIN_THICKNESS_PX=DOOR_SLIDE_PANEL_MIN_THICKNESS_PX * factor,
            DOOR_SLIDE_PANEL_MAX_THICKNESS_PX=DOOR_SLIDE_PANEL_MAX_THICKNESS_PX * factor,
            DOOR_SLIDE_FLANK_GAP_MIN_PX=DOOR_SLIDE_FLANK_GAP_MIN_PX * factor,
            DOOR_SLIDE_FLANK_GAP_MAX_PX=DOOR_SLIDE_FLANK_GAP_MAX_PX * factor,
            DOOR_SLIDE_PARK_GAP_MAX_PX=DOOR_SLIDE_PARK_GAP_MAX_PX * factor,
            # Wall-band thickness — the same quantity WALL_MIN/MAX_THICKNESS_PX
            # already carries as W in WallGates.
            DOOR_SLIDE_PARK_BAND_MIN_TH_PX=DOOR_SLIDE_PARK_BAND_MIN_TH_PX * factor,
            DOOR_SLIDE_PARK_BAND_MAX_TH_PX=DOOR_SLIDE_PARK_BAND_MAX_TH_PX * factor,
            DOOR_SLIDE_PARK_JAMB_TOL_PX=DOOR_SLIDE_PARK_JAMB_TOL_PX * factor,
            DOOR_FOLD_JAMB_ANCHOR_TOL_PX=DOOR_FOLD_JAMB_ANCHOR_TOL_PX * factor,
            DOOR_FOLD_JAMB_LINE_MIN_LEN_PX=DOOR_FOLD_JAMB_LINE_MIN_LEN_PX * factor,
            DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX=DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX * factor,
        )


DOOR_GATES_UNSCALED = DoorGates.at(1.0)
```

Add at the top of the file, after `import re`:

```python
from dataclasses import dataclass
```

**NOTE, part of Step 3 — no ordering assertion.** Do **not** add an assertion
or clamp comparing `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX` to
`DOOR_FOLD_LEAF_LINE_SEP_MAX_PX`. They invert at every f < 0.75 and that is
correct — see the test in Step 1 and spec §5. `assert factor > 0` is the only
assertion in `DoorGates.at`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_scale_door_gates -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover tests`
Expected: `Ran 816 tests` … `OK` (810 baseline + 6 new)

- [ ] **Step 6: Commit**

```bash
git add detection/doors/constants.py tests/test_scale_door_gates.py
git commit -m "feat(doors): add DoorGates for scale-aware door constants

Frozen dataclass mirroring WallGates/RoomGates: one field per world-space
constant, named identically, exact identity at factor 1.0. Paper-space and
dimensionless constants deliberately have no field.

The FOLD_LEAF_LINE_SEP_MAX / SLIDE_PANEL_MIN_THICKNESS inversion below f=0.75
is a documented no-op, pinned by a test so it is not later 'fixed' with a
clamp that would widen the folding window on every 1:100 page."
```

---

## Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point

**Files:**
- Modify: `detection/doors/arcs.py` (`_is_arc_like:21`, `_detect_polyline_arc_bboxes:520`, `_collect_door_swings:975`)
- Modify: `detection/doors/detect.py` (whole file, 19 lines)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: `DoorGates`, `DoorGates.at`, `DOOR_GATES_UNSCALED` from Task 1.
- Produces:
  - `detect_doors(paths, text_spans, collector=None, scale_factor: float = 1.0) -> list[Candidate]` — the `scale_factor` keyword is what `orchestrator.py` calls in Task 7.
  - `_is_arc_like(path, collector=None, *, gates: DoorGates) -> bool`
  - `_detect_polyline_arc_bboxes(line_paths, collector=None, *, gates: DoorGates) -> list[dict]`
  - `_collect_door_swings(paths, collector=None, *, gates: DoorGates) -> list[_DoorSwing]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
from detection import detect_doors
from detection.doors.arcs import _collect_door_swings, _is_arc_like
from models import PathPrimitive


def prim(idx, item_type, points, stroke_width=1.0, fill=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0, 0, 0), fill=fill, stroke_width=stroke_width,
        dashes=None, layer="", points=points)


def quarter_bezier(idx, cx, cy, r):
    """A quarter-arc cubic Bezier of radius r, hinged at (cx, cy).

    r is a WORLD extent: it halves on a 1:100 export.
    """
    k = 0.5523 * r
    return prim(idx, "c", [(cx + r, cy), (cx + r, cy + k), (cx + k, cy + r), (cx, cy + r)])


class TestArcGatesThreading(unittest.TestCase):
    def test_is_arc_like_requires_gates_keyword(self):
        p = quarter_bezier(0, 100, 100, 50)
        with self.assertRaises(TypeError):
            _is_arc_like(p)          # no gates -> must NOT silently run unscaled

    def test_small_arc_rejected_at_f1_accepted_at_half(self):
        # radius 12 -> size 12px: under the 20px floor at f=1.0, over the
        # scaled 10px floor at f=0.5.
        p = quarter_bezier(0, 100, 100, 12)
        self.assertFalse(_is_arc_like(p, gates=DoorGates.at(1.0)))
        self.assertTrue(_is_arc_like(p, gates=DoorGates.at(0.5)))

    def test_collect_swings_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_swings([quarter_bezier(0, 100, 100, 50)])

    def test_detect_doors_identity_factor_equals_omitted(self):
        paths = [quarter_bezier(0, 100, 100, 50)]
        self.assertEqual(
            [c.bbox for c in detect_doors(paths, [])],
            [c.bbox for c in detect_doors(paths, [], None, scale_factor=1.0)])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates -v`
Expected: FAIL — `_is_arc_like()` accepts one positional arg today, so `test_is_arc_like_requires_gates_keyword` fails with "TypeError not raised".

- [ ] **Step 3: Write the implementation**

In `detection/doors/arcs.py`:

1. Add `DoorGates` to the existing `from detection.doors.constants import (...)` block.
2. Change the three signatures to take a keyword-only, defaultless `gates`:

```python
def _is_arc_like(path: PathPrimitive, collector: DebugTraceCollector | None = None,
                 *, gates: DoorGates) -> bool:
```
```python
def _detect_polyline_arc_bboxes(line_paths: list[PathPrimitive],
                                collector: DebugTraceCollector | None = None,
                                *, gates: DoorGates) -> list[dict]:
```
```python
def _collect_door_swings(paths: list[PathPrimitive],
                         collector: DebugTraceCollector | None = None,
                         *, gates: DoorGates) -> list[_DoorSwing]:
```

3. Inside those functions and any private helper they call, replace **bare** references to the four scaled constants with the gates field:
   - `DOOR_MIN_SIZE_PX` → `gates.DOOR_MIN_SIZE_PX`
   - `DOOR_MAX_SIZE_PX` → `gates.DOOR_MAX_SIZE_PX`
   - `DOOR_SWING_LINE_DIST_PX` → `gates.DOOR_SWING_LINE_DIST_PX`
   - `DOOR_POLYLINE_MAX_SEG_PX` → `gates.DOOR_POLYLINE_MAX_SEG_PX`

   Any helper in `arcs.py` that reads one of these also gains `*, gates: DoorGates` and is passed `gates=gates` by its caller. **Leave `DOOR_BBOX_ASPECT_MIN/MAX`, `DOOR_POLYLINE_ENDPOINT_TOL`, `DOOR_CURVE_*_TOL_PX` and every `_DEG`/count constant exactly as they are** — they are D or P.

4. Update the internal call at `arcs.py:980` from `_is_arc_like(p, collector)` to `_is_arc_like(p, collector, gates=gates)`.

Rewrite `detection/doors/detect.py` in full:

```python
from __future__ import annotations
from models import PathPrimitive, TextSpan, Candidate
from debug.trace import DebugTraceCollector
from detection.doors.constants import DoorGates
from detection.doors.arcs import _collect_door_swings
from detection.doors.leaves import _collect_door_leaves
from detection.doors.assembly import _pair_door_assemblies, _merge_double_door_assemblies


def detect_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None = None,
    scale_factor: float = 1.0,
) -> list[Candidate]:
    """Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).

    Built once here and threaded down; helpers never default it, so a missing
    argument is a TypeError rather than a silent unscaled run.
    """
    gates = DoorGates.at(scale_factor)
    if collector:
        collector.init_primitives(paths)
    swings = _collect_door_swings(paths, collector, gates=gates)
    leaves = _collect_door_leaves(paths, collector)
    candidates = _pair_door_assemblies(swings, leaves, text_spans, paths, collector)
    return _merge_double_door_assemblies(candidates)
```

- [ ] **Step 4: Verify no bare references remain in the touched module**

Run:
```bash
for c in DOOR_MIN_SIZE_PX DOOR_MAX_SIZE_PX DOOR_SWING_LINE_DIST_PX DOOR_POLYLINE_MAX_SEG_PX; do
  bare=$(grep -n "\b$c\b" detection/doors/arcs.py | grep -v "gates\.$c" | grep -vc "import")
  [ "$bare" != "0" ] && echo "BARE USE REMAINS: $c ($bare)"
done; echo "audit done"
```
Expected: `audit done` with no `BARE USE REMAINS` lines. (Every use is
`gates.`-qualified; only the import line mentions the bare names.)

- [ ] **Step 5: Run tests**

Run: `python -m unittest tests.test_scale_door_gates -v && python -m unittest discover tests`
Expected: new tests PASS; full suite `OK` at 820 tests. **Existing arc tests that call `_is_arc_like(p)` or `_collect_door_swings(paths)` directly will now fail with `TypeError` — that is the no-default contract working.** Update those call sites in `tests/test_polyline_arc_pruning.py`, `tests/test_chained_curve_arcs.py`, `tests/test_door_assembly.py` and `tests/test_curve_arc_garden_doors.py` to pass `gates=DOOR_GATES_UNSCALED`. Do **not** change any expected value — only add the keyword.

- [ ] **Step 6: Commit**

```bash
git add detection/doors/arcs.py detection/doors/detect.py tests/
git commit -m "feat(doors): thread scale gates through arc collection

detect_doors gains scale_factor, builds DoorGates once and threads it into
_collect_door_swings/_is_arc_like/_detect_polyline_arc_bboxes. Gates are
keyword-only and defaultless so a missed call site is a TypeError, not a
silent unscaled run."
```

---

## Task 3: Thread gates through `leaves.py`

**Files:**
- Modify: `detection/doors/leaves.py` (`_collect_door_leaves:380`, `_find_anchored_leaf_line:421`, `_is_door_leaf`)
- Modify: `detection/doors/detect.py` (pass `gates=gates` to `_collect_door_leaves`)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: `DoorGates` (Task 1); `detect_doors` (Task 2).
- Produces: `_collect_door_leaves(paths, collector=None, *, gates: DoorGates) -> list[_DoorLeaf]`; `_find_anchored_leaf_line(..., *, gates: DoorGates)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
from detection.doors.leaves import _collect_door_leaves


class TestLeafGatesThreading(unittest.TestCase):
    def test_collect_leaves_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_leaves([])

    def test_short_leaf_rect_rejected_at_f1_accepted_at_half(self):
        # A 12 x 2.5 px leaf rectangle: length under the 20px DOOR_MIN_SIZE_PX
        # floor at f=1.0, over the scaled 10px floor at f=0.5. Aspect 4.8
        # clears DOOR_LEAF_ASPECT_MIN (4.0, dimensionless) at both factors.
        leaf = prim(0, "qu", [(0, 0), (12, 0), (12, 2.5), (0, 2.5)])
        self.assertEqual(_collect_door_leaves([leaf], gates=DoorGates.at(1.0)), [])
        self.assertEqual(len(_collect_door_leaves([leaf], gates=DoorGates.at(0.5))), 1)

    def test_leaf_companion_separation_is_paper_space(self):
        # DOOR_LEAF_COMPANION_PERP_PX is P: it must NOT move with the factor.
        # Measured: real leaf separations hold at ~2.6px on 1:100 sheets
        # (spec §2), so a 4px separation must stay acceptable at f=0.5.
        from detection.doors.constants import DOOR_LEAF_COMPANION_PERP_PX
        self.assertFalse(hasattr(DoorGates.at(0.5), "DOOR_LEAF_COMPANION_PERP_PX"))
        self.assertEqual(DOOR_LEAF_COMPANION_PERP_PX, 5.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates.TestLeafGatesThreading -v`
Expected: FAIL — "TypeError not raised".

- [ ] **Step 3: Write the implementation**

In `detection/doors/leaves.py`:
1. Add `DoorGates` to the constants import.
2. Give `_collect_door_leaves`, `_is_door_leaf` and `_find_anchored_leaf_line` a keyword-only `*, gates: DoorGates` parameter with no default, and pass `gates=gates` at every internal call.
3. Replace bare `DOOR_MIN_SIZE_PX`, `DOOR_MAX_SIZE_PX`, `DOOR_LEAF_LINE_ENDPOINT_TOL_PX` with `gates.`-qualified reads.
4. **Leave `DOOR_LEAF_COMPANION_PERP_PX` (line 528) as a bare module constant** — it is P.

In `detection/doors/detect.py`, change:
```python
    leaves = _collect_door_leaves(paths, collector)
```
to:
```python
    leaves = _collect_door_leaves(paths, collector, gates=gates)
```

- [ ] **Step 4: Verify the paper-space constant was not converted**

Run: `grep -n "DOOR_LEAF_COMPANION_PERP_PX" detection/doors/leaves.py`
Expected: the import line and a bare `DOOR_LEAF_COMPANION_PERP_PX` at the comparison — **never** `gates.DOOR_LEAF_COMPANION_PERP_PX`.

- [ ] **Step 5: Run tests**

Run: `python -m unittest discover tests`
Expected: `OK`. Fix any direct `_collect_door_leaves(...)` test call sites by adding `gates=DOOR_GATES_UNSCALED`.

- [ ] **Step 6: Commit**

```bash
git add detection/doors/leaves.py detection/doors/detect.py tests/
git commit -m "feat(doors): thread scale gates through leaf collection

DOOR_LEAF_COMPANION_PERP_PX stays a bare module constant: it gates a drawn
ink separation, measured paper-space (1.69px at 1:50 vs 2.63px at 1:100)."
```

---

## Task 4: Thread gates through `sliding.py`

**Files:**
- Modify: `detection/doors/sliding.py` (`_collect_slide_panels:214`, `_detect_sliding_doors:570`)
- Modify: `detection/doors/assembly.py` (the `_detect_sliding_doors` call site)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: `DoorGates` (Task 1).
- Produces:
  - `_collect_slide_panels(paths, include_stroked_rings=False, *, gates: DoorGates) -> list[_SlidePanel]`
  - `_detect_sliding_doors(paths, line_paths, swings, text_spans, collector, cand_idx, *, gates: DoorGates) -> tuple[list[Candidate], int]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
from detection.doors.sliding import _collect_slide_panels


class TestSlidingGatesThreading(unittest.TestCase):
    def test_collect_panels_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_slide_panels([])

    def test_thin_short_panel_rejected_at_f1_accepted_at_half(self):
        # 15 x 1.8px panel: length under DOOR_MIN_SIZE_PX (20) and thickness
        # under DOOR_SLIDE_PANEL_MIN_THICKNESS_PX (3.0) at f=1.0; both clear
        # their scaled floors (10.0 / 1.5) at f=0.5. Aspect 8.3 > 4.0.
        panel = prim(0, "qu", [(0, 0), (15, 0), (15, 1.8), (0, 1.8)])
        self.assertEqual(_collect_slide_panels([panel], gates=DoorGates.at(1.0)), [])
        self.assertEqual(len(_collect_slide_panels([panel], gates=DoorGates.at(0.5))), 1)

    def test_panel_thickness_ceiling_scales(self):
        # 60 x 15px panel: inside the 3-20px window at f=1.0, above the scaled
        # 1.5-10px window at f=0.5. Pins that MAX scales, not just MIN.
        panel = prim(0, "qu", [(0, 0), (60, 0), (60, 15), (0, 15)])
        self.assertEqual(len(_collect_slide_panels([panel], gates=DoorGates.at(1.0))), 1)
        self.assertEqual(_collect_slide_panels([panel], gates=DoorGates.at(0.5)), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates.TestSlidingGatesThreading -v`
Expected: FAIL — "TypeError not raised".

- [ ] **Step 3: Write the implementation**

In `detection/doors/sliding.py`:
1. Add `DoorGates` to the constants import.
2. Add `*, gates: DoorGates` (no default) to `_collect_slide_panels`, `_detect_sliding_doors` and every private helper of theirs that reads a scaled constant; pass `gates=gates` at each internal call.
3. Replace bare reads with `gates.`-qualified ones for: `DOOR_MIN_SIZE_PX`, `DOOR_MAX_SIZE_PX`, `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX`, `DOOR_SLIDE_PANEL_MAX_THICKNESS_PX`, `DOOR_SLIDE_FLANK_GAP_MIN_PX`, `DOOR_SLIDE_FLANK_GAP_MAX_PX`, `DOOR_SLIDE_PARK_GAP_MAX_PX`, `DOOR_SLIDE_PARK_BAND_MIN_TH_PX`, `DOOR_SLIDE_PARK_BAND_MAX_TH_PX`, `DOOR_SLIDE_PARK_JAMB_TOL_PX`.
4. **Leave alone** (P or D): `DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX`, `DOOR_SLIDE_PANEL_MERGE_TOL_PX`, every `_DEG`, every `_FRAC`/`_RATIO`/`_FACTOR`, `DOOR_SLIDE_ZONE_MAX_CROSSERS`, `DOOR_LEAF_ASPECT_MIN`.

In `detection/doors/assembly.py`:

1. Add `*, gates: DoorGates` (keyword-only, **no default**) to
   `_pair_door_assemblies`. This signature change belongs to **this** task, not
   Task 6: `assembly.py` is where `_detect_sliding_doors` is called from, and
   the no-default rule forbids passing `DOOR_GATES_UNSCALED` there as a
   stopgap — that is exactly the silent-unscaled-fallback bug this branch
   exists to prevent.
2. Pass `gates=gates` to the `_detect_sliding_doors(...)` call.
3. Do **not** convert assembly's own constants yet — Task 6 does that.

In `detection/doors/detect.py`, change the pairing call to:
```python
    candidates = _pair_door_assemblies(swings, leaves, text_spans, paths, collector,
                                       gates=gates)
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest discover tests`
Expected: `OK`. Update `tests/test_sliding_doors.py` call sites of `_collect_slide_panels` / `_detect_sliding_doors` with `gates=DOOR_GATES_UNSCALED`; change no expected values.

- [ ] **Step 5: Commit**

```bash
git add detection/doors/sliding.py detection/doors/assembly.py detection/doors/detect.py tests/
git commit -m "feat(doors): thread scale gates through sliding-door detection

Panel thickness scales on the mm argument (66mm at 1:50 = a real panel);
the CAD-precision snap tolerances stay paper-space."
```

---

## Task 5: Thread gates through `folding.py`

**Files:**
- Modify: `detection/doors/folding.py` (`_double_line_leaves:221`, `_detect_folding_doors:443`)
- Modify: `detection/doors/assembly.py` (the `_detect_folding_doors` call site)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: `DoorGates` (Task 1); `_pair_door_assemblies(..., *, gates)` (Task 4).
- Produces: `_detect_folding_doors(paths, text_spans, collector, cand_idx, *, gates: DoorGates) -> tuple[list[Candidate], int]`; `_double_line_leaves(line_paths, *, gates: DoorGates) -> list[_SlidePanel]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
from detection.doors.folding import _double_line_leaves


class TestFoldingGatesThreading(unittest.TestCase):
    def test_double_line_leaves_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _double_line_leaves([])

    def test_fold_leaf_line_separation_is_paper_space(self):
        # DOOR_FOLD_LEAF_LINE_SEP_MIN/MAX_PX gate a drawn ink separation (P).
        # Scaling them is what zeroed s06 in the spec's §3 table.
        from detection.doors.constants import (
            DOOR_FOLD_LEAF_LINE_SEP_MAX_PX, DOOR_FOLD_LEAF_LINE_SEP_MIN_PX)
        g = DoorGates.at(0.5)
        self.assertFalse(hasattr(g, "DOOR_FOLD_LEAF_LINE_SEP_MIN_PX"))
        self.assertFalse(hasattr(g, "DOOR_FOLD_LEAF_LINE_SEP_MAX_PX"))
        self.assertEqual((DOOR_FOLD_LEAF_LINE_SEP_MIN_PX,
                          DOOR_FOLD_LEAF_LINE_SEP_MAX_PX), (0.8, 4.0))

    def test_jamb_min_length_scales(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_FOLD_JAMB_LINE_MIN_LEN_PX, 7.5)
        self.assertAlmostEqual(g.DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX, 3.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates.TestFoldingGatesThreading -v`
Expected: FAIL — "TypeError not raised".

- [ ] **Step 3: Write the implementation**

In `detection/doors/folding.py`:
1. Add `DoorGates` to the constants import.
2. Add `*, gates: DoorGates` (no default) to `_double_line_leaves`, `_detect_folding_doors` and their scaled-constant-reading helpers; pass `gates=gates` internally.
3. Replace bare reads with `gates.`-qualified: `DOOR_MIN_SIZE_PX` (including the derived `DOOR_MIN_SIZE_PX * 0.7` at line 233 → `gates.DOOR_MIN_SIZE_PX * 0.7`), `DOOR_MAX_SIZE_PX`, `DOOR_FOLD_JAMB_ANCHOR_TOL_PX`, `DOOR_FOLD_JAMB_LINE_MIN_LEN_PX`, `DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX`.
4. **Leave alone**: `DOOR_FOLD_LEAF_LINE_SEP_MIN/MAX_PX` (P), `DOOR_FOLD_HINGE_TOL_PX` (P — fit slack, measured ≤0.3px), every `_DEG`, `DOOR_FOLD_MIN_CHAIN_LEAVES`, every `_RATIO`/`_TOL` fraction.
5. `_collect_slide_panels` is imported here from `sliding.py` — pass `gates=gates` at that call.

In `detection/doors/assembly.py`, pass `gates=gates` to `_detect_folding_doors(...)`.

- [ ] **Step 4: Run tests**

Run: `python -m unittest discover tests`
Expected: `OK`. Update `tests/test_folding_doors.py` call sites with `gates=DOOR_GATES_UNSCALED`.

- [ ] **Step 5: Commit**

```bash
git add detection/doors/folding.py detection/doors/assembly.py tests/
git commit -m "feat(doors): thread scale gates through folding-door detection

Jamb extents scale; the double-line leaf separation and the hinge fit slack
stay paper-space — scaling them zeroed s06's confirmed doors in measurement."
```

---

## Task 6: Thread gates through `assembly.py`

**Files:**
- Modify: `detection/doors/assembly.py` (`_pair_door_assemblies:202`, `_merge_double_door_assemblies:634`)
- Modify: `detection/doors/detect.py` (pass `gates=gates` to the merge)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: `_merge_double_door_assemblies(candidates, *, gates: DoorGates) -> list[Candidate]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
class TestAssemblyGatesThreading(unittest.TestCase):
    def test_merge_requires_gates_keyword(self):
        from detection.doors.assembly import _merge_double_door_assemblies
        with self.assertRaises(TypeError):
            _merge_double_door_assemblies([])

    def test_assembly_and_double_leaf_gates_scale(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX, 7.5)
        self.assertAlmostEqual(g.DOOR_DOUBLE_LEAF_GAP_PX, 6.0)
        self.assertAlmostEqual(g.DOOR_DOUBLE_LEAF_OVERLAP_PX, 2.5)
        self.assertAlmostEqual(g.DOOR_DOUBLE_LEAF_CENTER_TOL_PX, 4.0)
        self.assertAlmostEqual(g.DOOR_THRESHOLD_ENDPOINT_TOL_PX, 3.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates.TestAssemblyGatesThreading -v`
Expected: FAIL — "TypeError not raised".

- [ ] **Step 3: Write the implementation**

In `detection/doors/assembly.py`:
1. Add `*, gates: DoorGates` (no default) to `_merge_double_door_assemblies`.
2. Replace bare reads with `gates.`-qualified: `DOOR_ASSEMBLY_CONNECT_TOL_PX`, `DOOR_THRESHOLD_ENDPOINT_TOL_PX`, `DOOR_DOUBLE_LEAF_GAP_PX`, `DOOR_DOUBLE_LEAF_OVERLAP_PX`, `DOOR_DOUBLE_LEAF_CENTER_TOL_PX`.
3. **Leave alone**: `DOOR_LEAF_RADIUS_RATIO_TOL`, `DOOR_LABEL_SEARCH_RADIUS_PX` (P — no corpus signal), `DOOR_V2_BRIDGE_BUFFER_PX` (P), every confidence/boost/penalty, `DOOR_THRESHOLD_PARALLEL_TOL_DEG`.

In `detection/doors/detect.py`:
```python
    return _merge_double_door_assemblies(candidates, gates=gates)
```

- [ ] **Step 4: Verify every W constant is gates-qualified package-wide**

Run:
```bash
for c in DOOR_MIN_SIZE_PX DOOR_MAX_SIZE_PX DOOR_SWING_LINE_DIST_PX DOOR_POLYLINE_MAX_SEG_PX \
  DOOR_ASSEMBLY_CONNECT_TOL_PX DOOR_LEAF_LINE_ENDPOINT_TOL_PX DOOR_THRESHOLD_ENDPOINT_TOL_PX \
  DOOR_DOUBLE_LEAF_GAP_PX DOOR_DOUBLE_LEAF_OVERLAP_PX DOOR_DOUBLE_LEAF_CENTER_TOL_PX \
  DOOR_SLIDE_PANEL_MIN_THICKNESS_PX DOOR_SLIDE_PANEL_MAX_THICKNESS_PX \
  DOOR_SLIDE_FLANK_GAP_MIN_PX DOOR_SLIDE_FLANK_GAP_MAX_PX DOOR_SLIDE_PARK_GAP_MAX_PX \
  DOOR_SLIDE_PARK_BAND_MIN_TH_PX DOOR_SLIDE_PARK_BAND_MAX_TH_PX DOOR_SLIDE_PARK_JAMB_TOL_PX \
  DOOR_FOLD_JAMB_ANCHOR_TOL_PX DOOR_FOLD_JAMB_LINE_MIN_LEN_PX DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX; do
  bare=$(grep -rn "\b$c\b" detection/doors/*.py | grep -v constants.py | grep -v "gates\.$c" | grep -vc "import")
  [ "$bare" != "0" ] && echo "BARE USE REMAINS: $c ($bare)"
done; echo "audit done"
```
Expected: `audit done` with no `BARE USE REMAINS` lines.

- [ ] **Step 5: Run tests**

Run: `python -m unittest discover tests`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add detection/doors/assembly.py detection/doors/detect.py tests/
git commit -m "feat(doors): thread scale gates through assembly and double-door merge

Completes the doors package: every world-space DOOR_* constant now reads
through DoorGates. Verified by a package-wide bare-reference audit."
```

---

## Task 7: Wire `scale_factor` from the orchestrator (goes live)

**Files:**
- Modify: `detection/orchestrator.py:45`
- Test: `tests/test_scale_door_endtoend.py` (create)

**Interfaces:**
- Consumes: `detect_doors(..., scale_factor=...)` (Task 2).
- Produces: end-to-end scale-aware door detection. `run_heuristics(..., scale_factor=f)` now reaches doors.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale_door_endtoend.py`:

```python
"""End-to-end door scale behavior on FAITHFUL 1:100 fixtures.

A faithful 1:100 export scales EXTENTS and holds PAPER quantities fixed —
pen widths AND drawn ink separations. A blanket x0.5 of every coordinate is
NOT faithful: it halves the leaf-companion and fold-line separations that
real 1:100 sheets keep at ~2.6px, and that artifact accounted for all four
of s01's residual shrunk-world misses (spec §1).
"""
import unittest

from detection import detect_doors, run_heuristics
from models import PageData, PathPrimitive


def prim(idx, item_type, points, stroke_width=1.0, fill=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0, 0, 0), fill=fill, stroke_width=stroke_width,
        dashes=None, layer="", points=points)


def swing_door(base_idx, cx, cy, radius, leaf_sep=2.5):
    """Quarter-arc + a double-line leaf, as a faithful export at any scale.

    radius is a WORLD extent and scales with the drawing.
    leaf_sep is PAPER ink separation and does NOT scale — that is the whole
    point of this fixture builder.
    """
    k = 0.5523 * radius
    arc = prim(base_idx, "c",
               [(cx + radius, cy), (cx + radius, cy + k),
                (cx + k, cy + radius), (cx, cy + radius)])
    leaf_a = prim(base_idx + 1, "l", [(cx, cy), (cx, cy + radius)])
    leaf_b = prim(base_idx + 2, "l", [(cx - leaf_sep, cy), (cx - leaf_sep, cy + radius)])
    return [arc, leaf_a, leaf_b]


def page(paths):
    return PageData(
        page_number=1, width_px=1000, height_px=1000,
        paths=paths, text_spans=[], images=[], ocgs=[])


class TestFaithfulExportDetection(unittest.TestCase):
    def test_1to50_door_detected_at_factor_one(self):
        doors = detect_doors(swing_door(0, 200, 200, 50), [], None, scale_factor=1.0)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))

    def test_faithful_1to100_door_detected_at_factor_half(self):
        # Extents halved, leaf_sep held at its paper value.
        paths = swing_door(0, 100, 100, 25, leaf_sep=2.5)
        doors = detect_doors(paths, [], None, scale_factor=0.5)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))

    def test_negative_control_same_door_missed_when_unscaled(self):
        # If the threading is removed, this door is invisible. A regression
        # that silently drops gates makes THIS test fail.
        paths = swing_door(0, 100, 100, 25, leaf_sep=2.5)
        doors = detect_doors(paths, [], None, scale_factor=1.0)
        self.assertFalse(any(c.confidence >= 0.55 for c in doors))

    def test_paper_space_invariance_separation_must_not_scale(self):
        # leaf_sep 4.0px is under the unscaled 5.0px companion gate but OVER
        # a wrongly-scaled 2.5px one. Scaling DOOR_LEAF_COMPANION_PERP_PX
        # would break this — it is the s06 wipeout as a unit test.
        paths = swing_door(0, 100, 100, 25, leaf_sep=4.0)
        doors = detect_doors(paths, [], None, scale_factor=0.5)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))


class TestOrchestratorWiring(unittest.TestCase):
    def test_run_heuristics_forwards_scale_factor_to_doors(self):
        paths = swing_door(0, 100, 100, 25, leaf_sep=2.5)
        got = run_heuristics(page(paths), [], disable_windows=True,
                             disable_rooms=True, scale_factor=0.5)
        self.assertTrue(any(c.entity_type == "door" and c.confidence >= 0.55
                            for c in got))

    def test_run_heuristics_identity_at_one(self):
        paths = swing_door(0, 200, 200, 50)
        a = run_heuristics(page(paths), [], disable_windows=True, disable_rooms=True)
        b = run_heuristics(page(paths), [], disable_windows=True,
                           disable_rooms=True, scale_factor=1.0)
        self.assertEqual([c.bbox for c in a], [c.bbox for c in b])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_endtoend -v`
Expected: `test_run_heuristics_forwards_scale_factor_to_doors` FAILS — the orchestrator still calls `detect_doors` scale-blind.

If `test_faithful_1to100_door_detected_at_factor_half` also fails, the fixture geometry needs adjusting (radius/aspect), **not** the gates — tune the fixture until the f=1.0 case detects and the f=0.5 case is the only scale-dependent variable.

- [ ] **Step 3: Write the implementation**

In `detection/orchestrator.py`, change line 45 from:
```python
        doors = detect_doors(page_data.paths, page_data.text_spans, collector)
```
to:
```python
        doors = detect_doors(page_data.paths, page_data.text_spans, collector,
                             scale_factor=scale_factor)
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_scale_door_endtoend -v && python -m unittest discover tests`
Expected: all PASS, full suite `OK`.

- [ ] **Step 5: Commit**

```bash
git add detection/orchestrator.py tests/test_scale_door_endtoend.py
git commit -m "feat(doors): wire the detection scale factor into door detection

run_heuristics already resolved the per-page factor and forwarded it to
walls/rooms only; doors now receive it too. Fixtures model a FAITHFUL 1:100
export — extents scaled, pen widths and ink separations held at paper values."
```

---

## Task 8: `CrossGates` for door cross-validation

**Files:**
- Modify: `detection/postprocess.py` (constants block at :15–36, `_cross_validate:77`)
- Modify: `detection/orchestrator.py` (the `_cross_validate` call)
- Test: `tests/test_scale_door_gates.py` (append)

**Interfaces:**
- Consumes: nothing from the doors package.
- Produces: `CrossGates`, `CrossGates.at(factor) -> CrossGates`, `CROSS_GATES_UNSCALED`; `_cross_validate(candidates, network, *, scale_factor: float = 1.0) -> list[Candidate]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_door_gates.py`:

```python
class TestCrossGates(unittest.TestCase):
    def test_identity_at_one(self):
        from detection.postprocess import (
            CROSS_GATES_UNSCALED, CROSS_WALL_EXPAND_PX, CrossGates)
        g = CrossGates.at(1.0)
        self.assertEqual(g.CROSS_WALL_EXPAND_PX, CROSS_WALL_EXPAND_PX)
        self.assertEqual(g, CROSS_GATES_UNSCALED)

    def test_geometric_gates_scale(self):
        from detection.postprocess import CrossGates
        g = CrossGates.at(0.5)
        self.assertAlmostEqual(g.CROSS_WALL_EXPAND_PX, 10.0)
        self.assertAlmostEqual(g.CROSS_OPENING_ENDPOINT_TOL_PX, 6.0)
        self.assertAlmostEqual(g.CROSS_WALL_RUNS_THROUGH_MARGIN_PX, 6.0)
        self.assertAlmostEqual(g.CROSS_WALL_RUNS_THROUGH_BAND_PX, 4.0)
        self.assertAlmostEqual(g.CROSS_DOOR_EXPAND_PX, 10.0)
        self.assertAlmostEqual(g.CROSS_DOOR_FALLBACK_EXPAND_PX, 4.0)

    def test_confidence_penalties_have_no_field(self):
        from detection.postprocess import CrossGates
        g = CrossGates.at(0.5)
        for name in ("CROSS_NO_WALL_PENALTY",
                     "CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY",
                     "CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY",
                     "CROSS_WINDOW_ON_WALL_BOOST",
                     "CROSS_DOOR_MIN_CONFIDENCE",
                     "CROSS_DOOR_MIN_WINDOW_COVER"):
            self.assertFalse(hasattr(g, name), f"{name} is dimensionless")

    def test_scaled_gate_retains_measured_headroom(self):
        # Distribution measurement (spec §5): the p90 corridor reach that
        # confirmed doors actually need is <= 8.12px on every 1:100 sheet.
        from detection.postprocess import CrossGates
        self.assertGreater(CrossGates.at(0.5).CROSS_WALL_EXPAND_PX, 8.12)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_door_gates.TestCrossGates -v`
Expected: FAIL — `ImportError: cannot import name 'CrossGates'`.

- [ ] **Step 3: Write the implementation**

In `detection/postprocess.py`, after the constants block:

```python
@dataclass(frozen=True)
class CrossGates:
    """World-space cross-validation gates, pre-multiplied by the factor.

    Only the GEOMETRIC constants get fields; the confidence penalties and
    boosts are dimensionless and never scale.

    CROSS_WALL_EXPAND_PX is a door-bbox-to-wall corridor. Measured (findings
    §4d): the reach confirmed doors actually need has p90 9.64px at 1:50 vs
    0.78px at 1:100, and the scaled 10px gate still clears every 1:100
    sheet's p90 need (max 8.12px) with headroom.
    """
    factor: float
    CROSS_WALL_EXPAND_PX: float
    CROSS_OPENING_ENDPOINT_TOL_PX: float
    CROSS_WALL_RUNS_THROUGH_MARGIN_PX: float
    CROSS_WALL_RUNS_THROUGH_BAND_PX: float
    CROSS_DOOR_EXPAND_PX: float
    CROSS_DOOR_FALLBACK_EXPAND_PX: float

    @classmethod
    def at(cls, factor: float) -> "CrossGates":
        assert factor > 0, "scale factor must be positive"
        return cls(
            factor=factor,
            CROSS_WALL_EXPAND_PX=CROSS_WALL_EXPAND_PX * factor,
            CROSS_OPENING_ENDPOINT_TOL_PX=CROSS_OPENING_ENDPOINT_TOL_PX * factor,
            CROSS_WALL_RUNS_THROUGH_MARGIN_PX=CROSS_WALL_RUNS_THROUGH_MARGIN_PX * factor,
            CROSS_WALL_RUNS_THROUGH_BAND_PX=CROSS_WALL_RUNS_THROUGH_BAND_PX * factor,
            CROSS_DOOR_EXPAND_PX=CROSS_DOOR_EXPAND_PX * factor,
            CROSS_DOOR_FALLBACK_EXPAND_PX=CROSS_DOOR_FALLBACK_EXPAND_PX * factor,
        )


CROSS_GATES_UNSCALED = CrossGates.at(1.0)
```

Add `from dataclasses import dataclass` to the imports. Note `CROSS_DOOR_EXPAND_PX` and `CROSS_DOOR_FALLBACK_EXPAND_PX` are defined at lines 288/300, *after* `_cross_validate` — move the `CrossGates` definition below them so all six names are bound.

Change `_cross_validate` to build the gates and use them:

```python
def _cross_validate(
    candidates: list[Candidate],
    network: WallNetwork | None,
    *,
    scale_factor: float = 1.0,
) -> list[Candidate]:
```

Inside, `gates = CrossGates.at(scale_factor)`, then replace the six geometric constants with `gates.`-qualified reads. `scale_factor` keeps a default here because `_cross_validate` is called from tests directly and its default is genuine identity — the no-default rule applies to `gates` objects passed *between* modules, and this function builds its own.

In `detection/orchestrator.py`:
```python
        all_geo = _cross_validate(doors + windows, network, scale_factor=scale_factor)
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest discover tests`
Expected: `OK`. `tests/test_cross_validate.py` should need no changes (`scale_factor` defaults to 1.0).

- [ ] **Step 5: Commit**

```bash
git add detection/postprocess.py detection/orchestrator.py tests/
git commit -m "feat(doors): scale the geometric cross-validation gates

CROSS_WALL_EXPAND_PX and the five other geometric CROSS_ constants measure
door/window-to-wall distances and scale with the drawing; the confidence
penalties are dimensionless and do not. Derived from the needed-reach
distribution, not from door-survival counts."
```

---

## Task 9: Regression sweep, findings doc, graphify

**Files:**
- Modify: `docs/scale-normalization-findings.md` (new §4c, §4d; §6 updates)
- Modify: `graphify-out/` (regenerated)

**Interfaces:**
- Consumes: the complete implementation from Tasks 1–8.
- Produces: the frozen door classification table successors inherit.

- [ ] **Step 1: Confirm the fast tier is green**

Run: `python -m unittest discover tests`
Expected: `OK`. **Do not proceed while red.**

- [ ] **Step 2: Run the arbiter sweep**

Run: `python tools/regress.py 2>&1 | tee /tmp/sweep-doors.txt`

Expected per spec §6 — check each against the prediction:

| Sheet | expected new REVIEW (door / window / room) |
|---|---|
| s05 | 0 / 0 / 0 |
| s06 | 0 / 0 / 2 |
| s07 | 0 / 0 / 0 |
| s11 | 2 / 4 / 0 |
| s12 | 0 / 5 / 0 |
| s16 | 0 / 0 / 0 |
| s18 | 1 / 8 / 0 |

**Hard gates:** no `LOST` confirmed entity on any sheet; the 1:50 and
unresolved-scale sheets (s01, s02, s04, s08, s10, s14, s15, s20) byte-identical.
Exit 1 from the corpus's pre-existing FP debt (findings §3) is expected and is
**not** this branch's regression — compare `FALSE POSITIVE RETURNED` tallies
against §3's table before concluding anything.

- [ ] **Step 3: If the sweep diverges materially from the prediction, stop**

A material divergence is itself a finding (spec acceptance criterion 3).
Diagnose it, report to the user, and **do not** proceed to Step 4 or start a
second fix. One fix + one sweep per iteration, then ask.

- [ ] **Step 4: Write the findings-doc sections**

Add to `docs/scale-normalization-findings.md`:

- **§4c — Measurement-harness traps.** The whole-page-vs-region-filtered failure: a side harness that called `run_heuristics` on raw `PageData` instead of `resolve_page_regions(...).detection_page_data` produced a wall network the real pipeline never builds, flipped `wall_context` to `no_wall` for three s11 doors, and reported a non-existent "3 lost confirmed doors on main" (the sweep says 13/13). **Rule: any side harness must reproduce `tools/regress.py --sheet <slug>` before its numbers are used; the sweep is the arbiter.**
- **§4d — the frozen door classification table.** Every `DOOR_*` constant (103) and door-side `CROSS_*` constant (6) with its class and rationale, following §4's format. Include the arithmetic check: 33 px-valued = 19 W + 2 panel W + 12 P; 70 D. Cite the measurements: door extent ratio 0.496; leaf-panel thickness ratio 1.56; slide-panel bimodality; the CROSS needed-reach p90 table; the shrunk-world transform's unfaithfulness for ink separations.
- **§6 updates.** Mark the doors row done. Add two new deferred entries with their evidence: (a) **the Bezier aspect gate** — `DOOR_BBOX_ASPECT_MIN/MAX` [0.85, 1.15] rejects genuine 85°-sweep arcs at aspect 0.804; s06 detects 2 of 10 visible swings because of it; the polyline path already uses [0.65, 1.45] (`arcs.py:643`); dimensionless, so scale-awareness cannot fix it. (b) **the s11 assembly merge** — `door_0005`/`door_0007` (conf 0.60, at (765,1224) and (766,1640)) stay two half-width singles; the merge only fires when the paper-space `DOOR_LEAF_COMPANION_PERP_PX` is wrongly scaled, which costs 3 confirmed doors on s11, 5 on s16 and both of s06's, so it is **not** a scale bug.

- [ ] **Step 5: Regenerate the knowledge graph**

Run: `graphify update .`

- [ ] **Step 6: Commit**

```bash
git add docs/scale-normalization-findings.md graphify-out/
git commit -m "docs(scale): freeze the door constant classification

Adds the §4d door table (103 DOOR_* + 6 CROSS_*, arithmetic-checked),
the §4c harness trap that invalidated an earlier measurement, and two §6
deferred entries: the dimensionless Bezier aspect gate (s06's real miss
driver) and the s11 assembly merge (not a scale bug)."
```

- [ ] **Step 7: Report to the user and stop**

Report: the sweep's per-sheet REVIEW/LOST/RETURNED lines, the comparison against
§6's predicted table, and the review-image paths. **Do not run `tools/review.py`.**
The user verdicts the new detections personally.

---

## Self-Review

**Spec coverage.** §1 win → Tasks 2–7 + the Task 7 fixtures. §2 organising rule → the P-constant guards in Tasks 3/5. §3 retention → Task 9 Step 2. §4 panel thickness → Task 1 (comment + revisit trigger) and Task 4 (both MIN and MAX pinned). §5 CROSS_ → Task 8. §6 predicted deltas → Task 9 Step 2's table. §7 harness trap → Task 9 Step 4. Design §1 `DoorGates` → Task 1. §2 threading + no-defaults → Tasks 2–6 (`TypeError` tests in each). §3 `CrossGates` → Task 8. §4 classification → Task 1 fields + Task 9 §4d. §5 ordering → Task 1 Steps 1/3 (assert `factor > 0`, floor on `DOOR_MIN_SIZE_PX`, inversion pinned as a no-op). Testing section → Tasks 1–8 unit tests + Task 7 end-to-end. Acceptance criteria 1–5 → Task 9 Steps 1, 2, 7, 4, 5.

**Placeholders.** None. Every code step carries runnable code; every verification step carries the exact command and expected output.

**Type consistency.** `DoorGates` / `DoorGates.at` / `DOOR_GATES_UNSCALED` and `CrossGates` / `CrossGates.at` / `CROSS_GATES_UNSCALED` are used identically in every task. `detect_doors(paths, text_spans, collector=None, scale_factor=1.0)` is defined in Task 2 and called with that exact signature in Task 7. `_pair_door_assemblies` gains `*, gates` in Task 4 (noted there explicitly so Task 6 does not redefine it). Field names match their constants exactly, which is what makes the Task 6 audit grep sound.

**Known ordering wrinkle, called out.** Task 4 must add `*, gates: DoorGates` to `_pair_door_assemblies` (not just to `sliding.py`), because `assembly.py` is where `_detect_sliding_doors` is called from and the no-default rule forbids an unscaled fallback there. Task 6 then only converts assembly's own constants. This is stated in Task 4 Step 3 so an engineer reading tasks out of order does not double-implement it.
