# Floor-plan region filtering

**Date:** 2026-07-28
**Status:** design agreed, not yet implemented

## Problem

Sheets in `plans/` routinely carry a location plan, a block plan, a site plan,
elevations, a roof plan, notes and title blocks alongside the floor plans. Every
detector in `detection/` sees all of that ink. Several of the detectors depend on
page-global statistics — `wall_stroke_reference` (the length-weighted median pen
of paired wall faces), the lattice/hatch demotion scan, and the
`ROOM_WALL_PEN_MIN_FRAC` pen-colour gate — so elevation cladding stripes, roof
joists and title-block rules distort the thresholds the real floor plan is
measured against.

Separately, the existing Gemini stage asks the model to validate each heuristic
candidate individually. That is spatial grounding on small symbols, which vision
models do poorly, and it has not been useful in practice; `--no-gemini` is the
normal way this tool is run.

## Approach

Repoint Gemini from "judge 200 small symbols" to "say what these drawings are" —
a plain classification question it answers reliably. Geometry stays deterministic:
region boundaries come from the vector ink, which already has exact coordinates,
so the model is never asked for a bounding box.

```
1  extract      PageData (all ink, 150-DPI px)
2  render       render.png
─────────────────────────────────────────────────────
2a SEGMENT      ink map → recursive whitespace cut     (deterministic, no API)
                  + qualifying clip rects as cut lines
2b CLASSIFY     one crop per region → one Gemini call → a type per region
2c FILTER       union of the floor_plan regions
─────────────────────────────────────────────────────
3  plumber
4  heuristics   ONE pass over the union
5  ─── deleted (per-candidate validation) ───
6  overlay + 7  save (+ regions.json)
```

Detection runs **once, over the union** of the kept regions — not once per region.
See "Rejected alternatives".

Regions decide *which primitives detection sees*. Nothing is cropped or
translated: all coordinates stay in page space, so `final_entities.json`, the
overlay and the rest of the `outputs/` contract are unchanged.

## Evidence

All figures measured on 2026-07-28 against the files in `plans/` plus the two
reference PDFs.

**Segmentation quality** (recursive whitespace cut, 20px gutter):

| Sheet | Regions | Outcome |
|---|---|---|
| `floor-plans.pdf` | 2 | both floor plans, cleanly split |
| `EXISTING_AND_PROPOSED_ELEVATIONS_AND_FLOOR_PLANS-2557737` | 10 | all 3 floor plans isolated |
| `LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241` | 13 | both floor plans isolated |
| `PROPOSED_FLOOR_AND_ELEVATIONS-1326086` | 3 | 3 elevations, no floor plan present |
| `5-1133-WD03.pdf` | 1 | no gutters; whole-page fallback |

Path coverage: **100%** on `floor-plans.pdf`, **99.1%** on `5-1133` (the 77
unassigned paths sit at x≈2495 on a 2480px-wide page — off the sheet edge).

**Gutter threshold is not sensitive.** 12px, 20px and 28px produce byte-identical
splits on every sheet tested. 40px vs 80px differ only on the largest A1 sheets.

**Dropping page-spanning primitives is load-bearing.** A single border rule
spanning the sheet makes every gutter impossible: `2682241` found **0** regions
before the filter and 12 after.

**Classification accuracy.** A full sweep over all 20 pages (18 files in `plans/`
plus both reference PDFs) completed with 0 malformed responses and 0 missing
region ids, costing 44,437 input / 6,230 output tokens in total — about 2.2k
input tokens per page.

58 regions across 9 of those files were scored by inspection: **zero floor plans
missed, zero false floor plans.** `2682241` scored 13/13 despite having zero
extractable text (outlined to curves) and being rotated 90°; `2710870` scored
14/14. The only calls I could not confirm were two narrow strips on `1789452`
(elevation vs section) — neither is a floor plan, so the filtering outcome is
unaffected.

Two **true negatives** were confirmed by inspection: `PROPOSED_FLOOR_AND_ELEVATIONS-1326086`
and `EXISTING_FLOOR_AND_ELEVATIONS-1326087` contain only elevations despite their
filenames. Both are single-page. These pages currently produce phantom doors and
rooms from elevation linework; under rule 1 they are skipped.

