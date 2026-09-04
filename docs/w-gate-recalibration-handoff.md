# Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)

**Written:** 2026-08-19, after root-causing the s01 @ 1:92.2 detection regression.
**For:** the next agent picking up the recalibration of the world-space (W) detection constants.
**Status of the interim fix:** shipped and green — commit `1f795ed`
(`fix/measured-scale-detection-factor`): measured, non-nominal, non-viewport
denominators no longer drive detection-gate scaling (identity factor, source
`"measured"`, warning `SCALE_FACTOR_MEASURED_ONLY`). This handoff describes the
debt that fix routes around, not a bug in it.
**Status 2026-09-03:** the recalibration is the NEXT detection iteration, ahead
of the queue in `docs/hatch-cell-chords-handoff.md` — see "Status 2026-09-03"
and the fresh-context prompt at the end of this file.

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

## Status 2026-09-03 — this is the next iteration (user decision)

The user chose to do the recalibration BEFORE the rest of the detection
queue (`docs/hatch-cell-chords-handoff.md`: dash rows, the band pockets one
band deeper than the cap, the lattice knife-edges, Gap D), because those
are threshold rules on W-class constants and would otherwise be tuned twice.
What has changed since this handoff was written:

- **Sweep state.** Main is at `b5d293b`. s01 sweeps door 11/11, room 12/12,
  window 4/4 (green); s02 15/15 doors, 11/11 rooms, 11/11 windows; s13
  12/12 / 11/11 / 11/11. The pre-existing returned-FP debt is **71** lines
  over 11 sheets (s04, s05, s08, s11, s12, s14, s15, s16, s17, s18, s20), not
  the 103 above — count it, don't eyeball. A full `python tools/regress.py`
  now exceeds the 10-minute foreground tool limit: run four background
  groups (s18; s16 s11 s15; s01–s07; the rest) against
  `tools/compare_sweeps.py sNN --snapshot` baselines of main, ~2 min
  wall-clock, then diff the reports section-wise.
