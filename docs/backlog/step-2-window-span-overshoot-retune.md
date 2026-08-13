# Step 2 — Retune the window span-overshoot gate (paper-space FP kill)

Status: not started
Kind: small fix branch (one-constant retune + measurement + tests + sweep)
Expected payoff: kills the s12/s18 phantom-window families at measured-zero
confirmed cost.
Sequencing: do NOT run in the same sweep as step-1 — separate branches,
separate sweeps, user verdicts between (deltas become unattributable
otherwise).

## The problem (measured 2026-08-13, findings §4e/§6)

`WINDOW_SPAN_OVERSHOOT_PX` = **12.0** (`detection/windows.py`) caps how far a
glazing line may run past each jamb cap. It is frozen **paper-space** (do NOT
scale it — that classification is pinned by tests). But its VALUE has slack
the phantom windows live in:

- Confirmed windows' overshoot tails: 1:100 tier p90/max **8.62 / 9.38 px**;
  1:50 tier p90/max **6.27 / 10.50 px**. Nothing confirmed exceeds 10.50.
- The ground-truth FP window families overshoot at **11.75–11.92 px (s12,
  which carries 21 phantom windows)** and **11.93–11.98 px (s18, 12
  phantoms)** — just under the 12.0 gate.

A retune to **~11.0** (must stay above the confirmed 10.50 max with margin;
10.5 exactly would sit ON a confirmed window) is expected to kill a large
share of both FP families at zero confirmed cost. Note: the sibling
`WINDOW_SPAN_COVER_TOL_PX` (4.0) has confirmed shortfalls to 3.55 — no
usable slack; leave it alone.

## What to do

1. **Read first:** `CLAUDE.md`; `docs/window-detection-tuning-guide.md`;
   `docs/scale-normalization-findings.md` §4b/§4c (measurement discipline)
   and §4e (the frozen window table, the harness note, and the §6
   "span-overshoot retune" entry that this task executes).
2. **Baseline sweep**, saved (`tools/regress.py --json`; JSON starts at the
   first `[` in stdout).
3. **Re-measure, don't trust this file's numbers:** verdicts land
   continuously and the corpus may have moved. Reproduce the overshoot
   distributions (confirmed vs ground-truth-FP windows, per tier) through the
   real pipeline using the inert-tap method findings §4e's harness note
   describes: tap `detection/windows.py` to record per-band
   `span_over_a`/`span_over_b` into candidate evidence, pass through
   `finalize_candidates` into `final_entities.json`, verify the tapped sweep
   reproduces the baseline exactly, harvest matched against
   `tests/ground_truth/` (match type + IoU ≥ 0.5 via `regression.matching`),
   revert the tap. Confirm the gap between confirmed-max and FP-min still
   exists and pick the retuned value inside it with margin both ways.
4. **Change the constant, update its comment** with the measured rationale
   (the existing comment style documents evidence inline).
5. **Pin with fast-tier tests:** a fixture overshooting at the confirmed tail
   (~9–10 px) still detects; a fixture at the FP tail (~11.8 px) is rejected.
   Note `tests/test_scale_window_gates.py::TestPaperInvariance` has a
   span-overshoot fixture at ~9 px — it must stay green; the paper-space
   PINNING tests (never scale) are untouched by a value retune.
6. **One sweep, then stop for the user.** Expected: s12's and s18's returned
   window-FP counts DROP (disappearing known FPs are a sweep improvement and
   need no verdicts); zero lost confirmed anywhere. This retune applies at
   every scale, so 1:50 sheets are NOT exempt — check them all. Blast radius:
   rooms consume window candidates for seals — killed phantom windows can
   legitimately move room lines on s12/s18 (report any room delta explicitly;
   a lost CONFIRMED room fails).

## Process rules (binding)

- `.venv/bin/python`; fixtures verified via `tools/fetch_fixtures.py` (20
  present).
- New branch (e.g. `fix/window-span-overshoot-retune`); imperative commits
  with type prefix; NEVER a Co-Authored-By trailer; `graphify update .` after
  code changes.
- Fast tier green at every commit. The full sweep currently exits 1 from
  documented pre-existing debt (findings §3) — not your regression; never
  soften it.
- NEVER run `tools/review.py`; NEVER edit `tests/ground_truth/` or fixture
  bytes. One fix + one sweep, then the user verdicts personally.
- No PDFs committed.

## Acceptance

1. Fast tier green incl. the two new pins; the existing paper-invariance
   battery untouched and green.
2. Sweep: zero lost confirmed of any type; s12/s18 window-FP reduction
   reported with exact before/after counts and the killed FPs' bboxes; any
   room-line movement reported.
3. Findings §6's span-overshoot entry updated to DONE with the re-measured
   distributions and the chosen value.
