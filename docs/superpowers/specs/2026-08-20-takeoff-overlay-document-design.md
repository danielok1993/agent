# takeoff.json as the overlay document — design

**Status:** approved 2026-08-20
**Phase:** 2 of 2. Phase 1 ([room labels](2026-08-20-room-labels-design.md))
shipped to main as 81d79ac.

## Problem

The web app previews a takeoff by rendering the PDF itself and drawing the
detected rooms, doors and windows over it, with per-category toggles and an
editable assembly table. `takeoff.json` cannot drive that: it carries
quantities keyed by id and **no geometry at all** — no polygons, no bboxes,
no page dimensions.

Today the frontend would have to join three files: `takeoff.json` for the
numbers, `final_entities.json` for `bbox` and `attributes.polygon`, and
`summary.json` for `width_px`/`height_px`. Nothing records the coordinate
space those pixels live in.

Phase 2 makes `takeoff.json` the single document the overlay and the table
are both built from. No new output artifact is introduced — the existing
file is restructured.

## Decisions

Three were taken by the user during design:

1. **Openings are a page-level array referenced by id**, not nested and
   duplicated under each room. A door serving two rooms appears once with
   `room_ids: ["room_0005", "room_0000"]`; each room carries
   `opening_ids`. One physical opening is one row in the assembly table.
2. **Geometry is emitted in 150-DPI pixels with an explicit page frame** —
   the same space as `final_entities.json`, `render.png` and `overlay.png`,
   so a coordinate can be eyeballed against the existing overlay. The
   frontend computes one scale factor against its canvas.
3. **Scope is rooms, doors and windows only**, plus each opening's tag
   (`GD9`) which detection already attaches to the entity. No schedules, no
   `label` entities as their own array, no rejected candidates. Adding a
   category later is an additive schema change, not a breaking one.

## The document

```json
{
  "schema_version": 1,
  "page_number": 1,
  "page_frame": {
    "width_px": 2480.3, "height_px": 1753.9, "dpi": 150,
    "origin": "top-left", "y_axis": "down",
    "pdf_width_pt": 1190.6, "pdf_height_pt": 841.9, "rotation": 0
  },
  "scale": {
    "page": {"denominator": 50.0, "source": "text", "verified": true},
    "by_region": {"region_0000": {"denominator": 50.0, "source": "text"}},
    "evidence": {
      "dimensions": [{"path_index": 41, "label": "3600", "denominator": 92.2}],
      "verdicts": {"50": {"verdict": "implausible", "method": "dimensions"}}
    }
  },
  "heights": {
    "ceiling_m": 2.4, "door_m": 2.1, "window_m": 1.2,
    "source": {"ceiling": "flag", "door": "default", "window": "default"}
  },
  "rooms": [{
    "room_id": "room_0000",
    "label": "Kitchen",
    "confidence": 0.85,
    "bbox": [1712.3, 99.1, 2329.1, 536.6],
    "polygon": [[1733.1, 110.1], [1730.4, 107.6]],
    "opening_ids": ["door_0018"],
    "scale": {"denominator": 50.0, "source": "text",
              "region_id": "region_0000", "verified": true},
    "mm_per_px": 8.467,
    "quantities": {
      "floor_m2": 18.5, "ceiling_m2": 18.5, "perimeter_m": 19.28,
      "height_m": 2.4, "height_source": "flag",
      "wall_gross_m2": 46.27, "wall_net_m2": 44.95
    },
    "assumptions": ["flat_ceiling", "standoff_corrected_2px", "holes_filled"]
  }],
  "openings": [{
    "opening_id": "door_0018",
    "type": "door",
    "assembly_type": "sliding",
    "tag": "GD9",
    "confidence": 0.85,
    "bbox": [797.7, 787.7, 803.7, 882.2],
    "room_ids": ["room_0005", "room_0000"],
    "dropped_room_ids": [],
    "width_m": 0.63, "height_m": 2.1, "area_m2": 1.32,
    "width_source": "panel_length_px"
  }],
  "totals": {
    "floor_m2": 107.31, "ceiling_m2": 107.31, "wall_net_m2": 338.61,
    "rooms_measured": 12, "rooms_unscaled": 0
  },
  "warnings": [
    {"warning_code": "SCALE_UNVERIFIED", "severity": "warning",
     "message": "…", "page_number": 1}
  ]
}
```

### Field provenance

Every value already exists somewhere; nothing new is computed.

