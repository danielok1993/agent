# Window Detection — Tuning Guide

Reference for the architectural window-detection pipeline in `detection/windows.py`
plus the door-overlap cross-exclusion in `detection/postprocess.py`. Mirrors the
structure of `door-detection-tuning-guide.md`.

**Read first if you are about to change window detection.**

---

## 1. The signature (cap-anchored)

A window opening is drawn as a **pair of short perpendicular cap lines** (the
jambs) facing each other across the opening width, with one or more parallel
**glazing** lines (the panes) spanning the gap between them.

```
   cap                                   cap
    │  ╶──────── glazing pane ────────╴  │     ← horizontal window
    │  ╶──────── glazing pane ────────╴  │       (1–3 panes; 5-1133 Window A has 3,
    │  ╶──────── glazing pane ────────╴  │        Window B has 2, no centerline)
```

**The cap pair is the only feature stable across drawing standards.** The
glazing-line count (1–3), spacing (1–8 px) and pane depth all vary by drafting
style, so we anchor on the facing cap pair and treat the glazing band as
confirmation — rather than clustering the (variable) glazing first.

This is the v2 detector. History:
- v0 "group any 2–6 parallel lines 3–50 px apart" — missed real windows, flooded 88 FPs on 5-1133.
- v1 "glazing-rectangle" (cluster ≥3 equal-length parallel lines + caps) — clean 4/4 on floor-plans but **over-fit**: missed *every* 5-1133 window, whose panes are wider-spaced (~7 px), thicker (~14 px), unequal-length, and sometimes only 2.
- v2 cap-anchored (current) — one rule catches floor-plans' 4 and 5-1133's ground-truth windows. Driven by ground truth on both PDFs (see §5).

## 2. Pipeline shape

`detect_windows(paths)` (geometry only, no wall/door dependency):

1. **`_axis_lines`** — split `l` primitives into horizontal / vertical pools
   (within `WINDOW_AXIS_TOL_PX` of an axis). Each record carries `perp` (the
   constant coordinate) and `span` (lo, hi along the run axis). For a horizontal
   window the caps are the vertical pool and the glazing the horizontal pool;
   vice-versa for a vertical window.
2. **`_find_openings`** — sort caps (the short perpendicular pool, length in
   `[WINDOW_CAP_MIN_LEN_PX, WINDOW_CAP_MAX_LEN_PX]`) by position and pair them.
   A pair is an opening when: gap ∈ `[WINDOW_MIN_WIDTH_PX, WINDOW_MAX_WIDTH_PX]`;
   the caps are similar length (`WINDOW_CAP_LEN_RATIO`) and truly facing (their
   perp-extents overlap, `WINDOW_CAP_ALIGN_OVERLAP`); and a glazing band bridges
   the gap (`_spanning_glazing`).
3. **`_spanning_glazing`** — collect glazing lines whose perp sits within the
   caps' combined facing extent (`WINDOW_SPAN_PERP_TOL_PX`) and whose run-span
   covers the gap (reaches within `WINDOW_SPAN_COVER_TOL_PX` of each cap) without
   overshooting it by more than `WINDOW_SPAN_OVERSHOOT_PX` (this rejects long
   wall lines that merely cross the gap). De-dupe collinear duplicates by perp
   (`WINDOW_GLAZING_DISTINCT_EPS`), then take the tightest **band** via
   `_tight_band` (consecutive panes ≤ `WINDOW_GLAZING_ADJ_SPACING_PX`, total
   depth ≤ `WINDOW_GLAZING_THICKNESS_PX`). Require ≥ `WINDOW_MIN_GLAZING_LINES`
   distinct panes.
4. **2-pane jamb gate** — a 2-pane opening (no centerline) is geometrically a
   thin wall; accept it only when the caps are substantial
   (`cap_len ≥ WINDOW_TWO_LINE_MIN_CAP_PX`). Small-cap windows must show ≥3 panes.
5. bbox = union of caps + glazing band; confidence scored; emit.
6. **`_dedupe_openings`** — greedy NMS over duplicate cap pairs (prefer more
   panes, then tightest bbox; drop a candidate whose center sits inside a kept
   one).

