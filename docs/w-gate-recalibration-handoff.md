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
| `WALL_MAX_THICKNESS_PX` | 36 → 40 | **36** | 40 removed five recorded phantoms (s17's four 35 px reveal strips in its 37 px = 313 mm cavity walls; s16's striped block) but the 36–40 px band holds fixtures at wall spacing: s02's WC wall face × hairline basin edge at 38.25 px over two 13 px corner X symbols (notched the WC 14 %; cleared by iteration 3's far-side density rule), s01's 38.5 px kitchen units (600 mm at 1:92.2) pairing and lattice-demoting (hob fenced), +1 phantom each on s11/s15/s18. Thresholds 37.0 / 38.25 / 38.5 — spacing is not the discriminator |
| `WALL_FACE_MIN_LEN_PX` | 11 → 9 | **11** | a band's 45° hatch is T√2 long: s01's 7 px partitions hatch at 9.9 px and the band-end strokes paired (room_0003 edge jogged 4 px; s02 −55 px²); s18 worktop run fenced (−1 FP, +1 phantom) |
| `WALL_WEAK_MATERIAL_PER_100PX` | 3.0 → 2.2 | **2.2** | inert on the corpus at entity and polygon level |
| `ROOM_OPENING_SEAL_PX` | 12 → 15 | **12** | no value above 12 is safe: the tail touch reach is SEAL + `ROOM_PLUG_HALF_WIDTH_PX`, and a hinge-less door's swing-side edge within it of two walls becomes an interrupted plug — s15 lost two door swings at 14, s02's BEDROOM 2 was notched around a section marker at 15, s01 room_0005 moved at 13–14 |
| `CROSS_WALL_EXPAND_PX` | 20 → 24 | **24** | inert on the corpus at entity and polygon level |

The pattern: every census margin under ~1.25× on the *discriminator* (its ⚠
rows) broke on the sweep the moment the number moved — always by admitting a
drawn fixture the one-field ablation could not see because another gate had
been holding it out. The three reverts each name the prerequisite rule:
the far-side density rule (shipped, iteration 3 step 1), a swing-side
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

## Outcome — iteration 3, step 1 (2026-09-04, branch `fix/section-line-dashes-not-hatch`)

The "mark-class rule" premise was refuted by measurement: the s02 WC
phantom's material is two 13 px corner X symbols at the band's ends (the
section line's dashes are PDF-dashed strokes and never become marks), and
six mark-shape statistics all overlap real bands. What separates it is the
material density RATIO to the hatched wall sharing its far-side face: real
weak pairs ≥ 1.0×, the phantom 0.11×. Shipped as `_claims_far_side_sparse` /
`WALL_FAR_SIDE_DENSITY_RATIO` 0.33 with pins; sweep byte-identical to the
iteration-2 tree. Cap 40 retried in the harness on top of it: s02 fixed,
s17 −4 and s16 −1 recorded phantoms, but s01's 38.5 px kitchen units still
pair and the s11 recess box, s15 annotation pocket and s18 tree strip return
— two of the brief's three shipping conditions fail, so the cap stays 36.
Report: `docs/w-gate-iter3-checkpoints/step-1.md`. Next: step 2 (hinge-less
swing-side veto, then the seal retry), step 3 (short-piece material rule,
s01mode, `_gate_denominator`).

### Prompt for the next agent (iteration 3, step 2 onward — fresh context)

> Use `/fix-detection` for its discipline (topic branch; `compare_sweeps
> --snapshot` baselines of the tree you start from for all 20 slugs; four
> background sweep groups — s18; s16 s11 s15; s01–s07; the rest — a full
> `regress.py` exceeds the 10-minute foreground limit; verdict reports diffed
> section-wise; `tools/diff_room_polygons.py` on every sheet after EVERY
> sweep and a `tools/room_shape_crop.py` crop of every room whose IoU moved
> under 0.99 — verdict-identical is not clean, most of this work's reverts
> were caught only by polygon diffs). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-1.md`,
> `docs/w-gate-iter2-checkpoints/group-2.md` (the seal section and its
> pictures), the "Outcome" sections at the end of
> `docs/w-gate-recalibration-handoff.md`, the CLAUDE.md paragraphs "Room
> detection" and "Wall/room world-space gates", `detection/rooms.py::
> _door_plugs` and `_restrict_swing_plugs` with their docstrings, and
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> Where the tree is: main is `f5682fc`; iteration 2 is committed on
> `recal/w-gate-iter2` (b8aaa0f…376059a); iteration 3 step 1 (the far-side
> density rule, `_claims_far_side_sparse`) lives on
> `fix/section-line-dashes-not-hatch`, committed or merged by the user by the
> time you read this — check `git log --all --oneline | head` and `grep -n
> _claims_far_side_sparse detection/walls.py`; branch from the tip that has
> it. The corpus state on that tree: 71 returned FPs, 0 LOST, 5 unreviewed
> (`grep -c "FALSE POSITIVE RETURNED"`), byte-identical to main's verdicts;
> polygons differ from main only on s11 room_0003 (+144 px²), s13 (plugs
> 0.16 px wider) and s01 door_0012's bbox. Constants as of step 1:
> WALL_MAX_THICKNESS 36, WALL_FACE_MIN_LEN 11, ROOM_OPENING_SEAL 12,
> WALL_WEAK_MATERIAL_PER_100PX 2.2, CROSS_WALL_EXPAND 24, CROSS_DOOR_EXPAND
> 16, WALL_THICK_MATERIAL_MAX 56, WALL_THROUGH_HATCH_MAX 72, the per-band
> mark cap `_mark_len_cap`, ROOM_PLUG_HALF_WIDTH floored at 2.0,
> WALL_FAR_SIDE_DENSITY_RATIO 0.33.
>
> Tooling in `tools/census_scratch/` (cache/abl gitignored, rebuilt on first
> use): `harness.py` (exact stage-5 chain with `overrides(mult=…)` /
> `overrides(absolute=…)`), `attrib_rooms.py <slug> FIELD=MULT…` (rooms whose
> polygon differs from the baseline snapshot per single-field override),
> `attrib_delta.py` (rooms that appear/vanish per override), `attrib.py`
> (does a target bbox survive), `collinear_probe.py`, `probe_exemption.py`,
> `ablate.py s01 s01mode`. `tools/diff_wall_network.py sNN X0 Y0 X1 Y1
> --base-dir <worktree of the start tree with fixtures/sheets symlinked>` for
> barrier-level attribution. Attribute every change to ONE rule or constant
> before deciding; the sweep stays the arbiter.
>
> **Step 2 — hinge-less swing-side veto (rooms), then the seal retry.**
> Mechanism, measured in iteration 2: `_door_plugs` extends each bbox edge by
> ROOM_OPENING_SEAL_PX and calls an edge "interrupted" when its end windows
> TOUCH wall material within ROOM_PLUG_HALF_WIDTH_PX (5) and the middle is
> empty, so any edge whose ends fall within SEAL + 5 px of two walls
> qualifies; `_restrict_swing_plugs` holds SINGLE swing doors to their hinge
> edges, but a door with no derivable hinge (`_swing_hinge_edges` empty:
> pairs, arc-only, fallback tiers) keeps every edge, including its swing
> side. At seal 15 (harness: `attrib_rooms.py s15 ROOM_OPENING_SEAL_PX=1.25`,
> same for s02, s01, s04) this fenced s15's top-door swings out of rooms
> 0023/0024 (symdiff at [849,1638]–[937,1736] and [941,1638]–[1267,2272],
> −5.4k px² each; also rooms 0019/0020 at [849,1620]–[937,1631] and
> [941,1621]–[1009,1631] — the "810mm door set" at the top of the corridor
> and lounge), notched s02's BEDROOM 2 around its "A" section-marker bar (a
> fallback door detected on the bar; symdiff [1128,282]–[1144,372]), moved
> s01 room_0005 at 13–14, and — the improvement to regain — cleaned s04
> room_0002 (+10,345 px², the bedroom's bottom-left notch) and rooms
> 0001/0004. Pictures: `docs/w-gate-iter2-checkpoints/g2_s15_seal15_*.png`,
> `g2_s02_seal15_section_marker_notch.png`, `g2_s04_seal15_bedroom_improved.png`.
> Two synthetic fixtures already sit just outside the reach
> (`tests/test_room_detection.py`: the closet in
> TestRejectedDoorIsNotAnEntrance at 28 px clearance, the white-ring symbol
> in TestPhantomDoorSeals at 26 px) — move them back to 20 px as the pins
> once the veto exists. Find the drawing-convention difference and measure
> it on s15/s02/s04 AND s01/s02's real doorways before coding; the
> hypothesis to test first: a doorway edge's anchors are the two ends of the
> SAME wall run (material collinear with the edge — jamb nibs in the edge's
> own line), whereas a swing-side edge's anchors are two DIFFERENT walls it
> meets perpendicularly (material crossing the edge line at its ends, none
> along it). Then, only if the veto alone sweeps green (verdicts and
> polygons identical), retry ROOM_OPENING_SEAL 12 → 15 in the same
> checkpoint: expected s04 room_0002 +10k px², s02/s15/s01 unchanged, s03's
> two recorded FP rooms still out (they return at 18). If the seal still
> moves s01 or s02, it stays 12 and you report why.
>
> **Step 3 — short-piece material rule (thick tier), then `_gate_denominator`.**
> At f=0.542 s01's 21–25 px hatched walls pass the thick tier but their 36 px
> pieces between openings carry 3 marks and fail the ≥4-marks/span gates
> (`_band_has_wall_material`), leaking 4 of 12 rooms; make such a piece
> inherit the material verdict of the collinear band it continues. Then
> `python tools/census_scratch/ablate.py s01 s01mode` (log:
> `docs/w-gate-iter2-checkpoints/final_s01mode.txt` is the reference: doors
> 11/11, windows 4/4, rooms 8/12, 18 phantoms today; solo culprits
> WALL_MAX_THICKNESS and ROOM_OPENING_SEAL). If s01 at 0.542 keeps 11 doors,
> 12 rooms and 4 windows, narrow `scale/factor.py::_gate_denominator` so a
> user-stored non-nominal denominator drives the gates, update
> `tests/test_scale_factor.py`, retire or narrow `SCALE_FACTOR_MEASURED_ONLY`
> with the sweep as proof, then re-try WALL_MAX_THICKNESS 40 (blocked today
> by s01's 38.5 px kitchen units and the s11/s15/s18 pockets — see step-1.md).
>
> Every step: synthetic test first (must fail without the rule), harness
> pre-check on the named sheets, full sweep, polygon diff with crops,
> verdicts on every new REVIEW line, room-label reseed of every sheet whose
> outlines changed (`gcloud auth application-default login` first; an
> expired credential shows only as ROOM_LABEL_FAILED in warnings.json with
> exit 0; reseed with `python app.py extract fixtures/sheets/<pdf> --out
> <scratch> --ceiling-height 2.4 < /dev/null`), prose (constant comment,
> CLAUDE.md room paragraph, findings §4, this handoff's outcome section), a
> checkpoint report in the fix-detection template with before|after pictures
> under `docs/w-gate-iter3-checkpoints/`, and STOP at the checkpoint for the
> user's decision. Rules: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); do not bundle the dash rows, deeper band
> pockets, lattice knife-edges or Gap D; never `git stash`; macOS has no
> `timeout`; the venv lacks InquirerPy and `tests.test_takeoff_fn_equivalence`
> can fail on main — neither is a branch signal; s01 and s02 at f=1.0 must
> not change (entity set AND polygons); if a rule costs a confirmed entity or
> returns an FP, revert it, report why, and STOP. End every report with the
> numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next. Housekeeping the user still owns: the
> iteration-2 PNG crops are untracked and one
> (`g2_s04_seal15_bedroom_improved.png`) shows a street address printed on
> the drawing — it must never be committed.

## Outcome — iteration 3, step 2 (2026-09-04, branch `fix/hingeless-swing-side-veto`)

The "hinge-less swing-side veto" premise was refuted by measurement on both
sides. (a) None of the seal-15 regressions is a hinge-less swing-side plug:
s15's corridor door (door_0013, hinged) loses its DOORWAY plug at 14 because
the dashed "steel ridge beam" row (14.8 px strokes, 2.0 px pen, strong
barrier faces) crosses the doorway plane at its centre and the mid-window
in-plane count flips 2/10 → 3/11 with the sampling phase, so the 0.67 door
falls to the bbox stamp (the dash-row class, excluded from this iteration);
s02's BEDROOM 2 is notched at 15 because the 0.35 fallback door on the "A"
section-marker bar carries full-cover plugs whose tails end at the last
sample within the 5 px touch tolerance, 4.8 px past the bar, narrowing the
20.5 px neck to the wall under the 16 px free-space pinch; s01 room_0005
moves 6 px at 13–14 because door_0002's plug cross-section fit flips 4 → 10
px with the anchor sample set. (b) The hypothesised discriminator (a doorway
edge's anchors are collinear, a swing edge's cross it) does not separate on
the true class: of 100 hinge-derived doorway plugs on the corpus, 56 have a
perpendicular-only anchor (jamb end caps, the return wall the leaf parks
against) and 30 an anchor spanning more than a wall thickness across the
edge line; and of the 44 interrupted plugs on hinge-less doors, none is a
swing side (13 garden doorways, 4 folding planes, 26 fallback-tier boxes,
1 s18 single leaf). No corpus instance of the false class exists at 12 or
15, so no veto was built and the synthetic fixtures stay at 26–28 px.

What the s04 "improvement at 15" actually was: a corner door LINING the
lining rule rejected. door_0001's top jamb is the corner where the divider
meets BATHROOM 02's bottom band, so the lining shifted one ring-length up
lands in the perpendicular band (31.3 px across the 22.2 px probe) exactly
like the wedged fixture the rule excludes. Shipped: `_is_door_lining` also
accepts the ring when the strip of its own across-range one to two ring
depths beyond the opening's far edge is band material with the ring's
cross-section (a doorway is cut out of a wall; the wall resumes past the far
jamb). Pins: `TestDoorLiningRings.test_corner_lining_anchors_the_doorway_plug`
(fails without the rule) and `test_fixture_box_at_the_corner_is_not_wall`.
Sweep vs the main baseline: 0 LOST, 71 returned FPs, 5 REVIEW — verdicts
byte-identical; polygons change only on s04 (room_0002 MASTER BEDROOM
+10,745 px², room_0004 +1,127 px²); s04's labels reseeded. The far-side
strip admits three rings corpus-wide: s04 path 949 and two 2.5 px slivers
on s18 that change nothing. `ROOM_OPENING_SEAL_PX` stays 12; the constant
comment, `TestPlugSealReach`, findings §4 and group-2.md now carry the
measured mechanisms. Report: `docs/w-gate-iter3-checkpoints/step-2.md`.
Next: step 3 (short-piece material rule, s01mode, `_gate_denominator`); the
seal retry waits for the dash rows and a tail that ends AT the material it
shadows.

### Prompt for the next agent (iteration 3, step 3 — fresh context)

> Use `/fix-detection` for its discipline (topic branch from the tip that
> carries step 2 — `git log --all --oneline | head`, `grep -n far_strip
> detection/rooms.py`; if the user has not merged `fix/hingeless-swing-side-veto`
> into main yet, branch from that branch; `compare_sweeps --snapshot`
> baselines of that tree for all 20 slugs, re-swept first — never trust
> whatever sits in `outputs/regress/`; four background sweep groups — s18;
> s16 s11 s15; s01–s07; the rest — a full `regress.py` exceeds the 10-minute
> foreground limit; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` on every sheet after EVERY sweep and a
> `tools/room_shape_crop.py` crop of every room whose IoU moved under 0.99 —
> verdict-identical is not clean). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-2.md` (what the seal-15 sites really
> are — the swing-side veto is dead, do not resurrect it), `step-1.md`,
> `docs/w-gate-iter2-checkpoints/group-3.md` (3a the per-band mark cap, 3b
> the collinear tolerance ceiling), `final_s01mode.txt` (the reference
> ablation log), this handoff's iteration-2/3 outcome sections, the CLAUDE.md
> paragraphs "Room detection" and "Wall/room world-space gates",
> `detection/walls.py::_band_has_wall_material`, `_band_material_ts`,
> `_mark_len_cap`, `_claims_far_side_sparse`, `_merge_collinear_segs` and
> `_pair_faces_to_centerlines` with their docstrings,
> `scale/factor.py::_gate_denominator` + `tests/test_scale_factor.py`, and
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> Tree state: main `ee0f52f` + branch `fix/hingeless-swing-side-veto`
> (the corner door-lining rule in `_is_door_lining`; the seal stays 12).
> Corpus: 71 returned FPs, 0 LOST, 5 unreviewed (`grep -c "FALSE POSITIVE
> RETURNED"`); polygons differ from `ee0f52f` only on s04 rooms 0002/0004.
> Constants: WALL_MAX_THICKNESS 36, WALL_FACE_MIN_LEN 11, ROOM_OPENING_SEAL
> 12, WALL_WEAK_MATERIAL_PER_100PX 2.2, CROSS_WALL_EXPAND 24,
> CROSS_DOOR_EXPAND 16, WALL_THICK_MATERIAL_MAX 56, WALL_THROUGH_HATCH_MAX
> 72, `_mark_len_cap` per band, ROOM_PLUG_HALF_WIDTH floored at 2.0,
> WALL_FAR_SIDE_DENSITY_RATIO 0.33, COLLINEAR_OFFSET_TOL 4×f.
>
> Tooling in `tools/census_scratch/` (cache/abl gitignored, rebuilt on
> first use): `harness.py` (the exact stage-5 chain with `overrides(mult=…)`
> / `overrides(absolute=…)` and instrumentation taps), `attrib_rooms.py
> <slug> FIELD=MULT…` (rooms whose polygon differs from the baseline
> snapshot per single-field override — run it with NO override first to see
> what the current tree changes), `attrib_delta.py`, `attrib.py`,
> `collinear_probe.py`, `probe_exemption.py`, `ablate.py s01 s01mode`, and
> from step 2: `probe_plugs.py <slug> [SEAL]` (every door's plug profile per
> edge with anchor classes), `probe_box.py <slug> <seal> x0 y0 x1 y1 [door_id]`
> (every door seal, plug polygon and barrier area inside a box, with a
> per-sample distance dump for the named door), `probe_survey.py <slug>…`
> (every kept interrupted plug on a sheet). `tools/diff_wall_network.py sNN
> X0 Y0 X1 Y1 --base-dir <worktree of the start tree with fixtures/sheets
> symlinked>` for barrier-level attribution. Attribute every change to ONE
> rule or constant before deciding; the sweep stays the arbiter. Room-label
> reseed of every sheet whose outlines changed: `gcloud auth
> application-default print-access-token` first (an expired credential shows
> only as ROOM_LABEL_FAILED in warnings.json with exit 0), then `python
> app.py extract fixtures/sheets/<pdf> --out <scratch> --ceiling-height 2.4
> < /dev/null`, then re-sweep the sheet and check its warning count returns
> to the baseline's.
>
> **Step 3 — short-piece material rule (thick tier), then `_gate_denominator`.**
> At f=0.542 s01's 21–25 px hatched walls pass the thick tier but their
> ~36 px pieces between openings carry 3 marks and fail the ≥ 4-marks/span
> gates in `_band_has_wall_material`, leaking 4 of 12 rooms (log:
> `final_s01mode.txt`; solo culprits WALL_MAX_THICKNESS and
> ROOM_OPENING_SEAL). Measure first, with a tap on `_band_has_wall_material`
> in the harness (`Taps.material` already records n/per100/span per band):
> which pieces fail on s01 at 0.542, and whether the same short-piece
> signature exists at identity on s02 (stud partitions between doors), s03's
> 1:100 plan and s05 (the thick-tier sheet) — both classes, i.e. the short
> hatched wall piece between two openings AND any short fixture band that is
> collinear with a real wall (a radiator casing, a worktop end, a cupboard
> front in the wall's line). State the convention before coding: a band
> interrupted by openings is ONE band, so a piece that lies on a hatched
> band's own faces (within COLLINEAR_OFFSET_TOL, at the band's thickness,
> `_merge_collinear_segs`' membership test) with a door/window bbox in the
> gap between them inherits that band's material verdict; a collinear
> fixture has no opening between it and the band and its own marks are
> under the far-side density ratio. Synthetic test first (fails without the
> rule), harness pre-check on s01 at 0.542 (`overrides` with factor 0.542
> via `H.run(page, factor=0.542)`) AND on s01/s02/s03/s05 at their normal
> factors (must be identical), full sweep, polygon diff with crops,
> verdicts on every REVIEW line, reseed, prose (the constant/rule comment,
> CLAUDE.md room paragraph, findings §4, this handoff), checkpoint report
> `docs/w-gate-iter3-checkpoints/step-3.md` with before|after pictures, and
> STOP for the user's decision. Then, in the SAME checkpoint only if the
> rule alone is green: `python tools/census_scratch/ablate.py s01 s01mode`;
> if s01 at 0.542 keeps 11 doors, 12 rooms and 4 windows, narrow
> `scale/factor.py::_gate_denominator` so a user-stored non-nominal
> denominator drives the gates, update `tests/test_scale_factor.py`, retire
> or narrow `SCALE_FACTOR_MEASURED_ONLY` with the full sweep as proof (s01
> is then detected at f=0.542 — every s01 entity and polygon must survive,
> that is the whole point), and report. If s01 at 0.542 still loses rooms,
> name the next solo culprit from the ablation log and STOP.
>
> **After step 3, in this order, one rule per checkpoint:**
> 4. `WALL_MAX_THICKNESS_PX` 36 → 40 retry — only once s01 runs at its
>    true factor (its 38.5 px kitchen units become 20.9 px and stop pairing)
>    and the far-side density rule is in; the three cap-40 phantoms
>    (s11 wall-recess box (1030,1330)–(1123,1360), s15 annotation pocket
>    (1480,698)–(1595,792), s18 tree strip (156,724)–(197,863)) must stay
>    out, expected −5 recorded phantoms on s16/s17 (`step-1.md`).
> 5. Plug tails end AT the material they shadow, not up to
>    ROOM_PLUG_HALF_WIDTH_PX past it (`_door_plugs` tail trim; s02 door_0050
>    on the "A" bar, 4.8 px overshoot, `step-2.md`) — inert at seal 12, a
>    prerequisite for any seal move.
> 6. Dash rows: a collinear row of equal short pieces at equal gaps is a
>    DRAWN DASH LINE, never a barrier face and never a collinear-anchor vote
>    (s15's "steel ridge beam" row, 14.8 px strokes, 2.0 px pen: it splits
>    the corridor from the lounge and crosses door_0013's doorway plane;
>    s15 room_0016 in the anchor-line report). Check the s15 ground truth
>    before touching it — rooms 0023/0024 may be confirmed as split.
> 7. `ROOM_OPENING_SEAL_PX` 12 → 15 retry — only after 5 and 6; expected
>    s01/s02/s15 unchanged, s03's two recorded FP rooms still out (they
>    return at 18), s01 room_0005 at 13–14 is the plug-fit fallback
>    (`_door_plugs` "anchors disagree → full envelope"), its own knife-edge.
> 8. Deeper band pockets / recess class (11 recorded FP pockets on
>    s11/s12/s16/s18 at 1.2–2× the scaled cap, `_is_band_pocket` needs a
>    second discriminator), Gap D of `docs/hatch-cell-chords-handoff.md`, a
>    jamb-scale floor for lining rings (2.5 px slivers pass on s18), the
>    lattice knife-edges — each its own iteration, never bundled.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2 is metrically verified); never `git stash`;
> macOS has no `timeout`; the venv lacks InquirerPy and
> `tests.test_takeoff_fn_equivalence` fails on main — neither is a branch
> signal; s01 and s02 at f=1.0 must not change (entity set AND polygons)
> until `_gate_denominator` deliberately moves s01; if a rule costs a
> confirmed entity or returns an FP, revert it, report why, and STOP; PNG
> crops go under `docs/w-gate-iter3-checkpoints/` and must never show a
> street address or planning-portal id. End every report with the numbers:
> lost, returned FPs, new REVIEW lines with your verdicts, net phantom
> delta, and what is next.