| Field | Source |
| --- | --- |
| `schema_version` | literal `1`; bumped only on a breaking change |
| `scale.page` / `scale.by_region` | `PageScales.page_scale` / `.by_region`, already passed to `compute_takeoff` |
| `scale.evidence.dimensions` | `TakeoffPage.dimension_matches` (today's `scale_evidence.dimensions`) |
| `scale.evidence.verdicts` | `TakeoffPage.verdicts` — `takeoff/plausibility.py`'s verdict per denominator |
| `page_frame.width_px` / `height_px` | `PageData.width_px` / `height_px` |
| `page_frame.pdf_width_pt` / `height_pt` | `width_px / SCALE`, `SCALE = 150/72` |
| `page_frame.rotation` | `doc[idx].rotation`, in scope at the call site |
| `rooms[].bbox`, `.confidence` | room `Entity.bbox`, `.confidence` |
| `rooms[].polygon` | room `Entity.attributes["polygon"]` |
| `rooms[].label` | room `Entity.label` (Phase 1) |
| `rooms[].opening_ids` | `assign_openings`'s `assigned[room_id]` |
| `rooms[].quantities.*` | today's flat `RoomTakeoff` fields, regrouped |
| `openings[].bbox`, `.confidence`, `.tag` | door/window `Entity.bbox`, `.confidence`, `.label` |
| `openings[].assembly_type` | `Entity.attributes.get("assembly_type")` |
| `openings[].room_ids` | inverted `assigned` map |
| `openings[].dropped_room_ids` | `assign_openings`'s `over_assigned` |
| `openings[].width_m` … `width_source` | today's per-room opening dicts, deduplicated |
| `warnings` | `TakeoffPage.warnings`, today only forwarded to the page list |

### What disappears, and why

- `unassigned_openings` — an opening with `room_ids: []` is unassigned. The
  opening now appears in the array with its geometry rather than as a bare id.
- `unscaled_rooms` — a room with `scale: null` is unscaled.
- `over_assigned_openings` — **not** derivable from `room_ids`, since it
  records the rooms the two-room cap *dropped*. It moves onto the opening as
  `dropped_room_ids`.
- The per-room `openings` array — replaced by `opening_ids`.

`totals` keeps `rooms_unscaled`, computed from the rooms whose scale is null.

## Coordinate contract

150-DPI pixels, top-left origin, y down — the space
`extraction/extractor.py` normalises every primitive into, and the space
`render.png` is rasterised in. `page_frame.rotation` is recorded for
provenance only: `extractor.page_transform` has **already** applied the
page's `/Rotate`, so the coordinates match the rendered, rotated page and
need no further transform.

The frontend's whole mapping is one factor:

```js
const s = canvas.width / doc.page_frame.width_px;
polygon.map(([x, y]) => [x * s, y * s]);
```

`rooms[].polygon` is the raw detected polygon — the drawing's own linework,
so the overlay traces what the user sees on the sheet. `quantities.floor_m2`
(and the other area/perimeter fields) are computed from that polygon buffered
out by `ROOM_WALL_DILATE_PX` to undo the barrier standoff (`assumptions`
records this as `standoff_corrected_2px`). A consumer must not expect an area
recomputed from `polygon` to equal `floor_m2`.

## Editing

The document carries every input needed to recompute a room after the user
edits it. Adding a door by hand means appending an opening with
`room_ids: [roomId]` and recomputing
`wall_net_m2 = wall_gross_m2 − Σ area_m2` over that room's openings.
`wall_gross_m2`, `height_m` and each opening's `area_m2` are all present.
Recomputation is the web app's job; this repo does not consume edits.

## Code structure

- `takeoff/quantities.py` keeps the maths. It gains an `OpeningTakeoff`
  dataclass (page-level, one per physical opening) and geometry fields on
  `RoomTakeoff`.
- **New module `takeoff/document.py`** owns serialisation: dataclasses plus
  the page frame → the dict above. `quantities.py` is 258 lines and
  computing; assembling a document is a separate responsibility, and keeping
  both in one file would push it past 360 lines.
- `pipeline.py` passes `width_px`, `height_px` and `doc[idx].rotation` into
  `compute_takeoff`.
- `detection/` is untouched.

## Breaking change

`takeoff.json`'s shape changes with no compatibility shim: no external
consumer exists yet, and `schema_version: 1` marks the contract from here.
Two internal readers move with it:

- `TakeoffPage.attributes_by_room()`, which mirrors the room block onto
  `Entity.attributes["takeoff"]` in `final_entities.json`
- `summary.json`'s per-page `takeoff` totals

`final_entities.json` otherwise keeps its current shape. It remains the
debugging view — it carries the rejected candidates and the non-overlay
entity types this document deliberately omits.

## Testing

Existing `tests/test_takeoff_*.py` assertions on `to_dict` shape are
updated. New tests pin the invariants the frontend relies on:

- every `opening_ids` entry resolves to an opening, and that opening's
  `room_ids` contains the room — referential integrity in both directions
- a door assigned to two rooms appears exactly **once** in `openings`
- an unassigned opening is present with `room_ids: []`
- a three-room overreach populates `dropped_room_ids`
- `page_frame` matches the `PageData` it was built from, and
  `pdf_width_pt × SCALE == width_px`
- a room with no resolvable scale serialises `scale: null` and no quantities

## Out of scope

- Any second output file
- Schedule tables, standalone label entities, rejected candidates
- Consuming user edits back into the pipeline
- Multi-page aggregation — this document stays per-page, as today
