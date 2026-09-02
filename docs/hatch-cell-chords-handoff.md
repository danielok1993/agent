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
merges. The "chords" were fill seams (see the R1 resolution note below). The
open residue is now **Gap B** (the chain split), spelled out in the prompt at
the end. Working tree also carries the user's own uncommitted
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
  `git apply x.diff`.
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

## Prompt for the next agent (Gap B — the chain split)

The R1 prompt that used to sit here was executed on 2026-09-02 (see the R1
resolution note and `9e86031`). The next iteration is Gap B:

> Use `/fix-detection`. Branch from `main` after `fix/hatch-cell-chord-faces`
> is merged (or from that branch if it is not). Read the CLAUDE.md "Room
> detection" seam sentence — from "and fill SEAMS never become faces" through
> its "Known gap" clause — then `docs/hatch-cell-chords-handoff.md` (R1's
> resolution note and this prompt), `_collect_fill_rings`, `_fill_seams`,
> `_fill_ring_components` and `_FillRing.is_marker` in `detection/walls.py`.
> Do Gap B only: a fill chain that returns EXACTLY to its own start vertex
> and then continues is two rings drawn back to back, not one — an exporter
> emits triangle 2 from triangle 1's start vertex, the six-edge chain
> revisits its start, shapely rejects the self-touching polygon,
> `_collect_fill_rings` drops both triangles and the seam is never found,
> so s20's chord (552,2892)-(730,2881) is still an unstroked wall-fill
> face. Close the ring at the exact return and start a new chain there.
> Measure FIRST with `python tools/probe_fill_seams.py sNN --list` on s20,
> s04, s08, s14, s18, s13, s11, s16 and s03: the split must touch zero rings
> that are valid today (it does on every sheet measured), and the recovered
> sub-rings per fill class are the blast radius — s20 19 grey wall-band
> chains → 38 rings of which 14 are marker-flagged (12×12 jamb stubs and
> 3–9×12 slivers split into ≤ 24px triangles that `is_marker` then treats
> as arrowheads: no barrier area, no wall-fill face rights, while their
> fill-only edges ARE faces today — watch for s20 room leaks at those
> stubs, and note `_fill_ring_components` unions seam-connected rings only
> AFTER the marker exclusion, so a triangulated stub cannot be rescued by
> the union as coded; if the sweep shows that leak, testing `is_marker` on
> the seam-united polygon rather than each triangle is the candidate rule,
> measured on the corpus's marker population before you write it); s04/s08
> 140/144 red (1,0,0) 0.63×29.5px demolition slivers → 280/288 band-shaped
> rings that would make red a RATED class (today unrated, permissive) —
> their edges are already `RR_Walls`-hinted 1.0px faces, so measure what
> the 280 new barrier polygons change; s18 399 chains → 239 black
> band-shaped rings; s14 77 → 113 (73 markers); s11/s16 4 → 22 marker
> rings; s13 2 → 4. Pin the topology with a synthetic test in
> `tests/test_wall_network.py` next to `triangulated_band_h`: a fill-only
> (stroke 0, colour None) six-edge bow-tie chain whose second triangle
> starts at the first's start vertex → two rings from `_collect_fill_rings`,
> the diagonal in `_fill_seam_indices`, no face on it in
> `detect_wall_network`, and the band's faces still pair at its thickness;
> prove the test fails on the reverted code. Sweep the corpus in background
> sheet groups against `compare_sweeps` snapshots of the unmodified tree,
> run `tools/compare_room_shapes.py` on every sheet, render
> `tools/room_shape_crop.py` for every SHAPE line (after `compare_sweeps`,
> which wipes `outputs/compare/<slug>/`), reseed the room-label cache of
> any sheet whose outlines changed, and stop at the report with the net
> phantom count. The corpus baseline is red on the same 11 sheets (R3) —
> attribute by revert + re-sweep, never by assuming. Do not touch R2, and
> do not add a stroked-chord rule: the chord probe found no such class on
> the corpus.
