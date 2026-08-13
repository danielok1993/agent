# Scale-Aware Window Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thread the per-page detection scale factor into window detection via a
frozen `WindowGates` dataclass whose single world-space field is
`WINDOW_MIN_WIDTH_PX` (floored `max(1.0, ·f)`), leaving the 15 paper-space px
constants and 11 dimensionless constants untouched, with exact identity at
f=1.0.

**Architecture:** Mirror the WallGates/RoomGates/DoorGates pattern:
`detect_windows` gains a defaulted-scalar `scale_factor` entry point, builds
`WindowGates.at(factor)` once, and passes it down the one consuming call chain
(`_find_openings` → `_facing_cap_pairs`) as keyword-only, non-default `gates`
parameters. `CrossGates` gains NO new field (`CROSS_WINDOW_THICKNESS_TOL_PX`
froze P). New tests live in `tests/test_scale_window_gates.py`, all rotated to
50° via the existing `_rot`/fixture helpers.

**Tech Stack:** Python 3 (`.venv/bin/python` — bare `python` is NOT on PATH),
stdlib `unittest`, the `regression` package for sweeps.

**Spec:** `docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md`
— read it first; every constant classification and every number asserted below
is derived there. Findings doc: `docs/scale-normalization-findings.md`.

## Global Constraints

- Branch: `feat/scale-aware-window-gates` (already exists, spec committed at
  039b285). Working tree must be clean before starting.
- Run tests with `.venv/bin/python -m unittest …`. The fast tier
  (`discover tests`) must stay green after every task.
- NEVER run `tools/review.py`; NEVER modify `tests/ground_truth/`,
  `fixtures/MANIFEST.json`, or any fixture bytes. New detections surface as
  REVIEW lines for the user only.
- The final sweep (`tools/regress.py`) is EXPECTED to exit 1 from documented
  pre-existing debt (findings §3 + the 2026-08-13 baseline). Do not "fix" that.
  The pass criterion is the spec's predicted delta table: every f=1.0 sheet
  identical, and the only change anywhere is ONE new REVIEW window on s16 at
  (1337,1795,1354,1801) conf 0.67.
- Commit messages: imperative subject with type prefix (`feat(windows): …`,
  `test(windows): …`, `docs(scale): …`). NEVER add a Co-Authored-By trailer.
- `graphify update .` after code changes (Task 7).
- Paper-space constants must NOT gain gates fields — if a step seems to need
  one, stop and re-read the spec instead of adding it.

---

### Task 1: `WindowGates` dataclass

**Files:**
- Modify: `detection/windows.py` (insert after the `WINDOW_MULLION_GAP_MAX_PX`
  block, before `_GRID_PX`)
- Test: `tests/test_scale_window_gates.py` (create)

**Interfaces:**
- Consumes: the module constant `WINDOW_MIN_WIDTH_PX` (14.0).
- Produces: `WindowGates` frozen dataclass with fields `factor: float`,
  `WINDOW_MIN_WIDTH_PX: float`; classmethod `WindowGates.at(factor: float) ->
  WindowGates`; module singleton `WINDOW_GATES_UNSCALED = WindowGates.at(1.0)`.
  Tasks 2–5 import all three from `detection.windows`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scale_window_gates.py`:

```python
"""Scale-aware window gates: WindowGates, threading, and the frozen
classification's behavioral contracts.

Spec: docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md.
The classification is 1 W + 15 P + 11 D: only WINDOW_MIN_WIDTH_PX scales
(the opening's empty-space extent); every other px constant is paper-space
ink and must NOT move with the factor.
"""
import math
import unittest

from detection.windows import (
    WINDOW_MIN_WIDTH_PX, WindowGates, WINDOW_GATES_UNSCALED,
)


