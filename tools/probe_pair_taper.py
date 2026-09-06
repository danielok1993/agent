"""Measure face-pair TAPER on a corpus sheet — the diagnostic behind
WALL_PAIR_TAPER_MAX_FRAC (detection/walls.py).

For every candidate pair `_pair_faces_to_centerlines` would emit on the
sheet's detection page data, interpolate the partner's signed offset from the
first face's line at both ends of their overlap and report
|s_lo - s_hi| (px) and its ratio to the larger spacing. A wall's two faces are
parallel (ratio ~0, corpus max 0.30); a stroke crossing the band corner to
corner — a brick-hatch cell's diagonal — runs from the band's full width to
zero (ratio 1.0). Pairs are re-walked with the same gates as the detector so
the population matches; "survives" means both faces' path indices sit in one
final WallSegment.

Usage:
    python tools/probe_pair_taper.py s03 [--thresh 1.0]

Runs the real stages (extract -> cached regions -> scales -> doors -> wall
network) offline, exactly as tools/regress.py does; needs the sheet under
fixtures/sheets/ and its region cache.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fitz  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

import detection.walls as W  # noqa: E402
from detection.doors.assembly import door_open_leaf_path_indices  # noqa: E402
from detection.doors.detect import detect_doors  # noqa: E402
from detection.geometry import (  # noqa: E402
    _angle_diff_mod180, _line_angle_deg, _line_length, _projected_interval,
)
from extraction.extractor import extract_page  # noqa: E402
from pipeline import resolve_page_regions  # noqa: E402
from scale.dimensions import page_dimensions  # noqa: E402
from scale.factor import detection_scale  # noqa: E402
from scale.resolver import resolve_page_scales  # noqa: E402
from scale.store import load_stored  # noqa: E402
from scale.viewport import viewport_scales  # noqa: E402


def taper_of(fi, fj):
    """(|offset at lo|, |offset at hi|, overlap) of fj against fi's line."""
    len_i = _line_length(fi.p1, fi.p2)
    ux = (fi.p2[0] - fi.p1[0]) / len_i
    uy = (fi.p2[1] - fi.p1[1]) / len_i
    nx, ny = -uy, ux
    s1 = (fj.p1[0] - fi.p1[0]) * nx + (fj.p1[1] - fi.p1[1]) * ny
    s2 = (fj.p2[0] - fi.p1[0]) * nx + (fj.p2[1] - fi.p1[1]) * ny
    t1 = (fj.p1[0] - fi.p1[0]) * ux + (fj.p1[1] - fi.p1[1]) * uy
    t2 = (fj.p2[0] - fi.p1[0]) * ux + (fj.p2[1] - fi.p1[1]) * uy
    lo_i, hi_i = _projected_interval(fi.p1, fi.p2, ux, uy, fi.p1)
    lo_j, hi_j = _projected_interval(fj.p1, fj.p2, ux, uy, fi.p1)
    lo, hi = max(lo_i, lo_j), min(hi_i, hi_j)
    if abs(t2 - t1) < 1e-9:
        return abs(s1), abs(s1), hi - lo

    def s_at(t):
        return s1 + (s2 - s1) * (t - t1) / (t2 - t1)

    return abs(s_at(lo)), abs(s_at(hi)), hi - lo


