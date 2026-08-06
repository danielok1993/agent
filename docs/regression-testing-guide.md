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
| Unit | `python -m unittest discover tests` | ~8s | Synthetic geometry, 603 tests. Run constantly. |
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
python tools/regress.py --debug      # also write debug_trace.json + debug_viewer.html
                                      # per page -- off by default, see §4

python tools/review.py               # record verdicts, every sheet with unreviewed detections
python tools/review.py s07           # one sheet (repeatable)

python tools/fetch_fixtures.py       # verify the downloaded bundle
python tools/add_sheet.py new.pdf --desc existing-floor-plans
```

## 4. Sweep output

`tools/regress.py` used to extract into a `tempfile.TemporaryDirectory()` and
delete it the instant scoring finished, so a REVIEW line pointed at nothing a
human could open. Output now persists to `outputs/regress/<slug>/<timestamp>/`
(gitignored, same per-page contract as `python app.py extract`) — but each
slug's directory is **wiped at the start of that slug's next sweep**, so
`latest_run()` is unambiguous. Copy out anything you want to survive the next
`--sheet <slug>` run.

Two things are pruned or absent by default, both sized by measuring the actual
corpus rather than guessing:

- **The debug trace is opt-in** (`--debug`). It scales with primitive count,
  not page count: on the corpus's heaviest sheets it cost 200–300MB per sheet
  (s16, s18) against a +100MB/sheet budget, even though the same flag measured
  a cheap +11.1MB on the reference sheet s01 alone — a sweep of the reference
  sheets tells you nothing about the corpus's worst case. Without `--debug`,
  `debug_trace.json` and `debug_viewer.html` are not written at all.
- **Five page-level files nothing reads are deleted** right after scoring and
  after the review images are drawn: `primitives.json`, `candidates.json`,
  `pdfplumber_comparison.json`, `regions.json`, `region_crops/`. Measured on
  s18: 142MB for one page with the debug trace off, 139MB of it
  `primitives.json` alone; pruning took that page to 3.1MB. `pipeline.py`'s
  output contract for an ordinary `app.py extract` run is untouched — the
  sweep prunes only its own persisted copy. Need one of these files for a
  specific sheet anyway? Run `python app.py extract fixtures/sheets/<file>`
  directly — it writes the full, unpruned contract.

What survives every sweep: `render.png`, `overlay.png`, `final_entities.json`,
`review_<type>.png` (§8), `sweep_meta.json` (the sha the run was produced
from — `tools/review.py`'s provenance check reads it, §8), and the
run-root `summary.json` / `warnings.json`.

## 5. Reading the report

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
| `REVIEW new door_0007  conf 0.67  (954,850)` | A detection with no verdict yet. The name is this sweep's ordinal entity id, shown so you can find the box on `review_door.png` — never written to ground truth | no |
| `images: <dir>/pages/  — then: python tools/review.py <slug>` | Printed once per sheet with unreviewed items; where the review images live and the command that records verdicts against them (§8) | no |
| `REGION CACHE MISS` | Classification fell back to whole-page; detection scope differs from the labeled run | no |

**New detections never fail the sweep.** Improving detection must not turn the
suite red — it queues review instead. This is the single most important property
of the design; do not "tighten" it.

## 6. Exit codes

| Code | Cause |
|---|---|
| 0 | Clean, or REVIEW items only |
| 1 | Lost `confirmed` · returned `false_positives` · sha mismatch · unscored truth page · `labeled: true` with missing/unlabeled truth |
| 2 | A manifest sheet is not downloaded (incomplete corpus) |

A regression outranks a missing sheet.

## 7. Ground truth

One committed file per sheet: `tests/ground_truth/sNN.json`.

```json
{"sheet": "s01",
 "pdf_sha256": "0867a4be…",
 "reviewed": "2026-08-06",
 "pages": {
   "1": {
     "confirmed":       [{"type": "window", "bbox": [954.75, 811.5, 961.25, 888.5],
                          "tag": "W4", "path_indices": [1576], "note": "short, neutral"},
                         {"type": "room", "bbox": [...], "polygon": [[x, y], ...],
                          "shape": "partial", "note": "hall — outline not right yet"}],
     "false_positives": [{"type": "door", "bbox": [...], "note": "toilet pan corner"}],
     "deferred":        [{"type": "room", "bbox": [...], "note": "why we parked it"}]}}}
