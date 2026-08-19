# Room Quantity Takeoff — Design

**Date:** 2026-08-18
**Status:** Implemented (branch feat/room-takeoff)
**Predecessors:** `2026-08-11-floor-plan-scale-extraction-design.md` (scale
resolution, `scale/`), room detection (`detection/rooms.py`).

## Problem

Rooms come out of `detect_rooms` as closed polygons with `area_px2` /
`perimeter_px` in 150-DPI pixel space, and `scale/` resolves a drawing scale
per floor-plan region. Nothing yet turns the two into real-world quantities.
The purpose is a **decorating / finishes takeoff**: per room, floor area,
ceiling area, and net wall area (perimeter × height, minus door and window
openings). Not RICS GIA/NIA — that needs a different polygon and is out of
scope.

Heights are not on the plans: a scan of the 20 corpus sheets found **zero**
numeric ceiling heights (s02 "lowered ceiling", s06 "2- CEILINGS:" heading,
nothing with a number), so heights come from the user with defaults.

## Unit model

Everything downstream of `extraction/extractor.py` is 150-DPI pixels, so one
pixel is 25.4/150 = **0.16933 mm on paper**. A drawing at 1:D puts D real mm
in every paper mm, therefore

```
mm_per_px = 0.16933 × D
length_m  = px  × mm_per_px / 1000
area_m2   = px² × (mm_per_px / 1000)²
```

| Scale | mm/px | px per m | px² per m² |
|---|---|---|---|
| 1:50  | 8.467  | 118.1 | 13,948 |
| 1:100 | 16.933 | 59.1  | 3,487  |
| 1:200 | 33.867 | 29.5  | 872    |

D is `ScaleInfo.nominal` when present, else `denominator` — the same rule
`scale/factor.py::_effective_denominator` uses, so 1:50 sheets compute
exactly. Page rotation does not enter: `page_transform` scales uniformly.

### Which D applies to a room

Pages can carry different scales per region (s03, s17). Per room, in order:

1. the `floor_plan` region whose bbox contains the room polygon centroid,
   looked up in `page_scales.by_region` — if it has an effective D;
2. else, ONLY when the room lies in no `floor_plan` region (or in one the
   resolver recorded no verdict for), `det_scale.denominator`; a region the
   resolver marked `unresolved` leaves its rooms unscaled — on a mixed-scale
   page `det_scale` is the OTHER plan's scale, and borrowing it would be a
   guess dressed as a fallback;
3. else **no quantities for that room** and one `TAKEOFF_NO_SCALE` warning
   per page. Never a guessed denominator.

### Scale verification flag

The unit model trusts that the PDF is at its intended sheet size: an A1
drawing exported onto A3 paper carries a printed "1:50" that is really 1:100.
Corpus measurement (2026-08-18): 11/20 sheets carry `/VP` viewports (immune —
they measure the real page), 8/20 declare a sheet size in the title block
(all consistent with their mediabox), 5/20 carry dimension strings; 6 sheets
(s09 s10 s11 s16 s18 s19) have only a printed scale and nothing to test it
against.

This spec records the outcome only: every quantity block carries
`scale_verified: true|false`. Verified means the room's `ScaleInfo.source` is
`"viewport"` or `"user"`, or is `"text"` with a title-block sheet-size
declaration matching the mediabox within 5 % on both sides (ISO sizes:
A0 841×1189 … A4 210×297, either orientation). A DECLARATION, not any
`A0`–`A4` token on the page: the token counts only when written after an
`@` (`1:50@A3`, `As Shown @ A1`) or after a SHEET / SIZE / PAPER / FORMAT
keyword (up to a short separator). A bare token is usually part of a drawing
number — measured 2026-08-19, the page-wide scan matched s20's
`18-069-001(A1).A`; with the context rule s20 yields nothing and the six real
declarations (s02 s03 s04 s08 s14 s17) all still match.
Unverified rooms still get quantities plus one `SCALE_UNVERIFIED` (info)
warning per page. A declared size that *mismatches* the mediabox by ~2× is
recorded (`SCALE_PRINT_RESIZED`, warning) but **not** auto-corrected here —
correction and the dimension-string check are the next branch.

