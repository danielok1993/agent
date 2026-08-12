# Scale-Aware Wall/Room Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thread the resolved drawing scale into wall-network and room detection so world-space pixel gates (tuned at 1:50) fire correctly on 1:100 (and other-scale) sheets, with exact identity behavior at 1:50 and on unresolved sheets.

**Architecture:** A new pure function `detection_scale()` in the `scale` package turns `PageScales` + regions into one factor `f = 50 / nominal_denominator` per page (ink-dominant on mixed pages, clamped to [0.25, 4.0], 1.0 when unresolved). `pipeline.run_extract` passes it to `run_heuristics(scale_factor=…)`, which forwards it ONLY to `detect_wall_network` and `detect_rooms`. Inside walls/rooms, frozen "gates" dataclasses (`WallGates`, `RoomGates`) hold the world-space constants pre-multiplied by `f` (areas by `f²`) and are threaded explicitly to helpers — no module-global mutation; module constants keep their tuned 1:50 values. Paper-space and dimensionless constants are untouched. Uncertain-class constants are resolved by measurement (Task 2) before any gate code is written.

**Tech Stack:** Python 3.13, stdlib `unittest` (NOT pytest), PyMuPDF, shapely. Spec: `docs/superpowers/specs/2026-08-12-scale-aware-wall-room-gates-design.md`. Classification table: `docs/scale-normalization-findings.md` §4 (update it as part of this plan).

## Global Constraints

- Activate the venv first in every shell: `source .venv/bin/activate`.
- Tests are stdlib **unittest**: `python -m unittest tests.test_x.TestY.test_z` / `python -m unittest discover tests`. Never pytest.
- **Exact identity at f = 1.0**: every gate value at factor 1.0 must equal the module constant (`x * 1.0 == x` holds exactly in IEEE 754 for finite floats — rely on it; never round or reformat constants).
- No PDF is ever committed. The corpus lives in gitignored `fixtures/sheets/` (slugs `s01`–`s20`); scripts that read it go in the scratchpad, not the repo.
- Regression rules (`docs/regression-testing-guide.md`): `python tools/regress.py` must never lose a `confirmed` entity or re-emit a `false_positive`. New/changed detections print under REVIEW and are the USER's to verdict — stop and ask; never run `tools/review.py` yourself. One fix + one sweep per iteration, then ask before iterating again.
- Commit style: imperative subject with type prefix (`feat(scale): …`, `test(walls): …`, `docs(scale): …`). NEVER add a Co-Authored-By trailer. Work on branch `feat/scale-aware-wall-room-gates` (already exists, docs committed).
- After modifying code, run `graphify update .` (AST-only) before the task's final commit.
- Line numbers in this plan were measured 2026-08-12 on commit `2150052`; treat them as anchors, re-grep if drifted.

---

### Task 1: `detection_scale()` — the factor computation

**Files:**
- Create: `scale/factor.py`
- Modify: `scale/__init__.py` (add exports)
- Test: `tests/test_scale_factor.py` (new)

**Interfaces:**
- Consumes: `models.Region` (fields: `region_id`, `region_type`, `path_count`), `scale.resolver.PageScales` (fields: `by_region: dict[str, ScaleInfo]`, `page_scale: Optional[ScaleInfo]`), `models.ScaleInfo` (fields: `denominator`, `nominal`, `source`).
- Produces: `DetectionScale` dataclass with fields `factor: float`, `denominator: Optional[float]`, `source: str` (one of `"floor_plan_regions" | "page" | "unresolved" | "clamped"`), `warnings: list[dict]`; and `detection_scale(page_scales, regions, page_number) -> DetectionScale`. Task 5 calls this from `pipeline.run_extract`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scale_factor.py`:

```python
"""detection_scale(): PageScales + regions -> one detection factor per page."""
import unittest

from models import Region, ScaleInfo
from scale.factor import (
    DETECTION_FACTOR_MAX, DETECTION_FACTOR_MIN, DetectionScale, detection_scale,
)
from scale.resolver import PageScales


def region(rid, region_type="floor_plan", path_count=100):
    return Region(region_id=rid, bbox=(0, 0, 100, 100),
                  region_type=region_type, path_count=path_count)


def info(denominator, nominal=None, source="viewport"):
    return ScaleInfo(denominator=denominator, source=source,
                     nominal=nominal if nominal is not None else denominator)


