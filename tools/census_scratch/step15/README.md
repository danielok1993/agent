# Step 15 scratch tooling — `_is_band_pocket`'s cover read on the pocket's own sides (2026-09-06)

- `cover_census.py` / `cover_census_{a,b,s17}.json` + `.txt` (the step-14 tree) and
  `cover_census_after_{a,b}.json` + `.txt` (this tree) — the stage-5 chain through the harness
  with a tap on `rooms._is_band_pocket` (every call, with the rule's verdict) and the free-space
  tap reading detect_rooms' own `face_lines` / `door_barriers` / `wall_segments`; every call and
  every emitted room (the true class the rule would see if its entrance did not spare it) read
  five ways — `mrr` (the rectangle's edges, the reading before this step), `mrr_tol0` (the same
  with standoff 0 tolerated), `runs` (the polygon's own long runs against faces, union),
  `runs_caps` (the same with the wall solids' flat ends admitted — the reading built) and
  `runs_max` (largest single face per run) — with the verdict under each reading at each
  candidate ceiling. `COVER_CENSUS_OUT` names the output so several jobs run at once.
- `summarise.py` → `summary_before.txt` / `summary_after.txt` — the tables over those JSONs:
  the rule's population by band and reading, every call at pocket spacing, per-ceiling
  verdicts, the confirmed class under each reading, and the s17 strips per side.
- `s17_tab_probe.py` — what bounds each s17 strip's TAB: the perpendicular band's paired
  segment ending ON the strip's face line with a flat-capped solid, and the face lines beside it.
- `ceiling_census.py` / `ceiling_census_{a,b,c}.json` + `.txt` — the rule AS IMPLEMENTED run
  with its ceiling at 40 / 41 / 44 / 48 / 56 px (× f) for the rule alone on every sheet:
  every component newly dropped with its ground-truth class, rooms gone / new / moved, scores.
- `zoom15.py OUT` — the report's crops: the component, its rectangle, and its long-side runs
  coloured by what they lie along (face / cap / neither), both covers in the caption.
- `rooms_step15.diff` — the detector change, used for the bite check (revert, fail, restore).
- `sweep_base_g{1..4}.txt` / `sweep_base_raw.txt` / `sweep_base_verdicts.txt` — the baseline
  corpus sweep of the step-14 tree in four background groups, verdict lines sorted (identical
  to step 14's after-sweep); `sweep_after_*` — the same after the reading.
- `unittest_full.txt` — the fast tier after the change (1441 tests, OK).

Run from the repo root with `.venv/bin/python`. A background job imports the tree at
launch: never edit a constant while one is running. The step-13/14 census scripts call
`rooms._edge_face_cover`, which this step replaced with `_run_wall_cover` /
`_side_wall_covers`; they document their own trees and are not maintained against this one.
