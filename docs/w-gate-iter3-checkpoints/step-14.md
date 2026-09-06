# W-gate iteration 3 — step 14: an ENTRANCE is a seal that RUNS ALONG the space's boundary (`ROOM_ENTRANCE_MIN_RUN_PX`, `_entrance_run`) — built, censused as implemented, swept: verdict-identical in counts, s04 a trade, the s17 strips entrance-less and still emitted

Branch `fix/entrance-contact-run` from `recal/wall-max-thickness-40` (b52384e: the
step-13 measurement checkpoint plus its graphify chore; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups and
snapshotted for all 20 slugs (`outputs/regress_baseline/<slug>/2026-09-06_16-32-03`
… `16-33-15`) — **0 LOST, 68 returned FPs, 0 REVIEW**, s01 10/10 at its true
factor, the 88 verdict lines identical to step 13's once sorted
(`tools/census_scratch/step14/sweep_base_verdicts.txt`). 2026-09-06.

## The brief

`entrance_count` read any ≥ 0.55 seal within `ROOM_CONTACT_TOL_PX` (4px) of the
room boundary. A doorway cut through the wall a strip lies INSIDE of, or a
neighbour's doorway whose tail ends at the strip's face, touches the strip over
its own plug width only — and that touch was an entrance, so s17's four
cavity-wall reveal strips (rooms 0013/0014/0027/0032) never reached
`_is_band_pocket`. Step 13 measured (raw contact, per room the largest): every
confirmed entered room ≥ 67.2px at f=1.0 / 44px at f=0.5, the strips 15–18px,
s04's recorded-FP box 21.5px. Build it as a W-class floor on the contact run,
census it as implemented, and expect the strips to become entrance-less and
STILL stay (their rotated rectangles are pinned by 31.5px tabs, their
328–343mm spacing is over the 36px cap).

## The rule as built

`_entrance_run(boundary, seal)` = the boundary's length within
`ROOM_CONTACT_TOL_PX` of the seal, LESS `2 × ROOM_CONTACT_TOL_PX` (the
tolerance's reach past each end of the seal); −∞ when the seal is out of
contact. A seal counts as an entrance when its run is ≥
`ROOM_ENTRANCE_MIN_RUN_PX` = **29.5px = 250mm at 1:50** (W-class, in
`RoomGates`: 14.75px at 1:100, 16.0px at s01's 1:92.2, 10.8px at s13's 1:136).
`door_count` / `door_openings` / the confidence boost are untouched — they
still count every touching seal; only the entrance gate that feeds the
blind-window, wall-recess and band-pocket drops changed.

Why NET of the tolerance, not the raw contact: the tolerance is paper. A plug
meeting a strip end-on touches it over `2 × ROOM_PLUG_HALF_WIDTH_PX + 2 × TOL`
— 18px at 1:50 but 12px at s13's 1:136 (half-width floored at 2px), where a
world floor that clears s03's 67.2px true minimum by 1.5× at f=1.0 (≤ 44.8px =
379mm) scales to ≤ 16.4px, and one that clears the 12px false ceiling by 1.5×
needs ≥ 18px = 415mm at 1:50 — no world floor on the raw contact holds both
margins at both factors. On the net run the false class is the plug's
cross-section itself (10px at f=1.0, 5px at f=0.5, 4px at f=0.367), a
W-class quantity, and the true class the doorway width; 250mm is the
geometric centre of the two classes' px bands at f=1.0 (20.3–39.5px).

## Census 1 — both classes as the rule reads them (`entrance_census.py`, all 20 sheets at their factors)

For every room the chain EMITS with the gate OFF (`H.overrides(mult=
{"ROOM_ENTRANCE_MIN_RUN_PX": -1.0})`: a floor of −29.5×f, under any in-contact
run ≥ −8px for every corpus factor — the any-touch test exactly), read off
detect_rooms' own locals through the free-space tap: per entrance seal its raw
contact and its run, per room the LARGEST run (a neighbour's tail grazes real
rooms over 3.6–15px, so the statistic is per room, never per seal).

| sheet (f) | confirmed entered rooms | smallest largest-run | floor | margin |
|---|---|---|---|---|
| s01 (0.542) | 10 | 47.3px (738mm at 1:92.2) | 16.0 | 2.96× |
| s02 (1.0) | 11 | 82.6px | 29.5 | 2.80× |
| s03 (1.0) | 17 | **59.2px** (1077,1011)–(1187,1121) | 29.5 | **2.01×** |
| s04 (1.0) | 5 | 85.8px | 29.5 | 2.91× |
| s05 (0.5) | 8 | 37.2px | 14.75 | 2.52× |
| s06 (0.5) | 9 | 38.7px | 14.75 | 2.62× |
| s07 (0.5) | 5 | 43.2px | 14.75 | 2.93× |
| s08 (1.0) | 2 | 85.8px | 29.5 | 2.91× |
| s10 (1.0) | 9 | 103.0px | 29.5 | 3.49× |
| s11 (0.5) | 15 | 36.5px (1980,1131)–(2098,1217) | 14.75 | 2.47× |
| s12 (0.5) | 7 | 43.0px | 14.75 | 2.92× |
| s13 (0.367) | 11 | 37.3px | 10.8 | 3.45× |
| s15 (1.0) | 9 | 67.7px | 29.5 | 2.29× |
| s16 (0.5) | 17 | 36.5px | 14.75 | 2.47× |
| s17 (1.0) | 23 | 60.2px | 29.5 | 2.04× |
| s18 (0.5) | 9 | **36.0px** (1364,565)–(1423,732) | 14.75 | 2.44× |
| s20 (1.0) | 4 | 103.5px | 29.5 | 3.51× |

(s09/s14/s19 emit no rooms; s02's harness score reads "lost 12" under both
gates — the 11 labels and the schedule the stage-5 harness omits, as in every
previous step.)

The false class — every room whose entrance status flips, corpus-wide
**five**, all recorded false positives:

| sheet | room | seal | how it meets the room | raw contact | run | floor margin |
|---|---|---|---|---|---|---|
| s17 | 0013 (912,2174)–(947,2331) | door_0025's 0.95 plug (932,2331)–(942,2441) | collinear, meets the strip's bottom end | 18.0px | **10.0px** | 2.95× |
| s17 | 0032 (914,2609)–(949,3061) | door_0036's 0.95 plug (919,2499)–(929,2609) | collinear, meets the strip's top end | 18.0px | 10.0px | 2.95× |
| s17 | 0014 (3047,2174)–(3084,2489) | door_0002's 0.95 plug (2934,2458)–(3049,2465) | the BATH door's tail ending at the strip's left face | 15.0px | **7.0px** | 4.2× |
| s17 | 0027 (3047,2594)–(3084,3061) | door_0003's 0.95 plug (2941,2873)–(3049,2883) | a tail ending at the strip's left face | 18.0px | 10.0px | 2.95× |
| s04 | (1463,1042)–(1558,1131) | door_0000's 0.67 plug (1459,942)–(1466,1062) | the hall door's bottom tail running 20px down the box's left edge | 21.5px | **13.5px** | 2.19× |

No confirmed room changes status on any sheet; no room on s01 or s02 receives
a different count.

## Census 2 — what the flips do (fate under the gate as built)

- **s17's four strips stay emitted.** Entrance-less now, they reach
  `_is_band_pocket` for the first time (`pocket_census.py` on the new tree:
  7 calls on s17 against 3, `in_band 4, would_drop 0`) and the rule rejects
  them exactly as step 13 predicted — covers 0013 [0.0, 1.0], 0032 [0.0, 0.93],
  0014 [0.0, 0.04], 0027 [0.0, 0.0] (the 31.5px tab where the perpendicular
  band's flat-capped solid ends pins each rotated rectangle ON the face
  line) and spacing 38.75–40.5px over the 36px cap. Both are their own steps.
- **s04's box drops** — entrance-less, one window (window_0004), 8,123 px² <
  the 10k blind cap: the blind-window drop takes it. It is the stair's WINDER
  box (treads 11–13, `step14_s04_box_dropped_tail_run_13px.png`), a recorded FP.
- **and s04's stair flight returns**: (1588,1053)–(1762,1131), treads 4–9,
  13,485 px², door-less, conf 0.75 — a recorded FP too
  (`step14_s04_stair_flight_returned_recorded_fp.png`). It was in the pre-drop
  list under both gates and was dropped by `_drop_window_exterior_sides`: it is
  the door-less side of window_0004 while the winder box, with `door_count` 2,
  was the door-bearing side. With the box no longer a room the window has no
  door-bearing side and the flight stays. window_0004 (1558,1047)–(1588,1131)
  is tread 10 detected as a 0.62 window — itself one of the 68 returned FPs
  (`(1573,1089)`) — so both cells are the one staircase fenced by its own
  linework plus a false window; the entrance rule only swapped which cell is
  emitted. The rule that should catch them is the window detector's (a tread
  between two stringers is not glazing) or the stair recogniser's (a winder
  box beside a flight), not this one.

