"""Extract Hu Moment template from confirmed door arcs in a pipeline output run."""
import json
import math
import sys
import numpy as np
import cv2

PRIMITIVES = "outputs/2026-06-08_12-39-11/pages/page_01/primitives.json"

# path_indices for each confirmed door (from candidates.json)
DOOR_ARCS = {
    "door_0000": [1575, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587],
    "door_0001": [1711, 1712, 1713, 1714, 1715, 1716, 1717, 1718, 1719, 1720, 1721],
    "door_0002": [2819, 2820, 2821, 2822, 2823, 2824, 2825, 2826, 2827, 2828, 2829],
    "door_0003": [2851, 2852, 2853, 2854, 2855, 2856, 2857, 2858, 2859, 2860, 2861],
}

CANVAS = 64  # rasterize each arc onto a 64×64 binary canvas


def rasterize_segments(segments, canvas_size=CANVAS):
    """Draw line segments onto a normalized binary canvas."""
    if not segments:
        return None

    all_pts = [pt for seg in segments for pt in seg]
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w, h = x1 - x0, y1 - y0
    span = max(w, h)
    if span < 1e-6:
        return None

    margin = 4
    scale = (canvas_size - 2 * margin) / span

    img = np.zeros((canvas_size, canvas_size), dtype=np.uint8)
    for p1, p2 in segments:
        cx1 = int((p1[0] - x0) * scale) + margin
        cy1 = int((p1[1] - y0) * scale) + margin
        cx2 = int((p2[0] - x0) * scale) + margin
        cy2 = int((p2[1] - y0) * scale) + margin
        cv2.line(img, (cx1, cy1), (cx2, cy2), 255, 1)
    return img


def hu_log(img):
    m = cv2.moments(img)
    hu = cv2.HuMoments(m).flatten()
    return -np.sign(hu) * np.log10(np.abs(hu) + 1e-10)


def main():
    with open(PRIMITIVES) as f:
        data = json.load(f)

    # Build index: path_index → path entry
    by_index = {}
    for path in data.get("paths", []):
        by_index[path["path_index"]] = path

    all_hu = []
    for door_id, indices in DOOR_ARCS.items():
        segs = []
        for idx in indices:
            p = by_index.get(idx)
            if p is None:
                print(f"  WARNING: path_index {idx} not found")
                continue
            pts = p["points"]
            if len(pts) >= 2:
                segs.append((pts[0], pts[-1]))

        img = rasterize_segments(segs)
        if img is None:
            print(f"{door_id}: could not rasterize")
            continue

        hu = hu_log(img)
        all_hu.append(hu)
        print(f"{door_id}: hu = {[round(v, 4) for v in hu]}")

    if not all_hu:
        print("No doors rasterized — check path indices.")
        sys.exit(1)

    template = np.mean(all_hu, axis=0)
    print(f"\nTemplate (mean of {len(all_hu)} doors):")
    print(f"  {[round(v, 6) for v in template]}")
    print("\nPaste into detection/doors/constants.py:")
    vals = ", ".join(f"{v:.6f}" for v in template)
    print(f"_DOOR_HU_TEMPLATE = np.array([{vals}])")


if __name__ == "__main__":
    main()
