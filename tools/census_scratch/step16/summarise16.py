"""Markdown tables over backing_census_{a,b}.json for the step-16 report:
every `_is_band_pocket` call at or under 56 × f and every confirmed
door-less room at or under 72 × f, with the four readings of the brief —
(a) text / glyph strokes inside, (b) wall solid behind each long side,
(c) one pen on both sides, (d) end closures — plus the shipped covers.

Usage: .venv/bin/python tools/census_scratch/step16/summarise16.py > step16/summary16.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
recs = []
for name in ("backing_census_a.json", "backing_census_b.json"):
    p = HERE / name
    if p.exists():
        recs.extend(json.loads(p.read_text()))


def fmt(v):
    return "–" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))


def row(slug, f, c, extra):
    sides = c["sides"]
    ends = c["ends"]
    return (f"| {slug} ({f:.3g}) | ({c['bbox'][0]:.0f},{c['bbox'][1]:.0f})–({c['bbox'][2]:.0f},{c['bbox'][3]:.0f}) "
            f"| {c['spacing']:.2f} = {c['spacing_mm']}mm | {c['gt']} "
            f"| {'text' if c['text'] else 'no text'}, {c['glyph_strokes_inside']} glyph strokes "
            f"| {c['backed_any'][0]:.2f} / {c['backed_any'][1]:.2f} (spans {sides[0]['span_any_med']:.1f} / {sides[1]['span_any_med']:.1f}px) "
            f"| {'same' if c['same_pen_both_sides'] else 'different'} "
            f"| {c['covers'][0]:.2f} / {c['covers'][1]:.2f} "
            f"| **{min(e['backed_any'] for e in ends):.2f} / {max(e['backed_any'] for e in ends):.2f}** "
            f"| {extra} |")


head = ("| sheet (f) | component | spacing | ground truth | (a) inside | (b) solid behind each side | (c) pens | covers (shipped) | (d) end closures | note |\n"
        "|---|---|---|---|---|---|---|---|---|---|")
print("### Every `_is_band_pocket` call at or under 56 × f\n")
print(head)
calls = []
for r in recs:
    for c in r["calls"]:
        if c.get("degenerate"):
            continue
        if c["spacing"] <= 56.0 * r["factor"]:
            calls.append((r["slug"], r["factor"], c))
for slug, f, c in sorted(calls, key=lambda t: t[2]["spacing_mm"] or 0):
    print(row(slug, f, c, "dropped today" if c["res_now"] else "kept today"))
print()
print("### Every confirmed room at or under 72 × f (the true class, entered or not)\n")
print(head)
rooms = []
for r in recs:
    for c in r["rooms"]:
        if c["gt"] == "confirmed" and c["spacing"] <= 72.0 * r["factor"]:
            rooms.append((r["slug"], r["factor"], c))
for slug, f, c in sorted(rooms, key=lambda t: t[2]["spacing_mm"] or 0):
    print(row(slug, f, c, f"entrances {c['entrance_count']}, doors {c['door_count']}, windows {c['window_count']}"))
print()
n_calls = sum(len([c for c in r["calls"] if not c.get("degenerate")]) for r in recs)
n_rooms = sum(len(r["rooms"]) for r in recs)
n_conf = sum(1 for r in recs for c in r["rooms"] if c["gt"] == "confirmed")
encl = [(r["slug"], c["bbox"], c["gt"]) for r in recs for c in r["calls"]
        if not c.get("degenerate") and min(e["backed_any"] for e in c["ends"]) >= 0.65]
print(f"calls {n_calls}, emitted rooms {n_rooms} ({n_conf} confirmed); calls enclosed at both ends (>= 0.65): {len(encl)}")
for e in encl:
    print("   ", e)
# the true class over the whole corpus: confirmed rooms by end closure
import collections
hist = collections.Counter()
for r in recs:
    for c in r["rooms"]:
        if c["gt"] != "confirmed":
            continue
        m = min(e["backed_any"] for e in c["ends"])
        hist["enclosed" if m >= 0.65 else "open-ended"] += 1
print("confirmed rooms by end closure (both ends >= 0.65):", dict(hist))