## The sweep (four background groups, verdicts sorted section-wise)

**0 LOST, 68 returned FPs, 0 REVIEW** — the same counts as the baseline, with
exactly one verdict line swapped: `s04 room @ (1511,1090)` (the winder box)
gone, `s04 room @ (1675,1092)` (the flight) returned.
`tools/diff_room_polygons.py`: **19 sheets entity- and polygon-IDENTICAL**
(s01 at 0.542 and s02 at 1.0 among them), s04 `12 → 12` entities with the one
REMOVED (8,123 px², 0.9) and the one ADDED (13,485 px², 0.75); **0 changed
polygons**, so no room loses or gains any area and no unsimplified diff was
needed. Fast tier: 1440 tests green; `TestEntranceRunsAlongTheBoundary`
(the reveal strip ending at a doorway cut through the same cavity wall — the
0.95 door's interrupted plug meets the strip's end, run 10px, the strip is
dropped as a band pocket; and the true class, a 26px-wide cupboard entered
through a 60px doorway in its long side, which stays) fails with the code
reverted (`2 != 1`, the strip emitted) and passes with it.

## Pictures (this directory, plan crops only, none shows an address)

`step14_s04_box_dropped_tail_run_13px.png` (red the winder box, green
door_0000's plug with its tail on the box's edge, orange door_0000 and
window_0004), `step14_s04_stair_flight_returned_recorded_fp.png` (the flight,
orange window_0004 = tread 10), `step14_s17_reveal_strip_0013_now_entrance_less.png`
and `…_0032_…` (the collinear plug meeting the strip's end),
`…_0014_…` and `…_0027_…` (a neighbour's tail ending at the strip's face),
`step14_s03_true_floor_confirmed_run_59px.png` and
`step14_s11_true_floor_confirmed_run_36px_f05.png` (the true class's floor at
f=1.0 and f=0.5). Red = room polygon, green = entrance seals with their run,
orange = named openings.

## Residue / not in scope (one line each)

- The s04 staircase: two recorded-FP cells and a recorded-FP window on one
  flight; tread 10 as a window is the root, the winder box and the flight its
  consequences — window detection or the stair recogniser, its own step.
- `_is_band_pocket`'s cover reading on tab-pinned rotated rectangles (the s17
  strips read 0 on one edge) and its 36px ceiling against their 38.75–40.5px —
  the next two steps in the queue; the strips are candidates now.
- `_entrance_run` on a MultiPolygon seal (two plugs of one door) sums both
  parts' contact and subtracts the tolerance once — a mild overcount on the
  true side only; no corpus room is decided by it.
- `tests/test_takeoff_fn_equivalence.py` not run separately (it is in the
  discover run, which is green).

## Numbers

lost **0** · returned FPs **68** (one line swapped on s04: −1 winder box, +1
stair flight, both recorded) · new REVIEW lines **0** · net phantom delta
**0** (a trade inside one staircase) · s01 and s02 entity- and
polygon-identical · 19 sheets identical, s04 the only change · s17's four
strips entrance-less and still emitted, now rejected by `_is_band_pocket`'s
covers and ceiling · **next**: the tab-tolerant cover reading in
`_is_band_pocket` (cover on the polygon's own long runs, or standoff 0
tolerated where a perpendicular band ends), then the ceiling with s11's
368mm storage recognised another way, then the queue.

**Decision needed**: ship the rule as built (commit code + tests + prose + the
eight PNGs + `tools/census_scratch/step14/`), or hold it — its corpus effect
today is one recorded FP for another on s04 and the s17 strips made candidates
for the next step.
