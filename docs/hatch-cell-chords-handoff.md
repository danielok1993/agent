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
into the room. The next prompt (below) is that merged-run anchor — R2's
function, a measured instance; Gap D and the candidate-key conflation queue
after it.
**Status of the anchor (2026-09-02, branch `fix/collinear-merge-anchor-line`,
uncommitted, DECISION PENDING):** now implemented as "the run lies on the
member line the DRAWN INK agrees with" — the collinear-support vote
(`_support_anchor`, `WALL_ANCHOR_SUPPORT_REACH_PX` 120px W-class = one door
opening, `WALL_ANCHOR_LINE_TOL_PX` 0.3px, ties → longest member) with
membership untouched (re-projection after the passes converge, direction
kept), pinned by four tests in `tests/test_wall_network.py` (the two
longest-member tests still pass — a 400px face is its own support — plus the
68px-face / 142px-board-line pair at network and room level, which fail on
the longest-member code at 102.25 / 110.25), prose in the CLAUDE.md seam
sentence and a W row in `docs/scale-normalization-findings.md` §4. Swept
against MAIN: no confirmed entity lost, the same 71 pre-existing returned
FPs, 91 outlines move, s03 room_0013/0016 return EXACTLY to main's polygons,
net REVIEW +5 (s17: real SH/WC + two window-reveal slivers — the third,
room_0036, and the returned s18 legend-box FP of the longest-member form are
gone; s18: the ramp strip; s15: a NEW dash-row pocket, the vote's own
limitation). See "Outcome of the collinear-support anchor" below. The
longest-member form's history (three rejected variants) stays in "Outcome of
the anchor iteration".

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
- `python tools/probe_merge_anchor.py sNN [--support] [--list] [--json f]`
  (added with the anchor iteration) — every merged run's seed vs anchor
  (longest member), the displacement the anchor rule applies, each member's
  offset at both ends (the angled population), and with `--support` the
  strong-ink support of every distinct member line at reaches 0/50/100/200/
  page beyond the run — the measurement behind the collinear-support anchor.
  Uses the `trace` hook on `_merge_collinear_segs`.
