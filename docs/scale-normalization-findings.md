# Scale Normalization — Findings & Decision Log

**Started:** 2026-08-12 (brainstorm for the walls/rooms branch).
**Read this first** if you are working on scale-awareness for ANY detector
(doors, windows, labels, schedules are still scale-blind — see §6). The
design that consumes these findings: `docs/superpowers/specs/2026-08-12-scale-aware-wall-room-gates-design.md`.

## 1. The premise, verified

All geometric detection constants are absolute 150-DPI pixel values tuned on
the 1:50 reference sheets (s01, s02). At 150 DPI, 1px ≈ 0.1693mm of paper;
real-world mm per px = 0.1693 × denominator:

| Scale | mm/px | 300mm wall | 100mm leaf | 838mm door leaf |
|---|---|---|---|---|
| 1:50 | 8.5 | 35.4px | 11.8px | 49.5px |
| 1:100 | 16.9 | 17.7px | 5.9px | 24.8px |

Detection never sees the resolved scale: `resolve_page_scales` feeds only
`summary.json`/console (verified in `pipeline.py` — `page_scales` is not
passed to `run_heuristics`).

**Nuance that shapes everything:** only *world-space* constants should
scale. *Paper-space* ink (pen widths, dimension ticks, arrowheads) is drawn
at fixed paper size at any scale, and *dimensionless* gates (ratios, angles,
counts) are invariant. Blanket-scaling everything would be a bug — e.g.
scaling `WALL_MIN_STROKE_WIDTH_PX` would misclassify pens on 1:100 sheets.

## 2. Corpus scale census (measured 2026-08-12)

Method: extraction + cached region classification + `resolve_page_scales`
per sheet, no detection, no Gemini calls (script pattern: see the survey
section of the brainstorm; re-runnable in ~1min). Floor-plan regions only.

| Sheet | Floor-plan scale(s) | Source | Notes |
|---|---|---|---|
| s01 | 1:50 (both regions) | user (stored) | primary reference |
| s02 | 1:50 (page-level) | text ("scale bar - metric - 1:50@A3") | primary reference; fp region count 0 → page_scale path |
| s03 | 1:100 ×2 + 1:50 ×1 | viewport | **mixed on one page** |
| s04 | 1:50 | viewport (raw 50.0007) | nominal snap matters |
| s05 | 1:100 | viewport | |
| s06 | 1:100 | viewport | |
| s07 | 1:100 | viewport | |
| s08 | 1:50 | viewport | |
| s09 | — | — | no floor-plan regions |
| s10 | unresolved | | `SCALE_UNRESOLVED` |
| s11 | unresolved | | `SCALE_UNRESOLVED` |
| s12 | 1:100 | viewport | |
| s13 | ~1:136.4 | viewport | `SCALE_SOURCE_CONFLICT` — text says otherwise; viewport wins by design |
| s14 | 1:50 | text | |
| s15 | 1:50 | viewport | |
| s16 | unresolved | | `SCALE_UNRESOLVED` |
| s17 | 1:100 ×2 + 1:50 ×2 | viewport | **mixed on one page** |
| s18 | unresolved | | `SCALE_UNRESOLVED` |
| s19 | — | — | no floor-plan regions |
| s20 | unresolved | | `SCALE_MULTIPLE_UNBOUND` + `SCALE_UNRESOLVED` |

Bottom line: of 18 sheets reaching detection, 7 run at a non-1:50 scale the
constants weren't tuned for, 5 more are unknown.

## 3. Does scale mismatch explain the bad sheets? Partially.

False positives from committed ground truth vs resolved scale:

| Sheet | Scale | FPs | Sheet | Scale | FPs |
|---|---|---|---|---|---|
| s15 | **1:50** | **82** | s13 | ~1:136 | 6 |
| s12 | 1:100 | 22 | s16 | unresolved | 6 |
| s03 | mixed | 21 | s20 | unresolved | 6 |
| s17 | mixed | 18 | s08 | 1:50 | 3 |
| s18 | unresolved | 15 | s06 | 1:100 | 3 |

