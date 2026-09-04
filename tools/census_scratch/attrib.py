"""attrib.py <slug> <x0> <y0> <x1> <y1> FIELD=MULT [FIELD=MULT ...]

Runs the harness chain on <slug> once per FIELD=MULT config (each alone, on
top of the CURRENT tree's constants) and reports whether an entity with a
bbox within 4px of the given one is emitted, plus the sheet's score.
Config 'none' = the current tree unchanged."""
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402

slug = sys.argv[1]
tb = tuple(float(v) for v in sys.argv[2:6])
cfgs = sys.argv[6:]
pages = H.load(slug)


def has(ents):
    out = []
    for e in ents:
        b = e["bbox"]
        if all(abs(b[i] - tb[i]) <= 4.0 for i in range(4)):
            out.append((e["entity_type"], [round(v, 1) for v in b], e["confidence"]))
    return out


for cfg in ["none"] + cfgs:
    mult = {}
    if cfg != "none":
        for kv in cfg.split(","):
            k, v = kv.split("=")
            mult[k] = float(v)
    with H.overrides(mult=mult):
        for p in pages:
            ents, _ = H.run(p)
            sc = H.score(slug, p.page_number, ents)
            print(f"{cfg:40s} p{p.page_number} target={has(ents)} counts={sc['counts']} "
                  f"lost={len(sc['lost'])} retFP={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])}",
                  flush=True)
