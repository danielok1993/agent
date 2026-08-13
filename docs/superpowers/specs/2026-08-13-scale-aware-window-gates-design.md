# Scale-Aware Window Detection Gates — Design

**Date:** 2026-08-13
**Status:** Awaiting approval
**Companion:** `docs/scale-normalization-findings.md` — the corpus survey, the frozen
`WALL_*`/`ROOM_*` (§4) and `DOOR_*` (§4d) tables, the measurement protocol and its
traps (§4b, §4c). Predecessors: `2026-08-12-scale-aware-wall-room-gates-design.md`
(merged `48f19dd`), `2026-08-12-scale-aware-door-gates-design.md` (merged `06cda80`).

## Problem

`detection/windows.py` holds 27 `WINDOW_*` constants tuned on the 1:50 reference
sheets. `run_heuristics` receives `scale_factor` and forwards it to doors, walls,
rooms and both postprocess entry points — `detect_windows(page_data.paths)` at
`detection/orchestrator.py:48` is the last scale-blind call in the geometric
chain. `CROSS_WINDOW_THICKNESS_TOL_PX` (`detection/postprocess.py`) was left bare
by the doors branch, explicitly deferred to this one (findings §4d).

Corpus surface (baseline sweep 2026-08-13, post-doors-merge, post-verdict
commit `fd2fa2f`): **seven sheets run at f=0.5** (s05 s06 s07 s11 s12 s16 s18)
carrying **79 confirmed windows**, and **s13 runs at f=0.3666** with 11 more.
The mixed sheets s03/s17 currently resolve **f=1.0** (ink-dominant vote), and the
user's stored scales resolve s10/s20 to 1:50 — so the identity set is every sheet
except those eight, and it must stay byte-identical.

## Scope

**In:** classify all 27 `WINDOW_*` constants plus the window-side `CROSS_*`;
a `WindowGates` frozen dataclass; threading `scale_factor` into `detect_windows`;
the two blind-spot audits (unprefixed module constants, out-of-block literals).

**Out (recorded for findings §6):**
- `NMS_IOU_THRESHOLD` / `NMS_CENTER_DIST_PX` / `NMS_PROJ_PERP_MAX_PX` — shared
  cross-type suppression machinery in postprocess; scaling them moves every
  entity type at once and belongs to no single detector's branch.
- The span-overshoot FP lead (Evidence 6) — a *paper-space retune*, not a
  scale-awareness change; measured here, fixed elsewhere.
- The tuning-guide refresh: `docs/window-detection-tuning-guide.md` §4 is stale
  against the code (`WINDOW_CAP_MAX_LEN_PX` 34 vs 36; pre-rotation-general
  framing; §6 still says "diagonal not handled"). A `docs/window-guide-refresh`
  branch already exists; this branch does not touch the guide.
- Labels/schedules; per-scale-group detection for mixed pages (interim rule
  unchanged).

## Evidence base

All measurements ran through the real pipeline. Two mechanisms, both
§4c-compliant by construction rather than by after-the-fact reconciliation:

- **Distributions** came from inert measurement taps — extra `_meas` /
  `_meas_cross` evidence keys written by `detection/windows.py` /
  `detection/postprocess.py` and passed through `finalize_candidates` into
  `final_entities.json` — harvested from a full `tools/regress.py`-equivalent
  sweep. Inertness was verified: the tapped sweep reproduced the baseline sweep
  on every comparison key of every sheet. Taps are removed before any
  implementation commit; they never ship.
- **Variants** monkeypatched the module constants ×f and invoked
  `regression.sweep.sweep()` in-process — the harness IS the sweep. Self-checks:
  an unpatched variant run reproduced the baseline byte-for-byte on its three
  sheets, and the zero-delta V_cross run reproduced it on all eight.

