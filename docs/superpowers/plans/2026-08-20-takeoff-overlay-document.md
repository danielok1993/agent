# takeoff.json Overlay Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `takeoff.json` into a single parent→child document carrying room polygons, opening bboxes, sizes and an explicit page frame, so the web app can build both the PDF overlay and the editable assembly table from one file.

**Architecture:** Openings move from per-room nested copies to one page-level array cross-referenced by id, computed once each. Rooms gain their geometry, and rooms with no resolvable scale now appear with `scale: null` instead of being dropped. `takeoff/quantities.py` keeps the maths; a new `takeoff/document.py` owns serialisation. Geometry stays in 150-DPI pixels with a `page_frame` block recording the space.

**Tech Stack:** Python 3, `shapely`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-20-takeoff-overlay-document-design.md`

## Global Constraints

- All coordinates are 150-DPI pixels, top-left origin, y-down. `extractor.page_transform` has already applied the page's `/Rotate`, so coordinates match the rendered page and need no further transform. `page_frame.rotation` is provenance only.
- `SCALE = 150/72`, so `pdf_pt = px * 72/150`.
- Room polygons live at `Entity.attributes["polygon"]` as a list of `[x, y]` pairs.
- `takeoff/` is PURE: no I/O, no prompting, no globals. Warnings travel on `TakeoffPage.warnings`.
- Warning dicts use `SCREAMING_SNAKE_CASE` `warning_code`, plus `severity` and `message`.
- `detection/` must not be modified by any task in this plan.
- This is a deliberate BREAKING change to `takeoff.json`. No compatibility shim. `schema_version: 1`.
- Never commit a PDF, and never put address-bearing text into a tracked file.
- Git: work on a new branch; never add a `Co-Authored-By` trailer to a commit message.
- Tests run with `source .venv/bin/activate` first. Fast tier: `python -m unittest discover tests`.

---

### Task 1: Move `scale_summary_dict` into `scale/resolver.py`

`takeoff/` needs the same page/region scale block that `summary.json` already writes. It lives in `pipeline.py` today, and `takeoff/` must not import `pipeline`. Moving it to the module that defines `PageScales` lets both import it.

**Files:**
- Modify: `scale/resolver.py` (add the function)
- Modify: `pipeline.py:278-296` (remove the function, import it instead)
- Test: `tests/test_takeoff_scale.py`

**Interfaces:**
- Consumes: `scale.resolver.PageScales`, `scale.factor.DetectionScale`
- Produces: `scale.resolver.scale_summary_dict(page_scales: PageScales, det_scale=None) -> dict`

- [ ] **Step 1: Create the branch**

```bash
cd /Users/nestimate/Documents/GitHub/agent
git checkout main
git checkout -b feat/takeoff-overlay-document
```

- [ ] **Step 2: Write the failing test**

Append to `tests/test_takeoff_scale.py`:

```python
class TestScaleSummaryDict(unittest.TestCase):
    def test_page_and_region_scales_serialise(self):
        from models import ScaleInfo
        from scale.factor import DetectionScale
        from scale.resolver import PageScales, scale_summary_dict

        info = ScaleInfo(denominator=50.0, source="text", nominal=50.0)
        out = scale_summary_dict(
            PageScales(by_region={"region_0000": info}, page_scale=info),
            DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions"),
        )
        self.assertEqual(out["by_region"]["region_0000"]["denominator"], 50.0)
        self.assertEqual(out["page_scale"]["source"], "text")
        self.assertEqual(out["detection"]["factor"], 1.0)

    def test_no_detection_scale_omits_the_block(self):
        from scale.resolver import PageScales, scale_summary_dict
        out = scale_summary_dict(PageScales())
        self.assertNotIn("detection", out)
        self.assertIsNone(out["page_scale"])
        self.assertEqual(out["by_region"], {})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_scale -v`
Expected: FAIL with `ImportError: cannot import name 'scale_summary_dict' from 'scale.resolver'`

- [ ] **Step 4: Move the function**

Cut this function out of `pipeline.py` (currently at line 278) and paste it into `scale/resolver.py`, unchanged, after the `PageScales` dataclass:

```python
def scale_summary_dict(page_scales: PageScales, det_scale: "DetectionScale | None" = None) -> dict:
    """The scales block written into each page's summary.json entry, and into
    takeoff.json's `scale` block.

    Lives here rather than in pipeline.py because it serialises PageScales,
    and takeoff/ needs it too — takeoff/ must never import pipeline.
    The DetectionScale annotation is a string so no import of scale.factor is
    needed; only three attributes are read.
    """
    def one(info):
        return {"denominator": info.denominator, "source": info.source,
                "raw": info.raw, "nominal": info.nominal,
                "conflict": info.conflict,
                "bbox": list(info.bbox) if info.bbox else None}

    out = {
        "by_region": {rid: one(info) for rid, info in page_scales.by_region.items()},
        "page_scale": one(page_scales.page_scale) if page_scales.page_scale else None,
    }
    if det_scale is not None:
        out["detection"] = {
            "factor": round(det_scale.factor, 4),
            "denominator": det_scale.denominator,
            "source": det_scale.source,
        }
    return out
```

In `pipeline.py`, add `scale_summary_dict` to the existing import from `scale.resolver` (line 32), so it reads:

```python
from scale.resolver import PageScales, resolve_page_scales, scale_summary_dict
```

The call site at `pipeline.py:322` (`"scales": scale_summary_dict(page_scales, det_scale)`) is unchanged.

- [ ] **Step 5: Run the tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_scale tests.test_takeoff_pipeline -v`
Expected: PASS. The pipeline tests exercise `_page_summary_dict`, which calls the moved function — they prove the move did not break the caller.

- [ ] **Step 6: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no new failures.

- [ ] **Step 7: Commit**

```bash
git add scale/resolver.py pipeline.py tests/test_takeoff_scale.py
git commit -m "refactor(scale): move scale_summary_dict to resolver so takeoff can use it"
```

---

### Task 2: Openings become page-level records, computed once

**Files:**
- Modify: `takeoff/openings.py` (split the evidence-only width out of `opening_width_px`)
- Modify: `takeoff/quantities.py` (new `OpeningTakeoff`; build the page-level list; rooms deduct from it)
- Test: `tests/test_takeoff_openings.py`, `tests/test_takeoff_quantities.py`

**Interfaces:**
- Consumes: `assign_openings(room_polygons, openings) -> (assigned, unassigned, over_assigned)` from Task 0 (pre-existing)
- Produces:
  - `takeoff.openings.opening_width_px_from_evidence(entity_type: str, evidence: dict) -> tuple[float, str] | None`
  - `takeoff.quantities.OpeningTakeoff` dataclass with fields
    `opening_id, type, assembly_type, tag, confidence, bbox, room_ids, dropped_room_ids, width_px, width_source, width_m, height_m, area_m2, clamped`
  - `TakeoffPage.openings: list[OpeningTakeoff]`
  - `RoomTakeoff.opening_ids: list[str]` replacing `RoomTakeoff.openings`

