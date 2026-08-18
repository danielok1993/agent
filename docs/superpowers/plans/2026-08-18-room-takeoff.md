# Room Quantity Takeoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn detected room polygons + resolved drawing scale + user-supplied heights into per-room floor / ceiling / net-wall areas in metres, written to `takeoff.json`.

**Architecture:** A new pure package `takeoff/` (units, heights, scale selection/verification, opening assignment, quantities) consumed by `pipeline.run_extract` right after `finalize_candidates`. Detection code is untouched; the regression sweep is unaffected by construction. Heights resolve once per run (flag → tty prompt → default) and every quantity block carries its scale provenance and a `verified` flag.

**Tech Stack:** Python 3, shapely (already a dependency via `detection/rooms.py`), `unittest` (`python -m unittest discover tests`).

**Spec:** `docs/superpowers/specs/2026-08-18-room-takeoff-design.md`

## Global Constraints

- One pixel is `25.4 / 150` mm on paper (150-DPI pixel space everywhere past `extraction/`); `mm_per_px = 0.16933 × D`.
- D is `ScaleInfo.nominal` when not None, else `ScaleInfo.denominator` (mirrors `scale/factor.py::_effective_denominator`). Never guess a denominator: no D → no numbers.
- Standoff correction: buffer room polygons out by `detection.rooms.ROOM_WALL_DILATE_PX` (2.0) with mitre joins before measuring.
- Opening assignment: the standoff-corrected room polygon buffered by a further `ROOM_OPENING_SEAL_PX` (12 px; 14 px total from the detected polygon) intersects the opening bbox. Assignment runs over EVERY valid room; deductions only for scaled rooms.
- Room polygons are the filled exterior ring (`detection/rooms.py:1214` fills interior holes — they are fixture islands, which ARE floor for a finishes takeoff); no hole subtraction, recorded as assumption `holes_filled`.
- Heights must be positive, finite metres: `resolve_heights` raises `ValueError` on a bad explicit value; the CLI rejects it at parse time (`positive_metres`).
- `det_scale` is a fallback ONLY for a room in no `floor_plan` region (or one with no `by_region` entry); a room whose region is explicitly `unresolved` stays unscaled — on mixed-scale pages `det_scale` is another plan's scale.
- Height defaults: ceiling 2.4 m, door 2.1 m, window 1.2 m; precedence flag → prompt → default; prompt only for the ceiling, only when the caller allows prompting AND `scale.prompt.can_prompt()` is true.
- Rounding: 2 dp on m / m², 3 dp on `mm_per_px`.
- Warning codes: `TAKEOFF_NO_SCALE` (warning), `SCALE_UNVERIFIED` (info), `SCALE_PRINT_RESIZED` (warning), `TAKEOFF_OPENING_TALLER_THAN_CEILING` (info). One per page per code.
- Commits: never add a `Co-Authored-By` trailer. Work on branch `feat/room-takeoff` (already created; spec committed there).
- Run `python -m unittest discover tests` before every commit; it must stay green (~10 s).

---

## File structure

| File | Responsibility |
|---|---|
| `takeoff/__init__.py` | re-export `compute_takeoff`, `TakeoffPage`, `Heights`, `resolve_heights` |
| `takeoff/units.py` | pixel↔metre conversion, effective denominator |
| `takeoff/heights.py` | `Heights` dataclass, defaults, `resolve_heights` (flag/prompt/default) |
| `takeoff/scale.py` | per-room scale selection (`select_room_scale`), sheet-size verification (`verify_sheet_size`, `sheet_size_tokens`) |
| `takeoff/openings.py` | opening width from evidence/bbox, opening→room assignment |
| `takeoff/quantities.py` | `compute_takeoff` → `TakeoffPage` (+ `to_dict`), warnings |
| `pipeline.py` | resolve heights once, call `compute_takeoff` per page, write `takeoff.json`, mirror onto room entities, summary totals, warnings |
| `app.py` | `--ceiling-height`, `--door-height`, `--window-height` |
| `batch_extract.py` | ask for ceiling height once, forward `--ceiling-height` |
| `tests/test_takeoff_units.py`, `tests/test_takeoff_heights.py`, `tests/test_takeoff_scale.py`, `tests/test_takeoff_openings.py`, `tests/test_takeoff_quantities.py`, `tests/test_takeoff_pipeline.py` | fast tier |
| `CLAUDE.md` | commands, output layout, module layout |

---

### Task 1: Units

**Files:**
- Create: `takeoff/__init__.py`, `takeoff/units.py`
- Test: `tests/test_takeoff_units.py`

**Interfaces:**
- Produces:
  - `MM_PER_PX_AT_1_1: float = 25.4 / 150`
  - `effective_denominator(info) -> Optional[float]` — `info` has `.nominal` and `.denominator` (a `models.ScaleInfo`); nominal beats raw; None when both None or `info` is None
  - `mm_per_px(denominator: float) -> float`
  - `px_to_m(px: float, denominator: float) -> float`
  - `px2_to_m2(px2: float, denominator: float) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_units.py
import unittest

from models import ScaleInfo
from takeoff.units import (
    MM_PER_PX_AT_1_1, effective_denominator, mm_per_px, px_to_m, px2_to_m2,
)


class TestUnits(unittest.TestCase):
    def test_one_pixel_is_150dpi_paper(self):
        self.assertAlmostEqual(MM_PER_PX_AT_1_1, 0.16933, places=5)

    def test_mm_per_px_scales_with_denominator(self):
        self.assertAlmostEqual(mm_per_px(50.0), 8.4667, places=3)
        self.assertAlmostEqual(mm_per_px(100.0), 16.933, places=3)

    def test_118px_at_1_50_is_one_metre(self):
        self.assertAlmostEqual(px_to_m(118.11, 50.0), 1.0, places=3)

    def test_13948px2_at_1_50_is_one_square_metre(self):
        self.assertAlmostEqual(px2_to_m2(13948.0, 50.0), 1.0, places=3)

    def test_area_at_1_100_is_four_times_smaller_per_px2(self):
        self.assertAlmostEqual(px2_to_m2(13948.0, 100.0), 4.0, places=3)


class TestEffectiveDenominator(unittest.TestCase):
    def test_nominal_beats_raw(self):
        info = ScaleInfo(denominator=49.8, source="text", nominal=50.0)
        self.assertEqual(effective_denominator(info), 50.0)

    def test_raw_when_no_nominal(self):
        info = ScaleInfo(denominator=136.4, source="viewport", nominal=None)
        self.assertEqual(effective_denominator(info), 136.4)

    def test_unresolved_is_none(self):
        self.assertIsNone(effective_denominator(
            ScaleInfo(denominator=None, source="unresolved")))
        self.assertIsNone(effective_denominator(None))
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_units -v`
Expected: `ModuleNotFoundError: No module named 'takeoff'`

- [ ] **Step 3: Implement**

```python
# takeoff/__init__.py
"""Quantity takeoff — rooms + scale + heights → floor / ceiling / wall areas."""
```

```python
# takeoff/units.py
"""Pixel ↔ metre conversion.

Everything downstream of extraction/extractor.py is 150-DPI pixel space, so a
pixel is 25.4/150 mm on paper. A drawing at 1:D puts D real mm in every paper
mm. This module knows nothing about pages or rooms — pure arithmetic.
"""
from __future__ import annotations

from typing import Optional

MM_PER_PX_AT_1_1 = 25.4 / 150.0   # 0.16933 mm of paper per pixel


def effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute exactly (scale/factor.py rule)."""
    if info is None:
        return None
    if getattr(info, "nominal", None) is not None:
        return float(info.nominal)
    if getattr(info, "denominator", None) is not None:
        return float(info.denominator)
    return None


def mm_per_px(denominator: float) -> float:
    return MM_PER_PX_AT_1_1 * denominator


def px_to_m(px: float, denominator: float) -> float:
    return px * mm_per_px(denominator) / 1000.0


def px2_to_m2(px2: float, denominator: float) -> float:
    side = mm_per_px(denominator) / 1000.0
    return px2 * side * side
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_units -v`
Expected: 8 tests OK

- [ ] **Step 5: Commit**

```bash
git add takeoff/__init__.py takeoff/units.py tests/test_takeoff_units.py
git commit -m "feat(takeoff): pixel-to-metre unit model"
```

---

### Task 2: Heights

**Files:**
- Create: `takeoff/heights.py`
- Test: `tests/test_takeoff_heights.py`