**Coverage is narrower than the headline accuracy suggests:**

| Outcome | Pages | Effect |
|---|---|---|
| Split into ≥2 regions | 11/20 | filtering applies |
| Whole-page fallback (no gutters) | 7/20 | no filtering; behaves as today |
| Raster scan, no vector ink | 2/20 | out of scope for a vector-first pipeline |

Of the 11 that split, 2 are entirely floor plans (`floor-plans.pdf`, `3228943` —
nothing to filter), 2 are entirely elevations (correctly skipped), and **7 get
real noise removal**. Of the 7 that fall back to whole-page, at least three
(`EXISTING_FLOOR_AND_ELEVATION_PLAN-3055574`,
`PROPOSED_FLOOR_PLANS_AND_ELEVATIONS-3228948`,
`REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461`) do contain elevations and would
benefit if they split — the gutters between their drawings are below 20px. This
is the main opportunity for a follow-up, and the reason the gutter threshold
should stay a named constant.

**Native PDF grouping is not usable as a primary signal.** Only 7 of 20 files
carry ≥2 drawing-sized clip rects. Where present they are accurate (`2557737`'s
clips matched the whitespace cut almost exactly), but both reference PDFs have
none, and on `5-1133` all 4,202 clips are text and annotation masks. Clips are
therefore used only as an additional cut hint, gated on ink content.

## Component: `layout/segmenter.py`

Pure geometry, no API, no I/O. Testable offline.

```
1  build a 4px-bin occupancy map from path polylines + text-span boxes
2  drop primitives spanning > SEGMENT_SPAN_FRAC of page width or height
3  collect qualifying clip rects from get_drawings(extended=True)
4  recursive cut; at each step cut at whichever is wider:
     (a) the widest fully-empty band >= SEGMENT_MIN_GUTTER_PX, or
     (b) a qualifying clip-rect edge that separates ink
   stop at SEGMENT_MAX_DEPTH or when neither exists
5  drop regions below SEGMENT_MIN_REGION_SIDE_PX on either side
6  merge caption strips into their drawing
7  assign each primitive to the region containing its bbox centre
```

Clips are cut *hints*, not regions. Qualifying clips overlap and nest each other
(five of them do on `REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461`); feeding them
as cut candidates preserves the invariant that the output is a partition — every
primitive belongs to exactly one region.

A **caption** is a region with zero vector paths, height ≤ `CAPTION_MAX_H_PX`,
horizontally overlapping a drawing region by ≥ 50% of its width, within
`CAPTION_MAX_GAP_PX` vertically. It merges into the nearest such region. This
matters because drawing titles otherwise split off as their own regions — on
`floor-plans.pdf` at 20px, "PROPOSED GROUND FLOOR PLAN" and "PROPOSED FIRST FLOOR
PLAN" each became a separate zero-path region. A tall multi-line text block (the
notes paragraph on `2557737`, 568×284px) is not a caption and stays separate.

### Constants

| Constant | Value | Rationale |
|---|---|---|
| `SEGMENT_BIN_PX` | 4 | occupancy resolution; fine enough for a 20px gutter |
| `SEGMENT_MIN_GUTTER_PX` | 20 | measured insensitive across 12–28px |
| `SEGMENT_SPAN_FRAC` | 0.90 | border rules span the sheet; drawings never do |
| `SEGMENT_MAX_DEPTH` | 6 | backstop against pathological recursion |
| `SEGMENT_MIN_REGION_SIDE_PX` | 60 | below this a region cannot be a drawing |
| `CAPTION_MAX_H_PX` | 64 | measured captions 28px; notes blocks 284px |
| `CAPTION_MAX_GAP_PX` | 64 | measured caption gaps 44–48px |
| `CLIP_MIN_INK_FRAC` | 0.05 | text/annot clips 0.0–1.3%; drawing clips 5.7–62.4% |
| `CLIP_MAX_PAGE_FRAC` | 0.80 | whole-sheet clips measure 88–97% |

## Component: `gemini/classifier.py`

One call per page. Each region is rendered as its own PNG crop scaled so its long
edge is ~`CROP_TARGET_LONG_EDGE_PX` (1536), capped at `CROP_MAX_ZOOM` (10×) so a
tiny region is not blown up absurdly. Crops are sent in order, each preceded by a
text part giving its region number, its size on the sheet, and any text found
inside it.

