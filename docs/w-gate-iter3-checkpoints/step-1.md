# W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule")

Branch `fix/section-line-dashes-not-hatch` from `recal/w-gate-iter2` (main is
still `f5682fc`; iteration 2 is not merged, so this branch carries it).
Baseline: the iteration-2 tree's own sweep, snapshotted for all 20 slugs
(71 returned FPs, 0 LOST, 5 unreviewed). 2026-09-04.

## What the measurement said (the brief's premise was wrong)

The brief named the s02 WC phantom's material as "the dashed section line's
dashes" and asked for a mark-class rule. Reproducing the Group 2 trial in the
census harness (cap 40 + face floor 9) and tapping the material gate on the
band (1070.66,698)–(1070.49,844), th 38.25: it counted **4 marks at
2.75/100 px, span 0.93** — two 13 px X symbols, one at each END of the band
(y 702 and 838; paths 5731/5732 and their twin), 2.7 px inside the wall
face. The section line's dashes are PDF-dashed strokes and never enter the
mark list. Neither "section-line dashes" nor "cupboard X's" is the false
class here; two corner symbols are.

Six discriminators were then measured on every material-OK band of ten
sheets (161 bands) against the phantom:

| feature | phantom | real bands | separates? |
|---|---|---|---|
| distinct mark positions | 2 | s02's stud partitions pass on 2–3 X-blocks | no |
| max gap between positions | 136 px | s02 real 107 px, s15 113, s17 80 | no (1.27×) |
| marks spanning both faces | 0/4 | 0 on most s02/s17/s03/s08/s15 bands (inset hatch, blocks) | no |
| Σ mark length / band area | 0.0095 | corpus min 0.0109 (s01), 0.013 (s15) | no (1.15×) |
| median mark length / T | 0.35 | 0.05 (s01), 0.07 (s17 stipple), 0.14 (s15) | no |
| X size / T | 0.35 | crossings down to 0.15 (s18) | no |
| **density vs the hatched wall sharing the far-side face** | **0.11×** | **≥ 1.0× everywhere: s02 4.2/4.7, s01 8.0, s15 10.4, s18 1.0, s03 1.4/1.5, s05 1.56** | **yes, 9×** |

## Rule (`detection/walls.py::_claims_far_side_sparse`, `WALL_FAR_SIDE_DENSITY_RATIO` 0.33, D-class)

A material-gated (weak/thick) pair that shares a face with a kept, tighter,
hatched strong pair lying on the FAR side of that face is the room, not a
second wall, when its own marks are under 0.33× that wall's density. A
wall's material lies on one side of each face; the hatched side is the wall.
It is the weak-tier analogue of `_claims_far_side_pair`, which exempts any
band with material (the exemption the WC's two symbols satisfied). Geometry
mirrors that rule (shared face index, meaningfully tighter, centred beyond
the face, ≥ half-run overlap); only a hatched far wall claims (density 0 says
nothing). `_band_has_wall_material`'s mark selection is factored into
`_band_material_ts` so both bands are measured identically.

Tests (`tests/test_wall_network.py::TestWeakFacePairs`):
`test_far_side_sparse_band_is_the_room` (a hatched 12 px wall, a hairline
30 px into the room, two 13 px X's at the band's ends, 2.86/100 px — the
phantom pair must not form; fails with the rule disabled) and
`test_far_side_band_with_wall_density_stays` (the same band hatched like the
wall pairs). Full fast tier green except the two InquirerPy import errors.

## Sweep 1 — the rule alone (cap 36)

0 LOST · 71 returned FPs · 5 REVIEW — verdicts byte-identical to the
iteration-2 baseline; `tools/diff_room_polygons.py`: 0 changed, 0 added,
0 removed. The rule is inert at cap 36 on this corpus (no weak pair today
sits in that configuration) and bites only once the cap admits the WC band.

## The cap-40 retry — harness pre-check on the named sheets, NOT shipped

| sheet | rule alone | rule + cap 40 |
|---|---|---|
| s02 | identical | **identical — the WC phantom is gone** (single-sheet regress at 40 confirms: 0 polygons changed) |
| s01 | identical | room_0001 IoU 0.994 — the 38.5 px kitchen units (600 mm at 1:92.2) still pair as a plain strong pair; not this rule's domain |
| s03, s05 | identical | identical |
| s17 | identical | −4 recorded phantoms (the reveal strips) |
| s16 | identical | −1 recorded phantom; six outlines move 0.96–0.99 |
| s15 | identical | +1 phantom (annotation pocket (1480,698)–(1595,792)), room_0005 0.969 |
| s11 | identical | +1 phantom (wall-recess box (1030,1330)–(1123,1360)), room_0003 0.918 |
| s18 | identical | +1 phantom (tree strip (156,724)–(197,863)) |

The brief's conditions for shipping 40 were: rule alone green (yes), s01's
units must not pair (no), the s11/s15/s18 phantoms must stay out (no). Two
of three fail, so the cap stays 36 and no cap-40 corpus sweep was spent. Net
at 40 with this rule would be −5 recorded phantoms, +3 new ones, plus s01's
hob and s11/s15/s16 outline moves. Pictures:
`step1_s02_wc_cap40_without_rule.png` (the Group 2 notch); with the rule the
WC is identical to baseline.

## What blocks the cap now

- s01's kitchen units (38.5 px) — s01's true-scale factor (iteration 3 step 3).
- s11's wall-recess box and s15's annotation pocket — the deeper band-pocket /
  recess class queued in `docs/hatch-cell-chords-handoff.md`, not bundled here.
- s18's tree strip — a boundary-line pocket outside the building; same queue.

## Reseed

No room outline changed on the shipped tree; nothing to reseed.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 (the rule's payoff is deferred until the cap can move) · **next:
step 2, the hinge-less swing-side veto** (then the seal retry), then step 3.
