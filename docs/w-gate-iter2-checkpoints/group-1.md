# W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)

Branch `recal/w-gate-iter2` (from main `f5682fc`), 2026-09-04. Baseline of main
reproduced before any change: **71 returned FPs, 0 LOST, 5 unreviewed**;
snapshots of all 20 slugs refreshed from that run
(`outputs/regress_baseline/<slug>/2026-09-04_10-2*`).

## The four moves

| constant | was | now | world @1:50 | true class (measured) | false class (measured) | margins |
|---|---|---|---|---|---|---|
| `WINDOW_MIN_WIDTH_PX` | 14 | **12** | 102 mm | s02 20.5 px = 174 mm; s16 11.6 px @f=0.5 = 196 mm; s18 16.5 px = 279 mm; s03 17.2 px (1:100 plan at identity) | s18's FP windows start at 16.4 px — the width of its real ones: width separates nothing on this side | 1.7× under s02, 1.4× under s03 (was 1.46× / 1.23×) |
| `DOOR_FOLD_JAMB_ANCHOR_TOL_PX` | 6 | **10** | 85 mm | s01 door_0012's 3.4/3.6 px = 53–56 mm at its true 1:92.2 (the one constant whose 1:50 value, 51 mm, sat under its own defining feature) | nothing matches up to 12 px on s01 or s02 | 1.5× over 56 mm |
| `WALL_THROUGH_HATCH_MAX_PX` | 64 | **72** | 610 mm | s05's 475 mm through-hatched wall (28 px @f=0.5) | through-hatched floors/fixtures: s01 from 81.5 px (1272 mm at 1:92.2, identity), s05 66.5–68 px @f=0.5, s20 94 px | 1.28× over s05 (was 1.14×), 1.13× under s01 |
| `CROSS_DOOR_EXPAND_PX` | 20 | **16** — the brief said 10 | 135 mm | s03's real window lost at 25 px; real windows 2–8 px from doors (s10 4.0, s17 7.75, s18 2.0) kept by the cover rule + hinge-jamb exemption | door-ink phantoms ≤ 2.8 px from their door (s01; 0 on s15) — any reach; **and** a 100 mm DOOR LINING touching the door's hinge corner (s18, 6×49 px @f=0.5) which needs 10.3 px at 1:50 to reach 10 % cover | 1.55× over the lining, 1.56× under s03 (20 was 1.94× / 1.25×; 10 was 0.97× on the lining) |

`WALL_THICK_MATERIAL_MAX_PX` stays 48 (group 3, after the per-band mark cap).

**Why 16 and not the brief's 10 for `CROSS_DOOR_EXPAND_PX`.** The first
corpus sweep at 10 was byte-identical to baseline on 19 sheets and added ONE
REVIEW line: s18 window_0013, conf 0.75, bbox (2256,614)–(2262,662). From the
render it is the door lining / jamb nib between a wall corner and door_0271
(double swing, 0.66) — a phantom. Single-field revert with the census harness
attributed it: restoring the reach to 20 removes it; reverting the window
floor, the fold tolerance or the through cap does not. Geometry: door_0271's
top-left corner IS the box's bottom-right corner, so the dilation covers it
only diagonally — at the scaled 5 px reach ix·iy = 5×5.5 = 9.4 % of 292 px²
(under `CROSS_DOOR_MIN_WINDOW_COVER` 0.10), at 6 px 13.3 %; the need is
5.17 px scaled = **10.3 px at 1:50**. The census's one-field ablation never
saw this class because the lining was vetoed at every multiplier it tried
except 0.5×, where it did not look for new windows on s18. With the false
class now two-sided (door ink ≤ 2.8 px; corner-touching lining 10.3 px) and
the true class at 25 px (s03), 16 is the value with ≥ 1.5× both ways. At 16
the hinge-jamb wall-run exemption (`_window_in_door_wall_run`) decides three
corpus windows again (s10 4.0 px, s17 7.75 px, s18 2.0 px @f=0.5); at 10 it
decided none (measured with a probe over s01/s02/s03/s10/s11/s15/s16/s17/s18).
The exemption and the cover rule are untouched.

