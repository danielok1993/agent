# W-gate iteration 3 — step 13: `_is_band_pocket`'s spacing ceiling measured AS IMPLEMENTED on every sheet and NOT moved — the brief's premise fails on the true class and on its own target

Branch `recal/wall-max-thickness-40` (babe8d3: the step-4 measurement checkpoint
plus the twelve iteration-2 pictures; main is still `ee0f52f`). Baseline: this
tree's own sweep, re-run in four background groups and snapshotted for all 20
slugs (`outputs/regress_baseline/<slug>/2026-09-06_15-29-46` … `15-31-04`) —
**0 LOST, 68 returned FPs, 0 REVIEW**, s01 10/10 at its true factor, the 68
verdict lines identical to step 4's baseline (sorted; the groups ran in a
different order). 2026-09-06.

**No detection code was changed in this step.** `detection/` is byte-identical
to babe8d3. What changed: this report and ten PNGs, the
`ROOM_BAND_POCKET_FACE_COVER_MIN` comment, the CLAUDE.md gate paragraph, the
handoff, and scratch tooling under `tools/census_scratch/step13/`. There is no
"after" sweep because nothing moved; the with/without measurement ran through
the harness on the pipeline's exact inputs.

## The brief

Raise `_is_band_pocket`'s spacing ceiling from `WALL_MAX_THICKNESS_PX` (36px
= 305mm at 1:50) to `WALL_THICK_MATERIAL_MAX_PX` (56px = 475mm): "a strip
whose two long edges both lie on wall faces up to pier spacing apart is inside
that wall, not floor". Expected wins: s17's four cavity-wall reveal strips
(rooms 0013/0014/0027/0032, "held out by the 36 ceiling alone" per step 4) and
some of the 11 recorded-FP pockets on s11/s12/s16/s18. Must stay: s11's 19px
"storage in utility" (1078,1597)–(1097,1704), "which carries `door_0009` and
is never a candidate". Census first, the false side measured on at least two
sheets before the ceiling moves.

## Census 1 — every call the rule receives (`pocket_census.py`, 20 sheets at their factors)

A tap on `rooms._is_band_pocket` records every component that reaches it —
by construction every entrance-less, window-less free-space component that
survived the area / border / hole / erosion / contact / mass filters and the
recess rule — with the rule's own reading (text veto, minimum-rotated-
rectangle short side, spacing = short + 2 × `ROOM_LINE_BARRIER_PX`,
`_edge_face_cover` on both long edges against the exact `face_lines`), its
verdict at the current ceiling, and what the thick ceiling would do; then a
second run with the ceiling raised for this rule alone, rooms diffed and the
truth scored.

| | calls | under the cap (already dropped) | in (cap, thick] | of which both edges on faces, no text = **would drop** | over the thick cap |
|---|---|---|---|---|---|
| all 20 sheets | 54 | 1 (s17, a 21px strip) | 6 | **5** | 47 |

The five the raised ceiling drops, classed from the pictures:

| sheet (f) | component | short × long px | spacing | covers | what it is | ground truth |
|---|---|---|---|---|---|---|
| s18 (0.5) | (2079,1023)–(2096,1068) | 17.25 × 45 | 21.25px = **360mm** | 0.86 / 1.00 | a unit-end cell at the kitchen corner (`step13_s18_kitchen_corner_box_360mm.png`) | recorded FP — win |
| s11 (0.5) | (1078,1597)–(1095,1704) | 17.75 × 107 | 21.75px = **368mm** | 1.00 / 1.00 | the **storage in utility**, a 300 × 1800mm cupboard between the party wall and the utility partition (`step13_s11_storage_in_utility_confirmed_368mm.png`) | **confirmed — LOST** |
| s16 (0.5) | (2507,1323)–(2527,1401) | 20.0 × 78.5 | 24.0px = **406mm** | 1.00 / 1.00 | a boxed cell in a three-line partition beside the bathroom basins (`step13_s16_bathroom_box_406mm.png`) | recorded FP — win |
| s12 (0.5) | (1842,472)–(1873,494) | 22.1 × 31 | 26.1px = **442mm** | 1.00 / 1.00 | a kitchen unit cell between the unit front and the wall (`step13_s12_kitchen_unit_cell_442mm.png`) | recorded FP — win |
| s12 (0.5) | (1842,530)–(1873,554) | 23.75 × 31 | 27.75px = **470mm** | 0.94 / 1.00 | the next unit cell, with the sink (`step13_s12_kitchen_unit_cell_470mm.png`) — 27.75 against the 28.0 ceiling, a 0.99× knife-edge | recorded FP — win |

