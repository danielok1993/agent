"""Is the resolved scale believable? Two checks that read the drawing itself.

A scale can be wrong however it was obtained: a title-block "1:50" on a sheet
exported at A3 is really 1:100, a viewport can describe a different plan, and
a typed scale can be a typo. Every tier lands here before `verified` is set.

1. Door leaves. A swing leaf is 0.6–0.9 m on every real sheet in the corpus
   (medians 0.64–0.90 m; s01, the mis-declared one, 0.38 m), so the page's
   median leaf at the resolved scale falls outside [LEAF_MIN_M, LEAF_MAX_M]
   only when the scale is off — and off by a print factor, so the implied
   correction is snapped to ×0.25 / ×0.5 / ×2 / ×4 of the current denominator.
   Rooms cannot serve: the smallest room on every sheet is a sub-m² cupboard
   or phantom, and wall thickness never reaches the takeoff. Widths are taken
   from detector evidence only (arc radius, merged pair chord ÷ 2, panel
   length) — a bbox edge is not a leaf.

2. Dimension strings. "3600" written beside a line ticked at both ends IS the
   drawing's scale, measured: value_mm / (length_px × 0.16933). Median over
   ≥ DIM_MIN_MATCHES lines. Agreement within DIM_AGREE_TOL verifies even a
   text-only scale; a disagreement past DIM_DISAGREE_TOL contradicts even a
   typed one. Numbers are never swapped — the verdict only gates `verified`.

Dimensions decide when they are measurable; door leaves are the fallback.
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from typing import Optional

from takeoff.units import MM_PER_PX_AT_1_1, px_to_m

LEAF_MIN_M = 0.55
LEAF_MAX_M = 1.20
LEAF_TYPICAL_M = 0.80
LEAF_MIN_DOORS = 2
# Print-size corrections only: half/double/quadruple sheets.
CORRECTION_FACTORS = (0.25, 0.5, 2.0, 4.0)

_MERGED = frozenset({"double_swing"})
_ARCLESS = frozenset({"sliding", "folding"})


@dataclass(frozen=True)
class Verdict:
    status: str                        # ok | implausible | untested
    method: Optional[str]              # door_leaves | dimensions | None
    n: int = 0
    median_m: Optional[float] = None   # door_leaves: median leaf width
    implied_denominator: Optional[float] = None

    def to_dict(self) -> dict:
        d = {"status": self.status, "method": self.method, "n": self.n}
        if self.median_m is not None:
            d["median_leaf_m"] = round(self.median_m, 2)
        if self.implied_denominator is not None:
            d["implied_denominator"] = self.implied_denominator
        return d

    def describe(self, denominator: float) -> str:
        """The SCALE_IMPLAUSIBLE message for an implausible verdict."""
        if self.method == "dimensions":
            return (f"Scale {_fmt_scale(denominator)} contradicts the drawing's dimension "
                    f"strings: {self.n} ticked dimension(s) measure as "
                    f"{_fmt_scale(self.implied_denominator)}")
        leaf = self.median_m or 0.0
        at = leaf * self.implied_denominator / denominator
        return (f"Scale {_fmt_scale(denominator)} is implausible: median door leaf "
                f"{leaf:.2f} m over {self.n} door(s) (expected {LEAF_MIN_M:.2f}–"
                f"{LEAF_MAX_M:.2f}); at {_fmt_scale(self.implied_denominator)} it would "
                f"be {at:.2f} m")


def _fmt_scale(d: float) -> str:
    return f"1:{d:g}" if float(d).is_integer() else f"1:{d:.1f}"


UNTESTED = Verdict("untested", None)


def _positive(value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def leaf_width_px(evidence: dict) -> Optional[float]:
    """One leaf's width from detector evidence; None when only a bbox exists."""
    evidence = evidence or {}
    atype = evidence.get("assembly_type")
    if atype in _MERGED:
        try:
            (x0, y0), (x1, y1) = evidence.get("opening_line")
        except (TypeError, ValueError):
            return None
        chord = _positive(math.hypot(x1 - x0, y1 - y0))
        return chord / 2.0 if chord else None
    if atype in _ARCLESS:
        return _positive(evidence.get("panel_length_px"))
    arc = evidence.get("arc_bbox")
    if arc:
        try:
            x0, y0, x1, y1 = (float(v) for v in arc)
        except (TypeError, ValueError):
            return None
        return _positive(max(x1 - x0, y1 - y0))
    return _positive(evidence.get("leaf_line_length_px"))


def snap_correction(median_m: float, denominator: float) -> float:
    """The denominator that would put the median leaf at LEAF_TYPICAL_M,
    snapped to a print-size factor of the current one."""
    raw = LEAF_TYPICAL_M / median_m
    factor = min(CORRECTION_FACTORS, key=lambda f: abs(math.log(f) - math.log(raw)))
    return denominator * factor