- `python tools/diff_wall_network.py sNN X0 Y0 X1 Y1 [--base REF|--base-dir D]`
  and `… sNN --idx N [N …]` — faces / segments / fill polygons / white rings
  inside a probe box in the WORKING tree vs a detached worktree of `main`
  (or any ref), each built in its own interpreter, with the one-sided
  differences listed; `--idx` says where given path indices end up in each
  tree (lattice in/kept/out, network.faces, segments). This is the
  barrier-level diff — use it before reading verdict lines. CAVEAT (found
  2026-09-02 on the support-anchor iteration): the default base — a temp
  `git worktree` of main with no `fixtures/sheets` symlink — ran s18 at
  f=1.000 (522 faces) against the working tree's f=0.500 (1,827), so its
  one-sided lists were a scale artefact ("the ramp face split"; main's merge
  on identical inputs gives the branch's three runs). Pass `--base-dir` a
  worktree that has `fixtures/sheets` symlinked (the baseline-sweep worktree)
  and check the `f=` in both headers before reading the lists.
- `python tools/diff_room_polygons.py [sNN …] [--min px2]` — EVERY room whose
  polygon changed between the snapshot and the latest sweep (compare_room_shapes
  prints only IoU < 0.995), plus added/removed/moved entities of every type.
- `tools/room_shape_crop.py` now matches the counterpart by IoU (ids shift
  between runs), takes `--after ID` to name it, and `--only before|after` for
  a REMOVED / ADDED room.
- `tools/_corpus_page.py` — the shared offline loader (extract → cached
  regions → scales → doors → open-leaf exclusion) the new probes use.

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

## Prompt for the next agent (the merged run's anchor line — R2's function)

Gap C's sweep surfaced this with numbers: s03 room_0013 (1:100 BEDROOM) was
missing a 386×3.8px strip along its bottom band because `_merge_collinear_segs`
put the whole 416px band face on a 12px jamb-stub edge's line. The stub edge
is a seam now, which is why the strip came back — but the merge behaviour that
placed the run is untouched and any short face 1–4px off a long one, earlier
in path order, does the same thing.

> Use `/fix-detection`. Branch from `main` after `fix/fill-seam-probe-sliver`
> is merged. Read the CLAUDE.md "Room detection" seam sentence's room_0013
> clause (from "room_0013 (BEDROOM) gains a 386×3.8px strip"), the R2 section
> and the Gap C status note of `docs/hatch-cell-chords-handoff.md`, and
> `_merge_collinear_segs` in `detection/walls.py` (line ~2451): the run's line
> is the SEED member's line — `run.p1/p2 = a.p1 + u·t` over the members'
> projections, `a` being the first unused segment in list (= path) order — a
> member joins when its offset from that line, measured at `b.p1` ONLY, is
> within `COLLINEAR_OFFSET_TOL` (4px), and nothing re-fits the line once the
> members are in. Measured 2026-09-02 on s03: the band's 12px jamb stub at
> x 3741.67–3753.67 is drawn as a stack of strips whose joint edge at
> y=1778.42 (paths 15116/15148, before Gap C a 1.0px wall-fill face) came
> first in path order, so it seeded the run; the band's 416px top face at
> y=1782.17 (path 15154) joined at offset 3.75 and was projected onto the
> stub's line — the merged face sat 3.8px into the room, the band pair
> measured 15.5px against its drawn 11.75, and its solid fenced the strip
> (the tree before Gap C; `tools/compare_room_shapes.py s03` shows the strip
> returning). The convention: a stub is evidence of a line's EXTENT, never of
> its POSITION — the run lies on its longest member's line (or the
> length-weighted least-squares line through the members; measure which one
> the corpus wants, they differ only when two long members disagree), and a
> member's offset is tested at BOTH its endpoints so an angled chord inside
> `COLLINEAR_ANGLE_TOL` (3°) cannot join on one end (the s03 1:100 left-wall
> chord (1244,857)-(1252,1080) at 2.26°, R2's original instance). Measure
> FIRST with a scratch script re-walking the merge on s01, s02, s03, s04,
> s08, s12, s14, s17, s18 and s20: for every merged run with ≥ 2 members, the
> seed's length against the longest member's, the perpendicular displacement
> between the seed's line and the longest member's / length-weighted line,
> and each member's offset at both endpoints (max |Δ| between them is the
> angled population); count runs whose displacement exceeds 1px with a seed
> shorter than half the longest member (room_0013's: 12px seed, 416px
> member, 3.75px), whether those runs reach `network.faces` or a paired
> segment, and confirm on s01/s02 that same-band members differ by ≤ 0.3px
> (the redundancy-collapse measurement in the CLAUDE.md prose) so the
> anchor change moves nothing there. Ship the ANCHOR change in this branch;
> if the both-ends measurement shows angled members surviving inside the
> tolerance, ship the both-ends offset test as a SEPARATE branch — bundled
> REVIEW deltas are unattributable. Pin the topology with a synthetic test
> in `tests/test_wall_network.py` beside `test_long_face_pairs_with_multiple_stubs`:
> a 12px stub face 3.75px off a 400px face, the stub FIRST in path order,
> both in the wall pen → the merged face lies on the long face's line, and
> through `detect_rooms` (a `rect_room` whose one band carries the stub on
> its room side) the room edge sits at the long face's standoff; prove the
> test fails on the reverted code (the run at the stub's offset, the room
> edge 3.75px high). Sweep the corpus in background sheet groups against
> `compare_sweeps` snapshots of the unmodified tree; run
> `tools/compare_room_shapes.py` on every sheet AND a polygon diff of every
> room between the two trees (the shape tool prints only IoU < 0.995 — s03
> room_0008's 44 px² and room_0015's 134 px² moves never printed under Gap
> C; a `sys.path`-switched `run_heuristics` dump per tree, as in the Tooling
> section, sees them all); render `tools/room_shape_crop.py` for every
> changed room after `compare_sweeps`; reseed the room-label cache of any
> sheet whose outlines changed; stop at the report with the net phantom
> count. The corpus baseline is red on the same 11 sheets (71 returned-FP
> lines) — attribute by revert + re-sweep or a detached worktree of `main`,
> never by assuming. Do not start Gap D or the candidate-key conflation in
> the same branch.

## Outcome of the anchor iteration (2026-09-02, `fix/collinear-merge-anchor-line`)

Measured first (scratch re-walk of the merge on s01–s04, s08, s12, s14, s17,
s18, s20; 4,223 merged runs with ≥ 2 members, instrumented copy validated
byte-for-byte against the real function on every sheet):

- Seed ≠ longest member in 1,276 runs; displacement between the seed's line
  and the longest member's > 1px in 92 runs with the seed under half the
  longest's length — 61 in the strong-face merge, 52 reaching
  `network.faces`, 41 a paired segment. Per sheet: s01 1, s02 6 (+14 weak),
  s03 7 (+2 weak, +1 centerline), s04 4, s08 3, s12 1, s14 1 (+6 weak),
  s17 15 (+3 weak), s18 21 (+1 weak, +1 stair, +3 centerline), s20 2.
- Least-squares vs longest-member line: they differ by p90 1.3–2.0px on the
  face merges of every sheet (stubs pull the LSQ line off the drawn face), so
  the longest member was chosen; the LSQ line lies on no drawn line.