def candidate_pairs(faces, thick_tier, gates):
    """Re-walk the detector's pair loop (minus the taper gate) and yield
    (spacing, taper, overlap, s_lo, s_hi, fi, fj)."""
    n_buckets = max(1, int(math.ceil(180.0 / W.WALL_PARALLEL_ANGLE_TOL)))
    buckets: dict[int, list[int]] = {}
    for idx, f in enumerate(faces):
        b = int(_line_angle_deg(f.p1, f.p2) // W.WALL_PARALLEL_ANGLE_TOL) % n_buckets
        buckets.setdefault(b, []).append(idx)
    for b, members in buckets.items():
        nb = (b + 1) % n_buckets
        neighbor = buckets.get(nb, []) if nb != b else []
        for pos, i in enumerate(members):
            fi = faces[i]
            if _line_length(fi.p1, fi.p2) < 1e-6:
                continue
            for j in members[pos + 1:] + neighbor:
                fj = faces[j]
                if not W._pens_compatible(fi.pen, fj.pen):
                    continue
                if _angle_diff_mod180(
                    _line_angle_deg(fi.p1, fi.p2), _line_angle_deg(fj.p1, fj.p2)
                ) > W.WALL_PARALLEL_ANGLE_TOL:
                    continue
                spacing = W._perpendicular_spacing(fi.p1, fi.p2, fj.p1, fj.p2)
                if spacing < gates.WALL_MIN_THICKNESS_PX:
                    continue
                thick = spacing > gates.WALL_MAX_THICKNESS_PX
                if thick and (
                    not thick_tier
                    or spacing > gates.WALL_THROUGH_HATCH_MAX_PX
                    or fi.weak or fj.weak
                ):
                    continue
                s_lo, s_hi, ov = taper_of(fi, fj)
                if ov < gates.WALL_PAIR_MIN_OVERLAP_PX:
                    continue
                yield spacing, abs(s_lo - s_hi), ov, s_lo, s_hi, fi, fj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--thresh", type=float, default=1.0,
                    help="list pairs whose taper exceeds this many px")
    args = ap.parse_args()

    manifest = json.loads((ROOT / "fixtures" / "MANIFEST.json").read_text())
    entry = next(s for s in manifest["sheets"] if s["slug"] == args.slug)
    pdf = str(ROOT / "fixtures" / "sheets" / entry["file"])

    records: list[tuple] = []
    orig_pair = W._pair_faces_to_centerlines

    def recording_pair(faces, thick_tier=False, *, gates=W.WALL_GATES_UNSCALED):
        if thick_tier:  # the final pairing, not the interim stroke-reference one
            records.extend(candidate_pairs(faces, thick_tier, gates))
        return orig_pair(faces, thick_tier, gates=gates)

    W._pair_faces_to_centerlines = recording_pair

    doc = fitz.open(pdf)
    for pno in range(doc.page_count):
        page_data = extract_page(doc, pno)
        rr = resolve_page_regions(
            pdf_path=pdf, page=doc[pno], page_data=page_data, gemini_client=None,
            skip_gemini=True, refresh_regions=False, crop_dir=None,
        )
        if rr.skip_detection:
            print(f"{args.slug} page {pno + 1}: skip_detection")
            continue
        ps = resolve_page_scales(
            page_data=page_data, regions=rr.regions,
            viewports=viewport_scales(doc, doc[pno]),
            stored=load_stored(pdf, pno + 1), fallback=None, pdf_path=pdf,
            crop_fn=None, allow_prompt=False, suspend_display=None,
        )
        det = detection_scale(ps, rr.regions, pno + 1,
                              dimensions=page_dimensions(page_data))
        pd = rr.detection_page_data
        doors = detect_doors(pd.paths, pd.text_spans, None, scale_factor=det.factor)
        records.clear()
        network = W.detect_wall_network(
            pd.paths, pd.text_spans,
            exclude_path_indices=door_open_leaf_path_indices(doors, pd.paths),
            scale_factor=det.factor,
        )
        seg_idx = [set(s.face_path_indices) for s in network.segments]

        def survives(fi, fj):
            return any((fi.indices | fj.indices) <= idxs for idxs in seg_idx)

        print(f"\n{args.slug} page {pno + 1} f={det.factor:.3f} "
              f"candidate pairs: {len(records)}")
        if not records:
            continue
        tapers = sorted(r[1] for r in records)
        pct = lambda q: tapers[min(len(tapers) - 1, int(q * len(tapers)))]  # noqa: E731
        print(f"  taper px: median={statistics.median(tapers):.2f} "
              f"p90={pct(0.9):.2f} p99={pct(0.99):.2f} max={tapers[-1]:.2f}")
        surv = sorted(
            ((t / max(s_lo, s_hi, 1e-6), t, sp, s_lo, s_hi, ov, fi, fj)
             for sp, t, ov, s_lo, s_hi, fi, fj in records if survives(fi, fj)),
            key=lambda r: -r[0],
        )
        print(f"  surviving pairs: {len(surv)}; max ratio "
              f"{surv[0][0] if surv else 0:.3f}; candidate pairs over 0.5: "
              f"{sum(1 for r in records if r[1] / max(r[3], r[4], 1e-6) > 0.5)}")
        for ratio, t, sp, s_lo, s_hi, ov, fi, fj in surv[:8]:
            print(f"    ratio={ratio:.3f} taper={t:.1f} sp={sp:.1f} "
                  f"s_lo={s_lo:.1f} s_hi={s_hi:.1f} ov={ov:.0f} "
                  f"fi={tuple(round(v) for v in fi.p1)}-{tuple(round(v) for v in fi.p2)} "
                  f"sw={fi.stroke_width:.2f} layer={fi.layer} "
                  f"fj={tuple(round(v) for v in fj.p1)}-{tuple(round(v) for v in fj.p2)} "
                  f"sw={fj.stroke_width:.2f} layer={fj.layer}")
        print(f"  --- pairs with taper > {args.thresh}px:")
        for sp, t, ov, s_lo, s_hi, fi, fj in sorted(records, key=lambda r: -r[1]):
            if t <= args.thresh:
                continue
            dang = _angle_diff_mod180(
                _line_angle_deg(fi.p1, fi.p2), _line_angle_deg(fj.p1, fj.p2))
            print(f"   taper={t:5.1f} sp={sp:5.1f} s_lo={s_lo:5.1f} s_hi={s_hi:5.1f} "
                  f"ov={ov:6.1f} dang={dang:4.2f} survives={survives(fi, fj)} "
                  f"fi={tuple(round(v) for v in fi.p1)}-{tuple(round(v) for v in fi.p2)} "
                  f"L={_line_length(fi.p1, fi.p2):.0f} sw={fi.stroke_width:.2f} "
                  f"weak={fi.weak} layer={fi.layer} "
                  f"fj={tuple(round(v) for v in fj.p1)}-{tuple(round(v) for v in fj.p2)} "
                  f"L={_line_length(fj.p1, fj.p2):.0f} sw={fj.stroke_width:.2f} "
                  f"weak={fj.weak} layer={fj.layer}")


if __name__ == "__main__":
    main()