- **Consistent with scale mismatch:** s12/s03/s17 rank high. Mechanism
  example: at 1:100, a tile field's rungs are ~24px, under the 48px
  `WALL_LATTICE_MIN_RUNG_LEN_PX` floor → striped-field demotion stops firing
  → phantom walls.
- **Not the whole story:** the worst sheet, s15 (82 FPs), is 1:50.
- **Blind spot (important):** ground truth records only detections that were
  reviewed — false positives. Scale-shrink at 1:100 primarily predicts
  **misses** (features fall below px floors), and misses are invisible in
  this data because nothing was detected to review. Do not read the FP table
  as an upper bound on the scale problem.

## 4. Constant classification table

Classes: **W** = world-space (× f; areas × f²), **P** = paper-space
(unchanged), **D** = dimensionless (unchanged), **U** = uncertain — must be
measured on the real 1:100 sheets (s05/s07/s12) before the class is frozen.
`f = 50 / nominal_denominator` (1:100 → 0.5).

Status: **preliminary** — set during the 2026-08-12 brainstorm from each
constant's documented rationale. The implementation branch verifies every
use site and replaces U entries with measured verdicts. Update this table in
place; it is the successor branches' starting point.

### detection/walls.py

| Constant | Class | Rationale |
|---|---|---|
| WALL_MIN_STROKE_WIDTH_PX | P | pen width |
| WALL_FACE_MIN_LEN_PX | W | wall piece between openings |
| WALL_FACE_MERGE_GAP_PX | P | drafting artifact gap; note: must stay < scaled smallest opening |
| WALL_MIN_THICKNESS_PX | W | thinnest partition; floor scaled value at 1px (design §4) |
| WALL_MAX_THICKNESS_PX | W | heavy blockwork band (~305mm at 1:50) |
| WALL_THICK_MATERIAL_MAX_PX | W | 400mm band at 1:50 |
| WALL_PARALLEL_ANGLE_TOL | D | angle |
| WALL_BAND_MIN_ASPECT | D | ratio |
| WALL_PAIR_MIN_OVERLAP_PX | W | coincidence floor on face overlap |
| WALL_CENTERLINE_MERGE_GAP_PX | U | dedupe tolerance — thickness-tied (W?) or drafting (P?) |
| WALL_JUNCTION_SNAP_PX | U | endpoint reach — construction tolerance vs world gap |
| WALL_JUNCTION_MIN_ANGLE_DEG | D | angle |
| WALL_NETWORK_MIN_SEGMENTS | D | count |
| WALL_LIGHT_PEN_MIN_CHANNEL | P | color |
| WALL_DIM_TICK_MIN/MAX_LEN_PX, _END_TOL_PX, _STRADDLE_MIN_PX | P | dimension ticks are annotation |
| WALL_DIM_TICK_ANGLE_MIN/MAX | D | angles |
| WALL_BACKGROUND_FILL_MIN | P | color |
| WALL_FILL_CLASS_MIN_INK_PX | W | drawn ring length is world geometry |
| WALL_FILL_BLOCK_MAX_SIDE_PX | W | band-vs-block shape of built fills |
| WALL_MARKER_MAX_SIDE_PX | P | leader/dimension arrowheads are ~2–4mm of paper |
| WALL_HATCH_MIN_SEGMENTS | D | count |
| WALL_HATCH_MIN_RATIO | D | ratio |
| WALL_HATCH_MAX_LEN_PX | U | hatch stroke length — convention likely paper-space; interacts with LATTICE_MIN_RUNG_LEN ordering (design §4) |
| WALL_WEAK_STROKE_RATIO | D | pen ratio |
| WALL_WEAK_MIN_RUN_PX | W | partition run length |
| WALL_WEAK_MATERIAL_MIN_MARKS | D | count |
| WALL_WEAK_MATERIAL_MIN_SPAN | D | fraction |
| WALL_WEAK_MATERIAL_PER_100PX | U | density per WORLD length — but mark spacing may be paper-spaced hatch; measure |
| WALL_WEAK_MATERIAL_EDGE_PX | P | pen-adjacent exclusion |
| WALL_WEAK_MATERIAL_ANGLE_MIN/MAX | D | angles |
| WALL_WEAK_CLAIM_MARGIN_PX | U | thickness-comparison margin |
| WALL_WEAK_CLAIM_OVERLAP_FRAC | D | fraction |
| WALL_LATTICE_MIN_RUNGS | D | count (5 keeps cavity party wall out) |
| WALL_LATTICE_PITCH_TOL_PX | U | pitch equality tolerance |
| WALL_LATTICE_MIN_RUNG_LEN_PX | W | 48px ≈ 406mm at 1:50; **key phantom-wall gate at 1:100** — must stay above hatch-len cap in effect |
| WALL_LATTICE_TOUCH_GAP_PX | U | rung chaining reach |
| WALL_LATTICE_OFFSET_TOL_PX | P | collinearity tolerance |
| WALL_LATTICE_PEN_TOL | P | pen |
| WALL_HATCH_MAX_PITCH_PX | U | **critical**: hatch pitch measured 4.05/4.07px vs tightest real field 11.4px at 1:50; if hatch is paper-spaced the margin holds at 1:100, if world-spaced the classes collide at f=0.5 — measure on s05/s07/s12 |
| WALL_WHITE_TOUCH_TOL_PX | P | contact tolerance |
| WALL_WHITE_SPAN_MIN_FRAC | D | fraction |
| WALL_WHITE_TEXT_COVER_FRAC | D | fraction |
| WALL_JOINERY_BRIDGE_GAP_PX | W | open span between cavity segments (wardrobe runs) |
| WALL_JOINERY_BRIDGE_SLACK_PX | U | band-test slack |
| WALL_REDUNDANT_OFFSET_SLACK_PX | P | collapse tolerance |
| WALL_REDUNDANT_MIN_COVER | D | fraction |
| WALL_REDUNDANT_THICKNESS_SLACK_PX | U | thickness-comparison slack (the 4px far-face gate) |

