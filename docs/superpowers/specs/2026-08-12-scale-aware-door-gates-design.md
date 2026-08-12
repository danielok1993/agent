# Scale-Aware Door Detection Gates — Design

**Date:** 2026-08-12
**Status:** Awaiting approval
**Companion:** `docs/scale-normalization-findings.md` — the corpus survey, the
frozen `WALL_*`/`ROOM_*` classification table, and the decision log this design
inherits. Predecessor: `2026-08-12-scale-aware-wall-room-gates-design.md`
(merged at `48f19dd`).

## Problem

`detection/doors/constants.py` holds 103 constants tuned on the 1:50 reference
sheets. `run_heuristics` already receives `scale_factor` but forwards it only to
`detect_wall_network` / `detect_rooms` — `detect_doors(page_data.paths,
page_data.text_spans, collector)` is called scale-blind
(`detection/orchestrator.py:45`).

The premise is measured, not assumed. Detected door bbox max-side, by resolved
scale tier, over the whole corpus:

| Tier | sheets | median-of-medians |
|---|---|---|
| 1:50 | s01, s02, s04, s08, s14, s15 | **89.4 px** |
| 1:100 | s05, s06, s07, s12 | **44.3 px** |

Ratio **0.496 ≈ f**. Door symbols are world-space. With the user's backfilled
stored scales (s11, s16, s18 → 1:100; s10, s20 → 1:50) the corpus now runs
**seven sheets at 1:100**.

## Scope

**In:** classify every `DOOR_*` constant; a `DoorGates` frozen dataclass built
per call; threading `scale_factor` from `run_heuristics` into `detect_doors` and
through the doors package; the six geometric `CROSS_*` constants in
`detection/postprocess.py` that gate door cross-validation (user decision,
2026-08-12).

**Out:**
- The Bezier aspect gate (`DOOR_BBOX_ASPECT_MIN/MAX`). It is the single largest
  measured miss driver on the 1:100 sheets — s06 detects 2 of 10 visible swings
  because genuine 85°-sweep arcs measure bbox aspect 0.804 against a
  [0.85, 1.15] gate, while the polyline path already uses a wider [0.65, 1.45]
  (`detection/doors/arcs.py:643`). It is **dimensionless**, so scale-awareness
  cannot fix it. Deferred to its own branch (user decision); recorded in
  findings §6 with the measurement.
- `WINDOW_*`, labels, schedules, per-scale-group detection for mixed pages.
- The s11 double-door assembly merge (see "Non-goals" below).

## Evidence base

All measurements ran through the real detection path — `resolve_page_regions` →
`filter_page_data` → `run_heuristics` — and the harness is checked against
`python tools/regress.py --sheet <slug>` before any number is trusted (see
"Measurement harness" below, and findings §4c for the failure mode that made
this mandatory).

### 1. The win, isolated (shrunk-world on the references)

Coordinates × 0.5, pen widths untouched — that is what a 1:100 export of the
same drawing looks like. Region scope held identical between runs, so scale is
the only variable.

| Sheet | doors at f=1.0 | recovered at f=0.5, nothing scaled | recovered, `W + panel` scaled |
|---|---|---|---|
| s01 | 11 | 6 | **7** |
| s02 | 15 | 12 | **15 (full identity)** |

### 2. The organising rule, measured

Two independent drawn quantities were measured across tiers:

| Quantity | 1:50 | 1:100 | ratio | verdict |
|---|---|---|---|---|
| door symbol extent | 89.4 px | 44.3 px | **0.496** | **W** |
| drawn leaf-panel thickness (leaf ↔ companion perp) | 1.69 px | 2.63 px | **1.56** | **P** |
| drawn slide-panel thickness | 7.83 px | 8.06 px | **1.03** | weak, see §4 |

**Extents scale; drawn ink separations do not.** Draftsmen scale the geometry
but keep line-pair separations legible on paper. This is the doors analogue of
the walls branch's pen-width rule, and it is what makes a blanket "scale every
`_PX` constant" wrong.

### 3. Confirmed-door retention on the real 1:100 sheets

The sweep's own gate. Every variant run at each sheet's resolved factor:

