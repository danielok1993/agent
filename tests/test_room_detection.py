"""Room detection tests (detection/rooms.py).

Fixtures build wall bands as synthetic PathPrimitives (two stroked faces per
wall), run detect_wall_network, and extract rooms via detect_rooms. Rooms are
free-space components between wall solids, so expected bounds sit just inside
the inner wall faces (inner face + line barrier + wall dilation).
"""
import unittest

from shapely.geometry import (
    Point as ShapelyPoint, Polygon as ShapelyPolygon, box as shapely_box,
)
from shapely.ops import unary_union

from models import Candidate, PathPrimitive, TextSpan
from detection import detect_wall_network
from detection.rooms import (
    ROOM_GAP_CLOSE_PX, _door_plugs, _open_leaf_edges, _restrict_swing_plugs,
    _sliding_end_edges, _swing_hinge_edges, _window_seal, detect_rooms,
)

PAGE_W, PAGE_H = 1000.0, 800.0


def path(idx, points, item_type="l", stroke_width=1.5, fill=None, dashes="",
         layer=None, color=(0.0, 0.0, 0.0)):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx,
        item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=color,
        fill=fill,
        stroke_width=stroke_width,
        dashes=dashes,
        layer=layer,
        points=points,
    )


def hline(idx, x0, x1, y, **kw):
    return path(idx, [(x0, y), (x1, y)], **kw)


def vline(idx, x, y0, y1, **kw):
    return path(idx, [(x, y0), (x, y1)], **kw)


def wall_band_h(start_idx, x0, x1, y, thickness=8.0):
    return [hline(start_idx, x0, x1, y), hline(start_idx + 1, x0, x1, y + thickness)]


def wall_band_v(start_idx, x, y0, y1, thickness=8.0):
    return [vline(start_idx, x, y0, y1), vline(start_idx + 1, x + thickness, y0, y1)]


def rect_room(start_idx, x0, y0, x1, y1, thickness=8.0):
    return (
        wall_band_h(start_idx, x0, x1, y0, thickness)
        + wall_band_h(start_idx + 2, x0, x1, y1 - thickness, thickness)
        + wall_band_v(start_idx + 4, x0, y0, y1, thickness)
        + wall_band_v(start_idx + 6, x1 - thickness, y0, y1, thickness)
    )


def door_candidate(bbox, confidence=0.67):
    return Candidate(
        candidate_id="door_0000",
        entity_type="door",
        bbox=bbox,
        confidence=confidence,
        evidence={"method": "door_assembly", "assembly_type": "single_line_leaf"},
    )


def text_span(text, bbox):
    return TextSpan(
        text=text, bbox=bbox, font="Helvetica", size=10.0, color=0,
        block_no=0, line_no=0,
    )


def rooms_for(paths, doors=(), windows=(), text_spans=()):
    network = detect_wall_network(paths, list(text_spans))
    return detect_rooms(
        network, list(doors), list(windows), PAGE_W, PAGE_H, list(text_spans)
    )


class TestClosedRooms(unittest.TestCase):
    def test_single_rect_room(self):
        rooms = rooms_for(rect_room(0, 100, 100, 400, 300))
        self.assertEqual(len(rooms), 1)
        room = rooms[0]
        self.assertEqual(room.entity_type, "room")
        # Free space inside the inner faces (108..392 x 108..292) shrunk by
        # the 1.5px line barrier + rounding: (110..390) x (110..290).
        self.assertAlmostEqual(room.evidence["area_px2"], 280 * 180, delta=800)
        x0, y0, x1, y1 = room.bbox
        self.assertAlmostEqual(x0, 110.0, delta=2.0)
        self.assertAlmostEqual(y1, 290.0, delta=2.0)
        # Closed polygon: first point == last point, at least 4 corners
        poly = room.evidence["polygon"]
        self.assertGreaterEqual(len(poly), 5)
        self.assertEqual(poly[0], poly[-1])
        self.assertEqual(room.evidence["wall_segment_count"], 4)
        self.assertGreaterEqual(room.evidence["wall_contact"], 0.99)

    def test_two_adjacent_rooms_share_wall(self):
        paths = rect_room(0, 100, 100, 600, 400) + wall_band_v(8, 340, 100, 400)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2)
        left, right = sorted(rooms, key=lambda r: r.bbox[0])
        # Divider band spans x 340..348; each room stops at its inner face.
        self.assertAlmostEqual(left.bbox[2], 338.0, delta=2.0)
        self.assertAlmostEqual(right.bbox[0], 350.0, delta=2.0)

    def _quad_box(self, idx, x0, y0, x1, y1, **kw):
        # PyMuPDF quad point order: (ul, ur, ll, lr).
        return path(idx, [(x0, y0), (x1, y0), (x0, y1), (x1, y1)],
                    item_type="qu", **kw)

    def _hatch_h(self, start_idx, x0, x1, y0, y1, pitch=6.0):
        # 45-degree hatch strokes filling a horizontal band (short obliques
        # spanning the band, as CAD exports draw a new-wall infill).
        out = []
        h = y1 - y0
        x = x0
        i = start_idx
        while x + h <= x1:
            out.append(path(i, [(x, y1), (x + h, y0)], stroke_width=0.25))
            x += pitch
            i += 1
        return out

    def test_hatched_stroked_quad_divider_splits_room(self):
        # A wall segment drawn as one closed rectangle (the PDF `re`/`qu`
        # operator, unfilled) with hatch inside — s03's window infill, a
        # 1.5px `qu` outline 83x33px hatched at 0.25px. Its long edges are
        # virtual WEAK faces: they pair only on the material between them.
        paths = rect_room(0, 100, 100, 600, 500)
        paths += wall_band_h(8, 100, 350, 300)               # left half: faces
        paths.append(self._quad_box(10, 350, 300, 592, 308))  # right half: quad
        paths += self._hatch_h(11, 350, 592, 300, 308)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2)
        top, bottom = sorted(rooms, key=lambda r: r.bbox[1])
        self.assertAlmostEqual(top.bbox[3], 298.0, delta=2.0)
        self.assertAlmostEqual(bottom.bbox[1], 310.0, delta=2.0)

    def test_hollow_stroked_quad_is_not_a_wall(self):
        # The same box with NOTHING between its edges — a door leaf (5x90px
        # `re` on s17/s20) or a fixture outline — must not split the room.
        # No door candidate is passed, so it is the material gate, not the
        # open-leaf exclusion, that keeps the leaf out of the network.
        paths = rect_room(0, 100, 100, 600, 500)
        paths += wall_band_h(8, 100, 350, 300)
        paths.append(self._quad_box(10, 350, 300, 592, 308))
        self.assertEqual(len(rooms_for(paths)), 1)
        # A leaf standing open across the room, hinged on the divider: it
        # must contribute no wall segment at all (the room count alone
        # would not prove that — the leaf reaches no enclosing wall).
        paths.append(self._quad_box(20, 200, 308, 205, 398))
        network = detect_wall_network(paths, [])
        self.assertFalse(
            any(20 in seg.face_path_indices for seg in network.segments)
        )
        self.assertEqual(len(rooms_for(paths)), 1)

    def test_unhatched_furniture_quad_is_not_a_room(self):
        # A bed / bath drawn as a stroked rectangle inside the room: no
        # material, no faces with barrier rights — the room stays whole.
        paths = rect_room(0, 100, 100, 600, 500)
        paths.append(self._quad_box(10, 200, 200, 300, 400))   # 100x200 bed
        paths.append(self._quad_box(11, 400, 200, 430, 300))   # 30x100 tray
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].evidence["area_px2"], 480 * 380, delta=1200)

    def test_hairline_hatched_partition_splits_room(self):
        # New partition walls are often drawn in the joinery pen (0.45px)
        # with hatch/blocking between the faces; the material-backed weak
        # pair must bound rooms like any stroked wall.
        divider = [
            vline(100, 340, 100, 400, stroke_width=0.45),
            vline(101, 354, 100, 400, stroke_width=0.45),
        ]
        idx = 102
        for y in range(108, 380, 20):
            divider.append(
                path(idx, [(341, y + 12), (353, y)], stroke_width=0.3)
            )
            idx += 1
        paths = rect_room(0, 100, 100, 600, 400) + divider
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2)
        left, right = sorted(rooms, key=lambda r: r.bbox[0])
        self.assertAlmostEqual(left.bbox[2], 338.0, delta=2.0)
        self.assertAlmostEqual(right.bbox[0], 356.0, delta=2.0)

    def test_hairline_partition_without_material_does_not_split(self):
        # The same pair with nothing between the faces is fixture linework
        # (wardrobe edges, counter fronts) and must stay room-interior ink.
        paths = rect_room(0, 100, 100, 600, 400) + [
            vline(100, 340, 100, 400, stroke_width=0.45),
            vline(101, 354, 100, 400, stroke_width=0.45),
        ]
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)

    def _hairline_hatched_band_h(self, start_idx, x0, x1, y, thickness=14.0):
        # s02's partition convention: two joinery-pen faces with hatch
        # between them (the material-backed weak pair).
        prims = [
            hline(start_idx, x0, x1, y, stroke_width=0.45),
            hline(start_idx + 1, x0, x1, y + thickness, stroke_width=0.45),
        ]
        idx = start_idx + 2
        for x in range(int(x0) + 4, int(x1) - int(thickness) - 4, 8):
            prims.append(path(
                idx, [(x, y + thickness - 1), (x + thickness - 2, y + 1)],
                stroke_width=0.3,
            ))
            idx += 1
        return prims

    def test_joinery_front_collinear_with_hatched_bands_does_not_fence(self):
        # s02's "coats" cupboard: a built-in wardrobe recessed off the HALL,
        # closed on three sides by real walls and drawn OPEN to the hall
        # along its front — a 3px pair of joinery-pen lines with nothing
        # between them, collinear with the top faces of the hatched
        # partitions either side (the merge chains them into one 500px
        # face that pairs over only its two ends). The paired ends seal
        # through their segments; the plain run between them bounds no
        # material and must not fence the cupboard out of the hall.
        paths = rect_room(0, 100, 100, 600, 500)
        paths += self._hairline_hatched_band_h(20, 100, 200, 300)     # left band
        paths += self._hairline_hatched_band_h(60, 500, 600, 300)     # right band
        # Cupboard box: strong side and back walls, joinery front on top.
        paths += wall_band_v(100, 192, 300, 400)
        paths += wall_band_v(102, 500, 300, 400)
        paths += wall_band_h(104, 192, 508, 392)
        paths += [
            hline(110, 200, 500, 300, stroke_width=0.45),
            hline(111, 200, 500, 303, stroke_width=0.45),
        ]
        rooms = rooms_for(paths)
        # Hall (with the cupboard pocket) + the space below the bands.
        self.assertEqual(len(rooms), 2)
        hall = min(rooms, key=lambda r: r.bbox[1])
        self.assertAlmostEqual(hall.bbox[3], 390.0, delta=2.0)   # reaches the cupboard back
        self.assertAlmostEqual(hall.bbox[1], 110.0, delta=2.0)

    def test_sliding_threshold_collinear_with_hatched_bands_still_seals(self):
        # Same geometry with a confident sliding door standing on the front
        # line (s02 GD5: a 120px panel in a 200px structural opening, the
        # hairline track drawn across the whole opening): the line is the
        # door's in-plane evidence and keeps its run to the jambs, so the
        # pocket stays a room of its own.
        paths = rect_room(0, 100, 100, 600, 500)
        paths += self._hairline_hatched_band_h(20, 100, 200, 300)
        paths += self._hairline_hatched_band_h(60, 500, 600, 300)
        paths += wall_band_v(100, 192, 300, 400)
        paths += wall_band_v(102, 500, 300, 400)
        paths += wall_band_h(104, 192, 508, 392)
        paths += [
            hline(110, 200, 500, 300, stroke_width=0.45),
            hline(111, 200, 500, 303, stroke_width=0.45),
        ]
        door = door_candidate((300, 298, 420, 306), confidence=0.65)
        door.evidence["assembly_type"] = "sliding"
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 3)

    def test_non_closing_linework_yields_no_room(self):
        # U-shape (3 walls) + an unrelated floating wall: the open side merges
        # the interior with the page-border component.
        paths = (
            wall_band_h(0, 100, 400, 100)
            + wall_band_v(2, 100, 100, 300)
            + wall_band_v(4, 392, 100, 300)
            + wall_band_h(6, 500, 700, 500)
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 0)


