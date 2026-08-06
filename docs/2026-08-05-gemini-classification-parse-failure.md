# 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)

Task for the next agent: two fixes in the region-classification path.
Fix A makes malformed Gemini responses structurally impossible
(`response_schema` constrained decoding). Fix B makes any remaining
classification failure harmless (never cache it, fall back to unfiltered
detection). Both are small and TDD-able. Everything below is measured/observed
on this machine, 2026-08-05, branch `fix/batch-timeout-remediation`
(HEAD 96e7535).

## The incident (evidence)

Sheet `s11`
failed classification **twice in a row** — a 12:44 batch run and a 14:49
`--refresh-regions` run — while every other sheet in the same batch classified
correctly. From `outputs/2026-08-05_14-48-44/warnings.json`:

```
REGION_CLASSIFY_PARSE_FAILURE (error):
  "Region classification response was not valid JSON:
   Expecting ',' delimiter: line 10 column 6 (char 239)"
raw_response_snippet:
  {"regions": [{"id": 0, "type": "floor_plan",
   "title": "GROUND FLOOR LAYOUT", "confidence": 1.0,
   "contains_multiple": false,
   "notes": "Shows ground floor rooms, furniture, and door swings."
   immunotherapy for cancer treatment.     <-- mid-stream corruption
   "id": 1, ...
```

The response *starts* correct, then degenerates: a stray off-topic fragment
breaks the JSON and the object separator for region 1 is gone. This is
mid-stream token corruption (JSON mode does not constrain decoding), not a
prompt or crop problem — the same call succeeded on 9 other sheets minutes
earlier and s11 itself classified fine on 2026-08-04 (its two older cache
entries hold real types).

### Consequence chain (the actual bug)

What happened next is worse than the flaky response:

1. `apply_classification` (`gemini/classifier.py:139`) catches the
   `JSONDecodeError`, appends the warning, and **returns the regions
   unclassified without raising** (`classifier.py:153-162`).
2. `resolve_page_regions` (`pipeline.py:299-321`) only treats **raised**
   exceptions as failure (`REGION_CLASSIFY_FAILED` → run continues
   unfiltered, nothing cached). A non-raising parse failure walks the success
   path and **`save_regions` caches the all-`unclassified` region list**
   (`pipeline.py:315-316`), keyed by page content + region geometry.
3. All-unclassified means no `floor_plan` region → Rule 1
   (`pipeline.py:339-353`): `NO_FLOOR_PLAN_REGION`, **detection skipped
   entirely**, zero candidates (`NO_CANDIDATES`).
4. Every later run loads the poisoned entry
   (`plans/.regions_cache/s11_p01_29d82e10ad3426f6-f2b9314d4207b160.json`,
   13 regions, all `unclassified`, confidence 0.0) and skips detection again —
   until a `--refresh-regions` happens to get a parseable response.

So a parse failure is strictly worse than an outright API/auth failure:
an exception degrades to whole-page detection with no cache write; a parse
failure zeroes the sheet and persists. The 2026-08-04 findings doc's audit
line "classification failure → run continues unfiltered, no retry" is true
only for the raising path — this non-raising path was missed.

## Current implementation facts

- Model: **`gemini-2.5-flash`**, hard-coded at `gemini/classifier.py:36`
  (`MODEL`), called via Vertex AI — `google-genai` **2.2.0**,
  `genai.Client(vertexai=True, …)` in `gemini/client.py:34`.
- The call (`classifier.py:219-227`):
  `GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0,
  response_mime_type="application/json")`. **No `response_schema`** — plain
  JSON mode only. No `max_output_tokens` (defaults apply; 13 small region
  objects are nowhere near the limit, so truncation was not the cause here).
- The expected shape exists only as prose in the prompt
  (`classifier.py:78-81`): `{"regions": [{"id": <int>, "type": "<enum>",
  "title", "confidence", "contains_multiple", "notes"}]}`.
- `apply_classification` strips markdown fences (`classifier.py:151-152`),
  parses, ignores unknown ids, coerces out-of-taxonomy types to `"other"`
  with `REGION_CLASSIFY_INCOMPLETE`.
- One call per page, cache-miss only; `--refresh-regions` is the only forced
  re-call; no retry loops anywhere in `gemini/` (a deliberate boundedness
  property the user asked for — preserve it).
- Existing tests: `tests/test_region_classifier.py` (fence stripping, unknown
  ids, unaddressed regions, non-mutation), `tests/test_region_pipeline.py`
  (the five behaviour rules, cache reuse, injectable `classify_fn`).

## Fix A — constrained decoding via `response_schema`

Pass a schema in the config so Vertex constrains generation to schema-valid
JSON. With google-genai 2.2.0 the cleanest form is `types.Schema`:

