# W-gate iteration 3 — step 11: the DOORWAY VETO on the wall-pen share gate — s01's 17 furniture-pen phantoms gone at its true factor; corpus byte-identical

Branch `fix/wall-pen-discriminator` from `fix/material-seeking-plug-tail`
(7a32db4, which carries steps 2, 3, 5–10; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups (s18; s16
s11 s15; s01–s07; the rest) and snapshotted for all 20 slugs
(`outputs/regress_baseline/<slug>/2026-09-05_15-14-*` … `15-16-*`) — **0 LOST,
68 returned FPs, 0 REVIEW**, verdict lines byte-identical to step 9's
`sweep_base_all.txt`. 2026-09-05. Not committed.

## The symptom

s01 at its true factor (0.542) in the harness: 17 phantom rooms fenced by
the RED furniture pen (12 kitchen-unit / sofa-cushion cells of 0.24–0.38 m²,
2 slivers, 1 strip, 2 room splits — step 9 §2), because
`ROOM_WALL_PEN_MIN_FRAC` (0.15 of the network's paired stroked face length)
makes red a wall pen at 15.2 % there and not at 13.7 % at identity: 33 thin
same-pen sofa-arm/bed-frame pairs (th 2.5–4.8 px) appear at 0.542 while black
loses 700 px and blue 283. A knife-edge on both sides; 0.16 is a 1.05× number.

## The census (`tools/census_scratch/step11/`, every multi-pen sheet, s01 at both factors, the pipeline's exact inputs)

**The brief's classes, corrected from the pictures** (`render_pens.py`,
scratch overlays of each pen's faces): s03's 0.73 grey (10.4 %, "non-wall")
draws the existing ground-floor plan's rear-extension walls — bathroom,
bedroom, the living/lounge dividers — a wall pen with few openings; s02's
6.4 % "joinery" pen is the title block's logo lettering (paired letter
strokes). False class: s01 red (furniture, sanitary, stairs) and blue
(dimensions), s02's four annotation pens, s17's orange (demolition ticks,
the utility/WC line) and red (the site boundary dash row), the 0 % red pens
of s04/s08/s12. True class: s01 black + magenta (the extension walls and
the FF bathroom partitions), s02 black, s03 black + both greys, s04/s08
black + grey, s12 black + grey, s17 black.

**Per-pen features** (`pen_census.py`, `pen_census_out.txt`; ✗ = does not separate):

| feature | true class | false class | verdict |
|---|---|---|---|
| paired share | 10.4 % (s03 grey .73) … 99 % | 0 … 15.2 % (s01 red @0.542) | ✗ overlap |
| material share of same-pen segments (`_band_has_wall_material`) | **0 %** on s02 black, s04 black/grey, s08 grey/black, s12 grey; 40–81 % on s01/s03/s12 black | 0–5 % | ✗ (the reviewer's finding, confirmed) |
| pair thickness, length-weighted median | **5.3 px** (s04 black), **6.0** (s12 grey), 7.2 (s03 grey .73) … 30.5 | 6.2–12.8 (s01 red), 7.7 (s02 logo), 6.8 (s17 orange) | ✗ |
| longest same-pen segment | **31 px** (s12 grey), 116 (s08 black) … 873 | 109 (s01 red), 68–81 | ✗ |
| share of the pen's ink that pairs | **43 %** (s02 black) … 98 % | 26–100 % | ✗ |
| loops the pen closes alone (room-sized components) | 0 (s01 magenta, s03 grey .73, s08 black) … 28 | 2/8 (s01 red at identity/0.542), 0 | ✗ |
| lone-eligible ink (unpaired, ≥ the stroke gate) | 0 (s01 magenta at 1.0 px, s03 greys at 1.0 px) … 6,026 | 0 … 3,001 | ✗ |
| **doorways cut into the pen** (below) | **1–27, every pen** | **0, every pen** | ✓ |

**The doorway measure, refined three times** (`jamb_pens.py`, `tail_pens.py`,
`tail_pens2.py`, `rule_census.py`, then `implemented_census.py` on the
shipped function):

1. *Loose* — the pen's ink touches a plug tail: s01 red touches 4 doors at
   identity (unit runs and the WARDROBES end panel lie on the wall line
   beside doors), blue 3–6, s03 grey .73 3, s08 red 1. ✗
2. *Strict collinear both jambs* — a face of the pen collinear with the
   plugged edge ends at each jamb: false class 0 everywhere, but s01
   magenta 0 at identity (its two doorways are corner-hung: one jamb is a
   black return) and s02 black 2 of 15. ✗ (true-class zeros)
3. *Both tails, ink classed* — C a collinear face end, S a paired face /
   same-pen band, P a lone perpendicular end, x a crossing: with C or S at
   BOTH tails the false class is 0 on every sheet and every true pen ≥ 1 —
   but only on the room stage's FINAL plugs. With every pen treated as a
   wall pen (share 0), s01 blue "owns" the 1,800 garden opening at identity
   through its parallel dimension chains, which pair into 8.8–29.5 px
   "bands" whose solids reach the wall line. So the doorways are read off
   the pass-1 plugs and can only VETO.

**The rule as implemented** (`rule_census.py` → `implemented_census.py`,
`_doorway_pens` on the room stage's own pass-1 plugs): a confident
(≥ `ROOM_BBOX_SEAL_MIN_CONFIDENCE`) door's INTERRUPTED plug has two tails;
a pen forms a jamb when a PAIRED face of it intersects the tail envelope,
or a LONE face of it collinear with the doorway line (≤ `WALL_PARALLEL_ANGLE_TOL`,
both endpoints ≤ `ROOM_PLUG_NEAR_PX` off it) stops in the jamb window (the
tail plus the plug's first `ROOM_PLUG_NEAR_PX` inside the bbox — a swing
symbol overlaps its hinge jamb by the leaf thickness, 3 px on s01); the
doorway is cut into the pen forming BOTH jambs.

| sheet (f) | share-gated wall pens | doorways cut into each pen | vetoed |
|---|---|---|---|
| s01 (1.0) | black, magenta | black 6, magenta 2 | — |
| **s01 (0.542)** | black, magenta, **red** | black 5, magenta 4, red 0 | **red** |
| s02 | black | black 1 (the rest of its jambs are fill rings, pen-less) | — |
| s03 | black, grey .58 | black 14, grey .58 8, grey .73 1 (under the share: not promoted) | — |
| s04 / s08 | black, grey | 3 / 3 each | — |
| s12 (0.5) | black, grey | black 7, grey 4 | — |
| s17 | black | black 27 (orange 0, red 0) | — |
| single-pen sheets | the pen | 3–14 | — |

Without the lone-collinear clause (paired faces only) the counts differ on
s01@0.542 (magenta 4 → 3), s17 (27 → 23) and s18 (9 → 8) and no verdict
changes; the clause is pinned by the single-line-wall test below.

**Convention**: a doorway is cut out of a wall, so the pens the sheet's
doorways are cut into are its wall pens; a pen that built part of the
paired network but that no doorway is cut into drew furniture, dimensions
or annotation. False class: 0 doorways on 8 pens over 7 sheets (s01 red at
both factors). True class: ≥ 1 on every wall pen, ≥ 2 on all but s02 black
(the sole share-gated pen there — losing it would leave no owner and the
share gate standing) and s03's grey .73 (under the share anyway). The
margin is 0 vs ≥ 2 on every sheet where the veto could act.

## Fix

`detection/rooms.py`: `_doorway_pens(door_plugs, faces, paired_indices,
in_door_zone)` and a two-pass barrier build in `detect_rooms` — pass 1 with
the share-gated pens exactly as before; owners read off its plugs; a
share-gated pen with no doorway is vetoed and everything from the wall
solids to the door seals is rebuilt without it (pass 2 runs only when the
veto fires: at the sheets' factors, never). No new constant. The
`ROOM_WALL_PEN_MIN_FRAC` comment states the share is a candidate gate.

Tests (`tests/test_room_detection.py::TestDoorwayOwnedWallPens`, 6): a
black room with a doorway plus three red unit-box pairs at 22 % of the
network and a lone red line —
`test_network_building_furniture_pen_is_vetoed_by_the_doorways` and
`test_one_jamb_is_not_a_doorway` (a red unit run drawn up to one jamb)
**fail on the old rule** (2 rooms: the red line splits);
`test_the_pen_the_doorway_is_cut_into_keeps_its_rights` (the same line in
black splits), `test_without_a_doorway_the_share_gate_stands` (a closed
room, no door: red at 22 % is a wall pen — the fallback, pinned),
`test_a_rejected_door_names_no_pen` (a 0.45 door's plug seals but names
nobody), `test_a_single_line_wall_names_its_pen` (the doorway's wall drawn
as one line: only the lone-collinear clause names black). Bite-proven by
edit-and-revert: veto disabled → tests 1 and 3 fail; one jamb suffices →
test 3; confidence floor dropped → test 5; lone clause dropped → test 6.
Fast tier 1,422 tests green (one run flaked on `test_takeoff_fn_equivalence`
while the sweep groups were writing the s01 label cache — the known
concurrent-reseed flake; clean on the re-run).

## Proof

**Harness, s01** (`H.run`, exact scoring):

| | doors | windows | rooms | lost | unreviewed |
|---|---|---|---|---|---|
| identity | 11/11 | 4/4 | 12/12 | — | 0 |
| 0.542, before | 11/11 | 4/4 | 9/12 | the 3 stair verdicts | **18** (17 red-fenced + the landing) |
| **0.542, after** | 11/11 | 4/4 | **9/12** | the 3 stair verdicts | **1** — the merged landing (1032,697)–(1142,1136) |

**Corpus sweep** (four background groups vs the baseline; `diff_room_polygons.py` on all 20 slugs):

| | lost | returned FP | REVIEW | entities | polygons |
|---|---|---|---|---|---|
| baseline | 0 | 68 | 0 | — | — |
| **doorway veto** | **0** | **68** (identical lines) | **0** | **20 sheets IDENTICAL** | **20 sheets IDENTICAL** (0 changed, 0 added, 0 removed) |

s01 and s02 at f = 1.0 entity- and polygon-identical, as the rule
requires. Net phantoms at the sheets' factors: 0 → 0; at s01's true
factor: **−17** (27 rooms on the page → 10).

**Pictures** (this directory, none shows an address):
`step11_s01_ground_floor_furniture_pen_veto_0542_before_after.png` (the
kitchen units, sofa and wardrobe front fenced by red under the share gate
alone, vs the veto; red lines = furniture-pen faces, blue = barrier, orange
= door seals, green = rooms) and
`step11_s01_first_floor_furniture_pen_veto_0542_before_after.png` (the bed
frames, wardrobe end and stair box; the merged landing stays as the one
unreviewed room).

## Residue / not in scope (one line each)

- Promotion of an under-share wall pen by its doorways needs plugs that
  qualified on pen-independent material (fills, white bands, other pens);
  s03's 0.73 grey is the corpus instance and is inert (its fills seal it).
- A wall pen with NO doorway on a sheet whose doorways are cut into
  another pen (a door-less garden-wall pen) would be vetoed; no corpus
  instance — windows as a second evidence class are the natural extension.
- s02's black owns 1 doorway because its other jambs are fill rings
  (pen-less); the fallback covers the sole-pen case.
- s01's three stair verdicts and the merged landing are the
  `_gate_denominator` step's business (the user's retirement + re-review).

## Numbers

lost **0** · returned FPs **68** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** at the sheets' factors, **−17** for s01 at its true
factor in the harness (18 unreviewed → 1, rooms 9/12 with the three stair
verdicts the only losses) · corpus entity- and polygon-identical on all 20
sheets · **next**: narrow `_gate_denominator` (the user retires the three
stair verdicts by hand and re-reviews the landing through `tools/review.py`
then; s01's label cache reseeds), then step 4 (`WALL_MAX_THICKNESS_PX`
36 → 40).

**Decision needed**: accept and commit (code + tests + prose + the two PNGs
+ `tools/census_scratch/step11/`), or revert.
