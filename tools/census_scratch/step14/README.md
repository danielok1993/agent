# Step 14 scratch tooling — the entrance-run gate censused as implemented (2026-09-06)

- `entrance_census.py` / `entrance_census_{a,b}.json` / `entrance_census_{a,b}.txt` — the
  stage-5 chain through the harness twice per page: gate OFF
  (`H.overrides(mult={"ROOM_ENTRANCE_MIN_RUN_PX": -1.0})` — a floor of −29.5 × f, under any
  in-contact run ≥ −8px for every corpus factor, so every seal within the contact tolerance
  counts: the any-touch test the tree read before this step, exactly; asserted per page)
  and ON. For every room the OFF run emits, read off detect_rooms' own locals through the
  free-space tap (`face_lines`, `door_barriers`) and the `_drop_window_exterior_sides` tap:
  the any-touch and the run-gated entrance counts, per touching seal its raw contact and its
  `_entrance_run`, along/across the room's long axis, the room's largest run in px and in
  true-world mm, door / window counts, ground-truth class, and its fate under ON. Both runs
  scored and diffed. `ENTRANCE_CENSUS_OUT` names the output so two jobs run at once.
- `zoom14.py OUT` — the report's crops: the room polygon from the named sweep run (baseline
  snapshot or latest), every entrance seal the census recorded for it (green, with its run),
  named openings (orange). Targets listed in the file.
- `pocket_census_s17_after.json` — `step13/pocket_census.py` run on this tree for s17: the
  band-pocket rule now receives the four reveal strips (7 calls against 3) and rejects them
  by cover (one long edge 0) and spacing (38.75–40.5px over the 36px cap).
- `sweep_base_g{1..4}.txt` / `sweep_base_raw.txt` / `sweep_base_verdicts.txt` — the baseline
  corpus sweep of the step-13 tree in four background groups, verdict lines sorted (identical
  to step 13's); `sweep_after_*` — the same after the rule (one s04 line swapped).
- `unittest_full.txt` — the fast tier after the change (1440 tests, OK).

Run from the repo root with `.venv/bin/python`. A background job imports the tree at
launch: never edit a constant while one is running.