**Behaviour change to expect:** an opening's width is now computed ONCE, against the polygon of its FIRST assigned room. Today it is computed per room. The two differ only when `width_source == "bbox_edge"` (the last-resort fallback — every evidence-backed path ignores the polygon) AND the opening serves two rooms. Room two's wall deduction may shift slightly for such openings. This is intended: one physical opening has one width.

- [ ] **Step 1: Write the failing test for the width split**

Create `tests/test_takeoff_openings.py`:

```python
"""Evidence-only opening width (takeoff/openings.py)."""
import unittest

from shapely.geometry import Polygon

from takeoff.openings import opening_width_px, opening_width_px_from_evidence

SQUARE = Polygon([(0, 0), (200, 0), (200, 200), (0, 200)])


class TestOpeningWidthFromEvidence(unittest.TestCase):
    def test_a_window_reads_its_opening_width(self):
        self.assertEqual(
            opening_width_px_from_evidence("window", {"opening_width_px": 54.5}),
            (54.5, "opening_width_px"))

    def test_a_sliding_door_reads_its_panel_length(self):
        self.assertEqual(
            opening_width_px_from_evidence("door", {"panel_length_px": 94.5}),
            (94.5, "panel_length_px"))

    def test_no_evidence_returns_none_rather_than_falling_back(self):
        self.assertIsNone(opening_width_px_from_evidence("door", {}))
        self.assertIsNone(opening_width_px_from_evidence("window", {}))

    def test_the_polygon_form_still_falls_back_to_the_bbox_edge(self):
        w, src = opening_width_px("door", (10, 10, 40, 16), {}, SQUARE)
        self.assertEqual(src, "bbox_edge")
        self.assertGreater(w, 0)

    def test_the_polygon_form_prefers_evidence_over_the_bbox(self):
        self.assertEqual(
            opening_width_px("door", (10, 10, 40, 16), {"panel_length_px": 94.5}, SQUARE),
            (94.5, "panel_length_px"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_openings -v`
Expected: FAIL with `ImportError: cannot import name 'opening_width_px_from_evidence'`

- [ ] **Step 3: Split the width function**

In `takeoff/openings.py`, replace the whole `opening_width_px` function (currently lines 106-130) with:

```python
def opening_width_px_from_evidence(entity_type: str, evidence: dict):
    """Width from detector evidence alone, or None.

    Separated from opening_width_px because an UNASSIGNED opening has no room
    boundary to measure a bbox edge against, and the page-level opening record
    still wants whatever width the detector did establish.
    """
    evidence = evidence or {}
    if entity_type == "window":
        if evidence.get("orientation") == "diagonal":
            # An angled bay face: the axis-aligned opening width is the
            # glazing run's projection, the run itself is what is built.
            w = _positive(evidence.get("glazing_len_px"))
            if w is not None:
                return w, "glazing_len_px"
        w = _positive(evidence.get("opening_width_px"))
        if w is not None:
            return w, "opening_width_px"
        return None

    single = _single_swing_width(evidence)
    if single is not None:
        return single
    for key in ("opening_line",):
        w = _chord_length(evidence.get(key))
        if w is not None:
            return w, key
    for key in ("opening_span_px", "panel_length_px"):
        w = _positive(evidence.get(key))
        if w is not None:
            return w, key
    return None


def opening_width_px(entity_type: str, bbox, evidence: dict,
                     room_polygon: Polygon) -> tuple[float, str]:
    hit = opening_width_px_from_evidence(entity_type, evidence)
    if hit is not None:
        return hit
    return _bbox_edge_along_boundary(bbox, room_polygon), "bbox_edge"
```

