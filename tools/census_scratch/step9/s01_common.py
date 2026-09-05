"""Shared: run s01 (or any slug) through the harness at a factor with the
door-seal taps, keyed by door BBOX (ids shift between factors)."""
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from shapely.geometry import box, Polygon, LineString  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

F542 = 50.0 / 92.2


def run_tapped(page, factor, mult=None):
    clipped, stamps, gaps, barriers_seen, plug_calls = [], [], [], [], []
    o_clip, o_stamp, o_gap, o_fsc, o_plugs = (
        rooms._clip_plug_tails, rooms._plane_stamp, rooms._folding_chain_gap_plug,
        rooms._free_space_components, rooms._door_plugs)

    def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED, **kw):
        out = o_plugs(bbox, wall_material, skip_edges, gates=gates, **kw)
        plug_calls.append((tuple(bbox), wall_material, frozenset(skip_edges), gates, out))
        return out

    def tap_clip(bbox, plugs, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_clip(bbox, plugs, material, gates=gates)
        clipped.append((tuple(bbox), out, material, gates))
        return out

    def tap_stamp(c, skip_edges, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_stamp(c, skip_edges, material, gates=gates)
        stamps.append((c, out))
        return out

    def tap_gap(c, network, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_gap(c, network, material, gates=gates)
        gaps.append((c, out))
        return out

    def tap_fsc(page_poly, barriers):
        barriers_seen.append(barriers)
        return o_fsc(page_poly, barriers)

    rooms._clip_plug_tails, rooms._plane_stamp = tap_clip, tap_stamp
    rooms._folding_chain_gap_plug, rooms._free_space_components = tap_gap, tap_fsc
    rooms._door_plugs = tap_plugs
    try:
        with H.overrides(mult=mult or {}):
            ents, extras = H.run(page, factor=factor, keep_network=True)
    finally:
        rooms._clip_plug_tails, rooms._plane_stamp = o_clip, o_stamp
        rooms._folding_chain_gap_plug, rooms._free_space_components = o_gap, o_fsc
        rooms._door_plugs = o_plugs
    doors = [c for c in extras["all_geo"] if c.entity_type == "door"]
    by_bbox = {tuple(c.bbox): c for c in doors}
    seals = {}
    for bbox, plugs, mat, gates in clipped:
        c = by_bbox.get(bbox)
        if c is None:
            continue
        seals[bbox] = {"cand": c, "plugs": list(plugs), "mat": mat, "stamp": None, "gates": gates}
    for c, g in gaps:
        if g is not None and tuple(c.bbox) in seals:
            seals[tuple(c.bbox)]["plugs"].append((g, "chain_gap", None))
    for c, st in stamps:
        seals.setdefault(tuple(c.bbox), {"cand": c, "plugs": [], "mat": None, "stamp": None, "gates": None})
        seals[tuple(c.bbox)]["stamp"] = st
    for bb, rec in seals.items():
        if rec["plugs"]:
            rec["geom"] = unary_union([p for p, _, _ in rec["plugs"]])
            rec["how"] = "plugs:" + ",".join(f"{k}@{e}" for _, k, e in rec["plugs"])
        elif rec["stamp"] is not None:
            rec["geom"] = rec["stamp"]
            rec["how"] = "PLANE-STAMP"
        else:
            rec["geom"] = None
            rec["how"] = "none"
    # last _door_plugs call per bbox (the retry with leaves, if any)
    last_call = {}
    for bbox, mat, skip, gates, out in plug_calls:
        last_call[bbox] = (mat, skip, gates, out)
    return {"ents": ents, "extras": extras, "seals": seals,
            "barriers": barriers_seen[-1], "plug_calls": last_call,
            "rooms": room_list(ents)}


def room_list(ents):
    out = []
    for e in ents:
        if e["entity_type"] != "room":
            continue
        poly = Polygon(e["evidence"]["polygon"])
        out.append({"bbox": tuple(round(v) for v in e["bbox"]), "poly": poly, "area": poly.area,
                    "doors": e["evidence"].get("door_openings"),
                    "windows": e["evidence"].get("window_openings"),
                    "conf": e["confidence"], "ent": e})
    return out


EDGE = {0: "top", 1: "bot", 2: "left", 3: "right"}


def profile(bbox, mat, gates, edge_idx):
    """Replicate _door_plugs' per-edge numbers."""
    x0, y0, x1, y1 = bbox
    edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
             ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
    p, q = edges[edge_idx]
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
    S = gates.ROOM_OPENING_SEAL_PX
    a = (p[0] - ux * S, p[1] - uy * S)
    b = (q[0] + ux * S, q[1] + uy * S)
    ext = length + 2 * S
    line = LineString([a, b])
    n = max(int(ext / rooms.ROOM_PLUG_SAMPLE_PX), 8) + 1
    step = ext / (n - 1)
    pts = [line.interpolate(ext * i / (n - 1)) for i in range(n)]
    d = [pt.distance(mat) for pt in pts]
    covered = [v <= rooms.ROOM_PLUG_NEAR_PX for v in d]
    quarter = n // 4
    win = min(quarter, int(math.ceil(gates.ROOM_PLUG_ANCHOR_WIN_PX / rooms.ROOM_PLUG_SAMPLE_PX)) + 1)
    start_cov = sum(covered[:win]) / win
    end_cov = sum(covered[-win:]) / win
    trim = quarter + int(math.ceil(rooms.ROOM_PLUG_NEAR_PX / rooms.ROOM_PLUG_SAMPLE_PX))
    in_plane = [v <= rooms.ROOM_PLUG_MID_NEAR_PX for v in d]
    mid = in_plane[trim:n - trim] or in_plane[quarter:n - quarter]
    mid_cov = sum(mid) / len(mid)
    total_cov = sum(covered) / n
    touch = [v <= gates.ROOM_PLUG_HALF_WIDTH_PX for v in d]
    interrupted = (mid_cov <= rooms.ROOM_PLUG_MID_COV_MAX and any(touch[:win]) and any(touch[-win:]))
    ends_ok = start_cov >= rooms.ROOM_PLUG_END_COV_MIN and end_cov >= rooms.ROOM_PLUG_END_COV_MIN
    full = total_cov >= rooms.ROOM_PLUG_FULL_COV_MIN
    kind = None
    if ends_ok:
        kind = "interrupted" if interrupted else ("full" if full else None)
    return dict(n=n, step=step, win=win, trim=trim, d=d, covered=covered, touch=touch,
                start_cov=start_cov, end_cov=end_cov, mid_cov=mid_cov, total_cov=total_cov,
                ends_ok=ends_ok, interrupted=interrupted, full=full, kind=kind,
                pts=[(pt.x, pt.y) for pt in pts], seal=S, length=length)


def print_profile(label, bbox, mat, gates, edge_idx):
    pr = profile(bbox, mat, gates, edge_idx)
    print(f"  [{label}] edge {edge_idx} ({EDGE[edge_idx]}) seal={pr['seal']:.2f} half={gates.ROOM_PLUG_HALF_WIDTH_PX:.2f} "
          f"anchor_win={gates.ROOM_PLUG_ANCHOR_WIN_PX:.1f} n={pr['n']} step={pr['step']:.2f} win={pr['win']} trim={pr['trim']}")
    print(f"      start_cov={pr['start_cov']:.2f} end_cov={pr['end_cov']:.2f} mid_cov={pr['mid_cov']:.2f} total={pr['total_cov']:.2f} "
          f"touchA={any(pr['touch'][:pr['win']])} touchB={any(pr['touch'][-pr['win']:])} -> {pr['kind']}")
    print("      d=" + " ".join(f"{v:.1f}" for v in pr["d"]))
    print("      x=" + " ".join(f"{x:.0f}" for x, _ in pr["pts"]) if edge_idx < 2 else
          "      y=" + " ".join(f"{y:.0f}" for _, y in pr["pts"]))
    return pr
