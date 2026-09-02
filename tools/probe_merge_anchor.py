"""Measure the collinear merge's ANCHOR on a corpus sheet — the diagnostic
behind "a merged run lies on its longest member's line" in
detection/walls.py::_merge_collinear_segs.

For every merged run with >= 2 original members, on every merge call of the
network build (strong faces, weak faces, stair faces, centerlines):

- the SEED (the segment whose line decided membership) against the ANCHOR
  (the original member the run is placed on — the collinear-support winner,
  WALL_ANCHOR_SUPPORT_REACH_PX): lengths, and the perpendicular displacement
  between their lines at the run's midpoint — the distance the anchor rule
  moved the run;
- each member's offset from the run's line at BOTH endpoints — a member
  inside COLLINEAR_OFFSET_TOL at one end and outside at the other is an
  angled piece that joined on one end (the both-ends test's population);
- whether the run reaches network.faces or a paired segment.

--support additionally scores, for every run whose member lines disagree by
more than LINE_TOL, each distinct member line by the total length of STRONG
ink (stroked faces and wall-fill outlines — the strong-face merge's inputs,
which also vote for the weak and stair merges; the centerline merge votes
among its own stroked members here, though detection gives it no votes)
lying within LINE_TOL of it, for several reaches along the axis beyond the
run's extent, unfiltered (`support`) and restricted to ink pen-compatible
with the run (`support_pen`) — the measurement behind the collinear-support
anchor. It reports how often the support winner at each reach differs from
the anchor detection chose.

Usage:
    python tools/probe_merge_anchor.py s03 [--support] [--list] [--json out.json]

Measured 2026-09-02 (longest-member anchor, ten sheets): 4,223 runs, 1,276
with seed != longest, 92 displaced > 1px on a seed under half the longest's
length (61 strong-face, 52 reaching faces, 41 a segment); 197 one-end-only
members, 164 of them s01's 45-degree hatch chains. Support vote vs the
longest member (same sheets): winner differs in 101/219/253/294/313/357/581
runs at reaches 0/50/100/120/150/200/page (42/53/66/69/75/86/137 of them
reaching a paired segment); the pen filter moves ~14 of those and no known
case, so detection does not apply it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import detection.walls as W  # noqa: E402
from detection.geometry import _line_length  # noqa: E402
from tools._corpus_page import load_detection_pages  # noqa: E402

LINE_TOL = 0.3          # px: same drawn line (s02's same-line jitter is <= 0.3)
REACHES = (0.0, 50.0, 100.0, 120.0, 150.0, 200.0, math.inf)
CALL_LABELS = {1: "faces", 2: "weak", 3: "stair", 4: "centerlines"}


def _frame(seg):
    """Unit axis (ux, uy), normal (nx, ny) and origin of a segment's line."""
    L = _line_length(seg.p1, seg.p2)
    ux, uy = (seg.p2[0] - seg.p1[0]) / L, (seg.p2[1] - seg.p1[1]) / L
    return ux, uy, -uy, ux, seg.p1


def _offset(p, frame):
    ux, uy, nx, ny, o = frame
    return (p[0] - o[0]) * nx + (p[1] - o[1]) * ny


def _along(p, frame):
    ux, uy, nx, ny, o = frame
    return (p[0] - o[0]) * ux + (p[1] - o[1]) * uy


def _line_offset_at(seg, frame, t):
    """Signed offset of `seg`'s LINE from the frame's line at axis position t."""
    s1, s2 = _offset(seg.p1, frame), _offset(seg.p2, frame)
    t1, t2 = _along(seg.p1, frame), _along(seg.p2, frame)
    if abs(t2 - t1) < 1e-9:
        return s1
    return s1 + (s2 - s1) * (t - t1) / (t2 - t1)


def analyse_run(run, seed, anchor, members, tol):
    fr = _frame(anchor)
    t_lo, t_hi = sorted((_along(run.p1, fr), _along(run.p2, fr)))
    t_mid = 0.5 * (t_lo + t_hi)
    disp = _line_offset_at(seed, fr, t_mid)      # seed line vs run (anchor) line
    per_member = []
    one_end_only = 0
    max_delta = 0.0
    for m in members:
        s1, s2 = _offset(m.p1, fr), _offset(m.p2, fr)
        max_delta = max(max_delta, abs(s1 - s2))
        if (abs(s1) <= tol) != (abs(s2) <= tol):
            one_end_only += 1
        per_member.append((m, s1, s2))
    return {
        "seed_len": _line_length(seed.p1, seed.p2),
        "anchor_len": _line_length(anchor.p1, anchor.p2),
        "displacement": disp,
        "extent": (t_lo, t_hi),
        "frame": fr,
        "one_end_only": one_end_only,
        "max_delta": max_delta,
        "members": per_member,
    }


