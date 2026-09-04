# W-gate iteration 3 — step 6: dash rows are drawn lines, not wall faces (shipped after the user retired ten chunk verdicts)

Branch `fix/dash-rows-not-faces` from `fix/plug-tail-ends-at-material`
(2d48c3d, which carries steps 2, 3 and 5; main is still `ee0f52f`). Baseline:
that tree's own sweep, re-run in four background groups and snapshotted for
all 20 slugs (71 returned FPs, 0 LOST, 5 unreviewed). 2026-09-05.

**Decision (2026-09-05).** The first cut of this report held the rule as
`step-6-dash-rows.patch` because it lost ten confirmed rooms — nine s15
cells and s07's closet, every one fenced only by an annotation dash line —
and the run's rule for a lost confirmed entity is revert, report, stop. The
user looked at the before|after ("s15 looks good"; the split cells had been
confirmed as chunks of one room) and asked for the ten verdicts to be
retired. So: the patch is applied to the tree (`git apply`, its 11 tests
pass), the ten `confirmed` entries below were removed from
`tests/ground_truth/s15.json` (nine, all `"shape": "partial"`) and
`s07.json` (one) by hand with `regression.ground_truth.dump_truth` (a
61-line deletion, nothing else moves; `tests/test_ground_truth_hygiene`
green), labels were reseeded on s07/s15/s17/s18 (Gemini; warnings back to
their baseline counts, no `ROOM_LABEL_*`), and the re-sweep of those four
sheets reads **s07 6/6, s15 11/11, s17 24/24, s18 14/14 — 0 LOST**, with the
same six REVIEW lines as the final sweep below. The patch file stays in this
directory as the record of what was reviewed; it is identical to the diff
now in the tree. The two new s15 REVIEW rooms (the garage, real; the hall
slice, phantom) still wait for `tools/review.py s15`.

## What the measurement said (`tools/census_scratch/dash_rows.py`)

Every collinear row of ≥ 3 same-pen (colour + width) solid pieces at gaps
(0.5, 80] px on all 20 sheets, both classes, with where the pieces end up in
the network (strong face / barrier face / paired face). s15 first:

| row | pen | pieces (n) | piece lengths | gaps | class |
|---|---|---|---|---|---|
| "steel ridge beam 1", x=938.7, y 1406–2285 | 3.0 | 15 | 63.5, 14.8, 73.8, 14.7, 73.8, … (long/short alternating) | 14.8 (CV 0.00) | CHAIN dash |
| "existing steel beam", y=1396.7 / 1417.4 | 3.0 | 7 / 3 | 74, 14.8, 74, 14.7, 74 … | 14.8 | chain dash |
| boundary lines x=91.9 / 1596.7, y 87–2685 | 3.0 | 45 / 45 | 36.7, 14.7, 74, 14.7, 73.8 … | 14.8 | chain dash |
| drain run x=263.2, y 87–2566; "steel beam 2" y=1531.2; branches y=351/785/1484/2317 | 2.0 | 112 / 57 / 6–9 | 14.7–14.8 (end pieces 9–18) | 7.5 (CV 0.02) | plain dash |
| beam-symbol flanges y=1387.7 / 1405.4; unit and rooflight boxes | 1.0 | 19 / 12–17 | 14.7 / 7.5 | 7.5 / 3.7 | plain dash |
| **wall face x=115.4, y 1734–2442 (two windows)** | 3.0 | 3 | 212.5, 198.5, 212.5 | 42.5 | wall |
| **wall face x=434.4, y 379–808 (two openings)** | 3.0 | 3 | 70.8, 236.3, 28.5 | 76.7, 16.5 | wall |

And the true class across the corpus — every real wall face that reads as
"periodic" has exactly THREE pieces at world opening widths: s05 [165, 27,
165] at 49 px (1:100), s07 [106, 99, 106] at 21.3, s11/s16 [35, 71, 34] at
35, s16 [39, 129, 38] at 44, s03 [157, 201, 157] at 5.7, s14 [209, 209, 209]
at 35.5. Dash rows that matter (barrier or paired members) have ≥ 4 pieces
on s05, s07, s12, s15, s17, s18 and gaps of 3.7–15.0 px whatever the scale
(1:50 and 1:100 alike — a paper-space drafting convention). Piece lengths
alone do not separate (a chain line's long dash is 74 px, a dotted line's
6 px); a dash row's END pieces are clipped to any length (s15's rows begin
with 18.0 or 36.7 px pieces), so the pattern lives in the interior pieces.