Crops rather than one full-page image: Google's docs state images are "cropped and
scaled into 768×768 pixel tiles", and these sheets are A1 (3508×4967px at 150
DPI), so a whole-sheet image loses fine detail. A 1536px crop is 2×2 tiles
(~1,000 tokens). The per-request limit is 3,600 images, so region count is never a
constraint.

**Taxonomy** (exactly one per region): `floor_plan`, `elevation`, `section`,
`location_plan`, `block_plan`, `site_plan`, `roof_plan`, `schedule_table`,
`legend`, `title_block`, `detail`, `other`.

**Response** (`response_mime_type="application/json"`, temperature 0):

```json
{"regions": [
  {"id": 0, "type": "floor_plan", "title": "PROPOSED GROUND FLOOR PLAN",
   "confidence": 1.0, "contains_multiple": false, "notes": ""}
]}
```

`contains_multiple` records an imperfect split (both merged elevation strips on
`2557737` were correctly flagged). It is informational — it does not change
behaviour, because a region holding two floor plans is handled correctly by the
union pass anyway.

## Filtering rules

- `floor_plan` regions → their primitives form the union that feeds
  `run_heuristics`.
- `schedule_table` regions → scope the pdfplumber tables passed to
  `detect_schedules`.
- Everything else is recorded in `regions.json` and dropped.

Four behaviours decide the edge cases:

1. **Page split into ≥2 regions, no `floor_plan` found** → skip detection for the
   page, emit `NO_FLOOR_PLAN_REGION`. Verified correct on `1326086` and `1326087`.
2. **Page did not split (one whole-page region)** → classify it for the record,
   but run detection regardless of the answer. Guarantees never-worse-than-today
   on dense sheets such as `5-1133`. Applies to 7/20 pages.
3. **Page has no vector ink** (`page_type == "raster-heavy"`, zero paths) →
   segmentation and classification are both skipped entirely; emit
   `RASTER_PAGE_NO_VECTOR_INK` and let the pipeline behave as it does today. This
   is not a segmentation failure: `FLOOR_PLAN_-_EXISTING-3565362` and
   `SECOND_FLOOR_PLAN_ROOF_-_EXISTING-3565363` are scanned images (0 paths, 0 text
   spans, one full-page image), so there is nothing for a vector-first pipeline to
   segment or detect. Checking this *before* calling Gemini avoids 2 wasted calls
   per sweep and stops a raster page being reported as a classification miss.
4. **`--no-gemini`** → read the cached classification; if there is no cache, do no
   filtering. `--refresh-regions` forces a re-call.

## Caching

Gemini's classification is written to `regions.json` and cached under the PDF,
keyed on page content hash. One real call per page, ever. This exists because
`--no-gemini` is the normal way this tool is run, and without a cache that flag
would silently disable the entire feature.

## Data model and outputs

New `Region` dataclass in `models.py`:

```python
@dataclass
class Region:
    region_id: str          # "region_0000"
    bbox: BBox              # 150-DPI px, page space
    region_type: str        # taxonomy value, or "unclassified"
    title: Optional[str]
    confidence: float
    contains_multiple: bool
    path_count: int
    source: Literal["whitespace", "whitespace+clip", "page-fallback"]
```

New per-page artefact `regions.json`. `overlay.png` gains region outlines
labelled with their type. `summary.json` gains region counts per page. No existing
output changes shape.

## Deletions

From `gemini/client.py`: `SYSTEM_PROMPT`, `REQUIRED_KEYS`, `build_user_message`,
`_candidate_to_dict`, `_validate_response`, `call_gemini`.

From `pipeline.py`: the Gemini branch of `merge_gemini_and_heuristics`, including
the `0.5*heuristic + 0.5*gemini` blend and the Gemini-rejected-ID path. The
function collapses to applying `OFFLINE_MIN_CONFIDENCE` unconditionally — which is
today's `--no-gemini` behaviour, and what all existing tuning was measured
against.

Warning codes `GEMINI_SCHEMA_MISMATCH`, `GEMINI_UNKNOWN_CANDIDATE_ID` and
`GEMINI_PARSE_FAILURE` are removed. The classifier emits, in their place:

