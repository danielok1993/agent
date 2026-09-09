# CLAUDE.md Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move 126,285 characters of detection prose out of `CLAUDE.md` into three referenced documents, losing nothing, and repoint the `fix-detection` skill at them.

**Architecture:** A committed **section map** (JSON) assigns every character of the four oversized source lines to either a target document section or to "retained in CLAUDE.md". A **generator** slices the documents straight out of `CLAUDE.md` from that map — the prose is never retyped, so paraphrase is structurally impossible. An **independent verifier** then reads only the written documents and the original source and proves every character is accounted for exactly once.

**Tech Stack:** Python 3 stdlib only (`json`, `subprocess`, `re`, `unicodedata`). No new dependencies, no changes to project code.

**Spec:** `docs/superpowers/specs/2026-09-09-claude-md-split-design.md`

## Global Constraints

- **Branch:** `docs/split-claude-md`, based on `main` at `27b3986`. Never commit to `main`.
- **No AI-attribution trailer** on any commit (`Co-Authored-By`, `Generated with`). Project rule.
- **This is a move, not an edit.** No rewording, condensing, summarising or tidying of moved prose. No altering any number, path, identifier, sheet slug or measurement.
- **No file under `detection/`, `tests/`, `tools/`, `scale/`, `takeoff/`, `layout/`, `gemini/`, `extraction/` may be modified.** No detection behaviour changes. The corpus sweep is not run and must not be needed.
- **Permitted repairs, only at a split point:** (1) terminate the preceding clause with `.`; (2) capitalise the new clause's first letter; (3) drop an orphaned leading connective (`and`/`while`/`but`/`so`). Every instance is recorded in the section map as a machine-readable `repairs` entry.
- **Measurements are in characters (codepoints), not bytes.** `CLAUDE.md` at `27b3986` is 154,912 chars / 156,559 bytes / 385 lines. `awk length()` reports bytes and disagrees; use Python.
- **Source-of-truth line numbers** (1-based, in `CLAUDE.md` at `27b3986`): 197 (99,607 chars), 199 (3,923), 201 (18,476), 245 (4,356, of which only offsets [68, 4347) move).

### Correction to the spec

The spec estimated CLAUDE.md landing at "~26k" and set a success criterion of "≤30k". Both were byte/char estimates made before measurement. Measured: removing the four spans leaves **28,627 chars**, and the replacement pointers add ~1.6k, so the real landing is **~30.2k chars**. The success criterion is therefore **≤32,000 chars**. This is a corrected figure, not a scope change.

### Refinement to the spec

The spec proposed four commits. This plan uses nine tasks, each committing. Strictly more revertible, and it puts a reviewer gate on the section map *before* any prose moves — which the spec requires but four commits cannot express.

### Plan validation (done before this plan was written)

The machinery below is not sketched — it was prototyped against the real
`CLAUDE.md` at `27b3986` and the results are baked into the plan:

- **COVERAGE proven:** line 197's 31 spans and line 245's 3 spans are
  contiguous, gapless and overlap-free, summing to 99,607 and 4,356 chars
  exactly.
- **Round-trip proven:** all 34 sections slice → repair → wrap → invert →
  normalise back to text identical to their source spans.
- **One real bug found and fixed:** `textwrap.wrap`'s default
  `break_on_hyphens=True` split `already-slanted` across lines, and re-joining
  inserted a space that was never in the source. The generator now passes
  `break_on_hyphens=False, break_long_words=False`. This is the class of
  silent corruption the verifier exists to catch, and it caught one before a
  single character moved.
- **One schema gap found and closed:** repairs address a section's leading and
  trailing edges only, so a section built from two non-adjacent spans would
  need an unrepresentable repair at its internal junction. The pairing rules
  are therefore two sections (W6a, W6b) rather than one two-span section, and
  every section is now a single contiguous span.
- **Repair count measured:** 7, not the spec's estimated 25–40.
- **Append-mode `upsert` proven idempotent** in both positions (section last, section followed by another heading), with neighbouring sections untouched, and its output recovered byte-exactly by the verifier's heading parser.

Three further defects were found in code review of this plan and are fixed
above. All three were verified by running the offending code against the real
repository, not by inspection:

- **The dedup probe would have destroyed 22,399 characters.** It classified a
  whole claim as already-present when *any* eight-word window matched. Measured:
  3 of line 199's 7 claims and 17 of line 201's 33 marked PRESENT, while **zero**
  complete claims occur in the searched corpora — one accepted claim ran 223
  words, another 269. Those claims were then to be dropped, after the source
  line had already been replaced. Lines 199 and 201 are now span-assigned like
  197 and 245, so the same COVERAGE and CONTENT proof covers them; exact
  whole-claim matching finds **0** droppable claims, so the dedup premise was
  wrong — the overlap is at phrase level (shared constant names), not claim
  level. The number is reported, never acted on.
- **The verifier covered only two of the four deleted lines.** A direct
  consequence of the above, and it made the spec's central "every character
  accounted for" guarantee untrue for 22,399 chars. Now all four lines are
  covered, and Task 9's arithmetic reconciles against all four rather than
  expecting an equality that could not hold.
- **The generator was not reproducibly pinned to the source.** It read the
  working-tree `CLAUDE.md` while the map recorded `source_ref`, so any re-run
  after the cut would slice pointers or empty offsets. It now loads
  `git show {source_ref}:{source_file}`, as the verifier already did.

The cut is also reordered to run last of the content tasks, so no content is
absent from the working tree even for a single commit.

A second review round found four more, all reproduced against the repository
before fixing:

- **The preserved line-199 content was not routed to anyone.** F1 appended at
  the end of the findings document lands after §7, while every pointer and the
  skill's routing table aim at §4 — content preserved but undiscoverable. The
  generator now supports `insert_after`, F1 lands as **§4g between §4f and §5**,
  and both the CLAUDE.md pointer and the routing row name it. Verified: correct
  position, idempotent insert, all 12 pre-existing sections byte-identical.
- **The overlap measurement could only ever report 7/7.** It generated F1 into
  the findings document and then searched that same document for the source
  claims. Measured both ways: **0 of 7** against the pre-move document, **7 of
  7** against the post-move one. Both measurements now read every file at
  `27b3986`.
- **Retained spans had COVERAGE but no CONTENT proof.** The verifier skips
  `doc: null` sections, so after the cut, deleting line 245's 77 retained
  characters would still have printed `VERIFIED`. The verifier now has a
  RETAINED check asserting each retained fragment is still present in the
  working-tree `CLAUDE.md`.