**Interfaces:**
- Consumes: `scale.prompt.can_prompt` (existing).
- Produces:
  - `DEFAULT_CEILING_M = 2.4`, `DEFAULT_DOOR_M = 2.1`, `DEFAULT_WINDOW_M = 1.2`
  - `@dataclass(frozen=True) Heights(ceiling_m: float, door_m: float, window_m: float, sources: dict)` where `sources == {"ceiling": "flag"|"prompt"|"default", "door": ..., "window": ...}`; method `to_dict()` → `{"ceiling_m", "door_m", "window_m", "source": sources}`
  - `resolve_heights(ceiling: Optional[float], door: Optional[float], window: Optional[float], allow_prompt: bool = True, can_prompt_fn=can_prompt, input_fn=input, output_fn=print) -> Heights`
  - `parse_height(answer: str) -> Optional[float]` — accepts "2.4", "2400" (mm → m when ≥ 100), "2.4m"; None on blank/nonsense/≤0.
  - `valid_height_m(value: float, name: str) -> float` — returns the float when `0 < value < inf` and not NaN; else raises `ValueError(f"{name} height must be a positive finite number of metres, got {value!r}")`. `resolve_heights` runs every explicit (non-None) flag through it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_heights.py
import unittest

from takeoff.heights import (
    DEFAULT_CEILING_M, DEFAULT_DOOR_M, DEFAULT_WINDOW_M,
    Heights, parse_height, resolve_heights, valid_height_m,
)


class TestParseHeight(unittest.TestCase):
    def test_metres(self):
        self.assertEqual(parse_height("2.4"), 2.4)
        self.assertEqual(parse_height(" 2.7 m "), 2.7)

    def test_millimetres_are_converted(self):
        self.assertEqual(parse_height("2400"), 2.4)
        self.assertEqual(parse_height("2400mm"), 2.4)

    def test_blank_and_nonsense_and_nonpositive_are_none(self):
        for bad in ("", "   ", "tall", "0", "-2", None):
            self.assertIsNone(parse_height(bad), bad)


class TestResolveHeights(unittest.TestCase):
    def test_flags_win_and_are_recorded(self):
        h = resolve_heights(2.7, 2.0, 1.5, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual((h.ceiling_m, h.door_m, h.window_m), (2.7, 2.0, 1.5))
        self.assertEqual(h.sources, {"ceiling": "flag", "door": "flag", "window": "flag"})

    def test_prompt_only_for_ceiling_when_tty(self):
        asked = []
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda q: asked.append(q) or "2.6",
                            output_fn=lambda *_: None)
        self.assertEqual(len(asked), 1)
        self.assertEqual(h.ceiling_m, 2.6)
        self.assertEqual(h.sources["ceiling"], "prompt")
        self.assertEqual((h.door_m, h.window_m), (DEFAULT_DOOR_M, DEFAULT_WINDOW_M))
        self.assertEqual(h.sources["door"], "default")

    def test_no_prompt_without_tty(self):
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: False,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual(h.ceiling_m, DEFAULT_CEILING_M)
        self.assertEqual(h.sources["ceiling"], "default")

    def test_no_prompt_when_caller_forbids(self):
        h = resolve_heights(None, None, None, allow_prompt=False,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual(h.sources["ceiling"], "default")

    def test_blank_answer_and_eof_fall_to_default(self):
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: "", output_fn=lambda *_: None)
        self.assertEqual(h.sources["ceiling"], "default")

        def eof(_):
            raise EOFError
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=eof, output_fn=lambda *_: None)
        self.assertEqual(h.sources["ceiling"], "default")

    def test_to_dict_shape(self):
        d = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default",
                                     "window": "default"}).to_dict()
        self.assertEqual(set(d), {"ceiling_m", "door_m", "window_m", "source"})

    def test_invalid_flags_raise(self):
        for bad in (0.0, -2.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                resolve_heights(bad, None, None, allow_prompt=False)
            with self.assertRaises(ValueError):
                resolve_heights(None, bad, None, allow_prompt=False)
            with self.assertRaises(ValueError):
                resolve_heights(None, None, bad, allow_prompt=False)

    def test_valid_height_m(self):
        self.assertEqual(valid_height_m(2.4, "ceiling"), 2.4)
        with self.assertRaises(ValueError):
            valid_height_m(float("nan"), "ceiling")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_heights -v`
Expected: `ModuleNotFoundError: No module named 'takeoff.heights'`

- [ ] **Step 3: Implement**

```python
# takeoff/heights.py
"""Wall / opening heights — the one input the plan cannot supply.

0/20 corpus sheets carry a numeric ceiling height (measured 2026-08-18), so
heights come from the user: flag → tty prompt → default. The prompt is asked
once per run for the ceiling only, and shares the scale prompt's tty gate so
batch_extract and regress.py never block. `"drawing"` is a reserved source
value for a future text/section reader; nothing here emits it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Optional

from scale.prompt import can_prompt

DEFAULT_CEILING_M = 2.4
DEFAULT_DOOR_M = 2.1
DEFAULT_WINDOW_M = 1.2

_HEIGHT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(m|mm)?\s*$", re.I)


@dataclass(frozen=True)
class Heights:
    ceiling_m: float
    door_m: float
    window_m: float
    sources: dict   # {"ceiling": "flag"|"prompt"|"default", "door": ..., "window": ...}

    def to_dict(self) -> dict:
        return {"ceiling_m": self.ceiling_m, "door_m": self.door_m,
                "window_m": self.window_m, "source": dict(self.sources)}


def parse_height(answer: Optional[str]) -> Optional[float]:
    """Metres from "2.4", "2.4m", "2400", "2400mm". None to skip."""
    m = _HEIGHT_RE.match(answer or "")
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit == "mm" or (unit == "" and value >= 100):
        value = value / 1000.0
    return value if value > 0 else None


def valid_height_m(value, name: str) -> float:
    """A positive, finite number of metres — or ValueError naming the offender."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = float("nan")
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} height must be a positive finite number of metres, got {value!r}")
    return v


def _prompt_ceiling(input_fn, output_fn) -> Optional[float]:
    output_fn("No ceiling height on the drawing.")
    try:
        answer = input_fn(f"  Ceiling height in m (blank for {DEFAULT_CEILING_M}): ")
    except (EOFError, KeyboardInterrupt):
        return None
    return parse_height(answer)


def resolve_heights(
    ceiling: Optional[float],
    door: Optional[float],
    window: Optional[float],
    allow_prompt: bool = True,
    can_prompt_fn: Callable[[], bool] = can_prompt,
    input_fn=input,
    output_fn=print,
) -> Heights:
    sources = {}
    if ceiling is not None:
        ceiling, sources["ceiling"] = valid_height_m(ceiling, "ceiling"), "flag"
    else:
        answered = None
        if allow_prompt and can_prompt_fn():
            answered = _prompt_ceiling(input_fn, output_fn)
        if answered is not None:
            ceiling, sources["ceiling"] = answered, "prompt"
        else:
            ceiling, sources["ceiling"] = DEFAULT_CEILING_M, "default"

    if door is not None:
        door, sources["door"] = valid_height_m(door, "door"), "flag"
    else:
        door, sources["door"] = DEFAULT_DOOR_M, "default"

    if window is not None:
        window, sources["window"] = valid_height_m(window, "window"), "flag"
    else:
        window, sources["window"] = DEFAULT_WINDOW_M, "default"

    return Heights(float(ceiling), float(door), float(window), sources)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_heights -v`
Expected: 11 tests OK

- [ ] **Step 5: Commit**

```bash
git add takeoff/heights.py tests/test_takeoff_heights.py
git commit -m "feat(takeoff): heights — flag, tty prompt, default"
```

---

### Task 3: Per-room scale selection and sheet-size verification

**Files:**
- Create: `takeoff/scale.py`
- Test: `tests/test_takeoff_scale.py`

**Interfaces:**
- Consumes: `takeoff.units.effective_denominator`; `models.Region` (`.region_id`, `.bbox`, `.region_type`); `scale.resolver.PageScales` (`.by_region: dict[str, ScaleInfo]`); `scale.factor.DetectionScale` (`.denominator`, `.source`).
- Produces:
  - `@dataclass(frozen=True) RoomScale(denominator: Optional[float], source: str, region_id: Optional[str], verified: bool)` — `source` ∈ `"viewport"|"text"|"user"|"detection"|"unresolved"`; `to_dict()` → `{"denominator","source","region_id","verified"}`.
  - `select_room_scale(centroid: tuple[float,float], regions: list[Region], page_scales: PageScales, det_scale: Optional[DetectionScale]) -> RoomScale` — verification is filled by the caller (`verified=False` here). Rule: the first `floor_plan` region containing the centroid decides — if `page_scales.by_region` has an entry for it, that entry's effective D is the answer and an unresolved entry means `denominator=None, source="unresolved"` (NO det_scale fallback: on mixed-scale pages det_scale is another plan's scale); only a room in no floor_plan region, or in one with no `by_region` entry at all, falls to `det_scale`; else unresolved.
  - `sheet_size_tokens(text: str) -> set[str]` — `{"A1"}` etc., word-bounded `A0`–`A4`.
  - `verify_sheet_size(tokens: set[str], page_w_mm: float, page_h_mm: float) -> tuple[bool, bool]` → `(matches, resized)`: `matches` when any token's ISO size (either orientation) is within 5 % of the page on both sides; `resized` when any token is off by a factor in [1.8, 2.2] or [0.45, 0.55] on both sides (one A-step). Both False when no tokens.
  - `is_verified(room_scale: RoomScale, sheet_matches: bool) -> bool` — `source in ("viewport","user")` or (`source == "text"` and `sheet_matches`). `"detection"` inherits nothing → False.
  - `ISO_A_SIZES_MM = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_scale.py