| Code | Severity | When |
|---|---|---|
| `NO_FLOOR_PLAN_REGION` | warning | page split into ≥2 regions, none classified `floor_plan` |
| `RASTER_PAGE_NO_VECTOR_INK` | info | page has no vector paths; segmentation and classification skipped |
| `REGION_CLASSIFY_PARSE_FAILURE` | error | response was not valid JSON; page falls back to no filtering |
| `REGION_CLASSIFY_INCOMPLETE` | warning | a region id was missing from the response; that region is treated as `unclassified` and excluded |
| `REGION_CACHE_MISS_OFFLINE` | warning | `--no-gemini` with no cached `regions.json`; no filtering applied |

## Testing

**Segmenter** — pure geometry, no API. Golden region counts and floor-plan
identification on `floor-plans.pdf` (2 regions), `2557737` (10 regions, 3 floor
plans), `5-1133` (1 fallback region), and the span-line filter on `2682241` (0
regions without it, 12 with).

**Classifier** — tested against a recorded fixture response, not a live call.

**Regression gate** — before/after `final_entities.json` on the two reference
PDFs. `floor-plans.pdf` must be byte-identical: the union of its regions is all
3,764 paths, and a union pass was verified to reproduce the baseline exactly (13
rooms, all areas matching; doors 12; windows 4). `5-1133` must be identical except
for any effect of the 77 off-page paths, which must be checked rather than
assumed.

## Rejected alternatives

**Per-region detection** (one `run_heuristics` pass per floor-plan region) was the
original design and is wrong. Measured on `floor-plans.pdf`: 13 rooms /
478,923px² baseline vs 14 rooms / 446,261px² per-region. The kitchen units were
carved out of the DINING/SITTING+KITCHEN room (148,895 → 118,073px²) and
UTILITY/STORE spuriously split in two. Cause: `ROOM_WALL_PEN_MIN_FRAC` (0.15)
makes a pen a wall pen when it covers 15% of the network's paired-face length;
splitting the sheet shrinks that denominator until the red furniture pen clears
it and its pairs gain barrier rights. Every page-global statistic has the same
sensitivity. Noise removal is the goal; splitting plans apart is not.

**Gemini-supplied bounding boxes.** Rejected because vector ink already has exact
coordinates and spatial grounding is the weakest part of what vision models do.

**Native clip rects as the primary signal.** Rejected: absent on 13 of 20 files
including both reference PDFs.

**Full-page image instead of crops.** Rejected: these are A1 sheets; tiling costs
detail the crops keep.

## Risks and open questions

- **A missed floor plan silently skips a page.** Rule 1 makes this loud
  (`NO_FLOOR_PLAN_REGION`) but not recoverable. The full sweep found zero missed
  floor plans across 58 scored regions, and both zero-floor-plan pages were
  confirmed true negatives. This is the failure mode to watch as new drawing
  producers appear.
- **Under-splitting is the main limitation, not misclassification.** 7 of 20 pages
  produce a single whole-page region and get no filtering at all, and at least
  three of those do contain elevations that should have been excluded. Lowering
  `SEGMENT_MIN_GUTTER_PX` does not fix it — 12px was measured to give identical
  splits. A follow-up would need a different mechanism (projection-profile cuts
  at a lower ink threshold, or clip rects on the files that have them).
- **The 77 off-page paths on `5-1133`** are excluded by region assignment. Their
  effect on `wall_stroke_reference` must be measured, not assumed.
- **Rotated sheets.** `2682241` is rotated 90° and classified correctly, but the
  caption-merge rule assumes captions sit above or below their drawing. Sideways
  captions will not merge; this costs a text hint, not a region.

## Non-goals

- **Splitting tightly-packed sheets.** The 7 pages that produce a single
  whole-page region are explicitly out of scope for this spec (decided
  2026-07-28). They degrade to today's behaviour, so nothing regresses. Revisit
  after this ships and the output has been seen on real runs.
- Cross-page reasoning (matching an existing plan to its proposed counterpart).
- Using region type for anything beyond filtering — no per-type detection tuning.
- Re-splitting a region flagged `contains_multiple`.
- Curved-wall support, or any change to detection behaviour itself.
