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
