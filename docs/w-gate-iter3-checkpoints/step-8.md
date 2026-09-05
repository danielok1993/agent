# W-gate iteration 3 — step 8: the plane-restricted fallback stamp (`_plane_stamp`), built, measured, and HELD as a patch — it costs one confirmed s18 room

Branch `fix/plane-restricted-fallback-stamp` from `fix/seal-15-retry`
(71ba420, which carries steps 2, 3, 5, 6 and 7; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups and
snapshotted for all 20 slugs — **0 LOST, 68 returned FPs, 0 REVIEW**.
2026-09-05.

**Decision (2026-09-05, same day).** The user looked at the before|after
("s18 still needs a lot of work, we can ignore patio for now — it's
outside the house") and asked for the change back: the patch is applied to
the tree again (`git apply`, its 7 tests pass, the room module's 113
green). The user then asked for the s18 `confirmed` entry
(2267,758)–(2511,802) to be retired: removed from
`tests/ground_truth/s18.json` through `regression.ground_truth.dump_truth`
(a 6-line deletion, nothing else moves; `tests/test_ground_truth_hygiene`
green), committed as its own data commit. Labels reseeded on
s01/s04/s16/s17/s18 after the re-apply (Gemini; warning codes identical to
the baseline on all five), and the re-sweep reads **s01 12/12, s04 5/5,
s16 17/17, s17 25/25, s18 13/13 — 0 LOST, 68 returned FPs, 0 REVIEW**.

**Status (as first written, before the decision).** The rule is built (code, 7 tests, prose) and swept on the full
corpus: verdict lines byte-identical on 19 sheets, 10 room polygons gain
+21.8k px² and none loses a pixel (checked unsimplified), 13 sheets
polygon-identical, s02 untouched — and **one confirmed s18 room vanishes**:
the 244 × 44 px strip at (2267,758)–(2511,802), a `"shape": "partial"`
verdict, which only the OLD stamp's far edge had fenced. The run's rule for
a lost confirmed entity is revert, report, stop: the working tree is back
to 71ba420's code and the complete change — `detection/rooms.py`,
`tests/test_room_detection.py`, the CLAUDE.md room-paragraph sentence and
the findings §4 row — is **`step-8-plane-stamp.patch`** in this directory
(`git apply docs/w-gate-iter3-checkpoints/step-8-plane-stamp.patch`
restores it; it applies cleanly to 71ba420). The decision is the s18
verdict, below.

## What the measurement said (scratch `plugless_census.py` / `analyze_census.py`, the harness at the tree's seal)

Every door the room stage sees on the 18 detecting sheets, its final seal
reconstructed exactly as `detect_rooms` builds it: **565 doors — 435 plugged,
112 fallback-tier with no evidence (no seal), 18 plug-less at the
dilated-bbox fallback.** Of the 18, **7 touch a room** (the other 11 — s14 ×8,
s10, s20 ×2 — sit where no room is detected):

| door | type | why no plug | wall-plane edge (my read) | edge off material (min / median, px) | jamb past corner (px) |
|---|---|---|---|---|---|
| s01 door_0015, 0.65 | garden pair, 110 × 54 | the piers stand 18 px past both bbox ends — outside the 15 px reach (start/end cover 0.29) | bottom, the one edge `_open_leaf_edges` leaves | 17.5 (the pier corner) / 44 | 18 / 18 |
| s04 door_0003, 0.65 | slider, 7 × 141 in a 22 px band | long edges middling: total 0.60 < 0.75, mid 0.32 > 0.25 | both long edges (`_sliding_end_edges` vetoes the ends) | 0.0 / 7.6 | 0 / 0 |
| s17 door_0001, 0.83 | single, hinge {bottom, right} | bottom total 0.73 < 0.75 (a drawn line along the threshold), mid 0.42; right (leaf) edge hugs the wall at 8.3 px | bottom = doorway, right = leaf | 0.0 / 2.2 · 0.0 / 8.3 | 0 / 0 · — / 0 |
| s16 doors 0003 / 0004, 0.67 (f=0.5) | two singles back to back in one 81 px opening, hinge {top,right} / {bottom,right} | each hinge edge has material at the hinge corner only | right (x=959, shared) | 0.0 / 18.7 | the next door's bbox |
| s18 door_0018, 0.67 (f=0.5) | single_line_leaf, hinge {bottom, right} | bottom edge 3.5–10 px off a parallel band; right end cover 0.75 with no start touch | right | 2.5 / 7.5 | 15.5 / 6 |
| s18 door_0271, 0.66 (f=0.5) | garden pair, 46 × 90 | left edge: material at the bottom corner only (top: none within 60 px) | left (the un-vetoed edge) | 0.7 / 17.6 | — / 0 |

**The true class** — the orientation rule measured on the corpus's plugged
singles (187, 181 with a derivable hinge): the kept plug lies on a hinge
edge **177 / 181** (the guard case 4 times); that edge sits ON its wall
face — **median 0.0 px, p75 0.3, max 4.2 px** off the dilated material —
inside the plug's own ±5 px cross-section; the interrupted plugs' jambs sit
**≤ 13 px** past the bbox corner (p75 0; s01 door_0015's 18 px piers are the
plug-less outlier); and the leaf-axis "open leaf" convention (plane = the
hinge edge PERPENDICULAR to the leaf's long axis) names the plugged edge
**159 times, the closed-leaf convention 5 times**, both 13 — 3 % wrong, so
the fallback must stamp BOTH hinge edges, never pick one. On the reference
tier: s01 7/7 singles on a hinge edge, s02 8/9 (the guard), s02 has no
plug-less door at all, s01 exactly one (door_0015).

**Convention** (stated before coding): a door's wall plane lies along a bbox
edge its own evidence has not ruled out — a single swing's plane passes
through its hinge corner (one of the two hinge edges; the far edges bound
the swing square, room floor), a slider's long axis IS its wall, a garden
pair's parked leaves and tip chord are floor — and a plug-less door is
sealed by stamping each such edge as the plug it would have carried had its
profile qualified: the edge line at the plug's half-width, with a SEAL tail
at each end. Across-plane growth beyond the plug's cross-section serves
nothing: the plane edge is on its face.

## Rule (`detection/rooms.py::_plane_stamp`, in the patch)

Called from the `elif c.confidence >= ROOM_BBOX_SEAL_MIN_CONFIDENCE` branch
in place of `box(bbox).buffer(SEAL)`. Plane edges = `{0,1,2,3} − skip_edges`
(the caller's `_open_leaf_edges | _sliding_end_edges`), intersected with
`_swing_hinge_edges` when derivable; a door pinning nothing keeps all four
(a ring whose interior dissolves as door floor under the existing swing-zone
rule). Each edge → spine ± SEAL tails, buffered by
`gates.ROOM_PLUG_HALF_WIDTH_PX` with flat caps. **Tails are trust-based
(the old stamp's along-reach) and hug-clipped**: `_tail_material_end` with
`ROOM_PLUG_NEAR_PX` (8, the profile's loose hug) as the envelope, not a
qualified plug's 5 px touch — no sample proved these jambs are in reach; a
tail is kept as far as wall material hugs its spine and ends where that
material ends: a doorway tail runs into its jamb (s01's piers: hugged at
13 px, `end = reach`), a leaf edge's hinge-end tail crosses the plane and
stops at the band's far face (no stub into the far room), and a tail hugging
nothing — the leaf's free tip — is dropped. No new constant. The stamp is a
subset of the old one everywhere, so a room can only gain floor.

Tests (`tests/test_room_detection.py::TestPlaneRestrictedFallback`, 7):
three through `detect_rooms` — a plug-less single whose bbox stops 18 px
short of both jambs and 2 px off its face still seals its doorway while the
far room keeps its floor 1 px past the band's standoff (the old stamp
reached 3 px further), the swing square rejoins its room, and a plug-less
7 × 124 slider in a 22 px band leaves both flanking rooms their floor at the
standoff — **all three fail on the current code for those reasons**
(verified before the function existed) — plus four on the geometry
directly: hinge edges only with full doorway tails and a dropped leaf-tip
tail, the hinge-end tail ending at the band's far face, the slider's slabs
inside the band, vetoed edges and the four-edge ring. Full fast tier with
the patch: 1,402 tests, one failure — `test_takeoff_fn_equivalence`'s
`warnings` field, which fails identically on the untouched tree (a
`TAKEOFF_REGIONS_UNCLASSIFIED` region-cache mismatch, the known flake).

## Harness pre-check (scratch `precheck.py`, s01/s02/s04/s16/s17/s18 vs the snapshots)

s01 room_0001 +1,431 px² (IoU 0.990, 2 doors → 2); s02 identical; s04
rooms 0001/0002 +1,511 / +1,544; s17 room_0021 **+8,478 at IoU 0.752**
(the SH/WC regains its swing square — above the 0.5 match, the growth the
brief predicted); s16 rooms 0002/0006 +3,847 / +380; s18 rooms 0002/0003
+3,724 / +466 — and s18 room_0007 (2267,759,2511,802) **GONE**, one LOST
line. `door_openings` unchanged on every matched room (the far room's count
comes from a 4 px contact test that a fitted plug on a thick band already
fails the same way).

## Sweep (`tools/regress.py`, four background groups, vs the baseline)

| | lost | returned FP | REVIEW | doors/windows | polygons (`tools/diff_room_polygons.py`, all 20) |
|---|---|---|---|---|---|
| baseline | 0 | 68 | 0 | — | — |
| **plane stamp** | **1** (s18 room @ (2389,780)) | **68** (identical) | **0** | identical | **10 changed, all gains, 0 added, 1 removed**; 13 sheets IDENTICAL incl. s02 |

The ten: s01 room_0001 +1,431 (f=1.0 — a decision, as in steps 5 and 7);
s04 room_0001 +1,511 (IoU 0.965), room_0002 +1,544; s16 room_0002 +3,847
(0.974), room_0006 +380 (0.979); s17 room_0021 +8,478 (0.752), room_0025
+395 (the room across door_0001's plane, the strip the old stamp bit
through the "removed" wall); s18 room_0002 +3,724 (0.956, the day room's
doorway swing), room_0003 +466, room_0005 +223. Unsimplified check (scratch
`unsimplified_stamp.py`: `ROOM_SIMPLIFY_TOL_PX` 0, the old stamp
monkeypatched back in, every labelled sheet): **lost 0 px² on every sheet**,
gains s01 1,431 / s04 3,009 / s17 9,030 / s16 4,225 / s18 4,196, twelve
sheets byte-identical, `door_openings` unchanged everywhere, the s18 strip
GONE.

## The LOST room, attributed (`step8_s18_door_0271_patio_strip_lost_before_after.png`)

s18 room_0007 is a 244 × 44 px (0.75 m deep at 1:100) strip between the
"4200 Overall Extension projection" dimension text and the new extension's
hatched cavity wall, on the PATIO side of that wall (the "Proposed privacy
fence to be the full depth of the patio" note sits above it, the
extension's interior with the "3900" dimension below). Its boundaries:
bottom, the cavity wall (real); right, the extension's end wall (real);
left, the existing house wall's stub under the doorway (real); top — for
x 2316–2511 the dimension text's vector-glyph outline rings (s18's black
fill class is rated wall by them, gap (b) in the CLAUDE.md room paragraph),
and for x 2267–2316 **door_0271's old stamp along its parked bottom leaf**
(bbox bottom 751.7 + 7.5 = 759, the recorded polygon's top edge at 757.7).
Nothing drawn bounds that 50 px except the parked leaf (excluded ink) and
the dimension line (excluded); with the parked-leaf edge no longer stamped
the strip opens into the pair's swing zone and the patio region, which is
no room (page-border / mass filters), so the strip vanishes with no
REVIEW line. It was recorded `partial`. My read: a patio sliver fenced by
annotation, a phantom whose verdict is stale — but the user judges chunks,
never the agent.

## s01's stair rooms at the true factor (the parallel decision, `step8_s01_stair_rooms_identity_vs_true_factor.png`)

Harness on the reverted tree, s01 at identity vs f = 50/92.2: doors 11/11,
windows 4/4 at both; rooms 12/12 → **8/12, 18 unreviewed**, the same four
lost as step 3 measured — (1090,699)–(1142,876), (466,920)–(521,1056) the
CPD cupboard, (1033,925)–(1142,1134), and the hall (392,922)–(521,1387).
The picture outlines the three stair-split rooms red and the hall orange on
both panels: at 0.542 the stair-arrow phantom bands are gone and the landing
+ flights + the strip beside the bathroom come out as ONE room, the CPD
cupboard opens into the hall, and the hall merges with the living room into
(209,412)–(521,1389) (6 doors). **Step 3's "the seal is the hall's sole
blocker" no longer holds on this tree**: at 0.542 the hall door door_0002's
right edge now takes an `interrupted` plug (seal 8.13 px ≥ its 8 px gap;
end cover 1.0, mid 0.0) — yet the hall still merges, through something other
than that doorway; `ablate.py s01 s01mode` before `_gate_denominator` moves,
as the brief already orders.

## Pictures in this directory (none shows an address)

`step8_s17_room_0021_shwc_swing_square_regained.png`,
`step8_s04_room_0001_slider_strip_regained.png`,
`step8_s01_room_0001_double_swing_strip_regained.png`,
`step8_s16_room_0002_plugless_pair_notch_gone.png`,
`step8_s18_room_0002_day_room_swing_regained.png`,
`step8_s18_door_0271_patio_strip_lost_before_after.png`,
`step8_s01_stair_rooms_identity_vs_true_factor.png`.

## Residue / not in scope (one line each)

- The leaf hinge edge of a plug-less single is stamped too (±5 px beside
  the open leaf) because the ink cannot say which hinge edge is the wall
  (159 : 5 on the corpus); on the seven sites it costs nothing visible.
- A jamb 23–31 px past the corner (past the hug envelope's reach, inside
  the 16 px free-space pinch of the old stamp's corner) would leak where the
  old stamp sealed; no corpus door sits there (true class ≤ 13 px, s01's
  outlier 18).
- Room labels were NOT reseeded (the rule is held; no polygon in the tree
  moved).
- The s01 hall at 0.542 leaks through an opening other than its door —
  measure with `ablate.py s01 s01mode` in the `_gate_denominator` step.

## Numbers

lost **1** (s18 room (2267,758)–(2511,802), a `partial` patio strip fenced
by the old stamp's parked-leaf edge — attributed above; **rule held as a
patch, tree reverted**) · returned FPs **68** (unchanged) · new REVIEW lines
**0** · net phantom delta **0 recorded / −1 by my read** (the lost strip is
a phantom if the user agrees; no entity appears) · outline: **+21.8k px²
over 10 rooms, nothing loses** (s17's confirmed SH/WC +8.5k at IoU 0.75;
s01 +1,431 at f=1.0, s02 untouched) · **next**: the user's verdict on the
s18 strip (retire it and `git apply` the patch, or keep the old stamp);
the user's decision on s01's three stair-split rooms from the picture
above; then `_gate_denominator` (re-measure the hall's leak first), then
step 4 (`WALL_MAX_THICKNESS_PX` 36 → 40).

**Decision needed**: (1) s18 room (2267,758)–(2511,802) — a chunk of the
patio, retire and apply the patch; or a real space, in which case the rule
needs a parked-leaf exception I would argue against. (2) s01's stair rooms
at the true factor: one landing room (what the truth notes ask for) and the
CPD cupboard merged into the hall — re-review, or keep the three verdicts.
