# Step 17 scratch tooling — `_is_wall_recess`'s back edge on the tab (2026-09-06)

- `recess_census.py` / `recess_census_{s11,a,b,c}.json` + `.txt` — the stage-5 chain through the
  harness with a tap on `rooms._is_wall_recess` (every call, with the rule's verdict and its exact
  `wall_segments` / `opening_boxes` / `text_spans`) and the free-space tap reading detect_rooms' own
  `face_lines` / `cap_lines` / `wall_segments` / `solids` / `doors` / `windows` / `text_spans` off
  `sys._getframe(1)`; every call and every emitted room read for every collinear-gap candidate that
  passes the intersect / opening / gap-cover / depth gates: the EXTENT reading (`back`, as the
  step-16 tree implemented it) and the RUNS reading in four variants — the back runs at the standoff
  inside the band's outer line (`face`) or also ON it where a cap line lies on them (`caps`), over the
  gap's length (`gap`) or over the component's own extent inside the gap (`own`). Then the rule AS
  IMPLEMENTED with `_is_wall_recess` replaced by each runs variant: rooms gone / new / moved, scored.
  `RECESS_CENSUS_OUT` names the output; `RECESS_CENSUS_SHIPPED` names the reading the shipped rule
  implements (`extent` on the step-16 tree, `caps_own` on this one) — the census asserts the rule's
  verdict against its own reading on every call.
- `recess_census_after_{a,b,c}.json` + `.txt` — the same census on the shipped tree
  (`RECESS_CENSUS_SHIPPED=caps_own`): the reading-vs-implemented check.
- `summarise17.py` → `summary17.md` — the report's tables over the before-census JSONs.
- `fixture_probe.py` → `fixture_probe.txt` — the step-15 fixture (tabbed, and with the inner face line
  drawn through) through the stage with the pocket rule on and off: the components, which rule drops
  the reveal, and every recess candidate's numbers under both readings (measured on the step-16 tree).
- `fixture_picture.py` — the pin fixture as a picture (both readings in the caption).
- `zoom17.py OUT [tag]` → `zoom17.txt` — the report's context crops: a recess call (red) with the
  candidate's gap rect (yellow), its back runs coloured by what they lie on (thick green: a face at
  the standoff; thick orange: a wall solid's flat end), the stage's segment solids (blue), paired /
  lone faces (thin green / orange) and door / window seals (magenta / cyan).
- `rooms_step17.diff` — the detector change alone (the bite check reverts it).
- `sweep_base_g{1..4}.txt` / `sweep_base_raw.txt` / `sweep_base_verdicts.txt` — the baseline sweep of
  the step-16 tree in four background groups (verdict lines byte-identical to step 16's after-sweep);
  `sweep_after_*` — the same on the shipped tree (byte-identical); `diff_room_polygons_after.txt` —
  all 20 sheets entity- and polygon-identical.
- `unittest_full.txt` — the fast tier on the shipped tree (1452 tests, OK).

Run from the repo root with `.venv/bin/python`. A background job imports the tree at launch:
never edit a constant while one is running. The harness cache is `tools/census_scratch/cache/`
(delete a slug's pickle after any scale change).
