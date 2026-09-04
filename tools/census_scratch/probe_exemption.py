"""Which corpus windows does the hinge-jamb wall-run exemption DECIDE at the
current CROSS_DOOR_EXPAND_PX reach?  A window is decided by the exemption when
a real-tier door's dilated bbox covers >= CROSS_DOOR_MIN_WINDOW_COVER of it
(the plain veto would fire) and _window_in_door_wall_run returns True.
Also reports the closest real-door distance of every surviving window."""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import postprocess as pp  # noqa: E402
from detection.doors.detect import detect_doors  # noqa: E402
from detection.windows import detect_windows  # noqa: E402


def bbox_gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


for slug in sys.argv[1:]:
    pages = H.load(slug)
    for p in pages:
        f = p.scale_factor
        pd = p.page_data
        gates = pp.CrossGates.at(f)
        doors = detect_doors(pd.paths, pd.text_spans, None, scale_factor=f)
        wins = detect_windows(pd.paths, scale_factor=f)
        real = [d for d in doors if d.confidence >= pp.CROSS_DOOR_MIN_CONFIDENCE]
        decided, vetoed = [], []
        for w in wins:
            wa = pp._bbox_area(w.bbox)
            for d in real:
                db = pp._bbox_expanded(d.bbox, gates.CROSS_DOOR_EXPAND_PX)
                ix = max(0.0, min(w.bbox[2], db[2]) - max(w.bbox[0], db[0]))
                iy = max(0.0, min(w.bbox[3], db[3]) - max(w.bbox[1], db[1]))
                cover = ix * iy / wa if wa > 0 else 0
                if cover < pp.CROSS_DOOR_MIN_WINDOW_COVER:
                    continue
                ex = pp._window_in_door_wall_run(w, d)
                rec = (tuple(round(v) for v in w.bbox), d.candidate_id, round(cover, 3),
                       round(bbox_gap(w.bbox, d.bbox), 2))
                (decided if ex else vetoed).append(rec)
        print(f"{slug} p{p.page_number} f={f:.3f} reach={gates.CROSS_DOOR_EXPAND_PX:.1f} "
              f"windows={len(wins)} real_doors={len(real)}")
        for r in decided:
            print("   EXEMPTION DECIDES", r)
        for r in vetoed:
            print("   vetoed", r)