144 confirmed windows were matched (type + IoU ≥ 0.5, the sweep's own matcher)
across four tiers: f10_50 = {s01 s02 s15 s10 s20} (n=30), f10_mixed = {s03 s17}
(n=24, excluded from tier ratios), f05 = {s06 s07 s11 s16 s18 (s12 n=0)} (n=79),
f037 = {s13} (n=11). The s12/s18/s13 ground-truth FP windows were harvested as a
separate population (n=36).

### 1. The organising rule — the INVERSE of doors

Doors: symbol extents scale (0.496), drawn ink separations do not (1.56).
Windows: **the symbol's internal ink geometry is paper-space; only the opening's
own empty-space extent scales.** Median-of-per-sheet-medians, f05 / f10_50:

| Quantity | 1:50 | 1:100 | ratio | reading |
|---|---|---|---|---|
| adjacent pane gap | 5.11 px | 3.00 px | 0.587 | paper **floor**, not scaling — see below |
| band depth (≥3-pane) | 10.00 px | 10.63 px | **1.06** | paper |
| cap stroke length (line caps) | 16.06 px | 17.62 px | **1.10** | paper |
| span overshoot (median) | 3.22 px | 3.00 px | 0.93 | paper |
| opening width | 79.28 px | 75.62 px | 0.95 | see below |

The pane-gap 0.587 is the doors leaf-companion signature in disguise: converted
to millimetres the 1:100 gaps are *larger* (3.00 px ≈ 51 mm) than the 1:50 ones
(5.11 px ≈ 43 mm), i.e. a minimum drawn separation, and no confirmed window
anywhere in the corpus draws a pane gap below 1.75 px. Band depth ≈ Σ gaps, so
depth and spacing land in the same class *together* — no ordering clamp needed.

Cap length is the subtle row: a 300 mm wall at 1:100 is 17.7 px, and the f05
sheets draw their jamb caps at exactly that (17.62 median) — cap ink spans the
frame-to-blockwork convention range at *full drawn size* on every tier, so the
px union of conventions does not shrink with scale.

Opening width's flat 0.95 ratio is a building-stock confound, not a paper
verdict: unlike door leaves (standard ~838 mm), real window widths vary 10×, and
1:100 sheets depict larger buildings. Width is the one quantity in the gate set
that is empty space between ink (jamb to jamb), not ink — geometrically
world-space by construction. What the distribution does show is the unscaled
floor already grazing real windows: the tightest confirmed f05 window is
**16.49 px vs the 14.0 gate** (s18), 2.5 px of headroom.

### 2. Retention vetoes — the confirmed extremes kill every W-candidacy but one

Censoring caveat: every harvested quantity is a survivor of its own gate, so
maxima locate the gate, and the *extremes vs the scaled gate* are the decisive
statistic, not the ratios:

| Gate | scaled @f=0.5 | confirmed evidence against scaling |
|---|---|---|
| `WINDOW_CAP_MAX_LEN_PX` 36 | 18 | caps **24.75 px** (s16 w0001, s11 w0002); at f037 caps 12.75–13.0 vs 13.2 — 0.2 px from loss |
| `WINDOW_MAX_WIDTH_PX` 280 | 140 | width **210.76 px** (s18 w0021); at f037 103.94 vs 102.65 — loses s13 w0009/0010 |
| `WINDOW_GLAZING_THICKNESS_PX` 16 | 8 | depth to **14.25 px** (s16/s11); s13 12.74–13.0 vs 5.87 — all 11 die |
| `WINDOW_GLAZING_ADJ_SPACING_PX` 8.5 | 4.25 | confirmed gaps at **8.25 px** (s16); s06 median 4.50 |
| `WINDOW_SPAN_OVERSHOOT_PX` 12 / `_COVER_TOL_PX` 4 | 6 / 2 | tails saturated at BOTH tiers (9.38 & 10.5 vs 12; 3.38 & 3.55 vs 4) |

### 3. The variant matrix — every verdict exercised end-to-end

Each variant ran the real sweep at each sheet's true factor (0.5; s13 at
50/136.40428…), compared against the same-day baseline. 90 = 79 + 11 confirmed
windows at stake:

| Variant (what ×f) | window kept | new REVIEW | FP delta | door/room damage |
|---|---|---|---|---|
| identity (nothing) | 90/90 | 0 | 0 | byte-identical self-check |
| **`MIN_WIDTH` only (the accepted set)** | **90/90** | **1** | 0 | **none** |
| both min floors (`MIN_WIDTH` + `CAP_MIN_LEN`) | 90/90 | 1 (same entity) | 0 | none — but 2× stage cost, see below |
| max gates (cap/width/glazing/mullion/block) | 40/90 | 34* | −24 | 2 confirmed rooms lost (s16, s13) |
| separations (eps/tight/pad/span) | 36/90 | 40* | −16 | room FP shape-swap only |
| `CROSS_WINDOW_THICKNESS_TOL_PX` | 90/90 | 0 | **0 — exact zero delta** | none |
| blanket (all 16 px + CROSS) | 29/90 | 39* | −31 | 2 rooms lost; gates interact (s07 loses 7 vs 1/0 in isolation) |

