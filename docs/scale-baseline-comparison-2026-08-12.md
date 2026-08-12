# Baseline comparison — feat/scale-aware-wall-room-gates vs pre-branch (b0e705a)

Method: `git worktree add <scratch>/baseline-b0e705a b0e705a` (detached),
symlinked `fixtures/sheets` (which contains `.regions_cache/`) from the main
checkout, ran `python tools/regress.py --sheet <slug>` for each of the six
suspicious sheets from the branch's task-6 sweep, one at a time, using the
main checkout's venv. No code was modified anywhere; `tests/ground_truth/`
was read but never written; `tools/review.py` was never run. Worktree removed
after capture.

Branch sweep source: `.superpowers/sdd/2026-08-12-scale-aware-wall-room-gates/task-6-report.md`.

## s02 (1:50, reference sheet) — LOST confirmed schedule

Branch:
```
s02  door 15/15  label 11/11  room 12/12  schedule 0/1  window 11/11  unreviewed 1
    ✗ LOST schedule @ (0,0)
    REVIEW new schedule_0000  conf 0.60  (0,0)
    REGION CACHE MISS — classification fell back to the whole page
```

Baseline (b0e705a):
```
s02  door 15/15  label 11/11  room 12/12  schedule 0/1  window 11/11  unreviewed 1
    ✗ LOST schedule @ (0,0)
    REVIEW new schedule_0000  conf 0.60  (0,0)
    REGION CACHE MISS — classification fell back to the whole page
```

**Verdict: PRE-EXISTS.** Identical LOST + REVIEW + REGION_CACHE_MISS on
baseline, byte-for-byte. Confirms the task-6 report's own diagnosis: stale
region-classification cache entry, unrelated to this branch's diff (which
never touches `layout/` or `gemini/region_cache.py`).

## s04 (1:50) — 2 RETURNED false positives

Branch:
```
s04  door 3/3  room 6/6  unreviewed 1
    ✗ FALSE POSITIVE RETURNED room @ (1511,1090)
    ✗ FALSE POSITIVE RETURNED room @ (1675,1092)
    REVIEW new window_0002  conf 0.62  (1573,1089)
```

Baseline:
```
s04  door 3/3  room 6/6  unreviewed 1
    ✗ FALSE POSITIVE RETURNED room @ (1511,1090)
    ✗ FALSE POSITIVE RETURNED room @ (1675,1092)
    REVIEW new window_0002  conf 0.62  (1573,1089)
```

**Verdict: PRE-EXISTS.** Identical FPs at identical coordinates and identical
REVIEW candidate (same conf, same coords). Not a regression.

## s14 (1:50) — 2 RETURNED false positives

Branch:
```
s14  door 13/13
    ✗ FALSE POSITIVE RETURNED window @ (2872,1199)
    ✗ FALSE POSITIVE RETURNED room @ (2636,2066)
```

Baseline:
```
s14  door 13/13
    ✗ FALSE POSITIVE RETURNED window @ (2872,1199)
    ✗ FALSE POSITIVE RETURNED room @ (2636,2066)
```

**Verdict: PRE-EXISTS.** Identical FPs at identical coordinates.

## s11 (unresolved → factor 1.0) — 2 new REVIEW doors + 3 RETURNED FPs

Branch:
```
s11  door 13/13  room 14/14  window 23/23  unreviewed 2
    ✗ FALSE POSITIVE RETURNED room @ (1696,1199)
    ✗ FALSE POSITIVE RETURNED room @ (2180,1145)
    ✗ FALSE POSITIVE RETURNED room @ (1788,1384)
    REVIEW new door_0005  conf 0.60  (765,1224)
    REVIEW new door_0007  conf 0.60  (766,1640)
```

Baseline:
```
s11  door 13/13  room 14/14  window 23/23  unreviewed 2
    ✗ FALSE POSITIVE RETURNED room @ (1696,1199)
    ✗ FALSE POSITIVE RETURNED room @ (2180,1145)
    ✗ FALSE POSITIVE RETURNED room @ (1788,1384)
    REVIEW new door_0005  conf 0.60  (765,1224)
    REVIEW new door_0007  conf 0.60  (766,1640)
```

**Verdict: PRE-EXISTS.** Identical set — 3 room FPs at identical coords, 2
REVIEW doors at identical coords/confidence. At factor 1.0 the branch's
scale-aware gates are (as expected) a no-op vs. baseline behavior; this sheet
was already noisy before the branch existed.

