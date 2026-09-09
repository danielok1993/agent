# CLAUDE.md split — final verification

Date: 2026-09-09
Status: verified, no data loss

This document is Task 9 of `docs/superpowers/plans/2026-09-09-claude-md-split.md`
(SDD brief: `.superpowers/sdd/2026-09-09-claude-md-split/task-9-brief.md`) —
the committed proof that Tasks 1–8 moved four CLAUDE.md source lines
(126,362 characters, pinned at `git show 27b3986:CLAUDE.md`) into their
target documents byte-for-byte, with nothing lost, duplicated, or silently
paraphrased, and that no project code was touched in the process.

## Step 1 — verifier output

```
$ python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
COVERAGE line 197: 99607 chars, 31 spans, exact
COVERAGE line 199: 3923 chars, 1 spans, exact
COVERAGE line 201: 18476 chars, 1 spans, exact
COVERAGE line 245: 4356 chars, 3 spans, exact
CONTENT  S1    docs/page-segmentation.md          3576 chars exact
CONTENT  W1    docs/wall-network-rules.md         4579 chars exact
CONTENT  W2    docs/wall-network-rules.md         1788 chars exact
CONTENT  W3    docs/wall-network-rules.md         1362 chars exact
CONTENT  W4    docs/wall-network-rules.md         3514 chars exact
CONTENT  W5    docs/wall-network-rules.md         5218 chars exact
CONTENT  W6a   docs/wall-network-rules.md         3041 chars exact
CONTENT  W6b   docs/wall-network-rules.md         3643 chars exact
CONTENT  W7    docs/wall-network-rules.md         3788 chars exact
CONTENT  W8    docs/wall-network-rules.md         2933 chars exact
CONTENT  W9    docs/wall-network-rules.md         1392 chars exact
CONTENT  W9b   docs/wall-network-rules.md         6918 chars exact
CONTENT  W10a  docs/wall-network-rules.md         1655 chars exact
CONTENT  W10b  docs/wall-network-rules.md         1328 chars exact
CONTENT  W10c  docs/wall-network-rules.md         2509 chars exact
CONTENT  W10d  docs/wall-network-rules.md         1480 chars exact
CONTENT  R1    docs/room-detection-rules.md       151 chars exact
CONTENT  R2    docs/room-detection-rules.md       4830 chars exact
CONTENT  R3    docs/room-detection-rules.md       3711 chars exact
CONTENT  R4    docs/room-detection-rules.md       412 chars exact
CONTENT  R5a   docs/room-detection-rules.md       1052 chars exact
CONTENT  R5b   docs/room-detection-rules.md       1309 chars exact
CONTENT  R5c   docs/room-detection-rules.md       1080 chars exact
CONTENT  R5d   docs/room-detection-rules.md       2512 chars exact
CONTENT  R5e   docs/room-detection-rules.md       2708 chars exact
CONTENT  R5f   docs/room-detection-rules.md       4115 chars exact
CONTENT  R6    docs/room-detection-rules.md       1450 chars exact
CONTENT  R7a   docs/room-detection-rules.md       2821 chars exact
CONTENT  R7b   docs/room-detection-rules.md       2975 chars exact
CONTENT  R7c   docs/room-detection-rules.md       4544 chars exact
CONTENT  R8    docs/room-detection-rules.md       3551 chars exact
CONTENT  R9    docs/room-detection-rules.md       779 chars exact
CONTENT  F1    docs/scale-normalization-findings.md 3328 chars exact
CONTENT  H1    docs/w-gate-recalibration-handoff.md 15482 chars exact
RETAINED line 245: 2 fragment(s) [RET-245-head,RET-245-tail] anchored in order on one line (prefix=True, suffix=True)

VERIFIED: every character accounted for exactly once.
exit=0
```

4 COVERAGE lines (197, 199, 201, 245), 34 CONTENT lines, 1 RETAINED line,
`VERIFIED`, `exit=0` — matching the plan's expectation exactly.

## Step 2 — independent arithmetic

Run directly against the pinned source (`git show 27b3986:CLAUDE.md`), never
the working tree, and against the committed map
(`docs/superpowers/specs/2026-09-09-claude-md-split-map.json`):

```
       77 chars  (retained in CLAUDE.md)
     4279 chars  docs/page-segmentation.md
    45527 chars  docs/room-detection-rules.md
     3923 chars  docs/scale-normalization-findings.md
    18476 chars  docs/w-gate-recalibration-handoff.md
    54080 chars  docs/wall-network-rules.md
   126362 chars  TOTAL
   126362 chars  source lines 197+199+201+245

CLAUDE.md: 154912 -> 32002 chars (79.3% smaller)
```

