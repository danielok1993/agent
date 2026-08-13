# Step 1 — Widen the door Bezier aspect gate

Status: not started
Kind: small fix branch (one-constant change + measurement + tests + sweep)
Expected payoff: the single largest measured door-recall gap in the corpus.

## The problem (measured)

`DOOR_BBOX_ASPECT_MIN` / `DOOR_BBOX_ASPECT_MAX` = **[0.85, 1.15]**
(`detection/doors/constants.py`) gate the Bezier-arc detection path: a swing
arc's bbox must be roughly square. But a genuine **85°-sweep arc measures bbox
aspect 0.804** — below the gate — so real swings are rejected. Measured
consequence: **s06 detects only 2 of 10 visible door swings**. The polyline
arc path already uses a wider **[0.65, 1.45]** for the same judgment
(`detection/doors/arcs.py`, search for the polyline aspect gate) — the Bezier
path is tighter than its own sibling for no recorded reason.

This is a **dimensionless** constant (findings §4d), so the scale-aware
branches deliberately did not touch it; it was parked as its own follow-up in
`docs/scale-normalization-findings.md` §6 ("Doors — Bezier aspect gate"),
which records the 0.804 measurement. Most of the door-gates branch's
real-world payoff is gated behind this fix.

## What to do

1. **Read first:** `CLAUDE.md` (all), `docs/door-detection-tuning-guide.md`
   (the six swing topologies + known FP patterns + why the tight bound might
   have existed), `docs/scale-normalization-findings.md` §4b–§4d + §6 (the
   measurement discipline and the aspect-gate entry).
2. **Baseline:** `python tools/regress.py` fresh; save the JSON
   (`--json`, note stdout carries console tables before the JSON array — parse
   from the first `[`). This is your arbiter for every later comparison.
3. **Measure before choosing bounds:** through the REAL pipeline (findings
   §4c: any side harness must reproduce `tools/regress.py --sheet <slug>`
   counts before its numbers are trusted), collect the bbox-aspect
   distribution of (a) confirmed doors' arcs and (b) the candidate arc
   population, per sheet. The proven cheap method (findings §4e harness note):
   add an inert measurement tap (extra evidence key) in the arc path, pass it
   through `finalize_candidates` into `final_entities.json`, verify the tapped
   sweep reproduces the baseline byte-for-byte, harvest, then revert the tap
   before any implementation commit.
4. **Pick the bounds from the distribution** — the sibling polyline values
   [0.65, 1.45] are the natural candidate, but justify from data, and
   investigate what FP family motivated 0.85/1.15 originally (git log on the
   constants; the tuning guide's FP catalog) so widening is verified against
   it, not just against today's ground truth.
5. **Pin with a synthetic test** in the fast tier: an 85°-sweep Bezier arc
   door detected; whatever FP shape motivated the tight bound still rejected.
6. **One sweep, then stop for the user.** Expected: new REVIEW doors on s06
   (up to ~8) and possibly other sheets at every scale (the gate is
   dimensionless — 1:50 sheets may gain REVIEW lines too, which is allowed).
   Window REVIEW lines may move as a side effect (changed doors change the
   door→window suppression — the doors branch measured +17 windows from door
   changes; expected, not a bug). HARD failures: any lost confirmed entity,
   any RETURNED known false positive (widening can add FPs — new ones arrive
   as REVIEW lines and are fine; ground-truth-known FPs returning fails).

## Process rules (binding)

- `.venv/bin/python` (bare `python` not on PATH). Fixtures: `python
  tools/fetch_fixtures.py` must report 20 present.
- New branch (e.g. `fix/door-bezier-aspect-gate`). Imperative commits with
  type prefix. NEVER a Co-Authored-By trailer. `graphify update .` after code
  changes.
- Fast tier green at every commit (`python -m unittest discover tests`).
- The full sweep currently exits 1 from documented pre-existing FP debt
  (findings §3) — that is not your regression; never soften a failing signal.
- NEVER run `tools/review.py`; NEVER edit `tests/ground_truth/` or fixture
  bytes. One fix + one sweep, then the user verdicts personally.
- No PDFs committed; no address-bearing text.

## Acceptance

1. Fast tier green incl. the new synthetic pin.
2. Sweep: zero lost confirmed, zero returned known FPs; recall gains arrive
   as REVIEW lines (s06 is the headline — report its before/after door count).
3. Findings §6's aspect-gate entry updated to DONE with the measured
   distribution and the chosen bounds' rationale.
