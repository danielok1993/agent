"""Analyze jamb_seek.jsonl.
A. true class: kept interrupted plugs' anchored ends — along-line run of material
   beyond the jamb (on_run) vs the sheet's wall cap: collinear (long) or crossing (short)
B. extension candidates: edges with an end whose jamb lies BEYOND the seal reach
   (unreached today) within 60px, the other end reached — what are they?"""
import json
import statistics
from collections import Counter

recs = [json.loads(l) for l in open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/jamb_seek.jsonl")]
print("records", len(recs))

kept = [r for r in recs if r["kept"] == "interrupted" and r["conf"] >= 0.55]
print(f"\nA. kept interrupted plugs on >= 0.55 doors: {len(kept)} edges")
runs = []
for r in kept:
    for s in "ab":
        j, on, hug = r[f"jamb_{s}"], r[f"on_{s}"], r[f"hug_{s}"]
        if j is None:
            continue
        runs.append((on, hug, j, r["cap"], r["slug"], r["id"], r["edge"], s, r["mmpx"]))
on_vals = [x[0] for x in runs]
print(f"   anchored ends {len(runs)}: on_run px median {statistics.median(on_vals):.0f}, p25 {sorted(on_vals)[len(on_vals)//4]:.0f}, p10 {sorted(on_vals)[len(on_vals)//10]:.0f}, min {min(on_vals):.0f}")
short = [x for x in runs if x[0] <= x[3]]
print(f"   ends whose on-line run <= the wall cap (crossing wall / nib only): {len(short)} of {len(runs)}")
c = Counter(x[4] for x in short)
print("   by sheet:", dict(c))
print("   examples (on_run, hug, jamb, cap, slug, id, edge, side):")
for x in sorted(short, key=lambda t: t[0])[:12]:
    print("     ", x[:8])
# how many anchored ends have the jamb beyond 0 and a long run
far = [x for x in runs if x[2] > 0]
print(f"   ends with jamb > 0 px: {len(far)}; of them on_run > cap: {sum(1 for x in far if x[0] > x[3])}")
for x in sorted(far, key=lambda t: -t[2])[:15]:
    print("      jamb=%.0fpx=%.0fmm on_run=%.0f hug=%.0f cap=%.1f %s %s edge%d %s" % (x[2], x[2] * x[8], x[0], x[1], x[3], x[4], x[5], x[6], x[7]))

print("\nB. extension candidates: an end whose jamb lies beyond the seal (unreached) within 60 px; other end reached (or also beyond)")
rows = []
for r in recs:
    for s, o in (("a", "b"), ("b", "a")):
        j = r[f"jamb_{s}"]
        if j is None or j <= r["seal"] or j > 60:
            continue
        jo = r[f"jamb_{o}"]
        other = "reached" if (jo is not None and jo <= r["seal"]) else ("beyond" if jo is not None else "none")
        rows.append((r["slug"], r["id"], r["conf"], r["type"], r["layout"], r["edge"], r["hinge"], r["raw"], r["kept"], s, j, j * r["mmpx"], r[f"on_{s}"], r[f"hug_{s}"], r["cap"], other, jo))
rows.sort(key=lambda t: (t[0], t[1], t[5]))
print(f"   {len(rows)} ends")
for t in rows:
    hinge = "" if t[6] is None else ("H" if t[5] in t[6] else "far")
    print("   %s %s c%.2f %s/%s edge%d %-3s raw=%s kept=%s side %s jamb=%.0fpx=%.0fmm on_run=%.0f hug=%.0f cap=%.1f other=%s(%s)" % (
        t[0], t[1], t[2], t[3], t[4], t[5], hinge, t[7], t[8], t[9], t[10], t[11], t[12], t[13], t[14], t[15], t[16]))
