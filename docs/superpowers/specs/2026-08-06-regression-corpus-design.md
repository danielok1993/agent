# Regression Corpus — Design

**Date:** 2026-08-06
**Status:** Approved, not yet implemented

## Problem

Detection quality is now good enough that the binding constraint is *remembering
what "good" means*. Today it is not remembered anywhere:

- Two reference PDFs (`5-1133-WD03.pdf`, `floor-plans.pdf`) sit at the repo root
  and are committed. The other 18 sheets live in `plans/`, which is gitignored.
- Regressions are checked by re-running `app.py extract` and eyeballing the
  overlay, or by diffing two run directories with `tools/compare_entities.py`.
- When a new detection appears on a sheet, the *session* decides whether it is
  real. That verdict is never written down. The next session re-derives it from
  scratch, or silently accepts a false positive an earlier session had rejected.

The unit suite (432 tests, 8.3s) pins topologies as synthetic geometry and is
excellent at what it does, but it never sees a real sheet. `test_layout_golden.py`
is the only real-PDF gate and covers segmentation only.

**Goal:** make the human verdict durable, per sheet, so that "no regressions" is
a command rather than a memory exercise — and extend it from 2 sheets to 20.

## Constraints

1. **NDA.** Some sheets cannot be committed to any repo. They live in shared
   storage and are downloaded manually.
2. **No addresses.** Nothing committed may carry a property address, including
   indirectly: a planning-portal application ID resolves to an address on the
   public portal, so portal IDs count as address-bearing.
3. **Labeling stays manual.** The existing loop works: the user opens
   `debug_viewer.html`, reads off path indices, and hands them over. No review
   tooling is being built.
4. **The 8-second unit suite stays 8 seconds.** It is run constantly during TDD.

## Non-goals

- No labeling UI, contact sheets, or click-to-verdict viewer. (Revisit only if
  manual labeling actually becomes the bottleneck.)
- No CI. The sweep is a local command.
- No automatic verdicts. Nothing is ever marked correct without the user saying so.
- No history rewrite. Portal IDs remain in the 116 existing commits; only the
  working tree is scrubbed.

## Architecture

### Fixture layout

```
fixtures/                          # gitignored in its entirety
  sheets/
    s01-floor-plans.pdf
    s02-working-drawing-wd03.pdf
    s03-…  …  s20-….pdf
    .regions_cache/                # shipped in the bundle → sweeps never call Gemini
  MANIFEST.json                    # COMMITTED (see below)
tests/ground_truth/
  s01.json  s02.json  …            # COMMITTED — the human verdicts
tests/fixtures.py                  # slug → path resolution, skipUnless helper
tools/fetch_fixtures.py            # verifier (manual download, no SDK)
tools/add_sheet.py                 # adopt a new PDF into the corpus
tools/regress.py                   # the sweep
```

`fixtures/MANIFEST.json` is committed and is the authority on corpus membership:

```json
{"storage": "the corpus bundle is not public — ask the maintainer for it, and make sure every sheet is downloaded before sweeping",
 "sheets": [{"slug": "s07", "file": "s07-existing-floor-plans.pdf",
             "sha256": "9f2c…", "pages": 1, "tier": "corpus"}]}
```

`tier` is `reference` (s01, s02 — the two primary gates) or `corpus`, plus
`retired` for superseded revisions.

### Naming

`sNN-<drawing-type-descriptor>.pdf`. The descriptor is the existing drawing-type
wording, lowercased and kebab-cased (`existing-floor-plans`,
`proposed-plans-and-elevations`) — drawing type only, never a property
identifier. Slug order: `s01` = `floor-plans`, `s02` = the WD03 working
drawing, `s03`–`s20` = the remaining sheets alphabetically by their former name.

**Files are renamed at the source**, in shared storage, so the downloaded bundle
already uses slug names. No portal-ID → slug mapping file exists in the repo or
in the bundle; the translation is needed once, during migration, and then is
dead. Deduplication of a candidate new sheet is by sha256 against the manifest,
which needs no filename.

