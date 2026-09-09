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

Re-run after the post-review fix wave (2026-09-09): the wall document's sections
are now in source-offset order (W6b moved after W8, a map reordering with zero
prose edits), three sections carry `replace` repairs, and the verifier adds a
REACHABILITY check — every target document must still be cited BY PATH in the
working-tree `CLAUDE.md`. COVERAGE, CONTENT and RETAINED prove the characters
survive; only REACHABILITY proves anything auto-loaded still routes to them.
Measured before it existed: blanking lines 197/199/201 of `CLAUDE.md` left the
proof green (`VERIFIED`, exit 0) with all 126,362 characters unreachable. With
it, that attack reads:

```
FAIL: docs/room-detection-rules.md: no reference in the working-tree CLAUDE.md — the content survives but nothing auto-loaded routes to it
FAIL: docs/scale-normalization-findings.md: no reference ...
FAIL: docs/wall-network-rules.md: no reference ...
VERIFICATION FAILED — exit 1
```

(`docs/page-segmentation.md` and `docs/w-gate-recalibration-handoff.md` stay
REACHABLE under that attack because their pointer lines are not among the three
blanked — they are cited from lines 247 and 203 — and NOT because either is
cited more than once. Measured 2026-09-09: each of the five documents is cited
on exactly ONE line of the working-tree `CLAUDE.md` — wall and room on 199,
scale on 201, the handoff on 203, page segmentation on 247 (three of them
appear twice within that single line, none on a second line).

Blanking all four pointer lines instead of three fails all five REACHABLE
checks, and RETAINED as well, because line 247 is also the retained source
line 245:

```
FAIL: line 245: retained fragments [RET-245-head,RET-245-tail] matched 0 lines, need exactly 1 ...
FAIL: docs/page-segmentation.md: no reference in the working-tree CLAUDE.md — ...
FAIL: docs/room-detection-rules.md: no reference ...
FAIL: docs/scale-normalization-findings.md: no reference ...
FAIL: docs/w-gate-recalibration-handoff.md: no reference ...
FAIL: docs/wall-network-rules.md: no reference ...
VERIFICATION FAILED — exit 1
```

KNOWN LIMITATION, stated rather than fixed: REACHABILITY tests `path in
claude_md`, so an incidental mention of a document's path anywhere in
`CLAUDE.md` satisfies it exactly as a routing sentence does. That is sound
TODAY — each path occurs on one line and that line is the pointer — but it is
brittle: a future edit that mentions one of these paths in passing (a commit
note, an example, a "see also" in an unrelated section) would keep REACHABLE
green after the real pointer was deleted. Making the check demand a routing
sentence — a bolded imperative, or a proximity test against the document's own
title — is the next hardening, and it needs a definition of "routes to" that
this branch did not have to settle.

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
CONTENT  W7    docs/wall-network-rules.md         3788 chars exact
CONTENT  W8    docs/wall-network-rules.md         2933 chars exact
CONTENT  W6b   docs/wall-network-rules.md         3643 chars exact
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
REACHABLE docs/page-segmentation.md: cited in CLAUDE.md
REACHABLE docs/room-detection-rules.md: cited in CLAUDE.md
REACHABLE docs/scale-normalization-findings.md: cited in CLAUDE.md
REACHABLE docs/w-gate-recalibration-handoff.md: cited in CLAUDE.md
REACHABLE docs/wall-network-rules.md: cited in CLAUDE.md

VERIFIED: every character accounted for exactly once.
exit=0
```

4 COVERAGE lines (197, 199, 201, 245), 34 CONTENT lines, 1 RETAINED line and
5 REACHABLE lines, `VERIFIED`, `exit=0` — matching the plan's expectation
exactly, plus the REACHABILITY check added in the post-review fix wave.

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
`TAKEOFF_REGIONS_UNCLASSIFIED` warning. **Measured at the branch base**, not
deduced (this project's rule is that a deduction is not a measurement):

```
$ git worktree add /tmp/base27 27b3986
$ ln -s <repo>/fixtures/sheets /tmp/base27/fixtures/sheets
$ cd /tmp/base27 && <repo>/.venv/bin/python -m unittest tests.test_takeoff_fn_equivalence
FAIL: test_the_function_and_the_cli_agree_field_for_field (field='warnings')
AssertionError: Lists differ: ... First list contains 1 additional elements.
First extra element 2:
{'warning_code': 'TAKEOFF_REGIONS_UNCLASSIFIED', 'severity': 'warning',
 'message': 'Page 1: no region was classified, so the whole page was measured
 without floor-plan filtering', 'page_number': 1}
Ran 2 tests in 9.023s — FAILED (failures=1)
```

The same two tests at HEAD fail identically (same field, same extra element,
8.916s), so the failure is deterministic at BOTH ends and identical at both:
the branch neither introduced it nor changed it. It is the pre-existing
"room-label/region-cache equivalence flake" already on record in project memory
(`project-sweep-tooling-gotchas.md`, `project-w-gate-iter3-step12.md`: "the
equivalence test flakes on label cache" / "during concurrent reseed") and is
environmental — consistent with Step 4, which shows this branch touches no file
under `detection/`, `tests/`, `tools/`, `scale/`, `takeoff/`, `layout/`,
`gemini/`, or `extraction/`.

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

Seven sections' worth of source text needed light grammatical repair where a
sentence was extracted mid-flow (dropping a leading conjunction that made
sense inline but not as a document opener, capitalizing the new sentence
start, or closing a sentence the original left open into the next span), and
three more carry `replace` repairs added in the post-review fix wave (below).
The verifier inverts every repair before comparing against the source, so a
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

7 sections carry grammatical repairs; all inverted by the verifier before comparison.
```

All seven grammatically repaired sections belong to line 197's 31-span breakup
(the "Room detection" paragraph's wall-network half); lines 199, 201, and 245
needed none — they moved as single, uninterrupted spans.

### `replace` repairs (post-review fix wave, 2026-09-09)

The whole-branch review found three references that the MOVE ITSELF falsified —
directional wording pointing at a paragraph that is now in another file, or
nowhere — and a later pass found a ninth (below). Move-not-edit exists to
protect measured numbers, not to preserve pointers the move broke, so the map
gained a fourth op:

```json
{"op": "replace", "old": "<exact source text>", "new": "<exact replacement>"}
```

`apply_repairs` asserts `old` occurs EXACTLY ONCE in the span and substitutes
it; `invert` asserts `new` occurs exactly once in the written section and
substitutes back. Ops apply in order and invert in reverse, like the other
three. 9 ops in 3 sections; no number, constant, path, identifier, sheet slug
or measurement changes in any of them — since 2026-09-09 that is ENFORCED, not
asserted (see "The `replace` token guard" below).

```
docs/wall-network-rules.md §Order and exclusion sets  [W1]           1 replace
    "…are in the gates paragraph below"
 -> "…are in `docs/w-gate-recalibration-handoff.md` §"Iteration 1–3 summary,
     moved from CLAUDE.md (2026-09-09)", step 6"
docs/room-detection-rules.md §Plane stamp and the bbox fallback  [R5f]  1 replace
    "glyph-outline rings (gap (b) below)"
 -> "glyph-outline rings (gap (b), `docs/wall-network-rules.md` §"Known gap:
     glyph-outline fill rings")"
docs/w-gate-recalibration-handoff.md §Iteration 1–3 summary…  [H1]   7 replace
    six occurrences of "in the room paragraph above", each disambiguated by the
    identifier before it, repointed to the section that now holds the rule:
    `_clip_plug_tails`               -> room §"Tail trim and clip"
    `_doorway_pens`                  -> wall §"Wall pens and the doorway veto"
    `_entrance_run`                  -> room §"Entrances"
    `cap_lines`                      -> room §"The band-pocket drop"
    `ROOM_BAND_POCKET_END_CLOSURE_MIN` -> room §"Band-pocket end closures"
    `ROOM_RECESS_BACK_COVER_MIN`     -> room §"The wall-recess drop"
    plus the SEVENTH occurrence, which reads only "the paragraph above":
    `scale/dimensions.py`            -> findings §"4g. The detection-scale
                                        factor (moved from CLAUDE.md,
                                        2026-09-09)"
```

The ninth op, and why the fix wave missed it (2026-09-09). Source line 201
carries SEVEN occurrences of "paragraph above". The wave above fixed the six
reading "the room paragraph above" and its `grep -c 'the room paragraph above'`
legitimately returned 0 — but the PATTERN WAS NARROWER THAN THE DEFECT CLASS.
The seventh, in the step-12 sentence, reads only "the paragraph above":

```
…let the drawing's dimension strings verify a measured scale for the gates
(`scale/dimensions.py`, the paragraph above): s01 runs at its true factor…
```

Its antecedent is source line 199, now `docs/scale-normalization-findings.md`
§"4g. The detection-scale factor (moved from CLAUDE.md, 2026-09-09)". Because
H1 is APPENDED at the end of the handoff, "the paragraph above" resolved
instead to the step-4 `WALL_MAX_THICKNESS_PX` outcome that now precedes it — a
plausible-looking wrong rule, which is the worst kind of stale pointer. The
lesson worth keeping: a grep that returns 0 proves the absence of the PATTERN,
never the absence of the DEFECT; the count that mattered was the 7 occurrences
of the general form, against the 6 the narrow pattern caught. Confirmed the
bare form occurs exactly once in the span before recording it, and "the room
paragraph above" does not contain "the paragraph above", so the generator's
single-match assertion holds whichever op runs first.

### The `replace` token guard (2026-09-09)

`invert` restores `new`->`old` before CONTENT compares, so ANY consistent
(map, document) pair passes the character proofs. The reviewer demonstrated it:
shipping `ROOM_RECESS_BACK_COVER_MIN` 0.65 -> 0.95 in
`docs/room-detection-rules.md` with a matching map entry verifies clean, exit
0. The other three ops are structurally constrained — `append_period` adds one
".", `capitalize_first` changes one letter's case, `drop_leading_word` is
inverted from the map's own `word` — but `replace` is free text on both sides,
so it gave the map a kind of trust it did not have before, and nothing bounded
it.

The bound, written out in BOTH the generator (`apply_repairs`, an `assert`) and
the verifier (`invert`, a `fail`; the verifier never imports the generator, so
the check is duplicated by design): `old` and `new` must carry IDENTICAL
MULTISETS of numbers and backticked tokens, once the routing reference the
repoint exists to add is stripped out of `new` (`_strip_refs`: a target
document's backticked path plus the section clause and step number that belong
to it). A repoint may therefore only ADD a pointer — never drop, alter or
invent a measurement, constant name, identifier, path or sheet slug in the
prose around it.

Stripping is what makes EQUALITY achievable rather than mere preservation: a
repoint exists to add a `docs/...md` path, and two of the nine references carry
digits of their own (W1's §"Iteration 1–3 summary, moved from CLAUDE.md
(2026-09-09)", step 6; the ninth op's §"4g. The detection-scale factor (moved
from CLAUDE.md, 2026-09-09)"). Outside that reference the two sides must match
exactly, which is the property this branch's own constraint states.

All nine ops pass, measured op by op — the non-empty token multisets are H1's
`scale/dimensions.py`, `cap_lines`, `_clip_plug_tails`, `_doorway_pens`,
`_entrance_run`, `ROOM_RECESS_BACK_COVER_MIN`, and `0.65` + `36` carried
through the end-closures op unchanged; W1's and R5f's are empty.

Bite-proof on the reviewer's own attack, staged and then reverted:
```
(a) guard removed from the verifier, 0.95 shipped in docs/room-detection-rules.md
    and recorded in the map:
    VERIFIED: every character accounted for exactly once.        exit 0
    <- the hole reproduces
(b) verifier as shipped:
    FAIL: R7a: replace changes the moved prose's numbers/backticked tokens:
          dropped {'0.65': 1}, added {'0.95': 1} (outside the routing reference)
    VERIFICATION FAILED                                          exit 1
(c) generator as shipped:
    AssertionError: replace changes the moved prose's numbers/backticked tokens:
          dropped {'0.65': 1}, added {'0.95': 1} (outside the routing reference)
                                                                 exit 1
    <- fires before any document is written
```

Two measured corrections to the review's own brief, recorded rather than
assumed: the handoff carries **six** occurrences of "in the room paragraph
above", not four (all six repointed; `grep -c` now returns 0); and W1's "gates
paragraph below" points at the handoff's iteration summary, not
`docs/scale-normalization-findings.md` §4g — measured on the pinned source,
line 199 (which became §4g) contains the string "dash" zero times while line
201 (which became the iteration summary) carries the dash-row rule in full,
with its 18px = 3mm margin, under step 6.

Bite-proofs, both directions:
```
recorded but unapplied (bogus replace on R4, document not regenerated):
  FAIL: replace recorded but 'A BOGUS DIAGONAL window' occurs 0 times, need 1
  VERIFICATION FAILED, exit 1
applied but unrecorded (DIAGONAL -> BOGUSDIAGONAL edited into the document):
  FAIL: R4: diverges at 70
  VERIFICATION FAILED, exit 1
```

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

1. **RESOLVED in the post-review fix wave.**
   `docs/hatch-cell-chords-handoff.md:62` phrased its CLAUDE.md reference as
   a live instruction ("1. CLAUDE.md 'Room detection' paragraph — the
   sentence beginning…") and was left untouched here by the standing
   "frozen historical record" ruling. The whole-branch review overturned that
   ruling for this line and for `docs/backlog/step-3-s15-false-positive-
   diagnosis.md:23`/`:45`: both are LIVE — item 1 is reached by the step-18
   prompt's "Gap D of `docs/hatch-cell-chords-handoff.md`" pointer, and the
   backlog document is unstarted work whose whole method is reading that
   catalog. Both now name `docs/wall-network-rules.md` /
   `docs/room-detection-rules.md`.
2. Stale `CLAUDE.md "Room detection"` references that remain, deliberately.
   Measured after the fix wave with
   `grep -rn 'CLAUDE\.md' docs/ .claude/ README.md | grep -vi 'claude-md-split'
   | grep -iE 'room detection|room paragraph|room section'`: **18 hits in four
   files** — `docs/w-gate-recalibration-handoff.md` (14, every one inside a
   `>` blockquoted dated step prompt), `docs/hatch-cell-chords-handoff.md` (2,
   both blockquoted, lines 260 and 326), `docs/w-gate-iter3-checkpoints/
   step-8.md` (1) and `docs/w-gate-iter3-checkpoints/step-9-review-prompt.md`
   (1). All are records of what a past agent was told or reported; rewriting
   them falsifies the record. This project's own plan and spec are a separate
   population — they must quote the pre-split text verbatim to explain what
   moved — and are excluded from the pattern above. (The earlier "twelve
   across four files" in this report conflated the two populations and used a
   narrower pattern; the number above is the measured one.)
3. `CLAUDE.md` is 2 characters over the plan's `≤32,000` guard — the blank
   line between the line-197 pointer's two paragraphs, kept because the
   replacement blocks are verbatim and the blank line matches existing house
   style elsewhere in the file.

## Summary

| | Before | After |
|---|---|---|
| `CLAUDE.md` | 154,912 chars | 32,002 chars (−79.3%) |
| Room-detection/wall-network content | 1 undifferentiated 100k-char line | 35 addressable sections across 2 documents |
| Verifier | n/a | `VERIFIED`, exit 0, 4 COVERAGE + 34 CONTENT + 1 RETAINED + 5 REACHABLE |
| Arithmetic identity | n/a | 126,362 = 126,362, exact |
| Fast test tier | 1452 tests | 1452 tests, 1 failure measured IDENTICAL at base 27b3986, 0 code touched |
| Knowledge graph | 1 node for the whole block | 35 addressable heading nodes, concept lookup resolves directly |

No file under `detection/`, `tests/`, `tools/`, `scale/`, `takeoff/`,
`layout/`, `gemini/`, or `extraction/` was modified by this branch.
