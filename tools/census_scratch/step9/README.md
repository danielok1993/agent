# step 9 scratch tooling (W-gate iteration 3, 2026-09-05)

Measurement scripts behind `docs/w-gate-iter3-checkpoints/step-9.md`. All run
from the repo root with `.venv/bin/python tools/census_scratch/step9/<script>`
and import `tools/census_scratch/harness.py` (which caches each sheet's
detection page under `tools/census_scratch/cache/`). Nothing here is part of
the pipeline.

| script | what it measures | output kept beside it |
|---|---|---|
| `s01_common.py` | `run_tapped(page, factor)`: the stage-5 chain with taps on `_door_plugs`, `_clip_plug_tails`, `_plane_stamp`, `_folding_chain_gap_plug`, `_free_space_components`; door seals keyed by bbox; `profile()` replicates `_door_plugs`' per-edge numbers | — |
| `s01_leak.py` | s01 identity vs 0.542: scores, rooms, every door's final seal, and the LEAK pieces (0.542 free space outside the identity rooms touching two of them) attributed to identity barrier | `s01_leak_out.txt` |
| `s01_profile.py` | the hall door's edge profiles at both factors + material near its left jamb | `s01_profile_out.txt` |
| `s01_phantoms.py` | every unreviewed s01 room at 0.542: identity component? which NEW barrier (segments/faces/pens) fences it | `s01_phantoms_out.txt` |
| `s01_pens.py [slug]` | per-pen PAIRED face length (the `ROOM_WALL_PEN_MIN_FRAC` input) at identity (and 0.542 for s01) | `s01_pens_out.txt`, `pens_corpus.txt` |
| `jamb_census.py` / `jamb_analyze.py` | every door edge end: distance from the bbox corner outward to the dilated material (integer px), in mm at the sheet's TRUE scale | `jamb_census.jsonl`, `jamb_analyze_out.txt` |
| `jamb_seek_census.py` / `jamb_seek_analyze.py` | same, plus an along-line run — NOTE: the run is capped by `_door_plugs`' local material clip (SEAL + NEAR + 4 px) and its `on_run` metric is not meaningful; kept for the record | `jamb_seek.jsonl`, `jamb_seek_analyze_out.txt` |
| `collinear_census.py` / `collinear_analyze.py` | every door edge end: the nearest BARRIER face collinear with the edge beginning outward from the corner (g), at the sheets' factors and s01@0.5423 — the jamb-seek discriminator. Barrier faces are approximated (paired, or stroked ≥ 0.75×ref, or wall_fill/material_backed, plus segment flanks), not `rooms._barrier_extent` | `collinear.jsonl`, `collinear_analyze_out.txt` |
| `crop_s01.py` | the two step-9 PNGs | `docs/w-gate-iter3-checkpoints/step9_*.png` |
| `ablate.py s01 s01mode` (parent dir) | per-constant ablation at 0.542; this tree's log is `../abl/s01_s01mode.jsonl` (the step-3 tree's is `../abl/s01_s01mode_step3tree.jsonl`) | `ablate_s01mode.txt` |
| — | the four baseline sweep reports concatenated | `sweep_base_all.txt` |
| `material_seek_probe.py [slug[@factor] ...] [--cap-mm N]` (post-review) | every un-anchored HINGE-edge end of a ≥ 0.55 single: nearest touch outward against the FULL barrier union minus the door's own seal (door/window-seal hits are artifacts — the rule would use wall material) | `material_seek_probe_corpus.txt`, `material_seek_probe_s17_s01.txt` |
| `seek_census.py [slug[@factor] ...]` (step 10) | the material-seeking tail AS IMPLEMENTED: every door on every sheet at its factor (+ s01@0.5423), `_door_plugs` re-run on the exact pipeline inputs with and without `_seek_edges(c)`; every edge whose plug outcome differs, with the seek's hit distance (px, mm at true scale) and the material at the hit | `seek_census_out.txt` |
| `crop_step10.py` (step 10) | the two step-10 s01 pictures (old rule vs the seeking tail at 0.542; `_seek_edges` patched off for the "before" panel) | `docs/w-gate-iter3-checkpoints/step10_s01_*.png` |

The `*.jsonl` census files are gitignored (0.8 MB each); every script above
regenerates its own from the harness cache, and an independent review
(2026-09-05) found the regenerated data byte-identical.