**Slug content is immutable.** A revised drawing is adopted as a *new* slug; the
superseded entry is marked `retired` and keeps its ground truth. Mutating a
slug's bytes would silently invalidate every bbox recorded against it.

### Ground truth

One file per sheet, committed, hand-written from the user's verdicts:

```json
{"sheet": "s07",
 "pdf_sha256": "9f2c…",
 "reviewed": "2026-08-06",
 "pages": {
   "1": {
     "confirmed": [
       {"type": "door", "bbox": [797.7, 787.7, 803.7, 882.2],
        "tag": "GD9", "path_indices": [1576], "note": "front entrance"}],
     "false_positives": [
       {"type": "door", "bbox": [412.0, 233.0, 480.0, 283.0],
        "note": "single_line_leaf on a toilet pan corner"}],
     "deferred": [
       {"type": "room", "bbox": [120.0, 400.0, 340.0, 610.0],
        "note": "bare hairline-pen wardrobe partition; accepting bare hairline "
                "pairs reopens fixture FPs — see CLAUDE.md"}]}}}
```

- `reviewed: null` means the sheet is adopted but unlabeled. Valid state.
- `confirmed` — the user has said this detection is correct.
- `false_positives` — the user has said this detection is wrong. Matched against
  **emitted entities only**, never against `rejected`: a candidate the pipeline
  itself rejects is the desired outcome, so a known false positive sitting in
  `rejected` passes. The entry fails the run only when the thing is promoted to
  an entity again.
- `deferred` — a miss the user reported that we consciously decided **not** to
  fix. Written only on a deliberate parking decision, never speculatively. Most
  reported misses never appear here: they get fixed, and the fix is recorded as
  a `confirmed` entry plus a synthetic unit test.

**Matching is geometric**: same `type`, IoU ≥ 0.5, greedy by best IoU. Entity IDs
(`door_0015`) are ordinal and shift whenever detection changes, so they are not
stored. `path_indices` is the user's debug-viewer vocabulary, stored as a human
note only — `final_entities.json` does not currently expose path indices.

**No-address rule.** Ground truth stores geometry and type. Sheet text is copied
only into `tag`, and only when it matches a drawing-tag pattern
(`^[A-Z]{0,4}\d{1,3}[A-Z]?$` — `W11`, `GD9`, `D05`). Room names, title-block
text and schedule contents are never copied. `note` is written by a human.
A guard test (`tests/test_ground_truth_hygiene.py`) scans every committed ground
truth file and fails on: any string over 60 characters outside `note`, any
`tag` not matching the pattern, and any string matching street/road/lane/avenue/
close/drive/way or UK postcode patterns.

### The sweep — `tools/regress.py`

Runs the pipeline over manifest sheets with `--no-gemini` (the shipped region
cache makes this deterministic and offline), matches output against ground truth,
prints one line per sheet:

```
s02  doors 12/12  windows 8/8  rooms 5/5   FP 0   deferred 3   unreviewed 0
s14  doors 14/15  ✗ LOST door @ (812,440)
s07  doors  9/9   FP 0   deferred 2→1 CLOSED @ (330,905)   unreviewed 2   REVIEW
```

Exit codes:

| Condition | Exit |
|---|---|
| A `confirmed` entry no longer matches any output | 1 |
| A `false_positives` entry reappears in output | 1 |
| A manifest sheet's sha256 does not match the file on disk | 1 |
| A manifest sheet is missing from disk | 2 |
| New unmatched detections, or a `deferred` entry closed | 0, printed under REVIEW |
| Clean | 0 |

New detections never fail the run. Improving detection must not turn the suite
red; it queues review instead. A closed `deferred` entry is likewise a REVIEW
item — it needs the user's confirmation before being promoted to `confirmed`.

Flags: `--sheet s07` (one sheet, or several), `--json` (machine-readable report).

Measured runtime with `--no-gemini` on the three heaviest sheets: 1.8s, 7.8s,
22.8s. Full 20-sheet sweep ≈ 2–3 minutes.

### Adoption — `tools/add_sheet.py`

