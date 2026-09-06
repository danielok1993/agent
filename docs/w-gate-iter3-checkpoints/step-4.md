# W-gate iteration 3 — step 4: `WALL_MAX_THICKNESS_PX` 36 → 40 measured AS IMPLEMENTED on every sheet and NOT moved — the number is not the lever

Branch `recal/wall-max-thickness-40` from `recal/gate-denominator-stored-scale`
(83a603c, which carries steps 2, 3, 5–12; main is still `ee0f52f`). Baseline:
that tree's own sweep, re-run in four background groups and snapshotted for
all 20 slugs (`outputs/regress_baseline/<slug>/2026-09-06_14-32-*` …
`14-33-*`) — **0 LOST, 68 returned FPs, 0 REVIEW**, s01 10/10, the 68 verdict
lines byte-identical to step 12's minus s01's retired/recorded lines.
2026-09-06.

**No detection code was changed in this step.** `detection/` is
byte-identical to 83a603c (the constant was set to 40 for one corpus sweep
and restored from a backup, `cmp`-verified). What changed: this report and
ten PNGs, the `WALL_MAX_THICKNESS_PX` comment, the CLAUDE.md gate paragraph,
the handoff, and scratch tooling under `tools/census_scratch/step4/` plus
three harness fixes (`tools/census_scratch/harness.py`: the door-plug tap now
passes step 10's `seek_edges` through; the marks tap captures the ONE
through-diagonal mark population the pipeline collects since the W-gate
census, so `wide_pairs` carry real material verdicts; `wide_pairs` records
keep the pair's endpoints and pen).

## The brief's premise, and what the census found

The brief: move the cap 36 → 40 (340mm at 1:50, 20px at 1:100) for −5
recorded phantoms (s17's four cavity-wall reveal strips, s16's pocket), with
the s11 recess box (1030,1330)–(1123,1360), the s15 annotation pocket
(1480,698)–(1595,792) and the s18 tree strip (156,724)–(197,863) staying out
— after a census of every strong pair in the 36–40px band at the sheets'
factors, each classed wall or fixture, with the discriminator for whatever
the far-side rules do not catch measured on both classes before the number
moves.

**Census as implemented** (`band_census.py`: the whole stage-5 chain through
the harness at cap ×1.0 and ×40/36 — every use of the cap scales: pairing,
the thick tier's floor, stair-zone anchoring, lattice pitch, band pockets,
ring sizes — final network segments and rooms diffed, ground truth scored;
274 candidates over 20 sheets):

| sheet (f, band px) | candidates | admitted segs | rooms moved / gone / new | verdict delta |
|---|---|---|---|---|
| s17 (1.0, 36–40) | 15 | +24 −27 | 0 / **4** / 0 | **−4 returned FPs** (the reveal strips 0013/0014/0027/0032) |
| s16 (0.5, 18–20) | 74 | +63 −63 | 14 / **1** / 0 | **−1 returned FP** (the pocket at (2502,1563)) |
| s11 (0.5, 18–20) | 56 | +34 −42 | 13 / 0 / **1** | **+1 REVIEW** — the recess box, 0.62 |
| s18 (0.5, 18–20) | 74 | +60 −25 | 2 / 0 / **1** | **+1 REVIEW** — the tree strip, 0.77 |
| s15 (1.0, 36–40) | 7 | +4 −2 | 1 / 0 / 0 | none — but the confirmed bedroom **−5,135 px²** |
| s01 (0.542, 19.5–21.7) | 9 (3 with material) | +13 −7 | 0 / 0 / 0 | none, polygons IDENTICAL |
| s02 (1.0) | 9 | +14 −7 | 0 / 0 / 0 | none; 3 rooms move 3–19 px² (re-noding) |
| s03 / s05 / s12 / s14 / s10 | 4 / 2 / 4 / 18 / 2 | +6 / +3 / +6 / +23 / +2 | 0 | none, polygons identical |
| s04 s06 s07 s08 s09 s13 s19 s20 | 0 | 0 | 0 | none |

**What the 40 admits, classed from the pictures** (`crop_segments.py`,
`attribute_rooms.py`, the zooms in this directory):

| admitted pair | what it is | effect | class |
|---|---|---|---|
| s17: 36.5–36.75px × 125–435px stretches at (930,2270), (930,2817), (3065,2327), (3065,2810) | the 313mm cavity wall (leaf/cavity/leaf 11.75/12/13.25 = 37px) where its two leaf lines stop — the cap sits 1.03× under a standard modern cavity wall (102.5+100+100+13 = 315mm) | the four reveal strips are inside the solid — **−4 recorded phantoms** | **true wall** — the brief's win |
| s16: 18.0px × 55px at (2502,1554) | **two adjacent stair TREADS** — the "striped-block pocket" is the foot of a flight (`step4_s16_stair_tread_pair_cap40.png`) | the pocket sealed — −1 recorded phantom, for the wrong reason | false (stairs are furniture) |
| s11 + s16 (1:100): 27 × 19.87–19.88px external-wall pairs | the plans draw their external walls with finish lines on BOTH sides, 2.25px = 22mm off the 17.62px pair that paired before, symmetric about the same centreline (`step4_s11_porch_finish_lines_cap40.png`) | 27 rooms stop at the plaster face: 1.1px strips (11–816 px²); s11's porch −2,103 and utility −1,028 had leaked into the band and now stop at it | true wall — a correction, sub-1 % |
| s18: 18.25px × 682px at (140,1041) | the site boundary drawn DOUBLE — two 1.75px lines 18px apart, drawn twice, nothing between (`step4_s18_boundary_double_line_tree_strip_cap40.png`) | the tree strip (156,724)–(197,863) returns as a 0.77 room whose only opening is a 0.67 window (4.6k px² against the scaled 2.5k blind-window cap) | **false** — the brief's pocket 3 |
| s11: 19.88px × 15px at (975,1370) | a 20×15px stub box under the party wall — at 18 a material-gated thick pair (dropped), at 20 a plain pair | the neighbour's chimney-breast box beside it (1030,1330)–(1123,1360), a closed outline in both trees, now passes the room filters: 0.62, no door, no window, no text (`step4_s11_party_wall_recess_box_cap40.png`) | **false** — the brief's pocket 1 |
| s15: 39.75px × 156px at (1365,1068) and 36.25 × 31 at (1428,1069) | the wardrobe box's double bottom edge (paths 2305/2306, 3px apart) × the "3560" dimension line 40px below it (path 52609, layer TEXT — s15's mis-filed linework layer, its ticks unrecognised), the "1100" line making the vertical arm (`step4_s15_wardrobe_edge_x_dimension_line_cap40.png`) | the confirmed bedroom (1025,929)–(1441,1386) loses its top-right corner, **−5,135 px², IoU 0.969** | **false** — a fixture edge × an annotation line |
| s14 (16), s10 (2), s02 (3): 36–40px fill-outline pairs, 11–24px long | vector-text GLYPH OUTLINES of 5mm room labels — the letter height (`step4_s14_glyph_outline_candidates.png`; black fill outlines at 0.5px / width 0, the known gap (b) class) | none on rooms; s02 re-nodes three outlines by 3–19 px² | false, inert |
| s05, s12: 19px hatched walls | 380mm walls at 1:100, already thick-tier pairs on material | none | true, inert |
| s15's annotation pocket (1480,698)–(1595,792) | does not appear at 40 on this tree (the dash-row and far-side rules shipped since iteration 2) | — | — |

