# W-gate iteration 3 — step 16: what makes s11's storage a space when a hollow wall is not — ENCLOSURE by wall bands at both ends (built, censused as implemented, swept: corpus identical) — and the band-pocket ceiling moved to `WALL_THICK_MATERIAL_MAX_PX` as a separate change (swept: −8 recorded FPs, 0 lost)

Branch `fix/band-pocket-ceiling-storage` from `fix/band-pocket-tab-cover`
(b052729: the step-15 reading plus its graphify chore; main is `83a603c`,
not the `ee0f52f` the prompt names — it moved at step 12's data commit).
Baseline: that tree's own sweep, re-run in four background groups and
snapshotted for all 20 slugs (`outputs/regress_baseline/<slug>/2026-09-06_17-51-*`
… `17-52-21`) — **0 LOST, 68 returned FPs, 0 REVIEW**, s01 10/10 at its true
factor, the 88 verdict lines byte-identical to step 15's after-sweep
(`tools/census_scratch/step16/sweep_base_verdicts.txt`). 2026-09-06.

## The brief

Find what makes s11's confirmed "storage in utility" (1078,1597)–(1095,1704),
368mm at f=0.5, a space when a reveal is not, measured on both classes — the
four s17 strips (328–343mm, recorded FPs), the recorded-FP cells at 360–470mm
(s18 ×2, s16, s12 ×2) and every confirmed room the rule would see if its
entrance did not spare it — along (a) a vector-text label inside, (b) what
lies BEHIND each bounding side, (c) whether the two sides could have paired
as one band, (d) anything else the pictures suggest; build the one that
separates with a margin, pin it, then move the ceiling to the value the
census supports as a separate change with its own with/without census.

## What the storage IS (measured, `s11_storage_probe.py`; picture 1)

The brief's premise — "a cupboard lies between TWO walls, each with its own
material on the far side" — fails on the drawing. The storage's LEFT side is
a 5.7px partition (paths 8387/8388, x 1069.8–1075.5, paired); its RIGHT side
is a single 1.5px line (path 8383, x = 1097.2, y 1595–1706) with the utility
behind it — the cupboard's FRONT, drawn in the wall pen: the s02 "coats"
class, which keeps its lone-face barrier rights here because 21.75px from the
partition's flank is over the 1:100 cap (18px), so it never pairs and the
far-side rule never demotes it. What closes it is the 6px band above (paths
8346/8347, y 1589–1595) and the 17.6px external wall below (8333/8335, y
1706–1723.6).

## What the s17 strips ARE (measured, `s17_strip_lines.py`; pictures 2–3)

Not a reveal whose leaf lines stop. Around strip 0013 (912–947, y 2174–2331)
the vertical lines are: x = 911.92 path 2697 (y 2207–2333, lone) and 2698
(2451–2501, lone) — the strip's left face, drawn from the partition's far
flank to the doorway and resuming below it; x = 948.67 path 2756 (2172–2333,
paired with the 17.5px nib 948.67–966.17 on the ROOM side) — the right face;
and below the doorway the 11.75px pair 2753/2754 at x 948.67–960.42, again on
the room side of 948.67. No paired segment's flank is collinear with either
face with its band on the strip's side at ANY reach (`near_seg_gap` None on
all four strips, against 2.0px on both faces of the 25.25px reveal at
(3434,2186), whose cavity pair and inner leaf resume 2px past its end). The
strips are a 313mm wall drawn HOLLOW — two lines with rooms on both sides,
the existing-wall outline convention — from the partition's face to the
doorway's jamb line.

## The four readings on both classes (`backing_census.py`, all 20 sheets at their factors; `summary16.md`)

Every `_is_band_pocket` call at or under 56 × f (11 of 58), read off
detect_rooms' own `face_lines` / `cap_lines` / `solids` / `network`:

