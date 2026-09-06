# Step 12 scratch tooling — the dimension-verified gate scale (2026-09-06)

- `rule_census.py` / `rule_census_out.txt` — the rule AS IMPLEMENTED on every
  corpus sheet: per floor-plan region the claim, the ticked dimension strings
  matched inside it, the measured denominator and `_gate_choice`, then
  `detection_scale` with and without the dimensions (only s01's factor changes).
- `scale_census.py` — how each sheet's scale resolved in a sweep run
  (summary.json's `scales` block); the pre-step evidence that s01 is the only
  non-nominal, non-viewport scale on the corpus.
- `s01_factors.py` — harness scoring of s01 at identity and at 50/92.2.
- `unsimplified_diff.py` — s01 identity vs true factor with
  `ROOM_SIMPLIFY_TOL_PX` 0: per matched room lost / gained px² and where.
- `verdicts.py` — section-wise verdict extraction from `regress.py` reports;
  `sweep_base_verdicts.txt` / `sweep_after_verdicts.txt` are the two sweeps.

Run from the repo root with `.venv/bin/python`.
