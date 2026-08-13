# Accuracy backlog — ranked by ROI (2026-08-13)

One file per task, each self-contained: hand a single file to a fresh AI agent
as its opening brief. Ranked by measured accuracy gain ÷ effort at the time of
writing (post scale-aware window-gates merge, `02dd32c`).

| # | File | Kind | One-line payoff |
|---|---|---|---|
| 1 | `step-1-door-bezier-aspect-gate.md` | small fix branch | s06 detects 2 of 10 visible door swings because of one dimensionless gate |
| 2 | `step-2-window-span-overshoot-retune.md` | small fix branch | s12/s18's phantom-window families sit 0.02–0.25px under one gate |
| 3 | `step-3-s15-false-positive-diagnosis.md` | read-only investigation | the corpus's worst sheet (82 FPs, mostly rooms) has never been diagnosed |
| 4 | `step-4-1to100-misses-audit.md` | audit + user review | ground truth structurally cannot see misses; this converts them into a work queue |
| 5 | `step-5-per-scale-group-detection.md` | full spec→plan branch | mixed-scale pages (s03/s17) still detect at one scale |

**Ordering rules:** steps 1 and 2 are both small but must be SEQUENTIAL
(separate branches, separate sweeps, user verdicts between — one fix + one
sweep per iteration; their REVIEW deltas are unattributable if bundled).
Steps 3 and 4 can run any time and may re-rank step 5.

**Completion tracking:** flip the `Status:` line at the top of each file
(`not started` → `in progress` → `done (<branch/commit>)`) and commit the flip
with the work.

Every task file embeds the shared process rules; the numbers cited were
measured 2026-08-13 — each task re-baselines with a fresh sweep before
changing anything, because verdicts land continuously and counts move.