*Most "new REVIEW" windows under the destructive variants are shrunken
re-detections of the very windows counted lost (bbox collapsed to the band
alone, IoU < 0.5 vs truth) — churn, not recovery.

The blanket run is this design's central negative result: **−61 confirmed
windows**. The s12 phantom-window payoff it also shows (−16…−18 FPs) is real but
unreachable by scaling — the same gates that kill s12's phantoms kill 50
confirmed windows elsewhere. The one clean scaling win: the min-floor variant's
single new REVIEW window, **s16 (1337,1795,1354,1801) conf 0.67, width
11.6 px** — a real 1:100 window sitting below the unscaled 14 px floor. That is
the 21st-sheet argument in measured form.

The min-floor variant also exposed a perf trap, resolved by a follow-up
single-constant run: scaling `WINDOW_CAP_MIN_LEN_PX` (3.0 → 1.5) doubled the
windows stage on s16 (4.46 s → 9.11 s) and added 45%/88% on s18/s11 by flooding
the cap pool with tiny strokes, while contributing **zero** detection change
anywhere (the s16 REVIEW window's 6.0 px caps already cleared the unscaled 3.0
floor). The `MIN_WIDTH`-only variant reproduced the full result — 90/90 kept,
the identical REVIEW entity byte-for-byte, s13 strictly identical to baseline —
at ≤1.13× baseline cost (s16 5.04 s, s18 6.32 s, s11 3.87 s). Together with cap
ink's paper measurement (§1) this settles `CAP_MIN_LEN` as P.

### 4. Shrunk-world on s01/s02 — read for what it can and cannot say

The doors-spec exercise (coordinates ×0.5, region scope held): a run scaling
extent gates + glazing-band gates recovers every extent-dependent window on both
sheets and even zeroes s01's phantoms — but that is the **self-referential
trap** (doors spec §4): a ×0.5 shrink halves band geometry *by construction*,
while §1 measures real 1:100 exports holding it flat. Its honest yields:

- Every window whose detection rests on extents alone is recovered under scaled
  extent gates — corroborating `MIN_WIDTH`'s W.
- 9 of 11 residual misses under partial scaling are transform artifacts on
  paper-space separations (pane pairs collapsing under `DISTINCT_EPS` at halved
  gaps of 0.87–1.0 px that no real export produces — corpus-wide minimum 1.75 px).
- Scaling extent maxima while glazing stays paper produced MORE phantoms than
  scaling nothing on s02 (11 vs 5) — a fully-halved world punishes any partial
  set; on real exports the mechanism doesn't arise, but it is why this spec's
  synthetic fixtures use the faithful-export transform below, never a blanket
  shrink.
- One real interaction: `WINDOW_INTERIOR_BAND_PAD_PX` (P) at f=0.5 swept
  world-compressed neighbour ink into the clutter scan and killed one s02
  window on the shrunk page. No confirmed 1:100 window is clutter-rejected on
  the real corpus, so P stands, with a recorded revisit trigger: *a real 1:100
  window rejected by the interior-clutter gate*.

### 5. `CROSS_WINDOW_THICKNESS_TOL_PX` — P on mechanism, zero-delta measured

The tolerance compares bbox short side to measured wall thickness. Both are
world quantities, but the *mismatch* between them is cap-ink overshoot beyond
the wall band — the same drawn overshoot §1/§2 measure as paper (saturated span
tails at both tiers). Measured mismatch is bimodal at every tier (either ≈0 —
caps span the band exactly, the boost fires — or ≫6: medians 23.75 at f10_50,
9.38 at f05): there is nothing in the (3, 6] interval for scaling to flip, and
the variant run confirmed **exact zero delta** on all eight sheets. Frozen P;
`CrossGates` gains **no** new field, and the constant stays bare in
`postprocess.py` with a comment pointing at the findings row. (The window-side
scaled machinery that *should* scale — `_wall_runs_through`'s margin/band — is
already W inside `CrossGates` from the doors branch.)

