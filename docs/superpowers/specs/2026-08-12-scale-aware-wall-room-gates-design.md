# Scale-Aware Wall/Room Detection Gates — Design

**Date:** 2026-08-12
**Status:** Approved for planning
**Companion:** `docs/scale-normalization-findings.md` — the corpus survey, the
full constant classification table, and the decision log this design rests on.
Successor branches (doors/windows/labels/schedules) start there.

## Problem

Detection is scale-blind. `scale/` resolves a drawing scale per floor-plan
region (merged in `b0e705a`), but `run_heuristics` never receives it — the
result feeds only `summary.json` and the console table. Every geometric
constant in `detection/walls.py` and `detection/rooms.py` is an absolute
150-DPI pixel value tuned on the two 1:50 reference sheets (s01, s02).

At 150 DPI one pixel is ~0.17mm of paper. A 300mm cavity wall is ~35px at
1:50 but ~18px at 1:100; a 100mm partition leaf drops from ~12px to ~6px.
The corpus survey (findings doc §2) shows this is not hypothetical: of the 18
sheets that reach detection, 4 are pure 1:100 (s05, s06, s07, s12), 2 mix
1:50 and 1:100 floor plans on one page (s03, s17), 1 resolves ~1:136 (s13),
and 5 resolve nothing (s10, s11, s16, s18, s20). Gates tuned at 1:50
therefore run at the wrong effective size on at least 7 sheets — e.g. at
1:100 a tile field's rungs halve to ~24px, under the 48px
`WALL_LATTICE_MIN_RUNG_LEN_PX` floor, so the striped-field demotion stops
firing and phantom walls return.

Not every constant should scale (findings doc §4):

- **World-space** constants measure built objects (wall thickness, rung
  length, jamb reach, room area). These scale with the drawing: × `f` for
  lengths, × `f²` for areas.
- **Paper-space** constants measure ink and annotation drawn at fixed paper
  size regardless of scale (pen widths, dimension ticks, leader arrowheads,
  drafting tolerances). These must NOT scale.
- **Dimensionless** constants (ratios, fractions, angles, counts,
  confidences) are invariant.
- **Uncertain** constants (hatch pitch/density, drafting-gap closing,
  erosion) are resolved by measurement on the real 1:100 sheets before their
  class is frozen — never by guess.

## Scope

**In:** the factor computation, plumbing into `detect_wall_network` +
`detect_rooms`, and the classified conversion of the `WALL_*`/`ROOM_*`
constants. **Out (deferred, recorded in findings doc §6):** doors, windows,
labels, schedules; per-scale-group detection for mixed pages;
geometry-based scale inference for unresolved sheets.

## Design

### 1. Factor computation (`scale` package)

New pure function `detection_scale(page_scales: PageScales,
regions: list[Region]) -> tuple[float, list[dict]]`:

1. Collect floor-plan regions with a bound scale; pick the **ink-dominant**
   nominal denominator (sum of contained path counts per denominator,
   largest wins — gates act on primitives, not blank paper, so path count
   beats bbox area as the dominance measure). If bound floor-plan regions
   disagree, emit `SCALE_MIXED_FLOOR_PLANS` naming the scales present and
   the winner.

   **This single-factor treatment of mixed pages (s03, s17) is interim, not
   the end state.** The correct behavior — each plan detected at its own
   scale — requires per-scale-group detection passes with frozen
   union-level statistics, which is a measured-risk pipeline restructure
   deferred to a follow-up branch (findings doc §6 has the design sketch
   and the s01 degradation evidence that shapes it). Until then the warning
   guarantees mixed pages are never silently mispriced.
2. No bound floor-plan scales → fall back to `page_scale` (covers s02,
   where region filtering is suppressed and the caption binds page-level).
3. Nothing resolved → factor **1.0**. No new warning — the resolver already
   emits `SCALE_UNRESOLVED`.