- **Stale counts and reordered-task leftovers** (32 vs 34 sections, room 15 vs
  16, 30 vs 31 line-197 spans, Task 4 expecting sections that arrive two tasks
  later, "Task 5 shortens", "Same correction as Task 6") — all corrected, so
  the intermediate acceptance checks and commit records are accurate.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/specs/2026-09-09-claude-md-split-map.json` | **Create.** The section map: every span, its target document and heading, and its repairs. The single artefact carrying all judgement. |
| `docs/superpowers/specs/2026-09-09-claude-md-split-generate.py` | **Create.** Generator: map + `CLAUDE.md` → the three documents. Deterministic, re-runnable. |
| `docs/superpowers/specs/2026-09-09-claude-md-split-verify.py` | **Create.** Independent verifier. Reads only the written documents and `git show 27b3986:CLAUDE.md`. Never imports the generator. |
| `docs/superpowers/specs/2026-09-09-claude-md-split-verification.md` | **Create.** Committed verifier output — the no-data-loss proof, reproducible. |
| `docs/wall-network-rules.md` | **Create.** `detection/walls.py` rules. 15 sections, 54,080 chars. |
| `docs/room-detection-rules.md` | **Create.** `detection/rooms.py` rules. 16 sections, 45,527 chars. |
| `docs/page-segmentation.md` | **Create.** `layout/` ink map, nested-frame skip, four gutter tiers. 4,279 chars. |
| `CLAUDE.md` | **Modify.** Lines 197/199/201 replaced by pointers; line 245's movable span replaced by a pointer clause. |
| `docs/scale-normalization-findings.md` | **Modify.** Append-mode target: receives the whole of line 199 as section `F1`, span-proven. |
| `docs/w-gate-recalibration-handoff.md` | **Modify.** Append-mode target: receives the whole of line 201 as section `H1`, span-proven; live step-18 prompt repathed. |
| `.claude/skills/fix-detection/SKILL.md` | **Modify.** 3 repaths, routing table, phase-5 heading rule. |
| `.claude/skills/fix-detection/references/file-map.md` | **Modify.** Walls/Rooms "Read first" rows, s01/s02 note. |
| `.claude/skills/fix-detection/evals/evals.json` | **Modify.** 2 grading criteria. |
| `README.md` | **Modify.** 1 line. |

The generator, verifier and map live beside the spec they serve rather than in `tools/` — they are one-off migration aids, and `tools/` is the home of detection dev scripts. They are committed rather than left in the scratchpad (a deviation from the spec's wording) so the no-data-loss proof stays reproducible after this session ends.

---

## The Section Map

Derived and verified before this plan was written: all 31 line-197 anchors found, in source order, spans contiguous, summing exactly to each source line's length. **34 sections in total** — 15 wall, 16 room, 1 page-segmentation, 2 append-mode — covering all four source lines, 126,362 chars.

### `docs/wall-network-rules.md` — 15 sections, 54,080 chars


| id | Heading | Source span (line 197) | Chars |
|---|---|---|---|
| W1 | Order and exclusion sets | [0, 5466) | 5,466 |
| W2 | Stroked rectangles as weak faces | [5466, 7590) | 2,124 |
| W3 | Face collection and the length floor | [7590, 9219) | 1,629 |
| W4 | Lattice demotion — striped fields and hatch | [9219, 13431) | 4,212 |
| W5 | Stair demotion | [13431, 19696) | 6,265 |
| W6a | Pairing — plain, thick and through tiers | [19872, 23537) | 3,665 |
| W6b | Pairing — taper, redundancy collapse and the far-side rule | [31568, 35945) | 4,377 |
| W7 | The weak tier and the material gate | [23537, 28026) | 4,489 |
| W8 | Wall pens and the doorway veto | [28026, 31568) | 3,542 |
| W9 | Fill rings and class rating | [35945, 37571) | 1,626 |
| W9b | Fill seams | [37571, 45879) | 8,308 |
| W10a | The collinear-merge anchor | [45879, 47872) | 1,993 |
| W10b | Anchor reach and measurement | [47872, 49470) | 1,598 |
| W10c | Rejected anchor variants and sweep | [49470, 52475) | 3,005 |
| W10d | Known gap: glyph-outline fill rings | [52475, 54256) | 1,781 |

**Every section is a single contiguous span.** The pairing rules are split rather than rejoined: the "Four barrier tiers" enumeration opens them at 19,872 and resumes at 31,568 after the wall-pen digression, so they become W6a and W6b, placed adjacent in the document. Rejoining them into one two-span section was rejected during plan validation — the repair schema addresses a section's leading and trailing edges only, and a rejoined section needs a repair at its internal junction too, which the schema cannot express and the verifier could not check.

Sections therefore appear in the documents in a chosen order that differs from source order (W6a, W6b, W7, W8 read better than W6a, W7, W8, W6b), which is why the verifier reassembles by source offset rather than by document order.

### `docs/room-detection-rules.md` — 15 sections, 45,527 chars

| id | Heading | Source span (line 197) | Chars |
|---|---|---|---|
| R1 | Barriers are allowlisted — the four tiers | [19696, 19872) | 176 |
| R2 | Thin buffers and white rings (tiers 3 and 4) | [54256, 59980) | 5,724 |
| R3 | Jamb rings and door linings | [59980, 64483) | 4,503 |
| R4 | Window seals | [64483, 64975) | 492 |
| R5a | Door plugs — qualification and profile | [64975, 66227) | 1,252 |
| R5b | Vetoed edges — garden pairs and sliders | [66227, 67779) | 1,552 |
| R5c | Plug cross-section fit | [67779, 69080) | 1,301 |
| R5d | Tail trim and clip | [69080, 72103) | 3,023 |
| R5e | The jamb-seeking tail | [72103, 75366) | 3,263 |
| R5f | Plane stamp and the bbox fallback | [75366, 80300) | 4,934 |
| R6 | Free-space components and their filters | [80300, 82002) | 1,702 |
| R7a | The wall-recess drop | [82002, 85398) | 3,396 |
| R7b | The band-pocket drop | [85398, 88977) | 3,579 |
| R7c | Band-pocket end closures | [88977, 94462) | 5,485 |
| R8 | Entrances | [94462, 98697) | 4,235 |
| R9 | Limitations and scope | [98697, 99607) | 910 |

R1 is 176 chars and stays a section of its own: it is the tier enumeration's premise ("Barriers are ALLOWLISTED wall evidence, not all linework"), and the tier entries cross-reference W6–W9 from it.

### Append-mode targets — 2 sections, 22,399 chars

| id | Document | Heading | Source span | Chars |
|---|---|---|---|---|
| F1 | `docs/scale-normalization-findings.md` | **4g.** The detection-scale factor (moved from CLAUDE.md, 2026-09-09) — inserted after §4f, *not* appended | line 199, [0, 3923) | 3,923 |
| H1 | `docs/w-gate-recalibration-handoff.md` | Iteration 1–3 summary, moved from CLAUDE.md (2026-09-09) | line 201, [0, 18476) | 18,476 |

These land in **existing** documents, so the generator upserts one section by heading rather than rewriting the file. F1 carries `insert_after` so it lands as **§4g inside the findings document's §4 sequence**, between §4f and §5 — appending it past §7 would have preserved the content while routing no reader to it, since every pointer and the skill's routing table aim at §4. Verified: it lands between §4f and §5, the insert is idempotent, and all 12 pre-existing sections stay byte-identical. The verifier's heading parser reads them exactly as it reads a generated document, so they get the same CONTENT proof. Neither needs a repair: both open capitalised and end on terminal punctuation.

### `docs/page-segmentation.md` — 1 section, 4,279 chars

| id | Heading | Source span | Chars |
|---|---|---|---|
| S1 | Page segmentation — ink map, frames and gutter tiers | line 245, [68, 4347) | 4,279 |

Line 245's first 68 chars (`   classification crops keep their captions (source: "paths-only"). `) and its last 9 (`Detection`, which runs on into line 246) are **retained** — they are stage-3 sentence fragments, not segmentation rules.

---

## Task 1: Map schema, generator and verifier — proven end-to-end on `page-segmentation.md`

Build all three pieces of machinery and prove them on the smallest span (4,279 chars) before any large document is generated.

**Files:**
- Create: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json`
- Create: `docs/superpowers/specs/2026-09-09-claude-md-split-generate.py`
- Create: `docs/superpowers/specs/2026-09-09-claude-md-split-verify.py`
- Create: `docs/page-segmentation.md` (generated)

**Interfaces:**
- Produces: the map JSON schema every later task appends to; `generate.py` (CLI: no args, reads the map, writes every doc it names); `verify.py` (CLI: no args, exit 0 = proven, exit 1 = failure, prints a report to stdout).

- [ ] **Step 1: Write the section map with only the retained and S1 spans**

Create `docs/superpowers/specs/2026-09-09-claude-md-split-map.json`:

```json
{
  "source_ref": "27b3986",
  "source_file": "CLAUDE.md",
  "docs": {
    "docs/page-segmentation.md": {
      "title": "Page segmentation — ink map, frames and gutter tiers",
      "preamble": "Extracted verbatim from CLAUDE.md's pipeline stage 3. Covers `layout/` — how a sheet is split into its drawings before detection runs. See `CLAUDE.md` §Pipeline architecture for where this sits in the run."
    }
  },
  "sections": [
    {
      "id": "RET-245-head",
      "doc": null,
      "spans": [[245, 0, 68]],
      "repairs": []
    },
    {
      "id": "S1",
      "doc": "docs/page-segmentation.md",
      "heading": "Ink map, nested frames and the four gutter tiers",
      "spans": [[245, 68, 4347]],
      "repairs": []
    },
    {
      "id": "RET-245-tail",
      "doc": null,
      "spans": [[245, 4347, 4356]],
      "repairs": []
    }
  ]
}
```

- [ ] **Step 2: Write the generator**

Create `docs/superpowers/specs/2026-09-09-claude-md-split-generate.py`:

```python
#!/usr/bin/env python3
"""Generate the split documents from the section map.

The prose is SLICED out of CLAUDE.md, never retyped. Re-runnable: it
rewrites each target document from scratch every time.
"""
import json, pathlib, re, subprocess, sys, textwrap

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAP = HERE / "2026-09-09-claude-md-split-map.json"


def load_source(spec):
    """Read CLAUDE.md at the map's PINNED ref, never the working tree.

    LOAD-BEARING: the cut task shortens the source lines. A generator reading the
    working tree would slice pointers or empty offsets on any later re-run,
    so the committed generator would not be reproducible.
    """
    out = subprocess.run(
        ["git", "show", f"{spec['source_ref']}:{spec['source_file']}"],
        cwd=REPO, capture_output=True, text=True, check=True)
    return out.stdout.split("\n")


def upsert(path, heading, body, after=None):
    """Append-mode: replace this heading's section in an existing document,
    insert it after the `after` heading, or append it if neither applies.

    `after` is LOAD-BEARING for discoverability: a section appended past the
    end of a long document is content nothing routes to. F1 belongs inside the
    findings document's §4 sequence, which is where every pointer aims.

    Idempotent -- the generator is re-run by several tasks, and a
    non-idempotent upsert accumulated a trailing newline per run. Verified in
    all three positions: section last, section followed by another heading, and
    inserted mid-document after an anchor.
    """
    f = REPO / path
    text = f.read_text(encoding="utf-8")
    marker = f"\n## {heading}\n"
    block = f"## {heading}\n\n{body.rstrip()}\n"
    if marker in text:                       # already present: replace in place
        i = text.index(marker)
        j = text.find("\n## ", i + len(marker))
        tail = text[j:] if j > 0 else ""
        text = text[:i] + marker + "\n" + body.rstrip() + "\n" + tail
    elif after is not None:                  # insert after the anchor heading
        a = text.index(f"\n## {after}\n")
        j = text.find("\n## ", a + 1)
        text = (text.rstrip() + "\n\n" + block) if j < 0 else \
               (text[:j + 1] + block + "\n" + text[j + 1:])
    else:
        text = text.rstrip() + "\n\n" + block
    f.write_text(text, encoding="utf-8")


def apply_repairs(text, repairs):
    for r in repairs:
        op = r["op"]
        if op == "drop_leading_word":
            w = r["word"]
            assert text.startswith(w + " "), f"{w!r} not leading: {text[:60]!r}"
            text = text[len(w) + 1:]
        elif op == "capitalize_first":
            text = text[0].upper() + text[1:]
        elif op == "append_period":
            text = text.rstrip() + "."
        else:
            raise SystemExit(f"unknown repair op {op!r}")
    return text


def wrap(text):
    """Re-flow one long line into 79-column paragraphs. Whitespace only.

    break_on_hyphens=False is LOAD-BEARING: the default splits
    "already-slanted" across lines, and re-joining inserts a space that was
    never in the source. Caught by the verifier during plan validation.
    break_long_words=False keeps long paths and identifiers intact.
    """
    return "\n".join(textwrap.wrap(" ".join(text.split()), width=79,
                                   break_on_hyphens=False,
                                   break_long_words=False)) + "\n"


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    lines = load_source(spec)

    bydoc = {}
    for sec in spec["sections"]:
        if sec["doc"] is None:
            continue
        parts = [lines[ln - 1][a:b] for ln, a, b in sec["spans"]]
        body = apply_repairs(" ".join(parts).strip(), sec["repairs"])
        bydoc.setdefault(sec["doc"], []).append(
            (sec["heading"], body, sec.get("insert_after")))

    for path, secs in bydoc.items():
        meta = spec["docs"][path]
        if meta.get("mode", "create") == "append":
            for heading, body, after in secs:
                upsert(path, heading, wrap(body).rstrip(), after)
            print(f"upserted {path}: {len(secs)} section(s)")
            continue
        out = [f"# {meta['title']}", "", wrap(meta["preamble"]).rstrip(), ""]
        for heading, body, _ in secs:
            out += [f"## {heading}", "", wrap(body).rstrip(), ""]
        (REPO / path).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        print(f"wrote {path}: {len(secs)} sections")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the verifier**

Create `docs/superpowers/specs/2026-09-09-claude-md-split-verify.py`. It must not import the generator — it re-derives independently from `git show`:

```python
#!/usr/bin/env python3
"""Prove the split lost nothing.

Reads ONLY (a) CLAUDE.md at the map's source_ref, via git, and (b) the
written documents. Never imports the generator.

Two independent proofs:
  COVERAGE  every character of each touched source line belongs to exactly
            one span -- no gap, no overlap, no duplication.
  CONTENT   each written section, with its repairs inverted and whitespace
            normalised, is byte-identical to its source span; and its
            non-whitespace character count matches exactly.
"""
import json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAP = HERE / "2026-09-09-claude-md-split-map.json"

ok = True


def fail(msg):
    global ok
    ok = False
    print("FAIL: " + msg)


def norm(s):
    return " ".join(s.split())


def invert(text, repairs, src):
    for r in reversed(repairs):
        op = r["op"]
        if op == "append_period":
            if not text.endswith("."):
                fail(f"append_period recorded but no trailing '.': {text[-40:]!r}")
                return text
            text = text[:-1]
        elif op == "capitalize_first":
            text = text[0].lower() + text[1:]
        elif op == "drop_leading_word":
            text = r["word"] + " " + text
    return text