### 6. FP leads measured here, deliberately not taken (findings §6 entries)

- **Span-overshoot tightening (paper-space retune):** confirmed windows
  overshoot ≤ 9.38 px (f05) / 10.5 px (f10_50); the s12/s18 phantom windows
  live at 11.75–11.98 px, just under the 12.0 gate. A retune to ~10.5–11 px
  could kill those FP families at zero measured confirmed cost. Needs its own
  verification pass (it changes 1:50 sheets too); out of scope here.
- **s12's 21 phantom windows** are killable by max-gate scaling only at the
  cost of 50 confirmed windows elsewhere — scaling is the wrong tool for that
  sheet's debt.

## Design

### 1. `WindowGates` (mirrors `WallGates`/`RoomGates`/`DoorGates`)

```python
@dataclass(frozen=True)
class WindowGates:
    factor: float
    WINDOW_MIN_WIDTH_PX: float

    @classmethod
    def at(cls, factor: float) -> "WindowGates":
        assert factor > 0, "scale factor must be positive"
        return cls(factor=factor,
                   WINDOW_MIN_WIDTH_PX=max(1.0, WINDOW_MIN_WIDTH_PX * factor))

WINDOW_GATES_UNSCALED = WindowGates.at(1.0)
```

One field. That is the measured truth of this detector, and the dataclass is
still the right vehicle: exact identity at f=1.0, the absent-field convention
("not a field" = "measured not to scale") made auditable in one place, and the
established threading discipline for whichever fields future evidence adds (the
block-cap/mullion revisit triggers land here if a 1:100 framed-window sheet
appears). The `max(1.0, ·)` floor mirrors `DOOR_MIN_SIZE_PX` (raw product
3.5 px at the f=0.25 clamp bound, so the floor is inert on the calibrated
domain — backstop only).

### 2. Threading

`run_heuristics` passes its existing `scale_factor`:
`detect_windows(page_data.paths, scale_factor=scale_factor)`. The entry point
keeps a defaulted scalar (`scale_factor: float = 1.0`) — the same contract as
`_cross_validate` / `_resolve_door_window_conflicts` (genuine identity default,
exercised directly by ~30 test call sites). Inside, gates are built once and
passed to the single helper that consumes the field, as a **keyword-only,
non-default** parameter (a missing hand-off must be a `TypeError`, findings
§4b): `_facing_cap_pairs(caps, *, gates)` (the `width < MIN_WIDTH` gate). No
other helper consumes a scaled constant, so no other signature changes; helpers
reading only P/D constants keep reading module globals. Production audit
surface: `detection/orchestrator.py:48` is the sole non-test caller.

Perf (the 8c7f378 caution): the one touched inner loop hoists
`gates.WINDOW_MIN_WIDTH_PX` into a local before iterating (locals beat the
module-global reads already there). Re-profile the windows stage on s16/s18
before/after threading at f=1.0 — expected parity; the variant timing already
shows the f=0.5 behavior change itself is cheap (s16 5.04 s vs 4.46 baseline,
s18 6.32 vs 6.12, s11 3.87 vs 3.61 — ≤1.13×, a measurement that includes the
scaled floor actually admitting more pairs). Rankings invert after each change
— measure, don't assume.

### 3. Classification (frozen; full table to findings §4e)

**Arithmetic check:** 27 `WINDOW_*` constants = 16 px-valued (**1 W + 15 P**) +
11 D. Window-side `CROSS_*` (additional): `CROSS_WINDOW_THICKNESS_TOL_PX` P,
`CROSS_WINDOW_ON_WALL_BOOST` D.

**W (1):** `WINDOW_MIN_WIDTH_PX` — the opening's empty-space extent (jamb to
jamb), the only non-ink quantity in the gate set; 2.5 px headroom at f05 today,
and the measured +1 REVIEW window at 11.6 px is the recovery it buys. Floored
`max(1.0, ·f)`.

