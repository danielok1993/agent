"""Recursive XY-cut: split a page into drawing regions at whitespace gutters."""
from __future__ import annotations

from typing import Optional

from layout.constants import SEGMENT_MAX_DEPTH
from layout.occupancy import InkMap


def _row_profile(ink: InkMap, r0: int, r1: int, c0: int, c1: int) -> list[int]:
    return [sum(ink.bins[r][c0:c1]) for r in range(r0, r1)]


def _col_profile(ink: InkMap, r0: int, r1: int, c0: int, c1: int) -> list[int]:
    return [sum(ink.bins[r][c] for r in range(r0, r1)) for c in range(c0, c1)]


def _trim(profile: list[int], lo: int) -> tuple[int, int]:
    """Strip empty margins; returns absolute (start, end) bin indices."""
    a, b = 0, len(profile)
    while a < b and profile[a] == 0:
        a += 1
    while b > a and profile[b - 1] == 0:
        b -= 1
    return lo + a, lo + b


def _widest_gap(profile: list[int], offset: int, min_bins: int) -> Optional[tuple[int, int]]:
    """Widest fully-empty internal run of at least min_bins. Leading and
    trailing runs are margins, not gutters, and are ignored."""
    best: Optional[tuple[int, int]] = None
    i, n = 0, len(profile)
    while i < n:
        if profile[i] == 0:
            j = i
            while j < n and profile[j] == 0:
                j += 1
            if j - i >= min_bins and i > 0 and j < n:
                if best is None or (j - i) > (best[1] - best[0]):
                    best = (i, j)
            i = j
        else:
            i += 1
    return None if best is None else (offset + best[0], offset + best[1])


def _clip_cut(profile: list[int], offset: int, cut_positions: set[int]) -> Optional[int]:
    """First clip edge lying strictly inside the span with ink on both sides."""
    n = len(profile)
    for pos in sorted(cut_positions):
        idx = pos - offset
        if idx <= 0 or idx >= n:
            continue
        if any(profile[:idx]) and any(profile[idx:]):
            return pos
    return None


def _xy_cut(
    ink: InkMap,
    r0: int, r1: int, c0: int, c1: int,
    min_bins: int,
    cut_rows: set[int],
    cut_cols: set[int],
    depth: int,
    out: list[tuple[int, int, int, int]],
) -> None:
    rows = _row_profile(ink, r0, r1, c0, c1)
    r0, r1 = _trim(rows, r0)
    cols = _col_profile(ink, r0, r1, c0, c1)
    c0, c1 = _trim(cols, c0)
    if r1 <= r0 or c1 <= c0:
        return
    if depth >= SEGMENT_MAX_DEPTH:
        out.append((r0, r1, c0, c1))
        return

    rows = _row_profile(ink, r0, r1, c0, c1)
    cols = _col_profile(ink, r0, r1, c0, c1)
    gap_r = _widest_gap(rows, r0, min_bins)
    gap_c = _widest_gap(cols, c0, min_bins)
    height_r = 0 if gap_r is None else gap_r[1] - gap_r[0]
    height_c = 0 if gap_c is None else gap_c[1] - gap_c[0]

    # A real gutter always beats a clip edge: a clip edge has zero width.
    if height_r or height_c:
        if height_r >= height_c:
            m = (gap_r[0] + gap_r[1]) // 2
            _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
            _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        else:
            m = (gap_c[0] + gap_c[1]) // 2
            _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out)
            _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    m = _clip_cut(rows, r0, cut_rows)
    if m is not None:
        _xy_cut(ink, r0, m, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        _xy_cut(ink, m, r1, c0, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    m = _clip_cut(cols, c0, cut_cols)
    if m is not None:
        _xy_cut(ink, r0, r1, c0, m, min_bins, cut_rows, cut_cols, depth + 1, out)
        _xy_cut(ink, r0, r1, m, c1, min_bins, cut_rows, cut_cols, depth + 1, out)
        return

    out.append((r0, r1, c0, c1))
