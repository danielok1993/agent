# 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation

Session findings written for the next model to pick up. Everything below is
measured on this machine (MacBook, **10 cores, 16 GB RAM**, macOS 25.3.0,
Python 3.14 venv) unless explicitly marked *inferred*. Branch:
`feat/floor-plan-region-filtering`.

## Status at time of writing

- **Uncommitted working-tree change** (user has not asked to commit yet):
  the clip-cut extent fix in `layout/clips.py` + `layout/segmenter.py` +
  tests (`tests/test_layout_segmenter.py`, `tests/test_layout_clips.py`).
  `python -m unittest discover tests` → **406 tests, all pass**.
- Nothing else was changed. `batch_extract.py`, `extraction/extractor.py`,
  detection code: all untouched.
- Open decisions the user deferred: commit message suggested was
  `fix: clip-edge cuts only apply where the donating clip rect actually is`;
  fixes B/C/D below are proposed but **not implemented**.

---

## Part 1 — Fix (done): clip edges sliced drawings they never touch

### Bug

`clip_cut_positions` (`layout/clips.py`) flattened every qualifying clip
rect into bare row/col coordinates. `_clip_cut` (`layout/segmenter.py`) then
cut **any** XY-cut cell containing that coordinate with ink on both sides —
page-globally. One drawing's clip edge sliced unrelated drawings anywhere
along its axis, splitting single floor plans into multiple `floor_plan`
regions (the user's reported symptom: red dashed region outline through the
middle of a plan on the overlay).

Measured attributions (every split matched a clip edge from elsewhere):

| Sheet | Bogus cut | Donating clip (px, 150 DPI) |
|---|---|---|
| 2387826 | x=948 through both floor plans (top of sheet) | location plan clip `(948, 3345, 2700, 4859)` (bottom of sheet) |
| 2682241 | x=1924 through first-floor plan (y 864–1724) | `(1926, 3434, 2595, 4821)` |
| 2682241 | y=728 slicing existing-plan top strip | `(1507, 728, 2446, 1880)` |
| 2557737 | x=1572 splitting elevation pair; y=1504/1652 fragmenting right-column floor plan into 3 (two frags classified at 0.80) | `(283, 267, 1574, 1504)` and `(287, 1652, 3108, 2944)` |

### Fix

Cut candidates now carry the donating rect's perpendicular extent:
`clip_cut_positions` returns `(position, perp_lo, perp_hi)` bin tuples;
`_clip_cut(profile, offset, cuts, perp_lo, perp_hi)` skips an edge unless
`min(hi, perp_hi) - max(lo, perp_lo) > 0` against the cell being cut.
`_xy_cut` passes `(c0, c1)` for row cuts and `(r0, r1)` for col cuts.
TDD: new test `test_clip_edge_only_cuts_cells_its_rect_overlaps` failed
first (4 regions, top drawing split), passes after.

### Sweep (old vs new segmentation, all `plans/*.pdf` + both reference PDFs)

Sheets without qualifying clips are byte-identical by construction
(574477, 1789452, and others did not appear in the diff). Reference PDFs
have no qualifying clips → golden tests untouched.

| Sheet | Regions | assigned_path_fraction | Verdict |
|---|---|---|---|
| 2387826 | 14 → 10 | 0.943 → 0.943 | 4 floor_plan fragments → 2 whole plans; elevations merge same-type |
| 2682241 | 21 → 13 | 0.654 → 0.655 | both plans whole; elevation/block_plan groups merge |
| 2557737 | 26 → 18 | 0.989 → 0.991 | all mergers same-type (verified against classified run `outputs/2026-07-30_21-13-08`); right floor plan healed |
| 2710870 | 20 → 15 | 0.853 → 0.880 | coverage-suppressed both ways → no detection change |
| 3447461 | 19 → 19 | 0.993 → 0.997 | the 5-clip sheet clips were built for; legit splits kept |
| 3055574 | 8 → 7 | 1.000 → 1.000 | merged bottom strip is the title block (rendered and checked) |
| 3055578 | 3 → 3 | 1.000 → 1.000 | one box grew 4px |
| 4103493, 4103495 | same | same | SAME |

No sheet lost coverage. Detection input changes on **no** sheet: fragments
that merged were same-type, and the two coverage-suppressed sheets detect
whole-page regardless. Region cache is keyed on geometry → the changed
sheets re-classified **once** in the user's 16:38 batch (one Gemini call
each, now cached in `plans/.regions_cache/` — note the cache lives next to
the PDFs, not in the repo root).

---

## Part 2 — Investigation (no fix applied): four sheets time out in batch

User report: `batch_extract.py` marks these ✗ `timeout (5 minutes)`:
2682241, 574477, 2710870, 1789452.

### Verdict

**Not caused by the clip fix.** Two independent causes, both predating it:

| Sheet | Page paths | Images (p1) | Cause | Detection input today |
|---|---|---|---|---|
| PROPOSED_FLOOR_PLANS-574477 | 18,346 | **3,691** | stage-1 `extract_images`: per-image `get_image_bbox` → MuPDF content filter per call ≈ 6 of its 7.5 min | filtered, 17,657 paths (one floor_plan region, 96% of ink) |
| LOCATION…-2682241 | 148,257 | 0 | stage-5 detection | whole page (coverage 0.655 < 0.90 gate) |
| PROPOSED_PLANS…-2710870 | 298,603 | 1 | stage-5 detection | whole page (coverage 0.880 < 0.90 gate) |
| REV…-1789452 | 258,400 | 1 | stage-5 detection | filtered, **127,087** floor_plan paths (coverage ~0.96, filtering ACTIVE) |

Proof points that the clip fix is not the cause:

- 574477 and 1789452 have **no qualifying clips** → segmentation
  byte-identical pre/post fix; both have exactly **one** geometry hash in
  `plans/.regions_cache` (classification reused across both batches).
- 2682241's **pre-fix** batch run (15:28, dir since deleted) was already
  incomplete — no `warnings.json`, i.e. killed mid-run at the 5-min timeout
  before the fix existed.
- 2682241/2710870 are coverage-suppressed both before and after → identical
  whole-page detection load.

### Timings (measured, contention-free, `--no-gemini`, cache hits)

- **574477**: `454.56 s real / 451.44 s user`, exit 0, 46 candidates /
  15 entities, peak RSS 558 MB. Reproduced twice (second run also exit 0).
  Stack samples (macOS `sample`) at t=90 s, t=240 s and t=360 s all inside
  `pdf_filter_page_contents` → `PdfSanitizeFilterOptions2::image_filter`
  (MuPDF content-stream sanitize with per-op Python callback), and the
  run's `pages/page_01/` dir was still **empty at 5:43 elapsed** — so
  ≈ 6 min is stage-1 image extraction, ≈ 90 s is everything else including
  detection. The offending loop is `extraction/extractor.py:214`
  (`page.get_image_bbox(img)` per image); **identical loop exists on
  `main`** (`git show main:extraction/extractor.py`, line 134) — not a
  branch regression.
- **2710870**: stages 1–4 took **12 seconds total** (file mtimes:
  render.png 16:55:06, regions.json :09, pdfplumber_comparison.json :16
  for a 16:55:04 start). Everything after is stage-5 detection:
  **≥ 58 minutes without completing** (run was killed externally when its
  60-min watchdog expired; `candidates.json` never appeared). An earlier
  orphan of the same sheet was killed at 23:09 elapsed. So true cost is
  > 58 min — unknown total. Stack samples at t=300 s and t=1500 s: zero
  GEOS/shapely frames, dominant frames pure-Python bytecode at different
  code locations → it is in the **pure-Python wall pair-scanning phase
  (pre-rooms)**, progressing, not stuck in one loop.
- Batch context: 5-way `ProcessPoolExecutor` on 10 cores amplifies all of
  the above; completion order in the user's batch put these four last.

### `batch_extract.py` orphan bug (found, not yet fixed)

