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

try:
    firebase_admin.initialize_app()
except ValueError:
    # The already-initialised case, and the only one worth swallowing: the SDK
    # raises ValueError("The default Firebase app already exists") when the
    # module is imported twice. Anything else — a broken credential file, a
    # missing project — must propagate here, where the traceback names the
    # cause, rather than resurfacing opaquely from firestore.client() later.
    pass

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


def _measure(req, db, bucket) -> dict:
    """The handler's real body, with its clients injected so it is testable.

    Extracted for the same reason build_response and error_code are: the
    @https_fn.on_call decorator is awkward to invoke directly, and this is the
    wiring that actually runs in production.
    """
    try:
        request = parse_request(
            req.data,
            req.auth.uid if req.auth else None,
            dict(req.auth.token) if req.auth else None,
        )
    except TakeoffFnError as exc:
        raise https_fn.HttpsError(error_code(exc), str(exc)) from exc

    try:
        result = run_measurement(request, db=db, bucket=bucket)
    except TakeoffFnError as exc:
        raise https_fn.HttpsError(error_code(exc), str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # run_measurement has already written status: failed, so the record is
        # accurate before this surfaces to the caller.
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "Takeoff measurement failed") from exc

    return build_response(request, result)


@https_fn.on_call(
    region=config.REGION,
    memory=options.MemoryOption.GB_2,
    timeout_sec=config.TIMEOUT_SECONDS,
    max_instances=config.MAX_INSTANCES,
)
def measure_takeoff(req: https_fn.CallableRequest) -> dict:
    """Measure the drawings on takeoffs/{takeoffId} and return their sheets."""
    return _measure(req, firestore.client(), storage.bucket())
