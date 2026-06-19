# Window Detection — Tuning Guide

Reference for the architectural window-detection pipeline in `detection/windows.py`
plus the door-overlap cross-exclusion in `detection/postprocess.py`. Mirrors the
structure of `door-detection-tuning-guide.md`.

**Read first if you are about to change window detection.**

---

## 1. The signature

A window is drawn as a **thin glazing rectangle**: a tight cluster of parallel,
equal-length **glazing** lines (the glass-pane edges plus a centerline) closed at
both ends by short perpendicular **cap** lines.

```
   cap                                   cap
    │  ╶──────── glazing edge ────────╴  │     ← horizontal window (W1–W3)
    │  ╶──────── centerline ──────────╴  │
    │  ╶──────── glazing edge ────────╴  │
```

This replaced the original "group any 2–6 parallel lines 3–50 px apart" detector,
which **missed** real windows (their glazing lines are ~1 px apart — below the old
3 px floor) and **flooded** false positives (88 promoted on 5-1133-WD03). The
rewrite was driven by ground truth captured interactively on floor-plans.pdf
(see §5).

## 2. Pipeline shape

`detect_windows(paths)` (geometry only, no wall/door dependency):

1. **`_axis_lines`** — split `l` primitives into horizontal / vertical pools
   (within `WINDOW_AXIS_TOL_PX` of an axis). Each record carries `perp` (the
   constant coordinate) and `span` (lo, hi along the run axis).
2. **`_cluster_glazing`** — greedily group tight, aligned, near-equal-length
   parallel lines into clusters of `>= WINDOW_MIN_GLAZING_LINES`. A line joins a
   cluster when it is within `WINDOW_GLAZING_ADJ_SPACING_PX` of a member, is
   `_aligned` with it, and keeps total cluster depth under
   `WINDOW_GLAZING_THICKNESS_PX`.
3. **`_find_cap`** — for each cluster, require a short perpendicular line at each
   end of the span (`WINDOW_CAP_END_TOL_PX`) that crosses the cluster centerline
   and is no longer than `WINDOW_CAP_MAX_LEN_PX`. Both ends must cap or the
   cluster is dropped.
4. bbox = union of glazing lines + the two caps; confidence scored; emit.

Then, in `run_heuristics` → `_resolve_door_window_conflicts(doors + windows)`:
drop any window whose bbox overlaps a detected door (door bbox dilated by
`CROSS_DOOR_EXPAND_PX`). Door detection is reliable; this is the primary
false-positive filter and **does not depend on walls**.

## 3. Why both filters are needed (floor-plans.pdf)

23 raw cluster+cap candidates reduce to the 4 real windows via two orthogonal cuts:

| Filter | Removes | Keeps |
|---|---|---|
| `n >= 3` glazing lines | 5 `n==2` fixtures/doors (toilet, sink, cupboard, balcony door) | all 4 windows (`n==3`) |
| no door overlap | 14 door-related (garden/double doors, leaves, a wall on a door) | all 4 windows (clear of doors) |

Neither alone is sufficient; together they give 4/4 windows, 0 false positives.

## 4. The constants

`detection/windows.py`:

