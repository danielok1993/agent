# W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves)

Branch `recal/w-gate-iter2`, 2026-09-04, on top of Group 1. Baseline: main
`f5682fc` (71 returned FPs, 0 LOST, 5 unreviewed).

## Outcome in one line

Two of the five moves ship (`WALL_WEAK_MATERIAL_PER_100PX` 3.0 → 2.2,
`CROSS_WALL_EXPAND_PX` 20 → 24 — both inert on the corpus at entity AND
polygon level); three were tried on the full corpus and reverted with the
false class each one admitted measured and pinned. Every census row that
carried a ⚠ ("discriminator, not number") broke on the sweep the moment its
number moved.

## The five moves

| constant | census | shipped | pre-check (harness, named sheets) | corpus sweep verdict |
|---|---|---|---|---|
| `WALL_MAX_THICKNESS_PX` | 36 → 40 | **36** (tried 40, reverted) | s11 16/16 rooms kept, +1 unreviewed; s16 −1 FP; s17 −4 FP | −5 recorded FPs, +3 phantoms, s01 and s02 outlines changed — see below |
| `WALL_FACE_MIN_LEN_PX` | 11 → 9 | **11** (tried 9, reverted) | s07 7/7, s12 8/8 unchanged; s18 −1 FP +1 unreviewed | s01 room_0003 edge jogged 4 px, s02 room_0004 −55 px², s18 worktop phantom |
| `WALL_WEAK_MATERIAL_PER_100PX` | 3.0 → 2.2 | **2.2** | s02 11/11; s11/s16 unchanged | inert alone (its one visible effect needed the 40 cap and the 9 floor too) |
| `ROOM_OPENING_SEAL_PX` | 12 → 15 | **12** (tried 15, 14, 13 — reverted) | s03 17/17 at 15 (the two known FPs stay out) | s15 lost two door swings at ≥ 14, s02 notched at 15, s01 room_0005 moved at 13–14 |
| `CROSS_WALL_EXPAND_PX` | 20 → 24 | **24** | s01/s18/s17 unchanged | inert |

## What each revert measured

**`WALL_MAX_THICKNESS_PX` 40.** The sweep at 40: 0 LOST, returned FPs 71 → 66
(s16 room_0020 at (2502,1563), s17 rooms 0013/0014/0027/0032 — the four
35 px-wide reveal strips in its 37 px = 313 mm cavity walls, whose outer and
inner faces pair as one plain band once the cap clears 37; pictures
`g2_s17_cap40_four_reveal_strips_removed.png`), but four new REVIEW rooms
(s11 (1030,1330)–(1123,1360): a wall-recess box on the party wall; s15
(1480,698)–(1595,792): a pocket between a hatched wall and annotation
leaders; s18 (156,724)–(197,827): a strip between boundary lines and tree
symbols; s18's worktop, below, was the face floor's) — all phantoms — and
111 room polygons moved. On the reference sheets, attributed by single-field
revert with the census harness and by `tools/diff_wall_network.py` against
the main worktree:

- s02 room_0008 (WC, IoU 0.862, −4,670 px², `g2_s02_cap40_wc_notched.png`):
  a new segment (1070.66,703)–(1070.49,839) th 38.25 — the WC's 1.5 px wall
  face (paths 5031/5037/5038) paired with a hairline basin edge (5743–5745)
  38.25 px away, and the band passed the material gate on two 13 px corner X
  symbols — one at each end of the 146 px band, 4 marks = 2.75/100 px (NOT the
  dashed section line, as first written here; corrected by iteration 3 step 1,
  which measured the marks). It needs all three of cap ≥ 38.25, floor ≤ 9 and
  density ≤ 2.7: reverting any one restores the WC.
- s01 room_0001 (kitchen, IoU 0.990, −1,397 px²): the kitchen units are
  38.5 px deep (600 mm at its true 1:92.2 — 70 px at a real 1:50). Their
  side stubs (paths 3183/3184, 14.2 px) paired at th 38.5 and their 38.5 px
  -pitch rows (939/940/946) were demoted as a lattice; the hob was fenced.
- Intermediate caps: s01 and s02 hold at 37 and 38 and break at 39; s16
  room_0006 breaks at 38 (IoU 0.862); s17's wins need ≥ 37.0. Thresholds
  0.25 px apart — no value in 36–40 is a reference. Prerequisites: a
  far-side density rule (shipped in iteration 3 step 1 as
  `_claims_far_side_sparse`; the mark-shape statistics could not separate) and
  s01's true-scale factor.

