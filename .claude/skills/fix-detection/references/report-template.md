# Checkpoint report (phase 7)

Use this shape. Numbers come from runs you actually did; say "not measured"
rather than estimating.

```
## <slug> <type> — <one-line symptom>

**Root cause** (stage + rule): e.g. "walls.py strong-pair tier: the counter
front (1.5px, wall pen) pairs with the kitchen's inner face at 35.2px, under
WALL_MAX_THICKNESS_PX 36."

**Convention that separates it from real walls**: one sentence.

**Measured margin** (false class vs true class):
| feature | false (sNN) | true (sNN) | true (s01) | true (s02) |
|---|---|---|---|---|
(all four columns, or "not measured — <why>"; a rule justified on one sheet is not yet generic)

**Fix**: rule name / constant + value, file:line. Unit test: tests/…::test_…
(verified it bites).

**Net effect on <slug>** (from the pictures, my verdicts):
| id | what it is | before | after | my read |
|---|---|---|---|---|
| r19 | stair-foot cell | phantom | gone | win |
| r22 | worktop outline | — | new REVIEW | phantom (uncovered; belongs to the far-side/fixture rule) |
Net phantoms: N → M. <one sentence: win / trade / not yet>

**Pictures**: outputs/compare/<slug>/page_NN_changes.png, page_NN_side_by_side.png, <crop>.png
(copy them next to the report; the user reviews from these first).

**Sweep** (`tools/regress.py`, full corpus, exit N, vs baseline sweep of the unmodified tree):
| sheet | lost confirmed | returned FP | new REVIEW | deferred closed |
|---|---|---|---|---|
| sNN | 0 | 0 | 2 (room_0007, room_0009 — my read: …) | 1 |
| others | … | | | |
before|after: outputs/compare/sNN/page_NN_changes.png

**Not pinned yet**: new REVIEW detections need `tools/review.py sNN` to become
confirmed. Any deferred→closed needs the user's confirmation + hand promotion.

**Residue / not in scope**: anything else seen, one line each.

**Decision needed**: iterate (on what), accept and commit, or revert.
```