Then, in `run_heuristics` → `_resolve_door_window_conflicts(doors + windows)`:
drop any window the (dilated) door bbox **materially** covers — at least
`CROSS_DOOR_MIN_WINDOW_COVER` of the window's area, so a distant door whose 20 px
dilation merely grazes a window corner is not a conflict. Door detection is
reliable; this is the primary false-positive filter and **does not depend on
walls**.

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
| `WINDOW_AXIS_TOL_PX` | 1.5 | Max off-axis deviation to call a line H/V. Glazing/caps are axis-true; diagonal hatch excluded. |
| `WINDOW_CAP_MIN_LEN_PX` | 3.0 | Tiny caps exist (5-1133 bonus window jambs ~5 px). |
| `WINDOW_CAP_MAX_LEN_PX` | 34.0 | Caps are short; longer perpendiculars are walls. 5-1133 Window B caps overshoot to 30 px. |
| `WINDOW_CAP_LEN_RATIO` | 0.60 | The two caps must be of similar length. |
| `WINDOW_CAP_ALIGN_OVERLAP` | 0.60 | Their perp-extents must overlap — truly facing, not two offset stubs. |
| `WINDOW_MIN_WIDTH_PX` | 14.0 | Opening width (gap between caps). Smallest real ≈ 20 px (bonus). |
| `WINDOW_MAX_WIDTH_PX` | 240.0 | 5-1133 Window B is 173 px; caps out long wall/decoration runs. |
| `WINDOW_GLAZING_THICKNESS_PX` | 16.0 | Max perp-spread of the glazing band. Window A ≈ 14 px. |
| `WINDOW_GLAZING_ADJ_SPACING_PX` | 8.5 | Max gap between adjacent panes. Window B ≈ 7.6 px. **Rejects stair treads / widely-spaced parallels.** |
| `WINDOW_GLAZING_DISTINCT_EPS` | 1.5 | Panes closer than this in perp are one pane (collapses collinear duplicates / double-drawn faces). |
| `WINDOW_MIN_GLAZING_LINES` | 2 | ≥2 distinct panes must span the gap. 2 is the minimum real (Window B); single-line openings are too wall-like (see §6). |
| `WINDOW_TWO_LINE_MIN_CAP_PX` | 12.0 | A 2-pane opening needs real jamb caps (~20–30 px) to outrank a thin wall / fixture sliver. **Small-cap windows must show ≥3 panes** (the bonus). |
| `WINDOW_SPAN_COVER_TOL_PX` | 4.0 | A glazing line may fall short of each cap by this and still "span" the gap. |
| `WINDOW_SPAN_OVERSHOOT_PX` | 12.0 | …and run at most this far PAST each cap. Real glazing overshoots ≤7.5 px; **walls run hundreds past** — this is what stops long wall lines being read as glazing (and inflating bboxes). |
| `WINDOW_SPAN_PERP_TOL_PX` | 2.0 | Glazing perp may sit this far outside the cap facing-extent. |
| `WINDOW_MIN_CONFIDENCE` | 0.50 | Matches `OFFLINE_MIN_CONFIDENCE["window"]`. |

`detection/postprocess.py`:

| Constant | Value | Rationale |
|---|---|---|
| `CROSS_DOOR_EXPAND_PX` | 20.0 | Dilate door bbox before testing window overlap. Matches `CROSS_WALL_EXPAND_PX`. |
| `CROSS_DOOR_MIN_WINDOW_COVER` | 0.10 | Door must cover ≥10% of the window's area to suppress it. A dilated-corner graze from a distant door is **not** a conflict (was wrongly killing 5-1133 Window A). |

Confidence: base `0.62`, `+0.05` per glazing pane beyond 2, `+layer_prior` (or
`+0.10` weak layer hint), capped `0.90`. `_cross_validate` subtracts the no-wall
penalty when walls are enabled.

## 5. Reference data — current detection state (regression target)

### 5.1 floor-plans.pdf (offline, walls on/off both give 4)

Exactly **4 windows** under `run_heuristics` (walls on/off both give 4):

| bbox (x0,y0,x1,y1) | orient | notes |
|---|---|---|
| 955, 811 — 961, 889 | V | "W4" — 3 panes, caps 6.5 px (thin wall) |
| 867, 896 — 923, 918 | H | "W3" — panes ~1 px apart → collapse to n=2, caps 22 px |
| 903, 1375 — 980, 1397 | H | "W1" — n=2, caps 22 px |
| 1078, 1375 — 1129, 1397 | H | "W2" — n=2, caps 22 px |

Note W1–W3 panes are ~1 px apart and de-dupe to 2 distinct panes; they survive
the §4 2-pane gate because their jamb caps are ~22 px. The two former FP slivers
(toilet 978,773 and the 373,926 fixture, both n=2 with 4 px caps) are now
rejected by that gate. Doors unchanged (no regression vs door-guide §9.1).
Confirmed false positives that must stay rejected: garden/double doors, door
leaves (door overlap), toilets/sink/cupboard/balcony door.

### 5.2 5-1133-WD03.pdf

**Partially ground-truthed (run 2026-06-19_12-02-48).** Three windows confirmed
by the user, all now detected; output 14 windows (was 26). The three confirmed:

| Window | topology | glazing path idx | cap path idx |
|---|---|---|---|
| A | 3 H panes, ~7 px spacing, 13.7 px deep, 106 px wide | 2904 / 2926 / 2905 | 2909 / 2925 |
| B | 2 V panes, 7.6 px apart, **no centerline**, 173 px tall | 2046 / 2167 | 1951 / 2267 |
| bonus | 3 short H panes, ~2 px spacing, tiny ~5 px caps, 20 px wide | 2170 / 2181 / 2094 | 2096 / 2295 |

These drove the v2 cap-anchored rewrite (v1's `n≥3` + tight-spacing gates missed
all three). The other **11** detected candidates are **not yet verified** — next
iteration: have the user confirm which are real and tune from there.

## 6. Known limitations / not handled

| Case | Status | Note |
|---|---|---|
| 1-pane windows (single line + 2 caps) | Not detected | `WINDOW_MIN_GLAZING_LINES = 2`; a single line between caps is indistinguishable from a bracket/niche. Needs ground truth before relaxing. |
| Narrow 2-pane window with small caps | Not detected | The §4 2-pane jamb gate (`cap ≥ 12 px`) rejects these as wall/fixture slivers. A real one would need ≥3 panes or bigger caps to surface. |
| Windows drawn as native `re`/`qu` rectangle + lines | Not handled | both sample PDFs are lines-only; add a rectangle anchor if a real one appears. |
| Windows on a door (e.g. sidelight) | Suppressed | Door-overlap exclusion drops a window materially covered by a door. Unobserved as a real case. |
| Diagonal / bay windows | Not handled | Detector is axis-aligned only. |

## 7. How to verify a change won't regress

1. `python -m unittest discover tests` (window tests in `tests/test_window_detection.py`).
2. `python app.py extract floor-plans.pdf --no-gemini` → 4 windows at the §5.1
   bboxes, 9 doors.
3. The `TestFloorPlansRegression` test pins this end-to-end; keep it green.