import unittest

from models import Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.scale import (
    RoomScale, is_verified, select_room_scale, sheet_size_tokens,
    verify_sheet_size,
)


def _region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


class TestSelectRoomScale(unittest.TestCase):
    def setUp(self):
        self.regions = [_region("r1", (0, 0, 500, 500)),
                        _region("r2", (600, 0, 1100, 500)),
                        _region("e1", (0, 600, 500, 1100), rtype="elevation")]
        self.scales = PageScales(by_region={
            "r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0),
            "r2": ScaleInfo(denominator=99.0, source="text", nominal=100.0),
            "e1": ScaleInfo(denominator=20.0, source="text", nominal=20.0),
        })
        self.det = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")

    def test_room_takes_its_containing_floor_plan_region(self):
        rs = select_room_scale((100, 100), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (50.0, "viewport", "r1"))
        rs = select_room_scale((700, 100), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (100.0, "text", "r2"))

    def test_non_floor_plan_region_is_ignored(self):
        rs = select_room_scale((100, 700), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (50.0, "detection", None))

    def test_outside_every_region_falls_to_detection_scale(self):
        rs = select_room_scale((2000, 2000), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source), (50.0, "detection"))

    def test_unresolved_region_stays_unresolved_never_borrows_detection_scale(self):
        # mixed-scale page: det_scale is the OTHER plan's scale
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=None, source="unresolved"),
                                       "r2": ScaleInfo(denominator=100.0, source="text", nominal=100.0)})
        det = DetectionScale(factor=0.5, denominator=100.0, source="floor_plan_regions")
        rs = select_room_scale((100, 100), self.regions, scales, det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (None, "unresolved", "r1"))

    def test_region_with_no_entry_falls_to_detection_scale(self):
        rs = select_room_scale((100, 100), self.regions, PageScales(), self.det)
        self.assertEqual((rs.denominator, rs.source), (50.0, "detection"))

    def test_nothing_resolves_to_none(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        rs = select_room_scale((2000, 2000), self.regions, PageScales(), det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (None, "unresolved", None))
        rs = select_room_scale((2000, 2000), self.regions, PageScales(), None)
        self.assertIsNone(rs.denominator)

    def test_to_dict(self):
        d = RoomScale(50.0, "viewport", "r1", True).to_dict()
        self.assertEqual(d, {"denominator": 50.0, "source": "viewport",
                             "region_id": "r1", "verified": True})


class TestSheetSize(unittest.TestCase):
    def test_tokens_are_word_bounded(self):
        self.assertEqual(sheet_size_tokens("SHEET SIZE: A1  DWG A101 CAT5"), {"A1"})
        self.assertEqual(sheet_size_tokens("scale 1:50 @ A3"), {"A3"})
        self.assertEqual(sheet_size_tokens("nothing"), set())

    def test_matching_size_either_orientation(self):
        self.assertEqual(verify_sheet_size({"A3"}, 420.0, 297.0), (True, False))
        self.assertEqual(verify_sheet_size({"A3"}, 297.0, 420.0), (True, False))
        self.assertEqual(verify_sheet_size({"A1"}, 841.0, 594.0), (True, False))

    def test_one_step_mismatch_is_resized(self):
        # A1 drawing printed on A3 paper: both sides ~halved
        self.assertEqual(verify_sheet_size({"A1"}, 420.0, 297.0), (False, True))
        # A3 drawing blown up to A1
        self.assertEqual(verify_sheet_size({"A3"}, 841.0, 594.0), (False, True))

    def test_no_tokens_or_unrelated_size(self):
        self.assertEqual(verify_sheet_size(set(), 420.0, 297.0), (False, False))
        self.assertEqual(verify_sheet_size({"A0"}, 420.0, 297.0), (False, False))

    def test_is_verified(self):
        self.assertTrue(is_verified(RoomScale(50.0, "viewport", "r1", False), False))
        self.assertTrue(is_verified(RoomScale(50.0, "user", "r1", False), False))
        self.assertTrue(is_verified(RoomScale(50.0, "text", "r1", False), True))
        self.assertFalse(is_verified(RoomScale(50.0, "text", "r1", False), False))
        self.assertFalse(is_verified(RoomScale(50.0, "detection", None, False), True))
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_scale -v`
Expected: `ModuleNotFoundError: No module named 'takeoff.scale'`

- [ ] **Step 3: Implement**

```python
# takeoff/scale.py
"""Which drawing scale a room is measured at, and whether it can be trusted.

Pages can carry different scales per region (s03, s17), so each room takes
the floor_plan region containing its centroid, then the ink-dominant
detection scale, then nothing — never a guess.

The unit model trusts that the PDF is at its intended sheet size: an A1
drawing exported onto A3 paper carries a printed "1:50" that is really 1:100.
Viewport- and user-sourced scales are immune (they measure the real page);
text-sourced ones are verified against a title-block sheet-size token when
one exists. Correction on mismatch is a follow-up branch — here we only flag.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from takeoff.units import effective_denominator

ISO_A_SIZES_MM = {
    "A0": (841.0, 1189.0),
    "A1": (594.0, 841.0),
    "A2": (420.0, 594.0),
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
}
SHEET_SIZE_TOL_FRAC = 0.05
RESIZE_FACTOR_BANDS = ((1.8, 2.2), (0.45, 0.55))

_SIZE_TOKEN_RE = re.compile(r"\bA[0-4]\b")


@dataclass(frozen=True)
class RoomScale:
    denominator: Optional[float]
    source: str          # viewport | text | user | detection | unresolved
    region_id: Optional[str]
    verified: bool

    def to_dict(self) -> dict:
        return {"denominator": self.denominator, "source": self.source,
                "region_id": self.region_id, "verified": self.verified}


def _contains(bbox, x: float, y: float) -> bool:
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def select_room_scale(centroid, regions, page_scales, det_scale) -> RoomScale:
    x, y = centroid
    for region in regions:
        if region.region_type != "floor_plan" or not _contains(region.bbox, x, y):
            continue
        by_region = page_scales.by_region if page_scales else {}
        if region.region_id not in by_region:
            break                       # no verdict for this region → page fallback
        info = by_region[region.region_id]
        denom = effective_denominator(info)
        if denom is None:
            # Explicitly unresolved: never borrow another plan's scale.
            return RoomScale(None, "unresolved", region.region_id, False)
        return RoomScale(denom, info.source, region.region_id, False)
    if det_scale is not None and det_scale.denominator is not None:
        return RoomScale(float(det_scale.denominator), "detection", None, False)
    return RoomScale(None, "unresolved", None, False)


def sheet_size_tokens(text: str) -> set[str]:
    return set(_SIZE_TOKEN_RE.findall(text or ""))


def _ratio_pair(token: str, w: float, h: float) -> tuple[float, float]:
    """(w_ratio, h_ratio) of page over ISO size, orientation-matched."""
    a, b = ISO_A_SIZES_MM[token]
    short, long_ = (min(w, h), max(w, h))
    return short / a, long_ / b


def verify_sheet_size(tokens: set[str], page_w_mm: float, page_h_mm: float) -> tuple[bool, bool]:
    matches = resized = False
    for token in tokens:
        if token not in ISO_A_SIZES_MM:
            continue
        rw, rh = _ratio_pair(token, page_w_mm, page_h_mm)
        if abs(rw - 1.0) <= SHEET_SIZE_TOL_FRAC and abs(rh - 1.0) <= SHEET_SIZE_TOL_FRAC:
            matches = True
        for lo, hi in RESIZE_FACTOR_BANDS:
            if lo <= rw <= hi and lo <= rh <= hi:
                resized = True
    return matches, resized


def is_verified(room_scale: RoomScale, sheet_matches: bool) -> bool:
    if room_scale.source in ("viewport", "user"):
        return True
    return room_scale.source == "text" and sheet_matches
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_scale -v`
Expected: 12 tests OK

- [ ] **Step 5: Commit**

```bash
git add takeoff/scale.py tests/test_takeoff_scale.py
git commit -m "feat(takeoff): per-room scale selection + sheet-size verification"
```

---

### Task 4: Openings — width from evidence, assignment to rooms

**Files:**
- Create: `takeoff/openings.py`
- Test: `tests/test_takeoff_openings.py`

**Interfaces:**
- Consumes: shapely (`Polygon`, `box`, `Point`); `detection.rooms.ROOM_WALL_DILATE_PX`, `detection.rooms.ROOM_OPENING_SEAL_PX`.
- Produces:
  - `opening_width_px(entity_type: str, bbox, evidence: dict, room_polygon: Polygon) -> tuple[float, str]` — `(width_px, width_source)`; `width_source` ∈ `"opening_line"|"opening_width_px"|"opening_span_px"|"panel_length_px"|"bbox_edge"`.
  - `assign_openings(room_polygons: dict[str, Polygon], openings: list[tuple[str, str, tuple]]) -> tuple[dict[str, list[str]], list[str]]` — input tuples are `(entity_id, entity_type, bbox)`; `room_polygons` are the STANDOFF-CORRECTED polygons (already grown by `ROOM_WALL_DILATE_PX`); returns `(room_id → [entity_id...], unassigned_ids)`. Assignment: `room_polygon.buffer(ROOM_OPENING_SEAL_PX).intersects(box(*bbox))` — 14 px total reach from the detected polygon, never 16.
  - `OPENING_ASSIGN_BUFFER_PX = ROOM_OPENING_SEAL_PX`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_openings.py
import unittest

from shapely.geometry import box

from takeoff.openings import assign_openings, opening_width_px


ROOM = box(0, 0, 300, 200)   # a 300×200 px room


class TestOpeningWidth(unittest.TestCase):
    def test_swing_door_uses_opening_line_chord(self):
        ev = {"opening_line": [[100, 200], [160, 200]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "opening_line")

    def test_window_uses_opening_width_px(self):
        w, src = opening_width_px("window", (50, -4, 170, 4), {"opening_width_px": 118.0}, ROOM)
        self.assertEqual((w, src), (118.0, "opening_width_px"))

    def test_sliding_uses_opening_span_not_bbox(self):
        # bbox is 2× the opening (parked panel)
        w, src = opening_width_px("door", (100, 195, 240, 205),
                                  {"assembly_type": "sliding", "opening_span_px": 70.0}, ROOM)
        self.assertEqual((w, src), (70.0, "opening_span_px"))

    def test_folding_falls_to_panel_length(self):
        w, src = opening_width_px("door", (100, 195, 240, 205),
                                  {"assembly_type": "folding", "panel_length_px": 35.0}, ROOM)
        self.assertEqual((w, src), (35.0, "panel_length_px"))

    def test_bbox_fallback_takes_edge_along_room_boundary(self):
        # square-ish bbox on the room's bottom wall: bottom edge (y≈200) is nearest
        w, src = opening_width_px("door", (100, 150, 160, 202), {}, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "bbox_edge")
        # tall bbox on the room's right wall: the vertical edge at x≈300 is nearest
        w, src = opening_width_px("door", (298, 50, 350, 130), {}, ROOM)
        self.assertAlmostEqual(w, 80.0)
        self.assertEqual(src, "bbox_edge")

    def test_bad_evidence_falls_through(self):
        w, src = opening_width_px("door", (100, 150, 160, 202),
                                  {"opening_line": [[0, 0]], "opening_span_px": 0}, ROOM)
        self.assertEqual(src, "bbox_edge")


class TestAssignOpenings(unittest.TestCase):
    def test_partition_door_deducts_from_both_rooms(self):
        rooms = {"room_a": box(0, 0, 300, 200), "room_b": box(310, 0, 600, 200)}
        # door bbox sits in the 10px wall between them
        assigned, unassigned = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(assigned, {"room_a": ["door_1"], "room_b": ["door_1"]})
        self.assertEqual(unassigned, [])

    def test_exterior_window_deducts_once(self):
        rooms = {"room_a": box(0, 0, 300, 200), "room_b": box(310, 0, 600, 200)}
        assigned, unassigned = assign_openings(rooms, [("win_1", "window", (50, -8, 170, -2))])
        self.assertEqual(assigned, {"room_a": ["win_1"]})
        self.assertEqual(unassigned, [])

    def test_free_space_opening_is_unassigned(self):
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, unassigned = assign_openings(rooms, [("door_9", "door", (900, 900, 960, 960))])
        self.assertEqual(assigned, {})
        self.assertEqual(unassigned, ["door_9"])

    def test_reach_is_seal_only(self):
        # corrected room; an opening 13 px away is in, 15 px away is out
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, _ = assign_openings(rooms, [("d_in", "door", (100, 213, 160, 220))])
        self.assertEqual(assigned, {"room_a": ["d_in"]})
        assigned, unassigned = assign_openings(rooms, [("d_out", "door", (100, 215, 160, 220))])
        self.assertEqual(unassigned, ["d_out"])

    def test_room_key_order_is_stable(self):
        rooms = {"room_b": box(310, 0, 600, 200), "room_a": box(0, 0, 300, 200)}
        assigned, _ = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(list(assigned), ["room_b", "room_a"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_openings -v`
Expected: `ModuleNotFoundError: No module named 'takeoff.openings'`

- [ ] **Step 3: Implement**

```python
# takeoff/openings.py
"""Door / window openings: how wide, and which rooms they belong to.

Width comes from detector evidence when it exists — a swing bbox is roughly
square (leaf + arc) and a sliding/folding bbox is ~2× the opening (parked
panel / stack), so the bbox alone is the wrong measure for most doors. Only
the bare fallback reads the bbox, and then the edge that lies along the room
boundary, never the longer side.

Assignment is geometric: an opening belongs to every room whose
standoff-corrected polygon, grown by the seal reach, touches its bbox — an
internal door deducts on both sides, an external one on one.
"""
from __future__ import annotations

import math
from typing import Optional

from shapely.geometry import Point, Polygon, box

from detection.rooms import ROOM_OPENING_SEAL_PX

# Callers pass standoff-corrected polygons (already +ROOM_WALL_DILATE_PX), so
# only the seal reach is added here: 2 + 12 = 14 px from the detected polygon.
OPENING_ASSIGN_BUFFER_PX = ROOM_OPENING_SEAL_PX


def _positive(value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _chord_length(line) -> Optional[float]:
    try:
        (x0, y0), (x1, y1) = line
    except (TypeError, ValueError):
        return None
    return _positive(math.hypot(x1 - x0, y1 - y0))


def _bbox_edge_along_boundary(bbox, room_polygon: Polygon) -> float:
    x0, y0, x1, y1 = bbox
    edges = [  # (length, midpoint)
        (x1 - x0, ((x0 + x1) / 2.0, y0)),
        (x1 - x0, ((x0 + x1) / 2.0, y1)),
        (y1 - y0, (x0, (y0 + y1) / 2.0)),
        (y1 - y0, (x1, (y0 + y1) / 2.0)),
    ]
    boundary = room_polygon.exterior
    length, _ = min(edges, key=lambda e: boundary.distance(Point(e[1])))
    return float(length)


def opening_width_px(entity_type: str, bbox, evidence: dict, room_polygon: Polygon) -> tuple[float, str]:
    evidence = evidence or {}
    if entity_type == "window":
        w = _positive(evidence.get("opening_width_px"))
        if w is not None:
            return w, "opening_width_px"
    else:
        for key in ("opening_line",):
            w = _chord_length(evidence.get(key))
            if w is not None:
                return w, key
        for key in ("opening_span_px", "panel_length_px"):
            w = _positive(evidence.get(key))
            if w is not None:
                return w, key
    return _bbox_edge_along_boundary(bbox, room_polygon), "bbox_edge"


def assign_openings(room_polygons: dict, openings: list) -> tuple[dict, list]:
    grown = {rid: poly.buffer(OPENING_ASSIGN_BUFFER_PX) for rid, poly in room_polygons.items()}
    assigned: dict[str, list[str]] = {}
    unassigned: list[str] = []
    for entity_id, _entity_type, bbox in openings:
        b = box(*bbox)
        hit = False
        for rid, poly in grown.items():
            if poly.intersects(b):
                assigned.setdefault(rid, []).append(entity_id)
                hit = True
        if not hit:
            unassigned.append(entity_id)
    return assigned, unassigned
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_openings -v`
Expected: 11 tests OK

- [ ] **Step 5: Commit**

```bash
git add takeoff/openings.py tests/test_takeoff_openings.py
git commit -m "feat(takeoff): opening widths from evidence + room assignment"
```

---

### Task 5: Quantities — `compute_takeoff`

**Files:**
- Create: `takeoff/quantities.py`
- Modify: `takeoff/__init__.py`
- Test: `tests/test_takeoff_quantities.py`

**Interfaces:**
- Consumes: Tasks 1–4; `models.Entity`, `models.Candidate`, `models.Region`; `scale.resolver.PageScales`; `scale.factor.DetectionScale`; `detection.rooms.ROOM_WALL_DILATE_PX`; shapely `Polygon`.
- Produces:
  - `@dataclass RoomTakeoff` with fields `room_id, label, scale: RoomScale, mm_per_px, floor_m2, ceiling_m2, perimeter_m, height_m, height_source, wall_gross_m2, openings: list[dict], wall_net_m2, assumptions: list[str]`; `to_dict()`.
  - `@dataclass TakeoffPage` with `page_number, heights: Heights, rooms: list[RoomTakeoff], unassigned_openings: list[str], unscaled_rooms: list[str], warnings: list[dict]`; `totals() -> dict`; `to_dict()` (page JSON incl. `"totals"`; warnings NOT included — they travel separately); `attributes_by_room() -> dict[str, dict]` (the per-room dict minus `room_id`/`label`, for mirroring onto entities).
  - `compute_takeoff(entities: list[Entity], candidates: list[Candidate], page_scales: PageScales, regions: list[Region], det_scale: Optional[DetectionScale], heights: Heights, page_number: int, page_text: str, page_w_mm: float, page_h_mm: float) -> TakeoffPage`
  - Rooms are the entities with `entity_type == "room"` and a `"polygon"` in `attributes` (list of `[x, y]`); doors/windows are entities with `entity_type in ("door", "window")`. Evidence lookup: `{c.candidate_id: c.evidence for c in candidates}` (entity ids equal candidate ids).
  - Opening dict: `{"id", "type", "width_m", "height_m", "area_m2", "width_source"}` (+ `"clamped": true` when height was clamped to ceiling).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_quantities.py
import unittest

from models import Candidate, Entity, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.heights import Heights
from takeoff.quantities import compute_takeoff

PX_PER_M_50 = 1000.0 / (25.4 / 150 * 50)     # 118.11


def _room(rid, x0, y0, x1, y1, label=None):
    poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return Entity(entity_id=rid, entity_type="room", bbox=(x0, y0, x1, y1),
                  confidence=0.9, source="heuristic", label=label,
                  attributes={"polygon": poly, "area_px2": (x1 - x0) * (y1 - y0)})


def _door(did, bbox, evidence=None):
    return (Entity(entity_id=did, entity_type="door", bbox=bbox, confidence=0.8,
                   source="heuristic", attributes={}),
            Candidate(candidate_id=did, entity_type="door", bbox=bbox,
                      confidence=0.8, evidence=evidence or {}))


HEIGHTS = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
DET50 = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")
REGION = Region(region_id="r1", bbox=(0, 0, 2000, 2000), region_type="floor_plan")
SCALES_VP = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0)})


class TestComputeTakeoff(unittest.TestCase):
    def _run(self, entities, candidates=(), page_scales=SCALES_VP, det=DET50,
             regions=(REGION,), text="", w_mm=420.0, h_mm=297.0):
        return compute_takeoff(entities, list(candidates), page_scales, list(regions),
                               det, HEIGHTS, 1, text, w_mm, h_mm)

    def test_square_room_at_1_50(self):
        # 3 m × 4 m room, drawn 2 px inside its walls (barrier standoff)
        w, h = 3 * PX_PER_M_50 - 4, 4 * PX_PER_M_50 - 4
        page = self._run([_room("room_0000", 100, 100, 100 + w, 100 + h, "BED 1")])
        r = page.rooms[0]
        self.assertEqual(r.room_id, "room_0000")
        self.assertEqual(r.label, "BED 1")
        self.assertAlmostEqual(r.floor_m2, 12.0, places=1)
        self.assertEqual(r.ceiling_m2, r.floor_m2)
        self.assertAlmostEqual(r.perimeter_m, 14.0, places=1)
        self.assertAlmostEqual(r.wall_gross_m2, 33.6, places=1)
        self.assertEqual(r.wall_net_m2, r.wall_gross_m2)
        self.assertEqual(r.height_source, "default")
        self.assertAlmostEqual(r.mm_per_px, 8.467, places=3)
        self.assertEqual(r.scale.to_dict(), {"denominator": 50.0, "source": "viewport",
                                             "region_id": "r1", "verified": True})
        self.assertIn("flat_ceiling", r.assumptions)
        self.assertIn("standoff_corrected_2px", r.assumptions)
        self.assertEqual(page.unscaled_rooms, [])
        self.assertEqual(page.warnings, [])

    def test_partition_door_deducts_from_both_rooms(self):
        s = PX_PER_M_50
        a = _room("room_a", 0, 0, 3 * s, 3 * s)
        b = _room("room_b", 3 * s + 10, 0, 6 * s + 10, 3 * s)
        de, dc = _door("door_0001", (3 * s + 1, s, 3 * s + 9, s + 0.9 * s),
                       {"opening_line": [[3 * s + 5, s], [3 * s + 5, 1.9 * s]]})
        page = self._run([a, b, de], [dc])
        for r in page.rooms:
            self.assertEqual(len(r.openings), 1)
            self.assertAlmostEqual(r.openings[0]["width_m"], 0.9, places=2)
            self.assertAlmostEqual(r.openings[0]["area_m2"], 0.9 * 2.1, places=2)
            self.assertAlmostEqual(r.wall_net_m2, r.wall_gross_m2 - 0.9 * 2.1, places=2)
        self.assertEqual(page.unassigned_openings, [])

    def test_free_space_door_is_unassigned(self):
        de, dc = _door("door_0007", (1500, 1500, 1560, 1560))
        page = self._run([_room("room_a", 0, 0, 300, 300), de], [dc])
        self.assertEqual(page.unassigned_openings, ["door_0007"])
        self.assertEqual(page.rooms[0].openings, [])

    def test_no_scale_room_is_listed_not_zeroed(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=PageScales(), det=det)
        self.assertEqual(page.rooms, [])
        self.assertEqual(page.unscaled_rooms, ["room_a"])
        self.assertEqual([w["warning_code"] for w in page.warnings], ["TAKEOFF_NO_SCALE"])
        self.assertEqual(page.totals()["rooms_unscaled"], 1)

    def test_opening_on_unscaled_room_is_not_unassigned(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        de, dc = _door("door_0001", (100, 296, 160, 304))
        page = self._run([_room("room_a", 0, 0, 300, 300), de], [dc],
                         page_scales=PageScales(), det=det)
        self.assertEqual(page.unscaled_rooms, ["room_a"])
        self.assertEqual(page.unassigned_openings, [])
        self.assertEqual(page.rooms, [])

    def test_holes_are_filled_and_recorded(self):
        page = self._run([_room("room_a", 0, 0, 300, 300)])
        self.assertIn("holes_filled", page.rooms[0].assumptions)

    def test_text_scale_verified_by_sheet_size(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=scales,
                         text="A3 SHEET", w_mm=420.0, h_mm=297.0)
        self.assertTrue(page.rooms[0].scale.verified)
        self.assertEqual(page.warnings, [])

    def test_text_scale_unverified_warns_once(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300), _room("room_b", 400, 0, 700, 300)],
                         page_scales=scales, text="")
        self.assertFalse(page.rooms[0].scale.verified)
        self.assertEqual([w["warning_code"] for w in page.warnings], ["SCALE_UNVERIFIED"])
        self.assertEqual(page.warnings[0]["severity"], "info")

    def test_resized_sheet_warns(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=scales,
                         text="A1", w_mm=420.0, h_mm=297.0)
        codes = sorted(w["warning_code"] for w in page.warnings)
        self.assertEqual(codes, ["SCALE_PRINT_RESIZED", "SCALE_UNVERIFIED"])
        self.assertFalse(page.rooms[0].scale.verified)

    def test_opening_taller_than_ceiling_is_clamped(self):
        low = Heights(2.0, 2.1, 1.2, {"ceiling": "flag", "door": "default", "window": "default"})
        s = PX_PER_M_50
        de, dc = _door("door_0001", (s, 3 * s - 4, 1.9 * s, 3 * s + 4),
                       {"opening_line": [[s, 3 * s], [1.9 * s, 3 * s]]})
        page = compute_takeoff([_room("room_a", 0, 0, 3 * s, 3 * s), de], [dc], SCALES_VP,
                               [REGION], DET50, low, 1, "", 420.0, 297.0)
        op = page.rooms[0].openings[0]
        self.assertEqual(op["height_m"], 2.0)
        self.assertTrue(op["clamped"])
        self.assertIn("TAKEOFF_OPENING_TALLER_THAN_CEILING",
                      [w["warning_code"] for w in page.warnings])

    def test_rejected_candidate_never_deducts(self):
        # a door candidate with no matching entity (rejected by the floor)
        s = PX_PER_M_50
        _, dc = _door("door_0001", (s, 3 * s - 4, 1.9 * s, 3 * s + 4))
        page = self._run([_room("room_a", 0, 0, 3 * s, 3 * s)], [dc])
        self.assertEqual(page.rooms[0].openings, [])

    def test_to_dict_and_attributes(self):
        page = self._run([_room("room_a", 0, 0, 300, 300, "HALL")])
        d = page.to_dict()
        self.assertEqual(set(d), {"page_number", "heights", "rooms", "unassigned_openings",
                                  "unscaled_rooms", "totals"})
        room = d["rooms"][0]
        for k in ("room_id", "label", "scale", "mm_per_px", "floor_m2", "ceiling_m2",
                  "perimeter_m", "height_m", "height_source", "wall_gross_m2",
                  "openings", "wall_net_m2", "assumptions"):
            self.assertIn(k, room)
        self.assertEqual(room["floor_m2"], round(room["floor_m2"], 2))
        attrs = page.attributes_by_room()["room_a"]
        self.assertNotIn("room_id", attrs)
        self.assertIn("floor_m2", attrs)
        self.assertEqual(d["totals"]["rooms_measured"], 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_quantities -v`
Expected: `ModuleNotFoundError: No module named 'takeoff.quantities'`

- [ ] **Step 3: Implement**

```python
# takeoff/quantities.py
"""compute_takeoff — the pure core: rooms + scale + heights → metres.

No I/O, no prompting, no globals. pipeline.run_extract resolves heights once
per run, calls this per page after finalize_candidates, and writes the
result. Rooms without a resolvable scale are listed, never zeroed. Warnings
travel on TakeoffPage.warnings for the caller to fold into the page list —
the same shape PageScales.warnings uses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from shapely.geometry import Polygon

from detection.rooms import ROOM_WALL_DILATE_PX
from takeoff.heights import Heights
from takeoff.openings import assign_openings, opening_width_px
from takeoff.scale import (
    RoomScale, is_verified, select_room_scale, sheet_size_tokens, verify_sheet_size,
)
from takeoff.units import mm_per_px, px2_to_m2, px_to_m

STANDOFF_ASSUMPTION = f"standoff_corrected_{ROOM_WALL_DILATE_PX:g}px"
FLAT_CEILING_ASSUMPTION = "flat_ceiling"
HOLES_FILLED_ASSUMPTION = "holes_filled"   # detector fills fixture islands; they are floor


@dataclass
class RoomTakeoff:
    room_id: str
    label: Optional[str]
    scale: RoomScale
    mm_per_px: float
    floor_m2: float
    ceiling_m2: float
    perimeter_m: float
    height_m: float
    height_source: str
    wall_gross_m2: float
    openings: list = field(default_factory=list)
    wall_net_m2: float = 0.0
    assumptions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "label": self.label,
            "scale": self.scale.to_dict(),
            "mm_per_px": self.mm_per_px,
            "floor_m2": self.floor_m2,
            "ceiling_m2": self.ceiling_m2,
            "perimeter_m": self.perimeter_m,
            "height_m": self.height_m,
            "height_source": self.height_source,
            "wall_gross_m2": self.wall_gross_m2,
            "openings": list(self.openings),
            "wall_net_m2": self.wall_net_m2,
            "assumptions": list(self.assumptions),
        }


