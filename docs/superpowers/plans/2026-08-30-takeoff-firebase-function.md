# Takeoff Firebase Function Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose this repo's extraction pipeline as a Python `on_call` Firebase Function that measures an architectural PDF and returns a `takeoff.json` per floor-plan sheet, writing `page.svg` and the remaining pipeline outputs to Cloud Storage.

**Architecture:** A thin `main.py` callable delegates to `takeoff_fn/`, a package of small single-responsibility modules wired together by `takeoff_fn/runner.py`. The runner takes its Firestore client, Storage bucket and extraction function as **injected parameters**, so every module is unit-testable with fakes and no emulator. `pipeline.py` and every detector are untouched — the function is a transport wrapper around the existing `run_extract`.

**Tech Stack:** Python 3.13, `firebase-functions`, `firebase-admin`, `google-cloud-storage`, PyMuPDF/shapely/OpenCV (already present), `unittest` (repo standard).

**Spec:** `docs/superpowers/specs/2026-08-30-takeoff-firebase-function-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Detection must stay byte-identical to the CLI.** Do not modify `pipeline.py`, `detection/`, `extraction/`, `takeoff/`, `scale/`, `layout/` or `gemini/`. `tools/regress.py` guards the CLI path; if the function can diverge from it, that guard is worthless.
- **Runtime:** `python313`, region `europe-west2`, memory 2 GiB, timeout 900 s, `max_instances` 3.
- **Deployed callable name is `measure_takeoff`** — the Firebase Python SDK exports a callable under its Python function name and offers no override. rivet-mind must call `httpsCallable(functions, 'measure_takeoff')`.
- **Tenant identity is never taken from the request.** `customerId` comes from `request.auth.token['customerId']`, `userId` from `request.auth.uid`.
- **Storage prefix:** `customers/{customerId}/takeoffs/{takeoffId}/file_{NN}/page_{NN}/`.
- **Firestore collection:** top-level `takeoffs/{takeoffId}`. Statuses written: `processing`, `awaiting_review`, `failed`.
- **`takeoff_fn/` must not import `firebase_functions`.** Only `main.py` does. This keeps unit tests free of the SDK.
- **Test style:** `unittest`, `tempfile.mkdtemp()` + `shutil.rmtree` in `setUp`/`tearDown`, dependency injection via keyword arguments — matching `tests/test_region_pipeline.py`.
- **Run tests with:** `python -m unittest discover tests`

## File Structure

| File | Responsibility |
|---|---|
| `main.py` | **Create.** The `@https_fn.on_call` entry point. Maps domain errors to `HttpsError`. Nothing else. |
| `takeoff_fn/__init__.py` | **Create.** Empty package marker. |
| `takeoff_fn/config.py` | **Create.** Constants: runtime sizing, artefact name tuples, path templates, staleness window. |
| `takeoff_fn/errors.py` | **Create.** Domain exception hierarchy carrying a `code` string. No SDK import. |
| `takeoff_fn/request.py` | **Create.** `TakeoffRequest` dataclass + `parse_request`. Auth and payload validation. |
| `takeoff_fn/records.py` | **Create.** Firestore read, tenant/status guards, and the three status transitions. |
| `takeoff_fn/sources.py` | **Create.** `gs://` parsing, the tenant path boundary, download to a working dir, page counting. |
| `takeoff_fn/sheets.py` | **Create.** Reads a finished output tree; floor-plan filtering; sheet id / label / svg-path injection. |
| `takeoff_fn/artifacts.py` | **Create.** Object-path construction, artefact selection by debug flag, upload. |
| `takeoff_fn/runner.py` | **Create.** Orchestration and failure semantics. Everything injected. |
| `firebase.json` | **Create.** Single `takeoff` codebase, `source: "."`. |
| `.firebaserc` | **Create.** Project aliases mirroring rivet-mind's. |
| `requirements.txt` | **Modify.** Add three deps, drop `InquirerPy`. |
| `tests/test_takeoff_fn_*.py` | **Create.** One test module per `takeoff_fn` module. |

---

### Task 1: Scaffold, errors, and request parsing

Produces a deployable callable that authenticates and validates its payload, returning a stub. Everything after this builds on `TakeoffRequest`.

**Files:**
- Create: `firebase.json`, `.firebaserc`, `main.py`, `takeoff_fn/__init__.py`, `takeoff_fn/config.py`, `takeoff_fn/errors.py`, `takeoff_fn/request.py`
- Modify: `requirements.txt`
- Test: `tests/test_takeoff_fn_request.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `takeoff_fn.errors.TakeoffFnError` with class attribute `code: str`; subclasses `Unauthenticated`, `PermissionDenied`, `NotFound`, `InvalidArgument`, `FailedPrecondition`.
  - `takeoff_fn.request.TakeoffRequest(takeoff_id: str, customer_id: str, user_id: str, debug: bool)` — frozen dataclass.
  - `takeoff_fn.request.parse_request(data: dict | None, auth_uid: str | None, auth_token: dict | None) -> TakeoffRequest`.
  - `takeoff_fn.config` constants named in the code below.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_request.py`:

```python
import unittest

from takeoff_fn.errors import InvalidArgument, PermissionDenied, Unauthenticated
from takeoff_fn.request import TakeoffRequest, parse_request


class TestParseRequest(unittest.TestCase):
    def test_a_valid_payload_parses(self):
        req = parse_request(
            {"takeoffId": "t1"}, "uid-1", {"customerId": "cus-1"})
        self.assertEqual(
            req, TakeoffRequest(takeoff_id="t1", customer_id="cus-1",
                                user_id="uid-1", debug=False))

    def test_debug_defaults_false_and_is_honoured_when_true(self):
        self.assertFalse(parse_request(
            {"takeoffId": "t1"}, "u", {"customerId": "c"}).debug)
        self.assertTrue(parse_request(
            {"takeoffId": "t1", "debug": True}, "u", {"customerId": "c"}).debug)

    def test_no_auth_is_unauthenticated(self):
        with self.assertRaises(Unauthenticated):
            parse_request({"takeoffId": "t1"}, None, None)

    def test_a_token_without_a_customer_claim_is_denied(self):
        with self.assertRaises(PermissionDenied):
            parse_request({"takeoffId": "t1"}, "uid-1", {})

    def test_a_missing_or_blank_takeoff_id_is_invalid(self):
        for data in ({}, {"takeoffId": ""}, {"takeoffId": "   "}, None):
            with self.subTest(data=data):
                with self.assertRaises(InvalidArgument):
                    parse_request(data, "uid-1", {"customerId": "cus-1"})

    def test_a_non_string_takeoff_id_is_invalid(self):
        with self.assertRaises(InvalidArgument):
            parse_request({"takeoffId": 7}, "uid-1", {"customerId": "cus-1"})

    def test_a_customer_id_in_the_payload_is_ignored(self):
        # The tenant is the verified claim, never the caller's word for it.
        req = parse_request({"takeoffId": "t1", "customerId": "other"},
                            "uid-1", {"customerId": "cus-1"})
        self.assertEqual(req.customer_id, "cus-1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_request -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'takeoff_fn'`

- [ ] **Step 3: Write the package, config and errors**

Create `takeoff_fn/__init__.py` as an empty file.

Create `takeoff_fn/errors.py`:

```python
"""Domain errors, carrying the callable error code they map to.

This module deliberately does not import firebase_functions: keeping the SDK
out of takeoff_fn/ is what lets every unit test run without it. main.py owns
the translation to HttpsError.
"""
from __future__ import annotations


class TakeoffFnError(Exception):
    """Base class. `code` is a Firebase callable error code string."""
    code = "internal"


class Unauthenticated(TakeoffFnError):
    code = "unauthenticated"


class PermissionDenied(TakeoffFnError):
    code = "permission-denied"


class NotFound(TakeoffFnError):
    code = "not-found"


class InvalidArgument(TakeoffFnError):
    code = "invalid-argument"


class FailedPrecondition(TakeoffFnError):
    code = "failed-precondition"
```

Create `takeoff_fn/config.py`:

```python
"""Constants for the takeoff callable.

Runtime sizing is justified in the design doc: 2 GiB matches rivet-mind's
heaviest precedent and covers the tmpfs cost of the output tree, which is
charged against memory on Cloud Functions.
"""
from __future__ import annotations

REGION = "europe-west2"
MEMORY_MIB = 2048
TIMEOUT_SECONDS = 900
MAX_INSTANCES = 3

# Vertex location for the region-classification and room-label calls, so
# drawings do not leave the region the rest of the app runs in.
VERTEX_LOCATION = "europe-west2"

TAKEOFF_COLLECTION = "takeoffs"

# A takeoff left at "processing" longer than this is assumed dead (an
# instance killed by timeout or OOM) and may be re-measured. rivet-mind owns
# the reaper that sweeps such records; this only stops a live run being
# double-started.
STALE_PROCESSING_SECONDS = 1800

STATUS_PROCESSING = "processing"
STATUS_AWAITING_REVIEW = "awaiting_review"
STATUS_FAILED = "failed"
STATUS_APPROVED = "approved"

# Uploaded on every run. ~7 MB/page.
STANDARD_ARTIFACTS = (
    "page.svg",
    "takeoff.json",
    "final_entities.json",
    "render.png",
    "overlay.png",
    "primitives.json",
    "candidates.json",
    "regions.json",
)

# Uploaded only when the request sets debug: true. ~21 MB/page.
DEBUG_ARTIFACTS = (
    "debug_trace.json",
    "debug_viewer.html",
)

# Written by run_extract at the run root, once every page has finished.
RUN_ARTIFACTS = (
    "summary.json",
    "warnings.json",
)

SVG_ARTIFACT = "page.svg"
```

Create `takeoff_fn/request.py`:

