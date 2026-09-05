# W-gate iteration 3 — step 7: `ROOM_OPENING_SEAL_PX` 12 → 15 (the retry), measured and shipped pending the user's decision

Branch `fix/seal-15-retry` from `fix/dash-rows-not-faces` (16a4835, which
carries steps 2, 3, 5 and 6; main is still `ee0f52f`). Baseline: that tree's
own sweep, re-run in four background groups and snapshotted for all 20 slugs
— **0 LOST, 68 returned FPs, 0 REVIEW** (the user's uncommitted verdicts on
s10's two windows, s17 room_0021 and s18 room_0000 are in the working tree
and count as confirmed; s15's garage and hall slice are already recorded).
2026-09-05.

**Decision (2026-09-05, same day).** Accepted as-is and committed: 15 is
the value, the stamp and tail strips below are the accepted price, and the
plane-restricted fallback stamp that makes the move free (and recovers the
12 px strips every plug-less door already paid, s17's confirmed SH/WC
among them) is queued as **step 8**, ahead of `_gate_denominator`. The
user's s10/s17/s18 verdicts went in as their own data commit.

## What the constant is, and why 15

`ROOM_OPENING_SEAL_PX` is the reach a door's evidence gets past its bbox: the
plug tails that seek the jambs the arc stopped short of, the dilated-bbox
fallback's stamp, the material window a plug is fitted in, the swing-dissolve
zone, the threshold-track distance in `_backed_extent`, and (via
`takeoff/openings.py::OPENING_ASSIGN_BUFFER_PX`) the takeoff's opening
assignment reach. W-class. The jamb gap beyond a swing bbox at true scales:
s01 8 px = 125 mm (1:92.2 — 12 was set on s01 as if 1:50, so at f = 0.542 the
6.5 px tail stops short of the hall door's jamb and the hall merges with the
living room, step 3), s17 8 px = 135 mm, s05/s07 6 px at f = 0.5 = 102 mm
(exactly the old scaled tail). 15 = 127 mm at 1:50 (150 mm at 1:100), covering
s01 at 1.0× and s05/s07 at 1.25×; s03's two recorded FP rooms return at 18.

Iteration 2 tried 15 and reverted; step 2 measured the two mechanisms that
broke it and steps 5/6 removed both at 12 (`_clip_plug_tails`,
`_dash_row_indices`). This step is the retry the handoff queued.

## Measurement first (`tools/census_scratch/harness.py`, seals 12/13/14/15 as multipliers of the tree's value)

| sheet (f) | 13 | 14 | 15 |
|---|---|---|---|
| s01 (1.0) | room_0003 +80, room_0005 −305 (the fit flip) | room_0003 +143, room_0005 −314 | **room_0003 +143 only** — the fit flip is inert at 15 |
| s02 (1.0) | identical | identical | identical at IoU ≥ 0.995; unsimplified: 9 rooms move, −386 / +294 px² |
| s03 (mixed) | room_0009 +721 | +718 | **+715** |
| s04 (1.0) | identical | room_0001 −355 | **room_0001 −539** |
| s15 (1.0) | identical | identical | room_0007 −85 |
| s17 (mixed) | room_0021 −180 | **room_0021 +8,978 (IoU 0.744)** | room_0021 −547, room_0012 −27 |
| s05, s07, s11 (0.5) | identical | identical | identical |
| s16 (0.5) | room_0002 −1,226, room_0006 −697 | −1,407 / −749 | −1,593 / −872 (simplified sweep: −257 / −127) |

No door or window entity changes at any seal on any sheet; no room appears
or vanishes. (A first pass of the pre-check set the seal as an absolute
pixel value and ran the f = 0.5 sheets at double reach — the table above is
the corrected, scaled run.)

## The three classes every move falls into (probe_box / probe_boxes on each site)

**(a) The plug-less dilated-bbox FALLBACK stamps `bbox ⊕ SEAL` in every
direction**, so at each such door the room on the door's plane side loses a
3 px strip (1.5 px at f = 0.5). Pre-existing at 12 (a 12 px strip), 3 px worse
at 15; the across-plane growth serves nothing — a swing bbox's hinge edge
lies on its wall face within `ROOM_PLUG_NEAR_PX`, never 15 px off it.

| site | door | why no plug | room loss at 15 (sweep, simplified) |
|---|---|---|---|
| s01 living room | door_0015, 0.65 double swing (310–420 × 356–410) | the piers stand 17.5 px past each bbox end (a 1,717 mm pair centred in a 2,264 mm opening); at 15 one sample touches, 1/7 of the anchor window | room_0001 −447 (`step7_s01_room_0001_double_swing_stamp_12_vs_15.png`) |
| s04 slider | door_0003, 0.65 sliding (7 × 141 px bbox in a 22 px band) | no edge profile qualifies | room_0001 −539, room_0002 −538 (`step7_s04_room_0001_slider_stamp_12_vs_15.png`) |
| s17 SH/WC (confirmed 2026-09-05) | door_0001, 0.83 single | its bottom edge's total cover sits at the 0.75 gate: `full` at 14, nothing at 12 and 15 | room_0021 −547 — the confirmed L-shaped outline IS the seal-12 stamp's edge (`step7_s17_room_0021_shwc_stamp_12_vs_15.png`); at 14 the room regains its swing square, +9,001 (`step7_s17_room_0021_seal14_swing_square_regained.png`) |
| s16 (f = 0.5) | two plug-less doors between rooms 0002/0006 | — | room_0002 −257, room_0006 −127 |
| s18 (f = 0.5) | four plug-less doors | — | rooms 0002/0003/0005/0007 −222/−90/−47/−51 |

Class total ≈ **−2.9k px² over 10 doors**.

**(b) A tail on continuing material is 3 px longer**, and where the plug
crosses a room's corner it notches 3 px × the plug width more. Two
sub-cases: a jamb or band running on past the reach (the drawn-through
plane — s02's sliding doors 0013/0014/0015, s15's fallback-tier plugs beside
room_0007), and a PARALLEL band inside the 5 px touch half-width that the
sample-trim reads as "touching" — s17 door_0016's doorway plug (0.95 single,
bottom edge y = 1298, in-material 0.23) hugs the wall 4 px below its spine and
runs 15 px into rooms 0001 and 0002 on either side (−26 each,
`step7_s17_door_0016_tail_corners_12_vs_15.png`); the phantom
`interrupted` plugs of fallback-tier bar doors (s17 doors 0088/0089, 0.05 in
material; s04 door_0006; s08 door_0003) do the same. The simplifier turns a
3 × 9 px stub into a slant over the whole edge, so the sweep's numbers
exceed the unsimplified ones (s15 room_0008 −210 simplified vs −19.4
unsimplified). Class total ≈ **−1.0k px²** (s15 −409, s17 −193, s10 −182,
s02 −62, s20 −48, s04 −37, s08 −29, s18 −13).

