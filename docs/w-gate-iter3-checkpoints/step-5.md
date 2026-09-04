# W-gate iteration 3 — step 5: plug tails end AT the material they touch (`_clip_plug_tails`)

Branch `fix/plug-tail-ends-at-material` from `fix/short-piece-material-inherit`
(be5509e, which carries steps 2 and 3; main is still `ee0f52f`). Baseline: that
tree's own sweep, re-run in four background groups and snapshotted for all 20
slugs (71 returned FPs, 0 LOST, 5 unreviewed). 2026-09-04.

## What the measurement said (`tools/census_scratch/probe_tails.py`)

Every kept plug's two tails on s02/s01/s15/s04 at seals 12 and 15, measured on
the unmodified tree: today's tail length (the plug's axial extent beyond the
bbox corner) against the exact end of the wall material inside the tail's touch
envelope (the SEAL-long spine buffered by `ROOM_PLUG_HALF_WIDTH_PX`, round caps
— the region any tail sample touches). Classes: **continues** — material runs
past the tail's reach (a jamb, a band running on); **nib** — a clearance gap,
then material ending inside the reach; **band-end** — material at the corner
already, ending inside the reach (an island the plug shadows, a band the edge
lies on); **none**.

| sheet | seal | continues / band-end / nib / none | tails past their material | overshoot px (min–max, median) |
|---|---|---|---|---|
| s02 | 12 | 98 / 63 / 1 / 4 | 3 | 1.5–3.5, 2.4 |
| s02 | 15 | 83 / 49 / 2 / 2 | 47 | 0.9–5.0, 4.7 (door_0050's four bar tails: 4.8) |
| s01 | 12 | 25 / 6 / 1 / 0 | 7 | 1.0–3.2, 3.1 |
| s01 | 15 | 23 / 4 / 1 / 0 | 5 | 1.9–4.0, 2.1 |
| s15 | 12 | 474 / 52 / 0 / 0 | 45 | 1.3–4.4, 2.9 |
| s15 | 15 | 414 / 136 / 0 / 0 | 134 | 0.6–4.6, 1.5 |
| s04 | 12 | 23 / 23 / 0 / 0 | 1 | 3.6 |
| s04 | 15 | 22 / 6 / 0 / 0 | 5 | 2.6–4.9, 4.9 |

Not one "continues" tail overshoots (it cannot — the material outlasts the
reach), so class (a), a tail INTO a jamb, is untouched by construction; the
s01 nib (door_0003's bottom edge, material 0.7–4.7 px past the corner, tail
7.9) and every band-end overshoot are class (b). **The brief's "inert at seal
12" expectation was wrong**: s02's bar is missed at 12 only because the sample
phase lands at 7.95 and 12 px out (neither within 5 px of the bar's end at
2.0), while at 15 a sample lands at 6.7; on s01/s15/s04 the same overshoot
exists at 12 on 7/45/1 tails.

**Convention** (stated before coding): a tail exists to reach the jamb the
bbox stopped short of; it ends where the material it touches ends, never
beyond it — material continuing past the reach keeps the whole tail, material
ending inside the reach ends the tail there.

## Rule (`detection/rooms.py::_clip_plug_tails`, `_tail_material_end`)

After `_door_plugs` has trimmed a tail to its farthest touching SAMPLE, each
bbox-edge plug is cut to the slab between its two material ends along the edge
line, where a material end is the farthest wall material inside the tail's own
touch envelope, clipped to [0, SEAL]. The cross-section fit and lateral position
are untouched.

**Applied AFTER the plug is classified, and why.** The first cut clipped the
spine inside `_door_plugs`. That was not inert in the way expected: the
fallback tier's in-wall gate (`ROOM_PLUG_IN_WALL_FRAC` 0.80, applied in
`detect_rooms` to the polygon `_door_plugs` returns) was calibrated with the
out-of-material tails in its denominator (phantoms ~0.77, on-plane 0.84+), so
clipping first raised the fractions and let **57 more fallback-tier plugs
through on s15 (263 → 320)**; seven cut 8–38 px² notches into rooms — measured
on UNSIMPLIFIED polygons (scratch `unsimplified_check.py`, the simplifier off,
the clip toggled by monkeypatch): s15 rooms 0006 −11.3, 0010 −10.3, 0014 −7.6,
0020 −11.2, 0021 −37.6; s17 rooms 0022 −10.6, 0026 −15.7. A shorter barrier
cannot remove free space, so a loss meant a second rule had moved. The clip
now runs after kind, hinge restriction and the in-wall gate have been decided
on the sample-trimmed geometry; with it **no room on s02/s15/s17/s18 loses any
unsimplified area** (every difference is a gain).

Tests (`tests/test_room_detection.py::TestPlugTailTrim`):
`test_tail_ends_at_the_material_it_touches` (a 12 px bar island, dilated
198–214 × 138–202, a 12×48 fallback door on it: every plug must lie inside the
bar; without the clip the top-edge plug starts at x=196, fails) and
`test_tail_past_a_bar_end_does_not_pinch_the_neck` (the same bar 18 px below the
top band's dilated face, over the 16 px pinch; untrimmed the tails ran 4 px past
the bar, the neck fell to 14 px and the opening fenced it — the neck midpoint
must be room floor; fails without the clip). Both failed for the stated reason
before the code existed. `test_tail_trimmed_to_jamb_material`,
`test_tail_kept_on_through_material` and `test_plug_fits_the_jamb_cross_section`
still pass (class (a) unchanged). Full fast tier: 1383 tests, only the two
pre-existing InquirerPy import errors.