## s06 (1:100, scale-affected) — 1 LOST confirmed room

Branch:
```
s06  door 2/2  room 0/1  window 8/8  unreviewed 7
    ✗ LOST room @ (1115,982)
    ✗ FALSE POSITIVE RETURNED room @ (459,372)
    ✗ FALSE POSITIVE RETURNED room @ (459,520)
    REVIEW new room_0000..room_0007  (7 new rooms)
```

Baseline:
```
s06  door 2/2  room 1/1  window 8/8
    ✗ FALSE POSITIVE RETURNED room @ (569,402)
    ✗ FALSE POSITIVE RETURNED room @ (459,372)
    ✗ FALSE POSITIVE RETURNED room @ (459,520)
```

**Verdict: SCALE-INDUCED, does not pre-exist.** Baseline confirms room 1/1 —
the ground-truth room is NOT lost pre-branch. The branch's LOST @ (1115,982)
is a genuine consequence of making wall/room gates scale-aware at this 1:100
tier, exactly the expected-change category the branch brief called out (this
sheet's scale differs from the 1.0/50 identity tier, so a detection change
here is in scope, not an identity violation). Also notable: FP @ (459,372)
and (459,520) pre-exist unchanged; baseline's third FP @ (569,402) does NOT
appear in the branch's list — that FP VANISHED (improved) on the branch. The
branch also produces 7 new REVIEW room candidates absent from baseline,
consistent with scale-aware gates re-partitioning this sheet's rooms.

## s12 (1:100, scale-affected) — 1 LOST confirmed room

Branch:
```
s12  door 7/7  room 3/4
    ✗ LOST room @ (1953,1400)
    ✗ FALSE POSITIVE RETURNED door @ (1468,1533)
    ✗ FALSE POSITIVE RETURNED door @ (1468,1551)
    [17 window FPs]
    ✗ FALSE POSITIVE RETURNED room @ (352,680)
    ✗ FALSE POSITIVE RETURNED room @ (332,680)
```
(2 door + 17 window + 2 room = 21 RETURNED FPs total)

Baseline:
```
s12  door 7/7  room 4/4
    ✗ FALSE POSITIVE RETURNED door @ (1468,1533)
    ✗ FALSE POSITIVE RETURNED door @ (1468,1551)
    [same 17 window FPs, identical coordinates]
    ✗ FALSE POSITIVE RETURNED room @ (342,378)
    ✗ FALSE POSITIVE RETURNED room @ (352,680)
    ✗ FALSE POSITIVE RETURNED room @ (332,680)
```
(2 door + 17 window + 3 room = 22 RETURNED FPs total — matches the task-6
report's documented pre-branch baseline of 22)

**Verdict: SCALE-INDUCED, does not pre-exist.** Baseline confirms room 4/4 —
all four ground-truth rooms detected pre-branch, none lost. The branch's LOST
@ (1953,1400) is a genuine scale-tier behavior change, in scope for this
1:100 sheet per the branch brief. All 21 of the branch's RETURNED FPs
pre-exist on baseline at identical coordinates (door, window, and 2 of 3
room FPs); baseline's extra room FP @ (342,378) VANISHED (improved) on the
branch.

## Identity verdict — the four factor-1.0 / 1:50 sheets (s02, s04, s14, s11)

**IDENTITY HELD.** Every LOST/RETURNED/REVIEW line the branch sweep flagged
as suspicious on s02, s04, s14, and s11 reproduces byte-for-byte on the
pre-branch baseline (b0e705a) — same coordinates, same confidences, same
counts. None of these four sheets shows a single NEW failure introduced by
`feat/scale-aware-wall-room-gates`. All four are pre-existing corpus debt,
unrelated to the branch's diff.

## s06 / s12 verdict

Both LOST rooms are **scale-induced, not pre-existing** — baseline detects
the ground-truth room correctly on both sheets (s06 room 1/1, s12 room 4/4).
This is consistent with the branch brief's own framing: s06 and s12 are
1:100 sheets where scale-aware gates are expected to change wall/room
detection, so these losses are in-scope behavior changes requiring a
detection-quality judgment call (regression vs. acceptable tradeoff), not an
identity-guarantee violation (which only applies to factor-1.0 sheets).