- [ ] **Step 4: Run it to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_openings tests.test_takeoff_quantities -v`
Expected: PASS. `test_takeoff_quantities` proves the refactor is behaviour-preserving for the existing per-room path.

- [ ] **Step 5: Commit the split**

```bash
git add takeoff/openings.py tests/test_takeoff_openings.py
git commit -m "refactor(takeoff): split evidence-only opening width from the bbox fallback"
```

- [ ] **Step 6: Write the failing test for page-level openings**

Append to `tests/test_takeoff_quantities.py`, inside `class TestComputeTakeoff`:

```python
    def test_a_shared_door_is_one_opening_with_two_room_ids(self):
        w = 3 * PX_PER_M_50
        left = _room("room_a", 100, 100, 100 + w, 100 + w)
        right = _room("room_b", 100 + w + 8, 100, 100 + 2 * w + 8, 100 + w)
        # A door in the party wall, touching both grown polygons.
        door, cand = _door("door_0000", (100 + w + 1, 300, 100 + w + 7, 300 + 106),
                           {"panel_length_px": 106.0})
        page = self._run([left, right, door], [cand])
        self.assertEqual(len(page.openings), 1)
        op = page.openings[0]
        self.assertEqual(op.opening_id, "door_0000")
        self.assertEqual(sorted(op.room_ids), ["room_a", "room_b"])
        self.assertEqual(op.width_source, "panel_length_px")
        self.assertAlmostEqual(op.width_m, 0.9, places=2)
        for r in page.rooms:
            self.assertEqual(r.opening_ids, ["door_0000"])

    def test_an_unassigned_opening_is_present_with_no_rooms(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0007", (5000, 5000, 5006, 5100),
                           {"panel_length_px": 106.0})
        page = self._run([room, door], [cand])
        ids = [o.opening_id for o in page.openings]
        self.assertIn("door_0007", ids)
        op = next(o for o in page.openings if o.opening_id == "door_0007")
        self.assertEqual(op.room_ids, [])
        self.assertEqual(op.width_px, 106.0)     # evidence survives
        self.assertIsNone(op.width_m)            # no room, so no scale
        self.assertIsNone(op.area_m2)
        self.assertEqual(page.rooms[0].opening_ids, [])

    def test_an_unassigned_opening_without_evidence_has_no_width(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0008", (5000, 5000, 5030, 5006), {})
        page = self._run([room, door], [cand])
        op = next(o for o in page.openings if o.opening_id == "door_0008")
        self.assertIsNone(op.width_px)
        self.assertIsNone(op.width_source)

    def test_the_opening_carries_its_tag_confidence_and_assembly_type(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0000", (100, 200, 106, 306),
                           {"panel_length_px": 106.0})
        door.label = "GD9"
        door.attributes["assembly_type"] = "sliding"
        page = self._run([room, door], [cand])
        op = page.openings[0]
        self.assertEqual(op.tag, "GD9")
        self.assertEqual(op.assembly_type, "sliding")
        self.assertEqual(op.confidence, 0.8)

    def test_a_three_room_overreach_records_the_dropped_rooms(self):
        rooms = [_room("room_a", 100, 100, 200, 200),
                 _room("room_b", 210, 100, 310, 200),
                 _room("room_c", 100, 210, 200, 310)]
        door, cand = _door("door_0000", (195, 195, 215, 215), {"panel_length_px": 20.0})
        page = self._run(rooms + [door], [cand])
        op = page.openings[0]
        self.assertEqual(len(op.room_ids), 2)
        self.assertEqual(len(op.dropped_room_ids), 1)
        self.assertNotIn(op.dropped_room_ids[0], op.room_ids)

    def test_a_room_deducts_the_area_of_each_of_its_openings(self):
        w = 3 * PX_PER_M_50
        room = _room("room_a", 100, 100, 100 + w, 100 + w)
        door, cand = _door("door_0000", (100, 200, 106, 306),
                           {"panel_length_px": 106.0})
        page = self._run([room, door], [cand])
        r = page.rooms[0]
        op = page.openings[0]
        self.assertAlmostEqual(r.wall_net_m2, r.wall_gross_m2 - op.area_m2, places=2)
```

- [ ] **Step 7: Run it to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_quantities -v`
Expected: FAIL with `AttributeError: 'TakeoffPage' object has no attribute 'openings'`

- [ ] **Step 8: Add `OpeningTakeoff` and the page-level list**

In `takeoff/quantities.py`, add this dataclass immediately after `RoomTakeoff`:

```python
@dataclass
class OpeningTakeoff:
    """One physical door or window, once. A shared opening carries both room
    ids rather than being duplicated under each room."""
    opening_id: str
    type: str                                  # "door" | "window"
    assembly_type: Optional[str]
    tag: Optional[str]
    confidence: float
    bbox: tuple
    room_ids: list = field(default_factory=list)        # [] when unassigned
    dropped_room_ids: list = field(default_factory=list)
    width_px: Optional[float] = None
    width_source: Optional[str] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    area_m2: Optional[float] = None
    clamped: bool = False
```

Add `openings: list = field(default_factory=list)` to `TakeoffPage`, beside `rooms`.

Add the import at the top of `takeoff/quantities.py`, extending the existing `takeoff.openings` import:

```python
from takeoff.openings import (
    assign_openings, opening_width_px, opening_width_px_from_evidence,
)
```

Replace the `# Openings → rooms.` block (currently lines 183-194) with:

```python
    # Openings → rooms. Each opening is measured ONCE, against the polygon of
    # its first assigned room: the room polygon only matters to the bbox_edge
    # fallback, and one physical opening has one width.
    openings = [(e.entity_id, e.entity_type, e.bbox) for e in entities
                if e.entity_type in ("door", "window")]
    opening_by_id = {e.entity_id: e for e in entities if e.entity_type in ("door", "window")}
    assigned, unassigned, over_assigned = assign_openings(room_polys, openings)
    page.unassigned_openings = unassigned
    page.over_assigned_openings = [{"id": oid, "dropped_rooms": list(dropped)}
                                   for oid, dropped in over_assigned]
    if over_assigned:
        _warn(page, "TAKEOFF_OPENING_MULTI_ROOM", "info",
              f"{len(over_assigned)} opening(s) reached 3+ rooms; kept the two "
              "nearest room boundaries — an opening serves at most two spaces")

    # Invert assigned (room → [opening]) into opening → [room], preserving the
    # room order the entity list gave, so the "first" room is deterministic.
    rooms_by_opening: dict[str, list[str]] = {}
    for rid in room_polys:
        for oid in assigned.get(rid, []):
            rooms_by_opening.setdefault(oid, []).append(rid)
    dropped_by_opening = {oid: list(dropped) for oid, dropped in over_assigned}
```

- [ ] **Step 9: Build the opening records and switch rooms to `opening_ids`**

Still in `compute_takeoff`, insert this immediately AFTER the plausibility block sets `page.verdicts` (so `room_meta` carries its final `RoomScale`), and BEFORE the `for rid, (e, rs, poly) in room_meta.items():` loop:

```python
    # Page-level opening records. A room's scale is what converts px to metres,
    # so an opening in no room — or in an unscaled one — keeps its pixel width
    # and gets no metres.
    opening_records: dict[str, OpeningTakeoff] = {}
    for oid, oe in opening_by_id.items():
        rids = rooms_by_opening.get(oid, [])
        primary = rids[0] if rids else None
        if primary is not None:
            w_px, w_src = opening_width_px(
                oe.entity_type, oe.bbox, evidence.get(oid, {}), room_polys[primary])
        else:
            hit = opening_width_px_from_evidence(oe.entity_type, evidence.get(oid, {}))
            w_px, w_src = hit if hit is not None else (None, None)

        rec = OpeningTakeoff(
            opening_id=oid,
            type=oe.entity_type,
            assembly_type=(oe.attributes or {}).get("assembly_type"),
            tag=oe.label,
            confidence=oe.confidence,
            bbox=tuple(oe.bbox),
            room_ids=list(rids),
            dropped_room_ids=dropped_by_opening.get(oid, []),
            width_px=round(w_px, 2) if w_px is not None else None,
            width_source=w_src,
        )

        D = room_meta[primary][1].denominator if primary in room_meta else None
        if D is not None and w_px is not None:
            h_m = heights.door_m if oe.entity_type == "door" else heights.window_m
            if h_m > heights.ceiling_m:
                h_m = heights.ceiling_m
                rec.clamped = True
                _warn(page, "TAKEOFF_OPENING_TALLER_THAN_CEILING", "info",
                      "An opening height exceeded the ceiling height and was clamped")
            w_m = px_to_m(w_px, D)
            rec.width_m = round(w_m, 2)
            rec.height_m = round(h_m, 2)
            rec.area_m2 = round(w_m * h_m, 2)
        opening_records[oid] = rec
    page.openings = [opening_records[oid] for oid in opening_by_id]
```

Then, inside the existing `for rid, (e, rs, poly) in room_meta.items():` loop, replace the whole `ops = []` / `deduct = 0.0` / `for oid in assigned.get(rid, []):` block with:

```python
        opening_ids = list(assigned.get(rid, []))
        deduct = sum(opening_records[oid].area_m2 or 0.0 for oid in opening_ids)
```

and in the `RoomTakeoff(...)` construction replace `openings=ops,` with `opening_ids=opening_ids,`.

Rename the field on `RoomTakeoff` from `openings: list` to `opening_ids: list`, and in `RoomTakeoff.to_dict` replace `"openings": list(self.openings),` with `"opening_ids": list(self.opening_ids),`.

- [ ] **Step 10: Update the existing tests that read `room.openings`**

In `tests/test_takeoff_quantities.py`, these existing assertions read the removed per-room list. Rewrite each to read the page-level records:

- line ~69-71 (`len(r.openings) == 1`, `r.openings[0]["width_m"]`, `["area_m2"]`) →
  ```python
            self.assertEqual(len(r.opening_ids), 1)
            op = next(o for o in page.openings if o.opening_id == r.opening_ids[0])
            self.assertAlmostEqual(op.width_m, 0.9, places=2)
            self.assertAlmostEqual(op.area_m2, 0.9 * 2.1, places=2)
  ```
- line ~79 (`page.rooms[0].openings == []`) → `self.assertEqual(page.rooms[0].opening_ids, [])`
- line ~135 (`op = page.rooms[0].openings[0]`) → `op = page.openings[0]`, and change the dict subscripts on the following lines (`op["width_m"]` etc.) to attributes (`op.width_m`).
- line ~146 (`page.rooms[0].openings == []`) → `self.assertEqual(page.rooms[0].opening_ids, [])`
- line ~172 (`[r.room_id for r in page.rooms if r.openings]`) → `... if r.opening_ids]`
- line ~151-156: leave the `to_dict` shape assertion failing for now — Task 4 replaces it. Mark it skipped so the rest of the suite runs:
  ```python
    @unittest.skip("to_dict is replaced by takeoff.document.to_document in Task 4")
    def test_to_dict_and_attributes(self):
  ```

- [ ] **Step 11: Run the tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_quantities tests.test_takeoff_openings -v`
Expected: PASS, with one skip.

- [ ] **Step 12: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS with one skip, no failures.

- [ ] **Step 13: Commit**

```bash
git add takeoff/quantities.py tests/test_takeoff_quantities.py
git commit -m "feat(takeoff): openings become page-level records measured once each"
```

---

### Task 3: Rooms carry geometry, and unscaled rooms are kept

**Files:**
- Modify: `takeoff/quantities.py` (`RoomTakeoff` fields; the unscaled branch; `totals`; `attributes_by_room`)
- Test: `tests/test_takeoff_quantities.py`

**Interfaces:**
- Consumes: `OpeningTakeoff`, `RoomTakeoff.opening_ids` from Task 2
- Produces: `RoomTakeoff` with fields
  `room_id, label, confidence, bbox, polygon, opening_ids, scale, mm_per_px, floor_m2, ceiling_m2, perimeter_m, height_m, height_source, wall_gross_m2, wall_net_m2, assumptions`
  where `scale` is `Optional[RoomScale]` and every quantity is `Optional[float]`, all `None` for an unscaled room.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_takeoff_quantities.py`, inside `class TestComputeTakeoff`:

```python
    def test_a_room_carries_its_geometry_and_confidence(self):
        w = 3 * PX_PER_M_50
        page = self._run([_room("room_0000", 100, 100, 100 + w, 100 + w, "BED 1")])
        r = page.rooms[0]
        self.assertEqual(r.confidence, 0.9)
        self.assertEqual(tuple(r.bbox), (100, 100, 100 + w, 100 + w))
        self.assertEqual(r.polygon[0], [100, 100])
        self.assertGreaterEqual(len(r.polygon), 4)

    def test_an_unscaled_room_is_kept_with_geometry_and_no_quantities(self):
        # The file's established idiom for "no scale resolves" — see
        # test_no_scale_room_is_listed_not_zeroed. Do NOT pass det=None.
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 100, 100, 400, 400)],
                         page_scales=PageScales(), det=det, regions=())
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        r = page.rooms[0]
        self.assertIsNone(r.scale)
        self.assertIsNone(r.floor_m2)
        self.assertIsNone(r.wall_net_m2)
        self.assertIsNone(r.mm_per_px)
        self.assertEqual(tuple(r.bbox), (100, 100, 400, 400))   # geometry survives
        self.assertGreaterEqual(len(r.polygon), 4)

    def test_totals_count_only_measured_rooms(self):
        w = 3 * PX_PER_M_50
        scaled = _room("room_a", 100, 100, 100 + w, 100 + w)
        page = self._run([scaled])
        t = page.totals()
        self.assertEqual(t["rooms_measured"], 1)
        self.assertEqual(t["rooms_unscaled"], 0)
        self.assertGreater(t["floor_m2"], 0)

    def test_an_unscaled_room_gets_no_entity_attributes_block(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 100, 100, 400, 400)],
                         page_scales=PageScales(), det=det, regions=())
        self.assertEqual(page.attributes_by_room(), {})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_quantities -v`
Expected: FAIL with `AttributeError: 'RoomTakeoff' object has no attribute 'confidence'`

- [ ] **Step 3: Widen `RoomTakeoff`**

In `takeoff/quantities.py`, replace the `RoomTakeoff` dataclass and its `to_dict` with:

```python
@dataclass
class RoomTakeoff:
    room_id: str
    label: Optional[str]
    confidence: float
    bbox: tuple
    polygon: list
    opening_ids: list = field(default_factory=list)
    scale: Optional[RoomScale] = None            # None when unresolvable
    mm_per_px: Optional[float] = None
    floor_m2: Optional[float] = None
    ceiling_m2: Optional[float] = None
    perimeter_m: Optional[float] = None
    height_m: Optional[float] = None
    height_source: Optional[str] = None
    wall_gross_m2: Optional[float] = None
    wall_net_m2: Optional[float] = None
    assumptions: list = field(default_factory=list)

    @property
    def measured(self) -> bool:
        """True when a scale resolved and quantities exist."""
        return self.scale is not None
```

Delete `RoomTakeoff.to_dict` entirely — Task 4's `takeoff/document.py` replaces it.

- [ ] **Step 4: Keep unscaled rooms**

In `compute_takeoff`, the unscaled branch currently reads:

```python
        if rs.denominator is None:
            page.unscaled_rooms.append(e.entity_id)
            continue
```

Replace it with:

```python
        if rs.denominator is None:
            # Kept, with geometry: an unscaled room still has to appear on the
            # overlay, and it still takes part in opening assignment above.
            page.unscaled_rooms.append(e.entity_id)
            page.rooms.append(RoomTakeoff(
                room_id=e.entity_id, label=e.label, confidence=e.confidence,
                bbox=tuple(e.bbox), polygon=[list(p) for p in raw.exterior.coords],
            ))
            continue
```

- [ ] **Step 5: Fill the geometry on measured rooms**

First keep the RAW detected ring so the second loop does not have to re-parse
it. In `compute_takeoff`, beside `room_polys` and `room_meta`, add:

```python
    room_raw: dict[str, Polygon] = {}
```

and in the first room loop, right after `room_polys[e.entity_id] = poly`, add:

```python
        room_raw[e.entity_id] = raw
```

Then in the `RoomTakeoff(...)` construction inside the measured loop, add the four new arguments and keep the rest:

```python
        room = RoomTakeoff(
            room_id=rid, label=e.label, confidence=e.confidence,
            bbox=tuple(e.bbox),
            polygon=[list(p) for p in room_raw[rid].exterior.coords],
            opening_ids=opening_ids,
            scale=rs, mm_per_px=round(mm_per_px(D), 3),
            floor_m2=round(floor, 2), ceiling_m2=round(floor, 2),
            perimeter_m=round(perim, 2),
            height_m=heights.ceiling_m, height_source=heights.sources["ceiling"],
            wall_gross_m2=round(gross, 2),
            wall_net_m2=round(max(gross - deduct, 0.0), 2),
            assumptions=[FLAT_CEILING_ASSUMPTION, STANDOFF_ASSUMPTION, HOLES_FILLED_ASSUMPTION],
        )
```

Note the polygon is the RAW detected polygon (`_room_polygon(e)`), not the standoff-corrected `poly` — the overlay must match the drawing's linework, while the quantities use the corrected one. The `assumptions` list already records `standoff_corrected_2px`.

Rooms are now appended from two places, so `page.rooms` lists the unscaled ones
first and the measured ones after, rather than in entity order. That is
harmless — the document is consumed by id, not by position — but say so in
your report so a reviewer does not read it as a bug.

- [ ] **Step 6: Make `totals` and `attributes_by_room` skip unmeasured rooms**

Replace `TakeoffPage.totals` and `TakeoffPage.attributes_by_room` with:

```python
    def totals(self) -> dict:
        measured = [r for r in self.rooms if r.measured]
        return {
            "floor_m2": round(sum(r.floor_m2 for r in measured), 2),
            "ceiling_m2": round(sum(r.ceiling_m2 for r in measured), 2),
            "wall_net_m2": round(sum(r.wall_net_m2 for r in measured), 2),
            "rooms_measured": len(measured),
            "rooms_unscaled": len(self.unscaled_rooms),
        }

    def attributes_by_room(self) -> dict:
        """The per-room quantity block mirrored onto Entity.attributes["takeoff"].

        Unmeasured rooms are skipped: the key means "here are the quantities",
        and a room with no scale has none.
        """
        from takeoff.document import room_dict            # local: avoids a cycle
        out = {}
        for r in self.rooms:
            if not r.measured:
                continue
            d = room_dict(r)
            d.pop("room_id")
            d.pop("label")
            out[r.room_id] = d
        return out
```

`room_dict` arrives in Task 4. Until then this raises `ImportError` when called, which is why Step 7 runs only the tests that do not call it. Task 4 Step 6 re-runs the full suite.

- [ ] **Step 7: Run the geometry tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_quantities.TestComputeTakeoff -v`
Expected: PASS, except `test_an_unscaled_room_gets_no_entity_attributes_block`, which fails with `ModuleNotFoundError: No module named 'takeoff.document'`. That module is Task 4.

- [ ] **Step 8: Update the two existing tests that assert unscaled rooms are dropped**

Two tests in `tests/test_takeoff_quantities.py` assert the OLD behaviour —
that an unscaled room produces no room record at all. This task deliberately
changes that, so both must move with it. They are the reason the change is
worth reviewing, not collateral damage: read each before editing.

In `test_no_scale_room_is_listed_not_zeroed`, replace
`self.assertEqual(page.rooms, [])` with:

```python
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        self.assertIsNone(page.rooms[0].scale)
        self.assertIsNone(page.rooms[0].floor_m2)
```

In `test_opening_on_unscaled_room_is_not_unassigned`, replace
`self.assertEqual(page.rooms, [])` with:

```python
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        self.assertIsNone(page.rooms[0].floor_m2)
```

Both keep their existing `page.unscaled_rooms` and `totals()` assertions
unchanged — `rooms_unscaled` still counts them, and `rooms_measured` still
does not.

- [ ] **Step 9: Fix the canned `RoomTakeoff` in the pipeline test**

`tests/test_takeoff_pipeline.py` has a `_canned()` helper that builds a
`RoomTakeoff` with the OLD signature, so it now raises `TypeError`. Replace its
construction with:

```python
        page.rooms.append(RoomTakeoff(
            room_id="room_0000", label=None, confidence=0.9,
            bbox=(100.0, 100.0, 300.0, 250.0),
            polygon=[[100.0, 100.0], [300.0, 100.0], [300.0, 250.0],
                     [100.0, 250.0], [100.0, 100.0]],
            opening_ids=[],
            scale=RoomScale(50.0, "text", "r1", False),
            mm_per_px=8.467, floor_m2=floor, ceiling_m2=floor, perimeter_m=1.0,
            height_m=2.4, height_source="default", wall_gross_m2=2.4,
            wall_net_m2=2.4, assumptions=[]))
```

- [ ] **Step 10: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS except `test_an_unscaled_room_gets_no_entity_attributes_block`, which
still fails on the missing `takeoff.document` module from Task 4. No other failures.

- [ ] **Step 11: Commit**

```bash
git add takeoff/quantities.py tests/test_takeoff_quantities.py tests/test_takeoff_pipeline.py
git commit -m "feat(takeoff): rooms carry geometry; unscaled rooms are kept with no quantities"
```

---

### Task 4: `takeoff/document.py` — the serialiser

**Files:**
- Create: `takeoff/document.py`
- Modify: `takeoff/quantities.py` (`PageFrame`; `TakeoffPage.page_frame` / `.scale_block`; drop `TakeoffPage.to_dict`; `compute_takeoff` gains the frame parameters)
- Test: `tests/test_takeoff_document.py`, `tests/test_takeoff_quantities.py`

**Interfaces:**
- Consumes: `RoomTakeoff`, `OpeningTakeoff`, `TakeoffPage` from Tasks 2-3; `scale.resolver.scale_summary_dict` from Task 1
- Produces:
  - `takeoff.quantities.PageFrame(width_px, height_px, rotation, dpi=150)` with `.to_dict()`
  - `takeoff.document.room_dict(room: RoomTakeoff) -> dict`
  - `takeoff.document.opening_dict(op: OpeningTakeoff) -> dict`
  - `takeoff.document.to_document(page: TakeoffPage) -> dict`
  - `takeoff.document.SCHEMA_VERSION = 1`
  - `compute_takeoff(..., page_width_px=0.0, page_height_px=0.0, page_rotation=0)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_document.py`:

```python
"""The takeoff.json document (takeoff/document.py)."""
import unittest

from models import Entity, Candidate, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.document import SCHEMA_VERSION, to_document
from takeoff.heights import Heights
from takeoff.quantities import compute_takeoff

PX_PER_M_50 = 1000.0 / (25.4 / 150 * 50)
HEIGHTS = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
DET50 = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")
REGION = Region(region_id="r1", bbox=(0, 0, 4000, 4000), region_type="floor_plan")
SCALES = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0)})