def strong_ink(segs):
    """The support population: strong stroked faces and wall-fill outlines."""
    return [
        s for s in segs
        if (s.stroked and s.stroke_width > 0) or s.wall_fill
    ]


def support_votes(run_info, run, members, strong):
    """For each distinct member line, the strong-ink length within LINE_TOL of
    it at each reach beyond the run's extent, unfiltered and restricted to
    ink pen-compatible with the run. Returns
    [(member, {reach: len}, {reach: len_pen_compatible})]."""
    fr = run_info["frame"]
    t_lo, t_hi = run_info["extent"]
    # Distinct member lines (cluster by offset at the run midpoint).
    t_mid = 0.5 * (t_lo + t_hi)
    lines: list[tuple[object, float]] = []
    for m in members:
        off = _line_offset_at(m, fr, t_mid)
        for rep, rep_off in lines:
            if abs(off - rep_off) <= LINE_TOL:
                if _line_length(m.p1, m.p2) > _line_length(rep.p1, rep.p2):
                    lines[lines.index((rep, rep_off))] = (m, rep_off)
                break
        else:
            lines.append((m, off))
    if len(lines) < 2:
        return []
    votes = []
    for rep, rep_off in lines:
        rep_fr = _frame(rep)
        per_reach = {}
        per_reach_pen = {}
        for reach in REACHES:
            total = 0.0
            total_pen = 0.0
            for s in strong:
                # Both endpoints on the candidate line, and the piece within
                # reach of the run along the axis.
                if abs(_offset(s.p1, rep_fr)) > LINE_TOL or abs(_offset(s.p2, rep_fr)) > LINE_TOL:
                    continue
                a, b = sorted((_along(s.p1, fr), _along(s.p2, fr)))
                if b < t_lo - reach or a > t_hi + reach:
                    continue
                L = _line_length(s.p1, s.p2)
                total += L
                if W._pens_compatible(run.pen, s.pen):
                    total_pen += L
            per_reach[reach] = total
            per_reach_pen[reach] = total_pen
        votes.append((rep, per_reach, per_reach_pen))
    return votes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--support", action="store_true",
                    help="score member lines by collinear strong-ink support")
    ap.add_argument("--list", action="store_true",
                    help="list every displaced run (> --disp px, seed under half the anchor)")
    ap.add_argument("--disp", type=float, default=1.0)
    ap.add_argument("--json", type=Path, help="write per-run records here")
    args = ap.parse_args()

    records: list[dict] = []
    grand = {"runs": 0, "seed_ne_anchor": 0, "displaced": 0, "displaced_faces": 0,
             "displaced_seg": 0, "one_end_only": 0}
    support_summary: dict[float, int] = {r: 0 for r in REACHES}
    support_runs = 0
    orig = W._merge_collinear_segs

    for page in load_detection_pages(args.slug):
        tol = W.WallGates.at(page.scale_factor).COLLINEAR_OFFSET_TOL
        calls: list[tuple[str, list, list]] = []      # (label, inputs, trace)

        def recording(segs, gap_px, *, gates=W.WALL_GATES_UNSCALED, support=None):
            trace: list = []
            out = orig(segs, gap_px, gates=gates, support=support, trace=trace)
            calls.append((CALL_LABELS.get(len(calls) + 1, f"call{len(calls) + 1}"),
                          list(segs), trace))
            return out

        W._merge_collinear_segs = recording
        try:
            network = W.detect_wall_network(
                page.page_data.paths, page.page_data.text_spans,
                exclude_path_indices=page.exclude, scale_factor=page.scale_factor,
            )
        finally:
            W._merge_collinear_segs = orig
        face_sets = [set(f.indices) for f in network.faces]
        seg_sets = [set(s.face_path_indices) for s in network.segments]

        print(f"\n{args.slug} page {page.page_number} f={page.scale_factor:.3f} "
              f"tol={tol:.2f} faces={len(network.faces)} segs={len(network.segments)}")
        # The support population: the strong-face merge's own inputs vote
        # for it and for the weak/stair merges (a hairline run is placed by
        # the strong ink it continues, never by other hairlines); the
        # centerline merge votes among its own stroked members.
        strong_faces = strong_ink(calls[0][1]) if calls else []
        for label, inputs, trace in calls:
            runs = [(r, s, a, m) for r, s, a, m in trace if len(m) >= 2]
            if not runs:
                continue
            population = strong_ink(inputs) if label == "centerlines" else strong_faces
            disp_vals, displaced, one_end = [], [], 0
            for run, seed, anchor, members in runs:
                info = analyse_run(run, seed, anchor, members, tol)
                idx = set(run.indices)
                reaches_faces = any(idx <= fs for fs in face_sets)
                reaches_seg = any(idx & ss for ss in seg_sets)
                disp_vals.append(abs(info["displacement"]))
                one_end += info["one_end_only"]
                is_displaced = (abs(info["displacement"]) > args.disp
                                and info["seed_len"] < 0.5 * info["anchor_len"])
                rec = {
                    "page": page.page_number, "call": label,
                    "run": [list(run.p1), list(run.p2)],
                    "seed_len": info["seed_len"], "anchor_len": info["anchor_len"],
                    "displacement": info["displacement"],
                    "one_end_only": info["one_end_only"], "max_delta": info["max_delta"],
                    "n_members": len(members), "indices": sorted(run.indices),
                    "reaches_faces": reaches_faces, "reaches_segment": reaches_seg,
                    "displaced": is_displaced,
                }
                if args.support:
                    votes = support_votes(info, run, members, population)
                    if votes:
                        support_runs += 1
                        rec["support"] = []
                        for reach in REACHES:
                            # Detection's tie-break: ties go to the longest line.
                            winner = max(
                                votes,
                                key=lambda v: (v[1][reach], _line_length(v[0].p1, v[0].p2)),
                            )[0]
                            if winner is not anchor and _line_length(winner.p1, winner.p2) != info["anchor_len"]:
                                support_summary[reach] += 1
                        for rep, per_reach, per_reach_pen in votes:
                            rec["support"].append({
                                "line_len": _line_length(rep.p1, rep.p2),
                                "is_anchor": rep is anchor,
                                "p1": list(rep.p1), "p2": list(rep.p2),
                                "support": {str(k): v for k, v in per_reach.items()},
                                "support_pen": {str(k): v for k, v in per_reach_pen.items()},
                            })
                records.append(rec)
                if is_displaced:
                    displaced.append(rec)
            grand["runs"] += len(runs)
            grand["seed_ne_anchor"] += sum(1 for r, s, a, m in runs if s is not a)
            grand["displaced"] += len(displaced)
            grand["displaced_faces"] += sum(1 for r in displaced if r["reaches_faces"])
            grand["displaced_seg"] += sum(1 for r in displaced if r["reaches_segment"])
            grand["one_end_only"] += one_end
            disp_vals.sort()
            p90 = disp_vals[min(len(disp_vals) - 1, int(0.9 * len(disp_vals)))]
            print(f"  [{label}] runs={len(runs)} seed!=anchor="
                  f"{sum(1 for r, s, a, m in runs if s is not a)} "
                  f"|seed-anchor| p50={disp_vals[len(disp_vals) // 2]:.2f} p90={p90:.2f} "
                  f"max={disp_vals[-1]:.2f}  displaced(>{args.disp}px, seed<half)="
                  f"{len(displaced)} (faces {sum(1 for r in displaced if r['reaches_faces'])}, "
                  f"seg {sum(1 for r in displaced if r['reaches_segment'])})  "
                  f"one-end-only members={one_end}")
            if args.list:
                for r in displaced:
                    print(f"      seed L={r['seed_len']:.1f} anchor L={r['anchor_len']:.1f} "
                          f"disp={r['displacement']:+.2f} n={r['n_members']} "
                          f"run={tuple(round(v) for v in r['run'][0])}-{tuple(round(v) for v in r['run'][1])} "
                          f"faces={r['reaches_faces']} seg={r['reaches_segment']} idx={r['indices'][:4]}")

    print(f"\nTOTAL {grand}")
    if args.support:
        print(f"support-scored runs (member lines disagree by > {LINE_TOL}px): {support_runs}")
        for reach in REACHES:
            print(f"  reach {reach}: support winner != the anchor detection chose in {support_summary[reach]} runs")
    if args.json:
        args.json.write_text(json.dumps(records))
        print("wrote", args.json)


if __name__ == "__main__":
    main()
