# Handoff: hatch-cell chords in the wall network (follow-up to `fix/s03-bedroom-corner-notch`)

**Written:** 2026-09-02, after fixing the bottom-right notch on s03's BEDROOM
rooms 0005/0013.
**For:** the next agent picking up the residue of that fix, in a fresh session.
**Status of the fix:** committed on `fix/s03-bedroom-corner-notch` —
`a239176` (code + test + prose) and `2a0869e` (graphify-out). Not merged to
`main`; the user merges. Working tree also carries the user's own uncommitted
`extraction/renderer.py` change (overlay labels now print the entity id in
front of the room name) — leave it alone.

## Read these first (in order)

1. CLAUDE.md "Room detection" paragraph — the sentence beginning "pairing
   itself demands ONE THICKNESS ALONG THE OVERLAP" (`WALL_PAIR_TAPER_MAX_FRAC`).
2. `detection/walls.py:91` (the constant, with every measured number) and
   `_pair_faces_to_centerlines` around line 2567 (the gate).
3. `tests/test_wall_network.py::TestCenterlines::test_brick_cell_diagonal_does_not_pair_into_the_room`
   and `test_tapering_wall_still_pairs` — the pinned topology.
4. `docs/regression-testing-guide.md` §9, §10, §12, §13 and the
   `fix-detection` skill (`.claude/skills/fix-detection/SKILL.md`) — the
   cadence the user expects: one fix, one sweep, one report, then stop.
5. `.claude/projects/.../memory` note "Corpus baseline red 2026-09-02" (loaded
   into the session automatically) — why a red sweep line is not evidence
   that your branch regressed a sheet.

## What was fixed, in one paragraph

`_pair_faces_to_centerlines` measured face spacing at ONE point (the partner's
first endpoint). Inside `WALL_PARALLEL_ANGLE_TOL` (4°) a stroke crossing the
band corner to corner — the single diagonal of a brick-hatch cell, drawn in
the wall pen (s03 `EXISTING_BRICKWORK`, s04/s08 `RR_Wall Hatches`, s20; an
aspect-15 cell sits 3.9° off both faces) — read whatever the divergence was at
that one point, possibly hundreds of px past the cell, and its centerline
landed on the room side of the chord. The fix interpolates the partner's
signed offset at both ends of the overlap and drops a pair whose spacing
changes by more than half of itself (real pairs ≤ 0.30 corpus-wide, chords
1.0). The chords only became visible to face collection with `86c005b`
(width-0 strokes recorded at 1.0px), which is why the notch was a regression.

## Residue — the iteration this handoff is for

### R1. Hatch-cell chords are still wall FACES (the proper fix)

The taper gate stops the chord pairing with its own cell's faces, but the
chord still enters face collection as a strong 1.0px face and still pairs
with the NEXT cell's face at a ratio under the gate:

| sheet | chord | partner | spacing (lo → hi) | ratio | where the centerline lands |
|---|---|---|---|---|---|
| s04 | (1856,927)-(1851,831), `RR_Wall Hatches` | face x=1863 | 7.1 → 12.4 | 0.43 | inside the 1851–1868 band |
| s04 | (1868,927)-(1863,831) | face x=1856 | 12.4 → 7.1 | 0.43 | inside the band |
| s20 | (552,2892)-(730,2881), weak | face y=2904 | 12.0 → 23.7 | 0.49 | inside the band |
| s08 | (1498,639)-(1077,616) | face y=619 | 3.4 → 20.2 | 0.83 → now dropped | — |

Harmless today (every such centerline lies inside the wall band and the
sweep is byte-identical on those sheets), but they are not walls, they sit in
the paired-face stroke reference, and a longer/thinner cell (aspect ≥ 19
puts the chord under `COLLINEAR_ANGLE_TOL` 3°) can be MERGED collinearly into
a face run: `_merge_collinear_segs` uses the same single-endpoint offset test
(`b.p1` only, walls.py ~line 2415). s03's 1:100 left-wall chord
(1244,857)-(1252,1080) is 2.26°; no damage observed, but nothing prevents it.