@dataclass
class TakeoffPage:
    page_number: int
    heights: Heights
    rooms: list = field(default_factory=list)
    unassigned_openings: list = field(default_factory=list)
    unscaled_rooms: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def totals(self) -> dict:
        return {
            "floor_m2": round(sum(r.floor_m2 for r in self.rooms), 2),
            "ceiling_m2": round(sum(r.ceiling_m2 for r in self.rooms), 2),
            "wall_net_m2": round(sum(r.wall_net_m2 for r in self.rooms), 2),
            "rooms_measured": len(self.rooms),
            "rooms_unscaled": len(self.unscaled_rooms),
        }

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "heights": self.heights.to_dict(),
            "rooms": [r.to_dict() for r in self.rooms],
            "unassigned_openings": list(self.unassigned_openings),
            "unscaled_rooms": list(self.unscaled_rooms),
            "totals": self.totals(),
        }

    def attributes_by_room(self) -> dict:
        out = {}
        for r in self.rooms:
            d = r.to_dict()
            d.pop("room_id")
            d.pop("label")
            out[r.room_id] = d
        return out


def _warn(page: TakeoffPage, code: str, severity: str, message: str) -> None:
    if any(w["warning_code"] == code for w in page.warnings):
        return
    page.warnings.append({"page_number": page.page_number, "warning_code": code,
                          "severity": severity, "message": message})