- "Same-band members ≤ 0.3px" does NOT hold for faces: s01 356/391 face runs
  have a member > 0.3px off the longest (its 45° hatch chains at the 4.05px
  pitch straddling the 4px tolerance, 3.91/4.09); s02 36/255, s03 55/145.
  It holds for the centerline merge on s02 (max 0.13px), not s01 (2 runs at
  1.5px). So the anchor change MOVES rooms on both reference sheets.
- Angled population (offset at p1 within tolerance, at p2 outside): 197
  members, 164 of them s01's hatch strokes that never reach faces; 9 reach
  faces or a segment (s02 idx 1856, a 1,398px fill face 5px off over its
  length; s17 idx 19123, 106px weak, 5px; s18 idx 124570, 156px, 6px). The
  both-ends test is warranted but small — its own branch.

Shipped form and its sweep: see the status note at the top. Pictures and
diffs: `outputs/compare/anchor-line-report/` (crops per room, sweep reports,
`room_polygon_diff.txt`, and the two rejected variants' polygon diffs).

What follows from it, each its own iteration:

1. **The anchor should be the member line with the most collinear ink
   support, not the longest member.** s03 room_0013's top band: the run
   {15467 (68px face at y=1236.42), 20337 (141.8px window-board line at
   1238.67)} — the face is collinear with 15464/15850 (96.7px), the fill
   outline 15021/15027 (82.7px) and 15033 (108.7px) at 1236.42, ~440px of
   support against 141.8; the longest-member rule moved the edge 2.25px into
   the room. s01's jamb nib {2448 (19.25px at 1142.5), 3065 (32.75px stringer
   at 1139.75)}: 2449 (215.7px) continues 1142.5 across the doorway. The
   underlying flaw is the 4px offset tolerance admitting distinct parallel
   lines into one run at all; measure the support-vote before choosing.
2. **`WALL_MAX_THICKNESS_PX` vs a 37px cavity wall (s17).** The 1.75px band
   outer face 2171.92 / inner 2208.92 = 37.0px, paired only because the inner
   face was hung 1.5px off on a stub (35.5). With the true face it is over the
   cap, the thick tier wants hatch the cavity does not have, and the 21px
   pocket between each window's seal and the inner face line becomes a room
   (rooms 0015/0034/0036, ~3.1k px²). The blind-window rule
   (`ROOM_BLIND_WINDOW_MAX_AREA_PX2`) did not drop them — check how
   `window_openings` is counted for a pocket that only touches the seal's
   standoff.
3. **`_demote_lattice_faces` is direction-sensitive.** Reversing p1/p2 on
   runs whose LINE did not move (the rejected variant) newly demoted 57 faces
   on s18, among them the 1.75px wall belts at y 800–843 and 1271–1292
   (x 1841–2578), and 5 confirmed rooms merged away; with direction kept, 15
   non-wall faces. Rung grouping/walking should not depend on which face is
   the angle group's reference (walls.py ~2247–2264).
4. **Both-ends offset test** (R2 proper) — the 9 network-reaching angled
   members above.

## Prompt for the next agent (the collinear-support anchor)

