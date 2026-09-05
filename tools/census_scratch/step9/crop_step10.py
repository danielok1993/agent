"""Step-10 checkpoint picture: s01's hall door at its true factor (0.542),
old rule (no seek: the doorway plug lost, hall + living room one blob) vs
the material-seeking tail (the doorway plug reaches the corner jamb block).
Render = the baseline sweep's render.png (150 DPI, same frame). The old rule
is reproduced by patching `_seek_edges` to return nothing — the caller then
passes no seek edges and `_door_plugs` runs its fixed-reach profile only."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa
from crop_s01 import panel, side_by_side, OUT  # noqa  (the drawing helpers; crop_s01 renders its own pictures only under __main__)
from detection import rooms as _rooms

page = H.load("s01")[0]
_orig = _rooms._seek_edges
_rooms._seek_edges = lambda c: frozenset()
try:
    R_old = run_tapped(page, F542)
finally:
    _rooms._seek_edges = _orig
R_new = run_tapped(page, F542)

hall = [bb for bb in R_new["seals"] if abs(bb[0] - 424) < 3 and abs(bb[1] - 917) < 3][0]
crop = (380, 880, 540, 980)
p1 = panel(R_old, crop, 5, "f=0.542, fixed reach: seal 8.13 — the tail's first sample stops 4.1px off the jamb block; no doorway plug, hall merges with the living room", hall, 0)
p2 = panel(R_new, crop, 5, "f=0.542, material-seeking tail: the jamb block's right face found 12.2px out (191mm); reach 25.2, doorway plug interrupted, hall sealed", hall, 0)
side_by_side([p1, p2], f"{OUT}/step10_s01_hall_door_seek_0542_before_after.png",
             "s01 hall door (424,917)-(467,958) at the true factor: the doorway (top edge) plug's tail seeks the corner jamb block 222mm past the bbox. Blue = barrier, orange = door seals, green = rooms; samples green=touch, yellow=covered, red=no")

crop2 = (195, 400, 540, 1400)
p3 = panel(R_old, crop2, 1.2, "f=0.542, fixed reach: hall (392,920)-(521,1387) + living room (209,415)-(521,912) = one room")
p4 = panel(R_new, crop2, 1.2, "f=0.542, seeking tail: the hall is its own room again (confirmed verdict matched, rooms 9/12)")
side_by_side([p3, p4], f"{OUT}/step10_s01_hall_and_living_room_0542_before_after.png",
             "s01 at the true factor: the hall and the living room, old rule vs the material-seeking tail (the 17 furniture-pen phantoms are unchanged — a separate iteration)")
