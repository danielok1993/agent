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
