# Step 16 scratch tooling — what makes s11's storage a space when a hollow wall is not (2026-09-06)

- `backing_census.py` / `backing_census_{a,b}.json` + `.txt` — the stage-5 chain through the
  harness with a tap on `rooms._is_band_pocket` (every call, with the rule's verdict) and the
  free-space tap reading detect_rooms' own `face_lines` / `cap_lines` / `wall_segments` /
  `solid_parts` / `solids` / `network` / `door_barriers`; every call and every emitted room read
  for the brief's four discriminators — (a) text spans and vector-text glyph strokes inside
  (`walls._vector_text_indices`), (b) the wall SOLID behind each long side (a probe line 7px
  outward, and the median span of contiguous solid a ray enters, segment solids and other solids
  apart), (c) the pens of the covering network faces, (d) the END runs read the same way — plus
  (e) whether a bounding face pairs, along its own run or as a resuming segment's flank, with a
  partner on the pocket's side. `BACKING_CENSUS_OUT` names the output so two jobs run at once.
- `backing_census_key.json` — the first runs on s11 and s17 only.
- `summarise16.py` → `summary16.md` — the report's tables over those JSONs.
- `s11_storage_probe.py` — what bounds the storage on each side: the wall segments, network faces
  and drawn paths within 40px (the partition 8387/8388, the front line 8383, the bands 8346/8347
  and 8333/8335).
- `s17_strip_lines.py` — the drawn vertical lines, segments and merged faces around strip 0013
  (paths 2697 / 2756 drawn only along the strip; the inner leaf pair 2753/2754 on the room side).
- `end_runs_probe.py` — the END runs of the key components with the union-projection closure at
  probe depths 6 and 7 (identical), the reading the rule implements.
- `zoom16.py OUT [tag]` / `zoom16_true.py OUT` — the report's context crops: the component (red)
  with the stage's segment solids (blue), other solids (light blue), paired faces (green), lone
  faces (orange), door seals (magenta) and window seals (cyan).
- `ceiling_census16.py` / `ceiling_census16_{a,b}.json` + `.txt` — the rule AS IMPLEMENTED with
  the end-closure exemption ON and OFF at ceilings 36 / 40 / 41 / 44 / 48 / 56 (× f) for the rule
  alone on every sheet: every component newly dropped or un-dropped with its ground-truth class,
  rooms gone / new / moved, scores.
- `rooms_step16_closure.diff` — the exemption alone (the bite check reverts it);
  `rooms_step16_ceiling.diff` — the ceiling move alone (the separate change).
- `sweep_base_g{1..4}.txt` / `sweep_base_raw.txt` / `sweep_base_verdicts.txt` — the baseline
  sweep of the step-15 tree in four background groups (verdict lines byte-identical to step 15's
  after-sweep); `sweep_closure_*` — the same with the exemption at the 36 ceiling;
  `sweep_ceiling_*` — the same with the ceiling at `WALL_THICK_MATERIAL_MAX_PX`.
- `unittest_full.txt` — the fast tier after the exemption (1443 tests, OK).

Run from the repo root with `.venv/bin/python`. A background job imports the tree at launch:
never edit a constant while one is running. The harness cache is `tools/census_scratch/cache/`
(delete a slug's pickle after any scale change).
