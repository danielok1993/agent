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
