# Splitting CLAUDE.md into referenced rule documents

Date: 2026-09-09
Status: design, awaiting implementation plan

## Problem

`CLAUDE.md` is 156,559 characters over 384 lines. It is loaded into the
context of **every** session in this repo, including sessions that touch a CLI
flag, the takeoff, the Gemini cache or the region classifier and never go near
wall or room detection. At roughly 40k tokens that is both a per-session cost
and an attention cost: the instructions that govern a session compete with
s17's reveal-strip margins for the model's attention.

Four lines carry 82 % of the file:

| Line | Chars | Content |
|---|---|---|
| 197 | 100,654 | The "Room detection" paragraph — one single line, 112 sentences, ~18 distinct rule clusters |
| 201 | 18,690 | "The W references are being re-derived…" — the W-gate census and iteration 1–3 step log |
| 245 | 4,394 | Page-segmentation detail inside pipeline stage 3 |
| 199 | 3,968 | "Wall/room world-space gates" — the scale-factor paragraph |

Everything else — project purpose, commands, regression testing, the module
tree, Gemini auth, the seven pipeline stages, output layout, data model,
warning codes, graphify — totals ~29k and is the content an agent needs in
order to orient at all.

Line 197 is not only read every session, it is **written** most iterations:
`fix-detection` phase 5 step 5 requires the agent to add each new rule, its
measured numbers and its sheets to it. Eighteen W-gate steps have each
appended to it. Two consequences follow:

- Appending to a 100,654-character single line has no unique anchor, so the
  edit is fragile.
- The resulting diff is one enormous changed line, which cannot be reviewed at
  the user's checkpoints.

## Goals

1. Cut `CLAUDE.md` to ~26k characters while leaving it fully self-sufficient
   for orientation — an agent must still be able to work out what this repo is
   and where everything lives from `CLAUDE.md` alone.
2. Preserve **every** character of measured evidence. The numbers are the
   asset: the generic-fix rule and the census log both record that every
   constant moved without its measured false class in view broke something.
3. Make the detection rules retrievable by rule rather than by file — an agent
   diagnosing a band-pocket phantom should read ~8k, not 100k.
4. Make the prose *write* path surgical and its diff reviewable.
5. Keep `fix-detection` correct, and stop the new documents re-growing into
   single blobs.

## Non-goals

- **No rewording, condensing, summarising or "tidying" of the moved prose.**
  This is a move, not an edit. Prose quality improvements are a separate task
  and are explicitly out of scope.
- No change to code, tests, constants, detection behaviour or the `outputs/`
  JSON contract. The corpus sweep must be untouched by this work; it is not
  run as part of it.
- No rewriting of the ~40 *historical* step prompts in
  `docs/w-gate-recalibration-handoff.md` that say "the CLAUDE.md room
  paragraph". Those are records of what past agents were told and stay frozen.
  Only the live step-18 prompt is repathed.

## Target state

| File | Before | After |
|---|---|---|
| `CLAUDE.md` | 156.6k | **~26k**; each moved block replaced by a hard-instruction pointer in the style of the existing line 11 door-guide pointer |
| `docs/wall-network-rules.md` | — | new, ~55k, 10 headed sections — `detection/walls.py` |
| `docs/room-detection-rules.md` | — | new, ~45k, 9 headed sections — `detection/rooms.py` |
| `docs/page-segmentation.md` | — | new, ~4.4k, from line 245 |
| `docs/w-gate-recalibration-handoff.md` | | gains only what the dedup proves is unique to line 201; live step-18 prompt repathed |
| `docs/scale-normalization-findings.md` | | gains anything in line 199 not already in §4 |
| `.claude/skills/fix-detection/SKILL.md` | | 3 repaths, a symptom→section routing table, a phase-5 heading rule |
| `.claude/skills/fix-detection/references/file-map.md` | | Walls and Rooms "Read first" rows repathed; s01/s02 note repathed |
| `.claude/skills/fix-detection/evals/evals.json` | | 2 grading criteria repathed (see Risk 4) |
| `README.md` | | 1 line |

The two rule documents mirror the code, so `file-map.md`'s existing Walls and
Rooms rows need a path change rather than a rethink.

## The split protocol

This is where all the risk lives, so it is specified tightly.

### Why clause boundaries

Topics turn **mid-sentence**, repeatedly. Measured in line 197:

- Barrier tier 2 ("(2) wall-fill polygons — closed rings reconstructed by
  chaining consecutive same-fill `l` items…") begins at offset 4,621 **inside**
  a single 8,263-character sentence whose first 4,621 characters are tier-1
  pairing rules.
- The fill-seam rule begins at offset 6,247 inside that same sentence.
- The wall-pen doorway veto ("and since W-gate iteration 3 step 11 the sheet's
  DOORWAYS decide among the candidates") begins at offset 4,693 inside a
  5,487-character sentence.
- Barrier tier 3 ("(3) thin buffers of QUALIFYING faces only") begins at offset
  1,779 inside a 4,209-character sentence.
- The entrance-run rule begins at offset 865 inside a 1,717-character sentence.

Splitting only at sentence boundaries would file roughly 15k of content under
the wrong heading, which defeats goal 3.

### Rules

At a split point, and **nowhere else**, these three repairs are permitted:

1. Terminate the preceding clause with `.`
2. Capitalise the first letter of the new clause.
3. Drop a leading connective (`and`, `while`, `but`, `so`) only where the split
   leaves it orphaned.

Forbidden everywhere: rewording, reordering *within* a section, summarising,
deleting, merging, or altering any number, path, identifier, sheet slug or
measurement.

### The section map is the reviewable artefact

Every section carries a machine-readable source span — `(line, start_offset,
end_offset)` into the original `CLAUDE.md`. The map is produced and **reviewed
first**, before any prose is moved. Judgement lives entirely in the map; the
move itself is then mechanical.

Spans may be assigned to sections **out of linear order**. This is required:
the "Four barrier tiers" enumeration is `rooms.py` framing whose tier-1 and
tier-2 entries digress deep into `walls.py` pairing, fill-rating and seam
rules. The tier overview belongs in `room-detection-rules.md`; those digressions
belong in `wall-network-rules.md` under their own headings, with the tier
entries cross-referencing across. Order is preserved *within* every section.

### Verification gate

A throwaway script (scratchpad, never committed to the repo) reassembles the
original from the section spans **in source order** and compares byte-for-byte
against the original `CLAUDE.md` at its pre-split commit. It must report:

- every character of lines 197, 199, 201 and 245 accounted for **exactly once**
  — no loss, no duplication, no overlap;
- zero differences except the entries in the repair log.

The section map and the repair log are both committed, as
`docs/superpowers/specs/2026-09-09-claude-md-split-section-map.md` and
`…-repair-log.md`. The map is presented for review before any prose moves. The
log lists each repair as one line, e.g.:

```
docs/wall-network-rules.md §Fill rings and seams
  split at "…; and fill SEAMS never become faces"
  added '.' to previous clause; dropped leading "and"; capitalised "Fill"
  words added: 0   words removed: 1 ("and")
```

Measured while planning, against the real file: **7 entries**, all in the wall
document. The 16 room sections and the page-segmentation section need none. If
the verifier does not come back clean, the move does not land. The script's
output is committed as the verification report.

## Section map (proposed; finalised and reviewed in implementation step 1)

`docs/wall-network-rules.md` — `detection/walls.py`

1. Order and exclusion sets — detection order, text spans, annotation layers, vector text, drawn dash lines, door open-leaf exclusion, french/sliding/folding/garden treatment
2. Stroked rectangles as weak faces
3. Face collection and the length floor
4. Lattice demotion — striped fields and hatch
5. Stair demotion — tread runs, stair arrows, winder fans, zones
6. Pairing — plain, thick and through tiers
7. The weak tier and the material gate — far-side rules, interior-pair claims, taper, redundancy collapse
8. Wall pens and the doorway veto
9. Fill rings, seams and fill-class rating
10. The collinear-merge anchor

`docs/room-detection-rules.md` — `detection/rooms.py`

1. Barriers are allowlisted — the four barrier tiers (overview, cross-referencing wall-network §§6–9)
2. Thin buffers and white rings — tiers 3 and 4
3. Jamb rings and door linings
4. Window seals
5. Door plugs — qualification, cross-section fit, tails, the seek, the plane stamp, the bbox fallback
6. Free-space components and their filters
7. Recess, band pocket and blind-window drops
8. Entrances
9. Limitations and scope

`docs/page-segmentation.md` — the whole of line 245.

## Sequencing

Four commits, so any one can be reverted alone.

1. **Add.** Create the three new documents and the repair log. Delete nothing
   from `CLAUDE.md`. Run the verifier. The tree is briefly *duplicated*, which
   is the safe intermediate state.
2. **Cut.** Reduce `CLAUDE.md` to its pointers. Re-run the verifier against the
   pre-split commit from git history.
3. **Dedup.** Merge line 201's unique content into
   `docs/w-gate-recalibration-handoff.md` and line 199's into
   `docs/scale-normalization-findings.md` §4, with the dedup report attached.
   This is the only commit containing judgement calls about deletion.
4. **Repath.** `SKILL.md`, `file-map.md`, `evals.json`, `README.md`, and the
   live step-18 prompt.

Then `graphify update .`.

## fix-detection changes

**Repaths.** `SKILL.md` lines 37, 78 and 145; `file-map.md` Walls and Rooms
"Read first" cells and the s01/s02 sheet note.

**Routing table** added to SKILL.md phase 2, so an agent reads the ~8k section
its symptom points at rather than a 50k file:

| Symptom | Read |
|---|---|
| Fixture outline fenced a phantom room (counter, wardrobe, bed, sofa, unit) | wall-network §7 weak tier and material gate, §8 wall pens |
| Paving, tile grid, roof tiles, floorboards or treads fencing | wall-network §4 lattice demotion |
| Stair flight came out as a room, or stair ink fenced | wall-network §5 stair demotion |
| Room edge notched, slanted or offset a few px along a wall | wall-network §10 collinear-merge anchor; room-detection §1 barrier tiers |
| Hatch or brick-cell diagonal produced a slanted band | wall-network §6 pairing (taper), §9 fill seams |
| Wall band contributed no faces at all | wall-network §2, §3 |
| Rooms merged through a doorway, or a swing square left its room | room-detection §5 door plugs |
| A narrow strip, reveal or cavity was emitted as a room | room-detection §7 recess / band pocket / blind window |
| A real room was dropped | room-detection §6 free-space filters, §8 entrances |
| Window seal wrong, or a bay window | room-detection §4 window seals |
| A constant may need to scale with drawing scale | `docs/scale-normalization-findings.md` §4 |

**Phase-5 write rule.** The "update the prose" step names the target document
and adds: *a NEW rule gets its OWN heading under the stage it belongs to; an
extension to an existing rule goes under that rule's heading.* Without this the
documents re-blob within a dozen iterations, which is precisely how `CLAUDE.md`
reached 156k.

## Risks

1. **Silent loss during the move.** Mitigated by the span-based verifier, which
   proves every character is accounted for exactly once. This is the whole
   reason the section map carries source spans rather than being written by
   hand.
2. **Misfiling.** Mitigated by reviewing the section map before any text moves.
3. **Line 201 is not a duplicate of the handoff.** Spot-checked: while
   `CROSS_DOOR_EXPAND_PX` and "short-piece material rule" each appear in four
   other documents, the phrases "Group 1 (2026-09-04)", "verdict-identical to
   main on all 20 sheets" and "recalibrated tree is verdict-identical" appear
   **nowhere else in the repo**. Commit 3 therefore deletes nothing until the
   dedup diff shows it survives elsewhere; anything unique is appended to the
   handoff's outcome log.
4. **`evals.json` rot.** Two grading criteria read *"CLAUDE.md room paragraph
   or a `docs/*tuning-guide*.md`"*. `docs/room-detection-rules.md` matches
   neither, so after the split the eval would grade a correct fix as a failure.
   Repathing them is 2 lines and is included in commit 4. This is an addition to
   the originally agreed scope and can be dropped at spec review.
5. **The read gate.** A pointer is weaker than inlined text. Mitigated on both
   sides: `CLAUDE.md`'s pointers are written as hard instructions in the style
   of the existing line 11 door-guide pointer, which already works; and
   `fix-detection` phase 2 mandates the read and now names the section.

## Success criteria

- `CLAUDE.md` ≤ 30k characters and still self-sufficient for orientation.
- Verifier reports every character of lines 197/199/201/245 accounted for
  exactly once, with zero differences beyond the logged repairs.
- Repair log committed, every entry showing zero words added and at most one
  connective removed.
- No file under `detection/`, `tests/`, `tools/` or `scale/` modified.
- `python -m unittest discover tests` green (unchanged — no code is touched).
- `fix-detection` references resolve: no path in `SKILL.md`, `file-map.md` or
  `evals.json` points at a section of `CLAUDE.md` that no longer exists.

## Branch strategy (resolved 2026-09-09)

At design time this was a live correctness constraint: `main`'s `CLAUDE.md` was
136,554 characters against the detection chain's 156,559, so 20k of W-gate step
14–17 prose existed only on `fix/wall-recess-tab-back-edge`, and splitting from
`main` would have silently dropped it — a direct violation of goal 2. Five
branches carried `CLAUDE.md` edits, all landing on exactly the mega-lines the
split deletes.

Resolved before implementation. The five branches were one linear chain, not
four divergent histories, with its tip strictly ahead of `main` (13 commits
ahead, 0 behind), so `main` was fast-forwarded 83a603c → 27b3986 and all five
merged branches deleted:

```
fix/band-pocket-ceiling-storage  acd7157
fix/band-pocket-tab-cover        b052729
fix/entrance-contact-run         8468ce5
recal/wall-max-thickness-40      b52384e
fix/wall-recess-tab-back-edge    27b3986
```

`main` now carries the complete 156,559-character `CLAUDE.md`, and
`docs/split-claude-md` is based on it. The split therefore captures every
measured line, and no detection branch is in flight to conflict with it.

Local only — `origin/main` is still at 83a603c and `origin` still holds three
of the deleted branches. Push when ready.

**Remaining constraint:** any *new* detection branch created before the split
lands and merged after it will hit a delete/modify conflict on the mega-lines
and need its prose re-filed by hand into the new documents. Keeping the split's
in-flight window short is worth more than any other scheduling consideration
here.