```python
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["regions"],
    properties={"regions": types.Schema(
        type=types.Type.ARRAY,
        items=types.Schema(
            type=types.Type.OBJECT,
            required=["id", "type", "confidence"],
            properties={
                "id": types.Schema(type=types.Type.INTEGER),
                "type": types.Schema(type=types.Type.STRING, enum=REGION_TYPES),
                "title": types.Schema(type=types.Type.STRING, nullable=True),
                "confidence": types.Schema(type=types.Type.NUMBER),
                "contains_multiple": types.Schema(type=types.Type.BOOLEAN),
                "notes": types.Schema(type=types.Type.STRING),
            },
        ),
    )},
)
# in classify_regions:
config=types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    temperature=0.0,
    response_mime_type="application/json",
    response_schema=RESPONSE_SCHEMA,
)
```

Notes for the implementer:

- Verify the exact kwarg surface against the installed SDK
  (`.venv/bin/pip show google-genai` → 2.2.0) before trusting the snippet;
  the SDK also accepts TypedDict/pydantic models as `response_schema`.
- Keep `response.text` + `json.loads` in `apply_classification` (minimal
  change); `response.parsed` exists but switching is not required.
- The `type` enum in the schema makes the `"other"`-coercion path
  (`REGION_CLASSIFY_INCOMPLETE`) nearly dead, but leave it — it still guards
  older cached entries and any SDK/schema regression.
- Keep the prose schema in the prompt (it documents intent and helps the
  model fill sensible values) and keep the fence stripping (harmless belt).
- `apply_classification` is pure text-in → regions-out, so Fix A needs no
  changes there; the request-shape change can be covered by a test asserting
  the `GenerateContentConfig` passed to a stubbed client carries a
  `response_schema` whose `type` property enumerates `REGION_TYPES`.

## Fix B — never cache a parse-failed classification

Decision to encode: a **total parse failure** must behave exactly like the
raising failure path — warn, return the page **unfiltered**, write **no
cache entry**. A *partial* response (some regions unaddressed/coerced —
`REGION_CLASSIFY_INCOMPLETE`) is real information and should keep caching as
today.

Implementation options (pick one, prefer the first):

1. `apply_classification` returns a third value or sets a sentinel
   (e.g. returns `(regions, warnings, ok: bool)` or the warnings list is
   checked for `REGION_CLASSIFY_PARSE_FAILURE` by the caller).
   `resolve_page_regions` then mirrors its except-branch: emit the warning,
   `return unfiltered(regions)` **before** the `save_regions` call
   (`pipeline.py:315`). Checking the returned warnings for the code needs no
   signature change anywhere — `classify_fn` is injectable and stubbed in
   tests, so keeping the 2-tuple return is the least invasive.
2. Raise a dedicated `ClassificationParseError` from `apply_classification`
   and let the existing except-branch handle it — but that branch's comment
   explicitly says parse failures are NOT supposed to land there
   (`pipeline.py:306-309`), so update the comment if you take this route,
   and make sure the warning (with `raw_response_snippet`) still reaches the
   run's warnings.

TDD (RED first — both fail today):

- `tests/test_region_pipeline.py`: stub classifier returning
  `apply_classification(garbage, regions)` output (or inject a classify_fn
  that returns unclassified regions + a `REGION_CLASSIFY_PARSE_FAILURE`
  warning); assert: no file appears under the tmp pdf's `.regions_cache`,
  `result.detection_page_data` is the whole page, `skip_detection` is False,
  and the warning code is present. Then a second resolve on the same page
  must call the classifier AGAIN (no cache hit) — that is the poisoning
  regression test.
- Keep `tests/test_region_classifier.py`'s existing parse-failure test
  passing (the warning shape is unchanged).

## Cleanup after the fix lands

- Delete or refresh the poisoned entry: rerun
  `python app.py extract s11 --refresh-regions`
  (with Fix A it should parse; with Fix B a repeat flake no longer caches),
  or simply `rm plans/.regions_cache/*s11*f2b9314d4207b160.json` — the
  cache is derived data, safe to delete.
- Expected post-fix state for s11: classification with 2 `floor_plan`
  regions (its 2026-08-04 entries had 2 at the current-era segmentation;
  the pre-clip-fix entry had 4 fragments), detection runs, candidates > 0.
- Live boundedness check stays: one API call per page per geometry, none
  when cached, none with `--no-gemini`.

## Conventions for this repo

- `graphify query` before reading source; `graphify update .` after changes.
- TDD via the superpowers skill — failing test first, minimal fix.
- New branch for the work; never add a Co-Authored-By trailer.
- Warning codes are SCREAMING_SNAKE_CASE and emitted only from
  `pipeline.collect_warnings`, `extraction.plumber.compare_counts`, or
  `gemini/client.py`/classifier — reuse `REGION_CLASSIFY_PARSE_FAILURE`, do
  not invent a new code for Fix B.
- Full suite must stay green: `python -m unittest discover tests`
  (420 tests as of 96e7535).
