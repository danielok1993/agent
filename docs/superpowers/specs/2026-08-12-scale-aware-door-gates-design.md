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

Coordinates × 0.5, pen widths untouched. Region scope held identical between
runs, so scale is the only variable.

| Sheet | doors at f=1.0 | recovered at f=0.5, nothing scaled | recovered, `W + panel` scaled |
|---|---|---|---|
| s01 | 11 | 6 | **7** (+4 transform artifacts, see below) |
| s02 | 15 | 12 | **15 (full identity)** |

**The transform is faithful for extents and unfaithful for ink separations.** A
plain × 0.5 coordinate shrink halves *everything*, including the drawn
leaf-companion and fold-line separations that §2 measures as paper-space in real
1:100 exports (they hold at ~2.6 px, or grow). So any door whose detection rests
on a separation gate is tested under conditions a real 1:100 sheet never
produces, and a miss there says nothing about the classification.

s01's four unrecovered doors were diagnosed individually, and **all four are in
exactly that class** — three `single_line_leaf` doors whose evidence rests on a
leaf-companion separation, plus the `sliding`/`parked_leaf`. Every door on the
sheet whose detection rests on extents alone is recovered. So s01's 7/11
understates the classification's performance; it measures the synthetic
transform's fidelity, not the gates. The honest reading of this table is s02's
full-identity 15/15 plus "no extent-dependent door was lost on either sheet".

The Testing section's per-topology fixtures therefore shrink extents while
holding separations at their paper values, rather than scaling the whole
coordinate space — the synthetic equivalent of a real 1:100 export.

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

This table isolates the door gates and reports doors only. **Windows and rooms
are checked too**, with `CROSS_*` included and against the baseline rather than
in the absolute — see §6, which is the complete picture and the one to review.

### 4. `DOOR_SLIDE_PANEL_MIN/MAX_THICKNESS_PX` — the weakest row in the table

This constant gates a drawn panel thickness, so §1's caveat applies to it
directly: **the shrunk-world evidence is not independent** of the question. The
transform halves panel thickness by construction, so "scaling the gate recovers
the door" is close to restating the assumption. It cannot be cited as proof of
the class, and §1's 15/15 is not evidence for this row specifically.

Real-corpus evidence is also inconclusive: the 1:100 panel population is bimodal
(s12 2.13 px vs s11 8.06, s16 8.25) against a 1:50 baseline resting on one sheet
(s01 has no panels at all), so §2's 1.03 ratio is the small-sample aggregate
findings §4b warns about.

What does discriminate is converting to millimetres. Slide panels measure
7.83 px at 1:50 ≈ **66 mm** — a real panel-plus-frame thickness. Swing-leaf
companion separations measure 2.88 px ≈ 24 mm on s01 and 0.50 px ≈ 4 mm on s02 —
not a buildable leaf, i.e. symbolic. And the 1:100 leaf separations (2.62–3.25 px
≈ 44–55 mm) read as *larger* in mm than the 1:50 ones, which is the signature of
a **minimum drawn separation**: the drafting system will not put two lines closer
than ~2.5 px whatever the scale. That is why leaf-companion is P and a panel
rectangle is not.

Resolved **W**, with the ambiguity recorded rather than hidden, and two facts a
reviewer should hold: (a) `MIN`-only, `MAX`-only and both produce **identical**
deltas on every one of the seven 1:100 sheets, so this corpus cannot
discriminate the two halves; (b) scaling `MIN` is the permissive direction, and
its own tuning rationale ("thinner is a shower screen / glazing strip, measured
2.0–2.5 px") is itself a *drawn* separation subject to the same paper floor — so
the concrete revisit trigger is **shower screens or glazing strips appearing as
sliding doors on a 1:100 sheet**, not a miss.

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

### 6. Predicted sweep delta — what the user should expect to review

Measured by running the **full** `W + panel + CROSS` set on the real path at each
sheet's resolved factor, across **all three entity types** (not doors alone —
`CROSS_DOOR_EXPAND_PX` reaches the door→window suppression veto, so windows had
to be in scope of the check), and comparing against today's baseline on the same
path.

