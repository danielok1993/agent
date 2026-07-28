"""Room detection tests (detection/rooms.py).

Fixtures build wall bands as synthetic PathPrimitives (two stroked faces per
wall), run detect_wall_network, and extract rooms via detect_rooms. Rooms are
free-space components between wall solids, so expected bounds sit just inside
the inner wall faces (inner face + line barrier + wall dilation).
"""
import unittest

from shapely.geometry import box as shapely_box
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

    def test_tail_kept_on_through_material(self):
        # A band running the full extended edge supports both tails: the
        # plug keeps its whole reach (the drawn-through-plane case).
        band = shapely_box(188, 92, 294, 108)
        plugs = _door_plugs(self.BBOX, band)
        self.assertEqual([k for _, k, _ in plugs], ["full"])
        x0, _, x1, _ = plugs[0][0].bounds
        self.assertAlmostEqual(x0, 188.0, delta=0.1)
        self.assertAlmostEqual(x1, 294.0, delta=0.1)


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


if __name__ == "__main__":
    unittest.main()
