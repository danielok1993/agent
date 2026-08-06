# Regression Testing — Working Guide

Reference for anyone (human or agent) changing detection behaviour. `CLAUDE.md`'s
"Regression testing" section is the summary; this is the detail.

Built 2026-08-06. Design: `docs/superpowers/specs/2026-08-06-regression-corpus-design.md`.

## 1. Why this exists

Before this, "no regressions" meant re-running extraction and eyeballing the
overlay, and a session's judgement about whether a new detection was real died
with the session. The next session re-derived it, or silently accepted a false
positive an earlier session had rejected.

Ground truth is that judgement, written down. The corpus is 20 real sheets; the
verdicts are committed; the sweep re-checks every one of them on demand.

## 2. Two tiers — know which one you are in

| Tier | Command | Runtime | What it covers |
|---|---|---|---|
| Unit | `python -m unittest discover tests` | ~8s | Synthetic geometry, 525 tests. Run constantly. |
| Sweep | `python tools/regress.py` | ~2:15 | 20 real sheets vs. committed verdicts. |

The sweep is deliberately NOT in `unittest discover` — a 2-minute suite stops
being run during TDD. Nothing in the unit tier may invoke the real pipeline.

Every fix needs BOTH: a synthetic unit test pinning the topology, and a clean
sweep proving nothing else moved.

## 3. Commands

```bash
source .venv/bin/activate            # required; bare `python` is not on PATH

python tools/regress.py              # whole corpus
python tools/regress.py --sheet s07  # one sheet (repeatable)
python tools/regress.py --json       # machine-readable results

python tools/fetch_fixtures.py       # verify the downloaded bundle
python tools/add_sheet.py new.pdf --desc existing-floor-plans
```

## 4. Reading the report

One line per sheet, then indented detail. Every form you can see:

```
s01  window 4/4  unreviewed 24                        ← healthy, scored
s07  door 12/12  window 8/8  gaps CLOSED 1            ← healthy, needs review
s09  unlabeled — every detection is unreviewed        ← no verdicts recorded yet
s14  SKIPPED — not downloaded                         ← exit 2
s07  ✗ content changed since ground truth was recorded ← sha mismatch, exit 1
s07  ✗ manifest claims this sheet is labeled …         ← truth file lost, exit 1
```

Indented lines under a sheet:

| Line | Meaning | Fails? |
|---|---|---|
| `✗ LOST <type> @ (x,y)` | A `confirmed` verdict no longer matches any entity | **yes** |
| `✗ FALSE POSITIVE RETURNED <type> @ (x,y)` | A known-wrong detection came back as an entity | **yes** |
| `✗ UNSCORED PAGE(S) n` | Ground truth exists for a page the run produced no output for | **yes** |
| `REVIEW gap closed: …` | A `deferred` miss now detects — confirm, then promote it | no |
| `REVIEW new <type> @ (x,y) conf 0.67` | A detection with no verdict yet | no |
| `REGION CACHE MISS` | Classification fell back to whole-page; detection scope differs from the labeled run | no |

**New detections never fail the sweep.** Improving detection must not turn the
suite red — it queues review instead. This is the single most important property
of the design; do not "tighten" it.

## 5. Exit codes

| Code | Cause |
|---|---|
| 0 | Clean, or REVIEW items only |
| 1 | Lost `confirmed` · returned `false_positives` · sha mismatch · unscored truth page · `labeled: true` with missing/unlabeled truth |
| 2 | A manifest sheet is not downloaded (incomplete corpus) |

A regression outranks a missing sheet.

## 6. Ground truth

One committed file per sheet: `tests/ground_truth/sNN.json`.

```json
{"sheet": "s01",
 "pdf_sha256": "0867a4be…",
 "reviewed": "2026-08-06",
 "pages": {
   "1": {
     "confirmed":       [{"type": "window", "bbox": [954.75, 811.5, 961.25, 888.5],
                          "tag": "W4", "path_indices": [1576], "note": "short, neutral"}],
     "false_positives": [{"type": "door", "bbox": [...], "note": "toilet pan corner"}],
     "deferred":        [{"type": "room", "bbox": [...], "note": "why we parked it"}]}}}
```

| List | Meaning | Matched against |
|---|---|---|
| `confirmed` | The human said this detection is correct | emitted entities |
| `false_positives` | The human said this detection is wrong | **emitted entities only** — one sitting in `rejected` passes, because that is the desired outcome |
| `deferred` | A reported miss we consciously chose NOT to fix | emitted entities; a match is reported CLOSED |

Matching is **geometric**: same `type`, IoU ≥ 0.5, greedy best-pair-first. Entity
ids (`door_0015`) are ordinal and shift the moment an earlier detection
disappears, so nothing keys on them. `path_indices` is the debug-viewer handoff,
stored as a human note only.

`reviewed: null` = adopted but unlabeled. Valid state: every detection reads as
unreviewed, nothing can fail.

### Rules for editing these files

- **Never invent a verdict.** Ground truth records what a human judged. If you
  cannot point at the human's statement, it does not go in the file.
- **`deferred` is for conscious decisions only** — never speculative, never "this
  looks like it should have been detected".