class TestOpeningSeals(unittest.TestCase):
    def gapped_room(self):
        """Rect room with a 45px doorway gap in the top wall (240..285)."""
        return (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 285, 400, 100)
            + wall_band_h(4, 100, 400, 292)
            + wall_band_v(6, 100, 100, 300)
            + wall_band_v(8, 392, 100, 300)
        )

    def test_door_gap_sealed(self):
        door = door_candidate((238, 96, 290, 155))
        rooms = rooms_for(self.gapped_room(), doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].evidence["door_openings"], 1)
        # Door-connected rooms get the boost
        self.assertGreater(rooms[0].confidence, 0.80)

    def test_same_gap_without_door_stays_open(self):
        # The 45px doorway is far wider than what morphological closing seals.
        self.assertGreater(45.0, 2 * ROOM_GAP_CLOSE_PX)
        rooms = rooms_for(self.gapped_room())
        self.assertEqual(len(rooms), 0)

    def test_window_gap_sealed(self):
        window = Candidate(
            candidate_id="window_0000",
            entity_type="window",
            bbox=(240, 98, 285, 112),
            confidence=0.62,
            evidence={},
        )
        rooms = rooms_for(self.gapped_room(), windows=[window])
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].evidence["window_openings"], 1)

    def test_door_swing_area_stays_in_room(self):
        # The door bbox covers the swing — room floor. The room polygon must
        # run across the opening (wall-plane plug), not notch around the
        # bbox, and the open-leaf line inside the bbox must not slot it.
        paths = self.gapped_room() + [vline(10, 288, 110, 152)]
        door = door_candidate((238, 96, 290, 155))
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        # Notching the bbox out would cost ~2340 px2 (52x45 inside the inner
        # faces); the full interior is ~50400 px2 plus the doorway recess.
        self.assertGreaterEqual(rooms[0].evidence["area_px2"], 50400)

    def test_white_leaf_ring_does_not_notch_swing(self):
        # The open leaf drawn as a white-filled rectangle (the Vectorworks
        # filled-polygon signature) inside the swing bbox: it must not be
        # accepted as hollow wall — anchored by its own door's bbox — and
        # notch the swing area out of the room.
        door = door_candidate((238, 96, 290, 155))
        baseline = rooms_for(self.gapped_room(), doors=[door])
        paths = self.gapped_room() + fill_ring(
            10, 283, 110, 289, 152, fill=(1.0, 1.0, 1.0)
        )
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )

    def test_door_short_of_jamb_still_seals(self):
        # 70px doorway (240..310); the swing bbox stops 20px short of the
        # right jamb — wider than morphological closing bridges. The plug
        # spans the interrupted wall run, so the room must not leak through
        # the clearance strip and merge with the page-border component.
        paths = (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 310, 400, 100)
            + wall_band_h(4, 100, 400, 292)
            + wall_band_v(6, 100, 100, 300)
            + wall_band_v(8, 392, 100, 300)
        )
        door = door_candidate((238, 96, 290, 155))
        self.assertEqual(len(rooms_for(paths)), 0)  # unsealed: leaks out
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)

    def test_door_separates_adjacent_rooms(self):
        # Divider wall with a 45px doorway; the door swings into the left
        # room. The plug must split the free space into two rooms at the
        # divider plane, each seeing the door on its boundary.
        paths = (
            rect_room(0, 100, 100, 600, 400)
            + wall_band_v(8, 340, 100, 220)
            + wall_band_v(10, 340, 265, 400)
        )
        door = door_candidate((296, 218, 348, 270))
        self.assertEqual(len(rooms_for(paths)), 1)  # no door: one fused space
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 2)
        left, right = sorted(rooms, key=lambda r: r.bbox[0])
        # Left room keeps the swing area and reaches the plug at the divider;
        # the right room still starts at its inner face.
        self.assertAlmostEqual(left.bbox[2], 343.0, delta=2.0)
        self.assertAlmostEqual(right.bbox[0], 350.0, delta=2.0)
        self.assertEqual(left.evidence["door_openings"], 1)
        self.assertEqual(right.evidence["door_openings"], 1)

    def test_drawn_through_opening_keeps_swing_in_room(self):
        # Working-drawing style: the wall faces run straight through the
        # opening (existing-opening sill / closed sliding panel), so the
        # rooms are already separated there. The door bbox hanging off the
        # divider must not become a barrier that notches the swing area out
        # of its room.
        paths = (
            rect_room(0, 100, 100, 600, 500)
            + wall_band_h(8, 100, 600, 240)  # continuous divider, no gap
        )
        door = door_candidate((296, 248, 348, 300))  # swings into lower room
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 2)
        upper, lower = sorted(rooms, key=lambda r: r.bbox[1])
        # Lower interior is ~480x240 (~115200 px2) minus barrier margins; a
        # bbox-carved notch would cost ~2700 px2 more.
        self.assertGreaterEqual(lower.evidence["area_px2"], 114500)
        self.assertEqual(lower.evidence["door_openings"], 1)

    def test_small_drafting_gap_closes(self):
        # 10px collinear gap (< 2 * ROOM_GAP_CLOSE_PX) seals morphologically
        # without a door; confidence stays below the door-sealed case.
        paths = (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 250, 400, 100)
            + wall_band_h(4, 100, 400, 292)
            + wall_band_v(6, 100, 100, 300)
            + wall_band_v(8, 392, 100, 300)
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].evidence["door_openings"], 0)
        self.assertLess(rooms[0].confidence, 0.80)


class TestComponentFiltering(unittest.TestCase):
    def test_page_frame_dropped(self):
        # Sheet frame around a one-room plan: the frame interior exceeds the
        # page-area fraction and is dropped; the room survives.
        paths = rect_room(0, 20, 20, 980, 780) + rect_room(8, 100, 100, 400, 300)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].bbox[0], 110.0, delta=2.0)

    def test_sliver_face_dropped(self):
        # Interior 400x7 vanishes between the dilated wall solids.
        paths = rect_room(0, 100, 100, 508, 115, thickness=8.0)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 0)

    def test_tiny_face_dropped(self):
        # Free interior ~28x20 px < ROOM_MIN_AREA_PX2
        paths = rect_room(0, 100, 100, 148, 140, thickness=8.0)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 0)