## Outcome — iteration 3, step 3 (2026-09-04, branch `fix/short-piece-material-inherit`, measurement only)

The "short-piece material rule" premise was refuted by measurement, the
third time in this iteration. Tapping `_band_has_wall_material` and the
final pairing on s01 at f=0.542: 43 thick-tier gate calls, 12 pass, 31
fail — 27 with ZERO marks (kitchen units, the bath box, the stair flights),
3 corner end-blocks with 4–5 marks failing the span/min-run floors, and ONE
piece with 3 marks — (160.5–196, 906.8), whose faces are the blue
dimension-pen extension along the wall and whose collinear reference abuts
it at 0.2 px with no opening between (inert). The brief's class — a failing
piece collinear with a same-thickness hatched band with a door/window bbox
in the gap — has 0 instances on s01 at 0.542 and 0 on s01/s02/s03/s05 at
their own factors in the thick tier (s02 has one at 51.5 px with 0 marks;
the weak tier would admit 5/13/8/0 pieces with 0–4 clumped marks). Nothing
was built; no synthetic test; the tree's detection code is unchanged.

What actually loses s01's four confirmed rooms at 0.542 (`leak_finder.py`,
`probe_pairs_box.py`, `force_pair.py`, `plug_diff.py`, scratch): three are
cut at identity by STAIR-FLIGHT phantom bands — the stair ARROW line (an
open-headed 45.8 px stroke, no UP/DN text, so no recognizer names it) is
anchored out of the stair zone by real wall faces 28–35 px away
(`_demote_stair_faces::_paired_with` bounds partners by the scaled cap) and
pairs with them into 28–35 px strong bands (one passes material on the
neighbouring 7.2 px partition's own hatch) that seal the flights; at cap
19.5 the arrow is absorbed as stair ink and the flights open. The truth
notes on two of those rooms already say the cut is wrong ("needs to merge
with the hallway above", "detects stairs as part of the room"). The fourth
(the hall) is the seal: its door's top-edge plug reaches an 8 px = 125 mm
jamb gap that 6.5 px cannot. `ablate.py s01 s01mode` is unchanged (8/12,
18 phantoms); `_gate_denominator` is NOT narrowed; `SCALE_FACTOR_MEASURED_ONLY`
stays. Sweep: the baseline of this tree, 0 LOST, 71 returned FPs, 5 REVIEW.
Report: `docs/w-gate-iter3-checkpoints/step-3.md` (four PNGs beside it).

### Prompt for the next agent (iteration 3, step 5 onward — fresh context)

> Use `/fix-detection` for its discipline (topic branch from the tip that
> carries steps 2 and 3 — `git log --all --oneline | head`; if the user has
> not merged `fix/hingeless-swing-side-veto` / `fix/short-piece-material-inherit`
> into main yet, branch from the later of them; `compare_sweeps --snapshot`
> baselines of that tree for all 20 slugs, re-swept first — never trust
> whatever sits in `outputs/regress/`; four background sweep groups — s18;
> s16 s11 s15; s01–s07; the rest — a full `regress.py` exceeds the
> 10-minute foreground limit; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` on every sheet after EVERY sweep and a
> `tools/room_shape_crop.py` crop of every room whose IoU moved under 0.99
> — verdict-identical is not clean). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-3.md` (what holds s01 at its true
> scale: stair-arrow phantom bands and the seal — the short-piece rule is
> dead, do not resurrect it), `step-2.md` (the seal-15 sites, per
> mechanism), `step-1.md`, `docs/w-gate-iter2-checkpoints/group-2.md`, this
> handoff's iteration-3 outcome sections, the CLAUDE.md paragraphs "Room
> detection" and "Wall/room world-space gates", `detection/rooms.py::
> _door_plugs` (the tail trim and the cross-section fit) with its
> docstring, and `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> Tree state: main `ee0f52f` + `fix/hingeless-swing-side-veto` (d0a4376,
> the corner door lining) + `fix/short-piece-material-inherit` (prose and
> PNGs only). Corpus: 71 returned FPs, 0 LOST, 5 unreviewed; polygons
> differ from `ee0f52f` only on s04 rooms 0002/0004. Constants unchanged
> since step 2 (WALL_MAX_THICKNESS 36, ROOM_OPENING_SEAL 12, …).
>
> Tooling: `tools/census_scratch/` as before (`harness.py`,
> `attrib_rooms.py`, `probe_plugs.py`, `probe_box.py`, `probe_survey.py`,
> `ablate.py s01 s01mode`), `tools/diff_wall_network.py` with `--base-dir`.
> Attribute every change to ONE rule or constant before deciding; the sweep
> stays the arbiter. Reseed rooms' labels on every sheet whose outlines
> changed (`gcloud auth application-default print-access-token` first).
>
> **Step 5 — plug tails end AT the material they shadow.** `_door_plugs`
> trims a qualified plug's `ROOM_OPENING_SEAL_PX` tails back to the farthest
> profile sample still touching wall material within
> `ROOM_PLUG_HALF_WIDTH_PX`; a tail therefore ends up to 5 px PAST the
> material it shadows (s02 door_0050 on the "A" section-marker bar: plugs
> 297.9–372.0 vs bar 302.7–367.2 at seal 15, 4.8 px overshoot each end,
> narrowing the 20.5 px neck under the 16 px pinch — step-2.md). Measure
> first on s02/s01/s15/s04 with `probe_box.py`: every kept plug's tail
> overshoot beyond the material boundary at seal 12 and 15, both classes
> (a tail into a jamb the arc stopped short of — must still bridge the
> clearance gap — vs a tail past an island's end). The rule is inert at
> seal 12 by expectation: the sweep must be verdict- AND polygon-identical.
> Synthetic test first (fails without the trim), then the corpus.
>
> **Step 6 — dash rows** (s15's "steel ridge beam" row of 14.8 px strokes
> in a 2.0 px pen): a collinear row of equal short pieces at equal gaps is a
> DRAWN DASH LINE, never a barrier face and never a collinear-anchor vote.
> Check `tests/ground_truth/s15.json` first — rooms 0023/0024 may be
> confirmed as split by it.
>
> **Step 7 — `ROOM_OPENING_SEAL_PX` 12 → 15 retry**, only after 5 and 6:
> expected s01/s02/s15 unchanged, s03's two recorded FP rooms still out
> (they return at 18), s01 room_0005 at 13–14 is the plug-fit fallback.
> s01's hall door needs 125 mm of reach (8 px at 1:92.2); 15 at 1:50 is
> 127 mm — the value that lets s01 run at its true factor later.
>
> **Then, and only with the user's decision**: s01's three stair-split
> confirmed rooms ((1090,699)–(1142,876), (466,920)–(521,1056),
> (1033,925)–(1142,1134)) are held apart at identity by stair-arrow phantom
> bands under the 36 px cap; at the true factor they merge. Re-reviewing
> them is the user's call (`tools/review.py s01` after a sweep that shows
> the merged rooms — which needs the true factor first, i.e. a temporary
> `_gate_denominator` change on a throwaway branch to produce the REVIEW
> lines). After that decision and step 7, narrow `_gate_denominator`
> (s01 at 0.542 must keep 11 doors, 4 windows and every remaining
> confirmed room), then step 4 (`WALL_MAX_THICKNESS_PX` 36 → 40).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); never `git stash`; macOS has no `timeout`;
> the venv lacks InquirerPy; s01 and s02 at f=1.0 must not change (entity
> set AND polygons) until `_gate_denominator` deliberately moves s01; if a
> rule costs a confirmed entity or returns an FP, revert it, report why,
> and STOP; PNG crops go under `docs/w-gate-iter3-checkpoints/` and must
> never show a street address or planning-portal id. End every report with
> the numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.

## Outcome — iteration 3, step 5 (2026-09-04, branch `fix/plug-tail-ends-at-material`)

The tail overshoot was measured before coding (`tools/census_scratch/
probe_tails.py`, every kept plug's two tails on s02/s01/s15/s04 at seals 12
and 15, classed by what the tail's touch envelope holds): no tail INTO
material that continues past its reach ever overshoots, and every overshoot
is a band-end or nib tail — s02 3 tails at 12 / 47 at 15 (door_0050's four
bar tails 4.8 px), s01 7 / 5, s15 45 / 134, s04 1 / 5, all 0.6–5.0 px. The
brief's "inert at seal 12" expectation was wrong: s02's bar is missed at 12
only by sample phase, and s01/s15/s04 carry the same stubs at 12. Shipped
`_clip_plug_tails` / `_tail_material_end`: after `_door_plugs` trims a tail
to its farthest touching sample, the plug is cut to the slab between its two
material ends along the edge line (material continuing past the reach keeps
the whole tail, material ending inside it ends the tail there). The first
cut, inside `_door_plugs`, was NOT inert in a second way: the fallback
tier's in-wall gate (`ROOM_PLUG_IN_WALL_FRAC`) was calibrated with the tails
in its denominator, and gating on clipped plugs let 57 more fallback plugs
through on s15 (263 → 320), seven cutting 8–38 px² notches (unsimplified
polygons, s15 rooms 0006/0010/0014/0020/0021, s17 0022/0026). The clip now
runs after the plug is classified; with it no room loses any unsimplified
area. Pins: `TestPlugTailTrim.test_tail_ends_at_the_material_it_touches` and
`test_tail_past_a_bar_end_does_not_pinch_the_neck` (both fail without the
rule). Sweep vs the step-3 baseline: verdict lines byte-identical (0 LOST,
71 returned FPs, 5 REVIEW); 22 room polygons on s01/s02/s03/s11/s15/s17
gain 6–742 px² each (+3,377 px²; s17 room_0027's 467 px corridor edge no
longer leans on a 3.8 px stub; s01 +70 px² over three rooms and s02 +12 over
one, at f = 1.0 — the user's call), nothing added, removed or lost; labels
reseeded on the seven sheets whose outlines moved (s03's had been missing at
baseline and are back). Harness at seals 13/14/15 with the rule: s02
identical to its baseline at all three (the seal-15 notch is gone); s15
rooms 0019/0020/0023/0024 still move at ≥ 14 (dash rows), s01 room_0005 at
13–14 (fit flip), and two pre-existing unmeasured moves — s01 room_0003 at
14–15 (0.985), s04 room_0001 at 14–15 (0.987). Report:
`docs/w-gate-iter3-checkpoints/step-5.md` (six PNGs beside it). Next: step 6
(dash rows), then step 7 (the seal retry).

### Prompt for the next agent (iteration 3, step 6 onward — fresh context)

> Use `/fix-detection` for its discipline (topic branch from the tip that
> carries steps 2, 3 and 5 — `git log --all --oneline | head`; if the user
> has not merged `fix/plug-tail-ends-at-material` into main yet, branch from
> it; `compare_sweeps --snapshot` baselines of that tree for all 20 slugs,
> re-swept first — never trust whatever sits in `outputs/regress/`; four
> background sweep groups — s18; s16 s11 s15; s01–s07; the rest — a full
> `regress.py` exceeds the 10-minute foreground limit; verdict reports diffed
> section-wise; `tools/diff_room_polygons.py` on every sheet after EVERY
> sweep and a `tools/room_shape_crop.py` crop of every room whose IoU moved
> under 0.99 — verdict-identical is not clean; and a scratch UNSIMPLIFIED
> polygon diff (`ROOM_SIMPLIFY_TOL_PX` = 0, the rule toggled by monkeypatch)
> whenever any room LOSES area, because a barrier rule that only removes
> barrier cannot lose free space — step 5 found the fallback in-wall gate
> moving that way). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-5.md` (the tail clip, the in-wall-gate
> lesson, the residual seal-13/14/15 sites), `step-3.md`, `step-2.md`,
> `step-1.md`, `docs/w-gate-iter2-checkpoints/group-2.md`, this handoff's
> iteration-3 outcome sections, the CLAUDE.md paragraphs "Room detection"
> (the `_door_plugs` / `_clip_plug_tails` sentences, the lattice and
> dash-row context) and "Wall/room world-space gates",
> `detection/walls.py::_collect_wall_faces`, `_merge_collinear_segs` and
> `_support_anchor` with their docstrings, `detection/rooms.py::_door_plugs`
> and `_clip_plug_tails`, and `docs/regression-testing-guide.md` §9 §10 §12
> §13.
>
> Tree state: main `ee0f52f` + `fix/hingeless-swing-side-veto` (d0a4376)
> + `fix/short-piece-material-inherit` (be5509e) + `fix/plug-tail-ends-at-
> material` (the clip). Corpus: 71 returned FPs, 0 LOST, 5 unreviewed;
> polygons differ from `ee0f52f` on s04 rooms 0002/0004 (step 2) and on 22
> rooms of s01/s02/s03/s11/s15/s17 (step 5, all gains). Constants unchanged
> since step 2 (WALL_MAX_THICKNESS 36, ROOM_OPENING_SEAL 12, …).
>
> Tooling: `tools/census_scratch/` as before (`harness.py`,
> `attrib_rooms.py`, `probe_plugs.py`, `probe_box.py` — now applies the
> clip, `probe_survey.py`, `probe_tails.py [--no-clip]`, `ablate.py s01
> s01mode`), `tools/diff_wall_network.py` with `--base-dir`. Attribute every
> change to ONE rule or constant before deciding; the sweep stays the
> arbiter. Reseed rooms' labels on every sheet whose outlines changed
> (`gcloud auth application-default print-access-token` first; `python
> app.py extract fixtures/sheets/<pdf> --out <scratch> --ceiling-height 2.4
> < /dev/null` writes a timestamped run under `--out`; the cache is keyed on
> room geometry, so reseed AFTER the final geometry and re-sweep to check the
> warning count returns to the baseline's).
>
> **Step 6 — dash rows.** s15's "steel ridge beam" line is a row of 14.8 px
> strokes in a 2.0 px pen, each a strong barrier face: it splits the corridor
> from the lounge and crosses door_0013's doorway plane at x≈938, flipping
> the mid-window in-plane count 2/10 → 3/11 at seal 14 (step-2.md,
> `step2_s15_door_0013_dash_row_mid_cover_12_vs_14.png`); it is also the
> collinear-anchor vote that sealed s15 room_0016 in the anchor-line
> iteration. Convention to test: a collinear row of equal short pieces at
> equal gaps is a DRAWN DASH LINE — never a barrier face and never a
> collinear-anchor vote — whereas a wall drawn in touching pieces (s06's
> dashed walls, `_chains_across` in layout) chains with no gaps. Measure
> first, with the harness, on s15 AND on s01/s02: every collinear row of ≥ N
> same-pen pieces of equal length at equal gaps (pitch, length CV, gap/length
> ratio, pen), both classes — annotation dash rows (section lines, beam
> lines, boundary lines, "line of wall over") and real wall faces broken by
> text masks or by dimension ticks (which are gaps of UNEQUAL length). Check
> `tests/ground_truth/s15.json` BEFORE touching it — rooms 0023/0024 may be
> confirmed as split by that row, in which case the split is a LOST line and
> the user decides. Synthetic test first, harness pre-check on s15/s01/s02
> at seals 12 and 14, full sweep, polygon diff (simplified AND unsimplified
> when anything loses area), crops, verdicts, reseed, prose (the constant
> comment, CLAUDE.md room paragraph, findings §4, this handoff), checkpoint
> `docs/w-gate-iter3-checkpoints/step-6.md` with before|after pictures, and
> STOP.
>
> **Step 7 — `ROOM_OPENING_SEAL_PX` 12 → 15 retry**, only after 6: with
> step 5 in, s02 is already identical at 13/14/15; expected blockers left are
> s01 room_0005 at 13–14 (the plug-fit fallback "anchors disagree → full
> envelope", its own knife-edge) and two unmeasured pre-existing moves at
> 14–15 — s01 room_0003 (IoU 0.985) and s04 room_0001 (0.987) — measure
> both with `probe_box.py` before deciding; s03's two recorded FP rooms must
> stay out (they return at 18). s01's hall door needs 125 mm of reach (8 px
> at 1:92.2); 15 at 1:50 is 127 mm.
>
> **Then, and only with the user's decision**: s01's three stair-split
> confirmed rooms ((1090,699)–(1142,876), (466,920)–(521,1056),
> (1033,925)–(1142,1134)) are held apart at identity by stair-arrow phantom
> bands under the 36 px cap; at the true factor they merge (step-3.md).
> Re-reviewing them is the user's call (`tools/review.py s01` after a
> true-factor sweep on a throwaway branch). After that decision and step 7,
> narrow `_gate_denominator` (s01 at 0.542 must keep 11 doors, 4 windows and
> every remaining confirmed room), then step 4 (`WALL_MAX_THICKNESS_PX`
> 36 → 40: the s11 recess box, s15 annotation pocket and s18 tree strip must
> stay out; expected −5 recorded phantoms on s16/s17).
>
> Also queued, each its own iteration: re-calibrating the fallback in-wall
> gate on tail-less plugs (step 5 kept it on the sample-trimmed plug so its
> 0.77/0.84 margin holds); deeper band pockets / the recess class; Gap D of
> `docs/hatch-cell-chords-handoff.md`; a jamb-scale floor for lining rings;
> the lattice knife-edges; an open-arrowhead stair recognizer.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); never `git stash`; macOS has no `timeout`;
> the venv lacks InquirerPy; s01 and s02 at f=1.0 must not change (entity
> set AND polygons) until `_gate_denominator` deliberately moves s01 — step
> 5 moved them by +70 / +12 px² and reported it as a decision, do the same
> if a rule touches them; if a rule costs a confirmed entity or returns an
> FP, revert it, report why, and STOP; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id. End every report with the numbers: lost, returned FPs,
> new REVIEW lines with your verdicts, net phantom delta, and what is next.

## Outcome — iteration 3, step 6 (2026-09-05, branch `fix/dash-rows-not-faces`, built and measured, NOT shipped)

Measured first (`tools/census_scratch/dash_rows.py`: every collinear
same-pen row at gaps on all 20 sheets, both classes): a drawn dash line is a
periodic row — s15's "steel ridge beam 1" is a 3.0px CHAIN-dash (74/14.8px
pieces alternating at 14.8px gaps, CV 0.00), its 2.0px beam, boundary and
drain rows 14.8/7.5, its beam-symbol flanges and unit boxes 1.0px 14.7/7.5
and 7.5/3.7; s05/s12 draw 6/6 dotted lines, s07 7.5/3.8, s17 orange 14.8/7.5
demolition lines, s18 chain 47/9.5, s20 chain 38/7.7 — gaps 3.7–15.0px at
1:50 and 1:100 alike (paper-space). The true class, a wall face broken by
openings, has THREE pieces at world opening widths on every sheet (s05 [165,
27, 165] at 49px, s07 [106, 99, 106] at 21.3, s11 [35, 71, 34] at 35, s15
[212, 198, 212] at 42.5, s03 [157, 201, 157] at 5.7); a dash row's end pieces
are clipped to any length, so the pattern is read on the interior pieces.
Built `_dash_row_indices` (pre-pairing exclusion beside the dimension chains
and glyph strokes, so members neither fence nor vote in the collinear anchor;
`WALL_DASH_*`, all P-class: ≥ 4 pieces, gaps equal within 1.5px/12% and
≤ 18px, one interior length or two strictly alternating, end pieces ≤ one
period). The first corpus sweep forced two discriminators: nearest-piece
linking with a touching piece blocking the link plus a longest-dash ≤ 8 gaps
cap (s17's face [92, 3.75, 348.5, 3.75, 5.5] at 2px tick gaps read as a chain
and opened a confirmed corridor into the wall band), and a hatch-end
exemption (s05's 475mm wall has its inner face drawn as a 6/6 dotted row on
which its 104 through-hatch strokes end from one side at 23/100px; flagged, Bed
1 and Bed 2 merged through the band). Final sweep vs the step-5 baseline: 16
sheets polygon-identical (s01/s02 untouched at seals 12 and 14 beyond the
pre-existing s01 moves), returned FPs 71 → 67 (s15 −4), the s15 room_0016
dash-fenced pocket gone, s17/s18 +2.9k px² regained, no free space lost
outside s15's recorded-FP hall (−321 px² unsimplified, a 35px pair the
removed 9px flange pair had held out), s15 at seal 14 now equal to seal 12
(the step-2 door_0013 mechanism was the beam) — **and 10 confirmed rooms
LOST**: nine s15 cells fenced by the ridge beam (lounge 88|500, vestibule
88|77), the "existing steel beam" symbol and "steel beam 2" row (the kitchen
zone in five) and the page-long drain run at x=263 (the garage in three),
plus s07's closet behind a dashed double line 8px apart. Per the run's rule
the tree is reverted; the rule lives in
`docs/w-gate-iter3-checkpoints/step-6-dash-rows.patch` (applies clean; 8 of
its 11 tests fail on the baseline code). New REVIEW rooms: s15's garage
(real) and a 160×77px hall slice held by a 3-piece chain fragment (phantom,
n < 4 — a text-mask join rule is the next discriminator). Net phantoms −4.
Report: `docs/w-gate-iter3-checkpoints/step-6.md` (12 PNGs beside it).

### Prompt for the next agent (after the user's step-6 decision — fresh context)

> Use `/fix-detection` for its discipline (topic branch from the tip that
> carries steps 2, 3 and 5 — `git log --all --oneline | head`; if the user
> has applied and committed `docs/w-gate-iter3-checkpoints/step-6-dash-
> rows.patch`, branch from that; `compare_sweeps --snapshot` baselines of
> that tree for all 20 slugs, re-swept first in four background groups —
> s18; s16 s11 s15; s01–s07; the rest; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep, `tools/room_shape_crop.py`
> crops of every room whose IoU moved under 0.99, and a scratch UNSIMPLIFIED
> polygon diff whenever any room loses area). Read first:
> `docs/w-gate-iter3-checkpoints/step-6.md` (the dash-row rule, its two
> discriminators, the ten lost rooms and the decision), `step-5.md`,
> `step-3.md`, `step-2.md`, this handoff's iteration-3 outcome sections, the
> CLAUDE.md paragraphs "Room detection" and "Wall/room world-space gates",
> `detection/rooms.py::_door_plugs` / `_clip_plug_tails`, and
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> **The step-6 decision comes first.** (a) If the user applied the patch:
> the sweep has ten LOST lines until they re-review s15 and s07
> (`tools/review.py s15` / `s07` records verdicts on the new REVIEW rooms —
> the garage and the hall slice — and the stale confirmed cells must be
> retired by the user's own hand edit of `tests/ground_truth/s15.json` /
> `s07.json`; you never edit those); reseed labels on s07/s15/s17/s18; the
> remaining residue is the 3-piece chain fragment fencing the hall slice —
> a text-mask join (rows on one line either side of a text span are one row)
> is its own iteration. (b) If they rejected it, dash rows stay walls and
> s15's seal-14 blocker (the ridge beam across door_0013's doorway plane)
> stays.
>
> **Step 7 — `ROOM_OPENING_SEAL_PX` 12 → 15 retry**: with step 5 in, s02 is
> identical at 13/14/15; with the dash rule in, s15 is identical at 14.
> Blockers left: s01 room_0005 at 13–14 (the plug-fit fallback "anchors
> disagree → full envelope", its own knife-edge) and two unmeasured
> pre-existing moves at 14–15 — s01 room_0003 (IoU 0.985) and s04 room_0001
> (0.987) — measure both with `tools/census_scratch/probe_box.py` before
> deciding; s03's two recorded FP rooms must stay out (they return at 18).
> s01's hall door needs 125 mm of reach (8 px at 1:92.2); 15 at 1:50 is 127
> mm. Synthetic test first, harness pre-check on s01/s02/s03/s04/s15 at the
> candidate seal, full sweep, polygon diffs, crops, verdicts, reseed, prose,
> checkpoint `step-7.md`, and STOP.
>
> Then, only with the user's decision on s01's three stair-split confirmed
> rooms ((1090,699)–(1142,876), (466,920)–(521,1056), (1033,925)–(1142,1134),
> step-3.md): narrow `_gate_denominator` (s01 at 0.542 must keep 11 doors, 4
> windows and every remaining confirmed room), then step 4
> (`WALL_MAX_THICKNESS_PX` 36 → 40: the s11 recess box, s15 annotation pocket
> and s18 tree strip must stay out; expected −5 recorded phantoms on
> s16/s17). Also queued, each its own iteration: the dash-row text-mask join;
> re-calibrating the fallback in-wall gate on tail-less plugs; deeper band
> pockets / the recess class; Gap D of `docs/hatch-cell-chords-handoff.md`; a
> jamb-scale floor for lining rings; the lattice knife-edges; an
> open-arrowhead stair recognizer.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); never `git stash`; macOS has no `timeout`; the
> venv lacks InquirerPy; s01 and s02 at f=1.0 must not change (entity set
> AND polygons) until `_gate_denominator` deliberately moves s01 — report
> any move as a decision; if a rule costs a confirmed entity or returns an
> FP, revert it, report why, and STOP; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id. End every report with the numbers: lost, returned
> FPs, new REVIEW lines with your verdicts, net phantom delta, and what is
> next.

### Step-6 decision (2026-09-05, same day)

The user looked at the before|after ("s15 looks good"; the split cells had
been confirmed as CHUNKS of one room) and asked for the ten verdicts to be
retired. Done: `step-6-dash-rows.patch` applied to the tree (11 tests
green), the ten `confirmed` entries removed by hand from
`tests/ground_truth/s15.json` (nine `partial` chunks) and `s07.json` (the
closet) via `regression.ground_truth.dump_truth` (61-line deletion, hygiene
test green), labels reseeded on s07/s15/s17/s18 (warning counts back to
baseline, no `ROOM_LABEL_*`), re-sweep of those four sheets: s07 6/6, s15
11/11, s17 24/24, s18 14/14 — **0 LOST, 67 returned FPs, 6 REVIEW** corpus-
wide (s15's garage and hall slice still await `tools/review.py s15`). The
next-agent prompt above applies with branch (a): step 7 next, s15 no longer
blocks seal 14. Caution for step 7: the confirmed vestibule
[848.7,1549.4,936.7,1630.8] matches the merged 169px vestibule at IoU 0.52.

## Outcome — iteration 3, step 7 (2026-09-05, branch `fix/seal-15-retry`, shipped pending the user's decision)

`ROOM_OPENING_SEAL_PX` 12 → 15 (127 mm at 1:50, 7.5 px = 150 mm at 1:100),
branched from `fix/dash-rows-not-faces` (16a4835) with the user's uncommitted
s10/s17/s18 verdicts in the tree (baseline 0 LOST, 68 returned FPs, 0
REVIEW). Measured first with the harness at 13/14/15 (as multipliers, so the
f = 0.5 sheets scale) on s01–s05/s07/s11/s15–s17, then the full sweep: the
corpus is **verdict-identical** on all 20 sheets (0 lost, 68 returned FPs, 0
REVIEW, no door/window change) and **48 room polygons on 13 sheets move**
by sub-1% strips in three measured classes (`tools/diff_room_polygons.py`
after every sweep, scratch unsimplified diffs on every labelled sheet,
`probe_box` on every site): (a) the plug-less dilated-bbox FALLBACK stamps
`bbox ⊕ SEAL` in every direction, so at 10 plug-less doors the room on the
plane side loses 3 px more — s01 door_0015's double swing −447 px² on the
living room, s04 door_0003's slider −539 on each flanking room, s17
door_0001 −547 on the confirmed SH/WC whose recorded outline IS that stamp's
edge, s16/s18 by 1.5 px at f = 0.5 — ≈ −2.9k px²; (b) tails on continuing
material, or on a parallel band inside the 5 px touch half-width (s17
door_0016's doorway plug into rooms 0001/0002), are 3 px longer at room
corners — ≈ −1.0k; (c) sampling-phase knife-edges both ways — s03
door_0008's leaf-side phantom plug drops and room_0009 swallows a wall stub
as an island (+715), s02 door_0005's cross-section fit falls to the full
envelope (−276), s17 door_0001's bottom plug qualifies at 14 only (the SH/WC
regains its swing square there, +9.0k, not at 15) — ≈ +0.8k. Net ≈ −3.0k px²;
**s01 −304 / s02 −53 at f = 1.0** (a decision, as step 5's move was). The
brief's expected blockers: s01 room_0005's fit flip is inert at 15 (13–14
only), s01 room_0003 is +143 (two phantom plugs fit 1 px narrower), s04
room_0001 is −539 (class a), s15 is identical at 14 and −85 at 15 (class b),
s03's two recorded FPs stay out. `TestPlugSealReach` pins 14 sealed / 16 not;
`OPENING_ASSIGN_BUFFER_PX` follows the constant (17 px reach). Labels
reseeded on the 13 sheets and re-swept: identical verdicts and warning codes
(s16's stale `ROOM_LABEL_NO_GEMINI` gone). Report:
`docs/w-gate-iter3-checkpoints/step-7.md` (8 PNGs beside it). Constant
comment, CLAUDE.md gates paragraph, findings §4 row 355 and census row 17
updated.

### Prompt for the next agent (after the user's step-7 decision — fresh context)

> Use `/fix-detection` for its discipline (topic branch from the tip that
> carries steps 2, 3, 5, 6 and — if the user accepted it — 7:
> `git log --all --oneline | head`; `compare_sweeps --snapshot` baselines of
> that tree for all 20 slugs, re-swept first in four background groups — s18;
> s16 s11 s15; s01–s07; the rest; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep, `tools/room_shape_crop.py`
> crops of every room whose IoU moved under 0.99, and a scratch UNSIMPLIFIED
> polygon diff whenever any room loses area — set harness seal overrides as
> MULTIPLIERS of the tree's constant, never absolute px, or the f = 0.5 sheets
> run at double reach). Read first: `docs/w-gate-iter3-checkpoints/step-7.md`
> (the three move classes and their sites), `step-6.md`, `step-5.md`,
> `step-3.md`, this handoff's iteration-3 outcome sections, the CLAUDE.md
> paragraphs "Room detection" and "Wall/room world-space gates",
> `detection/rooms.py::_door_plugs` / `_clip_plug_tails` / the
> dilated-bbox fallback in `detect_rooms`, and
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> **Step 7 was accepted as-is and committed (2026-09-05): `ROOM_OPENING_SEAL_PX`
> is 15.** Next is **step 8 — the plane-restricted fallback stamp**, the
> iteration that pays for step 7. A door with no qualifying plug seals by
> `box(*c.bbox).buffer(SEAL, join_style=2)` (`detect_rooms`, the `elif
> c.confidence >= ROOM_BBOX_SEAL_MIN_CONFIDENCE` branch), which grows SEAL
> ACROSS the door's plane as well as along it, so the room on the plane side
> loses a SEAL-deep strip at every such door — 15 px now, 12 before. A swing
> bbox's hinge edge lies on its wall face within `ROOM_PLUG_NEAR_PX` (8 px),
> never SEAL off it, so the across-plane growth serves nothing. Measure
> first: per plug-less door on the corpus at 15, how far the bbox's
> wall-side edge sits off drawn wall material (the clearance the stamp must
> bridge across) and how far its ends sit from the jambs (along) — the class
> (a) sites in step-7.md are the test set (s01 door_0015 double swing, s04
> door_0003 slider, s17 door_0001 on the confirmed SH/WC, s16 rooms
> 0002/0006, s18 rooms 0002/0003/0005/0007) and `probe_box.py` dumps the
> per-edge profiles. Which edge is the wall side is the whole question: a
> swing door has `_swing_hinge_edges`, a slider's long axis IS the wall
> (s04 door_0003, 7 × 141 px between two rooms), a fallback-tier box has
> neither — state the orientation rule as a drawing convention and measure
> it on the true class (s01/s02's plug-less doors) before choosing SEAL
> along / NEAR across. Synthetic test first (a plug-less door whose bbox
> stops N px short of both jambs and M px off its wall face: the doorway
> must still seal, and the room on the far side of the wall must keep its
> floor), harness pre-check, full sweep, polygon diffs — s17's confirmed
> SH/WC outline IS the seal-12 stamp edge, so a shrunken stamp GROWS that
> room toward its swing square: IoU against the recorded polygon must stay
> ≥ 0.5 and the growth is a win to report, not a regression — crops,
> reseed, prose, `step-8.md`, STOP.
>
> In parallel the user's decision on s01's three stair-split confirmed
> rooms ((1090,699)–(1142,876), (466,920)–(521,1056), (1033,925)–(1142,1134),
> step-3.md; show the before|after from a true-factor sweep on a throwaway
> branch and ask — confirmed rooms are sometimes CHUNKS of one room). Only
> with it: narrow `_gate_denominator` (s01 at 0.542 must keep 11 doors, 4
> windows and every remaining confirmed room; step 3 measured the seal as
> the hall's sole blocker and 15 × 0.542 = 8.1 px ≥ its 8 px jamb gap, so
> re-measure the hall at 0.542 first with `ablate.py s01 s01mode`), then
> step 4 (`WALL_MAX_THICKNESS_PX` 36 → 40: the s11 recess box, s15 annotation
> pocket and s18 tree strip must stay out; expected −5 recorded phantoms on
> s16/s17). Also queued, each its own iteration: a same-line requirement for
> a tail's supporting material (class b — s17 door_0016's doorway plug hugs a
> parallel band 4 px off its spine and runs 15 px into both flanking rooms);
> phase-invariant plug profiles anchored at the bbox corners (class c — s17
> door_0001's bottom plug qualifies at 14 only, s02 door_0005's fit falls to
> the full envelope at 15); the dash-row text-mask join;
> re-calibrating the fallback in-wall gate on tail-less plugs; deeper band
> pockets / the recess class; Gap D of `docs/hatch-cell-chords-handoff.md`; a
> jamb-scale floor for lining rings; the lattice knife-edges; an
> open-arrowhead stair recognizer; interior rings in the exported room
> polygon (s03's islanded stub).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); never `git stash`; macOS has no `timeout`; the
> venv lacks InquirerPy; s01 and s02 at f=1.0 must not change (entity set
> AND polygons) until `_gate_denominator` deliberately moves s01 — report
> any move as a decision; if a rule costs a confirmed entity or returns an
> FP, revert it, report why, and STOP; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id. End every report with the numbers: lost, returned
> FPs, new REVIEW lines with your verdicts, net phantom delta, and what is
> next.

## Outcome — iteration 3, step 8 (2026-09-05, branch `fix/plane-restricted-fallback-stamp`, built and measured, HELD as a patch)

The plane-restricted fallback stamp (`detection/rooms.py::_plane_stamp`):
a plug-less door seals along its wall-plane edges only — a single's two
hinge edges (`_swing_hinge_edges`; measured on the corpus's 181
hinge-derivable plugged singles the plug lies on a hinge edge 177 times,
that edge sits on its face at median 0.0 / max 4.2 px, and the leaf-axis
"open leaf" convention names it only 159 : 5 against the closed-leaf one,
so the stamp never picks ONE), a slider's long edges, a garden pair's
un-vetoed edge, all four for a door pinning nothing — each as the plug it
would have carried: ±`ROOM_PLUG_HALF_WIDTH_PX`, SEAL tails kept as far as
material hugs them within `ROOM_PLUG_NEAR_PX` and ending where it ends. No
new constant; 7 tests (three through `detect_rooms`, failing on the old
code for the stated reasons). Census first (`plugless_census.py`, scratch):
565 doors reach the room stage on 18 sheets, 18 are plug-less, 7 touch a
room (s01 door_0015, s04 door_0003, s16 doors 0003/0004, s17 door_0001, s18
doors 0018/0271). Corpus sweep vs the baseline (0 LOST / 68 FPs / 0
REVIEW): **verdict-identical on 19 sheets, 10 room polygons gain +21.8k px²
(s17's confirmed SH/WC +8,478 at IoU 0.752 — its swing square; s04 ±1.5k
per flanking room; s01 room_0001 +1,431 at f=1.0; s02 untouched), nothing
loses a pixel unsimplified, `door_openings` unchanged — and ONE confirmed
s18 room is LOST**: (2267,758)–(2511,802), a `"shape": "partial"` 0.75 m
strip on the patio side of the extension's cavity wall, fenced on top by
the "4200 Overall Extension projection" glyph-outline rings (gap b) and,
for its first 50 px, by door_0271's old stamp along its PARKED bottom
leaf — nothing drawn bounds it there. Per the run's rule the tree is
reverted to 71ba420's code; the complete change (code, tests, CLAUDE.md
sentence, findings row) is `docs/w-gate-iter3-checkpoints/step-8-plane-stamp.patch`
(applies cleanly). Report: `docs/w-gate-iter3-checkpoints/step-8.md`
(7 PNGs beside it). Labels not reseeded (nothing in the tree moved).

In parallel, s01 at its true factor on this tree (harness, f = 50/92.2):
11/11 doors, 4/4 windows, 8/12 rooms, 18 unreviewed — the same four lost
as step 3 (three stair-split rooms + the hall); picture
`step8_s01_stair_rooms_identity_vs_true_factor.png`. New finding: the hall
door's right-edge plug NOW qualifies at 0.542 (`interrupted`, seal 8.13 px
≥ its 8 px gap) yet the hall still merges with the living room into
(209,412)–(521,1389) — step 3's "the seal is the hall's sole blocker" is
stale; the leak is elsewhere.

### Prompt for the next agent (after the user's step-8 decision — fresh context)

> Use `/fix-detection` for its discipline (topic branch from
> `fix/seal-15-retry` 71ba420 or its successor; `git log --all --oneline |
> head`; `compare_sweeps --snapshot` baselines of that tree for all 20
> slugs, re-swept first in four background groups — s18; s16 s11 s15;
> s01–s07; the rest; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep, `tools/room_shape_crop.py`
> for every room whose IoU moved under 0.99, a scratch UNSIMPLIFIED diff
> whenever any room loses area; harness overrides as MULTIPLIERS). Read
> first: `docs/w-gate-iter3-checkpoints/step-8.md`, `step-7.md`,
> `step-3.md`, this handoff's iteration-3 outcome sections, the CLAUDE.md
> paragraphs "Room detection" and "Wall/room world-space gates",
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> **Step 8 is held as `step-8-plane-stamp.patch`** pending the user's
> verdict on s18 room (2267,758)–(2511,802). If they retire it: `git apply`
> the patch, run the 7 tests, re-sweep the corpus (expect 0 LOST / 68 FPs /
> 0 REVIEW / 10 polygons +21.8k px², s18 room 13/13 after the retirement),
> reseed labels on s01/s04/s16/s17/s18, re-sweep those, and that is the
> step-8 commit (code + tests + prose in one, the truth edit as its own
> data commit by the user). If they keep it, the stamp stays as it is and
> class (a) of step 7 stays paid.
>
> Then, only with the user's decision on s01's three stair-split rooms
> (`step8_s01_stair_rooms_identity_vs_true_factor.png`: at 0.542 the
> landing + flights are one room and the CPD cupboard opens into the
> hall): narrow `_gate_denominator` — s01 at 0.542 must keep 11 doors, 4
> windows and every remaining confirmed room. **Re-measure the hall's
> leak first** (`ablate.py s01 s01mode`, then a probe of every opening on
> the hall/living boundary at 0.542): the hall door's plug qualifies now,
> and the hall still merges into (209,412)–(521,1389). Then step 4
> (`WALL_MAX_THICKNESS_PX` 36 → 40: the s11 recess box
> (1030,1330)–(1123,1360), s15 annotation pocket (1480,698)–(1595,792) and
> s18 tree strip (156,724)–(197,863) must stay out; expected −5 recorded
> phantoms on s16/s17).
>
> Also queued, each its own iteration: a same-line requirement for a plug
> tail's supporting material (s17 door_0016); phase-invariant plug
> profiles anchored at the bbox corners (s17 door_0001's bottom plug, s02
> door_0005); the dash-row text-mask join for 3-piece chain fragments;
> re-calibrating the fallback in-wall gate on tail-less plugs; deeper band
> pockets / the recess class; Gap D of `docs/hatch-cell-chords-handoff.md`;
> a jamb-scale floor for lining rings; the lattice knife-edges; an
> open-arrowhead stair recognizer; interior rings in the exported room
> polygon; and, from step 8, the glyph-outline fill rings that fence
> s18's patio strip (gap b — the same rings fenced it whichever way the
> stamp goes).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json`; never revert
> s01's truth scale (1:92.2); never `git stash`; macOS has no `timeout`;
> python is not on the shell path, use `.venv/bin/python` with an absolute
> path in background commands (the cwd resets); the venv lacks InquirerPy;
> `test_takeoff_fn_equivalence`'s `warnings` field fails on the untouched
> tree (a region-cache mismatch, pre-existing); s01 and s02 at f=1.0 must
> not change (entity set AND polygons) until `_gate_denominator`
> deliberately moves s01 — report any move as a decision; if a rule costs
> a confirmed entity or returns an FP, revert it, report why with a
> before|after of what the lost entity is a chunk of, and STOP; PNG crops
> go under `docs/w-gate-iter3-checkpoints/` and must never show a street
> address or planning-portal id. End every report with the numbers: lost,
> returned FPs, new REVIEW lines with your verdicts, net phantom delta, and
> what is next.

### Step-8 decision (2026-09-05, same day)

The user looked at the before|after and asked for the change back
("s18 still needs a lot of work, we can ignore patio for now — it's
outside the house"): the patch is applied to the tree again (its 7 tests
pass), labels reseeded on s01/s04/s16/s17/s18. The user then asked for the
s18 `confirmed` patio strip (2267,758)–(2511,802) to be retired: removed
through `regression.ground_truth.dump_truth` (a 6-line deletion), its own
data commit; the re-sweep reads s18 13/13 — **0 LOST, 68 returned FPs, 0
REVIEW** corpus-wide. Step 8 is committed on
`fix/plane-restricted-fallback-stamp`. The next agent's prompt above
applies as written from "Then, only with the user's decision on s01's
three stair-split rooms".

## Outcome — iteration 3, step 9 (2026-09-05, branch `recal/s01-true-factor`, measurement only — `_gate_denominator` NOT moved)

Baseline re-swept in four background groups and snapshotted for all 20
slugs: 0 LOST, 68 returned FPs, 0 REVIEW. s01 at f = 50/92.2 on this tree
(harness): 11/11 doors, 4/4 windows, 8/12 rooms, 18 unreviewed — and the
re-measurement the brief ordered shows THREE blockers, not one:

1. **The hall IS the seal** — step 8 misread door_0002's RIGHT edge (the
   open leaf's hinge edge on the CPD wall, interrupted at identity too) as
   the doorway; the doorway is the TOP edge, whose latch jamb face sits
   14.25 px = 222 mm (1:92.2) past the bbox corner. At 0.542 the 8.13 px
   tail's first sample stops 4.1 px short of the material (touch 2.71) and
   the start window covers 1/3; passing needs S ≥ 9.52 px = 17.6 at 1:50
   (s03's FPs return at 18). Corpus census of 378 kept doorway ends in mm at
   true scale: median 0, p90 34, the four largest are s01's swing doors
   (187–219 mm), next s05 135 mm. Fix = a jamb-seeking tail (extend to the
   nearest collinear wall face up to a world cap), its own iteration.
2. **17 phantoms = the furniture pen crossing `ROOM_WALL_PEN_MIN_FRAC`**:
   red carries 13.7 % of the paired stroked length at identity, 15.2 % at
   0.542 (33 thin sofa/bed pairs th 2.5–4.8 appear) — all 17 (12 unit /
   cushion cells, 2 slivers, 1 strip, 2 room splits) are fenced by red ink.
   Every other multi-pen sheet sits at ≥ 34 % or ≤ 10.4 %. Discriminator
   candidates: a wall pen's pairs carry hatch (red: 0 marks), or its longest
   paired run is room-long (red 109 px vs black 497 / magenta 567). Its own
   iteration.
3. The three stair-split rooms — step 3/8's finding, the user's verdict.

`ablate.py s01 s01mode` re-run on this tree confirms: the cap alone loses the
three stair rooms (+ the living room by bbox), the seal alone the hall, and
any one of four wall gates held at identity removes all 17 phantoms (an
interaction, no discriminator). Report:
`docs/w-gate-iter3-checkpoints/step-9.md` (2 PNGs beside it). No code, truth
or manifest changed; labels not reseeded.

### Prompt for the next agent (after the user's step-9 decisions — fresh context)

> Use `/fix-detection` for its discipline (topic branch from
> `recal/s01-true-factor` or its successor; `git log --all --oneline |
> head`; re-sweep in four background groups and `compare_sweeps --snapshot`
> all 20 slugs first; verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep, `tools/room_shape_crop.py`
> for every room whose IoU moved under 0.99, a scratch UNSIMPLIFIED diff
> whenever any room loses area; harness overrides as MULTIPLIERS). Read
> first: `docs/w-gate-iter3-checkpoints/step-9.md`, `step-8.md`,
> `step-3.md`, this handoff's iteration-3 outcome sections, the CLAUDE.md
> paragraphs "Room detection" and "Wall/room world-space gates",
> `docs/regression-testing-guide.md` §9 §10 §12 §13.
>
> With the user's decisions from step 9: (a) the JAMB-SEEKING TAIL — a
> doorway plug's tail extends along the edge line to the nearest collinear
> wall face (`network.faces` within `ROOM_PLUG_NEAR_PX` of the line, same
> direction) up to a world cap; census first (`jamb_census.py`'s pattern:
> every kept doorway end in mm at true scale, max 219 mm on s01, next
> 135 mm; the non-qualifying ends with material further out — s01
> door_0015 281 mm, door_0012 203, s10 door_0011 169, s14 door_0008 119, s02
> door_0016 110, s03 door_0008 85 — are the cases to picture before and
> after); proof = s01's hall sealed at 0.542 in the harness AND a corpus
> sweep byte-identical at the current factors. (b) The WALL-PEN
> DISCRIMINATOR — measure on every multi-pen sheet (s01/s02/s03/s04/s08/s17)
> per pen: paired length share, hatched-band share, longest paired run;
> state the convention, then build; proof = s01 at 0.542 in the harness
> shows 0 red-fenced rooms AND the corpus is byte-identical. (c) Only then
> narrow `_gate_denominator` (s01 keeps 11 doors, 4 windows, every remaining
> confirmed room, no new phantom beyond the landing), then step 4
> (`WALL_MAX_THICKNESS_PX` 36 → 40: the s11 recess box
> (1030,1330)–(1123,1360), s15 annotation pocket (1480,698)–(1595,792) and
> s18 tree strip (156,724)–(197,863) must stay out; expected −5 recorded
> phantoms on s16/s17).
>
> Rules for the whole run are those of the step-8 prompt above (no commits,
> no truth/manifest edits without a go for that entry, never revert s01's
> truth scale, never `git stash`, no `timeout` on macOS, `.venv/bin/python`
> by absolute path in background commands, s01/s02 at f = 1.0 unchanged until
> the denominator deliberately moves s01, a lost confirmed entity or a
> returned FP means revert + before|after + STOP, PNGs under
> `docs/w-gate-iter3-checkpoints/` with no address, and every report ends
> with lost / returned FPs / REVIEW lines with verdicts / net phantom delta /
> next).

### Step-9 decisions and the jamb-seek census (2026-09-05, same day)

The user retired the three stair verdicts in principle (to be removed by
hand once s01 runs at 0.542, the merged rooms re-reviewed then) and chose
the jamb-seeking tail as the next iteration. Its census
(`collinear_census.py`, every door edge end at the sheets' factors + s01 at
0.542, the nearest collinear BARRIER face beyond the corner) refutes it as
a standalone fix: a real doorway's collinear face begins at the corner
(median 34 mm, 22 % have none), and at 0.542 the hall door's nearest one
begins 546 mm out — the jamb block's unstroked bottom outline (path 331,
3 px off the wall face) is merged into the face run at identity by
`COLLINEAR_OFFSET_TOL` 4 and not at 2.17, and the block fails the
thick-tier material gate — while the false class (s17 door_0020: a
partition face 520 mm beyond an open leaf's tip on the leaf's line) sits at
the same distance. The hall needs a hatched-pier material rule AND a
material-based seek (≤ ~300 mm), each with one corpus instance; the pen
discriminator is the third. Report §1b. **Not built; decision pending**:
three s01-specific rules before `_gate_denominator`, or the denominator
stays as designed (`SCALE_FACTOR_MEASURED_ONLY`) and the next iterations
are the wall-pen discriminator (generic, validated at identity) and step 4.

### Step-9 review (2026-09-05, an independent agent — `docs/w-gate-iter3-checkpoints/step-9-review-prompt.md`)

Claims 1–3, 5, 6 confirmed with fresh runs; corrections adopted in
`step-9.md`: the hall's minimum seal is 9.57 px at 0.542 (17.65 at 1:50,
not 9.52 / 17.6); two `only:` ablation configs abort on the cap-ordering
assertion rather than reading 0/0; the collinear census under exact barrier
eligibility reads 308/396 doorway ends with a collinear face, 132 seek
candidates, 49 under 300 mm (the s17 door_0020 false class survives at
519 mm); the blue-dimension residue is withdrawn (path 3281 has no barrier
rights; removing the 17 blue primitives changes nothing); and BOTH wall-pen
discriminators I proposed fail on the other multi-pen sheets (a hatched
share fails s02/s04/s08/s12's unhatched wall pens; longest run overlaps —
s03's non-wall grey 491.5 px vs s02/s03 black 430.6/462.0), while
`ROOM_WALL_PEN_MIN_FRAC` 0.16 alone removes all 17 phantoms (a 1.05×
margin, not a rule) and s12 (black 59.1 % / grey 40.9 %) was missing from my
pen table. The decisive correction: the hall does NOT need the jamb block
to pair — its right face (path 278) keeps barrier rights at 0.542 and
current material reaches x ≈ 412.27, so a MATERIAL-seeking tail (nearest
wall material outward from an un-anchored hinge-edge end, a perpendicular
jamb return included, within a world cap) reaches it at ~12.3 px = 191 mm,
one rule, plausibly generic (true class: s05 door_0007 135 mm, s17
door_0004 169 mm, s18 door_0018 220 mm, s01 door_0002 203 mm). Its
false-class census (`tools/census_scratch/step9/material_seek_probe.py`:
every un-anchored hinge-edge end of a ≥ 0.55 single, the nearest FULL
barrier material outward excluding the door's own seal) is in step-9.md
§1b. `_gate_denominator` stays unchanged pending that rule and a
separating pen rule — agreed by both.

### Prompt for the next agent (iteration 3, step 10 — the material-seeking tail — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from
> `recal/s01-true-factor` (its head; `git log --all --oneline | head`; main
> is still `ee0f52f`). Re-sweep that tree first in four background groups
> (s18; s16 s11 s15; s01–s07; the rest) and `compare_sweeps --snapshot` all
> 20 slugs, never trusting what sits in `outputs/regress/`. Verdict reports
> diffed section-wise; `tools/diff_room_polygons.py` on every sheet after
> EVERY sweep; `tools/room_shape_crop.py` for every room whose IoU moved
> under 0.99; a scratch UNSIMPLIFIED polygon diff (`ROOM_SIMPLIFY_TOL_PX`
> 0, the rule toggled by monkeypatch) whenever any room loses area. Harness
> gate overrides go in as MULTIPLIERS (`H.overrides(mult=...)`), never
> absolute px. Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-9.md` (all of it — §1, §1b as
> corrected, §2, the review section), `step-9-review-prompt.md`,
> `step-8.md`, `step-3.md`, this handoff's iteration-3 outcome sections
> (step 9 and its review last), the CLAUDE.md paragraphs "Room detection"
> and "Wall/room world-space gates", `detection/rooms.py::_door_plugs`,
> `_restrict_swing_plugs`, `_swing_hinge_edges`, `_clip_plug_tails`,
> `_tail_material_end`, `_plane_stamp` and the `door_barriers` loop in
> `detect_rooms`, and `docs/regression-testing-guide.md` §9 §10 §12 §13.
> The step-9 scratch tooling is in `tools/census_scratch/step9/` (README):
> `s01_common.run_tapped` (seals keyed by bbox, taps on `_door_plugs` /
> `_clip_plug_tails` / `_plane_stamp` / `_free_space_components`),
> `s01_profile.py` (the hall door's profile numbers), `material_seek_probe.py`
> (the rule's false-class census); the harness cache is
> `tools/census_scratch/cache/`.
>
> **Tree state**: `ROOM_OPENING_SEAL_PX` 15, `_plane_stamp` shipped, corpus
> 0 LOST / 68 returned FPs / 0 REVIEW, every labelled sheet fully reviewed;
> `_gate_denominator` unchanged, s01 detects at identity. The user has
> decided (2026-09-05) to retire s01's three stair-split verdicts
> ((1090,699)–(1142,876), (466,920)–(521,1056), (1033,925)–(1142,1134)) BY
> HAND once s01 runs at 0.542 and to re-review the merged rooms then — do
> not touch `tests/ground_truth/s01.json` yourself.
>
> **This step: the MATERIAL-SEEKING TAIL** (`_door_plugs`), the rule an
> independent review of step 9 proposed and step 9's census supports. The
> convention: a doorway is cut out of a wall, so its jamb is wall material
> the plug's tail has to reach; the tail's reach is fixed in advance
> (bbox ± SEAL) while the jamb's distance is drawn. Rule: for a single
> swing door at ≥ `ROOM_BBOX_SEAL_MIN_CONFIDENCE` (0.55), on a HINGE edge
> (`_swing_hinge_edges`) whose profile fails at exactly ONE end's anchor
> (start/end cover or touch) while the other end anchors, sample outward
> from the failing corner beyond SEAL up to a new W-class constant
> `ROOM_PLUG_JAMB_SEEK_PX` (~250 mm: 29.5 px at 1:50, 16 px at 0.542,
> 14.8 px at 1:100), find the first sample within the plug half-width of
> WALL MATERIAL (a perpendicular jamb return counts; opening seals never
> do — `_door_plugs` only sees wall material anyway), extend THAT end's
> reach to that distance plus the anchor window, and re-run the profile
> with asymmetric reaches; only the interrupted signature may result (the
> doorway), never a "full" plug. Consequences you must handle: `local` (the
> material clipped `SEAL + NEAR + 4` around the bbox in the `door_barriers`
> loop) must be clipped at `SEEK + NEAR + 4` — prove that alone is inert
> (corpus byte-identical) before the seek; `_clip_plug_tails` uses SEAL as
> its reach and would cut the extended tail back — make its reach the
> plug's own along-edge extent beyond each corner (max of SEAL and the
> plug polygon's projection); `_plane_stamp` stays as it is.
>
> **Measured classes (step-9 §1b, `material_seek_probe.py` on all 18 sheets
> at their factors + s01 at 0.542, every un-anchored hinge-edge end of a
> ≥ 0.55 single, 172 + 5 ends)**: true — the s01 hall door's top edge at
> 0.542 (material at 12.3 px = 191 mm, the jamb block's right face, path
> 278, perpendicular; seals at S ≥ 9.57 px), s18 door_0018's right edge at
> 11 px = 186 mm (a 139 px 90° face; its doorway per step-8's table,
> plug-less today — expect its rooms 0002/0003 to change, a win to
> picture); false — exactly one within 300 mm: s14 door_0007's open-leaf
> tip reaching a wall-fill chevron ring (paths 3015/3016) at 35 px =
> 296 mm, which a 250 mm cap excludes at 1.18×; s01 door_0015's garden-pair
> piers at 18 px = 281 mm must stay OUT at identity (else s01 at f = 1.0
> moves — a decision, not a silent change); s14 door_0011 edge 0 has a
> jamb at 161 mm but nothing at its other end (no plug either way). Pin
> with synthetic tests: a doorway whose latch jamb is a perpendicular
> return 22 px past the corner at 1:50 seals (fails today); a leaf tip with
> material at cap + 6 px does not; a fallback-tier (0.35) box never seeks;
> each test must fail on the old code for the stated reason.
>
> **Proof**: the fast tier green (`python -m unittest discover tests`;
> `test_takeoff_fn_equivalence`'s `warnings` field fails on the untouched
> tree, pre-existing), the harness at s01 0.542 showing the hall matched
> (rooms 9/12 — the three stair rooms stay lost until their verdicts are
> retired) with no new phantom beyond the 18 already measured, then the
> corpus sweep: 0 LOST, 68 returned FPs, s01/s02 at f = 1.0 entity- and
> polygon-identical, every polygon move listed and pictured (s18 rooms
> 0002/0003 expected). If a rule costs a confirmed entity or returns an FP,
> revert it, report why with a before|after of what the lost entity is a
> chunk of, and STOP. Update the prose (the `_door_plugs` docstring, the
> constant's comment with the measured classes, the CLAUDE.md room
> paragraph's plug sentences, findings §4 row) in the existing style.
>
> **After it (each its own iteration)**: a wall-pen discriminator for
> colour-coded sheets (step-9 §2: s01's red furniture pen at 13.7 % / 15.2 %
> of the paired stroked length against `ROOM_WALL_PEN_MIN_FRAC` 0.15 —
> 0.16 alone clears the 17 phantoms at 0.542 but is a 1.05× number; both
> candidates I proposed, hatched-band share and longest paired run, were
> refuted on s02/s03/s04/s08/s12 — census every multi-pen sheet
> s01/s02/s03/s04/s08/s12/s17 before proposing anything); then narrow
> `_gate_denominator` (s01 at 0.542 keeps 11 doors, 4 windows, the hall
> and every remaining confirmed room; the stair retirement and the
> re-review happen then); then step 4 (`WALL_MAX_THICKNESS_PX` 36 → 40:
> the s11 recess box (1030,1330)–(1123,1360), s15 annotation pocket
> (1480,698)–(1595,792) and s18 tree strip (156,724)–(197,863) must stay
> out; expected −5 recorded phantoms on s16/s17); then the long queue
> (same-line tail material for s17 door_0016, phase-invariant plug profiles,
> the dash-row text-mask join, the fallback in-wall gate on tail-less plugs,
> band pockets / the recess class, Gap D of `docs/hatch-cell-chords-handoff.md`,
> a jamb-scale floor for lining rings, the lattice knife-edges, an
> open-arrowhead stair recognizer, interior rings in the exported room
> polygon, s18's glyph-outline fill rings).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an
> explicit go for that specific entry; never revert s01's truth scale
> (1:92.2); never `git stash`; macOS has no `timeout`; python is not on the
> shell path — use `.venv/bin/python` with an ABSOLUTE path in background
> commands (the cwd resets); the venv lacks InquirerPy; a Gemini label
> reseed needs `gcloud auth application-default login` in the user's
> prompt when it reports "Reauthentication is needed"; s01 and s02 at
> f = 1.0 must not change (entity set AND polygons) until
> `_gate_denominator` deliberately moves s01, and any move is reported as a
> decision; probe with the FULL wall material, never `_door_plugs`' 27 px
> local clip, and with the room stage's real barrier rules, never an
> approximation (both bit step 9); PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id; commit messages carry no Co-Authored-By or session
> trailer. End every report with the numbers: lost, returned FPs, new
> REVIEW lines with your verdicts, net phantom delta, and what is next.

## Outcome — iteration 3, step 10 (2026-09-05, branch `fix/material-seeking-plug-tail`, shipped pending the user's decision)

The MATERIAL-SEEKING TAIL (`detection/rooms.py`: `ROOM_PLUG_JAMB_SEEK_PX`
29.5 = 250mm W-class, `_seek_edges`, `_edge_profile`, `_seek_jamb`,
`_door_plugs(seek_edges=)`; `_clip_plug_tails` takes a sought tail's own
extent as its reach; the `local` clip widened to SEEK + anchor window +
NEAR + 4 and proven inert alone — corpus byte-identical). Rule: on a hinge
edge of a ≥ 0.55 single whose fixed profile anchors at exactly one end,
seek the nearest wall material outward from the failing corner within the
cap (the material buffered by the plug half-width, cut by the edge's ray —
phase-free; the envelope starts at the corner, so a touch inside the fixed
reach whose anchor window straddled the corner seeks too), extend that
end's reach to the hit plus the anchor window, re-profile; interrupted
only. Ten tests (`TestJambSeekingTail`), every guard bite-proven; the
one-end-anchored precondition is redundant with the re-profile's both-ends
check. Harness s01 at 0.542: rooms 8/12 → **9/12 (the hall)**, the same 18
unreviewed, doors/windows 11/4. Corpus sweep: **0 LOST, 68 returned FPs, 0
REVIEW**, verdict-identical; `seek_census.py` (the rule as implemented, every
door on 18 sheets with/without the seek): 4 doors change, every hit a
perpendicular wall at 76–178mm — s01 door_0002 @0.542, s14 door_0008 (76mm,
the straddling-window class; polygons identical), s17 door_0004 (121mm; the
confirmed `partial` room_0018 stops at the closed leaf instead of wrapping
under it into the threshold, −1,163 px², IoU vs verdict 0.545 → 0.572) and
s18 door_0018 (178mm; rooms 0002/0003 +695/+30). 17 sheets polygon-
identical, s01/s02 untouched at f=1.0, nothing appears or vanishes. Report
`docs/w-gate-iter3-checkpoints/step-10.md` (4 PNGs). Not committed.

### Prompt for the next agent (iteration 3, step 11 — the wall-pen discriminator — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from
> `fix/material-seeking-plug-tail` once the user has committed it (else from
> `recal/s01-true-factor`; `git log --all --oneline | head`; main is still
> `ee0f52f`). Re-sweep that tree first in four background groups (s18; s16
> s11 s15; s01–s07; the rest) and `compare_sweeps --snapshot` all 20 slugs,
> never trusting what sits in `outputs/regress/`. Verdict reports diffed
> section-wise; `tools/diff_room_polygons.py` after EVERY sweep;
> `tools/room_shape_crop.py` for every room whose IoU moved under 0.99; a
> scratch UNSIMPLIFIED diff whenever any room loses area; harness overrides
> as MULTIPLIERS. Read first, in this order: `docs/w-gate-iter3-checkpoints/
> step-10.md`, `step-9.md` (§2 and the review section), this handoff's
> iteration-3 outcome sections, the CLAUDE.md paragraphs "Room detection"
> (the wall-pen block: search `ROOM_WALL_PEN_MIN_FRAC` and `_pens_compatible`)
> and "Wall/room world-space gates", `detection/rooms.py::detect_rooms`'s
> wall-pen block, `docs/regression-testing-guide.md` §9 §10 §12 §13. The
> step-9/10 scratch tooling is in `tools/census_scratch/step9/` (README):
> `s01_pens.py [slug]` (per-pen PAIRED stroked face length, the gate's input;
> `pens_corpus.txt`), `s01_phantoms.py` (the 17 red-fenced rooms at 0.542),
> `s01_common.run_tapped`, `seek_census.py`; the harness cache is
> `tools/census_scratch/cache/`.
>
> **Tree state**: seal 15, `_plane_stamp`, the seeking tail; corpus 0 LOST /
> 68 returned FPs / 0 REVIEW; s01 detects at identity; at 0.542 in the
> harness s01 reads doors 11/11, windows 4/4, rooms 9/12 (the three stair
> verdicts the user will retire by hand) with 18 unreviewed: 17 phantoms
> fenced by the RED furniture pen (1,0,0) — 12 kitchen-unit / sofa-cushion
> cells of 0.24–0.38 m², 2 slivers, 1 strip, 2 room splits — plus the real
> merged landing (1032,697)–(1142,1136).
>
> **This step: a WALL-PEN DISCRIMINATOR for colour-coded sheets.** The room
> stage makes a pen a wall pen when its PAIRED stroked face length reaches
> `ROOM_WALL_PEN_MIN_FRAC` (0.15) of the network's total; s01's red pen sits
> at 13.7 % at identity and 15.2 % at 0.542 (33 thin same-pen sofa/bed pairs
> at th 2.5–4.8 appear while black loses 700px and blue 283px) — a knife-edge
> on both sides, and 0.16 alone clears the 17 phantoms but is a 1.05× number.
> Both candidates step 9 proposed were REFUTED on the other multi-pen sheets
> by the reviewer: a hatched-band share (fails the true unhatched wall pens
> of s02/s04/s08/s12) and the longest paired run (s03's NON-wall 0.73-grey
> pen reaches 491.5px while s02/s03 black stop at 430.6/462.0). Census EVERY
> multi-pen sheet — s01 (identity AND 0.542), s02, s03, s04, s08, s12, s17 —
> per pen and per paired segment before proposing anything: share of the
> paired length, share carrying wall MATERIAL (hatch marks per 100px,
> `_band_has_wall_material`'s input), thickness distribution of the pairs
> (s01's red pairs at 0.542 are 2.5–4.8px — under any real wall; s02's
> joinery pen?), whether a pen's pairs ever close a room-sized loop on their
> own, whether its faces ever carry a door/window opening (a wall pen's
> runs are interrupted by openings; a furniture pen's never are), the pen's
> share of the page's LONE barrier faces vs paired faces, and what each pen
> is on each sheet (the true class: s03 grey 0.58 / s04 s08 grey 0.6 / s12
> grey 40.9 % are EXISTING-wall pens; the false class: s01 red, s02 joinery
> 6.4 %, s03 grey 0.73 at 10.4 %, s17 orange 0.8 %). State the drawing
> convention ("a wall pen's runs are cut by the sheet's openings" or
> whatever the census supports with ≥ 1.5× margins on ≥ 2 sheets each
> side), pin it with a synthetic test that fails on the old code, build it,
> and prove: harness s01 at 0.542 with 0 red-fenced rooms (9/12, 1
> unreviewed — the landing) and the corpus sweep verdict-identical with
> s01/s02 at f=1.0 entity- and polygon-identical. If no convention separates
> with margin, report the census and STOP — the number 0.16 is not a rule.
>
> **After it (each its own iteration)**: narrow `_gate_denominator` (s01 at
> 0.542 keeps 11 doors, 4 windows, the hall and every remaining confirmed
> room; the user retires the three stair verdicts by hand then and
> re-reviews the merged landing through `tools/review.py`); then step 4
> (`WALL_MAX_THICKNESS_PX` 36 → 40: the s11 recess box (1030,1330)–
> (1123,1360), s15 annotation pocket (1480,698)–(1595,792) and s18 tree
> strip (156,724)–(197,863) must stay out; expected −5 recorded phantoms on
> s16/s17); then the long queue (same-line tail material for s17 door_0016,
> phase-invariant plug profiles, the dash-row text-mask join, the fallback
> in-wall gate on tail-less plugs, band pockets / the recess class, Gap D of
> `docs/hatch-cell-chords-handoff.md`, a jamb-scale floor for lining rings,
> the lattice knife-edges, an open-arrowhead stair recognizer, interior
> rings in the exported room polygon, s18's glyph-outline fill rings).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an
> explicit go for that specific entry; never revert s01's truth scale
> (1:92.2); never `git stash`; macOS has no `timeout`; python is not on the
> shell path — use `.venv/bin/python` with an ABSOLUTE path in background
> commands (the cwd resets); the venv lacks InquirerPy; a Gemini label
> reseed needs `gcloud auth application-default login` in the user's prompt
> when it reports "Reauthentication is needed"; s01 and s02 at f = 1.0 must
> not change (entity set AND polygons) until `_gate_denominator` deliberately
> moves s01, and any move is reported as a decision; probe with the FULL wall
> material and the room stage's real barrier rules, never an approximation;
> census the rule AS IMPLEMENTED (with/without it on the pipeline's exact
> inputs — `seek_census.py`'s pattern), not only the pre-build probe; never
> import `crop_s01.py`-style scratch scripts that render at import (guard
> under `__main__`); PNG crops go under `docs/w-gate-iter3-checkpoints/` and
> must never show a street address or planning-portal id; commit messages
> carry no Co-Authored-By or session trailer. End every report with the
> numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.

## Outcome — iteration 3, step 11 (2026-09-05, branch `fix/wall-pen-discriminator`, shipped pending the user's decision)

The DOORWAY VETO on the wall-pen share gate (`detection/rooms.py`:
`_doorway_pens`, a second barrier pass in `detect_rooms`). The census
(`tools/census_scratch/step11/`, every multi-pen sheet, s01 at both
factors) first corrected the brief's classes — s03's 0.73 grey draws the
existing rear-extension walls (10.4 %, a wall pen sealed by its fills), and
s02's 6.4 % "joinery" pen is the title block's logo lettering — then measured
every feature the brief listed: paired share, material share (0 % on the
unhatched wall pens of s02/s04/s08/s12), pair thickness (s12's grey wall pen
at 6 px median, s04's black 5.3), longest run, loop closure, the lone/paired
split — none separates. What does: **a doorway is cut out of a wall.** A
confident door's INTERRUPTED plug reaches a jamb at each end; a pen forms
the jamb when a PAIRED face of it intersects the tail envelope (the band
continuing, or a corner-hung door's return) or a LONE face of it collinear
with the doorway line stops in the jamb window (the tail plus the plug's
first `ROOM_PLUG_NEAR_PX` inside the bbox — a swing symbol overlaps its
hinge jamb by 3 px on s01); the doorway is cut into the pen forming BOTH
jambs. The loose "ink touches a tail" form was refuted first (s01 red
touched 4 doors at identity through units and wardrobe ends against the
wall; blue's dimension EXTENSION lines end at both jambs of one door per
factor — lone, perpendicular, excluded). On the pipeline's own plugs: every
network-building wall pen owns 1–27 doorways (s01 black 6/5, magenta 2/4,
s02 black 1, s03 black 14 / grey 8, s04 3/3, s08 3/3, s12 7/4, s17 27,
single-pen sheets 3–14), every annotation/furniture pen 0 (s01 red at both
factors and blue, s02's four, s17's orange and red, the 0 % reds). Because
ownership is read off pass-1 plugs, which qualified against the share-gated
material, the doorways VETO a share-gated pen and never promote an
under-share one (promotion is untestable without pen-independent material
and unobservable on the corpus — s03's 0.73 grey; its own iteration if a
sheet ever needs it); when no doorway names any pen the share gate stands
alone. Six tests (`TestDoorwayOwnedWallPens`), every guard bite-proven
(veto, both jambs, confidence floor, the lone-collinear clause via a
single-line wall). **Harness s01 at 0.542: doors 11/11, windows 4/4, rooms
9/12, unreviewed 18 → 1 (the merged landing); lost = the three stair
verdicts.** Corpus sweep: **0 LOST, 68 returned FPs, 0 REVIEW, all 20
sheets entity- and polygon-IDENTICAL** (the veto fires on no sheet at its
factor — the census said so before the sweep). Report
`docs/w-gate-iter3-checkpoints/step-11.md` (2 PNGs). Not committed.

### Prompt for the next agent (iteration 3, step 12 — narrowing `_gate_denominator` — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from
> `fix/wall-pen-discriminator` once the user has committed it (`git log
> --all --oneline | head`; main is still `ee0f52f`). Re-sweep that tree
> first in four background groups (s18; s16 s11 s15; s01–s07; the rest)
> and `compare_sweeps --snapshot` all 20 slugs, never trusting what sits in
> `outputs/regress/`. Verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep; `tools/room_shape_crop.py`
> for every room whose IoU moved under 0.99; a scratch UNSIMPLIFIED diff
> whenever any room loses area; harness overrides as MULTIPLIERS
> (`H.overrides(mult=...)`). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-11.md`, `step-10.md`, `step-9.md`
> (§2, §3 and the review), this handoff's iteration-3 outcome sections, the
> CLAUDE.md paragraphs "Room detection" (the wall-pen block: search
> `_doorway_pens`) and "Wall/room world-space gates" (the
> `SCALE_FACTOR_MEASURED_ONLY` design note and findings doc §4f),
> `scale/factor.py::detection_scale` / `_gate_denominator`,
> `docs/regression-testing-guide.md` §9 §10 §12 §13. Scratch tooling:
> `tools/census_scratch/harness.py` (`H.run(page, factor=...)`,
> `H.score`), `step9/s01_common.run_tapped`, `step11/implemented_census.py`;
> the harness cache is `tools/census_scratch/cache/`.
>
> **Tree state**: seal 15, `_plane_stamp`, the material-seeking tail, the
> doorway veto; corpus 0 LOST / 68 returned FPs / 0 REVIEW; s01 detects at
> identity (`SCALE_FACTOR_MEASURED_ONLY`: a measured, non-standard
> denominator never drives the gates); at 0.542 in the harness s01 reads
> doors 11/11, windows 4/4, rooms 9/12 — lost exactly the three stair
> verdicts (1090,699)–(1142,876), (466,920)–(521,1056),
> (1033,925)–(1142,1134) the user has retired in principle — with ONE
> unreviewed room, the merged landing (1032,697)–(1142,1136).
>
> **This step: let s01's measured 1:92.2 drive its gates.** Decide, with
> the user, what `_gate_denominator` should accept: a user-stored measured
> denominator (s01's is stored, `scale/store.py`), a dimension-verified one
> (`takeoff/plausibility.py` verifies 1:92.2 from 31 dimension strings), or
> both — and what stays excluded (an unverified text scale). Build it,
> then prove: the sweep loses EXACTLY the three stair verdicts and nothing
> else on s01 (11 doors, 4 windows, the hall and every other confirmed
> room), gains the merged landing as one REVIEW line, and every other sheet
> is entity- and polygon-identical (no other sheet has a measured-only
> scale — check `TRUE_SCALE` in the harness against `scale/` for each).
> Report the three LOST lines as the expected retirements; the user then
> deletes them from `tests/ground_truth/s01.json` by hand and records the
> landing through `tools/review.py s01` (data commit, theirs). Then s01's
> room-label cache needs a Gemini reseed at the new geometry
> (`python app.py extract fixtures/sheets/s01-*.pdf --out <dir>
> --ceiling-height 2.4 < /dev/null`; `gcloud auth application-default
> login` in the user's prompt if it reports "Reauthentication is needed").
>
> **After it (each its own iteration)**: step 4 (`WALL_MAX_THICKNESS_PX`
> 36 → 40: the s11 recess box (1030,1330)–(1123,1360), s15 annotation
> pocket (1480,698)–(1595,792) and s18 tree strip (156,724)–(197,863) must
> stay out; expected −5 recorded phantoms on s16/s17); then the long queue
> (promotion of an under-share wall pen by doorways on pen-independent
> material — s03's 0.73 grey is the instance, inert today; same-line tail
> material for s17 door_0016, phase-invariant plug profiles, the dash-row
> text-mask join, the fallback in-wall gate on tail-less plugs, band
> pockets / the recess class, Gap D of `docs/hatch-cell-chords-handoff.md`,
> a jamb-scale floor for lining rings, the lattice knife-edges, an
> open-arrowhead stair recognizer, interior rings in the exported room
> polygon, s18's glyph-outline fill rings).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an
> explicit go for that specific entry; never revert s01's truth scale
> (1:92.2); never `git stash`; macOS has no `timeout`; python is not on the
> shell path — use `.venv/bin/python` with an ABSOLUTE path in background
> commands (the cwd resets); the venv lacks InquirerPy; s02 at f = 1.0 must
> not change (entity set AND polygons), and every s01 change is reported
> as a decision with its LOST lines named; probe with the FULL wall
> material and the room stage's real barrier rules, never an
> approximation; census the rule AS IMPLEMENTED (with/without it on the
> pipeline's exact inputs); scratch scripts that render pictures do so
> under `__main__` only; PNG crops go under `docs/w-gate-iter3-checkpoints/`
> and must never show a street address or planning-portal id (s02's title
> block carries one — never crop it); commit messages carry no
> Co-Authored-By or session trailer. End every report with the numbers:
> lost, returned FPs, new REVIEW lines with your verdicts, net phantom
> delta, and what is next.

## Outcome — iteration 3, step 12 (2026-09-06, branch `recal/gate-denominator-stored-scale`, shipped pending the user's decision)

`_gate_denominator` narrowed by the DRAWING'S OWN DIMENSION STRINGS. The
user's decision (asked in plain terms — trust what was typed, trust only
proven numbers, or both): "autodetect — if there are numbers to verify the
claim we should use them … some builders who upload the PDF might not know
what the scale is … either way verify the claim if possible", and build it
although only s01 exercises it today. So: the ticked-dimension-string
matcher moved from `takeoff/plausibility.py` into `scale/dimensions.py`
(re-exported unchanged, one grammar; `MM_PER_PX_AT_1_1` now lives in
`scale/units.py` because scale/ must not import takeoff/), `run_extract`
matches the FULL page once and hands the list to both `detection_scale`
and `compute_takeoff` (which no longer re-matches), and
`scale/factor.py::_gate_choice` judges each floor-plan region by the ≥ 3
strings drawn inside its own bbox (`measured_denominator`, the median;
page-level fallback by all of them): agreement within 5 % VERIFIES the
claim and a verified claim drives the gates whatever its number; a
contradiction past 15 % replaces it with the measured scale
(`SCALE_FACTOR_FROM_DIMENSIONS`, source `dimensions`, snapped to a standard
scale when within 2 %; the takeoff keeps the claim and its
`SCALE_IMPLAUSIBLE`); inconclusive or unmeasurable claims stand or abstain
as before (`SCALE_FACTOR_MEASURED_ONLY` survives, narrowed to the
unverified case). `DetectionScale.measured` and the summary's
`detection.measured_denominator` record the page's measured scale. Tests:
`tests/test_scale_factor.py::TestDimensionsVerifyTheClaim` (8),
`tests/test_scale_dimensions.py` (6), wiring assertions in
`test_scale_pipeline.py` (run_extract and `tools/_corpus_page.py`), and the
takeoff's reuse of precomputed matches; bite-proven — with the two
dimension branches disabled exactly the five rule tests fail. **Rule
census as implemented (all 20 sheets): s01 24 + 7 strings, both plans
verified at 1:92.21/92.23, factor 1.0 → 0.5423; every other sheet 0
strings, factor unchanged.** Sweep vs the re-run baseline (0 LOST / 68 /
0, verdict lines byte-identical to step 9): **s01 3 LOST — exactly the
three retired stair verdicts (1090,699)–(1142,876), (466,920)–(521,1056),
(1033,925)–(1142,1134) — 68 returned FPs (identical lines), 1 REVIEW (the
merged landing (1032,697)–(1142,1136), 0.85, real); doors 11/11, windows
4/4, rooms 9/12; 19 sheets entity- and polygon-IDENTICAL.** s01's polygons:
the hall absorbs the CPD cupboard and the flight (+10.9k px², IoU 0.75
against its verdict, still matched), six rooms gain 24–791 px²,
unsimplified loss 143 px² in sub-pen slivers over all matched rooms
against 12.6k gained; door_0012's folding bbox is 8 px shorter along its
jamb (`DOOR_FOLD_JAMB_ANCHOR_TOL_PX` 5.4 px at 0.542, IoU 0.89, matched).
Pre-existing, attributed by revert + re-run:
`tests/test_takeoff_fn_equivalence.py` fails identically on the baseline
tree (the function arm's page comes back unclassified — Gemini
application-default credentials need a re-login: "Reauthentication
failed"), which also blocks the s01 label reseed. Report
`docs/w-gate-iter3-checkpoints/step-12.md` (3 PNGs). Same day, on the
user's go ("you can retire the 3"), the three stair verdicts were removed
from `tests/ground_truth/s01.json` (20 lines, 24 confirmed remain) and the
re-sweep reads s01 11/11 / 9/9 / 4/4, exit 0, one unreviewed room — the
landing, which the user then recorded through `tools/review.py s01`
(confirmed 2026-09-06, note: "more stair at the bottom right need to be
covered. The top left also has a slight notch and does not go all the way
to the wall" — queued with the stair work) → **s01 10/10, exit 0**. The
user re-logged in to gcloud and s01's label cache was reseeded at the new
geometry (the same four names as at identity). Not committed.

### Prompt for the next agent (iteration 3, step 4 — `WALL_MAX_THICKNESS_PX` 36 → 40 — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from
> `recal/gate-denominator-stored-scale` once the user has committed it and
> made the s01 data commit (`git log --all --oneline | head`; main is still
> `ee0f52f`). Re-sweep that tree first in four background groups (s18; s16
> s11 s15; s01–s07; the rest) and `compare_sweeps --snapshot` all 20 slugs,
> never trusting what sits in `outputs/regress/`. Verdict reports diffed
> section-wise; `tools/diff_room_polygons.py` after EVERY sweep;
> `tools/room_shape_crop.py` for every room whose IoU moved under 0.99; a
> scratch UNSIMPLIFIED diff whenever any room loses area; harness overrides
> as MULTIPLIERS (`H.overrides(mult=...)`). s01 now sweeps at f = 0.542
> (its stored 1:92.2 verified by 31 dimension strings) with 10 confirmed
> rooms; the merged landing's verdict note asks for the bottom-right stair
> to be covered and a top-left notch closed — stair-queue items, report
> any move on them. Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-12.md`, `step-11.md`, `step-3.md`
> (what the cap holds on s01), the iteration-2 group-2 note on the 40 that
> was tried and reverted (`docs/w-gate-iter2-checkpoints/group-2.md` and the
> `WALL_MAX_THICKNESS_PX` comment in `detection/walls.py`), the CLAUDE.md
> "Room detection" paragraph (the cap, the thick and through tiers,
> `_claims_far_side_pair`, `_claims_far_side_sparse`) and "Wall/room
> world-space gates", `docs/regression-testing-guide.md` §9 §10 §12 §13.
> Scratch tooling: `tools/census_scratch/harness.py`,
> `step11/implemented_census.py`; the harness cache is
> `tools/census_scratch/cache/` — s01's pickle now carries factor 0.542
> (delete a slug's pickle after any scale change).
>
> **Tree state**: seal 15, `_plane_stamp`, the material-seeking tail, the
> doorway veto, and the dimension-verified gate scale (s01 detects at
> 0.542 in the sweep); corpus 0 LOST / 68 returned FPs / 0 REVIEW once the
> user has retired s01's three stair verdicts and recorded the merged
> landing; s01's label cache reseeded at the new geometry (or still
> pending — check `ROOM_LABEL_NO_GEMINI` on s01).
>
> **This step: `WALL_MAX_THICKNESS_PX` 36 → 40** (W-class; 340mm at 1:50).
> Iteration 2 tried it and reverted because the 36–40px band is full of
> fixtures at wall spacing that only material can separate — s02's WC
> basin edge over two corner X symbols at 38.25px (since cleared by
> iteration 3's far-side density rule), s01's 38.5px kitchen units. Census
> every strong pair in the 36–40px band on all 20 sheets at their factors
> (the harness's `wide_pairs` tap) with the pipeline's exact material
> marks, class each as wall or fixture from the pictures, and find the
> discriminator for whatever the far-side rules do not already catch
> BEFORE moving the number. The s11 recess box (1030,1330)–(1123,1360),
> the s15 annotation pocket (1480,698)–(1595,792) and the s18 tree strip
> (156,724)–(197,863) must stay out; expected −5 recorded phantoms on
> s16/s17 (the reveal strips, step 11's residue). s01 and s02 at f = 1.0
> must not lose an entity.
>
> **After it (each its own iteration)**: the long queue — promotion of an
> under-share wall pen by doorways on pen-independent material (s03's 0.73
> grey, inert today); same-line tail material for s17 door_0016;
> phase-invariant plug profiles; the dash-row text-mask join; the fallback
> in-wall gate on tail-less plugs; band pockets / the recess class; Gap D of
> `docs/hatch-cell-chords-handoff.md`; a jamb-scale floor for lining rings;
> the lattice knife-edges; an open-arrowhead stair recognizer; interior
> rings in the exported room polygon; s18's glyph-outline fill rings.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an
> explicit go for that specific entry; never revert s01's truth scale
> (1:92.2); never `git stash` (and in zsh an unquoted `$VAR` does NOT
> word-split — pipe file lists through `xargs`); macOS has no `timeout`;
> python is not on the shell path — use `.venv/bin/python` with an
> ABSOLUTE path in background commands (the cwd resets); the venv lacks
> InquirerPy; s02 at f = 1.0 must not change (entity set AND polygons), and
> every s01 change is reported as a decision with its LOST lines named;
> probe with the FULL wall material and the room stage's real barrier
> rules, never an approximation; census the rule AS IMPLEMENTED
> (with/without it on the pipeline's exact inputs); scratch scripts that
> render pictures do so under `__main__` only; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id (s02's title block carries one — never crop it);
> commit messages carry no Co-Authored-By or session trailer. End every
> report with the numbers: lost, returned FPs, new REVIEW lines with your
> verdicts, net phantom delta, and what is next.

## Outcome — iteration 3, step 4 (2026-09-06, branch `recal/wall-max-thickness-40`, measurement only — `WALL_MAX_THICKNESS_PX` NOT moved)

The 36 → 40 move was run AS IMPLEMENTED on all 20 sheets at their factors
(`tools/census_scratch/step4/band_census.py`: the whole stage-5 chain at cap
×1.0 and ×40/36 through the harness, segments, rooms and truth scored; then
a full corpus sweep at 40, restored). Result: 0 LOST, 68 → 63 returned FPs
(s17's four cavity-wall reveal strips — the 313mm cavity wall drawn at
36.5–36.75px, 1.03× over the cap, a standard modern wall — and s16's pocket,
sealed by two stair TREADS 18px apart, the wrong reason), 2 new REVIEW rooms
both phantoms (s18's tree strip, fenced by the site boundary drawn double at
18.25px over 682px; s11's recess box — the neighbour's chimney breast —
freed by a 20×15px stub box pairing plain under the party wall), s15's
confirmed bedroom −5,135 px² (the wardrobe's double edge × the unrecognised
"3560" dimension line on its TEXT layer), s02 re-noded by 3–19 px² (glyph
outlines pairing), s01 identical, and 27 s11/s16 rooms stopping at their
plaster lines (19.88px external walls at 1:100 with finish lines on both
sides — correct, 1.1px strips; the porch and utility had leaked into their
bands). Discriminators measured on both classes (`interior_census.py`):
material, stroked linework parallel to the faces inside the band (over the
overlap AND over the faces' full extent — the cavity's leaf lines stop
exactly where the strips form), and confident openings in the band — all
read 0 on s17's four true stretches and on s18's boundary, s16's treads and
s11's stub alike, at the same world thickness; s15's wardrobe passes the
linework test on its own double edge. So the number is not the lever and was
not moved (the brief's rule: two of the three named pockets return). The
lever is the room stage: the s17 strips are exactly `_is_band_pocket`'s
class, rejected only by its `WALL_MAX_THICKNESS_PX` ceiling (35px + 2×2 >
36); the rule sees only entrance-less, window-less components and the
corpus's narrowest confirmed room (s11's 19px storage) carries a door, so a
`WALL_THICK_MATERIAL_MAX_PX` ceiling cannot touch an entered room — and the
11 recorded-FP pockets on s11/s12/s16/s18 at 1.2–2× the cap are the same
class. Also exposed: `_dimension_line_indices` misses s15's ticked "3560" /
"1100" lines on its TEXT layer; s18's blind-window drop caps at 2.5k px² at
1:100 while the tree strip is 4.6k. Harness fixes shipped with the scratch
tooling (door-plug tap passes `seek_edges`; the marks tap captures the one
through-diagonal population so `wide_pairs` carry real material verdicts and
keep endpoints/pen). Report `docs/w-gate-iter3-checkpoints/step-4.md` (10
PNGs). Not committed.

### Prompt for the next agent (iteration 3, step 13 — the band-pocket ceiling — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from
> `recal/wall-max-thickness-40` once the user has committed it (`git log
> --all --oneline | head`; main is still `ee0f52f`). Re-sweep that tree first
> in four background groups (s18; s16 s11 s15; s01–s07; the rest) and
> `compare_sweeps --snapshot` all 20 slugs, never trusting what sits in
> `outputs/regress/`. Verdict reports diffed section-wise;
> `tools/diff_room_polygons.py` after EVERY sweep; `tools/room_shape_crop.py`
> for every room whose IoU moved under 0.99; a scratch UNSIMPLIFIED diff
> whenever any room loses area; harness overrides as MULTIPLIERS
> (`H.overrides(mult=...)`). Read first, in this order:
> `docs/w-gate-iter3-checkpoints/step-4.md` (why the cap did not move and
> where the lever is), the CLAUDE.md "Room detection" paragraph's band-pocket
> block (`_is_band_pocket`, `ROOM_BAND_POCKET_FACE_COVER_MIN`, the s17
> cavity-wall measurements, the s11 storage margin, the "11 recorded-FP
> pockets at 1.2–2× the scaled cap"), `_is_wall_recess` and
> `_drop_window_exterior_sides` beside it, `docs/regression-testing-guide.md`
> §9 §10 §12 §13. Scratch tooling: `tools/census_scratch/harness.py`
> (`H.run`, `H.score`, the `components` tap — every free-space component
> with its minimum rotated rectangle), `step4/band_census.py` and
> `step4/attribute_rooms.py` as patterns; the harness cache is
> `tools/census_scratch/cache/` (delete a slug's pickle after any scale
> change).
>
> **Tree state**: seal 15, `_plane_stamp`, the material-seeking tail, the
> doorway veto, the dimension-verified gate scale; `WALL_MAX_THICKNESS_PX`
> still 36; corpus 0 LOST / 68 returned FPs / 0 REVIEW; s01 sweeps at 0.542
> with 10/10 rooms.
>
> **This step: raise `_is_band_pocket`'s spacing ceiling from
> `WALL_MAX_THICKNESS_PX` to `WALL_THICK_MATERIAL_MAX_PX`** (a strip whose
> two long edges lie on wall faces up to pier spacing apart is inside that
> wall). Census FIRST: every entrance-less, window-less free-space component
> on all 20 sheets whose minimum rotated rectangle's short side + 2 ×
> `ROOM_LINE_BARRIER_PX` lies between the cap and the thick cap at the
> sheet's factor, with `_edge_face_cover` on both long edges — classed from
> the pictures (s17's four reveal strips 0013/0014/0027/0032 are the
> expected wins; the 11 recorded-FP pockets on s11/s12/s16/s18 are the same
> class one band deeper; s11's 19px "storage in utility" (1078,1597)–
> (1097,1704) has `door_0009` and must stay). Measure the false side — any
> door-less, window-less REAL space that narrow (a duct, a lightwell, a
> cupboard drawn without a door) — before moving the ceiling. s01 and s02 at
> their factors must not change; report every polygon move with its
> unsimplified lost/gained px².
>
> **After it (each its own iteration)**: `_dimension_line_indices` on s15's
> TEXT-layer "3560"/"1100" lines (ticked, unrecognised — they pair with
> fixture edges at wall spacing); the s18 blind-window cap at 1:100 (the
> tree strip, 4.6k px² against the scaled 2.5k); promotion of an under-share
> wall pen by doorways on pen-independent material (s03's 0.73 grey); the
> merged landing's stair coverage and top-left notch (an open-arrowhead stair
> recognizer); same-line tail material for s17 door_0016; phase-invariant
> plug profiles; the dash-row text-mask join; the fallback in-wall gate on
> tail-less plugs; the recess class (s11's party-wall box is the neighbour's
> chimney breast); Gap D of `docs/hatch-cell-chords-handoff.md`; a jamb-scale
> floor for lining rings; the lattice knife-edges; interior rings in the
> exported room polygon; s18's and s14's glyph-outline fill rings (they pair
> at the letter height, 36–40px, inert today).
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an
> explicit go for that specific entry; never revert s01's truth scale
> (1:92.2); never `git stash` (in zsh an unquoted `$VAR` does NOT
> word-split — pipe file lists through `xargs`); macOS has no `timeout`;
> python is not on the shell path — use `.venv/bin/python` with an ABSOLUTE
> path in background commands (the cwd resets); a background job imports the
> tree at launch, so never edit a constant while one is running; the venv
> lacks InquirerPy (tools/review.py is the user's to run); s02 at f = 1.0
> must not change (entity set AND polygons), and every s01 change is
> reported as a decision with its LOST lines named; probe with the FULL wall
> material and the room stage's real barrier rules, never an approximation;
> census the rule AS IMPLEMENTED (with/without it on the pipeline's exact
> inputs); scratch scripts that render pictures do so under `__main__` only
> and are kept under `tools/census_scratch/step13/`; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id (s02's title block carries one — never crop it); commit
> messages carry no Co-Authored-By or session trailer. End every report with
> the numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.

## Outcome — iteration 3, step 13 (2026-09-06, branch `recal/wall-max-thickness-40`, measurement only — the band-pocket ceiling NOT moved)

The ceiling raise (`_is_band_pocket`: `WALL_MAX_THICKNESS_PX` →
`WALL_THICK_MATERIAL_MAX_PX`) was censused AS IMPLEMENTED on all 20 sheets at
their factors (`tools/census_scratch/step13/pocket_census.py`: a tap on every
call the rule receives — 54 entrance-less, window-less components corpus-wide
— with the rule's own reading of each, then the chain with the ceiling raised
for this rule alone, rooms diffed and truth scored). Result: five components
drop — four recorded-FP cells at 360 / 406 / 442 / 470mm (s18's kitchen-corner
box, s16's partition box, s12's two unit cells, the second at 0.99× the
ceiling) and s11's CONFIRMED "storage in utility" at 368mm, the brief's own
must-stay: a real 300 × 1800mm cupboard drawn without a door of its own
(`door_0009`, the brief's reason it was "never a candidate", is the utility's
door — its one plug is an interrupted plug on the bbox's bottom edge, 8.8px
from the storage, so the room stage reads `door_count` 0 and calls the rule on
it today, rejecting it by the ceiling alone). The true class's narrowest
member therefore lies INSIDE the false class's range; the next real door-less
spaces between two faces are 599–631mm on s20/s15/s07/s17/s08 (1.26–1.33×
over 475mm). And the expected win does not exist: s17's four reveal strips
never reach the rule — each ends at a doorway cut through the cavity wall
whose 0.95 plug touches it over 15–18px (an entrance under the 4px contact
test), and a 31.5px tab where the perpendicular 35.5px band's flat-capped
solid ends pins each strip's minimum rotated rectangle ON the face line, so
one or both `_edge_face_cover`s read 0; their 328–343mm spacing is the least
of the three holds. Score with/without: 0 → 1 LOST, 68 → 64 returned FPs,
0 REVIEW; s01/s02 receive no call and are identical. Measured for the next
step, not built: an ENTRANCE is a seal running ALONG the space's boundary —
every confirmed entered room's largest entrance contact is ≥ 569mm (67.2px at
1:50) / 745mm at 1:100, the s17 strips' 127–152mm, s04's recorded-FP box's
182mm — a 3.7× margin (per seal, a neighbour's tail grazes real rooms at
30–114mm, so the statistic is the room's maximum). Report
`docs/w-gate-iter3-checkpoints/step-13.md` (10 PNGs); scratch tooling under
`tools/census_scratch/step13/`. Not committed.

### Prompt for the next agent (iteration 3, step 14 — the entrance-contact rule — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from the tree that
> carries step 13 once the user has committed it (`git log --all --oneline |
> head`; main is still `ee0f52f`). Re-sweep that tree first in four background
> groups (s18; s16 s11 s15; s01–s07; the rest) and `compare_sweeps --snapshot`
> all 20 slugs, never trusting what sits in `outputs/regress/`. Verdict
> reports diffed section-wise (sort before `cmp` — the groups' order differs);
> `tools/diff_room_polygons.py` after EVERY sweep; `tools/room_shape_crop.py`
> for every room whose IoU moved under 0.99; a scratch UNSIMPLIFIED diff
> whenever any room loses area; harness overrides as MULTIPLIERS. Read first:
> `docs/w-gate-iter3-checkpoints/step-13.md` (why the ceiling did not move,
> the three holds on s17's strips, the contact measurement), the CLAUDE.md
> band-pocket block and its step-13 sentences, `ROOM_ENTRANCE_MIN_CONFIDENCE`
> and the `entrance_count` / `door_count` / `window_count` lines in
> `detect_rooms`, `docs/regression-testing-guide.md` §9 §10 §12 §13. Scratch
> tooling: `tools/census_scratch/step13/entered_census.py` (reads
> detect_rooms' own `face_lines` and `door_barriers` off its frame through the
> free-space tap; `ENTERED_ALL=1` records every room with its entrance
> contacts), `contact_stats.py`, `pocket_census.py`, `zoom13.py`.
>
> **Tree state**: seal 15, `_plane_stamp`, the material-seeking tail, the
> doorway veto, the dimension-verified gate scale; `WALL_MAX_THICKNESS_PX`
> 36; the band-pocket ceiling unchanged; corpus 0 LOST / 68 returned FPs / 0
> REVIEW; s01 sweeps at 0.542 with 10/10 rooms.
>
> **This step: an ENTRANCE is a seal that runs ALONG the space's boundary.**
> `entrance_count` reads any ≥ 0.55 seal within `ROOM_CONTACT_TOL_PX` of the
> boundary; a doorway cut through the wall a strip lies inside of, or a
> neighbour's doorway whose tail ends at the strip's face, touches it over its
> own plug width only. Measured (step 13, `entered_all_*.json`): every
> confirmed entered room's LARGEST entrance contact is ≥ 569mm at 1:50 (s03,
> 67.2px) and ≥ 745mm at 1:100 (s18, 44px); s17's four reveal strips 127–152mm
> (15–18px), s04's recorded-FP box (1463,1042)–(1558,1131) 182mm. Build it as a
> W-class floor on the contact run (a leaf width or so — measure where the
> 3.7× margin best splits; per-seal grazing contacts on real rooms go down to
> 30mm, so the test is per room over its seals, never per seal), census it AS
> IMPLEMENTED (which rooms change entrance status on all 20 sheets, both
> classes, from the pictures), and note that `door_count` / `door_openings` /
> the confidence boost are NOT the target — only the entrance gate that feeds
> the blind-window, recess and band-pocket drops. Expected: the four s17
> strips become entrance-less — and STILL stay, because their rotated
> rectangles are pinned by the 31.5px tabs (covers 0) and their 328–343mm
> spacing is over the 36 cap; say so, and leave the tab-tolerant cover reading
> and the ceiling for their own steps (the ceiling cannot pass s11's 368mm
> storage unless that cupboard is recognised another way — it has no door
> drawn). s01 and s02 at their factors must not change; report every polygon
> move with its unsimplified lost/gained px².
>
> **After it (each its own iteration)**: the tab-tolerant cover reading in
> `_is_band_pocket` (cover on the polygon's own long runs, or standoff 0
> tolerated where a perpendicular band ends); `_dimension_line_indices` on
> s15's TEXT-layer "3560"/"1100" lines; the s18 blind-window cap at 1:100;
> promotion of an under-share wall pen by doorways on pen-independent
> material (s03's 0.73 grey); the merged landing's stair coverage and top-left
> notch on s01; same-line tail material for s17 door_0016; phase-invariant
> plug profiles; the dash-row text-mask join; the fallback in-wall gate on
> tail-less plugs; the recess class (s11's party-wall box); Gap D of
> `docs/hatch-cell-chords-handoff.md`; a jamb-scale floor for lining rings;
> the lattice knife-edges; interior rings in the exported room polygon; s18's
> and s14's glyph-outline fill rings.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an explicit
> go for that specific entry; never revert s01's truth scale (1:92.2); never
> `git stash` (in zsh an unquoted `$VAR` does NOT word-split — pipe file lists
> through `xargs`; `echo =====` is a command lookup in zsh, quote it); macOS
> has no `timeout`; python is not on the shell path — use `.venv/bin/python`
> with an ABSOLUTE path in background commands (the cwd resets); a background
> job imports the tree at launch, so never edit a constant while one is
> running; the venv lacks InquirerPy (tools/review.py is the user's to run);
> s02 at f = 1.0 must not change (entity set AND polygons), and every s01
> change is reported as a decision with its LOST lines named; probe with the
> FULL wall material and the room stage's real barrier rules, never an
> approximation (a tap on `_free_space_components` can read detect_rooms'
> locals off `sys._getframe(1)` — `face_lines`, `door_barriers`,
> `wall_material` — without editing the stage); census the rule AS
> IMPLEMENTED (with/without it on the pipeline's exact inputs); scratch
> scripts that render pictures do so under `__main__` only and are kept under
> `tools/census_scratch/step14/`; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id (s02's title block carries one — never crop it); commit
> messages carry no Co-Authored-By or session trailer. End every report with
> the numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.

## Outcome — iteration 3, step 14 (2026-09-06, branch `fix/entrance-contact-run`, shipped pending the user's decision)

An ENTRANCE is a seal that RUNS ALONG the space's boundary: `_entrance_run`
(the boundary's length within `ROOM_CONTACT_TOL_PX` of the seal, less the
tolerance's reach past each end) ≥ `ROOM_ENTRANCE_MIN_RUN_PX` = 29.5px = 250mm
at 1:50 (W-class, `RoomGates`). Only `entrance_count` reads it — the
blind-window, wall-recess and band-pocket drops; `door_openings` and the
confidence boost still count every touching seal. The tolerance is subtracted
because it is paper: a crossing plug's raw contact is 2 × half-width + 2 × TOL
(18px at 1:50, 12px at s13's 1:136), so no world floor on the raw contact
clears both classes at every factor, while on the net run the false class is
the plug's cross-section (a W quantity) and the true class the doorway width.
Censused as implemented on every emitted room of all 20 sheets
(`tools/census_scratch/step14/entrance_census.py`, gate OFF via a −1.0
multiplier = the any-touch test exactly, then ON): the largest run of every
confirmed entered room is ≥ 59.2px at f=1.0 (s03, 2.01× over the floor), 36.0px
at f=0.5 (s18, 2.44×), 37.3px at s13's 0.367 (3.45×), 47.3px on s01 at 0.542
(2.96×); exactly five rooms flip, all recorded FPs — s17's four reveal strips
(runs 7–10px: door_0025's and door_0036's plugs collinear with strips
0013/0032 and meeting their ends, the BATH door's and door_0003's tails
ending at 0014/0027's faces) and s04's stair winder box (13.5px, the hall
door's tail running down its edge). Sweep: **0 LOST, 68 returned FPs, 0
REVIEW**, one verdict line swapped — s04's winder box (8,123 px², recorded FP)
drops as a blind-window pocket and s04's stair flight (1588,1053)–(1762,1131)
(13,485 px², recorded FP) returns, because it was the door-less side of
window_0004 (tread 10 detected as a 0.62 window, itself a returned FP) that
`_drop_window_exterior_sides` dropped against the box — one staircase fenced
by its own linework plus a false window, a trade, net 0; 19 sheets entity-
and polygon-identical, s01/s02 untouched, 0 changed polygons. The s17 strips
are entrance-less and STILL emitted: `_is_band_pocket` now receives them (7
calls on s17 against 3) and rejects them by the tab-pinned covers (0013
[0.0, 1.0], 0032 [0.0, 0.93], 0014 [0.0, 0.04], 0027 [0.0, 0.0]) and the
38.75–40.5px spacing over the 36px cap — the next two steps. Pinned by
`TestEntranceRunsAlongTheBoundary` (bite-proven). Report
`docs/w-gate-iter3-checkpoints/step-14.md` (8 PNGs). Not committed.

### Prompt for the next agent (iteration 3, step 15 — the tab-tolerant cover reading in `_is_band_pocket` — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from the tree that
> carries step 14 once the user has committed it (`git log --all --oneline |
> head`; main is still `ee0f52f`). Re-sweep that tree first in four background
> groups (s18; s16 s11 s15; s01–s07; the rest) and `compare_sweeps --snapshot`
> all 20 slugs, never trusting what sits in `outputs/regress/`. Verdict
> reports diffed section-wise (sort before `cmp`); `tools/diff_room_polygons.py`
> after EVERY sweep; `tools/room_shape_crop.py` for every room whose IoU moved
> under 0.99; a scratch UNSIMPLIFIED diff whenever any room loses area;
> harness overrides as MULTIPLIERS. Read first: `docs/w-gate-iter3-checkpoints/step-14.md`
> and `step-13.md` (the three holds on s17's strips — the entrance gate is
> gone, the covers and the ceiling remain), the CLAUDE.md band-pocket block,
> `_is_band_pocket` / `_edge_face_cover` in `detection/rooms.py`,
> `docs/regression-testing-guide.md` §9 §10 §12 §13. Scratch tooling:
> `tools/census_scratch/step14/entrance_census.py` (every emitted room with
> its entrance runs, gate OFF/ON), `step13/pocket_census.py` (a tap on every
> `_is_band_pocket` call with the rule's own reading — run it on the step-14
> tree: s17 now shows 7 calls, the four strips `in_band` with one cover 0),
> `step13/s17_strip_edges.py` (where each strip's long edge lies against its
> face line), `step14/zoom14.py`.
>
> **Tree state**: the entrance-run gate (`ROOM_ENTRANCE_MIN_RUN_PX` 29.5),
> seal 15, `_plane_stamp`, the material-seeking tail, the doorway veto, the
> dimension-verified gate scale; `WALL_MAX_THICKNESS_PX` 36; the band-pocket
> ceiling unchanged; corpus 0 LOST / 68 returned FPs / 0 REVIEW; s01 sweeps at
> 0.542 with 10/10 rooms.
>
> **This step: the cover reading.** `_is_band_pocket` reads the cover of each
> long edge of the component's MINIMUM ROTATED RECTANGLE against `face_lines`
> at the barrier standoff (`_edge_face_cover`). s17's strips carry a 31.5px
> tab at the end where the perpendicular 35.5px band's flat-capped solid ends
> (the band's solid stops there and the vertical face begins 33px lower), so
> the rectangle is pinned ON the face line (standoff 0, outside the 1.5px
> tolerance) and that edge's cover reads 0: 0013 [0.0, 1.0], 0032 [0.0, 0.93],
> 0014 [0.0, 0.04], 0027 [0.0, 0.0]. Measure first: for every call the rule
> receives (pocket_census's tap, all 20 sheets), the cover read on the
> polygon's OWN long runs (the boundary segments parallel to the long axis,
> each against the faces at the standoff) versus the rectangle's edges, and
> whether tolerating standoff 0 where a perpendicular band ends (the tab is
> the band's flat cap, its face line IS the strip's edge there) separates the
> strips from the true class — every confirmed room the rule would see if its
> entrance did not spare it (`entered_census.py`'s population). Then build
> the reading that separates, census it as implemented, and NOTE that the
> strips still need the ceiling (38.75–40.5px against 36): say what the
> strips do at each ceiling, and that s11's 368mm storage lies inside the
> false class's range (step 13) unless recognised another way. s01 and s02
> must not change; report every polygon move with its unsimplified px².
>
> **After it (each its own iteration)**: the band-pocket ceiling with s11's
> storage recognised; the s04 staircase (tread 10 detected as a 0.62 window
> fences the winder box and the flight into two recorded-FP cells — the
> window detector's or the stair recogniser's class); `_dimension_line_indices`
> on s15's TEXT-layer "3560"/"1100" lines; the s18 blind-window cap at 1:100
> (10k × f² = 2.5k px² while the tree strip is 4.6k); promotion of an
> under-share wall pen by doorways on pen-independent material (s03's 0.73
> grey); the merged landing's stair coverage and top-left notch on s01; same-
> line tail material for s17 door_0016; phase-invariant plug profiles; the
> dash-row text-mask join; the fallback in-wall gate on tail-less plugs; the
> recess class (s11's party-wall box); Gap D of
> `docs/hatch-cell-chords-handoff.md`; a jamb-scale floor for lining rings;
> the lattice knife-edges; interior rings in the exported room polygon; s18's
> and s14's glyph-outline fill rings.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an explicit
> go for that specific entry; never revert s01's truth scale (1:92.2); never
> `git stash` (in zsh an unquoted `$VAR` does NOT word-split — pipe file lists
> through `xargs`; `echo =====` is a command lookup in zsh, quote it); macOS
> has no `timeout`; python is not on the shell path — use `.venv/bin/python`
> with an ABSOLUTE path in background commands (the cwd resets); a background
> job imports the tree at launch, so never edit a constant while one is
> running; the venv lacks InquirerPy (tools/review.py is the user's to run);
> s02 at f = 1.0 must not change (entity set AND polygons), and every s01
> change is reported as a decision with its LOST lines named; probe with the
> FULL wall material and the room stage's real barrier rules, never an
> approximation (a tap on `_free_space_components` can read detect_rooms'
> locals off `sys._getframe(1)` — `face_lines`, `door_barriers`,
> `wall_material` — without editing the stage); census the rule AS
> IMPLEMENTED (with/without it on the pipeline's exact inputs); scratch
> scripts that render pictures do so under `__main__` only and are kept under
> `tools/census_scratch/step15/`; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id (s02's title block carries one — never crop it); commit
> messages carry no Co-Authored-By or session trailer. End every report with
> the numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.

## Outcome — iteration 3, step 15 (2026-09-06, branch `fix/band-pocket-tab-cover`, shipped pending the user's decision)

`_is_band_pocket` reads the cover of each long SIDE on the component's OWN
boundary runs, never on its minimum rotated rectangle's edges
(`_side_wall_covers`, `_run_wall_cover`; no constant moved): the runs
parallel to the rectangle's long axis are classed to a side by their offset
from its centre, a run lies along wall where a face runs beside it at the
barrier standoff (read where the face actually lies beside the run) or where
a wall solid's flat END lies on it (`cap_lines`, every paired segment's end
line, standoff 0), and a side's cover is the union of its runs' wall-lying
stretches projected on the axis over the rectangle's length. The tab: s17's
four reveal strips each end where a perpendicular 35.5px partition meets the
cavity wall with its two faces drawn unequal — the face at the strip's end
runs across the wall to its far face (paths 2701 / 2905 / 2697), so the
paired segment ends ON the strip's face line, its flat cap forms a 31.5px tab
at standoff 0, and the rectangle's edge sat on the face line the rest of the
side lies 2px inside of (covers 0013 [0.0, 1.0], 0032 [0.0, 0.93], 0014
[0.0, 0.04], 0027 [0.0, 0.0] before; [0.99, 1.0], [1.0, 1.0], [0.96, 0.99],
[1.0, 1.0] now — 0.79–0.93 on the face, the rest on the cap). Censused four
ways on every call the rule receives (58) and every emitted room (244) of
all 20 sheets at their factors, then as implemented at ceilings 40 / 41 /
44 / 48 / 56 for the rule alone (`tools/census_scratch/step15/`): the s11
storage reads 1.0/1.0 under every reading; s18's recorded-FP sofa-back strip
(907,810)–(1079,833) 0.14 → 0.90 (a notch pinned its rectangle); at the 36
ceiling the rule's population is one already-dropped reveal, so the sweep is
**0 LOST / 68 returned FPs / 0 REVIEW, verdict-line-identical, all 20 sheets
entity- and polygon-identical**. The strips are held out by the ceiling
ALONE: at 40 three drop (0027 at 40.5px stays), at 41 all four; s11's
confirmed 368mm storage is LOST from 44 up (22px at f=0.5 against 21.75),
s18's kitchen-corner box goes at 44, s16's partition box at 48, s12's two
unit cells and the sofa-back strip at 56; nothing else moves on any sheet at
any ceiling. Pinned by `TestBandPocketTabbedByAPerpendicularBand` (s17's
junction as drawn; bite-proven, 1441 tests green). Found on the way: the
wall-recess rule fails on the same tab (its back-edge test reads the
component's extent) — a tab-less version of the fixture is a recess, the
tabbed one is not; and a 41px ceiling would take all four strips and keep
the storage by 1.06× — a knife-edge. Report
`docs/w-gate-iter3-checkpoints/step-15.md` (6 PNGs). Not committed.

### Prompt for the next agent (iteration 3, step 16 — recognising s11's storage so the band-pocket ceiling can move — fresh context)

> Use `/fix-detection` for its discipline. Topic branch from the tree that
> carries step 15 (`fix/band-pocket-tab-cover`; `git log --all --oneline |
> head`; main is still `ee0f52f`). Re-sweep that tree first in four
> background groups (s18; s16 s11 s15; s01–s07; the rest) and
> `compare_sweeps --snapshot` all 20 slugs, never trusting what sits in
> `outputs/regress/`. Verdict reports diffed section-wise (sort before cmp —
> the groups' order differs); `tools/diff_room_polygons.py` after EVERY
> sweep; `tools/room_shape_crop.py` for every room whose IoU moved under
> 0.99; a scratch UNSIMPLIFIED diff whenever any room loses area; harness
> overrides as MULTIPLIERS (`H.overrides(mult=...)`). Read first, in this
> order: `docs/w-gate-iter3-checkpoints/step-15.md`, step-13.md (the s11
> storage: a real 300 × 1800mm cupboard between the party wall and the
> utility partition, drawn with NO door of its own — `door_0009` is the
> utility's door, its plug 8.8px off; the takeoff's grown polygon counts
> that door, the room stage's 4px contact does not) and step-4.md (what the
> 40 cap admits at the pairing stage), the CLAUDE.md "Room detection"
> paragraph's band-pocket block and the step-13/14/15 sentences at the end
> of the gate paragraph, `_is_band_pocket` / `_side_wall_covers` /
> `_run_wall_cover` / `_contains_text` / `_is_wall_recess` in
> `detection/rooms.py`, `_vector_text_indices` in `detection/walls.py`,
> `docs/regression-testing-guide.md` §9 §10 §12 §13. Scratch tooling:
> `tools/census_scratch/harness.py`, `step15/cover_census.py` (every
> `_is_band_pocket` call and every emitted room with the cover read four
> ways, off detect_rooms' own locals through the free-space tap —
> `face_lines`, `cap_lines`, `door_barriers`, `wall_segments`),
> `step15/ceiling_census.py` (the rule as implemented at ceilings 40 / 41 /
> 44 / 48 / 56 for the rule alone: what drops, rooms diffed, scored),
> `step15/zoom15.py`, `step13/pocket_census.py`, `step13/s11_storage_door.py`;
> the harness cache is `tools/census_scratch/cache/` (delete a slug's pickle
> after any scale change).
>
> Tree state: the band-pocket cover read on the component's own sides with
> wall solids' flat ends admitted (step 15), the entrance-run gate
> (`ROOM_ENTRANCE_MIN_RUN_PX` 29.5 net of the paper tolerance), seal 15,
> `_plane_stamp`, the material-seeking tail, the doorway veto, the
> dimension-verified gate scale; `WALL_MAX_THICKNESS_PX` 36; the band-pocket
> ceiling = that cap; corpus 0 LOST / 68 returned FPs / 0 REVIEW, all 20
> sheets identical to step 14; s01 sweeps at 0.542 with 10/10 rooms.
>
> This step: the band-pocket CEILING, gated on recognising s11's storage.
> Measured as implemented in step 15: the s17 strips (38.75 / 38.75 / 38.79 /
> 40.5px = 328–343mm, all recorded FPs) drop three at a 40 ceiling and all
> four at 41; s11's CONFIRMED "storage in utility" (1078,1597)–(1095,1704),
> 21.75px at f=0.5 = 368mm, both sides 1.0 under every reading, is LOST from
> 44 (22px); s18's recorded-FP kitchen box goes at 44, s16's box at 48,
> s12's two cells and s18's sofa strip at 56; nothing else on any sheet at
> any ceiling. 41 keeps the storage by 1.06× — the skill's 1.5× rule forbids
> it. So FIRST find what makes that cupboard a space when a reveal is not,
> measured on both classes (the four strips + the recorded-FP cells at
> 360–470mm vs the storage, and every confirmed room the rule would see if
> its entrance did not spare it — `ENTERED_ALL`, step 13's entered_census):
> (a) a LABEL drawn as vector text — s11 has zero text spans and
> `_contains_text` sees nothing, but `_vector_text_indices` already
> recognises glyph rows for the wall network; does a glyph row lie inside
> the storage, and inside none of the strips or cells? (a named space is a
> space whatever its shape — the rule's own text veto, extended to the
> sheets that draw their labels as strokes); (b) what lies BEHIND each
> bounding side — a paired segment's solid, a fill, hatch, or nothing (a
> reveal lies inside ONE wall whose leaf lines stop; a cupboard lies between
> TWO walls, each with its own material on the far side); (c) whether the
> two sides could have paired as one band (same pen, the "could have paired"
> premise); (d) anything else the pictures suggest. Build the one that
> separates with a margin, pin it with a synthetic test, then move the
> ceiling to the value the census supports (`WALL_THICK_MATERIAL_MAX_PX`
> if the storage is recognised, else nothing) as a SEPARATE change with its
> own with/without census — one fix per iteration; if the discriminator
> needs its own step, stop there and report. s01 and s02 at their factors
> must not change (entity set AND polygons); report every polygon move with
> its unsimplified lost/gained px².
>
> After it (each its own iteration): `_is_wall_recess`'s back-edge test on
> the same tab (a tab-less version of `TestBandPocketTabbedByAPerpendicularBand`'s
> fixture is a recess, the tabbed one is not); the s04 staircase (tread 10
> detected as a 0.62 window, a returned FP, fences the winder box and the
> flight into two recorded-FP cells — the window detector's or the stair
> recogniser's class); `_dimension_line_indices` on s15's TEXT-layer
> "3560"/"1100" lines; the s18 blind-window cap at 1:100 (10k × f² = 2.5k
> px² while the tree strip is 4.6k); promotion of an under-share wall pen by
> doorways on pen-independent material (s03's 0.73 grey); the merged
> landing's stair coverage and top-left notch on s01 (an open-arrowhead
> stair recogniser); same-line tail material for s17 door_0016;
> phase-invariant plug profiles; the dash-row text-mask join; the fallback
> in-wall gate on tail-less plugs; the recess class (s11's party-wall box is
> the neighbour's chimney breast); Gap D of
> `docs/hatch-cell-chords-handoff.md`; a jamb-scale floor for lining rings;
> the lattice knife-edges; interior rings in the exported room polygon;
> s18's and s14's glyph-outline fill rings.
>
> Rules for the whole run: do not commit (the user commits); do not edit
> `tests/ground_truth/*.json` or `fixtures/MANIFEST.json` without an explicit
> go for that specific entry; never revert s01's truth scale (1:92.2); never
> `git stash` (in zsh an unquoted `$VAR` does NOT word-split — pipe file lists
> through `xargs`; `echo =====` is a command lookup in zsh, quote it; a glob
> like `--include=*.py` must be quoted); macOS has no `timeout`; python is
> not on the shell path — use `.venv/bin/python` with an ABSOLUTE path in
> background commands (the cwd resets); a background job imports the tree at
> launch, so never edit a constant while one is running; the venv lacks
> InquirerPy (tools/review.py is the user's to run); s02 at f = 1.0 must not
> change (entity set AND polygons), and every s01 change is reported as a
> decision with its LOST lines named; probe with the FULL wall material and
> the room stage's real barrier rules, never an approximation (a tap on
> `_free_space_components` reads detect_rooms' locals off
> `sys._getframe(1)` — `face_lines`, `cap_lines`, `door_barriers`,
> `wall_segments`, `wall_material` — without editing the stage); census the
> rule AS IMPLEMENTED (with/without it on the pipeline's exact inputs; a
> synthetic fixture that passes on the unmodified tree does not bite — two
> of step 15's three attempts did, through `_snap_intersections` reach and
> the far-side rule demoting an unpaired partner face); scratch scripts that
> render pictures do so under `__main__` only and are kept under
> `tools/census_scratch/step16/`; PNG crops go under
> `docs/w-gate-iter3-checkpoints/` and must never show a street address or
> planning-portal id (s02's title block carries one — never crop it); commit
> messages carry no Co-Authored-By or session trailer. End every report with
> the numbers: lost, returned FPs, new REVIEW lines with your verdicts, net
> phantom delta, and what is next.