```

| List | Meaning | Matched against |
|---|---|---|
| `confirmed` | The human said this detection is correct | emitted entities |
| `false_positives` | The human said this detection is wrong | **emitted entities only** — one sitting in `rejected` passes, because that is the desired outcome |
| `deferred` | A reported miss we consciously chose NOT to fix | emitted entities; a match is reported CLOSED |

Matching is **geometric**: same `type`, IoU ≥ 0.5, greedy best-pair-first — for
every type, rooms included. Entity ids (`door_0015`) are ordinal and shift the
moment an earlier detection disappears, so nothing keys on them, and nothing
ever writes one into this file. `path_indices` is a debug-viewer handoff for
the hard cases, stored as a human note only.

A `confirmed` room carries two more fields (§8): `polygon`, the outline
recorded at review time, and `shape`, either `partial` ("real room, the
polygon isn't right yet" — a baseline to detect drift against, not an ideal)
or `approved` (signed off). **Both are write-only in V1** — `evaluate_page`
matches every type, rooms included, on bbox IoU alone, so a `partial` room's
polygon can drift across sweeps without failing anything. Geometry-based room
scoring (IoU bands against `shape`, an accept-new-baseline pass) is a later
phase; don't read `shape` as an active guard.

`reviewed: null` = adopted but unlabeled. Valid state: every detection reads as
unreviewed, nothing can fail.

## 8. Recording verdicts

`python tools/review.py [slug ...]` is how ground truth gets written — not by
hand-editing JSON (§9 covers the cases that are still a hand edit). It reads
the output a sweep already persisted (§4) and never re-runs detection; run
`tools/regress.py` first.

The walk is **sheet → page → category**, category being
`door → window → room → label → schedule` — doors first because they are the
most numerous and most often wrong, rooms last because judging a room is
slower and the earlier passes warm up the eye on the same drawing. Per
category it prints the path to that category's `review_<type>.png` — one
image per page per entity type, each detection stamped with a short id
(`d7` = door_0007, `w3` = window_0003, `r2` = room_0002) matching the
terminal's REVIEW lines — then asks **twice**:

1. which detections are CORRECT
2. of what's left, which are WRONG

Anything ticked in neither pass stays unreviewed and reappears on the next
sweep — "I can't tell from this image" costs nothing. **The toggle key is
Space.** The first choice on every screen is `— none of these —`; ticking it
means the whole selection is empty, no matter what else got ticked alongside
it — a second, visible way to postpone a screen on top of the picker's own
correct empty-Enter behavior.

Recording a false positive is expected to turn the *next* sweep red: it will
exit 1 (§6) until the detector stops emitting that detection. That is by
design, not a break — it is the queue of detector work the verdicts you just
recorded created. Don't be alarmed by a red sweep right after a review
session.

Review images are drawn once, at sweep time, from that sweep's full
unreviewed set — they are a snapshot, not a live view. If a session is
interrupted partway through a sheet and resumed later against the same sweep
output (no re-sweep in between), the picker correctly shrinks to what is
still actually unreviewed, but the image on disk still shows every box from
the original set — including ones a prior partial session already gave a
verdict to. The picker is always the authority; re-run
`python tools/regress.py --sheet <slug>` to redraw the images. This matters
in practice: labeling 19 sheets is multi-session work, and a
`review_door.png` still showing yesterday's confirmed door is expected, not
a sign the verdict was lost.

A room ticked CORRECT gets one more prompt: is the recorded polygon the
outline you want (`approved`), or a real room whose shape still needs work
(`partial`)? Either answer confirms the room; `partial` only flags the
polygon as a baseline, not a rejection (§7).

Verdicts for a whole sheet are written in a single call, after every category
on every page has been walked (`regression/verdicts.py::record_verdicts`), so
an interrupted session loses at most the sheet in progress, never a
half-written page. That same call sets `"labeled": true` on the sheet's
`fixtures/MANIFEST.json` entry. Ctrl-C exits 130 and records nothing for the
sheet in progress (earlier sheets in a multi-slug run are already on disk); a
sheet that fails some other way is reported and skipped, and the walk
continues, exiting 1 at the end — so a scripted run can tell "20 clean" from
"19 clean, one broken."

`tools/review.py` refuses to review a sheet whose provenance is doubtful,
rather than guess:

- no persisted sweep output for the slug — run `tools/regress.py --sheet
  <slug>` first
- the PDF on disk no longer hashes to what `fixtures/MANIFEST.json` records
- the run's `sweep_meta.json` names a different sha than the manifest holds
  now (swept, then the PDF was swapped and the manifest re-pinned) — or is
  missing entirely, which means the run predates this stamp and its
  provenance cannot be recovered
- the existing ground truth was reviewed against a different PDF than the one
  on disk now

Each of these is a state where the image could show one drawing while a
verdict gets pinned to another. The fix is always cheap (re-sweep, or adopt
the revision as a new slug, §10) — it is never worth papering over.

## 9. Rules for editing ground truth

`tools/review.py` is the normal writer now. You still touch
`tests/ground_truth/sNN.json` directly for the one thing the tool does not do:
promoting a `REVIEW gap closed` line to `confirmed` (§10) — a `deferred` entry
has to be removed as part of that promotion, and `record_verdicts` only ever
appends, on purpose (widening it to delete would make it possible to destroy
a recorded verdict by accident). The same rules apply whichever way the write
happens:

- **Never invent a verdict.** Ground truth records what a human judged. If you
  cannot point at the human's statement, it does not go in the file.
- **`deferred` is for conscious decisions only** — never speculative, never "this
  looks like it should have been detected".
- Record a `false_positive` only if the pipeline currently EMITS it as an entity.
  Recording one it already rejects is inert.
- Bboxes must be REAL bboxes from the pipeline's current output, not
  hand-drawn. (`tools/review.py` enforces this by construction — it only ever
  offers entities from an actual run.)
- When you record a sheet's first verdicts, set `"labeled": true` on its
  `fixtures/MANIFEST.json` entry. From then on the sweep exits 1 if that ground
  truth ever goes missing. (`record_verdicts` does this for you.)

## 10. The loop when tuning detection

1. `python tools/regress.py` — establish the baseline is clean.
2. Open `outputs/regress/sNN/<timestamp>/pages/page_NN/review_<type>.png` —
   each unreviewed detection is stamped with a short id (`d7` = door_0007)
   matching the sweep's REVIEW lines. For a hard case, re-run with `--debug`
   and open `debug_viewer.html` instead (§4).
3. `python tools/review.py sNN` — tick the correct detections, then the wrong
   ones (Space to toggle); anything ticked in neither is postponed and
   reappears next sweep. This writes `tests/ground_truth/sNN.json` and sets
   `"labeled": true` in `fixtures/MANIFEST.json` (§8) — commit both as a data
   commit, no code.
4. Fix the algorithm. Pin the topology with a synthetic test in the fast tier.
5. `python tools/regress.py` again — no lost `confirmed`, no returned false
   positives. A `deferred` entry that flips to `REVIEW gap closed` is
   confirmed by the user, then promoted to `confirmed` by hand (§9) —
   `tools/review.py` only records verdicts on a sweep's unreviewed
   detections, not this promotion.

Steps 3 and 4 are separate commits. The verdict is data; the fix is code.

## 11. Corpus mechanics

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

## 12. Invariants you must not break

- **No PDF is ever committed.** The sheets are NDA-covered.
- **No address-bearing text in tracked files.** A planning-portal application
  number (e.g. a 6–7 digit id) resolves to a property address on the public
  portal, so those ids count. They were scrubbed once; do not reintroduce one.
  `tests/test_ground_truth_hygiene.py` scans committed ground truth AND the
  manifest; `add_sheet.py` rejects an address-bearing `--desc`.
- **The unit tier stays fast** and never runs the pipeline.
- **A test must be able to fail.** See §13.
- **Sweep output (`outputs/regress/`) is gitignored and disposable.** It is
  re-derived from the PDF plus whatever code is checked out; nothing there is
  a record of anything. The record is `tests/ground_truth/`.

## 13. Gotchas, each learned by shipping the bug

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

## 14. Current state (2026-08-06)

- **s01 is the only labeled sheet** — 4 confirmed windows, carried over from the
  interactive ground truth in `tests/test_window_detection.py`. Its doors, rooms,
  labels and schedules are unreviewed, as is all of s02–s20.
- **s09 and s19 detect nothing** (0 entities). Unexplained — check before
  labeling them.
- **s02 hits `REGION_CACHE_MISS_OFFLINE`**, so it detects whole-page rather than
  region-filtered. Resolve before recording s02's verdicts, or they pin to a
  fallback run.

## 15. Where the code lives

```
regression/corpus.py         # manifest reading, slug → path, hashing
regression/ground_truth.py   # verdict dataclasses, load_truth, write_empty_truth
regression/matching.py       # iou, match_entities (MIN_IOU = 0.5)
regression/sweep.py          # runs the pipeline per sheet, persists + prunes
                              # output, scores pages (see PRUNE_PAGE_ENTRIES)
regression/run_dir.py        # outputs/regress/<slug>/<timestamp> layout;
                              # reset_slug_dir, latest_run
regression/review_render.py  # write_review_overlays — per-category review
                              # PNGs, short_id (door_0007 -> d7)
regression/review_session.py # pending() — what still needs a verdict, plus
                              # the provenance checks tools/review.py refuses on
regression/verdicts.py       # Verdict, record_verdicts — the one ground-truth
                              # writer; entity ids never reach disk
regression/report.py         # SheetResult, render, exit_code
regression/hygiene.py        # address/postcode patterns, shared by the guards
tools/regress.py             # the sweep CLI
tools/review.py              # the verdict-recording CLI
tools/fetch_fixtures.py      # bundle verifier (download is manual)
tools/add_sheet.py           # adoption
```

`regression/__init__.py` re-exports ground-truth and matching names only — it
must NOT import `sweep`, which pulls in the heavy `pipeline` module and would
slow every test touching the package.