def _room_polygon(entity) -> Optional[Polygon]:
    pts = entity.attributes.get("polygon")
    if not pts or len(pts) < 3:
        return None
    poly = Polygon([tuple(p) for p in pts])
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if not poly.is_empty else None


def compute_takeoff(entities, candidates, page_scales, regions, det_scale, heights: Heights,
                    page_number: int, page_text: str, page_w_mm: float, page_h_mm: float) -> TakeoffPage:
    page = TakeoffPage(page_number=page_number, heights=heights)
    evidence = {c.candidate_id: c.evidence for c in candidates}

    tokens = sheet_size_tokens(page_text)
    sheet_matches, sheet_resized = verify_sheet_size(tokens, page_w_mm, page_h_mm)
    if sheet_resized:
        _warn(page, "SCALE_PRINT_RESIZED", "warning",
              f"Title block declares {'/'.join(sorted(tokens))} but the page is "
              f"{page_w_mm:.0f}x{page_h_mm:.0f} mm — printed scale may be one A-size off")

    # Rooms: polygon, corrected for the barrier standoff, and its scale.
    # EVERY valid room takes part in opening assignment (so an opening on an
    # unscaled room is not mis-reported as free-space); only scaled rooms
    # get quantities.
    room_polys: dict[str, Polygon] = {}
    room_meta: dict[str, tuple] = {}
    for e in entities:
        if e.entity_type != "room":
            continue
        raw = _room_polygon(e)
        if raw is None:
            continue
        poly = raw.buffer(ROOM_WALL_DILATE_PX, join_style=2)   # 2 = mitre
        room_polys[e.entity_id] = poly
        c = raw.centroid
        rs = select_room_scale((c.x, c.y), regions, page_scales, det_scale)
        if rs.denominator is None:
            page.unscaled_rooms.append(e.entity_id)
            continue
        rs = RoomScale(rs.denominator, rs.source, rs.region_id, is_verified(rs, sheet_matches))
        room_meta[e.entity_id] = (e, rs, poly)

    if page.unscaled_rooms:
        _warn(page, "TAKEOFF_NO_SCALE", "warning",
              f"{len(page.unscaled_rooms)} room(s) have no resolvable drawing scale; "
              "no quantities computed for them")

    # Openings → rooms.
    openings = [(e.entity_id, e.entity_type, e.bbox) for e in entities
                if e.entity_type in ("door", "window")]
    opening_by_id = {e.entity_id: e for e in entities if e.entity_type in ("door", "window")}
    assigned, unassigned = assign_openings(room_polys, openings)
    page.unassigned_openings = unassigned

    for rid, (e, rs, poly) in room_meta.items():
        D = rs.denominator
        floor = px2_to_m2(poly.area, D)
        perim = px_to_m(poly.exterior.length, D)
        gross = perim * heights.ceiling_m
        ops = []
        deduct = 0.0
        for oid in assigned.get(rid, []):
            oe = opening_by_id[oid]
            w_px, w_src = opening_width_px(oe.entity_type, oe.bbox, evidence.get(oid, {}), poly)
            w_m = px_to_m(w_px, D)
            h_m = heights.door_m if oe.entity_type == "door" else heights.window_m
            clamped = h_m > heights.ceiling_m
            if clamped:
                h_m = heights.ceiling_m
                _warn(page, "TAKEOFF_OPENING_TALLER_THAN_CEILING", "info",
                      "An opening height exceeded the ceiling height and was clamped")
            area = w_m * h_m
            deduct += area
            op = {"id": oid, "type": oe.entity_type, "width_m": round(w_m, 2),
                  "height_m": round(h_m, 2), "area_m2": round(area, 2), "width_source": w_src}
            if clamped:
                op["clamped"] = True
            ops.append(op)
        room = RoomTakeoff(
            room_id=rid, label=e.label, scale=rs, mm_per_px=round(mm_per_px(D), 3),
            floor_m2=round(floor, 2), ceiling_m2=round(floor, 2), perimeter_m=round(perim, 2),
            height_m=heights.ceiling_m, height_source=heights.sources["ceiling"],
            wall_gross_m2=round(gross, 2), openings=ops,
            wall_net_m2=round(max(gross - deduct, 0.0), 2),
            assumptions=[FLAT_CEILING_ASSUMPTION, STANDOFF_ASSUMPTION, HOLES_FILLED_ASSUMPTION],
        )
        page.rooms.append(room)
        if not rs.verified:
            _warn(page, "SCALE_UNVERIFIED", "info",
                  "Room quantities rest on a printed scale that could not be verified "
                  "against a viewport or sheet size")

    return page
