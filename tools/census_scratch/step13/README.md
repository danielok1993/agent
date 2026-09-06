# Step 13 scratch tooling — `_is_band_pocket`'s ceiling measured as implemented (2026-09-06)

- `pocket_census.py` / `pocket_census_{heavy,light}.json` — the stage-5 chain through the
  harness with a tap on `rooms._is_band_pocket`: every call (= every entrance-less,
  window-less component that reached the rule) with the rule's own reading — text veto,
  minimum-rotated-rectangle short side, face spacing (short + 2 × `ROOM_LINE_BARRIER_PX`),
  `_edge_face_cover` on both long edges against the pipeline's exact `face_lines` — its
  verdict at the current ceiling and at the thick ceiling, its ground-truth class (bbox
  IoU ≥ 0.5 against confirmed / false_positive / deferred rooms), then a second run with
  the ceiling raised for this rule only, rooms diffed and truth scored. `POCKET_CENSUS_OUT`
  names the output so two jobs run at once.
- `entered_census.py` / `entered_census_{a,b}.json` / `entered_all_{a,b}.json` — the
  rooms detect_rooms EMITS, read off its own locals through the free-space tap
  (`face_lines`, `door_barriers`) and the `_drop_window_exterior_sides` tap (the rooms
  list with door / window counts): per room at pocket spacing (or every room with
  `ENTERED_ALL=1`) the same features plus the entrance count as detect_rooms reads it
  and, per touching entrance, the boundary length within `ROOM_CONTACT_TOL_PX` of the
  seal and the seal's axis against the room's long axis.
- `openings_near.py SLUG name=x0,y0,x1,y1 …` — every post-suppression door / window
  within 16px of the named boxes, confidence, entrance status, distance.
- `s17_strip_openings.py`, `s17_strip_barriers.py`, `s17_strip_edges.py` — the four s17
  reveal strips: which openings touch them, which barrier tier bounds each long side,
  and where each long edge lies against its face line.
- `pocket_crops.py OUT [slug …]` — contact sheets of every recorded component (bbox red,
  minimum rotated rectangle blue, caption with the features and verdicts).
- `zoom13.py OUT` — the report's zoom crops (targets listed in the file).
- `sweep_base_raw.txt` / `sweep_base_verdicts.txt` — the baseline corpus sweep of this
  tree (0 LOST, 68 returned FPs, 0 REVIEW). No detection code changed in this step, so
  there is no "after" sweep.

Run from the repo root with `.venv/bin/python`. A background job imports the tree at
launch: never edit a constant while one is running.