def sections_of(path):
    """Split a generated doc into {heading: body} on '## ' headings."""
    text = (REPO / path).read_text(encoding="utf-8")
    out, heading, buf = {}, None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if heading is not None:
                out[heading] = "\n".join(buf).strip()
            heading, buf = line[3:].strip(), []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        out[heading] = "\n".join(buf).strip()
    return out


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    src = subprocess.run(
        ["git", "show", f"{spec['source_ref']}:{spec['source_file']}"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    lines = src.split("\n")

    # ---- COVERAGE ----
    spans = {}
    for sec in spec["sections"]:
        for ln, a, b in sec["spans"]:
            spans.setdefault(ln, []).append((a, b, sec["id"]))
    for ln in sorted(spans):
        got = sorted(spans[ln])
        n = len(lines[ln - 1])
        cursor = 0
        for a, b, sid in got:
            if a != cursor:
                fail(f"line {ln}: {'gap' if a > cursor else 'overlap'} at {cursor}..{a} (before {sid})")
            cursor = b
        if cursor != n:
            fail(f"line {ln}: covered {cursor} of {n} chars")
        else:
            print(f"COVERAGE line {ln}: {n} chars, {len(got)} spans, exact")

    # ---- CONTENT ----
    cache = {}
    for sec in spec["sections"]:
        if sec["doc"] is None:
            continue
        cache.setdefault(sec["doc"], sections_of(sec["doc"]))
        written = cache[sec["doc"]].get(sec["heading"])
        if written is None:
            fail(f"{sec['id']}: heading {sec['heading']!r} not in {sec['doc']}")
            continue
        expect = norm(" ".join(lines[ln - 1][a:b] for ln, a, b in sec["spans"]))
        actual = norm(invert(norm(written), sec["repairs"], expect))
        if actual != expect:
            i = next((k for k in range(min(len(actual), len(expect)))
                      if actual[k] != expect[k]), min(len(actual), len(expect)))
            fail(f"{sec['id']}: diverges at {i}\n"
                 f"    expected: {expect[max(0,i-60):i+60]!r}\n"
                 f"    actual  : {actual[max(0,i-60):i+60]!r}")
            continue
        se = len(re.sub(r"\s", "", expect))
        sa = len(re.sub(r"\s", "", actual))
        if se != sa:
            fail(f"{sec['id']}: non-whitespace count {sa} != {se}")
        else:
            print(f"CONTENT  {sec['id']:<5} {sec['doc']:<34} {se} chars exact")

    # ---- RETAINED ----
    # Characters that stay in CLAUDE.md get COVERAGE but would otherwise get no
    # CONTENT proof: after the cut, deleting them would still report VERIFIED.
    cur = (REPO / spec["source_file"]).read_text(encoding="utf-8")
    for sec in spec["sections"]:
        if sec["doc"] is not None:
            continue
        for ln, a, b in sec["spans"]:
            frag = lines[ln - 1][a:b]
            if not frag.strip():
                continue
            if frag not in cur:
                fail(f"{sec['id']}: retained fragment missing from the working-tree "
                     f"{spec['source_file']}: {frag[:70]!r}")
            else:
                print(f"RETAINED {sec['id']:<14} {len(frag)} chars still in {spec['source_file']}")

    print()
    print("VERIFIED: every character accounted for exactly once." if ok else "VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the verifier before the document exists — it must FAIL**

```bash
cd /Users/danielszweda/Documents/GitHub/UD/agent
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py
```

Expected: exit 1, `FileNotFoundError` or `FAIL: S1: heading … not in docs/page-segmentation.md`. This proves the verifier actually inspects the written file rather than reporting success unconditionally.

- [ ] **Step 5: Generate the document**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
```

Expected: `wrote docs/page-segmentation.md: 1 sections`

- [ ] **Step 6: Run the verifier — it must now PASS**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `COVERAGE line 245: 4356 chars, 3 spans, exact`, `CONTENT S1 … exact`, `VERIFIED: every character accounted for exactly once.`, `exit=0`.

- [ ] **Step 7: Prove the verifier bites — corrupt the document and confirm it fails**

```bash
python3 - <<'EOF'
import pathlib
p = pathlib.Path("docs/page-segmentation.md")
t = p.read_text()
p.write_text(t.replace("16px", "17px", 1))
EOF
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `FAIL: S1: diverges at …`, `exit=1`. Then restore:

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `exit=0`.

- [ ] **Step 8: Commit**

```bash
git add docs/superpowers/specs/2026-09-09-claude-md-split-map.json \
        docs/superpowers/specs/2026-09-09-claude-md-split-generate.py \
        docs/superpowers/specs/2026-09-09-claude-md-split-verify.py \
        docs/page-segmentation.md
git commit -m "docs(split): section-map machinery, proven on page-segmentation.md

The generator SLICES prose out of CLAUDE.md from a committed section map and
never retypes it, so paraphrase is structurally impossible. The verifier reads
only the written documents and git show 27b3986:CLAUDE.md -- it never imports
the generator -- and proves two things independently: COVERAGE, that every
character of each touched source line belongs to exactly one span with no gap
or overlap; and CONTENT, that each written section with its repairs inverted
and whitespace normalised is identical to its source span, non-whitespace
character counts included.

Proven end-to-end on the smallest span first: line 245 offsets [68, 4347),
4,279 chars, zero repairs. Line 245's first 68 chars and its trailing
'Detection' are retained -- they are stage-3 sentence fragments that run into
line 246, not segmentation rules. Bite-proven: the verifier fails before the
document exists, and fails again on a single 16px -> 17px corruption."
```

---

## Task 2: Complete the section map for line 197 — the review gate

Add all 31 line-197 sections. No prose moves in this task; the coverage proof runs against a map whose documents do not yet exist, so a boundary error is caught before it can misfile 100k of prose.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json`

**Interfaces:**
- Consumes: the map schema and `verify.py`'s COVERAGE proof from Task 1.
- Produces: the complete line-197 span assignment that Tasks 3 and 4 generate from.

- [ ] **Step 1: Add the two document entries**

Add to `"docs"` in the map:

```json
"docs/wall-network-rules.md": {
  "title": "Wall-network rules",
  "preamble": "Extracted verbatim from CLAUDE.md. The rules of `detection/walls.py` -- the INTERNAL wall-centerline network, which is never emitted as candidates and exists to feed `detection/rooms.py`. Every rule here is a drawing convention backed by margins measured on named sheets; the numbers are the asset. See `docs/room-detection-rules.md` for what consumes this, and `docs/scale-normalization-findings.md` §4 for which constants scale with drawing scale."
},
"docs/room-detection-rules.md": {
  "title": "Room detection rules",
  "preamble": "Extracted verbatim from CLAUDE.md. The rules of `detection/rooms.py` -- rooms are the connected free-space components left after subtracting barriers. Every rule here is a drawing convention backed by margins measured on named sheets; the numbers are the asset. See `docs/wall-network-rules.md` for the network this consumes, and `docs/scale-normalization-findings.md` §4 for which constants scale with drawing scale."
}
```

- [ ] **Step 2: Add the 14 wall-network sections**

Append to `"sections"`. Every entry has `"repairs": []` for now; Task 3 fills them in.

```json
{"id":"W1","doc":"docs/wall-network-rules.md","heading":"Order and exclusion sets","spans":[[197,0,5466]],"repairs":[]},
{"id":"W2","doc":"docs/wall-network-rules.md","heading":"Stroked rectangles as weak faces","spans":[[197,5466,7590]],"repairs":[]},
{"id":"W3","doc":"docs/wall-network-rules.md","heading":"Face collection and the length floor","spans":[[197,7590,9219]],"repairs":[]},
{"id":"W4","doc":"docs/wall-network-rules.md","heading":"Lattice demotion — striped fields and hatch","spans":[[197,9219,13431]],"repairs":[]},
{"id":"W5","doc":"docs/wall-network-rules.md","heading":"Stair demotion","spans":[[197,13431,19696]],"repairs":[]},
{"id":"W6a","doc":"docs/wall-network-rules.md","heading":"Pairing — plain, thick and through tiers","spans":[[197,19872,23537]],"repairs":[]},
{"id":"W6b","doc":"docs/wall-network-rules.md","heading":"Pairing — taper, redundancy collapse and the far-side rule","spans":[[197,31568,35945]],"repairs":[]},
{"id":"W7","doc":"docs/wall-network-rules.md","heading":"The weak tier and the material gate","spans":[[197,23537,28026]],"repairs":[]},
{"id":"W8","doc":"docs/wall-network-rules.md","heading":"Wall pens and the doorway veto","spans":[[197,28026,31568]],"repairs":[]},
{"id":"W9","doc":"docs/wall-network-rules.md","heading":"Fill rings and class rating","spans":[[197,35945,37571]],"repairs":[]},
{"id":"W9b","doc":"docs/wall-network-rules.md","heading":"Fill seams","spans":[[197,37571,45879]],"repairs":[]},
{"id":"W10a","doc":"docs/wall-network-rules.md","heading":"The collinear-merge anchor","spans":[[197,45879,47872]],"repairs":[]},
{"id":"W10b","doc":"docs/wall-network-rules.md","heading":"Anchor reach and measurement","spans":[[197,47872,49470]],"repairs":[]},
{"id":"W10c","doc":"docs/wall-network-rules.md","heading":"Rejected anchor variants and sweep","spans":[[197,49470,52475]],"repairs":[]},
{"id":"W10d","doc":"docs/wall-network-rules.md","heading":"Known gap: glyph-outline fill rings","spans":[[197,52475,54256]],"repairs":[]},
```

- [ ] **Step 3: Add the 16 room-detection sections**

```json
{"id":"R1","doc":"docs/room-detection-rules.md","heading":"Barriers are allowlisted — the four tiers","spans":[[197,19696,19872]],"repairs":[]},
{"id":"R2","doc":"docs/room-detection-rules.md","heading":"Thin buffers and white rings (tiers 3 and 4)","spans":[[197,54256,59980]],"repairs":[]},
{"id":"R3","doc":"docs/room-detection-rules.md","heading":"Jamb rings and door linings","spans":[[197,59980,64483]],"repairs":[]},
{"id":"R4","doc":"docs/room-detection-rules.md","heading":"Window seals","spans":[[197,64483,64975]],"repairs":[]},
{"id":"R5a","doc":"docs/room-detection-rules.md","heading":"Door plugs — qualification and profile","spans":[[197,64975,66227]],"repairs":[]},
{"id":"R5b","doc":"docs/room-detection-rules.md","heading":"Vetoed edges — garden pairs and sliders","spans":[[197,66227,67779]],"repairs":[]},
{"id":"R5c","doc":"docs/room-detection-rules.md","heading":"Plug cross-section fit","spans":[[197,67779,69080]],"repairs":[]},
{"id":"R5d","doc":"docs/room-detection-rules.md","heading":"Tail trim and clip","spans":[[197,69080,72103]],"repairs":[]},
{"id":"R5e","doc":"docs/room-detection-rules.md","heading":"The jamb-seeking tail","spans":[[197,72103,75366]],"repairs":[]},
{"id":"R5f","doc":"docs/room-detection-rules.md","heading":"Plane stamp and the bbox fallback","spans":[[197,75366,80300]],"repairs":[]},
{"id":"R6","doc":"docs/room-detection-rules.md","heading":"Free-space components and their filters","spans":[[197,80300,82002]],"repairs":[]},
{"id":"R7a","doc":"docs/room-detection-rules.md","heading":"The wall-recess drop","spans":[[197,82002,85398]],"repairs":[]},
{"id":"R7b","doc":"docs/room-detection-rules.md","heading":"The band-pocket drop","spans":[[197,85398,88977]],"repairs":[]},
{"id":"R7c","doc":"docs/room-detection-rules.md","heading":"Band-pocket end closures","spans":[[197,88977,94462]],"repairs":[]},
{"id":"R8","doc":"docs/room-detection-rules.md","heading":"Entrances","spans":[[197,94462,98697]],"repairs":[]},
{"id":"R9","doc":"docs/room-detection-rules.md","heading":"Limitations and scope","spans":[[197,98697,99607]],"repairs":[]}
```

- [ ] **Step 4: Run the COVERAGE proof**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^(COVERAGE|FAIL)"
```

Expected: `COVERAGE line 197: 99607 chars, 31 spans, exact` and `COVERAGE line 245: 4356 chars, 3 spans, exact`, with no `FAIL` on coverage. CONTENT failures for W*/R* are expected here — their documents do not exist yet.

- [ ] **Step 5: Prove the coverage check bites — introduce a one-character gap**

```bash
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path("docs/superpowers/specs/2026-09-09-claude-md-split-map.json")
m = json.loads(p.read_text())
for s in m["sections"]:
    if s["id"] == "W2":
        s["spans"][0][1] = 5467   # leave char 5466 orphaned
p.write_text(json.dumps(m, indent=2, ensure_ascii=False))
EOF
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^FAIL: line"
```

Expected: `FAIL: line 197: gap at 5466..5467 (before W2)`. Restore `5467` to `5466` and re-run step 4 to confirm it is clean again.

- [ ] **Step 6: Print the map for review**

```bash
python3 - <<'EOF'
import json, pathlib
m = json.loads(pathlib.Path("docs/superpowers/specs/2026-09-09-claude-md-split-map.json").read_text())
src = pathlib.Path("CLAUDE.md").read_text(encoding="utf-8").split("\n")
for s in m["sections"]:
    if s["doc"] is None: continue
    n = sum(b - a for _, a, b in s["spans"])
    ln, a, _ = s["spans"][0]
    print(f"{s['id']:<5} {n:>6}  {s['heading']}")
    print(f"        opens: {src[ln-1][a:a+95]!r}")
EOF
```

**This output is the review gate.** Read every `opens:` line and confirm it begins the rule its heading names. A wrong boundary here misfiles a rule; every later task is mechanical.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/specs/2026-09-09-claude-md-split-map.json
git commit -m "docs(split): complete the section map for CLAUDE.md line 197

Thirty sections over line 197's 99,607 chars -- 14 to wall-network-rules.md
(54,080) and 16 to room-detection-rules.md (45,527), summing exactly. Every
boundary anchored on a located substring, all in source order, spans
contiguous with no gap or overlap; COVERAGE proves it and bites on a
one-character gap.

Two structural notes. Every section is a single contiguous span: the pairing
rules are SPLIT into W6a and W6b rather than rejoined, because the 'Four
barrier tiers' enumeration opens them at 19,872 and resumes at 31,568 after
the wall-pen digression, and a rejoined section would need a repair at its
internal junction that the schema cannot express. Sections are placed in the
documents in reading order, not source order, which is why the verifier
reassembles by source offset. R1 stays a 176-char section of its own because it is the tier
enumeration's premise -- 'Barriers are ALLOWLISTED wall evidence, not all
linework' -- that the tier entries cross-reference W6-W9 from.

The 15,325-char door-plug cluster and the 12,460-char recess/pocket cluster
are subdivided (R5a-f, R7a-c) so no section exceeds ~8.3k: an agent
diagnosing a band-pocket phantom should read one section, not one file. No
prose has moved yet -- this commit is the reviewable judgement, and every
later task is mechanical."
```

---

## Task 3: Generate `docs/wall-network-rules.md`

**Files:**
- Create: `docs/wall-network-rules.md` (generated)
- Modify: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json` (repairs only)

**Interfaces:**
- Consumes: the complete map from Task 2; `generate.py` and `verify.py` from Task 1.
- Produces: the finished wall document that Task 5's CLAUDE.md pointer names.

- [ ] **Step 1: Generate**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
```

Expected: `wrote docs/wall-network-rules.md: 15 sections` (plus the other documents).

- [ ] **Step 2: Verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^(CONTENT W|FAIL)"
```

Expected: 15 `CONTENT W… exact` lines, no `FAIL`. The document is byte-faithful before any repair is applied, because every span was cut at a sentence or clause start that already reads as one.

- [ ] **Step 3: Read each section's first and last 200 chars and record needed repairs**

```bash
python3 - <<'EOF'
import re, pathlib
t = pathlib.Path("docs/wall-network-rules.md").read_text(encoding="utf-8")
for m in re.finditer(r"^## (.+)$", t, re.M):
    end = t.find("\n## ", m.end())
    body = " ".join(t[m.end():end if end > 0 else len(t)].split())
    print(f"--- {m.group(1)}")
    print(f"    OPENS: {body[:160]}")
    print(f"    ENDS : {body[-160:]}")
EOF
```

A repair is needed only when a section **opens** with an orphaned lowercase connective (`and `, `while `, `but `, `so `) or a lowercase word, or **ends** without terminal punctuation.

**Measured during plan validation — exactly 7 of the 15 wall sections need one, and these are they.** Confirm the printed openings match before applying; if any differs, the map's boundaries moved and Task 2 needs revisiting.

| id | Opens | Repairs, in order |
|---|---|---|
| W6a | `Four barrier tiers: (1) wall solids — paired cen…` | `append_period` |
| W7 | `hairline faces (below \`WALL_MIN_STROKE_WIDTH_PX\`…` | `capitalize_first`, `append_period` |
| W8 | `and since W-gate iteration 3 step 11 (2026-09-05…` | `drop_leading_word` (`and`), `capitalize_first`, `append_period` |
| W6b | `pairing itself demands ONE THICKNESS ALONG THE O…` | `capitalize_first`, `append_period` |
| W9 | `(2) wall-fill polygons — closed rings reconstruc…` | `append_period` |
| W9b | `and fill SEAMS never become faces (\`_fill_seam_i…` | `drop_leading_word` (`and`), `capitalize_first` |
| W10d | `Known gap, a separate iteration: (b) glyph-outli…` | `append_period` |

`(2) wall-fill polygons` and `(3) thin buffers` need no `capitalize_first` — a parenthesised enumerator is a legitimate opening. The other 8 wall sections need nothing.

- [ ] **Step 4: Record the repairs in the map**

For each repair identified, add to that section's `repairs` array, in application order. Example for W9b:

```json
{"id":"W9b","doc":"docs/wall-network-rules.md","heading":"Fill seams",
 "spans":[[197,37571,45879]],
 "repairs":[{"op":"drop_leading_word","word":"and"},{"op":"capitalize_first"}]}
```

- [ ] **Step 5: Regenerate and re-verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `exit=0`. The verifier inverts each repair before comparing, so a repair that was recorded but not actually applied — or applied but not recorded — fails here.

- [ ] **Step 6: Confirm the character budget**

```bash
python3 -c "
import pathlib,re
t=pathlib.Path('docs/wall-network-rules.md').read_text(encoding='utf-8')
body=re.sub(r'^#.*$','',t,flags=re.M)
print('non-whitespace chars in bodies:', len(re.sub(r'\s','',body)))
print('sections:', t.count(chr(10)+'## ')+t.startswith('## '))
"
```

Expected: 15 sections. The non-whitespace count is recorded for the Task 9 report.

- [ ] **Step 7: Commit**

```bash
git add docs/wall-network-rules.md docs/superpowers/specs/2026-09-09-claude-md-split-map.json
git commit -m "docs(split): generate docs/wall-network-rules.md from the section map

Fourteen sections, 54,080 source chars of detection/walls.py rules, sliced
from CLAUDE.md line 197 by the generator -- the prose was never retyped, so
paraphrase is structurally impossible. Repairs recorded in the map and
inverted by the verifier before comparison, so a repair applied but not
recorded, or recorded but not applied, fails the CONTENT proof.

Verifier green: every section byte-identical to its source span with
non-whitespace character counts matching exactly."
```

---

## Task 4: Generate `docs/room-detection-rules.md`

Identical mechanics to Task 3, on the 16 room sections.

**Files:**
- Create: `docs/room-detection-rules.md` (generated)
- Modify: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json` (repairs only)

**Interfaces:**
- Consumes: the complete map from Task 2; the machinery from Task 1.
- Produces: the finished room document that Task 5's CLAUDE.md pointer and Task 8's routing table name.

- [ ] **Step 1: Generate**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
```

Expected: `wrote docs/room-detection-rules.md: 16 sections`.

- [ ] **Step 2: Verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^(CONTENT R|FAIL)"
```

Expected: 16 `CONTENT R… exact` lines, no `FAIL`. With no repairs needed, this should pass on the first generation.

- [ ] **Step 3: Read each section's first and last 200 chars and record needed repairs**

```bash
python3 - <<'EOF'
import re, pathlib
t = pathlib.Path("docs/room-detection-rules.md").read_text(encoding="utf-8")
for m in re.finditer(r"^## (.+)$", t, re.M):
    end = t.find("\n## ", m.end())
    body = " ".join(t[m.end():end if end > 0 else len(t)].split())
    print(f"--- {m.group(1)}")
    print(f"    OPENS: {body[:160]}")
    print(f"    ENDS : {body[-160:]}")
EOF
```

**Measured during plan validation: none of the 16 room sections needs any repair.** Every one already opens capitalised or on a parenthesised enumerator and ends on terminal punctuation — R2 opens `(3) thin buffers of QUALIFYING faces only…`, R7b `And a component lying INSIDE a band's thickness…`, R5e `And since W-gate iteration 3 step 10…`, R7c `Since W-gate iteration 3 step 16…`, R8 `Both drops and the recess rule count ENTRANCES…`.

So this step is a confirmation, not a change: run the command, confirm every section opens and closes cleanly, and leave every `repairs` array empty. If any section does need one, the map's boundaries moved and Task 2 needs revisiting.

- [ ] **Step 4: Record the repairs in the map**

Same JSON shape as Task 3 step 4.

- [ ] **Step 5: Regenerate and re-verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `exit=0`, with all 32 sections reporting `exact` (F1 and H1 arrive in Tasks 5 and 6).

- [ ] **Step 6: Confirm the cross-references resolve**

R1 names the four tiers and cross-references the wall document. Confirm both documents exist and every `docs/…-rules.md` mention in either resolves:

```bash
grep -oh "docs/[a-z-]*\.md" docs/wall-network-rules.md docs/room-detection-rules.md | sort -u | while read f; do
  [ -f "$f" ] && echo "  OK   $f" || echo "  MISS $f"
done
```

Expected: every line `OK`.

- [ ] **Step 7: Commit**

```bash
git add docs/room-detection-rules.md docs/superpowers/specs/2026-09-09-claude-md-split-map.json
git commit -m "docs(split): generate docs/room-detection-rules.md from the section map

Sixteen sections, 45,527 source chars of detection/rooms.py rules, sliced from
CLAUDE.md line 197. With Task 3's 54,080 this accounts for all 99,607 chars of
the line exactly.

The 15,325-char door-plug cluster is subdivided R5a-f (qualification, vetoed
edges, cross-section fit, tail trim and clip, the jamb-seeking tail, plane
stamp and bbox fallback) and the 12,460-char drop cluster R7a-c (wall recess,
band pocket, end closures), so the largest section an agent must read to
diagnose one phantom is ~5.5k rather than 100k.

Verifier green on all 34 sections; every docs/*.md cross-reference resolves."
```

---

## Task 5: Move line 199 into `docs/scale-normalization-findings.md` under the span map

Lines 199 and 201 are **span-assigned exactly like 197 and 245** — not probed by a heuristic. The eight-word-window dedup this task originally used was measured and rejected: see "Plan validation" above.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json`
- Modify: `docs/scale-normalization-findings.md`

**Interfaces:**
- Consumes: the map schema, generator and verifier from Task 1.
- Produces: COVERAGE over line 199, closing the verifier's gap.

- [ ] **Step 1: Add the append-mode document and the F1 section to the map**

Add to `"docs"`:

```json
"docs/scale-normalization-findings.md": {
  "mode": "append",
  "title": "(existing document — append mode, title unused)",
  "preamble": ""
}
```

Add to `"sections"`:

```json
{"id":"F1","doc":"docs/scale-normalization-findings.md",
 "heading":"4g. The detection-scale factor (moved from CLAUDE.md, 2026-09-09)",
 "insert_after":"4f. Measured scales do not drive the gates (2026-08-19)",
 "spans":[[199,0,3923]],"repairs":[]}
```

The whole of line 199 moves. CLAUDE.md's replacement is **newly written pointer prose**, not a retained span — the map accounts for where the original characters went, and new summary prose in CLAUDE.md is not claimed as preserved content.

- [ ] **Step 2: Generate and verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^(COVERAGE line 199|CONTENT F1|FAIL)"
```

Expected: `COVERAGE line 199: 3923 chars, 1 spans, exact` and `CONTENT F1 … exact`, no `FAIL`.

- [ ] **Step 3: Measure and report the actual overlap with §4 — as a number, not a gate**

The target document must be read at `27b3986` — **before** F1 was inserted into it. Reading the working tree after step 2 searches a document that now contains the whole source line and necessarily reports every claim present:

```bash
python3 - <<'EOF'
import subprocess, re
def show(ref_path):
    return subprocess.run(["git","show",ref_path],capture_output=True,text=True,check=True).stdout
line = show("27b3986:CLAUDE.md").split("\n")[198]
tgt  = " ".join(show("27b3986:docs/scale-normalization-findings.md").split())
claims = re.split(r'(?<=[.;]) (?=[A-Z(`])', line)
full = sum(1 for c in claims if " ".join(c.split()) in tgt)
print(f"line 199: {len(claims)} claims, {full} present in the PRE-MOVE findings doc as COMPLETE claims")
EOF
```

Expected: `7 claims, 0 present`. Measured while planning, both ways: 0 of 7 against the pre-move document, 7 of 7 against the post-move one — which is why the ref is pinned rather than reading the working tree. Record the pre-move number in the Task 9 report as the evidence that this content was never a duplicate. **Nothing is deleted on the strength of it** — it is reported, not acted on.

- [ ] **Step 4: Commit**

```bash
git add docs/scale-normalization-findings.md docs/superpowers/specs/2026-09-09-claude-md-split-map.json
git commit -m "docs(split): move CLAUDE.md's gates paragraph into findings under the span map

Line 199 moves whole, span-assigned exactly like 197 and 245, so COVERAGE and
CONTENT now prove it -- 3,923 chars that the original plan would have deleted
under a probe instead.

The eight-word-window dedup is gone. Measured against the real repository it
marked 3 of line 199's 7 claims PRESENT while ZERO complete claims occur in
the findings document -- a 223-word claim accepted because one eight-word
fragment matched -- and those claims would then have been dropped after the
source line had already been replaced. Exact whole-claim matching finds 0
droppable claims, so the dedup premise was wrong: the overlap is at phrase
level (shared constant names), not claim level. The number is now reported in
the verification report, never acted on."
```

---

## Task 6: Move line 201 into `docs/w-gate-recalibration-handoff.md` under the span map

Same correction as Task 5, on the larger block. Design-time spot-checking already found phrases in line 201 present nowhere else in the repo; exact whole-claim matching now confirms the stronger result.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-claude-md-split-map.json`
- Modify: `docs/w-gate-recalibration-handoff.md`

**Interfaces:**
- Consumes: the map schema, generator and verifier from Task 1.
- Produces: COVERAGE over line 201, completing exact accounting for all four source lines.

- [ ] **Step 1: Add the append-mode document and the H1 section to the map**

Add to `"docs"`:

```json
"docs/w-gate-recalibration-handoff.md": {
  "mode": "append",
  "title": "(existing document — append mode, title unused)",
  "preamble": ""
}
```

Add to `"sections"`:

```json
{"id":"H1","doc":"docs/w-gate-recalibration-handoff.md",
 "heading":"Iteration 1–3 summary, moved from CLAUDE.md (2026-09-09)",
 "spans":[[201,0,18476]],"repairs":[]}
```

- [ ] **Step 2: Generate and verify**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-generate.py
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `exit=0`, **4 COVERAGE lines (197, 199, 201, 245)** and 34 CONTENT lines. This is the first point at which the spec's "exact accounting for lines 197, 199, 201 and 245" is actually true.

- [ ] **Step 3: Measure and report the actual overlap — as a number, not a gate**

Every file is read at `27b3986`, for the same reason as Task 5 — including the handoff, which now contains the moved section:

```bash
python3 - <<'EOF'
import subprocess, re
def show(p):
    return subprocess.run(["git","show",f"27b3986:{p}"],capture_output=True,text=True,check=True).stdout
files = subprocess.run(["git","ls-tree","-r","--name-only","27b3986","docs/"],
                       capture_output=True,text=True,check=True).stdout.split()
files = [f for f in files if "w-gate" in f and f.endswith(".md")]
corpus = " ".join(" ".join(show(f).split()) for f in files)
line = show("CLAUDE.md").split("\n")[200]
claims = re.split(r'(?<=[.;]) (?=[A-Z(`])', line)
full = sum(1 for c in claims if " ".join(c.split()) in corpus)
print(f"line 201: {len(claims)} claims, {full} present in the PRE-MOVE W-gate docs as COMPLETE claims")
print(f"  corpus: {len(files)} files")
EOF
```

Expected: `33 claims, 0 present`. Record in the Task 9 report.

- [ ] **Step 4: Repath the live step-18 prompt only**

```bash
grep -n "CLAUDE.md" docs/w-gate-recalibration-handoff.md | tail -5
```

Identify the step-18 prompt (the last one, the live next-step brief). Change its "the CLAUDE.md paragraphs 'Room detection'…" reference to name `docs/wall-network-rules.md` and `docs/room-detection-rules.md`. **Leave every earlier step prompt untouched** — they are records of what past agents were told and stay frozen.

- [ ] **Step 5: Confirm exactly one prompt changed, and that the moved section is intact**

```bash
git diff docs/w-gate-recalibration-handoff.md | grep -c "^-.*CLAUDE.md"
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py 2>&1 | grep -E "^(CONTENT H1|FAIL)"
```

Expected: exactly `1` removed line mentioning CLAUDE.md, and `CONTENT H1 … exact` — the repath must not have disturbed the moved section.

- [ ] **Step 6: Commit**

```bash
git add docs/w-gate-recalibration-handoff.md docs/superpowers/specs/2026-09-09-claude-md-split-map.json
git commit -m "docs(split): move CLAUDE.md's W-gate log into the handoff under the span map; repath step 18