### detection/rooms.py

| Constant | Class | Rationale |
|---|---|---|
| ROOM_MIN_AREA_PX2 | W (× f²) | smallest closet |
| ROOM_MAX_PAGE_AREA_FRAC, ROOM_HOLE_AREA_FRAC_MAX | D | fractions |
| ROOM_WALL_DILATE_PX, ROOM_LINE_BARRIER_PX | P | pen-tied standoff; MUST remain equal to each other (barrier-standoff rule) |
| ROOM_BARRIER_STROKE_RATIO, ROOM_PAIRED_FACE_MIN_FRAC, ROOM_WALL_PEN_MIN_FRAC | D | ratios/fractions |
| ROOM_PLUG_MID_NEAR_PX | U | hug distance |
| ROOM_GAP_CLOSE_PX | U | drafting gaps (P?) vs joint gaps that scale (W?); must stay < scaled thinnest doorway (design §4) |
| ROOM_EROSION_PX | U | wall-sliver scale — thickness-tied? |
| ROOM_BORDER_TOL_PX, ROOM_CONTACT_TOL_PX, ROOM_MASS_TOUCH_TOL_PX | P | contact tolerances |
| ROOM_WALL_CONTACT_MIN, ROOM_MAJOR_MASS_FRAC | D | fractions |
| ROOM_SIMPLIFY_TOL_PX | P | sub-pen-width simplification |
| ROOM_OPENING_SEAL_PX | W | reach into jambs the arc stopped short of |
| ROOM_PLUG_NEAR_PX | U | edge-hugs-material distance |
| ROOM_PLUG_SAMPLE_PX | P | numeric sampling resolution (finer relative sampling at small f is harmless) |
| ROOM_PLUG_ANCHOR_WIN_PX | W | "a jamb is jamb-sized" — jamb size is world-sized |
| ROOM_PLUG_HALF_WIDTH_PX | W | wall-band half-thickness |
| ROOM_PLUG_END/MID/FULL_COV_* | D | coverage fractions |
| ROOM_SLIDE_END_ASPECT_MIN | D | aspect |
| ROOM_BLIND_WINDOW_MAX_AREA_PX2 | W (× f²) | closet-scale area; margins re-checked at f=0.5 (real rooms ≥17k px² at 1:50 → ≥4.25k at 1:100 vs 10k×0.25=2.5k cap — holds) |
| ROOM_BASE_CONFIDENCE, *_BOOST, *_WEIGHT, *_MIN_CONFIDENCE, ROOM_BBOX_SEAL_MIN_CONFIDENCE | D | confidences |
| ROOM_PLUG_IN_WALL_FRAC, ROOM_FOLD_SPAN_TOL, ROOM_OPENING_TEXT_COVER_MAX | D | fractions |
| ROOM_FOLD_STACK_NEAR_PX, ROOM_FOLD_JAMB_MIN_LEN_PX | W | threshold depth / jamb-scale |
| ROOM_FOLD_GAP_ESCAPE_PX | P | ray-start construction offset |

