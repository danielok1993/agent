"""Wall-pen census (W-gate iteration 3, step 11): every multi-pen sheet, per
stroke PEN, on the pipeline's exact inputs (harness = the sweep's chain).

Per pen: share of the network's PAIRED stroked face length (the input of
ROOM_WALL_PEN_MIN_FRAC), the same-pen segments' thickness distribution and
material share (_band_has_wall_material on each), lone-eligible ink (unpaired
faces at/above the lone-barrier stroke gate), whether the pen's ink alone
closes room-sized loops, and — the candidate discriminator — how many of the
sheet's confident openings the pen FRAMES: its ink lies at the jamb a door
plug's tail reaches (the room stage's own final plugs, from _clip_plug_tails)
or at the end zones of a window seal.

Usage: .venv/bin/python tools/census_scratch/step11/pen_census.py [slug[@factor] ...]
Default: s01 s01@0.5423 s02 s03 s04 s08 s12 s17
"""
import json
import math
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403  (H, rooms, F542, run_tapped, room_list)
from detection import walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg  # noqa: E402
from shapely.geometry import box, LineString, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

DEFAULT = ["s01", f"s01@{F542}", "s02", "s03", "s04", "s08", "s12", "s17"]
BIG = 1e5


def _wmedian(pairs):
    """Length-weighted median of (value, weight)."""
    pairs = sorted(pairs)
    tot = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= tot / 2:
            return v
    return pairs[-1][0] if pairs else 0.0