def fill_ring(start_idx, x0, y0, x1, y1, fill, stroke_width=0.0):
    """Closed filled rectangle exploded into 4 chained `l` items (the
    Vectorworks filled-polygon signature)."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    return [
        path(start_idx + i, [pts[i], pts[i + 1]],
             stroke_width=stroke_width, fill=fill)
        for i in range(4)
    ]


class TestBarrierAllowlist(unittest.TestCase):
    """Room-interior ink (masks, tile grids, furniture) must not chop rooms;
    classified wall material (hollow white bands, wall-fill rings) must."""

    FULL_INTERIOR = 280 * 180  # rect_room(_, 100, 100, 400, 300) free space

    def test_white_text_mask_does_not_chop_room(self):
        # Unstroked white box mid-room (a wall-type tag mask): its parallel
        # edges must not pair into a fake wall nor become thin barriers.
        paths = rect_room(0, 100, 100, 400, 300) + fill_ring(
            8, 180, 190, 300, 210, fill=(1.0, 1.0, 1.0)
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertGreaterEqual(
            rooms[0].evidence["area_px2"], self.FULL_INTERIOR - 1500
        )

    def test_light_pen_grid_does_not_chop_room(self):
        # Floor-tile grid penned at 0.6 vs 1.5 walls: below the stroke gate,
        # unpaired (50px spacing > wall thickness cap) — not a barrier.
        paths = rect_room(0, 100, 100, 400, 300)
        idx = 8
        for x in (150, 200, 250, 300, 350):
            paths.append(vline(idx, x, 108, 292, stroke_width=0.6))
            idx += 1
        for y in (150, 200, 250):
            paths.append(hline(idx, 108, 392, y, stroke_width=0.6))
            idx += 1
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertGreaterEqual(
            rooms[0].evidence["area_px2"], self.FULL_INTERIOR - 1500
        )

    def test_furniture_fill_blocks_do_not_bound_rooms(self):
        # Two compact rings of one fill class (cabinet blocks) rate as
        # furniture: no faces, no pseudo-rooms, no chop.
        paths = (
            rect_room(0, 100, 100, 400, 300)
            + fill_ring(8, 108, 108, 208, 168, fill=(0.9, 0.9, 0.9))
            + fill_ring(12, 240, 200, 340, 260, fill=(0.9, 0.9, 0.9))
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertGreaterEqual(
            rooms[0].evidence["area_px2"], self.FULL_INTERIOR - 1500
        )

    def test_hollow_white_wall_band_seals_room(self):
        # Three stroked walls + a white (hollow) band as the fourth side:
        # the textless band touches the wall network, so its polygon seals.
        paths = (
            wall_band_h(0, 100, 400, 100)
            + wall_band_h(2, 100, 400, 292)
            + wall_band_v(4, 100, 100, 300)
            + fill_ring(6, 392, 100, 400, 300, fill=(1.0, 1.0, 1.0))
            # Filler wall so the network passes the min-segment gate.
            + wall_band_h(10, 600, 800, 600)
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].bbox[2], 390.0, delta=2.5)

    def test_wall_fill_band_rings_seal_room(self):
        # Walls drawn purely as unstroked gray filled bands (no strokes at
        # all): the fill class rates as wall, faces pair, polygons seal.
        paths = (
            fill_ring(0, 100, 100, 400, 108, fill=(0.7, 0.7, 0.7))
            + fill_ring(4, 100, 292, 400, 300, fill=(0.7, 0.7, 0.7))
            + fill_ring(8, 100, 100, 108, 300, fill=(0.7, 0.7, 0.7))
            + fill_ring(12, 392, 100, 400, 300, fill=(0.7, 0.7, 0.7))
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)

    def test_arrowhead_markers_do_not_chop_room(self):
        # Leader/dimension arrowheads mid-room, drawn in the wall pen: tiny
        # filled triangles are marker rings, not wall area or faces, so the
        # room keeps its full free space.
        walls = (
            fill_ring(0, 100, 100, 400, 108, fill=(0.7, 0.7, 0.7))
            + fill_ring(4, 100, 292, 400, 300, fill=(0.7, 0.7, 0.7))
            + fill_ring(8, 100, 100, 108, 300, fill=(0.7, 0.7, 0.7))
            + fill_ring(12, 392, 100, 400, 300, fill=(0.7, 0.7, 0.7))
        )
        arrows = []
        for i, (tx, ty) in enumerate([(200.0, 200.0), (300.0, 150.0)]):
            pts = [(tx, ty), (tx + 13.0, ty - 3.0), (tx + 10.0, ty + 8.0), (tx, ty)]
            arrows += [
                path(16 + 3 * i + j, [pts[j], pts[j + 1]],
                     stroke_width=0.0, fill=(0.7, 0.7, 0.7))
                for j in range(3)
            ]
        base_area = rooms_for(walls)[0].evidence["area_px2"]
        rooms = rooms_for(walls + arrows)
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].evidence["area_px2"], base_area, delta=20.0)


class TestTriangulatedFillRings(unittest.TestCase):
    """Exporters triangulate fills: a wall band arrives as two right
    triangles sharing the diagonal. Each ring is buffered on its own, and a
    mitre join at a triangle's acute vertex runs out to the mitre limit —
    a 10px spike past the band end — so the room edge beside a jamb nib or
    band end stood 8-10px off the wall (s03 corridor room_0014)."""

    WALLS = (
        fill_ring(0, 100, 100, 400, 108, fill=(0.7, 0.7, 0.7))
        + fill_ring(4, 100, 292, 400, 300, fill=(0.7, 0.7, 0.7))
        + fill_ring(8, 100, 100, 108, 300, fill=(0.7, 0.7, 0.7))
        + fill_ring(12, 392, 100, 400, 300, fill=(0.7, 0.7, 0.7))
    )

    @staticmethod
    def _tri(start_idx, pts, fill=(0.7, 0.7, 0.7)):
        pts = list(pts) + [pts[0]]
        return [
            path(start_idx + i, [pts[i], pts[i + 1]], stroke_width=0.0, fill=fill)
            for i in range(3)
        ]

    def test_triangle_pair_band_matches_rectangle_exactly(self):
        # Seam-sharing triangles are unioned into their band before
        # dilation, so the room outline is the same as for one rectangle
        # ring — no bevel residue at the acute vertices.
        rect = fill_ring(16, 108, 196, 300, 208, fill=(0.7, 0.7, 0.7))
        tris = (
            self._tri(16, [(108, 196), (300, 196), (300, 208)])
            + self._tri(19, [(300, 208), (108, 208), (108, 196)])
        )
        ref = ShapelyPolygon(rooms_for(self.WALLS + rect)[0].evidence["polygon"])
        got = ShapelyPolygon(rooms_for(self.WALLS + tris)[0].evidence["polygon"])
        self.assertLessEqual(ref.symmetric_difference(got).area, 1.0)

    def test_triangle_pair_acute_spike_is_capped(self):
        # A 12px partition band 108..300 x 196..208 ending mid-room, once as
        # one rectangle ring, once as the exporter's two triangles.
        rect = fill_ring(16, 108, 196, 300, 208, fill=(0.7, 0.7, 0.7))
        tris = (
            self._tri(16, [(108, 196), (300, 196), (300, 208)])
            # Second ring starts off the first ring's close point so the
            # chainer opens a new ring (as the exporter's winding does).
            + self._tri(19, [(300, 208), (108, 208), (108, 196)])
        )
        ref = rooms_for(self.WALLS + rect)
        got = rooms_for(self.WALLS + tris)
        self.assertEqual(len(ref), 1)
        self.assertEqual(len(got), 1)
        room = ShapelyPolygon(got[0].evidence["polygon"])
        # Band end at x=300 + 2px barrier standoff: 305 is room floor.
        # The spike sits at the acute vertex (300, 208): an 8x3.5px tab to
        # x=310 before the fix. 306,209 is room floor; 305,198 too.
        self.assertTrue(room.contains(ShapelyPoint(306.0, 209.0)))
        self.assertTrue(room.contains(ShapelyPoint(305.0, 198.0)))
        self.assertAlmostEqual(
            got[0].evidence["area_px2"], ref[0].evidence["area_px2"], delta=20.0
        )


def stroked_ring_path(start_idx, pts, stroke_width=1.5):
    """Closed stroked (fill-less) polyline exploded into chained `l` items."""
    pts = list(pts) + [pts[0]]
    return [
        path(start_idx + i, [pts[i], pts[i + 1]], stroke_width=stroke_width)
        for i in range(len(pts) - 1)
    ]


class TestJambNibRings(unittest.TestCase):
    """s03 corridor room_0014: the jamb nibs beside door_0007/door_0019 are
    closed STROKED wall-pen outlines (12x5px L-shapes with a door-stop
    rebate, paths 15805-15816) whose every edge is under the 11px face
    floor, so they were no barrier at all and the corridor edge bulged
    over them to the door plug (x=3749 instead of the nib face at 3740)."""

    def _plan(self, nibs=True, where="jamb"):
        # 500x300 room split by a vertical band at x=340 with a doorway
        # y 214..286; the door swings into the right room.
        paths = rect_room(0, 100, 100, 600, 400)
        paths += wall_band_v(8, 340, 100, 214) + wall_band_v(10, 340, 286, 400)
        if nibs:
            if where == "jamb":
                top = [(340, 214), (356, 214), (356, 220), (348, 220), (348, 217), (340, 217)]
                bot = [(340, 286), (356, 286), (356, 280), (348, 280), (348, 283), (340, 283)]
            else:  # a same-sized stroked box floating mid-room
                top = [(200, 214), (216, 214), (216, 220), (208, 220), (208, 217), (200, 217)]
                bot = [(200, 286), (216, 286), (216, 280), (208, 280), (208, 283), (200, 283)]
            paths += stroked_ring_path(20, top) + stroked_ring_path(26, bot)
        # Jamb blocks 16px deep (a nib one wall-thickness wide beside the
        # 8px band); the door bbox starts at their far face.
        door = door_candidate((356.0, 220.0, 416.0, 280.0), confidence=0.9)
        return paths, [door]

    def test_nibs_at_the_jambs_are_wall(self):
        paths, doors = self._plan()
        rooms = rooms_for(paths, doors=doors)
        self.assertEqual(len(rooms), 2)
        polys = [ShapelyPolygon(r.evidence["polygon"]) for r in rooms]
        # Inside the top nib, outside the door plug: wall, in no room.
        # (the nib's 16px band-side edge is itself a face; probe the
        # sub-floor rebate side of the L, 5px inside it)
        self.assertFalse(any(p.contains(ShapelyPoint(344.0, 219.0)) for p in polys))
        self.assertFalse(any(p.contains(ShapelyPoint(344.0, 281.0)) for p in polys))
        # The doorway itself stays room floor up to the plug.
        self.assertTrue(any(p.contains(ShapelyPoint(344.0, 250.0)) for p in polys))

    def test_floating_boxes_are_not_wall(self):
        base, doors = self._plan(nibs=False)
        boxed, _ = self._plan(where="floating")
        a = sum(r.evidence["area_px2"] for r in rooms_for(base, doors=doors))
        b = sum(r.evidence["area_px2"] for r in rooms_for(boxed, doors=doors))
        self.assertAlmostEqual(a, b, delta=5.0)


class TestPhantomDoorSeals(unittest.TestCase):
    """Fallback-tier door candidates (label boxes, symbol clutter — kept
    only for Gemini arbitration) must not reshape room outlines: no
    dilated-bbox seal, no free-space plugs, no white-wall anchoring. Only
    plug profiles that carry their own evidence survive."""

    def gapped_room(self):
        return (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 285, 400, 100)
            + wall_band_h(4, 100, 400, 292)
            + wall_band_v(6, 100, 100, 300)
            + wall_band_v(8, 392, 100, 300)
        )

    def test_fallback_interrupted_plug_still_seals(self):
        # The sliding-door carve-out: a fallback-tier door whose bbox spans
        # a genuine gap between two jambs (interrupted wall run) keeps its
        # plug — the doorway signature is its own evidence.
        door = door_candidate((238, 96, 290, 155), confidence=0.35)
        rooms = rooms_for(self.gapped_room(), doors=[door])
        self.assertEqual(len(rooms), 1)

    def test_text_covered_door_box_never_seals(self):
        # The same bbox mostly covered by the text written inside it is an
        # annotation tag ("WALL TYPE 1" boxes detect as leaf rectangles),
        # not a door — even the interrupted profile is denied, so the gap
        # stays open and the room leaks out.
        door = door_candidate((238, 96, 290, 155), confidence=0.35)
        span = text_span("WALL TYPE 1", (240, 100, 290, 150))
        rooms = rooms_for(self.gapped_room(), doors=[door], text_spans=[span])
        self.assertEqual(len(rooms), 0)

    def test_fallback_interrupted_plug_still_splits_rooms(self):
        # Divider with a doorway gap between two rooms: the fallback-tier
        # door's interrupted-run plug must still split the rooms at the
        # divider plane (real low-confidence sliding doors live here).
        paths = (
            rect_room(0, 100, 100, 600, 400)
            + wall_band_v(8, 340, 100, 220)
            + wall_band_v(10, 340, 265, 400)
        )
        door = door_candidate((296, 218, 348, 270), confidence=0.35)
        self.assertEqual(len(rooms_for(paths)), 1)
        self.assertEqual(len(rooms_for(paths, doors=[door])), 2)

    def test_fallback_door_in_open_space_is_inert(self):
        # Mid-room phantom (a tag box detected as a leaf): no wall material
        # anywhere near, so no plugs qualify and the dilated-bbox fallback
        # is denied — the room polygon must be identical to the no-door run.
        paths = rect_room(0, 100, 100, 400, 300)
        baseline = rooms_for(paths)
        door = door_candidate((200, 180, 260, 240), confidence=0.35)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )
        self.assertEqual(rooms[0].evidence["door_openings"], 0)

    def test_fallback_door_hugging_wall_no_notch(self):
        # Phantom alongside a wall band (railings, jamb clutter): its edge
        # passes full-cover by mere PROXIMITY to the band, but the plug band
        # hangs in free space — below ROOM_PLUG_IN_WALL_FRAC overlap it is
        # dropped instead of notching the room outline.
        paths = rect_room(0, 100, 100, 400, 300)
        baseline = rooms_for(paths)
        door = door_candidate((112, 150, 126, 250), confidence=0.35)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )
        self.assertEqual(rooms[0].evidence["door_openings"], 0)

    def test_fallback_door_does_not_erase_joinery_ring(self):
        # Door detection often fires ON white joinery rectangles (wardrobe
        # dividers) — the open-leaf exclusion must not extend to
        # fallback-tier doors, or the partition ring would vanish and the
        # rooms it separates merge into one.
        paths = rect_room(0, 100, 100, 600, 400) + fill_ring(
            8, 340, 100, 352, 400, fill=(1.0, 1.0, 1.0)
        )
        door = door_candidate((338, 98, 354, 402), confidence=0.35)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 2)

    def test_fallback_door_does_not_anchor_white_ring(self):
        # A phantom door detected on a white fixture symbol must not anchor
        # the symbol into the hollow-wall acceptance: pre-gate, the ring
        # became wall material, merged with the nearby band under gap
        # closing, and carved a bay out of the room. The symbol's ends stay
        # 26px from the top/bottom bands — past ROOM_OPENING_SEAL_PX +
        # ROOM_PLUG_HALF_WIDTH_PX (20): a fallback door's edge running 6px
        # along the side wall whose tails TOUCH both end walls reads as an
        # interrupted run, the one profile the fallback tier keeps, and
        # plugs an 11px bay off the room (the fixture sat at exactly 20px
        # before the seal moved 12 -> 15).
        paths = rect_room(0, 100, 100, 400, 300) + fill_ring(
            8, 116, 136, 128, 264, fill=(1.0, 1.0, 1.0)
        )
        baseline = rooms_for(rect_room(0, 100, 100, 400, 300))
        door = door_candidate((116, 136, 128, 264), confidence=0.35)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )


class TestBboxSealFloor(unittest.TestCase):
    """The dilated-bbox fallback is the one seal with no evidence of its
    own, so it requires a door the pipeline itself stands behind
    (ROOM_BBOX_SEAL_MIN_CONFIDENCE, the offline floor). Doors in the
    0.40-0.55 band keep every plug path — those qualify on drawn wall
    material — but may not stamp free space (the 5-1133 bath-fixture FP:
    single_line_leaf on a toilet symbol at 0.52, no_wall, plugs found no
    wall plane, and the dilated bbox notched the FAMILY BATH room edge)."""

    def test_mid_tier_door_in_open_space_is_inert(self):
        # Replicates door_0011: a 0.52 phantom in open room space, no wall
        # material anywhere near its bbox. No plug qualifies and the bbox
        # fallback is denied — the room must be identical to the no-door run.
        paths = rect_room(0, 100, 100, 400, 300)
        baseline = rooms_for(paths)
        door = door_candidate((200, 180, 260, 240), confidence=0.52)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )

    def test_mid_tier_door_at_room_edge_no_notch(self):
        # Replicates the FAMILY BATH notch: the phantom's bbox reaches the
        # room's wall band but no edge lies ON a wall plane (no interrupted
        # run, no drawn-through plane), so no plug qualifies — and without
        # the bbox fallback the room outline runs straight along the wall
        # face instead of detouring around the stamp.
        paths = rect_room(0, 100, 100, 400, 300)
        baseline = rooms_for(paths)
        door = door_candidate((330, 180, 420, 240), confidence=0.52)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )

    def test_mid_tier_interrupted_plug_still_seals(self):
        # A real doorway between jambs keeps sealing below the floor: the
        # interrupted-run profile is the plug's own evidence.
        paths = (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 285, 400, 100)
            + wall_band_h(4, 100, 400, 292)
            + wall_band_v(6, 100, 100, 300)
            + wall_band_v(8, 392, 100, 300)
        )
        door = door_candidate((238, 96, 290, 155), confidence=0.52)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)

    def test_floor_tier_door_keeps_bbox_fallback(self):
        # The identical geometry at the offline floor keeps the dilated-bbox
        # safety net: the heuristics stand behind this door, so the stamp
        # (merged with the wall band it overlaps) notches the free space.
        paths = rect_room(0, 100, 100, 400, 300)
        baseline = rooms_for(paths)
        door = door_candidate((330, 180, 420, 240), confidence=0.55)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertLess(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"] - 2000,
        )


class TestGardenDoorSeals(unittest.TestCase):
    """Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto."""

    BBOX = (200.0, 100.0, 282.0, 265.0)  # 82x165, like 5-1133 door 0121

    def test_anchor_window_caps_at_jamb_scale(self):
        # The 165px doorway edge is anchored only by jamb-scale stubs at its
        # corners (a 45-degree bay jamb hugs the edge line for ~20px). The
        # legacy n//4 quarter dilutes that to 5/12 and fails the 0.5 gate;
        # the capped window must qualify the true wall-plane edge.
        from shapely.geometry import box as sbox
        from shapely.ops import unary_union
        jambs = unary_union([
            sbox(192, 80, 208, 98),    # stub at the top-left corner
            sbox(192, 267, 208, 285),  # stub at the bottom-left corner
        ])
        plugs = _door_plugs(self.BBOX, jambs)
        self.assertEqual(len(plugs), 1)
        plug, kind, edge_idx = plugs[0]
        self.assertEqual(kind, "interrupted")
        self.assertEqual(edge_idx, 2)
        x0, _, x1, _ = plug.bounds
        self.assertAlmostEqual((x0 + x1) / 2.0, 200.0, delta=1.0)  # left edge

    def test_open_leaf_edges_garden_vs_french(self):
        def cand(layout, leaf_a, leaf_b):
            return Candidate("door_0001", "door", self.BBOX, 0.65, evidence={
                "swing_layout": layout,
                "leaf_bbox_a": leaf_a, "leaf_bbox_b": leaf_b,
            })
        garden = cand(
            "garden",
            (200.1, 100.0, 282.0, 101.0),  # parked along the top edge
            (200.1, 264.0, 282.0, 265.0),  # parked along the bottom edge
        )
        self.assertEqual(_open_leaf_edges(garden), frozenset({0, 1}))
        # French pair: collinear leaves drawn closed IN the wall plane along
        # the top edge — that edge must stay plug-eligible.
        french = cand(
            "french",
            (200.0, 100.0, 240.0, 101.0),
            (242.0, 100.0, 282.0, 101.0),
        )
        self.assertEqual(_open_leaf_edges(french), frozenset())

    def test_open_leaf_edges_veto_tip_chord_edge(self):
        # floor-plans door_0016: leaves parked along the LEFT/RIGHT edges,
        # doorway at the top. The merged opening_line joins the leaves' open
        # tips along the BOTTOM edge — the swing-extent side, room floor. It
        # must be vetoed too: it anchored on the jamb walls continuing past
        # the doorway, pattern-matched an interrupted run, and its plug held
        # the bedroom outline 5px short of the doorway.
        bbox = (1001.0, 403.8, 1110.7, 458.3)
        garden = Candidate("door_0016", "door", bbox, 0.65, evidence={
            "swing_layout": "garden",
            "leaf_bbox_a": (1109.7, 403.8, 1110.7, 458.3),
            "leaf_bbox_b": (1001.0, 403.8, 1002.0, 458.3),
            "opening_line": [(1110.2, 458.2), (1001.5, 458.2)],
        })
        self.assertEqual(_open_leaf_edges(garden), frozenset({1, 2, 3}))
        # A diagonal garden pair's chord lies along no axis edge — no veto
        # beyond the leaf edges themselves.
        diagonal = Candidate("door_0121", "door", bbox, 0.65, evidence={
            "swing_layout": "garden",
            "leaf_bbox_a": (1109.7, 403.8, 1110.7, 458.3),
            "leaf_bbox_b": (1001.0, 403.8, 1002.0, 458.3),
            "opening_line": [(1001.5, 403.8), (1110.2, 458.2)],
        })
        self.assertEqual(_open_leaf_edges(diagonal), frozenset({2, 3}))

    def test_skip_edges_suppresses_qualified_plug(self):
        # A full wall band hugs the top edge: it qualifies as a drawn-through
        # plane — unless the door's own leaf evidence vetoes the edge.
        from shapely.geometry import box as sbox
        band = sbox(188, 92, 294, 108)
        plugs = _door_plugs(self.BBOX, band)
        self.assertEqual([k for _, k, _ in plugs], ["full"])
        self.assertEqual(_door_plugs(self.BBOX, band, skip_edges=frozenset({0})), [])


class TestPlugSealReach(unittest.TestCase):
    """ROOM_OPENING_SEAL_PX stays 12px (102mm at 1:50). The W-gate census
    (2026-09-04) proposed 15 — the jamb gap beyond a swing bbox at true
    scales is s01 8px = 125mm (1:92.2), s17 8px = 135mm, s05/s07 6px at
    f=0.5 = 102mm — and iteration 2 tried it; iteration 3 step 2 measured
    what broke: s15's corridor door lost its doorway plug at 14 because a
    dash-row barrier crossing the doorway plane flips the mid-window count
    2/10 -> 3/11 with the sampling phase (bbox stamp, two swings fenced),
    and s02 was notched around a section-marker bar at 15 because a
    fallback door's full-cover plug tails overshoot the bar by 4.8px and
    pinch the neck to the wall (see ROOM_OPENING_SEAL_PX). Measured on this
    fixture, an interrupted plug seals a jamb gap of at most SEAL - 1px (11
    at 12, 13 at 14, 15 at 15): an 11px gap must seal, 13 must not."""

    BBOX = (200.0, 100.0, 270.0, 150.0)   # top edge y=100 lies in the band

    @staticmethod
    def _jambs(gap):
        return unary_union([
            shapely_box(100, 96, 200 - gap, 104),
            shapely_box(270 + gap, 96, 370, 104),
        ])

    def test_jamb_11px_past_the_bbox_is_sealed(self):
        plugs = _door_plugs(self.BBOX, self._jambs(11.0))
        self.assertIn(("interrupted", 0), [(k, e) for _, k, e in plugs])

    def test_jamb_13px_past_the_bbox_is_not(self):
        plugs = _door_plugs(self.BBOX, self._jambs(13.0))
        self.assertNotIn(0, [e for _, _, e in plugs])


class TestPlugTailTrim(unittest.TestCase):
    """Plug extensions end at their supporting material; slide ends veto.

    Geometry mirrors floor-plans door_0011 (vertical pocket slider) and
    door_0002 (swing whose top-left tail floated 8.7px off material and
    notched room_0005 beside the jamb).
    """

    BBOX = (200.0, 100.0, 282.0, 265.0)  # same doorway as TestGardenDoorSeals

    def test_sliding_end_edges_vetoed(self):
        def cand(bbox, assembly="sliding"):
            return Candidate("door_0011", "door", bbox, 0.65, evidence={
                "assembly_type": assembly,
            })
        # Vertical slider (floor-plans door_0011): short ends top/bottom.
        self.assertEqual(
            _sliding_end_edges(cand((387.5, 1018.3, 398.3, 1117.8))),
            frozenset({0, 1}),
        )
        # Horizontal leaf_pair (5-1133 door_0013): short ends left/right.
        self.assertEqual(
            _sliding_end_edges(cand((1191.2, 834.7, 1333.3, 841.2))),
            frozenset({2, 3}),
        )
        # Near-square bbox (diagonal wall) and non-sliding assemblies veto
        # nothing.
        self.assertEqual(
            _sliding_end_edges(cand((100.0, 100.0, 140.0, 150.0))),
            frozenset(),
        )
        self.assertEqual(
            _sliding_end_edges(
                cand((387.5, 1018.3, 398.3, 1117.8), assembly="single")
            ),
            frozenset(),
        )

    def test_tail_trimmed_to_jamb_material(self):
        # Jamb stubs set back from the extended edge ends: the plug must
        # still reach INTO both jambs but not carry the floating tail
        # remainder past them into free space.
        jambs = unary_union([
            shapely_box(196, 92, 210, 108),
            shapely_box(272, 92, 286, 108),
        ])
        plugs = _door_plugs(self.BBOX, jambs)
        self.assertEqual([(k, e) for _, k, e in plugs], [("interrupted", 0)])
        x0, _, x1, _ = plugs[0][0].bounds
        self.assertGreater(x0, 190.0)   # untrimmed tail started at 188
        self.assertLess(x0, 197.0)      # still overlaps the left jamb
        self.assertLess(x1, 292.0)      # untrimmed tail ended at 294
        self.assertGreater(x1, 285.0)   # still overlaps the right jamb

    def test_plug_fits_the_jamb_cross_section(self):
        # s03 door_0003: the hinge-edge bbox side lies ON the inner face of
        # a 6px band (dilated material x 298..308 here, faces 300/306), so
        # the plug centred on the edge with the 5px half-width stood 3px
        # proud of the wall's own 2px standoff — a step at every doorway
        # that simplify redrew as a slant across the whole room edge. The
        # plug must take the jamb's cross-section: room side flush with
        # the dilated material (298), never 295.
        jambs = unary_union([
            shapely_box(298, 50, 308, 100),
            shapely_box(298, 150, 308, 200),
        ])
        plugs = _door_plugs((250.0, 100.0, 300.0, 150.0), jambs)
        self.assertEqual([(k, e) for _, k, e in plugs], [("interrupted", 3)])
        x0, y0, x1, y1 = plugs[0][0].bounds
        self.assertAlmostEqual(x0, 298.0, delta=0.3)
        self.assertLessEqual(x1, 305.0 + 0.3)
        self.assertLess(y0, 100.0)      # tails still reach into both jambs
        self.assertGreater(y1, 150.0)

    def test_tail_kept_on_through_material(self):
        # A band running the full extended edge (ROOM_OPENING_SEAL_PX = 12
        # past each bbox end) supports both tails: the plug keeps its whole
        # reach (the drawn-through-plane case).
        band = shapely_box(188, 92, 294, 108)
        plugs = _door_plugs(self.BBOX, band)
        self.assertEqual([k for _, k, _ in plugs], ["full"])
        x0, _, x1, _ = plugs[0][0].bounds
        self.assertAlmostEqual(x0, 188.0, delta=0.1)
        self.assertAlmostEqual(x1, 294.0, delta=0.1)


class TestJambNib(unittest.TestCase):
    """A doorway whose jamb is a one-wall-thickness nib (s03 door_0018)."""

    def layout(self, nib_len):
        # Two rooms side by side above a divider band (y 300..308); the
        # vertical wall x 392..400 between them is interrupted by a doorway
        # from y=200 down to the nib, and the nib runs from there to the
        # divider. The door hinges bottom-right: leaf lying along the
        # bottom edge, arc from the top jamb to the leaf tip at the left.
        nib_top = 300 - nib_len
        paths = (
            rect_room(0, 100, 100, 700, 500)
            + wall_band_h(8, 100, 700, 300)
            + wall_band_v(10, 392, 100, 200)
            + wall_band_v(12, 392, nib_top, 300)
        )
        door = Candidate(
            candidate_id="door_0000", entity_type="door",
            bbox=(304.0, 200.0, 392.0, nib_top), confidence=0.95,
            evidence={
                "method": "door_assembly", "assembly_type": "single",
                "opening_line": [[392.0, 200.0], [304.0, nib_top - 2.0]],
                "leaf_bbox": [304.0, nib_top - 5.0, 392.0, nib_top],
            },
        )
        return paths, door

    def test_one_thickness_nib_anchors_doorway_plug(self):
        # 11.5px nib: one wall thickness (100mm at 1:50 is 11.8px). Its
        # faces must reach the wall network so the doorway edge's plug
        # anchors on it; otherwise no plug qualifies and the dilated-bbox
        # fallback fences the swing square out of the room.
        paths, door = self.layout(11.5)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 3)
        top_left = min(
            (r for r in rooms if r.bbox[1] < 250), key=lambda r: r.bbox[0])
        poly = ShapelyPolygon(top_left.evidence["polygon"])
        self.assertTrue(poly.contains(ShapelyPoint(348.0, 244.0)))
        self.assertAlmostEqual(top_left.bbox[2], 392.0, delta=3.0)


class TestSwingHingePlugRestriction(unittest.TestCase):
    """Single swing doors: plugs live on the hinge edges, one wall plane.

    Geometry mirrors floor-plans door_0000 (the main entrance): leaf drawn
    open along the LEFT edge, hinge at the bottom-left corner, arc chord
    from the leaf tip (top-left) to the closed position (bottom-right) —
    wall plane = bottom edge. The corridor walls crossing near the top
    edge's extended ends made the top edge pattern-match the interrupted
    doorway signature, fencing the swing square out of the hallway.
    """

    BBOX = (458.0, 1336.5, 511.75, 1391.75)

    @staticmethod
    def cand(**evidence_overrides):
        evidence = {
            "method": "door_assembly",
            "assembly_type": "single_line_leaf",
            "leaf_bbox": [458.0, 1336.5, 459.75, 1386.0],
            "opening_line": [[459.25, 1336.5], [511.75, 1391.75]],
        }
        evidence.update(evidence_overrides)
        return Candidate(
            candidate_id="door_0000", entity_type="door",
            bbox=TestSwingHingePlugRestriction.BBOX,
            confidence=0.67, evidence=evidence,
        )

    def test_hinge_edges_from_leaf_and_chord(self):
        # Hinge at (458, 1386) = bottom-left corner -> bottom + left edges.
        self.assertEqual(_swing_hinge_edges(self.cand()), frozenset({1, 2}))

    def test_hinge_underivable_returns_none(self):
        self.assertIsNone(_swing_hinge_edges(self.cand(opening_line=None)))
        self.assertIsNone(_swing_hinge_edges(self.cand(leaf_bbox=None)))
        # Chord touching the leaf at both ends (or neither) is ambiguous.
        self.assertIsNone(_swing_hinge_edges(
            self.cand(opening_line=[[459.25, 1336.5], [459.25, 1386.0]])
        ))
        # A half-open leaf whose hinge floats inside the bbox derives nothing.
        self.assertIsNone(_swing_hinge_edges(
            self.cand(leaf_bbox=[470.0, 1345.0, 495.0, 1370.0],
                      opening_line=[[495.0, 1370.0], [511.75, 1391.75]])
        ))
        # Non-swing assemblies never veto.
        self.assertIsNone(_swing_hinge_edges(self.cand(assembly_type="sliding")))

    def test_far_edge_plug_dropped(self):
        # Top edge (0) bounds the swing square: its plug is phantom whatever
        # profile it matched. Bottom (1) is a hinge edge and stays.
        from shapely.geometry import box as sbox
        top = sbox(446, 1331.5, 523.75, 1341.5)
        bottom = sbox(446, 1386.75, 523.75, 1396.75)
        plugs = [(top, "interrupted", 0), (bottom, "interrupted", 1)]
        self.assertEqual(_restrict_swing_plugs(self.cand(), plugs),
                         [(bottom, "interrupted", 1)])

    def test_interrupted_hinge_plug_beats_full_sibling(self):
        # The left edge hugged the parallel divider band 5px away and came
        # out "full"; the bottom edge carries the doorway signature. One
        # wall plane only: the full sibling drops.
        from shapely.geometry import box as sbox
        bottom = sbox(446, 1386.75, 523.75, 1396.75)
        left = sbox(453, 1324.5, 463, 1403.75)
        plugs = [(bottom, "interrupted", 1), (left, "full", 2)]
        self.assertEqual(_restrict_swing_plugs(self.cand(), plugs),
                         [(bottom, "interrupted", 1)])

    def test_full_hinge_plugs_kept_without_interrupted_sibling(self):
        # A closed-drawn door in a drawn-through wall: full plugs on hinge
        # edges are the only seal evidence and must survive.
        from shapely.geometry import box as sbox
        bottom = sbox(446, 1386.75, 523.75, 1396.75)
        plugs = [(bottom, "full", 1)]
        self.assertEqual(_restrict_swing_plugs(self.cand(), plugs), plugs)

    def test_far_edge_only_plugs_survive_as_guard(self):
        # If every qualifying plug lies on a far edge, the restriction would
        # push the door to the dilated-bbox fallback — keep the status quo.
        from shapely.geometry import box as sbox
        top = sbox(446, 1331.5, 523.75, 1341.5)
        plugs = [(top, "interrupted", 0)]
        self.assertEqual(_restrict_swing_plugs(self.cand(), plugs), plugs)


class TestDiagonalWindowSeal(unittest.TestCase):
    def test_straight_window_seals_full_bbox(self):
        c = Candidate("window_0000", "window", (240, 98, 285, 112), 0.62,
                      evidence={"orientation": "horizontal"})
        self.assertAlmostEqual(_window_seal(c).area, 45 * 14, delta=1.0)

    def test_diagonal_window_seals_band_not_square(self):
        # 45-degree bay window: square axis bbox. The seal must follow the
        # glazing diagonal instead of stamping the square into free space
        # (the square fenced terrace pockets into phantom rooms on 5-1133).
        from shapely.geometry import Point
        c = Candidate("window_0001", "window", (100, 100, 158, 158), 0.62,
                      evidence={"orientation": "diagonal",
                                "glazing_angle_deg": 45.0,
                                "opening_width_px": 70.0})
        seal = _window_seal(c)
        self.assertLess(seal.area, 0.45 * 58 * 58)
        self.assertTrue(seal.contains(Point(129, 129)))       # on the band
        self.assertFalse(seal.contains(Point(150, 108)))      # off-band corner
        # An ascending glazing angle picks the other diagonal.
        c2 = Candidate("window_0002", "window", (100, 100, 158, 158), 0.62,
                       evidence={"orientation": "diagonal",
                                 "glazing_angle_deg": 135.0,
                                 "opening_width_px": 70.0})
        seal2 = _window_seal(c2)
        self.assertTrue(seal2.contains(Point(129, 129)))
        self.assertFalse(seal2.contains(Point(108, 108)))


class TestBlindWindowPocket(unittest.TestCase):
    def window(self, bbox=(120, 98, 160, 112)):
        return Candidate("window_0000", "window", bbox, 0.62, evidence={})

    def test_window_only_pocket_dropped(self):
        # A closet-scale space whose ONLY opening is a window cannot be
        # entered: it is the exterior side of that window (terrace pocket,
        # lightwell), not a room. The same space stays a room while blind
        # AND windowless — interior rooms legitimately lose their door to a
        # missed detection.
        paths = rect_room(0, 100, 100, 180, 180)  # ~60x60 = 3.6k px2 inside
        self.assertEqual(len(rooms_for(paths)), 1)
        self.assertEqual(len(rooms_for(paths, windows=[self.window()])), 0)

    def test_window_only_room_above_cap_kept(self):
        paths = rect_room(0, 100, 100, 400, 300)  # ~50k px2 inside
        rooms = rooms_for(paths, windows=[self.window()])
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].evidence["window_openings"], 1)


class TestWindowExteriorSide(unittest.TestCase):
    """A window is a wall opening between inside and outside. When the space
    on one side of it is a door-bearing room and the space on the other side
    has no door at all, the door-less side is the exterior — a lower roof,
    terrace or lightwell the room looks out over (measured on s03: the
    ground-floor roof drawn as a striped field above the PROPOSED BEDROOM,
    fenced by the roof outline, came out as a 133k px2 door-less "room" on
    the far side of the bedroom's window)."""

    def stacked(self):
        # Two rooms sharing the y=292..300 band: A above (100..292), B below
        # (300..500). B has a doorway in its bottom wall.
        return (
            rect_room(0, 100, 100, 400, 500)
            + wall_band_h(8, 100, 400, 292)
        )

    def door_b(self):
        # Doorway gap in B's bottom band (492..500) sealed by a door.
        return door_candidate((238, 445, 290, 504))

    def window_shared(self):
        return Candidate("window_0000", "window", (200, 293, 300, 299), 0.62,
                         evidence={})

    @staticmethod
    def _drop_h(paths, ys):
        return [
            p for p in paths
            if not (p.points[0][1] == p.points[1][1] and p.points[0][1] in ys)
        ]

    def paths_with_gap(self):
        # B's bottom band (492..500) rebuilt with a 45px doorway at 240..285.
        paths = self._drop_h(self.stacked(), (492.0, 500.0))
        return paths + wall_band_h(20, 100, 240, 492) + wall_band_h(22, 285, 400, 492)

    def test_doorless_side_of_window_is_dropped(self):
        rooms = rooms_for(self.paths_with_gap(), doors=[self.door_b()],
                          windows=[self.window_shared()])
        self.assertEqual(len(rooms), 1)
        self.assertGreater(rooms[0].bbox[1], 295.0)  # B survives, A dropped

    def test_without_window_both_rooms_stay(self):
        rooms = rooms_for(self.paths_with_gap(), doors=[self.door_b()])
        self.assertEqual(len(rooms), 2)

    def test_doors_on_both_sides_keep_both(self):
        # An internal window (borrowed light) between two entered rooms.
        paths = self._drop_h(self.paths_with_gap(), (100.0, 108.0)) + \
            wall_band_h(24, 100, 240, 100) + wall_band_h(26, 285, 400, 100)
        door_a = door_candidate((238, 96, 290, 155))
        door_a.candidate_id = "door_0001"
        rooms = rooms_for(paths, doors=[self.door_b(), door_a],
                          windows=[self.window_shared()])
        self.assertEqual(len(rooms), 2)


class TestSwingRecessDissolution(unittest.TestCase):
    def test_recess_between_plug_and_threshold_not_a_room(self):
        # Garden pair in a wall: the outer wall plane plugs (interrupted
        # run) and the drawn threshold line fences the swing recess inside
        # the door bbox into its own free-space component — door floor, not
        # a room (measured on floor-plans' 1800mm garden pairs). It must
        # dissolve while the interior room survives.
        paths = (
            wall_band_h(0, 100, 240, 100)
            + wall_band_h(2, 360, 500, 100)
            + wall_band_h(4, 100, 500, 392)
            + wall_band_v(6, 100, 100, 400)
            + wall_band_v(8, 492, 100, 400)
            + [hline(10, 230, 370, 160)]  # threshold, wider than the door zone
        )
        door = door_candidate((240, 96, 360, 160))
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertGreater(rooms[0].evidence["area_px2"], 90000)


class TestEmptyNetwork(unittest.TestCase):
    def test_no_network_no_rooms(self):
        self.assertEqual(detect_rooms(None, [], [], PAGE_W, PAGE_H), [])

    def test_sparse_network_no_rooms(self):
        rooms = rooms_for(wall_band_h(0, 100, 300, 100))
        self.assertEqual(rooms, [])


class TestAnnotationPenBarriers(unittest.TestCase):
    """Lone thin barriers require a wall pen. On color-coded drawings the
    annotation pens match (or beat) the wall WIDTH — floor-plans pens
    furniture red and dimensions blue at 1.5 over magenta walls at 1.0 —
    and a red worktop line fenced a 34px phantom "room" against the
    utility's south wall. A pen whose color barely pairs did not draw the
    walls and gets no lone-barrier rights."""

    def test_annotation_pen_line_does_not_split_room(self):
        paths = rect_room(0, 100, 100, 400, 300)
        red = hline(50, 108, 392, 200, color=(1.0, 0.0, 0.0))
        rooms = rooms_for(paths + [red])
        self.assertEqual(len(rooms), 1)

    def test_wall_pen_line_still_splits_room(self):
        paths = rect_room(0, 100, 100, 400, 300)
        rooms = rooms_for(paths + [hline(50, 108, 392, 200)])
        self.assertEqual(len(rooms), 2)

    def test_furniture_pen_pair_does_not_partition(self):
        # A furniture rectangle's opposite edges pair at wall-like spacing
        # in the SAME annotation pen (floor-plans room_0012: the bed's
        # pillow rectangles beside the wall, red-red pairs at th 24/32px),
        # so the pen-compatible pairing gate cannot catch them. The
        # resulting segment must not become a barrier solid — the room
        # keeps its full extent up to the wall face instead of notching
        # around the furniture.
        paths = rect_room(0, 100, 100, 400, 300)
        pillow = [
            vline(50, 360, 150, 250, color=(1.0, 0.0, 0.0)),
            vline(51, 380, 150, 250, color=(1.0, 0.0, 0.0)),
        ]
        rooms = rooms_for(paths + pillow)
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].bbox[2], 390.0, delta=2.0)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"], 280 * 180, delta=800
        )

    def test_wall_pen_pair_still_partitions(self):
        paths = rect_room(0, 100, 100, 400, 300)
        divider = [vline(50, 300, 100, 300), vline(51, 320, 100, 300)]
        rooms = rooms_for(paths + divider)
        self.assertEqual(len(rooms), 2)


