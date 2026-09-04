"""Per-constant population statistics across sheets, from pop/*.json.

Prints, per constant, per sheet: the TRUE-class extreme the gate must admit
and the FALSE-class extreme it must exclude, in px (at the sheet's drawn
size) and in world mm at the sheet's TRUE scale, next to the gate's value
at the factor the sheet actually runs at.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

POP = Path(__file__).resolve().parent / "pop"
MMPX = 0.16933

SHEETS = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s10", "s11",
          "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s20"]
TRUE_D = {"s01": 92.2, "s02": 50, "s03": "50/100", "s04": 50, "s05": 100, "s06": 100,
          "s07": 100, "s08": 50, "s10": 50, "s11": 100, "s12": 100, "s13": 136.4,
          "s14": 50, "s15": 50, "s16": 100, "s17": "50/100", "s18": 100, "s20": 50}


def load_all(only=None):
    out = {}
    for s in SHEETS:
        if only and s not in only:
            continue
        p = POP / f"{s}.json"
        if p.exists():
            out[s] = json.loads(p.read_text())["pages"][0]
    return out


def q(xs, ps=(0.0, 0.5, 0.9, 1.0)):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if not n:
        return "-"
    vals = [xs[min(int(round(p * (n - 1))), n - 1)] for p in ps]
    return "n=%d " % n + "/".join("%.1f" % v for v in vals)


def fmt(v, nd=1):
    return "-" if v is None else ("%%.%df" % nd) % v


def mm_of(pg, px, d=None):
    return None if d is None else px * MMPX * d


def row(sheet, pg, label, true_px, true_mm, false_px, false_mm, gate_px, note=""):
    f = pg["factor"]
    print(f"  {sheet:4s} f={f:.3f} D={str(TRUE_D[sheet]):6s} gate={gate_px:7.2f}px | {label:26s} "
          f"TRUE {fmt(true_px)}px {fmt(true_mm,0)}mm | FALSE {fmt(false_px)}px {fmt(false_mm,0)}mm {note}")


def denom_mm(rec, px_key, mm_key):
    return rec.get(mm_key)


# ---------------------------------------------------------------------------
def c_face_min_len(P):
    print("\n## WALL_FACE_MIN_LEN_PX (11): true = shortest PAIRED faces (nibs); false = solid wall-pen strokes 6-11px (admitted if floor drops)")
    for s, pg in P.items():
        faces = [f for f in pg["faces"] if f["paired"]]
        lens = sorted((f["len"], f["len_mm"]) for f in faces)
        short = pg["short_strokes"]
        gate = pg["face_min_len_gate"]
        n_axis = sum(1 for x in short if not x["diag"] and 0.55 * gate <= x["len"] < gate)
        n_diag = sum(1 for x in short if x["diag"] and 0.55 * gate <= x["len"] < gate)
        n_axis_above = sum(1 for x in short if not x["diag"] and gate <= x["len"] < 2 * gate)
        nibs = [l for l in lens if l[0] < 2.0 * gate]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.2f}px: paired faces n={len(lens)} min={fmt(lens[0][0]) if lens else '-'}px "
              f"({fmt(lens[0][1],0) if lens else '-'}mm); faces under 2x gate: n={len(nibs)} "
              f"[{', '.join('%.1f' % l[0] for l in nibs[:8])}] ; axis-aligned wall-pen strokes in [0.55g, g): {n_axis} (diag {n_diag}); axis in [g,2g): {n_axis_above}")


def c_thickness(P):
    print("\n## WALL_MIN/MAX_THICKNESS, THICK, THROUGH: kept pair spacing by tier; false = above-cap strong pairs (wide probe)")
    for s, pg in P.items():
        pairs = pg["pairs"]
        strong = [p for p in pairs if not p["weak"] and not p["thick"]]
        weak = [p for p in pairs if p["weak"]]
        thick = [p for p in pairs if p["thick"] and not p["through"]]
        through = [p for p in pairs if p["through"]]
        wide = pg["wide_pairs"]
        f = pg["factor"]
        cap = 36 * f
        print(f"  {s} f={f:.3f} D={TRUE_D[s]}: strong th px {q([p['th'] for p in strong])} mm {q([p['th_mm'] for p in strong])}")
        print(f"        weak th px {q([p['th'] for p in weak])} ; thick(kept pre-material) px {q([p['th'] for p in thick])} mm {q([p['th_mm'] for p in thick])} ; through px {q([p['th'] for p in through])}")
        # material-passing thick/through (from material calls)
        mat = pg["material"]
        ok_thick = [m for m in mat if m["ok"] and m["thick"]]
        print(f"        thick+material OK: n={len(ok_thick)} th px {q([m['th'] for m in ok_thick])} mm {q([m['th_mm'] for m in ok_thick])}")
        wm = [w for w in wide if w["material"]]
        wt = [w for w in wide if w["through"]]
        print(f"        ABOVE-CAP strong pairs (probe 4x): n={len(wide)} th px {q([w['th'] for w in wide])} ; with material n={len(wm)} th px {q([w['th'] for w in wm])} mm {q([w['th_mm'] for w in wm])} ; through-hatch n={len(wt)} th px {q([w['th'] for w in wt])}")
        # nearest above-cap pairs (what a raised cap admits first)
        near = sorted(wide, key=lambda w: w["th"])[:6]
        print(f"        first above cap: {[(round(w['th'],1), round(w['len']), w['material']) for w in near]}")
        rooms = [r for r in pg["rooms"] if r["verdict"] == "confirmed"]
        print(f"        confirmed rooms min short side px {q([r['short_px'] for r in rooms], (0.0,0.1,0.5))} mm {q([r['short_mm'] for r in rooms], (0.0,0.1,0.5))}")


def c_overlap(P):
    print("\n## WALL_PAIR_MIN_OVERLAP_PX (12): kept pair overlap length (true = shortest kept)")
    for s, pg in P.items():
        pairs = pg["pairs"]
        strong = [p for p in pairs if not p["weak"]]
        print(f"  {s} f={pg['factor']:.3f} gate={12*pg['factor']:.1f}: strong pair len px {q([p['len'] for p in strong], (0,0.05,0.1,0.5))} mm {q([p['len_mm'] for p in strong], (0,0.05,0.1,0.5))}")


def c_material(P):
    print("\n## WALL_WEAK_MATERIAL_PER_100PX (3.0, /f): density of material-gated bands; true = OK bands, false = failing bands with >=4 marks")
    for s, pg in P.items():
        mat = pg["material"]
        ok = [m for m in mat if m["ok"]]
        bad = [m for m in mat if not m["ok"] and m["n"] >= 4 and m["span"] >= 0.5]
        gate = 3.0 / pg["factor"]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.2f}/100px: OK n={len(ok)} per100 {q([m['per100'] for m in ok],(0,0.1,0.5))} per_m {q([m['per_m'] for m in ok],(0,0.1,0.5))} "
              f"| FAIL(n>=4,span ok) n={len(bad)} per100 {q([m['per100'] for m in bad],(0.5,0.9,1.0))} per_m {q([m['per_m'] for m in bad],(0.5,0.9,1.0))}")


def c_weak_min_run(P):
    print("\n## WALL_WEAK_MIN_RUN_PX (30): material-OK weak/thick band lengths (true = shortest); weak pairs under the gate (false, unknown material)")
    for s, pg in P.items():
        mat = pg["material"]
        ok = [m for m in mat if m["ok"]]
        gate = 30 * pg["factor"]
        under = [p for p in pg["pairs"] if (p["weak"] or p["thick"]) and p["len"] < gate]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.1f}: OK len px {q([m['len'] for m in ok],(0,0.1,0.5))} mm {q([m['len_mm'] for m in ok],(0,0.1,0.5))} | weak/thick pairs under gate n={len(under)} len px {q([p['len'] for p in under],(0.5,0.9,1.0))}")


def c_hatch_len(P):
    print("\n## WALL_HATCH_MAX_LEN_PX (48): diagonal strokes inside kept wall bands (true class = hatch); false = long diagonal linework")
    for s, pg in P.items():
        h = pg["hatch_in_bands"]
        gate = 48 * pg["factor"]
        over = sum(1 for x in h if x["len"] > gate)
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.1f}: n={len(h)} len px {q([x['len'] for x in h],(0.5,0.9,0.99,1.0))} mm {q([x['len_mm'] for x in h],(0.5,0.9,0.99,1.0))} over gate: {over}")
        # band thickness vs hatch length (hatch length ~ th*sqrt2 for 45deg through-hatch)
        byth = defaultdict(list)
        for x in h:
            byth[round(x["th"] / 5) * 5].append(x["len"])
        print("        by band th: " + ", ".join(f"th~{k}: p90 {sorted(v)[int(0.9*(len(v)-1))]:.0f} (n{len(v)})" for k, v in sorted(byth.items())))


def c_collinear(P):
    print("\n## COLLINEAR_OFFSET_TOL (4): false class = thinnest kept pair spacing (must stay above tol)")
    for s, pg in P.items():
        pairs = [p for p in pg["pairs"] if not p["weak"]]
        allp = pg["pairs"]
        print(f"  {s} f={pg['factor']:.3f} tol={4*pg['factor']:.2f}: strong min th {q([p['th'] for p in pairs],(0,0.02,0.05,0.1))} px ; all pairs min th {q([p['th'] for p in allp],(0,0.02,0.05))} px, mm {q([p['th_mm'] for p in allp],(0,0.02,0.05))}")


def c_anchor_reach(P):
    print("\n## WALL_ANCHOR_SUPPORT_REACH_PX (120): true = door opening widths (the interruption a face continues past)")
    for s, pg in P.items():
        ds = [d for d in pg["doors"] if d["verdict"] == "confirmed"]
        ow = [(d["opening_width_px"] or d["extent_px"], d["denom"]) for d in ds]
        px = [o for o, _ in ow]
        mmv = [o * MMPX * d for o, d in ow if d]
        print(f"  {s} f={pg['factor']:.3f} gate={120*pg['factor']:.0f}: confirmed doors n={len(ds)} opening/extent px {q(px,(0,0.5,0.9,1.0))} mm {q(mmv,(0,0.5,0.9,1.0))}")


def c_room_area(P):
    print("\n## ROOM_MIN_AREA_PX2 (2500 x f^2): true = smallest confirmed room; false = dropped small components")
    for s, pg in P.items():
        rooms = [r for r in pg["rooms"] if r["verdict"] == "confirmed"]
        fp = [r for r in pg["rooms"] if r["verdict"] == "fp"]
        gate = 2500 * pg["factor"] ** 2
        comps = pg["components"]
        small = [c for c in comps if c["fate"] == "dropped" and c["area"] < gate]
        smallish = [c for c in comps if c["fate"] == "dropped" and gate <= c["area"] < 4 * gate]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.0f}px2: confirmed rooms n={len(rooms)} area px2 {q([r['area_px2'] for r in rooms],(0,0.1,0.5))} m2 {q([r['area_m2'] for r in rooms],(0,0.1,0.5))} ; FP rooms n={len(fp)} m2 {q([r['area_m2'] for r in fp],(0,0.5,1))}")
        print(f"        dropped comps under gate: n={len(small)} area {q([c['area'] for c in small],(0.5,0.9,1.0))} m2 {q([c['area_m2'] for c in small],(0.5,0.9,1.0))} ; dropped in [g,4g): n={len(smallish)}")


def c_blind_window(P):
    print("\n## ROOM_BLIND_WINDOW_MAX_AREA_PX2 (10000 x f^2): true = smallest confirmed room WITH a window; false = window-touching door-less dropped components")
    for s, pg in P.items():
        rooms = [r for r in pg["rooms"] if r["verdict"] == "confirmed" and (r["windows"] or 0) > 0]
        gate = 10000 * pg["factor"] ** 2
        comps = pg["components"]
        pockets = [c for c in comps if c["fate"] == "dropped" and c["touch_window"] and not c["touch_conf_door"] and c["area"] < 4 * gate]
        fp = [r for r in pg["rooms"] if r["verdict"] == "fp" and (r["windows"] or 0) > 0 and not r["doors"]]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.0f}px2: confirmed window rooms n={len(rooms)} area px2 {q([r['area_px2'] for r in rooms],(0,0.1,0.5))} m2 {q([r['area_m2'] for r in rooms],(0,0.1,0.5))} "
              f"| dropped window-only pockets n={len(pockets)} px2 {q([c['area'] for c in pockets],(0.5,0.9,1.0))} m2 {q([c['area_m2'] for c in pockets],(0.5,0.9,1.0))} | emitted FP door-less window rooms n={len(fp)} m2 {q([r['area_m2'] for r in fp],(0,0.5,1.0))}")


def c_plugs(P):
    print("\n## ROOM_OPENING_SEAL_PX (12) / ROOM_PLUG_ANCHOR_WIN_PX (24): jamb gap beyond bbox corner (true = max needed) and jamb hug run length (anchor evidence) for confirmed doors' qualified edges")
    for s, pg in P.items():
        pl = [p for p in pg["plugs"] if p["verdict"] == "confirmed" and p["qualified"]]
        gaps = [g for p in pl for g in (p["jamb_gap_a"], p["jamb_gap_b"]) if g is not None]
        gaps_mm = [g for p in pl for g in (p["jamb_gap_a_mm"], p["jamb_gap_b_mm"]) if g is not None]
        hugs = [h for p in pl if p["qualified"] == "interrupted" for h in (p["hug_a"], p["hug_b"])]
        hugs_mm = [h for p in pl if p["qualified"] == "interrupted" for h in (p["hug_a_mm"], p["hug_b_mm"])]
        print(f"  {s} f={pg['factor']:.3f} seal={12*pg['factor']:.1f} win={24*pg['factor']:.1f}: qualified edges n={len(pl)} jamb gap px {q(gaps,(0.5,0.9,1.0))} mm {q(gaps_mm,(0.5,0.9,1.0))} | interrupted-edge hug px {q(hugs,(0,0.1,0.5,1.0))} mm {q(hugs_mm,(0,0.1,0.5,1.0))}")


def c_doors(P):
    print("\n## DOOR_MIN/MAX_SIZE_PX (20/200): confirmed door symbol extents; FP door extents")
    for s, pg in P.items():
        ds = [d for d in pg["doors"] if d["verdict"] == "confirmed"]
        fps = [d for d in pg["doors"] if d["verdict"] == "fp"]
        print(f"  {s} f={pg['factor']:.3f} gate={20*pg['factor']:.1f}-{200*pg['factor']:.0f}: confirmed n={len(ds)} extent px {q([d['extent_px'] for d in ds],(0,0.1,0.5,0.9,1.0))} mm {q([d['extent_mm'] for d in ds],(0,0.1,0.5,0.9,1.0))} | FP n={len(fps)} px {q([d['extent_px'] for d in fps],(0,0.5,1.0))}")
        c = Counter((d["method"], d["assembly"]) for d in ds)
        print("        types: " + ", ".join(f"{k[1] or k[0]}:{v}" for k, v in c.most_common()))


def c_cross(P):
    print("\n## CROSS_WALL_EXPAND_PX (20): needed reach for confirmed doors (true = max); FP doors' need (false)")
    for s, pg in P.items():
        ds = [d for d in pg["doors"] if d["verdict"] == "confirmed"]
        fps = [d for d in pg["doors"] if d["verdict"] == "fp"]
        need = [d["cross_need_px"] for d in ds if d["cross_need_px"] is not None]
        need_mm = [d["cross_need_px"] * MMPX * d["denom"] for d in ds if d["cross_need_px"] is not None and d["denom"]]
        none = sum(1 for d in ds if d["cross_need_px"] is None)
        sll = [d["cross_need_stroked_px"] for d in ds if d["assembly"] == "single_line_leaf" and d["cross_need_stroked_px"] is not None]
        print(f"  {s} f={pg['factor']:.3f} gate={20*pg['factor']:.1f}: confirmed n={len(ds)} need px {q(need,(0.5,0.9,1.0))} mm {q(need_mm,(0.5,0.9,1.0))} (none within 60px: {none}) ; single_line_leaf stroked-need px {q(sll,(0.5,0.9,1.0))} | FP doors need px {q([d['cross_need_px'] for d in fps],(0,0.5,1.0))} ctx {Counter(d['wall_context'] for d in fps)}")
    print("\n## CROSS_DOOR_EXPAND_PX (20) / FALLBACK (8): distance of confirmed windows from nearest confident/fallback door bbox (false: must not be vetoed); suppressed window candidates' distance (true: reach needed)")
    for s, pg in P.items():
        ws = [w for w in pg["windows"] if w["verdict"] == "confirmed"]
        sup = pg["suppressed_windows"]
        print(f"  {s} f={pg['factor']:.3f}: confirmed windows n={len(ws)} dist to conf door px {q([w['dist_conf_door'] for w in ws],(0,0.1,0.5))} ; to fallback door {q([w['dist_fallback_door'] for w in ws],(0,0.1,0.5))} | suppressed n={len(sup)} dist conf {q([x['dist_conf_door'] for x in sup],(0.5,0.9,1.0))} fallback {q([x['dist_fallback_door'] for x in sup],(0.5,0.9,1.0))}")
    print("\n## CROSS_WALL_RUNS_THROUGH (12/8): confirmed windows where a face runs through (boost withheld) vs FP windows")
    for s, pg in P.items():
        ws = [w for w in pg["windows"] if w["verdict"] == "confirmed"]
        fps = [w for w in pg["windows"] if w["verdict"] == "fp"]
        print(f"  {s}: confirmed n={len(ws)} runs_through True {sum(1 for w in ws if w['runs_through'])} ctx {Counter(w['wall_context'] for w in ws)} | FP n={len(fps)} runs_through True {sum(1 for w in fps if w['runs_through'])} ctx {Counter(w['wall_context'] for w in fps)}")


def c_windows(P):
    print("\n## WINDOW_MIN_WIDTH_PX (14): confirmed window opening widths (true = min); FP window widths")
    for s, pg in P.items():
        ws = [w for w in pg["windows"] if w["verdict"] == "confirmed"]
        fps = [w for w in pg["windows"] if w["verdict"] == "fp"]
        print(f"  {s} f={pg['factor']:.3f} gate={max(1.0,14*pg['factor']):.1f}: confirmed n={len(ws)} width px {q([w['width_px'] for w in ws],(0,0.1,0.5,1.0))} mm {q([w['width_mm'] for w in ws],(0,0.1,0.5,1.0))} | FP n={len(fps)} px {q([w['width_px'] for w in fps],(0,0.1,0.5))}")


def c_fill(P):
    print("\n## WALL_FILL_CLASS_MIN_INK_PX (150) / WALL_FILL_BLOCK_MAX_SIDE_PX (72): fill classes (ink, verdict, ring short sides)")
    for s, pg in P.items():
        fc = pg["fill_classes"]
        if not fc:
            print(f"  {s}: no fill rings")
            continue
        items = sorted(fc.items(), key=lambda kv: -kv[1]["ink"])
        print(f"  {s} f={pg['factor']:.3f} gate ink={150*pg['factor']:.0f} side={72*pg['factor']:.0f}:")
        for k, v in items[:8]:
            sh = sorted(v["shorts"])
            print(f"        {k[:28]:28s} ink={v['ink']:9.0f} n={v['n']:4d} wall={v['wall']} band_like={v['band_like']} short px {q(sh,(0.5,0.9,1.0))}")


def c_bridges(P):
    print("\n## WALL_JOINERY_BRIDGE_GAP_PX (80): accepted white-ring gaps (candidate spans)")
    for s, pg in P.items():
        b = pg["bridges"]
        if not b:
            print(f"  {s}: no white-ring candidates")
            continue
        gate = 80 * pg["factor"]
        under = [x["gap"] for x in b if x["gap"] <= gate]
        over = [x["gap"] for x in b if x["gap"] > gate]
        print(f"  {s} f={pg['factor']:.3f} gate={gate:.0f}: bridges made={pg['n_bridges']} ; gaps<=gate {q(under,(0,0.5,0.9,1.0))} ; gaps>gate {q(over,(0,0.1,0.5))}")


ALL = [c_face_min_len, c_thickness, c_overlap, c_material, c_weak_min_run, c_hatch_len,
       c_collinear, c_anchor_reach, c_room_area, c_blind_window, c_plugs, c_doors,
       c_cross, c_windows, c_fill, c_bridges]

if __name__ == "__main__":
    only = [a for a in sys.argv[1:] if a.startswith("s")]
    which = [a for a in sys.argv[1:] if not a.startswith("s")]
    P = load_all(only or None)
    for fn in ALL:
        if which and not any(w in fn.__name__ for w in which):
            continue
        fn(P)
