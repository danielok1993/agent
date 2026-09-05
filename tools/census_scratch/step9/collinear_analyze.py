"""Analyze collinear.jsonl.
A. true class: kept interrupted plugs (>= 0.55 doors) — per anchored end, does a
   collinear barrier face begin within 60 px (g) and how far?  (the doorway convention)
B. seek candidates: ends where g > seal - 2 (beyond today's reach) and g <= SEEK cap,
   grouped by whether the edge is a hinge edge / far edge / fallback box, with the
   other end's status."""
import json
import statistics
from collections import Counter, defaultdict

recs = [json.loads(l) for l in open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/collinear.jsonl")]
print("records", len(recs))
ident = [r for r in recs if not (r["slug"] == "s01" and r["factor"] < 0.9)]
s01t = [r for r in recs if r["slug"] == "s01" and r["factor"] < 0.9]

kept = [r for r in ident if r["kept"] == "interrupted" and r["conf"] >= 0.55]
print(f"\nA. kept interrupted plugs (>= 0.55) at the sheets' factors: {len(kept)} edges")
gs = []
none = 0
for r in kept:
    for s in "ab":
        c = r[f"col_{s}"]
        if c is None:
            none += 1
        else:
            gs.append((c["g"], c["g"] * r["mmpx"], c["run"], c["off"], r["slug"], r["id"], r["edge"], s))
print(f"   ends with a collinear barrier face within 60px: {len(gs)}; without: {none}")
print(f"   g px: median {statistics.median([x[0] for x in gs]):.1f}, p90 {sorted(x[0] for x in gs)[int(0.9*len(gs))]:.1f}, max {max(x[0] for x in gs):.1f}")
print(f"   g mm: median {statistics.median([x[1] for x in gs]):.0f}, p90 {sorted(x[1] for x in gs)[int(0.9*len(gs))]:.0f}, max {max(x[1] for x in gs):.0f}")
print("   run px of the collinear face: median %.0f p10 %.0f min %.0f" % (statistics.median([x[2] for x in gs]), sorted(x[2] for x in gs)[len(gs)//10], min(x[2] for x in gs)))
print("   largest g (px, mm, run, off, slug, id, edge, side):")
for x in sorted(gs, key=lambda t: -t[0])[:12]:
    print("     ", tuple(round(v, 1) if isinstance(v, float) else v for v in x))

print("\nB. seek candidates at the sheets' factors: an end with a collinear face beginning beyond the seal (g > seal) within 60px")
rows = []
for r in ident:
    for s, o in (("a", "b"), ("b", "a")):
        c = r[f"col_{s}"]
        if c is None or c["g"] <= r["seal"]:
            continue
        co = r[f"col_{o}"]
        hinge = "" if r["hinge"] is None else ("H" if r["edge"] in r["hinge"] else "far")
        rows.append((r["slug"], r["id"], r["conf"], r["type"], r["layout"], r["edge"], hinge, r["raw"], r["kept"], s, c["g"], c["g"] * r["mmpx"], c["run"], c["off"], None if co is None else co["g"], r["seal"]))
rows.sort(key=lambda t: (t[0], t[1], t[5]))
print(f"   {len(rows)} ends")
for t in rows:
    print("   %s %s c%.2f %s/%s edge%d %-3s raw=%s kept=%s side %s g=%.1fpx=%.0fmm run=%.0f off=%.1f other_g=%s seal=%.2f" % (
        t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], t[10], t[11], t[12], t[13],
        "-" if t[14] is None else f"{t[14]:.1f}", t[15]))

print("\nC. s01 at 0.542: every edge end with a collinear face beyond the seal")
for r in s01t:
    for s, o in (("a", "b"), ("b", "a")):
        c = r[f"col_{s}"]
        if c is None or c["g"] <= r["seal"]:
            continue
        co = r[f"col_{o}"]
        hinge = "" if r["hinge"] is None else ("H" if r["edge"] in r["hinge"] else "far")
        print("   %s c%.2f %s edge%d %-3s raw=%s kept=%s side %s g=%.1fpx=%.0fmm run=%.0f off=%.1f other_g=%s seal=%.2f" % (
            r["id"], r["conf"], r["type"], r["edge"], hinge, r["raw"], r["kept"], s, c["g"], c["g"] * r["mmpx"], c["run"], c["off"],
            "-" if co is None else f"{co['g']:.1f}", r["seal"]))
