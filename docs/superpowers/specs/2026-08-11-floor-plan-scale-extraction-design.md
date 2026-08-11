# Floor Plan Scale Extraction — Design

**Date:** 2026-08-11
**Status:** Approved, not yet implemented

## Problem

Every entity the pipeline emits is measured in 150-DPI pixels. Nothing in the
codebase knows how many millimetres a pixel is worth, so no output can be stated
in real-world units — a door is `28.2pt wide`, never `838mm wide`.

The drawing itself always knows. The question is where it keeps that knowledge,
and the answer differs sheet to sheet. Four situations have to be covered:

1. One floor plan, one scale.
2. Several floor plans, all at the same scale.
3. Several floor plans at *different* scales — the scale must bind to the
   individual plan, not the sheet.
4. No scale recoverable from the document at all — the user has to supply it.

**Goal:** resolve a scale per floor plan and print it. Nothing consumes the
value yet; this release only reads and displays. The storage design, however, is
chosen so that a later unattended run (`regress.py`, an AI rerun) can reuse a
scale the user typed once.

## Evidence

Everything below was measured on the 20-sheet regression corpus on 2026-08-11.
No figure here is estimated.

### `/VP` → `/Measure` carries the scale on half the corpus

CAD exporters write a PDF viewport measurement dictionary (ISO 32000-1 §12.9) so
a reader's measure tool can report real lengths. It looks like this, from s03:

```
/VP [ << /BBox [137 270 1492 891]
         /Measure << /Subtype /RL
                     /X [ << /C 35.27546 /U ( ) >> ]
```

`/C` is real-world units per PDF point. Since 1 pt = 25.4/72 = 0.352778 mm:

```
denominator = C / 0.352778
```

Confirmed against printed text on the same sheets — this is not inferred:

| Sheet | `/C` | `C / 0.352778` | Printed text | |
|---|---|---|---|---|
| s17 plan | 35.27288 | 99.99 | `SCALE 1:100` | agrees |
| s17 plan | 17.63849 | 50.00 | `SCALE 1:50` | agrees |
| s03 plan | 35.27546 | 100.0 | `SCALE 1:100` | agrees |
| s06 inner | 35.13904 | 99.6 | `SCALE 1:100` | agrees |
| s03 inset | 176.35 | 499.9 | — | 1:500, standard OS |
| s17 inset | 440.67 | 1249.1 | — | 1:1250, standard OS |

`/U` is a blank string on every corpus sheet, so the unit is unlabelled. What
pins it to millimetres is the paper-space viewport reading `C = 0.35278`, which
is exactly 1 mm/pt. That holds on all 10 viewport-bearing sheets.

The method was independently validated through detection geometry: s03 is
verified 1:100 by both sources, and at that scale its detected door swing bboxes
measure 838, 838, 786, 756, 902, 906, 931 mm — standard UK leaf widths.

### Two structural rules the raw data forces

**Paper-space viewports must be excluded.** s03, s04, s08 and s17 each carry a
viewport at `1:1` spanning the whole sheet. It is the paper, not a drawing.

**Viewports nest, and the innermost governs.** s06 carries two:

```
BBox [30  50 1159 791]  C=51.51447  → 1:146.0    (outer)
BBox [30 172 1023 790]  C=35.13904  → 1:99.6     (inner)
```

The inner value is the one matching the sheet's own `SCALE 1:100`. An earlier
regex-based parse of this spec's research crossed `/C` from one viewport with
`/BBox` from another and produced a phantom mismatch on s06. Any implementation
must parse the `/VP` array structurally. Note that `xref_get_key(xref, "VP[0]")`
returns null in PyMuPDF — only the whole `VP` array comes back, as a string, so
it needs a bracket-aware split.

### The `/VP` bbox is y-up, unlike everything else in the pipeline

`xref_get_key` returns the raw PDF object, so `/BBox` is in PDF native
coordinates: **y-up, origin bottom-left**. Every other coordinate in this
codebase is PyMuPDF's y-down, top-left. The conversion is:

```python
x_mu = x_pdf - mediabox.x0
y_mu = mediabox.y1 - y_pdf      # note the flip, and that y0/y1 swap
```

and only then does `page_transform` apply.

This was verified by rendering both interpretations and looking at them. On
s17 the `1:1250` viewport `[2100 1267 2296 1519]` renders as the **title block**
if taken as-is, and as the **OS location plan** — red site outline, north arrow —
when flipped. s03's `1:500` viewport `[802 1037 1518 1448]` behaves identically.

