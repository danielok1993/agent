# W-gate iteration 3 — step 15: `_is_band_pocket`'s cover read on the pocket's OWN sides (faces at the standoff, wall solids' flat ends on it) — built, censused as implemented, swept: corpus identical, the s17 strips now held out by the ceiling alone

Branch `fix/band-pocket-tab-cover` from `fix/entrance-contact-run` (8468ce5: the
step-14 entrance-run rule plus its graphify chore; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups and
snapshotted for all 20 slugs (`outputs/regress_baseline/<slug>/2026-09-06_17-05-35`
… `17-06-57`) — **0 LOST, 68 returned FPs, 0 REVIEW**, s01 10/10 at its true
factor, the 88 verdict lines identical to step 14's after-sweep once sorted
(`tools/census_scratch/step15/sweep_base_verdicts.txt`). 2026-09-06.

## The brief

`_is_band_pocket` read the cover of each long edge of the component's MINIMUM
ROTATED RECTANGLE against `face_lines` at the barrier standoff
(`_edge_face_cover`, `ROOM_BAND_POCKET_FACE_COVER_MIN` 0.65). s17's four
reveal strips (rooms 0013/0014/0027/0032, entrance-less since step 14) carry a
31.5px tab where a perpendicular 35.5px band's flat-capped solid ends, so the
rectangle is pinned ON the face line and that edge's cover read 0 (0013
[0.0, 1.0], 0032 [0.0, 0.93], 0014 [0.0, 0.04], 0027 [0.0, 0.0]). Measure the
cover on the polygon's own long runs against the rectangle's edges, and
whether tolerating standoff 0 where a perpendicular band ends separates the
strips from the true class; build the reading that separates; note that the
strips still need the ceiling and that s11's 368mm storage lies inside the
false class's range.

## What the tab is (measured, `s17_tab_probe.py`)

The partition's paired segment — (593.04, 2189.67)–(911.92, 2189.67), th 35.5
for room_0013 — ends EXACTLY on the strip's face line x = 911.92. Its two
faces are drawn unequal: the top face (path 2701) runs from x = 718 across
the cavity wall to the wall's inner face at 948.67 and is the strip's END
barrier; the bottom face (path 2905) stops at 911.92, the outer leaf's inner
face line, which is itself drawn from the partition's far flank down (path
2697, y 2207.42–2332.67). The pair overlaps 718–911.92, so the segment's
flat-capped solid (`cap_style=2`: no extension past the centreline's end)
ends on the face line, the strip's boundary lies ON it over the partition's
thickness less two standoffs (35.5 − 4 = 31.5px) and 2px inside it
everywhere else. Nothing collinear ends within junction-snap reach of the
partition's centreline (the outer leaf is unpaired there — the cavity wall
is 36.75px, over the cap), so `_snap_intersections` leaves the end where the
ink put it. 0014 and 0027 carry the tab at BOTH ends (two partitions);
0014's tabs sit at opposite corners and tilt its rectangle 0.4°.

## The reading as built

