# Takeoff as a Firebase Function — design

**Date:** 2026-08-30
**Status:** approved, ready for an implementation plan

## Purpose

Expose this repo's extraction pipeline as a callable Firebase Function so the
sibling app `rivet-mind` can measure an architectural PDF and get back a
`takeoff.json` per floor-plan sheet, with the rendered SVG and the remaining
pipeline outputs written to Cloud Storage.

The function is a **transport wrapper**. It must not change detection
behaviour: for the same PDF and options, its output is identical to
`python app.py extract`. The regression corpus (`tools/regress.py`,
`tests/ground_truth/`) remains the only guard on detection quality, and it
guards the CLI path. If the deployed function can diverge from the CLI, that
guard means nothing.

## Context: what rivet-mind already has

Reconnaissance only — this design does not build on the incomplete branch, but
it must land in the socket that branch cut.

`rivet-mind` is a React + Firebase app. Its vocabulary differs from the brief:

| Brief's word | Actual concept | Location |
|---|---|---|
| organisation / tenant | **customer** (`customerId`) | `customers/{customerId}`, and an auth custom claim |
| client | the customer's *end-customer* | `customers/{customerId}/clients/{clientId}` |
| project | **estimate** (`estimateId`) | `estimates/{estimateId}` (top-level) |

There is no project entity. The tenant boundary is the `customerId` custom
claim, set only by `functions/src/auth/auth-operations.ts:118`.

The takeoff feature lives on two branches. `feat/takeoff-review-ui` (the root
checkout) is UI-only. `feat/takeoff-wizard-integration` — checked out in a
worktree at `rivet-mind/.claude/worktrees/takeoff-wizard` — is the further-along
state and already has:

- `takeoffs/{takeoffId}`, a **top-level** collection:
  `{ customerId, userId, status, projectTitle, estimateId | null,
     sourceFiles: [{fileName, storageUrl}], document: string | null,
     estimateRequest, error, createdAt, updatedAt }`
- the status lifecycle `queued → processing → awaiting_review → approved`,
  plus `failed`
- `firestore.rules:246-265` — backend-only create/delete; the only client update
  permitted is `hasOnly(['document','status','updatedAt'])` into `approved`
- the whole review UI, working against a fixture
- **exactly one hole**, `functions/src/takeoff/run-takeoff.ts:4-7`:

```ts
export interface RunTakeoffDeps {
  update: (id: string, patch: Record<string, unknown>) => Promise<void>;
  measure: () => Promise<TakeoffDocument>;   // a 20s sleep + fixture
}
```

`functions/shared/types/takeoff.ts:140` already carries a zod schema that parses
this repo's snake_case `takeoff.json` wire shape, and
`functions/shared/constants/takeoff.ts:41` hard-codes
`TAKEOFF_POLYGON_OFFSET_PX = 2.0` to match `ROOM_WALL_DILATE_PX` here. The
contract between the two repos therefore already exists and this design keeps
it.

Their infrastructure permits this cleanly: `firebase.json`'s `functions` block
is already the array form (`{source: "functions", codebase: "default"}`), region
`europe-west2`, and `firebase-tools 15.25.1` supports `python310`–`python314`.
Projects are `rivet-mind-dev` (dev/default), `nestimate-qa` (qa),
`nestimate-app` (prod).

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Function home | This repo, deployed into rivet-mind's Firebase project | The detector stays with its regression corpus, ground truth and tuning guides. rivet-mind gains a callable it does not own. |
| Transport | Python `on_call`, invoked from the frontend | Same project, so auth is the ordinary Firebase ID token + `customerId` claim, exactly like `enqueueEstimate`. No OIDC, no token exchange. |
| State | The function writes the takeoff record's status and document | The frontend subscribes to that record; it must be coherent if the tab closes mid-run. |
| Synchronicity | Synchronous | ~10 s for a very large page against a 30-minute ceiling. |
| Scale | Fully automatic; no scale input | The client calibrates afterwards. See "Accepted limitation". |
| Sheet scope | Only pages that produced a `floor_plan` region | The reviewer sees the drawings a person can actually check. |
| Artefacts | Standard set always, heavy trace on request | ~7 MB/page always, +21 MB/page under `debug: true`. |
| Storage prefix | `customers/{customerId}/takeoffs/{takeoffId}/` | Matches their newest nested convention; keyed by takeoffId, which is never null. |