Line 201 moves whole, span-assigned like the rest, so all four source lines
are now covered: 18,476 chars that the original plan would have deleted on a
probe's say-so. With this the spec's 'exact accounting for lines 197, 199, 201
and 245' is true for the first time -- the previous plan covered only 197 and
245 and left 22,399 chars to a heuristic.

That heuristic marked 17 of line 201's 33 claims PRESENT while ZERO complete
claims occur in the census or the checkpoint reports; one accepted claim ran
269 words. Exact whole-claim matching finds 0 droppable, confirming the
design-time spot check that found 'Group 1 (2026-09-04)',
'verdict-identical to main on all 20 sheets' and 'recalibrated tree is
verdict-identical' nowhere else in the repo.

Only the live step-18 prompt is repathed; the ~40 earlier step prompts stay
frozen as records of what past agents were told."
```

---


## Task 7: Cut `CLAUDE.md` to its pointers

The only task that deletes anything from `CLAUDE.md`, and it runs **last** of the content tasks: every pointer it writes names a document section that Tasks 1–6 have already created and proven, so the content is never absent from the working tree even for one commit. The verifier reads `27b3986`, so it keeps proving the documents against the pre-split original after the cut.

**Files:**
- Modify: `CLAUDE.md` lines 197, 199, 201, 245

**Interfaces:**
- Consumes: the three generated documents.
- Produces: the `CLAUDE.md` every later task and every future session reads.

- [ ] **Step 1: Replace line 197 with its pointer**

Replace the whole of line 197 with:

```markdown
Room detection: order matters — doors/windows detect first, then `detect_wall_network(paths, text_spans, exclude_path_indices)` builds the internal wall-centerline network (walls are never emitted as candidates), and `detect_rooms` extracts rooms as the connected free-space components of the page after subtracting barriers. Barriers are ALLOWLISTED wall evidence, not all linework — room-interior ink (floor-tile grids, furniture outlines, sanitary symbols, text masks) must not chop the free space — in four tiers: wall solids (paired centerline segments dilated to their measured thickness), wall-fill polygons, thin buffers of qualifying faces, and white (background-fill) rings, completed by opening seals at the surviving doors and windows. Rooms are heuristic-only: never sent to Gemini, they bypass the `OFFLINE_MIN_CONFIDENCE` floors and NMS, and carry the closed polygon in `Candidate.evidence["polygon"]` / `Entity.attributes["polygon"]`.

