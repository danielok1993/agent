# Review prompt — verify the step-9 claims independently

You are reviewing another agent's measurement-only checkpoint in this
repository (`/Users/danielszweda/Documents/GitHub/UD/agent`, branch
`recal/s01-true-factor`, off commit a3ec9e8). The agent changed NO detection
code, ground truth or manifest; it wrote `docs/w-gate-iter3-checkpoints/step-9.md`
(the report), two PNGs beside it, an appendix to
`docs/w-gate-recalibration-handoff.md` ("Outcome — iteration 3, step 9" and
"Step-9 decisions and the jamb-seek census"), and its scratch tooling under
`tools/census_scratch/step9/` (see its `README.md`). Your job is to re-derive
every numbered claim below with your own runs, not to trust the report, and
to say for each: CONFIRMED (with your numbers), REFUTED (with your numbers
and where the agent went wrong), or UNVERIFIABLE (why). Then judge the
recommendation (claim 9) on its merits, including whether a generic rule the
agent missed would change it.

Read first, in this order: `CLAUDE.md` (the "Room detection" and "Wall/room
world-space gates" paragraphs), `docs/w-gate-iter3-checkpoints/step-9.md`,
`step-8.md`, `step-3.md`, `docs/regression-testing-guide.md` §9 §10 §12 §13,
`scale/factor.py::_gate_denominator`, `detection/rooms.py::_door_plugs`
(and `_restrict_swing_plugs`, `_swing_hinge_edges`, `_plane_stamp`,
`_clip_plug_tails`), and the room stage's wall-pen block in
`detection/rooms.py::detect_rooms` (search `ROOM_WALL_PEN_MIN_FRAC`).

## Environment rules (learned the hard way; do not skip)

- `python` is not on the shell path: use `.venv/bin/python` (absolute path
  in background commands; the cwd resets between commands). macOS has no
  `timeout`. The venv lacks InquirerPy (ignore the two import errors in the
  fast tier). `test_takeoff_fn_equivalence`'s `warnings` field fails on the
  untouched tree (a region-cache mismatch, pre-existing).
- The corpus PDFs are under `fixtures/sheets/` (NDA, never commit one). The
  harness `tools/census_scratch/harness.py` runs the stage-5 chain exactly as
  `tools/regress.py` does (labels/schedules omitted) and caches each sheet's
  detection page in `tools/census_scratch/cache/<slug>.pkl`; `H.run(page,
  factor=...)` runs at any factor; `H.overrides(mult=...)` scales gate fields
  by MULTIPLIERS (never absolute px). `H.score(slug, page_number, ents)`
  matches against the committed ground truth (type + bbox IoU ≥ 0.5).
- Do not commit, do not edit `tests/ground_truth/*.json` or
  `fixtures/MANIFEST.json`, never `git stash`, never revert s01's stored
  scale (1:92.2). A full `tools/regress.py` exceeds a 10-minute foreground
  limit: run it as four background groups (`--sheet s18`; `--sheet s16
  --sheet s11 --sheet s15`; s01–s07; the rest), each with output redirected
  to a file. A re-sweep of a slug wipes `outputs/regress/<slug>/`; the
  baseline snapshots are in `outputs/regress_baseline/<slug>/2026-09-05_11-47-*`.
- The scratch scripts in `tools/census_scratch/step9/` are run from the repo
  root, e.g. `.venv/bin/python tools/census_scratch/step9/s01_profile.py`.
  Each writes/kept its output beside it (`*_out.txt`, `*.jsonl`) — regenerate
  rather than read, and diff against what is there.

## Claims to verify

1. **Baseline.** On a3ec9e8 the corpus sweep reads 0 LOST, 68 returned FPs
   (1 door, 48 rooms, 19 windows), 0 REVIEW, s09/s19 unlabelled.
   Evidence: `tools/census_scratch/step9/sweep_base_all.txt`. Re-run the
   four groups and count `FALSE POSITIVE RETURNED`, `LOST`, `REVIEW` lines.

2. **s01 at f = 50/92.2 on this tree** (harness, `H.run(page, factor=50/92.2)`):
   doors 11/11, windows 4/4, rooms 8/12, 18 unreviewed; the four LOST rooms
   are (1090,699)–(1142,876), (466,920)–(521,1056), (392,922)–(521,1387) and
   (1033,925)–(1142,1134); at identity the harness reproduces the sweep
   (12/12, 0 unreviewed). Evidence: `s01_leak_out.txt` (run `s01_leak.py`).

3. **The hall leaks through door_0002's TOP-edge (doorway) plug, not its
   right edge.** door_0002's bbox is (424.5,917.0)–(467.5,957.5), hinge
   edges {0 top, 3 right}. At identity both edges carry `interrupted` plugs;
   at 0.542 only edge 3 does. The 0.542 free-space piece connecting the hall
   and the living room is (412.0,912.9)–(463.1,918.8), 285 px², covered at
   identity 285/285 by door_0002's seal. The right edge (x = 467.5) lies on
   the CPD cupboard's wall face (464.4, y 957.5→1114.8) and its plug seals
   nothing between hall and living room; step-8.md's sentence "the hall
   door's right-edge plug now qualifies at 0.542 ... the leak is elsewhere"
   misidentified the doorway edge. Evidence: `s01_leak_out.txt`,
   `s01_profile_out.txt`. Check the drawn geometry: the hall/living wall face
   at y = 917.75 runs x 203.5→410.25 and resumes at 464.5 (`s01_profile.py`
   prints the faces near the jamb); confirm which bbox edge lies on it.

4. **The doorway profile at 0.542** (`_door_plugs` replicated by
   `s01_common.profile`, verify against the function itself): seal 8.13,
   half-width 2.71, anchor window 3 samples, step 4.23; samples from the
   corner outward at x 416.4 / 420.6 / 424.8 with distances 4.1 / 8.4 / 12.6
   to the material → start cover 1/3 < 0.5, no touch ≤ 2.71 → no plug. The
   dilated jamb material ends at x = 412.27 (the block's right face at
   410.25 buffered 2 px); the drawn jamb face is 14.25 px = 222 mm (at
   1:92.2, 0.16933 mm/px × 92.2) past the bbox corner. Passing needs a
   first sample within 2.71 px of 412.27, i.e. S ≥ 9.52 px at 0.542 = 17.6
   px at 1:50. Also confirm `ROOM_PLUG_HALF_WIDTH_PX` held at 5 does not
   rescue it (touch passes, cover stays 1/3) — the ablation line
   `loo:ROOM_PLUG_HALF_WIDTH_PX` in `../abl/s01_s01mode.jsonl` says lost 4.

5. **Corpus jamb-gap census** (`jamb_census.py` + `jamb_analyze.py`, at each
   sheet's detection factor; mm at the TRUE scale from
   `harness.TRUE_SCALE`): over the 198 kept `interrupted` plugs on ≥ 0.55
   doors (396 ends, 378 of which have material within 100 px), the
   distance from the bbox corner outward to the dilated material is median
   0 mm, p75 17, p90 34, max 219; the four largest are s01 door_0003 (219),
   door_0006 (203), door_0002 (203), door_0001 (187); next s05 door_0007
   135 mm, s17 110, s18/s08 102, s14/s02 85, every other sheet ≤ 51 mm.
   Note the census walks integer px from the corner, so s01 door_0002's 13 px
   here vs 12.2 px in claim 4 is the sampling, not a discrepancy. Evidence:
   `jamb_analyze_out.txt`.

6. **The 17 phantoms at 0.542 are the furniture pen becoming a wall pen.**
   (a) The 18 unreviewed rooms are: 12 cells of 0.24–0.38 m² (three sofa
   cushions at x 222–263, nine kitchen units along x 209–243 / y 860–894 /
   the tall cupboard at (486,872)), two slivers of 0.21 m², one 0.93 m² strip
   at (970,653)–(1082,687), two room splits (198,1086)–(384,1119) and
   (819,1144)–(1031,1179), and the real merged landing (1032,697)–(1142,1136).
   (b) None of the 17 is a free-space component at identity; each is fenced
   by NEW barrier at 0.542 whose faces/pairs are 100 % in pen (1.0, 0.0, 0.0)
   (`s01_phantoms_out.txt`; the pen check on the segments is in the report
   §2 — re-derive it). (c) Per-pen PAIRED stroked face length
   (`s01_pens.py s01`): red 2,203 px = 13.7 % at identity (not a wall pen)
   and 2,409 px = 15.2 % at 0.542 (≥ `ROOM_WALL_PEN_MIN_FRAC` 0.15 → wall
   pen); black 56.0 → 52.3 %, magenta 23.3 → 27.3 %, blue 6.9 → 5.2 %.
   (d) On every other multi-pen sheet the second pen is ≥ 34 % (s03 grey
   0.58, s04/s08 grey 0.6) or ≤ 10.4 % (s03 grey 0.73, s02 joinery 6.4 %,
   s17 orange 0.8 %) — `pens_corpus.txt`. (e) Red's longest paired run is
   109 px at both factors, black's 493–497, magenta's 567.

7. **Ablation** (`tools/census_scratch/ablate.py s01 s01mode`; this tree's
   log `tools/census_scratch/abl/s01_s01mode.jsonl` — move it aside to
   re-run, the script skips done labels): `only:WALL_MAX_THICKNESS_PX` →
   lost 4 (the three stair rooms + the living room by bbox) / 1 unreviewed;
   `only:ROOM_OPENING_SEAL_PX` → lost 2 (the hall + the living room by
   bbox) / 0; every other `only:` → 0/0; `loo:ROOM_OPENING_SEAL_PX` → lost 3
   / 18; `loo:ROOM_MIN_AREA_PX2` → 4 / 4; `loo:WALL_FACE_MIN_LEN_PX`,
   `loo:WALL_PAIR_MIN_OVERLAP_PX`, `loo:COLLINEAR_OFFSET_TOL`,
   `loo:WALL_THROUGH_HATCH_MAX_PX` → 1 unreviewed each (the phantoms are an
   interaction). Also: the 0.542 hall/living blob (209,412)–(521,1389)
   matches the confirmed living room (209,415)–(521,912) at bbox IoU ≈ 0.50.

8. **The jamb-seeking tail is refuted as a standalone fix**
   (`collinear_census.py` + `collinear_analyze.py`; NOTE its barrier-face set
   is an approximation — paired faces, stroked faces ≥ 0.75 × the stroke
   reference, wall_fill / material_backed faces, plus every segment's two
   flanks — not `rooms._barrier_extent`; check whether the approximation
   changes any conclusion below):
   (a) over the kept doorway ends, 310 of 396 have a collinear barrier face
   within 60 px, g median 2.3 px / p90 6.2 / max 57.8 (34 / 78 / 979 mm);
   (b) at 0.542 the hall door's nearest collinear barrier face along
   y ≈ 917.75 begins at x ≈ 389.5 (g ≈ 35 px ≈ 546 mm), because at identity
   the face run (410.25,917.75)–(203.5,917.75) has members {path 331, path
   941} — 331 is the jamb block's UNSTROKED bottom outline at y = 920.75,
   3.0 px off, absorbed by `COLLINEAR_OFFSET_TOL` 4 and re-projected onto
   941's line — while at 0.542 (tolerance 2.17) the run is
   (389.53,917.75)–(196.25,917.75) with members {333, 941}, path 331 is a
   separate unstroked unpaired face, and the block (faces 332 × 278, th
   20.5) is not a segment (it fails the thick-tier material gate: 4 marks,
   run 15.5 < 16.3, span 0.39 — step-3.md). Verify by listing
   `network.faces` near (390–410, 905–921) at both factors with their
   `indices`, `stroked`, `wall_fill`, paired status;
   (c) the false class: s17 door_0020 (0.95 single), hinge edge 3, has a
   collinear barrier face beginning 30.7 px = 520 mm beyond its open leaf's
   tip on the leaf's line, other end anchored — a seek reaching 546 mm
   would plug a 520 mm walkway there; (d) at the sheets' factors 134 ends
   have a collinear face beyond the seal within 60 px, ~40 under 300 mm,
   mostly fallback-tier (0.27–0.35) boxes; (e) the material-based
   alternative (extend to material ON the line) would reach the block's
   dilated solid at 12.2 px = 191 mm ONLY if the block pairs again, so the
   hall needs a hatched-pier rule AND a seek — two rules with one corpus
   instance each; s01 door_0015's piers (281 mm) at identity would swap a
   plane stamp for a plug (an f = 1.0 change).

9. **The recommendation.** Leave `_gate_denominator` as designed
   (`SCALE_FACTOR_MEASURED_ONLY`: a measured non-standard scale drives the
   takeoff, never the gates), because s01 at 0.542 is an outlier on three
   independent fronts (222 mm jamb gaps, a 242 mm hatched pier, a furniture
   pen at 15.2 % of the pairing) and each fix is a one-sheet rule; take the
   wall-pen discriminator (generic) and step 4 at identity next. Judge this:
   is there a drawing-convention rule the agent missed that fixes the hall
   or the phantoms generically (measure any candidate on the true class on
   at least two sheets, per the repo's generic-fix rule in
   `.claude/skills/fix-detection/SKILL.md`)? Is the pen-fraction knife-edge
   (13.7 % vs 15.2 % against 0.15) correctly attributed to the four scaled
   gates in claim 7, and would the candidate discriminators (hatched-band
   share per pen; longest paired run per pen) separate on s01 AND on the
   other multi-pen sheets? Is the report's "s01 door_0003/0006 doorway plugs
   anchor on a blue dimension line" residue real, and does it matter?

## Deliverable

A report with one section per claim (CONFIRMED / REFUTED / UNVERIFIABLE,
your numbers, your commands), any mistake in the agent's arithmetic or
attribution, and a one-paragraph verdict on claim 9. Do not change code,
ground truth or the manifest; put any picture you make under
`docs/w-gate-iter3-checkpoints/` with a `step9-review_` prefix and never
show a street address or planning-portal id. End with the numbers: lost,
returned FPs, new REVIEW lines (there should be none — no code changed), and
what you think should be next.
