"""Step-11 checkpoint pictures: s01 at its true factor (0.542), the share
gate alone (the red furniture pen at 15.2 % is a wall pen: 17 phantoms) vs
the doorway veto (no doorway is cut into red: the phantoms are gone). Render
= the baseline sweep's render.png (150 DPI, same frame). The old rule is
reproduced by patching `_doorway_pens` to name nobody, which leaves the
share gate standing alone exactly as before the step. Red lines = the faces
in the furniture pen; blue = barrier; orange = door seals; green = rooms."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa
from crop_s01 import panel, side_by_side, OUT  # noqa  (drawing helpers; crop_s01 renders only under __main__)
from detection import rooms as _rooms

RED = (1.0, 0.0, 0.0)


def main():
    page = H.load("s01")[0]
    _orig = _rooms._doorway_pens
    _rooms._doorway_pens = lambda *a, **k: {}
    try:
        R_old = run_tapped(page, F542)
    finally:
        _rooms._doorway_pens = _orig
    R_new = run_tapped(page, F542)
    n_old = len(R_old["rooms"]); n_new = len(R_new["rooms"])

    crop = (195, 400, 540, 1400)
    p1 = panel(R_old, crop, 1.2, f"f=0.542, share gate alone: red = 15.2% of the paired network -> wall pen; {n_old} rooms on the page", show_faces_pen=RED)
    p2 = panel(R_new, crop, 1.2, f"f=0.542, doorway veto: no doorway is cut into red -> furniture; {n_new} rooms on the page", show_faces_pen=RED)
    side_by_side([p1, p2], f"{OUT}/step11_s01_ground_floor_furniture_pen_veto_0542_before_after.png",
                 "s01 ground floor at the true factor: the kitchen units, sofa and wardrobe front fenced by the red furniture pen (share gate alone) vs the doorway veto. Red lines = faces in the furniture pen; blue = barrier; orange = door seals; green = rooms")

    crop2 = (800, 400, 1150, 1400)
    p3 = panel(R_old, crop2, 1.2, "f=0.542, share gate alone: the bed frame, wardrobe end and stair box fence slivers, a strip and a bedroom split", show_faces_pen=RED)
    p4 = panel(R_new, crop2, 1.2, "f=0.542, doorway veto: the bedroom and the front room whole again; the merged landing (unreviewed) stays", show_faces_pen=RED)
    side_by_side([p3, p4], f"{OUT}/step11_s01_first_floor_furniture_pen_veto_0542_before_after.png",
                 "s01 first floor at the true factor: share gate alone vs the doorway veto. Red lines = faces in the furniture pen; blue = barrier; orange = door seals; green = rooms")
    print("rooms old/new:", n_old, n_new)


if __name__ == "__main__":
    main()
