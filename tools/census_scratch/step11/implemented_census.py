"""The shipped rule AS IMPLEMENTED (rooms._doorway_pens on the room stage's
own pass-1 plugs), every sheet at its factor + s01 at 0.542: today's
share-gated wall pens, the doorway owners, the VETOED pens — and the same
with the lone-collinear clause disabled (paired faces only), to show which
clause each corpus verdict rests on.

Usage: .venv/bin/python tools/census_scratch/step11/implemented_census.py [slug[@factor] ...]
"""
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from detection.geometry import _line_length  # noqa: E402

ALL = [f"s{i:02d}" for i in range(1, 21)]
DEFAULT = ["s01", f"s01@{F542}"] + [s for s in ALL if s != "s01"]


def census(slug, factor):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    try:
        r = run_tapped(page, factor)
    except IndexError:
        print(f"=== {slug} f={f:.3f}: nothing detected")
        return
    net = r["extras"]["network"]
    if net is None or net.is_empty():
        print(f"=== {slug} f={f:.3f}: empty network")
        return
    doors = [c for c in r["extras"]["all_geo"] if c.entity_type == "door"]
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

    paired = net.paired_face_indices()
    per = {}
    for fc in net.faces:
        if fc.stroked and fc.pen is not None and (fc.indices & paired):
            per[fc.pen] = per.get(fc.pen, 0.0) + _line_length(fc.p1, fc.p2)
    tot = sum(per.values())
    today = {p for p, L in per.items() if L >= rooms.ROOM_WALL_PEN_MIN_FRAC * tot}
    records = [(rec["cand"], rec["plugs"]) for rec in r["seals"].values()]
    owners = rooms._doorway_pens(records, net.faces, paired, in_zone)
    paired_faces = [fc for fc in net.faces if fc.indices & paired]
    owners_b = rooms._doorway_pens(records, paired_faces, paired, in_zone)
    vet = {p for p in today if p not in owners} if owners else set()
    vet_b = {p for p in today if p not in owners_b} if owners_b else set()
    print(f"=== {slug} f={f:.3f}: share-gated {sorted(map(str, today))}")
    print(f"    owners      : " + ", ".join(f"{p}={n}" for p, n in sorted(owners.items(), key=lambda kv: str(kv[0])))
          + f"   vetoed {sorted(map(str, vet)) or '-'}")
    print(f"    paired-only : " + ", ".join(f"{p}={n}" for p, n in sorted(owners_b.items(), key=lambda kv: str(kv[0])))
          + f"   vetoed {sorted(map(str, vet_b)) or '-'}" + ("   <- DIFFERS" if vet_b != vet or owners_b != owners else ""))


if __name__ == "__main__":
    for a in (sys.argv[1:] or DEFAULT):
        slug, _, fac = a.partition("@")
        census(slug, float(fac) if fac else None)
