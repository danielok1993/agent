# W-gate iteration 3 — step 9: `_gate_denominator` measured on this tree and NOT moved — s01 at its true factor is held by three things, not one

Branch `recal/s01-true-factor` from `fix/plane-restricted-fallback-stamp`
(a3ec9e8, which carries steps 2, 3, 5, 6, 7 and 8; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups (s18; s16
s11 s15; s01–s07; the rest) and snapshotted for all 20 slugs
(`outputs/regress_baseline/<slug>/2026-09-05_11-47-*`) — **0 LOST, 68
returned FPs (1 door, 48 rooms, 19 windows), 0 REVIEW**, every labelled
sheet fully reviewed. 2026-09-05.

**No code was changed in this step.** The tree is byte-identical to a3ec9e8
apart from prose (this report, the handoff) and two PNGs. `_gate_denominator`
is unchanged and s01 still detects at identity. The brief ordered "only with
the user's decision on s01's three stair-split rooms, narrow
`_gate_denominator`; re-measure the hall's leak first" — the re-measurement
below shows the move would lose a confirmed room (the hall) and add 17
phantoms whatever the stair verdict, so per the run's rule it was not made.

## s01 at f = 50/92.2 on this tree (harness, `tools/census_scratch/harness.py`)

| | doors | windows | rooms | unreviewed |
|---|---|---|---|---|
| identity (= the sweep) | 11/11 | 4/4 | 12/12 | 0 |
| **f = 0.542** | 11/11 | 4/4 | **8/12** | **18** (1 real, 17 phantoms) |

`ablate.py s01 s01mode` re-run on this tree (`tools/census_scratch/abl/
s01_s01mode.jsonl`; the step-3 log is beside it as `s01_s01mode_step3tree.jsonl`):

| configuration | lost | unreviewed |
|---|---|---|
| `full_f0.542` | 4 | 18 |
| `only:WALL_MAX_THICKNESS_PX` (= `only:CAPS3`) | 4 (the three stair rooms + the living room by bbox) | 1 (the merged landing) |
| `only:ROOM_OPENING_SEAL_PX` | 2 (the hall, and the living room's bbox) | 0 |
| every other `only:` that runs | 0 | 0 |
| `only:WALL_THICK_MATERIAL_MAX_PX`, `only:WALL_THROUGH_HATCH_MAX_PX` | abort on the harness's cap-ordering assertion (scaling one cap alone inverts the tier order) — not measured | — |
| `loo:ROOM_OPENING_SEAL_PX` (everything scaled but the seal) | 3 (the stair rooms; the hall stays) | 18 |
| `loo:CAPS3` | 1 (the hall) | 11 |
| `loo:ROOM_MIN_AREA_PX2` | 4 | 4 (landing + strip + two splits) |
| `loo:WALL_FACE_MIN_LEN_PX` / `loo:WALL_PAIR_MIN_OVERLAP_PX` / `loo:COLLINEAR_OFFSET_TOL` / `loo:WALL_THROUGH_HATCH_MAX_PX` | 6 / 6 / 5 / 4 | **1** each |

So the four losses are still exactly the cap (three stair rooms) and the seal
(the hall), and the 17 phantoms are an INTERACTION: any ONE of four wall
gates held at identity removes all of them.

### The four lost rooms, attributed (scratch `s01_leak.py`: every piece of 0.542 free space outside the identity room polygons that touches two of them, and the identity barrier that used to cover it)

| lost room | leak piece at 0.542 | what covered it at identity |
|---|---|---|
| hall (392,920)–(521,1387) ↔ living room | (412.0,912.9)–(463.1,918.8), 285 px² — the hall doorway | **door_0002's TOP-edge (doorway) plug** — 285 of 285 px² |
| CPD (466,920)–(521,1051) ↔ hall | (466.5,1052.2)–(521,1115.6), 3,223 px² — the flight below the cupboard | the two phantom flight pairs th 28.0 / 30.8 (step 3's row 2) |
| (1090,698)–(1142,878) ↔ (1033,923)–(1142,1135) | (1059.4,878.5)–(1142,926.5), 2,319 px² — the flight | the stair-arrow phantom pairs th 35.2 / 28.2 (step 3's row 1) |

The hall/living merged blob (209,412)–(521,1389) matches the confirmed living
room (209,415)–(521,912) at bbox IoU 0.5015 — one pixel from a fifth LOST
line.

## 1. The hall: it IS the seal — step 8's "the leak is elsewhere" was a misread

Step 8 looked at door_0002's RIGHT edge ("takes an interrupted plug at 0.542,
seal 8.13 ≥ its 8 px gap") and concluded the hall leaks elsewhere. The right
edge (x = 467.5) is the OPEN LEAF's hinge edge, lying on the CPD cupboard's
wall line — it takes an interrupted plug at identity too (`plugs:
interrupted@0, interrupted@3`) and seals nothing between the hall and the
living room. The doorway is the TOP edge (y = 917): the hall/living wall face
at y = 917.75 runs x 203.5 → 410.25, stops, and resumes at 464.5 — a 54 px =
847 mm opening — while the door's leaf/arc spans x 424.5 → 467.5 (43 px =
671 mm). The leaf overlaps the hinge jamb by 3 px and stops **14.25 px = 222 mm
(at 1:92.2) short of the latch jamb face** — 12.2 px = 191 mm short of its
dilated material. Profile of that edge (`s01_profile.py`, the exact numbers
`_door_plugs` computes):

| | seal | half-width | samples from the corner outward (d to material) | start cover | touch | verdict |
|---|---|---|---|---|---|---|
| identity | 15.0 | 5.0 | x 409.5 → d 0.0, 413.6 → 1.3, 417.6 → 5.4, 421.7 → 9.4 | 3/4 | 2 samples ≤ 5 | **interrupted** |
| 0.542 | 8.13 | 2.71 | x 416.4 → d **4.1**, 420.6 → **8.4**, 424.8 → 12.6 | 1/3 < 0.5 | none ≤ 2.71 | **none** |

Two scaled numbers fail together: the tail's first sample stops 4.1 px short
of the jamb material (> the 2.71 px touch), and the second sample sits 0.4 px
outside the 8 px hug (1/3 covered). To pass, the tail needs S ≥ 9.57 px at
0.542 = **17.65 px at 1:50** (the reviewer's direct probe of `_door_plugs`:
9.52 still fails, first distance 2.762 > 2.7115; 9.60 qualifies — my 9.52
was a linear estimate off the material bounds) — over the 15 shipped in
step 7 and a hair under the 18 at which s03's two recorded FP rooms return
(step 7). Keeping the half-width at 5 (`loo:ROOM_PLUG_HALF_WIDTH_PX`) does
not save it: touch passes, cover stays 1/3. Step 7's "s01 needs 125 mm" was
computed against the 5 px half-width and the touch envelope, not the drawn
jamb.

**The corpus census** (`jamb_census.py` / `jamb_analyze.py`: every
`_door_plugs` call on 18 sheets, 2,173 edges; for every KEPT interrupted plug
on a ≥ 0.55 door the distance from each bbox corner outward to the dilated
material, in mm at the sheet's TRUE scale):

| kept interrupted doorway ends (n = 378) | median | p75 | p90 | max |
|---|---|---|---|---|
| jamb gap, mm | 0 (255 of 378 have material at the corner) | 17 | 34 | **219** |

The four largest gaps on the whole corpus are s01's four swing doors —
door_0003 219 mm, door_0006 203, door_0002 203, door_0001 187 — then s05
135 mm, s17 110, s18/s08 102, s14/s02 85, and every other sheet ≤ 51 mm. s01
draws its door symbols short of their openings on the latch side (a 671 mm
leaf in an 847 mm opening); no other sheet does. At identity the 15 + 5 px
reach (169 mm at 1:50) covers everything, s01 included, because s01 is being
read as 1:50; at its true factor the reach is 169 mm × 0.542 against a
222 mm gap. The other three wide-jamb doorways survive 0.542 by sample
phase: wall material happens to lie within their 8.13 px tails (door_0001:
the black face at (438,1175)–(438,1185); door_0003/door_0006: a 7 px
magenta/blue pair at y = 692.5 and magenta hatch strokes) — none of it is
the furniture pen, so the pen fix below does not endanger them, but each is
one phase shift from the hall's fate. (A first draft named a 35 px blue
dimension line as their anchor; the reviewer showed it has no barrier
rights and that removing every blue primitive there changes nothing.)

A seal number cannot cover this (⚠ "discriminator, not number"): what a
draughtsperson does is cut the doorway OUT of a wall, so the doorway's jamb
is wall material the plug's tail has to reach, and the reach is what the
bbox ± SEAL rule fixes in advance. The rule is a **material-seeking tail**
— §1b, as corrected by the review: my first form (seek a COLLINEAR face)
is refuted by its own census; the nearest WALL MATERIAL outward, a
perpendicular jamb return included, is what reaches the hall. **Its own
iteration; not built here.**

Picture: `step9_s01_hall_door_doorway_plug_identity_vs_0542.png` (the
doorway plug and its tail samples at both factors; blue = barrier, orange =
door seals, green = rooms).

### 1b. The jamb-seeking tail, measured before building — the COLLINEAR seek refuted, a MATERIAL seek is the rule (corrected after review)

The user chose the jamb-seeking tail as the next iteration (2026-09-05);
the census that was to precede the code refutes the form I had proposed.
`collinear_census.py` (every door edge end on 18 sheets at their factors,
plus s01 at 0.542: the nearest BARRIER face collinear with the edge — angle
≤ 4°, perpendicular offset ≤ `ROOM_PLUG_NEAR_PX` — beginning outward from
the corner, its distance g; my script approximated barrier eligibility, the
reviewer re-ran it with the room stage's exact rule and the counts below
are the reviewer's):

| | n | collinear barrier face within 60 px | g median / p90 / max |
|---|---|---|---|
| kept interrupted doorway ends (true class) | 396 | 308 (78 %) | 2.3 / 6.2 / 57.8 px = 34 / 78 / 979 mm |

A real doorway's jamb face begins AT the corner (median 34 mm); 22 % of
doorway ends have no collinear face at all (the jamb is a perpendicular
return or a fill ring). **And at 0.542 the hall door's nearest collinear
barrier face begins at x = 389.5, g = 35 px = 546 mm**, not at the jamb
(410.25, 14.25 px): at identity the wall face run
(410.25,917.75)–(203.5,917.75) has TWO members — the long face, path 941,
and path 331, the jamb block's UNSTROKED bottom outline at y = 920.75
(3.0 px off, absorbed by `COLLINEAR_OFFSET_TOL` 4 and re-projected onto the
face's line) — and the block itself pairs as a 20.5 px band; at 0.542 the
tolerance is 2.17 px, path 331 stays a separate unstroked, unpaired face
with no barrier rights, the run ends at x = 389.5, and the block fails the
thick-tier material gate (step 3: 4 marks at 25.8/100 px, run 15.5 < 16.3,
span 0.39). The false class at that distance is real: s17 door_0020 (0.95
single), hinge edge 3 — an eligible lone wall-pen face begins 30.65 px =
519 mm beyond its open leaf's tip on the leaf's own line (hinge end
anchored, mid empty); a collinear seek reaching the hall at 0.542 (546 mm)
fires there too and bridges a 519 mm walkway with an "interrupted" plug.
Margin 1.0×. At the sheets' own factors 132 ends have a collinear barrier
face beyond the seal within 60 px, 49 of them under 300 mm — mostly
fallback-tier label boxes. **The collinear seek is not the rule.**

**What I got wrong (the review's decisive correction):** I wrote that a
material-based seek "would reach the block's dilated solid only if the
block pairs again". It does not need the block to pair. The block's RIGHT
face, path 278 — a 29.5 px stroked wall-pen face at x = 410.25,
perpendicular to the doorway — keeps its lone-face barrier rights at 0.542,
and its 2 px buffer is wall material on the doorway's line out to
x = 412.27 (`s01_profile.py` prints it: "material piece near left jamb
bounds (404.37,900)–(412.27,922.77)"). A seek for the nearest WALL MATERIAL
outward from the un-anchored end — a perpendicular jamb return included —
reaches it at 12.3 px = 191 mm (the touch envelope at 9.57 px); the
reviewer's direct probe at S = 9.60 shows the top plug qualifying with no
pairing change. One rule, not two; no hatched-pier rule.

**Its false class, measured** (`material_seek_probe.py`: every HINGE-edge
end of a ≥ 0.55 single that is NOT anchored today, the nearest touch
outward against the FULL barrier union minus the door's own seal, at the
sheets' factors and s01 at 0.542):

| | ends | hits ≤ 300 mm | what they are |
|---|---|---|---|
| 18 sheets at their factors | 172 | 10 | 7 are the seals of OTHER openings, which a wall-material seek never sees (s14 door_0013, door_0011 edge 3, s16 doors 0003/0004 back to back, s20 doors 0003/0004 — a leaf tip at the next door's seal; s10 door_0009 — window_0002's seal at the corner); **s14 door_0011 edge 0 at 161 mm** (a wall-fill jamb return, the doorway of a plug-less door whose other end has no material — no plug either way); **s14 door_0007 edge 0 at 296 mm — the one false hit**: the open leaf's tip reaching a wall-fill chevron ring (paths 3015/3016, two 22 px 45° edges) 35 px out, which an interrupted plug would then spur to (hinge end on the wall, mid empty) |
| s01 at 0.542 | 5 | 1 | **the hall door's top edge at 10 px = 156 mm** (integer touch; 191 mm to the material) — the true class |
| the reviewer's true-class examples at the sheets' factors | | | s18 door_0018 edge 3 at 11 px = 186 mm (its doorway per step 8's table, plug-less today — a WIN), s05 door_0007 135 mm and s17 door_0004 169 mm (anchored today by phase) |

So a world cap of ~250 mm (29.5 px at 1:50, 16 px at 0.542, 14.8 px at
1:100) admits the hall (191 mm, 1.31× under) and s18 door_0018 (186 mm)
and excludes the chevron (296 mm, 1.18× over) — thin on the false side,
one instance; the "one end anchored" condition the reviewer states is what
keeps a leaf tip pointing at open floor from ever plugging. `_door_plugs`
sees material clipped SEAL + NEAR + 4 px around the bbox (27 px at 1:50),
so the seek needs the local clip widened to the cap; `_clip_plug_tails`
uses SEAL as its reach and must take the plug's own extent instead. s01
door_0015's piers (281 mm at identity) lie past a 250 mm cap and keep
their plane stamp, so s01 at f = 1.0 would not move. **Next iteration:
synthetic test, rule, harness at 0.542, corpus sweep.**

## 2. The 17 phantoms: s01's furniture pen crosses the wall-pen fraction gate

Every one of the 18 unreviewed rooms at 0.542, classed (`s01_phantoms.py`,
`s01_pens.py`):

| class | rooms | area | fenced by |
|---|---|---|---|
| real | (1032,697)–(1142,1136), the merged landing + flights (7.5 m²) | — | the stairs-are-furniture merge step 3 measured |
| kitchen-unit / sofa-cushion cells | 12: (222,484)–(263,514), (222,518)–(263,549), (222,553)–(263,583) [the sofa], (209,667)–(243,702), (209,706)–(243,740), (209,744)–(243,778), (212,782)–(240,817), (209,821)–(243,856), (218,860)–(264,894), (335,860)–(368,894), (372,860)–(406,894) [the units], (486,872)–(521,906) [the tall cupboard] | 0.24–0.38 m² | red 1.5 px faces (paths 503, 947, 948, …) |
| slivers | (984,775)–(1040,792), (315,928)–(371,945) | 0.21 m² | same-pen red pairs th 2.5–22 |
| strip | (970,653)–(1082,687), cut off room (970,409)–(1142,689) | 0.93 m² | red face 3044 (116 px) + red pair th 18.2 |
| room splits | (198,1086)–(384,1119) off (198,1020)–(382,1119); (819,1144)–(1031,1179) off the bedroom (819,1144)–(1142,1373) — both parents still match at IoU 0.58 / 0.85 | 1.5 / 1.8 m² | red faces 878 (191 px, the wardrobe front) and 3028 (216 px, the bed) |

**All 17 are fenced by ink in the red furniture pen (1,0,0)** — checked face
by face and, for the same-pen pairs, member by member (every member 100 %
red). None is a component at identity: the red pen is not a wall pen there.
The room stage's `ROOM_WALL_PEN_MIN_FRAC` (0.15) makes a pen a wall pen when
its PAIRED stroked face length reaches 15 % of the network's total:

| s01 pen | identity paired px (share) | 0.542 paired px (share) |
|---|---|---|
| black (walls) | 8,991 (56.0 %) | 8,292 (52.3 %) |
| magenta (walls / hatch) | 3,740 (23.3 %) | 4,327 (27.3 %) |
| **red (furniture)** | **2,203 (13.7 %) — not a wall pen** | **2,409 (15.2 %) — WALL PEN** |
| blue (dimensions) | 1,108 (6.9 %) | 825 (5.2 %) |

At 0.542 the red pen gains 33 thin same-pen pairs (th 2.5–4.8 px, sofa arms
and bed frames drawn as double lines; identity's red pairs start at 5.8 px)
while blue loses 283 px and black 700 px, and 15.2 % ≥ 0.15 turns every red
1.5 px stroke into a lone barrier face at the wall pen's own weight. The
fraction is a knife-edge on both sides — 0.91× below the gate at identity,
1.01× above it at the true factor — and the ablation's four independent
"cures" (face floor, pair overlap, collinear tolerance, through cap, each
alone) are four ways of nudging that ratio back under 15 %, none of them a
discriminator. On the rest of the corpus the gate is comfortable: every sheet
with a second pen has it at ≥ 34 % (s03's grey 0.58, s04/s08's grey 0.6 —
existing-wall pens) or ≤ 10.4 % (s03's grey 0.73, s02's joinery pen 6.4 %,
s17's orange demolition pen 0.8 %); s01 is the only sheet whose furniture pen
carries more than a tenth of the pairing.

Confirmed by the reviewer (2026-09-05) with two additions: raising
`ROOM_WALL_PEN_MIN_FRAC` alone from 0.15 to 0.16 removes all 17 phantoms at
0.542 and leaves only the merged landing (the red-pen cause, directly); and
holding each of the four interaction gates at identity puts red at 13.65 /
13.88 / 11.79 / 14.90 % (face floor / pair overlap / collinear tolerance /
through cap), so the attribution stands. s12 is multi-pen too and was
missing from my corpus table: black 59.1 %, grey 40.9 % — on the ≥ 34 %
side. 0.16 is a number on a 1.05× margin, not a rule.

What a draughtsperson does differently: walls carry MATERIAL (s01's black and
magenta bands are hatched; its 33 red pairs and 27 red thick-tier candidates
carry 0 marks — step 3's "27 fail with zero marks: kitchen units, the
bath/stair box, the flights"), and wall runs are room-long (red's longest
paired run is 109 px, the sofa back, at both factors; black's 493–497,
magenta's 567). I proposed either as a discriminator; **the reviewer
measured both on the other multi-pen sheets and neither separates**: a
hatched-band share fails the true unhatched wall pens of s02, s04, s08 and
s12, and the longest paired run overlaps (s03's NON-wall 0.73-grey pen
reaches 491.5 px while the true wall pens s02 black and s03 black stop at
430.6 and 462.0 px). A separating wall-pen rule for colour-coded sheets is
still to be found; **its own iteration, and the pen census has to include
every multi-pen sheet (s01/s02/s03/s04/s08/s12/s17).**

Picture: `step9_s01_living_room_furniture_pen_flip_identity_vs_0542.png`
(red = faces in the furniture pen, blue = barrier, green = rooms).

## 3. The three stair-split rooms — unchanged, the user's call

Exactly step 3's and step 8's finding: (1090,699)–(1142,876) and
(1033,925)–(1142,1134) come out as one landing room, and the CPD cupboard
(466,920)–(521,1056) opens into the hall through the flight below it, because
at 0.542 the 19.5 px cap no longer anchors s01's open-headed stair arrows out
of the stair zone and the flights open (stairs are furniture). Picture:
`step8_s01_stair_rooms_identity_vs_true_factor.png`.

## What `_gate_denominator` needs before it can move (revised after review)

1. The user's verdict on the three stair rooms — **given 2026-09-05: retire
   all three (by hand, once s01 runs at 0.542) and re-review the merged
   landing and the hall+CPD through `tools/review.py`.**
2. The hall at 0.542: ONE rule, a material-seeking tail (§1b as corrected —
   the nearest wall material outward from an un-anchored hinge-edge end,
   a perpendicular jamb return included, within a world cap; the jamb
   block's right face already carries barrier rights at 0.542, so no
   hatched-pier rule is needed). Plausibly generic: its true class on the
   corpus includes s05 door_0007 (135 mm), s17 door_0004 (169 mm), s18
   door_0018 (220 mm) and s01 door_0002 (203 mm, the reviewer's numbers);
   its false class is measured below (`material_seek_probe.py`). Its own
   iteration: census, synthetic test, rule, sweep.
3. A wall-pen discriminator that is not the paired-length fraction (§2) —
   still to be found; both candidates I proposed fail on the other
   multi-pen sheets.

`_gate_denominator` stays unchanged until both exist — the reviewer and I
agree on that, not on my first rationale ("three one-sheet rules"): the
hall's rule is one and may be generic. The design note stands as context:
`SCALE_FACTOR_MEASURED_ONLY` already gives s01's takeoff its 1:92.2 numbers,
and every sheet drafted at a standard scale already runs at its true
factor; s01 is the only measured-scale sheet.

## Pictures in this directory (none shows an address)

`step9_s01_hall_door_doorway_plug_identity_vs_0542.png`,
`step9_s01_living_room_furniture_pen_flip_identity_vs_0542.png`.

## Residue / not in scope (one line each)

- (Withdrawn after review.) I listed a 35 px BLUE dimension line (path 3281,
  y = 696) among the faces at door_0003's and door_0006's tail ends and
  called it their anchor; the reviewer checked that it has no barrier rights
  at either factor and that removing all 17 blue primitives in that band
  leaves both doors' plugs unchanged — I had listed `network.faces` near the
  point, not the barrier. The mixed blue/magenta PAIRS (`_pens_compatible`)
  are real but not causal there.
- The hall's corner jamb block (20.5 px, 4 marks) still fails the thick-tier
  run/span floors at 0.542 (step 3); inert for the leak (its face buffer
  reaches the same x as the segment did).
- The 0.542 hall/living blob matches the living room at IoU 0.50 — any move
  that merges them costs two lines, not one.

## Numbers

lost **0** · returned FPs **68** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** (no code change; the true factor as it stands would be
4 lost / +17 phantoms / +1 real on s01) · **next**: the material-seeking
tail as its own iteration (census in §1b, then test → rule → sweep), then a
separating wall-pen rule, then `_gate_denominator`, then step 4.

**Decisions**: (1) the stair rooms — decided (retire all three, re-review
the merged rooms when s01 runs at 0.542). (2) The COLLINEAR jamb seek is
refuted by its census (§1b); the MATERIAL seek the reviewer proposed is the
next iteration unless the user says otherwise. (3) `_gate_denominator`
unchanged until (2) and a pen rule ship.

## Review (2026-09-05, an independent agent, `step-9-review-prompt.md`)

Claims 1, 2, 3, 5, 6 confirmed with fresh runs (byte-identical census
data). Corrected here from the review: claim 4's minimum seal (9.52 →
9.57 px, 17.65 at 1:50); claim 7's "every other only: → 0/0" (two abort on
the cap-ordering assertion); claim 8's counts under exact barrier
eligibility (308/396, 132 candidates, 49 under 300 mm) and its subclaim (e)
— the block's right face keeps barrier rights at 0.542, so a material seek
reaches it without any pairing change and the hall needs one rule, not two;
the blue-dimension residue (withdrawn, not causal); and §2's two
discriminator candidates (neither separates on the other multi-pen sheets).
The reviewer's proposed material-seeking tail is taken up in §1b with its
false-class census.