| sheet (f) | component | spacing | ground truth | (a) inside | (b) solid behind each side | (c) pens | covers | **(d) end closures** |
|---|---|---|---|---|---|---|---|---|
| s17 (1) | (3434,2186)–(3579,2207) reveal, dropped today | 25.25 = 214mm | unmatched | none | 0.00 / 1.00 (11.2px behind one) | same | 1.00 / 1.00 | **0.00 / 1.00** |
| s17 (1) | room_0013 (912,2174)–(947,2331) | 38.75 = 328mm | recorded FP | none | 0.12 / 0.21 (tabs) | same | 0.99 / 1.00 | **0.00 / 0.34** |
| s17 (1) | room_0032 (914,2609)–(949,3061) | 38.75 = 328mm | recorded FP | none | 0.08 / 0.11 | same | 1.00 / 1.00 | **0.14 / 0.34** |
| s17 (1) | room_0014 (3047,2174)–(3084,2489) | 38.79 = 328mm | recorded FP | none | 0.16 / 0.20 | same | 0.96 / 0.99 | **0.00 / 0.00** |
| s17 (1) | room_0027 (3047,2594)–(3084,3061) | 40.50 = 343mm | recorded FP | none | 0.10 / 0.11 | same | 1.00 / 1.00 | **0.00 / 0.00** |
| s18 (0.5) | kitchen-corner box (2079,1023)–(2096,1068) | 21.25 = 360mm | recorded FP | none | 0.00 / 0.04 | same | 0.86 / 1.00 | **0.00 / 0.29** |
| **s11 (0.5)** | **storage in utility (1078,1597)–(1095,1704)** | 21.75 = 368mm | **confirmed** | none (0 of 696 glyph strokes) | 0.00 / 1.00 (5.1px behind one) | same | 1.00 / 1.00 | **1.00 / 1.00** |
| s16 (0.5) | partition box (2507,1323)–(2527,1401) | 24.00 = 406mm | recorded FP | none | 0.00 / 0.00 | same | 1.00 / 1.00 | **1.00 / 1.00** |
| s12 (0.5) | unit cell (1842,472)–(1873,494) | 26.13 = 442mm | recorded FP | none | 0.09 / 1.00 | different | 1.00 / 1.00 | **0.00 / 1.00** |
| s18 (0.5) | sofa-back strip (907,810)–(1079,833) | 27.25 = 462mm | recorded FP | none | 0.00 / 0.00 | same | 0.90 / 1.00 | **0.00 / 0.72** |
| s12 (0.5) | unit cell (1842,530)–(1873,554) | 27.75 = 470mm | recorded FP | none | 0.00 / 1.00 | same | 0.94 / 1.00 | **0.00 / 1.00** |

- **(a)** fails: no text span and no vector-text glyph stroke lies inside
  any call on the corpus (s11 draws 696 glyph strokes; "UTILITY" is in the
  utility). The rule's text veto has nothing to extend to.
- **(b)** fails: the storage has a wall solid behind ONE side (the
  partition, 5.1px) and nothing behind its front line — exactly the 25.25px
  reveal's reading (the outer leaf behind one side), and the s12 cells' too.
  The strips have none behind either side (the tabs' 0.1–0.2 is the
  perpendicular partition's solid behind the cap stretch).
- **(c)** fails: every face in play on s11 and s17 is the one black 1.5px
  pen; only s12's 442mm cell mixes pens (a unit line).
- **(d) separates**: the storage is closed by wall BANDS at both ends
  (1.0 / 1.0); every pocket and every recorded-FP cell but one has an end
  closed by a line, an opening or nothing (max of the min 0.34 on the
  strips, 0.0 on the reveal, ≤ 0.29 on the cells). The exception is s16's
  partition box, enclosed 1.0 / 1.0 — a cell between paired partition
  lines, which stays as it does today. On the whole corpus 17 of the 58
  calls are enclosed at both ends, 15 of them wider than 56 × f (the rule
  never sees them), and of the 187 confirmed emitted rooms 77 are enclosed
  and 110 open-ended — entered rooms have doorways at their ends.

The confirmed door-less rooms at or under 72 × f (the true class, pictures
4–5): the storage (1.0 / 1.0) and then s20's passage (554,2812)–(948,2878)
599mm **0.00 / 1.00**, s15's space (766,1549)–(833,1669) 601mm **1.00 / 0.50**,
s07's cupboard (454,190)–(486,290) 610mm **0.06 / 0.06** — a box of lone
lines with a single front line like the storage's, its ends single lines
too. So enclosure recognises the fully WALLED cupboard, not every door-less
space; the other three are held out by the spacing ceiling alone.

## The rule as built

`_end_closures(comp, end_edge, centre, solids)`: the component's boundary
runs parallel to the rectangle's SHORT edge are classed to an end by their
offset from the centre; each run is probed `ROOM_BAND_POCKET_END_PROBE_PX`
(7px) outward — past the 2px line barrier a lone face keeps around itself,
inside the solid of any band behind the face (dilated 2px past it, spanning
its thickness beyond; 6 and 7 read identically on every component) —
against the stage's `solids` (segments, fills, white walls, bridges, jamb
rings), and an end's closure is the union of its runs' solid-backed
stretches projected on the edge over its width. `_is_band_pocket` takes
`solids=` and, after the covers pass, returns False when BOTH closures are
≥ `ROOM_BAND_POCKET_END_CLOSURE_MIN` (0.65, the family's "mostly" threshold:
1.54× under the storage, 1.88× over the strips). The convention: walls meet
at junctions where one STOPS at the other's face, so a wall band never
stands across another wall's thickness — a pocket inside a wall is closed
at its ends by the wall's own interruptions (an opening's jamb line, a face
drawn across the wall, a partition's face continuing across), while a
component with a band standing across each end is a cell of the wall grid.