4. `factor = 50.0 / denominator`, preferring `ScaleInfo.nominal` over the
   raw denominator so 1:50 sheets compute **exactly 1.0** (s04's raw
   viewport gives 50.0007; the nominal snap makes identity exact by
   construction, not by float luck). 1:100 → 0.5. s13 → the viewport's
   ~1:136 wins, per the resolver's existing conflict rule (`/Measure`
   describes the PDF as it is).
5. **Clamp:** a factor outside **[0.25, 4.0]** (denominators outside
   1:12.5–1:200) falls back to 1.0 with a `SCALE_FACTOR_CLAMPED` warning.
   Site-plan scales (1:500, 1:1250) don't draw walls as double lines, so
   scaling gates toward them only creates noise.

The chosen factor and its provenance (denominator, source, mixed/clamped
flags) are added to `summary.json`'s existing `scales` dict.

### 2. Plumbing

`pipeline.run_extract` calls `detection_scale` after `resolve_page_scales`
and passes the factor to `run_heuristics(…, scale_factor: float = 1.0)`,
which forwards it to `detect_wall_network` and `detect_rooms` only. Warnings
from `detection_scale` fold into the page's warning list alongside the
resolver's, same as today.

Inside walls/rooms:

- **No module-global mutation.** The entry functions build an explicit
  scaled-gates object (world-space constants × `f`, areas × `f²`) once per
  call and pass it to the helpers that need it. Module constants keep their
  tuned 1:50 definitions and remain importable by tests.
- **Exact identity at `f = 1.0`:** the scaled values are the constants
  themselves (multiplication by 1.0), so every comparison is bit-identical
  to today's behavior on 1:50 and unresolved sheets.
