# Handoff: hatch-cell chords in the wall network (follow-up to `fix/s03-bedroom-corner-notch`)

**Written:** 2026-09-02, after fixing the bottom-right notch on s03's BEDROOM
rooms 0005/0013.
**For:** the next agent picking up the residue of that fix, in a fresh session.
**Status of the fix:** committed on `fix/s03-bedroom-corner-notch` —
`a239176` (code + test + prose) and `2a0869e` (graphify-out); merged to
`main` as `0de608b`.
**Status of R1 (updated 2026-09-02, later the same day):** done on
`fix/hatch-cell-chord-faces` as a SEAM fix, not a chord rule — `9e86031`
(code + tests + prose) plus the tools/handoff commit after it; the user
merges. The "chords" were fill seams (see the R1 resolution note below).
**Status of Gap B (2026-09-02, branch `fix/fill-chain-start-revisit`):** done —
`_collect_fill_rings` closes a ring at an EXACT return to its start vertex
(`WALL_FILL_CHAIN_REVISIT_TOL_PX`) and opens the next chain there; the CLAUDE.md
seam sentence carries the rule and the corpus measurement. Sweep: every
verdict line identical to baseline except s18's recorded false-positive
room_0009 (gone — an incidental win: the pocket was never fenced, the 8px
opening severed it, and recovered glyph patches reshaped the re-dilation) and
s03 room_0007 (a 2×4px mitre spike from a recovered sub-2px sliver triangle,
126 px² after simplification). Two residues surfaced, both pre-existing and
both queued below: **Gap C**, the seam probe leaves any fill thinner than 2px
so sliver triangles never seam-unite; **Gap D**, s18's black fill class is
rated wall on the strength of vector-text GLYPH OUTLINES (1,328 of its 1,633
rings are ≥ 8-vertex rings inside 16px), which enter the barrier area.
**Status of Gap C (2026-09-02, branch `fix/fill-seam-probe-sliver`):** done —
`_fill_seams` probes at the smaller of `WALL_FILL_SEAM_PROBE_PX` (1px) and
`WALL_FILL_SEAM_PROBE_FRAC` (0.5) of the thinnest sharing ring's `short`; the
fraction was measured, not picked (clearance at a sliver triangle's seam
midpoint is 0.98–1.07 × `short` corpus-wide, so half keeps a 2× margin). The
CLAUDE.md seam sentence carries the rule, the per-sheet recovery counts and the
telemetry. Sweep verdict-identical on all 20 sheets; s03 room_0007 and
room_0014 are byte-for-byte back on their pre-Gap-B outlines, and three s03
rooms move toward their walls — room_0013 (+1,466 px²) because a jamb stub's
strip-stack joint edge had been a wall-fill face that the collinear merge
(R2's single-endpoint offset test) hung the whole 416px band face on, 3.8px
into the room. Gap D is next; R2 remains open and now has a measured instance.

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

> **Resolution (2026-09-02, branch `fix/hatch-cell-chord-faces`):** the
> premise below is wrong — none of these strokes is a hatch cell. Dumping
> the primitives around each "chord" shows the shared diagonal of two
> same-fill triangles: the exporter triangulated the wall's FILL polygon
> (the layers `EXISTING_BRICKWORK` / `RR_Wall Hatches` hold the fill, not a
> hatch) and attached the fill colour as a width-0 stroke, recorded at
> 1.0px. `_fill_seams` already finds them; the gap was that the seam veto
> only stripped the `wall_fill` flag, so a self-coloured seam stayed a
> STROKED face (s03 248, s04 50/50, s08 48/48, s12 116, s17 128). Seams
> now join the pre-pairing exclusion set beside `_dimension_line_indices`.
> A geometric chord probe (endpoints on two opposite corners of a
> same-pen box, aspect ≥ 2) matched ZERO strokes on s03/s04/s08/s20 and
> only the 0.3/0.45px blocking X's on s02 — there is no stroked-chord
> class on the corpus to key a rule on. s20's chord is a different gap:
> its two triangles chain into one six-edge ring that revisits its start,
> shapely rejects it, and the seam goes unseen (see the CLAUDE.md seam
> sentence for the measured blast radius of splitting such chains — the
> next iteration, not this one).

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
  `git apply x.diff`. Or, without touching the working tree at all:
  `git worktree add --detach <scratchpad>/base_tree main`, run a scratch
  script that `sys.path.insert(0, <tree>)`s before importing `detection`
  (the PDF and its caches stay under the main checkout's `fixtures/`), and
  `git worktree remove --force` it afterwards — this is how the s03 corridor
  edge was diffed barrier-by-barrier between the two code states (Gap B).
- A barrier-level diff beats reasoning: monkeypatch
  `detection.rooms._free_space_components` to capture `barriers`, the raw
  `page.difference(barriers)` pieces and the opened components inside a probe
  box, run `detection.run_heuristics` in both trees, and diff the WKTs with
  shapely (`base.difference(fix)` / `fix.difference(base)`). It found s18
  room_0009 was never fenced (one page-sized raw piece in both states) and
  s03's 8 px² mitre spike in one pass each.
- Room labels are cached per page keyed on EVERY room polygon
  (`gemini/room_label_cache.py`), so any outline change on a sheet drops its
  cached names until a Gemini-enabled `python app.py extract fixtures/sheets/<sheet>.pdf`
  reseeds `fixtures/sheets/.room_labels_cache/`. Done on 2026-09-02 for s03,
  s04, s08, s16 after the taper fix and for s03, s12 after the seam fix; do it
  again for any sheet Gap B / R2 reshapes.
- `python tools/probe_fill_seams.py sNN [--list]` (added with the seam fix) —
  Gap A count (seams still reaching face collection; 0 everywhere now) and the
  Gap B population: fill chains that revisit their start EXACTLY, how many
  VALID rings a split there would touch (0 on every measured sheet), and the
  sub-rings a split would recover per fill class with band-shaped / marker
  counts. Run it on a sheet before touching `_collect_fill_rings`.
- `python tools/room_shape_crop.py sNN room_00NN` — the before|after picture
  behind a `compare_room_shapes` SHAPE line (baseline red, latest green;
  zoomed on the symmetric difference plus the whole room). Run it AFTER
  `tools/compare_sweeps.py sNN` — that tool wipes `outputs/compare/<slug>/`.
- Sweep attribution shortcut: keep each background group's log; the section
  after the first `sNN  door …` line is the verdict report, and a post-fix
  report byte-identical to the baseline's (`diff`) means no verdict moved.

## Prompt that was executed for Gap C (the seam probe distance)

Executed on 2026-09-02 (see the Gap C status note at the top); kept for the
record of what was asked. The next agent's prompt is the Gap D sketch below.
Gap B's measured residue on s03 was Gap C:

> Use `/fix-detection`. Branch from `main` after `fix/fill-chain-start-revisit`
> is merged. Read the CLAUDE.md "Room detection" seam sentence — from "and
> fill SEAMS never become faces" through its "Known gaps" clause — then
> `docs/hatch-cell-chords-handoff.md` (the Gap B status note and this
> prompt), `_fill_seams`, `_fill_ring_components` and `_collect_fill_rings`
> in `detection/walls.py`, and the `ROOM_RING_MITRE_LIMIT` dilation of
> `fill_polygons` in `detection/rooms.py`. Do Gap C only: `_fill_seams`
> proves a coincident edge is a seam by testing fill on both sides at 1px
> either side of the edge midpoint, and a 1px probe leaves any fill thinner
> than 2px, so the two triangles of a sub-2px sliver never seam-unite and
> each dilates alone — a sliver triangle's 0.36° tip then runs its mitre to
> the `ROOM_RING_MITRE_LIMIT` (2.0) cap, 4px past the vertex and 2px past
> the band's own 2px standoff (measured 2026-09-02 on s03 room_0007: the
> Gap-B-recovered triangle, paths 284–286, of the 0.75px-tall grey sliver
> under the bathroom's bottom band, x 1075–1195, y 1127.92–1128.67, tip at
> (1194.67,1128.67), dilates to x=1198.68 and bites a 2×4px notch, 8 px²,
> at [1196.67,1126.68]–[1198.67,1130.67] out of the corridor corner, which
> `ROOM_SIMPLIFY_TOL_PX` redraws as a wedge on the already-slanted
> plug/band edge — 126 px² symmetric difference; its twin 281–283, a valid
> ring before Gap B, points its tip into the left wall band and never
> showed). The convention: a seam has fill on both sides at ANY distance,
> so the probe must stay inside the fill it tests — sample at the smaller of
> 1px and a fraction of the thinnest sharing ring's `short` (its
> equivalent-rectangle side; 0.75px for the sliver; a point exactly ON a
> ring boundary is not `contains`, so the fraction must leave a margin —
> measure it, don't pick it). Measure FIRST with a scratch script over
> `_fill_seams`' candidate edges (same fill, same rounded endpoints, ≥ 2
> distinct rings) on s03, s04, s08, s18, s14, s02, s12 and s17: how many
> candidates fail today's probe and pass the scaled one, per fill class and
> ring thickness; confirm every recovered seam has fill on both sides at
> the new distance while an overdrawn duplicate (fill on one side only)
> still fails at any distance. s04/s08's 140/144 red 0.63×29.5px sliver
> pairs are the bulk — today their 29.5px diagonals at 1.2° are
> `RR_Walls`-hinted wall-fill faces and would become excluded seams, and
> their 280/288 triangles would union into 140/144 slivers, so `fill_polygons`
> on s04 falls from 291 — and s18's 1,633 black rings hold sub-2px pieces
> too (measure how many). Pin the topology with a synthetic test in
> `tests/test_wall_network.py` beside `fan_triangulated_band_h`: a
> 0.75px-tall fill-only sliver fan-triangulated into two rings, hugging the
> inner face of a `rect_room` band → the diagonal in `_fill_seam_indices`,
> `fill_polygons` a single rectangle of area width × 0.75, and through
> `detect_rooms` no room vertex past the band's 2px standoff at the sliver's
> tip; prove the test fails on the reverted code (the tip vertex lands 2px
> into the room). Sweep the corpus in background sheet groups against
> `compare_sweeps` snapshots of the unmodified tree, run
> `tools/compare_room_shapes.py` on every sheet, render
> `tools/room_shape_crop.py` for every SHAPE line (after `compare_sweeps`,
> which wipes `outputs/compare/<slug>/`), reseed the room-label cache of any
> sheet whose outlines changed, and stop at the report with the net phantom
> count — s03 room_0007 must return to its pre-Gap-B outline (the remaining
> slant from the door_0003 plug at x=1193.8 to the 1196.7 standoff is the
> separate plug-growth residue in the CLAUDE.md plug sentence; leave it).
> The corpus baseline is red on the same 11 sheets (R3) — attribute by
> revert + re-sweep (or a detached worktree of `main`, see Tooling), never
> by assuming. Do not touch R2, do not add a stroked-chord rule, and do not
> start Gap D in the same branch.

