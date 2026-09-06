# Step 4 scratch tooling — WALL_MAX_THICKNESS_PX 36 -> 40 measured as implemented (2026-09-06)

- `band_census.py` / `band_census_{heavy,light}.json` / `band_census_out.txt` — the
  whole stage-5 chain through the harness at cap x1.0 and x40/36 per sheet (every use
  of the cap scales): the 36f–40f candidate population (wide_pairs with material /
  through verdicts), the admitted / lost network segments, room moves / removals /
  additions, and the ground-truth score at both caps. `BAND_CENSUS_OUT` names the
  output file so two jobs can run at once.
- `interior_census.py` / `interior_census.json` / `interior_census_out.txt` — per
  candidate: material, stroked linework parallel to the faces inside the band (over the
  overlap and over the faces' full extent), confident openings in the band; joined to
  the admitted segments and the rooms they touched.
- `attribute_rooms.py` — per moved / gone / new room, the new (blue) and lost (orange)
  segments near it, tiled contact sheets.
- `crop_segments.py` — contact sheets of every candidate or admitted segment per slug.
- `zoom.py` — the zoom crops the report cites (edit the targets list).
- `unsimplified_diff.py` / `unsimplified_diff_out.txt` — per-room lost / gained px² at
  ROOM_SIMPLIFY_TOL_PX 0 between the two caps (s15, s11, s16).
- `sweep_base_verdicts.txt` / `sweep_cap40_verdicts.txt` — the two corpus sweeps.

Run from the repo root with `.venv/bin/python`. A background job imports the tree at
launch: never edit a constant while one is running.