Pictures: `g1_s18_door_lining_10_vs_16.png` (left: the phantom at 10; right: 16).

**s01 at f=1.0 — one bbox moved, nothing else.** `DOOR_FOLD_JAMB_ANCHOR_TOL_PX`
10 lets a second line anchor door_0012's top tip: path 1472, the 1.5 px wall
face (387.5, 924.75)–(387.5, 948.5), ending 7.77 px from the tip (the 1.0 px
jamb line at 3.4 px anchored before and still does). The anchor points feed
the bbox corridor, so the bbox top moves 955.5 → 948.5 (IoU 0.889 against the
confirmed bbox; `opening_span_px` 55.8, `leaf_run_px` 48.1, `anchored_tips` 1,
confidence 0.65 all identical; s01's 12 rooms unchanged, takeoff unchanged).
Picture: `g1_s01_door_0012_before_after.png`. s02 is byte-identical.

## Tests (fast tier, each proven to bite)

| test | pins | fails at |
|---|---|---|
| `test_window_detection.TestMinWidthReference` | 13 px opening detected, 11 px not | 14 |
| `test_folding_doors.OpenVTests.test_jamb_anchor_7px_off_tip_still_anchors` (+ 12 px rejected) | jamb ends 6.9/7.0 px off the tip anchor | 6 |
| `test_through_hatch_band.ThroughHatchCapReferenceTests` | 68 px through-hatched band pairs, bare does not; s05 margin ≥ 1.25× at f=0.5 | 64 |
| `test_window_detection.TestDoorWindowExclusion.test_door_lining_touching_door_corner_vetoed` | s18 lining at identity (12×97.5 box at the door corner) vetoed | 10 |
| `…test_window_18px_from_door_kept` | window 18 px past the door kept | 20 (exactly 10 % cover) |
| `test_scale_door_gates`, `test_scale_window_gates` | scaled literals (6.0 / 3.0 / 48.0; 8.0 at f=0.5) | old values |

Full fast tier: 1362 tests, green except the three pre-existing failures
(`test_review_cli` / `test_review_picker` import errors — InquirerPy not in
the venv; `test_takeoff_fn_equivalence` field='warnings' — fails on main).
Harness self-check: s01 11/11 · 12/12 · 4/4, s02 15/15 · 11/11 · 11/11.

## Sweep (four background groups vs. the main snapshots)

| | lost confirmed | returned FP | REVIEW | deferred closed |
|---|---|---|---|---|
| baseline (main) | 0 | 71 | 5 (s18 room_0000, s15 room_0016, s10 window_0000/0001, s17 room_0021) | 0 |
| G1 at census values (reach 10) | 0 | 71 | 6 (+ s18 window_0013 — phantom, see above) | 0 |
| **G1 final (reach 16)** | **0** | **71** | **5 — verdict lines byte-identical to baseline** | 0 |

`tools/diff_room_polygons.py` over all 20 slugs: **0 rooms with a changed
polygon, 0 added, 0 removed**; the only entity delta is s01 door_0012's bbox
(IoU 0.889). No room outline changed anywhere, so no room-label cache was
reseeded.

**Net phantom delta: 0** (the +1 at reach 10 was caught by the sweep and
removed by the corrected value before the final sweep).

## Prose updated

Constant comments (`walls.py`, `windows.py`, `doors/constants.py`,
`postprocess.py` — the `CROSS_DOOR_WALL_RUN_TOL_PX` comment now records the
16 px measurements), findings §4 rows (walls, §4d, §4e), the window and door
tuning-guide tables, the census report's "move?" cells (rows 5, 41, 44, 49 —
row 49 records the refutation of 10), CLAUDE.md's gate paragraph, and the
handoff's new "Outcome — iteration 2" section.

## Residue / not in scope

- The census's window row 44 called width non-separating on the false side;
  Group 1 confirms it (no window changed on any sheet between 14 and 12).
- The pictures in this directory are 130–180 px crops of two corpus sheets;
  no PNG has been committed under `docs/` before — the user decides whether
  they stay in the tree.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 · **next: Group 2** (thin-margin moves; harness pre-checks on the
named sheets first).