**Before changing wall or room detection, read `docs/wall-network-rules.md` and `docs/room-detection-rules.md`.** They carry every rule, its drawing-convention rationale, its measured margins and the sheets those were measured on — most fixture classes (paving, hatch, tile grids, stairs, counters, wardrobes, radiators, leader arrows) already have a rule, so the correct fix is usually a gap in an existing rule rather than a new one. `docs/wall-network-rules.md` covers the exclusion sets, face collection, lattice and stair demotion, the pairing tiers, the weak tier's material gate, pen gating and the doorway veto, fill rings and seams, and the collinear-merge anchor. `docs/room-detection-rules.md` covers the four barrier tiers, jamb rings and door linings, window seals, door plugs, the free-space filters, the wall-recess / band-pocket / blind-window drops, and the entrance rule.
```

- [ ] **Step 2: Replace line 199 with its pointer**

```markdown
Wall/room world-space gates (the `W`-classed constants in `docs/scale-normalization-findings.md` §4) scale via a per-page factor threaded from `scale.factor.detection_scale(page_scales, regions, page_number)` into `detect_wall_network` / `detect_rooms` as `scale_factor`: `f = 50 / nominal_denominator`, so f=1.0 (identity, unchanged behavior) at 1:50 and on unresolved-scale pages, f=0.5 at 1:100. Paper-space (`P`) and dimensionless (`D`) constants are left unscaled. **Before touching any gate constant, read `docs/scale-normalization-findings.md` §4** — its table says whether that gate scales with drawing scale, **§4g** carries the full rules for how the factor is resolved and threaded (dimension-string verification, mixed-scale sheets, the warning codes), and §4f records why feeding a measured scale straight to the gates regressed s01.
```

- [ ] **Step 3: Replace line 201 with its pointer**

```markdown
The W references were re-derived at the sheets' TRUE scales over iterations 1–3. **The census, the per-constant outcomes and the step-by-step log live in `docs/w-gate-census-2026-09-04.md`, `docs/w-gate-recalibration-handoff.md` (start at "Iteration 1–3 summary, moved from CLAUDE.md") and `docs/w-gate-iter3-checkpoints/`.** Read the handoff's outcome sections before moving any W-classed constant: every census row flagged ⚠ ("discriminator, not number") broke the moment its number moved, always by admitting a drawn fixture another gate had been holding out.
```

- [ ] **Step 4: Replace line 245's movable span with its pointer**

Keep the first 68 chars and the trailing `Detection`; replace the middle:

```markdown
   classification crops keep their captions (source: "paths-only"). **The ink map's construction, the nested sheet-furniture skip and the four gutter tiers are in `docs/page-segmentation.md`.** Detection