class TestPlugPlaneEvidence(unittest.TestCase):
    """Interrupted-run plugs need jambs that REACH the plug band and a mid
    that is empty IN the opening plane (ROOM_PLUG_MID_NEAR_PX)."""

    def test_perpendicular_cap_off_plane_keeps_doorway_interrupted(self):
        # A perpendicular wall ending a few px below the doorway plane
        # (floor-plans door_0008: the bathroom east wall under the bedroom
        # doorway) must not fill the interrupted-run middle at the loose
        # hug and cost the true doorway edge its plug.
        material = unary_union([
            shapely_box(100, 200, 205, 210),
            shapely_box(255, 200, 360, 210),
            shapely_box(225, 216, 235, 300),
        ])
        plugs = _door_plugs((205, 150, 255, 210), material)
        self.assertIn(("interrupted", 1), {(k, e) for _, k, e in plugs})

    def test_parallel_band_beyond_reach_is_full_not_interrupted(self):
        # A band hugging the whole edge from 6px away anchors both ends at
        # the loose hug but never reaches the plug band: an annotation or
        # fixture box beside a wall, not a doorway. Classified full, so a
        # fallback-tier door's plug still dies on the in-wall test instead
        # of stamping a trusted interrupted seal into free space.
        material = shapely_box(193, 140, 199, 280)
        plugs = _door_plugs((205, 150, 255, 270), material)
        edge2 = [kind for _, kind, e in plugs if e == 2]
        self.assertEqual(edge2, ["full"])


