"""Per-pen PAIRED face length at identity vs 0.542 on s01 — the room stage's
wall-pen fraction (ROOM_WALL_PEN_MIN_FRAC) — and what each pen's pairs are."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa
from detection.geometry import _line_length  # noqa

slug = sys.argv[1] if len(sys.argv) > 1 else "s01"
factors = [None, F542] if slug == "s01" else [None]
page = H.load(slug)[0]
for f in factors:
    ents, extras = H.run(page, factor=f, keep_network=True)
    net = extras["network"]
    paired = net.paired_face_indices()
    per_pen = {}
    per_pen_all = {}
    for fc in net.faces:
        L = _line_length(fc.p1, fc.p2)
        key = fc.pen if fc.stroked else ("unstroked",)
        per_pen_all[key] = per_pen_all.get(key, 0.0) + L
        if fc.stroked and fc.pen is not None and (fc.indices & paired):
            per_pen[fc.pen] = per_pen.get(fc.pen, 0.0) + L
    total = sum(per_pen.values())
    print(f"\n=== {slug} f={page.scale_factor if f is None else f:.3f}: paired stroked length {total:.0f}px, "
          f"stroke_ref={net.wall_stroke_reference():.2f}, segments={len(net.segments)}")
    for pen, L in sorted(per_pen.items(), key=lambda kv: -kv[1]):
        print(f"   pen={pen} paired={L:.0f} ({100 * L / total:.1f}%) {'WALL PEN' if L >= rooms.ROOM_WALL_PEN_MIN_FRAC * total else 'not'}   all faces of this pen={per_pen_all.get(pen, 0):.0f}")
    # segments by pen composition and tier
    faces_by_path = {}
    for fc in net.faces:
        for pi in fc.indices:
            faces_by_path.setdefault(pi, []).append(fc)
    tier_by_pen = {}
    for s in net.segments:
        pens = set()
        for pi in s.face_path_indices:
            for fc in faces_by_path.get(pi, ()):
                pens.add(fc.pen if fc.stroked else None)
        tier = "through" if getattr(s, "through", False) else "thick" if getattr(s, "thick", False) else "weak" if getattr(s, "weak", False) else "plain"
        key = (tuple(sorted(map(str, pens))), tier)
        L = _line_length(s.p1, s.p2)
        t = tier_by_pen.setdefault(key, [0, 0.0, []])
        t[0] += 1
        t[1] += L
        t[2].append(round(s.thickness_px, 1))
    for key, (n, L, ths) in sorted(tier_by_pen.items(), key=lambda kv: -kv[1][1]):
        print(f"   segs pens={key[0]} tier={key[1]}: n={n} len={L:.0f} th={sorted(set(ths))[:8]}")