```

- [ ] **Step 5: Confirm the size and that nothing else changed**

```bash
python3 -c "
t=open('CLAUDE.md',encoding='utf-8').read()
print('chars:', len(t), '(target <= 32000)')
print('lines:', len(t.split(chr(10))))
"
git diff --stat main -- CLAUDE.md
```

Expected: ~30,200 chars, and the diff touches only lines 197/199/201/245.

- [ ] **Step 6: Re-run the verifier — it must still pass**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py; echo "exit=$?"
```

Expected: `exit=0`. The verifier reads `git show 27b3986:CLAUDE.md`, so cutting the working copy cannot make it pass vacuously — this is the proof that the documents still match the pre-split original.

- [ ] **Step 7: Confirm every pointer target exists**

```bash
grep -oh "docs/[a-z0-9./-]*\(\.md\|/\)" CLAUDE.md | sort -u | while read f; do
  [ -e "${f%/}" ] && echo "  OK   $f" || echo "  MISS $f"
done
```

Expected: every line `OK`.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(split): cut CLAUDE.md to its pointers — 154,912 -> ~30,200 chars

Lines 197, 199 and 201 and line 245's movable span are replaced by pointers
written as hard instructions, in the style of the line 11 door-guide pointer
that already works. Each pointer keeps enough prose that CLAUDE.md stays
self-sufficient for orientation -- the detection order, the allowlisted-barrier
premise, the four tier names, rooms being heuristic-only, and the scale
factor's definition -- and names the document carrying the rules.

The verifier reads git show 27b3986:CLAUDE.md, not the working copy, so
cutting the file cannot make it pass vacuously: it still proves all 34
sections against the pre-split original, which is the point of running it
here. The RETAINED check is the other half -- it asserts line 245's 77
retained characters are still present in the working-tree file, which COVERAGE
alone would not catch."
```

---

## Task 8: Update the `fix-detection` skill, file map, evals and README

**Files:**
- Modify: `.claude/skills/fix-detection/SKILL.md`
- Modify: `.claude/skills/fix-detection/references/file-map.md`
- Modify: `.claude/skills/fix-detection/evals/evals.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished documents and their section headings from Tasks 3 and 4.
- Produces: the skill a future detection session actually runs.

- [ ] **Step 1: Repath SKILL.md's three CLAUDE.md references**

Line ~37 — change:
> Read the CLAUDE.md "Room detection" paragraph and the relevant tuning guide before diagnosing

to:
> Read `docs/wall-network-rules.md` / `docs/room-detection-rules.md` (the section your symptom routes to, below) and the relevant tuning guide before diagnosing

Line ~78 — in phase 2's numbered list, change `the CLAUDE.md "Room detection" paragraph + detection/walls.py / detection/rooms.py module docstrings` to `docs/wall-network-rules.md and docs/room-detection-rules.md — the section the routing table below names — plus the module docstrings of detection/walls.py / detection/rooms.py`.

Line ~145 — in phase 5 step 5, change `the tuning guide section (or the CLAUDE.md room paragraph for walls/rooms)` to `the tuning guide section (or docs/wall-network-rules.md / docs/room-detection-rules.md for walls/rooms)`.

- [ ] **Step 2: Add the routing table to SKILL.md phase 2**

Insert after phase 2's numbered list:

```markdown
Route by symptom — read the section, not the whole document:

| Symptom | Read |
|---|---|
| A fixture outline fenced a phantom room (counter, wardrobe, bed, sofa, unit) | wall-network §The weak tier and the material gate, §Wall pens and the doorway veto |
| Paving, tile grid, roof tiles, floorboards or treads fencing | wall-network §Lattice demotion |
| A stair flight came out as a room, or stair ink fenced | wall-network §Stair demotion |
| A room edge is notched, slanted, or a few px off its wall | wall-network §The collinear-merge anchor; room-detection §Thin buffers and white rings |
| A hatch or brick-cell diagonal produced a slanted band | wall-network §Pairing (the taper rule), §Fill seams |
| A wall band contributed no faces at all | wall-network §Stroked rectangles as weak faces, §Face collection and the length floor |
| Rooms merged through a doorway, or a swing square left its room | room-detection §Door plugs (R5a–f) |
| A narrow strip, reveal or cavity was emitted as a room | room-detection §The band-pocket drop, §Band-pocket end closures |
| A real room was dropped | room-detection §Free-space components and their filters, §Entrances |
| A window seal is wrong, or a bay window | room-detection §Window seals |
| The constant may need to scale with drawing scale | `docs/scale-normalization-findings.md` §4 (the W/P/D table) and §4g (how the factor is resolved and threaded) |
```

- [ ] **Step 3: Add the phase-5 heading rule to SKILL.md**

In phase 5 step 5, after the repathed sentence, add:

> A **new** rule gets its **own** `##` heading in the document for its stage; an extension to an existing rule goes under that rule's heading. These documents exist because a single 100k paragraph could not be anchored, edited or reviewed — do not rebuild one.

- [ ] **Step 4: Repath file-map.md**

In the Walls row, change the "Read first" cell from `CLAUDE.md "Room detection" paragraph (the rules + every measured number); module docstring of walls.py` to `docs/wall-network-rules.md (the rules + every measured number); module docstring of walls.py`.

In the Rooms row, change `same as walls` to `docs/room-detection-rules.md; docs/wall-network-rules.md for the network it consumes`.

In the "Sheet notes" paragraph, change `every rule in CLAUDE.md was measured on them` to `every rule in docs/wall-network-rules.md and docs/room-detection-rules.md was measured on them`.

- [ ] **Step 5: Repath the two evals.json grading criteria**

Both read:

```
"fix.diff updates the prose rule reference (CLAUDE.md room paragraph or a docs/*tuning-guide*.md) with the measured rationale"
```

Change both to:

```
"fix.diff updates the prose rule reference (docs/wall-network-rules.md, docs/room-detection-rules.md, or a docs/*tuning-guide*.md) with the measured rationale"
```

- [ ] **Step 6: Validate the JSON still parses**

```bash
python3 -c "import json; d=json.load(open('.claude/skills/fix-detection/evals/evals.json')); print('evals OK:', len(d) if isinstance(d,list) else list(d))"
```

Expected: parses without error.