def census(slug, factor):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    r = run_tapped(page, factor)
    net = r["extras"]["network"]
    gw = walls.WallGates.at(f)
    gr = rooms.RoomGates.at(f)
    paired = net.paired_face_indices()
    ref = net.wall_stroke_reference()
    gate = max(walls.WALL_MIN_STROKE_WIDTH_PX, rooms.ROOM_BARRIER_STROKE_RATIO * ref)
    all_geo = r["extras"]["all_geo"]
    doors = [c for c in all_geo if c.entity_type == "door"]
    windows = [c for c in all_geo if c.entity_type == "window"]
    conf_doors = [c for c in doors if c.confidence >= rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE]
    conf_windows = [c for c in windows if c.confidence >= rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE]
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

    faces_by_path = defaultdict(list)
    for fc in net.faces:
        for pi in fc.indices:
            faces_by_path[pi].append(fc)

    pens = {}
    for fc in net.faces:
        if not fc.stroked or fc.pen is None:
            continue
        d = pens.setdefault(fc.pen, dict(
            total=0.0, paired=0.0, lone_elig=0.0, lone_any=0.0, n_faces=0,
            widths=set(), longest_face=0.0, layers=set(),
            faces=[], segs=[], seg_len=0.0, seg_mat_len=0.0, seg_ths=[],
            frames_doors=set(), frames_windows=set(), frames_doors_gate=set(),
            frames_windows_gate=set(), loops=0, loops_area=0.0,
            hatchlike=0.0,
        ))
        L = _line_length(fc.p1, fc.p2)
        d["total"] += L
        d["n_faces"] += 1
        d["widths"].add(round(fc.stroke_width, 2))
        d["longest_face"] = max(d["longest_face"], L)
        d["faces"].append(fc)
        if fc.indices & paired:
            d["paired"] += L
        else:
            d["lone_any"] += L
            if fc.stroke_width >= gate:
                d["lone_elig"] += L
        if (L <= gw.WALL_HATCH_MAX_LEN_PX
                and walls._is_diagonal_hatch_angle(_line_angle_deg(fc.p1, fc.p2))):
            d["hatchlike"] += L
    total_paired = sum(d["paired"] for d in pens.values())

    # Same-pen segments: every stroked member face is this pen.
    marks = walls._collect_material_marks(
        page.page_data.paths, gates=gw,
        max_len=max(gw.WALL_HATCH_MAX_LEN_PX, gw.WALL_THROUGH_HATCH_MAX_PX * math.sqrt(2) + 2),
    )
    mixed_len = 0.0
    for s in net.segments:
        spens = set()
        stroked_any = False
        for pi in s.face_path_indices:
            for fc in faces_by_path.get(pi, ()):
                if fc.stroked and fc.pen is not None:
                    spens.add(fc.pen)
                    stroked_any = True
        L = _line_length(s.p1, s.p2)
        if len(spens) == 1:
            pen = next(iter(spens))
            d = pens[pen]
            d["segs"].append(s)
            d["seg_len"] += L
            d["seg_ths"].append((s.thickness_px, L))
            c = walls._Seg(p1=s.p1, p2=s.p2, thickness=s.thickness_px)
            if walls._band_has_wall_material(c, marks, gates=gw):
                d["seg_mat_len"] += L
        elif len(spens) > 1:
            mixed_len += L

    # Per-pen MATERIAL (what the pen's ink would be as barrier): face lines
    # buffered like line barriers (square caps), hatch-angle short faces and
    # door-zone faces excluded, plus its same-pen segment solids.
    def pen_material(d, min_width=0.0):
        parts = []
        for fc in d["faces"]:
            if fc.stroke_width < min_width or in_zone(fc.p1, fc.p2):
                continue
            L = _line_length(fc.p1, fc.p2)
            if (L <= gw.WALL_HATCH_MAX_LEN_PX
                    and walls._is_diagonal_hatch_angle(_line_angle_deg(fc.p1, fc.p2))
                    and not fc.wall_fill):
                continue
            parts.append(LineString([fc.p1, fc.p2]).buffer(rooms.ROOM_LINE_BARRIER_PX, cap_style=3))
        for s in d["segs"]:
            parts.append(LineString([s.p1, s.p2]).buffer(
                s.thickness_px / 2.0 + rooms.ROOM_WALL_DILATE_PX, cap_style=2))
        return unary_union(parts) if parts else Polygon()

    # Opening jamb zones from the room stage's own final plugs.
    door_tails = {}   # bbox -> list of tail polygons (plug beyond the bbox corners)
    for bb, rec in r["seals"].items():
        c = rec["cand"]
        if c.confidence < rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE or not rec["plugs"]:
            continue
        x0, y0, x1, y1 = bb
        tails = []
        for poly, kind, edge in rec["plugs"]:
            if edge is None or poly is None or poly.is_empty:
                continue
            if edge in (0, 1):
                inner = box(x0, y0 - BIG, x1, y1 + BIG)
            else:
                inner = box(x0 - BIG, y0, x1 + BIG, y1)
            t = poly.difference(inner)
            if not t.is_empty:
                tails.append(t)
        if tails:
            door_tails[bb] = unary_union(tails)
    win_zones = {}
    S = gr.ROOM_OPENING_SEAL_PX
    for c in conf_windows:
        x0, y0, x1, y1 = c.bbox
        if c.evidence.get("orientation") == "diagonal":
            continue
        if (x1 - x0) >= (y1 - y0):
            z = unary_union([box(x0 - S, y0 - 2, x0, y1 + 2), box(x1, y0 - 2, x1 + S, y1 + 2)])
        else:
            z = unary_union([box(x0 - 2, y0 - S, x1 + 2, y0), box(x0 - 2, y1, x1 + 2, y1 + S)])
        win_zones[tuple(c.bbox)] = z

    page_poly = box(0, 0, page.page_data.width_px, page.page_data.height_px)
    out = {"slug": slug, "f": f, "ref": ref, "gate": gate, "total_paired": total_paired,
           "mixed_len": mixed_len, "n_conf_doors": len(conf_doors),
           "n_plugged_doors": len(door_tails), "n_conf_windows": len(win_zones),
           "pens": {}}
    for pen, d in pens.items():
        mat = pen_material(d)
        mat_gate = pen_material(d, min_width=gate)
        for bb, tails in door_tails.items():
            if mat.intersects(tails):
                d["frames_doors"].add(bb)
            if mat_gate.intersects(tails):
                d["frames_doors_gate"].add(bb)
        for bb, z in win_zones.items():
            if mat.intersects(z):
                d["frames_windows"].add(bb)
            if mat_gate.intersects(z):
                d["frames_windows_gate"].add(bb)
        # loops the pen closes on its own
        comps = rooms._free_space_components(page_poly, mat) if not mat.is_empty else []
        loops = [c for c in comps
                 if c.area >= gr.ROOM_MIN_AREA_PX2 and not c.intersects(page_poly.exterior)]
        d["loops"] = len(loops)
        d["loops_area"] = sum(c.area for c in loops)
        ths = d["seg_ths"]
        out["pens"][str(pen)] = dict(
            total=d["total"], paired=d["paired"], share=(d["paired"] / total_paired if total_paired else 0),
            paired_frac_of_pen=(d["paired"] / d["total"] if d["total"] else 0),
            lone_elig=d["lone_elig"], lone_any=d["lone_any"], n_faces=d["n_faces"],
            widths=sorted(d["widths"]), longest_face=d["longest_face"],
            hatchlike=d["hatchlike"],
            n_segs=len(d["segs"]), seg_len=d["seg_len"],
            seg_mat_len=d["seg_mat_len"],
            seg_mat_share=(d["seg_mat_len"] / d["seg_len"] if d["seg_len"] else 0),
            th_min=(min(t for t, _ in ths) if ths else 0), th_med=_wmedian(ths),
            th_max=(max(t for t, _ in ths) if ths else 0),
            longest_seg=(max(L for _, L in ths) if ths else 0),
            frames_doors=len(d["frames_doors"]), frames_doors_gate=len(d["frames_doors_gate"]),
            frames_windows=len(d["frames_windows"]), frames_windows_gate=len(d["frames_windows_gate"]),
            loops=d["loops"], loops_area=d["loops_area"],
            wall_pen_today=(d["paired"] >= rooms.ROOM_WALL_PEN_MIN_FRAC * total_paired),
        )
    return out


