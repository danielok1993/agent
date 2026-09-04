"""attrib_rooms.py <slug> FIELD=MULT [...]: for each config (each alone on top
of the current tree), compare the harness's room polygons with the BASELINE
snapshot's rooms (outputs/regress_baseline/<slug>) and print every baseline
room whose best IoU is < 0.995 — i.e. which single-field revert restores a
room's baseline shape."""
import glob, json, sys
from shapely.geometry import Polygon

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402

slug = sys.argv[1]
cfgs = sys.argv[2:]
pages = H.load(slug)
bdir = sorted(glob.glob(f"/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress_baseline/{slug}/*"))[-1]
be = json.load(open(f"{bdir}/pages/page_01/final_entities.json"))
be = be["entities"] if isinstance(be, dict) else be
base_rooms = [(e["entity_id"], Polygon(e["attributes"]["polygon"])) for e in be if e["entity_type"] == "room"]


def poly_iou(a, b):
    if not a.is_valid: a = a.buffer(0)
    if not b.is_valid: b = b.buffer(0)
    u = a.union(b).area
    return a.intersection(b).area / u if u > 0 else 0.0


for cfg in ["none"] + cfgs:
    mult = {}
    if cfg != "none":
        for kv in cfg.split(","):
            k, v = kv.split("=")
            mult[k] = float(v)
    with H.overrides(mult=mult):
        ents, _ = H.run(pages[0])
    rooms = [Polygon(e["evidence"]["polygon"]) for e in ents if e["entity_type"] == "room"]
    moved = []
    for rid, bp in base_rooms:
        best = max((poly_iou(bp, r) for r in rooms), default=0.0)
        if best < 0.995:
            moved.append(f"{rid}:{best:.3f}")
    print(f"{cfg:45s} rooms={len(rooms)} moved_vs_baseline={moved}", flush=True)
