"""The drawing's own dimension strings as a scale MEASUREMENT.

"3600" written beside a line ticked at both ends IS the drawing's scale,
measured: value_mm / (length_px × MM_PER_PX_AT_1_1). The median over
≥ DIM_MIN_MATCHES such lines either verifies a claimed scale (agreement
within DIM_AGREE_TOL) or contradicts it (past DIM_DISAGREE_TOL); between the
two it is inconclusive. Two readers, one grammar:

  * takeoff/plausibility.py — `verified`: agreeing strings verify even a
    text-only scale, contradicting ones unverify even a typed one. The
    numbers the takeoff publishes are never swapped.
  * scale/factor.py — the detection gates: a VERIFIED claim drives them
    whatever its number (s01's stored 1:92.2, which no standard scale
    matches, W-gate iteration 3 step 12), a CONTRADICTED claim is replaced
    by the measured scale, and an unverifiable non-standard claim abstains
    exactly as before.

This lives under scale/ rather than takeoff/ because the gates need it BEFORE
detection and scale/ must not import takeoff/ (takeoff imports detection).
`dimension_matches` reaches into detection.walls for the ticked-line
recogniser lazily, at call time, for the same reason.
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from typing import Optional

from models import BBox
from scale.units import MM_PER_PX_AT_1_1

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
    # Debug trail: which line (primitives.json path_index, endpoints) was
    # measured against which label.
    path_index: Optional[int] = None
    line: Optional[tuple] = None
    label: Optional[str] = None
    label_bbox: Optional[tuple] = None

    def to_dict(self) -> dict:
        d = {"value_mm": self.value_mm, "length_px": round(self.length_px, 1),
             "implied_denominator": round(self.implied_denominator, 1),
             "path_index": self.path_index, "label": self.label}
        if self.line is not None:
            d["line"] = [[round(v, 1) for v in pt] for pt in self.line]
        if self.label_bbox is not None:
            d["label_bbox"] = [round(v, 1) for v in self.label_bbox]
        return d


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
        labels.append((v, ((x0 + x1) / 2.0, (y0 + y1) / 2.0), x1 - x0, y1 - y0, s))
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
        lines.append((a, b, length, p.path_index))

    pairs = []   # (score, line_no, label_no)
    for li, (a, b, length, _pi) in enumerate(lines):
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        for ti, (v, (cx, cy), w, h, _s) in enumerate(labels):
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
        v, span = labels[ti][0], labels[ti][4]
        a, b, length, pi = lines[li]
        out.append(DimensionMatch(
            v, length, v / (length * MM_PER_PX_AT_1_1), path_index=pi,
            line=((float(a[0]), float(a[1])), (float(b[0]), float(b[1]))),
            label=span.text.strip(), label_bbox=tuple(float(x) for x in span.bbox)))
    return out


def page_dimensions(page_data) -> list[DimensionMatch]:
    """The page's matches, on the FULL page — the takeoff's convention, and
    what run_extract hands both to detection_scale and to compute_takeoff."""
    return dimension_matches(page_data.paths, page_data.text_spans)


def measured_denominator(
    matches: list[DimensionMatch], region_bbox: Optional[BBox] = None,
) -> Optional[float]:
    """The drawing's measured scale: the median implied denominator over the
    matches — those whose line midpoint lies inside `region_bbox` when one
    is given, because a mixed-scale sheet's plans each carry their own
    strings (s03/s17) and a page-wide median would judge every plan by the
    mixture — or None under DIM_MIN_MATCHES of them. A match with no
    recorded line cannot be placed and counts page-wide only. The median,
    not the mean: one label paired with the wrong line must not move it
    (s01's 31 matches sit within ±0.5 % of 1:92.2)."""
    picked: list[float] = []
    for m in matches:
        if region_bbox is not None:
            if m.line is None:
                continue
            (ax, ay), (bx, by) = m.line
            mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
            x0, y0, x1, y1 = region_bbox
            if not (x0 <= mx <= x1 and y0 <= my <= y1):
                continue
        picked.append(m.implied_denominator)
    if len(picked) < DIM_MIN_MATCHES:
        return None
    return statistics.median(picked)


def agreement(implied: float, claimed: float) -> str:
    """How the measured scale relates to a claimed one: "ok" within
    DIM_AGREE_TOL, "implausible" past DIM_DISAGREE_TOL, else "inconclusive"."""
    off = abs(implied / claimed - 1.0)
    if off <= DIM_AGREE_TOL:
        return "ok"
    if off > DIM_DISAGREE_TOL:
        return "implausible"
    return "inconclusive"
