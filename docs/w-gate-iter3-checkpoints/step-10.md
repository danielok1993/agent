# W-gate iteration 3 — step 10: the MATERIAL-SEEKING TAIL — s01's hall seals at its true factor; corpus verdict-identical

Branch `fix/material-seeking-plug-tail` from `recal/s01-true-factor` (c6f53e8,
which carries steps 2, 3, 5, 6, 7, 8 and 9; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups (s18; s16
s11 s15; s01–s07; the rest) and snapshotted for all 20 slugs
(`outputs/regress_baseline/<slug>/2026-09-05_13-39-*` … `13-41-*`) — **0 LOST,
68 returned FPs (24 + 21 + 3 + 20), 0 REVIEW**, verdict lines byte-identical
to step 9's `sweep_base_all.txt`. 2026-09-05. Not committed.

## s01 door — the hall merges with the living room at the true factor (0.542)

**Root cause** (rooms.py, `_door_plugs`): the doorway edge's plug tail has a
FIXED reach (bbox ± `ROOM_OPENING_SEAL_PX`, 8.13px at 0.542) while the
jamb's distance is drawn — s01 draws its swing symbols short of their
openings on the latch side (a 671mm leaf in an 847mm opening; the hall
door's latch jamb face is 14.25px = 222mm past the bbox corner at 1:92.2).
The tail's first sample stopped 4.1px off the corner jamb block's right
face (touch 2.71), the anchor window read 1/3, no doorway plug, and the
hall (392,920)–(521,1387) merged with the living room (step 9 §1).

**Convention that separates it**: a doorway is cut out of a wall, so its
latch jamb IS wall material and lies where it is drawn — the plug should
reach for it, not for a distance decided in advance. A plug that finds a
jamb by seeking is still a doorway plug only if the profile between the
jambs is empty (interrupted); a sought profile that reads "full" is a
drawn-through plane the fixed reach did not assert.

**Measured margin** (world mm at true scale; `jamb_census.py` step 9,
`material_seek_probe.py` step 9 §1b, `seek_census.py` this step):

| feature | false class | true (s01 @ 0.542) | true (s18) | true (s17 / s14) |
|---|---|---|---|---|
| distance from the un-anchored corner to the nearest wall material within the plug half-width | s14 door_0007's open-leaf tip → a wall-fill chevron ring at **296mm** (the only hit ≤ 300mm on 172 un-anchored hinge-edge ends over 18 sheets; every other hit is another opening's seal, invisible to `_door_plugs`) | hall door top edge: **149mm** to the first touching sample, 191mm to the block's right face (path 278, a 30px perpendicular face) | door_0018 right edge: **178mm** (a 139px face at 90°) | door_0004 bottom edge: **121mm** (a 32.5px band at 90°); door_0008 right edge: **76mm** (an 11.5px band at 90°) |
| kept interrupted doorway ends, jamb gap (n = 378) | — | s01's four swings 187–219mm | s18 102 | s17 110 / s14 85; every other sheet ≤ 51 |
| the cap `ROOM_PLUG_JAMB_SEEK_PX` = 250mm | 1.18× under the chevron | 1.31× over the hall (by the face) | 1.40× | 2.07× / 3.29× |

The margin on the false side is thin (one instance, 1.18×), and the
"exactly one end anchored" + "interrupted only" conditions are what keep a
leaf tip pointing at open floor from ever plugging: no leaf tip seeks
anywhere on the corpus (`seek_census.py`: four doors change, all four
hits perpendicular walls at 76–178mm).

**Fix**: `detection/rooms.py` — `ROOM_PLUG_JAMB_SEEK_PX` 29.5 (W-class,
scaled in `RoomGates.at`; 16px at 0.542, 14.8 at 1:100), `_seek_edges`
(the hinge edges of a ≥ `ROOM_BBOX_SEAL_MIN_CONFIDENCE` single; a garden
pair or slider pins no hinge, so s01 door_0015's piers at 281mm stay a
plane stamp at identity), the per-edge profile factored into
`_edge_profile` / `_EdgeProfile` with asymmetric reaches, `_seek_jamb`
(the material's outline buffered by the plug half-width, cut by the
edge's ray from the failing corner — phase-free; a perpendicular return, a
band end and a fill ring all count), and in `_door_plugs`: when a seeking
edge's fixed profile qualifies nothing and anchors at exactly one end, seek
from the failing corner, extend that end's reach to the hit plus the anchor
window, re-profile, and accept only "interrupted". Consequences handled:
the `local` clip in `detect_rooms` widened from SEAL + NEAR + 4 (27px) to
SEEK + anchor window + NEAR + 4 (65.5px at 1:50) — **proven inert alone:
the corpus sweep of that change by itself is verdict-identical and
entity- and polygon-IDENTICAL on all 20 sheets** — and `_clip_plug_tails`
takes a sought tail's own extent (the plug polygon's projection beyond the
corner) as its reach, SEAL otherwise (byte-identical for every existing
plug, whose extent is ≤ SEAL by construction). `_plane_stamp` untouched.