def stair_arrowhead(start_idx, tip, base_y, half=3.0):
    """Filled arrowhead triangle (a marker ring) pointing down at `tip`."""
    tx, ty = tip
    pts = [(tx - half, base_y), (tx + half, base_y), (tx, ty), (tx - half, base_y)]
    return [
        path(start_idx + i, [pts[i], pts[i + 1]], stroke_width=0.0,
             fill=(0.0, 0.0, 0.0))
        for i in range(3)
    ]


class TestStairFurniture(unittest.TestCase):
    """Stairs are furniture to the room stage: a room polygon runs to the
    enclosing walls straight through the flight (RICS GIA takeoff). None of
    a stair's ink — treads, stringers, cut line, direction arrow, winders,
    balustrade lines — may qualify as a barrier, whatever pen it is drawn
    in (s03 draws the stair in the 1.5px wall pen)."""

    def _one_room_containing(self, paths, points, text_spans=()):
        rooms = rooms_for(paths, text_spans=text_spans)
        self.assertEqual(len(rooms), 1, [r.bbox for r in rooms])
        poly = ShapelyPolygon(rooms[0].evidence["polygon"])
        for pt in points:
            self.assertTrue(
                poly.contains(ShapelyPoint(*pt)), f"{pt} fenced out of the room"
            )
        return rooms[0], poly

    def _flight(self):
        # Four treads at 15px pitch spanning from the top wall face down to
        # a partition band, plus the section cut line crossing them (the
        # s03 first-floor stair beside room_0012).
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(4)]
        cut = [path(110, [(430, 120), (500, 190)])]
        partition = wall_band_h(120, 400, 592, 200)
        return treads + cut + partition

    def test_tread_flight_with_cut_line_does_not_bound_room(self):
        paths = rect_room(0, 100, 100, 600, 400) + self._flight()
        room, poly = self._one_room_containing(
            paths, [(447, 150), (462, 150), (477, 150), (492, 150)]
        )
        # The partition the flight lands on is still a wall.
        self.assertFalse(poly.contains(ShapelyPoint(500, 204)))

    def test_four_faces_without_crossing_stay_walls(self):
        # The same four parallel faces with nothing crossing them are a
        # cavity party wall (leaf/cavity/leaf at equal width): rooms split.
        treads = [vline(100 + i, 440 + 15 * i, 100, 400) for i in range(4)]
        rooms = rooms_for(rect_room(0, 100, 100, 600, 400) + treads)
        self.assertEqual(len(rooms), 2)

    def test_arrow_with_up_text_and_winders_do_not_bound_room(self):
        # s03 ground-floor stair: no tread lines at all — a full-height
        # stringer beside the flight, two winders fanning from the newel
        # corner, a direction arrow crossing the stringer into the flight
        # with an arrowhead, "UP" at its tail, and a landing edge line.
        stringer = [vline(100, 180, 108, 392)]
        winders = [
            path(101, [(180, 300), (108, 340)]),
            path(102, [(180, 300), (140, 392)]),
        ]
        landing_edge = [hline(103, 108, 180, 300)]
        arrow = [hline(104, 140, 240, 200), vline(105, 140, 200, 290)]
        head = stair_arrowhead(106, (140, 300), 290)
        text = [text_span("UP", (243, 194, 258, 206))]
        paths = rect_room(0, 100, 100, 600, 400) + stringer + winders + landing_edge + arrow + head
        self._one_room_containing(
            paths, [(150, 250), (150, 350), (300, 250)], text_spans=text
        )

    def test_leader_arrow_without_stair_text_keeps_walls(self):
        # A leader crossing a partition to point at something beyond it
        # is annotation, not a stair: the partition it crosses stays.
        partition = wall_band_v(100, 300, 100, 400)
        arrow = [hline(104, 400, 250, 200)]
        head = stair_arrowhead(106, (250, 200), 200)  # degenerate; use side head
        head = [
            path(106, [(250, 200), (256, 197)], stroke_width=0.0, fill=(0.0, 0.0, 0.0)),
            path(107, [(256, 197), (256, 203)], stroke_width=0.0, fill=(0.0, 0.0, 0.0)),
            path(108, [(256, 203), (250, 200)], stroke_width=0.0, fill=(0.0, 0.0, 0.0)),
        ]
        rooms = rooms_for(rect_room(0, 100, 100, 600, 400) + partition + arrow + head)
        self.assertEqual(len(rooms), 2)

    def test_cross_hatched_wall_stays_wall(self):
        # s20: a wall band filled with cross-hatch — two families of short
        # shallow-oblique (15deg) strokes at 12px pitch crossing each other — is a
        # "flight" by pitch, extent and crossing; hatch is excluded by
        # shape (short + oblique), and the wall faces beside it stay.
        # Faces drawn in short pieces (s20 draws walls between openings as
        # 50-70px lines), so a hatch-run zone can enclose a piece whole.
        band = [
            vline(100 + k, x, y, y + 50)
            for k, (x, y) in enumerate(
                (x, y) for x in (300, 336) for y in range(100, 400, 50)
            )
        ]
        idx = 120
        hatch = []
        for y in range(104, 390, 12):
            hatch.append(path(idx, [(300, y + 10), (336, y)], stroke_width=0.75))
            idx += 1
            hatch.append(path(idx, [(300, y - 4), (336, y + 6)], stroke_width=0.75))
            idx += 1
        rooms = rooms_for(rect_room(0, 100, 100, 600, 400) + band + hatch)
        self.assertEqual(len(rooms), 2)

    def test_multi_line_wall_crossed_by_annotation_stays_wall(self):
        # s17: a wall drawn as four parallel lines at leaf pitch, with a
        # short "to be removed" tick in another pen crossing one of them.
        # Neither an off-pen crosser nor lines 20x their pitch make a stair.
        lines = [vline(100 + i, 300 + 12 * i, 100, 400) for i in range(4)]
        tick = [hline(110, 306, 330, 250, color=(1.0, 0.5, 0.0))]
        rooms = rooms_for(rect_room(0, 100, 100, 600, 400) + lines + tick)
        self.assertEqual(len(rooms), 2)

    def test_end_cuts_outside_the_treads_do_not_bound_the_flight(self):
        # s17: a stairwell whose section cuts (shallow zigzag lines) lie one
        # pitch ABOVE the first tread and BELOW the last — touching and
        # crossing nothing — fenced the flight into its own "room" between
        # them. A same-pen chain within a pitch of a run end that spans the
        # flight is the cut, and stair ink.
        well = wall_band_v(100, 300, 100, 400) + wall_band_v(102, 400, 100, 400)
        treads = [hline(110 + i, 308, 400, 160 + 20 * i) for i in range(6)]
        arrow = [vline(120, 354, 150, 300)]
        top_cut = [path(121, [(308, 148), (350, 140)]), path(122, [(350, 140), (352, 146)]),
                   path(123, [(352, 146), (400, 138)])]
        bottom_cut = [path(124, [(308, 300), (400, 285)])]
        paths = rect_room(0, 100, 100, 600, 400) + well + treads + arrow + top_cut + bottom_cut
        rooms = rooms_for(paths)
        wells = [r for r in rooms if 300 < r.bbox[0] < 320]
        self.assertEqual(len(wells), 1, [r.bbox for r in rooms])
        poly = ShapelyPolygon(wells[0].evidence["polygon"])
        self.assertTrue(poly.contains(ShapelyPoint(354, 120)))   # above the top cut
        self.assertTrue(poly.contains(ShapelyPoint(354, 380)))   # below the bottom cut

    def test_flight_abutting_wall_keeps_that_wall(self):
        # The last tread sits one pitch off a wall face (s03 FF tread 1131 vs
        # face 355): the tread is stair ink, the wall face is not.
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(4)]
        cut = [path(110, [(430, 120), (500, 190)])]
        nosing = [hline(111, 430, 500, 200)]
        wall = wall_band_v(120, 500, 100, 400)
        paths = rect_room(0, 100, 100, 600, 400) + treads + cut + nosing + wall
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2)
        left = min(rooms, key=lambda r: r.bbox[0])
        poly = ShapelyPolygon(left.evidence["polygon"])
        self.assertTrue(poly.contains(ShapelyPoint(492, 150)))
        self.assertAlmostEqual(left.bbox[2], 498.0, delta=2.0)

    def test_collinear_piece_abutting_last_tread_does_not_unseat_it(self):
        # s03 FF (measured under the rejected strong-edge variant of
        # ab888ab): the last tread (path 1132, 48.5px) abutted end-to-end
        # the 17.7px short edge of a window-frame box on the same axis.
        # Fusing the two into one rung made a 66px envelope against 51px
        # siblings, the tread failed the end-tolerance test, dropped out of
        # the run and stayed a STRONG face that fenced the flight off the
        # landing. Members qualify on their OWN interval: the tread is
        # stair ink, the collinear piece is not.
        # The cut crosses the first three treads only (s03's cut 1350
        # spans x 1143-1161 of a flight ending at 1190), so the zone does
        # not reach the last tread and nothing rescues it if it drops.
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(4)]
        cut = [path(110, [(430, 120), (475, 165)])]
        partition = wall_band_h(120, 400, 592, 200)
        # An 18px same-pen piece continuing the last tread's line past the
        # partition it lands on (a frame edge, a skirting, a wall face).
        piece = [vline(111, 485, 200, 218)]
        paths = rect_room(0, 100, 100, 600, 400) + treads + cut + partition + piece
        room, poly = self._one_room_containing(
            paths, [(447, 150), (462, 150), (477, 150), (492, 150), (540, 150)]
        )
        self.assertFalse(poly.contains(ShapelyPoint(500, 204)))

    def test_cut_clipping_one_tread_mid_flight_is_evidence(self):
        # s03 1:50 plan, stair beside room_0017: a four-tread flight whose
        # zigzag break line clips only the FIRST tread — the tread stops
        # mid-flight ON the cut (61.5px against 97px siblings) and the cut
        # crosses nothing. Under the ">= 2 treads end on it" rule the run
        # had no evidence, the treads stayed strong lone barriers and the
        # stair foot came out as its own room. A tread stopping in the
        # interior of the flight on a long oblique same-pen line is a
        # clipped tread: walls stop at perpendicular jamb caps, and a hatch
        # stroke meets a face's end only at the band's corner.
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(1, 4)]
        treads.append(vline(100, 440, 150, 200))          # clipped
        cut = [path(110, [(448, 120), (421, 221)])]       # through (440,150)
        partition = wall_band_h(120, 400, 592, 200)
        paths = rect_room(0, 100, 100, 600, 400) + treads + cut + partition
        room, poly = self._one_room_containing(
            paths, [(462, 150), (477, 150), (492, 150), (447, 185)]
        )
        self.assertFalse(poly.contains(ShapelyPoint(500, 204)))

    def test_break_line_lower_half_across_the_zigzag_is_stair_ink(self):
        # s03 1:50 plan: the cut is a BREAK LINE — two collinear oblique
        # pieces joined by a zigzag jog (8.6/17/8.7px pieces, under the
        # face floor, so they are not faces). The upper half clips the
        # first tread and is stair ink; the lower half sits 11.6px past it
        # along the same line, outside the flight bbox, and stayed a strong
        # lone barrier notching the merged room. A same-pen oblique face
        # continuing a cut member collinearly across a jog is the cut.
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(1, 4)]
        treads.append(vline(100, 440, 150, 200))          # clipped
        upper = [path(110, [(452, 105), (436, 165)])]     # through (440,150)
        # jog pieces (too short to be faces) then the collinear lower half
        jog = [path(111, [(436, 165), (432, 163)]), path(112, [(432, 163), (434, 171)])]
        lower = [path(113, [(433, 176), (421, 221)])]     # 11px gap, same line
        partition = wall_band_h(120, 400, 592, 200)
        paths = rect_room(0, 100, 100, 600, 400) + treads + upper + jog + lower + partition
        room, poly = self._one_room_containing(
            paths, [(462, 150), (477, 150), (492, 150), (447, 185), (426, 188)]
        )
        self.assertFalse(poly.contains(ShapelyPoint(500, 204)))

    def test_oblique_line_at_a_face_corner_is_not_a_cut(self):
        # The same four parallel lines full-length, with a long oblique
        # same-pen line meeting the first line's END corner: a hatch stroke
        # or mitre at a wall end, not a section cut — the end lies at the
        # run's extent, not inside it. Cavity wall: rooms split.
        lines = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(4)]
        corner = [path(110, [(440, 108), (410, 200)])]
        partition = wall_band_h(120, 400, 592, 200)
        paths = rect_room(0, 100, 100, 600, 400) + lines + corner + partition
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2, [r.bbox for r in rooms])

    def test_tread_split_by_text_mask_qualifies_on_aggregate_length(self):
        # A tread cut in two by a text mask arrives as two touching
        # fragments, each under half the reference length. Their UNION
        # covers the reference, so the tread still qualifies (a per-
        # fragment length floor would drop it and re-fence the flight).
        treads = [vline(100 + i, 440 + 15 * i, 108, 200) for i in range(3)]
        treads += [vline(103, 485, 108, 150), vline(104, 485, 152, 200)]
        cut = [path(110, [(430, 120), (475, 165)])]
        partition = wall_band_h(120, 400, 592, 200)
        paths = rect_room(0, 100, 100, 600, 400) + treads + cut + partition
        self._one_room_containing(
            paths, [(447, 150), (462, 150), (477, 150), (492, 150), (540, 150)]
        )