| Constant | Value | Rationale |
|---|---|---|
| `WINDOW_AXIS_TOL_PX` | 1.5 | Max off-axis deviation to call a line H/V. Glazing lines are axis-true; diagonal wall hatch is excluded by this. |
| `WINDOW_MIN_GLAZING_LEN_PX` | 15.0 | Shortest plausible glazing run. |
| `WINDOW_MAX_GLAZING_LEN_PX` | 220.0 | Caps out long wall/decoration runs. Longest real glazing observed ~77 px. |
| `WINDOW_MIN_GLAZING_LINES` | 3 | Glass edges + centerline. **Every floor-plans window is n=3; every n=2 cluster was a false positive.** Lowering to 2 re-admits fixtures — only do so with ground truth that 2-line windows exist (possible on 5-1133, untested). |
| `WINDOW_MAX_GLAZING_LINES` | 6 | Upper guard against hatched bands. |
| `WINDOW_GLAZING_ADJ_SPACING_PX` | 4.0 | Max gap between adjacent lines in a cluster. Real spacing 1–3 px; 4 gives headroom. |
| `WINDOW_GLAZING_THICKNESS_PX` | 8.0 | Max total pane depth. Real panes 2–6.5 px. This is what rejects stair treads / widely-spaced parallels. |
| `WINDOW_GLAZING_LEN_RATIO` | 0.80 | Cluster lines must be near-equal length. |
| `WINDOW_GLAZING_OVERLAP` | 0.80 | And project onto each other (aligned extents, not merely parallel). |
| `WINDOW_CAP_END_TOL_PX` | 4.0 | Cap's constant coordinate must sit this close to a glazing span end. |
| `WINDOW_CAP_MAX_LEN_PX` | 30.0 | Caps are short (6.5–22 px). **Critical** — excludes long wall lines crossing the span end. |
| `WINDOW_CAP_CROSS_TOL_PX` | 3.0 | Cap's own span must cover the glazing centerline within this. |
| `WINDOW_MIN_CONFIDENCE` | 0.50 | Matches `OFFLINE_MIN_CONFIDENCE["window"]`. |

`detection/postprocess.py`:

| Constant | Value | Rationale |
|---|---|---|
| `CROSS_DOOR_EXPAND_PX` | 20.0 | Dilate door bbox before testing window overlap. Matches `CROSS_WALL_EXPAND_PX`. |

Confidence: base `0.62`, `+0.05` per glazing line beyond 3, `+layer_prior` (or
`+0.10` weak layer hint), capped `0.90`. `_cross_validate` subtracts the no-wall
penalty when walls are enabled.

## 5. Reference data — current detection state (regression target)

### 5.1 floor-plans.pdf (offline, walls on/off both give 4)

Exactly **4 windows**, all `n=3` glazing clusters, conf 0.62:

| bbox (x0,y0,x1,y1) | orient | notes |
|---|---|---|
| 948, 811 — 968, 889 | V | "W4" — caps 6.5 px (thin wall) |
| 867, 896 — 923, 918 | H | "W3" |
| 903, 1375 — 980, 1397 | H | "W1" |
| 1078, 1375 — 1129, 1397 | H | "W2" |

Doors unchanged at 9 (no regression vs door-guide §9.1). Confirmed false
positives that must stay rejected: garden/double doors, door leaves (door
overlap), toilets/sink/cupboard/balcony door (`n=2`).

### 5.2 5-1133-WD03.pdf

**Not yet ground-truthed.** Current output 26 windows (was 88). Windows there may
use native `re`/`qu` rectangles and/or 2-line panes — revisit `WINDOW_MIN_GLAZING_LINES`
and add a rectangle-primitive path once real windows are confirmed by the user.

## 6. Known limitations / not handled

| Case | Status | Note |
|---|---|---|
| 2-line windows (no centerline) | Not detected | `WINDOW_MIN_GLAZING_LINES = 3`. Needs ground truth before relaxing. |
| Windows drawn as native `re`/`qu` rectangle + lines | Not handled | floor-plans is lines-only; add a rectangle anchor for 5-1133. |
| Windows on a door (e.g. sidelight) | Suppressed | Door-overlap exclusion would drop a real window sitting on a door. Unobserved. |
| Diagonal / bay windows | Not handled | Detector is axis-aligned only. |

## 7. How to verify a change won't regress

1. `python -m unittest discover tests` (window tests in `tests/test_window_detection.py`).
2. `python app.py extract floor-plans.pdf --no-gemini` → 4 windows at the §5.1
   bboxes, 9 doors.
3. The `TestFloorPlansRegression` test pins this end-to-end; keep it green.