**P (15 px + 1 CROSS):** the ink family. With their evidence classes:
- *Measured decisive* (scaling loses confirmed windows): `CAP_MAX_LEN` (24.75 >
  18; f037 margin 0.2 px), `MAX_WIDTH` (210.76 > 140; f037 103.94 > 102.65),
  `GLAZING_THICKNESS` (14.25 > 8; s13 wiped), `GLAZING_ADJ_SPACING` (8.25 at the
  gate; s06 median 4.50 > 4.25), `SPAN_OVERSHOOT`/`SPAN_COVER_TOL` (saturated
  both tiers), `CAP_MIN_LEN` (cap ink flat 1.10; scaling = 2× stage cost for
  zero retention gain), `TWO_LINE_MIN_CAP` (cap ink flat — 300 mm walls draw
  17.7 px caps at 1:100, so the unscaled 12 keeps discriminating; the only f05
  2-pane confirmed window has 17.77 px caps).
- *Mechanism + zero-delta measured:* `CROSS_WINDOW_THICKNESS_TOL_PX` (Evidence 5).
- *Semantic (CAD-precision / pen-adjacent ink), variant-corroborated:*
  `GLAZING_DISTINCT_EPS` (stroke-doubling collapse; px-valued despite no `_PX`
  suffix — flagged for the census-methodology note), `TIGHT_PAIR_GAP` (drawn
  legibility band, FP 1.6–2.5 vs true 1.75–3.5), `TIGHT_PAIR_JAMB_MARGIN` (sign
  test + noise floor; the true gate population is 3 windows, all 1:50),
  `INTERIOR_BAND_PAD` (pen-adjacent pad; shrunk-world revisit trigger recorded),
  `SPAN_PERP_TOL` (fit tolerance).
- *Conservative default, no corpus signal at any other scale:*
  `BLOCK_CAP_MAX_THICK` and `MULLION_GAP_MAX` — block-cap framed windows exist
  only on s02/s10/s03 (a drawing-house convention split, not a scale tier), so
  no cross-tier ratio exists even in principle on this corpus. P is
  retention-safe under both the world convention (~3 px bars / ~5.75 px gaps at
  1:100 — pass) and the paper convention (~6 px / ~11.5 px — pass), while
  W-scaling rejects the paper convention. Revisit trigger: **a 1:100 sheet
  drawing framed multi-light windows**.

**D (11):** `ANGLE_TOL_DEG`, `ANGLE_GRID_DEG` (angles); `CAP_LEN_RATIO`,
`CAP_ALIGN_OVERLAP`, `MIN_WIDTH_CAP_RATIO`, `BLOCK_CAP_MIN_ASPECT`,
`BLOCK_CAP_CROSS_RATIO` (ratios); `MIN_GLAZING_LINES`, `INTERIOR_SHAPE_MAX`,
`INTERIOR_OBLIQUE_MAX` (counts); `MIN_CONFIDENCE`.

**No densities/per-length rates exist in `WINDOW_*`** — the ÷f case
(`WALL_WEAK_MATERIAL_PER_100PX`) does not arise. Stated so nobody goes looking.

### 4. Hidden-constant audits (both §4b blind-spot classes)

**Unprefixed module constants:**
- `_GRID_PX` (64.0) — spatial-hash cell size, self-documented "not a tunable";
  trades cells visited vs records per cell, never which records pass. Layout;
  untouched.
- `_GLAZE_U_BIN_PX` = `SPAN_OVERSHOOT + SPAN_COVER` (16.0) — glazing-index bin.
  Correct at ANY width (the query iterates the full bin range); "at most two
  bins" is perf-only. Both parents froze P, so it stays a true module constant.
- `_CAP_V_BIN_PX` = `CAP_MAX_LEN + 4.0` (40.0) — **correctness-coupled**: the
  same-or-adjacent-bin pruning in `_facing_cap_pairs` is exact only while bin
  width exceeds the in-effect cap max. Had `CAP_MAX_LEN` been W, this bin would
  silently drop facing pairs at f>1 (caps to 144 px vs a 40 px bin inside the
  clamp domain) and would have had to be derived per call from gates. With
  `CAP_MAX_LEN` frozen P the hazard is vacuous at every factor — recorded here
  as an audit note precisely because a future W-reclassification of
  `CAP_MAX_LEN` MUST move this bin into the gates path in the same change.