The sixth in-band component, s18's (907,810)–(1079,833) strip under a sofa
(462mm), is held out by its 0.14 cover. Score with/without: returned FPs 68 →
64 (s12 7 → 5, s16 10 → 9, s18 24 → 23), **LOST 0 → 1** (s11's storage), no
REVIEW line either way; s01 and s02 receive no call at all (every room on
both carries an entrance) and are entity- and polygon-identical.

## The must-stay is a candidate, and the brief's reason for it was wrong

`door_0009` (0.67, `single_line_leaf`, bbox (1102,1670)–(1147,1715)) is not
the storage's door. Its leaf stands vertical at x = 1102 and its one
qualifying plug is an INTERRUPTED plug on the bbox's BOTTOM edge — the
doorway is in the wall under the utility at y ≈ 1715, running x 1094.5–1154.2,
and the door swings up into the utility (`s11_storage_door.py`). That seal
lies 8.83px from the storage's boundary (contact tolerance 4px), so the
storage's `door_count` is 0 in the sweep's own record, it has no window and no
text (a vector-text sheet), and `_is_band_pocket` IS called on it today —
rejected only by the ceiling (21.75 > 18). It is a real cupboard drawn without
a door of its own: exactly the false side the brief asked for, and it lies
inside the band the brief would open.

## Census 2 — the false side: real door-less, window-less spaces between two faces

Every confirmed room the pocket rule sees, or would see if its sub-floor door
or window did not spare it (`entered_census.py` with `ENTERED_ALL=1`: the rooms
detect_rooms emits, read off its own locals, same features):

| sheet (f) | room | short px | spacing | covers | how it escapes today | margin to the 475mm ceiling |
|---|---|---|---|---|---|---|
| s11 (0.5) | storage in utility | 17.75 | 21.75px = **368mm** | 1.00 / 1.00 | the ceiling only | **0.77× — inside the band** |
| s20 (1.0) | passage (554,2812)–(948,2878) | 66.75 | 70.75px = 599mm | 1.00 / 1.00 | over the ceiling | 1.26× |
| s15 (1.0) | space (766,1549)–(833,1669) | 67.0 | 71.0px = 601mm | 1.00 / 1.00 | over the ceiling | 1.27× |
| s07 (0.5) | cupboard (454,190)–(486,290) | 32.0 | 36.0px = 610mm | 1.00 / 1.00 | over the ceiling | 1.29× |
| s17 (1.0) | (950,2209)–(1145,2278), a 0.35 door and a window | 68.25 | 72.25px = 612mm | 1.00 / 1.00 | its window (13.3k px² > the blind cap) | 1.29× |
| s08 (1.0) | "Heating" (1463,1060)–(1678,1131) | 70.5 | 74.5px = 631mm | 1.00 / 1.00 | text, and over the ceiling | 1.33× |

So the true class of narrow door-less spaces between two wall faces runs
from **368mm** (s11) and then 599–631mm on five sheets, while the false
pockets the ceiling would remove sit at 360, 406, 442 and 470mm — the true
class's narrowest member lies INSIDE the false class's range (368mm against
360mm, a 1.02× "margin" on the wrong side). Width between faces does not
separate a cupboard from a unit cell; only the door drawn into it does, and
this cupboard has none. By the brief's own rule ("must stay") and the
skill's ("a margin under 1.5× means the discriminator is wrong, not the
threshold") the number does not move.

## The expected win does not exist: s17's strips are not held out by the ceiling

`_is_band_pocket` is called on **none** of the four strips (three calls on
s17 in all, none in the band). Three things hold them out, the ceiling the
least of them (`s17_strip_openings.py`, `s17_strip_barriers.py`,
`s17_strip_edges.py`, `entered_census.py`):

1. **Entrance seals touch their ends.** Each strip ends where a doorway is cut
   through the cavity wall, and that doorway's 0.95 plug touches the strip:
   room_0013 ← door_0025's vertical plug (932,2331)–(942,2441) starting at the
   strip's bottom, contact 18px; room_0032 ← door_0036, 18px; room_0014 ←
   door_0002's horizontal plug (2934,2458)–(3049,2465) whose tail ends at the
   strip's left face, 15px; room_0027 ← door_0003, 18px (plus two sub-floor
   doors). `entrance_count` ≥ 1 on all four, so the rule is never consulted
   (`step13_s17_reveal_strip_0013_with_entrance_seal.png`,
   `…_0014_….png`, the seal in green).
2. **Their minimum rotated rectangles do not lie on the faces.** Each strip's
   long edges sit at the 2px standoff over 125–436px, but at the end where the
   perpendicular 35.5px band meets the cavity wall the polygon carries a
   31.5px tab reaching the face line itself (x = 911.9 against the face at
   911.9; the band's flat-capped solid ends there and the vertical face begins
   33px lower). The rectangle is pinned by the tab, its long edge lands ON the
   face (standoff 0, outside the 1.5px tolerance) and `_edge_face_cover` reads
   0: covers 0013 [0.0, 1.0], 0032 [0.0, 0.93], 0014 [0.0, 0.04], 0027
   [0.0, 0.0] — the band ends at BOTH ends of 0014/0027.