## Contract

### Request

```ts
{ takeoffId: string, debug?: boolean }
```

That is the entire input. Deliberately **not** in the request:

- `customerId` — read from the verified `request.auth.token.customerId`. A
  client that could name its own tenant could measure another tenant's drawings.
- `userId` — `request.auth.uid`.
- `estimateId`, `sourceFiles` — already on `takeoffs/{takeoffId}`. Reading them
  back is also the authorization check.

### Response

```ts
{
  takeoffId: string,
  sheets: TakeoffSheetJson[],          // the snake_case takeoff.json shape
  artifacts: {
    prefix: string,                    // customers/{c}/takeoffs/{t}/
    bySheet: { [sheetId]: { svg, takeoff, render, overlay, ... } }
  },
  run: { startedAt, finishedAt, pagesProcessed, pagesSkipped, warnings }
}
```

A sheet is ~39 KB, so a three-plan set is ~120 KB against the 10 MB callable
response ceiling.

### Sheet identity

Their parser derives `sheetId = "sheet_" + page_number`
(`functions/shared/types/takeoff.ts:155`), which collides across source files —
page 1 of file A and page 1 of file B both become `sheet_1`. This function emits
a globally unique `sheet_id` (`{sourceFileIndex}_{pageNumber}`) and fills the
`source_file_id` and `label` their parser currently hard-codes to `null` /
`"Page N"`.

Note their transform must then *read* those fields. A zod object strips unknown
keys silently rather than erroring, so if `takeoffSheetSchema` is left as-is the
new `sheet_id` / `source_file_id` / `label` are discarded without a warning and
the collision returns. This is on their side of the boundary, listed under
"Out of scope" below.

### Two deviations from their current types

Both are deliberate, and both need a small change on their side.

1. **`planSvgUrl` carries the Storage object path, not an HTTPS URL.** A signed
   URL baked into a persisted document expires with it; a download-token URL
   never expires and cannot be revoked. Their mapper resolves the path with
   `getDownloadURL()` — one line, respects `storage.rules`, and matches how the
   rest of their app reads Storage.

2. **`warnings` stays structured.** `takeoff/document.py:121` emits
   `{warning_code, severity, message, page_number}`; their zod declares
   `warnings: z.array(z.string())` (`takeoff.ts:151`) and has never been
   exercised because the fixture is `[]`. **The first page emitting a real
   warning fails their parse today.** Flattening to strings would discard
   `warning_code`, which is the only machine-readable part — and
   `SCALE_IMPLAUSIBLE` vs `TAKEOFF_NO_SCALE` is precisely what should drive
   their calibrate panel.

### Firestore writes

| Point | Write |
|---|---|
| entry | `status: 'processing'`, `startedAt`, `updatedAt` |
| success | `status: 'awaiting_review'`, `document: <JSON string>`, `error: null`, `updatedAt` |
| failure | `status: 'failed'`, `error: <message>`, `updatedAt` |

`document` is written inline as a JSON string, matching
`run-takeoff.ts:29-37`. Their note about the 1 MB document cap (~25 sheets) is
not a live risk once only floor-plan pages become sheets, and the canonical copy
lands in Storage regardless — so moving to a pointer later needs no contract
change.

### Storage layout

```
customers/{customerId}/takeoffs/{takeoffId}/
  file_00/page_01/        <- keyed by source file too; a takeoff may hold several
    page.svg              <- planSvgUrl, browser-readable
    takeoff.json
    final_entities.json
    render.png
    overlay.png
    primitives.json
    candidates.json
    regions.json
    debug_trace.json      <- debug: true only
    debug_viewer.html     <- debug: true only
  summary.json
  warnings.json
  run.json                <- versions, timings, options, skipped pages
```

