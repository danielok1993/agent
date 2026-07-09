"""Room detection tests (detection/rooms.py).

Fixtures build wall bands as synthetic PathPrimitives (two stroked faces per
wall), run detect_wall_network, and extract rooms via detect_rooms. Rooms are
free-space components between wall solids, so expected bounds sit just inside
the inner wall faces (inner face + line barrier + wall dilation).
"""
import unittest

from models import Candidate, PathPrimitive, TextSpan
from detection import detect_wall_network
from detection.rooms import ROOM_GAP_CLOSE_PX, detect_rooms

PAGE_W, PAGE_H = 1000.0, 800.0


def path(idx, points, item_type="l", stroke_width=1.5, fill=None, dashes="", layer=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx,
        item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0.0, 0.0, 0.0),
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
    network = detect_wall_network(paths)
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
        # closing, and carved a bay out of the room.
        paths = rect_room(0, 100, 100, 400, 300) + fill_ring(
            8, 116, 130, 128, 270, fill=(1.0, 1.0, 1.0)
        )
        baseline = rooms_for(rect_room(0, 100, 100, 400, 300))
        door = door_candidate((116, 130, 128, 270), confidence=0.35)
        rooms = rooms_for(paths, doors=[door])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(
            rooms[0].evidence["area_px2"],
            baseline[0].evidence["area_px2"],
            delta=200,
        )


class TestEmptyNetwork(unittest.TestCase):
    def test_no_network_no_rooms(self):
        self.assertEqual(detect_rooms(None, [], [], PAGE_W, PAGE_H), [])

    def test_sparse_network_no_rooms(self):
        rooms = rooms_for(wall_band_h(0, 100, 300, 100))
        self.assertEqual(rooms, [])


if __name__ == "__main__":
    unittest.main()