- Record a `false_positive` only if the pipeline currently EMITS it as an entity.
  Recording one it already rejects is inert.
- Bboxes must be REAL bboxes from the pipeline's current output, not hand-drawn.
- When you record a sheet's first verdicts, set `"labeled": true` on its
  `fixtures/MANIFEST.json` entry. From then on the sweep exits 1 if that ground
  truth ever goes missing.

## 7. The loop when tuning detection

1. `python tools/regress.py` — establish the baseline is clean.
2. The user opens `debug_viewer.html` (`app.py extract --debug`) and reports path
   indices of misses / false positives.
3. Record the verdicts in `tests/ground_truth/sNN.json` — a data commit, no code.
4. Fix the algorithm. Pin the topology with a synthetic test in the fast tier.
5. `python tools/regress.py` — no lost `confirmed`, no returned false positives.
   A `deferred` that flips to CLOSED gets confirmed by the user, then promoted.

Steps 3 and 4 are separate commits. The verdict is data; the fix is code.

## 8. Corpus mechanics

`fixtures/MANIFEST.json` (committed) is the **sole authority** on membership — a
PDF sitting in `fixtures/sheets/` that is not in the manifest is reported
UNTRACKED and never swept. This is what makes a sweep reproducible across
machines from a given commit.

| Field | Meaning |
|---|---|
| `slug` | `sNN`, the stable identity |
| `file` | `sNN-<drawing-type>.pdf` |
| `sha256` | Pins the bytes the verdicts were recorded against |
| `pages` | Page count |
| `tier` | `reference` (s01, s02) · `corpus` · `retired` (skipped by the sweep) |
| `labeled` | Optional. `true` = this sheet HAS verdicts; losing them fails the sweep |

**Slug content is immutable.** A revised drawing is adopted as a NEW slug —
never dropped over an existing one, which would silently invalidate every bbox
recorded against it. `add_sheet.py` refuses a duplicate by sha and assigns the
next free slug (never reusing a gap, which would collide with a retired slug's
ground truth).

Adopting a sheet leaves two follow-ups: seed its region cache with one
Gemini-enabled run (`python app.py extract fixtures/sheets/sNN-….pdf`), and
upload the PDF plus its `.regions_cache/` entry to shared storage.

## 9. Invariants you must not break

- **No PDF is ever committed.** The sheets are NDA-covered.
- **No address-bearing text in tracked files.** A planning-portal application
  number (e.g. a 6–7 digit id) resolves to a property address on the public
  portal, so those ids count. They were scrubbed once; do not reintroduce one.
  `tests/test_ground_truth_hygiene.py` scans committed ground truth AND the
  manifest; `add_sheet.py` rejects an address-bearing `--desc`.
- **The unit tier stays fast** and never runs the pipeline.
- **A test must be able to fail.** See §10.

## 10. Gotchas, each learned by shipping the bug

| Trap | What happens | Do instead |
|---|---|---|
| `git grep -E "\bID\b"` | `\b` is unsupported by the default matcher here — returns empty ALWAYS, so the check passes with the thing still present | `git grep -P` |
| `from regression.corpus import SHEETS_DIR` | Binds the path at import; a test's monkeypatch becomes a no-op and the tool silently reads the REAL corpus while passing | `import regression.corpus as c` then `c.SHEETS_DIR` |
| Test fixture below a gate | An IoU-0.43 bbox never reaches the sort it was written to test — deleting the sort broke nothing | Prove it: delete the code, watch the test fail, restore |
| `warnings.json` as a list | It is `{"total_warnings": N, "warnings": [...]}` | Read the `warnings` key |
| Guard length caps | A sha256 is 64 chars and tripped the 60-char cap on its first real file | Budget per field, narrowly |

When you add a guard or a regression test, **verify it bites**: remove the code
it protects, confirm the test fails, then restore. A test that cannot fail is
worse than no test — it advertises protection that does not exist.

## 11. Current state (2026-08-06)

- **s01 is the only labeled sheet** — 4 confirmed windows, carried over from the
  interactive ground truth in `tests/test_window_detection.py`. Its doors, rooms,
  labels and schedules are unreviewed, as is all of s02–s20.
- **s09 and s19 detect nothing** (0 entities). Unexplained — check before
  labeling them.
- **s02 hits `REGION_CACHE_MISS_OFFLINE`**, so it detects whole-page rather than
  region-filtered. Resolve before recording s02's verdicts, or they pin to a
  fallback run.

## 12. Where the code lives

```
regression/corpus.py       # manifest reading, slug → path, hashing
regression/ground_truth.py # verdict dataclasses, load_truth, write_empty_truth
regression/matching.py     # iou, match_entities (MIN_IOU = 0.5)
regression/sweep.py        # runs the pipeline per sheet, scores pages
regression/report.py       # SheetResult, render, exit_code
regression/hygiene.py      # address/postcode patterns, shared by the guards
tools/regress.py           # the CLI
tools/fetch_fixtures.py    # bundle verifier (download is manual)
tools/add_sheet.py         # adoption
```

`regression/__init__.py` re-exports ground-truth and matching names only — it
must NOT import `sweep`, which pulls in the heavy `pipeline` module and would
slow every test touching the package.