```

Then update `takeoff/__init__.py`:

```python
# takeoff/__init__.py
"""Quantity takeoff — rooms + scale + heights → floor / ceiling / wall areas."""
from takeoff.heights import Heights, resolve_heights
from takeoff.quantities import RoomTakeoff, TakeoffPage, compute_takeoff

__all__ = ["Heights", "resolve_heights", "RoomTakeoff", "TakeoffPage", "compute_takeoff"]
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_quantities -v`
Expected: 12 tests OK. If `test_square_room_at_1_50` is off by the standoff, check the buffer is applied once with `join_style=2` (a 4 px total growth per axis restores the 3 × 4 m).

- [ ] **Step 5: Run the whole fast tier**

Run: `python -m unittest discover tests`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add takeoff/quantities.py takeoff/__init__.py tests/test_takeoff_quantities.py
git commit -m "feat(takeoff): compute_takeoff — per-room floor/ceiling/wall quantities"
```

---

### Task 6: Pipeline + CLI wiring

**Files:**
- Modify: `pipeline.py` (imports ~L15–35; `run_extract` signature L450–460; page loop after `finalize_candidates` ~L648–668; warnings block ~L716–722; `_page_summary_dict` L283–305; root `totals` ~L745)
- Modify: `app.py` (`cmd_extract` L88–100; `extract` parser L171–178)
- Test: `tests/test_takeoff_pipeline.py`

