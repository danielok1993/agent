"""Interior-linework census for the 36f-40f candidates (step 4).

Convention under test: a band wider than the standard cap is a wall only
when it is drawn as a BUILT-UP wall — further stroked linework parallel to
its faces lies strictly inside the band (cavity-wall leaf lines, a render or
plaster line, block courses) — or when it carries material. A single pair
of lines at 360-400mm with nothing between (a site boundary drawn double, a
wardrobe box edge) is not.

For every candidate (the base run's wide_pairs in the band) this measures:
  interior_frac  — the fraction of the pair's overlap length covered by
                   stroked faces (strong, weak, lattice- or stair-demoted —
                   every face the network collected) parallel to the band
                   whose offset lies strictly inside it (WALL_MIN_THICKNESS
                   in from either face);
  n_interior     — how many such faces;
  material / through — the pipeline's own verdicts (from wide_pairs).
Then it joins each candidate to band_census*.json's admitted segments (by
midpoint/thickness) and to the rooms that changed, so the feature can be
read against the class.

Usage: .venv/bin/python tools/census_scratch/step4/interior_census.py [slugs...]
Writes step4/interior_census.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from detection import walls  # noqa: E402
from detection.geometry import _angle_diff_mod180, _line_angle_deg  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "interior_census.json"


def _load_admitted():
    recs = []
    for f in HERE.glob("band_census*.json"):
        recs.extend(json.loads(f.read_text()))
    return {(r["slug"], r["page"]): r for r in recs}


def _proj(p, origin, ux, uy):
    return (p[0] - origin[0]) * ux + (p[1] - origin[1]) * uy


def _perp(p, origin, ux, uy):
    return (p[0] - origin[0]) * -uy + (p[1] - origin[1]) * ux


def interior(cand, faces, gates):
    p1, p2, th = cand["p1"], cand["p2"], cand["th"]
    L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if L < 1e-6:
        return 0.0, 0
    ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
    axis = _line_angle_deg(p1, p2)
    inner = th / 2.0 - gates.WALL_MIN_THICKNESS_PX
    spans = []
    for f in faces:
        if not f["stroked"]:
            continue
        if _angle_diff_mod180(f["ang"], axis) > walls.WALL_PARALLEL_ANGLE_TOL:
            continue
        off = _perp(f["mid"], p1, ux, uy)
        if abs(off) >= inner:
            continue
        a, b = _proj(f["p1"], p1, ux, uy), _proj(f["p2"], p1, ux, uy)
        lo, hi = max(min(a, b), 0.0), min(max(a, b), L)
        if hi - lo > 1.0:
            spans.append((lo, hi))
    spans.sort()
    covered, cur = 0.0, None
    for lo, hi in spans:
        if cur is None or lo > cur[1]:
            if cur:
                covered += cur[1] - cur[0]
            cur = [lo, hi]
        else:
            cur[1] = max(cur[1], hi)
    if cur:
        covered += cur[1] - cur[0]
    return covered / L, len(spans)


def face_interior(cand, faces, gates):
    """The interior test over the FULL extent of the pair's two faces, not
    just their overlap: a cavity wall's leaf lines stop at its openings, so a
    stretch of the wall across an opening carries none, but the faces it
    lies on carry them elsewhere along their length — while a site boundary
    drawn double carries nothing anywhere. Faces are found by geometry
    (parallel, at ±th/2 from the centerline within 1 px, overlapping the
    pair). Returns (fraction over the union extent, union length)."""
    p1, p2, th = cand["p1"], cand["p2"], cand["th"]
    L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if L < 1e-6:
        return 0.0, 0.0
    ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
    axis = _line_angle_deg(p1, p2)
    lo_u, hi_u = 0.0, L
    for f in faces:
        if _angle_diff_mod180(f["ang"], axis) > walls.WALL_PARALLEL_ANGLE_TOL:
            continue
        off = _perp(f["mid"], p1, ux, uy)
        if abs(abs(off) - th / 2.0) > 1.0:
            continue
        a, b = _proj(f["p1"], p1, ux, uy), _proj(f["p2"], p1, ux, uy)
        if max(a, b) < 0.0 or min(a, b) > L:
            continue
        lo_u, hi_u = min(lo_u, min(a, b)), max(hi_u, max(a, b))
    ext = {"p1": (p1[0] + ux * lo_u, p1[1] + uy * lo_u),
           "p2": (p1[0] + ux * hi_u, p1[1] + uy * hi_u), "th": th}
    frac, _n = interior(ext, faces, gates)
    return frac, hi_u - lo_u


def openings_in_band(cand, geo, min_conf):
    """Fraction of the pair's length covered by confident door/window bboxes
    that intersect the band (the pipeline's own post-suppression candidates,
    what detect_rooms receives), and their count/types — 'an opening is cut
    out of a wall' (step 11) read at the pairing stage."""
    from shapely.geometry import LineString, box
    p1, p2, th = cand["p1"], cand["p2"], cand["th"]
    L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if L < 1e-6:
        return 0.0, 0, []
    band = LineString([p1, p2]).buffer(th / 2.0, cap_style=2)
    ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
    spans, kinds = [], []
    for c in geo:
        if c.confidence < min_conf:
            continue
        b = box(*c.bbox)
        inter = band.intersection(b)
        if inter.is_empty or inter.area < 0.25 * min(b.area, band.area):
            continue
        ts = [_proj(pt, p1, ux, uy) for pt in inter.exterior.coords]
        lo, hi = max(min(ts), 0.0), min(max(ts), L)
        if hi > lo:
            spans.append((lo, hi))
            kinds.append(f"{c.entity_type}:{c.confidence:.2f}")
    spans.sort()
    covered, cur = 0.0, None
    for lo, hi in spans:
        if cur is None or lo > cur[1]:
            if cur:
                covered += cur[1] - cur[0]
            cur = [lo, hi]
        else:
            cur[1] = max(cur[1], hi)
    if cur:
        covered += cur[1] - cur[0]
    return covered / L, len(spans), kinds