`storage.rules` has **no wildcard fallback** — six explicit `match` blocks, and
anything unlisted is denied. This prefix needs a new block on their side, gated
on `request.auth.token.customerId == customerId`. It fits the existing
`customers/{customerId}/**` shape, so it is additive.

## Repo layout and deployment

The whole repo is the function root: Firebase uploads only the `source`
directory, so a `functions/` subdirectory could not import `detection/`,
`extraction/` or `takeoff/` at the root. `source: "."` avoids vendoring, a
submodule, and a copy step.

```jsonc
// agent/firebase.json — functions only, no hosting/firestore/storage blocks
{ "functions": [{
    "source": ".", "codebase": "takeoff", "runtime": "python313",
    "ignore": ["tests", "fixtures", "outputs", "graphify-out", "docs",
               "plans", ".venv", "**/__pycache__", ".git"]
}]}
```

```
agent/
  main.py            NEW — the callable, thin
  takeoff_fn/        NEW — request parsing, Storage I/O, Firestore writes, upload
  firebase.json  .firebaserc  requirements.txt
  detection/ extraction/ takeoff/ scale/ layout/ gemini/ pipeline.py   (untouched)
```

Two repos deploying into one Firebase project is what `codebase` exists for: the
CLI reconciles only against functions labelled `takeoff`, so a deploy from here
cannot touch rivet-mind's `default` functions. **Verify with a dry run before
the first real deploy.**

### Runtime

`python313` (matches the venv here), region `europe-west2`, **2 GiB** memory,
**900 s** timeout, `maxInstances` set explicitly rather than inheriting their
global 10.

2 GiB matches their heaviest precedent (`generateEstimatePdf`), and is right for
a second reason: `/tmp` on Cloud Functions is a **tmpfs**, so the output tree is
charged against memory. The function uploads and deletes each page's tree before
processing the next, rather than accumulating.

### Dependencies

Add `firebase-functions`, `firebase-admin`, `google-cloud-storage`. Drop
`InquirerPy` (only `tools/review.py` uses it).

- `rich` **stays** — `pipeline.py:11-15` imports it; it degrades fine on a
  non-tty and its output goes to Cloud Logging.
- `opencv-python-headless` **stays** — an optional import in
  `detection/doors/shape.py`, but its absence silently changes door detection.
  The deployed detector must be byte-identical to the one the corpus validates.

### Vertex AI

No code change: `gemini/client.py:15` already falls back to `GCLOUD_PROJECT`,
which the runtime sets. Set `GOOGLE_CLOUD_LOCATION=europe-west2` so drawings do
not cross into `us-central1`. The function's service account needs
`roles/aiplatform.user`, which is **not** granted by default.

### Known import coupling

`scale/store.py:35-37` imports `from regression import corpus` and
`regression.ground_truth`. `regression/` therefore cannot be in the ignore list
or the stored-scale tier crashes on import. It is pure Python and small, so it
ships. Confirm at implementation time that `regression/corpus.py` does not read
`fixtures/MANIFEST.json` at import time, since `fixtures/` is excluded.

## Execution flow

1. Assert `request.auth`; read `customerId` from the token, `uid` for `userId`.
2. Load `takeoffs/{takeoffId}`. `not-found` if absent; `permission-denied` if
   `doc.customerId != token.customerId`.
3. Concurrency guard: refuse if already `processing` with a recent `updatedAt`,
   or already `approved`.
4. Write `status: 'processing'`, `startedAt`.
5. Per source file: validate the `gs://` path sits under `.../{customerId}/`
   (the same trust boundary as `attachment-download.ts:93`), download to `/tmp`.
6. `run_extract(pdf_path, page_indices=all, out_parent=<tmp>, write_svg=True,
   allow_scale_prompt=False, debug=req.debug)`.
7. Per page: skip if `regions.json` holds no `floor_plan` region; else upload
   the artefact set, then **delete that page's tree** before the next page.
8. Assemble sheets with unique ids, `source_file_id` and `label`.
9. Write `status: 'awaiting_review'`, `document`, `error: null`. Return.

