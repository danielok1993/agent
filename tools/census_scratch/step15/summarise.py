"""Tables over cover_census_{a,b,s17}.json (or any COVER_CENSUS files
named on the command line): the rule's population and the true class
under each cover reading, and the per-ceiling verdicts.

Usage: .venv/bin/python tools/census_scratch/step15/summarise.py [json...]
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
files = [Path(a) for a in sys.argv[1:]] or sorted(HERE.glob("cover_census_*.json"))
recs = []
for f in files:
    recs.extend(json.loads(f.read_text()))
recs.sort(key=lambda r: r["slug"])

READINGS = ("mrr", "mrr_tol0", "runs", "runs_caps", "runs_max")
COVER_MIN = 0.65
CEILINGS = ("36", "40", "41", "44", "48", "56")


def mn(rec, r):
    return min(rec["covers"][r])


print("=== 1. the rule's population: every _is_band_pocket call, by band and reading (min cover >= 0.65) ===")
calls = [(r["slug"], r["factor"], c) for r in recs for c in r["calls"] if not c.get("degenerate")]
degen = sum(1 for r in recs for c in r["calls"] if c.get("degenerate"))
print(f"calls {len(calls)} (+{degen} degenerate)")
bands = Counter()
for slug, f, c in calls:
    sp = c["spacing"]
    band = "<=36f" if sp <= 36 * f else ("(36f,56f]" if sp <= 56 * f else ">56f")
    bands[band] += 1
print("by band:", dict(bands))
for band_name, lo, hi in (("<=36f", 0, 36), ("(36f,56f]", 36, 56), (">56f", 56, 1e9)):
    sub = [(s, f, c) for s, f, c in calls if lo * f < c["spacing"] <= hi * f]
    line = f"  {band_name:10s} n={len(sub):3d}"
    for r in READINGS:
        n = sum(1 for s, f, c in sub if mn(c, r) >= COVER_MIN and not c["text"])
        line += f"  {r}:{n:3d}"
    print(line)

print("\n=== 2. every call with spacing <= 56f (the ceiling step's population) ===")
print(f"{'sheet':5s} {'bbox':34s} {'sp':>6s} {'mm':>5s} {'gt':14s} {'mrr':>12s} {'tol0':>12s} {'runs':>12s} {'caps':>12s} {'max':>12s} now")
for slug, f, c in sorted(calls, key=lambda t: t[2]["spacing"] / t[1]):
    if c["spacing"] > 56 * f:
        continue
    cv = c["covers"]
    fmt = lambda v: f"[{v[0]:.2f},{v[1]:.2f}]"
    print(f"{slug:5s} {str([round(v) for v in c['bbox']]):34s} {c['spacing']:6.2f} {str(c['spacing_mm']):>5s} {c['gt']:14s} "
          f"{fmt(cv['mrr']):>12s} {fmt(cv['mrr_tol0']):>12s} {fmt(cv['runs']):>12s} {fmt(cv['runs_caps']):>12s} {fmt(cv['runs_max']):>12s} "
          f"{'DROPPED' if c['res_now'] else 'kept'}{' TEXT' if c['text'] else ''}")

print("\n=== 3. per-ceiling verdicts (drop = spacing <= ceiling*f, no text, both covers >= 0.65), calls with spacing <= 56f ===")
for slug, f, c in sorted(calls, key=lambda t: t[2]["spacing"] / t[1]):
    if c["spacing"] > 56 * f:
        continue
    line = f"{slug:5s} {str([round(v) for v in c['bbox']]):34s} {c['spacing']:6.2f} ({c['spacing_mm']}mm) {c['gt']:14s}"
    for r in ("mrr", "runs", "runs_caps"):
        v = c["verdicts"][r]
        line += f" | {r}: " + " ".join(f"{k}:{'D' if v[k] else '.'}" for k in CEILINGS)
    print(line)

print("\n=== 4. the true class: every CONFIRMED emitted room, min cover under each reading ===")
rooms = [(r["slug"], r["factor"], m) for r in recs for m in r["rooms"]]
conf = [(s, f, m) for s, f, m in rooms if m["gt"] == "confirmed"]
print(f"emitted rooms {len(rooms)}, confirmed {len(conf)}")
for r in READINGS:
    n = sum(1 for s, f, m in conf if mn(m, r) >= COVER_MIN)
    print(f"  confirmed rooms with both sides >= 0.65 under {r:9s}: {n:3d} / {len(conf)}")
print("  confirmed rooms that read >= 0.65 under runs_caps but NOT under mrr (spacing, entrance count):")
for s, f, m in sorted(conf, key=lambda t: t[2]["spacing"] / t[1]):
    if mn(m, "runs_caps") >= COVER_MIN and mn(m, "mrr") < COVER_MIN:
        print(f"    {s} {[round(v) for v in m['bbox']]} sp {m['spacing']} ({m['spacing_mm']}mm, {m['spacing']/f:.1f}px@1:50) "
              f"entr {m['entrance_count']} doors {m['door_count']} win {m['window_count']} text={m['text']} "
              f"mrr {m['covers']['mrr']} runs_caps {m['covers']['runs_caps']}")
print("  narrowest confirmed rooms with both sides >= 0.65 under runs_caps (the ceiling step's true floor):")
narrow = sorted(((m["spacing"] / f, s, f, m) for s, f, m in conf if mn(m, "runs_caps") >= COVER_MIN),
                key=lambda t: (t[0], t[1]))
for sp50, s, f, m in narrow[:12]:
    print(f"    {s} {[round(v) for v in m['bbox']]} sp {m['spacing']} = {sp50:.1f}px@1:50 ({m['spacing_mm']}mm) "
          f"entr {m['entrance_count']} doors {m['door_count']} win {m['window_count']} text={m['text']} "
          f"mrr {m['covers']['mrr']} runs_caps {m['covers']['runs_caps']}")

print("\n=== 5. every emitted room whose min cover changes class between mrr and runs_caps (any gt) ===")
for s, f, m in sorted(rooms, key=lambda t: t[2]["spacing"] / t[1]):
    a, b = mn(m, "mrr") >= COVER_MIN, mn(m, "runs_caps") >= COVER_MIN
    if a != b:
        print(f"    {s} {[round(v) for v in m['bbox']]} sp {m['spacing']} ({m['spacing_mm']}mm) gt={m['gt']} "
              f"entr {m['entrance_count']} win {m['window_count']} text={m['text']} "
              f"mrr {m['covers']['mrr']} -> runs_caps {m['covers']['runs_caps']}  {'UP' if b else 'DOWN'}")

print("\n=== 6. the s17 strips, per side (runs reading) ===")
for r in recs:
    if r["slug"] != "s17":
        continue
    for c in r["calls"]:
        if c.get("degenerate") or c["spacing"] > 56:
            continue
        print(f"  {[round(v) for v in c['bbox']]} sp {c['spacing']} long {c['long']} covers mrr {c['covers']['mrr']} runs {c['covers']['runs']} caps {c['covers']['runs_caps']}")
        for i, sd in enumerate(c["side_detail"]):
            print(f"    side {i}: parallel {sd['parallel_len']}px in {sd['n_runs']} runs")
            for run in sd["runs"]:
                print(f"       run {run['a']}-{run['b']} len {run['len']} offset {run['offset']} covered by faces {run['cov_faces']} with caps {run['cov_with_caps']}")
