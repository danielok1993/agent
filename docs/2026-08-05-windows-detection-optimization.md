# 2026-08-05 — detect_windows performance on giant sheets (handoff)

Task for the next agent: make `detection/windows.py::detect_windows` fast on
100k+-path sheets **without changing its output by a single byte**. This is a
pure performance task — no detection-behavior change, no constant tuning, no
"improvements" to the heuristics along the way. If an optimization changes any
candidate on any gate PDF, the optimization is wrong, not the baseline.

Everything below is measured on this machine (MacBook, 10 cores, 16 GB,
macOS 25.3.0, Python 3.14 venv) unless marked *estimated*. Baseline branch:
`fix/batch-timeout-remediation` (commits 9af0fcc, 97b85ba, a58afb9, 9279901,
d4fd142 — see `docs/2026-08-04-region-clip-fix-and-batch-timeout-findings.md`
and its addendum for the context).

## Why this task exists (and why it was deferred)

The 2026-08-04 batch-timeout investigation blamed the giant-sheet detection
time on the wall pair-scan. That was wrong: per-stage timing logs (now on the
`detection.orchestrator` logger at INFO, commit a58afb9) show the time is in
`detect_windows`, which runs *before* walls — that is what the "pure-Python,
pre-rooms" stack samples were actually sampling.

Measured on floor_plan-filtered inputs (region cache classifications):

| Sheet | Paths into detection | windows | wall_network | total detection |
|---|---|---|---|---|
| 2682241 | 50,995 | **84.1 s** | 0.46 s | 86.1 s |
| 1789452 | 127,087 | **315.1 s** | 2.38 s | 320.5 s |

Scaling ≈ quadratic in path count (2.49× paths → 3.75× time). *Estimated*:
2710870 filtered (~74k paths) ≈ 110 s; unfiltered whole-page giants were the
>5-min / >58-min batch-timeout cases.

Deferred because fixes 1–3 already put all four timeout sheets comfortably
inside the batch runner's new 30-minute default. This task is the remaining
win: it turns ~5 min of windows scanning on 1789452 into seconds.

## Where the time goes

`detect_windows` (`detection/windows.py:479`) anchors on pairs of short
"cap" lines (jambs, 3–36 px) facing each other across an opening, confirmed
by ≥2 parallel glazing lines spanning the gap. Read
`docs/window-detection-tuning-guide.md` before touching the file — every
constant is measured against ground truth on the two reference PDFs.

Pipeline per page, with the complexity of each step (n = paths, C = cap
records in an orientation frame, G = glazing records in a frame):

1. `_line_records` (`windows.py:137`) — O(n). Cheap.
2. `_block_cap_records` (`windows.py:157`) — for every bar-shaped `re`/`qu`
   candidate, `crossed()` (`windows.py:170`) scans **all paths** → O(bars·n).
   Secondary hotspot on rect-heavy sheets.
3. `_cap_orientation_frames` (`windows.py:207`) — 90 overlapping angle frames
   (grid 2°, tol 4°); each cap lands in ~4 frames. On a hatch-dense sheet
   most short linework qualifies as a cap (3–36 px), so frames hold thousands
   of members.
4. Per frame (`windows.py:499`):
   - glaze pool rebuild — O(n) per frame, 90 frames. Tolerable.
   - `_find_openings` (`windows.py:378`) — caps sorted by `perp` (position
     along the run axis u); the pair loop breaks only when the opening width
     exceeds `WINDOW_MAX_WIDTH_PX` (280 px). That is a **1-D window on u,
     unbounded along v** (the cap direction): every cap within a 280 px slab
     pairs with every other, even ones metres apart along v. This is the
     quadratic core: ~C²·(280/sheet extent) candidate pairs per frame.
   - `_spanning_glazing` (`windows.py:361`) — called per surviving pair,
     scans the **entire glaze pool** → O(pairs·G). Dominant term.
   - `_band_interior_clutter` (`windows.py:430`) — per accepted opening,
     scans all paths + all line records → O(openings·n).

cProfile on 2682241's filtered 50,995 paths (77.6 s under the profiler vs
84.1 s plain — consistent; 28 raw windows found, 65.6M function calls):

