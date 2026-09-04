"""dash_rows.py <slug> [<slug> ...] [--min-n N] [--gap-max PX] [--all]

Census of COLLINEAR ROWS of same-pen stroked pieces on each detection page:
every chain of >= N solid `l` pieces (same quantized colour AND width) lying
on one line (offset <= LINE_TOL, angle bin 0.5 deg), sorted along the axis,
whose consecutive gaps all lie in (GAP_MIN, GAP_MAX].  Both classes side by
side — annotation dash rows (beam / section / boundary lines, "line of wall
over", dashed fixture boxes) and real wall faces broken into pieces by text
masks or crossings — so the discriminator, if there is one, is measured
before any rule is written (W-gate iteration 3 step 6).

Per row: n, pen (colour, width), angle, extent, median piece length and
length CV, median gap and gap CV, gap/len, and where the pieces end up in the
network — strong faces (from _collect_wall_faces), barrier faces
(network.faces, stroked) and paired faces (any segment's face indices).
"""
from __future__ import annotations

import math
import statistics
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection.walls import _is_dashed, _pen_key  # noqa: E402

LINE_TOL = 0.6      # px: pieces of one drawn line share its offset (s02 jitter 0.3)
GAP_MIN = 0.5       # px: a REAL gap — touching pieces are one drawn line
GAP_MAX = 80.0      # px: census ceiling (text masks run 20–80 px)
MIN_LEN = 2.0