def check_door_leaves(leaf_px: list[float], denominator: float) -> Verdict:
    widths = [w for w in leaf_px if w and w > 0]
    if len(widths) < LEAF_MIN_DOORS:
        return Verdict("untested", "door_leaves", n=len(widths))
    median = px_to_m(statistics.median(widths), denominator)
    if LEAF_MIN_M <= median <= LEAF_MAX_M:
        return Verdict("ok", "door_leaves", n=len(widths), median_m=median)
    return Verdict("implausible", "door_leaves", n=len(widths), median_m=median,
                   implied_denominator=snap_correction(median, denominator))


# ---------------------------------------------------------------- dimensions

DIM_MIN_MATCHES = 3
DIM_AGREE_TOL = 0.05       # |implied/resolved − 1| ≤ this → the dimensions confirm it
DIM_DISAGREE_TOL = 0.15    # beyond this they contradict it; between: inconclusive
DIM_MIN_MM = 100.0         # shorter "dimensions" are tag numbers (door codes, levels)
DIM_METRES_MAX = 100.0     # "4.50" is metres; "150.0" is not a dimension string
# A label sits just off its line: centre within this many text heights of the
# line (perpendicular), and its extent along the line may exceed a short
# line's length by at most this factor (s01: "300" 22px along a 19px stub).
DIM_LABEL_OFFSET_HEIGHTS = 2.5
DIM_LABEL_OVERHANG = 1.5

_MM_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$|^\d{3,6}$")
_M_RE = re.compile(r"^\d{1,2}\.\d{1,3}$")


@dataclass(frozen=True)
class DimensionMatch:
    value_mm: float
    length_px: float
    implied_denominator: float

    def to_dict(self) -> dict:
        return {"value_mm": self.value_mm, "length_px": round(self.length_px, 1),
                "implied_denominator": round(self.implied_denominator, 1)}


def parse_dimension_mm(text: str) -> Optional[float]:
    t = (text or "").strip()
    if _MM_RE.match(t):
        v = float(t.replace(",", ""))
        return v if v >= DIM_MIN_MM else None
    if _M_RE.match(t):
        v = float(t)
        if 0.0 < v < DIM_METRES_MAX:
            return v * 1000.0 if v * 1000.0 >= DIM_MIN_MM else None
    return None


def dimension_matches(paths, text_spans) -> list[DimensionMatch]:
    """Every ticked dimension line with a numeric label beside it."""
    from detection.walls import _dimension_line_indices

    labels = []
    for s in text_spans:
        v = parse_dimension_mm(s.text)
        if v is None:
            continue
        x0, y0, x1, y1 = s.bbox
        labels.append((v, ((x0 + x1) / 2.0, (y0 + y1) / 2.0), x1 - x0, y1 - y0))
    if not labels:
        return []
    idx = _dimension_line_indices(paths)
    lines = []
    for p in paths:
        if p.path_index not in idx:
            continue
        a, b = p.points[0], p.points[-1]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 0:
            continue
        lines.append((a, b, length))

    pairs = []   # (score, line_no, label_no)
    for li, (a, b, length) in enumerate(lines):
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        for ti, (v, (cx, cy), w, h) in enumerate(labels):
            dx, dy = cx - mx, cy - my
            along = abs(dx * ux + dy * uy)
            perp = abs(-dx * uy + dy * ux)
            # The text's own extent along / across the line.
            text_along = abs(w * ux) + abs(h * uy)
            text_across = abs(w * uy) + abs(h * ux)
            if perp > DIM_LABEL_OFFSET_HEIGHTS * text_across:
                continue
            if along > length / 2.0:
                continue
            if text_along > DIM_LABEL_OVERHANG * length:
                continue
            pairs.append((math.hypot(along, perp), li, ti))

    used_lines: set[int] = set()
    used_labels: set[int] = set()
    out = []
    for _, li, ti in sorted(pairs):
        if li in used_lines or ti in used_labels:
            continue
        used_lines.add(li)
        used_labels.add(ti)
        v = labels[ti][0]
        length = lines[li][2]
        out.append(DimensionMatch(v, length, v / (length * MM_PER_PX_AT_1_1)))
    return out


def check_dimensions(matches: list[DimensionMatch], denominator: float) -> Verdict:
    n = len(matches)
    if n < DIM_MIN_MATCHES:
        return Verdict("untested", "dimensions", n=n)
    implied = statistics.median(m.implied_denominator for m in matches)
    off = abs(implied / denominator - 1.0)
    if off <= DIM_AGREE_TOL:
        status = "ok"
    elif off > DIM_DISAGREE_TOL:
        status = "implausible"
    else:
        status = "inconclusive"
    return Verdict(status, "dimensions", n=n, implied_denominator=round(implied, 1))


# ---------------------------------------------------------------- combined

def assess_scale(denominator: float, leaf_px: list[float], paths, text_spans) -> Verdict:
    """Dimensions decide when they can; door leaves are the fallback."""
    dims = check_dimensions(dimension_matches(paths, text_spans), denominator)
    if dims.status != "untested":
        return dims          # measured (ok / inconclusive / implausible) beats a band
    return check_door_leaves(leaf_px, denominator)