def triangulated_fill_band_v(start_idx, x0, y0, x1, y1, fill=(0.5, 0.5, 0.5)):
    """A filled wall band exported as two triangles (CAD fill triangulation).

    Each triangle is its own chained ring, so the shared diagonal arrives
    twice — once per triangle — as an invisible (w0, filled) `l` item.
    """
    tri_a = [(x1, y0), (x0, y0), (x1, y1), (x1, y0)]
    tri_b = [(x0, y0), (x1, y1), (x0, y1), (x0, y0)]
    out = []
    idx = start_idx
    for tri in (tri_a, tri_b):
        for a, b in zip(tri, tri[1:]):
            out.append(path(idx, [a, b], stroke_width=0.0, fill=fill))
            idx += 1
    return out


class TestFillSeams(unittest.TestCase):
    def _right_edge_xs(self, room):
        poly = room.evidence["polygon"]
        top = [x for x, y in poly if y < 130 and x > 400]
        bottom = [x for x, y in poly if y > 370 and x > 400]
        return max(top), max(bottom)

    def test_triangulated_fill_band_keeps_room_edge_straight(self):
        # s03 bedroom: the right wall band is a grey fill exported as two
        # triangles; the diagonal seam (18px over 300px, ~3.4 deg) lies
        # within WALL_PARALLEL_ANGLE_TOL of the band's own face and paired
        # with it into a slanted centerline whose solid cut the room 17px
        # short at one end (measured on s03 room_0000: 818 vs 835).
        paths = (
            wall_band_h(0, 100, 610, 100)
            + wall_band_h(2, 100, 610, 392)
            + wall_band_v(4, 100, 100, 400)
            + triangulated_fill_band_v(6, 592, 100, 610, 400)
        )
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 1)
        top_x, bottom_x = self._right_edge_xs(rooms[0])
        self.assertAlmostEqual(top_x, bottom_x, delta=1.5)
        self.assertAlmostEqual(rooms[0].bbox[2], 590.0, delta=2.0)