- Every use site of every `WALL_*`/`ROOM_*` constant is accounted for in
  the findings-doc table — a missed use site (one gate scaling while a
  related one doesn't) is the primary implementation risk, and the table is
  the audit trail against it.

### 3. Constant classification

The full per-constant table with rationales lives in the findings doc (§4)
— it is the deliverable future branches inherit. Rules of the game:

- **World-space** (× `f`; areas × `f²`): `WALL_MIN/MAX_THICKNESS_PX`,
  `WALL_THICK_MATERIAL_MAX_PX`, `WALL_FACE_MIN_LEN_PX`,
  `WALL_PAIR_MIN_OVERLAP_PX`, `WALL_WEAK_MIN_RUN_PX`,
  `WALL_LATTICE_MIN_RUNG_LEN_PX`, `WALL_FILL_BLOCK_MAX_SIDE_PX`,
  `WALL_JOINERY_BRIDGE_GAP_PX`, `ROOM_OPENING_SEAL_PX`,
  `ROOM_PLUG_ANCHOR_WIN_PX`, `ROOM_PLUG_HALF_WIDTH_PX`,
  `ROOM_FOLD_STACK_NEAR_PX`, `ROOM_FOLD_JAMB_MIN_LEN_PX`,
  `ROOM_MIN_AREA_PX2` (× `f²`), `ROOM_BLIND_WINDOW_MAX_AREA_PX2` (× `f²`), …
- **Paper-space** (unchanged): `WALL_MIN_STROKE_WIDTH_PX` and every pen
  ratio; `WALL_DIM_TICK_*`; `WALL_MARKER_MAX_SIDE_PX` (arrowheads are
  ~2–4mm of paper at any scale); `ROOM_WALL_DILATE_PX` /
  `ROOM_LINE_BARRIER_PX` / `ROOM_SIMPLIFY_TOL_PX` (pen-width-tied, and the
  first two must stay EQUAL per the barrier-standoff rule); color channels.
- **Dimensionless** (unchanged): all `*_FRAC`, `*_RATIO`, `*_TOL` angles,
  counts, confidences.
- **Uncertain — measure before freezing:** `WALL_HATCH_MAX_PITCH_PX` and
  `WALL_WEAK_MATERIAL_PER_100PX` hinge on whether hatch spacing in these
  CAD exports is world- or paper-space; `ROOM_GAP_CLOSE_PX`,
  `ROOM_EROSION_PX`, `WALL_JUNCTION_SNAP_PX`, `WALL_LATTICE_PITCH_TOL_PX`,
  `WALL_CENTERLINE_MERGE_GAP_PX` and the other small tolerances are
  ambiguous. Each is measured on the real 1:100 sheets (s05, s07, s12)
  during implementation; the measurement and the resulting class go in the
  findings table. Guessing a class for these is expressly forbidden — the
  hatch-vs-wall pitch separation (measured 4.05px vs 11.4px at 1:50) is
  load-bearing, and at f = 0.5 the gap between the classes narrows.

### 4. Interactions to preserve (invariants across scales)

Several constants are tuned relative to EACH OTHER; scaling one class but
not the other must not break the orderings the algorithms rely on:

- `WALL_LATTICE_MIN_RUNG_LEN_PX` must remain above the hatch-stroke length
  cap in effect, whatever class `WALL_HATCH_MAX_LEN_PX` lands in — that
  ordering is what keeps short hatch from forming rungs.
- `WALL_MIN_THICKNESS_PX` × f at f = 0.25 approaches pen width; the clamp
  (§1) plus a floor of 1px on the scaled value keeps the pair search sane.
- `ROOM_GAP_CLOSE_PX` must stay smaller than the scaled thinnest real
  doorway gap, or gap-closing seals real openings at small factors.

The implementation adds an assertion-style check (in the scaled-gates
constructor) for these orderings so a bad factor fails loudly, not silently.

### 5. Testing

- **Unit — factor:** ink-dominant pick; page-scale fallback; unresolved →
  1.0; mixed → `SCALE_MIXED_FLOOR_PLANS`; nominal preferred over raw;
  clamp behavior.
- **Identity:** all existing synthetic tests run at the default factor
  unchanged, plus an explicit test that output at `scale_factor=1.0` equals
  output with the parameter omitted.
- **Shrunk-world synthetics (the strong tier):** representative synthetic
  topologies (wall pair, lattice field, hatch field, material-backed weak
  pair, room with door plugs) with all *coordinates* scaled by 0.5 and *pen
  widths left unchanged* — exactly what a 1:100 export looks like — assert
  detection with `scale_factor=0.5` reproduces the 1:50 result. This
  includes the paper-space-invariance case: a test that would fail if
  stroke-width gates were wrongly scaled.
- **Area law:** room-area floors apply at f².
- **Ordering assertions:** the §4 invariant checks have their own tests at
  the clamp boundaries.
- **Regression:** `tools/regress.py` — no lost `confirmed`, no returned
  false positive anywhere; the 1:50 sheets (s01, s02, s04, s08, s14, s15)
  must be effectively identical. The 1:100 sheets are *expected* to change;
  new detections surface as REVIEW lines for the user's verdicts. One fix +
  one sweep per iteration, then the user reviews (per the standing
  checkpoint rule).

### 6. Rejected alternatives (full reasoning in findings doc §5)

- **Geometry normalization** (rescale all coordinates into canonical 1:50
  space before detection, inverse-transform outputs): silently changes every
  detector at once — the opposite of the walls/rooms-first scoping — and the
  inverse transform must find every geometry field in candidate evidence;
  one missed field is silent corruption.
- **Redefining constants in millimetres:** invalidates every measured px
  number in the tuning guide and CLAUDE.md lore, churns all tests, and still
  needs the same threading. Cosmetic.
- **Geometry-based scale inference for unresolved sheets:** guess-based;
  the user backfills the five unresolved sheets via the existing
  prompt→store flow instead ('user'-source stored scales, as s01 already
  has).

## Acceptance criteria

1. `python -m unittest discover tests` green, including the new factor,
   identity, shrunk-world, area-law and ordering tests.
2. `python tools/regress.py`: exit 0 — no lost confirmed, no returned false
   positive on any sheet; 1:50 sheets unchanged.
3. Changes on the 1:100 sheets appear only as REVIEW lines; the user
   verdicts them via `tools/review.py`.
4. `summary.json` records the detection factor and provenance per page.
5. `docs/scale-normalization-findings.md` contains the frozen
   classification table with every `WALL_*`/`ROOM_*` constant accounted
   for, uncertain entries resolved by recorded measurements.