**(c) Sampling-phase knife-edges, both ways** — the profile's sample count
and phase change with the reach:

| site | mechanism | at 15 |
|---|---|---|
| s03 room_0009 | door_0008 (0.95 single): its LEFT-edge `interrupted` plug (0.29 in material — the open leaf's line, anchored by a wall stub above and the band below) drops, mid cover 1/6 → 2/7 > 0.25; the stub it tied to the band becomes an island the exported exterior swallows | **+715** (`step7_s03_room_0009_stub_island_12_vs_15.png`) — cosmetic: a phantom plug column gone, ~460 px² of wall stub counted as floor |
| s02 room_0000 (f = 1.0) | door_0005 (0.83 single, GD4): the full plug's cross-section fit falls to the full ±5 envelope (7 → 10 px, in-material 0.98 → 0.72) — the same "anchors disagree" knife-edge as s01 room_0005 at 13–14 | **−276** (`step7_s02_room_0000_door_0005_fit_flip_12_vs_15.png`) |
| s02 room_0001 | door_0018 (folding): the phantom `interrupted` right-edge plug (0.13 in material, 10 px) becomes `full` and fits to 5 px | +282 |
| s08 room_0000 | fallback doors 0011/0013 (0.35, 27 × 6 px boxes): their `interrupted` plugs (0.17 in material) no longer qualify | +179 net (four 8 × 8 corners regained) |
| s10 room_0002 | door_0010 (0.67 single_line_leaf): the top-edge plug's fit widens 4 → 7 px over 95 px | −445 |
| s17 room_0025 | door_0030's plug fit narrows 7 → 5.5 px | +125 |
| s01 room_0003 | doors 0003/0006's phantom `interrupted` plugs (0.09/0.14 in material) fit 1 px narrower | +143 |
| s05 room_0005 (f = 0.5) | door_0008's phantom plug fit narrows 0.4 px | +63 |

Class total ≈ **+0.8k px²**. Net over the 48 moved polygons: **≈ −3.0k px²**.

**s01 and s02 at f = 1.0 move**: s01 −304 px² (room_0001 −447 class (a),
room_0003 +143 class (c)); s02 −53 (room_0000 −276, room_0001 +282, six
rooms −1 to −31 in class (b)). The run's rule says they must not change
until `_gate_denominator` moves s01; this is the decision below.

## Change

`detection/rooms.py::ROOM_OPENING_SEAL_PX` 12.0 → 15.0 (comment rewritten
with the measured classes). `takeoff/openings.py` keeps
`OPENING_ASSIGN_BUFFER_PX = ROOM_OPENING_SEAL_PX` (17 px total reach from the
detected polygon; its comment updated). Tests:
`tests/test_room_detection.py::TestPlugSealReach` now pins **14 px sealed /
16 px not** (the 14-gap test fails at 12 — verified before the constant
moved; at 15, 15 px is a floating-point borderline on the 8 px hug and is not
pinned); `TestPlugTailTrim.test_tail_kept_on_through_material` builds its
through-band from the constant (it hard-coded ± 12);
`tests/test_takeoff_openings.py::test_reach_is_seal_only` places its doors
at reach ∓ 1 from `OPENING_ASSIGN_BUFFER_PX` (it hard-coded 211/213). Full
fast tier: 1,399 tests, OK.

## Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline snapshots)

| | lost | returned FP | REVIEW | doors/windows | polygons |
|---|---|---|---|---|---|
| baseline | 0 | 68 | 0 | — | — |
| **seal 15** | **0** | **68** (verdict lines byte-identical on all 20 sheets) | **0** | identical | **48 changed** on 13 sheets (`tools/diff_room_polygons.py`: s01 2, s02 8, s03 1, s04 3, s05 1, s07 1, s08 2, s10 6, s15 5, s16 3, s17 8, s18 7, s20 1), 0 added, 0 removed; s06/s09/s11/s12/s13/s14/s19 IDENTICAL |

Unsimplified check (scratch `unsimplified_seal.py`, `ROOM_SIMPLIFY_TOL_PX`
0, seals as multipliers) on every labelled sheet: the losses are exactly the
(a)/(b) strips above (s01 −424, s02 −386, s04 −1,116, s10 −622, s15 −97,
s16 −432, s17 −953, s18 −410, s20 −48, s07 −25, s08 −57, s11 −2; s05/s06/
s12/s13 none), no room is GONE or new anywhere.

Room labels reseeded on the 13 moved sheets (Gemini; the cache is keyed on
room geometry) and those sheets re-swept: verdict lines identical, the same
48 polygon moves, warning codes identical to the baseline's except s16, whose
baseline had been carrying a stale `ROOM_LABEL_NO_GEMINI` that the reseed
cleared (as s03's did in step 5).

Pictures in this directory: the seven `step7_*.png` named above plus
`step7_s04_side_by_side.png` (`compare_sweeps`); none shows an address.

## Residue / not in scope (one line each, each its own iteration)

- The dilated-bbox fallback stamps SEAL across the door's plane as well as
  along it; a plane-restricted stamp (SEAL along the bbox's wall-side edges,
  `ROOM_PLUG_NEAR_PX` across) would recover class (a) at 15 AND the 12 px
  strips every plug-less door already costs — s17's confirmed SH/WC outline
  is one of them.
- The sample-trim's "touching" test admits a parallel band 4 px off the tail's
  spine (s17 door_0016), so a doorway plug runs SEAL into the rooms on both
  sides of its jambs; a same-line requirement for the tail's supporting
  material is the class (b) fix.
- Profile knife-edges on the sample phase (s17 door_0001's bottom edge at the
  0.75 total-cover gate, s02 door_0005's fit fallback) — the profile is
  re-sampled from the extended edge's start, so the phase shifts with SEAL;
  anchoring samples at the bbox corners would make the gates phase-invariant.
- The exported room polygon drops interior rings, so a wall stub islanded by
  a vanished plug is counted as floor (s03 room_0009).
- s01's hall at its true factor was not re-measured here (`_gate_denominator`
  is unchanged and s01 still detects at identity); step 3 measured the seal
  as the hall's sole blocker at 0.542 and 15 × 0.542 = 8.1 px ≥ its 8 px gap.

## Numbers

lost **0** · returned FPs **68** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** (no entity appears or vanishes; **≈ −3.0k px² of outline
over 48 rooms**, −2.9k of it the fallback stamp's extra 3 px at 10 plug-less
doors, +0.8k from knife-edges; s01 −304 / s02 −53 at f = 1.0) · **next**: the
user's re-review of s01's three stair-split rooms (step-3.md), then
`_gate_denominator` (s01 at 0.542 must keep 11 doors, 4 windows and every
remaining confirmed room), then step 4 (`WALL_MAX_THICKNESS_PX` 36 → 40); the
plane-restricted fallback stamp is the iteration that makes this move free.

**Decision needed**: accept 15 as-is (the sweep is green; the cost is the
stamp/tail strips above, mostly pre-existing at 12 and 25 % deeper), accept
it only together with the plane-restricted fallback stamp (revert this branch
until that iteration lands, then retry — s01's true factor waits one more
step), or revert.