| function | ncalls | tottime | cumtime | share |
|---|---|---|---|---|
| `_spanning_glazing` (windows.py:361) | 308,743 | **68.5 s** | 68.8 s | **88%** |
| `_find_openings` (windows.py:378) | 90 | 3.1 s | 74.8 s | 4% |
| `min`/`max` builtins (pair gates) | 47M | 2.2 s | — | 3% |
| `_interval_overlap` | 5.27M | 1.0 s | 1.7 s | 1% |
| `_angle_diff_mod180` (frame builds) | 4.70M | 0.6 s | 1.0 s | <1% |
| `_band_interior_clutter` | 143 | 0.9 s | 0.9 s | 1% |
| `_block_cap_records` + `crossed` | 1 | — | 0.008 s | ~0 |

Takeaways: 308,743 cap pairs survive the cheap gates and each pays a
full-pool `_spanning_glazing` scan — that one list comprehension is 88% of
the stage. The pair enumeration itself (5.3M `_interval_overlap` calls and
the min/max churn around them) is the ~5 s that remains once the scan is
indexed. `_band_interior_clutter` and `crossed()` are noise on this sheet
(143 and 1 calls) — touch them only if they surface in the *post-fix*
profile of 1789452.

## Optimization plan (pruning-only, output-identical)

Each item removes work that the existing gates provably reject anyway. None
changes a threshold or a comparison. Ordered by measured payoff:

1. **Index the glaze pool by perp for `_spanning_glazing`** — kills the 88%.
   The first filter is `ext_lo ≤ g.perp ≤ ext_hi` where the extent window is
   the caps' spans ± 2 px (≤ ~40 px). Sort the pool by perp once per frame
   and `bisect` the window instead of scanning all G records for each of the
   308k pairs. Caveat: `spanning` currently inherits *pool order*, and
   `_dedupe_by_perp`/`_tight_band` re-sort with stable `sorted()` — exact
   float ties in `(perp, -len)` would resolve by input order, so a
   perp-sorted input can only differ on exact ties. The byte-identical gate
   below decides whether that ever bites (verify, don't assume). Note
   `_merge_mullion_chains` APPENDS merged chains to the pool after the plain
   records (`windows.py:318`) — keep whatever index you build downstream of
   that append.
2. **Bucket caps by their v-extent in `_find_openings`** — kills the
   residual ~5 s of pair enumeration. The facing gate (`windows.py:399-400`)
   requires `_interval_overlap(c1.span, c2.span) ≥ 0.60 · min(len)` with min
   cap length ≥ 3 px, so real partners' spans *intersect* — and caps are
   ≤ 36 px long, so partners sit within ≤ 36 px along v. Bucket caps into
   v-bins of ≥ 40 px (bin ≥ max span, so any intersecting pair shares a bin
   or sits in adjacent bins); enumerate candidate pairs from same+adjacent
   bins only, dedupe, then **evaluate the surviving pairs in the exact
   (i, j) order of the current perp-sorted double loop** so `openings` — and
   therefore candidate numbering and NMS input order — stay byte-identical.
3. **Spatial grid for `_band_interior_clutter`** — only if the post-1+2
   profile of 1789452 still shows it (143 calls / 0.9 s on 2682241). One
   coarse grid of path bboxes per page; per opening, test only primitives
   whose bbox intersects the oriented band's axis-aligned bbox (bbox
   intersection is necessary for any point to lie inside the oriented rect,
   so the surviving set is identical).
4. **Prefilter `crossed()` in `_block_cap_records`** — same condition:
   measured at 0.008 s on 2682241, so almost certainly skip. Cross strokes
   must be ≥ `0.75 · diag`, diag ≤ hypot(36, 8) ≈ 37 px, both endpoints
   inside the block bbox ± 1 px.

Expected end state: windows stage seconds, not minutes, on 1789452's 127k
paths (*estimated* from removing the pairs·G term; re-measure, don't trust
the estimate).

## Verification gates (all must pass, in this order)