```python
"""Parsing and validating one callable request.

The tenant is taken from the verified auth token, never from the payload: a
client that could name its own customerId could measure another tenant's
drawings.
"""
from __future__ import annotations

from dataclasses import dataclass

from takeoff_fn.errors import InvalidArgument, PermissionDenied, Unauthenticated


@dataclass(frozen=True)
class TakeoffRequest:
    takeoff_id: str
    customer_id: str
    user_id: str
    debug: bool


def parse_request(data, auth_uid, auth_token) -> TakeoffRequest:
    if not auth_uid:
        raise Unauthenticated("User must be authenticated")

    customer_id = (auth_token or {}).get("customerId")
    if not customer_id:
        raise PermissionDenied("Missing customer context")

    payload = data or {}
    takeoff_id = payload.get("takeoffId")
    if not isinstance(takeoff_id, str) or not takeoff_id.strip():
        raise InvalidArgument("takeoffId is required")

    return TakeoffRequest(
        takeoff_id=takeoff_id.strip(),
        customer_id=str(customer_id),
        user_id=str(auth_uid),
        debug=bool(payload.get("debug", False)),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_request -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Write the Firebase scaffold**

Create `firebase.json`. Note there is no `hosting`, `firestore` or `storage`
block: those belong to rivet-mind and a deploy from here must not touch them.

```json
{
  "functions": [
    {
      "source": ".",
      "codebase": "takeoff",
      "runtime": "python313",
      "ignore": [
        "tests",
        "fixtures",
        "outputs",
        "graphify-out",
        "docs",
        "plans",
        "tools",
        ".venv",
        ".git",
        "**/__pycache__",
        "**/*.pyc"
      ]
    }
  ]
}
```

Create `.firebaserc`, mirroring rivet-mind's aliases:

```json
{
  "projects": {
    "default": "rivet-mind-dev",
    "dev": "rivet-mind-dev",
    "qa": "nestimate-qa",
    "prod": "nestimate-app"
  }
}
```

- [ ] **Step 6: Update requirements.txt**

Replace the contents of `requirements.txt` with:

```
PyMuPDF>=1.24.0
pdfplumber>=0.11.0
pdfminer.six>=20231228
google-genai>=0.8.0
Pillow>=10.3.0
shapely>=2.0.0
rich>=13.7.0
opencv-python-headless>=4.9.0
firebase-functions>=0.4.0
firebase-admin>=6.5.0
google-cloud-storage>=2.16.0
```

`InquirerPy` is dropped — only `tools/review.py` imports it, and `tools/` is in
the deploy ignore list. `rich` stays: `pipeline.py:11-15` imports it and it
degrades fine on a non-tty. `opencv-python-headless` stays: it is an optional
import in `detection/doors/shape.py`, but its absence silently changes door
detection, and the deployed detector must match the one the corpus validates.

- [ ] **Step 7: Write the callable entry point**

Create `main.py`:

```python
"""Firebase entry point for the takeoff extraction pipeline.

This module is the only place firebase_functions is imported. Everything it
delegates to lives in takeoff_fn/ and is testable without the SDK.
"""
from __future__ import annotations

from firebase_functions import https_fn, options

from takeoff_fn import config
from takeoff_fn.errors import TakeoffFnError
from takeoff_fn.request import parse_request

_ERROR_CODES = {
    "unauthenticated": https_fn.FunctionsErrorCode.UNAUTHENTICATED,
    "permission-denied": https_fn.FunctionsErrorCode.PERMISSION_DENIED,
    "not-found": https_fn.FunctionsErrorCode.NOT_FOUND,
    "invalid-argument": https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
    "failed-precondition": https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
    "internal": https_fn.FunctionsErrorCode.INTERNAL,
}


@https_fn.on_call(
    region=config.REGION,
    memory=options.MemoryOption.GB_2,
    timeout_sec=config.TIMEOUT_SECONDS,
    max_instances=config.MAX_INSTANCES,
)
def measure_takeoff(req: https_fn.CallableRequest) -> dict:
    """Measure the drawings on takeoffs/{takeoffId} and return their sheets."""
    try:
        request = parse_request(
            req.data,
            req.auth.uid if req.auth else None,
            dict(req.auth.token) if req.auth else None,
        )
    except TakeoffFnError as exc:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(exc.code, https_fn.FunctionsErrorCode.INTERNAL),
            str(exc),
        ) from exc

    # Wired to the runner in Task 7.
    return {"takeoffId": request.takeoff_id, "sheets": [], "artifacts": {},
            "run": {}}
```

- [ ] **Step 8: Verify the whole suite still passes**

Run: `python -m unittest discover tests`
Expected: PASS — the existing suite is untouched, plus the 7 new tests.

- [ ] **Step 9: Commit**

```bash
git add firebase.json .firebaserc main.py takeoff_fn/ requirements.txt tests/test_takeoff_fn_request.py
git commit -m "feat(fn): scaffold the takeoff callable with auth and payload validation"
```

---

### Task 2: Firestore record access and status transitions

**Files:**
- Create: `takeoff_fn/records.py`
- Test: `tests/test_takeoff_fn_records.py`

**Interfaces:**
- Consumes: `takeoff_fn.errors`, `takeoff_fn.config`.
- Produces:
  - `takeoff_fn.records.SourceFile(index: int, file_name: str, storage_url: str)` — frozen dataclass.
  - `takeoff_fn.records.TakeoffRecord(takeoff_id: str, customer_id: str, status: str, estimate_id: str | None, source_files: list[SourceFile])` — frozen dataclass.
  - `load_record(db, takeoff_id: str, customer_id: str, now_epoch_ms: int) -> TakeoffRecord`
  - `mark_processing(db, takeoff_id: str, now_epoch_ms: int) -> None`
  - `mark_awaiting_review(db, takeoff_id: str, document_json: str, now_epoch_ms: int) -> None`
  - `mark_failed(db, takeoff_id: str, message: str, now_epoch_ms: int) -> None`
  - `db` is anything exposing `.collection(name).document(id)` with `.get()` / `.update(dict)`, matching the `google-cloud-firestore` sync client.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_records.py`:

```python
import unittest

from takeoff_fn import config, records
from takeoff_fn.errors import FailedPrecondition, NotFound, PermissionDenied

NOW = 1_700_000_000_000


class FakeDoc:
    def __init__(self, data):
        self._data = data
        self.updates = []

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data)

    def get(self):
        return self

    def update(self, patch):
        self.updates.append(patch)
        if self._data is not None:
            self._data.update(patch)


class FakeCollection:
    def __init__(self, doc):
        self._doc = doc
        self.name = None

    def document(self, _id):
        return self._doc


class FakeDb:
    def __init__(self, data):
        self.doc = FakeDoc(data)
        self.collections = []

    def collection(self, name):
        self.collections.append(name)
        return FakeCollection(self.doc)


def _record_data(**overrides):
    data = {
        "customerId": "cus-1",
        "status": "queued",
        "estimateId": "est-1",
        "updatedAt": NOW - 1000,
        "sourceFiles": [
            {"fileName": "a.pdf", "storageUrl": "gs://b/estimate_images/cus-1/est-1/a.pdf"},
            {"fileName": "b.pdf", "storageUrl": "gs://b/estimate_images/cus-1/est-1/b.pdf"},
        ],
    }
    data.update(overrides)
    return data


class TestLoadRecord(unittest.TestCase):
    def test_a_queued_record_loads_with_indexed_source_files(self):
        db = FakeDb(_record_data())
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual(db.collections, [config.TAKEOFF_COLLECTION])
        self.assertEqual(rec.customer_id, "cus-1")
        self.assertEqual(rec.estimate_id, "est-1")
        self.assertEqual([s.index for s in rec.source_files], [0, 1])
        self.assertEqual([s.file_name for s in rec.source_files], ["a.pdf", "b.pdf"])

    def test_a_missing_document_is_not_found(self):
        with self.assertRaises(NotFound):
            records.load_record(FakeDb(None), "t1", "cus-1", NOW)

    def test_another_tenants_record_is_denied(self):
        db = FakeDb(_record_data(customerId="cus-2"))
        with self.assertRaises(PermissionDenied):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_live_processing_run_is_refused(self):
        db = FakeDb(_record_data(status="processing", updatedAt=NOW - 1000))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_stale_processing_run_may_be_restarted(self):
        stale = NOW - (config.STALE_PROCESSING_SECONDS * 1000) - 1
        db = FakeDb(_record_data(status="processing", updatedAt=stale))
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual(rec.status, "processing")

    def test_an_approved_record_is_refused(self):
        db = FakeDb(_record_data(status="approved"))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_record_with_no_source_files_is_a_failed_precondition(self):
        db = FakeDb(_record_data(sourceFiles=[]))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_source_file_without_a_storage_url_is_skipped(self):
        db = FakeDb(_record_data(sourceFiles=[
            {"fileName": "a.pdf"},
            {"fileName": "b.pdf", "storageUrl": "gs://b/estimate_images/cus-1/e/b.pdf"},
        ]))
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual([s.file_name for s in rec.source_files], ["b.pdf"])
        self.assertEqual([s.index for s in rec.source_files], [0])

    def test_a_missing_estimate_id_is_none_not_an_error(self):
        db = FakeDb(_record_data(estimateId=None))
        self.assertIsNone(records.load_record(db, "t1", "cus-1", NOW).estimate_id)


class TestStatusTransitions(unittest.TestCase):
    def test_mark_processing_writes_status_and_timestamps(self):
        db = FakeDb(_record_data())
        records.mark_processing(db, "t1", NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_PROCESSING,
            "startedAt": NOW, "updatedAt": NOW, "error": None}])

    def test_mark_awaiting_review_writes_the_document_and_clears_error(self):
        db = FakeDb(_record_data())
        records.mark_awaiting_review(db, "t1", '{"schemaVersion":1}', NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_AWAITING_REVIEW,
            "document": '{"schemaVersion":1}',
            "error": None, "updatedAt": NOW}])

    def test_mark_failed_writes_the_message(self):
        db = FakeDb(_record_data())
        records.mark_failed(db, "t1", "boom", NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_FAILED, "error": "boom", "updatedAt": NOW}])

    def test_mark_failed_truncates_a_very_long_message(self):
        db = FakeDb(_record_data())
        records.mark_failed(db, "t1", "x" * 5000, NOW)
        self.assertEqual(len(db.doc.updates[0]["error"]), records.MAX_ERROR_CHARS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_records -v`