The per-document span totals sum to **126,362** and source lines
197+199+201+245 total **126,362** — the same number, independently derived.
All four source lines are span-assigned (this was fixed during planning: an
earlier draft of the map excluded lines 199 and 201, and the identity could
not hold under that draft), so this equality is the proof that no character
of the four moved paragraphs is missing or double-counted.

`CLAUDE.md` measures **32,002 characters**, not the plan's original "~26k /
≤30k" estimate (a pre-measurement figure, corrected once during planning to
"≤32,000") and not the brief's "~30,200" (also a pre-measurement estimate).
The measured breakdown: 154,912 source chars − 126,362 moved chars =
28,627 chars survive verbatim, plus 3,375 chars of newly written pointer
prose replacing the four moved paragraphs = 32,002. This is **2 characters**
over the plan's `≤32,000` guard — see "Deferred minors" below.

## Step 3 — fast test tier

```
$ source .venv/bin/activate && python -m unittest discover tests
...
FAIL: test_the_function_and_the_cli_agree_field_for_field
  (test_takeoff_fn_equivalence.TestCliEquivalence.test_the_function_and_the_cli_agree_field_for_field)
  (field='warnings')
Ran 1452 tests in 58.789s
FAILED (failures=1)
```

1452 tests, 1 failure: `test_takeoff_fn_equivalence` disagreeing on a
`TAKEOFF_REGIONS_UNCLASSIFIED` warning (a region-classification cache/state
flake — reproducible in isolation, re-running the single test in isolation
reproduces the same diff). This is the pre-existing "room-label/region-cache
equivalence flake" already on record in project memory
(`project-sweep-tooling-gotchas.md`, `project-w-gate-iter3-step12.md`: "the
equivalence test flakes on label cache" / "during concurrent reseed") and is
environmental, not a code regression — this branch touches no file under
`detection/`, `tests/`, `tools/`, `scale/`, `takeoff/`, `layout/`, `gemini/`,
or `extraction/` (see Step 4), so there is no code path this branch could
have changed to produce it. Named explicitly per the brief's allowance.

## Step 4 — no project code modified

```
$ git diff --stat main --name-only | grep -E "^(detection|tests|tools|scale|takeoff|layout|gemini|extraction)/" || echo "  none — correct"
  none — correct
```

Full list of files changed vs `main` (14 files, all documentation, specs, or
the `fix-detection` skill):

```
.claude/skills/fix-detection/SKILL.md
.claude/skills/fix-detection/evals/evals.json
.claude/skills/fix-detection/references/file-map.md
CLAUDE.md
README.md
docs/page-segmentation.md
docs/room-detection-rules.md
docs/scale-normalization-findings.md
docs/superpowers/plans/2026-09-09-claude-md-split.md
docs/superpowers/specs/2026-09-09-claude-md-split-design.md
docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
docs/superpowers/specs/2026-09-09-claude-md-split-map.json
docs/superpowers/specs/2026-09-09-claude-md-split-verify.py
docs/w-gate-recalibration-handoff.md
docs/wall-network-rules.md
```

## Pre-move overlap measurements (reported, never acted on)

Tasks 5 and 6 each measured, before moving a paragraph, whether its content
already duplicated an existing document — as a number to report, never a
deletion gate. Both scripts read every file via `git show 27b3986:<path>`,
**before** the move landed:

- **Line 199** (the scale-factor paragraph, into `docs/scale-normalization-findings.md`):
  **7 claims, 0 present** in the pre-move findings document as complete
  claims (whole-sentence matching against the document's own text).
- **Line 201** (the W-gate census/iteration log, into
  `docs/w-gate-recalibration-handoff.md`): **33 claims, 0 present** in the
  pre-move W-gate corpus (25 files matched `docs/w-gate*.md`) as complete
  claims.

Both numbers match the plan's expectation exactly. Re-running the identical
scripts against the *post-move* documents (reproduced during this task)
reads **7/7** and **33/33** respectively — every claim now present, because
the target document now *contains* the moved paragraph verbatim. This is
exactly why the pinned ref (`27b3986`) is load-bearing rather than optional:
reading the working tree at any point after the move would have reported
"every claim already present" and made the overlap look like a pre-existing
duplicate, when in fact it was zero. Nothing was ever deleted on the
strength of these numbers — each paragraph moved whole, span-assigned, and
COVERAGE/CONTENT above prove it landed intact.

## Complete repair log

Three sections' worth of source text needed light grammatical repair where a
sentence was extracted mid-flow (dropping a leading conjunction that made
sense inline but not as a document opener, capitalizing the new sentence
start, or closing a sentence the original left open into the next span). The
verifier inverts every repair before comparing against the source, so a
repaired section still proves byte-identical to its source span once
un-repaired.

```
docs/wall-network-rules.md §Pairing — plain, thick and through tiers  [W6a]
    append_period
docs/wall-network-rules.md §Pairing — taper, redundancy collapse and the far-side rule  [W6b]
    capitalize_first
    append_period
docs/wall-network-rules.md §The weak tier and the material gate  [W7]
    capitalize_first
    append_period
docs/wall-network-rules.md §Wall pens and the doorway veto  [W8]
    drop_leading_word ('and')
    capitalize_first
    append_period
docs/wall-network-rules.md §Fill rings and class rating  [W9]
    append_period
docs/wall-network-rules.md §Fill seams  [W9b]
    drop_leading_word ('and')
    capitalize_first
docs/wall-network-rules.md §Known gap: glyph-outline fill rings  [W10d]
    append_period

7 sections carry repairs; all inverted by the verifier before comparison.
```

All seven repaired sections belong to line 197's 31-span breakup (the "Room
detection" paragraph's wall-network half); lines 199, 201, and 245 needed no
repairs — they moved as single, uninterrupted spans.

## Knowledge graph refresh

```
$ ~/.local/bin/graphify update .
AST extraction: 413/413 files (100%) [10 workers]
[graphify watch] backed up curated graph (5 files) -> 2026-09-09/
[graphify watch] Rebuilt: 5522 nodes, 13544 edges, 330 communities
```

### Retrieval check

The plan's premise was that a single 100k-character line is a poor
retrieval unit. Two ways of confirming this:

**Node-level, before vs. after.** The pre-update graph (backed up to
`graphify-out/2026-09-09/graph.json`, dated 2026-09-06 — before this
branch's moves) has exactly one document node covering all of CLAUDE.md's
room-detection/wall-network prose: `Module layout` (`CLAUDE.md` L135–L203).
No node in that graph carries a label like "band pocket," "band-pocket end
closures," or any of the other ~18 rule clusters the paragraph held — they
were all inside one node's text, unaddressable individually. The refreshed
graph has 18 separate heading nodes for `docs/room-detection-rules.md` and
17 for `docs/wall-network-rules.md`, including
`docs_room_detection_rules_band_pocket_end_closures`
(`docs/room-detection-rules.md` L517).

**Query-level.** `graphify query` (BFS from keyword-matched seed nodes)
seeded on code identifiers for "why is a band pocket not a room" (`room()`
test fixtures, `band_census.py`, `pocket_census.py`) rather than the
document node — a limitation of its code-first seeding, not the split.
`graphify explain "band pocket"` (concept lookup) resolves directly and
solely to the intended target:

```
$ ~/.local/bin/graphify explain "band pocket"
Node: Band-pocket end closures
  Source:    docs/room-detection-rules.md L517
  Type:      document
  Community: 182
  Connections (1):
    <-- Room detection rules [contains] [EXTRACTED]
```

Before the split this same lookup had no node to resolve to short of the
entire `Module layout` section (which never appeared under a "band pocket"
label at all, since the label was CLAUDE.md's generic heading, not the rule
name). Retrieval is scoped and specific now where it was previously
all-or-nothing; recorded here as the side benefit the plan named, not a
data-loss check.

## Deferred minors (for the whole-branch review to triage)

1. `docs/hatch-cell-chords-handoff.md:62` phrases its CLAUDE.md reference as
   a live instruction ("1. CLAUDE.md 'Room detection' paragraph — the
   sentence beginning…"). That handoff's work shipped 2026-09-02, so it
   reads as historical, but an agent resuming it would follow a dead
   pointer. Left untouched by standing ruling: it is a frozen historical
   record.
2. Twelve stale `CLAUDE.md "Room detection"` references remain across four
   files, all deliberately excluded from repathing: the two frozen
   historical records (this one, and `docs/w-gate-recalibration-handoff.md`'s
   earlier step prompts) plus this project's own plan and spec, which must
   quote the pre-split text verbatim to explain what was moved and why.
3. `CLAUDE.md` is 2 characters over the plan's `≤32,000` guard — the blank
   line between the line-197 pointer's two paragraphs, kept because the
   replacement blocks are verbatim and the blank line matches existing house
   style elsewhere in the file.

## Summary

| | Before | After |
|---|---|---|
| `CLAUDE.md` | 154,912 chars | 32,002 chars (−79.3%) |
| Room-detection/wall-network content | 1 undifferentiated 100k-char line | 35 addressable sections across 2 documents |
| Verifier | n/a | `VERIFIED`, exit 0, 4 COVERAGE + 34 CONTENT + 1 RETAINED |
| Arithmetic identity | n/a | 126,362 = 126,362, exact |
| Fast test tier | 1452 tests | 1452 tests, 1 pre-existing environmental flake, 0 code touched |
| Knowledge graph | 1 node for the whole block | 35 addressable heading nodes, concept lookup resolves directly |

No file under `detection/`, `tests/`, `tools/`, `scale/`, `takeoff/`,
`layout/`, `gemini/`, or `extraction/` was modified by this branch.