**Convention** (stated before coding): a drawn dash line is ONE line its
line type exploded into a periodic row — same pen, every gap equal and short,
pieces of one length (plain) or two strictly alternating (chain / dash-dot),
its clipped end dashes never longer than one period. Wall linework is never
periodic: a face broken by text masks has unequal gaps, a face broken by
openings has three pieces at opening widths, a wall drawn in touching pieces
(s06) has no gaps.

## Rule (`detection/walls.py::_dash_row_indices`, in the patch)

Joins the pre-pairing exclusion set beside `_dimension_line_indices` and
`_vector_text_indices`, so members leave every face tier and the
collinear-anchor vote; material marks are untouched (an axis-parallel dash is
never diagonal to its band). Constants, all P-class: `WALL_DASH_MIN_PIECES`
4 (a plain row needs two equal interior pieces, a chain row three
alternating), `WALL_DASH_GAP_MAX_PX` 18 (3 mm; corpus max 15.0, the nearest
3-piece wall row 21.3), `WALL_DASH_GAP_MIN_PX` 0.5, `WALL_DASH_GAP_TOL_PX`
1.5 / `WALL_DASH_TOL_FRAC` 0.12 (a 7.8 in a 6.0 row is a phase reset and
splits the row; both halves qualify), `WALL_DASH_LINE_TOL_PX` 0.6,
`WALL_DASH_ANGLE_TOL` 0.5°.

**Two discriminators the first corpus sweep forced** (the first cut lost 13
confirmed rooms, the final one 10):

- **Nearest-piece linking + `WALL_DASH_MAX_DASH_GAP_RATIO` 8** — s17's
  external wall face at y=3062.67 is [92, 3.75, 348.5, 3.75, 5.5] at gaps
  [0, 2.25, 2.0, 0]; linking a piece to ANY piece within 18 px (past the
  touching 3.75 px tick) read it as a chain-dash, dropped the face's two
  pairs (th 35.5 and 11.75) and opened the confirmed corridor
  (628,3056)–(905,3119) into the wall band, where the exterior contact
  filter dropped it (`step6_s17_tick_stub_face_first_cut_lost_strip.png`).
  Each piece now links only to the nearest piece following it, a touching or
  overlapping piece is a solid continuation and links to nothing, and no
  piece class may exceed 8 gaps — every standard line type keeps its longest
  dash within ~5 (s15 74/14.8, s20 38/7.7, s18 47/9.5, s02's hairline
  78/11.5 = 6.8), a face between tick stubs is 100+.
- **`WALL_DASH_HATCH_END_TOL_PX` 1.5 / `WALL_DASH_HATCH_SIDE_FRAC` 0.8** —
  s05's 475 mm external wall (28 px at f=0.5) has its INNER FACE drawn as a
  6/6 dotted row of 38 pieces on which its 104 through-hatch strokes end
  (23 per 100 px, all from the band side); flagged, the band lost its pair,
  the divider between Bed 1 and Bed 2 no longer met a solid and the two
  confirmed bedrooms merged through the wall
  (`step6_s05_dotted_face_first_cut_merged_bedrooms.png`). A row that hatch
  strokes end on, obliquely, predominantly from one side, at the weak-tier
  material density (`WALL_WEAK_MATERIAL_MIN_MARKS` 4 and
  `WALL_WEAK_MATERIAL_PER_100PX`), is the face of a hatched band drawn
  dotted. A beam line crossing a hatched band is crossed by the hatch, which
  ends on the band's own faces (0–2 ends on s15's ridge beam).

Tests (in the patch): `tests/test_wall_network.py::TestDashRowExclusion`
(plain and chain rows never become faces, a dash row is not an anchor vote —
the s15 room_0016 topology, opening-broken faces and s06's touching pieces
keep their rights, the recogniser directly) and `TestDashRowDiscriminators`
(the s17 tick-stub face, the s05 dotted hatched face with and without its
hatch, a chain row crossing hatched bands is still flagged);
`tests/test_room_detection.py::TestDashRowBarriers` (a beam line does not
split a room; a wall in touching pieces still does). 8 of the 11 fail on the
baseline code (the three "true class keeps its rights" tests pass either
way by design). Full fast tier with the rule: 1394 tests, only the two
InquirerPy import errors.

