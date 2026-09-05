"""Analyze jamb_census.jsonl: for every KEPT interrupted plug (the true class —
a doorway the plug sealed), the jamb gap at each end in world mm; and for
every hinge/doorway edge that did NOT qualify but has material within reach
at one end, the same. Distribution + the s01 hall door."""
import json
from collections import defaultdict

recs = [json.loads(l) for l in open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/jamb_census.jsonl")]
print("records", len(recs))

MMPX = 0.16933


def gaps_mm(r):
    out = []
    for side in ("a", "b"):
        g = r[f"gap_{side}_px"]
        inside = r[f"in_{side}_px"]
        if g is None:
            out.append(None)
        else:
            out.append(g * MMPX * (r["denom"] or 50.0))
    return out


# True class: kept interrupted plugs on doors >= 0.55 (real doorways)
kept = [r for r in recs if r["kept"] == "interrupted" and r["conf"] >= 0.55]
print(f"\nKEPT interrupted plugs on doors >= 0.55: {len(kept)}")
per_sheet = defaultdict(list)
allg = []
for r in kept:
    for side, g in zip("ab", gaps_mm(r)):
        if g is None:
            continue
        per_sheet[r["slug"]].append(g)
        allg.append((g, r["slug"], r["id"], r["edge"], side, r[f"gap_{side}_px"], r["seal_px"], r["half_px"], r["factor"]))
allg.sort(reverse=True)
import statistics
print("  jamb gap (corner -> dilated material) mm at TRUE scale: n=%d median=%.0f p75=%.0f p90=%.0f max=%.0f" % (
    len(allg), statistics.median([g[0] for g in allg]),
    sorted(g[0] for g in allg)[int(0.75 * len(allg))], sorted(g[0] for g in allg)[int(0.9 * len(allg))], allg[0][0]))
print("  top 25:")
for g in allg[:25]:
    print("   %6.0f mm  %s %s edge%d side %s  gap_px=%.0f seal=%.2f half=%.2f f=%.3f" % g)
print("  per sheet max mm:", {k: round(max(v)) for k, v in sorted(per_sheet.items())})
# zero-gap fraction
z = sum(1 for g in allg if g[0] == 0)
print(f"  ends with gap 0 (material already at the corner): {z}/{len(allg)}")

# Failing edges: hinge edges (or any edge when hinge is None) of doors >= 0.55 that took NO plug (raw None),
# where one end has material within 100px and the other end's gap is the question.
print("\nNon-qualifying hinge edges of doors >= 0.55 (no raw plug): gap at each end, mm")
fails = [r for r in recs if r["raw"] is None and r["conf"] >= 0.55 and (r["hinge"] is None or r["edge"] in r["hinge"])]
rows = []
for r in fails:
    ga, gb = gaps_mm(r)
    rows.append((r["slug"], r["id"], r["type"], r["edge"], ga, gb, r["gap_a_px"], r["gap_b_px"], r["seal_px"], r["half_px"]))
rows.sort(key=lambda t: (t[0], t[1]))
for t in rows:
    print("   %s %s %s edge%d  gap_a=%s mm (%s px)  gap_b=%s mm (%s px)  seal=%.2f half=%.2f" % (
        t[0], t[1], t[2], t[3],
        "-" if t[4] is None else f"{t[4]:.0f}", t[6], "-" if t[5] is None else f"{t[5]:.0f}", t[7], t[8], t[9]))
