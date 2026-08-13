# Scale Normalization — Findings & Decision Log

**Started:** 2026-08-12 (brainstorm for the walls/rooms branch).
**Read this first** if you are working on scale-awareness for ANY detector
(windows, labels, schedules are still scale-blind — see §6; doors are DONE,
`feat/scale-aware-door-gates`, §4c/§4d). The design that consumes these
findings: `docs/superpowers/specs/2026-08-12-scale-aware-wall-room-gates-design.md`
(walls/rooms) and `docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md`
(doors).

## 1. The premise, verified

All geometric detection constants are absolute 150-DPI pixel values tuned on
the 1:50 reference sheets (s01, s02). At 150 DPI, 1px ≈ 0.1693mm of paper;
real-world mm per px = 0.1693 × denominator:

| Scale | mm/px | 300mm wall | 100mm leaf | 838mm door leaf |
|---|---|---|---|---|
| 1:50 | 8.5 | 35.4px | 11.8px | 49.5px |
| 1:100 | 16.9 | 17.7px | 5.9px | 24.8px |

Detection never sees the resolved scale: `resolve_page_scales` feeds only
`summary.json`/console (verified in `pipeline.py` — `page_scales` is not
passed to `run_heuristics`).

**Nuance that shapes everything:** only *world-space* constants should
scale. *Paper-space* ink (pen widths, dimension ticks, arrowheads) is drawn
at fixed paper size at any scale, and *dimensionless* gates (ratios, angles,
counts) are invariant. Blanket-scaling everything would be a bug — e.g.
scaling `WALL_MIN_STROKE_WIDTH_PX` would misclassify pens on 1:100 sheets.

## 2. Corpus scale census (measured 2026-08-12)

Method: extraction + cached region classification + `resolve_page_scales`
per sheet, no detection, no Gemini calls (script pattern: see the survey
section of the brainstorm; re-runnable in ~1min). Floor-plan regions only.

| Sheet | Floor-plan scale(s) | Source | Notes |
|---|---|---|---|
| s01 | 1:50 (both regions) | user (stored) | primary reference |
| s02 | 1:50 (page-level) | text ("scale bar - metric - 1:50@A3") | primary reference; fp region count 0 → page_scale path |
| s03 | 1:100 ×2 + 1:50 ×1 | viewport | **mixed on one page** |
| s04 | 1:50 | viewport (raw 50.0007) | nominal snap matters |
| s05 | 1:100 | viewport | |
| s06 | 1:100 | viewport | |
| s07 | 1:100 | viewport | |
| s08 | 1:50 | viewport | |
| s09 | — | — | no floor-plan regions |
| s10 | unresolved | | `SCALE_UNRESOLVED` |
| s11 | unresolved | | `SCALE_UNRESOLVED` |
| s12 | 1:100 | viewport | |
| s13 | ~1:136.4 | viewport | `SCALE_SOURCE_CONFLICT` — text says otherwise; viewport wins by design |
| s14 | 1:50 | text | |
| s15 | 1:50 | viewport | |
| s16 | unresolved | | `SCALE_UNRESOLVED` |
| s17 | 1:100 ×2 + 1:50 ×2 | viewport | **mixed on one page** |
| s18 | unresolved | | `SCALE_UNRESOLVED` |
| s19 | — | — | no floor-plan regions |
| s20 | unresolved | | `SCALE_MULTIPLE_UNBOUND` + `SCALE_UNRESOLVED` |

Bottom line: of 18 sheets reaching detection, 7 run at a non-1:50 scale the
constants weren't tuned for, 5 more are unknown.

## 3. Does scale mismatch explain the bad sheets? Partially.

False positives from committed ground truth vs resolved scale:

| Sheet | Scale | FPs | Sheet | Scale | FPs |
|---|---|---|---|---|---|
| s15 | **1:50** | **82** | s13 | ~1:136 | 6 |
| s12 | 1:100 | 22 | s16 | unresolved | 6 |
| s03 | mixed | 21 | s20 | unresolved | 6 |
| s17 | mixed | 18 | s08 | 1:50 | 3 |
| s18 | unresolved | 15 | s06 | 1:100 | 3 |

- **Consistent with scale mismatch:** s12/s03/s17 rank high. Mechanism
  example: at 1:100, a tile field's rungs are ~24px, under the 48px
  `WALL_LATTICE_MIN_RUNG_LEN_PX` floor → striped-field demotion stops firing
  → phantom walls.
- **Not the whole story:** the worst sheet, s15 (82 FPs), is 1:50.
- **Blind spot (important):** ground truth records only detections that were
  reviewed — false positives. Scale-shrink at 1:100 primarily predicts
  **misses** (features fall below px floors), and misses are invisible in
  this data because nothing was detected to review. Do not read the FP table
  as an upper bound on the scale problem.

### Post-scaling sweep outcome (2026-08-12)

`tools/fetch_fixtures.py`: 20 present, 0 missing, 0 mismatched, 0 untracked —
corpus intact. `tools/regress.py` on `feat/scale-aware-wall-room-gates`
(commits through `e86d3ab`): **exit 1**.

**Cross-check against this table's own baseline FP counts (measured before
any scale code existed) resolves most of the exit-1 noise as pre-existing,
not branch-caused.** Re-running today's sweep's `FALSE POSITIVE RETURNED`
tallies against the row above landed exact or near-exact on 7 of 9 sheets:
s15 82=82, s03 21=21, s17 18=18, s18 15=15, s16 6=6, s20 6=6, s08 3=3. A
`RETURNED` false positive by construction matches an entry already sitting
in that sheet's `ground_truth` `false_positives` list (§ground-truth-format),
so reproducing the *exact* pre-branch count is direct evidence the detector
still emits the same old, already-known-wrong candidates — not new ones this
branch introduced. Do not read this exit code as this branch failing; read
it as the corpus's already-documented FP debt (per this section) still
being unpaid, which is exactly the state the FP table above predicts.

| Sheet | Scale tier | REVIEW | LOST | RETURNED FP | Read |
|---|---|---|---|---|---|
| s01 | 1:50 | 0 | 0 | 0 | clean |
| s02 | 1:50 | 1 (schedule) | 1 (schedule) | 0 | **surprise, see below** |
| s03 | mixed (0.5) | 5 | 0 | 21 | FP count matches pre-branch baseline exactly; REVIEW expected |
| s04 | 1:50 | 1 (window) | 0 | 2 (room) | **surprise, see below** |
| s05 | 1:100 | 0 | 0 | 0 | clean |
| s06 | 1:100 | 7 | 1 (room) | 2 (room) | REVIEW expected; LOST is new, see below |
| s07 | 1:100 | 1 | 0 | 0 | clean, REVIEW expected |
| s08 | 1:50 | 0 | 0 | 3 | FP count matches pre-branch baseline exactly |
| s09 | — (no floor plan) | unlabeled | — | — | n/a |
| s10 | unresolved | 0 | 0 | 1 (room) | **surprise, minor, see below** |
| s11 | unresolved | 2 (door) | 0 | 3 (room) | **surprise, see below** |
| s12 | 1:100 | 0 | 1 (room) | 21 | FP count ≈ pre-branch (22); LOST is new, see below |
| s13 | ~1:136.4 | 9 | 4 (1 door, 3 room) | 0 | REVIEW + LOST both expected at this scale |
| s14 | 1:50 | 0 | 0 | 2 (window+room) | **surprise, minor, see below** |
| s15 | 1:50 | 0 | 0 | 82 | FP count matches pre-branch baseline exactly |
| s16 | unresolved | 14 | 0 | 6 | FP count matches pre-branch baseline exactly; REVIEW is a surprise |
| s17 | mixed (0.5) | 5 | 0 | 18 | FP count matches pre-branch baseline exactly; REVIEW expected |
| s18 | unresolved | 0 | 0 | 15 | FP count matches pre-branch baseline exactly |
| s19 | — (no floor plan) | unlabeled | — | — | n/a |
| s20 | unresolved | 0 | 0 | 6 | FP count matches pre-branch baseline exactly |

**Identity-tier surprises (1:50 / unresolved sheets — factor 1.0 end-to-end,
expected byte-identical to pre-branch), not yet bisected per the standing
checkpoint rule (one fix, one sweep, then ask):**

- **s02 — LOST schedule, `REGION_CACHE_MISS` warning.** The sweep's own
  message: "classification fell back to the whole page; detection scope
  differs from the labeled run." `gemini/region_cache.py::cache_key` hashes
  page content + region geometry (`page_content_hash` /
  `region_geometry_hash`); neither `layout/` nor `gemini/region_cache.py` is
  touched on this branch (diff stat: only `detection/orchestrator.py`,
  `detection/rooms.py`, `detection/walls.py`, `pipeline.py`, `scale/factor.py`
  + tests + docs). A stale cache entry does exist on disk
  (`fixtures/sheets/.regions_cache/s02-working-drawing-wd03_p01_*.json`,
  dated Jul 30) whose key no longer matches — i.e. something upstream of
  this branch (plausibly the already-merged `feat/scale-extraction`, which
  touched extraction) changed `page_content_hash`'s inputs and invalidated
  every cached classification project-wide. Likely **not** caused by this
  branch, but it does mean s02 did not actually exercise a byte-identical
  region-filtered detection pass this sweep — re-verify after a
  `--refresh-regions` run repopulates the cache.
- **s04 — 2 RETURNED room FPs, 1 REVIEW window**, not present in this
  section's original pre-branch top-10 table (small enough to have been
  omitted, or genuinely new).
- **s06 — 1 LOST room** (1:100 tier, so within this branch's direct scope —
  a room the scale-aware gates now draw differently enough to drop below
  IoU 0.5 against the confirmed polygon, with no compensating REVIEW room at
  the same location).
- **s11 — 2 REVIEW new doors, 3 RETURNED room FPs**, unresolved tier
  (factor 1.0). New door candidates appearing with no wall/room gate change
  in effect at f=1.0 is the more notable identity flag — plausibly a
  downstream cross-validation effect if the (supposedly identical) room
  network output isn't byte-identical at f=1.0, but unverified.
- **s12 — 1 LOST room** on top of the near-exact 21/22 pre-branch FP count
  (1:100 tier, in-scope like s06).
- **s14 — 2 RETURNED FPs** (window + room), not in the original top-10
  table.

**Baseline-worktree verification (2026-08-12, same day):** every
identity-tier surprise above was re-run on a throwaway worktree of the
branch point (`b0e705a`, pre-scale-code) with the same corpus, venv and
caches. Verdicts (full line-by-line comparison:
`docs/scale-baseline-comparison-2026-08-12.md`):

- **s02, s04, s14, s11 — identity HELD.** All four reproduce their LOST /
  RETURNED / REVIEW lines byte-for-byte on the pre-branch baseline,
  including s02's stale-region-cache schedule loss and s11's 2 REVIEW
  doors. They are pre-existing corpus debt, invisible until this sweep only
  because the last full sweep predates the scale-extraction merge.