## 5. Decisions (2026-08-12 brainstorm, user-approved)

1. **Approach: thread a scale factor** into walls/rooms and scale classified
   constants at use ("Approach B"). Rejected: geometry normalization into
   canonical 1:50 space (changes every detector at once + inverse-transform
   must find every evidence geometry field — silent-corruption risk);
   mm-redefinition of constants (invalidates tuning-guide/CLAUDE.md px lore,
   churns tests, cosmetic).
2. **Unresolved scale → identity (f = 1.0)**, current behavior. The user
   backfills s10/s11/s16/s18/s20 by hand via the existing prompt→store flow
   ('user'-source stored scales, as s01 already has). Rejected: geometric
   scale inference (guess-based subsystem; wrong guesses silently distort
   every gate).
3. **Mixed-scale pages (s03, s17): area-dominant floor-plan scale** + a
   `SCALE_MIXED_FLOOR_PLANS` warning. Per-scale-group detection deferred —
   per-region detection is a measured regression (see memory/CLAUDE.md:
   "never run heuristics per region").
4. **Nominal denominator preferred over raw** so 1:50 is exactly f=1.0.
5. **Clamp f to [0.25, 4.0]**, outside → 1.0 + `SCALE_FACTOR_CLAMPED`.
6. **s13 conflict:** viewport (~1:136) wins over caption text, per the
   resolver's existing rule.
7. **Scope:** walls/rooms only this branch; doors/windows/labels/schedules
   deferred (§6).
8. Regression gates: s01/s02 (and all 1:50 sheets) unchanged; 1:100 changes
   arrive as REVIEW lines for user verdicts. One fix + one sweep per
   iteration, then ask (standing checkpoint rule).

## 6. Deferred work (for successor branches)

- **Doors:** `DOOR_*` constants in `detection/doors/constants.py` — arc
  radii, leaf lengths, panel sizes are world-space (an 838mm leaf is 24.8px
  at 1:100, likely under current radius floors → predicts *misses* on
  s05/s06/s07/s12). Same classification discipline; reuse the shrunk-world
  synthetic test pattern (coordinates × 0.5, pen widths unchanged).
- **Windows:** `WINDOW_*` in `detection/windows.py` — sill/glazing gaps are
  world-space; angle gates dimensionless.
- **Labels/schedules:** mostly text-driven; font sizes are paper-space —
  expect few W constants. Audit anyway.
- **Cross-validation:** `CROSS_*` in `detection/postprocess.py` (door/window
  vs wall distances — world-space).
- **Layout segmentation:** `SEGMENT_MIN_REGION_SIDE_PX` etc. measure
  *drawing extents*, which scale — but region filtering has its own
  coverage guard; audit before touching.
- **Per-scale-group detection** for mixed pages (s03, s17): would need the
  union-per-scale-group compromise between "once over the union" and the
  known per-region degradation. Not designed.
- **Misses audit on 1:100 sheets:** ground truth cannot see misses (§3);
  after the walls/rooms branch lands, spot-check s05/s07/s12 overlays for
  undetected doors/partitions to size the doors branch.

## 7. Test patterns that worked (reuse them)

- **Shrunk-world synthetics:** scale coordinates × 0.5, keep pen widths —
  that IS a 1:100 export. Assert f=0.5 reproduces the f=1.0 result,
  including a case that fails if paper-space gates are wrongly scaled.
- **Identity test:** f=1.0 output == parameter-omitted output.
- **Ordering assertions** in the scaled-gates constructor (design §4) so a
  pathological factor fails loudly.