def rows_for_page(pd, min_n: int, gap_max: float):
    pieces = []
    for p in pd.paths:
        if p.item_type != "l" or len(p.points) < 2 or p.stroke_width <= 0:
            continue
        if p.color is None or _is_dashed(p.dashes):
            continue
        a, b = p.points[0], p.points[-1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < MIN_LEN:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        if ux < 0 or (abs(ux) < 1e-9 and uy < 0):
            ux, uy = -ux, -uy
        ang = math.degrees(math.atan2(uy, ux)) % 180.0
        pieces.append((p.path_index, a, b, L, (_pen_key(p.color), round(p.stroke_width, 2)), ang, p.fill is not None))

    groups: dict[tuple, list] = {}
    for pc in pieces:
        idx, a, b, L, pen, ang, _ = pc
        abin = round(ang * 2.0) / 2.0 % 180.0
        groups.setdefault((pen, abin), []).append(pc)

    rows = []
    for (pen, abin), members in groups.items():
        th = math.radians(abin)
        ux, uy = math.cos(th), math.sin(th)
        nx, ny = -uy, ux
        recs = []
        for idx, a, b, L, _, ang, filled in members:
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            off = mx * nx + my * ny
            t1 = a[0] * ux + a[1] * uy
            t2 = b[0] * ux + b[1] * uy
            recs.append((off, min(t1, t2), max(t1, t2), idx, L, a, b, ang, filled))
        recs.sort()
        # cluster by offset
        clusters, cur = [], [recs[0]]
        for r in recs[1:]:
            if r[0] - cur[-1][0] <= LINE_TOL:
                cur.append(r)
            else:
                clusters.append(cur)
                cur = [r]
        clusters.append(cur)
        for cl in clusters:
            cl.sort(key=lambda r: r[1])
            chain = [cl[0]]
            def flush(chain):
                if len(chain) >= min_n:
                    rows.append((pen, abin, chain))
            for r in cl[1:]:
                gap = r[1] - chain[-1][2]
                if GAP_MIN < gap <= gap_max:
                    chain.append(r)
                else:
                    flush(chain)
                    chain = [r]
            flush(chain)
    return rows


def cv(xs):
    if len(xs) < 2:
        return 0.0
    m = statistics.mean(xs)
    return statistics.pstdev(xs) / m if m > 0 else 0.0


def length_clusters(lens, tol_frac=0.12, tol_abs=1.5):
    """Greedy 1-D clustering of piece lengths; returns (k, labels)."""
    centers: list[float] = []
    labels = []
    for L in lens:
        for k, c in enumerate(centers):
            if abs(L - c) <= max(tol_abs, tol_frac * c):
                labels.append(k)
                break
        else:
            centers.append(L)
            labels.append(len(centers) - 1)
    return len(centers), labels


def periodic(lens, gaps):
    """A drawn dash pattern: every gap equal, pieces of one length (plain
    dash) or two lengths strictly alternating (chain / dash-dot)."""
    if len(gaps) < 2:
        return False, "n<3"
    gm = statistics.median(gaps)
    tol = max(1.5, 0.12 * gm)
    if any(abs(g - gm) > tol for g in gaps):
        return False, "gaps"
    k, labels = length_clusters(lens)
    if k == 1:
        return True, "plain"
    if k == 2 and all(labels[i] != labels[i + 1] for i in range(len(labels) - 1)):
        return True, "chain"
    return False, f"k={k}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    min_n = 3
    gap_max = GAP_MAX
    show_all = "--all" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--min-n":
            min_n = int(sys.argv[i + 1])
        if a == "--gap-max":
            gap_max = float(sys.argv[i + 1])
    for slug in args:
        pages = H.load(slug)
        for page in pages:
            taps = H.Taps()
            ents, extras = H.run(page, taps=taps, keep_network=True)
            net = extras["network"]
            strong_idx = set()
            for f in taps.faces:
                if f["stroked"]:
                    strong_idx.update(f["idx"])
            barrier_idx = set()
            for f in net.faces:
                if f.stroked:
                    barrier_idx.update(f.indices)
            paired_idx = set()
            for s in net.segments:
                paired_idx.update(s.face_path_indices)
            rows = rows_for_page(page.page_data, min_n, gap_max)
            rows.sort(key=lambda r: -len(r[2]))
            try:
                import math as _m
                from detection.walls import (
                    _dash_row_indices, _collect_material_marks, WallGates,
                )
                _g = WallGates.at(page.scale_factor)
                _marks = _collect_material_marks(
                    page.page_data.paths, gates=_g,
                    max_len=_g.WALL_THROUGH_HATCH_MAX_PX * _m.sqrt(2.0) + 2.0,
                )
                flagged = _dash_row_indices(page.page_data.paths, _marks, gates=_g)
            except ImportError:
                flagged = set()
            print(f"=== {slug} p{page.page_number} f={page.scale_factor:.3f}: {len(rows)} rows of >= {min_n} pieces (gap {GAP_MIN}-{gap_max}px); rule flags {len(flagged)} pieces ===")
            print("   n  pen(color,w)                 ang   extent                         len_med len_cv gap_med gap_cv gapmax gap/len  strong barrier paired  rule  class")
            for pen, abin, chain in rows:
                lens = [r[4] for r in chain]
                gaps = [chain[i + 1][1] - chain[i][2] for i in range(len(chain) - 1)]
                idxs = [r[3] for r in chain]
                ns = sum(1 for i in idxs if i in strong_idx)
                nb = sum(1 for i in idxs if i in barrier_idx)
                npd = sum(1 for i in idxs if i in paired_idx)
                xs = [v for r in chain for v in (r[5][0], r[6][0])]
                ys = [v for r in chain for v in (r[5][1], r[6][1])]
                lm, gm = statistics.median(lens), statistics.median(gaps)
                lc, gc = cv(lens), cv(gaps)
                ok, why = periodic(lens, gaps)
                klass = f"DASH-{why}" if ok else f"irregular({why})"
                nf = sum(1 for i in idxs if i in flagged)
                if not show_all and nb == 0 and ns == 0 and not ok and nf == 0:
                    continue
                col = pen[0]
                cs = "(" + ",".join(f"{c:.2f}" for c in col) + f",{pen[1]})" if col else f"(None,{pen[1]})"
                print(f"  {len(chain):3d}  {cs:28s} {abin:5.1f}  ({min(xs):6.1f},{min(ys):6.1f})-({max(xs):6.1f},{max(ys):6.1f})  {lm:6.1f} {lc:6.2f}  {gm:6.1f} {gc:6.2f}  {max(gaps):5.1f}  {gm / lm if lm else 0:5.2f}   {ns:3d}    {nb:3d}    {npd:3d}   {nf:3d}   {klass}  lens={[round(v, 1) for v in lens[:6]]}{'…' if len(lens) > 6 else ''}")


if __name__ == "__main__":
    main()