The drawing convention to key on: a hatch cell is a CLOSED same-pen box whose
short side is wall thickness, with ONE stroke joining two diagonally opposite
corners (existing brickwork, UK convention) or an X (blocking). Wall linework
never joins opposite corners of a band-shaped box — faces run along it, end
caps across it. Proposed rule, in `detect_wall_network` next to
`_dimension_line_indices` / `_vector_text_indices` (a pre-pairing exclusion,
never a barrier-rights demotion — a vetoed line that merely lost barrier
rights would still pair): `_hatch_cell_chord_indices(paths, gates)` — a
solid `l` item whose two endpoints coincide (≤ 1px) with two opposite
corners of a rectangle formed by four same-pen `l` items (or a stroked
`re`/`qu`) with short side in `[WALL_MIN_THICKNESS_PX, WALL_THROUGH_HATCH_MAX_PX]`
and aspect ≥ 2; exclude the chord, and — worth measuring first — feed it to
the material tiers as a mark (`_collect_material_marks` caps length at
`WALL_HATCH_MAX_LEN_PX`, so a 219px chord is not material today; a
single-diagonal cell IS the band's drawn material, exactly like through-hatch).
Measure on s03/s04/s08/s20 how many strokes match, and confirm on s01/s02
that no wall linework does (a chamfer stub meets a face end-to-end at ONE
corner, never two).

### R2. The single-endpoint offset test in the collinear merge

Same class of flaw as the fix, in `_merge_collinear_segs`: the offset of `b`
from the run's line is measured at `b.p1` only. A both-ends test (offset at
`b.p1` AND `b.p2` within `COLLINEAR_OFFSET_TOL`) is the principled version;
the seam rule in CLAUDE.md ("the bedroom band's diagonal, 17.7px over 336.7px
= 3.0°") is the historical instance. Sweep it separately from R1 — bundled
REVIEW deltas are unattributable.

### R3. The corpus baseline is RED on 11 sheets (the user's queue, not yours)

On `main` at `7038748` and unchanged by this branch, `python tools/regress.py`
prints `✗ FALSE POSITIVE RETURNED` lines on s04 (1 window, 1 room), s05 (1
room), s08 (1 window), s11 (4 rooms), s12 (7 rooms), s14 (1 window), s15 (1
door, 3 windows, 7 rooms), s16 (10 rooms), s17 (10 rooms), s18 (12 windows,
~13 rooms), s20 (1 window). Verified pre-existing by reverting this branch's
only code change and re-sweeping each sheet: identical lines. No
`REGION_CACHE_MISS_OFFLINE` involved. Nobody has bisected which commit after
the verdicts were recorded returned them (candidates: the layout commits
`fe81c1d`…`d57de02`, `86c005b`, `ad90876`, `26609a8`). Ask the user before
spending a session on it; it may be known.

## Tooling that exists now

- `python tools/probe_pair_taper.py sNN [--thresh px]` — the corpus probe
  behind the gate: every candidate pair's spacing at both overlap ends,
  ratio, and whether it survives into the network. Run it on a sheet before
  and after R1 to see the chords leave the pair population.
- `python tools/compare_room_shapes.py sNN …` — entity/room-shape delta
  between `outputs/regress_baseline/<slug>` (from
  `tools/compare_sweeps.py sNN --snapshot`) and the latest sweep run. The
  sweep report cannot see a room that merely changed outline; this can.
  Use it corpus-wide after every sweep.
- Operational: a full `python tools/regress.py` exceeds the Bash tool's
  10-minute foreground limit. Run 3–4 background `--sheet` groups (s18 ≈ 2
  min, s16 ≈ 1 min, s11/s15 ≈ 30 s, the rest seconds) and read the logs.
- Attribution without `git stash` (the stash is shared across worktrees):
  `git diff detection/walls.py > x.diff && git checkout -- detection/walls.py`,
  sweep the sheet, `python tools/compare_sweeps.py sNN --snapshot`,
  `git apply x.diff`.
- Room labels are cached per page keyed on EVERY room polygon
  (`gemini/room_label_cache.py`), so any outline change on a sheet drops its
  cached names until a Gemini-enabled `python app.py extract fixtures/sheets/<sheet>.pdf`
  reseeds `fixtures/sheets/.room_labels_cache/`. Done on 2026-09-02 for s03,
  s04, s08, s16 after this fix; do it again for any sheet R1/R2 reshapes.

## Prompt for the next agent

> Use `/fix-detection`. Branch from `main` after `fix/s03-bedroom-corner-notch`
> is merged (or from that branch if it is not). Read
> `docs/hatch-cell-chords-handoff.md` and do R1 only: hatch-cell chord
> strokes (a same-pen stroke joining two diagonally opposite corners of a
> closed wall-thickness box) must never become wall faces — add a
> pre-pairing exclusion beside `_dimension_line_indices` in
> `detection/walls.py`, measure the matching strokes on s03, s04, s08, s20
> and prove on s01/s02 that no wall linework matches, pin the topology with
> a synthetic test in `tests/test_wall_network.py`, sweep the corpus in
> background sheet groups against `compare_sweeps` snapshots, run
> `tools/compare_room_shapes.py` on every sheet, and stop at the report. The
> corpus baseline is already red on 11 sheets (R3) — attribute by revert +
> re-sweep, never by assuming. Do not touch R2 in the same iteration.