| Variant | s11 | s16 | s12 | s05 | s07 | s06 |
|---|---|---|---|---|---|---|
| today | 13/13 | 14/14 | 7/7 | 8/8 | 4/4 | 2/2 |
| **W only** | 13/13 | 14/14 | 7/7 | 8/8 | 4/4 | 2/2 |
| **W + panel thickness** | **13/13** | **14/14** | **7/7** | **8/8** | **4/4** | **2/2** |
| W + panel + ink-sep | 10/13 | 9/14 | 7/7 | 8/8 | 4/4 | **0/2** |
| ALL px (blanket) | 10/13 | 10/14 | 7/7 | 8/8 | 4/4 | **0/2** |

`W + panel thickness` is the only set that both achieves full shrunk-world
recovery on s02 and loses no confirmed door anywhere. Scaling the ink-separation
constants zeroes s06 — decisive evidence for their **P** verdict.

### 4. `DOOR_SLIDE_PANEL_MIN/MAX_THICKNESS_PX` — the one genuinely mixed row

Shrunk-world evidence is clean and says **W**: scaling it is what takes s02 from
12/15 to 15/15 (three sliding doors). Real-corpus evidence is not clean — the
1:100 panel population is bimodal (s12 2.13 px vs s11 8.06, s16 8.25) and the
1:50 baseline rests on a single sheet (s01 has no panels at all), so the 1.03
ratio in §2 is a small-sample aggregate of the kind findings §4b warns about.

Resolved **W**, because the two evidence sources answer different questions and
only one is decisive here: the shrunk-world test proves that *if* a 1:100 export
is a geometric halving, the gate must halve; and scaling it costs **zero**
confirmed doors on all six real 1:100 sheets while gaining three on s02. The
ambiguity is recorded, not hidden — revisit if a 1:100 sweep shows artifacts.

### 5. `CROSS_*` — re-derived by distribution

Classified first by what each constant measures: `CROSS_WALL_EXPAND_PX` is the
corridor reach beyond `thickness/2` at which a door bbox still counts as
`in_wall` — semantically a door-to-wall-band distance, a world-space candidate.

Then measured: for every confirmed door, the smallest `expand_px` at which
`WallNetwork.near_bbox` turns True, on each sheet's real network.

| Tier | median needed reach | p90, median-of-sheets | p90, max |
|---|---|---|---|
| 1:50 | 0.00 px | 9.64 px | 13.54 px |
| 1:100 | 0.00 px | 0.78 px | 8.12 px |

The **median is degenerate** — most confirmed doors sit directly on a band, so
the median is 0 at both tiers and carries no signal. The tail is the informative
statistic, and it scales (p90 ratio 0.081). The load-bearing safety property:
the scaled gate at f=0.5 is 10.0 px, which still exceeds every 1:100 sheet's p90
need (max 8.12 px) with 1.88 px of headroom.

Verdict **W** for all six geometric door-side `CROSS_*` constants, confirmed
behavior-neutral on the corrected path across all seven 1:100 sheets (s11 13/13,
s16 14/14, s12 7/7, s05 8/8, s07 4/4, s06 2/2, s18 9/9 — unchanged, including
candidate counts).

**This reverses an earlier conclusion.** A first pass classified `CROSS_*` as
conservative-P on the basis of door-survival counts from the broken harness;
that derivation was void twice over — wrong numbers, and wrong method (findings
§4 requires classifying by what a constant measures, then measuring the
distribution, never by which setting keeps more doors alive on one sheet).

### 6. Measurement harness — the failure mode to record

The first harness called `run_heuristics` on **raw whole-page `PageData`**
instead of `resolve_page_regions(...).detection_page_data`. On s11 the page also
carries a location plan, a block plan and elevations; a wall network built over
that ink is not the network the real pipeline produces, so `wall_context` flipped
to `no_wall` for three `single_line_leaf` doors, `CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY`
(0.15) dropped them 0.67 → 0.52, under the 0.55 floor, and the harness reported
a non-existent "3 lost confirmed doors on main". `tools/regress.py --sheet s11`
says **13/13**.

Rule adopted: **any side harness must reproduce the sweep's counts before its
numbers are used, and `tools/regress.py` is the arbiter.** `harness.py` carries
a self-check against five sheets' known sweep counts for exactly this reason.
Goes into findings §4c alongside the other measurement traps.

