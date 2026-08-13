# Step 3 — Diagnose s15's 82 false positives (read-only)

Status: not started
Kind: investigation — NO code changes, NO constant changes. Output is a
written diagnosis and scoped fix proposals.
Expected payoff: s15 is the corpus's worst sheet and has never been
mechanism-audited; if one mechanism dominates, the follow-up fix could dwarf
steps 1–2 combined.

## The problem (baseline 2026-08-13)

s15 is a **1:50** sheet (factor 1.0 — scale-awareness never touches it) with
**82 returned false positives**, the largest FP mass in the corpus, stable
across every sweep since the FP table in
`docs/scale-normalization-findings.md` §3 was first recorded. Composition (as
of the 2026-08-13 baseline): **72 room FPs, 9 window FPs, 1 door FP** — the
mass is overwhelmingly PHANTOM ROOMS. Confirmed counts on the sheet: 12
doors, 2 windows, 15 rooms — so the detector emits ~5 phantom rooms for every
real one.

## What to do

1. **Read first:** `CLAUDE.md` in full — especially the very long room
   detection section, which catalogs every phantom-room mechanism already
   fixed (striped-field lattice demotion, hatch-tier pairs, weak-pair
   material gates, annotation/furniture pens, white-ring bridging, plug
   tails, paving pockets...). Your job is largely to determine whether s15's
   phantoms match a KNOWN mechanism that mis-fires on this sheet's drafting
   style, or a new one. Also `docs/regression-testing-guide.md` (reading the
   sweep + review artifacts).
2. **Regenerate artifacts:** `python tools/regress.py --sheet s15` (fresh
   overlays under `outputs/regress/s15/<timestamp>/pages/page_01/` —
   `overlay.png`, `render.png`). For per-primitive tracing add `--debug`
   (writes `debug_trace.json` + `debug_viewer.html`; s15's cost is moderate —
   the 200-300MB warning applies to s16/s18).
3. **Sample and classify:** take ~15 of the 72 room FPs (bboxes are in
   `tests/ground_truth/s15.json` `false_positives`; the sweep JSON's
   `returned_fps` carries the live matches). For each: what fenced the
   phantom — a phantom wall pair (which pen/linework?), a seal from a phantom
   opening, a white-ring bridge, gap-closing, a fill-class rating? Use the
   overlay + debug viewer + `final_entities.json` room polygons. Group into
   mechanisms with counts. Do the same lightly for the 9 window FPs (check
   whether they are the span-overshoot family step-2 targets — measure their
   overshoots) and the 1 door FP.
4. **Cross-check against the known-mechanism catalog** (CLAUDE.md room
   section + the memory of past branches recorded there): for each mechanism
   found, name the closest already-shipped fix and why it does not fire here.
5. **Write up:** a new doc (e.g.
   `docs/s15-false-positive-diagnosis.md`) with: per-mechanism counts, one
   worked example each (bbox, the fencing linework's path indices, the gate
   decisions from the trace), the ranked fix proposals with predicted
   FP-kill counts, and explicit regression risk per proposal (which confirmed
   rooms/windows sit near the mechanism). Add a findings §6 pointer entry.

## Hard limits

- Read-only on detection: no code or constant changes in this task; each
  proposed fix becomes its own follow-up branch scoped to ONE mechanism
  (repo history shows every phantom-room fix is a single-mechanism branch).
- NEVER run `tools/review.py`; NEVER edit `tests/ground_truth/` or fixture
  bytes. No PDFs committed; no address-bearing text in the write-up
  (findings §regression rules — sheet slugs only, never portal IDs or
  addresses that may appear in title blocks).
- `.venv/bin/python`; verify fixtures with `tools/fetch_fixtures.py` first.
- Docs-only commits on a new branch, imperative subject with type prefix,
  never a Co-Authored-By trailer.

## Acceptance

1. The diagnosis doc exists with ≥ 15 room FPs classified into named
   mechanisms with counts, worked examples, and ranked fix proposals with
   predicted kills and risks.
2. A one-paragraph verdict: does one mechanism dominate (→ one high-ROI fix
   branch) or is the mass heterogeneous (→ re-rank the backlog)?
3. Zero changes outside `docs/`.
