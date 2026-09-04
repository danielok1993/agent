"""probe_box.py <slug> <seal> x0 y0 x1 y1 [door_id ...]

Run the harness at the given ROOM_OPENING_SEAL_PX, reconstruct every door's
FINAL seal (plugs after _restrict_swing_plugs + the fallback-tier filter, the
folding chain gap plug, or the dilated-bbox fallback), and print what lies in
the box: each door seal intersecting it, the barrier-union area inside it, and
the free-space components touching it. Optional door ids get a per-sample
distance dump of every edge's profile.
"""
import math
import sys
from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402

slug = sys.argv[1]
seal = float(sys.argv[2])
bx = box(*[float(v) for v in sys.argv[3:7]])
dump_ids = set(sys.argv[7:])

pages = H.load(slug)
page = pages[0]

calls, barriers_seen, gap_plugs = [], [], []
o_plugs, o_restrict, o_fsc, o_gap = (rooms._door_plugs, rooms._restrict_swing_plugs,
                                     rooms._free_space_components, rooms._folding_chain_gap_plug)


def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED):
    out = o_plugs(bbox, wall_material, skip_edges, gates=gates)
    calls.append({"bbox": bbox, "mat": wall_material, "skip": skip_edges, "gates": gates,
                  "out": out, "cand": None, "restricted": None})
    return out


def tap_restrict(c, plugs):
    out = o_restrict(c, plugs)
    for call in reversed(calls):
        if call["cand"] is None:
            call["cand"] = c
            call["restricted"] = out
            break
    return out


def tap_gap(c, network, wall_material, *, gates=rooms.ROOM_GATES_UNSCALED):
    out = o_gap(c, network, wall_material, gates=gates)
    gap_plugs.append((c, out))
    return out


def tap_fsc(page_poly, barriers):
    barriers_seen.append(barriers)
    return o_fsc(page_poly, barriers)


rooms._door_plugs, rooms._restrict_swing_plugs = tap_plugs, tap_restrict
rooms._free_space_components, rooms._folding_chain_gap_plug = tap_fsc, tap_gap
with H.overrides(absolute={"ROOM_OPENING_SEAL_PX": seal}):
    ents, extras = H.run(page, keep_network=True)
    gates = rooms.RoomGates.at(page.scale_factor)
rooms._door_plugs, rooms._restrict_swing_plugs = o_plugs, o_restrict
rooms._free_space_components, rooms._folding_chain_gap_plug = o_fsc, o_gap

seal_px = gates.ROOM_OPENING_SEAL_PX
print(f"{slug} seal={seal_px} f={page.scale_factor:.3f} box={bx.bounds}")

# Reconstruct final door seals exactly as detect_rooms does.
gap_by_id = {c.candidate_id: g for c, g in gap_plugs}
for call in calls:
    c = call["cand"]
    if c is None:
        continue
    plugs = list(call["restricted"] or [])
    kinds = {e: k for _, k, e in plugs}
    if c.confidence < rooms.ROOM_OPENING_MIN_CONFIDENCE:
        plugs = [(p, k, e) for p, k, e in plugs
                 if k == "interrupted"
                 or p.intersection(call["mat"]).area >= rooms.ROOM_PLUG_IN_WALL_FRAC * p.area]
    if hasattr(rooms, "_clip_plug_tails"):        # step 5: tails end at material
        plugs = rooms._clip_plug_tails(c.bbox, plugs, call["mat"], gates=gates)
    g = gap_by_id.get(c.candidate_id)
    if g is not None:
        plugs.append((g, "chain_gap", None))
    if plugs:
        seal_geom = unary_union([p for p, _, _ in plugs])
        how = "plugs:" + ",".join(f"{k}@{e}" for _, k, e in plugs)
    elif c.confidence >= rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE:
        seal_geom = box(*c.bbox).buffer(seal_px, join_style=2)
        how = "BBOX-FALLBACK"
    else:
        seal_geom = None
        how = "none"
    hit = seal_geom is not None and seal_geom.intersects(bx)
    if hit or c.candidate_id in dump_ids:
        bb = tuple(round(v) for v in c.bbox)
        print(f"\n{c.candidate_id} conf={c.confidence:.2f} type={c.evidence.get('assembly_type')} bbox={bb} "
              f"raw_kinds={kinds} -> {how}  in_box_area={seal_geom.intersection(bx).area if seal_geom is not None else 0:.0f}")
        for p, k, e in plugs:
            print(f"      plug {k}@{e} bounds={tuple(round(v,1) for v in p.bounds)} area={p.area:.0f} in_mat={p.intersection(call['mat']).area/p.area:.2f}")
        if c.candidate_id in dump_ids:
            mat_in = call["mat"].intersection(bx)
            for g in getattr(mat_in, "geoms", [mat_in]):
                if not g.is_empty:
                    print(f"      material piece bounds={tuple(round(v,1) for v in g.bounds)} area={g.area:.0f}")
    if c.candidate_id in dump_ids:
        x0, y0, x1, y1 = c.bbox
        edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
        for e, (p, q) in enumerate(edges):
            length = math.hypot(q[0] - p[0], q[1] - p[1])
            ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
            S = seal_px
            a = (p[0] - ux * S, p[1] - uy * S)
            b = (q[0] + ux * S, q[1] + uy * S)
            ext = length + 2 * S
            line = LineString([a, b])
            n = max(int(ext / rooms.ROOM_PLUG_SAMPLE_PX), 8) + 1
            d = [line.interpolate(ext * i / (n - 1)).distance(call["mat"]) for i in range(n)]
            quarter = n // 4
            win = min(quarter, int(math.ceil(gates.ROOM_PLUG_ANCHOR_WIN_PX / rooms.ROOM_PLUG_SAMPLE_PX)) + 1)
            trim = quarter + int(math.ceil(rooms.ROOM_PLUG_NEAR_PX / rooms.ROOM_PLUG_SAMPLE_PX))
            print(f"   edge{e} n={n} quarter={quarter} win={win} trim={trim} step={ext/(n-1):.2f}")
            print("      d=" + " ".join(f"{v:.1f}" for v in d))
            mid = [v <= rooms.ROOM_PLUG_MID_NEAR_PX for v in d][trim:n - trim]
            print(f"      mid[{trim}:{n-trim}] in_plane={sum(mid)}/{len(mid)} = {sum(mid)/len(mid):.2f}")

barriers = barriers_seen[-1]
print(f"\nbarrier area in box: {barriers.intersection(bx).area:.0f} px2")
rooms_in = [e for e in ents if e["entity_type"] == "room" and box(*e["bbox"]).intersects(bx)]
for e in rooms_in:
    from shapely.geometry import Polygon
    poly = Polygon(e["evidence"]["polygon"])
    print(f"room bbox={tuple(round(v) for v in e['bbox'])} area={poly.area:.0f} in_box={poly.intersection(bx).area:.0f}")