def _room(rid, x0, y0, x1, y1, label=None):
    poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return Entity(entity_id=rid, entity_type="room", bbox=(x0, y0, x1, y1),
                  confidence=0.9, source="heuristic", label=label,
                  attributes={"polygon": poly})


def _door(did, bbox, evidence=None):
    return (Entity(entity_id=did, entity_type="door", bbox=bbox, confidence=0.8,
                   source="heuristic", attributes={}),
            Candidate(candidate_id=did, entity_type="door", bbox=bbox,
                      confidence=0.8, evidence=evidence or {}))


def _page(entities, candidates=()):
    return compute_takeoff(entities, list(candidates), SCALES, [REGION], DET50,
                           HEIGHTS, 1, "", 420.0, 297.0,
                           page_width_px=2480.3, page_height_px=1753.9, page_rotation=0)


class TestDocumentShape(unittest.TestCase):
    def test_top_level_keys(self):
        d = to_document(_page([_room("room_a", 100, 100, 500, 500)]))
        self.assertEqual(set(d), {
            "schema_version", "page_number", "page_frame", "scale", "heights",
            "rooms", "openings", "totals", "warnings"})
        self.assertEqual(d["schema_version"], SCHEMA_VERSION)

    def test_page_frame_records_the_pixel_space(self):
        f = to_document(_page([_room("room_a", 100, 100, 500, 500)]))["page_frame"]
        self.assertEqual(f["width_px"], 2480.3)
        self.assertEqual(f["height_px"], 1753.9)
        self.assertEqual(f["dpi"], 150)
        self.assertEqual(f["origin"], "top-left")
        self.assertEqual(f["y_axis"], "down")
        self.assertEqual(f["rotation"], 0)
        self.assertAlmostEqual(f["pdf_width_pt"], 2480.3 * 72 / 150, places=1)
        self.assertAlmostEqual(f["pdf_height_pt"], 1753.9 * 72 / 150, places=1)

    def test_a_room_carries_geometry_and_grouped_quantities(self):
        w = 3 * PX_PER_M_50
        r = to_document(_page([_room("room_a", 100, 100, 100 + w, 100 + w, "Kitchen")]))["rooms"][0]
        self.assertEqual(r["room_id"], "room_a")
        self.assertEqual(r["label"], "Kitchen")
        self.assertEqual(r["confidence"], 0.9)
        self.assertEqual(len(r["bbox"]), 4)
        self.assertGreaterEqual(len(r["polygon"]), 4)
        self.assertEqual(r["opening_ids"], [])
        self.assertIn("floor_m2", r["quantities"])
        self.assertIn("wall_net_m2", r["quantities"])
        self.assertNotIn("floor_m2", r)          # grouped, not flat

    def test_an_unscaled_room_serialises_null_scale_and_null_quantities(self):
        unresolved = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = compute_takeoff([_room("room_a", 100, 100, 500, 500)], [], PageScales(),
                               [], unresolved, HEIGHTS, 1, "", 420.0, 297.0,
                               page_width_px=100.0, page_height_px=100.0)
        r = to_document(page)["rooms"][0]
        self.assertIsNone(r["scale"])
        self.assertIsNone(r["quantities"])
        self.assertGreaterEqual(len(r["polygon"]), 4)

    def test_the_scale_block_carries_page_region_and_evidence(self):
        s = to_document(_page([_room("room_a", 100, 100, 500, 500)]))["scale"]
        self.assertEqual(set(s), {"page", "by_region", "detection", "evidence"})
        self.assertEqual(s["by_region"]["r1"]["denominator"], 50.0)
        self.assertEqual(set(s["evidence"]), {"dimensions", "verdicts"})