| Sheet | f | door kept / new / gone | window kept / new / gone | room kept / new / gone |
|---|---|---|---|---|
| s05 | 0.50 | 8/8 · 0 · 0 | — | — |
| s06 | 0.50 | 2/2 · 0 · 0 | 8/8 · 0 · 0 | 0/1 · 2 · 2 |
| s07 | 0.50 | 4/4 · 0 · 0 | 10/10 · 0 · 0 | 7/7 · 0 · 0 |
| s11 | 0.50 | 13/13 · **2** · 0 | 23/23 · **4** · 0 | 17/17 · 0 · 0 |
| s12 | 0.50 | 7/7 · 0 · **2** | 0/0 · **5** · 1 | 3/4 · 0 · 0 |
| s16 | 0.50 | 14/14 · 0 · 0 | 23/23 · 0 · 0 | 13/13 · 0 · 0 |
| s18 | 0.50 | 9/9 · **1** · 0 | 4/4 · **8** · 0 | 6/9 · 0 · 0 |
| **total** | | 57/57 · **3** · 2 | 68/68 · **17** · 1 | 46/51 · 2 · 2 |

**No confirmed entity is lost on any sheet or any type** — every retention count
is identical to the baseline's, checked side by side. The room shortfalls (s06
0/1, s12 3/4, s18 6/9) are **pre-existing baseline debt**, present before and
after, and are not this branch's.

Two things a reviewer must not be surprised by:

- **The branch produces more window REVIEW lines than door ones (17 vs 3).**
  Isolated, most of that comes from the *door* gates rather than `CROSS_*` (s18:
  door gates +8, CROSS alone +1): changed door candidates change what
  `_resolve_door_window_conflicts` and the door→window veto suppress, so
  different windows survive. Expected, measured, and the sweep's window lines
  are where it shows up.
- **The real-corpus door win is small — 3 new REVIEW doors across seven 1:100
  sheets.** This branch is correctness infrastructure plus the 21st-sheet
  argument, not a large detection gain on today's corpus; s06's 80 % miss rate
  is driven by the dimensionless aspect gate that this branch deliberately does
  not touch, so the visible payoff largely waits on the deferred aspect-gate
  branch. Judging this sweep against a large door delta would be judging it
  against the wrong target.

### 7. Measurement harness — the failure mode to record

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
world-space by the 0.496 measurement above and Δθ is a fixed exporter setting,
so the segment scales with r. **Caveat:** that holds for fixed-Δθ tessellation;
an exporter that tessellates to a fixed *chord error* instead gives segment
length ~ √r, which still shrinks with scale but by ~0.71 at f=0.5, not 0.5. This
is unmeasurable on the corpus — every 1:100 sheet draws its arcs as native
Beziers, so there are no 1:100 polyline arcs to measure — so the row is W on the
dimensional argument alone. **Revisit if a polyline-arc sheet at another scale
appears.**),
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
dimensionless (angle bins, ratios, confidences, counts). (corrected
2026-08-13: this overstates it — five px-valued fit/snap slacks exist, all
≤4px: `folding.py:381,384,391,412,419` (4.0/3.0/2.0px slacks in the `open_v`
corridor span/crosser scan), `sliding.py:369,460` (3.0px flank-straightness
slack), `arcs.py:544` (2.0px polyline min-segment floor). None are
world-space — they behave as implicitly paper-space, the same class as the
P constants above, and are left unscaled — but "clean" and "every ... is
dimensionless" were wrong; a future re-audit should check these sites rather
than skip them on that word.) The one derived use site, `folding.py:233`
(`DOOR_MIN_SIZE_PX * 0.7`), scales automatically. No
`COLLINEAR_OFFSET_TOL`-shaped blind spot exists in this package.

### 5. Ordering invariants — what is asserted, floored, and left alone

`WallGates.at` (`detection/walls.py:262`) set the precedent and this follows it
exactly: **assertions are only for factor-independent programming errors;
cross-class relationships get a floor or an explicit documented no-op.** An
assertion on a relationship that legitimately inverts would crash
`DoorGates.at(0.5)` on every 1:100 page — the failure mode this section exists to
prevent, not to introduce.

**Asserted** (factor-independent — true at every factor, so a failure is a bug):