The seek envelope starts at the CORNER, not at SEAL: an end that touches
material inside the fixed reach but whose anchor window (28px at 1:50,
straddling the corner into the doorway by construction) is under half
covered seeks the same way and finds that material — s14 door_0008's
doorway (a jamb 9px out: touch at its first sample, window 3/7 = 0.43)
gains its interrupted plug this way, a population the step-9 probe (whose
"un-anchored" meant "no touch within SEAL") could not see. The tests pin
both the 22px case and this straddling class implicitly (the direct
fixture's return is 22px out and the window is 7 samples).

Unit tests (`tests/test_room_detection.py::TestJambSeekingTail`, 10):
`test_perpendicular_return_22px_past_the_corner_seals` and
`test_hall_doorway_seals_through_the_room_stage` (the s01 hall analogue:
a divider ending at a corner block, the door hinged on the far jamb with
its leaf parked along a partition so the leaf edge plugs and the door never
falls to the plane stamp) **fail on the old rule for the stated reason**
(no plug on the doorway edge; 3 rooms instead of 4 — the hall merged with
the room above); `test_return_past_the_cap_is_not_sought` and
`test_leaf_tip_material_past_the_cap_does_not_plug` bite when the cap is
lifted (×10); `test_seek_never_yields_a_full_plug` bites when the
interrupted-only clause is dropped; `test_fallback_tier_door_never_seeks`
and `test_seek_edges_are_the_hinge_edges_of_a_confident_single` bite when
the confidence gate is dropped; `test_sought_tail_survives_the_material_clip`
(and the hall test) bite when `_clip_plug_tails` keeps SEAL as its reach;
`test_seek_needs_the_other_end_anchored` bites when the re-profile's
both-ends requirement is dropped — the "exactly one end anchored"
precondition on its own is REDUNDANT with that requirement (relaxing it
alone changes nothing: a seek from a corner whose other end has no
material re-profiles to a failing far end), so it is kept as the cheap
filter and the rule's statement, not as a load-bearing guard. Every
bite-test edit reverted; full fast tier 1,416 tests green.

**Harness at s01 0.542** (`H.run`, exact scoring): doors 11/11, windows
4/4, rooms **8/12 → 9/12** — the hall (392,922)–(521,1387) matched; lost
= exactly the three stair verdicts the user is retiring ((1090,699)–
(1142,876), (466,920)–(521,1056), (1033,925)–(1142,1134)); unreviewed
**18 → 18, the same 18** step 9 §2 listed (17 furniture-pen phantoms + the
merged landing). The hall door reads `plugs: interrupted@0, interrupted@3`
as at identity. s01 at identity: 12/12, hall door unchanged.

**Net effect on the corpus** (`seek_census.py`: every door on 18 sheets at
its factor, `_door_plugs` re-run on the pipeline's exact inputs with and
without `_seek_edges`; 4 of ~560 doors change):

| door | what changed | hit | room effect | my read |
|---|---|---|---|---|
| s01 door_0002 (0.67), at 0.542 only | edge 0 (doorway) None → interrupted | 9.57px = 149mm, the jamb block's right face (30px, 90°) | the hall is its own room again | **win** (the step's target; at identity nothing changes) |
| s14 door_0008 (0.72 single) | edge 3 None → interrupted (was plug-less: plane stamp on both hinge edges) | 9.0px = 76mm, an 11.5px band at 90° | none — s14 polygons identical | neutral (a real jamb; the stamp had sealed the same plane) |
| s17 door_0004 (0.95 single, leaf drawn CLOSED in its doorway) | edge 1 (doorway) None → interrupted, edge 3 kept | 14.25px = 121mm, a 32.5px band at 90° | confirmed `partial` room_0018 (1182,2209)–(1286,2444) **−1,163 px²** (IoU vs its recorded bbox 0.545 → 0.572): the outline had wrapped UNDER the closed leaf into the threshold and now stops at the wall plane — unsimplified diff: lost 1,163, gained 0 | **win** (the strip is the doorway, never floor; the outline moves toward the recorded verdict) |
| s18 door_0018 (0.67, plug-less before) | edge 3 (doorway) None → interrupted | 10.5px = 178mm, a 139px face at 90° | day room rooms 0002 **+695 px²** (IoU 0.9918), 0003 +30 — the doorway strip and swing corner rejoin the room | **win** (the brief's expected picture) |

Net phantoms: 0 → 0 at the sheets' factors; no room appears, vanishes,
merges or splits. The step's win is s01 at its true factor (the hall) plus
two sub-1% outline corrections.

**Pictures** (this directory, none shows an address):
`step10_s01_hall_door_seek_0542_before_after.png` (the doorway plug's tail
samples at 0.542 without and with the seek; blue = barrier, orange = door
seals, green = rooms), `step10_s01_hall_and_living_room_0542_before_after.png`
(the hall and living room at 0.542, one blob vs two rooms — the 17 red-pen
phantoms unchanged), `step10_s17_room_0018_closed_leaf_threshold_before_after.png`
(`room_shape_crop`: the outline wrapping under the closed leaf, then
stopping on it), `step10_s18_room_0002_door_0018_doorway_regained_before_after.png`
(`room_shape_crop`: the D2 doorway strip and swing corner regained).
`outputs/compare/s17|s18/page_01_side_by_side.png` hold the whole-page views.

**Sweep** (`tools/regress.py`, four background groups, vs the baseline of
the unmodified tree; `tools/diff_room_polygons.py` on all 20 slugs):

| | lost | returned FP | REVIEW | doors/windows | polygons |
|---|---|---|---|---|---|
| baseline | 0 | 68 | 0 | — | — |
| `local` clip widened only | 0 | 68 | 0 | identical | **20 sheets IDENTICAL** |
| **seek** | **0** | **68** (identical lines) | **0** | identical | **3 changed** (s17 room_0018 −1,163; s18 room_0002 +695, room_0003 +30), 0 added, 0 removed; **17 sheets IDENTICAL incl. s01 and s02** |

Unsimplified check (`ROOM_SIMPLIFY_TOL_PX` 0, `_seek_edges` patched off vs
on, via the harness): s17 lost 1,163 / gained 0 at (1182,2433)–(1286,2444);
s18 lost 0 / gained 695 + 30; s01 and s02 byte-identical. `door_openings`
unchanged on every moved room. Labels were not reseeded (three sub-1%
outline moves).

**Not pinned yet**: nothing new to review — no REVIEW line. The hall's
return at 0.542 becomes a sweep-visible fact only when `_gate_denominator`
moves s01 (its own iteration).

**Residue / not in scope** (one line each):
- s01 at 0.542 still carries the 17 furniture-pen phantoms (step 9 §2,
  `ROOM_WALL_PEN_MIN_FRAC` 13.7 % → 15.2 %) and the three stair verdicts
  to retire — the pen discriminator and the denominator are the next two
  iterations.
- s14 door_0008's other hinge edge (0) lost the plane stamp it used to
  carry (the door now has a real plug); no room on s14 touches it.
- The false side of the cap is one instance at 1.18× (s14 door_0007's
  chevron ring); the interrupted-only clause and the one-anchored-end
  condition carry the rest — a leaf tip with a partition parallel to the
  wall within 250mm of it would plug along the leaf (no corpus instance:
  `seek_census.py` finds no leaf-tip hit on 18 sheets).
- `crop_s01.py` (step 9) rendered its pictures at import; it now does so
  only under `__main__` so `crop_step10.py` can reuse its drawing helpers
  (the two step-9 PNGs it re-rendered were restored with `git checkout`).

## Numbers

lost **0** · returned FPs **68** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** at the sheets' factors (**+1 confirmed room** for s01 at
its true factor in the harness: 8/12 → 9/12, the hall; the same 18
unreviewed) · outline: s17 room_0018 −1,163 px² (a closed-leaf threshold,
toward its verdict), s18 +725 px², 17 sheets identical, s01/s02 untouched
at f = 1.0 · **next**: the wall-pen discriminator for colour-coded sheets
(census every multi-pen sheet s01/s02/s03/s04/s08/s12/s17 before proposing
anything), then narrow `_gate_denominator` (retire the three s01 stair
verdicts by hand and re-review the merged landing then), then step 4
(`WALL_MAX_THICKNESS_PX` 36 → 40).

**Decision needed**: accept and commit (code + tests + prose + the four
PNGs + the step-9 scratch additions `seek_census.py`, `seek_census_out.txt`,
`crop_step10.py`, the `crop_s01.py` main guard and the `s01_common.py` tap
signature), or revert.