- **More W constants exist now**, every one calibrated at identity on the
  same half-false premise. Scaled fields today: `WallGates`
  (`WALL_FACE_MIN_LEN_PX` — now 11, not 24; `WALL_MIN_THICKNESS_PX`,
  `WALL_MAX_THICKNESS_PX`, `WALL_THICK_MATERIAL_MAX_PX`,
  `WALL_THROUGH_HATCH_MAX_PX` 64 — new, measured on s05 at 1:100,
  `WALL_PAIR_MIN_OVERLAP_PX`, `WALL_FILL_CLASS_MIN_INK_PX`,
  `WALL_FILL_BLOCK_MAX_SIDE_PX`, `WALL_WEAK_MIN_RUN_PX`,
  `WALL_JOINERY_BRIDGE_GAP_PX`, `WALL_HATCH_MAX_LEN_PX`,
  `COLLINEAR_OFFSET_TOL`, `WALL_ANCHOR_SUPPORT_REACH_PX` 120 — new, "one
  door opening", justified on s01's 59px doorway *at identity*), `RoomGates`
  (`ROOM_MIN_AREA_PX2` ×f², `ROOM_BLIND_WINDOW_MAX_AREA_PX2` ×f²,
  `ROOM_OPENING_SEAL_PX`, `ROOM_PLUG_ANCHOR_WIN_PX`, `ROOM_PLUG_HALF_WIDTH_PX`,
  `ROOM_FOLD_STACK_NEAR_PX`, `ROOM_FOLD_JAMB_MIN_LEN_PX`, plus the two
  walls-owned caps), and `DoorGates` / `WindowGates` / `CrossGates` (findings
  §4d/§4e). Rules shipped since August that sit directly on these caps: the
  thick/through pairing tiers, the collinear-support anchor reach, the
  blind-window drop and today's `_is_band_pocket`
  (`WALL_MAX_THICKNESS_PX`) and `ROOM_ENTRANCE_MIN_CONFIDENCE` (D-class).
- **A concrete instance of the blur** to open the census with:
  `ROOM_BLIND_WINDOW_MAX_AREA_PX2` 10,000 px² was justified as "every real
  window-bearing room on both reference PDFs is ≥ 17k px²". At 1:50 a px² is
  71.7 mm², so 10k px² = 0.72 m² and 17k = 1.22 m²; at s01's 1:92.2 a px² is
  243.8 mm², so the same 10k px² = 2.44 m² and s01's 17k rooms are 4.1 m².
  Likewise `WALL_MAX_THICKNESS_PX` 36 is 305 mm at 1:50 but 562 mm on s01,
  which is how s01's 25px = 390 mm party wall passes at identity.
- **Tooling that did not exist in August**: `tools/_corpus_page.py`
  (`load_detection_pages(slug)` — the region-filtered page data, door
  exclusion set and detection factor per page, exactly as `regress.py` sees
  them; NOTE its `scale_factor` for s01 is 1.0 by the measured-only rule, so
  the census must convert with the TRUE denominator from
  `tests/ground_truth/sNN.json` `scales` / the viewport, not with that
  factor), `tools/diff_wall_network.py … --base-dir <fixtures-linked
  worktree>` (barrier-level attribution; the default temp base loses the
  stored scale), `tools/diff_room_polygons.py` (every moved polygon,
  corpus-wide), `tools/room_shape_crop.py`, `tools/probe_merge_anchor.py`,
  `tools/probe_pair_taper.py`, `tools/probe_fill_seams.py`. For room-stage
  questions, a scratch probe that monkeypatches
  `rooms._free_space_components` and `rooms._restrict_swing_plugs`
  reproduces `detect_rooms`' door geometries exactly (used 2026-09-03).
- **Environment traps** (each cost a cycle): macOS has no `timeout`; the
  venv lacks `InquirerPy`/`prompt_toolkit` (two test modules error at import,
  pre-existing); `tests.test_takeoff_fn_equivalence` fails on main
  (field='warnings', `TAKEOFF_REGIONS_UNCLASSIFIED` in the function arm only)
  and is not a branch signal; a room-label reseed needs
  `gcloud auth application-default login` first and an expired credential
  surfaces only as `ROOM_LABEL_FAILED` in `warnings.json` with exit code 0;
  never `git stash` (shared across worktrees).

### Prompt for the next agent (fresh context)

> Use `/fix-detection` for its discipline — topic branch from `main`,
> `compare_sweeps --snapshot` baselines of main for all 20 slugs, four
> background sweep groups (s18; s16 s11 s15; s01–s07; the rest), verdict
> reports diffed section-wise, `tools/diff_room_polygons.py` on every sheet,
> one checkpoint per iteration — but the task is the **W-gate
> recalibration** of `docs/w-gate-recalibration-handoff.md`, not a
> single-symptom fix, and the deliverable of the FIRST checkpoint is a
> measurement table, not code. Read that handoff in full (its "Status
> 2026-09-03" section last), then `docs/scale-normalization-findings.md`
> §1–§4b, §4f and §5, `scale/factor.py::_gate_denominator` with
> `tests/test_scale_factor.py`, the CLAUDE.md paragraphs "Room detection"
> and "Wall/room world-space gates", and `docs/regression-testing-guide.md`
> §9, §10, §12, §13. The premise to fix: every W-class constant was tuned at
> factor 1.0 as if s01 and s02 were both 1:50, but s01's world ink is 1:92.2
> (31 dimension strings within ±0.5 %; its paper conventions — 1.5px wall
> pen, 4.05px hatch pitch — are standard), so the W references mix 1:50-px
> and 1:92.2-px measurements and their world meanings are accurate only to
> ~1.8×; the shipped `SCALE_FACTOR_MEASURED_ONLY` rule keeps s01 at identity
> precisely because scaling the gates by 50/92.2 puts s01's own calibration
> features outside them (six independent gates break at once — the table in
> the handoff). NEVER revert s01's truth scale to 1:50; 1:92.2 is metrically
> verified and the takeoff depends on it.
>
> **Iteration 1 — the census (stop after it).** For every scaled field of
> `WallGates`, `RoomGates`, `DoorGates`, `WindowGates` and `CrossGates`
> (the `.at()` bodies are the authoritative list; the handoff's status
> section enumerates the walls/rooms ones), find the defining features its
> rationale names — the constant's comment, the CLAUDE.md room paragraph,
> the door/window tuning guides and findings §4b ("measured on floor-plans"
> = s01, "on 5-1133" = s02) — and MEASURE them again on the real sheets,
> converting to world millimetres at each sheet's TRUE scale: 0.16933 mm/px
> × the denominator from `tests/ground_truth/sNN.json` `scales` or the
> viewport (s01 92.2, s02 50, s03 50/100 mixed, s05 100, s13 136.4, s17
> 50/100 mixed, ink-dominant plan), NOT `_corpus_page.load_detection_pages`'
> `scale_factor`, which is 1.0 for s01 by the measured-only rule. For each
> gate measure BOTH sides of its discrimination — the wall-class quantity it
> admits and the noise-class quantity it excludes (furniture pairs, hatch,
> dimension ticks, fixture boxes, tile grids — the rationales name them
> too) — on s01 and s02 at least and on every other sheet the rationale
> cites. Reuse the handoff's ablation method (pickle the region-filtered
> `PageData`, wrap `WallGates.at`/`RoomGates.at`/`DoorGates.at` with
> `dataclasses.replace` to scale one field subset, run the stage-5 chain by
> hand, score by type + IoU ≥ 0.5 against the f=1 baseline) and the probe
> tools listed in the status section. Deliver ONE table: constant · class
> (W / ×f² / ÷f) · current value at 1:50 · defining features with sheet ·
> world range of the true class at true scales · world range of the false
> class · headroom today at f=1.0, 0.5, 0.367 and at s01's 0.542 · proposed
> reference at 1:50 (= mm ÷ 8.47) with the margin it leaves · whether the
> constant needs to move at all (the handoff suspects gate headroom masks
> most of them at the standard factors). Open with the two instances already
> worked out (`ROOM_BLIND_WINDOW_MAX_AREA_PX2`, `WALL_MAX_THICKNESS_PX`) and
> with the six gates that broke at 0.542. Where a margin comes out under
> ~1.5× the discriminator is wrong, not the number — say so in the row.
> Report the table and STOP for the user's verdict on the reference values;
> change no constant before it.
>
> **Iteration 2+ (after the go-ahead).** Move constants in small groups,
> each pinned first by a synthetic test in the fast tier (helpers in
> `tests/test_wall_network.py`, `tests/test_room_detection.py`,
> `tests/test_scale_gates.py`; prove each test bites by reverting), then a
> full-corpus sweep per group against the main snapshots: zero LOST
> confirmed entities, the 71 pre-existing returned FPs unchanged (count
> them), every new REVIEW line given your own verdict from
> `page_NN_changes.png` and `room_shape_crop.py`, and
> `tools/diff_wall_network.py … --base-dir <fixtures-linked worktree of
> main>` for any room that merges or appears. s13 (viewport 1:136.4, f=0.367)
> and the 1:100 sheets (s05, s03/s17's 1:100 plans) are the sheets the
> references actually change; s01/s02 at f=1.0 must not move. Reseed the
> room-label cache of every sheet whose outlines change
> (`python app.py extract fixtures/sheets/<pdf> --out <scratch>
> --ceiling-height 2.4 < /dev/null`, after `gcloud auth
> application-default login`). Then, as its own iteration, revisit
> `_gate_denominator` so that s01 runs at f = 0.542 with its 11 doors, 12
> rooms and 4 windows intact, and only then retire `SCALE_FACTOR_MEASURED_ONLY`
> or narrow it. Finish by updating findings §4's rows (new values +
> provenance), its §4f closing paragraph, the CLAUDE.md gate paragraph and
> this handoff's outcome section. Do not commit, do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`, do not bundle the
> dash rows, the deeper band pockets, the lattice knife-edges or Gap D into
> this branch, and stop at every report with the numbers.

## Outcome — iteration 2 (2026-09-04, branch `recal/w-gate-iter2`)

Iteration 1 (the census, `docs/w-gate-census-2026-09-04.md`) changed no
constant. Iteration 2 moves the references in three groups; each group is
pinned by synthetic tests that fail at the old value, swept against
`compare_sweeps --snapshot` baselines of main `f5682fc` (71 returned FPs,
0 LOST, 5 unreviewed — reproduced before any change), and reported with
before|after pictures. Checkpoint reports live in
`docs/w-gate-iter2-checkpoints/`.

### Group 1 — safe reference moves

| constant | was | now | world @1:50 | margin true / false |
|---|---|---|---|---|
| `WINDOW_MIN_WIDTH_PX` | 14 | 12 | 102 mm | 1.7× under s02's 174 mm; false side does not separate on width |
| `DOOR_FOLD_JAMB_ANCHOR_TOL_PX` | 6 | 10 | 85 mm | 1.5× over s01's 56 mm (true 1:92.2) |
| `WALL_THROUGH_HATCH_MAX_PX` | 64 | 72 | 610 mm | 1.28× over s05's 475 mm wall; 1.13× under s01's first through-hatched fixture |
| `CROSS_DOOR_EXPAND_PX` | 20 | **16** (census said 10) | 135 mm | 1.55× over s18's 100 mm door lining (needs 10.3 px); 1.56× under s03's window lost at 25 px |

Corpus sweep of the final group: see the checkpoint report. The one
surprise: the census's 10 px for `CROSS_DOOR_EXPAND_PX` uncovered a
phantom window on s18 — a 100 mm door lining touching a door's hinge corner
is covered only diagonally by the dilation and needs 10.3 px at 1:50 to reach
the 10 % cover rule. One-field ablation could not see it because the lining
was vetoed at every multiplier the census tried above 0.5×; it is the
"discriminator has two false classes" case, and 16 is the value that leaves
≥ 1.5× on both sides. `WALL_THICK_MATERIAL_MAX_PX` stays 48 until group 3's
per-band hatch-mark cap (at f=0.5 a 56 cap is 28 px, where s05's wall pairs).

### Group 2 — thin-margin moves (three of five tried and reverted)

| constant | census | shipped | why |
|---|---|---|---|
| `WALL_MAX_THICKNESS_PX` | 36 → 40 | **36** | 40 removed five recorded phantoms (s17's four 35 px reveal strips in its 37 px = 313 mm cavity walls; s16's striped block) but the 36–40 px band holds fixtures at wall spacing: s02's WC wall face × hairline basin edge at 38.25 px over section-line dashes (notched the WC 14 %), s01's 38.5 px kitchen units (600 mm at 1:92.2) pairing and lattice-demoting (hob fenced), +1 phantom each on s11/s15/s18. Thresholds 37.0 / 38.25 / 38.5 — spacing is not the discriminator |
| `WALL_FACE_MIN_LEN_PX` | 11 → 9 | **11** | a band's 45° hatch is T√2 long: s01's 7 px partitions hatch at 9.9 px and the band-end strokes paired (room_0003 edge jogged 4 px; s02 −55 px²); s18 worktop run fenced (−1 FP, +1 phantom) |
| `WALL_WEAK_MATERIAL_PER_100PX` | 3.0 → 2.2 | **2.2** | inert on the corpus at entity and polygon level |
| `ROOM_OPENING_SEAL_PX` | 12 → 15 | **12** | no value above 12 is safe: the tail touch reach is SEAL + `ROOM_PLUG_HALF_WIDTH_PX`, and a hinge-less door's swing-side edge within it of two walls becomes an interrupted plug — s15 lost two door swings at 14, s02's BEDROOM 2 was notched around a section marker at 15, s01 room_0005 moved at 13–14 |
| `CROSS_WALL_EXPAND_PX` | 20 → 24 | **24** | inert on the corpus at entity and polygon level |

The pattern: every census margin under ~1.25× on the *discriminator* (its ⚠
rows) broke on the sweep the moment the number moved — always by admitting a
drawn fixture the one-field ablation could not see because another gate had
been holding it out. The three reverts each name the prerequisite rule:
a mark-class rule (section-line dashes, cupboard X's ≠ hatch), a swing-side
veto for hinge-less doors, and s01's true-scale factor (its 9.9 px hatch
strokes and 38.5 px kitchen units are 1:92.2 quantities detected at
identity).

### Group 3 — class fixes

**3a — per-band hatch-mark cap + `WALL_THICK_MATERIAL_MAX_PX` 48 → 56
(shipped).** `_collect_material_marks` runs once at the through-hatch
diagonal; `_band_has_wall_material` filters to `_mark_len_cap(T)` =
max(`WALL_HATCH_MAX_LEN_PX`, T√2 + 2) and counts a mark longer than the
page-wide cap only when both its ends lie on the band's faces (through-hatch).
The first corpus sweep without that condition was verdict-identical but
paired s17's stair stringers (48 px apart) on two arrowhead barbs and two
cut lines — exactly the 4-mark floor, reachable only since Group 2 lowered
the density to 2.2/100 px (at 3.0 a 141 px band needs 5) — and fenced the
flight out of its hall (room_0006 −5.9k px², IoU 0.73). With the condition:
verdicts identical to baseline, s05 9/9 rooms via the thick tier, two
sub-1 % outline improvements (s11 porch +144 px², s13 bedroom +146 px²).
`tests/test_through_hatch_band.py` now pins the tier above 56 with a 64 px
band. The lone-face helpers and the stair/barrier ceilings keep 48.

**3b — `COLLINEAR_OFFSET_TOL` as paper-with-ceiling (measured, no code
change).** Harness on s11, s16, s13, s02, s03, s18 and s01 at 0.542 for the
current 4f, unscaled 4.0 and min(4.0, 6f): the two paper forms both lose a
confirmed s18 room (its 47 mm partitions at 1:100 hold at 2.5 px and fuse at
2.75 → ceiling 5.5 × f; unscaled 4.0 also adds three phantoms on s18 and one
on s16). The widest safe form, min(4.0, 5f), changes no sheet and does not
reach the 3.25 px that cuts s01's phantoms 18 → 1 at 0.542 — and at 0.542
s01 loses four rooms whatever the tolerance (the thick-tier short-piece
issue). The value stays 4 × f, 1.37× under the ceiling; the findings row now
reads "P true class, W ceiling, numerically W", pinned by
`test_scaled_tolerance_stays_under_the_partition_ceiling`.

**3c — `ROOM_PLUG_HALF_WIDTH_PX` paper floor (shipped).** `RoomGates.at`
floors it at `ROOM_LINE_BARRIER_PX` (2.0), not 3.0 (which loses s13's room
at (1040,999)–(1079,1085)). Corpus sweep: verdicts identical; s13's eleven
rooms move by the 0.16 px plug growth (IoU ≥ 0.987).

### Where this leaves `_gate_denominator` (the final iteration)

See the Group 3 checkpoint report for the s01mode re-run on the final tree.

s01mode on the final tree: f=0.542 keeps 11/11 doors and 4/4 windows, loses
4/12 rooms with 18 phantoms; the solo culprits are now only
`WALL_MAX_THICKNESS_PX` (the short-piece material issue the census predicted)
and `ROOM_OPENING_SEAL_PX` (reverted in Group 2). `_gate_denominator` is
unchanged; `SCALE_FACTOR_MEASURED_ONLY` stays. Next iteration: the short-piece
material rule, the hinge-less swing-side veto, the mark-class rule.

### Prompt for the next agent (iteration 3 — fresh context)

> Use `/fix-detection` for its discipline (topic branch from `main`;
> `compare_sweeps --snapshot` baselines of main for all 20 slugs; four
> background sweep groups — s18; s16 s11 s15; s01–s07; the rest — because a
> full `regress.py` exceeds the 10-minute foreground limit; verdict reports
> diffed section-wise; `tools/diff_room_polygons.py` on every sheet after
> EVERY sweep, and a `tools/room_shape_crop.py` crop of every room whose IoU
> moved under 0.99 — a verdict-identical sweep is not a clean sweep, three of
> iteration 2's reverts were caught only by polygon diffs). Read first, in
> this order: `docs/w-gate-iter2-checkpoints/group-{1,2,3}.md` (what shipped,
> what was tried and why it was reverted, with the measured false classes),
> this handoff's "Outcome — iteration 2" section, the "move?" column of
> `docs/w-gate-census-2026-09-04.md`, the CLAUDE.md paragraphs "Room
> detection" and "Wall/room world-space gates", and
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> Tooling you inherit in `tools/census_scratch/` (untracked cache/abl dirs
> are rebuilt on first use): `harness.py` runs the exact stage-5 chain with
> gate overrides (`overrides(mult=…)` / `overrides(absolute=…)`) and scores
> against ground truth; `attrib.py <slug> x0 y0 x1 y1 FIELD=MULT[,FIELD=MULT]…`
> reports whether a target bbox survives each single-field override;
> `attrib_delta.py` lists rooms that appear/vanish per override;
> `attrib_rooms.py` lists rooms whose polygon differs from the baseline
> snapshot per override; `collinear_probe.py`, `probe_exemption.py`,
> `ablate.py s01 s01mode`. Use them to attribute every change to ONE
> constant or rule before deciding anything; the sweep stays the arbiter.
> `tools/diff_wall_network.py sNN X0 Y0 X1 Y1 --base-dir <worktree of main
> with fixtures/sheets symlinked>` for barrier-level attribution (the default
> base loses the stored scale).
>
> State you start from: main carries iteration 2. Shipped: WINDOW_MIN_WIDTH
> 12, DOOR_FOLD_JAMB_ANCHOR_TOL 10, WALL_THROUGH_HATCH_MAX 72, CROSS_DOOR_EXPAND
> 16, WALL_WEAK_MATERIAL_PER_100PX 2.2, CROSS_WALL_EXPAND 24, the per-band
> hatch-mark cap `_mark_len_cap` (long marks count only as through-hatch),
> WALL_THICK_MATERIAL_MAX 56, ROOM_PLUG_HALF_WIDTH floored at 2.0. Tried and
> reverted, each with its false class in the constant's comment:
> WALL_MAX_THICKNESS 40, WALL_FACE_MIN_LEN 9, ROOM_OPENING_SEAL 15/14/13.
> COLLINEAR_OFFSET_TOL stays 4f (s18's 47mm partitions fuse at 2.75px at
> f=0.5). Corpus: 71 returned FPs, 0 LOST, 5 unreviewed — count them with
> `grep -c "FALSE POSITIVE RETURNED"`. s01 at f=0.542 keeps 11 doors and 4
> windows but loses 4/12 rooms; `_gate_denominator` is unchanged.
>
> Three iterations, in this order, ONE rule per iteration, each with its own
> synthetic test (fails without the rule), harness pre-check on the named
> sheets, full sweep, polygon diff with crops, verdicts on every new REVIEW
> line, room-label reseed of every sheet whose outlines changed (`gcloud
> auth application-default login` first; an expired credential shows only as
> ROOM_LABEL_FAILED in warnings.json with exit 0), prose (constant comment,
> CLAUDE.md room paragraph, findings §4, this handoff) and a checkpoint
> report in the fix-detection template with before|after pictures:
>
> 1. **Mark-class rule** (walls, `_collect_material_marks` /
>    `_band_has_wall_material`): a dashed section line's dashes and a
>    cupboard's X diagonals are not hatch. Measured instance: s02's WC wall
>    face paired at 38.25px with a hairline basin edge (paths 5743–5745) over
>    the diagonal section line's dashes once the cap was 40 (needs cap ≥
>    38.25, face floor ≤ 9, density ≤ 2.7). Find the drawing-convention
>    difference (hatch is a regular-pitch field of parallel strokes; a
>    section line is ONE collinear row of dashes; cupboard X's are two
>    crossing diagonals per box) and measure it on s01/s02 and the sheet.
>    Then retry WALL_MAX_THICKNESS 36 → 40 in the SAME sweep only if the
>    rule alone is green: expected −5 recorded phantoms (s16 room at
>    (2502,1563); s17 rooms at (929,2252), (3064,2331), (3065,2828),
>    (931,2838)), and s01's kitchen units (38.5px = 600mm at 1:92.2, paths
>    3183/3184/939/940/946) must NOT pair — if they do, the cap waits for
>    s01's true-scale factor; also the 40-cap phantoms on s11 (wall-recess
>    box (1030,1330)–(1123,1360)), s15 (annotation pocket
>    (1480,698)–(1595,792)) and s18 (tree strip (156,724)–(197,827)) must
>    stay out.
> 2. **Hinge-less swing-side veto** (rooms, `_door_plugs` /
>    `_restrict_swing_plugs`): a door with no derivable hinge edge must not
>    get an interrupted plug along an edge that is its swing side. Measured:
>    the tail touch reach is SEAL + ROOM_PLUG_HALF_WIDTH_PX, so any bbox edge
>    whose ends lie within it of two walls qualifies; at seal 14 s15 rooms
>    0023/0024 lost their top-door swings (−5.4k px² each), at 15 s02's
>    BEDROOM 2 was notched around its "A" section-marker bar (a fallback
>    door on it), at 13–14 s01 room_0005 moved. Synthetic pins already
>    exist at 26–28px clearance in test_room_detection (the closet and
>    white-ring fixtures). Then retry ROOM_OPENING_SEAL 12 → 15 in the same
>    sweep only if the veto alone is green: expected s04 room_0002 +10k px²
>    (the bedroom's notch), s02/s15/s01 unchanged, s03's two recorded FP
>    rooms still out (they return at 18).
> 3. **Short-piece material rule** (thick tier): a hatched band's piece
>    between two openings (s01: 36px, 3 marks) fails the ≥4-marks/span gates
>    and the room leaks at f=0.542; make such a piece inherit the material
>    verdict of the collinear band it continues. Then re-run `ablate.py s01
>    s01mode`; if s01 at 0.542 keeps 11 doors, 12 rooms and 4 windows, narrow
>    `scale/factor.py::_gate_denominator` so a user-stored non-nominal
>    denominator drives the gates, update `tests/test_scale_factor.py`, and
>    retire or narrow `SCALE_FACTOR_MEASURED_ONLY` with the sweep as proof.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2 is metrically verified); do not bundle the dash
> rows, deeper band pockets, lattice knife-edges or Gap D; never `git stash`;
> macOS has no `timeout`; the venv lacks InquirerPy and
> `tests.test_takeoff_fn_equivalence` fails on main — neither is a branch
> signal; s01 and s02 at f=1.0 must not change (entity set AND polygons);
> if a rule costs a confirmed entity or returns an FP, revert it, report why,
> and STOP. End every checkpoint report with the numbers: lost, returned FPs,
> new REVIEW lines with your verdicts, net phantom delta, and what is next.