def report(o):
    print(f"\n=== {o['slug']} f={o['f']:.3f}  paired stroked {o['total_paired']:.0f}px "
          f"(mixed-pen segs {o['mixed_len']:.0f}px)  ref={o['ref']:.2f} gate={o['gate']:.2f}  "
          f"conf doors {o['n_conf_doors']} (plugged {o['n_plugged_doors']}), conf windows {o['n_conf_windows']}")
    hdr = (f"{'pen':22} {'wall?':5} {'share':>6} {'pen-paired':>10} {'loneElig':>8} {'nSeg':>4} "
           f"{'segLen':>6} {'mat%':>5} {'thMin':>5} {'thMed':>5} {'thMax':>5} {'lngSeg':>6} "
           f"{'lngFace':>7} {'D':>3} {'Dg':>3} {'W':>3} {'Wg':>3} {'loops':>5} {'widths'}")
    print(hdr)
    for pen, d in sorted(o["pens"].items(), key=lambda kv: -kv[1]["share"]):
        print(f"{pen:22} {'WALL' if d['wall_pen_today'] else 'no':5} {100 * d['share']:5.1f}% "
              f"{100 * d['paired_frac_of_pen']:9.0f}% {d['lone_elig']:8.0f} {d['n_segs']:4d} "
              f"{d['seg_len']:6.0f} {100 * d['seg_mat_share']:4.0f}% {d['th_min']:5.1f} {d['th_med']:5.1f} "
              f"{d['th_max']:5.1f} {d['longest_seg']:6.0f} {d['longest_face']:7.0f} "
              f"{d['frames_doors']:3d} {d['frames_doors_gate']:3d} {d['frames_windows']:3d} "
              f"{d['frames_windows_gate']:3d} {d['loops']:5d} {d['widths']}")


if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT
    results = []
    for a in args:
        slug, _, fac = a.partition("@")
        o = census(slug, float(fac) if fac else None)
        results.append(o)
        report(o)
    with open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step11/pen_census.json", "w") as fh:
        json.dump(results, fh, indent=1, default=str)