Expected: FAIL with `ImportError: cannot import name 'records'`

- [ ] **Step 3: Write the implementation**

Create `takeoff_fn/records.py`:

```python
"""The takeoffs/{takeoffId} record: reading it, guarding it, moving its status.

Reading the record is also the authorization check — the caller names a
takeoffId, and the record says which tenant owns it. This mirrors rivet-mind's
own pattern in functions/src/estimates/attachment-download.ts:136.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from takeoff_fn import config
from takeoff_fn.errors import FailedPrecondition, NotFound, PermissionDenied

# Firestore rejects documents over 1 MB; an error string is never worth a
# meaningful fraction of that budget.
MAX_ERROR_CHARS = 2000


@dataclass(frozen=True)
class SourceFile:
    index: int
    file_name: str
    storage_url: str


@dataclass(frozen=True)
class TakeoffRecord:
    takeoff_id: str
    customer_id: str
    status: str
    estimate_id: Optional[str]
    source_files: list[SourceFile]


def _doc(db, takeoff_id: str):
    return db.collection(config.TAKEOFF_COLLECTION).document(takeoff_id)


def _source_files(raw) -> list[SourceFile]:
    """Index is assigned over the SURVIVING files, so it always matches the
    position used to build a storage path and can never leave a gap."""
    out: list[SourceFile] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        url = item.get("storageUrl")
        if not isinstance(url, str) or not url.strip():
            continue
        out.append(SourceFile(index=len(out),
                              file_name=str(item.get("fileName") or f"file_{len(out)}"),
                              storage_url=url.strip()))
    return out


def load_record(db, takeoff_id: str, customer_id: str,
                now_epoch_ms: int) -> TakeoffRecord:
    snapshot = _doc(db, takeoff_id).get()
    if not snapshot.exists:
        raise NotFound(f"No takeoff {takeoff_id}")

    data = snapshot.to_dict() or {}
    owner = data.get("customerId")
    if owner != customer_id:
        # Deliberately the same message as a missing record would give, so the
        # response cannot be used to probe which takeoff ids exist.
        raise PermissionDenied("Takeoff does not belong to this customer")

    status = str(data.get("status") or "")
    if status == config.STATUS_APPROVED:
        raise FailedPrecondition("Takeoff is already approved")
    if status == config.STATUS_PROCESSING:
        updated_at = data.get("updatedAt") or 0
        age_ms = now_epoch_ms - int(updated_at)
        if age_ms < config.STALE_PROCESSING_SECONDS * 1000:
            raise FailedPrecondition("Takeoff is already being measured")

    source_files = _source_files(data.get("sourceFiles"))
    if not source_files:
        raise FailedPrecondition("Takeoff has no source files to measure")

    estimate_id = data.get("estimateId")
    return TakeoffRecord(
        takeoff_id=takeoff_id,
        customer_id=str(owner),
        status=status,
        estimate_id=str(estimate_id) if estimate_id else None,
        source_files=source_files,
    )


def mark_processing(db, takeoff_id: str, now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_PROCESSING,
        "startedAt": now_epoch_ms,
        "updatedAt": now_epoch_ms,
        "error": None,
    })


def mark_awaiting_review(db, takeoff_id: str, document_json: str,
                         now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_AWAITING_REVIEW,
        "document": document_json,
        "error": None,
        "updatedAt": now_epoch_ms,
    })


def mark_failed(db, takeoff_id: str, message: str, now_epoch_ms: int) -> None:
    _doc(db, takeoff_id).update({
        "status": config.STATUS_FAILED,
        "error": str(message)[:MAX_ERROR_CHARS],
        "updatedAt": now_epoch_ms,
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_records -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add takeoff_fn/records.py tests/test_takeoff_fn_records.py
git commit -m "feat(fn): read the takeoff record and drive its status transitions"
```

---

### Task 3: Source file download and the tenant path boundary

**Files:**
- Create: `takeoff_fn/sources.py`
- Test: `tests/test_takeoff_fn_sources.py`

**Interfaces:**
- Consumes: `takeoff_fn.errors`, `takeoff_fn.records.SourceFile`.
- Produces:
  - `takeoff_fn.sources.parse_gs_uri(uri: str) -> tuple[str, str]` — returns `(bucket, object_path)`; raises `InvalidArgument`.
  - `takeoff_fn.sources.assert_customer_scoped(object_path: str, customer_id: str) -> None` — raises `PermissionDenied`.
  - `takeoff_fn.sources.DownloadedSource(index: int, file_name: str, local_path: str)` — frozen dataclass.
  - `takeoff_fn.sources.download_sources(bucket, source_files, dest_dir) -> tuple[list[DownloadedSource], list[dict]]` — returns downloads and warning dicts.
  - `takeoff_fn.sources.page_count(pdf_path: str) -> int`
  - `bucket` is anything exposing `.blob(path).download_to_filename(local)`, matching `google-cloud-storage`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_sources.py`:

```python
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import sources
from takeoff_fn.errors import InvalidArgument, PermissionDenied
from takeoff_fn.records import SourceFile


class FakeBlob:
    def __init__(self, path, payload):
        self.path = path
        self._payload = payload

    def download_to_filename(self, local):
        if self._payload is None:
            raise RuntimeError(f"no such object: {self.path}")
        Path(local).write_bytes(self._payload)


class FakeBucket:
    def __init__(self, objects):
        self._objects = objects
        self.requested = []

    def blob(self, path):
        self.requested.append(path)
        return FakeBlob(path, self._objects.get(path))


class TestParseGsUri(unittest.TestCase):
    def test_a_valid_uri_splits_into_bucket_and_object(self):
        self.assertEqual(
            sources.parse_gs_uri("gs://my-bucket/estimate_images/cus-1/est-1/a.pdf"),
            ("my-bucket", "estimate_images/cus-1/est-1/a.pdf"))

    def test_a_non_gs_scheme_is_invalid(self):
        for uri in ("https://example.com/a.pdf", "estimate_images/cus-1/a.pdf", ""):
            with self.subTest(uri=uri):
                with self.assertRaises(InvalidArgument):
                    sources.parse_gs_uri(uri)

    def test_a_uri_with_no_object_path_is_invalid(self):
        with self.assertRaises(InvalidArgument):
            sources.parse_gs_uri("gs://my-bucket")


class TestCustomerScope(unittest.TestCase):
    def test_a_path_containing_the_customer_segment_is_allowed(self):
        sources.assert_customer_scoped(
            "estimate_images/cus-1/est-1/a.pdf", "cus-1")
        sources.assert_customer_scoped(
            "customers/cus-1/takeoffs/t1/a.pdf", "cus-1")

    def test_another_tenants_path_is_denied(self):
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-2/est-1/a.pdf", "cus-1")

    def test_a_prefix_collision_is_denied(self):
        # "cus-10" must not satisfy the boundary for "cus-1".
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-10/est-1/a.pdf", "cus-1")

    def test_a_traversal_segment_is_denied(self):
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-1/../cus-2/a.pdf", "cus-1")


class TestDownloadSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_files_download_to_index_named_paths(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/a.pdf": b"%PDF-1.4 A"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-1/e/a.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(warnings, [])
        self.assertEqual(len(got), 1)
        self.assertEqual(Path(got[0].local_path).read_bytes(), b"%PDF-1.4 A")
        self.assertTrue(Path(got[0].local_path).name.startswith("file_00"))

    def test_a_failed_download_warns_and_the_others_survive(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/b.pdf": b"%PDF-1.4 B"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-1/e/a.pdf"),
             SourceFile(1, "b.pdf", "gs://b/estimate_images/cus-1/e/b.pdf")],
            self.tmp, "cus-1")
        self.assertEqual([s.file_name for s in got], ["b.pdf"])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["warning_code"], "TAKEOFF_SOURCE_UNREADABLE")

    def test_another_tenants_file_warns_rather_than_downloading(self):
        bucket = FakeBucket({"estimate_images/cus-2/e/a.pdf": b"%PDF"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-2/e/a.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(got, [])
        self.assertEqual(warnings[0]["warning_code"], "TAKEOFF_SOURCE_FORBIDDEN")
        self.assertEqual(bucket.requested, [])

    def test_a_pdf_name_is_sanitised_out_of_the_local_path(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/x.pdf": b"%PDF"})
        got, _ = sources.download_sources(
            bucket,
            [SourceFile(0, "../../etc/passwd", "gs://b/estimate_images/cus-1/e/x.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(Path(got[0].local_path).parent, Path(self.tmp))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_sources -v`
Expected: FAIL with `ImportError: cannot import name 'sources'`

- [ ] **Step 3: Write the implementation**

Create `takeoff_fn/sources.py`:

```python
"""Fetching the drawings a takeoff points at.

The tenant boundary here is the same one rivet-mind enforces on downloads
(functions/src/estimates/attachment-download.ts:89-95): an object path is only
readable if it actually sits under the calling tenant's segment. The record
itself is tenant-checked before we get here, but a storageUrl is data a client
wrote, so it is checked again rather than trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from takeoff_fn.errors import InvalidArgument, PermissionDenied
from takeoff_fn.records import SourceFile

GS_SCHEME = "gs://"


@dataclass(frozen=True)
class DownloadedSource:
    index: int
    file_name: str
    local_path: str


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not isinstance(uri, str) or not uri.startswith(GS_SCHEME):
        raise InvalidArgument(f"Not a gs:// URI: {uri!r}")
    remainder = uri[len(GS_SCHEME):]
    bucket, _, object_path = remainder.partition("/")
    if not bucket or not object_path:
        raise InvalidArgument(f"Incomplete gs:// URI: {uri!r}")
    return bucket, object_path


def assert_customer_scoped(object_path: str, customer_id: str) -> None:
    """The path must contain the tenant as a whole segment.

    Segment equality, not a startswith: a prefix test lets customer "cus-1"
    reach "cus-10"'s objects. A ".." anywhere is refused outright rather than
    normalised, because normalising invites disagreement with the storage
    layer about what the path means.
    """
    segments = object_path.split("/")
    if ".." in segments:
        raise PermissionDenied("Source path contains a traversal segment")
    if customer_id not in segments:
        raise PermissionDenied("Source file does not belong to this customer")


def _local_name(index: int, file_name: str) -> str:
    """A flat, collision-free name under our own working directory.

    The record's fileName is client-supplied, so only its suffix is trusted
    and even that is bounded; the stem is our index.
    """
    suffix = Path(str(file_name)).suffix.lower()
    if suffix != ".pdf":
        suffix = ".pdf"
    return f"file_{index:02d}{suffix}"


def download_sources(bucket, source_files, dest_dir: str,
                     customer_id: str) -> tuple[list[DownloadedSource], list[dict]]:
    """Download what we can. A file we cannot read warns and is skipped.

    One corrupt file in a three-file set must not lose the two good plans, so
    failure here is per-file and never raises.
    """
    downloaded: list[DownloadedSource] = []
    warnings: list[dict] = []
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    for source in source_files:
        try:
            _, object_path = parse_gs_uri(source.storage_url)
            assert_customer_scoped(object_path, customer_id)
        except PermissionDenied as exc:
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_FORBIDDEN", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue
        except InvalidArgument as exc:
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_UNREADABLE", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue

        local = str(Path(dest_dir) / _local_name(source.index, source.file_name))
        try:
            bucket.blob(object_path).download_to_filename(local)
        except Exception as exc:  # noqa: BLE001 - any storage failure is per-file
            warnings.append({
                "warning_code": "TAKEOFF_SOURCE_UNREADABLE", "severity": "error",
                "message": f"{source.file_name}: {exc}", "page_number": None})
            continue

        downloaded.append(DownloadedSource(
            index=source.index, file_name=source.file_name, local_path=local))

    return downloaded, warnings


def page_count(pdf_path: str) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_sources -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Commit**

```bash
git add takeoff_fn/sources.py tests/test_takeoff_fn_sources.py
git commit -m "feat(fn): download source drawings behind a tenant path boundary"
```

---

### Task 4: Sheet collection from a finished output tree

**Files:**
- Create: `takeoff_fn/sheets.py`
- Test: `tests/test_takeoff_fn_sheets.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `takeoff_fn.sheets.page_dirs(out_dir: str) -> list[tuple[int, str]]` — `(page_number, path)` sorted by page number.
  - `takeoff_fn.sheets.has_floor_plan(page_dir: str) -> bool`
  - `takeoff_fn.sheets.sheet_id(file_index: int, page_number: int) -> str` — returns `"sheet_{file:02d}_{page:02d}"`.
  - `takeoff_fn.sheets.collect_sheets(out_dir, file_index, file_name, svg_path_for) -> tuple[list[dict], list[dict]]` — returns `(sheets, skipped)`. `svg_path_for` is `Callable[[int], str]` taking a page number.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_sheets.py`:

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import sheets


def _write_page(out_dir, page_number, region_types, takeoff=None):
    page_dir = Path(out_dir) / "pages" / f"page_{page_number:02d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "regions.json").write_text(json.dumps({
        "page_number": page_number,
        "regions": [{"region_id": f"r{i}", "region_type": t, "bbox": [0, 0, 1, 1]}
                    for i, t in enumerate(region_types)],
    }), encoding="utf-8")
    if takeoff is not None:
        (page_dir / "takeoff.json").write_text(json.dumps(takeoff), encoding="utf-8")
    return str(page_dir)


def _takeoff(page_number):
    return {"schema_version": 1, "page_number": page_number,
            "page_frame": {"width_px": 100, "height_px": 200},
            "rooms": [], "openings": [], "warnings": []}


class SheetsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def collect(self, file_index=0, file_name="plans.pdf"):
        return sheets.collect_sheets(
            self.tmp, file_index, file_name,
            svg_path_for=lambda p: f"prefix/file_{file_index:02d}/page_{p:02d}/page.svg")


class TestPageDiscovery(SheetsTestCase):
    def test_page_dirs_are_returned_in_page_order(self):
        _write_page(self.tmp, 10, ["floor_plan"], _takeoff(10))
        _write_page(self.tmp, 2, ["floor_plan"], _takeoff(2))
        self.assertEqual([n for n, _ in sheets.page_dirs(self.tmp)], [2, 10])

    def test_a_tree_with_no_pages_directory_yields_nothing(self):
        self.assertEqual(sheets.page_dirs(self.tmp), [])


class TestFloorPlanFilter(SheetsTestCase):
    def test_a_floor_plan_page_becomes_a_sheet(self):
        _write_page(self.tmp, 1, ["floor_plan", "title_block"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(len(found), 1)
        self.assertEqual(skipped, [])

    def test_an_elevation_only_page_is_skipped_with_a_reason(self):
        _write_page(self.tmp, 1, ["elevation", "title_block"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_floor_plan_region"}])

    def test_a_floor_plan_page_with_no_takeoff_json_is_skipped(self):
        _write_page(self.tmp, 1, ["floor_plan"], takeoff=None)
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_takeoff_document"}])

    def test_a_page_with_no_regions_json_is_skipped(self):
        (Path(self.tmp) / "pages" / "page_01").mkdir(parents=True)
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_regions_document"}])


class TestSheetIdentity(SheetsTestCase):
    def test_ids_are_unique_across_source_files(self):
        _write_page(self.tmp, 1, ["floor_plan"], _takeoff(1))
        a, _ = self.collect(file_index=0)
        b, _ = self.collect(file_index=1)
        self.assertEqual(a[0]["sheet_id"], "sheet_00_01")
        self.assertEqual(b[0]["sheet_id"], "sheet_01_01")
        self.assertNotEqual(a[0]["sheet_id"], b[0]["sheet_id"])

    def test_source_file_and_label_and_svg_path_are_injected(self):
        _write_page(self.tmp, 3, ["floor_plan"], _takeoff(3))
        found, _ = self.collect(file_index=2, file_name="WD03.pdf")
        sheet = found[0]
        self.assertEqual(sheet["source_file_id"], "file_02")
        self.assertEqual(sheet["source_file_name"], "WD03.pdf")
        self.assertEqual(sheet["label"], "WD03.pdf — page 3")
        self.assertEqual(sheet["plan_svg_url"], "prefix/file_02/page_03/page.svg")

    def test_the_takeoff_payload_is_preserved_verbatim(self):
        _write_page(self.tmp, 1, ["floor_plan"], _takeoff(1))
        sheet = self.collect()[0][0]
        self.assertEqual(sheet["schema_version"], 1)
        self.assertEqual(sheet["page_number"], 1)
        self.assertEqual(sheet["page_frame"], {"width_px": 100, "height_px": 200})

    def test_structured_warnings_survive_unflattened(self):
        payload = _takeoff(1)
        payload["warnings"] = [{"warning_code": "TAKEOFF_NO_SCALE",
                                "severity": "warning", "message": "no scale",
                                "page_number": 1}]
        _write_page(self.tmp, 1, ["floor_plan"], payload)
        sheet = self.collect()[0][0]
        self.assertEqual(sheet["warnings"][0]["warning_code"], "TAKEOFF_NO_SCALE")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_sheets -v`
Expected: FAIL with `ImportError: cannot import name 'sheets'`

- [ ] **Step 3: Write the implementation**

Create `takeoff_fn/sheets.py`:

```python
"""Turning a finished run_extract output tree into wire sheets.

Only pages the region classifier called a floor_plan become sheets: an
elevation or a title-block page has nothing a reviewer can check. Skipped
pages are reported rather than dropped silently, so a wrongly-skipped plan is
diagnosable from run.json.

The three fields injected here — sheet_id, source_file_id, label — are ones
rivet-mind's parser currently synthesises. Theirs derives sheet_id from the
page number alone, which collides across source files; ours is unique.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def page_dirs(out_dir: str) -> list[tuple[int, str]]:
    pages_root = Path(out_dir) / "pages"
    if not pages_root.is_dir():
        return []
    found: list[tuple[int, str]] = []
    for entry in pages_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("page_"):
            continue
        try:
            found.append((int(entry.name[len("page_"):]), str(entry)))
        except ValueError:
            continue
    return sorted(found)


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def has_floor_plan(page_dir: str) -> bool:
    document = _read_json(Path(page_dir) / "regions.json")
    if not isinstance(document, dict):
        return False
    return any(r.get("region_type") == "floor_plan"
               for r in document.get("regions", [])
               if isinstance(r, dict))


def sheet_id(file_index: int, page_number: int) -> str:
    return f"sheet_{file_index:02d}_{page_number:02d}"


def collect_sheets(out_dir: str, file_index: int, file_name: str,
                   svg_path_for: Callable[[int], str]
                   ) -> tuple[list[dict], list[dict]]:
    found: list[dict] = []
    skipped: list[dict] = []

    for page_number, page_dir in page_dirs(out_dir):
        regions = _read_json(Path(page_dir) / "regions.json")
        if not isinstance(regions, dict):
            skipped.append({"page_number": page_number,
                            "reason": "no_regions_document"})
            continue
        if not has_floor_plan(page_dir):
            skipped.append({"page_number": page_number,
                            "reason": "no_floor_plan_region"})
            continue

        payload = _read_json(Path(page_dir) / "takeoff.json")
        if not isinstance(payload, dict):
            skipped.append({"page_number": page_number,
                            "reason": "no_takeoff_document"})
            continue

        sheet = dict(payload)
        sheet["sheet_id"] = sheet_id(file_index, page_number)
        sheet["source_file_id"] = f"file_{file_index:02d}"
        sheet["source_file_name"] = file_name
        sheet["label"] = f"{file_name} — page {page_number}"
        sheet["plan_svg_url"] = svg_path_for(page_number)
        found.append(sheet)

    return found, skipped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_sheets -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Commit**

```bash
git add takeoff_fn/sheets.py tests/test_takeoff_fn_sheets.py
git commit -m "feat(fn): collect floor-plan sheets from a finished output tree"
```

---

### Task 5: Artefact selection and upload

**Files:**
- Create: `takeoff_fn/artifacts.py`
- Test: `tests/test_takeoff_fn_artifacts.py`

**Interfaces:**
- Consumes: `takeoff_fn.config`.
- Produces:
  - `takeoff_fn.artifacts.run_prefix(customer_id: str, takeoff_id: str) -> str`
  - `takeoff_fn.artifacts.page_prefix(prefix: str, file_index: int, page_number: int) -> str`
  - `takeoff_fn.artifacts.object_path(prefix, file_index, page_number, name) -> str`
  - `takeoff_fn.artifacts.artifact_names(debug: bool) -> tuple[str, ...]`
  - `takeoff_fn.artifacts.upload_page(bucket, page_dir, prefix, file_index, page_number, debug) -> dict[str, str]`
  - `takeoff_fn.artifacts.upload_run_files(bucket, out_dir, prefix, file_index) -> dict[str, str]`
  - `takeoff_fn.artifacts.upload_json(bucket, prefix, name, payload) -> str`
  - `bucket` exposes `.blob(path)` returning an object with `.upload_from_filename(path, content_type=...)` and `.upload_from_string(data, content_type=...)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_artifacts.py`:

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import artifacts, config


class FakeBlob:
    def __init__(self, path, sink):
        self.path = path
        self._sink = sink
        self.content_type = None

    def upload_from_filename(self, local, content_type=None):
        self.content_type = content_type
        self._sink[self.path] = Path(local).read_bytes()

    def upload_from_string(self, data, content_type=None):
        self.content_type = content_type
        self._sink[self.path] = data.encode("utf-8") if isinstance(data, str) else data


class FakeBucket:
    def __init__(self):
        self.uploaded = {}
        self.blobs = []

    def blob(self, path):
        blob = FakeBlob(path, self.uploaded)
        self.blobs.append(blob)
        return blob


class TestPaths(unittest.TestCase):
    def test_the_run_prefix_is_customer_scoped(self):
        self.assertEqual(artifacts.run_prefix("cus-1", "t1"),
                         "customers/cus-1/takeoffs/t1")

    def test_page_paths_are_keyed_by_file_and_page(self):
        prefix = artifacts.run_prefix("cus-1", "t1")
        self.assertEqual(
            artifacts.object_path(prefix, 2, 7, "page.svg"),
            "customers/cus-1/takeoffs/t1/file_02/page_07/page.svg")


class TestArtifactSelection(unittest.TestCase):
    def test_standard_run_excludes_the_heavy_trace(self):
        names = artifacts.artifact_names(debug=False)
        self.assertEqual(names, config.STANDARD_ARTIFACTS)
        self.assertNotIn("debug_trace.json", names)

    def test_debug_run_adds_the_trace_and_viewer(self):
        names = artifacts.artifact_names(debug=True)
        self.assertIn("debug_trace.json", names)
        self.assertIn("debug_viewer.html", names)
        for name in config.STANDARD_ARTIFACTS:
            self.assertIn(name, names)


class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bucket = FakeBucket()
        self.prefix = artifacts.run_prefix("cus-1", "t1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _page_dir(self, names):
        page_dir = Path(self.tmp) / "pages" / "page_01"
        page_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            (page_dir / name).write_bytes(b"x")
        return str(page_dir)


class TestUploadPage(UploadTestCase):
    def test_present_standard_artifacts_upload_and_are_mapped(self):
        page_dir = self._page_dir(["page.svg", "takeoff.json", "render.png"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertEqual(
            got["page.svg"],
            "customers/cus-1/takeoffs/t1/file_00/page_01/page.svg")
        self.assertIn("takeoff.json", got)
        self.assertEqual(len(self.bucket.uploaded), 3)

    def test_absent_artifacts_are_skipped_without_error(self):
        page_dir = self._page_dir(["page.svg"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertEqual(list(got), ["page.svg"])

    def test_the_trace_is_not_uploaded_unless_debug_is_set(self):
        page_dir = self._page_dir(["page.svg", "debug_trace.json"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertNotIn("debug_trace.json", got)

    def test_the_trace_is_uploaded_when_debug_is_set(self):
        page_dir = self._page_dir(["page.svg", "debug_trace.json"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=True)
        self.assertIn("debug_trace.json", got)

    def test_content_types_are_set_so_the_browser_renders_the_svg(self):
        page_dir = self._page_dir(["page.svg", "takeoff.json", "render.png"])
        artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                              debug=False)
        by_path = {b.path: b.content_type for b in self.bucket.blobs}
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/page.svg"],
            "image/svg+xml")
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/takeoff.json"],
            "application/json")
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/render.png"],
            "image/png")


class TestUploadRunFiles(UploadTestCase):
    def test_run_root_files_upload_under_the_file_prefix(self):
        Path(self.tmp, "summary.json").write_text("{}", encoding="utf-8")
        Path(self.tmp, "warnings.json").write_text("[]", encoding="utf-8")
        got = artifacts.upload_run_files(self.bucket, self.tmp, self.prefix, 1)
        self.assertEqual(got["summary.json"],
                         "customers/cus-1/takeoffs/t1/file_01/summary.json")
        self.assertEqual(len(self.bucket.uploaded), 2)


class TestUploadJson(UploadTestCase):
    def test_a_dict_is_written_as_pretty_json_at_the_run_root(self):
        path = artifacts.upload_json(self.bucket, self.prefix, "run.json",
                                     {"pagesProcessed": 2})
        self.assertEqual(path, "customers/cus-1/takeoffs/t1/run.json")
        self.assertEqual(
            json.loads(self.bucket.uploaded[path].decode("utf-8")),
            {"pagesProcessed": 2})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_artifacts -v`
Expected: FAIL with `ImportError: cannot import name 'artifacts'`

- [ ] **Step 3: Write the implementation**

Create `takeoff_fn/artifacts.py`:

```python
"""Uploading a run's outputs to Cloud Storage.

Layout is customers/{customerId}/takeoffs/{takeoffId}/file_NN/page_NN/. The
file segment matters: a takeoff may carry several PDFs, and without it page 1
of the second drawing would overwrite page 1 of the first.

Content types are set explicitly. page.svg is loaded by the review UI as an
<img src>, and a browser will not render an SVG served as
application/octet-stream.
"""
from __future__ import annotations

import json
from pathlib import Path

from takeoff_fn import config

CONTENT_TYPES = {
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".png": "image/png",
    ".html": "text/html",
}
DEFAULT_CONTENT_TYPE = "application/octet-stream"


def run_prefix(customer_id: str, takeoff_id: str) -> str:
    return f"customers/{customer_id}/takeoffs/{takeoff_id}"


def page_prefix(prefix: str, file_index: int, page_number: int) -> str:
    return f"{prefix}/file_{file_index:02d}/page_{page_number:02d}"


def object_path(prefix: str, file_index: int, page_number: int,
                name: str) -> str:
    return f"{page_prefix(prefix, file_index, page_number)}/{name}"


def artifact_names(debug: bool) -> tuple[str, ...]:
    if debug:
        return config.STANDARD_ARTIFACTS + config.DEBUG_ARTIFACTS
    return config.STANDARD_ARTIFACTS


def _content_type(name: str) -> str:
    return CONTENT_TYPES.get(Path(name).suffix.lower(), DEFAULT_CONTENT_TYPE)


def _upload_file(bucket, local: Path, remote: str) -> None:
    bucket.blob(remote).upload_from_filename(
        str(local), content_type=_content_type(local.name))


def upload_page(bucket, page_dir: str, prefix: str, file_index: int,
                page_number: int, debug: bool) -> dict[str, str]:
    """Upload one page's artefacts. Absent files are skipped, not errors:
    page.svg only exists with write_svg, debug_* only with debug, and
    region_crops/ is absent on a classification cache hit."""
    uploaded: dict[str, str] = {}
    for name in artifact_names(debug):
        local = Path(page_dir) / name
        if not local.is_file():
            continue
        remote = object_path(prefix, file_index, page_number, name)
        _upload_file(bucket, local, remote)
        uploaded[name] = remote
    return uploaded


def upload_run_files(bucket, out_dir: str, prefix: str,
                     file_index: int) -> dict[str, str]:
    """summary.json and warnings.json live at the run root, and run_extract
    writes one run per source PDF, so they are stored under the file prefix."""
    uploaded: dict[str, str] = {}
    for name in config.RUN_ARTIFACTS:
        local = Path(out_dir) / name
        if not local.is_file():
            continue
        remote = f"{prefix}/file_{file_index:02d}/{name}"
        _upload_file(bucket, local, remote)
        uploaded[name] = remote
    return uploaded


def upload_json(bucket, prefix: str, name: str, payload) -> str:
    remote = f"{prefix}/{name}"
    bucket.blob(remote).upload_from_string(
        json.dumps(payload, indent=2, default=str),
        content_type="application/json")
    return remote
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_artifacts -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Commit**

```bash
git add takeoff_fn/artifacts.py tests/test_takeoff_fn_artifacts.py
git commit -m "feat(fn): upload run artefacts to a customer-scoped storage prefix"
```

---

### Task 6: Runner orchestration and failure semantics

**Files:**
- Create: `takeoff_fn/runner.py`
- Test: `tests/test_takeoff_fn_runner.py`

**Interfaces:**
- Consumes: `request.TakeoffRequest`, `records.*`, `sources.*`, `sheets.collect_sheets`, `artifacts.*`, `config`.
- Produces:
  - `takeoff_fn.runner.RunResult(sheets: list[dict], artifacts: dict, run: dict, document: dict)` — frozen dataclass.
  - `takeoff_fn.runner.run_measurement(request, *, db, bucket, extract_fn=None, page_count_fn=None, now_fn=None, workdir=None) -> RunResult`
  - `extract_fn` has `run_extract`'s keyword signature and returns the output directory path.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_runner.py`:

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import config, runner
from takeoff_fn.errors import TakeoffFnError
from takeoff_fn.request import TakeoffRequest

NOW = 1_700_000_000_000


class FakeBlob:
    def __init__(self, path, sink, objects):
        self.path, self._sink, self._objects = path, sink, objects

    def download_to_filename(self, local):
        if self.path not in self._objects:
            raise RuntimeError(f"no such object: {self.path}")
        Path(local).write_bytes(self._objects[self.path])

    def upload_from_filename(self, local, content_type=None):
        self._sink[self.path] = Path(local).read_bytes()

    def upload_from_string(self, data, content_type=None):
        self._sink[self.path] = data.encode("utf-8") if isinstance(data, str) else data


class FakeBucket:
    def __init__(self, objects=None):
        self.uploaded, self._objects = {}, objects or {}

    def blob(self, path):
        return FakeBlob(path, self.uploaded, self._objects)


class FakeDoc:
    def __init__(self, data):
        self._data, self.updates = data, []

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data)

    def get(self):
        return self

    def update(self, patch):
        self.updates.append(patch)
        self._data.update(patch)


class FakeDb:
    def __init__(self, data):
        self.doc = FakeDoc(data)

    def collection(self, _name):
        class _C:
            def __init__(self, doc):
                self._doc = doc

            def document(self, _id):
                return self._doc
        return _C(self.doc)


def _record(source_urls):
    return {
        "customerId": "cus-1", "status": "queued", "estimateId": "est-1",
        "updatedAt": NOW - 1000,
        "sourceFiles": [{"fileName": f"f{i}.pdf", "storageUrl": u}
                        for i, u in enumerate(source_urls)],
    }


def _make_extract(pages):
    """pages: {page_number: (region_types, takeoff_dict | None)}"""
    def _extract(**kwargs):
        out_dir = kwargs["out_parent"] + "/run"
        for number, (types, takeoff) in pages.items():
            page_dir = Path(out_dir) / "pages" / f"page_{number:02d}"
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "regions.json").write_text(json.dumps({
                "page_number": number,
                "regions": [{"region_type": t} for t in types]}), encoding="utf-8")
            (page_dir / "page.svg").write_text("<svg/>", encoding="utf-8")
            if takeoff is not None:
                (page_dir / "takeoff.json").write_text(json.dumps(takeoff),
                                                       encoding="utf-8")
        Path(out_dir, "summary.json").write_text("{}", encoding="utf-8")
        Path(out_dir, "warnings.json").write_text("[]", encoding="utf-8")
        return out_dir
    return _extract


def _takeoff(page_number):
    return {"schema_version": 1, "page_number": page_number,
            "rooms": [], "openings": [], "warnings": []}


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_it(self, db, bucket, extract, **kwargs):
        return runner.run_measurement(
            self.request, db=db, bucket=bucket, extract_fn=extract,
            page_count_fn=lambda _p: 1, now_fn=lambda: NOW,
            workdir=self.tmp, **kwargs)


class TestHappyPath(RunnerTestCase):
    def test_a_floor_plan_page_produces_a_sheet_and_awaiting_review(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))

        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.sheets[0]["sheet_id"], "sheet_00_01")
        statuses = [u["status"] for u in db.doc.updates]
        self.assertEqual(statuses, [config.STATUS_PROCESSING,
                                    config.STATUS_AWAITING_REVIEW])

    def test_the_document_written_to_firestore_is_a_json_string(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({1: (["floor_plan"], _takeoff(1))}))

        raw = db.doc.updates[-1]["document"]
        self.assertIsInstance(raw, str)
        parsed = json.loads(raw)
        self.assertEqual(parsed["schemaVersion"], 1)
        self.assertEqual(len(parsed["sheets"]), 1)

    def test_the_svg_path_on_the_sheet_matches_where_it_was_uploaded(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))
        svg_path = result.sheets[0]["plan_svg_url"]
        self.assertIn(svg_path, bucket.uploaded)

    def test_the_working_directory_is_cleaned_up(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({1: (["floor_plan"], _takeoff(1))}))
        leftovers = list(Path(self.tmp).iterdir())
        self.assertEqual(leftovers, [])


class TestFiltering(RunnerTestCase):
    def test_an_elevation_page_is_skipped_and_recorded(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket, _make_extract({
            1: (["floor_plan"], _takeoff(1)),
            2: (["elevation"], _takeoff(2)),
        }))
        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.run["pagesSkipped"][0]["page_number"], 2)

    def test_a_skipped_page_uploads_no_artifacts(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({2: (["elevation"], _takeoff(2))}))
        self.assertNotIn(
            "customers/cus-1/takeoffs/t1/file_00/page_02/page.svg",
            bucket.uploaded)