> Use `/fix-detection`. Continue on branch `fix/collinear-merge-anchor-line`
> — it holds UNCOMMITTED work in `detection/walls.py`
> (`_merge_collinear_segs`, plus its `trace` hook), `tests/test_wall_network.py`
> (two anchor tests beside `test_long_face_pairs_with_multiple_stubs`),
> CLAUDE.md (the seam sentence's anchor clause), `docs/hatch-cell-chords-handoff.md`
> (status note + "Outcome of the anchor iteration") and the promoted probes
> `tools/probe_merge_anchor.py`, `tools/diff_wall_network.py`,
> `tools/diff_room_polygons.py`, `tools/_corpus_page.py` and the extended
> `tools/room_shape_crop.py`; read those diffs first, then the R2 section, the
> Outcome section and the "Tooling that exists now" entries for the probes. The shipped form places a merged run
> on its LONGEST member's line, with membership untouched (re-projection after
> the passes converge, run direction kept — both are load-bearing: seeding
> longest-first or re-anchoring between passes fused s01's 5.75px jamb nib
> with a stair stringer, and taking the anchor's direction flipped
> `_demote_lattice_faces` on s18 and lost 5 confirmed rooms). It swept with no
> confirmed entity lost but is NOT a win: net phantoms +5 and two edges move
> the wrong way, because the longest member is not always the wall face —
> s03 room_0013's TOP band merges the 68px face 15467 (y=1236.42) with the
> 141.8px window-board line 20337 (y=1238.67); the face has ~440px of collinear
> ink at 1236.42 (15464/15850 96.7px, the fill outline 15021/15027 82.7px,
> 15033 108.7px, the demoted piece 20311 83px) and the board line has none, yet
> the room edge moved 2.25px INTO the room (−877 px²; room_0016 −878 the same
> way). s01's nib {2448 19.25px at 1142.5, 3065 32.75px stringer at 1139.75}:
> 2449 (215.7px) continues 1142.5 across the 59px doorway. The convention: a
> run lies on the member line the DRAWN INK agrees with — the member whose
> line carries the most collinear face length on the page, not the longest
> member and not the first in path order. Measure FIRST with
> `python tools/probe_merge_anchor.py sNN --support --list --json …` on the
> same ten sheets (s01–s04, s08, s12, s14, s17, s18, s20; it reads the
> `trace` hook of `_merge_collinear_segs`, so it sees the real membership):
> for every run whose member lines disagree by > 0.3px (1,276 runs have seed
> ≠ longest; the 0.3px is s02's same-line jitter, the hatch-chain population
> on s01 sits at 3.9–4.1) it scores each candidate member line's support =
> total length of strong stroked faces plus wall-fill outline faces (never
> weak/hairline pieces — a window board can be a hairline) lying within
> 0.3px of that line, for reaches of the run's extent ± 0, 50, 100, 200px
> and the whole page (on s01 the support winner differs from the longest
> member in 6 / 10 / 18 / 30 / 83 of 356 scored runs); tabulate from the
> JSON which reach makes the support winner agree with the drawn face on
> the known cases (s03 room_0013
> top band → 1236.42; s03 room_0013 bottom band, Gap C's case, → the 416px
> face; s01 nib → 1142.5; s17's inner face → 2208.92; s01 WETROOM top edge and
> s03 room_0000 left edge → the faces the longest-member form already chose)
> and how often the support winner differs from the longest member across the
> corpus; beware that on a rectilinear plan every window on one wall puts its
> board line at the same offset, so a page-wide vote counts all of them — the
> table decides the reach, not a guess. Then replace the longest-member choice
> with the support winner (ties → longest), keep the after-convergence
> re-projection and the direction rule, keep both existing tests (they must
> still pass: a 400px face is its own support) and add one beside them: a
> 68px face at y=100 merged with a 142px parallel line at y=102.25, plus a
> 100px collinear piece of the face beyond a 60px gap, both in the wall pen →
> the run lies at y=100, and through `detect_rooms` the room edge sits at the
> face's standoff; prove it fails on the longest-member code (run at 102.25).
> Sweep against `compare_sweeps` snapshots of MAIN (not of this branch; the
> baseline is red on the same 11 sheets, 71 returned-FP lines, attribute by
> revert + re-sweep, never by assuming), in four background groups (s18; s16
> s11 s15; s01–s07; the rest — a foreground full sweep exceeds the tool
> limit), diff the verdict reports section-wise, run
> `tools/compare_room_shapes.py` AND `tools/diff_room_polygons.py` on every
> sheet (the shape tool prints only IoU < 0.995; the polygon diff is the
> only thing that saw s03's 44 px² and 134 px² moves), render before|after
> crops with `tools/room_shape_crop.py` (it matches the counterpart by IoU;
> `--only after` for an ADDED room), and when a room merges or a phantom
> appears, run `tools/diff_wall_network.py sNN X0 Y0 X1 Y1` (working tree vs
> `main`) or `… --idx N` before reading verdict lines — that diff, not the
> report, found every mechanism this iteration. Expect
> and REPORT, do not fix: s17's three window-reveal slivers (rooms
> 0015/0034/0036) persist under any correct anchor because the true cavity
> band is 37.0px, over `WALL_MAX_THICKNESS_PX` — the cap / blind-window
> counting is its own iteration; check whether s18's ramp strip (room_0000)
> and the legend box at (2126,2532) still appear once small hairline runs sit
> on their support lines. Reseed the room-label cache of every sheet whose
> outlines changed (`python app.py extract fixtures/sheets/<sheet>.pdf --out
> <dir> --ceiling-height 2.4 < /dev/null`; there is no `timeout` command on
> this Mac). Stop at the report with the net phantom count and the per-room
> verdicts; do not commit, do not start the both-ends test, the lattice
> direction sensitivity, Gap D or the candidate-key conflation in the same
> branch.

## Outcome of the collinear-support anchor (2026-09-02, same branch)

Measured first (`tools/probe_merge_anchor.py --support --json`, ten sheets,
reaches 0/50/100/120/150/200/page, unfiltered and pen-compatible support;
tabulation in the CLAUDE.md seam sentence):

