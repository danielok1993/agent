# Scale Normalization — Findings & Decision Log

**Started:** 2026-08-12 (brainstorm for the walls/rooms branch).
**Read this first** if you are working on scale-awareness for ANY detector
(doors, windows, labels, schedules are still scale-blind — see §6). The
design that consumes these findings: `docs/superpowers/specs/2026-08-12-scale-aware-wall-room-gates-design.md`.

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

- **Doors:** s11 carries a concrete assembly-merge test case (reported by
  the user 2026-08-12): a double door detected as TWO half-width singles —
  the french/garden pair merge does not fire on that drawing. The halves sit
  at ~IoU 0.5 against the true full-width door, exactly the matcher's
  boundary, so they are deliberately left UNREVIEWED (either verdict could
  misfire against the future fixed detection); record the full door as a
  hand-written `deferred` miss when its extent is confirmed. Pre-dates the
  scale branch (baseline-verified byte-identical).
- **Doors:** `DOOR_*` constants in `detection/doors/constants.py` — arc
  radii, leaf lengths, panel sizes are world-space (an 838mm leaf is 24.8px
  at 1:100, likely under current radius floors → predicts *misses* on
  s05/s06/s07/s12). Same classification discipline; reuse the shrunk-world
  synthetic test pattern (coordinates × 0.5, pen widths unchanged).
- **Windows:** `WINDOW_*` in `detection/windows.py` — sill/glazing gaps are
  world-space; angle gates dimensionless.
- **Labels/schedules:** mostly text-driven; font sizes are paper-space —
  expect few W constants. Audit anyway.
- **Cross-validation:** `CROSS_*` in `detection/postprocess.py` (door/window
  vs wall distances — world-space).
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