`_side_wall_covers(comp, axis_edge, centre, face_lines, cap_lines)`: the
component's boundary runs parallel to the rectangle's long axis are classed
to a side by the sign of their offset from the rectangle's centre; for each
run `_run_wall_cover` returns the stretches lying along wall — the projected
extents of the faces parallel to it whose line sits at the barrier standoff
(`ROOM_LINE_BARRIER_PX` ± `ROOM_RECESS_BACK_TOL_PX`, read where the face
actually lies beside the run: at the middle of the overlap, interpolated
between the face's endpoint distances) and of the wall solids' flat ends
lying on it (`cap_lines`: every paired segment's end line across its
thickness, standoff 0 within the same tolerance); a side's cover is the
union of its runs' stretches projected onto the axis, over the axis edge's
length. `detect_rooms` builds `cap_lines` beside `face_lines` in the segment
loop and passes it through. The rectangle now gives only the axis and the
width (spacing = short side + 2 × standoff ≤ `WALL_MAX_THICKNESS_PX`,
unchanged). No constant moved.

Why the union over the side, not the largest single face (the old helper's
semantic) and not the sum of per-run covers: a face split by a text mask
covers a side in two pieces, and an L-shaped room has two parallel walls on
one side whose per-run sum exceeds 1.0 (the census's per-side sum reads
1.4–1.8 on s17/s15/s11 rooms; the shipped union cannot exceed 1.0). Why the
caps count: the tab IS wall-bounded — the partition's solid — and without
them a reveal shorter than 2.9 partition thicknesses (90px for one tab,
180px for two) would read under 0.65 on the tabbed side while a long one
reads over it, a length dependence with no drawing meaning.

## Census 1 — both populations, four readings (`cover_census.py`, all 20 sheets at their factors)

Every `_is_band_pocket` call (= every entrance-less, window-less component
past the filters and the recess rule) and every emitted room, read off
detect_rooms' own locals (`face_lines`, `door_barriers`, `wall_segments`):
`mrr` (the rectangle's edges, as before), `mrr_tol0` (the same with standoff
0 tolerated), `runs` (the polygon's own runs against faces), `runs_caps`
(the same with the caps — the reading built; the shipped numbers below are
`_side_wall_covers`' own, `zoom15.py`).

Every call at or under the 56px thick ceiling (11 of 58):

| sheet (f) | component | spacing | gt | rectangle (before) | own sides (now) |
|---|---|---|---|---|---|
| s17 (1.0) | (3434,2186)–(3579,2207) reveal | 25.25 = 214mm | unmatched, already dropped | [1.00, 1.00] | [1.00, 1.00] |
| s17 | room_0013 (912,2174)–(947,2331) | 38.75 = 328mm | recorded FP | [0.00, 1.00] | **[0.99, 1.00]** |
| s17 | room_0032 (914,2609)–(949,3061) | 38.75 = 328mm | recorded FP | [0.00, 0.93] | **[1.00, 1.00]** |
| s17 | room_0014 (3047,2174)–(3084,2489) | 38.79 = 328mm | recorded FP | [0.00, 0.04] | **[0.96, 0.99]** |
| s17 | room_0027 (3047,2594)–(3084,3061) | 40.50 = 343mm | recorded FP | [0.00, 0.00] | **[1.00, 1.00]** |
| s18 (0.5) | (2079,1023)–(2096,1068) kitchen-corner box | 21.25 = 360mm | recorded FP | [0.86, 1.00] | [0.86, 1.00] |
| s11 (0.5) | (1078,1597)–(1095,1704) **storage in utility** | 21.75 = 368mm | **confirmed** | [1.00, 1.00] | [1.00, 1.00] |
| s16 (0.5) | (2507,1323)–(2527,1401) partition box | 24.00 = 406mm | recorded FP | [1.00, 1.00] | [1.00, 1.00] |
| s12 (0.5) | (1842,472)–(1873,494) unit cell | 26.13 = 442mm | recorded FP | [1.00, 1.00] | [1.00, 1.00] |
| s18 (0.5) | (907,810)–(1079,833) strip under a sofa | 27.25 = 461mm | recorded FP | [0.14, 1.00] | **[0.90, 1.00]** |
| s12 (0.5) | (1842,530)–(1873,554) unit cell | 27.75 = 470mm | recorded FP | [0.94, 1.00] | [0.94, 1.00] |

Without the caps the strips' tabbed sides read 0.79 / 0.93 / 0.86 / 0.93
(the face over that fraction of the length, nothing over the tab); the
rectangle with standoff 0 tolerated reads the same 0.79–0.93 but by accident
of which end of the tilted rectangle's edge the face's p1 falls beside — a
reading of the rectangle, not of the strip. The s18 sofa strip is the one
other component the new reading raises over 0.65: a notch in its boundary
pinned its rectangle 2px off the run. The true class (187 confirmed emitted
rooms, all entered or wider than the thick ceiling): 65 read both sides ≥
0.65 on the rectangle, 124 on their own sides — a rectangle is pinned off
every bay, notch and pier — and none of the 59 that flip is under 599mm wide
or entrance-less at pocket spacing; the narrowest confirmed door-less,
window-less space between two faces is still s11's storage at 368mm, then
599–631mm on s20/s15/s07/s17/s08 (step 13).

Reading-vs-implemented check (`cover_census_after_*.json`): on the shipped
tree the tap's own reading and the rule's verdict agree on all 58 calls.

## Census 2 — the rule AS IMPLEMENTED at each ceiling (`ceiling_census.py`, 20 sheets, rooms diffed and scored)

The chain once as it stands, then once per ceiling with `_is_band_pocket`
handed a gates object whose `WALL_MAX_THICKNESS_PX` is the ceiling × f, for
the rule alone. No room moves or appears at any ceiling on any sheet; what
drops:

| ceiling (1:50) | newly dropped | score delta |
|---|---|---|
| 36 (as is) | — | 0 LOST / 68 FPs / 0 REVIEW |
| 40 | s17 strips 0013, 0032, 0014 (38.75–38.79px); 0027 at 40.5 stays | FPs 68 → 65 |
| 41 | all four s17 strips | FPs 68 → 64 |
| 44 | + s18's kitchen-corner box (21.25px at f=0.5) — and **s11's storage, confirmed, LOST** (21.75 against 22) | LOST 0 → 1, FPs → 63 |
| 48 | + s16's partition box (24.0) | LOST 1, FPs → 62 |
| 56 | + s12's two unit cells (26.13, 27.75) and s18's sofa strip (27.25) | LOST 1, FPs → 59 |

s01–s10, s13, s14, s15, s19, s20: nothing at any ceiling; s02 receives no
call. So the strips are held out by the ceiling ALONE now, and the ceiling
cannot move past 41 (347mm) without losing the storage — 41 keeps it by
21.75 / 20.5 = 1.06×, a knife-edge the skill's 1.5× rule forbids — until that
cupboard is recognised another way (it has no door drawn; door_0009 is the
utility's, 8.8px off, step 13).

## The sweep (four background groups, verdicts sorted section-wise)

**0 LOST, 68 returned FPs, 0 REVIEW** — the 88 verdict lines identical to the
baseline's. `tools/diff_room_polygons.py`: **all 20 sheets entity- and
polygon-IDENTICAL** (s01 at 0.542 and s02 at 1.0 among them), 0 changed
polygons, nothing added or removed, so no unsimplified diff was needed;
`compare_sweeps.py s17` / `s18`: no entity added or removed. Fast tier:
1441 tests green (`unittest_full.txt`); `TestBandPocketTabbedByAPerpendicularBand`
(s17's junction as drawn: the partition's near face across the cavity wall,
its far face to the inner face line, the inner face drawn from the far flank
on and paired beyond the reveal, nothing collinear within snap reach) reads
3 rooms with the detector reverted — the reveal (302,113.8)–(438,144) with
its 28px tab and the rectangle's bottom edge at cover 0.0 — and 2 with it.

## Pictures (this directory, plan crops only, none shows an address)

`step15_s17_reveal_strip_0013_tab_on_band_cap.png`,
`…_0014_tabs_at_both_ends.png`, `…_0027_tabs_at_both_ends.png`,
`…_0032_tab_at_the_far_end.png`, `step15_s18_sofa_strip_recorded_fp_notch_0.14_to_0.90.png`,
`step15_s11_storage_in_utility_confirmed_1.0_both_readings.png`. Red = the
component, blue = its minimum rotated rectangle; the long-side runs coloured
by what they lie along — green a face at the standoff, orange a wall
solid's flat end (the tab), grey neither; both covers in the caption. No
before|after pair: the sweep is identical.

## Residue / not in scope (one line each)

- The ceiling: 40.5px (343mm) for the last strip against 36; s11's storage at
  21.75px (f=0.5) inside the false range from 44 — its own step, after the
  cupboard is recognised.
- `_is_wall_recess` reads its back edge off the component's extent and fails
  on the same tab (a tab-less version of the fixture is dropped as a recess,
  the tabbed one is not) — its own iteration.
- The census's per-side reading sums per-run covers (can exceed 1.0 on
  L-shaped rooms); the shipped union cannot — the table-4 counts above are
  the census's, the strips' numbers the shipped helper's.
- The step-13/14 scratch scripts call the removed `rooms._edge_face_cover`;
  they document their own trees (step15/README.md).
- `tests/test_takeoff_fn_equivalence.py` ran inside the discover run (green).

## Numbers

lost **0** · returned FPs **68** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** (by construction: at the 36 ceiling the rule's population
is one already-dropped reveal) · s01 and s02 entity- and polygon-identical ·
all 20 sheets identical · the s17 strips read ≥ 0.96 on both sides and are
held out by the ceiling alone (three drop at 40, all four at 41) · **next**:
the band-pocket ceiling with s11's storage recognised another way (the
knife-edge at 41), then the queue (the s04 staircase, `_dimension_line_indices`
on s15's TEXT-layer lines, the s18 blind-window cap at 1:100, …).

**Decision needed**: ship the reading as built (commit code + test + prose +
the six PNGs + `tools/census_scratch/step15/`), or hold it — its corpus effect
today is nil, and its value is that the strips are now decided by one number
(the ceiling) instead of three.