**Numeric literals outside the constants block:** `crossed()`'s ±1.0 px bbox
slack, `_merge_mullion_chains`' ±2.0 px block-perp-in-gap slack — px-valued
fit slacks ≤4 px, implicitly P (the same class findings §4d froze for doors);
`_facing_cap_pairs`' `+1.0` float-rounding slack (rides beside `MAX_WIDTH`,
numeric); `1e-6` epsilons; confidence literals 0.62/0.05/0.10/0.90 and the
0→180° frame sweep (D). `_merge_mullion_chains` additionally reuses
`SPAN_PERP_TOL` and `GLAZING_DISTINCT_EPS` at its own call sites — those sites
inherit the constants' P verdicts.

### 5. Ordering invariants

Nothing to assert beyond `factor > 0` (matching every predecessor):
- `MIN_WIDTH×f < MAX_WIDTH` holds trivially across the clamp domain
  (14×f peaks at 56 px at the f=4.0 bound, far under 280).
- The depth/spacing coupling (`GLAZING_THICKNESS ≈ Σ gaps`) froze both P
  *together*, so their relationship is factor-independent by construction.
- `MIN_WIDTH×f` vs `MIN_WIDTH_CAP_RATIO` (D): the ratio gate compares width to
  cap length, not to the floor; no relationship to preserve.
The `max(1.0, ·)` floor is the only regime guard (§Design/1).

## Testing (rotation-general shrunk-world synthetics)

**The faithful 1:100-export transform, per the measurements:** shrink ONLY the
opening extent (width / overall placement); HOLD at paper values the pane
separations, band depth, AND cap stroke lengths (all measured flat-or-growing at
1:100 — a blanket ×0.5 produced 9 spurious misses and a phantom explosion in the
shrunk-world run and must not be the fixture transform). Every new fixture is
built at **50°** via the existing `_rot`/`diagonal_window` helpers — a non-grid
angle so perpendicular-distance and cap-alignment arithmetic is exercised off-axis
(the `_window_seal`/W11 lesson) — with an axis-aligned twin only where it pins a
distinct code path.

- **Identity (exact):** `detect_windows(paths, scale_factor=1.0)` equals the
  parameter-omitted call candidate-for-candidate (bbox + evidence) across the
  entire existing fixture suite; plus the full fast tier green, unchanged.
- **Negative control for the W row** (fails if threading is removed): a 50°
  window of width 10 px (3 panes at paper gaps ~2.5–3 px, caps ~5 px, satisfying
  `MIN_WIDTH_CAP_RATIO`): **missed** at f=1.0 (10 < 14), **detected** at f=0.5
  (10 ≥ 7). If a helper stops receiving gates, the f=0.5 assertion fails.
- **Paper-invariance controls, one per P family** (each fails if that family is
  wrongly scaled; all at 50°, extents shrunk, named quantity held at paper value):
  * gaps held at 8.25 px (`GLAZING_ADJ_SPACING`) — s16's convention;
  * band depth held at ~13 px (`GLAZING_THICKNESS`) — s13's convention;
    asserted on `glazing_lines == 3`, because a wrongly-scaled thickness
    truncates the band to its 2-pane suffix rather than always killing the
    window;
  * caps held at 22 px with width shrunk (`CAP_MAX_LEN`, `TWO_LINE_MIN_CAP` —
    fails if either scales: 22 > 18 scaled cap max would reject the jambs);
  * tight pair held at 1.75 px (`GLAZING_DISTINCT_EPS`, `TIGHT_PAIR_GAP`,
    `TIGHT_PAIR_JAMB_MARGIN`) — the s01 signature;
  * glazing overshoot held at ~9 px (`SPAN_OVERSHOOT`; and shortfall ~3.4 px for
    `SPAN_COVER_TOL`);
  * a framed multi-light twin with block thickness ~6 px and mullion gaps
    ~11.5 px held (`BLOCK_CAP_MAX_THICK`, `MULLION_GAP_MAX`).
- **CrossGates identity:** `_cross_validate` at f=0.5 with a synthetic network
  must apply the boost under the same 6.0 px tolerance as f=1.0 (pins the
  no-new-field decision).
- **TypeError enforcement:** `_facing_cap_pairs` without `gates=` raises.
- **Clamp-bound construction:** `WindowGates.at(0.25)` / `.at(4.0)` construct;
  the floor engages only below the clamp domain.
