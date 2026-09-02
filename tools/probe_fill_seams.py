"""Measure the two FILL-SEAM gaps on a corpus sheet (detection/walls.py).

Exporters triangulate filled wall polygons; the shared diagonal arrives as an
`l` item with fill on both sides — a SEAM, never drawn ink (`_fill_seams`).

Gap A (closed 2026-09-02): a seam carrying the fill's own colour as a width-0
stroke (recorded 1.0px) entered `_collect_wall_faces` as a STROKED face. This
reports how many seams would still do so — expected 0 everywhere now.

Gap B (open): `_collect_fill_rings` chains consecutive same-fill edges into
one ring, so an exporter that starts triangle 2 at triangle 1's start vertex
yields a six-edge chain that REVISITS its start; shapely rejects the
self-touching polygon, both triangles are dropped and the seam is never found
(s20: 19 grey wall-band chains, its chord among them). This reports, per
sheet, the chains that revisit their start EXACTLY (within EXACT_TOL), whether
any ring valid today would be touched by splitting there (must be 0), and the
sub-rings a split would recover by fill class — with band-shaped and marker
(`_FillRing.is_marker`) counts, because a recovered 12x12 jamb stub splits
into two <= 24px triangles that the marker rule then treats as arrowheads.

Usage:
    python tools/probe_fill_seams.py s20 [--list]

Runs extract -> cached regions -> scales offline, exactly as tools/regress.py
does; needs the sheet under fixtures/sheets/ and its region cache.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fitz  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import detection.walls as W  # noqa: E402
from detection.geometry import _distance, _line_angle_deg, _line_length  # noqa: E402
from extraction.extractor import extract_page  # noqa: E402
from pipeline import resolve_page_regions  # noqa: E402
from scale.factor import detection_scale  # noqa: E402
from scale.resolver import resolve_page_scales  # noqa: E402
from scale.store import load_stored  # noqa: E402
from scale.viewport import viewport_scales  # noqa: E402

EXACT_TOL = 0.01   # an exporter re-emits the shared vertex bit-for-bit


def fill_chains(paths):
    """Replay _collect_fill_rings' chaining: (fill key, points, path indices)
    for every CLOSED chain (first-to-last within 2px), valid or not."""
    out = []
    key_, pts, idx = None, [], []

    def flush():
        nonlocal key_, pts, idx
        if key_ is not None and len(pts) >= 4 and _distance(pts[0], pts[-1]) <= 2.0:
            out.append((key_, list(pts), list(idx)))
        key_, pts, idx = None, [], []

    for p in paths:
        if p.fill is not None and len(p.points) >= 2 and p.item_type == "l":
            key = W._fill_key(p.fill)
            a, b = p.points[0], p.points[-1]
            if key_ == key and pts and _distance(pts[-1], a) <= 1.0:
                pts.append(b)
                idx.append(p.path_index)
                continue
            flush()
            key_, pts, idx = key, [a, b], [p.path_index]
            continue
        flush()
    flush()
    return out


def valid_ring(pts):
    if len(pts) < 3:
        return None
    poly = Polygon(pts)
    return poly if poly.is_valid and poly.area >= 4.0 else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--list", action="store_true", help="print each Gap-A face and Gap-B chain")
    args = ap.parse_args()

    manifest = json.loads((ROOT / "fixtures" / "MANIFEST.json").read_text())
    entry = next(s for s in manifest["sheets"] if s["slug"] == args.slug)
    pdf = str(ROOT / "fixtures" / "sheets" / entry["file"])
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
        det = detection_scale(ps, rr.regions, pno + 1)
        gates = W.WallGates.at(det.factor)
        paths = rr.detection_page_data.paths
        by_idx = {p.path_index: p for p in paths}

        # Gap A — seams that still reach face collection.
        rings = W._collect_fill_rings(paths)
        fill_is_wall = W._rate_fill_classes(rings, gates=gates)
        seams, _ = W._fill_seams(rings, paths)
        markers = {i for r in rings if r.is_marker() for i in r.indices} | seams
        faces, _ = W._collect_wall_faces(paths, fill_is_wall, markers, frozenset(seams), gates=gates)
        face_idx = {i for f in faces for i in f.indices}
        gap_a = sorted(i for i in seams if i in face_idx)

        # Gap B — chains revisiting their start exactly.
        n_valid = n_invalid = n_valid_exact = 0
        exact_chains = []
        recovered: dict[tuple, list] = {}
        for key, pts, idx in fill_chains(paths):
            today = valid_ring(pts[:-1])
            exact = [k for k in range(2, len(pts) - 1) if _distance(pts[0], pts[k]) <= EXACT_TOL]
            if today is not None:
                n_valid += 1
                n_valid_exact += 1 if exact else 0
                continue
            n_invalid += 1
            if not exact:
                continue
            cuts = [0] + exact + [len(pts) - 1]
            subs = []
            for s, e in zip(cuts, cuts[1:]):
                sub = pts[s:e + 1]
                poly = valid_ring(sub[:-1]) if _distance(sub[0], sub[-1]) <= 2.0 else None
                if poly is not None:
                    short, long_ = W._equivalent_sides(poly)
                    r = W._FillRing(key=key, poly=poly, short=short, long=long_, indices=set())
                    subs.append(r)
                    ent = recovered.setdefault(key, [0, 0, 0, 0.0])
                    ent[0] += 1
                    ent[1] += 1 if r.is_band(gates) else 0
                    ent[2] += 1 if r.is_marker() else 0
                    ent[3] += long_
            exact_chains.append((idx, len(pts) - 1, key, subs))

        print(f"\n{args.slug} page {pno + 1} f={det.factor:.3f} paths={len(paths)} rings={len(rings)} "
              f"seams={len(seams)}")
        print(f"  GAP A: seams still reaching face collection: {len(gap_a)}")
        print(f"  GAP B: fill chains valid={n_valid} invalid={n_invalid}; exact start-revisit chains "
              f"(invalid today)={len(exact_chains)}; VALID rings an exact split would touch={n_valid_exact}")
        for key, (n, nb, nm, tl) in sorted(recovered.items(), key=lambda kv: -kv[1][0]):
            print(f"    split would recover fill={key} white={W._is_background_fill(key)}: "
                  f"rings={n} band-shaped={nb} marker-flagged={nm} total_long={tl:.0f}px")
        if args.list:
            for i in gap_a[:20]:
                p = by_idx[i]
                a, b = p.points[0], p.points[-1]
                print(f"    A {i} ({a[0]:.1f},{a[1]:.1f})-({b[0]:.1f},{b[1]:.1f}) L={_line_length(a, b):.1f} "
                      f"ang={_line_angle_deg(a, b):.2f} w={p.stroke_width:.2f} layer={p.layer!r}")
            for idx, n, key, subs in exact_chains[:20]:
                desc = "; ".join(
                    f"{r.poly.bounds[2] - r.poly.bounds[0]:.1f}x{r.poly.bounds[3] - r.poly.bounds[1]:.1f}"
                    f"{' marker' if r.is_marker() else ''}" for r in subs
                )
                print(f"    B chain {idx[0]}..{idx[-1]} edges={n} fill={key} -> {len(subs)} rings [{desc}]")


if __name__ == "__main__":
    main()
