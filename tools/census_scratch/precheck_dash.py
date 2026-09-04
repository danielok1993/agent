"""precheck_dash.py <slug> [...]: harness score vs truth and room moves vs the
baseline snapshot at seals 12 (as shipped) and 14, on the current tree."""
import glob, json, sys
from shapely.geometry import Polygon

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402


def poly_iou(a, b):
    if not a.is_valid: a = a.buffer(0)
    if not b.is_valid: b = b.buffer(0)
    u = a.union(b).area
    return a.intersection(b).area / u if u > 0 else 0.0


for slug in sys.argv[1:]:
    pages = H.load(slug)
    bdir = sorted(glob.glob(f"/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress_baseline/{slug}/*"))[-1]
    be = json.load(open(f"{bdir}/pages/page_01/final_entities.json"))["entities"]
    base_rooms = [(e["entity_id"], Polygon(e["attributes"]["polygon"])) for e in be if e["entity_type"] == "room"]
    for seal in (12.0, 14.0):
        with H.overrides(absolute={"ROOM_OPENING_SEAL_PX": seal}):
            ents, _ = H.run(pages[0])
        sc = H.score(slug, pages[0].page_number, ents)
        rooms = [Polygon(e["evidence"]["polygon"]) for e in ents if e["entity_type"] == "room"]
        moved = []
        for rid, bp in base_rooms:
            best = max((poly_iou(bp, r) for r in rooms), default=0.0)
            if best < 0.995:
                moved.append(f"{rid}:{best:.3f}")
        new = []
        for r in rooms:
            best = max((poly_iou(bp, r) for _, bp in base_rooms), default=0.0)
            if best < 0.5:
                b = r.bounds
                new.append(f"({b[0]:.0f},{b[1]:.0f})-({b[2]:.0f},{b[3]:.0f})")
        print(f"{slug} seal={seal:.0f} rooms={len(rooms)} counts={sc['counts']} lost={sc['lost']} retFP={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])} closed={sc['closed']}", flush=True)
        print(f"   moved_vs_baseline={moved}", flush=True)
        print(f"   new_vs_baseline={new}", flush=True)