```bash
python tools/add_sheet.py ~/Downloads/SOME_PLAN.pdf --desc existing-floor-plans
```

Hashes the file; if the sha is already in the manifest, reports the existing slug
and stops. Otherwise assigns the next free slug, renames the file into
`fixtures/sheets/`, reads the page count, appends the manifest entry, writes an
empty `tests/ground_truth/sNN.json` with `reviewed: null`, and prints the two
follow-ups: seed the region cache with one Gemini-enabled run, then upload the
renamed PDF and its cache file to storage.

A PDF sitting in `fixtures/sheets/` that is not in the manifest is reported by
the sweep as `UNTRACKED` and is never run. The manifest — not the directory — is
the authority, so a sweep is reproducible across machines from a given commit.

### Verification — `tools/fetch_fixtures.py`

Manual download; this is a verifier, not a downloader. Checks every manifest
sheet against `fixtures/sheets/`, reports missing slugs and sha mismatches, and
prints the storage location from the manifest. Exit 0 when the corpus is complete.

`tests/fixtures.py` resolves a slug to a path and provides the `skipUnless`
helper the real-PDF tests use, emitting one loud warning per session when the
fixtures directory is absent — so a fresh clone cannot silently skip every
real-PDF test and still look green.

## Two tiers, kept separate

| Tier | Command | Runtime | Covers |
|---|---|---|---|
| Unit | `python -m unittest discover tests` | 8s | Synthetic topologies, 432 tests |
| Sweep | `python tools/regress.py` | 2–3 min | 20 real sheets vs. ground truth |

The sweep is deliberately **not** part of `unittest discover`: a 2-minute suite
would stop being run during TDD. Real-PDF tests that already exist
(`test_layout_golden.py`, the ground-truth classes in `test_window_detection.py`,
the rotation test in `test_extraction_transform.py`) stay in the unit tier and
keep their current assertions — only their path resolution changes to the slug
loader.

## Workflow

1. `python tools/regress.py`
2. User opens `debug_viewer.html` on a sheet, hands over path indices of misses
   and false positives.
3. Verdicts are written into `tests/ground_truth/sNN.json` — a data commit, no
   code change.
4. The algorithm is fixed, and the topology gets a synthetic unit test in the
   8-second tier.
5. `regress.py` again: no lost `confirmed`, no returned `false_positives`. A
   `deferred` entry that flips to CLOSED is confirmed by the user and promoted.

## Phasing

**Phase 1 — migration.** Fixture layout, renaming (in storage and in the repo),
manifest, `fetch_fixtures.py`, `tests/fixtures.py`, existing real-PDF tests
switched to the slug loader, and the ~150 portal-ID mentions across `docs/`,
`tests/` and the memory files rewritten to slugs. Zero detection change, verified
by `tools/compare_entities.py` reporting identical output before and after.

**Phase 2 — mechanism.** `regress.py`, the ground-truth format, the hygiene guard
test, and `add_sheet.py`. Seeded with s01 and s02 only, whose correct detections
are already well understood.

**Phase 3 — corpus labeling.** Sheets labeled one at a time, as each is tuned.
Not 900 entities up front. Each newly labeled sheet becomes a gate the moment its
first verdict lands.

## Risks

- **Ground truth rots against a changed algorithm.** A change to coordinate
  normalization or region filtering would shift every bbox at once and fail every
  sheet. Mitigation: matching is IoU-based, not exact; a mass failure is a loud,
  correct signal rather than a subtle one.
- **Region-cache invalidation.** The cache key includes region geometry, so a
  `layout/` change turns cached classifications into misses, and the sweep falls
  back to whole-page detection (`REGION_CACHE_MISS_OFFLINE`) — changing detection
  scope silently. `regress.py` surfaces that warning per sheet in the report and
  counts it as a REVIEW item.
- **Unreviewed drift.** Since new detections never fail, a sheet can accumulate
  unreviewed detections indefinitely. The per-sheet `unreviewed` count in the
  report is the backlog signal; a sheet whose count keeps growing is a sheet
  whose ground truth is going stale.