**Interfaces:**
- Consumes: `takeoff.compute_takeoff`, `takeoff.resolve_heights`, `takeoff.TakeoffPage`.
- Produces:
  - `run_extract(..., ceiling_height: Optional[float] = None, door_height: Optional[float] = None, window_height: Optional[float] = None)` — new keyword params, defaults None.
  - `pipeline.attach_takeoff(entities: list[Entity], page: TakeoffPage) -> None` — mutates room entities' `attributes` with `page.attributes_by_room()` under key `"takeoff"`.
  - `pipeline._page_summary_dict(..., takeoff: Optional[TakeoffPage] = None)` adds `"takeoff": page.totals()` when given.
  - `pages/page_NN/takeoff.json` = `TakeoffPage.to_dict()`; root `summary.json["totals"]["takeoff"]` = summed page totals `{floor_m2, ceiling_m2, wall_net_m2, rooms_measured, rooms_unscaled}`.
  - Page dimensions in mm: `page_data.width_px / 150 * 25.4`, same for height. Page text: `" ".join(s.text for s in page_data.text_spans)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_takeoff_pipeline.py
import unittest
from unittest import mock

from models import Entity
from pipeline import _page_summary_dict, attach_takeoff
from takeoff.heights import Heights
from takeoff.quantities import RoomTakeoff, TakeoffPage
from takeoff.scale import RoomScale


def _page():
    h = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
    page = TakeoffPage(page_number=1, heights=h)
    page.rooms.append(RoomTakeoff(
        room_id="room_0000", label="HALL", scale=RoomScale(50.0, "viewport", "r1", True),
        mm_per_px=8.467, floor_m2=5.5, ceiling_m2=5.5, perimeter_m=9.4, height_m=2.4,
        height_source="default", wall_gross_m2=22.56, openings=[], wall_net_m2=22.56,
        assumptions=["flat_ceiling"]))
    return page


class TestAttachTakeoff(unittest.TestCase):
    def test_room_entity_gets_takeoff_block(self):
        room = Entity(entity_id="room_0000", entity_type="room", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={"polygon": []})
        door = Entity(entity_id="door_0000", entity_type="door", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={})
        attach_takeoff([room, door], _page())
        self.assertEqual(room.attributes["takeoff"]["floor_m2"], 5.5)
        self.assertNotIn("room_id", room.attributes["takeoff"])
        self.assertNotIn("takeoff", door.attributes)

    def test_unscaled_room_gets_no_block(self):
        room = Entity(entity_id="room_0009", entity_type="room", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={"polygon": []})
        attach_takeoff([room], _page())
        self.assertNotIn("takeoff", room.attributes)


class TestSummaryTotals(unittest.TestCase):
    def test_page_summary_carries_takeoff_totals(self):
        page_data = mock.Mock(page_number=1, page_type="vector", width_px=1000.0,
                              height_px=800.0, paths=[], text_spans=[], images=[])
        from scale.resolver import PageScales
        d = _page_summary_dict(page_data, [], [], [], [], PageScales(), None, takeoff=_page())
        self.assertEqual(d["takeoff"]["rooms_measured"], 1)
        self.assertEqual(d["takeoff"]["floor_m2"], 5.5)

    def test_page_summary_without_takeoff(self):
        page_data = mock.Mock(page_number=1, page_type="vector", width_px=1000.0,
                              height_px=800.0, paths=[], text_spans=[], images=[])
        from scale.resolver import PageScales
        d = _page_summary_dict(page_data, [], [], [], [], PageScales(), None)
        self.assertNotIn("takeoff", d)


class TestCliFlags(unittest.TestCase):
    def test_extract_parser_accepts_height_flags(self):
        import app
        parser = app.build_parser()
        ns = parser.parse_args(["extract", "x.pdf", "--ceiling-height", "2.7",
                                "--door-height", "2.0", "--window-height", "1.5"])
        self.assertEqual((ns.ceiling_height, ns.door_height, ns.window_height), (2.7, 2.0, 1.5))
        ns = parser.parse_args(["extract", "x.pdf"])
        self.assertIsNone(ns.ceiling_height)

    def test_extract_parser_rejects_bad_heights(self):
        import app
        parser = app.build_parser()
        for bad in ("0", "-2", "nan", "inf", "tall"):
            with self.assertRaises(SystemExit):
                with mock.patch("sys.stderr"):
                    parser.parse_args(["extract", "x.pdf", "--ceiling-height", bad])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_takeoff_pipeline -v`
Expected: `ImportError: cannot import name 'attach_takeoff'` (and `app.build_parser` missing).

- [ ] **Step 3: Implement — `app.py`**

Split `main()` so the parser is testable, and add the flags. In `app.py` replace:

```python
def main() -> None:
    parser = argparse.ArgumentParser(
```
with
```python
def positive_metres(text: str) -> float:
    """argparse type: a positive, finite height in metres."""
    from takeoff.heights import valid_height_m
    try:
        return valid_height_m(float(text), "flag")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive number of metres, got {text!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
```
and replace the tail
```python
    p_extract.set_defaults(func=cmd_extract)

    args = parser.parse_args()
    args.func(args)
```
with
```python
    p_extract.add_argument(
        "--ceiling-height", type=positive_metres, default=None, metavar="M",
        help="Ceiling height in metres for the wall-area takeoff (default: ask on a tty, else 2.4)",
    )
    p_extract.add_argument(
        "--door-height", type=positive_metres, default=None, metavar="M",
        help="Door opening height in metres (default 2.1)",
    )
    p_extract.add_argument(
        "--window-height", type=positive_metres, default=None, metavar="M",
        help="Window opening height in metres, sill to head (default 1.2)",
    )
    p_extract.set_defaults(func=cmd_extract)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
```

In `cmd_extract`, extend the `run_extract(` call:

```python
        allow_scale_prompt=not args.no_scale_prompt,
        ceiling_height=args.ceiling_height,
        door_height=args.door_height,
        window_height=args.window_height,
    )
```

- [ ] **Step 4: Implement — `pipeline.py`**

Imports (after `from scale.viewport import viewport_scales`):

```python
from takeoff import Heights, TakeoffPage, compute_takeoff, resolve_heights
```

Add the helper next to `_room_entity`:

```python
def attach_takeoff(entities: list[Entity], page: TakeoffPage) -> None:
    """Mirror the per-room takeoff onto room Entity.attributes["takeoff"]."""
    blocks = page.attributes_by_room()
    for e in entities:
        if e.entity_type == "room" and e.entity_id in blocks:
            e.attributes["takeoff"] = blocks[e.entity_id]
```

`_page_summary_dict`: add parameter `takeoff: Optional[TakeoffPage] = None` after `det_scale`, and inside the returned dict builder add the key only when present — change the function body to:

```python
    out = {
        ... existing keys unchanged ...
    }
    if takeoff is not None:
        out["takeoff"] = takeoff.totals()
    return out
```

`run_extract` signature — add after `allow_scale_prompt: bool = True,`:

```python
    ceiling_height: Optional[float] = None,
    door_height: Optional[float] = None,
    window_height: Optional[float] = None,
```

Resolve heights once, before the `with Progress(` block (after `total_entities = 0`):

```python
    heights = resolve_heights(ceiling_height, door_height, window_height,
                              allow_prompt=allow_scale_prompt)
    takeoff_totals = {"floor_m2": 0.0, "ceiling_m2": 0.0, "wall_net_m2": 0.0,
                      "rooms_measured": 0, "rooms_unscaled": 0}
```

In the page loop, right after `entities, rejected = finalize_candidates(candidates)` and before `write_json(... final_entities.json ...)`:

