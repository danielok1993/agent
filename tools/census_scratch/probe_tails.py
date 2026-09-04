"""probe_tails.py <slug> [SEAL_PX ...] [--all]

W-gate iteration 3 step 5 — how far a kept plug's tail runs PAST the wall
material it touches. Runs the harness at each seal, reconstructs every door's
FINAL plug set exactly as detect_rooms does (after _restrict_swing_plugs and
the fallback-tier in-material filter), and for each of a kept plug's two
tails prints:

  tail_now   the tail's length today (the plug polygon's axial extent beyond
             the bbox corner; the sample-based trim, quantised to the profile
             step and capped at SEAL)
  mat_start  axial position, from the corner outward, of the FIRST material
             inside the tail's touch envelope (the SEAL-long spine buffered by
             ROOM_PLUG_HALF_WIDTH_PX, round caps — the region any tail sample
             touches within the half-width); >0 is the clearance gap the tail
             exists to bridge
  mat_end    axial position of the LAST material inside that envelope; when
             it is >= SEAL the material continues past the tail's reach
  class      continues  — material reaches past SEAL (a tail INTO a jamb or
                          along a band that runs on)
             nib        — a clearance gap, then material ending inside reach
             band-end   — material at the corner already, ending inside reach
                          (an island the plug shadows, a band the edge lies on)
             none       — nothing in the envelope
  over       tail_now - mat_end when the material ends inside reach (>0 means
             the tail runs past the material it touches)
  new        the tail the step-5 rule would give: min(SEAL, mat_end), >= 0

--all also prints tails with zero overshoot; --no-clip measures the plugs as
_door_plugs returns them (the pre-step-5 tails) even when _clip_plug_tails
exists. Summary per class at the end.
"""
import math
import sys
from collections import Counter, defaultdict

from shapely.geometry import LineString, box

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402

slug = sys.argv[1]
seals = [float(v) for v in sys.argv[2:] if not v.startswith("--")] or [None]
show_all = "--all" in sys.argv
no_clip = "--no-clip" in sys.argv

pages = H.load(slug)
EDGE = {0: "top", 1: "bot", 2: "left", 3: "right"}


def kept_plugs_for(page, seal):
    calls = []
    o_plugs, o_restrict = rooms._door_plugs, rooms._restrict_swing_plugs

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

    rooms._door_plugs, rooms._restrict_swing_plugs = tap_plugs, tap_restrict
    absolute = {"ROOM_OPENING_SEAL_PX": seal} if seal is not None else {}
    try:
        with H.overrides(absolute=absolute):
            ents, extras = H.run(page, keep_network=True)
            gates = rooms.RoomGates.at(page.scale_factor)
    finally:
        rooms._door_plugs, rooms._restrict_swing_plugs = o_plugs, o_restrict
    out = []
    for call in calls:
        c = call["cand"]
        if c is None:
            continue
        plugs = list(call["restricted"] or [])
        if c.confidence < rooms.ROOM_OPENING_MIN_CONFIDENCE:
            plugs = [(p, k, e) for p, k, e in plugs
                     if k == "interrupted"
                     or p.intersection(call["mat"]).area >= rooms.ROOM_PLUG_IN_WALL_FRAC * p.area]
        if not no_clip and hasattr(rooms, "_clip_plug_tails"):   # step 5 in place
            plugs = rooms._clip_plug_tails(c.bbox, plugs, call["mat"], gates=gates)
        for p, k, e in plugs:
            out.append((c, call["mat"], call["gates"], p, k, e))
    return out, gates, ents


def axial_extent(geom, origin, ux, uy):
    """(min, max) projection of every vertex of geom onto the axis u from origin."""
    lo, hi = math.inf, -math.inf
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty:
            continue
        rings = [g.exterior.coords] if hasattr(g, "exterior") else [g.coords]
        for ring in rings:
            for cx, cy in ring:
                t = (cx - origin[0]) * ux + (cy - origin[1]) * uy
                lo, hi = min(lo, t), max(hi, t)
    return (None, None) if lo is math.inf else (lo, hi)


def measure_tail(corner, ux, uy, plug, mat, seal, half):
    """ux,uy point OUTWARD from the corner along the edge line."""
    # today's tail: the plug's axial extent beyond the corner
    _lo, hi = axial_extent(plug, corner, ux, uy)
    tail_now = max(hi, 0.0)
    far = (corner[0] + ux * seal, corner[1] + uy * seal)
    env = LineString([corner, far]).buffer(half)          # round caps: the touch region
    hit = env.intersection(mat)
    if hit.is_empty:
        return tail_now, None, None, "none", tail_now, 0.0
    m_lo, m_hi = axial_extent(hit, corner, ux, uy)
    if m_hi <= 0.0:
        cls = "none"
        new = 0.0
        over = tail_now
    elif m_hi >= seal - 1e-6:
        cls = "continues"
        new = min(tail_now, seal)
        over = 0.0
    else:
        cls = "nib" if m_lo > 0.5 else "band-end"
        new = min(tail_now, max(m_hi, 0.0))
        over = max(tail_now - m_hi, 0.0)
    return tail_now, m_lo, m_hi, cls, new, over


for seal in seals:
    for page in pages:
        plugs, gates, ents = kept_plugs_for(page, seal)
        S = gates.ROOM_OPENING_SEAL_PX
        half = gates.ROOM_PLUG_HALF_WIDTH_PX
        n_rooms = sum(1 for e in ents if e["entity_type"] == "room")
        print(f"\n=== {slug} p{page.page_number} seal={S} half={half} f={page.scale_factor:.3f} "
              f"rooms={n_rooms} kept_plugs={len(plugs)}")
        by_class = Counter()
        over_by_class = defaultdict(list)
        changed = 0
        for c, mat, g, plug, kind, e in plugs:
            x0, y0, x1, y1 = c.bbox
            edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
                     ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
            p, q = edges[e]
            length = math.hypot(q[0] - p[0], q[1] - p[1])
            ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
            rows = []
            for tag, corner, ox, oy in (("A", p, -ux, -uy), ("B", q, ux, uy)):
                tail_now, m_lo, m_hi, cls, new, over = measure_tail(corner, ox, oy, plug, mat, S, half)
                by_class[cls] += 1
                over_by_class[cls].append(over)
                delta = tail_now - new
                if delta > 0.05:
                    changed += 1
                if show_all or delta > 0.05:
                    ms = "-" if m_lo is None else f"{m_lo:.1f}"
                    me = "-" if m_hi is None else f"{m_hi:.1f}"
                    rows.append(f"      tail{tag} now={tail_now:5.1f} mat=[{ms},{me}] {cls:9s} "
                                f"over={over:4.1f} new={new:5.1f} delta={delta:4.1f}")
            if rows:
                bb = tuple(round(v) for v in c.bbox)
                print(f"   {c.candidate_id} conf={c.confidence:.2f} type={c.evidence.get('assembly_type')} "
                      f"bbox={bb} {kind}@{EDGE[e]} L={length:.0f} plug={tuple(round(v, 1) for v in plug.bounds)}")
                print("\n".join(rows))
        print(f"   summary: tails by class {dict(by_class)}; tails the rule would shorten: {changed}")
        for cls, overs in sorted(over_by_class.items()):
            nz = [o for o in overs if o > 0.05]
            if nz:
                print(f"      {cls:9s} n={len(overs)} overshoot>0: {len(nz)} "
                      f"min={min(nz):.1f} med={sorted(nz)[len(nz)//2]:.1f} max={max(nz):.1f}")
            else:
                print(f"      {cls:9s} n={len(overs)} overshoot>0: 0")
