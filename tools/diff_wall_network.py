"""Diff the wall network between two code trees inside a probe box — the
barrier-level attribution the sweep report cannot give.

Builds detect_wall_network for one sheet in the WORKING TREE and in a BASE
tree (a detached `git worktree` of --base, default main, created and removed
here; or an existing checkout via --base-dir), each in its own interpreter so
neither tree's modules leak into the other. The PDF and its caches are read
from this checkout's fixtures/. Prints, per tree, every face, segment,
wall-fill polygon and white ring intersecting the box, then the faces and
segments present in only one tree (matched by rounded geometry).

--idx traces path indices instead of a box: where each ends up in each tree
(input to / kept by / demoted by _demote_lattice_faces, network.faces,
segments) — the question "why did this face vanish" in one run.

Usage:
    python tools/diff_wall_network.py s17 3425 2170 3592 2220
    python tools/diff_wall_network.py s01 --idx 2448 3065 2454
    python tools/diff_wall_network.py s18 2240 780 2580 840 --base HEAD~1
    python tools/diff_wall_network.py s03 ... --base-dir /path/to/other/checkout

Found this iteration's mechanisms in one pass each: s17's inner face moving
1.5px onto its true line made a 35.5px band 37.0 (over WALL_MAX_THICKNESS_PX,
window-reveal slivers); s01's jamb nib fused with a stair stringer under
longest-first seeding; s18's wall belts lattice-demoted when run direction
flipped.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools._corpus_page import sheet_pdf  # noqa: E402

# Runs inside each tree. argv: tree_dir pdf page_number idx_json
DUMP = r'''
import json, sys
tree, pdf, pno, idxs = sys.argv[1], sys.argv[2], int(sys.argv[3]), set(json.loads(sys.argv[4]))
sys.path.insert(0, tree)
import fitz
import detection.walls as W
from detection.doors.assembly import door_open_leaf_path_indices
from detection.doors.detect import detect_doors
from detection.geometry import _line_length
from extraction.extractor import extract_page
from pipeline import resolve_page_regions
from scale.factor import detection_scale
from scale.resolver import resolve_page_scales
from scale.store import load_stored
from scale.viewport import viewport_scales
doc = fitz.open(pdf)
page_data = extract_page(doc, pno - 1)
rr = resolve_page_regions(pdf_path=pdf, page=doc[pno - 1], page_data=page_data,
                          gemini_client=None, skip_gemini=True, refresh_regions=False, crop_dir=None)
if rr.skip_detection:
    print(json.dumps({"skip": True})); sys.exit(0)
ps = resolve_page_scales(page_data=page_data, regions=rr.regions,
                         viewports=viewport_scales(doc, doc[pno - 1]),
                         stored=load_stored(pdf, pno), fallback=None, pdf_path=pdf,
                         crop_fn=None, allow_prompt=False, suspend_display=None)
det = detection_scale(ps, rr.regions, pno)
pd = rr.detection_page_data
doors = detect_doors(pd.paths, pd.text_spans, None, scale_factor=det.factor)
excl = door_open_leaf_path_indices(doors, pd.paths)
lattice = {"in": [], "kept": [], "out": []}
orig = W._demote_lattice_faces
def rec(faces, *, gates=W.WALL_GATES_UNSCALED):
    kept, lat = orig(faces, gates=gates)
    def keep(lst): return [seg(f) for f in lst if set(f.indices) & idxs]
    lattice["in"], lattice["kept"], lattice["out"] = keep(faces), keep(kept), keep(lat)
    return kept, lat
def seg(f):
    return {"p1": list(f.p1), "p2": list(f.p2), "L": _line_length(f.p1, f.p2),
            "stroked": bool(getattr(f, "stroked", False)),
            "sw": float(getattr(f, "stroke_width", 0.0)),
            "fill": bool(getattr(f, "wall_fill", False)),
            "hint": bool(getattr(f, "layer_hint", False)),
            "backed": bool(getattr(f, "material_backed", False)),
            "idx": sorted(f.indices)}
W._demote_lattice_faces = rec if idxs else orig
net = W.detect_wall_network(pd.paths, pd.text_spans, exclude_path_indices=excl, scale_factor=det.factor)
out = {
    "factor": det.factor,
    "faces": [seg(f) for f in net.faces],
    "segments": [{"p1": list(s.p1), "p2": list(s.p2), "th": s.thickness_px, "src": s.source,
                  "stroked": s.stroked, "idx": list(s.face_path_indices)} for s in net.segments],
    "fills": [{"bounds": list(p.bounds), "area": p.area} for p in net.fill_polygons],
    "white": [list(r.poly.bounds) for r in net.white_bands],
    "lattice": lattice,
}
print(json.dumps(out))
'''


def dump(tree: Path, pdf: str, page: int, idxs: list[int]) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", DUMP, str(tree), pdf, str(page), json.dumps(idxs)],
        capture_output=True, text=True, cwd=str(tree),
    )
    if proc.returncode != 0:
        raise SystemExit(f"dump failed in {tree}:\n{proc.stderr[-4000:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _fmt_face(f: dict) -> str:
    idx = f["idx"]
    return (f"face {tuple(round(v, 2) for v in f['p1'])}-{tuple(round(v, 2) for v in f['p2'])} "
            f"L={f['L']:.1f} stroked={f['stroked']} sw={f['sw']:.2f} fill={f['fill']} "
            f"hint={f['hint']} backed={f['backed']} idx={idx[:6]}{'…' if len(idx) > 6 else ''}")


def _fmt_seg(s: dict) -> str:
    return (f"seg {tuple(round(v, 2) for v in s['p1'])}-{tuple(round(v, 2) for v in s['p2'])} "
            f"th={s['th']} src={s['src']} stroked={s['stroked']} idx={s['idx'][:6]}")


def _in_box(item: dict, box) -> bool:
    from shapely.geometry import LineString, box as shp_box
    return LineString([item["p1"], item["p2"]]).intersects(shp_box(*box))


def _key(item: dict, extra=()) -> tuple:
    return (tuple(round(v, 1) for v in item["p1"]), tuple(round(v, 1) for v in item["p2"]), *extra)


def report_box(trees: dict[str, dict], box) -> None:
    from shapely.geometry import box as shp_box
    b = shp_box(*box)
    for label, d in trees.items():
        print(f"\n=== {label}: faces={len(d['faces'])} segs={len(d['segments'])} "
              f"fills={len(d['fills'])} f={d['factor']:.3f}")
        for f in d["faces"]:
            if _in_box(f, box):
                print("  " + _fmt_face(f))
        for s in d["segments"]:
            if _in_box(s, box):
                print("  " + _fmt_seg(s))
        for i, p in enumerate(d["fills"]):
            if shp_box(*p["bounds"]).intersects(b):
                print(f"  fill#{i} bounds={[round(v, 1) for v in p['bounds']]} area={p['area']:.0f}")
        for w in d["white"]:
            if shp_box(*w).intersects(b):
                print(f"  white ring bounds={[round(v, 1) for v in w]}")
    (la, a), (lb, bt) = trees.items()
    fa = {_key(f, (f["stroked"], f["fill"])): f for f in a["faces"] if _in_box(f, box)}
    fb = {_key(f, (f["stroked"], f["fill"])): f for f in bt["faces"] if _in_box(f, box)}
    print(f"\n--- faces only in {la}:")
    for k, f in fa.items():
        if k not in fb:
            print("  " + _fmt_face(f))
    print(f"--- faces only in {lb}:")
    for k, f in fb.items():
        if k not in fa:
            print("  " + _fmt_face(f))
    sa = {_key(s, (round(s["th"], 1),)): s for s in a["segments"] if _in_box(s, box)}
    sb = {_key(s, (round(s["th"], 1),)): s for s in bt["segments"] if _in_box(s, box)}
    print(f"--- segs only in {la}:")
    for k, s in sa.items():
        if k not in sb:
            print("  " + _fmt_seg(s))
    print(f"--- segs only in {lb}:")
    for k, s in sb.items():
        if k not in sa:
            print("  " + _fmt_seg(s))


def report_idx(trees: dict[str, dict], idxs: list[int]) -> None:
    want = set(idxs)
    for label, d in trees.items():
        print(f"\n=== {label}: fate of {sorted(want)}")
        for stage in ("in", "kept", "out"):
            for f in d["lattice"][stage]:
                print(f"  [lattice {stage}] " + _fmt_face(f))
        for f in d["faces"]:
            if set(f["idx"]) & want:
                print("  [network.faces] " + _fmt_face(f))
        for s in d["segments"]:
            if set(s["idx"]) & want:
                print("  [network.segments] " + _fmt_seg(s))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("box", nargs="*", type=float, metavar="X0 Y0 X1 Y1",
                    help="probe box in 150-DPI page pixels")
    ap.add_argument("--idx", nargs="+", type=int, help="trace these path indices instead")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--base", default="main", help="git ref for the base tree (default main)")
    ap.add_argument("--base-dir", type=Path, help="an existing checkout to use as the base tree")
    args = ap.parse_args()
    if not args.idx and len(args.box) != 4:
        ap.error("give a box (X0 Y0 X1 Y1) or --idx")

    pdf = sheet_pdf(args.slug)
    idxs = args.idx or []
    tmp: Path | None = None
    base_dir = args.base_dir
    try:
        if base_dir is None:
            tmp = Path(tempfile.mkdtemp(prefix="wallnet_base_"))
            subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach",
                            str(tmp), args.base], check=True, capture_output=True)
            base_dir = tmp
            base_label = f"BASE({args.base})"
        else:
            base_label = f"BASE({base_dir})"
        trees = {
            base_label: dump(base_dir, pdf, args.page, idxs),
            "WORKING": dump(ROOT, pdf, args.page, idxs),
        }
    finally:
        if tmp is not None:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(tmp)],
                           capture_output=True)
    if any(d.get("skip") for d in trees.values()):
        raise SystemExit(f"{args.slug} page {args.page}: detection skipped")
    if idxs:
        report_idx(trees, idxs)
    else:
        report_box(trees, tuple(args.box))


if __name__ == "__main__":
    main()