class TestWallRecess(unittest.TestCase):
    """A chimney breast / pier drawn as a closed box on the room side of a
    wall band, its back open to the band: the pocket between the wall's
    outer line and the breast front is wall material, not a room."""

    def _plan(self):
        # 16px walls; the top band's inner face is interrupted by a 160px
        # breast whose front lies 44px (2.75 bands) below the outer line —
        # past WALL_MAX_THICKNESS_PX (36; 44 keeps clear of the 40 the W-gate
        # census tried), so the front cannot pair with the outer line as a
        # thick wall and the pocket comes out as free space.
        return (
            [hline(0, 100.0, 500.0, 100.0),
             hline(1, 100.0, 180.0, 116.0), hline(2, 340.0, 500.0, 116.0),
             vline(3, 180.0, 116.0, 144.0), vline(4, 340.0, 116.0, 144.0),
             hline(5, 180.0, 340.0, 144.0)]
            + wall_band_h(6, 100.0, 500.0, 384.0, thickness=16.0)
            + wall_band_v(8, 100.0, 100.0, 400.0, thickness=16.0)
            + wall_band_v(10, 484.0, 100.0, 400.0, thickness=16.0)
        )

    def test_breast_pocket_is_not_a_room(self):
        # s11/s16: door-less, textless pockets 31-42px deep in a 17.6px band
        # (depth 1.75-2.4x the band) came out as 0.63 rooms; the pocket fills
        # the collinear gap between the band's two segments and its back
        # lies on the wall's outer line.
        rooms = rooms_for(self._plan())
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].bbox[1], 118.0, delta=2.0)

    def test_labelled_recess_stays(self):
        # s02's "coats" cupboard sits in the same signature but is labelled:
        # a space the draughtsperson named is a space.
        rooms = rooms_for(
            self._plan(),
            text_spans=[text_span("coats", (240.0, 112.0, 280.0, 124.0))],
        )
        self.assertEqual(len(rooms), 2)