```python
            # 5a. Quantity takeoff — rooms + scale + heights → metres
            takeoff_page = compute_takeoff(
                entities, candidates, page_scales, region_result.regions, det_scale,
                heights, page_num,
                " ".join(s.text for s in page_data.text_spans),
                page_data.width_px / 150.0 * 25.4,
                page_data.height_px / 150.0 * 25.4,
            )
            attach_takeoff(entities, takeoff_page)
            write_json(str(Path(page_dir) / "takeoff.json"), takeoff_page.to_dict())
            for k, v in takeoff_page.totals().items():
                takeoff_totals[k] = round(takeoff_totals[k] + v, 2) if isinstance(v, float) else takeoff_totals[k] + v
```

Warnings block — after `page_warnings.extend(det_scale.warnings)`:

```python
            page_warnings.extend(takeoff_page.warnings)
```

Summary call — pass the page:

```python
            all_page_summaries.append(
                _page_summary_dict(page_data, candidates, entities, page_warnings,
                                   region_result.regions, page_scales, det_scale,
                                   takeoff=takeoff_page)
            )
```

Root `summary.json` totals — add `"takeoff": takeoff_totals,` inside `"totals": {...}`.

- [ ] **Step 5: Run to verify pass**

Run: `python -m unittest tests.test_takeoff_pipeline -v && python -m unittest discover tests`
Expected: all OK. `tests/test_scale_no_prompt.py` and `tests/test_batch_extract.py` must still pass (the new flags are optional).

- [ ] **Step 6: Smoke run on a real sheet**

Run: `source .venv/bin/activate && python app.py extract fixtures/sheets/s01-floor-plans.pdf --no-gemini --ceiling-height 2.4 --out /private/tmp/claude-501/-Users-nestimate-Documents-GitHub-agent/3753f5a0-40a6-4009-8920-56609de6cd03/scratchpad/takeoff-smoke`
Then: `python -c "import json,glob; d=json.load(open(glob.glob('/private/tmp/claude-501/-Users-nestimate-Documents-GitHub-agent/3753f5a0-40a6-4009-8920-56609de6cd03/scratchpad/takeoff-smoke/*/pages/page_01/takeoff.json')[0])); print(d['totals']); [print(r['room_id'], r['label'], r['floor_m2'], r['wall_net_m2'], r['scale']) for r in d['rooms'][:6]]"`
Expected: `takeoff.json` exists, rooms carry plausible m² (a bedroom 8–20 m², not 0.01 or 5000), `scale.denominator` 50.0. If s01's scale is unresolved on a `--no-gemini` cache miss, the rooms land in `unscaled_rooms` — that is correct behaviour, retry with a sheet whose scale resolves (s02) rather than "fixing" it.

- [ ] **Step 7: Commit**

```bash
git add app.py pipeline.py tests/test_takeoff_pipeline.py
git commit -m "feat(takeoff): wire takeoff.json + height flags into extract"
```

---

### Task 7: batch_extract ceiling-height prompt

**Files:**
- Modify: `batch_extract.py` (`build_extract_command` L40–56; the interactive option prompts — find the function that asks about windows/walls/gemini via `grep -n "input(" batch_extract.py`)
- Test: `tests/test_batch_extract.py` (append)

**Interfaces:**
- Consumes: `takeoff.heights.parse_height`.
- Produces: `build_extract_command(pdf_path, enable_windows, enable_walls, use_gemini, ceiling_height: Optional[float] = None) -> list[str]` — appends `["--ceiling-height", str(ceiling_height)]` when not None. Batch children run with `--no-scale-prompt`, so without this the ceiling always defaults silently.

- [ ] **Step 1: Write the failing test** (append to `tests/test_batch_extract.py`; match its existing import of `build_extract_command`)

```python
class TestCeilingHeightFlag(unittest.TestCase):
    def test_flag_forwarded_when_given(self):
        from pathlib import Path
        cmd = build_extract_command(Path("x.pdf"), True, True, False, ceiling_height=2.7)
        i = cmd.index("--ceiling-height")
        self.assertEqual(cmd[i + 1], "2.7")

    def test_flag_absent_by_default(self):
        from pathlib import Path
        cmd = build_extract_command(Path("x.pdf"), True, True, False)
        self.assertNotIn("--ceiling-height", cmd)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest tests.test_batch_extract -v`
Expected: `TypeError: ... unexpected keyword argument 'ceiling_height'`

- [ ] **Step 3: Implement**

`build_extract_command` (L40): add the parameter `ceiling_height: Optional[float] = None` (add `from typing import Optional` at the top if absent) and, before `return cmd`:

```python
    if ceiling_height is not None:
        cmd += ["--ceiling-height", str(ceiling_height)]
```

`run_extract` (L95): add `ceiling_height: Optional[float] = None` after `timeout_seconds`, and pass it through: `cmd = build_extract_command(pdf_path, enable_windows, enable_walls, use_gemini, ceiling_height=ceiling_height)`.

`main()` (L146–148), after `use_gemini = prompt_bool(...)`:

```python
    from takeoff.heights import DEFAULT_CEILING_M, parse_height
    try:
        ceiling_height = parse_height(
            input(f"Ceiling height in m for the wall takeoff (blank = {DEFAULT_CEILING_M}): "))
    except (EOFError, KeyboardInterrupt):
        ceiling_height = None
```

Add to the "Configuration:" printout: `print(f"  Ceiling height: {ceiling_height if ceiling_height is not None else f'{DEFAULT_CEILING_M} (default)'} m")`, and in the `executor.submit(run_extract, pdf, enable_windows, enable_walls, use_gemini, timeout_seconds, ...)` call append `ceiling_height` as the last positional argument.

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest tests.test_batch_extract -v && python -m unittest discover tests`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add batch_extract.py tests/test_batch_extract.py
git commit -m "feat(batch): forward ceiling height to extract"
```

---

### Task 8: Docs + graph refresh + corpus sanity

**Files:**
- Modify: `CLAUDE.md` (Commands block; Module layout tree; Output layout tree; a one-paragraph "Takeoff" note under Pipeline architecture stage 6)
- Modify: `docs/superpowers/specs/2026-08-18-room-takeoff-design.md` (Status line)

- [ ] **Step 1: CLAUDE.md**

Commands — add to the `extract` usage lines:
```
                                          [--ceiling-height M] [--door-height M]
                                          [--window-height M]
# Heights feed the per-room quantity takeoff (takeoff/). --ceiling-height is
# prompted for on a tty when absent (same gate as the scale prompt); defaults
# 2.4 / 2.1 / 1.2 m.
```
Module layout — add after `scale/`:
```
takeoff/           # rooms + scale + heights → floor / ceiling / net wall m² per room
                   # (units, heights, per-room scale + sheet-size verification,
                   # opening assignment, compute_takeoff). Pure; wired in
                   # pipeline.run_extract after finalize_candidates.
```
Output layout — add under `pages/page_NN/`:
```
    ├── takeoff.json          # per-room floor/ceiling/wall m², openings, scale provenance
```
Pipeline architecture stage 6 — append one paragraph:
```
   After finalisation, `takeoff.compute_takeoff` converts each room polygon
   (buffered out by `ROOM_WALL_DILATE_PX` to undo the barrier standoff) into
   metres at 0.16933 mm/px × the room's denominator (its floor_plan region's
   scale, else the detection scale, else no numbers + `TAKEOFF_NO_SCALE`),
   assigns door/window entities to the rooms whose grown polygon touches them
   (widths from `opening_line` / `opening_width_px` / `opening_span_px`, bbox
   edge as last resort), and writes `takeoff.json`; the block is mirrored onto
   the room entity's `attributes["takeoff"]` and totals into `summary.json`.
   `scale.verified` is true for viewport/user scales, or text scales whose
   title-block sheet size matches the mediabox; `SCALE_UNVERIFIED` /
   `SCALE_PRINT_RESIZED` flag the rest. Heights: flag → tty prompt → default.
```

- [ ] **Step 2: Corpus sanity (record numbers in the commit message, not a test)**

Run the smoke command from Task 6 Step 6 on `s02` (`fixtures/sheets/s02-working-drawing-wd03.pdf`, 1:50, 41 dimension strings). Open `overlay.png`, pick two rooms with printed dimensions (e.g. a "3600" × "2700" room), and confirm `floor_m2` ≈ product within 3 %. Also compare one printed dimension to the px between its extension lines × 8.467. Note the three numbers in the commit message.

- [ ] **Step 3: Spec status + graph**

Set `**Status:** Implemented (branch feat/room-takeoff)` in the spec. Then run `graphify update .` (AST-only).

- [ ] **Step 4: Full test run and commit**

Run: `python -m unittest discover tests`
Expected: OK

```bash
git add CLAUDE.md docs/superpowers/specs/2026-08-18-room-takeoff-design.md graphify-out
git commit -m "docs: takeoff stage in CLAUDE.md; s02 sanity numbers"
```

- [ ] **Step 5: Regression sweep is untouched — prove it**

Run: `python tools/regress.py`
Expected: exit 0, no lost confirmed, no returned FPs (takeoff never changes detection; if anything moves, the cause is elsewhere — stop and report, do not soften).