## Queued after it (Gap D — glyph-outline fill rings)

s18 draws its notes as FILLED glyph outlines (n ≥ 8 vertices inside 16px;
1,332 of its 1,633 fill rings), and `_rate_fill_classes` reads each one as a
band because a glyph's long perimeter against its small area gives a long,
thin equivalent rectangle — so the black class is rated wall by text, and
every glyph ring enters `wall_ring_ids` and the barrier area. That is how
room_0009 was fenced: a pocket between the parking-bay kerb line and a text
column, never wall evidence (raw free space is one page-sized piece), severed
by the 8px opening, and dissolved by Gap B only because 28 recovered glyph
patches reshaped the eroded core's mitred re-dilation (`_free_space_components`
re-dilates the WHOLE eroded multipolygon, so eroded cores CAN re-merge despite
its docstring). The candidate rule is the fill analogue of
`_vector_text_indices`: a glyph ring is small, many-vertexed, freestanding
(touches no larger fill or linework) and sits in a row of like rings sharing a
base line at gaps under one glyph height; exclude such rings from the class
rating, `wall_ring_ids` and wall-fill face qualification. Measure the corpus
glyph-ring population per sheet first (s18 1,332; s14 has 32 "other"
many-vertex rings at 23×12px; s11/s16 draw their text as STROKES, not fills,
so they are unaffected) and confirm no jamb stub or corner post is
many-vertexed. Expect s18 to change most; watch for phantoms that the glyph
barriers were accidentally suppressing.
