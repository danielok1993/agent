# Deploying the takeoff callable

The extraction pipeline deploys from THIS repo into rivet-mind's Firebase
project as a second functions codebase named `takeoff`. rivet-mind continues
to deploy its own `default` codebase; neither touches the other.

## Verified facts

Confirmed on the machine this doc was written on:

- `firebase` CLI **14.27.0** is on `PATH` (`/Users/danielszweda/.volta/bin/firebase`)
  with login state present at `~/.config/configstore/firebase-tools.json`.
  rivet-mind pins `firebase-tools` `15.25.1` locally in its own repo, but that
  pin is irrelevant here: this repo has no local pin, so a deploy run from
  here uses whatever `firebase` resolves on `PATH` — the global 14.27.0.
- `.firebaserc` in this repo maps `dev` -> `rivet-mind-dev`, `qa` ->
  `nestimate-qa`, `prod` -> `nestimate-app`.

- `"runtime": "python313"` is accepted by that CLI. First read out of its
  supported-runtimes table
  (`lib/deploy/functions/runtimes/supported/types.js`), then confirmed in
  practice: the 2026-08-31 dry-run against `rivet-mind-dev` loaded and
  analysed this codebase without a runtime complaint. `python3.13` resolves
  to 3.13.7 at `/usr/local/bin/python3.13`.

## Prerequisite — create the discovery venv first

The Firebase CLI does **not** create the virtual environment for a Python
codebase. It expects one at `venv/` in the source directory, imports the
source inside it, and reads the endpoints back off a short-lived local
Flask server. Without it, every deploy and dry-run fails immediately with:

```
Error: Failed to find location of Firebase Functions SDK:
Missing virtual environment at venv directory.
Did you forget to run 'python3.13 -m venv venv'?
```

So, once per checkout:

```bash
python3.13 -m venv venv
./venv/bin/pip install -r requirements.txt
```

The interpreter must match `firebase.json`'s `"runtime": "python313"`.
Installing via `./venv/bin/pip` rather than activating avoids disturbing a
`.venv` you may already have active for development.

This `venv/` is **local tooling only**. The deployed container is built
server-side from `requirements.txt`, which is why `venv` is in
`firebase.json`'s ignore list — that is correct and should stay. It is also
gitignored.

## REQUIRED MANUAL GATE — read before any deploy command

The gate below was run and passed for **`rivet-mind-dev` only**, on
2026-08-31, against this exact configuration — see "Dry-run result" after the
checks. It has **not** been run against `nestimate-app` (prod) or
`nestimate-qa`.

Before anyone deploys to a project this gate has not covered, or after any
change to `firebase.json`, `.firebaserc`, or this codebase's function set,
the operator — a human, with their own credentials — MUST first run:

```bash
firebase deploy --only functions --project dev --dry-run
```

and read the plan output before ever dropping `--dry-run`. This is a real
authenticated action against the live `rivet-mind-dev` Firebase project. Do
not script around this gate, do not run it from an agent, and do not assume
a prior dry-run on a different machine or a different config still applies.

Confirm **both** of the following in the dry-run output before proceeding
any further:

1. **It plans to CREATE `measure_takeoff` in codebase `takeoff`.** If the
   plan does not show a new function named `measure_takeoff` under the
   `takeoff` codebase, stop — something about the source, ignore list, or
   codebase wiring is wrong and the deploy will not do what this doc
   describes.
2. **It plans to DELETE NOTHING.** Read every line of the plan looking for a
   delete/removal action. If it proposes deleting `enqueueEstimate`,
   `processEstimateTask`, `stripeWebhook`, or **any** other rivet-mind
   function from the `default` codebase, **STOP IMMEDIATELY** and do not
   proceed to a real deploy. That would mean the `codebase` key is not
   isolating `takeoff` from `default` the way this whole plan assumes, and
   running the real deploy would delete rivet-mind's existing functions.
   Escalate to a human before touching anything further.

Only once both checks pass on a real dry-run, on the actual target project,
should `--dry-run` ever be dropped.

### Dry-run result — `rivet-mind-dev`, 2026-08-31