## Design

### 1. `DoorGates` (mirrors `WallGates`/`RoomGates`)

A frozen dataclass in `detection/doors/constants.py`, one field per scaled
constant, **named exactly like the constant it scales**:

```python
@dataclass(frozen=True)
class DoorGates:
    DOOR_MIN_SIZE_PX: float
    DOOR_MAX_SIZE_PX: float
    ...

    @classmethod
    def at(cls, factor: float) -> "DoorGates":
        return cls(DOOR_MIN_SIZE_PX=DOOR_MIN_SIZE_PX * factor, ...)

DOOR_GATES_UNSCALED = DoorGates.at(1.0)
```

- **Exact identity at f = 1.0** — every field is `constant * 1.0`, so all 1:50
  and unresolved-scale sheets are bit-identical to today.
- Module constants keep their tuned 1:50 definitions and stay importable by
  tests; no module-global mutation.
- Paper-space and dimensionless constants are **not fields** — being absent from
  the dataclass is what makes "this one does not scale" unmissable in review.

### 2. Threading

`run_heuristics` passes its existing `scale_factor` to `detect_doors`, which
builds `DoorGates.at(scale_factor)` once and passes it down. The doors package
is acyclic (`constants ← arcs/leaves/shape/sliding ← folding ← assembly ←
detect`), so gates flow strictly downward.

**Every helper that consumes a scaled constant takes `gates` as a keyword-only,
non-default parameter.** No `gates: DoorGates = DOOR_GATES_UNSCALED` defaults
anywhere — findings §4(b) records that a single defaulted parameter silently ran
`_bridge_white_runs` unscaled on every sheet, and a name-grep could not find it.
A missing argument must be a `TypeError`, not a silent identity fallback.

Audit surface, already established: the only production caller of the doors
package is `detection/orchestrator.py:45`; everything else importing
`detection.doors.*` is a test. Within the package, `assembly.py` →
`sliding.py` / `folding.py` are the cross-module calls that get the same
no-default treatment.

### 3. `CrossGates`

The same pattern in `detection/postprocess.py` for the six geometric door-side
constants. `_cross_validate` builds it from a `scale_factor` parameter threaded
from `run_heuristics`.

Note for review: `CROSS_DOOR_EXPAND_PX` / `CROSS_DOOR_FALLBACK_EXPAND_PX` gate
the door→window suppression veto, so scaling them can move window candidates
too. Measured neutral on the corpus (§5), but it is the one place this branch
reaches outside doors, and the sweep's window lines are the check.

### 4. Classification

All 103 `DOOR_*` constants are accounted for. Full per-constant table with
rationale goes in findings §4d (the deliverable successors inherit); the rules:

**W — world-space, × f (19 + 2 panel + 6 CROSS):** extents and spans of built
objects. `DOOR_MIN_SIZE_PX`, `DOOR_MAX_SIZE_PX`, `DOOR_SWING_LINE_DIST_PX`,
`DOOR_POLYLINE_MAX_SEG_PX` (a tessellated arc's segment is `r·Δθ`; r is
world-space by §1's 0.496 measurement and Δθ is a fixed exporter setting, so the
segment scales with r — no direct cross-scale measurement is available because
the 1:100 sheets draw their arcs as native Beziers, not polylines),
`DOOR_ASSEMBLY_CONNECT_TOL_PX`, `DOOR_LEAF_LINE_ENDPOINT_TOL_PX`,
`DOOR_THRESHOLD_ENDPOINT_TOL_PX`, `DOOR_DOUBLE_LEAF_{GAP,OVERLAP,CENTER_TOL}_PX`,
`DOOR_SLIDE_FLANK_GAP_{MIN,MAX}_PX`, `DOOR_SLIDE_PARK_{GAP_MAX,JAMB_TOL}_PX`,
`DOOR_SLIDE_PARK_BAND_{MIN,MAX}_TH_PX` (wall-band thickness — the same quantity
`WALL_MIN/MAX_THICKNESS_PX` already carries as W),
`DOOR_FOLD_JAMB_ANCHOR_TOL_PX`, `DOOR_FOLD_JAMB_LINE_MIN_LEN_PX` (jamb-scale,
matching `ROOM_FOLD_JAMB_MIN_LEN_PX`), `DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX`,
`DOOR_SLIDE_PANEL_{MIN,MAX}_THICKNESS_PX` (§4), and the six `CROSS_*` (§5).