## Sweep (`tools/regress.py`, four background groups, vs the baseline)

| | lost | returned FP | REVIEW | polygons |
|---|---|---|---|---|
| baseline | 0 | 71 | 5 | — |
| first cut (no discriminators) | 13 (s15 9, s05 2, s07 1, s17 1) | 66 | 7 | 12 changed, 2 added, 18 removed |
| **final** | **10 (s15 9, s07 1)** | **67** (s15 −4: (1538,1117), (1529,1928), (635,1311), (1543,1459)) | **6** (s15 room_0016 gone; + s15 room_0009 (929,1458), room_0015 (257,2102)) | 9 changed, 1 added, 14 removed; **16 sheets IDENTICAL** incl. s01/s02 |

`tools/diff_room_polygons.py`: s07 room_0002 removed, room_0003 +2,827 px²
(fills the dashed double-line band it hugged); s15 as below; s17 rooms 0022
/0025 +1,955 / +726 (orange demolition lines beside an opening); s18
room_0021 +245 (a chain line across a doorway plane). Unsimplified check
(`ROOM_SIMPLIFY_TOL_PX` 0, the rule toggled by monkeypatch, s05/s07/s15/s17
/s18): the ONLY room losing free space is s15's recorded-FP hall room_0000
(−321 px² at (853–941, 1370–1415)): with the beam symbol's 9 px flange pair
(776–852, 1392) gone, a 35.25 px strong pair (799–852, 1370) the interior-pair
rule had dropped now stands. Harness at seals 12 and 14: s01 and s02
identical at 12 (at 14 only the pre-existing s01 room_0003/0005 moves);
**s15 at 14 equals s15 at 12** — the step-2 mechanism (the ridge beam crossing
door_0013's doorway plane, 3/11 mid cover) is gone with the beam.

Per-sheet flagged pieces (final rule, census re-run with the marks): s01 12
(a dotted leader), s02 0, s03 855, s04 1,196, s05 12, s06 0, s07 137, s08
584, s09–s11 0, s12 432, s13 0, s14 17, s15 998, s16 0, s17 238, s18 844,
s19 0, s20 243 — almost all hairline/grey unit-box and rooflight dashes that
never were faces; rows with barrier or paired members: s01 1, s05 1 (a
2.8 px dotted stub), s07 2, s15 2 (dashed X diagonals of a fixture box), s17
7 (orange demolition lines), s18 2, s20 2 (chain lines, paired only).

## The ten LOST rooms, each attributed to its dash row (my read)

| lost (truth centre) | baseline room | what fenced it | with the rule | my read |
|---|---|---|---|---|
| s15 (893,1955) | room_0023 [849,1638,937,2272], the 88 px strip left of the ridge beam | the 3.0 px chain-dash "steel ridge beam 1" at x=938.7 | merges into the lounge (rule room_0014, IoU 0.847 vs room_0024 — that verdict survives) | the lounge is one 500×650 px room under a beam line; **stale verdict** (`step6_s15_lounge_ridge_beam_before_after.png`) |
| s15 (979,1590) | room_0020 [941,1549,1018,1631] | the same beam, splitting the "810mm door set" vestibule 88\|77 | one 169 px vestibule (rule room_0012, IoU 0.52 vs room_0019 — survives) | stale verdict |
| s15 (975,1456) | room_0013 [941,1419,1009,1492] | the beam (left) and the 3-piece chain fragment y=1417.4 (top) | merges with the 93 px strip left of the beam into rule room_0009 (new REVIEW, 0.90) | both states are a slice of the hall zone held by beam lines — **phantom either way** |
| s15 (195,2102) / (331,2018) / (331,2401) | rooms 0025/0026/0027 — the garage cut into three | the page-long 2.0 px drain run at x=263 and its branch at y=2317 | ONE garage (rule room_0015, new REVIEW, 0.90) | the drawn garage; **stale verdicts, a real room regained** (`step6_s15_garage_drain_run_before_after.png`) |
| s15 (541,1311) / (638,1468) / (470,1468) | rooms 0009/0012/0011 — cells of the kitchen zone | the "existing steel beam" symbol (two 1.0 px dashed flanges + the chain line at y 1388–1405) and the "steel beam 2" row at y=1531 | the kitchen zone from the hall's wall down to the dining area is one room (rule room_0008, IoU 0.742 vs room_0017 — survives) | stale verdicts (`step6_s15_kitchen_beam_symbols_before_after.png`) |
| s07 (247,381), note "does not cover the top part of the room, stops at door leaf" | room_0002 [220,336,273,426], a 53×90 px closet | a dashed DOUBLE line — two 5-piece 7.5/3.7 rows 8.3 px (140 mm at 1:100) apart at x 275/283 — is its only right-hand boundary | opens into the neighbouring room | drawn as a dashed partition (overhead or hidden); **uncertain — the user's call** (`step6_s07_closet_dashed_partition_before_after.png`) |

New REVIEW rooms, my verdicts: s15 room_0015 (257,2102) — the garage, **real**
(a win once confirmed); s15 room_0009 (929,1458) — a 160×77 px slice of the
hall held by the 3-piece chain fragment [74.8, 14.7, 74.8] at y=1417.4 (n <
`WALL_DASH_MIN_PIECES`) and the utility's wall, **phantom**. Recorded
phantoms that vanish: s15 rooms (1538,1117), (1529,1928), (1543,1459) — the
three cells between the east boundary chain line x=1514 and the wall — and
(635,1311), the kitchen zone's merged cell, plus the REVIEW pocket
room_0016 between two drain rows (`step6_s15_room_0016_pocket_gone.png`).

**Net phantoms: −4** (−4 recorded, −1 REVIEW pocket, +1 new). Plan-wide
picture: `step6_s15_plan_baseline_green_rule_red_dash_rows_blue.png`
(every flagged piece in blue — the beam lines, the drain runs, the rooflight
and unit boxes, the "remove chimney breast" outline).

## Residue / not in scope (one line each)

- A chain fragment of three pieces (the "existing steel beam" line broken by
  its label) keeps its faces and fences s15's hall slice; a text-mask join
  rule (rows on one line either side of a text span are one row) is the next
  discriminator, not bundled.
- s15 room_0000's −261 px² (a 35 px pair the flange pair had held out) is
  inside a recorded-FP hall; not chased.
- Dashed DOUBLE lines at wall spacing (s07's closet, s17's orange rows 11.8 px
  apart) are "wall over / to be removed" symbols; whether an EXISTING plan's
  dashed partition bounds a room is a drafting-convention question the truth
  must answer.
- Labels were NOT reseeded: no polygon in the working tree moved (the rule is
  reverted). Reseed s07/s15/s17/s18 after the patch is applied.

## Numbers

Against the step-5 baseline truth: lost **10** (s15 9, s07 1 — all
dash-fenced chunks, attributed above), which the user retired; **against the
edited truth: lost 0** · returned FPs 71 → **67** (−4, all s15) · new REVIEW
lines **2** (s15 room_0015 garage — real; s15 room_0009 hall slice —
phantom) and one gone (s15 room_0016 pocket) · net phantom delta **−4** ·
working tree: rule in (code + 11 tests + prose), ten verdicts retired, labels
reseeded on s07/s15/s17/s18, 16 sheets polygon-identical, s01/s02 untouched ·
**next: step 7** (the seal retry: s15's seal-14 blocker is gone with the
beam; s01 room_0005's fit flip and the two unmeasured 14–15 moves on s01
room_0003 / s04 room_0001 remain), the user's `tools/review.py s15` verdicts
on the garage and the hall slice, and the text-mask join for 3-piece chain
fragments as its own iteration. One caution: the confirmed vestibule
[848.7,1549.4,936.7,1630.8] now matches the merged 169px vestibule at IoU
0.52 — a 2px shift would drop it under the 0.5 match; re-confirming the
merged room through `review.py` when it next appears would pin it.

**Decision needed**: commit this branch (code, tests, prose, the two truth
files, the census tools and the 12 PNGs, none of which shows an address).