class TestBandPocket(unittest.TestCase):
    """A window reveal in a cavity wall (s17 rooms 0015/0034): the wall is
    drawn as four lines — outer face, outer leaf's inner face, inner leaf's
    outer face, inner face (11.75 / 12 / 13.25px leaf-cavity-leaf, 37px in
    all, over the then-36px WALL_MAX_THICKNESS_PX) — with hatch only at the
    jambs. At the window the two middle lines stop, the glazing line runs
    mid-leaf in the continuous outer leaf, and the reveal between the outer
    leaf's inner face and the wall's inner face comes out as a 21px-deep
    free-space pocket that survives the 8px opening. It lies INSIDE the
    wall's thickness — both long edges on wall faces at wall spacing — so it
    is wall material, never floor.

    The fixture is drawn 44px in all (11.75 / 19 / 13.25) with a 32px
    reveal — clear of the plain cap whatever the W-gate recalibration
    settles on (40 was tried on 2026-09-04: s17's 37px outer and inner
    faces then paired as one plain band and its reveals were solid before
    the room stage saw them; reverted to 36 for the fixtures that band
    admits)."""

    OUTER, OUTER_IN, INNER_OUT, INNER = 100.0, 111.75, 130.75, 144.0
    REVEAL = 280.0   # the window runs from here to the wall's end — the
                     # inner pair resumes on ONE side only, as beside s17
                     # room_0015 (the next window's reveal adjoins it), so the
                     # collinear-gap recess rule cannot see the pocket

    def _cavity_plan(self):
        x0, x1 = 100.0, 600.0
        r0 = self.REVEAL
        paths = [
            hline(0, x0, x1, self.OUTER),                          # outer face
            hline(1, x0, x1, self.OUTER_IN),                       # outer leaf, inner face
            hline(2, x0, r0, self.INNER_OUT),                      # inner leaf, outer face,
                                                                   #   stops at the reveal
            hline(3, x0, x1, self.INNER),                          # inner face / board line
            hline(4, r0, x1 - 8.0, 105.25),                        # glazing, mid outer leaf
                                                                   #   (s17's 5.25px offset)
        ]
        idx = 5
        # Cavity-closer hatch at the jambs only — a cavity wall carries no
        # hatch along its run (s17: 0 diagonal marks in the 37px band).
        for xj in (r0 - 10.0, x1 - 24.0):
            for k in range(2):
                xs = xj + 4.0 * k
                paths.append(path(idx, [(xs, self.INNER), (xs + 8.0, self.OUTER_IN)],
                                  stroke_width=0.25))
                idx += 1
        paths += wall_band_v(idx, x0, self.OUTER, 400.0)
        idx += 2
        paths += wall_band_v(idx, x1 - 8.0, self.OUTER, 400.0)
        idx += 2
        paths += wall_band_h(idx, x0, x1, 392.0)
        return paths

    def _pocket(self, rooms):
        return [r for r in rooms if r.bbox[3] < self.INNER]

    def test_reveal_pocket_is_not_a_room(self):
        rooms = rooms_for(self._cavity_plan())
        self.assertEqual(len(rooms), 1, [r.bbox for r in rooms])
        self.assertAlmostEqual(rooms[0].bbox[1], self.INNER + 2.0, delta=2.0)

    def test_rejected_door_plug_does_not_enter_the_pocket(self):
        # s17 door_0039: a 0.48 single_line_leaf candidate — under the
        # offline door floor, so the pipeline rejects it — lies IN the
        # reveal; its full-cover plugs hug the reveal's faces and their
        # tails fence the pocket beside it, which then counts a door. A door
        # the pipeline rejects is not an entrance: the pocket stays wall.
        door = door_candidate((492.0, 118.0, 580.0, 126.0), confidence=0.48)
        rooms = rooms_for(self._cavity_plan(), doors=[door])
        self.assertEqual(len(rooms), 1, [r.bbox for r in rooms])

    def test_labelled_pocket_stays(self):
        # A named space is a space whatever its shape.
        rooms = rooms_for(
            self._cavity_plan(),
            text_spans=[text_span("DUCT", (360.0, 118.0, 400.0, 130.0))],
        )
        self.assertEqual(len(self._pocket(rooms)), 1, [r.bbox for r in rooms])

    def test_space_wider_than_a_wall_stays(self):
        # The true class: a door-less, window-less, unlabelled strip WIDER
        # than WALL_MAX_THICKNESS_PX between two wall faces is floor (s11
        # room_0018, a 19px-wide storage cupboard at f=0.5 — 21.75px face
        # spacing against the scaled 18px cap — is confirmed).
        paths = rect_room(0, 100, 100, 600, 500) + wall_band_h(8, 100, 600, 160)
        rooms = rooms_for(paths)
        self.assertEqual(len(rooms), 2, [r.bbox for r in rooms])
        strip = min(rooms, key=lambda r: r.bbox[1])
        self.assertAlmostEqual(strip.bbox[3] - strip.bbox[1], 48.0, delta=2.0)


class TestRejectedDoorIsNotAnEntrance(unittest.TestCase):
    """detect_rooms consumes candidates before the offline floor, so a door
    the pipeline itself rejects (< ROOM_BBOX_SEAL_MIN_CONFIDENCE, the floor's
    mirror) can still seal through an evidence-bearing plug — and used to
    count as an entrance, vetoing the blind-window and wall-recess drops
    (s17 room_0034: a 0.35 arc_fallback sliver's full-cover plugs)."""

    def closet(self):
        # 100..196 box, ~4.5k px2 inside, a 20px doorway gap in the top band.
        # The synthetic door carries no hinge evidence, so every bbox edge is
        # plug-eligible; its swing-side edge ends must stay farther than
        # ROOM_OPENING_SEAL_PX + ROOM_PLUG_HALF_WIDTH_PX (20px) from the side
        # walls, or that edge reads as an interrupted run and plugs the
        # closet in two (28px clearance here).
        return (
            wall_band_h(0, 100, 138, 100) + wall_band_h(2, 158, 196, 100)
            + wall_band_h(4, 100, 196, 172)
            + wall_band_v(6, 100, 100, 180) + wall_band_v(8, 188, 100, 180)
        )

    def window(self):
        return Candidate("window_0000", "window", (128, 171, 168, 181), 0.62,
                         evidence={})

    def test_rejected_door_does_not_veto_the_blind_window_drop(self):
        # The door bbox's wall-plane edge sits mid-band, so its interrupted-
        # run plug lies within ROOM_CONTACT_TOL_PX of the room boundary and
        # is counted — as s17's rejected candidates were.
        door = door_candidate((136, 104, 160, 148), confidence=0.48)
        rooms = rooms_for(self.closet(), doors=[door], windows=[self.window()])
        self.assertEqual(len(rooms), 0, [r.evidence for r in rooms])

    def test_entered_closet_with_window_stays(self):
        door = door_candidate((136, 104, 160, 148), confidence=0.67)
        rooms = rooms_for(self.closet(), doors=[door], windows=[self.window()])
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].evidence["door_openings"], 1)


if __name__ == "__main__":
    unittest.main()


def stroked_box_path(idx, x0, y0, x1, y1, stroke_width=0.56):
    """A lone stroked, unfilled `qu` item — a joinery-pen box."""
    # PyMuPDF quad order (ul, ur, ll, lr), as extract_paths emits it.
    return path(idx, [(x0, y0), (x1, y0), (x0, y1), (x1, y1)], item_type="qu",
                stroke_width=stroke_width, color=(0.5, 0.5, 0.5))


class TestDoorLiningRings(unittest.TestCase):
    """s04 BATHROOM 01 (room_0000, door_0002): the structural opening is
    112px wide for a 90px leaf, and the 22px difference is two DOOR-LINING
    blocks drawn as stroked `qu` rings (12.4x14.5px, 0.56px grey pen on a
    detail layer, paths 950/951) sitting IN the wall band between each jamb
    face and the leaf bbox edge. Penned under the wall gate they were no
    material, the 12px plug extension reached 1px into the jamb (anchor
    coverage 3/7 = 0.43 < 0.5), no plug qualified, and the dilated-bbox
    fallback fenced the swing square out of the room."""

    def _plan(self, linings=True, fixture=False):
        # 500x300 room split by a 14px horizontal band at y=250 with a
        # 112px structural opening x 260..372; the swing square sits above.
        paths = rect_room(0, 100, 100, 600, 400, thickness=14)
        paths += wall_band_h(8, 100, 260, 250, thickness=14)
        paths += wall_band_h(10, 372, 600, 250, thickness=14)
        if linings:
            paths.append(stroked_box_path(20, 260, 250, 272, 264))
            paths.append(stroked_box_path(21, 360, 250, 372, 264))
        if fixture:
            # Same-sized joinery box hugging the band's room-side face,
            # touching the leaf bbox corner: outside the band plane.
            paths.append(stroked_box_path(22, 360, 236, 372, 250))
        door = door_candidate((272.0, 160.0, 360.0, 250.0), confidence=0.9)
        return paths, [door]

    def _top_room(self, rooms):
        return max(
            (ShapelyPolygon(r.evidence["polygon"]) for r in rooms),
            key=lambda p: p.centroid.y < 250,
        )

    def test_lining_blocks_anchor_the_doorway_plug(self):
        paths, doors = self._plan()
        rooms = rooms_for(paths, doors=doors)
        self.assertEqual(len(rooms), 2)
        top = self._top_room(rooms)
        # The swing square is room floor right down to the wall plane.
        self.assertTrue(top.contains(ShapelyPoint(316.0, 240.0)))
        self.assertTrue(top.contains(ShapelyPoint(280.0, 242.0)))
        # The lining blocks themselves are wall, in no room.
        self.assertFalse(top.contains(ShapelyPoint(266.0, 257.0)))
        self.assertFalse(top.contains(ShapelyPoint(366.0, 257.0)))

    def test_fixture_box_beside_the_door_is_not_wall(self):
        base, doors = self._plan()
        boxed, _ = self._plan(fixture=True)
        a = sorted(r.evidence["area_px2"] for r in rooms_for(base, doors=doors))
        b = sorted(r.evidence["area_px2"] for r in rooms_for(boxed, doors=doors))
        self.assertEqual(len(a), 2)
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=5.0)

    # --- the jamb at a wall CORNER (s04 door_0001, MASTER BEDROOM) -------
    #
    # The divider between BATHROOM 02 and the bedroom (14.2px, x 1854-1868)
    # meets the bathroom's bottom band at the door's top jamb, so the top
    # lining (path 949, 14.2x12.4px) stands at a corner: shifted one
    # ring-length up it lands in the PERPENDICULAR band, whose 31.3px
    # across-span fails the 22.2px band-width probe, while the bottom
    # lining (path 946) shifts onto the divider (18.2px span) and is
    # accepted. With the top jamb 12.4px past the leaf bbox the doorway
    # plug's anchor coverage was 3/7 and the dilated bbox fenced the swing
    # square out of the bedroom (-10,345 px2). Beyond the far jamb the
    # divider resumes with the ring's own cross-section, and that is where a
    # corner lining finds the band it continues.

    def _corner_plan(self, corner_lining=True, fixture=False):
        # 500x300 room, thickness 14 (top band y 100..114); a vertical
        # divider x 300..314 from y=226 down; the 112px opening runs from
        # the top band's face (114) to the divider's end (226), so the top
        # jamb IS the corner with the top band. Linings 12.4px deep at both
        # jambs, an 88px leaf bbox spanning the band from its far face and
        # abutting each lining within the 2px barrier tolerance (s04: 0.2px).
        paths = rect_room(0, 100, 100, 600, 400, thickness=14)
        paths += wall_band_v(8, 300, 226, 400, thickness=14)
        if corner_lining:
            paths.append(stroked_box_path(20, 300, 114, 314, 126.4))
        paths.append(stroked_box_path(21, 300, 213.6, 314, 226))
        if fixture:
            # Same-sized joinery box wedged between the door's top-left
            # corner and the top band, on the ROOM side of the divider's
            # face: it shifts INTO the top band like the lining does, but
            # beyond the far jamb its across-range is room floor.
            paths.append(stroked_box_path(22, 314, 114, 328, 126.4))
        door = door_candidate((300.0, 126.0, 390.0, 214.0), confidence=0.9)
        return paths, [door]

    def _right_room(self, rooms):
        return max(
            (ShapelyPolygon(r.evidence["polygon"]) for r in rooms),
            key=lambda p: p.centroid.x,
        )

    def test_corner_lining_anchors_the_doorway_plug(self):
        paths, doors = self._corner_plan()
        rooms = rooms_for(paths, doors=doors)
        self.assertEqual(len(rooms), 2)
        right = self._right_room(rooms)
        # The swing square is bedroom floor right up to the divider's face.
        self.assertTrue(right.contains(ShapelyPoint(350.0, 170.0)))
        self.assertTrue(right.contains(ShapelyPoint(320.0, 170.0)))
        # The corner lining itself is wall, in no room.
        self.assertFalse(right.contains(ShapelyPoint(307.0, 120.0)))

    def test_fixture_box_at_the_corner_is_not_wall(self):
        base, doors = self._corner_plan()
        boxed, _ = self._corner_plan(fixture=True)
        a = sorted(r.evidence["area_px2"] for r in rooms_for(base, doors=doors))
        b = sorted(r.evidence["area_px2"] for r in rooms_for(boxed, doors=doors))
        self.assertEqual(len(a), 2)
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=5.0)