- [ ] **Step 7: Update README.md**

Change:
> See `CLAUDE.md` for architecture details and `project.md` for the original spec.

to:
> See `CLAUDE.md` for architecture details — with the detection rules in `docs/wall-network-rules.md` and `docs/room-detection-rules.md` — and `project.md` for the original spec.

- [ ] **Step 8: Confirm no stale reference survives outside the frozen history**

```bash
grep -rn 'CLAUDE.md "Room detection"\|CLAUDE.md room paragraph\|CLAUDE.md .Room detection. paragraph' \
  --include="*.md" --include="*.json" . 2>/dev/null \
  | grep -v graphify-out | grep -v w-gate-recalibration-handoff
```

Expected: no output. Hits inside `w-gate-recalibration-handoff.md` are the frozen historical step prompts and are excluded deliberately.

- [ ] **Step 9: Confirm every path the skill names exists**

```bash
grep -oh "docs/[a-z0-9./-]*\(\.md\|/\)" \
  .claude/skills/fix-detection/SKILL.md \
  .claude/skills/fix-detection/references/file-map.md \
  .claude/skills/fix-detection/evals/evals.json \
  | tr -d '`,)' | sort -u | while read f; do
  case "$f" in *'*'*) continue;; esac
  [ -e "${f%/}" ] && echo "  OK   $f" || echo "  MISS $f"
done
```

Expected: every line `OK`.

- [ ] **Step 10: Commit**

```bash
git add .claude/skills/fix-detection/SKILL.md \
        .claude/skills/fix-detection/references/file-map.md \
        .claude/skills/fix-detection/evals/evals.json \
        README.md
git commit -m "docs(split): repoint fix-detection at the split rule documents

Three SKILL.md references, two file-map.md rows and the s01/s02 sheet note,
and one README line. Plus two things the split needs to pay off and to last:

A symptom-to-section routing table in phase 2, so a band-pocket phantom sends
the agent to one ~5.5k section rather than a 45k file -- retrieval by rule was
the point of splitting by rule.

A phase-5 rule that a NEW rule gets its OWN heading and an extension goes
under its rule's heading. Without it these documents re-blob within a dozen
iterations, which is exactly how CLAUDE.md reached 154,912 chars.

The two evals.json grading criteria accepted only 'CLAUDE.md room paragraph'
or 'docs/*tuning-guide*.md'; neither new document matches either glob, so
after the split the suite would have graded a correct fix as a failure. Both
now name the new documents."
```

---

## Task 9: Final verification, graph refresh and the report

**Files:**
- Create: `docs/superpowers/specs/2026-09-09-claude-md-split-verification.md`
- Modify: `graphify-out/` (regenerated)

**Interfaces:**
- Consumes: everything.
- Produces: the committed no-data-loss proof.

- [ ] **Step 1: Run the full verifier and capture its output**

```bash
python3 docs/superpowers/specs/2026-09-09-claude-md-split-verify.py \
  > /tmp/split-verify.txt 2>&1; echo "exit=$?"
cat /tmp/split-verify.txt
```

Expected: `exit=0`, 4 COVERAGE lines (197, 199, 201 and 245), 34 CONTENT lines, `VERIFIED`.

- [ ] **Step 2: Independently confirm the arithmetic**

```bash
python3 - <<'EOF'
import json, subprocess, pathlib
m = json.loads(pathlib.Path("docs/superpowers/specs/2026-09-09-claude-md-split-map.json").read_text())
src = subprocess.run(["git","show","27b3986:CLAUDE.md"],capture_output=True,text=True,check=True).stdout
L = src.split("\n")
tot = {}
for s in m["sections"]:
    key = s["doc"] or "(retained in CLAUDE.md)"
    tot[key] = tot.get(key, 0) + sum(b-a for _,a,b in s["spans"])
for k, v in sorted(tot.items()):
    print(f"  {v:>7} chars  {k}")
print(f"  {sum(tot.values()):>7} chars  TOTAL")
print(f"  {sum(len(L[n-1]) for n in (197,199,201,245)):>7} chars  source lines 197+199+201+245")
now = len(pathlib.Path('CLAUDE.md').read_text(encoding='utf-8'))
print(f"\nCLAUDE.md: {len(src)} -> {now} chars ({100*(1-now/len(src)):.1f}% smaller)")
EOF
```

Expected: the per-document totals sum exactly to the source lines' total, and `CLAUDE.md` is ~30,200 chars.

All four source lines are span-assigned, so this total must match exactly. If it does not, a span is missing or double-counted and the split is not proven — do not proceed to the report.

- [ ] **Step 3: Run the fast test tier to confirm no code was touched**

```bash
source .venv/bin/activate && python -m unittest discover tests 2>&1 | tail -5
```

Expected: the usual pass count, green (a known room-label cache flake is acceptable and should be named if it appears). No test should change — this task modified no code.

- [ ] **Step 4: Confirm no project code was modified**

```bash
git diff --stat main --name-only | grep -E "^(detection|tests|tools|scale|takeoff|layout|gemini|extraction)/" || echo "  none — correct"
```

Expected: `none — correct`.

- [ ] **Step 5: Write the verification report**

Create `docs/superpowers/specs/2026-09-09-claude-md-split-verification.md` containing: the captured verifier output from step 1, the arithmetic from step 2, the probe results from Tasks 6 and 7, the complete repair log rendered from the map, and the final size. Render the repair log with:

```bash
python3 - <<'EOF'
import json, pathlib
m = json.loads(pathlib.Path("docs/superpowers/specs/2026-09-09-claude-md-split-map.json").read_text())
n = 0
for s in m["sections"]:
    if not s["repairs"]: continue
    n += 1
    print(f"{s['doc']} §{s['heading']}  [{s['id']}]")
    for r in s["repairs"]:
        print(f"    {r['op']}" + (f" ({r['word']!r})" if 'word' in r else ""))
print(f"\n{n} sections carry repairs; all inverted by the verifier before comparison.")
EOF
```

- [ ] **Step 6: Refresh the knowledge graph**

```bash
~/.local/bin/graphify update .
```

(`graphify` is not on the default shell PATH — use the full path.)

- [ ] **Step 7: Confirm the split improved retrieval**

```bash
~/.local/bin/graphify query "why is a band pocket not a room" 2>&1 | head -20
```

Expected: the result surfaces `docs/room-detection-rules.md`'s band-pocket sections rather than the whole of CLAUDE.md. Record the outcome in the report; a 100k single line was a poor retrieval unit and this is the side benefit worth confirming.

- [ ] **Step 8: Commit**

```bash
git add docs/superpowers/specs/2026-09-09-claude-md-split-verification.md graphify-out
git commit -m "docs(split): verification report and graph refresh

CLAUDE.md 154,912 -> ~30,200 chars, 80% smaller, still self-sufficient for
orientation. The proof, reproducible from the committed map, generator and
verifier: COVERAGE shows every character of ALL FOUR source lines -- 197, 199,
201 and 245, 126,362 chars -- belongs to exactly one span with no gap or
overlap; CONTENT shows all 34 written sections identical to their source spans
with repairs inverted and non-whitespace counts matching.

Exact whole-claim matching found 0 droppable claims in lines 199 and 201, so
nothing was deduplicated away; the numbers are reported here as evidence that
the content was never a duplicate, and were never used as a deletion gate.

Full repair log included. No file under detection/, tests/, tools/, scale/,
takeoff/, layout/, gemini/ or extraction/ was modified; the fast tier is
unchanged and green."
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: target state → Tasks 1/3/4/5; split protocol and its three permitted repairs → the map's `repairs` schema (Task 1) applied in Tasks 3/4; the section map as reviewable artefact → Task 2 step 6, the explicit review gate; verification gate → Tasks 1/3/4/5/9; sequencing → nine tasks; fix-detection changes including the routing table and heading rule → Task 8; risk 3 (line 201 is not a duplicate) → Task 7's probe; risk 4 (evals rot) → Task 8 steps 5–6; risk 5 (the read gate) → Task 5's hard-instruction pointers plus Task 8's routing table; branch strategy → resolved before planning, `main` at `27b3986`.

**Two deliberate deviations, both flagged inline:** the spec's "~26k / ≤30k" is corrected to ≤32,000 chars on measurement, and the generator/verifier are committed beside the spec rather than left in the scratchpad, so the no-data-loss proof stays reproducible.

**Placeholder scan.** No TBD, no "handle edge cases", no "similar to Task N". Every code step carries runnable code; every boundary carries a measured offset; the only content produced at execution time is the repair list, which Tasks 3/4 step 3 derives mechanically from printed section openings and step 5 proves.

**Type consistency.** `apply_repairs` (generator) and `invert` (verifier) implement inverse operations over the same three op names — `drop_leading_word` (with `word`), `capitalize_first`, `append_period` — applied in order and inverted in reverse. The map schema (`source_ref`, `source_file`, `docs{title,preamble}`, `sections[{id,doc,heading,spans,repairs}]`) is written in Task 1 and only appended to thereafter. `spans` are `[line, start, end)` triples, 1-based line, 0-based half-open offsets, throughout.
