# W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto")

Branch `fix/hingeless-swing-side-veto` from main `ee0f52f` (which carries
iterations 2 and 3-step-1). Baseline: main's own sweep, re-run and
snapshotted for all 20 slugs (71 returned FPs, 0 LOST, 5 unreviewed).
2026-09-04.

## What the measurement said (the brief's premise was wrong, twice)

The brief attributed the seal-15 regressions of Group 2 to a hinge-less
door's SWING-side edge qualifying as an interrupted run (its ends within
SEAL + 5 px of two walls), and asked for a veto keyed on anchor geometry.
Tapping every `_door_plugs` call in the census harness at seals 12/13/14/15
on s15, s02, s01 and s04 (scratch probes, per door, per edge, per profile
sample) gives a different mechanism at every site:

| site (Group 2 verdict) | what actually happens | class |
|---|---|---|
| s15 rooms 0023/0024 (−5.4k px² each at ≥ 14), 0019/0020 | door_0013 — a HINGED single leaf, hinge edges [top, left] — loses its DOORWAY plug: the dashed "steel ridge beam" line (a row of 14.8 px strokes in a 2.0 px pen, each a strong barrier face) crosses the doorway plane at x≈938, the centre of the 85 px top edge; the mid-window in-plane count is 2/10 at seal 12 and 3/11 = 0.27 > `ROOM_PLUG_MID_COV_MAX` at 14 and 15 (the sample phase shifts with the tail length); the 0.67 door falls to the dilated-bbox stamp and the swing square is fenced | dash rows — excluded from this iteration |
| s02 BEDROOM 2 notched around the "A" marker at 15 | door_0050, the 0.35 fallback door on the section-marker BAR (a filled ring — barrier material, an island in the room): its two full-cover plugs shadow the bar's long edges (in-material 1.00 at 12); at 15 each tail ends at the last sample within the 5 px touch tolerance, 4.8 px PAST the bar (plug 297.9–372.0 vs bar 302.7–367.2, in-material 0.87 ≥ the 0.80 gate); the neck between the bar and the top wall shrinks 20.5 → 15.7 px, under the 16 px free-space pinch, and the bar column is fenced (barrier +134 px², room −1,437 px²) | plug tails overshooting the material they shadow |
| s01 room_0005 at 13–14 (IoU 0.957) | door_0002's right-edge interrupted plug: the cross-section fit gives 4 px (462.5–466.5) at 12 and 15 but 10 px (462.5–472.5) at 13–14 — the anchor sample set shifts and the two ends disagree, so the fit falls back to the full ±5 envelope; −305 px² | plug-fit knife-edge |
| s04 room_0002 +10,345 px² at 15 (the "improvement") | door_0001's top jamb is 12.4 px past the leaf bbox — a door LINING — and the lining ring is rejected (below), so at seal 12 the anchor coverage is 3/7 = 0.43 < 0.5, no plug qualifies, and the bbox stamp fences the swing square; at 15 it is 4/7 | a gap in `_is_door_lining` |

No door on those four sheets gains an interrupted plug on a hinge-less
swing side between 12 and 15. And the hypothesised discriminator does not
separate on the TRUE class either — a survey of every kept interrupted plug
on the corpus at seal 12 (158 plugs), classifying each end anchor by the
wall elements the touching samples lie on and by the material's extent
across the edge line:

| class | count | anchors |
|---|---|---|
| hinge-derived doorway plugs (true) | 100 | 44 par/par · 24 par/perp · 18 perp/par · 6 perp/perp · 8 other; 30 have an anchor spanning > 40 px across the edge, 2 both anchors (s15 door_0011 96/86 px, s07 door_0004 48/71) |
| hinge-less, interrupted | 44 | 13 garden-pair doorway edges (already restricted by `_open_leaf_edges`), 4 folding planes, 26 fallback-tier box edges (0.35), 1 s18 single leaf (door_0021, par/perp) — no swing side among them |