Pinned by `TestBandPocketEnclosedByWallBands`: a 26px cupboard between an
8px partition and a 6px front panel (a lone front line 30px from the
partition would pair with it at 1:50 and be demoted by the far-side rule —
the s02 "coats" treatment — where s11's front keeps its rights because
21.75px is over the 1:100 cap), closed by 8px bands, stays; the same cell
closed by lines with a 10px jamb nib on each end (0.38) is dropped. Both
bite: the banded cupboard fails with the detector reverted (dropped as a
pocket), the nibbed hollow wall fails at a 0.3 floor. 1443 tests green.

## Census as implemented and the sweep of the exemption alone (ceiling 36)

`ceiling_census16.py` — the chain with the exemption ON and OFF at ceilings
36 / 40 / 41 / 44 / 48 / 56 (× f) for the rule alone, all 20 sheets: at 36
the rule's population is the one already-dropped reveal (0.0 / 1.0, still a
pocket), so the exemption is inert; s01–s10, s13, s14 show nothing at any
ceiling. Corpus sweep with the exemption at 36 (four background groups):
**0 LOST / 68 returned FPs / 0 REVIEW, the 88 verdict lines byte-identical
to the baseline, `diff_room_polygons.py` all 20 sheets entity- and
polygon-IDENTICAL** (s01 at 0.542, s02 at 1.0 among them).

## The ceiling — the separate change (`rooms_step16_ceiling.diff`)

`_is_band_pocket` reads `WALL_THICK_MATERIAL_MAX_PX` (56px = 475mm at 1:50,
28px at 1:100, 20.5px at s13's 1:136) from a new `RoomGates` field scaled
exactly as `WallGates` scales it, in place of `WALL_MAX_THICKNESS_PX`: two
faces that could have paired as one wall, plain or thick. The as-implemented
census (`ceiling_census16.py`, exemption ON and OFF, every sheet at its
factor; rooms diffed and scored):

| ceiling (1:50) | exemption ON: newly dropped | exemption OFF: newly dropped | score (ON) |
|---|---|---|---|
| 36 (as is) | — | — | 0 LOST / 68 FPs / 0 REVIEW |
| 40 | s17 strips 0013, 0032, 0014 | same | FPs 65 |
| 41 | + s17 strip 0027 (40.5px) | same | FPs 64 |
| 44 | + s18's kitchen-corner box (21.25px at f=0.5) | same, **+ s11's storage LOST** | FPs 63 |
| 48 | nothing more | + s16's partition box (enclosed) | FPs 63 |
| **56** | + s12's two unit cells (26.13 / 27.75), s18's sofa-back strip (27.25) | same | **0 LOST / 60 FPs / 0 REVIEW** |

No room moves or appears at any ceiling on any sheet; s01–s10, s13, s14,
s15, s19, s20 show nothing. The corpus sweep at 56 (four background groups,
verdicts sorted section-wise): **0 LOST, 60 returned FPs, 0 REVIEW** — the
eight lines that vanish are s17's four strips (929,2252) (931,2838)
(3064,2331) (3065,2828), s18's (993,821) and (2087,1046), s12's (1857,483)
and (1857,542), every one a recorded false positive; the 20 per-sheet count
lines are identical to the baseline's; `diff_room_polygons.py`: **0 changed
polygons, 0 added, 8 removed**, s01 at 0.542 and s02 at 1.0 identical, so no
unsimplified diff was needed; `compare_sweeps.py` s17 / s18 / s12: 4 / 2 / 2
removed, nothing added (pictures 11–13); s16 and s11 unchanged (s16's
enclosed box stays, the storage stays).

Verdicts on the eight, from the pictures: the four s17 strips are the
hollow-drawn wall — wins for the right reason; s18's kitchen-corner box is a
hollow junction cell in the wall grid, closed by a lone line — a win;
s12's two unit cells (0.93× and 0.99× the scaled 28px ceiling) and s18's
sofa-back strip (0.97×) are FIXTURE cells against a wall, not wall
material — the rule's premise is false for them and they drop by a
coincidence of the 1:100 factor. Net phantoms **−8**, three of them for the
wrong reason; a fixture-cell rule would own those (queue).

**The margin, stated plainly.** With enclosure protecting the storage, the
true class the ceiling must clear is the other confirmed door-less spaces —
boxes of lone lines at 599 / 601 / 610mm — and the false class tops out at
343mm: 475mm sits 1.38× over the strips and 1.26× under s20's passage, and
NO ceiling clears the skill's 1.5× both ways (that would need ≥ 515mm and
≤ 399mm at once). 56 is the walls' own thick-tier cap — the width up to
which two faces pair as one wall with material — not a measured midpoint;
the exposure it opens is a missed-door cupboard 305–475mm deep drawn with
wall-pen faces and a single line at one end (the corpus has none; standard
cupboards are 450–600mm deep, so the 450s sit inside it). Pinned by
`TestBandPocketCeilingAtTheThickTier` (the hollow wall at s17's 38.75px face
spacing fails on the 36-ceiling tree — the bite check, taken before the
change; the walled cell at the same spacing stays; the storage's own 1:100
topology with a lone front line stays) and
`TestRoomGatesConstruction::test_wall_thick_material_max_matches_wallgates_scaling`.
Fast tier: 1449 tests, the only failure the known label-cache flake in
`test_takeoff_fn_equivalence` (green on its own re-run).