| known case | must land on | 0 | 50 | 100 | 120 | 150 | 200 | page |
|---|---|---|---|---|---|---|---|---|
| s03 room_0013 top band {15467, 20337} | 1236.42 (face) | ✓ 360 vs 142 | ✓ | ✓ 661 | ✓ | ✓ | ✓ | ✓ 1177 |
| s03 room_0016 top band {15474, 15476, 15855} | 2186.17 | ✓ 593 vs 176 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| s01 jamb nib {2448, 3065} | 1142.5 | ✗ 19 vs 33 | ✗ | ✓ 235 vs 33 | ✓ | ✓ | ✓ | ✓ 445 |
| s01 WETROOM top edge {331, 941} | 917.75 | ✓ 186 vs 20 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| s03 room_0000 left edge {12, 130, 136} | 646.42 | ✓ 462 vs 33 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| s17 inner face {11815, 11817, 11825} | 2208.92 | ✓ 566 vs 346 | ✓ 566 vs 439 | ✓ | ✓ | ✓ 566 vs 530 | ✓ 566 vs 530 | ✗ 1116 vs 1939 |
| corpus: winner ≠ longest (reaching a segment) | | 101 (42) | 219 (53) | 253 (66) | 294 (69) | 313 (75) | 357 (86) | 581 (137) |

100–200 hold every case; 150/200 thin s17's margin to 1.07× and add a
714-vs-713 coin flip on a doubled s17 line (1547,2377)-(1547,2207); the pen
filter moves ~14 of 253 overturns and no known case. 120px = a 1000mm door
opening at 1:50 (118px) — s01's 921mm doorway is 59px only because its world
is 1:92 detected at identity — so the reach is W-class.

Shipped: `_support_anchor` (walls.py, before `_merge_collinear_segs`), the
`support=` parameter (the page's strong faces for the strong/weak/stair
merges, `[]` for centerlines), `WallGates.WALL_ANCHOR_SUPPORT_REACH_PX`. The
probe's per-run winner at 120px equals the shipped anchor on every scored run
of s03 and s17 (0 mismatches).

Sweep against MAIN (four background groups; `outputs/regress_baseline/` is
now main at `eacefe8`): verdict reports byte-identical on s01–s07 and
otherwise differ only by the five REVIEW rooms; 71 returned FPs before and
after; 0 lost. `tools/diff_room_polygons.py`: 91 outlines changed, 5 added,
0 removed; s06/s07/s09/s10/s13/s14/s19 IDENTICAL. Room-label caches reseeded
for the 13 sheets that moved (s01–s05, s08, s11, s12, s15–s18, s20).

Per-room verdicts (crops in `outputs/compare/<slug>/page_01_shape_*.png`):

- s17 room_0022 SH/WC (146×233px, 0.90) — REAL, split off the landing
  (room_0020 → 0026 −35k px²). Win pending the user's verdict; its
  bottom-right swing square is still fenced out.
- s17 rooms 0015 (148×21) and 0034 (21×147), ~3.1k px² — window-reveal
  slivers, PHANTOM, expected: the cavity wall's true inner face is 37.0px
  from the outer one, over `WALL_MAX_THICKNESS_PX`; room_0036 of the
  longest-member form no longer appears.