A veto on "crossing, none along" would kill real doorways (s01's main
entrance door_0000 anchors on the 21/22 px jamb END CAPS of its 22 px wall,
perp/perp; s15 door_0013's own doorway anchors sit in the corner where the
corridor's left wall meets the top band) and has no false instance to
remove. Nothing was built for it; the synthetic fixtures stay at 26–28 px.

## The rule that the measurement supports (`detection/rooms.py::_is_door_lining`)

s04 door_0001 (MASTER BEDROOM, hinge edges [bottom, left], doorway plane
x=1854): two stroked `qu` rings, paths 946/949, 14.2×12.4 px in the 0.56 px
grey joinery pen, fill the 12.4 px between each jamb face and the leaf bbox.
The bottom one shifts one ring-length down onto the divider (dilated
span 18.2 px ≤ the 22.2 px probe) and is accepted. The top one is at a
CORNER — the divider meets BATHROOM 02's bottom band there — so shifted up
it lands in the perpendicular band, 31.3 px across the probe, exactly the
signature of the wedged fixture the rule excludes.

Convention: a doorway is cut OUT of a wall, so the wall resumes beyond the
far jamb whatever happens at the near one. The ring is also a lining when
the strip of its own across-range one to two ring depths past the opening's
far edge (past the far jamb's twin lining) is drawn wall material with the
ring's own cross-section — the same cover (0.80) and span (depth + 4 + 4)
gates as the near shift. The wedged fixture's across-range lies on the room
side of the wall plane; beyond the far jamb that strip is floor.

| feature | s04 path 949 (corner lining) | s04 path 946 (straight lining) | wedged fixture (synthetic) |
|---|---|---|---|
| near shift: cover / across span | 1.00 / **31.3 px > 22.2** | 1.00 / 18.2 px | 1.00 / whole probe |
| far strip: cover / across span | **1.00 / 18.2 px** | 1.00 / 18.2 px | **0.14** (2 of 14 px on the divider's dilation) |

Corpus telemetry (`_is_door_lining` tapped, near-only vs with the strip):
rings admitted by the far strip alone — s04: path 949; s18: two 2.5 px
jamb stops at (1706,1027) and (1801,1283), one where a closed leaf meets
the wall line and one at a frame's hinge corner, inert (no polygon moves).
Every other sheet: 0 (s01/s03/s05–s07/s09/s11–s13/s15–s17/s19/s20 admit no
ring by either path; s02 10 rejected, s10 19, s14 11 — all still rejected).
s01 and s02 draw no lining rings, so "true (s01)/(s02)" is not measurable
on this feature; the corpus telemetry stands in.

Tests (`tests/test_room_detection.py::TestDoorLiningRings`):
`test_corner_lining_anchors_the_doorway_plug` — a 14 px divider ending at
the room's top band, a 112 px opening from the band's face, 12.4 px linings
at both jambs, an 88 px leaf bbox spanning the band; the swing square must
be room floor and the corner lining wall (fails without the rule: the
swing square is fenced, verified by reverting `rooms.py`); and
`test_fixture_box_at_the_corner_is_not_wall` — the same box on the room
side of the divider's face changes no room. Full fast tier: 1381 tests,
only the three pre-existing failures (two InquirerPy import errors,
`test_takeoff_fn_equivalence`).

## Net effect on s04 (from the crops, my verdicts)

| id | what it is | before | after | my read |
|---|---|---|---|---|
| room_0002 | MASTER BEDROOM | swing square of door_0001 fenced out (bbox stamp), 206,754 px² | outline runs along the divider face, both linings excluded, 217,499 px² (+10,745, IoU 0.951) | win |
| room_0004 | the unlabelled room below the door | a 10 px strip beside the divider fenced by the same stamp, 37,023 px² | 38,150 px² (+1,127, IoU 0.970) | win |

Net phantoms: 0 → 0 (no entity appears or vanishes anywhere). Pictures:
`step2_s04_room_0002_master_bedroom_before_after.png`,
`step2_s04_room_0004_before_after.png` (from `room_shape_crop`);
`outputs/compare/s04/page_01_side_by_side.png`. Mechanism pictures for the
attribution above: `step2_s15_door_0013_dash_row_mid_cover_12_vs_14.png`
(seal 12 plug in orange with the dash row's barrier pieces crossing it;
seal 14 the bbox stamp) and `step2_s02_bar_tail_overshoot_12_vs_15.png`
(plugs coincide with the bar at 12; at 15 the tails reach past it and the
outline wraps the column).

## Sweep (`tools/regress.py`, full corpus in four background groups, vs the main baseline)

| sheet | lost confirmed | returned FP | new REVIEW | polygons |
|---|---|---|---|---|
| s04 | 0 | 0 | 0 | room_0002 IoU 0.951 (+10,745 px²), room_0004 0.970 (+1,127) |
| all other 19 | 0 | 71 (unchanged, byte-identical reports) | 5 (unchanged) | `tools/diff_room_polygons.py`: IDENTICAL on every sheet |

s04's room labels reseeded (Gemini run, no `ROOM_LABEL_*` warning; the
re-sweep hits the cache and names the Master Bedroom again). No other sheet
changed, nothing else to reseed.

## The seal retry — NOT attempted, and why

The brief allowed 12 → 15 only if the veto alone swept green with s02/s15/s01
unchanged. Measured with the harness on this tree: at 14 s15 still loses the
corridor and lounge swings (the dash row across the doorway is untouched by
anything in this step), at 15 s02's bar is still notched (the tail
overshoot), and s01 room_0005 still moves at 13–14. The s04 payoff the
retry was meant to regain is now obtained at 12. `ROOM_OPENING_SEAL_PX`
stays 12; its comment, `TestPlugSealReach`, findings §4 and group-2.md now
state the measured mechanisms instead of the swing-side one.

## Residue / not in scope (one line each, each its own iteration)

- Dash rows as barrier faces (s15's beam line splits the corridor from the
  lounge AND crosses door_0013's doorway plane) — queued already.
- A trimmed plug tail ends AT the material it shadows, not up to 5 px past
  it (s02 door_0050) — a prerequisite for any seal move; inert at 12.
- The plug cross-section fit's fallback to the full envelope when the two
  ends disagree (s01 door_0002 at 13–14) — a knife-edge, inert at 12 and 15.
- Sub-jamb-scale rings (2.5 px) pass the lining gates on s18 — inert; a
  minimum ring depth would be a separate discriminator.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 (+11,872 px² of real room outline regained on s04) · **next: step 3**
(short-piece material rule for the thick tier, `ablate.py s01 s01mode`, then
`_gate_denominator`) — the handoff carries the prompt.

**Decision needed**: accept and commit this branch (code + prose + the four
PNGs in this directory, none of which shows an address), or revert.