- Evidence continuity: the 50° fixtures assert `glazing_angle_deg` and
  `orientation: "diagonal"` are unchanged at f=0.5 (rooms' `_window_seal`
  consumes them — the s13 W11 history).

## Predicted sweep delta — what the user should expect to review

Measured directly by the accepted variant on the real pipeline at each sheet's
factor (not extrapolated):

| Sheet | f | window kept/new/gone | door | room |
|---|---|---|---|---|
| s05 | 0.5 | —/0/0 | 8/8 · 0 · 0 | unchanged |
| s06 | 0.5 | 8/8 · 0 · 0 | unchanged | unchanged |
| s07 | 0.5 | 10/10 · 0 · 0 | unchanged | unchanged |
| s11 | 0.5 | 27/27 · 0 · 0 | unchanged | unchanged |
| s12 | 0.5 | 0/0 · 0 · 0 (21 FP unchanged) | unchanged | unchanged |
| s16 | 0.5 | 23/23 · **+1 REVIEW** · 0 | unchanged | unchanged |
| s18 | 0.5 | 11/11 · 0 · 0 (12 FP unchanged) | unchanged | unchanged |
| s13 | 0.367 | 11/11 · 0 · 0 (3 FP unchanged) | unchanged | unchanged |

The single behavior change on today's corpus: **one new REVIEW window on s16 at
(1337,1795,1354,1801), conf 0.67, width 11.6 px** — the user verdicts it. Every
f=1.0 sheet (including mixed s03/s17 and stored-scale s10/s20) byte-identical.
A sweep diverging from this table is a finding to investigate before handover,
not a result to hand over. The sweep still exits 1 on the corpus's documented
pre-existing debt (findings §3 + baseline: s02 schedule-cache loss, s13's
walls-era lost door/rooms, s06/s12/s18 room debt, returned-FP inventories) —
that exit code is not this branch's regression and must not be "fixed" here.

This branch is correctness infrastructure plus one measured recovery; like the
doors branch, its visible payoff is deliberately small. The window-detection
wins that ARE available on this corpus (s12's phantom family, the span-overshoot
retune) are paper-space retunes recorded in findings §6 for their own branch.

## Rejected alternatives

- **Blanket-scale every px constant:** −61 confirmed windows across the eight
  non-identity sheets, 2 confirmed rooms, gate interactions (s07 loses 7 windows
  under blanket vs ≤1 under either subset alone). The central negative result.
- **Scale the extent maxima** (`CAP_MAX`/`MAX_WIDTH`/glazing band/mullion):
  −50 windows, −2 rooms; kills s12 phantoms only by killing 5× as many real
  windows.
- **Scale `CAP_MIN_LEN` alongside `MIN_WIDTH`:** zero additional retention or
  recovery (measured — the single-constant follow-up reproduced the identical
  result set), 2× windows-stage cost on s16 (4.46→9.11 s vs 5.04 s without it)
  from cap-pool bloat, and cap ink measures paper (1.10). Rejected on all three.
- **Skip the gates object because only one field scales:** the pattern is the
  audit trail — identity discipline, the TypeError contract, and the documented
  place future reclassifications (block/mullion triggers) land. A bare
  `min_width_px=` parameter re-opens the defaulted-argument blind spot §4b
  exists to close.
- **Geometry normalization:** rejected for the same silent-corruption reasons
  as every predecessor (findings §5).

## Acceptance criteria

1. `python -m unittest discover tests` green, including the new identity,
   negative-control, paper-invariance, TypeError, and clamp tests.
2. `python tools/regress.py`: no lost confirmed entity, no returned FP beyond
   the documented debt; every f=1.0 sheet byte-identical against the 2026-08-13
   baseline; the f=0.5/f037 sheets match the predicted table above exactly.
3. The measurement taps are fully reverted (working tree diff vs main touches
   only the intended implementation files); `graphify update .` run after code
   changes.
4. Findings doc gains §4e (this frozen window table, each measured row citing
   its evidence), the harness-by-construction note, and §6 entries:
   span-overshoot retune lead, NMS constants deferred, interior-band-pad and
   block-cap/mullion revisit triggers, tuning-guide staleness.
5. The sweep's REVIEW lines go to the user; this branch never runs
   `tools/review.py`, never edits `tests/ground_truth/` or fixture bytes.