Do not try to verify this by testing whether a `SCALE 1:N` caption falls inside
its viewport. Captions are drawn in paper space *beneath* the plan, outside the
model viewport — s03's `SCALE 1:50` caption sits 60px below its own (correctly
flipped) box. That test scores the wrong hypothesis higher on four of the five
captioned sheets, because their viewports are large and nearly symmetric about
the page's horizontal midline.

### Text is the fallback, with two traps

Three sheets carry no viewport but state a scale in text: s02 (`1:50@A3`), s14
(`1:50@A1`), s20 (`Scale:` + `1:50  & 1:100`).

- **Negations must not match.** s14 contains `PLEASE DO NOT SCALE FROM THIS
  DRAWING` and s15 contains `DO NOT SCALE THIS DRAWING`. Matching on the word
  "scale" is wrong; only a `1:N` pattern may produce a value.
- **Values split across spans.** s03 and s20 put `Scale:` in one span and the
  value in another. **Joining them is NOT implemented, deliberately** — on
  every corpus sheet the *value* span already carries the `1:N` itself
  (s20's is `1:50  & 1:100`), so a join finds nothing a plain per-span scan
  misses, and s03's `Scale:` pairs with `As Shown @ A1`, which states no ratio
  at all. Reinstate only when a sheet appears whose value span lacks the ratio.

### Seven sheets have nothing to parse

s01, s09, s10, s11, s16, s18 and s19 carry no viewport. Six of them return **zero
text spans** — the text is outlined to curves.

This is not the same as having no scale. s09's title block plainly reads
`SCALE 1:100` and `A3`, and a graduated scale bar (`0 · 1 metre · … · 5 metre`)
sits under the plan. None of it reaches `get_text()`. These sheets are the case
for a future vision tier; until then they fall to the user prompt.

### Measured coverage

| Resolution | Sheets | |
|---|---|---|
| Viewport | 10 | s03, s04, s05, s06, s07, s08, s12, s13, s15, s17 |
| Text | 3 | s02, s14, s20 |
| Unresolved | 7 | s01, s09, s10, s11, s16, s18, s19 |

Exactly one sheet produces a source conflict: **s13** reads 1:136.4 from its
inner viewport while its text says `SCALE 1:100`, and its room geometry is the
same magnitude as s06's 1:100 plans. It is flagged, not silently resolved.

## Constraints

1. **Nothing may block an unattended run.** `batch_extract.py` runs five sheets
   in parallel and `tools/regress.py` sweeps 20 sheets unattended. Neither is
   safely identified by `isatty()`: the sweep calls `run_extract` in-process,
   and the batch children inherit the parent's stdin. An explicit flag carries
   the guarantee; see Tier 4.
2. **A user-typed scale must survive a fresh clone.** `.regions_cache/` sits
   next to the PDF and is gitignored, and `fixtures/*` is gitignored except
   `MANIFEST.json`, so a cache-next-to-the-PDF loses everything on clone.
3. **No addresses, per the corpus rule.** Anything committed is keyed by slug,
   never by filename — PDF stems in this corpus contain property addresses.
4. **The fast unit tier stays fast.** New tests must not require a PDF.

## Non-goals

- **No consumption of the value.** Nothing converts pixels to millimetres yet.
  The scale is detected, displayed, and stored. That is the whole release.
- **No vision tier.** Reading an outlined-to-curves title block or a scale bar
  via Gemini is deferred, behind the same resolver interface.
- **No scale-bar measurement.** The bar's tick labels are outlined curves on
  precisely the sheets that would need it, so this belongs with the vision tier.
- **No `--scale` CLI flag.** The prompt plus the store means a scale is typed
  once, not passed on every invocation.
- **No paper-size inference.** `@A3` / `@A1` suffixes are captured verbatim in
  `raw` but not interpreted.

## Architecture

### Module layout

A new `scale/` package, following the `detection/` · `layout/` · `gemini/`
convention of the repo:

```
scale/
  viewport.py   # tier 1 — parse /VP -> /Measure
  text.py       # tier 2 — parse scale text spans
  store.py      # tier 4 — persistence (ground truth + local cache)
  prompt.py     # tier 4 — interactive prompt, tty-gated
  resolver.py   # the ladder + region binding
```

A future `scale/vision.py` returns the same type and slots into the ladder
without touching callers.

### Data model

`ScaleInfo` joins the other shared dataclasses in `models.py`:

```python
@dataclass
class ScaleInfo:
    denominator: Optional[float]   # 100.0 means 1:100
    source: Literal["viewport", "text", "user", "unresolved"]
    bbox: Optional[BBox]           # 150-DPI px, page space — extent of the evidence
    raw: Optional[str]             # "1:50@A3", or "C=35.27546"
    nominal: Optional[float]       # nearest standard scale, if within 2%
    conflict: Optional[str]        # set when two tiers disagree
```

`nominal` snaps against {1, 20, 25, 50, 100, 200, 500, 1000, 1250, 2500} within
2%. s06's 99.6 snaps to 100; s13's 136.4 snaps to nothing and stays raw.

A page's result is a `PageScales` record: `by_region: dict[str, ScaleInfo]`
keyed by `region_id`, `page_scale: Optional[ScaleInfo]` for the unbound case,
and `warnings: list[dict]`. `region_id` keys the in-memory result only — it is
never persisted, for the reason given under Tier 4. `page_scale` is `None`
whenever the sheet states more than one scale, and serialises to `summary.json`
under `page_scale`.

### Tier 1 — viewport

1. Read `doc.xref_get_key(page.xref, "VP")`; if it is not an array, no result.
2. Split the array string into top-level `<< >>` chunks with a bracket-aware
   scanner. Regex alone is not safe here (see Evidence).
3. Per chunk, require `/Subtype /RL`; take `/BBox` and `/Measure/X[0]/C`.
4. `denominator = C / (25.4/72)`. Drop anything below 1.5 as paper space.
5. Flip `/BBox` about the mediabox, *then* transform through
   `extraction.extractor.page_transform`. See "The `/VP` bbox is y-up" below —
   getting this backwards silently mis-binds every scale.
6. Sort ascending by area, so a containment lookup returns the innermost match.

### Tier 2 — text

Scan `page_data.text_spans` for `\b1\s*:\s*(\d{1,4}(?:\.\d+)?)\b`, optionally
followed by `@\s*A[0-4]`. Never match on the bare word "scale". Three rules:

- **Colon separator only, never a slash.** `1/5/2024` would otherwise read as
  1:5, and every scale on every corpus sheet is written with a colon.
- **A decimal denominator is accepted.** No sheet prints one, but this is the
  same grammar the store parses a user-typed scale back with, and the prompt
  accepts decimals so a measured value like 1:136.4 can be recorded. An
  integer-only pattern would silently reload that as 1:136.
- **Split `Scale:` / value spans are not joined** — see the Evidence section
  for why no corpus sheet needs it.

Each result keeps its own span bbox, which is what binds `SCALE 1:100` sitting
beneath a plan to that plan.

### Tier 4 — prompt and store

Interactive `app.py extract` prompts once per unresolved `floor_plan` region,
printing that region's crop path so the user can look before answering. The crop
is **rendered on demand** — `region_crops/` is written only by the Gemini
classification call, so on a cache hit, with `--no-gemini`, or on a raster page
it does not exist.

Prompting is controlled by **two** gates, and both are needed:

1. `run_extract(..., allow_scale_prompt=True)`, surfaced as `--no-scale-prompt`.
   `regression/sweep.py` and `batch_extract.py` set it off.
2. `sys.stdin.isatty()`, as defence in depth.

The tty check alone does **not** hold. `regress.py` calls `run_extract`
*in-process*, so a sweep started from a terminal has a real stdin; and
`batch_extract.py` spawns `app.py extract` with `Popen(stdout=PIPE,
stderr=PIPE)` without redirecting stdin, so its five parallel children inherit
the terminal too. Seven of the twenty corpus sheets resolve no scale, so a sweep
would stop for input on the common path, not an edge case. `batch_extract` also
passes `stdin=subprocess.DEVNULL` so a future prompt that escapes the flag
still cannot hang it.

A suppressed prompt records `source="unresolved"` and emits `SCALE_UNRESOLVED`.

Persistence mirrors the split the repo already uses for verdicts versus caches:

- **Corpus sheet** → a `"scales"` block in `tests/ground_truth/<slug>.json`.
  Committed, diffable, slug-keyed so no address is ever written, and
  `regress.py` already loads these files.
- **Any other PDF** → `.scale_cache/<stem>_pNN.json` beside it, gitignored,
  mirroring `.regions_cache/`.

Both stores are consulted *before* prompting, so a given scale is typed once.

Entries are keyed by the region's **bbox, never its `region_id`**, and matched
at IoU ≥ 0.5. Region ids are ordinal — `layout/segmenter.py` numbers them over
a sorted box list — so any change to segmentation renumbers them, and a stored
value sits at the top of the ladder, meaning a mis-attached one would *override*
a correct viewport reading rather than merely be ignored. `tests/ground_truth/`
already matches detections geometrically for exactly this reason.

### Resolution ladder

Per `floor_plan` region, first hit wins:

1. Stored value (ground truth, then local cache)
2. Smallest viewport whose bbox contains the region centroid
3. Nearest scale text span inside the region, or immediately below it
4. The page-level scale, if exactly one candidate exists sheet-wide —
   counted after clustering near-equal denominators, since CAD writes one
   scale as many floats (s04's two 1:50 viewports measure 49.995 and 50.001,
   s17's four 1:100 plans measure 99.986 through 99.995)
5. Prompt if interactive, else unresolved

When tiers 2 and 3 both yield a value and they differ by more than 2%, **tier 2
wins** and `conflict` records the losing value. Accuracy is the requirement, and
`/Measure` describes the PDF as it actually exists rather than as it was
intended. s13 is the only corpus sheet that trips this.

### Pipeline placement

A new stage in `pipeline.run_extract`, immediately after `resolve_page_regions`
— it needs `region_type == "floor_plan"` to bind against. Its output goes into
`summary.json` per page and is printed to the console.

`inspector.py` never segments regions, so `inspect` degrades by design: it lists
every scale found on the sheet, unbound, with no prompting.

The same degradation covers `--no-gemini` with a cold region cache. Regions
collapse to whole-page, so binding collapses to the page-level scale — which
exists only when the sheet states **one** scale after clustering. A sheet
stating several has no page-level scale at all: no single number describes s17,
and publishing one to `summary.json` would be wrong for most of the sheet. Such
a run emits `SCALE_MULTIPLE_UNBOUND` instead. s20 (`1:50  & 1:100`, with nothing
marking which plan is which) hits this even with regions available.

### Warning codes

Following the existing `SCREAMING_SNAKE_CASE` convention.

These are **not** emitted from `pipeline.collect_warnings`. They are produced by
`scale.resolver.resolve_page_scales`, which returns them on `PageScales.warnings`
— it is the only code that knows which tier resolved a region, so it is the only
code that can say why one did not. `run_extract` folds them into the page's
`page_warnings` list before the summary is built, so they reach both
`warnings.json` and the per-page `warning_count` in `summary.json`. Appending
them straight to `all_warnings` would put them in the first and omit them from
the second.

This makes the resolver a fourth warning source alongside
`pipeline.collect_warnings`, `extraction.plumber.compare_counts` and
`gemini.client._validate_response`; `CLAUDE.md`'s "Warning codes" section
should be updated to say so when this ships.

| Code | Severity | Meaning |
|---|---|---|
| `SCALE_UNRESOLVED` | warning | No tier produced a value for a floor plan region |
| `SCALE_SOURCE_CONFLICT` | warning | Viewport and text disagree beyond 2% |
| `SCALE_MULTIPLE_UNBOUND` | warning | Either several sheet-level candidates with none bindable to a region, or two different scales printed near one plan |
| `SCALE_STORE_WRITE_FAILED` | warning | A scale was entered but could not be persisted — a read-only directory must not silently discard it |

### Console output

```
Page 1 — scales
  region_0002  floor_plan  1:100    viewport   (C=35.27546)
  region_0004  floor_plan  1:100    viewport   (C=35.13904)
  region_0006  elevation   1:50     viewport
  region_0009  location    1:1250   viewport   -> nearest standard 1:1250
  region_0003  floor_plan  1:136.4  viewport   CONFLICT: text nearby says 1:100
```

## Testing

**Fast tier** (`tests/test_scale_viewport.py`, `test_scale_text.py`,
`test_scale_store.py`) — synthetic, no PDF, so the unit suite stays fast:

- `/VP` array strings covering the nested case, the paper-space `1:1` case, a
  missing `/Measure`, a non-`RL` subtype, and a malformed array
- the `DO NOT SCALE` negations from s14 and s15
- split `Scale:` / `1:50` spans, and the `1:50  & 1:100` two-value case
- `page_transform` applied under `/Rotate 270`
- store round-trip for both back-ends, including read-before-prompt precedence

**Corpus tier** — a committed expectation table asserting the 10 viewport sheets
resolve to their measured denominators, the 3 text sheets to theirs, and the 7
remaining to `unresolved`. Small enough to read in a diff, and it pins the s13
conflict so a future change cannot silence it unnoticed.

## Open questions

None blocking. Two deferred by choice:

- Whether s13's true scale is 1:136.4 or 1:100 is unresolved. The design flags
  it rather than guessing; a vision tier reading its title block would settle it.
- The unit behind `/U` is inferred as millimetres from the 1 mm/pt paper-space
  viewport. Every corpus sheet is metric UK practice. A sheet in imperial units
  would need `/U` honoured properly.