3. **The spacing**: 38.75–40.5px = 328–343mm, over the 36 cap and under 56.

Raising the ceiling alone changes nothing on s17. Removing the strips needs
the entrance semantics and the cover reading changed first, and then a
ceiling of at least 41px — which reopens s11's storage at 21.75px (f = 0.5)
unless that cupboard is recognised some other way.

## What does separate an entrance from a doorway cut across a strip (measured, not built)

The ENTRANCE gate reads "a confident seal within 4px of the boundary". A
doorway INTO a space is cut through one of its bounding walls, so its plug
runs ALONG that boundary over the doorway's width; a doorway cut through the
wall a strip lies inside of, or a neighbour's doorway whose tail ends at the
strip's face, merely touches the strip over its own plug width. Measured on
every emitted room of all 20 sheets (`entered_all_*.json`, `contact_stats.py`
— the room boundary's length within the contact tolerance of each entrance
seal, and per room the LARGEST such contact, because a neighbour's seal
grazes a real room's corner at 3.6–13px on s03/s17/s01/s15):

| class | largest entrance contact per room |
|---|---|
| every confirmed entered room, 17 sheets | ≥ 44.0px at 1:100 (745mm, s18), ≥ 67.2px at 1:50 (569mm, s03), ≥ 55.3px on s01 (863mm); medians 775–1482mm |
| s17's four reveal strips | 15–18px = **127–152mm** |
| s04's recorded-FP box (1463,1042)–(1558,1131) | 21.5px = 182mm |
| the other recorded-FP rooms with an entrance (s15, s17, s18) | 463–1138mm — real doorways along phantom cells |

Margin 3.7× between the true class's floor (569mm) and the strips (152mm). A
room's entrance is a seal running along its boundary over at least a leaf
width; a 15–18px touch is a doorway through the wall the strip is inside. That
is the first rule of the next iteration, not this one — one fix per step, and
it only makes the strips candidates; they then still need the tab-tolerant
cover reading and a ceiling the s11 storage survives.

## Pictures (this directory, plan crops only, none shows an address)

`step13_s11_storage_in_utility_confirmed_368mm.png` (the must-stay, in the
band; door_0009 in green is the utility's door, 8.8px below it),
`step13_s18_kitchen_corner_box_360mm.png`, `step13_s16_bathroom_box_406mm.png`,
`step13_s12_kitchen_unit_cell_442mm.png`, `step13_s12_kitchen_unit_cell_470mm.png`
(the four wins), `step13_s07_cupboard_confirmed_610mm.png`,
`step13_s20_passage_confirmed_599mm.png`, `step13_s15_space_confirmed_601mm.png`
(the false side over the ceiling), `step13_s17_reveal_strip_0013_with_entrance_seal.png`,
`step13_s17_reveal_strip_0014_with_entrance_seal.png` (the expected wins with
the seal that holds them out). Red = component bbox, blue = its minimum
rotated rectangle, green = the door bbox or seal named in the caption.

## Residue / not in scope (one line each)

- s11's storage cupboard carries no detected door of its own; its
  `door_count` of 1 in the takeoff record comes from the takeoff's grown
  polygon, not the room stage's 4px contact — the two disagree on this room.
- s12's second unit cell drops at 0.99× the ceiling; had the ceiling moved,
  that win would have been a coincidence of the 1:100 factor.
- The pocket rule's minimum-rotated-rectangle reading is sensitive to a
  single tab at a T-junction (s17's 31.5px tabs) — measuring cover on the
  polygon's own long runs, or tolerating standoff 0, is its own iteration.
- s18's (1835,2408)–(1900,2430) recorded-FP cell carries a 0.7 door along its
  full length (67px contact) — a phantom no entrance rule can touch.
- `tests/test_takeoff_fn_equivalence.py` not run (no detection change).

## Numbers

lost **0** · returned FPs **68** (unchanged — no code moved) · new REVIEW
lines **0** · net phantom delta **0** (the raised ceiling as implemented would
be −4 recorded FPs with the confirmed s11 storage LOST and s17 untouched) ·
s01 and s02 untouched · **next**: the entrance-contact rule (a seal counts as
an entrance only along ≥ a leaf width of the boundary; measured true ≥ 569mm,
false ≤ 182mm), then the tab-tolerant cover reading, then the queue
(`_dimension_line_indices` on s15's TEXT-layer lines, the s18 blind-window cap
at 1:100, …).

**Decision needed**: accept this as a measurement-only checkpoint (commit the
report, the ten PNGs, the prose notes and `tools/census_scratch/step13/`), or
direct the ceiling anyway with its measured trade (−4 phantoms, −1 confirmed
cupboard).
