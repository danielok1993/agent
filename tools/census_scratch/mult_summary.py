"""Summarise abl/<slug>_mult.jsonl: per field x sheet, the damage at each multiplier.

Damage = (lost confirmed beyond baseline, returned FPs beyond baseline, gone-vs-base, new-vs-base).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ABL = Path(__file__).resolve().parent / "abl"
MULTS = [0.5, 0.67, 0.8, 1.25, 1.5, 2.0]


def load(slug):
    fn = ABL / f"{slug}_mult.jsonl"
    if not fn.exists():
        return None
    recs = {}
    for line in fn.read_text().splitlines():
        r = json.loads(line)
        recs[r["label"]] = r
    return recs


def damage(rec, base):
    if rec is None:
        return None
    if "error" in rec:
        return "ord"
    pg = rec["pages"][0]
    bp = base["pages"][0]
    lost = len(pg["score"]["lost"]) - len(bp["score"]["lost"])
    fp = len(pg["score"]["returned_fps"]) - len(bp["score"]["returned_fps"])
    gone = len(pg["vs_base"]["gone"])
    new = len(pg["vs_base"]["new"])
    return (lost, fp, gone, new)


def cell(d):
    if d is None:
        return "   ...   "
    if d == "ord":
        return "   ord   "
    lost, fp, gone, new = d
    if lost == 0 and fp == 0 and gone == 0 and new == 0:
        return "    .    "
    s = ""
    if lost:
        s += f"L{lost}"
    if fp:
        s += f"F{fp}"
    if gone or new:
        s += f"({gone}-{new})" if not s else f"({gone}-{new})"
    return f"{s:^9s}"


def main(slugs):
    data = {s: load(s) for s in slugs}
    data = {s: d for s, d in data.items() if d}
    fields = []
    for d in data.values():
        for k in d:
            if "@" in k:
                f = k.split("@")[0]
                if f not in fields:
                    fields.append(f)
    print("cell = L<lost confirmed> F<returned FP> (<gone>-<new> vs baseline); '.' = identical; 'ord' = ordering assert")
    for f in fields:
        print(f"\n{f}")
        print("      " + "".join(f"{m:^9}" for m in MULTS))
        for s, d in data.items():
            base = d.get("baseline")
            row = [damage(d.get(f"{f}@{m}"), base) for m in MULTS]
            print(f"  {s:4s}" + "".join(cell(x) for x in row))


if __name__ == "__main__":
    main(sys.argv[1:] or ["s01", "s02", "s03", "s05", "s07", "s12", "s13", "s17"])