## Pictures (this directory, plan crops only, none shows an address)

1. `step16_s11_storage_confirmed_partition_and_lone_front_line_bands_at_both_ends.png`
2. `step16_s17_hollow_wall_strip_0013_jamb_line_and_partition_face_ends.png`
3. `step16_s17_hollow_wall_strip_0014_rooms_on_both_sides.png`
4. `step16_s07_cupboard_confirmed_610mm_lone_line_ends.png`
5. `step16_s20_passage_confirmed_599mm_one_end_open.png`
6. `step16_s17_reveal_25px_leaves_resume_one_end_dropped_today.png`
7. `step16_s16_partition_box_406mm_recorded_fp_enclosed_stays.png`
8. `step16_s12_unit_cell_442mm_recorded_fp_one_end_open.png`
9. `step16_s18_sofa_strip_462mm_recorded_fp_door_seal_end.png`
10. `step16_s18_kitchen_corner_box_360mm_recorded_fp_lone_line_end.png`
11. `step16_s17_four_hollow_wall_strips_removed_ceiling_56.png` (compare_sweeps)
12. `step16_s18_kitchen_box_and_sofa_strip_removed_ceiling_56.png` (compare_sweeps)
13. `step16_s12_two_unit_cells_removed_ceiling_56.png` (compare_sweeps)

In 1–10: red = the component; blue = wall SEGMENT solids, light blue =
fills / white walls / jamb rings; green = a paired face, orange = a lone
face; magenta = a door seal, cyan = a window seal.

## Residue / not in scope (one line each)

- The exemption recognises the fully walled cupboard only; s07/s20/s15's
  door-less spaces are held by the ceiling at 1.26–1.29× — a missed-door
  cupboard under 475mm with a lone-line end is the exposure.
- s12's unit cells and s18's sofa strip drop for the wrong reason (fixture
  cells, 0.93–0.99× the scaled ceiling) — a fixture-cell rule's class.
- s16's partition box (406mm, enclosed by paired partition lines) stays a
  recorded FP — a cell between two partitions, the recess/duct class.
- A hollow cavity between two paired leaves wider than 8px would now read
  enclosed at a resuming leaf's caps only if BOTH ends are caps; the
  recess rule catches the collinear-gap form first (no corpus instance).
- `_is_wall_recess` reads its back edge off the component's extent and
  fails on the step-15 tab — the next step.
- The as-implemented census job died when the turn ended (re-run for s18–
  s20 in `ceiling_census16_c.txt`); the s11–s17 results are in `_b.txt`
  (its JSON was never written).
- `tests/test_takeoff_fn_equivalence.py` flaked once on label punctuation
  inside the discover run; green alone.

## Numbers

Change 1 (enclosure, ceiling 36): lost **0** · returned FPs **68**
(unchanged) · new REVIEW lines **0** · net phantom delta **0** · all 20
sheets entity- and polygon-identical.

Change 2 (ceiling 56, with enclosure): lost **0** · returned FPs **60**
(−8: s17 ×4, s18 ×2, s12 ×2, all recorded) · new REVIEW lines **0** · net
phantom delta **−8** (five for the right reason, three fixture cells by
the factor's coincidence) · 0 polygons changed, s01 and s02 identical ·
**next**: `_is_wall_recess`'s back edge on the tab, then the queue (the
s04 staircase, `_dimension_line_indices` on s15's TEXT-layer lines, the
s18 blind-window cap at 1:100, a fixture-cell rule for the three, …).

**Decision needed**: (i) accept the enclosure exemption (inert today, the
storage's protection); (ii) accept the ceiling at 56 with its 1.26× true
margin and the three wrong-reason drops, or hold it as
`rooms_step16_ceiling.diff` — the exemption stands on its own either way.