`run_extract` uses `subprocess.run(cmd, shell=True, timeout=300)` where cmd
is `source .venv/bin/activate && python app.py extract …`. On timeout,
only the **shell** is killed; the python grandchild survives. Measured: an
orphaned `app.py extract …2710870` (PPID 1) at 99% CPU, 23+ minutes after
its "timeout"; killed manually. Consequences: every batch retry runs on a
machine still burning cores from previous attempts (the user's "keep
timing out" experience), and "timed-out" work sometimes completes later
and writes output dirs nobody associates with the batch.

### Gemini call-boundedness audit (user asked "no infinite AI calls")

- Single call-site: `pipeline.py:301` (`resolve_page_regions`), executed
  only on cache miss; `--refresh-regions` is the only forced re-call.
- `gemini/client.py` contains **no retry/backoff/sleep loop at all**.
- Classification failure → `REGION_CLASSIFY_FAILED` warning, run continues
  unfiltered, **no retry**. Success → written to `<pdf_dir>/.regions_cache`.
- Raster pages (no vector paths) skip classification entirely.
- Therefore: worst case one API call per page per segmentation geometry.
  All 18 plan sheets currently have cache entries → a batch re-run today
  costs **zero** Gemini calls. `--no-gemini` never calls (uses cache or
  falls back to whole-page with `REGION_CACHE_MISS_OFFLINE`).

### Loop-termination audit (user asked "no infinite loops")

All `while` loops in `detection/`, `layout/`, `extraction/` reviewed:
index-walkers, DFS over finite stacks, or convergence loops with strict
progress (`detection/walls.py:464` moves ≥1 ring pool→accepted per pass;
`detection/walls.py:1390` collinear merge strictly reduces segment count
per pass — worst case **O(n³)**, a slowness suspect on 100k+ faces, never
non-terminating). `doors/arcs.py` `while True` loops walk visited-sets or
are capped (`DOOR_POLYLINE_CYCLE_MAX_SEGMENTS`). Empirically 574477
terminates (twice); 2710870 unproven beyond 58 min (bounded by analysis,
not by observation).

---

## Part 3 — Proposed fixes for the next model (none implemented)

Ordered by value/effort:

1. **`batch_extract.py`: kill process groups + realistic timeout.**
   Launch without `shell=True` (use `.venv/bin/python` directly — no
   activate needed), `start_new_session=True`, on `TimeoutExpired` send
   `os.killpg(os.getpgid(p.pid), SIGKILL)`. Raise per-PDF timeout to
   ≥ 30 min or make it a CLI flag — note 2710870 exceeds even 58 min until
   fix 4 lands, so consider a `--skip` list or per-sheet budget.
2. **`extract_images` single-pass** (`extraction/extractor.py:200`):
   replace the per-image `get_image_bbox` loop with one
   `page.get_image_info(xrefs=True)` pass (one content-stream traversal
   for all images), mapping xref→bbox. Must preserve: 150-DPI scale-only
   transform (NOT rotation — see the e97c551 rationale in the code
   comment and `[[pymupdf-rotation-frame-gotcha]]`), `pixel_area`
   computed from raw (point-space) bbox vs page.rect area, and dedup
   semantics of `get_images(full=True)`. Expected: 574477 ≈ 7.5 min →
   ≈ 90 s. Verify bbox parity on 574477 + 1326087 (rot 270) + 3447461
   (31 images) before/after.
3. **Fold dropped sub-min-side leaves into the nearest kept region**
   (the region-filtering branch's known deferred follow-up) so coverage
   clears `REGION_MIN_COVERAGE_FRAC` (0.90) and filtering activates on
   the giants. Measured stakes: 2682241 coverage 0.655 → detection input
   would drop 148,257 → ≈ 51k paths (floor_plan regions 29,719 + 21,276);
   2710870 coverage 0.880 → 298,603 → 73,874 (cached classification,
   entry `…-eca91b20b29056c9`: GROUND 50,050 + FIRST 23,824). Pair scans
   are superlinear so expect better-than-4× wall-clock. Risk: folding must
   not change which regions classify as what (geometry change → cache
   miss → one re-classification call per sheet, by design).
4. **Detection performance on giant path counts** — the only rescue for
   1789452 (127k paths already filtered). Where the time is: pure-Python
   wall pair-scanning before rooms (no GEOS in samples at 5 and 25 min);
   prime suspects are the O(n²) face-pair loops and the O(n³)-worst-case
   collinear merge (`detection/walls.py:1390`). Profile properly with
   `sudo py-spy` (installed in the venv; needs root on macOS) or add
   per-stage timing logs to `detection/orchestrator.py` before optimizing.
   A cheap interim: spatial-bucket the face-pair candidate search.

### Re-measurement recipes

```bash
# Solo timing (cache hit → no API call):
/usr/bin/time -l python app.py extract plans/<sheet>.pdf --no-gemini

# Stage attribution without instrumentation: watch output-file mtimes
ls -lT outputs/<run>/pages/page_01/    # render(2) → regions(3) → plumber(4) → candidates(5)

# C-level stack sample (no root):  sample <pid> 15 -file out.txt
# Python-level:                    sudo .venv/bin/py-spy dump --pid <pid>

# Segmentation-only old-vs-new comparison harness: monkeypatch
# layout.segmenter.clip_cut_positions to a flattening wrapper and diff
# segment_page results per sheet (used for the Part-1 sweep).
```

Batch tally observed by the user (18 PDFs, 5 workers): 14 ✓, 4 ✗ — the
four sheets above, all at exactly `timeout (5 minutes)`.

---

## 2026-08-05 addendum — fixes landed, attribution corrected

Branch `fix/batch-timeout-remediation`: fixes 1–3 implemented (process-group
kill + 30-min `--timeout-minutes` default; single-pass `get_image_info`
image extraction; path-bearing small leaves fold into the nearest kept
region with a no-leak overlap gate). Measured: 574477 end-to-end
454.6 s → 9.1 s with identical detection output (46 candidates /
15 entities); coverage reaches 1.000 on every vector sheet, filtering
newly activates on 2682241 / 2710870 / 1326087.

**Fix 4 attribution correction**: with per-stage timing logs
(`detection.orchestrator` logger, INFO), the giant-sheet time is in
`detect_windows`, NOT the wall pair-scan the stack samples suggested —
windows runs before walls, which is what "pure-Python, pre-rooms" was
actually sampling. Measured on floor_plan-filtered inputs: 2682241
(51k paths) windows 84.1 s of 86.1 s total, wall_network 0.46 s; 1789452
(127k paths) windows 315.1 s of 320.5 s, wall_network 2.38 s. Scaling is
~quadratic in path count. Any future optimization effort belongs in
`detection/windows.py`'s pair scan, not `detection/walls.py`. With
fixes 1–3 all four timeout sheets fit comfortably inside the 30-minute
default budget, so that optimization was deferred.

Two pre-existing quirks documented while verifying image parity, both now
handled by the single-pass implementation: `get_images(full=True)` yields
one row per reference *name* (one xref drawn twice = two rows), and
`get_image_info` returns UNROTATED mediabox coordinates (like
`get_drawings`, unlike the rotated-frame `get_image_bbox` it replaced), so
images now take the full page transform.
