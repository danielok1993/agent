"""Per-room entrance-contact statistics from entered_all_*.json: for every
confirmed room the LARGEST contact any entrance seal makes with its boundary
(a real room has at least one proper doorway along its edge), and the s17
strips' contacts, in px and world mm."""
import glob, json, statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent
MM = 0.16933
rows = []
for f in sorted(HERE.glob("entered_all_*.json")):
    for r in json.load(open(f)):
        for rm in r["rooms"]:
            if not rm["entrances"]:
                continue
            mx = max(e["contact_px"] for e in rm["entrances"])
            rows.append((r["slug"], r["factor"], rm["gt"], rm["spacing"], mx, rm["bbox"], len(rm["entrances"])))
def mm(px, f): return px * MM * 50 / f
print("confirmed rooms: smallest MAX-entrance-contact per sheet")
for slug in sorted({r[0] for r in rows}):
    v = sorted((r[4], r[5], r[6]) for r in rows if r[0] == slug and r[2] == "confirmed")
    if not v: continue
    f = [r[1] for r in rows if r[0] == slug][0]
    print(f"  {slug} f={f}: n={len(v)} min max-contact {v[0][0]:.1f}px ({mm(v[0][0], f):.0f}mm) at {v[0][1]} ({v[0][2]} entrances); "
          f"median {statistics.median([x[0] for x in v]):.1f}px ({mm(statistics.median([x[0] for x in v]), f):.0f}mm)")
print("corpus-wide 10 smallest confirmed max-contacts:")
for r in sorted([r for r in rows if r[2] == "confirmed"], key=lambda r: mm(r[4], r[1]))[:10]:
    print(f"  {r[0]} {r[5]} spacing {r[3]} max contact {r[4]}px = {mm(r[4], r[1]):.0f}mm ({r[6]} entrances)")
print("false-positive rooms with entrances:")
for r in sorted([r for r in rows if r[2] == "false_positive"], key=lambda r: mm(r[4], r[1])):
    print(f"  {r[0]} {r[5]} spacing {r[3]} max contact {r[4]}px = {mm(r[4], r[1]):.0f}mm ({r[6]} entrances)")