class TestPartialFailure(RunnerTestCase):
    def test_one_unreadable_file_warns_and_the_other_still_measures(self):
        good = "gs://b/estimate_images/cus-1/est-1/f1.pdf"
        bad = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([bad, good]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f1.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))

        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)
        codes = [w["warning_code"] for w in result.run["warnings"]]
        self.assertIn("TAKEOFF_SOURCE_UNREADABLE", codes)

    def test_no_readable_files_fails_the_takeoff(self):
        db = FakeDb(_record(["gs://b/estimate_images/cus-1/est-1/f0.pdf"]))
        bucket = FakeBucket({})
        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket, _make_extract({}))
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)

    def test_no_floor_plan_anywhere_fails_the_takeoff(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket,
                        _make_extract({1: (["elevation"], _takeoff(1))}))
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)

    def test_an_extraction_crash_marks_failed_and_reraises(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})

        def _boom(**_kwargs):
            raise RuntimeError("detector exploded")

        with self.assertRaises(RuntimeError):
            self.run_it(db, bucket, _boom)
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)
        self.assertIn("detector exploded", db.doc.updates[-1]["error"])


class TestExtractionOptions(RunnerTestCase):
    def test_the_scale_prompt_is_disabled_and_the_svg_is_requested(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        seen = {}

        base = _make_extract({1: (["floor_plan"], _takeoff(1))})

        def _spy(**kwargs):
            seen.update(kwargs)
            return base(**kwargs)

        self.run_it(db, bucket, _spy)
        self.assertFalse(seen["allow_scale_prompt"])
        self.assertTrue(seen["write_svg"])
        self.assertFalse(seen["debug"])
        self.assertEqual(seen["page_indices"], [0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_runner -v`
Expected: FAIL with `ImportError: cannot import name 'runner'`

- [ ] **Step 3: Write the implementation**

Create `takeoff_fn/runner.py`:

```python
"""Orchestration: record -> download -> extract -> filter -> upload -> record.

Every collaborator is injected so the whole flow is unit-testable without
Firestore, Storage, or a PDF. The default extract_fn is pipeline.run_extract
itself — the function is a transport wrapper, and calling anything else would
put the deployed detector on a different code path from the CLI that
tools/regress.py validates.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from takeoff_fn import artifacts, config, records, sheets, sources
from takeoff_fn.errors import FailedPrecondition
from takeoff_fn.request import TakeoffRequest


@dataclass(frozen=True)
class RunResult:
    sheets: list[dict]
    artifacts: dict
    run: dict
    document: dict = field(default_factory=dict)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _document(sheet_list: list[dict]) -> dict:
    """The TakeoffDocument rivet-mind persists.

    `overrides` is seeded empty rather than omitted: their review UI reads it
    unconditionally, and an absent key is worse for a consumer than an empty
    one.
    """
    return {
        "schemaVersion": 1,
        "sheets": sheet_list,
        "overrides": {"rooms": {}, "openings": {}, "addedOpenings": [],
                      "addedRooms": [], "heights": {}},
    }


def run_measurement(request: TakeoffRequest, *, db, bucket,
                    extract_fn=None, page_count_fn=None, now_fn=None,
                    workdir: Optional[str] = None) -> RunResult:
    if extract_fn is None:
        from pipeline import run_extract as extract_fn  # noqa: N806
    if page_count_fn is None:
        page_count_fn = sources.page_count
    if now_fn is None:
        now_fn = _now_ms

    started_at = now_fn()
    record = records.load_record(db, request.takeoff_id, request.customer_id,
                                 started_at)
    records.mark_processing(db, request.takeoff_id, started_at)

    owns_workdir = workdir is None
    work_root = workdir or tempfile.mkdtemp(prefix="takeoff-")
    prefix = artifacts.run_prefix(request.customer_id, request.takeoff_id)

    all_sheets: list[dict] = []
    all_artifacts: dict[str, dict] = {}
    skipped: list[dict] = []
    warnings: list[dict] = []

    try:
        downloads, download_warnings = sources.download_sources(
            bucket, record.source_files, str(Path(work_root) / "sources"),
            request.customer_id)
        warnings.extend(download_warnings)

        if not downloads:
            raise FailedPrecondition(
                "No source drawing could be read for this takeoff")

        for source in downloads:
            out_parent = str(Path(work_root) / f"out_{source.index:02d}")
            Path(out_parent).mkdir(parents=True, exist_ok=True)

            out_dir = extract_fn(
                pdf_path=source.local_path,
                page_indices=list(range(page_count_fn(source.local_path))),
                out_parent=out_parent,
                skip_gemini=False,
                disable_rooms=False,
                disable_windows=False,
                debug=request.debug,
                refresh_regions=False,
                write_svg=True,
                # Without this, an unresolvable scale blocks on input() inside
                # a Cloud Function until the timeout kills the instance.
                allow_scale_prompt=False,
                ceiling_height=None,
                door_height=None,
                window_height=None,
            )

            def _svg_path_for(page_number: int, _i=source.index) -> str:
                return artifacts.object_path(prefix, _i, page_number,
                                             config.SVG_ARTIFACT)

            found, page_skips = sheets.collect_sheets(
                out_dir, source.index, source.file_name, _svg_path_for)
            skipped.extend({**s, "source_file_id": f"file_{source.index:02d}"}
                           for s in page_skips)

            for sheet in found:
                uploaded = artifacts.upload_page(
                    bucket, str(Path(out_dir) / "pages"
                                / f"page_{sheet['page_number']:02d}"),
                    prefix, source.index, sheet["page_number"], request.debug)
                all_artifacts[sheet["sheet_id"]] = uploaded

            all_artifacts.setdefault("_run", {}).update(
                artifacts.upload_run_files(bucket, out_dir, prefix,
                                           source.index))
            all_sheets.extend(found)

        if not all_sheets:
            raise FailedPrecondition(
                "No floor plan was found in any source drawing")

        finished_at = now_fn()
        run_block = {
            "startedAt": started_at,
            "finishedAt": finished_at,
            "durationMs": finished_at - started_at,
            "sourceFiles": len(record.source_files),
            "sourceFilesRead": len(downloads),
            "pagesMeasured": len(all_sheets),
            "pagesSkipped": skipped,
            "warnings": warnings,
            "debug": request.debug,
        }
        run_block["manifest"] = artifacts.upload_json(
            bucket, prefix, "run.json", run_block)

        document = _document(all_sheets)
        records.mark_awaiting_review(
            db, request.takeoff_id,
            json.dumps(document, default=str), finished_at)

        return RunResult(sheets=all_sheets,
                         artifacts={"prefix": prefix, "bySheet": all_artifacts},
                         run=run_block, document=document)

    except Exception as exc:  # noqa: BLE001 - the record must never lie
        records.mark_failed(db, request.takeoff_id, str(exc) or repr(exc),
                            now_fn())
        traceback.print_exc()
        raise
    finally:
        if owns_workdir:
            shutil.rmtree(work_root, ignore_errors=True)
        else:
            for child in Path(work_root).iterdir():
                shutil.rmtree(child, ignore_errors=True) if child.is_dir() \
                    else child.unlink(missing_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_runner -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover tests`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add takeoff_fn/runner.py tests/test_takeoff_fn_runner.py
git commit -m "feat(fn): orchestrate measurement with per-file failure tolerance"
```

---

### Task 7: Wire the runner into the callable

**Files:**
- Modify: `main.py`
- Test: `tests/test_takeoff_fn_main.py`

**Interfaces:**
- Consumes: `runner.run_measurement`, `request.parse_request`, `errors.TakeoffFnError`.
- Produces:
  - `main.build_response(request, result) -> dict` — importable without the Firebase SDK being configured.
  - `main.error_code(exc) -> FunctionsErrorCode`

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_main.py`:

```python
import unittest

from takeoff_fn.errors import NotFound, PermissionDenied, TakeoffFnError
from takeoff_fn.request import TakeoffRequest
from takeoff_fn.runner import RunResult


class TestBuildResponse(unittest.TestCase):
    def setUp(self):
        import main
        self.main = main

    def test_the_response_carries_sheets_artifacts_and_run(self):
        request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)
        result = RunResult(
            sheets=[{"sheet_id": "sheet_00_01", "page_number": 1}],
            artifacts={"prefix": "customers/cus-1/takeoffs/t1", "bySheet": {}},
            run={"pagesMeasured": 1})
        body = self.main.build_response(request, result)
        self.assertEqual(body["takeoffId"], "t1")
        self.assertEqual(body["sheets"][0]["sheet_id"], "sheet_00_01")
        self.assertEqual(body["artifacts"]["prefix"],
                         "customers/cus-1/takeoffs/t1")
        self.assertEqual(body["run"]["pagesMeasured"], 1)

    def test_the_response_does_not_leak_the_customer_id(self):
        # The caller already knows its own tenant; echoing it back is noise
        # that also ends up in browser logs.
        request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)
        body = self.main.build_response(
            request, RunResult(sheets=[], artifacts={}, run={}))
        self.assertNotIn("customerId", body)


class TestErrorMapping(unittest.TestCase):
    def setUp(self):
        import main
        from firebase_functions import https_fn
        self.main, self.https_fn = main, https_fn

    def test_domain_errors_map_to_their_callable_codes(self):
        cases = [
            (NotFound("x"), self.https_fn.FunctionsErrorCode.NOT_FOUND),
            (PermissionDenied("x"),
             self.https_fn.FunctionsErrorCode.PERMISSION_DENIED),
        ]
        for exc, expected in cases:
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(self.main.error_code(exc), expected)

    def test_an_unknown_domain_error_falls_back_to_internal(self):
        class Weird(TakeoffFnError):
            code = "not-a-real-code"
        self.assertEqual(self.main.error_code(Weird("x")),
                         self.https_fn.FunctionsErrorCode.INTERNAL)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_takeoff_fn_main -v`
Expected: FAIL with `AttributeError: module 'main' has no attribute 'build_response'`

- [ ] **Step 3: Rewrite main.py**

Replace `main.py` with:

```python
"""Firebase entry point for the takeoff extraction pipeline.

This module is the only place firebase_functions is imported. Everything it
delegates to lives in takeoff_fn/ and is testable without the SDK.

The deployed callable name is the Python function name: rivet-mind must call
httpsCallable(functions, 'measure_takeoff').
"""
from __future__ import annotations

import os

import firebase_admin
from firebase_admin import firestore, storage
from firebase_functions import https_fn, options

from takeoff_fn import config
from takeoff_fn.errors import TakeoffFnError
from takeoff_fn.request import parse_request
from takeoff_fn.runner import RunResult, run_measurement

# Keeps region classification and room labelling inside the region the rest of
# the app runs in. gemini/client.py reads this; it needs no code change.
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", config.VERTEX_LOCATION)

firebase_admin.initialize_app()

_ERROR_CODES = {
    "unauthenticated": https_fn.FunctionsErrorCode.UNAUTHENTICATED,
    "permission-denied": https_fn.FunctionsErrorCode.PERMISSION_DENIED,
    "not-found": https_fn.FunctionsErrorCode.NOT_FOUND,
    "invalid-argument": https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
    "failed-precondition": https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
    "internal": https_fn.FunctionsErrorCode.INTERNAL,
}


def error_code(exc: TakeoffFnError):
    return _ERROR_CODES.get(exc.code, https_fn.FunctionsErrorCode.INTERNAL)


def build_response(request, result: RunResult) -> dict:
    return {
        "takeoffId": request.takeoff_id,
        "sheets": result.sheets,
        "artifacts": result.artifacts,
        "run": result.run,
    }


@https_fn.on_call(
    region=config.REGION,
    memory=options.MemoryOption.GB_2,
    timeout_sec=config.TIMEOUT_SECONDS,
    max_instances=config.MAX_INSTANCES,
)
def measure_takeoff(req: https_fn.CallableRequest) -> dict:
    """Measure the drawings on takeoffs/{takeoffId} and return their sheets."""
    try:
        request = parse_request(
            req.data,
            req.auth.uid if req.auth else None,
            dict(req.auth.token) if req.auth else None,
        )
    except TakeoffFnError as exc:
        raise https_fn.HttpsError(error_code(exc), str(exc)) from exc

    try:
        result = run_measurement(
            request, db=firestore.client(), bucket=storage.bucket())
    except TakeoffFnError as exc:
        raise https_fn.HttpsError(error_code(exc), str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # run_measurement has already written status: failed, so the record is
        # accurate before this surfaces to the caller.
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "Takeoff measurement failed") from exc

    return build_response(request, result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_takeoff_fn_main -v`
Expected: PASS, 4 tests

If `firebase_admin.initialize_app()` raises at import because no credentials
are configured, guard it:

```python
try:
    firebase_admin.initialize_app()
except Exception:  # already initialised, or no ambient credentials in tests
    pass
```

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover tests`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_takeoff_fn_main.py
git commit -m "feat(fn): wire the runner into the measure_takeoff callable"
```

---

### Task 8: The equivalence test

The test that keeps the regression corpus meaningful. It asserts the function's
sheet payload is identical to what `app.py extract` produces for the same PDF.

**Files:**
- Test: `tests/test_takeoff_fn_equivalence.py`

**Interfaces:**
- Consumes: `runner.run_measurement`, `regression.corpus.sheet_path`.
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_takeoff_fn_equivalence.py`:

```python
"""The function must not change detection results.

tools/regress.py guards the CLI path against the ground-truth corpus. If the
deployed callable can drift from that path, the guard means nothing. This test
runs one corpus sheet both ways and compares the takeoff payload field for
field.

Skipped when the NDA corpus is not on disk — see fixtures/MANIFEST.json.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from regression import corpus
from takeoff_fn import runner
from takeoff_fn.request import TakeoffRequest

SLUG = "s01"
NOW = 1_700_000_000_000

# Injected by the function; absent from a bare CLI run, so not compared.
INJECTED_KEYS = {"sheet_id", "source_file_id", "source_file_name", "label",
                 "plan_svg_url"}


class FakeBlob:
    def __init__(self, path, sink, objects):
        self.path, self._sink, self._objects = path, sink, objects

    def download_to_filename(self, local):
        Path(local).write_bytes(self._objects[self.path])

    def upload_from_filename(self, local, content_type=None):
        self._sink[self.path] = Path(local).stat().st_size

    def upload_from_string(self, data, content_type=None):
        self._sink[self.path] = len(data)


class FakeBucket:
    def __init__(self, objects):
        self.uploaded, self._objects = {}, objects

    def blob(self, path):
        return FakeBlob(path, self.uploaded, self._objects)


class FakeDoc:
    def __init__(self, data):
        self._data, self.updates = data, []

    @property
    def exists(self):
        return True

    def to_dict(self):
        return dict(self._data)

    def get(self):
        return self

    def update(self, patch):
        self.updates.append(patch)
        self._data.update(patch)


class FakeDb:
    def __init__(self, data):
        self.doc = FakeDoc(data)

    def collection(self, _name):
        class _C:
            def __init__(self, doc):
                self._doc = doc

            def document(self, _id):
                return self._doc
        return _C(self.doc)


def _corpus_sheet():
    try:
        return corpus.sheet_path(SLUG)
    except Exception:
        return None


@unittest.skipUnless(
    _corpus_sheet() is not None,
    f"corpus sheet {SLUG} is not on disk (see fixtures/MANIFEST.json)")
class TestCliEquivalence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(_corpus_sheet())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cli_takeoff(self) -> dict:
        from pipeline import run_extract
        out_parent = str(Path(self.tmp) / "cli")
        Path(out_parent).mkdir(parents=True, exist_ok=True)
        out_dir = run_extract(
            pdf_path=self.pdf, page_indices=[0], out_parent=out_parent,
            skip_gemini=False, disable_rooms=False, disable_windows=False,
            debug=False, refresh_regions=False, write_svg=True,
            allow_scale_prompt=False, ceiling_height=None,
            door_height=None, window_height=None)
        return json.loads(
            (Path(out_dir) / "pages" / "page_01" / "takeoff.json")
            .read_text(encoding="utf-8"))

    def _function_takeoff(self) -> dict:
        object_path = f"estimate_images/cus-1/est-1/{Path(self.pdf).name}"
        db = FakeDb({
            "customerId": "cus-1", "status": "queued", "estimateId": "est-1",
            "updatedAt": NOW - 1000,
            "sourceFiles": [{"fileName": Path(self.pdf).name,
                             "storageUrl": f"gs://b/{object_path}"}]})
        bucket = FakeBucket({object_path: Path(self.pdf).read_bytes()})
        result = runner.run_measurement(
            TakeoffRequest("t1", "cus-1", "uid-1", debug=False),
            db=db, bucket=bucket, now_fn=lambda: NOW,
            workdir=str(Path(self.tmp) / "fn"))
        return result.sheets[0]

    def test_the_function_and_the_cli_agree_field_for_field(self):
        cli = self._cli_takeoff()
        fn = self._function_takeoff()

        self.assertEqual(set(fn) - set(cli), INJECTED_KEYS,
                         "the function added a field the CLI does not emit")
        for key in cli:
            with self.subTest(field=key):
                self.assertEqual(fn[key], cli[key])

    def test_warnings_stay_structured_dicts(self):
        for warning in self._function_takeoff().get("warnings", []):
            self.assertIsInstance(warning, dict)
            self.assertIn("warning_code", warning)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_takeoff_fn_equivalence -v`

Expected, if the corpus is not downloaded: `SKIPPED` — that is a pass.
Expected, if it is: PASS. A FAIL here means the function changed detection
behaviour and must be fixed before going further; do not adjust the test to
accommodate a difference.

- [ ] **Step 3: Run the full suite**

Run: `python -m unittest discover tests`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_takeoff_fn_equivalence.py
git commit -m "test(fn): assert the callable and the CLI produce identical takeoffs"
```

---

### Task 9: Deploy verification and the rivet-mind handoff

Confirms the codebase isolation actually holds, and writes down everything
rivet-mind must land. Nothing here is deployed to production.

**Files:**
- Create: `docs/takeoff-function-deployment.md`
- Test: manual verification, recorded in the doc.

**Interfaces:**
- Consumes: `firebase.json`, `.firebaserc` from Task 1.
- Produces: nothing importable.

- [ ] **Step 1: Verify the codebase isolation with a dry run**

Run from the repo root:

```bash
firebase deploy --only functions --project dev --dry-run
```

Read the output and confirm **both**:
1. It plans to create `measure_takeoff` in codebase `takeoff`.
2. It plans to **delete nothing**. If it proposes deleting any of
   `enqueueEstimate`, `processEstimateTask`, `stripeWebhook`, or any other
   rivet-mind function, **stop** — the `codebase` key is not isolating as
   expected and the plan's assumption is wrong.

Record the exact output in the deployment doc in Step 3.

- [ ] **Step 2: Verify the deploy bundle imports cleanly**

The deploy `ignore` list excludes `fixtures/`, and `scale/store.py` imports
`regression`, so confirm the shipped subset imports on its own:

```bash
python -c "import main; print(main.measure_takeoff)"
```

Expected: prints a function reference with no `ModuleNotFoundError`.

Then confirm the stored-scale tier tolerates the missing manifest:

```bash
python -c "from regression import corpus; print(corpus.load_manifest()['sheets'][:1] or 'empty corpus ok')"
```

Expected: prints a sheet entry locally; on a machine without `fixtures/` it
prints `empty corpus ok` rather than raising.

- [ ] **Step 3: Write the deployment and handoff doc**

Create `docs/takeoff-function-deployment.md`:

````markdown
# Deploying the takeoff callable

The extraction pipeline deploys from THIS repo into rivet-mind's Firebase
project as a second functions codebase named `takeoff`. rivet-mind continues
to deploy its own `default` codebase; neither touches the other.

## Deploy

```bash
firebase deploy --only functions --project dev    # rivet-mind-dev
firebase deploy --only functions --project prod   # nestimate-app
```

Always run with `--dry-run` first and confirm it deletes nothing.

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
its Python function name and offers no override.

```ts
const measure = httpsCallable(functions, 'measure_takeoff');
const { data } = await measure({ takeoffId, debug: false });
```

Request: `{ takeoffId: string, debug?: boolean }`. Nothing else — the tenant
comes from the verified `customerId` claim, and the source drawings come from
`takeoffs/{takeoffId}.sourceFiles`.

Response: `{ takeoffId, sheets, artifacts: { prefix, bySheet }, run }`.

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
````

- [ ] **Step 2 verification recap and Step 4: Run the full suite**

Run: `python -m unittest discover tests`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/takeoff-function-deployment.md
git commit -m "docs(fn): record deploy verification and the rivet-mind handoff"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| Request `{takeoffId, debug}`, tenant from claim | Task 1 |
| Response `{takeoffId, sheets, artifacts, run}` | Task 7 |
| Sheet identity, unique across files, `source_file_id` / `label` | Task 4 |
| `planSvgUrl` as a Storage object path | Tasks 4, 5 (path), 9 (handoff) |
| `warnings` stays structured | Tasks 4, 8 (asserted) |
| Firestore status transitions + inline `document` | Tasks 2, 6 |
| Storage layout `customers/{c}/takeoffs/{t}/file_NN/page_NN/` | Task 5 |
| `firebase.json`, `source: "."`, `python313`, ignore list | Task 1 |
| Runtime sizing 2 GiB / 900 s / europe-west2 | Tasks 1, 7 |
| Dependency changes | Task 1 |
| Vertex `GOOGLE_CLOUD_LOCATION` + IAM grant | Tasks 7, 9 |
| `regression/` ships, `fixtures/` excluded | Tasks 1, 9 |
| Execution flow steps 1-9 | Task 6 |
| Failure handling, per-file tolerance, fail only if no sheets | Task 6 |
| `allow_scale_prompt=False` | Task 6 (asserted in test) |
| Existing suite unchanged | every task's final step |
| Unit tests with fakes | Tasks 1-7 |
| Equivalence test | Task 8 |
| Out-of-scope items recorded for rivet-mind | Task 9 |

No gaps.

**Placeholder scan:** No TBD/TODO. Every code step carries complete, runnable
code. No "similar to Task N" references.

**Type consistency:** `TakeoffRequest(takeoff_id, customer_id, user_id, debug)`
is constructed identically in Tasks 1, 6, 7, 8. `SourceFile(index, file_name,
storage_url)` is produced in Task 2 and consumed in Task 3. `DownloadedSource`
fields match between Tasks 3 and 6. `artifacts.object_path(prefix, file_index,
page_number, name)` has one signature, used in Tasks 5 and 6.
`sheets.collect_sheets(out_dir, file_index, file_name, svg_path_for)` matches
its Task 6 call site. `RunResult(sheets, artifacts, run, document)` is built in
Task 6 and read in Tasks 7 and 8. `records.mark_*` signatures all take
`(db, takeoff_id, ..., now_epoch_ms)`.

**One deliberate coupling to watch during execution:** Task 6's runner builds a
page directory path as `Path(out_dir) / "pages" / f"page_{n:02d}"`, duplicating
the convention `takeoff_fn/sheets.page_dirs` already knows. If the implementer
finds this brittle, having `collect_sheets` return the page directory alongside
each sheet is a fair simplification — the tests in Task 4 would need the extra
field.