class TestReferentialIntegrity(unittest.TestCase):
    def _doc(self):
        w = 3 * PX_PER_M_50
        left = _room("room_a", 100, 100, 100 + w, 100 + w)
        right = _room("room_b", 100 + w + 8, 100, 100 + 2 * w + 8, 100 + w)
        door, cand = _door("door_0000", (100 + w + 1, 300, 100 + w + 7, 300 + 106),
                           {"panel_length_px": 106.0})
        return to_document(_page([left, right, door], [cand]))

    def test_every_opening_id_on_a_room_resolves_to_an_opening(self):
        d = self._doc()
        by_id = {o["opening_id"] for o in d["openings"]}
        for room in d["rooms"]:
            for oid in room["opening_ids"]:
                self.assertIn(oid, by_id)

    def test_every_room_id_on_an_opening_resolves_and_points_back(self):
        d = self._doc()
        rooms = {r["room_id"]: r for r in d["rooms"]}
        for op in d["openings"]:
            for rid in op["room_ids"]:
                self.assertIn(rid, rooms)
                self.assertIn(op["opening_id"], rooms[rid]["opening_ids"])

    def test_a_shared_opening_appears_exactly_once(self):
        d = self._doc()
        ids = [o["opening_id"] for o in d["openings"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_document -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'takeoff.document'`

- [ ] **Step 3: Add `PageFrame` and the two new `TakeoffPage` fields**

In `takeoff/quantities.py`, add after the assumption constants:

```python
# 150 DPI is where extraction/extractor.py normalises every coordinate; the
# PDF's own user space is 72 dpi. Kept here rather than imported from
# extraction/ so takeoff/ stays free of that dependency — extractor.SCALE is
# its reciprocal.
TAKEOFF_DPI = 150
PT_PER_PX = 72.0 / TAKEOFF_DPI


@dataclass
class PageFrame:
    """The space every coordinate in this document lives in.

    extractor.page_transform has ALREADY applied the page's /Rotate, so these
    coordinates match the rendered page. `rotation` is provenance only — a
    consumer must not re-apply it.
    """
    width_px: float
    height_px: float
    rotation: int = 0
    dpi: int = TAKEOFF_DPI

    def to_dict(self) -> dict:
        return {
            "width_px": round(self.width_px, 1),
            "height_px": round(self.height_px, 1),
            "dpi": self.dpi,
            "origin": "top-left",
            "y_axis": "down",
            "pdf_width_pt": round(self.width_px * PT_PER_PX, 1),
            "pdf_height_pt": round(self.height_px * PT_PER_PX, 1),
            "rotation": self.rotation,
        }
```

Add to `TakeoffPage`, beside `openings`:

```python
    page_frame: Optional[PageFrame] = None
    scale_block: dict = field(default_factory=dict)
```

Delete `TakeoffPage.to_dict` entirely.

- [ ] **Step 4: Populate them in `compute_takeoff`**

Change the signature to add three keyword parameters at the end:

```python
def compute_takeoff(entities, candidates, page_scales, regions, det_scale, heights: Heights,
                    page_number: int, page_text: str, page_w_mm: float, page_h_mm: float,
                    paths=(), text_spans=(),
                    page_width_px: float = 0.0, page_height_px: float = 0.0,
                    page_rotation: int = 0) -> TakeoffPage:
```

Add the import at the top of `takeoff/quantities.py`:

```python
from scale.resolver import scale_summary_dict
```

and immediately after `page = TakeoffPage(page_number=page_number, heights=heights)` add:

```python
    page.page_frame = PageFrame(page_width_px, page_height_px, page_rotation)
    page.scale_block = scale_summary_dict(page_scales, det_scale)
```

- [ ] **Step 5: Write `takeoff/document.py`**

```python
"""takeoff.json — the document the web app's overlay and assembly table are
both built from.

Rooms and openings are sibling arrays cross-referenced by id: one physical
opening is one record carrying every room it serves, rather than a copy under
each. Geometry is 150-DPI pixels, the same space as final_entities.json and
render.png, with page_frame recording that space explicitly.

Serialisation only — takeoff/quantities.py does the maths.
"""
from __future__ import annotations

from takeoff.quantities import OpeningTakeoff, RoomTakeoff, TakeoffPage

# Bumped only on a breaking change to the shape below.
SCHEMA_VERSION = 1


def room_dict(room: RoomTakeoff) -> dict:
    """One room: geometry, its opening ids, and its quantities.

    `quantities` is None rather than a dict of nulls when no scale resolved —
    the absence of numbers is the fact, and a caller testing `if
    room["quantities"]` gets the right answer.
    """
    quantities = None
    if room.measured:
        quantities = {
            "floor_m2": room.floor_m2,
            "ceiling_m2": room.ceiling_m2,
            "perimeter_m": room.perimeter_m,
            "height_m": room.height_m,
            "height_source": room.height_source,
            "wall_gross_m2": room.wall_gross_m2,
            "wall_net_m2": room.wall_net_m2,
        }
    return {
        "room_id": room.room_id,
        "label": room.label,
        "confidence": room.confidence,
        "bbox": list(room.bbox),
        "polygon": [list(p) for p in room.polygon],
        "opening_ids": list(room.opening_ids),
        "scale": room.scale.to_dict() if room.scale is not None else None,
        "mm_per_px": room.mm_per_px,
        "quantities": quantities,
        "assumptions": list(room.assumptions),
    }


def opening_dict(op: OpeningTakeoff) -> dict:
    """One door or window. `room_ids` is empty when it reached no room;
    `dropped_room_ids` records rooms the two-room cap discarded."""
    d = {
        "opening_id": op.opening_id,
        "type": op.type,
        "assembly_type": op.assembly_type,
        "tag": op.tag,
        "confidence": op.confidence,
        "bbox": list(op.bbox),
        "room_ids": list(op.room_ids),
        "dropped_room_ids": list(op.dropped_room_ids),
        "width_px": op.width_px,
        "width_source": op.width_source,
        "width_m": op.width_m,
        "height_m": op.height_m,
        "area_m2": op.area_m2,
    }
    if op.clamped:
        d["clamped"] = True
    return d


def to_document(page: TakeoffPage) -> dict:
    """The whole page as one document."""
    scale = dict(page.scale_block)
    scale["page"] = scale.pop("page_scale", None)
    scale["evidence"] = {
        "dimensions": [m.to_dict() for m in page.dimension_matches],
        "verdicts": {f"{D:g}": v.to_dict() for D, v in page.verdicts.items()},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "page_number": page.page_number,
        "page_frame": page.page_frame.to_dict() if page.page_frame else None,
        "scale": scale,
        "heights": page.heights.to_dict(),
        "rooms": [room_dict(r) for r in page.rooms],
        "openings": [opening_dict(o) for o in page.openings],
        "totals": page.totals(),
        "warnings": [dict(w) for w in page.warnings],
    }
```

- [ ] **Step 6: Run the tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_document tests.test_takeoff_quantities -v`
Expected: PASS. `test_an_unscaled_room_gets_no_entity_attributes_block` from Task 3 now passes too, since `room_dict` exists.

- [ ] **Step 7: Delete the skipped legacy test**

In `tests/test_takeoff_quantities.py`, remove the whole `test_to_dict_and_attributes` method you skipped in Task 2 Step 10 — `tests/test_takeoff_document.py` now covers the document shape, and `test_an_unscaled_room_gets_no_entity_attributes_block` covers the attributes mirror.

- [ ] **Step 8: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, zero skips, zero failures.

- [ ] **Step 9: Commit**

```bash
git add takeoff/document.py takeoff/quantities.py tests/test_takeoff_document.py tests/test_takeoff_quantities.py
git commit -m "feat(takeoff): takeoff.json becomes one overlay document with a page frame"
```

---

### Task 5: Pipeline wiring

**Files:**
- Modify: `pipeline.py` — the `compute_takeoff` call and the `takeoff.json` write (both in `run_extract`, around lines 772-790)
- Test: `tests/test_takeoff_pipeline.py`

**Interfaces:**
- Consumes: `takeoff.document.to_document`, `compute_takeoff(..., page_width_px, page_height_px, page_rotation)`
- Produces: `takeoff.json` on disk in the new shape

- [ ] **Step 1: Write the failing test**

`tests/test_takeoff_pipeline.py::TestRunExtractWiring` **mocks** `compute_takeoff`
— deliberately, so its assertions are about wiring and never about detection.
That means this task's test must assert on what the pipeline PASSES and WRITES,
not on numbers a mock cannot produce.

Two edits to that class.

First, `fake_compute` must accept the three new keyword arguments or the call
raises `TypeError`. Change its signature and body to:

```python
            def fake_compute(entities, candidates, page_scales, regions, det_scale,
                             heights, page_number, page_text, w_mm, h_mm,
                             paths=(), text_spans=(),
                             page_width_px=0.0, page_height_px=0.0, page_rotation=0):
                calls.append((page_number, heights, round(w_mm), round(h_mm),
                              round(page_width_px), round(page_height_px), page_rotation))
                self.assertIsInstance(list(paths), list)     # primitives reach the takeoff
                return self._canned(page_number, floor=10.0 * page_number)
```

Second, `_canned` must set a page frame, since `to_document` reads it. Add this
line to `_canned` just before `return page`:

```python
        page.page_frame = PageFrame(1239.6, 1754.2, 0)
```

and add `PageFrame` to that file's existing import from `takeoff.quantities`.

Now append these two tests to `TestRunExtractWiring`:

```python
    def test_the_page_frame_is_passed_from_the_real_page(self):
        """The synthetic PDF is 595x842 pt; at 150 DPI that is 1239.6x1754.2 px.
        A zero here means run_extract fell back to compute_takeoff's defaults."""
        import tempfile
        from pathlib import Path
        import pipeline

        with tempfile.TemporaryDirectory() as tmp:
            pdf = str(Path(tmp) / "two.pdf")
            self._pdf(pdf)
            calls = []

            def fake_compute(entities, candidates, page_scales, regions, det_scale,
                             heights, page_number, page_text, w_mm, h_mm,
                             paths=(), text_spans=(),
                             page_width_px=0.0, page_height_px=0.0, page_rotation=0):
                calls.append((round(page_width_px), round(page_height_px), page_rotation))
                return self._canned(page_number, floor=1.0)

            with mock.patch.object(pipeline, "compute_takeoff", side_effect=fake_compute):
                pipeline.run_extract(pdf, [0], out_parent=tmp, skip_gemini=True,
                                     allow_scale_prompt=False, ceiling_height=2.7)

        self.assertEqual(calls[0], (1240, 1754, 0))

    def test_takeoff_json_is_written_in_the_document_shape(self):
        import json
        import tempfile
        from pathlib import Path
        import pipeline

        with tempfile.TemporaryDirectory() as tmp:
            pdf = str(Path(tmp) / "two.pdf")
            self._pdf(pdf)

            def fake_compute(*args, **kwargs):
                return self._canned(kwargs.get("page_number") or args[6], floor=7.5)

            with mock.patch.object(pipeline, "compute_takeoff", side_effect=fake_compute):
                out_dir = pipeline.run_extract(pdf, [0], out_parent=tmp, skip_gemini=True,
                                               allow_scale_prompt=False, ceiling_height=2.7)

            d = json.loads((Path(out_dir) / "pages" / "page_01" / "takeoff.json").read_text())

        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(set(d), {
            "schema_version", "page_number", "page_frame", "scale", "heights",
            "rooms", "openings", "totals", "warnings"})
        self.assertEqual(d["page_frame"]["dpi"], 150)
        self.assertEqual(d["page_frame"]["width_px"], 1239.6)
        self.assertEqual(d["rooms"][0]["quantities"]["floor_m2"], 7.5)
        self.assertEqual(d["rooms"][0]["opening_ids"], [])
        self.assertEqual(d["openings"], [])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_pipeline -v`
Expected: FAIL. `test_the_page_frame_is_passed_from_the_real_page` gets `(0, 0, 0)`
because `run_extract` does not pass the frame yet, and
`test_takeoff_json_is_written_in_the_document_shape` sees the old keys because
`run_extract` still calls `takeoff_page.to_dict()`, which Task 4 deleted —
so it may instead fail with `AttributeError: 'TakeoffPage' object has no
attribute 'to_dict'`. Either failure is the expected RED.

- [ ] **Step 3: Confirm the existing wiring test still describes reality**

The pre-existing `test_takeoff_is_wired_per_page` asserts on `calls[0][2]` and
`calls[0][3]` (the page size in mm). Your widened `fake_compute` appends three
more items to each tuple, which does not disturb those indices. Re-read that
test and confirm its assertions still hold before moving on.

- [ ] **Step 4: Wire it up**

In `pipeline.py`, add the import beside the existing takeoff import (line 36):

```python
from takeoff.document import to_document
```

Change the `compute_takeoff` call (currently at line 772) to pass the page frame. It currently ends:

```python
                paths=page_data.paths, text_spans=page_data.text_spans,
            )
```

Make it:

```python
                paths=page_data.paths, text_spans=page_data.text_spans,
                page_width_px=page_data.width_px,
                page_height_px=page_data.height_px,
                page_rotation=doc[idx].rotation,
            )
```

Change the write (currently `write_json(str(Path(page_dir) / "takeoff.json"), takeoff_page.to_dict())`) to:

```python
            write_json(str(Path(page_dir) / "takeoff.json"), to_document(takeoff_page))
```

`attach_takeoff(entities, takeoff_page)` and the `takeoff_totals` accumulation above and below it are unchanged.

- [ ] **Step 5: Run the tests**

Run: `source .venv/bin/activate && python -m unittest tests.test_takeoff_pipeline -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, zero failures.

- [ ] **Step 7: Commit**

```bash
git add pipeline.py tests/test_takeoff_pipeline.py
git commit -m "feat(takeoff): write the overlay document, with the page frame from the real page"
```

---

### Task 6: Live verification and documentation

**Files:**
- Modify: `CLAUDE.md` — the "Output layout" tree and the stage-6 takeoff paragraph
- Modify: `docs/superpowers/specs/2026-08-20-takeoff-overlay-document-design.md` only if the live run contradicts it

**Interfaces:**
- Consumes: everything from Tasks 1-5
- Produces: no code interface; a verified run and updated docs

- [ ] **Step 1: Run the reference sheet**

```bash
source .venv/bin/activate
python app.py extract fixtures/sheets/s02-working-drawing-wd03.pdf --ceiling-height 2.4
```

The room-label cache from the previous phase is already seeded, so this needs no new Gemini call for labels; region classification is cached too. If it does call, that is fine.

- [ ] **Step 2: Check the document by its own invariants**

```bash
python - <<'PY'
import json, glob
d = json.loads(open(sorted(glob.glob('outputs/*/pages/page_01/takeoff.json'))[-1]).read())
print("keys:", sorted(d))
print("frame:", d["page_frame"])
rooms = {r["room_id"]: r for r in d["rooms"]}
ops = {o["opening_id"]: o for o in d["openings"]}
print(f"{len(rooms)} rooms, {len(ops)} openings")
for r in d["rooms"]:
    q = r["quantities"]
    print(f'  {r["room_id"]:11} {r["label"] or "-":22} '
          f'{(q or {}).get("floor_m2", "unscaled")!s:>9}  '
          f'poly={len(r["polygon"])}pts  openings={r["opening_ids"]}')
bad = [(rid, oid) for rid, r in rooms.items() for oid in r["opening_ids"] if oid not in ops]
bad += [(oid, rid) for oid, o in ops.items() for rid in o["room_ids"]
        if rid not in rooms or oid not in rooms[rid]["opening_ids"]]
print("BROKEN REFS:", bad or "none")
print("unassigned:", [o for o, v in ops.items() if not v["room_ids"]])
PY
```

Expected: 9 of 12 rooms named (Phase 1's result), every room carrying a polygon of 4+ points, `BROKEN REFS: none`, and the unassigned list matching the five ids the old file reported (`window_0000`, `window_0013`, `door_0006`, `door_0017`, `door_0016`).

If `BROKEN REFS` is non-empty, stop and report it — that is the one invariant the frontend cannot work around.

- [ ] **Step 3: Confirm the frame matches the render**

```bash
python - <<'PY'
import json, glob
from PIL import Image
p = sorted(glob.glob('outputs/*/pages/page_01'))[-1]
d = json.loads(open(p + '/takeoff.json').read())
w, h = Image.open(p + '/render.png').size
print("frame:", d["page_frame"]["width_px"], d["page_frame"]["height_px"])
print("render:", w, h)
PY
```

Expected: the two agree to within a pixel. They must — the render and the coordinates come from the same 150-DPI normalisation. If they disagree, the page frame is wrong and the overlay would be offset; report it rather than adjusting the numbers.

- [ ] **Step 4: Run the regression sweep**

```bash
python tools/regress.py
```

Expected: exit 1 with the same 103 pre-existing RETURNED FALSE POSITIVES and **zero lost `confirmed` entities**. This plan does not touch `detection/`, so any lost confirmed entity is a real regression from the pipeline wiring — report it.

- [ ] **Step 5: Update `CLAUDE.md`**

In the "Output layout" tree, replace the `takeoff.json` comment lines:

```
    ├── takeoff.json          # THE overlay document: page_frame (150-DPI px space),
    │                         # scale + evidence, heights, rooms[] (polygon, bbox,
    │                         # label, opening_ids, quantities), openings[] (bbox,
    │                         # type, tag, room_ids, widths), totals, warnings.
    │                         # schema_version 1. Rooms and openings are sibling
    │                         # arrays cross-referenced by id — one physical opening
    │                         # is one record, whichever rooms it serves.
```

In the stage-6 takeoff paragraph, after the sentence describing `compute_takeoff`, add:

> `takeoff/document.py` then serialises the page into `takeoff.json`. Rooms and
> openings are sibling arrays cross-referenced by id rather than openings nested
> per room, so a door serving two rooms is one record carrying both `room_ids`.
> Geometry is 150-DPI pixels — the same space as `final_entities.json` and
> `render.png` — with a `page_frame` block recording it; `extractor.page_transform`
> has already applied the page's `/Rotate`, so `rotation` is provenance and a
> consumer must not re-apply it. A room whose scale did not resolve is kept, with
> its polygon, `scale: null` and `quantities: null`.

- [ ] **Step 6: Refresh the knowledge graph and commit**

```bash
graphify update .
git status --short
git add CLAUDE.md graphify-out
git commit -m "docs: takeoff.json is the overlay document"
```

- [ ] **Step 7: Report the outcome**

Paste the Step 2 output, the Step 3 frame-vs-render comparison, and `tools/regress.py`'s exit code. Do not claim success without the room table from Step 2 and `BROKEN REFS: none`.