**`WALL_FACE_MIN_LEN_PX` 9.** With the cap back at 36: s01 room_0003's right
edge jogged 4 px into a hatched pier (IoU 0.975, `g2_s01_face9_hatch_jog.png`)
— `diff_wall_network` shows ten new 45° faces of 9.9–14.1 px in the 1.0 px
pen (paths 2568–2925), the hatch of s01's 7 px partitions (7√2 = 9.9 px);
the lattice rule demotes a 5-deep run but the band-end strokes paired into a
7.95 px diagonal segment. s02 room_0004 moved 55 px² the same way. On s18 the
4.5 px scaled floor fenced the kitchen worktop run (348×31 px at f=0.5 =
5.9 × 0.53 m; `g2_s18_face9_worktop_run.png`) as a 0.70 room while removing
one recorded FP at (172,1144): net 0. The census's false class was
axis-aligned strokes; diagonal hatch of thin bands lies between 9 and 11 on
both reference sheets. At a true 1:50 a 100 mm band's hatch is 16.7 px, so
this too is s01-at-identity.

**`ROOM_OPENING_SEAL_PX` 15/14/13.** A tail touches material within
`ROOM_PLUG_HALF_WIDTH_PX` (5) of its end, so the effective reach is
SEAL + 5 and any bbox edge whose ends fall within it of two walls qualifies
as an interrupted run — for a door with no derivable hinge edge that includes
its swing side (two synthetic fixtures sat at exactly 20 px clearance and
exposed the mechanism before the sweep did). Measured with the harness at
cap 36: 13 → s01 room_0005 IoU 0.957; 14 → s15 rooms 0019/0020/0023/0024
(the corridor and lounge lose their top-door swings, −5.4k px² each,
`g2_s15_seal15_*_swing_fenced.png`); 15 → s02 BEDROOM 2 notched around its
"A" section-marker bar (`g2_s02_seal15_section_marker_notch.png`). Only 15
also cleaned s04's bedroom (+10,345 px², `g2_s04_seal15_bedroom_improved.png`)
— an improvement lost with the revert. Prerequisite: a swing-side veto for
hinge-less doors. (CORRECTED by iteration 3 step 2, which measured each site:
none of these is a hinge-less swing-side plug — s15 is a dash-row barrier
crossing the doorway plane, s02 a fallback door's plug tails overshooting the
bar they shadow, s01 the plug cross-section fit flipping, and the s04
improvement a corner door lining the lining rule rejected, fixed at seal 12
— see `docs/w-gate-iter3-checkpoints/step-2.md`.)

## Fixtures moved (all documented in the tests)

The pier-tier fixture bulges to 44 px, the wall-recess breast front to 44 px,
the cavity-wall fixture to 44 px total (32 px reveal), the rejected-door
closet to 96 px wide and the white-ring symbol to 26 px end clearance — each
sat at the old 36 or at the 20 px tail-touch reach.

## Tests (fast tier)

| test | pins |
|---|---|
| `test_wall_network.TestFillClassRating.test_bare_band_at_38px_does_not_pair` | the 36–40 band stays corridor |
| `test_wall_network.TestFaceCollection.test_ten_px_hatch_stroke_is_not_a_face` (+ 12 px nib is) | the 9.9 px hatch class |
| `test_wall_network.TestWeakFacePairs.test_material_at_2_7_per_100px_qualifies` (+ 1.7 does not) | 2.2, fails at 3.0 |
| `test_room_detection.TestPlugSealReach` (11 sealed, 13 not) | 12 |
| `test_cross_validate.TestDoorPenalties.test_single_line_leaf_26px_from_centerline_is_in_wall` (+ 30 px no_wall) | 24, fails at 20 |

Full fast tier green except the three pre-existing failures.

## Sweep (final tree: cap 36, floor 11, density 2.2, seal 12, corridor 24)

| | lost | returned FP | REVIEW | polygons changed |
|---|---|---|---|---|
| baseline | 0 | 71 | 5 | — |
| G2 at census values | 0 | 66 | 9 | 111 (s02 WC 0.86, s01 kitchen 0.99, s15 ×4 …) |
| G2 cap 36, seal 12, floor 9 | 0 | 70 | 6 (+ s18 worktop) | s01 room_0003 0.975, s02 room_0004, s03/s05/s06 small |
| **G2 final** | **0** | **71** | **5 — byte-identical to baseline** | **0** |

`tools/diff_room_polygons.py`: 0 changed, 0 added, 0 removed; the only
entity delta corpus-wide is Group 1's s01 door_0012 bbox. No room-label
reseed needed.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 (the tried values reached −5 +3 and −1 +1; both reverted) · **next:
Group 3** (per-band hatch-mark cap then `WALL_THICK_MATERIAL_MAX_PX` 56;
`COLLINEAR_OFFSET_TOL` as paper-with-ceiling; `ROOM_PLUG_HALF_WIDTH_PX` paper
floor).