class TestDetectionScale(unittest.TestCase):
    def test_single_floor_plan_scale_sets_factor(self):
        ps = PageScales(by_region={"region_0000": info(100.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 0.5)
        self.assertEqual(ds.denominator, 100.0)
        self.assertEqual(ds.source, "floor_plan_regions")
        self.assertEqual(ds.warnings, [])

    def test_one_to_fifty_is_exactly_identity(self):
        ps = PageScales(by_region={"region_0000": info(50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 1.0)  # exact, not approx

    def test_nominal_preferred_over_raw_denominator(self):
        # s04: raw viewport 50.0007, nominal snap 50.0 -> factor exactly 1.0
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=50.0007, source="viewport",
                                     nominal=50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 1.0)

    def test_unsnapped_denominator_is_used_raw(self):
        # s13: viewport 136.4, nominal None -> continuous factor, no special case
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=136.4, source="viewport",
                                     nominal=None)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertAlmostEqual(ds.factor, 50.0 / 136.4)

    def test_mixed_scales_ink_dominant_wins_and_warns(self):
        # s03 shape: two 1:100 regions carry more ink than the 1:50 one
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(100.0),
            "region_0003": info(50.0)})
        regions = [region("region_0000", path_count=800),
                   region("region_0001", path_count=700),
                   region("region_0003", path_count=400)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 100.0)
        self.assertEqual(len(ds.warnings), 1)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_MIXED_FLOOR_PLANS")
        self.assertEqual(ds.warnings[0]["page_number"], 1)

    def test_mixed_scales_minority_ink_loses(self):
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(50.0)})
        regions = [region("region_0000", path_count=100),
                   region("region_0001", path_count=2000)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 50.0)

    def test_non_floor_plan_regions_are_ignored(self):
        # a site-plan region's 1:500 must not influence detection
        ps = PageScales(by_region={
            "region_0000": info(50.0), "region_0001": info(500.0)})
        regions = [region("region_0000"),
                   region("region_0001", region_type="site_plan")]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.warnings, [])   # not "mixed": only one fp scale

    def test_page_scale_fallback(self):
        # s02 shape: no region bindings, page-level caption
        ps = PageScales(by_region={}, page_scale=info(50.0, source="text"))
        ds = detection_scale(ps, [], page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "page")

    def test_unresolved_is_identity_no_new_warning(self):
        ds = detection_scale(PageScales(), [region("region_0000")],
                             page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertIsNone(ds.denominator)
        self.assertEqual(ds.source, "unresolved")
        self.assertEqual(ds.warnings, [])   # resolver already warned

    def test_extreme_factor_clamps_to_identity_with_warning(self):
        ps = PageScales(by_region={"region_0000": info(500.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=3)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "clamped")
        self.assertEqual(ds.denominator, 500.0)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_CLAMPED")
        self.assertEqual(ds.warnings[0]["page_number"], 3)

    def test_clamp_bounds_are_inclusive(self):
        # denominator 200 -> factor 0.25 == DETECTION_FACTOR_MIN: kept
        ps = PageScales(by_region={"region_0000": info(200.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, DETECTION_FACTOR_MIN)
        self.assertEqual(ds.source, "floor_plan_regions")
        # denominator 12.5 -> factor 4.0 == DETECTION_FACTOR_MAX: kept
        ps = PageScales(by_region={"region_0000": info(12.5)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, DETECTION_FACTOR_MAX)

    def test_tie_breaks_to_smaller_denominator_deterministically(self):
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(50.0)})
        regions = [region("region_0000", path_count=500),
                   region("region_0001", path_count=500)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 50.0)   # tie -> less aggressive scaling


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_scale_factor -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scale.factor'`.

- [ ] **Step 3: Implement `scale/factor.py`**

```python
"""One detection factor per page: which scale governs the ink detection sees.

Detection runs ONCE over the union of the floor-plan regions, so a page gets
ONE factor. On mixed-scale pages (s03, s17) the ink-dominant floor-plan scale
wins — an interim compromise the SCALE_MIXED_FLOOR_PLANS warning makes loud;
the per-scale-group fix is a follow-up (findings doc §6). Non-floor-plan
regions never reach the detectors, so their scales are ignored here by
construction, not by special-casing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import Region
from scale.resolver import PageScales
from scale.units import format_scale

# The scale every detection constant was tuned at (s01/s02 are 1:50).
DETECTION_REFERENCE_DENOMINATOR = 50.0

# Calibration domain: the corpus evidence spans 1:50–1:136. Beyond
# [1:12.5, 1:200] the drafting convention itself changes (site plans draw
# walls as single lines), and an extreme factor more likely means a resolver
# mis-binding — fall back to identity, loudly.
DETECTION_FACTOR_MIN = 0.25
DETECTION_FACTOR_MAX = 4.0


@dataclass(frozen=True)
class DetectionScale:
    factor: float
    denominator: Optional[float]
    source: str  # "floor_plan_regions" | "page" | "unresolved" | "clamped"
    warnings: list = field(default_factory=list)


def _effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY."""
    return info.nominal if info.nominal is not None else info.denominator


def detection_scale(
    page_scales: PageScales,
    regions: list[Region],
    page_number: int,
) -> DetectionScale:
    floor_plans = {r.region_id: r for r in regions
                   if r.region_type == "floor_plan"}

    votes: dict[float, int] = {}
    for rid, info in page_scales.by_region.items():
        reg = floor_plans.get(rid)
        if reg is None:
            continue
        denom = _effective_denominator(info)
        if denom is None:
            continue
        # Gates act on primitives, not blank paper: dominance is ink
        # (path count), not bbox area. max(_, 1) so a zero-count region
        # still casts a vote.
        votes[denom] = votes.get(denom, 0) + max(reg.path_count, 1)

    warnings: list[dict] = []
    if votes:
        # Tie-break: smaller denominator (less aggressive scaling), made
        # deterministic by iterating denominators in sorted order.
        denom = max(sorted(votes), key=lambda d: votes[d])
        source = "floor_plan_regions"
        if len(votes) > 1:
            warnings.append({
                "page_number": page_number,
                "warning_code": "SCALE_MIXED_FLOOR_PLANS",
                "severity": "warning",
                "message": (
                    "Floor-plan regions carry different scales ("
                    + ", ".join(format_scale(d) for d in sorted(votes))
                    + f"); detection runs at ink-dominant {format_scale(denom)}"
                ),
            })
    elif (page_scales.page_scale is not None
          and _effective_denominator(page_scales.page_scale) is not None):
        denom = _effective_denominator(page_scales.page_scale)
        source = "page"
    else:
        return DetectionScale(1.0, None, "unresolved", warnings)

    factor = DETECTION_REFERENCE_DENOMINATOR / denom
    if not (DETECTION_FACTOR_MIN <= factor <= DETECTION_FACTOR_MAX):
        warnings.append({
            "page_number": page_number,
            "warning_code": "SCALE_FACTOR_CLAMPED",
            "severity": "warning",
            "message": (
                f"Resolved scale {format_scale(denom)} gives detection factor "
                f"{factor:.3f}, outside [{DETECTION_FACTOR_MIN}, "
                f"{DETECTION_FACTOR_MAX}] — falling back to 1.0"
            ),
        })
        return DetectionScale(1.0, denom, "clamped", warnings)
    return DetectionScale(factor, denom, source, warnings)
```

Check `format_scale`'s signature in `scale/units.py` before use (it exists — exported by `scale/__init__.py`); if it takes anything other than a denominator float, adapt the two call sites.

- [ ] **Step 4: Export from `scale/__init__.py`**

Add to the imports and `__all__`:

```python
from scale.factor import (
    DETECTION_FACTOR_MAX, DETECTION_FACTOR_MIN,
    DETECTION_REFERENCE_DENOMINATOR, DetectionScale, detection_scale,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_scale_factor -v`
Expected: all PASS.

- [ ] **Step 6: Run the whole fast tier**

Run: `python -m unittest discover tests`
Expected: green (nothing existing touched).

- [ ] **Step 7: Commit**

```bash
git add scale/factor.py scale/__init__.py tests/test_scale_factor.py
git commit -m "feat(scale): detection_scale() — one ink-dominant factor per page"
```

---

### Task 2: Measure the uncertain-class constants (no production code)

The findings table (`docs/scale-normalization-findings.md` §4) marks several
constants **U** (uncertain). This task resolves the measurable ones with data
and freezes the rest under a conservative default, BEFORE any gate code is
written. Tasks 3–4 then implement the frozen table — they must not guess.

**Files:**
- Modify: `docs/scale-normalization-findings.md` (§4 table: replace U verdicts; add a §4b "measurements" note)
- Create (scratchpad only, NOT committed): `<scratchpad>/measure_hatch.py`

**Interfaces:**
- Consumes: `fixtures/sheets/*.pdf` (corpus must be downloaded), `extraction.extractor.extract_page`.
- Produces: a frozen classification table. Tasks 3–4 read their W/P verdicts from it.

- [ ] **Step 1: Write the measurement script**

The decidable question: is hatch geometry (stroke length, pitch, mark
density) **paper-space** (same px on 1:50 and 1:100 sheets) or
**world-space** (halved px on 1:100)? Compare distributions between the
1:50 sheets (s01, s02) and the 1:100 sheets (s05, s07, s12).

```python
"""Hatch geometry: paper-space or world-space? Compare 1:50 vs 1:100 sheets."""
import glob, math, statistics, sys
sys.path.insert(0, "/Users/nestimate/Documents/GitHub/agent")
import fitz
from extraction.extractor import extract_page

SHEETS = {"s01": 50, "s02": 50, "s05": 100, "s07": 100, "s12": 100}

def hatch_strokes(paths):
    """Short diagonal stroked lines — the material-mark signature."""
    out = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2 or p.fill is not None:
            continue
        (x0, y0), (x1, y1) = p.points[0], p.points[-1]
        length = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0
        off_axis = min(ang % 90.0, 90.0 - (ang % 90.0))
        if 3.0 <= length <= 60.0 and 20.0 <= off_axis <= 70.0:
            out.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0, ang, length))
    return out

def pitches(strokes):
    """Nearest-neighbor spacing measured along the field's normal.

    Group by angle (2° bins); project midpoints onto the normal; sort;
    take consecutive diffs under 20px (same field), ignore bigger jumps
    (different fields).
    """
    by_angle = {}
    for x, y, ang, _ in strokes:
        by_angle.setdefault(round(ang / 2.0), []).append(
            x * math.cos(math.radians(ang + 90.0))
            + y * math.sin(math.radians(ang + 90.0)))
    diffs = []
    for offs in by_angle.values():
        offs.sort()
        diffs += [b - a for a, b in zip(offs, offs[1:]) if 0.5 < b - a < 20.0]
    return diffs

for slug, denom in SHEETS.items():
    pdf = glob.glob(f"/Users/nestimate/Documents/GitHub/agent/fixtures/sheets/{slug}-*.pdf")[0]
    doc = fitz.open(pdf)
    strokes = hatch_strokes(extract_page(doc, 0).paths)
    ps = pitches(strokes)
    lens = [s[3] for s in strokes]
    print(f"{slug} (1:{denom}): n={len(strokes)}  "
          f"median_len={statistics.median(lens):.2f}px  "
          f"median_pitch={statistics.median(ps):.2f}px" if ps and lens
          else f"{slug}: insufficient hatch strokes ({len(strokes)})")
```

- [ ] **Step 2: Run it and interpret**

Run: `source .venv/bin/activate && python <scratchpad>/measure_hatch.py`

Decision rule, applied separately to **length** and **pitch** medians
(ratio = 1:100 median ÷ 1:50 median):

- ratio ≥ 0.8 → **paper-space** → constant stays a module constant, unscaled.
- ratio ≤ 0.65 → **world-space** → constant moves into the gates dataclass, × f.
- in between → paper-space (the conservative default: unchanged behavior),
  with the ambiguous numbers recorded in the findings doc for the 1:100
  regression review to revisit.

This freezes: `WALL_HATCH_MAX_LEN_PX`, `WALL_HATCH_MAX_PITCH_PX`,
`WALL_WEAK_MATERIAL_PER_100PX` (density is marks per band px: if mark
spacing is paper-fixed while band length is world, the safe reading follows
the pitch verdict — same class as `WALL_HATCH_MAX_PITCH_PX`).

- [ ] **Step 3: Freeze the remaining U constants by rule, not measurement**

The small tolerances have no measurable corpus signal. Freeze them
**paper-space (unchanged)** — the conservative default that preserves
today's behavior at every factor — and record the rationale + "revisit if
the 1:100 sweep shows artifacts" in the findings doc:
`WALL_CENTERLINE_MERGE_GAP_PX`, `WALL_JUNCTION_SNAP_PX`,
`WALL_WEAK_CLAIM_MARGIN_PX`, `WALL_LATTICE_PITCH_TOL_PX`,
`WALL_LATTICE_TOUCH_GAP_PX`, `WALL_JOINERY_BRIDGE_SLACK_PX`,
`WALL_REDUNDANT_THICKNESS_SLACK_PX`, `ROOM_PLUG_MID_NEAR_PX`,
`ROOM_PLUG_NEAR_PX`, `ROOM_GAP_CLOSE_PX`, `ROOM_EROSION_PX`.

- [ ] **Step 4: Update the findings table and commit**

Edit `docs/scale-normalization-findings.md` §4: every U row becomes W or P
with the measured number or the conservative-default rationale. Add the raw
measurement output as a short §4b block.

```bash
git add docs/scale-normalization-findings.md
git commit -m "docs(scale): freeze uncertain gate classes from corpus measurements"
```

---

### Task 3: `WallGates` — scale the wall-network world-space gates

**Files:**
- Modify: `detection/walls.py`
- Test: `tests/test_scale_gates.py` (new; walls half)

**Interfaces:**
- Consumes: the frozen findings table (Task 2). If Task 2 moved any hatch
  constant to W, include it below exactly like the other W fields.
- Produces: `WallGates` frozen dataclass (fields named exactly like the
  constants they scale), `WallGates.at(f)` classmethod,
  `WALL_GATES_UNSCALED = WallGates.at(1.0)`, and
  `detect_wall_network(paths, text_spans=None, exclude_path_indices=None, scale_factor=1.0)`.
  Task 4 imports `WallGates` for rooms' two walls-owned gates; Task 5 passes
  `scale_factor` from the orchestrator.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scale_gates.py` (walls half; Task 4 adds the rooms half).
Reuse the fixture helpers from `tests/test_wall_network.py` by import:

```python
"""Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5.

A "shrunk world" is a 1:100 export: every COORDINATE halves, every pen
width stays (pens are paper-space). Detection with scale_factor=0.5 must
reproduce the 1:50 result.
"""
import unittest

from detection import detect_wall_network
from detection.walls import (
    WALL_MAX_THICKNESS_PX, WALL_MIN_THICKNESS_PX, WallGates,
    WALL_GATES_UNSCALED,
)
from tests.test_wall_network import hline, path, vline, wall_band_h, wall_band_v


def shrink(paths, s=0.5):
    """Scale coordinates by s, keep stroke widths — a 1:100 export."""
    out = []
    for p in paths:
        pts = [(x * s, y * s) for (x, y) in p.points]
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        out.append(type(p)(
            path_index=p.path_index, item_type=p.item_type,
            bbox=(min(xs), min(ys), max(xs), max(ys)),
            color=p.color, fill=p.fill,
            stroke_width=p.stroke_width,      # paper-space: NOT scaled
            dashes=p.dashes, layer=p.layer, points=pts))
    return out


def room_box_walls(thickness=8.0):
    """A closed 400x300 room drawn as four double-line wall bands."""
    t = thickness
    return (wall_band_h(0, 100, 500, 100, t) + wall_band_h(2, 100, 500, 400, t)
            + wall_band_v(4, 100, 100, 400 + t, t)
            + wall_band_v(6, 500, 100, 400 + t, t))


class TestWallGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = WallGates.at(1.0)
        self.assertEqual(g.WALL_MAX_THICKNESS_PX, WALL_MAX_THICKNESS_PX)
        self.assertEqual(g.WALL_MIN_THICKNESS_PX, WALL_MIN_THICKNESS_PX)

    def test_world_gates_scale_linearly(self):
        g = WallGates.at(0.5)
        self.assertEqual(g.WALL_MAX_THICKNESS_PX, WALL_MAX_THICKNESS_PX * 0.5)

    def test_min_thickness_floored_at_one_pixel(self):
        g = WallGates.at(0.25)   # 2.0 * 0.25 = 0.5 -> floored
        self.assertEqual(g.WALL_MIN_THICKNESS_PX, 1.0)

    def test_ordering_floors_hold_at_clamp_bounds(self):
        for f in (0.25, 0.5, 1.0, 2.0, 4.0):
            g = WallGates.at(f)
            self.assertLess(g.WALL_MIN_THICKNESS_PX, g.WALL_MAX_THICKNESS_PX)
            self.assertLess(g.WALL_MAX_THICKNESS_PX,
                            g.WALL_THICK_MATERIAL_MAX_PX)


class TestWallNetworkScaled(unittest.TestCase):
    def test_identity_factor_equals_omitted(self):
        paths = room_box_walls()
        base = detect_wall_network(paths)
        same = detect_wall_network(paths, scale_factor=1.0)
        self.assertEqual(len(base.segments), len(same.segments))
        for a, b in zip(base.segments, same.segments):
            self.assertEqual((a.p1, a.p2, a.thickness),
                             (b.p1, b.p2, b.thickness))

    def test_shrunk_world_reproduces_wall_network(self):
        paths = room_box_walls(thickness=8.0)
        base = detect_wall_network(paths)
        shrunk = detect_wall_network(shrink(paths), scale_factor=0.5)
        self.assertEqual(len(base.segments), len(shrunk.segments))

    def test_shrunk_thick_wall_still_pairs(self):
        # 30px band at 1:50 (under the 36 cap) becomes 15px at 1:100 —
        # trivially under an UNscaled cap too; the discriminating case is
        # the inverse: a 60px band at 1:50 must NOT pair (over cap), and
        # its 30px shrunk twin must ALSO not pair at f=0.5 (over 18px cap).
        wide = wall_band_h(0, 100, 500, 100, thickness=60.0)
        filler = room_box_walls()  # so the network clears WALL_NETWORK_MIN_SEGMENTS
        base = detect_wall_network(filler + [p for p in wide])
        n_base = len(base.segments)
        shrunk = detect_wall_network(shrink(filler + [p for p in wide]),
                                     scale_factor=0.5)
        self.assertEqual(n_base, len(shrunk.segments))

    def test_unscaled_run_on_shrunk_world_differs(self):
        # The negative control: WITHOUT the factor, the 60px-at-1:50 band
        # shrinks to 30px and wrongly pairs under the unscaled 36px cap.
        wide = wall_band_h(0, 100, 500, 100, thickness=60.0)
        filler = room_box_walls()
        base = detect_wall_network(filler + wide)
        blind = detect_wall_network(shrink(filler + wide))  # no factor
        self.assertNotEqual(len(base.segments), len(blind.segments))
```

Note on `path_index` collisions: `room_box_walls` uses indices 0–7 and the
`wide` band also starts at 0 — renumber `wide` with start_idx 100 when
combining (`wall_band_h(100, ...)`) so indices stay unique. Apply that in
all three tests that combine fixtures.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_scale_gates -v`
Expected: ImportError (`WallGates` not defined).

- [ ] **Step 3: Implement `WallGates` and thread it**

At the top of `detection/walls.py` (after the constants block, ~line 200):

```python
@dataclass(frozen=True)
class WallGates:
    """World-space wall gates, pre-multiplied by the detection factor.

    Fields keep the exact names of the module constants they scale, so a
    use site reads `gates.WALL_MAX_THICKNESS_PX` where it read the module
    constant. Paper-space constants (pen widths, tick sizes, drafting
    tolerances) deliberately have NO field here — they never scale.
    At factor 1.0 every field equals its constant exactly.
    """
    factor: float
    WALL_FACE_MIN_LEN_PX: float
    WALL_MIN_THICKNESS_PX: float
    WALL_MAX_THICKNESS_PX: float
    WALL_THICK_MATERIAL_MAX_PX: float
    WALL_PAIR_MIN_OVERLAP_PX: float
    WALL_FILL_CLASS_MIN_INK_PX: float
    WALL_FILL_BLOCK_MAX_SIDE_PX: float
    WALL_WEAK_MIN_RUN_PX: float
    WALL_LATTICE_MIN_RUNG_LEN_PX: float
    WALL_JOINERY_BRIDGE_GAP_PX: float
    # + any hatch constant Task 2 froze as W, same pattern

    @classmethod
    def at(cls, factor: float) -> "WallGates":
        return cls(
            factor=factor,
            WALL_FACE_MIN_LEN_PX=WALL_FACE_MIN_LEN_PX * factor,
            # Floor: below ~1px the pair search chases pen-width noise.
            WALL_MIN_THICKNESS_PX=max(1.0, WALL_MIN_THICKNESS_PX * factor),
            WALL_MAX_THICKNESS_PX=WALL_MAX_THICKNESS_PX * factor,
            WALL_THICK_MATERIAL_MAX_PX=WALL_THICK_MATERIAL_MAX_PX * factor,
            WALL_PAIR_MIN_OVERLAP_PX=WALL_PAIR_MIN_OVERLAP_PX * factor,
            WALL_FILL_CLASS_MIN_INK_PX=WALL_FILL_CLASS_MIN_INK_PX * factor,
            WALL_FILL_BLOCK_MAX_SIDE_PX=WALL_FILL_BLOCK_MAX_SIDE_PX * factor,
            WALL_WEAK_MIN_RUN_PX=WALL_WEAK_MIN_RUN_PX * factor,
            # Cross-class floor: the rung floor exists to sit ABOVE the
            # hatch-stroke length cap (paper-space if Task 2 froze it P);
            # at small factors the scaled floor would sink under it and
            # hatch could fake wall-pitch fields. Floors, not asserts —
            # a 1:200 page is legitimate, not a programming error.
            WALL_LATTICE_MIN_RUNG_LEN_PX=max(
                WALL_LATTICE_MIN_RUNG_LEN_PX * factor,
                WALL_HATCH_MAX_LEN_PX + 1.0),
            WALL_JOINERY_BRIDGE_GAP_PX=WALL_JOINERY_BRIDGE_GAP_PX * factor,
        )

    def __post_init__(self):
        # Programming-error asserts (never factor-dependent in [0.25, 4]).
        assert self.WALL_MIN_THICKNESS_PX < self.WALL_MAX_THICKNESS_PX
        assert self.WALL_MAX_THICKNESS_PX < self.WALL_THICK_MATERIAL_MAX_PX


WALL_GATES_UNSCALED = WallGates.at(1.0)
```

(If Task 2 froze `WALL_HATCH_MAX_LEN_PX` as W, the rung-floor guard uses
the SCALED hatch cap and the two move together — drop the `max()` and
multiply both.) Add `from dataclasses import dataclass` if not imported.

Then thread `gates: WallGates = WALL_GATES_UNSCALED` through the use sites
mapped below (measured on `2150052`; re-grep on drift). The mechanical
rule: the function gains a keyword-only `gates: WallGates =
WALL_GATES_UNSCALED` parameter; each listed constant reference becomes
`gates.<NAME>`; NO other constant in the function changes; callers inside
walls.py pass `gates=gates` down.

| Function | Lines | Constants → `gates.` |
|---|---|---|
| `_FillRing.is_band` (+ class-body uses ~175/216) | 286 | `WALL_MAX_THICKNESS_PX` (pass gates into the method: `is_band(gates)`) |
| `_rate_fill_classes` | 377, 393 | `WALL_FILL_CLASS_MIN_INK_PX` |
| `_white_wall_candidates` | 422 | `WALL_FILL_BLOCK_MAX_SIDE_PX` |
| `_bridge_white_runs` (inner `find`) | 520 | `WALL_JOINERY_BRIDGE_GAP_PX` (SLACK@530 stays module — frozen P) |
| `_segment_bbox_distance` | 794 | `WALL_MAX_THICKNESS_PX` |
| `_wall_fill` | 856, 873, 875 | `WALL_FACE_MIN_LEN_PX`, `WALL_MIN_THICKNESS_PX`, `WALL_MAX_THICKNESS_PX` |
| `_collect_weak_faces` | 917 | `WALL_FACE_MIN_LEN_PX` |
| `_dimension_line_indices` | 954 | `WALL_FACE_MIN_LEN_PX` |
| `_band_has_wall_material` | 1049, 1078 | `WALL_WEAK_MATERIAL_PER_100PX` only if Task 2 froze it W; else untouched |
| `_face_is_material_backed` | 1100, 1124 | `WALL_WEAK_MIN_RUN_PX` (+ density if W) |
| `_demote_lattice_faces` | 1188, 1276–1279 | `WALL_MAX_THICKNESS_PX`, `WALL_LATTICE_MIN_RUNG_LEN_PX` (+ `WALL_HATCH_MAX_PITCH_PX` if W; `WALL_LATTICE_PITCH_TOL_PX` stays module — frozen P) |
| `_scan_striped_runs` | 1306, 1317–1323 | `WALL_MIN_THICKNESS_PX` (pitch/touch tolerances stay module — frozen P) |
| `_pair_faces_to_centerlines` | 1482–1538 | `WALL_MIN_THICKNESS_PX`, `WALL_MAX_THICKNESS_PX`, `WALL_THICK_MATERIAL_MAX_PX`, `WALL_PAIR_MIN_OVERLAP_PX` |
| `_collect_wall_faces` | (caller of `_wall_fill` etc.) | forwards `gates` |
| `detect_wall_network` | 1684 entry; 1802, 1808, 1890 | gains `scale_factor: float = 1.0`; builds `gates = WallGates.at(scale_factor)` first line; `WALL_MAX_THICKNESS_PX`, `WALL_WEAK_MIN_RUN_PX`, `WALL_FILL_BLOCK_MAX_SIDE_PX` → `gates.`; `WALL_CENTERLINE_MERGE_GAP_PX`@1832 stays module (frozen P) |

Untouched by design (frozen P, verify against the final Task 2 table):
`_claims_interior_pair`, `_collapse_redundant_centerlines`,
`_snap_intersections`, `_merge_collinear_segs` gap, all `WALL_DIM_TICK_*`,
`WALL_MARKER_MAX_SIDE_PX`, stroke/pen/color gates.

Audit completeness check after editing — every remaining bare reference to
a W-class constant must be a definition or a `WallGates.at` line:

```bash
grep -nE "WALL_(FACE_MIN_LEN|MIN_THICKNESS|MAX_THICKNESS|THICK_MATERIAL_MAX|PAIR_MIN_OVERLAP|FILL_CLASS_MIN_INK|FILL_BLOCK_MAX_SIDE|WEAK_MIN_RUN|LATTICE_MIN_RUNG_LEN|JOINERY_BRIDGE_GAP)_PX" detection/walls.py | grep -v "gates\.\|^[0-9]*: *#\|= *[0-9]\|WallGates.at\|factor,$"
```

- [ ] **Step 4: Run the new tests**

Run: `python -m unittest tests.test_scale_gates -v`
Expected: PASS (all construction + identity + shrunk-world + negative-control tests).

- [ ] **Step 5: Run the whole fast tier — identity must hold**

Run: `python -m unittest discover tests`
Expected: green. Any wall/room test failure here means f=1.0 identity broke — fix before proceeding, do not adjust the failing test.

- [ ] **Step 6: Commit**

```bash
git add detection/walls.py tests/test_scale_gates.py
git commit -m "feat(walls): WallGates — world-space gates scale with the detection factor"
```

---

### Task 4: `RoomGates` — scale the room-stage world-space gates

**Files:**
- Modify: `detection/rooms.py`
- Test: `tests/test_scale_gates.py` (extend with the rooms half)

**Interfaces:**
- Consumes: `WallGates` (Task 3) for the two walls-owned constants rooms
  uses; frozen findings table (Task 2).
- Produces: `RoomGates` frozen dataclass + `RoomGates.at(f)` +
  `ROOM_GATES_UNSCALED`, and `detect_rooms(network, doors, windows,
  page_width_px, page_height_px, text_spans=None, scale_factor=1.0)`.
  Task 5 passes `scale_factor` from the orchestrator.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scale_gates.py`. Room fixtures: build the closed
`room_box_walls()` from the walls half, run the real pipeline order
(network → rooms) with no doors/windows:

```python
from detection import detect_rooms
from detection.rooms import ROOM_MIN_AREA_PX2, ROOM_GATES_UNSCALED, RoomGates


def rooms_for(paths, scale_factor=1.0, page=(700.0, 600.0)):
    network = detect_wall_network(paths, scale_factor=scale_factor)
    return detect_rooms(network, [], [], page[0], page[1],
                        scale_factor=scale_factor)


class TestRoomGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = RoomGates.at(1.0)
        self.assertEqual(g.ROOM_MIN_AREA_PX2, ROOM_MIN_AREA_PX2)

    def test_areas_scale_by_factor_squared(self):
        g = RoomGates.at(0.5)
        self.assertEqual(g.ROOM_MIN_AREA_PX2, ROOM_MIN_AREA_PX2 * 0.25)


class TestRoomsScaled(unittest.TestCase):
    def test_identity_factor_equals_omitted(self):
        paths = room_box_walls()
        a = rooms_for(paths)
        b = rooms_for(paths, scale_factor=1.0)
        self.assertEqual(len(a), len(b))
        self.assertEqual([c.bbox for c in a], [c.bbox for c in b])

    def test_shrunk_world_room_still_detected(self):
        paths = room_box_walls()
        base = rooms_for(paths)
        shrunk = rooms_for(shrink(paths), scale_factor=0.5,
                           page=(350.0, 300.0))
        self.assertEqual(len(base), len(shrunk))
        self.assertEqual(len(shrunk), 1)

    def test_area_floor_applies_at_f_squared(self):
        # A 58x58 interior (3364px² > 2500 floor) detects at 1:50. Its
        # shrunk twin is 29x29 = 841px² — BELOW the unscaled floor, above
        # the f² floor (625). Scale-aware detection keeps it; the blind
        # run is the negative control.
        t = 8.0
        small = (wall_band_h(0, 100, 174 + t, 100, t)
                 + wall_band_h(2, 100, 174 + t, 166, t)
                 + wall_band_v(4, 100, 100, 166 + t, t)
                 + wall_band_v(6, 166, 100, 166 + t, t))
        base = rooms_for(small, page=(300.0, 300.0))
        self.assertEqual(len(base), 1)
        shrunk = rooms_for(shrink(small), scale_factor=0.5,
                           page=(150.0, 150.0))
        self.assertEqual(len(shrunk), 1)
        blind = rooms_for(shrink(small), scale_factor=1.0,
                          page=(150.0, 150.0))
        self.assertEqual(len(blind), 0)   # eaten by the unscaled area floor
```

Geometry note: `wall_band_v(4, 100, 100, 166 + t, t)` puts inner faces at
x∈[100+t? — no: faces at x=100 and x=100+t]. The interior span is
(100+t)…166 horizontally and (100+t)…166 vertically = 58×58 with t=8.
Verify the exact enclosed area in the first assertion while implementing;
if the fixture needs ±2px adjustment to clear dilation, adjust the OUTER
coordinates (174/166), never the assertion counts.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_scale_gates -v`
Expected: ImportError (`RoomGates` not defined).

- [ ] **Step 3: Implement `RoomGates` and thread it**

After the rooms constants block (~line 240 of `detection/rooms.py`):

```python
@dataclass(frozen=True)
class RoomGates:
    """World-space room gates pre-multiplied by the detection factor
    (areas by factor²). Same field-naming rule as WallGates. The two
    walls-owned constants rooms consumes are scaled here identically to
    WallGates so the stages can never disagree about a wall's size."""
    factor: float
    ROOM_MIN_AREA_PX2: float                 # × f²
    ROOM_BLIND_WINDOW_MAX_AREA_PX2: float    # × f²
    ROOM_OPENING_SEAL_PX: float
    ROOM_PLUG_ANCHOR_WIN_PX: float
    ROOM_PLUG_HALF_WIDTH_PX: float
    ROOM_FOLD_STACK_NEAR_PX: float
    ROOM_FOLD_JAMB_MIN_LEN_PX: float
    WALL_MAX_THICKNESS_PX: float             # walls-owned, used by rooms

    @classmethod
    def at(cls, factor: float) -> "RoomGates":
        return cls(
            factor=factor,
            ROOM_MIN_AREA_PX2=ROOM_MIN_AREA_PX2 * factor * factor,
            ROOM_BLIND_WINDOW_MAX_AREA_PX2=(
                ROOM_BLIND_WINDOW_MAX_AREA_PX2 * factor * factor),
            ROOM_OPENING_SEAL_PX=ROOM_OPENING_SEAL_PX * factor,
            ROOM_PLUG_ANCHOR_WIN_PX=ROOM_PLUG_ANCHOR_WIN_PX * factor,
            ROOM_PLUG_HALF_WIDTH_PX=ROOM_PLUG_HALF_WIDTH_PX * factor,
            ROOM_FOLD_STACK_NEAR_PX=ROOM_FOLD_STACK_NEAR_PX * factor,
            ROOM_FOLD_JAMB_MIN_LEN_PX=ROOM_FOLD_JAMB_MIN_LEN_PX * factor,
            WALL_MAX_THICKNESS_PX=WALL_MAX_THICKNESS_PX * factor,
        )


ROOM_GATES_UNSCALED = RoomGates.at(1.0)
```

Use-site map (anchors on `2150052`; same mechanical rule as Task 3 —
keyword-only `gates: RoomGates = ROOM_GATES_UNSCALED`, listed constants →
`gates.`, callers forward):

| Function | Lines | Constants → `gates.` |
|---|---|---|
| `_window_seal` | 289 | `ROOM_PLUG_HALF_WIDTH_PX` |
| `_open_leaf_edges` | 325 | `ROOM_PLUG_HALF_WIDTH_PX` |
| `_door_plugs` | 494–597 | `ROOM_OPENING_SEAL_PX`, `ROOM_PLUG_ANCHOR_WIN_PX`, `ROOM_PLUG_HALF_WIDTH_PX` (`ROOM_PLUG_NEAR_PX`/`ROOM_PLUG_MID_NEAR_PX` stay module — frozen P) |
| `_folding_chain_gap_plug` | 628, 639 | `ROOM_FOLD_JAMB_MIN_LEN_PX`, `ROOM_FOLD_STACK_NEAR_PX` |
| `detect_rooms` body + its nested helpers | 711 entry; 980, 1030, 1067–1126 | gains `scale_factor: float = 1.0`, builds `gates = RoomGates.at(scale_factor)` first line; `ROOM_OPENING_SEAL_PX`, `WALL_MAX_THICKNESS_PX`, `ROOM_MIN_AREA_PX2`, `ROOM_BLIND_WINDOW_MAX_AREA_PX2` → `gates.` (nested defs close over `gates` — no param needed) |
| `_free_space_components` | 660–675 | untouched (`ROOM_GAP_CLOSE_PX` frozen P) |
| `_swing_hinge_edges`, `_restrict_swing_plugs` | 390–445 | untouched (`ROOM_PLUG_NEAR_PX` frozen P) |

Run the completeness grep, walls-style, over the eight scaled names in
`detection/rooms.py`.

- [ ] **Step 4: Run the new tests**

Run: `python -m unittest tests.test_scale_gates -v`
Expected: PASS, including both negative controls.

- [ ] **Step 5: Run the whole fast tier**

Run: `python -m unittest discover tests`
Expected: green (identity preserved).

- [ ] **Step 6: Commit**

```bash
git add detection/rooms.py tests/test_scale_gates.py
git commit -m "feat(rooms): RoomGates — world-space room gates scale with the detection factor"
```

---

### Task 5: Plumb the factor through orchestrator, pipeline, and summary

**Files:**
- Modify: `detection/orchestrator.py:32-60` (`run_heuristics`)
- Modify: `pipeline.py` (~585 `resolve_page_scales` block, ~615 `run_heuristics` call, `scale_summary_dict` at 261, `build_page_summary` at ~281, `scale_table` at 221 optionally)
- Test: extend `tests/test_scale_gates.py`

**Interfaces:**
- Consumes: `detection_scale` (Task 1), `run_heuristics`/`detect_wall_network`/`detect_rooms` signatures (Tasks 3–4).
- Produces: `run_heuristics(…, scale_factor: float = 1.0)`; `summary.json` pages gain `scales.detection = {"factor": …, "denominator": …, "source": …}`.

- [ ] **Step 1: Write the failing test**

```python
class TestOrchestratorForwardsFactor(unittest.TestCase):
    def test_run_heuristics_scale_factor_reaches_rooms(self):
        from detection import run_heuristics
        from models import PageData
        paths = shrink(room_box_walls())
        pd = PageData(page_number=1, width_px=350.0, height_px=300.0,
                      page_type="vector-rich", paths=paths, text_spans=[],
                      images=[])
        scaled = run_heuristics(pd, [], scale_factor=0.5)
        blind = run_heuristics(pd, [])
        rooms_scaled = [c for c in scaled if c.entity_type == "room"]
        rooms_blind = [c for c in blind if c.entity_type == "room"]
        self.assertEqual(len(rooms_scaled), 1)
        # The blind run may or may not find the room (thickness 4px vs
        # unscaled gates) — the discriminating assertion is only that the
        # factor CHANGED the outcome pathway; assert on the scaled result.
```

Check `PageData`'s actual constructor fields in `models.py:43` before
writing (it has more fields with defaults; supply only the required ones —
adjust to the dataclass definition, e.g. `ocgs`/`plumber` fields if
non-default).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_scale_gates.TestOrchestratorForwardsFactor -v`
Expected: TypeError (`run_heuristics() got an unexpected keyword argument 'scale_factor'`).

- [ ] **Step 3: Implement**

`detection/orchestrator.py` — signature gains trailing
`scale_factor: float = 1.0`; the two forwards:

```python
        network = None if disable_rooms else detect_wall_network(
            ..., scale_factor=scale_factor)   # keep existing args
        ...
        rooms = detect_rooms(..., scale_factor=scale_factor)
```

`pipeline.py`, right after the `resolve_page_scales` call (~line 595):

```python
            det_scale = detection_scale(page_scales, region_result.regions,
                                        page_num)
            page_warnings_extra = det_scale.warnings  # fold with resolver's
```

(import `from scale.factor import detection_scale` at the top, next to the
existing `from scale.resolver import …` import at line 31). Fold
`det_scale.warnings` exactly where `page_scales.warnings` already folds
into the page's warning list — find that fold and append to the same list.
Pass the factor at the `run_heuristics` call (~line 615):
`scale_factor=det_scale.factor`.

`scale_summary_dict(page_scales)` at line 261 → add a parameter
`det_scale` and a `"detection"` key:

```python
def scale_summary_dict(page_scales: PageScales, det_scale=None) -> dict:
    out = { ...existing... }
    if det_scale is not None:
        out["detection"] = {
            "factor": round(det_scale.factor, 4),
            "denominator": det_scale.denominator,
            "source": det_scale.source,
        }
    return out
```

Update its call site in `build_page_summary` (line ~296) to pass the page's
`det_scale` (thread it as a new `build_page_summary` parameter from
`run_extract`).

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_scale_gates -v` then `python -m unittest discover tests`
Expected: all PASS.

- [ ] **Step 5: Smoke-run one real 1:50 sheet and one 1:100 sheet**

```bash
python app.py extract fixtures/sheets/s01-floor-plans.pdf --no-gemini --out /tmp/scale-smoke-s01
python app.py extract fixtures/sheets/s05-existing-floor-and-elevations.pdf --no-gemini --out /tmp/scale-smoke-s05
```

Expected: s01's summary shows `"detection": {"factor": 1.0, …}`; s05 shows
`factor 0.5, source floor_plan_regions`. No crashes, no new warnings on s01.

- [ ] **Step 6: graphify + commit**

```bash
graphify update .
git add detection/orchestrator.py pipeline.py tests/test_scale_gates.py graphify-out
git commit -m "feat(pipeline): thread the detection scale factor into wall/room heuristics"
```

---

### Task 6: Regression sweep, docs, and the user checkpoint

**Files:**
- Modify: `docs/scale-normalization-findings.md` (record sweep outcome), `CLAUDE.md` (one short paragraph in the module-layout/rooms area noting walls/rooms gates now scale via `detection_scale`)
- No production code.

**Interfaces:**
- Consumes: everything above, the downloaded corpus.
- Produces: a clean sweep + a REVIEW list for the user. **This task ends at a user checkpoint — do not iterate past it.**

- [ ] **Step 1: Verify fixtures then run the sweep**

```bash
python tools/fetch_fixtures.py     # bytes must match the manifest
python tools/regress.py
```

- [ ] **Step 2: Read the report against expectations**

Hard failures (exit 1) — a lost `confirmed` or returned `false_positive`
ANYWHERE — must be fixed before anything else. Expected shape:

- 1:50 sheets (s01, s02, s04, s08, s14, s15) and unresolved sheets (s10,
  s11, s16, s18, s20): **unchanged** — factor 1.0 end-to-end. Any diff
  here is an identity bug: bisect it (likely a mis-threaded gate or a
  wrongly-scaled P constant) — one fix, one sweep, then stop again.
- 1:100 sheets (s05, s06, s07, s12), mixed (s03, s17 — now running at
  0.5), and s13 (~0.37): changed detections are EXPECTED and print under
  REVIEW. New detections never fail the sweep.

- [ ] **Step 3: Record and hand over**

Append the sweep outcome (per-sheet REVIEW counts, any surprises) to
`docs/scale-normalization-findings.md` §3, update `CLAUDE.md`, commit:

```bash
git add docs/scale-normalization-findings.md CLAUDE.md
git commit -m "docs(scale): record post-scaling sweep outcome"
```

Then STOP and report to the user: the sweep summary, which review images
to open (`outputs/regress/<slug>/<ts>/pages/page_NN/review_<type>.png`),
and that `python tools/review.py s05 s07 s12 s03 s17 s13 s06` records their
verdicts. The user reviews; verdict data commits are theirs. Any fix
iteration after their review follows one-fix-one-sweep-then-ask.

---

## Self-review notes (already applied)

- **Spec coverage:** factor computation §1 → Task 1; plumbing §2 → Tasks 3–5 (signatures) + Task 5 (pipeline/summary); classification §3 → Task 2 (freeze) + Tasks 3–4 (implementation); interactions §4 → gates-constructor floors + `TestWallGatesConstruction.test_ordering_floors_hold_at_clamp_bounds`; testing §5 → Tasks 1, 3, 4, 5 tests + Task 6 sweep; findings-doc criterion → Tasks 2 and 6. Deviation from spec §4 wording: cross-class orderings are enforced as **floors** rather than raising assertions, because at f=0.25 the rung-floor/hatch-cap ordering legitimately inverts when hatch is paper-space — a floor preserves the invariant; an assert would crash a legitimate 1:200 page. Spec intent (fail loudly on programming errors) is kept via the remaining asserts.
- **Type consistency:** `detection_scale(page_scales, regions, page_number) -> DetectionScale` used identically in Tasks 1 and 5; `scale_factor: float = 1.0` spelled the same on `detect_wall_network`, `detect_rooms`, `run_heuristics`; gates field names mirror constant names exactly.
- **Known line-drift risk:** all line anchors stamped `2150052`; every task re-greps before editing.