- **s06, s12 — the LOST rooms are scale-induced (NEW),** confirmed absent
  on baseline. Each comes WITH an improvement on the same sheet: one
  pre-existing room FP vanished on s06 (569,402) and one on s12 (342,378) —
  the predicted phantom-wall payoff. Whether each lost room reappears as a
  differently-drawn REVIEW room or is a true miss is the user's verdict at
  review time.

**Not a surprise, expected:** s13's 4 LOST + 9 REVIEW (largest rescale in
the corpus, ~0.37×) and s03/s06/s07/s17's REVIEW lines (1:100/mixed tiers,
scale-aware gates now active).

**Review images** (per the sweep's own `images:` lines) —
`outputs/regress/<slug>/<timestamp>/pages/page_NN/review_<type>.png`, e.g.
`outputs/regress/s03/2026-08-12_13-16-13/pages/page_01/review_window.png`,
`.../s06/2026-08-12_13-16-21/pages/page_01/review_room.png`,
`.../s07/2026-08-12_13-16-28/.../review_room.png`,
`.../s11/2026-08-12_13-16-34/.../review_door.png`,
`.../s13/2026-08-12_13-16-52/.../review_room.png`,
`.../s16/2026-08-12_13-17-34/.../review_room.png`,
`.../s17/2026-08-12_13-17-57/.../review_window.png`. Verdicts for the
expected-change sheets: `python tools/review.py s05 s07 s12 s03 s17 s13 s06`.

**Status:** the identity-tier surprises above are unresolved and block
treating this sweep as clean; per the task-6 hard rule they are reported,
not fixed, here. The controller should bisect s02/s04/s06/s11/s12/s14
(one fix, one sweep, then ask) before the expected-change sheets go to the
user for review.

### Re-sweep after the bridging fix (2026-08-12)

One Critical fix landed since the table above: `_bridge_white_runs` (called
from `detect_rooms`) now receives scaled `WallGates` instead of silently
falling back to its unscaled default (`415d4b1`, doc note §4a "(b)";
confirmed `e86d3ab` — the commit the table above was recorded at — is an
ancestor of `415d4b1` via `git merge-base --is-ancestor`). Re-ran
`python tools/regress.py` at `fb8f418`: **exit 1** (same as before — expected,
this corpus carries pre-existing FP/REVIEW debt per §3 above, not a new
failure).

**Result: every one of the 20 sheets reproduced its REVIEW/LOST/RETURNED
lines byte-for-byte against the table above** — same counts, same
coordinates, checked line-by-line, not just totals. This holds both for the
11 factor-1.0 sheets (identity expected and confirmed unchanged) **and** for
all 7 scale-affected sheets (s03, s05, s06, s07, s12, s13, s17) that the
bridging fix could plausibly have changed. The fix landed with zero
observable effect on this corpus's regression output — not a red flag (a
correctness fix can be inert on a given corpus if the buggy path wasn't
exercised differently by these 20 sheets' geometry), but it means this sweep
gives no positive evidence the fix changed behavior anywhere, only that it
introduced no regression. Full per-sheet comparison table and reasoning:
`.superpowers/sdd/2026-08-12-scale-aware-wall-room-gates/resweep-report.md`.

**Review images** (fresh timestamped paths this run, same pages as before):
`outputs/regress/s03/2026-08-12_13-48-35/pages/page_01/review_window.png`,
`.../s06/2026-08-12_13-48-42/.../review_room.png`,
`.../s07/2026-08-12_13-48-50/.../review_room.png`,
`.../s11/2026-08-12_13-48-56/.../review_door.png`,
`.../s13/2026-08-12_13-49-13/.../review_room.png`,
`.../s16/2026-08-12_13-49-54/.../review_room.png`,
`.../s17/2026-08-12_13-50-17/.../review_window.png`. Sheets with unreviewed
detections this sweep: s02, s03, s04, s06, s07, s11, s13, s16, s17 —

```
python tools/review.py s02 s03 s04 s06 s07 s11 s13 s16 s17
```

**Status unchanged:** the identity-tier surprises (s02/s04/s06/s11/s12/s14)
are still unresolved and still block treating this sweep as clean; this
re-sweep neither fixes nor worsens them, and no algorithm changes were made
to investigate them (out of scope for this pass). The controller's
bisect-then-ask plan above still stands.

## 4. Constant classification table

Classes: **W** = world-space (× f; areas × f²), **P** = paper-space
(unchanged), **D** = dimensionless (unchanged). (Formerly also **U** =
uncertain, pending measurement; all U rows were resolved 2026-08-12 — see
§4b — and none remain.) `f = 50 / nominal_denominator` (1:100 → 0.5).

Status: **frozen** — set during the 2026-08-12 brainstorm from each
constant's documented rationale, then every U entry resolved to W or P by
corpus measurement or explicit conservative-default rule (§4b). Tasks 3–4
implement this table verbatim; they do not re-derive classes. A future
branch may still revisit a P verdict flagged "revisit if 1:100 sweep shows
artifacts" — that is a new decision, not a reopening of this table.

### detection/walls.py

| Constant | Class | Rationale |
|---|---|---|
| WALL_MIN_STROKE_WIDTH_PX | P | pen width |
| WALL_FACE_MIN_LEN_PX | W | wall piece between openings |
| WALL_FACE_MERGE_GAP_PX | P | drafting artifact gap; note: must stay < scaled smallest opening |
| WALL_MIN_THICKNESS_PX | W | thinnest partition; floor scaled value at 1px (design §4) |
| WALL_MAX_THICKNESS_PX | W | heavy blockwork band (~305mm at 1:50) |
| WALL_THICK_MATERIAL_MAX_PX | W | 400mm band at 1:50 |
| WALL_PARALLEL_ANGLE_TOL | D | angle |
| WALL_BAND_MIN_ASPECT | D | ratio |
| WALL_PAIR_MIN_OVERLAP_PX | W | coincidence floor on face overlap |
| WALL_CENTERLINE_MERGE_GAP_PX | P | measured 2026-08-12: no corpus signal (small tolerance, not a hatch/geometry quantity); conservative default, unchanged behavior at every f; revisit if 1:100 sweep shows artifacts |
| WALL_JUNCTION_SNAP_PX | P | measured 2026-08-12: no corpus signal; conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| WALL_JUNCTION_MIN_ANGLE_DEG | D | angle |
| WALL_NETWORK_MIN_SEGMENTS | D | count |
| WALL_LIGHT_PEN_MIN_CHANNEL | P | color |
| WALL_DIM_TICK_MIN/MAX_LEN_PX, _END_TOL_PX, _STRADDLE_MIN_PX | P | dimension ticks are annotation |
| WALL_DIM_TICK_ANGLE_MIN/MAX | D | angles |
| WALL_BACKGROUND_FILL_MIN | P | color |
| WALL_FILL_CLASS_MIN_INK_PX | W | drawn ring length is world geometry |
| WALL_FILL_BLOCK_MAX_SIDE_PX | W | band-vs-block shape of built fills |
| WALL_MARKER_MAX_SIDE_PX | P | leader/dimension arrowheads are ~2–4mm of paper |
| WALL_HATCH_MIN_SEGMENTS | D | count |
| WALL_HATCH_MIN_RATIO | D | ratio |
| WALL_HATCH_MAX_LEN_PX | W | measured 2026-08-12, revised after code review (§4b): length ratio ≈0.47–0.59 at every adequately-sampled angle band (per-sheet n≥95, well above the brief's n<50 caution), matching pitch's robust W verdict on the same strokes; initial 0.47–1.06 spread traced to small-sample noise in the two narrowest bands (deciding-sheet n as low as 227), not a real signal, and de-censoring the length cap (60px→150px) ruled out truncation bias as the cause — move into gates dataclass, × f. Scales together with WALL_LATTICE_MIN_RUNG_LEN_PX (both W, both 48px×f), preserving their current exact-equality relationship at every f instead of colliding |
| WALL_WEAK_STROKE_RATIO | D | pen ratio |
| WALL_WEAK_MIN_RUN_PX | W | partition run length |
| WALL_WEAK_MATERIAL_MIN_MARKS | D | count |
| WALL_WEAK_MATERIAL_MIN_SPAN | D | fraction |
| WALL_WEAK_MATERIAL_PER_100PX | W | measured 2026-08-12 (§4b): follows the WALL_HATCH_MAX_PITCH_PX verdict per the mark-spacing rule (mark spacing measured world-space, ratio ≈0.50–0.55) — but it is a DENSITY (marks per 100 paper-px of band length), so it scales **÷ f**, not × f: at f=0.5 world-spaced marks pack 2× tighter per paper-px, and the MINIMUM must rise to keep discrimination. Dimensional check against the measured separations: real partitions ≥4.8/100px and noise ≤2.6 at 1:50 → at 1:100 ≥9.6 vs ≤5.2; the unscaled gate (3) admits noise, ×f (1.5) is worse, ÷f (6) separates cleanly. (Direction corrected 2026-08-12 by the controller after Task 2 review — the original row said × f.) |
| WALL_WEAK_MATERIAL_EDGE_PX | P | pen-adjacent exclusion |
| WALL_WEAK_MATERIAL_ANGLE_MIN/MAX | D | angles |
| WALL_WEAK_CLAIM_MARGIN_PX | P | measured 2026-08-12: no corpus signal (small tolerance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| WALL_WEAK_CLAIM_OVERLAP_FRAC | D | fraction |
| WALL_LATTICE_MIN_RUNGS | D | count (5 keeps cavity party wall out) |
| WALL_LATTICE_PITCH_TOL_PX | P | measured 2026-08-12: no corpus signal (small tolerance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| WALL_LATTICE_MIN_RUNG_LEN_PX | W | 48px ≈ 406mm at 1:50; **key phantom-wall gate at 1:100** — updated 2026-08-12 (§4b): WALL_HATCH_MAX_LEN_PX is also W (both 48px × f), so at every f the two scale together and stay exactly equal, matching the 1:50 baseline relationship; no clamp risk, no collision, and the rung floor legitimately shrinks to ~24px at 1:100 so the design's predicted s12 phantom-wall fix (§3) is not neutralized |
| WALL_LATTICE_TOUCH_GAP_PX | P | measured 2026-08-12: no corpus signal (small tolerance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| WALL_LATTICE_OFFSET_TOL_PX | P | collinearity tolerance |
| WALL_LATTICE_PEN_TOL | P | pen |
| WALL_HATCH_MAX_PITCH_PX | W | measured 2026-08-12 (§4b): pitch ratio ≈0.50–0.55, robust across every angle-band width tried (0.500–0.551) — hatch pitch is world-space; move into gates dataclass, × f. This closes the gap with `WALL_LATTICE_MIN_RUNG_LEN_PX` at 1:100 (both shrink by f=0.5 together) rather than colliding |
| WALL_WHITE_TOUCH_TOL_PX | P | contact tolerance |
| WALL_WHITE_SPAN_MIN_FRAC | D | fraction |
| WALL_WHITE_TEXT_COVER_FRAC | D | fraction |
| WALL_JOINERY_BRIDGE_GAP_PX | W | open span between cavity segments (wardrobe runs) |
| WALL_JOINERY_BRIDGE_SLACK_PX | P | measured 2026-08-12: no corpus signal (small tolerance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| WALL_REDUNDANT_OFFSET_SLACK_PX | P | collapse tolerance |
| WALL_REDUNDANT_MIN_COVER | D | fraction |
| WALL_REDUNDANT_THICKNESS_SLACK_PX | P | measured 2026-08-12: no corpus signal (thickness-comparison slack, the 4px far-face gate); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| COLLINEAR_ANGLE_TOL | D | angle; used only by `_merge_collinear_segs` to decide two faces lie on the same infinite line |
| COLLINEAR_OFFSET_TOL | W | found 2026-08-12 during Task 3 TDD (not `WALL_`-prefixed, so it was missed by the original corpus census and this table — the audit only searched `WALL_`/`ROOM_`-prefixed names). Gates the perpendicular offset below which `_merge_collinear_segs` treats two parallel faces as pieces of the SAME drawn line and fuses them into one — the identical "is this the same wall face" judgment `WALL_MIN_THICKNESS_PX` makes for pairing, so it belongs in the same class. Left unscaled (4.0px) it collides with a shrunk-world wall's own face spacing: an 8px-at-1:50 wall band shrinks to 4px at f=0.5 — exactly the unscaled tolerance — and the brief's own `test_shrunk_world_reproduces_wall_network` caught it live, fusing the wall's two faces into one line with zero centerlines recoverable. Pre-existing independent of scale awareness: `WALL_MIN_THICKNESS_PX` (2.0) was already below `COLLINEAR_OFFSET_TOL` (4.0) at f=1.0, so any real ≤4px partition on an unscaled 1:50 sheet would already have silently fused; the corpus apparently never drew one thin enough to trigger it. Fixed by adding it as a `WallGates` field (× factor, exact same name), not a private per-function multiply — see `docs/superpowers/sdd/2026-08-12-scale-aware-wall-room-gates/task-3-report.md` for the TDD trace. **Action for Task 4/5:** grep rooms.py (and any other detector) for non-`WALL_`/`ROOM_`-prefixed px tolerances that feed the same kind of "same feature or different feature" geometric judgment — this table's census methodology missed COLLINEAR_OFFSET_TOL exactly this way and an analogous constant could hide there too. |

**(a) `_segment_bbox_distance` is not a `WALL_MAX_THICKNESS_PX` use site (fix-wave note, 2026-08-12).** The Task 3 plan table (`docs/superpowers/plans/2026-08-12-scale-aware-wall-room-gates.md:643`) listed `_segment_bbox_distance` (old line 794) as a `WALL_MAX_THICKNESS_PX` use site — that line was a comment inside `WallNetwork.near_bbox`, not inside `_segment_bbox_distance` itself. The function (`detection/walls.py`) carries no constants at all; its only caller is `WallNetwork.near_bbox`, and `near_bbox`'s only caller is `detection/postprocess.py`'s door/window cross-validation, gated by `CROSS_*` constants — a different constant family, out of this branch's scope. Recorded here so a future auditor doesn't re-chase it as an open Task 3/4 item.

**(b) A second COLLINEAR_OFFSET_TOL-shaped blind spot: default-`gates` parameters at cross-module call sites (fix-wave note, 2026-08-12).** The COLLINEAR_OFFSET_TOL row above documents one blind spot in the original census (a non-`WALL_`-prefixed constant, invisible to a bare-name grep for `WALL_`/`ROOM_`). The whole-branch review found a second, structurally different instance: `detection/rooms.py`'s `detect_rooms` called `detection/walls.py`'s `_bridge_white_runs` without a `gates=` argument, silently falling back to `_bridge_white_runs`'s `gates: WallGates = WALL_GATES_UNSCALED` default and running `WALL_JOINERY_BRIDGE_GAP_PX`-gated bridging unscaled on every sheet regardless of `scale_factor`. Grepping for the constant name found nothing wrong — the constant itself scales correctly inside `WallGates.at()`; the bug was entirely in a call site never passing the scaled gates object through. The audit for this class of bug is not a constant-name grep at all: it is grepping CALLS to gates-carrying `walls.py` helpers from outside `walls.py` (`grep -rn "_bridge_white_runs\|_rate_fill_classes\|..." detection/*.py tests/*.py`, per the fix-wave report) and checking each cross-module call site passes `gates=` explicitly. Fixed by building `WallGates.at(scale_factor)` in `detect_rooms` alongside `RoomGates.at(scale_factor)` and threading it through, and by making `_bridge_white_runs`'s `gates` parameter keyword-only and required (no default) — the only walls.py helper actually called from a different production module, so it is the only one where a missing `gates=` needed to become a hard TypeError rather than a silent unscaled fallback.

### detection/rooms.py

| Constant | Class | Rationale |
|---|---|---|
| ROOM_MIN_AREA_PX2 | W (× f²) | smallest closet |
| ROOM_MAX_PAGE_AREA_FRAC, ROOM_HOLE_AREA_FRAC_MAX | D | fractions |
| ROOM_WALL_DILATE_PX, ROOM_LINE_BARRIER_PX | P | pen-tied standoff; MUST remain equal to each other (barrier-standoff rule) |
| ROOM_BARRIER_STROKE_RATIO, ROOM_PAIRED_FACE_MIN_FRAC, ROOM_WALL_PEN_MIN_FRAC | D | ratios/fractions |
| ROOM_PLUG_MID_NEAR_PX | P | measured 2026-08-12: no corpus signal (hug distance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| ROOM_GAP_CLOSE_PX | P | measured 2026-08-12: no corpus signal; conservative default (§4b) — must stay < scaled thinnest doorway (design §4); revisit if 1:100 sweep shows artifacts |
| ROOM_EROSION_PX | P | measured 2026-08-12: no corpus signal (wall-sliver scale); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| ROOM_BORDER_TOL_PX, ROOM_CONTACT_TOL_PX, ROOM_MASS_TOUCH_TOL_PX | P | contact tolerances |
| ROOM_WALL_CONTACT_MIN, ROOM_MAJOR_MASS_FRAC | D | fractions |
| ROOM_SIMPLIFY_TOL_PX | P | sub-pen-width simplification |
| ROOM_OPENING_SEAL_PX | W | reach into jambs the arc stopped short of |
| ROOM_PLUG_NEAR_PX | P | measured 2026-08-12: no corpus signal (edge-hugs-material distance); conservative default (§4b); revisit if 1:100 sweep shows artifacts |
| ROOM_PLUG_SAMPLE_PX | P | numeric sampling resolution (finer relative sampling at small f is harmless) |
| ROOM_PLUG_ANCHOR_WIN_PX | W | "a jamb is jamb-sized" — jamb size is world-sized |
| ROOM_PLUG_HALF_WIDTH_PX | W | wall-band half-thickness |
| ROOM_PLUG_END/MID/FULL_COV_* | D | coverage fractions |
| ROOM_SLIDE_END_ASPECT_MIN | D | aspect |
| ROOM_BLIND_WINDOW_MAX_AREA_PX2 | W (× f²) | closet-scale area; margins re-checked at f=0.5 (real rooms ≥17k px² at 1:50 → ≥4.25k at 1:100 vs 10k×0.25=2.5k cap — holds) |
| ROOM_BASE_CONFIDENCE, *_BOOST, *_WEIGHT, *_MIN_CONFIDENCE, ROOM_BBOX_SEAL_MIN_CONFIDENCE | D | confidences |
| ROOM_PLUG_IN_WALL_FRAC, ROOM_FOLD_SPAN_TOL, ROOM_OPENING_TEXT_COVER_MAX | D | fractions |
| ROOM_FOLD_STACK_NEAR_PX, ROOM_FOLD_JAMB_MIN_LEN_PX | W | threshold depth / jamb-scale |
| ROOM_FOLD_GAP_ESCAPE_PX | P | ray-start construction offset |

## 4b. Measurements (2026-08-12)

**Question:** is hatch geometry (stroke length, pitch, mark density)
paper-space (same px on 1:50 and 1:100 sheets) or world-space (halved px on
1:100)? Measured on the corpus's five sheets with a resolved single scale
per page and enough hatch ink to be usable: s01, s02 (1:50) vs s05, s07, s12
(1:100). Script: `extraction.extractor.extract_page`, page 0 of each sheet
(all five are single-page PDFs), no detection/Gemini calls. Script lived at
`<scratchpad>/measure_hatch.py` (not committed — scratchpad only, per the
brief).

**Method.** `hatch_strokes()`: unfilled `l` items, length 3–60px, off-axis
angle (deviation from the nearest 90°) inside a band — the brief's starting
script used 20–70°. `pitches()`: group by 2°-wide angle bins, project stroke
midpoints onto the field normal, sort, keep consecutive gaps in (0.5, 20)px
as same-field pitch samples.

**Refinement made and why.** The angle histogram (5° bins of off-axis angle)
showed a dominant peak in the 45°±5° bin on **all five sheets** (e.g. s01:
1263/1507 strokes at the 45° bin; s07: 91/96) — the standard ANSI31 hatch
convention — with a long, thinner tail at other angles (angled walls,
leader/dimension diagonals, bay-window framing). The brief's literal 20–70°
band mixes that tail in, and per-sheet the tail's size varies independent of
scale, so it pollutes the length statistic differently sheet to sheet.
Reported below: (a) the literal brief script (20–70° band, "primary"), and
(b) a sensitivity sweep over four progressively tighter hatch-angle bands to
check whether the ratio verdict is stable.

**Per-sheet raw numbers, primary run (20–70° band, brief's literal script):**

| Sheet | Scale | n strokes | n pitch samples | median length (px) | median pitch (px) |
|---|---|---|---|---|---|
| s01 | 1:50 | 1507 | 946 | 12.37 | 2.83 |
| s02 | 1:50 | 923 | 189 | 12.97 | 6.37 |
| s05 | 1:100 | 1417 | 830 | 14.50 | 2.30 |
| s07 | 1:100 | 96 | 21 | 7.42 | 1.46 |
| s12 | 1:100 | 616 | 234 | 6.37 | 4.42 |

Group medians (median of the two/three per-sheet medians, per the brief):
1:50 length = 12.67px, 1:100 length = 7.42px → **length ratio = 0.586**.
1:50 pitch = 4.60px, 1:100 pitch = 2.30px → **pitch ratio = 0.500**.

s07 is thin (n pitch samples = 21, below the "n < 50 → note it" bar in the
brief's practical notes) — it is the low-ink sheet of the three 1:100
references; s05 and s12 both clear 200+ pitch samples and carry the group
median.

**Sensitivity sweep (off-axis angle-band half-width around the 45° hatch
peak), pitch ratio vs. length ratio:**

| Band (off-axis°) | Pitch ratio | Length ratio |
|---|---|---|
| 20–70 (brief literal) | 0.500 | 0.586 |
| 35–55 | 0.525 | 0.472 |
| 38–52 | 0.551 | 0.472 |
| 40–50 | 0.511 | 0.878 |
| 42–48 | 0.506 | 1.056 |

**Fix (2026-08-12, code review): length re-measured with censoring removed.**
Code review flagged that the shared `3.0 <= length <= 60.0` filter in
`hatch_strokes()` right-truncates the sample, and if world-space diagonal
ink near/above 60px is disproportionately excluded at 1:50 vs 1:100 that
would bias the length ratio upward toward false paper-space readings. Also
flagged: length and pitch are measured off the SAME drawn hatch strokes, so
it would be physically odd for them to land in different scale classes —
the more parsimonious read of instability is a noisy proxy, not a real
paper/world split. Re-ran with the length cap raised to 150px (`3.0 <=
length <= 150.0`, well above every sheet's measured tail — the true max
across all five sheets is 184.6px on s02, but that is itself an
outlier reaching only 7% of s02's population above 60px; 150px comfortably
covers the bulk of the tail without re-admitting unrelated long diagonal
wall/leader ink) and pitch computation unchanged:

| Band (off-axis°) | Pitch ratio (len≤150) | Length ratio (len≤60, original) | Length ratio (len≤150, de-censored) |
|---|---|---|---|
| 20–70 (brief literal) | 0.520 | 0.586 | 0.584 |
| 35–55 | 0.608 | 0.472 | 0.472 |
| 38–52 | 0.611 | 0.472 | 0.467 |
| 40–50 | 0.570 | 0.878 | 0.878 |
| 42–48 | 0.565 | 1.056 | 1.056 |

De-censoring moved the length ratio by ≤0.005 in every band tested — the
censoring hypothesis is empirically **not** the source of instability (the
>60px tail is dominated by non-45° ink that the angle filter already
excludes at narrow bands, and is a negligible fraction of the population at
wide bands: s01/s05 <0.3% over 60px, s07 0%, s12 1.8%, s02 7%). What
changes the ratio is the angle-band width itself, and per-sheet sample
count explains why: s12's own median length is unstable as the band
narrows (n=627→276→227, median 6.37px→13.97px→24.93px) purely from losing
samples, and because the three 1:100 sheets' medians (s05, s07, s12) are
themselves close together, this instability flips *which sheet* the
group's median-of-three lands on — at the two broad/medium bands (20–70,
35–55, 38–52) the group median is s07's own value (7.42px, the sheet's
thinnest and most stable), landing the ratio at 0.47–0.59; at the two
narrowest bands (40–50, 42–48) s12's inflated small-sample median (13.97,
24.93) or s05's (16.79) takes over, landing the ratio at 0.88–1.06 on n as
low as 227. That is aggregation noise from small samples at extreme
band widths, not a competing physical signal — and unlike pitch (robustly
W, 0.50–0.61, in every band including the narrow ones, on the *same*
underlying stroke sets), length only leaves the world-space range when the
per-sheet sample collapses. Taking the three bands with adequate sample
depth (per-sheet n across s01/s02/s05/s07/s12 — 20–70: 96–1508; 35–55:
95–1359; 38–52: 95–1331 — every sheet still clears the brief's n<50
caution line) as the trustworthy reads, length ratio is consistently ≤0.65
(0.584, 0.472,
0.467) — **world-space**, matching pitch. The two narrow bands are excluded
from the verdict as sample-starved (n≤276 for the deciding sheet), not
because they disagree with the desired answer.

**Sanity anchor.** CLAUDE.md/tuning-guide era measurement: hatch pitch
~4.05/4.07px on s01/s02 (measured against the production `_scan_striped_runs`
algorithm, not this proxy). This script's s01/s02 pitch medians (2.73–2.83,
5.35–6.37 across bands) are the right order of magnitude but not an exact
match, as expected — different measurement method (any diagonal stroke
proxy vs. the production paired-face striped-run scan) — consistent with,
not a substitute for, the historical number.

**Verdicts:**

- **Pitch is robust**: ratio stays in a tight 0.50–0.55 band across every
  angle-band width tried, always well under the ≤0.65 world-space threshold.
  `WALL_HATCH_MAX_PITCH_PX` → **W** (world-space). `WALL_WEAK_MATERIAL_PER_100PX`
  follows by the brief's explicit rule (mark spacing is the load-bearing
  quantity in a per-band-px density) → **W**.
- **Length is world-space**, revised after the de-censoring fix above. The
  raw ratio range (0.47–1.06) looked noisy, but de-censoring ruled out the
  originally-suspected cause (right-truncation bias) and traced the
  remaining spread to small-sample instability in the two narrowest angle
  bands (s12's own median swings 6.37px→24.93px as its sample shrinks from
  627 to 227). At every band with an adequate sample (20–70, 35–55, 38–52;
  n≥227, mostly n>300), the ratio is consistently ≤0.65 (0.584, 0.472,
  0.467), matching pitch's robust W verdict on the *same* underlying hatch
  strokes — the parsimonious read is one physical signal (CAD hatch
  patterns typically scale their stroke length and pitch together with plot
  scale), not two. `WALL_HATCH_MAX_LEN_PX` → **W** (world-space; move into
  gates dataclass, × f). This also resolves the ordering concern raised in
  review: `WALL_LATTICE_MIN_RUNG_LEN_PX` (also W, 48px × f) and
  `WALL_HATCH_MAX_LEN_PX` (48px × f) now scale by the identical factor at
  every f, so their relationship at 1:50 (currently exactly equal, 48.0 ==
  48.0) is preserved unchanged at every scale — no clamp, no collision.
  Had `WALL_HATCH_MAX_LEN_PX` stayed **P** (48px, unscaled) while
  `WALL_LATTICE_MIN_RUNG_LEN_PX` scaled to 48×f, the required ordering
  `48f > 48` would be false for every f < 1: at 1:100 (f=0.5) the rung
  floor's own scaled value (24px) sits *below* the unscaled hatch cap
  (48px), so a gates constructor enforcing the ordering invariant would
  have to clamp the rung floor up to ~49px at every 1:100-and-smaller
  sheet — well above the ~24px the design's s12 phantom-wall fix (§3, the
  "tile field's rungs are ~24px, under the 48px floor" mechanism) requires
  to actually fire. The W verdict avoids that outcome entirely rather than
  relying on a clamp to paper over it.

**Remaining small-tolerance U rows** (`WALL_CENTERLINE_MERGE_GAP_PX`,
`WALL_JUNCTION_SNAP_PX`, `WALL_WEAK_CLAIM_MARGIN_PX`,
`WALL_LATTICE_PITCH_TOL_PX`, `WALL_LATTICE_TOUCH_GAP_PX`,
`WALL_JOINERY_BRIDGE_SLACK_PX`, `WALL_REDUNDANT_THICKNESS_SLACK_PX`,
`ROOM_PLUG_MID_NEAR_PX`, `ROOM_PLUG_NEAR_PX`, `ROOM_GAP_CLOSE_PX`,
`ROOM_EROSION_PX`) have no corpus signal to measure — they are dedupe/
tolerance/slack constants, not geometry with a paper-vs-world reading — and
are frozen **P** by the brief's Step 3 rule: conservative default, unchanged
behavior at every factor, revisit if the 1:100 sweep shows artifacts.

## 4c. Measurement-harness traps (2026-08-13)

**The whole-page-vs-region-filtered failure.** The doors branch's first
measurement pass used a side harness that called `run_heuristics` directly on
raw whole-page `PageData`, instead of `resolve_page_regions(...).detection_page_data`
— the region-filtered path the real pipeline (`pipeline.run_extract`) actually
runs. On s11 the page also carries a location plan, a block plan and
elevations; a wall network built over that extra ink is not the network the
real pipeline produces. The unfiltered network flipped `wall_context` to
`no_wall` for three `single_line_leaf` doors, `CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY`
(0.15) then dropped their confidence 0.67 → 0.52 — under the 0.55 offline
floor — and the harness reported a non-existent **"3 lost confirmed doors on
main."** `tools/regress.py --sheet s11` says **13/13**: no door was lost at all.

**Rule adopted: any side harness must reproduce `tools/regress.py --sheet
<slug>`'s counts before its numbers are trusted — the sweep is the arbiter,**
never a bespoke script's own detection pass, however faithful that script
believes itself to be to "the pipeline." `harness.py` (the doors branch's
measurement tool) carries a self-check against five sheets' known sweep
counts for exactly this reason. This is the doors-branch instance of the same
discipline §4c's sibling findings already establish for walls/rooms
(per-region detection degrading room statistics, §6 "Per-scale-group
detection") and for Gemini classification caching (§3's `REGION_CACHE_MISS`
surprises) — a measurement that skips a pipeline stage is not measuring the
pipeline, and the failure mode is silent: the harness's output still looks
like a normal, plausible regression report.

## 4d. Door constant classification table (frozen 2026-08-13)

Companion to §4's wall/room table, same method: classes **W** (world-space,
× f; areas × f²), **P** (paper-space, unchanged), **D** (dimensionless,
unchanged). `f = 50 / nominal_denominator`. Status: **frozen** — set during
the 2026-08-12 door-gates design from each constant's rationale and measured
where cited; a future branch may still revisit a P verdict flagged "revisit
if ..." — that is a new decision, not a reopening of this table. Full
citations and derivations: `docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md`
§§Evidence base, Design/4.

**Arithmetic check, so the table is provably exhaustive:** 103 `DOOR_*`
constants (including `_DOOR_HU_TEMPLATE_VALUES`, non-numeric, and excluding
the derived `DOOR_GATES_UNSCALED` singleton) = 33 px-valued (21 W + 12 P) +
70 D. The 21 W constants are 19 extents/reaches + 2 panel-thickness (the
`DoorGates` dataclass's 21 fields, one-to-one). Plus 6 door-side `CROSS_*`
constants in `detection/postprocess.py` (all W, additional to the 103,
mirroring `CrossGates`'s 6 fields).

**Key measurements this table rests on** (full derivation in the design
spec):

- **Door symbol extent is world-space**: median-of-medians bbox max-side
  89.4px at 1:50 vs 44.3px at 1:100, ratio **0.496 ≈ f**. This is the premise
  the whole branch is built on (design §Evidence base/1) and is what
  `DOOR_MIN_SIZE_PX`/`DOOR_MAX_SIZE_PX` scale on.
- **Drawn leaf-panel thickness (leaf ↔ companion perpendicular separation) is
  paper-space**: 1.69px at 1:50 vs 2.63px at 1:100, ratio **1.56** — ink
  separations do NOT shrink with scale; draftsmen keep line pairs legible on
  paper regardless of drawing scale. This is `DOOR_LEAF_COMPANION_PERP_PX`'s
  and `DOOR_FOLD_LEAF_LINE_SEP_{MIN,MAX}_PX`'s P verdict, and scaling them
  zeroes s06 (0/2 confirmed doors) on the real corpus — decisive negative
  evidence for the P class, not just an absence of positive W evidence.
- **Drawn slide-panel thickness is the weakest row**: ratio 1.03 (7.83px at
  1:50 vs a **bimodal** 1:100 population — s12 2.13px, s11 8.06px, s16
  8.25px), and the shrunk-world evidence is circular for a drawn-thickness
  gate (the transform halves panel thickness by construction, so "scaling
  recovers the door" restates the assumption rather than testing it).
  Resolved **W** on an independent argument: converted to millimetres, slide
  panels measure 7.83px at 1:50 ≈ **66mm** — a real panel-plus-frame
  thickness — while leaf-companion separations measure 2.88px ≈ 24mm (s01)
  and 0.50px ≈ 4mm (s02), not a buildable leaf, i.e. symbolic; and the 1:100
  leaf separations (2.62–3.25px ≈ 44–55mm) read *larger* in mm than the 1:50
  ones, the signature of a **minimum drawn separation** (a paper floor), not
  a built dimension. `DOOR_SLIDE_PANEL_{MIN,MAX}_THICKNESS_PX` → **W**, with
  the ambiguity recorded: `MIN`-only, `MAX`-only and both scaled produce
  *identical* deltas on every one of the seven 1:100 sheets (this corpus
  cannot discriminate the two halves), and the concrete revisit trigger is
  **shower screens or glazing strips appearing as sliding doors on a 1:100
  sheet** (the constant's own tuning rationale, "thinner is a shower screen,"
  is itself a drawn separation subject to the same paper-floor risk as the P
  constants above) — not a miss.
- **`CROSS_*` needed-reach, re-derived by distribution, not survival count.**
  For every confirmed door, the smallest `expand_px` at which
  `WallNetwork.near_bbox` turns True, on each sheet's real network: p90
  reach 9.64px at 1:50 vs 0.78px at 1:100 (ratio 0.081 — scales), max 8.12px
  on any 1:100 sheet. The scaled `CROSS_WALL_EXPAND_PX` gate at f=0.5 is
  10.0px — 1.88px of headroom over the worst 1:100 sheet's actual need. This
  reversed an earlier conclusion that classified `CROSS_*` as conservative-P
  from door-survival counts on the broken §4c harness — void twice over
  (wrong numbers, and the wrong method: classify by what a constant
  *measures*, then measure its distribution, never by which setting
  happened to keep more doors alive on one sheet).
- **The shrunk-world transform is faithful for extents and unfaithful for
  ink separations.** A plain × 0.5 coordinate shrink halves *everything*,
  including drawn separations that real 1:100 exports hold at their paper
  value. s01's four residual shrunk-world misses (after `W + panel`
  scaling) were diagnosed individually and **all four rest on a separation
  gate** — three `single_line_leaf` doors on the leaf-companion separation
  plus the `sliding`/`parked_leaf` door — so they measure the synthetic
  transform's fidelity, not the classification; s02's full-identity 15/15
  plus "no extent-dependent door was lost on either sheet" is the honest
  read of that table. This is why the Testing section's fixtures shrink
  extents while holding separations at their paper values, rather than
  scaling the whole coordinate space.
- **Hidden-constant audit — no world-space literals found.** Every numeric
  literal in `detection/doors/*.py` outside `constants.py` was enumerated;
  most are dimensionless (angle bins, ratios, confidences, counts). Five are
  px-valued fit/snap slacks, all ≤4px, and behave as implicitly paper-space —
  the same class as the P-frozen snap tolerances in the table below, left
  unscaled: `folding.py:381,384,391,412,419` (4.0/3.0/2.0px slacks in the
  `open_v` corridor span/crosser scan), `sliding.py:369,460` (3.0px
  flank-straightness slack), `arcs.py:544` (2.0px polyline min-segment
  floor). Full derivation: design spec Design/4 (corrected 2026-08-13 — the
  original wording there overstated this as "clean … every numeric literal
  is dimensionless"; a future re-audit should check these sites, not skip
  them on that word).

### detection/doors/constants.py

| Constant | Class | Rationale |
|---|---|---|
| DOOR_BBOX_ASPECT_MIN | D | aspect ratio (Bezier bbox roughly-square gate); see §6's Bezier-aspect-gate deferred entry |
| DOOR_BBOX_ASPECT_MAX | D | aspect ratio; see §6 |
| DOOR_MIN_SIZE_PX | W | smallest door symbol extent — the load-bearing gate (0.496 ratio, above); floored at `max(1.0, ·×f)`, inert on the calibrated domain |
| DOOR_MAX_SIZE_PX | W | largest door symbol extent, same measurement |
| DOOR_SWING_LINE_DIST_PX | W | max px from arc corner to a nearby line endpoint — built distance between door parts |
| DOOR_LABEL_PATTERN | D | regex, not a numeric gate |
| DOOR_LABEL_SEARCH_RADIUS_PX | P | no corpus signal — only s02 carries door labels at all and every 1:100 sheet has zero; frozen P under the conservative-default rule (§4b) |
| DOOR_MIN_CONFIDENCE | D | confidence floor |
| DOOR_POLYLINE_MIN_SEGMENTS | D | count |
| DOOR_POLYLINE_MAX_SEGMENTS | D | count |
| DOOR_POLYLINE_MAX_SEG_PX | W | a tessellated arc segment is r·Δθ; r is world-space (0.496 ratio) and Δθ is a fixed exporter setting, so the segment scales with r. Caveat: holds for fixed-Δθ tessellation only — a fixed-chord-error exporter gives segment length ~√r instead (≈0.71 at f=0.5, not 0.5); unmeasurable on this corpus (every 1:100 sheet draws native Beziers, no polyline arcs to check against). Revisit if a polyline-arc sheet at another scale appears |
| DOOR_POLYLINE_ENDPOINT_TOL | P | the snap-key divisor bucketing polyline endpoints; scaling it costs a confirmed door |
| DOOR_POLYLINE_SPUR_MAX_SEGMENTS | D | count |
| DOOR_POLYLINE_CHAIN_DELTA_DEG | D | angle |
| DOOR_POLYLINE_CYCLE_MAX_SEGMENTS | D | count |
| DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS | D | count |
| DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS | D | count |
| DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX | P | "CAD-precise curve endpoints" — own comment states the rationale; CAD-precision snap tolerance |
| DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX | P | "machine-precise endpoints" — own comment states the rationale |
| DOOR_CURVE_CHAIN_MIN_CURVES | D | count |
| DOOR_LAYER_KEYWORDS | D | string list, not a numeric gate |
| DOOR_ASSEMBLY_CONNECT_TOL_PX | W | leaf-to-arc connection reach — built distance between assembly parts |
| DOOR_LEAF_RADIUS_RATIO_TOL | D | ratio tolerance |
| DOOR_FALLBACK_CONFIDENCE | D | confidence |
| DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX | P | CAD-precision snap tolerance |
| DOOR_LINEWORK_LEAF_MIN_SEGMENTS | D | count |
| DOOR_LINEWORK_LEAF_MAX_SEGMENTS | D | count |
| DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS | D | count |
| DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG | D | angle |
| DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG | D | angle |
| DOOR_THRESHOLD_ENDPOINT_TOL_PX | W | threshold endpoint ↔ leaf long-edge corner snap — built joinery reach, jamb-scale |
| DOOR_THRESHOLD_PARALLEL_TOL_DEG | D | angle |
| DOOR_THRESHOLD_CONFIDENCE_BOOST | D | confidence |
| DOOR_POLYLINE_MAX_ANGLE_BINS | D | count (angle bins) |
| DOOR_DOUBLE_LEAF_GAP_PX | W | max gap between leaf long-axis intervals — built double-door spacing |
| DOOR_DOUBLE_LEAF_OVERLAP_PX | W | max overlap on leaf long-axis intervals — same built quantity |
| DOOR_DOUBLE_LEAF_CENTER_TOL_PX | W | max offset between leaf long-axis centerlines — same |
| DOOR_V2_BRIDGE_BUFFER_PX | P | max dist from bridge line for an obstructing segment — a fit-tolerance construction offset |
| DOOR_V2_OPENING_CLEAR_BOOST | D | confidence |
| DOOR_V2_OPENING_OBSTRUCTED_PENALTY | D | confidence |
| DOOR_LEAF_LINE_ENDPOINT_TOL_PX | W | leaf-line-to-arc-endpoint snap (single-line-leaf topology) — built assembly reach |
| DOOR_LEAF_LINE_LENGTH_TOL | D | fraction tolerance (leaf length vs. arc radius match) |
| DOOR_LEAF_LINE_AXIS_TOL_DEG | D | angle |
| DOOR_LEAF_COMPANION_PERP_PX | P | measured (§2/§3 above): drawn leaf-companion separation, ratio 1.56 — decisive P; scaling zeroes s06 (0/2 confirmed doors) |
| DOOR_LEAF_COMPANION_OVERLAP | D | fraction |
| DOOR_ASSEMBLY_LINE_LEAF_BASE | D | confidence base |
| DOOR_ARC_FALLBACK_MAX | D | confidence cap |
| DOOR_HU_CANVAS_SIZE | D | raster canvas size — normalised shape-distance machinery, not a geometric gate |
| DOOR_HU_THRESHOLD_VERIFIED | D | normalised distance threshold |
| DOOR_HU_THRESHOLD_FAR | D | normalised distance threshold |
| DOOR_HU_VERIFIED_BOOST | D | confidence |
| DOOR_HU_PLAUSIBLE_BOOST | D | confidence |
| DOOR_HU_FAR_PENALTY | D | confidence |
| _DOOR_HU_TEMPLATE_VALUES | D | fixed Hu-moment template values, not a numeric gate |
| DOOR_LEAF_ASPECT_MIN | D | aspect |
| DOOR_SLIDE_PANEL_MIN_THICKNESS_PX | W | the weakest row in the table (measured above) — resolved W on the mm argument, not the (circular) shrunk-world test; revisit trigger: shower screens/glazing strips reading as sliding doors on a 1:100 sheet |
| DOOR_SLIDE_PANEL_MAX_THICKNESS_PX | W | same panel-thickness call as MIN; `MIN`-only/`MAX`-only/both scaled are indistinguishable on this corpus |
| DOOR_SLIDE_RECT_PARALLEL_TOL_DEG | D | angle |
| DOOR_SLIDE_RECT_PERP_TOL_DEG | D | angle |
| DOOR_SLIDE_PANEL_MERGE_TOL_PX | P | white ring + stroked qu of the SAME panel merge into one — CAD-precision merge tolerance |
| DOOR_SLIDE_AXIS_TOL_DEG | D | angle |
| DOOR_SLIDE_LENGTH_RATIO_TOL | D | ratio |
| DOOR_SLIDE_LATERAL_FACTOR | D | dimensionless multiplier of a panel dimension that itself scales |
| DOOR_SLIDE_OVERLAP_MIN_FRAC | D | fraction |
| DOOR_SLIDE_OVERLAP_MAX_FRAC | D | fraction |
| DOOR_SLIDE_FLANK_GAP_MIN_PX | W | flank-face-to-panel-edge gap — built pocket-cavity clearance |
| DOOR_SLIDE_FLANK_GAP_MAX_PX | W | same, upper bound |
| DOOR_SLIDE_FLANK_LINE_MIN_LEN_FRAC | D | fraction (× panel length) |
| DOOR_SLIDE_FLANK_SIDE_MIN_FRAC | D | fraction |
| DOOR_SLIDE_FLANK_MIN_FRAC | D | fraction |
| DOOR_SLIDE_FLANK_MAX_FRAC | D | fraction |
| DOOR_SLIDE_PROTRUSION_MIN_FRAC | D | fraction |
| DOOR_SLIDE_PROTRUSION_MAX_FRAC | D | fraction |
| DOOR_SLIDE_ZONE_WIDTH_FACTOR | D | dimensionless multiplier of panel half-thickness |
| DOOR_SLIDE_ZONE_MAX_CROSSERS | D | count |
| DOOR_SLIDE_ASSEMBLY_BASE | D | confidence base |
| DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX | P | "stroked rings snap at CAD precision" — own comment states the rationale |
| DOOR_SLIDE_PARK_GAP_MAX_PX | W | panel-to-band-face gap — built parked-leaf clearance |
| DOOR_SLIDE_PARK_FACE_COVER_MIN | D | fraction |
| DOOR_SLIDE_PARK_BAND_MIN_TH_PX | W | wall-band thickness — the same quantity `WALL_MIN_THICKNESS_PX` already carries as W in `WallGates` |
| DOOR_SLIDE_PARK_BAND_MAX_TH_PX | W | wall-band thickness, same quantity as `WALL_MAX_THICKNESS_PX` |
| DOOR_SLIDE_PARK_JAMB_TOL_PX | W | band-end vs panel-end alignment — built jamb-fit reach |
| DOOR_SLIDE_PARK_SPAN_RATIO_TOL | D | ratio tolerance (slide law: opening span ≈ panel length) |
| DOOR_FOLD_ANGLE_MIN_DEG | D | angle |
| DOOR_FOLD_ANGLE_MAX_DEG | D | angle |
| DOOR_FOLD_LENGTH_RATIO_TOL | D | ratio |
| DOOR_FOLD_HINGE_TOL_PX | P | corner-to-corner fit slack at a hinge where leaves share the ring vertex exactly — measured offsets ≤0.3px, a fit tolerance, not a built dimension |
| DOOR_FOLD_MIN_CHAIN_LEAVES | D | count |
| DOOR_FOLD_STACK_SPAN_RATIO_TOL | D | ratio tolerance |
| DOOR_FOLD_STACK_MIRROR_TOL_DEG | D | angle |
| DOOR_FOLD_STACK_PERP_EXTENT_MAX | D | dimensionless ratio (≤ ~one leaf length, expressed as a multiplier) |
| DOOR_FOLD_ASSEMBLY_BASE | D | confidence base |
| DOOR_FOLD_OPEN_ANGLE_MIN_DEG | D | angle |
| DOOR_FOLD_OPEN_ANGLE_MAX_DEG | D | angle |
| DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG | D | angle |
| DOOR_FOLD_LEAF_LINE_SEP_MIN_PX | P | measured (§2/§3 above): drawn double-line leaf separation is paper-space; scaling zeroes s06 (0/2). See the arithmetic correction below re: its relationship to `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX` |
| DOOR_FOLD_LEAF_LINE_SEP_MAX_PX | P | same measurement, upper bound; see the arithmetic correction below |
| DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN | D | ratio |
| DOOR_FOLD_LEAF_LINE_OVERLAP_MIN | D | fraction |
| DOOR_FOLD_JAMB_ANCHOR_TOL_PX | W | jamb line endpoint to leaf tip — built anchor reach |
| DOOR_FOLD_JAMB_LINE_MIN_LEN_PX | W | jamb-scale minimum length, matching `ROOM_FOLD_JAMB_MIN_LEN_PX`'s W verdict |
| DOOR_FOLD_JAMB_AXIS_TOL_DEG | D | angle |
| DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX | W | lateral half-width of the opening corridor searched for the far jamb — band-half-thickness scale |

### detection/postprocess.py (door-side CROSS_*)

| Constant | Class | Rationale |
|---|---|---|
| CROSS_WALL_EXPAND_PX | W | corridor reach beyond thickness/2 for `in_wall` containment — a door-to-wall-band distance; measured needed-reach p90 1:50 9.64px vs 1:100 0.78px (ratio 0.081, scales), max 8.12px on any 1:100 sheet; scaled gate at f=0.5 is 10.0px — 1.88px of headroom |
| CROSS_OPENING_ENDPOINT_TOL_PX | W | `opening_line` endpoint ↔ centerline snap — built reach |
| CROSS_WALL_RUNS_THROUGH_MARGIN_PX | W | centerline extends past both bbox ends by this — built reach |
| CROSS_WALL_RUNS_THROUGH_BAND_PX | W | face must lie within the bbox short extent + this — built reach |
| CROSS_DOOR_EXPAND_PX | W | dilate real door bboxes before testing window overlap — built veto reach; reaches the door→window suppression, measured behavior-neutral across all seven 1:100 sheets (s11 13/13, s16 14/14, s12 7/7, s05 8/8, s07 4/4, s06 2/2, s18 9/9 — unchanged, including candidate counts) |
| CROSS_DOOR_FALLBACK_EXPAND_PX | W | veto reach of a fallback-tier door — same built quantity, smaller radius |

`CROSS_WINDOW_THICKNESS_TOL_PX` is deliberately **left bare** (not a `CrossGates`
field, not scaled) — it gates WINDOW cross-validation (a glazing-thickness
check), not doors, and its classification is deferred to the windows branch.
The window-side confidence constants (`CROSS_WINDOW_ON_WALL_BOOST`) and the
door-side confidence penalties/thresholds (`CROSS_NO_WALL_PENALTY`,
`CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY`, `CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY`,
`CROSS_DOOR_MIN_WINDOW_COVER`, `CROSS_DOOR_MIN_CONFIDENCE`) are **D** —
dimensionless, never scale.

**Arithmetic-relationship correction (2026-08-13).** The design spec's §5
("Ordering invariants") originally claimed `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX`
(W, 3.0 × f) and `DOOR_FOLD_LEAF_LINE_SEP_MAX_PX` (P, 4.0) "invert below
f = 0.75." That threshold is arithmetically wrong. Solving `3.0 × f = 4.0`
gives a crossing at **f ≈ 1.333**, not 0.75 — and 1.333 is *above* 1.0 (finer
than the 1:50 reference scale), well outside this branch's actual operating
range (every resolved sheet in the corpus has f ≤ 1.0: 1:50 sheets at f=1.0,
1:100 sheets at f=0.5, s13 at f≈0.366). At f=1.0 the W value (3.0) is
*already* below the P value (4.0), and stays below it for every smaller f —
so across the whole domain this branch actually exercises, the relationship
between these two constants is **monotone, never inverting**. 0.75 appears to
be the ratio 3/4 mislabeled as a crossing factor, rather than a solution to
`3f = 4`. This **strengthens** the original no-assertion conclusion rather
than weakening it: there was never a real in-range crossing to guard against
in the first place, so the "documented no-op, deliberately unchecked"
decision (design §5) needed no revision — only its stated arithmetic did. The
corrected note lives in the design spec itself (§5, bracketed
2026-08-13 addendum) rather than as a silent rewrite of the original
(wrong) claim; the same correction was applied to the comment prose in
`tests/test_scale_door_gates.py`'s `test_cross_class_inversion_is_a_no_op_not_a_crash`
(assertions unchanged — only the explanatory comment was wrong).

## 4e. Window constant classification table (frozen 2026-08-13)

Companion to §4's wall/room table and §4d's door table, same method: classes
**W** (world-space, × f; areas × f²), **P** (paper-space, unchanged), **D**
(dimensionless, unchanged). `f = 50 / nominal_denominator`. Status:
**frozen** — set during the 2026-08-13 window-gates design from each
constant's rationale and measured where cited; a future branch may still
revisit a P verdict flagged "revisit if ..." — that is a new decision, not a
reopening of this table. Full citations and derivations:
`docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md`
§§Evidence base, Design/3.

Windows are **the INVERSE of doors: the window symbol's internal ink
geometry is paper-space; only the opening's own empty-space extent scales.**

**Arithmetic check, so the table is provably exhaustive:** 27 `WINDOW_*`
constants = 16 px-valued (**1 W + 15 P**) + 11 D. Window-side `CROSS_*`
(additional): `CROSS_WINDOW_THICKNESS_TOL_PX` P, `CROSS_WINDOW_ON_WALL_BOOST`
D.

**Key measurements this table rests on** (full derivation in the design
spec):

- **The organising ratio table** — median-of-per-sheet-medians, f05 /
  f10_50:

  | Quantity | 1:50 | 1:100 | ratio | reading |
  |---|---|---|---|---|
  | adjacent pane gap | 5.11 px | 3.00 px | 0.587 | paper **floor**, not scaling — see below |
  | band depth (≥3-pane) | 10.00 px | 10.63 px | **1.06** | paper |
  | cap stroke length (line caps) | 16.06 px | 17.62 px | **1.10** | paper |
  | span overshoot (median) | 3.22 px | 3.00 px | 0.93 | paper |
  | opening width | 79.28 px | 75.62 px | 0.95 | see below |

  The pane-gap 0.587 is the doors leaf-companion signature in disguise:
  converted to millimetres the 1:100 gaps are *larger* (3.00 px ≈ 51 mm)
  than the 1:50 ones (5.11 px ≈ 43 mm), i.e. a minimum drawn separation, and
  no confirmed window anywhere in the corpus draws a pane gap below 1.75 px.
  Band depth ≈ Σ gaps, so depth and spacing land in the same class
  *together* — no ordering clamp needed. Cap length is the subtle row: a
  300 mm wall at 1:100 is 17.7 px, and the f05 sheets draw their jamb caps
  at exactly that (17.62 median) — cap ink spans the frame-to-blockwork
  convention range at *full drawn size* on every tier, so the px union of
  conventions does not shrink with scale. Opening width's flat 0.95 ratio is
  a building-stock confound, not a paper verdict: unlike door leaves
  (standard ~838 mm), real window widths vary 10×, and 1:100 sheets depict
  larger buildings — width is the one quantity in the gate set that is
  empty space between ink (jamb to jamb), not ink, i.e. geometrically
  world-space by construction. What the distribution does show is the
  unscaled floor already grazing real windows: the tightest confirmed f05
  window is **16.49 px vs the 14.0 gate** (s18), 2.5 px of headroom.

- **Retention vetoes** — the confirmed extremes kill every W-candidacy but
  one (censoring caveat: every harvested quantity is a survivor of its own
  gate, so maxima locate the gate, and the *extremes vs the scaled gate* are
  the decisive statistic, not the ratios):

  | Gate | scaled @f=0.5 | confirmed evidence against scaling |
  |---|---|---|
  | `WINDOW_CAP_MAX_LEN_PX` 36 | 18 | caps **24.75 px** (s16 w0001, s11 w0002); at f037 caps 12.75–13.0 vs 13.2 — 0.2 px from loss |
  | `WINDOW_MAX_WIDTH_PX` 280 | 140 | width **210.76 px** (s18 w0021); at f037 103.94 vs 102.65 — loses s13 w0009/0010 |
  | `WINDOW_GLAZING_THICKNESS_PX` 16 | 8 | depth to **14.25 px** (s16/s11); s13 12.74–13.0 vs 5.87 — all 11 die |
  | `WINDOW_GLAZING_ADJ_SPACING_PX` 8.5 | 4.25 | confirmed gaps at **8.25 px** (s16); s06 median 4.50 |
  | `WINDOW_SPAN_OVERSHOOT_PX` 12 / `_COVER_TOL_PX` 4 | 6 / 2 | tails saturated at BOTH tiers (9.38 & 10.5 vs 12; 3.38 & 3.55 vs 4) |

- **Variant matrix summary** — 90 = 79 + 11 confirmed windows at stake, each
  variant run through the real sweep at each sheet's true factor:
  `MIN_WIDTH`-only (the accepted set) kept **90/90** with exactly **+1 s16
  REVIEW window, (1337,1795,1354,1801) conf 0.67, width 11.6 px**, zero FP
  delta, and no door/room damage — a real 1:100 window sitting below the
  unscaled 14 px floor, the 21st-sheet argument in measured form. Max gates
  (cap/width/glazing/mullion/block) lost **50** confirmed windows (40/90,
  −24 FP, 2 confirmed rooms lost); separations (eps/tight/pad/span) lost
  **54** (36/90, −16 FP, room FP shape-swap only); blanket (all 16 px +
  CROSS) lost **61** (29/90, −31 FP, 2 rooms lost, gates interact — s07
  loses 7 vs 1/0 in isolation) — this is the design's central negative
  result. `CROSS_WINDOW_THICKNESS_TOL_PX` scaled alone produced **exact
  zero delta** (0 kept/new/FP change) on all eight sheets. The min-floor
  variant also exposed a perf trap: scaling `WINDOW_CAP_MIN_LEN_PX`
  (3.0 → 1.5) doubled the windows stage on s16 (**4.46 s → 9.11 s**) by
  flooding the cap pool with tiny strokes, for **zero** detection change
  anywhere; the `MIN_WIDTH`-only variant reproduced the identical result at
  ≤1.13× baseline cost (s16 5.04 s, s18 6.32 s, s11 3.87 s) —
  `CAP_MIN_LEN` scaling costs 2× stage time for zero detection change, which
  together with cap ink's paper measurement (1.10) settles it as P.

### detection/windows.py

| Constant | Class | Rationale |
|---|---|---|
| WINDOW_ANGLE_TOL_DEG | D | angle tolerance — "two lines within this are the same direction" |
| WINDOW_ANGLE_GRID_DEG | D | angle — spacing of the overlapping cap-orientation frames |
| WINDOW_CAP_MIN_LEN_PX | P | cap ink measures flat (1.10 ratio, above); scaling doubles the s16 windows stage (4.46 s → 9.11 s) for zero detection change anywhere — settled P on cost, not retention |
| WINDOW_CAP_MAX_LEN_PX | P | measured decisive: confirmed caps to **24.75 px** (s16 w0001, s11 w0002) vs the scaled gate 18; at f037 caps sit 0.2 px from loss (12.75–13.0 vs 13.2) |
| WINDOW_CAP_LEN_RATIO | D | ratio — facing caps must be similar length |
| WINDOW_CAP_ALIGN_OVERLAP | D | ratio — facing caps' perp-extents must overlap |
| WINDOW_MIN_WIDTH_PX | W | the opening's empty-space extent (jamb to jamb) — the only non-ink quantity in the gate set; 2.5 px headroom at f05 today, and the measured +1 REVIEW window at 11.6 px is the recovery it buys. Floored `max(1.0, ·f)` |
| WINDOW_MAX_WIDTH_PX | P | measured decisive: confirmed width **210.76 px** (s18 w0021) vs the scaled gate 140; at f037, 103.94 vs 102.65 loses s13 w0009/0010 |
| WINDOW_GLAZING_THICKNESS_PX | P | measured decisive: confirmed depth to **14.25 px** (s16/s11) vs the scaled gate 8; s13's 12.74–13.0 vs 5.87 wipes all 11 confirmed windows |
| WINDOW_GLAZING_ADJ_SPACING_PX | P | measured decisive: confirmed gaps at **8.25 px** (s16) against the scaled gate 4.25; s06 median 4.50 also clears only the unscaled 8.5 |
| WINDOW_GLAZING_DISTINCT_EPS | P | semantic (CAD-precision), variant-corroborated: stroke-doubling collapse tolerance; px-valued despite carrying no `_PX` suffix — flagged below as a census-methodology blind spot |
| WINDOW_MIN_GLAZING_LINES | D | count — ≥2 distinct parallel panes must span the gap |
| WINDOW_MIN_WIDTH_CAP_RATIO | D | ratio — opening width vs jamb-cap length |
| WINDOW_TWO_LINE_MIN_CAP_PX | P | measured decisive: cap ink flat — a 300 mm wall at 1:100 draws 17.7 px caps, so the unscaled 12 keeps discriminating; the only f05 2-pane confirmed window has 17.77 px caps |
| WINDOW_TIGHT_PAIR_GAP_PX | P | semantic, variant-corroborated: drawn legibility band, FP range 1.6–2.5 vs true range 1.75–3.5 |
| WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX | P | semantic, variant-corroborated: sign test + noise floor — the true gate population is 3 windows, all 1:50 |
| WINDOW_SPAN_COVER_TOL_PX | P | measured decisive: confirmed shortfall tails saturated at both tiers (3.38 px f05, 3.55 px f10_50, vs the 4 gate) |
| WINDOW_SPAN_OVERSHOOT_PX | P | measured decisive: confirmed overshoot tails saturated at both tiers (9.38 px f05, 10.5 px f10_50, vs the 12 gate) |
| WINDOW_SPAN_PERP_TOL_PX | P | semantic, variant-corroborated: fit tolerance |
| WINDOW_MIN_CONFIDENCE | D | confidence floor |
| WINDOW_INTERIOR_BAND_PAD_PX | P | semantic (pen-adjacent pad), variant-corroborated; shrunk-world revisit trigger recorded: at f=0.5 on the synthetic shrunk s01/s02 world it swept world-compressed neighbour ink into the clutter scan and killed one s02 window, but no confirmed 1:100 window is clutter-rejected on the real corpus |
| WINDOW_INTERIOR_SHAPE_MAX | D | count — non-line primitives between the panes |
| WINDOW_INTERIOR_OBLIQUE_MAX | D | count — oblique lines between the panes |
| WINDOW_BLOCK_CAP_MAX_THICK_PX | P | conservative default, no corpus signal at any other scale: block-cap framed windows exist only on s02/s10/s03, a drawing-house convention split, not a scale tier — no cross-tier ratio exists even in principle on this corpus. Retention-safe under both the world convention (~3 px bars at 1:100 — pass) and the paper convention (~6 px — pass), while W-scaling rejects the paper convention. Revisit trigger: a 1:100 sheet drawing framed multi-light windows |
| WINDOW_BLOCK_CAP_MIN_ASPECT | D | aspect ratio |
| WINDOW_MULLION_GAP_MAX_PX | P | conservative default, same call and same revisit trigger as `BLOCK_CAP_MAX_THICK`: retention-safe under both the world convention (~5.75 px gaps at 1:100 — pass) and the paper convention (~11.5 px — pass) |
| WINDOW_BLOCK_CAP_CROSS_RATIO | D | ratio — a line ≥ this fraction of the block's diagonal |

### detection/postprocess.py (window-side CROSS_*)

| Constant | Class | Rationale |
|---|---|---|
| CROSS_WINDOW_THICKNESS_TOL_PX | P | mechanism + zero-delta measured (design spec Evidence 5): compares bbox short side to measured wall thickness — both world quantities, but the *mismatch* between them is cap-ink overshoot beyond the wall band, the same drawn-overshoot quantity measured paper above (saturated span tails at both tiers); the mismatch is bimodal at every tier (≈0 where the boost fires, or ≫6 — medians 23.75 at f10_50, 9.38 at f05), nothing in (3, 6] for scaling to flip, and the variant run confirmed exact zero delta on all eight sheets. `CrossGates` gains no new field; the constant stays bare in `postprocess.py` with a comment pointing at this row |
| CROSS_WINDOW_ON_WALL_BOOST | D | confidence boost |

**Hidden-constant audits (both §4b blind-spot classes).**

*Unprefixed module constants:*
- `_GRID_PX` (64.0) — spatial-hash cell size, self-documented "not a
  tunable"; trades cells visited vs records per cell, never which records
  pass. Layout; untouched.
- `_GLAZE_U_BIN_PX` = `SPAN_OVERSHOOT + SPAN_COVER` (16.0) — glazing-index
  bin. Correct at ANY width (the query iterates the full bin range); "at
  most two bins" is perf-only. Both parents froze P, so it stays a true
  module constant.
- `_CAP_V_BIN_PX` = `CAP_MAX_LEN + 4.0` (40.0) — **correctness-coupled**:
  the same-or-adjacent-bin pruning in `_facing_cap_pairs` is exact only
  while bin width exceeds the in-effect cap max. Had `CAP_MAX_LEN` been W,
  this bin would silently drop facing pairs at f>1 (caps to 144 px vs a
  40 px bin inside the clamp domain) and would have had to be derived per
  call from gates. With `CAP_MAX_LEN` frozen P the hazard is vacuous at
  every factor — recorded here as an audit note precisely because **a
  future W-reclassification of `WINDOW_CAP_MAX_LEN_PX` must move this bin
  into the gates path in the same change.**

*Numeric literals outside the constants block:* `crossed()`'s ±1.0 px bbox
slack, `_merge_mullion_chains`' ±2.0 px block-perp-in-gap slack — px-valued
fit slacks ≤4 px, implicitly P (the same class findings §4d froze for
doors); `_facing_cap_pairs`' `+1.0` float-rounding slack (rides beside
`MAX_WIDTH`, numeric); `1e-6` epsilons; confidence literals
0.62/0.05/0.10/0.90 and the 0→180° frame sweep (D). `_merge_mullion_chains`
additionally reuses `SPAN_PERP_TOL` and `GLAZING_DISTINCT_EPS` at its own
call sites — those sites inherit the constants' P verdicts.
`WINDOW_GLAZING_DISTINCT_EPS` is itself worth flagging: it is px-valued
despite carrying no `_PX` suffix — a census-methodology blind spot of the
same shape as `COLLINEAR_OFFSET_TOL` (§4b): naming convention alone cannot
be trusted to enumerate every px-valued constant, so the constants block
must be read in full, not grepped by suffix.

**Harness note.** Both measurement mechanisms are §4c-compliant by
construction rather than by after-the-fact reconciliation: distributions
came from inert measurement taps (`_meas`/`_meas_cross` evidence keys)
harvested from a full `tools/regress.py`-equivalent sweep, and variants
monkeypatched module constants ×f and invoked `regression.sweep.sweep()`
in-process — the harness IS the sweep, so §4c's traps are satisfied by
construction rather than needing after-the-fact reconciliation. Taps were
verified byte-inert (the tapped sweep reproduced the baseline sweep on
every comparison key of every sheet) and fully reverted before the
implementation commit; they never ship.

## 5. Decisions (2026-08-12 brainstorm, user-approved)

1. **Approach: thread a scale factor** into walls/rooms and scale classified
   constants at use ("Approach B"). Rejected: geometry normalization into
   canonical 1:50 space (changes every detector at once + inverse-transform
   must find every evidence geometry field — silent-corruption risk);
   mm-redefinition of constants (invalidates tuning-guide/CLAUDE.md px lore,
   churns tests, cosmetic).
2. **Unresolved scale → identity (f = 1.0)**, current behavior. The user
   backfills s10/s11/s16/s18/s20 by hand via the existing prompt→store flow
   ('user'-source stored scales, as s01 already has). Rejected: geometric
   scale inference (guess-based subsystem; wrong guesses silently distort
   every gate).
3. **Mixed-scale pages (s03, s17): ink-dominant floor-plan scale (by path
   count per region)** + a `SCALE_MIXED_FLOOR_PLANS` warning — explicitly
   **interim**. The user's requirement (2026-08-12) is that each plan runs
   at its own scale even on a single page; that fix is deferred to a
   follow-up because it is a pipeline restructure with measured regression
   risk, not a bolt-on (see §6, "Per-scale-group detection", for the
   evidence and the design sketch).
4. **Nominal denominator preferred over raw** so 1:50 is exactly f=1.0.
5. **Clamp f to [0.25, 4.0]**, outside → 1.0 + `SCALE_FACTOR_CLAMPED`.
6. **s13 conflict:** viewport (~1:136) wins over caption text, per the
   resolver's existing rule.
7. **Scope:** walls/rooms only this branch; doors/windows/labels/schedules
   deferred (§6).
8. Regression gates: s01/s02 (and all 1:50 sheets) unchanged; 1:100 changes
   arrive as REVIEW lines for user verdicts. One fix + one sweep per
   iteration, then ask (standing checkpoint rule).

## 6. Deferred work (for successor branches)

- **Doors:** `DOOR_*` constants in `detection/doors/constants.py` — **DONE**
  (`feat/scale-aware-door-gates`, 2026-08-13). All 103 `DOOR_*` constants plus
  6 door-side `CROSS_*` classified and threaded via `DoorGates`/`CrossGates`;
  frozen table at §4d, harness trap at §4c. Sweep matched the design's
  predicted delta exactly across all seven 1:100 sheets (door 57/57 kept ·
  +3 new · −2 gone-FP; window 68/68 kept · +17 new · −1 gone-FP; room 46/51
  kept · +2 new · −2 gone-FP; zero confirmed entities lost anywhere; all
  1:50/unresolved sheets byte-identical). See
  `.superpowers/sdd/2026-08-12-scale-aware-door-gates/task-9-report.md` for
  the full sweep-vs-prediction table.
- **Doors — Bezier aspect gate (deferred, not this branch's scope):**
  `DOOR_BBOX_ASPECT_MIN`/`MAX` ([0.85, 1.15]) rejects genuine 85°-sweep arcs
  at measured bbox aspect **0.804** — below the gate. This is the single
  largest measured miss driver on the 1:100 sheets: s06 detects only 2 of 10
  visible swings because of it. The polyline detection path already uses a
  wider [0.65, 1.45] gate for the same judgment (`detection/doors/arcs.py:643`)
  — the Bezier path's gate is tighter than its own sibling for no measured
  reason. **Dimensionless** (an aspect ratio), so scale-awareness cannot fix
  it; the fix is widening the gate and re-verifying against the false-positive
  risk that motivated the tight bound originally. Recorded here (design
  §Scope/Out, 2026-08-12) rather than fixed on the scale-aware-gates branch —
  a large chunk of this branch's real-corpus payoff is gated behind this
  follow-up, not behind scale.
- **Doors — s11 double-door assembly merge (deferred, confirmed NOT a scale
  bug):** `door_0005`/`door_0007` (conf 0.60, at (765,1224) and (766,1640))
  detect as two half-width singles instead of merging into one full-width
  french/garden door; the halves sit at ~IoU 0.5 against the true full-width
  door, exactly the matcher's boundary, so they are deliberately left
  UNREVIEWED (either verdict could misfire against the future fixed
  detection) — record the full door as a hand-written `deferred` miss once
  its extent is confirmed. Pre-dates the scale branch (baseline-verified
  byte-identical, original report 2026-08-12). Tested directly on the doors
  branch (design "Non-goals"): the merge only fires when the **paper-space**
  `DOOR_LEAF_COMPANION_PERP_PX` is scaled — i.e. only under the classification
  this branch measured and rejected — and doing so costs **3 confirmed doors
  on s11, 5 on s16, and both of s06's** (the same negative result documented
  in §4d's leaf-companion-separation evidence, §2/§3 of the design). So the
  merge defect is real but belongs to the assembly-merge logic itself, not to
  scale-awareness; fixing it needs its own branch, not a constant reclassification.
- **Windows:** `WINDOW_*` constants in `detection/windows.py` — **DONE**
  (`feat/scale-aware-window-gates`, 2026-08-13). 1 W + 15 P + 11 D via
  `WindowGates`; frozen table at §4e; predicted delta: s16 +1 REVIEW window
  only.
- **Windows — span-overshoot retune (paper-space, NOT scale):** confirmed
  windows overshoot ≤ 9.38px (f05) / 10.5px (f10_50); the s12/s18 phantom
  windows sit at 11.75–11.98px against the 12.0 gate — a retune to ~10.5–11px
  could kill those FP families at zero measured confirmed cost. Changes 1:50
  sheets too → own branch with its own sweep.
- **Windows — NMS constants:** `NMS_CENTER_DIST_PX` / `NMS_PROJ_PERP_MAX_PX`
  (postprocess) deliberately unclassified — shared cross-type suppression
  machinery; scaling them moves every entity type at once.
- **Windows — revisit triggers for frozen-P rows:** `WINDOW_BLOCK_CAP_MAX_THICK_PX`
  / `WINDOW_MULLION_GAP_MAX_PX` (a 1:100 sheet drawing framed multi-light
  windows — no such sheet exists in the corpus, the convention split is by
  drawing house, not scale); `WINDOW_INTERIOR_BAND_PAD_PX` (a real 1:100
  window rejected by the interior-clutter gate — observed only on the
  synthetic shrunk world).
- **Window tuning guide staleness:** guide §4 lists `WINDOW_CAP_MAX_LEN_PX`
  34 vs the code's 36 and pre-dates the rotation-general rewrite (§6 still
  says "diagonal not handled"); a `docs/window-guide-refresh` branch exists.
- **Labels/schedules:** mostly text-driven; font sizes are paper-space —
  expect few W constants. Audit anyway.
- **Cross-validation:** the door-side `CROSS_*` constants in
  `detection/postprocess.py` are DONE (§4d, `CrossGates`); the window-side
  ones (`CROSS_WINDOW_*`) remain for the windows branch, per the bullet
  above.
- **Layout segmentation:** `SEGMENT_MIN_REGION_SIDE_PX` etc. measure
  *drawing extents*, which scale — but region filtering has its own
  coverage guard; audit before touching.
- **Per-scale-group detection** for mixed pages (s03, s17) — **required
  follow-up, not optional** (user requirement 2026-08-12: each plan must
  run at the scale attached to that plan, even on a single page).

  *Why it isn't a bolt-on:* running detection on less than the union is a
  measured regression. On s01 (2026-07-28, both regions the SAME scale),
  per-region passes degraded rooms: 13 rooms / 478,923px² → 14 / 446,261px²
  — kitchen units carved out of DINING/SITTING+KITCHEN (148,895 → 118,073px²),
  UTILITY/STORE spuriously split (17,430 → 10,526 + 6,144). Mechanism:
  page-global statistics — `ROOM_WALL_PEN_MIN_FRAC` (0.15 of paired-face
  length makes a pen a wall pen), the `wall_stroke_reference` median, the
  lattice/hatch demotion scans — lose their denominator when the path set
  shrinks; s01's red furniture pen cleared 15% within one region alone and
  its pairs gained barrier rights. Any split reintroduces this.

  *Design sketch:* decouple statistics scope from detection scope, along
  the same world/paper split as the constants. Paper-space statistics (pen
  medians, wall-pen color fractions) are poolable across scales — one CAD
  export, one pen convention — so compute them ONCE over the union and
  pass them FROZEN into per-group passes. Geometric scans (lattice/hatch
  pitch demotion) are scale-dependent and belong inside each group's pass
  with that group's factor. Pipeline side: partition floor-plan regions by
  resolved factor, `filter_page_data` per group, run
  `detect_wall_network`/`detect_rooms` per group with (frozen stats, group
  factor), concatenate candidates; doors/windows/labels/schedules scope
  decided by whatever state that branch finds them in. Verify on s03/s17
  under the one-fix-one-sweep checkpoint rule, and re-verify the s01
  union-identity property (single-scale pages must still take exactly one
  pass with unchanged results).
- **Misses audit on 1:100 sheets:** ground truth cannot see misses (§3);
  after the walls/rooms branch lands, spot-check s05/s07/s12 overlays for
  undetected doors/partitions to size the doors branch.

## 7. Test patterns that worked (reuse them)

- **Shrunk-world synthetics:** scale coordinates × 0.5, keep pen widths —
  that IS a 1:100 export. Assert f=0.5 reproduces the f=1.0 result,
  including a case that fails if paper-space gates are wrongly scaled.
- **Identity test:** f=1.0 output == parameter-omitted output.
- **Ordering assertions** in the scaled-gates constructor (design §4) so a
  pathological factor fails loudly.