**Discriminators measured on both classes** (`interior_census.py`: every
candidate, the pipeline's exact faces, marks and post-suppression openings):

| feature | s17's four admitted cavity stretches (true) | s18 boundary / s16 treads / s11 stub (false) | s15 wardrobe (false) | s11/s16 finish-line walls (true) |
|---|---|---|---|---|
| material marks in the band (`_band_has_wall_material`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 | 0 | 0 |
| stroked linework parallel to the faces INSIDE the band, over the overlap | **0.00** ×4 | 0.00 / 0.00 / 0.00 | **1.00** (its own double edge, 3px in) | 0.92–1.00 |
| the same over the faces' FULL extent (a cavity's leaf lines stop at openings) | **0.00** ×4 (the leaf lines are absent along these faces — that is why the strips form) | 0.00 / 0.00 / 0.00 | 0.44 | 0.55–1.00 |
| confident openings in the band | 0 ×4 (each stretch ENDS at a doorway; no window lies in it) | 0 / 0 / 0 | 0 | 0.85–1.00 (a window each) |

**Nothing at the pairing stage separates s17's true stretches from s18's
boundary, s16's treads or s11's stub**: all read zero on every feature, at
the same world thickness (313mm vs 365 / 360 / 398mm). The two hypotheses I
measured before building — "a band over the standard cap is a built-up wall
with linework inside it" and "an opening is cut into it" — are refuted by the
true class itself, and the s15 wardrobe passes the first on its own double
edge. What DOES separate them is context: s17's stretches bound entered
rooms of the house, s18's bounds a garden strip, s16's a stair cell, s11's a
box on the neighbour's side of a party wall — a room-stage distinction, not
a pairing gate. So per the brief's rule the number does not move.

## Sweep at 40 (the number alone, for the record; `tools/regress.py` four groups vs the baseline, `diff_room_polygons.py` all 20)

| | lost | returned FP | REVIEW | polygons |
|---|---|---|---|---|
| baseline (36) | 0 | 68 | 0 | — |
| **cap 40** | **0** | **63** (s17 −4, s16 −1) | **2** (s18 room_0007 the tree strip; s11 room_0012 the recess box — both phantoms) | **31 changed, 2 added, 1 removed**: s01 IDENTICAL; s02 3 rooms ±3–19 px²; s15 room_0004 −5,135 (confirmed); s11 6 (−2,103 … +283); s16 4 (−142 … −816) + the pocket; s17 2 (8, 21 px²) + the four strips; s18 +907 + the strip; 12 sheets identical |

Net phantoms **−3** (−5 +2) with one confirmed-room outline regression
(s15) and the s02 rule ("must not change") broken by 3–19 px² — a trade, not
a win; two of the brief's three must-stay-out pockets return. s01 at its
true factor is entity- and polygon-identical (its band is 19.5–21.7px; 3 of
its 9 candidates carry material and already pair). **Unsimplified** (`unsimplified_diff.py`, `ROOM_SIMPLIFY_TOL_PX` 0 at both
caps): s15 loses exactly the 181×30px wardrobe strip (5,135 px², nothing
gained); s11 loses 6,189 px² over 13 rooms against 394 gained — 1.1px
finish-line strips on nine of them, the porch's and utility's band leaks
(1,429 + 439 and 1,028 px²), and one 43×19px bite — and s16 loses 3,450
against 7: finish strips plus two box-scale bites, 43×19px at (2091,1328) and
28×37px at (2427,1241), the same class as s11's 20×15px stub — a closed
box at wall spacing (400 × 300mm at 1:100: a pier, a duct, a cupboard)
pairing as a plain band once the cap clears it.

## Where the lever is (proposed next step, not built)

The s17 strips are exactly `_is_band_pocket`'s class — free space between
two wall faces that could have paired as one wall — and the rule rejects
them only because its spacing ceiling is `WALL_MAX_THICKNESS_PX`: the strip
is 35px wide and the test reads `35 + 2 × 2 = 39 > 36`. The rule is called
only for components with **no entrance and no window**, so raising its
ceiling to `WALL_THICK_MATERIAL_MAX_PX` (56px at 1:50, 28 at 1:100) cannot
touch an entered room: the narrowest confirmed room on the corpus, s11's
19px "storage in utility" (1078,1597)–(1097,1704), carries `door_0009`
(measured in its takeoff record) and is never a candidate. The 11 recorded-FP
pockets on s11/s12/s16/s18 at 1.2–2× the scaled cap (CLAUDE.md, the
band-pocket paragraph) are the same class one band deeper. That step needs
its own census — every entrance-less, window-less component 36–56px wide on
the corpus, classed from the pictures — and leaves the pairing cap alone, so
s18's boundary, s11's stub and s15's wardrobe edge never pair. The cavity
wall's true thickness (315mm, 1.03× over the cap) is then recorded as the
known exception the pocket rule closes, not a reason to admit every empty
band up to 340mm.

Two smaller gaps the census exposed, each its own line in the queue:
s15's "3560" / "1100" dimension lines on the TEXT layer are not recognised
by `_dimension_line_indices` (their ticks are drawn but the recogniser
misses them — an annotation line free to pair with any parallel edge at wall
spacing), and s18's blind-window drop caps at `ROOM_BLIND_WINDOW_MAX_AREA_PX2`
× f² = 2.5k px² at 1:100 while the tree strip is 4.6k.

## Pictures (this directory, none shows an address)

`step4_s17_reveal_strip_inside_cavity_band_cap40.png`,
`step4_s17_four_reveal_strips_removed_cap40.png` (compare_sweeps),
`step4_s18_boundary_double_line_tree_strip_cap40.png`,
`step4_s18_tree_strip_added_cap40.png` (compare_sweeps),
`step4_s11_party_wall_recess_box_cap40.png`,
`step4_s11_recess_box_added_cap40.png` (compare_sweeps),
`step4_s11_porch_finish_lines_cap40.png`,
`step4_s15_wardrobe_edge_x_dimension_line_cap40.png`,
`step4_s16_stair_tread_pair_cap40.png`,
`step4_s14_glyph_outline_candidates.png`. In every zoom: blue = the pair the
40 admits, orange = the segment it replaces, red = the room before, green =
after.

## Residue / not in scope (one line each)

- The finish-line corrections on s11/s16 (27 rooms, 1.1px = 22mm at 1:100)
  are real and would come with any rule that pairs those 19.88px walls; they
  change 27 confirmed outlines and the takeoff by sub-1 %, and are reported
  here as a decision for whenever such a rule ships.
- The harness's `wide_pairs` tap had reported `material=None` for every
  candidate since the W-gate census moved mark collection to one call; fixed
  here — earlier censuses that read that field (none did, the step-3 and
  step-9 probes used their own taps) are unaffected.
- `tests/test_takeoff_fn_equivalence.py` still flakes on Gemini label
  punctuation; not run here (no detection change).

## Numbers

lost **0** · returned FPs **68** (unchanged — no code moved) · new REVIEW
lines **0** · net phantom delta **0** (the 40 as implemented would be −5 +2,
with a confirmed bedroom −5,135 px² and s02 moved) · s01 and s02 untouched ·
**next**: the band-pocket ceiling (`_is_band_pocket` up to
`WALL_THICK_MATERIAL_MAX_PX`, with its census), then the queue.

**Decision needed**: accept this as a measurement-only checkpoint (commit the
report, the ten PNGs, the prose notes and `tools/census_scratch/step4/` with
the harness fixes), or direct the 40 anyway with its measured trade.
