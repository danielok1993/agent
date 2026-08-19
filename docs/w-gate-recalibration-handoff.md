# Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)

**Written:** 2026-08-19, after root-causing the s01 @ 1:92.2 detection regression.
**For:** the next agent picking up the recalibration of the world-space (W) detection constants.
**Status of the interim fix:** shipped and green — commit `1f795ed`
(`fix/measured-scale-detection-factor`): measured, non-nominal, non-viewport
denominators no longer drive detection-gate scaling (identity factor, source
`"measured"`, warning `SCALE_FACTOR_MEASURED_ONLY`). This handoff describes the
debt that fix routes around, not a bug in it.

## Read these first (in order)

1. `docs/scale-normalization-findings.md` **§4f** — the full root-cause write-up
   of this incident, with every measured number.
2. `docs/scale-normalization-findings.md` §1–§4b — the original premise, corpus
   census, and the frozen W/P/D class table this handoff says is half-mis-calibrated.
3. `scale/factor.py::_gate_denominator` — the shipped routing rule + docstring.
4. `tests/test_scale_factor.py` — 5 pinning tests
   (`test_measured_nonstandard_scale_does_not_drive_gates` and neighbors).
5. `docs/regression-testing-guide.md` — before touching any constant.

## The problem in one paragraph

The detection constants were tuned at factor 1.0 on the two reference sheets
under the premise "s01 and s02 are both 1:50" (findings §1). That premise is
half-false: s01's 31 dimension strings measure **1:92.2** (every label within
±0.5 % of its line), while its **paper conventions are standard drafting size**
— wall pen 1.5 px and hatch pitch 4.05 px, identical to s02's 1.5 / 4.07
(measured 2026-08-19; pen histogram: s01 top pens {1.5: 2570, 1.0: 1156},
s02 {0.45: 3185, 1.5: 887, ...}). So every W constant whose defining
measurement came from s01 encodes a **1:92.2 world quantity under a 1:50
label**. The W references are therefore world-accurate only to ~1.8×. At the
standard corpus factors (1.0, 0.5, 0.367-viewport) this is masked by gate
headroom and validated by the sweeps; a genuine non-standard **viewport** scale
near 1:92 would expose it exactly the way s01 did.

## Evidence: what broke at f = 50/92.2 = 0.542 (all measured on the real PDF)

Sweep fell from clean (11/11 doors, 13/13 rooms) to door 10/11, room 7/13,
17 phantoms. Per-gate ablation (scale one gate at a time, then leave-one-out)
proved **no single constant** is the cause — only full identity reproduces
13/13 + 0 extras. The independent mechanisms:

| Gate | At f=1 | At f=0.542 | s01 feature it collides with |
|---|---|---|---|
| `WALL_MAX_THICKNESS_PX` | 36 | 19.5 | real 25 px = 390 mm party wall (y=908, kitchen/wetroom); exterior wall 19.3 px sits at zero headroom |
| `WALL_HATCH_MAX_LEN_PX` | 48 | 26 | that wall's own 30–35 px hatch strokes → thick tier finds "no material" |
| `WALL_WEAK_MATERIAL_PER_100PX` (÷f) | 3.0 | 5.5 | s01's real hatch density 4.8/100px fails its own gate |
| `ROOM_OPENING_SEAL_PX` | 12 | 6.5 | plug tails stop 12 px short of jambs (e.g. door at bbox 424,917,467,958 — jamb material ends at x=412) |
| `ROOM_MIN_AREA_PX2` (×f²) | 2000 | 588 | 34×34 px sofa-cushion cells (~950–1240 px²) admitted as rooms |
| `WALL_FACE_MIN_LEN_PX` + `COLLINEAR_OFFSET_TOL` | 24 / 4 | 13 / 2.2 | furniture edges become wall faces and enclose the cells above |
| `DOOR_FOLD_JAMB_ANCHOR_TOL_PX` | 6 | 3.25 | the 3.4 / 3.6 px offsets **measured on s01 itself** — folding door_0012 lost |

Side-finding worth keeping: the old rationales' world meanings shift under the
corrected scale — the "≈305 mm" thickness cap was actually admitting
390–546 mm bands; the 48 px thick tier is a ~750 mm chimney breast at 1:92.2,
not a "400 mm band".

