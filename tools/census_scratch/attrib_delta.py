"""attrib_delta.py <slug> FIELD=MULT [...]: run the harness once per config
(each alone on top of the CURRENT tree) and list, per config, the ROOMS that
appear/disappear relative to the unmodified tree (type+IoU>=0.5 matching) —
i.e. which single-field revert removes a new room or restores a vanished one."""
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from regression.matching import iou  # noqa: E402

slug = sys.argv[1]
cfgs = sys.argv[2:]
pages = H.load(slug)
page = pages[0]


def rooms_of(ents):
    return [tuple(e["bbox"]) for e in ents if e["entity_type"] == "room"]


def delta(a, b):
    """rooms in a with no IoU>=0.5 match in b."""
    return [tuple(round(v) for v in x) for x in a if not any(iou(x, y) >= 0.5 for y in b)]


ents0, _ = H.run(page)
base = rooms_of(ents0)
print(f"none: {len(base)} rooms", flush=True)
for cfg in cfgs:
    mult = {}
    for kv in cfg.split(","):
        k, v = kv.split("=")
        mult[k] = float(v)
    with H.overrides(mult=mult):
        ents, _ = H.run(page)
    cur = rooms_of(ents)
    print(f"{cfg:45s} rooms={len(cur)} gone_with_revert={delta(base, cur)} back_with_revert={delta(cur, base)}", flush=True)