`firebase deploy --only functions --project dev --dry-run` completed with
`✔ Dry run complete!` and **no deletion prompt of any kind**. The CLI
interrupts a deploy that would remove functions, so its silence here is the
pass on check 2: the `codebase` key does isolate `takeoff` from rivet-mind's
`default` functions.

Two supporting observations from that run:

- **Package size 386.03 KB.** The ignore list is doing its job; without the
  `.claude` entry this would have been ~118 MB of agent worktrees uploaded
  on every deploy.
- **Endpoint discovery succeeded** (`GET /__/functions.yaml → 200`).

Check 1 deserves a caveat: `--dry-run` reports completion without
enumerating the functions it would create, so that output alone does not
prove `measure_takeoff` was discovered with the right settings. It was
confirmed separately by reading the endpoint the SDK actually built:

```bash
./venv/bin/python -c "import main; print(main.measure_takeoff.__firebase_endpoint__)"
```

which returned `entryPoint: measure_takeoff`, `region: [europe-west2]`,
`availableMemoryMb: 2048`, `timeoutSeconds: 900`, `maxInstances: 3`,
`platform: gcfv2`, `callableTrigger: {}` and the label
`deployment-callable: "true"` — every value matching this document and the
design. That command is a cheap way to re-verify the deployed configuration
after any change to the decorator options, and needs no network.

## Deploy

```bash
firebase deploy --only functions --project dev    # rivet-mind-dev
firebase deploy --only functions --project prod   # nestimate-app
```

Always run with `--dry-run` first (see the gate above) and confirm it
deletes nothing.

## One-time GCP setup, per project

The function's service account needs Vertex AI access, which is not granted
by default:

```bash
gcloud projects add-iam-policy-binding rivet-mind-dev \
  --member="serviceAccount:<runtime-sa>@rivet-mind-dev.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

It also needs read on the drawing prefixes and write on the takeoff prefix.
The default Firebase Admin SDK service account already has both; a
narrower runtime service account would need `roles/storage.objectAdmin` on
the default bucket.

## The callable

Name: **`measure_takeoff`** — the Firebase Python SDK exports a callable under
its Python function name and offers no override. The frontend calls it as:

```ts
const measure = httpsCallable(functions, 'measure_takeoff');
const { data } = await measure({ takeoffId, debug: false });
```

Request: `{ takeoffId: string, debug?: boolean }`. Nothing else — the tenant
comes from the verified `customerId` claim, and the source drawings come from
`takeoffs/{takeoffId}.sourceFiles`.

Response: `{ takeoffId, sheets, artifacts: { prefix, bySheet, run }, run }`.
`artifacts.bySheet` is keyed by `sheetId` and holds nothing else;
`artifacts.run` is the sibling map of per-source-file run artefacts
(`{ file_00: { "summary.json": …, "warnings.json": … } }`). The top-level
`run` block reports `pagesMeasured` (the number of sheets returned) and
`pagesSkipped`.

Firestore: the function writes `processing` on entry, then
`awaiting_review` + `document` (a JSON string) on success, or
`failed` + `error` on failure.

## What rivet-mind must land

1. **A `storage.rules` block for the new prefix.** There is no wildcard
   fallback in that file, so an unlisted path is denied:

   ```
   match /customers/{customerId}/takeoffs/{takeoffId}/{allPaths=**} {
     allow read: if request.auth != null
       && request.auth.token.customerId == customerId;
     allow write: if false;   // backend-only
   }
   ```

2. **Resolve `planSvgUrl`.** The function emits a Storage OBJECT PATH, not an
   HTTPS URL — a signed URL baked into a persisted document expires with it.
   Their mapper resolves it:

   ```ts
   planSvgUrl: await getDownloadURL(ref(storage, sheet.plan_svg_url))
   ```

3. **Widen the `warnings` schema.** `functions/shared/types/takeoff.ts:151`
   declares `warnings: z.array(z.string())`; the pipeline emits
   `{warning_code, severity, message, page_number}`. Their fixture is `[]`, so
   this has never been exercised — **the first page emitting a real warning
   fails their parse today.** `warning_code` is the only machine-readable
   part, and `TAKEOFF_NO_SCALE` vs `SCALE_IMPLAUSIBLE` is exactly what should
   drive their calibrate panel.

4. **Consume the injected sheet fields.** The function emits `sheet_id`,
   `source_file_id`, `source_file_name` and `label`. A zod object STRIPS
   unknown keys silently rather than erroring, so if `takeoffSheetSchema` is
   left as-is these are discarded without a warning and their
   `sheet_${page_number}` id collides across source files again.

5. **Call `measure_takeoff` in place of the `measure()` stub**
   (`functions/src/takeoff/on-takeoff-created.ts`), and raise the trigger's
   `timeoutSeconds` from the 60 s default.

6. **A stuck-record reaper.** If the 900 s timeout or an OOM kills the
   instance, the record stays at `processing`. The function writes `startedAt`
   so such a record is detectable; the sweep belongs on their side, alongside
   `reapStuckEstimatesScheduled`.

## Local verification performed (this repo, no network, no deploy)

Both commands were run from the repo root with this repo's dev virtualenv,
`/Users/danielszweda/Documents/GitHub/UD/agent/.venv/bin/python`.

**The deploy bundle imports cleanly:**

```
$ python -c "import main; print(main.measure_takeoff)"
<function measure_takeoff at 0x10d0d98a0>
```

No `ModuleNotFoundError`. `main.py` is the only module that imports
`firebase_functions`/`firebase_admin`, and it initialises cleanly outside a
deployed environment (the `firebase_admin.initialize_app()` call is wrapped
in a `try`/`except` for exactly this reason — no ambient credentials under
test still leaves `main.measure_takeoff` importable and callable).

**The stored-scale tier tolerates a missing corpus manifest:**

```
$ python -c "from regression import corpus; print(corpus.load_manifest().get('sheets', [])[:1] or 'empty corpus ok')"
[{'slug': 's01', 'file': 's01-floor-plans.pdf', 'sha256': '0867a4be9327989619cd71a783eb701ea11ff231877b548209764eaad2527559', 'pages': 1, 'tier': 'reference', 'labeled': True}]
```

`fixtures/MANIFEST.json` is committed (only `fixtures/sheets/*.pdf` is
NDA-excluded), so on this machine — which has the manifest but not the NDA
PDFs — `load_manifest()` returns the real manifest and this printed the
first sheet entry rather than the `'empty corpus ok'` fallback. The fallback
path itself (`regression/corpus.py::load_manifest`, `if not
MANIFEST_PATH.exists(): return {"storage": "", "sheets": []}`) is exercised
by this repo's own test suite, not by this particular run; what this run
confirms is that `scale/store.py` importing `regression` does not itself
raise when `fixtures/sheets/` (the deploy-ignored, NDA-only part) is absent —
only the manifest file, which ships, is on the read path at import time.

## Known limitations

- **Unresolved scale.** The scale ladder's tty-prompt tier cannot exist in a
  function and this contract accepts no scale input, so a sheet with neither a
  `/VP` measure viewport nor legible scale text returns `scale: null` and
  `quantities: null`. Geometry is still correct. The larger cost:
  `scale.factor.detection_scale` scales the detection gates themselves by
  `f = 50 / denominator`, so such a sheet is detected at the identity factor
  and client-side calibration cannot recover a wrong room set. See the design
  doc's "Accepted limitation".
- **SVG weight.** `render_page_svg` emits MuPDF's raw redraw, 0.2–21 MB across
  the corpus, against the 2.3 MB their viewer was tuned on. Serving gzipped
  covers most of it; an optimisation pass is a follow-up if it does not.
- **No cross-invocation Gemini cache.** Each run costs two Gemini calls per
  page (region classification, room labels).
- **The equivalence test has never actually run.** `tests/test_takeoff_fn_equivalence.py`
  SKIPS unless BOTH the NDA corpus sheet `s01` is on disk in `fixtures/sheets/`
  AND Vertex AI credentials are configured. Neither condition is met by CI or
  by the environment this task was verified in, so the test has skipped on
  every run so far. The claim that the callable's detection output is
  byte-identical to the CLI's is therefore enforced by a test that exists in
  the suite, but it has **not yet been exercised** — nobody has watched it
  pass. Running it for real (on a machine with the corpus downloaded and
  `gcloud auth application-default login` completed) is outstanding work, not
  a verified fact.