## How the ablation was done (reproduce in ~30 min)

Scratchpad scripts are gone; the method is simple:

1. Extract s01 once and pickle the region-filtered `PageData`
   (`extraction.extractor.extract_page` → `pipeline.resolve_page_regions`
   with `skip_gemini=True` → `region_result.detection_page_data`).
   Fixture: `fixtures/sheets/s01-floor-plans.pdf`, page 0.
2. Monkeypatch `WallGates.at` / `RoomGates.at` / `DoorGates.at` with a wrapper
   that scales only a chosen field subset
   (`dataclasses.replace(cls_orig(1.0), **{k: getattr(cls_orig(f), k)})`);
   remember `WALL_THICK_MATERIAL_MAX_PX` must move with
   `WALL_MAX_THICKNESS_PX` or `__post_init__` asserts.
3. Run the stage-5 chain by hand: `detect_doors` → `detect_windows` →
   `_resolve_door_window_conflicts` → `detect_wall_network`
   (with `door_open_leaf_path_indices`) → `_cross_validate` → `_suppress` →
   `detect_rooms`. Score rooms against the f=1 baseline by type+IoU≥0.5
   (same rule as `regression/compare.py`).
4. Two sweeps per hypothesis: scale-one-alone (find culprits) and
   leave-one-unscaled (find rescuers).

## The recalibration task (the "proper fix")

Goal: give every W constant a reference value whose **world meaning** is
derived from corpus measurements at the sheets' *true* scales (s01 relabeled
1:92.2), so that `× f` is trustworthy across the whole factor domain — after
which `_gate_denominator`'s abstention rule can be revisited (that is a new
decision, not a reopening of the frozen table; §4f says the same).

Plan sketch:

1. **Re-measure per constant.** For each W row in §4's tables, find the
   defining corpus features (the docs' rationale strings usually name them:
   "measured on floor-plans…" = s01, "on 5-1133…" = s02) and recompute their
   world sizes with s01 at 92.2. Output: a table of (constant, features,
   world range at true scales, proposed reference value at 1:50).
2. **Check the discrimination margins**, not just the features: each gate
   separates a wall-class quantity from a noise-class quantity (furniture,
   hatch, annotation). Both sides must be re-measured — raising a cap to
   admit s01's 390 mm wall at any scale must not re-admit the furniture pairs
   the cap excludes at f=1 on s02/s15/s17.
3. **Pin with synthetic tests first** (fast tier, ~20 s), per constant.
4. **Sweep the corpus** (`python tools/regress.py`, ~3 min) after each
   constant or small group — memory rule: one fix + one sweep, then ask
   before iterating. Zero LOST confirmed entities, no returned FPs beyond
   the pre-existing 103 (count them, don't eyeball: `grep -c "FALSE POSITIVE
   RETURNED"`).
5. **Update the docs**: findings §4 table rows (new values + provenance),
   §4f closing paragraph, CLAUDE.md's gate paragraph.

Estimate: several days (~15 constants; the original scale-aware branch was
comparable). Not urgent — no corpus sheet currently needs it; the trigger is
a real sheet with a genuine non-standard viewport scale that detects badly.

## Traps

- **Do not revert s01's truth scale to 1:50.** 1:92.2 is metrically correct
  and the takeoff/plausibility layer depends on it (s01 room_0000 = 11.98 m²,
  verified, 31 dimensions).
- The ~103 `FALSE POSITIVE RETURNED` across s04–s20 are pre-existing debt
  (findings §3) — not your regression. s06/s11 also carry 2 unreviewed doors
  each, pre-existing.
- `WALL_WEAK_MATERIAL_PER_100PX` scales **÷ f** (density), and §4b's ratio
  measurements for hatch pitch/length were made with s01 mislabeled 1:50 —
  re-derive them, don't reuse.
- Gate constants live in `WallGates`/`RoomGates`/`DoorGates`.at(); some
  W constants are shared across dataclasses (`WALL_MAX_THICKNESS_PX` on both
  WallGates and RoomGates) — change the module constant, not a copy.
- s13 (viewport 1:136.4, factor 0.367) is pinned by its truth file; any
  reference change must keep it green.