## Geometry

### Floor and ceiling

The room polygon is the free-space component after every barrier was dilated
by `ROOM_WALL_DILATE_PX` (2.0 px, `detection/rooms.py:51`), so it sits ~2 px
inside the true wall face — 17 mm per side at 1:50, ~1 % of a 3 m room. The
takeoff buffers the polygon out by `ROOM_WALL_DILATE_PX` (`join_style=mitre`,
so corners stay square) before measuring:

```
floor_m2     = area(buffered)         × (mm_per_px/1000)²
perimeter_m  = length(buffered.exterior) × mm_per_px/1000
ceiling_m2   = floor_m2               # flat-ceiling assumption, recorded
```

The polygon is the FILLED exterior ring: `detect_rooms` deliberately fills
interior holes (`detection/rooms.py:1214`, "interior holes (fixtures)
filled") and keeps only their count. Those holes are fixture islands
(kitchen units, sanitaryware rings) — floor for a finishes takeoff — so
nothing is subtracted, and every room records the assumption
`holes_filled`. A true structural island (a chimney breast standing free of
the walls) is therefore counted as floor; noted as a limitation.

### Openings and wall area

```
wall_gross_m2 = perimeter_m × H_ceiling
wall_net_m2   = wall_gross_m2 − Σ openings (width_m × H_type)
```

Every door and window **entity** (post-`finalize_candidates`, so rejected
candidates never deduct) is assigned to each room whose buffered polygon,
dilated by a further `ROOM_OPENING_SEAL_PX` (14 px total from the detected
polygon), intersects the opening's bbox. Assignment runs over every valid
room, scaled or not, so an opening on an unscaled room is never mis-reported
as free-space; deductions are computed for scaled rooms only.
An internal door therefore deducts from both rooms; an external door or a
window from one. An opening touching no room is listed under the page's
`unassigned_openings` and deducts nothing. Assignment is CAPPED at two rooms
— a door separates at most two spaces, yet the grown reach put three s01
doors in three rooms each (measured 2026-08-19) — so when three or more rooms
are hit, only the two whose un-grown polygon boundary lies nearest the bbox
centre keep it; the rest are recorded under the page's
`over_assigned_openings` (`{"id":…, "dropped_rooms":[…]}`) with one
`TAKEOFF_OPENING_MULTI_ROOM` (info) warning.

Opening width, in order of evidence:

- SINGLE swing door (`assembly_type` `"single"` / `"single_line_leaf"`, or
  any door carrying an `arc_bbox` with no merged/arcless type): the arc
  RADIUS — the longer side of `evidence["arc_bbox"]` — falling back to
  `leaf_line_length_px`. `opening_line` is NOT the opening for a single leaf:
  `detection/doors/assembly.py` sets it to the two swing-arc endpoints, which
  a quarter swing puts 90° apart, so the chord measures r·√2 (measured on
  s02: chord = 1.08 m against a 0.762 m leaf);
- MERGED pair (`assembly_type` `"double_swing"` — french/garden/double
  swings): `evidence["opening_line"]`, recomputed at merge time as the
  farthest-apart pair of both halves' arc endpoints, so it does span the
  opening;
- window: `evidence["opening_width_px"]`, except a DIAGONAL one
  (`orientation == "diagonal"`), which takes `glazing_len_px` — the
  axis-aligned opening width is only the angled run's projection;
- sliding / folding doors: `evidence["opening_span_px"]` (recorded by both
  `detection/doors/sliding.py` and `folding.py`; bbox is ~2× the opening —
  parked panel / stack), falling back to `panel_length_px` for the fill-less
  parked_leaf / open_v tiers that carry no span;
- else: the bbox side that lies along the room edge — of the four bbox
  edges, the one whose midpoint is nearest the room boundary.

The takeoff reads a `{candidate_id: evidence}` map built from the page's
candidates because `finalize_candidates` strips evidence from
`Entity.attributes`; entities keep the confidence floors, candidates keep the
geometry.

Heights per opening type: doors `H_door`, windows `H_window` (sill-to-head).
Openings taller than the ceiling are clamped to `H_ceiling` and flagged.

## Heights

Three CLI options on `extract` (and `batch_extract.py`'s prompt):
`--ceiling-height`, `--door-height`, `--window-height`, metres — each must be
a positive finite number; the CLI rejects anything else at parse time and
`resolve_heights` raises on a bad explicit value (never a silent default).

Precedence per value: **flag → prompt → default**. The prompt asks once per
run for the ceiling height only (doors/windows are rarely known better than
the defaults), and only when `--ceiling-height` is absent and
`scale.prompt.can_prompt()` is true — the same tty gate the scale prompt
uses, so `batch_extract.py` and `tools/regress.py` never block. Blank / EOF /
nonsense → default. Defaults: **2.4 m / 2.1 m / 1.2 m**.

Every room records `height_m` and `height_source: "flag"|"prompt"|"default"`.
The value `"drawing"` is reserved for a future text/section reader and is
never emitted by this branch. Heights are per run, not per room; per-room
overrides are a follow-up if the flat-ceiling assumption proves too coarse.

## Module layout

```
takeoff/
  __init__.py     # compute_takeoff re-export
  units.py        # MM_PER_PX_AT_1_1, mm_per_px(D), px→m helpers, effective D
  heights.py      # Heights dataclass, resolve_heights(flags, can_prompt, input_fn)
  openings.py     # opening width from evidence, room assignment
  quantities.py   # compute_takeoff(...) -> TakeoffPage
```

`compute_takeoff(entities, candidates, page_scales, regions, det_scale,
heights, page_text) -> TakeoffPage` is pure: no I/O, no globals, no prompting
(heights are resolved once in `run_extract` before the page loop). Detection
modules are untouched; the regression sweep is unaffected by construction.

`pipeline.run_extract` calls it directly after `finalize_candidates`, writes
`pages/page_NN/takeoff.json`, mirrors the per-room block onto the room
`Entity.attributes` (so `final_entities.json` is self-contained), and folds
`takeoff` totals into the page's `summary.json` entry. Its warnings join the
page warning list via the existing collection path.

## Output

`pages/page_NN/takeoff.json`:

```json
{
  "page_number": 1,
  "heights": {"ceiling_m": 2.4, "door_m": 2.1, "window_m": 1.2,
              "source": {"ceiling": "prompt", "door": "default", "window": "default"}},
  "rooms": [
    {
      "room_id": "room_0003", "label": "BEDROOM 2",
      "scale": {"denominator": 50.0, "source": "viewport", "region_id": "r02",
                "verified": true},
      "mm_per_px": 8.467,
      "floor_m2": 12.84, "ceiling_m2": 12.84, "perimeter_m": 14.52,
      "height_m": 2.4, "height_source": "prompt",
      "wall_gross_m2": 34.85,
      "openings": [
        {"id": "door_0007", "type": "door", "width_m": 0.84, "height_m": 2.1,
         "area_m2": 1.76, "width_source": "opening_line"},
        {"id": "window_0002", "type": "window", "width_m": 1.20, "height_m": 1.2,
         "area_m2": 1.44, "width_source": "opening_width_px"}
      ],
      "wall_net_m2": 31.65,
      "assumptions": ["flat_ceiling", "standoff_corrected_2px", "holes_filled"]
    }
  ],
  "unassigned_openings": ["door_0011"],
  "unscaled_rooms": [],
  "totals": {"floor_m2": 88.1, "ceiling_m2": 88.1, "wall_net_m2": 201.3,
             "rooms_measured": 9, "rooms_unscaled": 0}
}
```

Rounding: 2 dp on metres and m², 3 dp on `mm_per_px`. Rooms without a scale
appear in `unscaled_rooms` with no numbers, never with zeros.

## Warnings

| code | severity | when |
|---|---|---|
| `TAKEOFF_NO_SCALE` | warning | ≥1 room on the page has no effective D |
| `SCALE_UNVERIFIED` | info | ≥1 measured room's scale is text-only and unverifiable |
| `SCALE_PRINT_RESIZED` | warning | title-block sheet size mismatches the mediabox by a factor in [1.8, 2.2] or [0.45, 0.55] (half-/double-size print — linear factor 2, two ISO A-steps, A1↔A3) |
| `TAKEOFF_OPENING_TALLER_THAN_CEILING` | info | an opening height was clamped |
| `TAKEOFF_OPENING_MULTI_ROOM` | info | ≥1 opening reached 3+ rooms; the two nearest kept, the rest dropped |

Emitted from `takeoff.quantities` on `TakeoffPage.warnings` and folded into
the page list by `run_extract`, mirroring how `PageScales.warnings` travels.

## Testing

Fast tier (`tests/test_takeoff_*.py`, synthetic, no PDFs):

- `units`: 118.1 px at 1:50 → 1.00 m; 13,948 px² → 1.00 m²; nominal beats raw;
  D=None → no quantities.
- standoff: a 100×100 px polygon measures as 104×104 px after correction.
- region choice: two floor-plan regions at 1:50 and 1:100, a room in each,
  each gets its own D; a room outside both falls to `det_scale`; no
  `det_scale` → `TAKEOFF_NO_SCALE` and the room lands in `unscaled_rooms`.
- verification: viewport source → verified; text + "A3" on a 420×297 mm page
  → verified; text + "A1" on a 420×297 page → unverified +
  `SCALE_PRINT_RESIZED`; text alone → unverified + `SCALE_UNVERIFIED`.
- openings: door bbox straddling two rooms deducts from both; window on the
  exterior deducts once; opening in free space → `unassigned_openings`;
  width taken from `opening_line` over bbox; sliding door width from evidence
  not bbox; rejected candidate never deducts.
- heights: flag > prompt > default; prompt skipped when `can_prompt` is false;
  blank answer → default; opening taller than ceiling clamped + flagged.
- pipeline: `takeoff.json` written, room entity attributes carry `floor_m2`,
  summary totals present.

Corpus sanity (one-off, recorded in the PR, not a test): on s01 and s02 —
both 1:50, both carrying dimension strings — measure the px between two
dimension extension lines and confirm `× 8.467` reproduces the printed mm
within 2 %; then compare three room floor areas against hand-computed
length × width from those dimensions.

## Out of scope (recorded)

- RICS GIA/NIA (needs the wall-inclusive polygon).
- Automatic scale correction from sheet-size mismatch, and the
  dimension-string scale verifier — next branch.
- Reading ceiling heights from the drawing (0/20 corpus evidence).
- Per-room heights, sloped ceilings, hole-perimeter wall area,
  skirting/coving lengths (trivial once perimeter exists — a follow-up if
  wanted).
- Wall-centric (per `WallNetwork` segment) quantities.
- `RoomTakeoff.label` is always `None` until room labels are matched to
  rooms — `pipeline._room_entity` sets `label=None`.
- s01's stored user scale (1:50) measures as 1:100 on the drawing (1800 mm
  garden pair = 108.7 px); its takeoff numbers are 4× low until that stored
  scale is corrected — a separate data fix, because the stored scale also
  moves the detection factor and every W-classed wall/room gate. A
  plausibility guard (room < 1 m² / door < 0.5 m at the resolved scale) is a
  candidate follow-up.