**P — paper-space, unchanged (12):** drawn ink separations —
`DOOR_LEAF_COMPANION_PERP_PX`, `DOOR_FOLD_LEAF_LINE_SEP_{MIN,MAX}_PX` (measured,
§2/§3) — and CAD-precision snap tolerances, whose own comments already state the
rationale: `DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX` ("machine-precise endpoints"),
`DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX` ("CAD-precise curve endpoints"),
`DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX`, `DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX`
("stroked rings snap at CAD precision"), `DOOR_SLIDE_PANEL_MERGE_TOL_PX`,
`DOOR_FOLD_HINGE_TOL_PX` (corner-to-corner fit slack at a hinge where leaves
share the ring vertex exactly — measured offsets ≤ 0.3 px, i.e. a fit tolerance,
not a built dimension), `DOOR_POLYLINE_ENDPOINT_TOL` (the snap-key divisor;
scaling it costs a confirmed door), `DOOR_V2_BRIDGE_BUFFER_PX`, and
`DOOR_LABEL_SEARCH_RADIUS_PX` — **no corpus signal**, only s02 carries door
labels at all and every 1:100 sheet has zero, so it freezes P under findings
§4b's conservative-default rule.

Arithmetic check, so the table is provably exhaustive: 103 `DOOR_*` constants =
33 px-valued (19 W + 2 panel-thickness W + 12 P) + 70 D. The six door-side
`CROSS_*` constants are additional to the 103.

**D — dimensionless, unchanged (70):** all `*_DEG` angles (15), `*_FRAC` /
`*_RATIO` / `*_TOL` fractions and confidences (28 + `DOOR_LEAF_LINE_LENGTH_TOL`,
`DOOR_LEAF_COMPANION_OVERLAP`), segment/bin/curve/leaf counts (13), aspects
(`DOOR_BBOX_ASPECT_MIN/MAX`, `DOOR_LEAF_ASPECT_MIN`), the `*_FACTOR` multipliers
(`DOOR_SLIDE_LATERAL_FACTOR`, `DOOR_SLIDE_ZONE_WIDTH_FACTOR` — both defined
relative to a panel dimension that itself scales), `DOOR_HU_*` (a normalised
raster and shape distances), plus `DOOR_LABEL_PATTERN`, `DOOR_LAYER_KEYWORDS`
and `_DOOR_HU_TEMPLATE_VALUES` (not numeric gates).

**No densities or per-length rates exist in `DOOR_*`**, so the ÷ f case that
`WALL_WEAK_MATERIAL_PER_100PX` needed does not arise here. Stated explicitly so
a future auditor does not go looking.

**Hidden-constant audit — clean.** Every numeric literal in
`detection/doors/*.py` outside `constants.py` was enumerated and is
dimensionless (angle bins, ratios, confidences, counts). The one derived use
site, `folding.py:233` (`DOOR_MIN_SIZE_PX * 0.7`), scales automatically. No
`COLLINEAR_OFFSET_TOL`-shaped blind spot exists in this package.

### 5. Ordering invariants

Checked in `DoorGates.at`, so a pathological factor fails loudly:

- `DOOR_MIN_SIZE_PX < DOOR_MAX_SIZE_PX` and
  `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX < DOOR_SLIDE_PANEL_MAX_THICKNESS_PX`
  (preserved automatically by a common factor; asserted anyway).
- `DOOR_FOLD_LEAF_LINE_SEP_MAX_PX` (P, 4.0) vs `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX`
  (W, 3.0 × f): these bound the same physical thing — a drawn leaf's two edges —
  from opposite sides, and at f < 0.75 the W value drops below the P one. That
  is not a contradiction (they gate different detectors, and the measured
  populations differ), but it is exactly the kind of cross-class relationship
  findings §4b flagged for `WALL_HATCH_MAX_LEN_PX`, so it is asserted and
  documented rather than left to be rediscovered.
- The scaled `DOOR_MIN_SIZE_PX` floors at 1 px, mirroring the
  `WALL_MIN_THICKNESS_PX` treatment.

