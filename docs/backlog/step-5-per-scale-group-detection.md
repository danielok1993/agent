# Step 5 — Per-scale-group detection for mixed-scale pages

Status: not started
Kind: FULL architectural branch — brainstorm → spec → user review → plan →
implement (the superpowers process; the scale-aware gates branches are the
template). The largest item in this backlog; consider re-ranking after steps
3–4 report.
Requirement provenance: user decision 2026-08-12 (findings §5.3) — "each plan
runs at the scale attached to that plan, even on a single page." The current
ink-dominant single-factor treatment is explicitly interim, kept loud by the
`SCALE_MIXED_FLOOR_PLANS` warning.

## The problem

A page's floor-plan regions can carry different scales (s03: two 1:100
regions + one 1:50; s17: two 1:100 + two 1:50). Detection runs ONCE over the
union with ONE factor (`scale/factor.py::detection_scale`, ink-dominant
vote) — currently both sheets resolve f=1.0, so their 1:100 regions are
detected with 1:50-tuned gates. Known debt on exactly these sheets: s03 21
window FPs + 5 room FPs; s17 18 room FPs + 5 window FPs (re-baseline before
trusting counts). Their 1:100-region MISSES are invisible (see step-4).

## Why it is NOT a bolt-on (measured hazard)

Naive per-region detection is a measured regression
(`docs/scale-normalization-findings.md` §6 "Per-scale-group detection"; also
the standing memory rule "never run heuristics per region"): on s01
(2026-07-28, both regions the SAME scale), per-region passes degraded rooms
13 → 14 with area 478,923 → 446,261 px² — kitchen units carved out of
DINING/SITTING+KITCHEN (148,895 → 118,073 px²), UTILITY/STORE spuriously
split (17,430 → 10,526 + 6,144). Mechanism: page-global statistics lose
their denominator when the path set shrinks — `ROOM_WALL_PEN_MIN_FRAC` (a pen
is a wall pen at ≥ 0.15 of paired-face length), the `wall_stroke_reference`
median, the lattice/hatch demotion scans; s01's red furniture pen cleared 15%
within one region alone and its pairs gained barrier rights.

## The design sketch to start from (findings §6, verbatim intent)

Decouple STATISTICS scope from DETECTION scope, along the same world/paper
split as the constants:

- Paper-space statistics (pen medians, wall-pen color fractions,
  `wall_stroke_reference`) are poolable across scales — one CAD export, one
  pen convention — compute them ONCE over the union and pass them FROZEN
  into per-group passes.
- Geometric scans (lattice/hatch pitch demotion) are scale-dependent and run
  inside each group's pass with that group's factor.
- Pipeline: partition floor-plan regions by resolved factor
  (`scale/factor.py` + `scale/resolver.py` give per-region scales),
  `filter_page_data` per group, run detection per group with (frozen stats,
  group factor), concatenate candidates before postprocess/NMS. Doors,
  windows, walls, rooms are all now per-page-factor scale-aware
  (`DoorGates`/`WindowGates`/`WallGates`/`RoomGates`/`CrossGates`) — the
  threading exists; this branch moves WHERE the factor comes from
  (per-group instead of per-page) and what each detector sees.
- Single-scale pages MUST remain exactly one pass with byte-identical
  results (the s01 union-identity property — make it an explicit test).
- Open design questions for the spec: cross-group NMS and door→window
  suppression (candidates from different groups can overlap at region
  seams); label/schedule scope; `regions.json`/cache interactions;
  s13-style odd factors.

## Process (binding)

- Full superpowers flow: brainstorm, then a spec in
  `docs/superpowers/specs/`, USER REVIEWS THE SPEC before planning, plan in
  `docs/superpowers/plans/`, then implement. Use the two predecessor pairs
  (`2026-08-12-scale-aware-wall-room-gates-*`,
  `2026-08-13-scale-aware-window-gates-*`) as the structural template,
  including measurement-first evidence and a predicted per-sheet delta table
  for s03/s17.
- Measurement discipline: findings §4b/§4c — any harness must reproduce
  `tools/regress.py --sheet` counts before its numbers are trusted; the
  sweep is the arbiter; predictions written before results.
- Regression gates: every single-scale sheet byte-identical (this is the
  make-or-break invariant, per the s01 hazard above); s03/s17 changes arrive
  only as REVIEW lines for the user; the sweep's current exit-1 debt
  (findings §3) is not yours to fix or soften. One fix + one sweep, then the
  user verdicts.
- NEVER run `tools/review.py`; NEVER edit `tests/ground_truth/` or fixture
  bytes. No PDFs committed. `.venv/bin/python`; fixtures verified first.
- New branch; imperative commits with type prefix; never a Co-Authored-By
  trailer; `graphify update .` after code changes.

## Acceptance (to refine in the spec)

1. s03/s17's 1:100 regions detect at f=0.5, 1:50 regions at f=1.0, in one
   extract run; `SCALE_MIXED_FLOOR_PLANS` demoted or reworded accordingly.
2. Every single-scale sheet byte-identical to the pre-branch baseline —
   including s01's rooms (13 rooms, the union-identity property, pinned by a
   test).
3. Changes on s03/s17 arrive only as REVIEW lines matching the spec's
   predicted table; user verdicts them personally.
4. Findings §5.3/§6 updated: the interim single-factor decision closed out.