## Net effect (from the crops, my verdicts) — 22 rooms on 6 sheets, all gains

| sheet / room | what moved | px² | my read |
|---|---|---|---|
| s01 room_0001 | bottom edge over the hatched pier sits on the drawn face (door_0002's right-edge plug tail 12 → 11 px), a 59 × 0.5 px sliver | +29 | win |
| s01 room_0004 (hall) | the strip above door_0011's sliding-panel plugs, whose tails ran 3 px past the material at y 1009 | +32 | win (`step5_s01_room_0004_hall_stub_before_after.png`) |
| s01 room_0006 | the matching corner notch at (382,1006) | +9 | win |
| s02 room_0000 | door_0055's interrupted plug tail (12 → 9.6 px), a 3 × 5 notch | +12 | win (`step5_s02_room_0000_stub_before_after.png`) |
| s03 room_0004 / 0005 | a doorway-plane edge straight instead of a 55 px lean; a 3 × 7 notch | +60 / +18 | win |
| s11 room_0005 | the stair room's top edge, a 97 × 1 px lean | +88 | win |
| s15 room_0000 (corridor) | eight stubs at fallback-box plug ends (416 px² of them along the en-suite wall at (1344–1441, 782–786)) | +790 | win |
| s15 room_0003 (en suite) | the top-left corner chamfer (265 px²) | +274 | win |
| s15 room_0005 / 0021 / 0024 | corner beside a dimension tick; two "810mm door set" top edges leaning along the leaf | +43 / +70 / +303 | win (`step5_s15_room_0024_door_set_slant_before_after.png`) |
| s15 room_0008 | bottom edge lean, 78 × 4 px | +319 | win (`step5_s15_room_0008_stub_slant_before_after.png`) |
| s17 room_0027 (corridor, IoU 0.954) | a 3.8 px stub at the top made the simplifier lean the whole 467 px right edge; now straight on the wall face | +742 | win (`step5_s17_room_0027_corridor_stub_slant_before_after.png`) |
| s17 room_0006 (stair strip) | the bottom notch (148 px²) gone; the top step is redrawn as a slant (−39, a vertex choice — unsimplified loss 0) | +113 | win, cosmetic trade |
| s17 rooms 0002 / 0010 / 0013 / 0016 / 0025 / 0031 / 0032 | notches at leaf ends, closet bottom-edge leans, a doorway-gap edge, three stubs on the wardrobe room's right edge | +24 / +16 / +41 / +6 / +164 / +188 / +36 | win |

Net phantoms: 0 → 0 (no entity appears or vanishes anywhere). Total outline
regained +3,377 px²; s18 and the other 13 sheets are polygon-identical.

**s01 and s02 at f = 1.0 moved** (+70 and +12 px², three and one rooms, every
piece a stub the rule removes). The run's rules say they must not change until
`_gate_denominator` moves s01; the change is attributable to this rule alone and
is in the direction of the drawn ink, but it is the user's call — see the
decision below.

**The payoff at seal 15** (harness, `attrib_rooms.py` vs the baseline snapshot):
s02 is now identical at 13, 14 and 15 (before: BEDROOM 2 IoU 0.988 at 15, the
bar column wrapped — `step5_s02_bar_seal15_before_after.png`). Still moving:
s15 rooms 0019/0020/0023/0024 at ≥ 14 (the dash row, step 6), s01 room_0005 at
13–14 (the plug-fit flip) and, pre-existing and not yet measured, s01 room_0003
at 14–15 (0.985) and s04 room_0001 at 14–15 (0.987).

## Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline)

| | lost | returned FP | REVIEW | polygons |
|---|---|---|---|---|
| baseline | 0 | 71 | 5 | — |
| **step 5** | **0** | **71** | **5 — verdict lines byte-identical** | 22 changed (all gains), 0 added, 0 removed (`tools/diff_room_polygons.py` on all 20) |

Room labels reseeded on s01/s02/s03/s11/s15/s17/s18 (Gemini; the label cache is
keyed on room geometry, so every moved room missed). s03's baseline had been
missing its labels (`ROOM_LABEL_NO_GEMINI` in the baseline warnings) and has
them now.

## Residue / not in scope (one line each)

- The in-wall gate measured on clipped plugs is a different (weaker) gate;
  re-calibrating it on tail-less plugs is its own iteration, not this one.
- s01 room_0003 and s04 room_0001 move at seals 14–15 with or without this
  rule — unmeasured, ahead of step 7.
- `_door_plugs`' end-anchor windows still count samples in the overshoot zone
  (their probes hit nothing); harmless, left alone so the fit is byte-identical.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 (+3,377 px² of stub-notched outline regained on 22 rooms; s02's seal-15
notch gone) · **next: step 6** (dash rows: s15's "steel ridge beam" row —
check `tests/ground_truth/s15.json` for rooms 0023/0024 first), then step 7
(the seal retry); the user's s01 stair-room decision is still pending.

**Decision needed**: accept and commit this branch (code + tests + prose + the
six PNGs in this directory, none of which shows an address) knowing s01 (+70
px², 3 rooms) and s02 (+12 px², 1 room) moved at f = 1.0, or revert.