## Non-goals (recorded, not fixed)

**The s11 double door is not a scale bug.** Findings §6 named it as this
branch's regression target, and it was tested directly: the french/garden merge
fires on s11 only when `DOOR_LEAF_COMPANION_PERP_PX` is scaled — and that is the
paper-space constant whose scaling costs 3 confirmed doors on s11, 5 on s16, and
both of s06's. Under the correct classification the merge does **not** fire, so
`door_0005` / `door_0007` (conf 0.60, at (765,1224) and (766,1640)) stay two
half-width singles and stay unreviewed. This branch must not be judged on that
target; it is a separate assembly-merge defect and moves to findings §6 with
this measurement attached.

## Testing

- **Identity:** `detect_doors(...)` with `scale_factor=1.0` equals the
  parameter-omitted call, candidate-for-candidate.
- **Shrunk-world synthetics** (findings §7's pattern): each door topology that
  owns a scaled constant — arc + anchored-line leaf (`DOOR_MIN_SIZE_PX`),
  sliding `leaf_pair` (`DOOR_SLIDE_PANEL_*_THICKNESS_PX`), sliding `parked_leaf`
  (`DOOR_SLIDE_PARK_BAND_*`), folding `open_v` (`DOOR_FOLD_JAMB_*`), double-leaf
  pairing (`DOOR_DOUBLE_LEAF_*`) — built at 1:50 coordinates, then again at
  × 0.5 with **stroke widths unchanged**, asserting `scale_factor=0.5`
  reproduces the f=1.0 detection.
- **Negative controls** (fail if threading is removed): each shrunk-world case
  asserts the door is **missed** at `scale_factor=1.0`, so a helper that stops
  receiving gates breaks a test rather than silently reverting.
- **Paper-space invariance:** a shrunk-world case whose leaf double-line
  separation stays at its paper value must still detect — it fails if
  `DOOR_LEAF_COMPANION_PERP_PX` is wrongly scaled. This is the s06 wipeout
  (0/2) captured as a unit test.
- **Ordering assertions** at the clamp boundaries (f = 0.25 and 4.0).
- **No-default enforcement:** a test asserting the gates-carrying helpers raise
  `TypeError` when `gates=` is omitted.
- The fast tier stays green throughout. A pre-existing test failing means
  identity broke — fix the code, never the test.

## Acceptance criteria

1. `python -m unittest discover tests` green, including the new identity,
   shrunk-world, negative-control, paper-space-invariance and ordering tests.
2. `python tools/regress.py`: **no lost `confirmed` entity and no returned false
   positive** beyond the corpus's already-documented debt (findings §3). The
   1:50 and unresolved-scale sheets must be byte-identical — verified against a
   baseline worktree sweep if there is any doubt, as
   `docs/scale-baseline-comparison-2026-08-12.md` did.
3. Changes on the 1:100 sheets arrive only as REVIEW lines. The user verdicts
   them; this branch never runs `tools/review.py`, never edits
   `tests/ground_truth/` or fixture bytes.
4. Findings §4d carries the frozen per-constant table with every `DOOR_*` and
   door-side `CROSS_*` constant accounted for and each measured row citing its
   measurement; §4c carries the harness failure mode; §6 gains the aspect-gate
   and s11-merge entries with their evidence.
5. `graphify update .` run after the code changes.

## Rejected alternatives

- **Blanket-scale every `_PX` constant.** Measured: loses 3 confirmed doors on
  s11, 4–5 on s16, and both of s06's. This is the design's central negative
  result, not a hypothetical.
- **Scale only the two constants measured load-bearing** (`DOOR_MIN_SIZE_PX`,
  `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX`). Tempting — it is the minimum that
  reproduces the win on this corpus — but "inert on 20 sheets" is not
  "dimensionless", and leaving a genuinely world-space gate unscaled just defers
  the bug to the 21st sheet. The walls branch set the precedent of implementing
  the whole classified table.
- **Geometry normalization** into canonical 1:50 space — rejected for doors for
  the same reason findings §5 rejected it for walls: the inverse transform must
  find every geometry field in candidate evidence (`arc_bbox`, `leaf_bbox`,
  `opening_line`, `leaf_bbox_a/b`, …) and one missed field is silent corruption.
