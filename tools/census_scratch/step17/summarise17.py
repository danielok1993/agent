"""Markdown tables over recess_census_{s11,a,b,c}.json for the step-17 report:
every `_is_wall_recess` call that reaches the back-edge test (a collinear-gap
candidate past the intersect / opening / gap-cover / depth gates) with the
extent reading and the four runs readings, the candidate-less calls per
sheet, the emitted rooms that reach a candidate (the true class), and the
rule as implemented under each reading.

Usage: .venv/bin/python tools/census_scratch/step17/summarise17.py > step17/summary17.md
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
recs = []
for name in ("recess_census_s11.json", "recess_census_a.json", "recess_census_b.json", "recess_census_c.json"):
    p = HERE / name
    if p.exists():
        recs.extend(json.loads(p.read_text()))
recs.sort(key=lambda r: r["slug"])
V = ("face_gap", "caps_gap", "face_own", "caps_own")

print("### Every `_is_wall_recess` call that reaches the back-edge test (a collinear-gap candidate past the other gates)\n")
print("| sheet (f) | component | area px² | ground truth | th | gap cover | depth (bands) | back (extent) | extent verdict | face / gap | caps / gap | face / own | caps / own | dropped today |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
n_calls = n_cand = 0
for r in recs:
    for c in r["calls"]:
        n_calls += 1
        if not c["candidates"]:
            continue
        n_cand += 1
        for cd in c["candidates"]:
            mm = c["mm_per_px"]
            b = c["bbox"]
            print(f"| {r['slug']} ({r['factor']:.3g}) | ({b[0]:.0f},{b[1]:.0f})–({b[2]:.0f},{b[3]:.0f}) | {c['area']} | {c['gt']} "
                  f"| {cd['th']:.2f}px" + (f" = {cd['th'] * mm:.0f}mm" if mm else "") +
                  f" | {cd['gap_cover']:.3f} | {cd['depth_bands']:.2f} | {cd['back']:+.2f} | {'recess' if cd['extent_ok'] else 'not'} "
                  f"| {cd['face_gap']:.3f} | {cd['caps_gap']:.3f} | {cd['face_own']:.3f} | {cd['caps_own']:.3f} "
                  f"| {'yes' if c['res_now'] else 'no'} |")
print()
print(f"Calls corpus-wide: {n_calls}; with a candidate: {n_cand}; without (held out by the intersect / opening / gap-cover / depth gates, both readings False): {n_calls - n_cand}.\n")

print("### Calls per sheet\n")
print("| sheet (f) | recess calls | with a candidate | dropped today | emitted rooms | rooms with a candidate |")
print("|---|---|---|---|---|---|")
for r in recs:
    calls = r["calls"]
    rooms = r["rooms"]
    print(f"| {r['slug']} ({r['factor']:.3g}) | {len(calls)} | {sum(1 for c in calls if c['candidates'])} "
          f"| {sum(1 for c in calls if c['res_now'])} | {len(rooms)} | {sum(1 for c in rooms if c['candidates'])} |")
print()

print("### Emitted rooms that reach a candidate (the true class the back edge would decide)\n")
any_room = False
for r in recs:
    for c in r["rooms"]:
        if c["candidates"]:
            any_room = True
            b = c["bbox"]
            print(f"- {r['slug']} ({b[0]:.0f},{b[1]:.0f})–({b[2]:.0f},{b[3]:.0f}) gt={c['gt']} verdicts {c['verdict']}")
if not any_room:
    print("None on any sheet: every emitted room is held out by the intersect / opening / gap-cover / depth gates before the back edge is read.")
print()

print("### The rule AS IMPLEMENTED under each runs reading (rooms diffed against the unmodified chain, scored)\n")
print("| sheet (f) | base score (lost / returned FPs / unreviewed) | " + " | ".join(V) + " |")
print("|---|---|" + "---|" * len(V))
for r in recs:
    bs = r["base_score"]
    cells = []
    for v in V:
        vr = r["variants"][v]
        sc = vr["score"]
        if vr["gone"] or vr["new"] or vr["moved"]:
            cells.append(f"gone {len(vr['gone'])} new {len(vr['new'])} moved {len(vr['moved'])} → {sc['lost']} / {sc['returned_fps']} / {sc['unreviewed']}")
        else:
            cells.append("identical")
    print(f"| {r['slug']} ({r['factor']:.3g}) | {bs['lost']} / {bs['returned_fps']} / {bs['unreviewed']} | " + " | ".join(cells) + " |")
print()
print("(s02's 12 'lost' are the harness's omitted labels and schedule, as in every step's census; the sweep reads s02 15/15 doors, 11/11 rooms, 11/11 windows, 11/11 labels, 1/1 schedule.)")
