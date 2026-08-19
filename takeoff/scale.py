"""Which drawing scale a room is measured at, and whether it can be trusted.

Pages can carry different scales per region (s03, s17), so each room takes
the floor_plan region containing its centroid, then the ink-dominant
detection scale, then nothing — never a guess.

The unit model trusts that the PDF is at its intended sheet size: an A1
drawing exported onto A3 paper carries a printed "1:50" that is really 1:100.
Viewport- and user-sourced scales are immune (they measure the real page);
text-sourced ones are verified against a title-block sheet-size token when
one exists. A bare "A1" anywhere on the sheet is NOT that token — s20 carries
one inside the drawing number `18-069-001(A1).A` — so the scan only counts a
size that is DECLARED: written after an "@" (`1:50@A3`, `As Shown @ A1`) or
after a SHEET / SIZE / PAPER / FORMAT keyword. Correction on mismatch is a
follow-up branch — here we only flag.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from takeoff.units import effective_denominator

ISO_A_SIZES_MM = {
    "A0": (841.0, 1189.0),
    "A1": (594.0, 841.0),
    "A2": (420.0, 594.0),
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
}
SHEET_SIZE_TOL_FRAC = 0.05
# Half-size / double-size prints (A1↔A3: two ISO A-steps, linear factor 2).
RESIZE_FACTOR_BANDS = ((1.8, 2.2), (0.45, 0.55))

# The size must be declared: "@ A3", or a SHEET/SIZE/PAPER/FORMAT keyword
# with at most a short separator ("SHEET SIZE: A3", "ORIGINAL FORMAT - A0").
_SIZE_TOKEN_RE = re.compile(
    r"(?:@\s*|(?:SHEET|SIZE|PAPER|FORMAT)[^A-Za-z0-9]{0,12})(A[0-4])\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RoomScale:
    denominator: Optional[float]
    source: str          # viewport | text | user | detection | unresolved
    region_id: Optional[str]
    verified: bool
    plausibility: Optional[object] = None   # takeoff.plausibility.Verdict

    def to_dict(self) -> dict:
        d = {"denominator": self.denominator, "source": self.source,
             "region_id": self.region_id, "verified": self.verified}
        if self.plausibility is not None:
            d["plausibility"] = self.plausibility.to_dict()
        return d


def _contains(bbox, x: float, y: float) -> bool:
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def select_room_scale(centroid, regions, page_scales, det_scale) -> RoomScale:
    x, y = centroid
    for region in regions:
        if region.region_type != "floor_plan" or not _contains(region.bbox, x, y):
            continue
        by_region = page_scales.by_region if page_scales else {}
        if region.region_id not in by_region:
            break                       # no verdict for this region → page fallback
        info = by_region[region.region_id]
        denom = effective_denominator(info)
        if denom is None:
            # Explicitly unresolved: never borrow another plan's scale.
            return RoomScale(None, "unresolved", region.region_id, False)
        return RoomScale(denom, info.source, region.region_id, False)
    if det_scale is not None and det_scale.denominator is not None:
        return RoomScale(float(det_scale.denominator), "detection", None, False)
    return RoomScale(None, "unresolved", None, False)


def sheet_size_tokens(text: str) -> set[str]:
    return {m.upper() for m in _SIZE_TOKEN_RE.findall(text or "")}


def _ratio_pair(token: str, w: float, h: float) -> tuple[float, float]:
    """(w_ratio, h_ratio) of page over ISO size, orientation-matched."""
    a, b = ISO_A_SIZES_MM[token]
    short, long_ = (min(w, h), max(w, h))
    return short / a, long_ / b


def verify_sheet_size(tokens: set[str], page_w_mm: float, page_h_mm: float) -> tuple[bool, bool]:
    matches = resized = False
    for token in tokens:
        if token not in ISO_A_SIZES_MM:
            continue
        rw, rh = _ratio_pair(token, page_w_mm, page_h_mm)
        if abs(rw - 1.0) <= SHEET_SIZE_TOL_FRAC and abs(rh - 1.0) <= SHEET_SIZE_TOL_FRAC:
            matches = True
        for lo, hi in RESIZE_FACTOR_BANDS:
            if lo <= rw <= hi and lo <= rh <= hi:
                resized = True
    return matches, resized


def is_verified(room_scale: RoomScale, sheet_matches: bool, plausibility=None) -> bool:
    """Source-level trust, then the drawing's own evidence: a failed
    plausibility check unverifies every tier (typed scales included), and
    agreeing dimension strings verify even a text-only one."""
    if plausibility is not None:
        if plausibility.status == "implausible":
            return False
        if plausibility.status == "ok" and plausibility.method == "dimensions":
            return True
    if room_scale.source in ("viewport", "user"):
        return True
    return room_scale.source == "text" and sheet_matches
