"""Parsing and validating one callable request.

The tenant is taken from the verified auth token, never from the payload: a
client that could name its own customerId could measure another tenant's
drawings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scale.units import SUPPLIABLE_SCALES
from takeoff_fn.errors import InvalidArgument, PermissionDenied, Unauthenticated


@dataclass(frozen=True)
class TakeoffRequest:
    takeoff_id: str
    customer_id: str
    user_id: str
    debug: bool
    # A scale the user supplied for a sheet the resolver could not read. Last
    # and defaulted so every existing construction still holds.
    scale_denominator: Optional[float] = None


def _scale_denominator(raw) -> Optional[float]:
    """The supplied scale, or None.

    Only a member of SUPPLIABLE_SCALES is accepted. Anything else snaps to no
    standard scale, so scale/factor.py's _gate_denominator would abstain and
    the re-measurement would detect at identity — handing the user back the
    same unmeasurable takeoff they just answered a question about. The client
    offers this set, but the client is not the authority on it.

    bool is excluded explicitly: it is a subclass of int, and `True` would
    otherwise validate as 1.0.
    """
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise InvalidArgument("scaleDenominator must be a number")
    value = float(raw)
    if value not in SUPPLIABLE_SCALES:
        offered = ", ".join(f"1:{d:g}" for d in SUPPLIABLE_SCALES)
        raise InvalidArgument(
            f"scaleDenominator must be one of {offered}")
    return value


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
        scale_denominator=_scale_denominator(payload.get("scaleDenominator")),
    )