def census(slug, admitted):
    from detection.rooms import ROOM_OPENING_MIN_CONFIDENCE
    out = []
    for p in H.load(slug):
        f = p.scale_factor
        lo, hi = 36.0 * f, 40.0 * f
        taps = H.Taps()
        _ents, extras = H.run(p, taps=taps)
        geo = [c for c in extras["all_geo"] if c.entity_type in ("door", "window")]
        gates = walls.WallGates.at(f)
        # every face the network collected: strong (taps.faces) — weak faces
        # carry no geometry in the tap, so the interior test reads strong
        # stroked faces only (leaf lines, finish lines, courses are strong).
        faces = taps.faces
        rec = admitted.get((slug, p.page_number), {})
        new_segs = rec.get("segments_new", [])
        rooms = rec.get("rooms_moved", []) + rec.get("rooms_gone", []) + rec.get("rooms_new", [])
        for w in taps.wide_pairs:
            if not (lo < w["th"] <= hi + 1e-6):
                continue
            frac, n = interior(w, faces, gates)
            ffrac, fext = face_interior(w, faces, gates)
            ofrac, n_open, kinds = openings_in_band(w, geo, ROOM_OPENING_MIN_CONFIDENCE)
            mid = w["mid"]
            adm = [s for s in new_segs
                   if abs(s["mid"][0] - mid[0]) <= 6 and abs(s["mid"][1] - mid[1]) <= 6
                   and abs(s["th"] - w["th"]) <= 1.0]
            near_rooms = [r for r in rooms
                          if (r.get("bbox") and r["bbox"][0] - 12 <= mid[0] <= r["bbox"][2] + 12
                              and r["bbox"][1] - 12 <= mid[1] <= r["bbox"][3] + 12)]
            out.append({
                "slug": slug, "page": p.page_number, "factor": round(f, 4),
                "th": round(w["th"], 2), "len": round(w["len"], 1),
                "mid": [round(mid[0]), round(mid[1])],
                "stroked": bool(w["stroked"]), "fill": bool(w["fill"]),
                "pen": w.get("pen"), "sw": w.get("sw"),
                "material": bool(w.get("material")), "through": bool(w.get("through")),
                "interior_frac": round(frac, 3), "n_interior": n,
                "face_interior_frac": round(ffrac, 3), "face_extent": round(fext, 1),
                "openings_frac": round(ofrac, 3), "n_openings": n_open, "openings": kinds,
                "admitted": bool(adm), "rooms_touched": len(near_rooms),
            })
            print(f"{slug} th {w['th']:.2f} len {w['len']:.0f} at {mid[0]:.0f},{mid[1]:.0f} "
                  f"str={int(bool(w['stroked']))} fill={int(bool(w['fill']))} mat={int(bool(w.get('material')))} "
                  f"interior {frac:.2f} (n={n}) face-interior {ffrac:.2f} over {fext:.0f} "
                  f"openings {ofrac:.2f} (n={n_open} {kinds}) "
                  f"admitted={int(bool(adm))} rooms={len(near_rooms)}", flush=True)
    return out


if __name__ == "__main__":
    slugs = sys.argv[1:] or ["s01", "s02", "s03", "s05", "s10", "s11", "s12", "s14", "s15", "s16", "s17", "s18"]
    admitted = _load_admitted()
    rows = []
    for s in slugs:
        rows.extend(census(s, admitted))
    OUT.write_text(json.dumps(rows, indent=1))
    print("wrote", OUT)