- `assert factor > 0`, matching `WallGates.at` verbatim.

**Floored** (a scaled value that would cross into a different physical regime):

- `DOOR_MIN_SIZE_PX = max(1.0, DOOR_MIN_SIZE_PX * factor)`, mirroring
  `WALL_MIN_THICKNESS_PX`'s `max(1.0, …)`. At the f = 0.25 clamp boundary the
  raw product is 5.0 px, so the floor is inert on the calibrated domain and
  exists only as a backstop.

**Same-class pairs — no check needed** (both endpoints carry the identical
factor, so the ordering is preserved arithmetically):
`DOOR_MIN_SIZE_PX < DOOR_MAX_SIZE_PX`,
`DOOR_SLIDE_PANEL_MIN_THICKNESS_PX < DOOR_SLIDE_PANEL_MAX_THICKNESS_PX`,
`DOOR_SLIDE_FLANK_GAP_MIN_PX < DOOR_SLIDE_FLANK_GAP_MAX_PX`,
`DOOR_SLIDE_PARK_BAND_MIN_TH_PX < DOOR_SLIDE_PARK_BAND_MAX_TH_PX`. This is the
`WALL_LATTICE_MIN_RUNG_LEN_PX` / `WALL_HATCH_MAX_LEN_PX` situation from findings
§4b — documented, not enforced.

**Cross-class inversion — a documented no-op, deliberately unchecked:**

`DOOR_FOLD_LEAF_LINE_SEP_MAX_PX` (P, 4.0) and
`DOOR_SLIDE_PANEL_MIN_THICKNESS_PX` (W, 3.0 × f) both describe the separation of
a drawn leaf's two edges, and at **f < 0.75 — i.e. every 1:100 sheet in the
corpus — the W value drops below the P one.** (corrected 2026-08-13: crossing
is at f≈1.33, above the operating range — the relation is monotone in range;
conclusion unchanged and strengthened) Nothing is asserted, floored or
clamped here, because there is no invariant to preserve: the two constants gate
**different detectors** over **different candidate populations** (folding's
`open_v` double-line leaves vs sliding's panel rectangles), they are never
compared to each other anywhere in the code, and §4's mm analysis shows they are
measuring genuinely different things (a symbolic line pair vs a built panel).
The inversion is a coincidence of numeric proximity at f = 1.0, not a
relationship.

It is recorded here for one reason: a future reader who notices the crossing
should find the reasoning already done, rather than "fixing" it with a clamp
that would silently widen the folding detector's window on every 1:100 page. The
plan carries a unit test pinning `DoorGates.at(0.5)` as constructing
successfully with the inverted pair, so nobody later adds that assertion.

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
- **Shrunk-world synthetics** (findings §7's pattern, corrected per §1): each
  door topology that owns a scaled constant — arc + anchored-line leaf
  (`DOOR_MIN_SIZE_PX`), sliding `leaf_pair` (`DOOR_SLIDE_PANEL_*_THICKNESS_PX`),
  sliding `parked_leaf` (`DOOR_SLIDE_PARK_BAND_*`), folding `open_v`
  (`DOOR_FOLD_JAMB_*`), double-leaf pairing (`DOOR_DOUBLE_LEAF_*`) — built at
  1:50, then rebuilt as a **faithful 1:100 export**: extents × 0.5, stroke
  widths unchanged, and **drawn ink separations held at their paper values**
  (leaf-companion offsets, fold double-line separations), because §2 measures
  those as paper-space on real 1:100 sheets. A blanket × 0.5 of every coordinate
  is what produced s01's four spurious residual misses (§1) and must not be the
  fixture transform. Assert `scale_factor=0.5` reproduces the f=1.0 detection.
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
3. Changes on the 1:100 sheets arrive only as REVIEW lines, and **the sweep's
   actual deltas match §6's predicted table** (≈3 new doors, ≈17 new windows,
   ≈2 new rooms across the seven 1:100 sheets; no confirmed loss anywhere). A
   material divergence from that prediction is itself a finding to investigate
   before the sweep goes to the user, not a result to hand over. The user
   verdicts the REVIEW lines; this branch never runs `tools/review.py`, never
   edits `tests/ground_truth/` or fixture bytes.
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