1. `python -m unittest discover tests` — 420 tests green. Window ground
   truths live in `tests/test_window_detection.py`
   (`TestWindow51133Topology`, `TestFloorPlansRegression` — they run the real
   reference PDFs).
2. **Byte-identical `detect_windows` output** on: `5-1133-WD03.pdf` p1 and
   `floor-plans.pdf` p1 (whole page), plus the filtered giants 2682241 and
   1789452 (recipes below). Dump full candidates (id, bbox, confidence, the
   whole evidence dict) in returned order — candidate order IS part of the
   contract (`window_NNNN` numbering, NMS input order).
3. **Byte-identical `candidates.json` + `final_entities.json`** from a full
   `app.py extract --no-gemini` run on the two reference PDFs. Project
   convention (see memory / prior branches): detection regressions gate on
   the two reference PDFs ONLY — plans/ comparisons are informative, never
   the gate.
4. Re-measure stage timings on 2682241 + 1789452 and record before/after in
   the commit message. Numbers are measured, never estimated
   ([[verify-before-asserting]]).

## Reproduction recipes (self-contained — scratchpad scripts die with the session)

Stage timing on a filtered giant (same harness used for the baseline numbers):

```python
# time_windows.py — run from the repo root with .venv/bin/python
import glob, json, logging, sys, time
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
import fitz
from extraction.extractor import extract_page
from layout.filter import filter_page_data
from models import Region
from detection import run_heuristics

PDF = "plans/REV_._PROPOSED_PLANS_AND_ELEVATIONS-1789452.pdf"  # or 2682241
floor_plans = []
for f in sorted(glob.glob("plans/.regions_cache/*1789452*")):
    fp = [Region(**r) for r in json.load(open(f))["regions"]
          if r["region_type"] == "floor_plan"]
    if fp:                      # parse-failed entries cache as all-unclassified
        floor_plans = fp        # — never pick those (2682241 has one)
doc = fitz.open(PDF)
pd = extract_page(doc, 0)
filtered = filter_page_data(pd, floor_plans)
print(len(filtered.paths), "paths")
t0 = time.monotonic()
run_heuristics(filtered, plumber_tables=[])
print(f"total {time.monotonic()-t0:.1f}s")   # stage lines appear via logging
```

Byte-identical windows dump (run before AND after, diff the files):

```python
# dump_windows.py <out.json> — same page loading as above, then:
from detection.windows import detect_windows
wins = detect_windows(filtered.paths)
json.dump([{ "id": c.candidate_id, "bbox": c.bbox,
             "confidence": c.confidence, "evidence": c.evidence }
           for c in wins], open(sys.argv[1], "w"), indent=1, sort_keys=True)
```

For the two reference PDFs, load whole-page (`extract_page` only, no
filtering). cProfile: wrap the `detect_windows` call in
`cProfile.Profile()`; sort by `tottime` and `cumulative`, top 25.

## Constraints and gotchas

- **Region cache**: entries live in `plans/.regions_cache/`, keyed
  `<content-hash>-<geometry-hash>`; several geometries per sheet coexist
  (pre-clip-fix, pre-fold, post-fold). A Gemini parse failure is cached as
  all-`unclassified` (2682241's `…-f2b9314d4207b160` entry, 2026-08-05) —
  always select entries by checking for `floor_plan` regions, and know that
  such an entry makes the real pipeline skip detection for the sheet until
  `--refresh-regions`.
- `detect_windows` takes only `paths` — no text, no network — so it can be
  tested in isolation exactly as the recipes do.
- `_dedupe_openings` and the final re-numbering (`windows.py:577-582`) make
  candidate ids order-sensitive; preserve emission order through any pruning.
- Windows on doors are suppressed later (`postprocess`), not here — do not
  "help" by pre-filtering.
- Workflow conventions for this repo: run `graphify query` before reading
  source, `graphify update .` after changing it; TDD (superpowers skill) for
  any new helper — an equivalence test for the bucketing (bucketed pair set ==
  brute-force pair set on synthetic dense data) is the natural RED test;
  work on a new branch; never add a Co-Authored-By trailer.
- `--disable-windows` is the user-facing workaround until this lands.