class TestWindowGates(unittest.TestCase):
    def test_identity_at_factor_one_is_exact(self):
        g = WindowGates.at(1.0)
        self.assertEqual(g.factor, 1.0)
        self.assertEqual(g.WINDOW_MIN_WIDTH_PX, WINDOW_MIN_WIDTH_PX)
        self.assertEqual(WINDOW_GATES_UNSCALED, g)

    def test_scaling_at_half(self):
        g = WindowGates.at(0.5)
        self.assertEqual(g.WINDOW_MIN_WIDTH_PX, 7.0)

    def test_clamp_domain_bounds_construct(self):
        # The pipeline clamps f to [0.25, 4.0]; both bounds must construct
        # with the raw product (floor inert on the calibrated domain).
        self.assertEqual(WindowGates.at(0.25).WINDOW_MIN_WIDTH_PX, 3.5)
        self.assertEqual(WindowGates.at(4.0).WINDOW_MIN_WIDTH_PX, 56.0)

    def test_floor_engages_below_clamp_domain(self):
        # Backstop only: a sub-pixel width floor is never a window gate.
        self.assertEqual(WindowGates.at(0.05).WINDOW_MIN_WIDTH_PX, 1.0)

    def test_nonpositive_factor_asserts(self):
        with self.assertRaises(AssertionError):
            WindowGates.at(0.0)
        with self.assertRaises(AssertionError):
            WindowGates.at(-1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates -v`
Expected: FAIL at import — `cannot import name 'WindowGates'`.

- [ ] **Step 3: Implement `WindowGates`**

In `detection/windows.py`, after the `WINDOW_BLOCK_CAP_CROSS_RATIO` constant
block and before the `_GRID_PX` comment, insert (add
`from dataclasses import dataclass` to the imports at the top):

```python
@dataclass(frozen=True)
class WindowGates:
    """World-space window gates, pre-multiplied by the detection factor.

    Exactly ONE field: the frozen classification
    (docs/scale-normalization-findings.md §4e, measured 2026-08-13) found the
    window symbol's internal ink geometry — band depth, pane spacing, cap
    stroke lengths, span overshoots — to be paper-space (the INVERSE of
    doors), leaving the opening's empty-space extent floor as the only
    constant that scales. Paper-space and dimensionless constants
    deliberately have NO field here; absence is the audit trail. At factor
    1.0 the field equals its module constant exactly.
    """
    factor: float
    WINDOW_MIN_WIDTH_PX: float

    @classmethod
    def at(cls, factor: float) -> "WindowGates":
        assert factor > 0, "scale factor must be positive"
        # Floor mirrors DOOR_MIN_SIZE_PX's: raw product 3.5px at the f=0.25
        # clamp bound, so the floor is inert on the calibrated domain.
        return cls(factor=factor,
                   WINDOW_MIN_WIDTH_PX=max(1.0, WINDOW_MIN_WIDTH_PX * factor))


WINDOW_GATES_UNSCALED = WindowGates.at(1.0)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Fast tier green**

Run: `.venv/bin/python -m unittest discover tests -q`
Expected: OK (854 tests — 849 + the 5 new).

- [ ] **Step 6: Commit**

```bash
git add detection/windows.py tests/test_scale_window_gates.py
git commit -m "feat(windows): add the WindowGates scaled-gates dataclass"
```

---

### Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`

**Files:**
- Modify: `detection/windows.py` (`detect_windows` ~line 650,
  `_find_openings` ~line 515, `_facing_cap_pairs` ~line 460)
- Modify: `detection/orchestrator.py:48`
- Modify: `tests/test_window_detection.py` (the four `_facing_cap_pairs`
  call sites in `TestWindowPruningEquivalence`)
- Test: `tests/test_scale_window_gates.py` (extend)

**Interfaces:**
- Consumes: `WindowGates`, `WINDOW_GATES_UNSCALED` (Task 1).
- Produces: `detect_windows(paths, *, scale_factor: float = 1.0)`;
  `_find_openings(cap_pool, glaze_index, *, gates: WindowGates)`;
  `_facing_cap_pairs(caps, *, gates: WindowGates)`. Tasks 3–4 call
  `detect_windows(..., scale_factor=0.5)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scale_window_gates.py`:

```python
from detection import detect_windows
from detection.windows import _facing_cap_pairs, _find_openings, _glaze_index
from tests.test_window_detection import (
    diagonal_window, framed_triple_window, horizontal_window, vertical_window,
)


class TestThreading(unittest.TestCase):
    def test_identity_scale_factor_one_equals_omitted(self):
        # Candidate-for-candidate: bbox, confidence AND evidence must match.
        paths = (horizontal_window(100, 100.0, 176.0, 387.0)
                 + vertical_window(200, 400.0, 477.0, 303.0)
                 + diagonal_window(800, 45)
                 + framed_triple_window(500))
        base = detect_windows(paths)
        explicit = detect_windows(paths, scale_factor=1.0)
        self.assertEqual(len(base), len(explicit))
        for a, b in zip(base, explicit):
            self.assertEqual(a.bbox, b.bbox)
            self.assertEqual(a.confidence, b.confidence)
            self.assertEqual(a.evidence, b.evidence)

    def test_gates_are_keyword_only_and_required(self):
        # findings §4b: a missing gates hand-off must be a TypeError, never
        # a silent unscaled fallback.
        caps = [{"idx": 0, "perp": 0.0, "span": (0.0, 20.0), "len": 20.0},
                {"idx": 1, "perp": 50.0, "span": (0.0, 20.0), "len": 20.0}]
        with self.assertRaises(TypeError):
            list(_facing_cap_pairs(caps))
        with self.assertRaises(TypeError):
            _find_openings(caps, _glaze_index([]))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates.TestThreading -v`
Expected: `test_identity...` FAILS with `TypeError: detect_windows() got an
unexpected keyword argument 'scale_factor'`; `test_gates...` FAILS because the
calls do NOT raise TypeError yet.

- [ ] **Step 3: Implement the threading**

In `detection/windows.py`:

(a) `_facing_cap_pairs` — signature and the one gate read, hoisted to a local
(the 8c7f378 perf discipline — this loop is hot):

```python
def _facing_cap_pairs(caps: list[dict], *, gates: WindowGates) -> Iterator[tuple[int, int, float]]:
```

Inside, before the `for i, c1 in enumerate(caps):` loop add
`min_width = gates.WINDOW_MIN_WIDTH_PX`, and change the width floor line
`if width < WINDOW_MIN_WIDTH_PX:` to `if width < min_width:`. The
`WINDOW_MAX_WIDTH_PX` reads (the `limit` slack and the `break`) are paper-space
and stay module-global. Docstring: append one line — "``gates`` carries the
scaled opening-width floor; keyword-only and required (findings §4b)."

(b) `_find_openings` — pass-through:

```python
def _find_openings(cap_pool: list[dict],
                   glaze_index: tuple[dict[int, tuple[list[float], list[int]]], list[dict]],
                   *, gates: WindowGates) -> list[dict]:
```

and `for i, j, width in _facing_cap_pairs(caps, gates=gates):`. The
`WINDOW_CAP_MIN_LEN_PX`/`WINDOW_CAP_MAX_LEN_PX` pool filter is paper-space and
stays module-global.

(c) `detect_windows` — entry point (defaulted scalar, same contract as
`_cross_validate`):

```python
def detect_windows(paths: list[PathPrimitive], *,
                   scale_factor: float = 1.0) -> list[Candidate]:
```

First line of the body: `gates = WindowGates.at(scale_factor)`. Change the
opening call to
`for opening in _find_openings(caps, _glaze_index(glaze_pool), gates=gates):`.
Docstring: append — "``scale_factor`` scales the world-space gates
(`WindowGates`); 1.0 is exact identity. Only the opening-width floor scales —
the symbol's internal ink gates are paper-space (findings §4e)."

(d) `detection/orchestrator.py:48`:

```python
        windows = [] if disable_windows else detect_windows(
            page_data.paths, scale_factor=scale_factor)
```

(e) `tests/test_window_detection.py` — `TestWindowPruningEquivalence`: add
`WINDOW_GATES_UNSCALED` to the `from detection.windows import (...)` list and
change the four `_facing_cap_pairs(...)` calls (two in tests at ~lines 658/669,
two inside `_dense_glaze`/`test_spanning_glazing_index_matches_brute_force` at
~lines 690/719) to `_facing_cap_pairs(caps, gates=WINDOW_GATES_UNSCALED)`. The
`_brute_pairs` reference implementation keeps reading `WINDOW_MIN_WIDTH_PX`
directly — it is the unscaled brute force the pruning is compared against.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates tests.test_window_detection -v 2>&1 | tail -5`
Expected: all PASS.

- [ ] **Step 5: Full fast tier**

Run: `.venv/bin/python -m unittest discover tests -q`
Expected: OK. (`TestFloorPlansRegression` exercises the real s01 end-to-end
through `run_heuristics` — it passing proves orchestrator threading is
identity-safe at f=1.0.)

- [ ] **Step 6: Commit**

```bash
git add detection/windows.py detection/orchestrator.py tests/test_window_detection.py tests/test_scale_window_gates.py
git commit -m "feat(windows): thread the detection scale factor into window detection"
```

---

### Task 3: The W-row negative control at 50°

**Files:**
- Test: `tests/test_scale_window_gates.py` (extend)

**Interfaces:**
- Consumes: `detect_windows(..., scale_factor=)` (Task 2); `_rot`, `path`,
  `hline`, `vline` from `tests/test_window_detection.py`.
- Produces: module-level helper `rot_paths(prims, cx, cy, deg)` used by Task 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scale_window_gates.py`:

```python
from tests.test_window_detection import _rot, hline, path, quad, vline


def rot_paths(prims, cx, cy, deg):
    """Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)."""
    return [path(p.path_index,
                 [_rot(x, y, cx, cy, deg) for x, y in p.points],
                 item_type=p.item_type)
            for p in prims]


class TestMinWidthNegativeControl(unittest.TestCase):
    """The one world-space gate, exercised at a non-grid angle.

    A faithful 1:100 export of a small window: opening width 10px (a 20px
    1:50 window shrunk), ink held at paper values — 3 panes at 2.5px gaps
    (depth 5), 5px caps. Missed at f=1.0 (10 < 14), detected at f=0.5
    (10 >= 7). Fails if the gates threading is removed.
    """

    def _fixture(self, deg=50):
        prims = [
            hline(0, 395.0, 405.0, 397.5),
            hline(1, 395.0, 405.0, 400.0),
            hline(2, 395.0, 405.0, 402.5),
            vline(3, 397.5, 402.5, 395.0),   # cap, 5px
            vline(4, 397.5, 402.5, 405.0),   # cap, 5px
        ]
        return rot_paths(prims, 400.0, 400.0, deg)

    def test_missed_at_identity(self):
        self.assertEqual(detect_windows(self._fixture()), [])

    def test_detected_at_half_scale(self):
        wins = detect_windows(self._fixture(), scale_factor=0.5)
        self.assertEqual(len(wins), 1, f"got {[c.bbox for c in wins]}")
        # Evidence continuity: rooms' _window_seal consumes these (s13 W11).
        from detection.geometry import _angle_diff_mod180
        self.assertEqual(wins[0].evidence["orientation"], "diagonal")
        self.assertLessEqual(
            _angle_diff_mod180(wins[0].evidence["glazing_angle_deg"], 50.0), 4.0)
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)
```

- [ ] **Step 2: Run to verify the failure mode is the right one**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates.TestMinWidthNegativeControl -v`
Expected: both tests PASS immediately (Task 2 already implemented threading).
Then verify the negative control actually discriminates: temporarily change
`_facing_cap_pairs`'s local back to `WINDOW_MIN_WIDTH_PX` (simulating removed
threading), rerun, and confirm `test_detected_at_half_scale` FAILS; revert.

- [ ] **Step 3: Run the file**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates -v 2>&1 | tail -3`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add tests/test_scale_window_gates.py
git commit -m "test(windows): pin the scaled opening-width floor with a rotated negative control"
```

---

### Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°

**Files:**
- Test: `tests/test_scale_window_gates.py` (extend)

**Interfaces:**
- Consumes: `rot_paths` (Task 3), `detect_windows(..., scale_factor=0.5)`.
- Produces: nothing downstream; these tests ARE the spec's paper-invariance
  contract.

Every fixture is a "faithful 1:100 export": extents sized like a shrunk
opening, INK HELD AT PAPER VALUES, rotated 50°. Each asserts behavior at
`scale_factor=0.5` that breaks if its named constants are ever scaled.

- [ ] **Step 1: Write the tests**

Append:

```python
class TestPaperInvariance(unittest.TestCase):
    """One fixture per paper-space family (spec §Testing). Each fails if its
    named constant is wrongly given a WindowGates field."""

    def _detect(self, prims, cx=400.0, cy=400.0):
        return detect_windows(rot_paths(prims, cx, cy, 50), scale_factor=0.5)

    def test_adj_spacing_held_at_paper(self):
        # WINDOW_GLAZING_ADJ_SPACING_PX: s16's 8.25px convention at f=0.5.
        # Scaled (4.25) the band breaks and the window dies.
        prims = [hline(0, 380.0, 420.0, 395.875), hline(1, 380.0, 420.0, 404.125),
                 vline(2, 391.15, 408.85, 380.0), vline(3, 391.15, 408.85, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_band_depth_held_at_paper(self):
        # WINDOW_GLAZING_THICKNESS_PX: s13's 13px-deep 3-pane convention.
        # Scaled (8) the band truncates to its 2-pane suffix — assert on the
        # pane count, since the truncated window can still detect.
        prims = [hline(0, 380.0, 420.0, 393.5), hline(1, 380.0, 420.0, 400.0),
                 hline(2, 380.0, 420.0, 406.5),
                 vline(3, 393.0, 407.0, 380.0), vline(4, 393.0, 407.0, 420.0)]
        wins = self._detect(prims)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)

    def test_cap_length_held_at_paper(self):
        # WINDOW_CAP_MAX_LEN_PX: 22px caps (s01 convention) with a shrunk
        # 40px opening. Scaled (18) the caps leave the pool and nothing pairs.
        prims = [hline(0, 380.0, 420.0, 396.5), hline(1, 380.0, 420.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_two_line_min_cap_not_scaled(self):
        # WINDOW_TWO_LINE_MIN_CAP_PX: a 2-pane sliver with 9px caps must stay
        # REJECTED at f=0.5 (9 < 12). Scaled (6) it would be admitted.
        prims = [hline(0, 390.0, 410.0, 398.5), hline(1, 390.0, 410.0, 401.5),
                 vline(2, 395.5, 404.5, 390.0), vline(3, 395.5, 404.5, 410.0)]
        self.assertEqual(self._detect(prims), [])

    def test_distinct_eps_not_scaled(self):
        # WINDOW_GLAZING_DISTINCT_EPS: a double-struck pane (1.2px apart)
        # must still dedupe to ONE pane at f=0.5. Scaled (0.75) it splits and
        # the pane count inflates to 3.
        prims = [hline(0, 380.0, 420.0, 398.0), hline(1, 380.0, 420.0, 399.2),
                 hline(2, 380.0, 420.0, 402.2),
                 vline(3, 393.0, 407.0, 380.0), vline(4, 393.0, 407.0, 420.0)]
        wins = self._detect(prims)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].evidence["glazing_lines"], 2)

    def test_tight_pair_gates_not_scaled(self):
        # WINDOW_TIGHT_PAIR_GAP_PX + WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX: a
        # doubled-material-edge FP (2.0px pair, jamb margin 1.0 via the
        # asymmetric caps) must stay rejected at f=0.5. Scaling EITHER gate
        # admits it (gap 2.0 >= 1.375 skips the test; margin 1.0 >= 0.75
        # passes it).
        prims = [hline(0, 380.0, 420.0, 399.0), hline(1, 380.0, 420.0, 401.0),
                 vline(2, 398.0, 410.0, 380.0), vline(3, 398.0, 410.0, 420.0)]
        self.assertEqual(self._detect(prims), [])

    def test_span_overshoot_held_at_paper(self):
        # WINDOW_SPAN_OVERSHOOT_PX: glazing overshooting each cap by 9px
        # (confirmed 1:100 windows reach 9.38) must still span. Scaled (6)
        # the panes are excluded and the window dies.
        prims = [hline(0, 371.0, 429.0, 396.5), hline(1, 371.0, 429.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_span_cover_tol_held_at_paper(self):
        # WINDOW_SPAN_COVER_TOL_PX: glazing falling 3.4px short of each cap
        # (confirmed tiers reach 3.38-3.55) must still span. Scaled (2) it dies.
        prims = [hline(0, 383.4, 416.6, 396.5), hline(1, 383.4, 416.6, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_span_perp_tol_held_at_paper(self):
        # WINDOW_SPAN_PERP_TOL_PX: a pane sitting 1.5px outside the caps'
        # facing extent must still join the band (tol 2.0). Scaled (1.0) it
        # is excluded, the band drops to one pane, and the window dies.
        prims = [hline(0, 380.0, 420.0, 389.5),   # 1.5px above the cap span
                 hline(1, 380.0, 420.0, 396.5),
                 vline(2, 391.0, 408.0, 380.0),   # caps span y 391..408
                 vline(3, 391.0, 408.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_interior_band_pad_held_at_paper(self):
        # WINDOW_INTERIOR_BAND_PAD_PX: a hatched wall whose crosshatch quads
        # sit 1.0px outside the pane band must still be REJECTED (pad 1.5
        # sweeps them into the interior scan; 2 shapes > SHAPE_MAX 1).
        # Scaled (0.75) the pad no longer reaches them and the FP is admitted.
        prims = [hline(0, 380.0, 420.0, 396.5), hline(1, 380.0, 420.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0),
                 quad(4, 390.0, 404.5, 394.0, 404.7),
                 quad(5, 400.0, 404.5, 404.0, 404.7)]
        self.assertEqual(self._detect(prims), [])

    def test_framed_multi_light_ink_held_at_paper(self):
        # WINDOW_BLOCK_CAP_MAX_THICK_PX + WINDOW_MULLION_GAP_MAX_PX: a
        # half-width three-light frame whose block bars keep their 6px
        # thickness and 11.5px mullion gaps. Scaled (4 / 7) the blocks stop
        # being caps / the chains stop bridging.
        prims = [
            hline(0, 926.2, 1057.2, 267.2),                 # top rail
            hline(1, 926.2, 1057.2, 282.0),                 # bottom rail
            quad(2, 926.2, 267.2, 932.2, 282.0),            # left end cap
            quad(3, 1051.2, 267.2, 1057.2, 282.0),          # right end cap
            quad(4, 968.2, 267.2, 974.2, 282.0),            # mullion pair 1
            quad(5, 974.2, 267.2, 979.7, 282.0),
            quad(6, 1011.2, 267.2, 1017.2, 282.0),          # mullion pair 2
            quad(7, 1017.2, 267.2, 1022.7, 282.0),
            hline(8, 932.2, 968.2, 274.7),                  # center, light 1
            hline(9, 979.7, 1011.2, 274.7),                 # center, light 2
            hline(10, 1022.7, 1051.2, 274.7),               # center, light 3
        ]
        wins = detect_windows(rot_paths(prims, 990.0, 275.0, 50),
                              scale_factor=0.5)
        self.assertEqual(len(wins), 1, f"got {[c.bbox for c in wins]}")
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)
        self.assertEqual(wins[0].evidence["lights"], 3)
```

- [ ] **Step 2: Run and fix fixture geometry if needed**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates.TestPaperInvariance -v`
Expected: all PASS on the first run — these assert CURRENT behavior at f=0.5
(nothing but MIN_WIDTH scales, and every fixture's width clears both 14 and 7).
If any fails, the fixture geometry is off (check cap-span coverage of the band,
`WINDOW_MIN_WIDTH_CAP_RATIO` — width ≥ 1.5 × cap length — and span cover);
adjust the fixture, never the detector.

- [ ] **Step 3: Verify each fixture discriminates**

One-off sanity (do not commit any of this): in `detection/windows.py`
temporarily multiply each named constant by 0.5 in turn (edit the constant
line), rerun the matching test, confirm it FAILS, revert. Batch check:

```bash
for c in WINDOW_GLAZING_ADJ_SPACING_PX WINDOW_GLAZING_THICKNESS_PX \
         WINDOW_CAP_MAX_LEN_PX WINDOW_TWO_LINE_MIN_CAP_PX \
         WINDOW_GLAZING_DISTINCT_EPS WINDOW_TIGHT_PAIR_GAP_PX \
         WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX \
         WINDOW_SPAN_OVERSHOOT_PX WINDOW_SPAN_COVER_TOL_PX \
         WINDOW_SPAN_PERP_TOL_PX WINDOW_INTERIOR_BAND_PAD_PX \
         WINDOW_BLOCK_CAP_MAX_THICK_PX WINDOW_MULLION_GAP_MAX_PX; do
  .venv/bin/python - <<EOF
import detection.windows as W
setattr(W, "$c", getattr(W, "$c") * 0.5)
import unittest
r = unittest.main(module="tests.test_scale_window_gates",
                  defaultTest="TestPaperInvariance", exit=False)
print("$c:", "DISCRIMINATES" if not r.result.wasSuccessful() else "NOT CAUGHT")
EOF
done
```

Expected: every line prints DISCRIMINATES. If a constant is NOT CAUGHT,
tighten the matching fixture until it is — never weaken the detector.

- [ ] **Step 4: Full fast tier**

Run: `.venv/bin/python -m unittest discover tests -q`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add tests/test_scale_window_gates.py
git commit -m "test(windows): pin every paper-space window gate with rotated invariance controls"
```

---

### Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it

**Files:**
- Modify: `detection/postprocess.py` (comment only, at the constant)
- Test: `tests/test_scale_window_gates.py` (extend)

**Interfaces:**
- Consumes: `_cross_validate(candidates, network, *, scale_factor)` from
  `detection.postprocess`; `h_wall_with_gap` from `tests/test_cross_validate`.
- Produces: nothing downstream.

- [ ] **Step 1: Write the failing-if-ever-scaled test**

Append:

```python
from models import Candidate
from detection.postprocess import CROSS_WINDOW_ON_WALL_BOOST, _cross_validate
from tests.test_cross_validate import h_wall_with_gap


class TestCrossWindowToleranceUnscaled(unittest.TestCase):
    """CROSS_WINDOW_THICKNESS_TOL_PX froze P (spec Evidence 5): the mismatch
    it tolerates is cap-ink overshoot, which is paper-space. The boost must
    fire identically at f=1.0 and f=0.5 for a 5px mismatch (inside 6.0,
    outside a wrongly-scaled 3.0). CrossGates must NOT gain this field."""

    def _window_over_gap(self):
        # h_wall_with_gap: horizontal run at y=104, thickness 16, gap x
        # 200-260. Window bbox short side 21 -> mismatch |21 - 16| = 5.
        return Candidate("window_0000", "window",
                         (205.0, 93.5, 255.0, 114.5), 0.70, {})

    def test_boost_fires_at_both_factors(self):
        network = h_wall_with_gap(thickness=16.0)
        for factor in (1.0, 0.5):
            out = _cross_validate([self._window_over_gap()], network,
                                  scale_factor=factor)
            self.assertEqual(out[0].evidence["wall_context"],
                             "spans_wall_thickness", f"factor {factor}")
            self.assertEqual(out[0].confidence,
                             round(0.70 + CROSS_WINDOW_ON_WALL_BOOST, 3),
                             f"factor {factor}")
```

- [ ] **Step 2: Run to verify pass, then verify it discriminates**

Run: `.venv/bin/python -m unittest tests.test_scale_window_gates.TestCrossWindowToleranceUnscaled -v`
Expected: PASS. Then temporarily change the tolerance use in
`detection/postprocess.py` to `CROSS_WINDOW_THICKNESS_TOL_PX * gates.factor`
(CrossGates carries `factor`), rerun, confirm the f=0.5 case FAILS
(mismatch 5 > 3.0), revert.

- [ ] **Step 3: Add the pointer comment**

In `detection/postprocess.py`, extend the constant's line:

```python
CROSS_WINDOW_THICKNESS_TOL_PX = 6.0  # frozen P (findings §4e): the mismatch it
                                     # tolerates is cap-ink overshoot beyond the
                                     # wall band — paper-space, measured bimodal
                                     # (~0 or >>6) at every scale tier. NOT a
                                     # CrossGates field; scaling it is pinned
                                     # off by TestCrossWindowToleranceUnscaled.
```

- [ ] **Step 4: Fast tier + commit**

Run: `.venv/bin/python -m unittest discover tests -q` → OK.

```bash
git add detection/postprocess.py tests/test_scale_window_gates.py
git commit -m "test(windows): pin the cross-validation thickness tolerance as paper-space"
```

---

### Task 6: Findings doc — §4e frozen table, §6 entries

**Files:**
- Modify: `docs/scale-normalization-findings.md`

**Interfaces:** none (docs). The spec's Evidence sections are the source; copy
numbers verbatim from `docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md`.

- [ ] **Step 1: Insert §4e after §4d's table**

Add a new section titled `## 4e. Window constant classification table (frozen 2026-08-13)`
containing, in this order (all content exists in the spec — this step is
transcription, not authorship):

1. Preamble: same class definitions as §4d; status **frozen**; pointer to the
   window spec for full derivations; the headline sentence "the INVERSE of
   doors: the window symbol's internal ink geometry is paper-space; only the
   opening's own empty-space extent scales."
2. The arithmetic check: 27 = 16 px (1 W + 15 P) + 11 D; window-side CROSS_*
   additional (`CROSS_WINDOW_THICKNESS_TOL_PX` P, `CROSS_WINDOW_ON_WALL_BOOST` D).
3. Key measurements: the ratio table (pane gap 0.587-as-paper-floor with the
   mm argument, depth 1.06, cap length 1.10, span 0.93, width 0.95-confounded);
   the retention-veto table (caps 24.75 vs 18; width 210.76 vs 140 and 103.94
   vs 102.65; depth 14.25 vs 8; gaps 8.25 vs 4.25; span tails 9.38/10.5 vs 12
   and 3.38/3.55 vs 4); the variant matrix summary (90/90 under MIN_WIDTH-only
   with exactly +1 s16 REVIEW window; 50/54/61 lost under
   maxgates/separations/blanket; V_cross exact zero delta; CAP_MIN_LEN scaling
   = 2× s16 stage cost for zero detection change).
4. The per-constant table: one row per WINDOW_* constant (all 27) with class
   and one-line rationale, copied from the spec's Design §3 groupings, plus
   the two CROSS_* rows.
5. The audit block: `_GRID_PX` layout; `_GLAZE_U_BIN_PX` parents-both-P;
   `_CAP_V_BIN_PX` correctness coupling with the explicit warning that a
   future W-reclassification of `WINDOW_CAP_MAX_LEN_PX` must move the bin
   into the gates path in the same change; the out-of-block literal list;
   the note that `WINDOW_GLAZING_DISTINCT_EPS` is px-valued without a `_PX`
   suffix (census-methodology blind spot, COLLINEAR_OFFSET_TOL's shape).
6. The harness note: taps + in-process `regression.sweep.sweep()` — the
   harness IS the sweep, §4c satisfied by construction; taps verified
   byte-inert and fully reverted before implementation.

- [ ] **Step 2: Update §6**

In §6 "Deferred work": mark the **Windows** bullet DONE (mirroring the doors
bullet's format — branch name, date, "1 W + 15 P + 11 D via WindowGates;
frozen table at §4e; predicted delta: s16 +1 REVIEW window only") and add
four new bullets:

- **Windows — span-overshoot retune (paper-space, NOT scale):** confirmed
  windows overshoot ≤ 9.38px (f05) / 10.5px (f10_50); the s12/s18 phantom
  windows sit at 11.75–11.98px against the 12.0 gate — a retune to ~10.5–11px
  could kill those FP families at zero measured confirmed cost. Changes 1:50
  sheets too → own branch with its own sweep.
- **Windows — NMS constants:** `NMS_CENTER_DIST_PX` / `NMS_PROJ_PERP_MAX_PX`
  (postprocess) deliberately unclassified — shared cross-type suppression
  machinery; scaling them moves every entity type at once.
- **Windows — revisit triggers for frozen-P rows:** `WINDOW_BLOCK_CAP_MAX_THICK_PX`
  / `WINDOW_MULLION_GAP_MAX_PX` (a 1:100 sheet drawing framed multi-light
  windows — no such sheet exists in the corpus, the convention split is by
  drawing house, not scale); `WINDOW_INTERIOR_BAND_PAD_PX` (a real 1:100
  window rejected by the interior-clutter gate — observed only on the
  synthetic shrunk world).
- **Window tuning guide staleness:** guide §4 lists `WINDOW_CAP_MAX_LEN_PX`
  34 vs the code's 36 and pre-dates the rotation-general rewrite (§6 still
  says "diagonal not handled"); a `docs/window-guide-refresh` branch exists.

- [ ] **Step 3: Commit**

```bash
git add docs/scale-normalization-findings.md
git commit -m "docs(scale): freeze the window constant classification"
```

---

### Task 7: graphify, perf re-profile, full regression sweep vs the predicted table

**Files:**
- None modified (verification only; graphify-out/ regenerated).

**Interfaces:** consumes everything above.

- [ ] **Step 1: graphify update**

Run: `graphify update .`
Expected: completes without error (AST-only).

- [ ] **Step 2: Perf re-profile at f=1.0 (the 8c7f378 watch)**

```bash
.venv/bin/python - <<'EOF'
import sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
from regression.sweep import sweep
sweep(["s16", "s18"])
EOF
```

Read the `detection.orchestrator windows:` lines. Expected: s16 ≈ 4.5 s,
s18 ≈ 6.1 s — parity with the campaign baseline (4.46 / 6.12; the measured
band for unchanged code across that campaign's repeat runs was ±3%). If either
exceeds 1.25× baseline, STOP and investigate before proceeding (do not
rationalize it as noise — rerun once to check machine load, then profile).

- [ ] **Step 3: Full sweep**

Run: `.venv/bin/python tools/regress.py`
Expected: **exit 1** (documented pre-existing debt — NOT this branch's
regression). Verify against the spec's predicted table, line by line:

- Every f=1.0 sheet (s01 s02 s03 s04 s08 s10 s14 s15 s17 s20 + unlabeled
  s09/s19) identical to the 2026-08-13 baseline: same counts, same
  lost/returned/REVIEW lines at the same bboxes.
- s05 s06 s07 s11 s12 s18 s13: identical to baseline (windows: s05 none,
  s06 8/8, s07 10/10, s11 27/27, s12 0 confirmed with FP 21→21,
  s18 11/11 with FP 12→12, s13 11/11 with FP 3→3).
- s16: 23/23 windows kept PLUS exactly one new REVIEW line — a window at
  (1337, 1795, 1354, 1801), conf 0.67. No other REVIEW line anywhere. No
  door or room change on any sheet.

Any divergence from this table is a finding to investigate before handover —
per the spec, "not a result to hand over."

- [ ] **Step 4: Report and stop**

Report to the user: the sweep outcome vs the predicted table, the s16 REVIEW
window's review image path
(`outputs/regress/s16/<timestamp>/pages/page_01/review_window.png`), and the
perf numbers. **Do not run `tools/review.py`; do not touch ground truth.** The
user verdicts the REVIEW window personally. Merging/finishing the branch is a
separate decision after that verdict.