`allow_scale_prompt=False` is load-bearing: without it a sheet with no
resolvable scale blocks on `input()` inside a Cloud Function until the timeout.

## Failure handling

A source file that will not download or parse records a warning in `run.json`
and the run continues — one corrupt file in a three-file set must not lose the
two good plans. The takeoff goes `failed` only when **no** sheet survives, or on
an unexpected exception. Either way `status: 'failed'` + `error` is written
before the `HttpsError` propagates, so the record never misreports its state.

**Unclosable from this side:** if the 900 s timeout or an OOM kills the
instance, the document stays at `processing` indefinitely — the same failure
`reapStuckEstimatesScheduled` exists to sweep on the estimate side. This design
writes `startedAt` so a stuck record is detectable; the reaper belongs to
rivet-mind and is not built here.

## Testing

1. **Existing fast tier** — `python -m unittest discover tests`, unchanged.
   `pipeline.py` and every detector are untouched by this work.
2. **New unit tests** for `takeoff_fn/`, with fakes for Firestore and Storage:
   the tenant boundary on `storageUrl`, sheet-id uniqueness across multiple
   source files, floor-plan filtering, the artefact manifest, and every status
   transition including the failure path. No emulator required.
3. **The equivalence test.** The same corpus PDF through the callable and
   through `app.py extract` must produce identical `takeoff.json`. This is the
   test that keeps the regression corpus meaningful.

`tools/regress.py` remains the detection guard and is untouched.

## Out of scope

Stated so it is on the record, not because it was overlooked:

- **No scale override in the request.** The client calibrates afterwards.
- **No Gemini cache persistence between invocations.** Each run costs two Gemini
  calls per page (region classification + room labels). The `/tmp` caches still
  dedupe within a run.
- **No Cloud Tasks, no retries.** Synchronous, one attempt.
- **No changes to rivet-mind.** Theirs to land, once this function exists:
  the `storage.rules` block for the new prefix; `getDownloadURL` resolution of
  `planSvgUrl`; the widened `warnings` schema; consuming `sheet_id` /
  `source_file_id` / `label` in `takeoffSheetSchema` instead of synthesising
  them; calling `measureTakeoff` in place of the `measure()` stub; and the
  stuck-record reaper.

## Accepted limitation: unresolved scale

The scale ladder is `stored → viewport → text → sole page-level candidate →
prompt` (`scale/resolver.py:8`). The prompt tier cannot exist in a function, and
this design accepts no scale input, so a sheet with neither a `/VP` measure
viewport nor legible scale text returns `scale: null`, `quantities: null` and
`TAKEOFF_NO_SCALE`. Geometry — rooms, openings, polygons — is still correct and
still reviewable.

The cost is larger than missing numbers, and is recorded here so it is not
rediscovered as a bug. The drawing scale also feeds the **detection gates**:
`scale.factor.detection_scale` scales every W-class constant by
`f = 50 / denominator` (see `docs/scale-normalization-findings.md` §4). A sheet
whose scale does not self-resolve is therefore detected at the identity factor,
which is correct for a 1:50 drawing and progressively wrong below it. Client-side
calibration rescales quantities but cannot re-run detection at the right gate
sizes, so the *room set itself* may differ from what a scaled run would find.

`resolve_page_scales(..., stored=[...])` (`scale/resolver.py:168,214`) already
takes caller-supplied scales as a parameter, matched by bbox IoU and outranking
every detected tier. Adding an override later is therefore an additive change to
the request shape, not a redesign — and the request shape defined above leaves
room for it.

## Known risk: SVG weight

Their `page.svg` fixture is 2.3 MB and their own comment
(`plan-svg-layer.tsx:11-14`) calls it *optimised* at ~42,000 elements,
"roughly 410 KB gzipped". `extraction.renderer.render_page_svg` emits MuPDF's
raw redraw, measured at 0.2–21 MB across the corpus. Serving it gzipped from
Storage covers most of the gap. If the raw output proves materially heavier than
what their viewer was tuned against, an optimisation pass is a follow-up — not
something to build speculatively now.