- s18 room_0000 (67×475, 0.69) — the external ramp between its balustrades,
  PHANTOM (circulation, not a room; the user's call). Same as the
  longest-member form; the returned legend-box FP at (2126,2532) is gone.
  Mechanism (`diff_wall_network.py s18 --idx 1508 2984 3169 --base-dir
  <main worktree>`): its bottom seal, the 70.7px landing edge across the ramp
  at y=990.23, has identical geometry in both trees but is `[lattice out]`
  on main and `[lattice kept]` on the branch — a neighbouring rung of the
  balustrades' striped field moved by the vote and broke the equal-pitch
  chain. `_demote_lattice_faces` is sensitive to sub-px rung positions as it
  is to run direction (item 3).
- s15 room_0016 (132×43, 0.675) — PHANTOM, NEW, the vote's own limitation:
  s15 draws dashed boundary lines as separate 14.8px strokes in a 2.0px pen
  (paths 52384–52542), each admitted as a strong face; a 59px wall face
  (5465/5467, 3.0px, y=1529.42) merged with three of them at 1531.17 and ~20
  collinear dashes within reach (~300px) outvoted its 59px, so it moved
  1.75px onto the dash row's line and the pocket between the two dash rows
  sealed. Five neighbouring rooms (0012–0015) also grew 3.5px because the
  970px band face {3912, 41704} moved from 1494.17 onto 41704's line at
  1497.67 — onto the drawn wall line (crop of room_0014), a correct move.

Net: +5 REVIEW rooms vs main, of which 1 real, 2 expected slivers (cap
iteration), 1 ramp (user's call), 1 new phantom (dash rows). Against the
longest-member form: −1 sliver, −1 returned FP, +1 dash-row phantom, and the
two wrong-way edges (s03 room_0013/0016) fixed.

What follows, each its own iteration:

1. **Drawn dash rows are not faces.** A collinear row of ≥ 3 equal short
   pieces at equal gaps (s15: 14.8px strokes at 7.3px gaps, 2.0px pen) is a
   dashed line the exporter emitted as strokes — annotation, never a wall
   face. Recognise it beside `_dimension_line_indices` (a pre-pairing
   exclusion), which also removes it from the vote. Measure on s15 how many
   rows exist and on s01/s02 that no wall face is a row.
2. **`WALL_MAX_THICKNESS_PX` vs the 37px cavity wall** (s17 slivers) — as
   before.
3. **Lattice direction sensitivity**, the both-ends test — as before.
4. `tools/diff_wall_network.py`'s default base tree runs without the
   fixtures symlink (s18 at f=1.0 there) — pass `--base-dir`.

## Prompt for the next agent (the s17 window-reveal slivers)

> Use `/fix-detection`. Branch from `main` (the collinear-support anchor is
> merged). Target: s17 rooms 0015 and 0034 — two 21px-deep, ~3.1k px²
> phantom pockets (bboxes [3434,2186]–[3582,2207] and
> [1548,2766]–[1569,2913], conf 0.85) lying INSIDE the 1.75px-pen cavity wall
> whose outer face is y=2171.92 and inner face 2208.92 (37.0px; the third
> sliver of the longest-member form, room_0036, no longer appears). Read
> "Outcome of the collinear-support anchor" and the CLAUDE.md seam sentence
> first, then measure before proposing anything — three mechanisms stack
> here and the fix must be the generic one, not a cap nudge: (1) the band is
> over `WALL_MAX_THICKNESS_PX` (36px at f=1.0; s17 runs at identity), so its
> two faces no longer pair and no solid seals the cavity — the thick tier
> (36–48px) wants `_band_has_wall_material` hatch between the faces and
> `_claims_interior_pair`, and a cavity wall drawn leaf/cavity/leaf carries
> its insulation hatch only at the jambs (measure the band's marks per 100px
> with `_collect_material_marks`, and whether the LEAVES pair at leaf
> thickness inside it); (2) no window is detected on either pocket — the
> glazing lines above room_0015 (the crop
> `outputs/compare/support-anchor-report/s17_page_01_shape_room_0015_zoom.png`)
> are strong faces that form the pocket's outer edge, and the nearest window
> entity, window_0008 at [3101,2179]–[3191,2209], is 240px away — so
> `window_count` is 0 and the blind-window rule never sees a window; (3)
> both pockets carry `door_openings: 1` although the nearest door entity is
> 170px+ away (door_0026 [3287,2379]–[3377,2470]; door_0033 for room_0034):
> the rejected door candidate at [3594,2190]–[3696,2196] (102×6px, final
> conf 0) sits 12px from room_0015's end and its `ROOM_OPENING_SEAL_PX` plug
> tail reaches the pocket, so `door_count` is 1 and BOTH the blind-window
> drop and `_is_wall_recess` (door_count == 0 required) are vetoed. Confirm
> (3) by monkeypatching `_free_space_components` to capture the `door_geoms`
> within `ROOM_CONTACT_TOL_PX` of each pocket and the confidence detect_rooms
> saw for that candidate — detect_rooms consumes candidates before the
> offline floor, so a candidate the pipeline rejects can still seal. The
> drawing convention to key on: a door-less, window-less pocket lying
> ENTIRELY inside a wall band's thickness — between the band's outer-line
> ink (glazing, sill) and its inner face, at most one band deep, no text —
> is wall material, never floor (the recess rule's premise, extended from
> "in the band's plane" to "inside the band"); and an opening the pipeline
> rejects should not count as an opening for those two drops. Measure the
> candidate rule on the true class (every real window-bearing room on
> s01/s02 is ≥ 17k px² and carries a confident door; s01 has real blind
> window-less rooms at 3.3–8.5k px² that must stay) and on the corpus's other
> cavity walls (s02's leaf/cavity/leaf party wall). Write the synthetic
> test first (a 37px band drawn as two 1.75px leaves with hatch only at the
> jambs, a window's glazing lines inside it, no door: the pocket must not be
> a room), prove it fails on main, then sweep against `compare_sweeps`
> snapshots of MAIN in four background groups (s18; s16 s11 s15; s01–s07;
> the rest), diff the verdict reports section-wise, run
> `tools/diff_room_polygons.py` on every sheet, crop with
> `tools/room_shape_crop.py`, and for any room that merges or appears run
> `tools/diff_wall_network.py … --base-dir <fixtures-linked worktree>` —
> NOT the default temp base, which loses the stored scale (s18 ran at
> f=1.0 there). Reseed the room-label cache of every sheet whose outlines
> change. Stop at the report with the net phantom count and per-room
> verdicts; do not commit; do not touch the dash rows, the lattice
> direction sensitivity, the both-ends test, Gap D or the candidate-key
> conflation in the same branch.

## Outcome of the s17 window-reveal slivers (2026-09-03, branch `fix/s17-cavity-wall-pockets`, not committed)

Measured first (scratch probes over the corpus, replicating `run_heuristics`
up to `detect_rooms` with `_free_space_components` / `_restrict_swing_plugs`
captured; prototype rule evaluated on every emitted room of all 20 sheets):

- The cavity wall is FOUR lines in the 1.5px pen — 2171.92 / 2183.67 /
  2195.67 / 2208.92 — and every adjacent pair pairs as its own segment
  (outer leaf 11.75, cavity 12.0, inner leaf 13.25); the 37px outer/inner
  pair is over the cap and the band carries 0 diagonal marks (34 marks in
  600px, none diagonal), so neither the thick nor the through tier could
  pair it. At each window the two middle lines stop, the glazing runs
  mid-leaf (2177.17, 5.25px in from the outer face) in the continuous outer
  leaf, and the reveal between 2183.67 and 2208.92 — a 25.25px strong pair
  that `_claims_far_side_pair` drops (the outer-leaf pair shares 2183.67 on
  the far side, no fill/hatch in the band; its docstring's "an unhatched
  cavity is a closed sliver the room stage erodes away" holds only under
  2 × `ROOM_GAP_CLOSE_PX`) — is the 21px pocket.
- Mechanism (3) confirmed: room_0015's only counted door is door_0039, a
  0.48 `single_line_leaf` (in_wall) lying in the NEXT reveal (3594–3696),
  whose full-cover plugs' 12px tails reach x=3581.7 and fence the pocket's
  end (distance 0.00); room_0034's is door_0042, a 0.35 `arc_fallback`
  1.4×44px sliver in the cavity whose four full plugs pass the in-wall gate
  (distance 0.00). Both are under the 0.55 offline floor.
- The collinear-gap recess rule already fits room_0034 once the door no
  longer counts (its inner-leaf pair resumes on both sides of the window);
  room_0015's inner pair resumes on the LEFT only — the next window's reveal
  adjoins it across a 6px jamb block — so the recess rule cannot see it.

Shipped (rooms.py only; the wall network is untouched):

1. `ROOM_ENTRANCE_MIN_CONFIDENCE` (= `ROOM_BBOX_SEAL_MIN_CONFIDENCE`, the
   offline floor's mirror): the blind-window drop, `_is_wall_recess` and the
   new rule count ENTRANCES — seals of doors at/above the floor — while
   `door_openings` and confidence still count every seal. Corpus-wide 16
   rooms carry only sub-floor doors; none changes verdict (the nearest is
   s17 room_0018, confirmed, 13.3k px² with a window and a 0.35 door, 1.33×
   over the 10k blind cap).
2. `_is_band_pocket` (`ROOM_BAND_POCKET_FACE_COVER_MIN` 0.65): both long
   edges of the component's minimum rotated rectangle lie at the barrier
   standoff along wall faces (barrier-face extents or segment flanks), and
   the faces' spacing is ≤ `WALL_MAX_THICKNESS_PX` — two faces that could
   have paired as one wall. Corpus-wide the signature matches exactly rooms
   0015/0034. The narrowest confirmed room is s11 room_0018, a 19px-wide
   "storage in utility" at f=0.5 whose faces sit 21.75px apart against the
   scaled 18px cap (1.2×); every other confirmed room is ≥ 52px wide at
   identity (s01 room_0003).

Tests: `TestBandPocket` (the four-line cavity wall with a reveal running to
the wall's end, glazing at s17's 5.25px offset, cavity-closer hatch at the
jambs only; the rejected-door plug case; labelled pocket stays; a 48px strip
stays) and `TestRejectedDoorIsNotAnEntrance` (closet with a 0.48 doorway
plug + window is blind; at 0.67 it stays). All three failing tests fail on
main for the right reason and pass with the fix; reverting the code fails
them again.

Sweep against MAIN (four background groups, snapshots of main at `b799874`):
every verdict report byte-identical except s17, where REVIEW rooms 0015 and
0034 are gone and the real SH/WC split (now room_0021) remains; 71 returned
FPs before and after, 0 lost, REVIEW 7 → 5. `tools/diff_room_polygons.py`:
19 sheets IDENTICAL, s17 2 removed / 0 changed. Net: −2 phantoms, +0.

**Ordering decision (user, 2026-09-03): the W-gate recalibration goes
FIRST** — `docs/w-gate-recalibration-handoff.md`, "Status 2026-09-03" and its
prompt. Every item below except the dash rows is a threshold rule on a
W-class constant calibrated at identity on s01's 1:92.2 ink, and would be
tuned twice otherwise. The s17 SH/WC verdict (`python tools/review.py s17`)
is independent and can be recorded any time.

Knife-edges found, each its own iteration:

- Synthetic fixture: with the glazing line at 105.9 (5.9/5.85px from the
  outer leaf's faces) `_demote_lattice_faces` demoted the WHOLE cavity wall
  (five rungs at "equal" pitch with tolerated 2×-pitch gaps), at 105.25
  (s17's own 5.25/6.5 offsets) it did not — the lattice rule's equal-pitch
  test is sensitive to a mid-leaf glazing line, the same knife-edge as its
  direction/position sensitivity (item 3 above).
- The 11 recorded-FP pockets on s11/s12/s16/s18 (door-less, textless, both
  long edges on faces, 20–31.6px wide at f=0.5) are the same class one band
  deeper — 1.2–2× the scaled cap, in the same width range as the confirmed
  s11 storage cupboard (21.75) — so a rule reaching them needs a second
  discriminator (e.g. a glazing/board line inside the adjacent band, or a
  collinear wall segment running into the pocket's end).
- `tests.test_takeoff_fn_equivalence` fails on main and on the branch alike
  (field='warnings': `TAKEOFF_REGIONS_UNCLASSIFIED` in the function arm
  only) — pre-existing, unrelated.

Room-label cache: the s17 reseed (`python app.py extract … --ceiling-height
2.4 < /dev/null`) first hit `ROOM_LABEL_FAILED` — "Reauthentication is
needed. Please run `gcloud auth application-default login`" (an expired ADC
surfaces only there, exit code 0) — and succeeded after the login: a new
`.room_labels_cache/s17-…-7a6a5b8ea8e08349-v1.json` entry, 20 of 35 rooms
named, and the offline sweep no longer warns `ROOM_LABEL_NO_GEMINI`.

## Queued after it (drawn dash rows — s15 room_0016)

The vote's own limitation, one iteration after the slivers: s15 draws its
dashed boundary/demolition lines as SEPARATE 14.8px strokes at ~7.3px gaps in
a 2.0px pen with an empty dash attribute (paths 52384–52542 around
[263,1484]–[1514,1531]; `_is_dashed` never sees them), each above
`WALL_FACE_MIN_LEN_PX` and therefore a strong face. A 59px wall face
(5465/5467, 3.0px, y=1529.42) merged with three dashes at 1531.17, ~20
collinear dashes within one reach (~300px) outvoted its 59px, the face moved
1.75px onto the dash row and the 132×43px pocket between the two dash rows
(room_0016, 0.675) sealed. The convention: a collinear row of ≥ 3 near-equal
short pieces at near-equal gaps no longer than a piece is a DRAWN DASHED LINE
— annotation, never a wall face (a wall face interrupted by text masks is
pieces of unequal length at one or two gaps; a row of jamb nibs is never
collinear). Recognise it beside `_dimension_line_indices` as a pre-pairing
exclusion (which also removes it from the vote and from face collection);
measure on s15 how many rows exist and what they annotate, on s01/s02 that
no wall face is such a row, and on s18/s20 (vector-text sheets) that glyph
strokes are not caught twice. Expect s15 rooms 0012–0015 to keep their
+3.5px (that move was the 970px band face {3912, 41704} landing on its drawn
line) and room_0016 to vanish.

## Queued after it (the candidate-key conflation in `_fill_seams`)

`_fill_seams` keys candidate edges by their INTEGER-rounded endpoints, so a
ring thinner than 1px whose two long edges round to the same y shares one key
between its diagonal and both long edges (and their twins), and `members[0]`
— path order — decides which edge geometry is probed: a long edge probes
one-sided and the sliver stays un-united. Measured 2026-09-02: 9 of s04's 70
twice-drawn red slivers and 9 of s08's 72 (61/63 diagonals recovered of
70/72); no room changed on either sheet, so this is telemetry, not a symptom.
Candidate rule: probe every distinct member geometry under a key (a seam if
ANY passes), or key on the edge's own midpoint/angle rather than rounded
endpoints. Measure the conflated-key population corpus-wide before touching it.

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
