"""Wall-network builder tests (detection/walls.py).

Synthetic PathPrimitive fixtures follow the test_window_detection.py pattern:
each helper builds atomic primitives directly in 150-DPI pixel space.
"""
import unittest

from shapely.geometry import Point as ShapelyPoint, box as shapely_box

from models import PathPrimitive
from detection import WallNetwork, detect_wall_network
from detection.walls import (
    WALL_JOINERY_BRIDGE_GAP_PX,
    WALL_JOINERY_BRIDGE_SLACK_PX,
    WALL_NETWORK_MIN_SEGMENTS,
    _FillRing,
    _bridge_white_runs,
    _collect_wall_faces,
    _equivalent_sides,
    _is_dashed,
)


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
    """Horizontal wall drawn as two stroked faces."""
    return [
        hline(start_idx, x0, x1, y),
        hline(start_idx + 1, x0, x1, y + thickness),
    ]


def wall_band_v(start_idx, x, y0, y1, thickness=8.0):
    return [
        vline(start_idx, x, y0, y1),
        vline(start_idx + 1, x + thickness, y0, y1),
    ]


def rect_room(start_idx, x0, y0, x1, y1, thickness=8.0):
    """Four wall bands forming a closed rectangular room (outer faces at the
    given coordinates, inner faces inset by thickness)."""
    return (
        wall_band_h(start_idx, x0, x1, y0, thickness)
        + wall_band_h(start_idx + 2, x0, x1, y1 - thickness, thickness)
        + wall_band_v(start_idx + 4, x0, y0, y1, thickness)
        + wall_band_v(start_idx + 6, x1 - thickness, y0, y1, thickness)
    )


class TestDashDetection(unittest.TestCase):
    def test_solid_variants(self):
        self.assertFalse(_is_dashed(""))
        self.assertFalse(_is_dashed("[] 0"))

    def test_dashed(self):
        self.assertTrue(_is_dashed("[ 3 ] 0"))
        self.assertTrue(_is_dashed("[3 2] 0"))


class TestFaceCollection(unittest.TestCase):
    def test_dashed_lines_excluded(self):
        paths = [hline(0, 100, 300, 100), hline(1, 100, 300, 108, dashes="[ 3 ] 0")]
        faces, _ = _collect_wall_faces(paths)
        self.assertEqual(len(faces), 1)

    def test_filled_band_yields_centerline(self):
        band = path(
            0,
            [(100, 100), (300, 100), (300, 108), (100, 108)],
            item_type="re",
            fill=(0.5, 0.5, 0.5),
        )
        _, bands = _collect_wall_faces([band])
        self.assertEqual(len(bands), 1)
        seg = bands[0]
        self.assertAlmostEqual(seg.thickness, 8.0)
        # Centerline runs along the long axis at mid-thickness
        ys = sorted([seg.p1[1], seg.p2[1]])
        self.assertAlmostEqual(ys[0], 104.0)
        self.assertAlmostEqual(ys[1], 104.0)
        self.assertAlmostEqual(abs(seg.p2[0] - seg.p1[0]), 200.0)

    def test_solid_fixture_block_not_a_band(self):
        # Square filled block (aspect < WALL_BAND_MIN_ASPECT) must not
        # produce a centerline.
        block = path(
            0,
            [(100, 100), (140, 100), (140, 140), (100, 140)],
            item_type="re",
            fill=(0.2, 0.2, 0.2),
        )
        _, bands = _collect_wall_faces([block])
        self.assertEqual(len(bands), 0)


class TestCenterlines(unittest.TestCase):
    def test_parallel_pair_gives_one_centerline(self):
        paths = wall_band_h(0, 100, 300, 100, thickness=8.0)
        # Sparse network (< min segments) — inspect segments directly.
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 1)
        seg = network.segments[0]
        self.assertAlmostEqual(seg.thickness_px, 8.0)
        ys = [seg.p1[1], seg.p2[1]]
        self.assertAlmostEqual(ys[0], 104.0)
        self.assertAlmostEqual(ys[1], 104.0)

    def test_hatch_strokes_do_not_pair(self):
        # Short diagonal hatch strokes inside a wall band: adjacent strokes are
        # parallel but their projected overlap stays below the pairing minimum.
        paths = wall_band_h(0, 100, 400, 100, thickness=10.0)
        idx = 2
        hatch = []
        for x in range(105, 390, 8):
            hatch.append(path(idx, [(x, 110), (x + 10, 100)], stroke_width=0.6))
            idx += 1
        network = detect_wall_network(paths + hatch)
        for seg in network.segments:
            self.assertAlmostEqual(seg.thickness_px, 10.0, delta=0.5)

    def test_long_face_pairs_with_multiple_stubs(self):
        # One long exterior face with two short inner stubs (opening between
        # them): both stubs must yield centerlines — the retired detector's
        # greedy pairing lost the second one.
        paths = [
            hline(0, 100, 500, 100),
            hline(1, 100, 250, 108),
            hline(2, 310, 500, 108),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 2)
        spans = sorted(
            (min(s.p1[0], s.p2[0]), max(s.p1[0], s.p2[0])) for s in network.segments
        )
        self.assertAlmostEqual(spans[0][0], 100.0, delta=1.0)
        self.assertAlmostEqual(spans[0][1], 250.0, delta=1.0)
        self.assertAlmostEqual(spans[1][0], 310.0, delta=1.0)
        self.assertAlmostEqual(spans[1][1], 500.0, delta=1.0)


def weak_hatched_band_h(start_idx, x0, x1, y, thickness=14.0, pen=0.45,
                        hatch_step=20, hatch_pen=0.3):
    """Partition wall in the joinery pen: two hairline faces with diagonal
    hatch strokes between them (the universal new-partition signature)."""
    prims = [
        hline(start_idx, x0, x1, y, stroke_width=pen),
        hline(start_idx + 1, x0, x1, y + thickness, stroke_width=pen),
    ]
    idx = start_idx + 2
    for x in range(int(x0) + 4, int(x1) - int(thickness) - 4, hatch_step):
        prims.append(path(
            idx, [(x, y + thickness - 1), (x + thickness - 2, y + 1)],
            stroke_width=hatch_pen,
        ))
        idx += 1
    return prims


class TestWeakFacePairs(unittest.TestCase):
    def test_hatched_hairline_pair_forms_wall(self):
        paths = weak_hatched_band_h(0, 100, 400, 200)
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 1)
        seg = network.segments[0]
        self.assertAlmostEqual(seg.thickness_px, 14.0, delta=0.5)
        self.assertFalse(seg.stroked)
        xs = sorted((seg.p1[0], seg.p2[0]))
        self.assertAlmostEqual(xs[0], 100.0, delta=2.0)
        self.assertAlmostEqual(xs[1], 400.0, delta=2.0)

    def test_hairline_pair_without_material_does_not_pair(self):
        # Two parallel fixture edges in the same pen, nothing between them.
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 214, stroke_width=0.45),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_sparse_marks_do_not_qualify(self):
        # Glazing-strip analog: a long hairline pair with a few scattered
        # diagonal ticks stays out (density below WALL_WEAK_MATERIAL_PER_100PX).
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 214, stroke_width=0.45),
        ]
        for i, x in enumerate((120, 200, 280, 360)):
            paths.append(path(10 + i, [(x, 213), (x + 12, 201)], stroke_width=0.3))
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_clumped_marks_do_not_qualify(self):
        # A hatched symbol at one end of a long fixture run must not turn the
        # whole run into wall (span gate).
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 214, stroke_width=0.45),
        ]
        idx = 10
        for x in range(104, 164, 5):
            paths.append(path(idx, [(x, 213), (x + 12, 201)], stroke_width=0.3))
            idx += 1
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_perpendicular_fins_do_not_qualify(self):
        # Radiator signature: hairline pair with perpendicular fins — fins are
        # not diagonal to the band axis, so no wall.
        paths = [
            hline(0, 100, 300, 200, stroke_width=0.45),
            hline(1, 100, 300, 214, stroke_width=0.45),
        ]
        idx = 10
        for x in range(105, 295, 10):
            paths.append(vline(idx, x, 201, 213, stroke_width=0.45))
            idx += 1
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_short_dense_sliver_does_not_qualify(self):
        # Dimension-tick clusters pass the density gate trivially on a very
        # short pair; the minimum run length keeps such slivers out.
        paths = [
            hline(0, 100, 122, 200, stroke_width=0.45),
            hline(1, 100, 122, 214, stroke_width=0.45),
        ]
        idx = 10
        for x in range(102, 120, 3):
            paths.append(path(idx, [(x, 213), (x + 10, 201)], stroke_width=0.3))
            idx += 1
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_light_pen_face_needs_material(self):
        # Floor-tile grid signature: a 0.75px line running parallel to a
        # 1.5px wall face at wall-like spacing inside the room. It clears the
        # absolute stroke floor but sits under WALL_WEAK_STROKE_RATIO of the
        # wall pen, so it is demoted to weak and, with no material in the
        # band, must not pair into a phantom wall across the room interior.
        paths = rect_room(0, 100, 100, 500, 400) + [
            hline(50, 120, 480, 138, stroke_width=0.75),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 4)
        self.assertNotIn(50, network.paired_face_indices())

    def test_light_pen_pair_with_material_forms_wall(self):
        # Demotion routes light-pen faces through the material gate rather
        # than dropping them: a 0.75px partition with hatch between its faces
        # is still a wall on a page whose wall pen is 1.5px.
        paths = rect_room(0, 100, 100, 500, 400) + weak_hatched_band_h(
            100, 120, 480, 250, pen=0.75
        )
        network = detect_wall_network(paths)
        partitions = [
            s for s in network.segments
            if abs(s.thickness_px - 14.0) < 0.5
        ]
        self.assertEqual(len(partitions), 1)

    def test_duplicate_ticks_do_not_validate_weak_pair(self):
        # Dimension-line signature: CAD exports re-draw each oblique tick
        # (heavy pen, light pen, and once per adjoining dimension run), so 2
        # tick locations arrive as 6 strokes. Deduped, they stay under the
        # material count gate and the hairline pair they sit on must not
        # become a wall.
        paths = [
            hline(0, 100, 250, 200, stroke_width=0.45),
            hline(1, 100, 250, 214, stroke_width=0.45),
        ]
        idx = 10
        for x in (110, 240):
            for pen in (1.8, 0.5, 0.3):
                paths.append(
                    path(idx, [(x, 213), (x + 12, 201)], stroke_width=pen)
                )
                idx += 1
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 0)

    def test_outer_line_does_not_claim_inner_pair_material(self):
        # Floor-tile line running parallel OUTSIDE a hatched hairline
        # partition, at wall-like spacing from the partition's far face
        # (5-1133 WC/bath divider): the over-wide pair (tile x far face)
        # encloses the partition's band and passes the material gate on the
        # partition's OWN hatch. The kept tighter pair strictly inside that
        # band claims the material; the tile pair is dropped, so only the
        # true partition remains and the tile line never becomes a face.
        paths = weak_hatched_band_h(0, 100, 400, 200) + [
            hline(50, 100, 400, 180, stroke_width=0.45),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 1)
        self.assertAlmostEqual(network.segments[0].thickness_px, 14.0, delta=0.5)
        self.assertNotIn(50, network.paired_face_indices())

    def test_weak_faces_do_not_drag_stroke_reference(self):
        # Strong walls at 1.5px + a material-backed hairline partition: the
        # reference stays at the strong pen so the rooms' relative
        # pen-weight gate is not diluted.
        paths = rect_room(0, 100, 100, 500, 400) + weak_hatched_band_h(
            100, 100, 500, 250
        )
        network = detect_wall_network(paths)
        self.assertAlmostEqual(network.wall_stroke_reference(), 1.5)
        # ... and the weak faces still ride in the face list as paired faces.
        paired = network.paired_face_indices()
        self.assertTrue({100, 101} <= paired)


class TestNetworkAssembly(unittest.TestCase):
    def test_rect_room_closes(self):
        paths = rect_room(0, 100, 100, 400, 300, thickness=8.0)
        network = detect_wall_network(paths)
        self.assertFalse(network.is_empty())
        self.assertEqual(len(network.segments), 4)
        self.assertIsNotNone(network.merged)
        # The noded merge must polygonize into exactly one face.
        from shapely.ops import polygonize
        faces = list(polygonize(network.merged))
        self.assertEqual(len(faces), 1)
        # Face is bounded by the centerlines: 292x192 (inset half thickness).
        self.assertAlmostEqual(faces[0].area, 292 * 192, delta=200)

    def test_t_junction_dangle_extension(self):
        # Vertical partition butting into a horizontal wall from below: the
        # partition's centerline ends ~thickness/2 short and must be extended.
        paths = (
            wall_band_h(0, 100, 500, 100, thickness=8.0)
            + wall_band_v(2, 296, 108, 300, thickness=8.0)
        )
        network = detect_wall_network(paths)
        vertical = [
            s for s in network.segments
            if abs(s.p1[0] - s.p2[0]) < abs(s.p1[1] - s.p2[1])
        ]
        self.assertEqual(len(vertical), 1)
        top_y = min(vertical[0].p1[1], vertical[0].p2[1])
        # Extended onto the horizontal centerline at y=104
        self.assertAlmostEqual(top_y, 104.0, delta=1.0)

    def test_sparse_page_is_empty(self):
        paths = wall_band_h(0, 100, 300, 100)
        network = detect_wall_network(paths)
        self.assertTrue(network.is_empty())
        self.assertLess(len(network.segments), WALL_NETWORK_MIN_SEGMENTS)
        self.assertIsNone(network.merged)


class TestNetworkQueries(unittest.TestCase):
    def make_network(self):
        return detect_wall_network(rect_room(0, 100, 100, 400, 300, thickness=8.0))

    def test_near_bbox(self):
        network = self.make_network()
        self.assertTrue(network.near_bbox((180, 90, 220, 115), 5.0))     # on top wall
        self.assertFalse(network.near_bbox((200, 180, 240, 220), 5.0))   # room interior

    def test_nearest_segment(self):
        network = self.make_network()
        seg, dist = network.nearest_segment((250, 104))
        self.assertLess(dist, 1.0)
        self.assertAlmostEqual(seg.thickness_px, 8.0)

    def test_collinear_overlap(self):
        network = self.make_network()
        # A window-like bbox sitting on the top wall band, fully covered.
        self.assertGreaterEqual(
            network.collinear_overlap((150, 98, 350, 110), 4.0), 0.99
        )
        # Perpendicular orientation: no collinear coverage.
        self.assertEqual(network.collinear_overlap((200, 150, 210, 250), 4.0), 0.0)

    def test_empty_network_queries(self):
        network = WallNetwork(segments=[])
        self.assertTrue(network.is_empty())
        self.assertFalse(network.near_bbox((0, 0, 100, 100), 20.0))
        self.assertEqual(network.collinear_overlap((0, 0, 100, 10), 4.0), 0.0)
        self.assertIsNone(network.nearest_segment((0, 0)))


def fill_ring(start_idx, x0, y0, x1, y1, fill, stroke_width=0.0):
    """Closed filled rectangle exploded into 4 chained `l` items."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    return [
        path(start_idx + i, [pts[i], pts[i + 1]],
             stroke_width=stroke_width, fill=fill)
        for i in range(4)
    ]


class TestFillClassRating(unittest.TestCase):
    def test_heavy_wall_band_pairs_at_32px(self):
        # A 32px blockwork band must pair (WALL_MAX_THICKNESS_PX raised past
        # the old 30px cap, which left such walls as hollow slivers).
        paths = [hline(0, 100, 400, 100), hline(1, 100, 400, 132)]
        network = detect_wall_network(paths)
        self.assertTrue(
            any(abs(s.thickness_px - 32.0) < 0.5 for s in network.segments)
        )

    def test_white_fill_outlines_are_not_faces(self):
        # Unstroked white (background) polygons are masks or hollow-wall
        # candidates, never plain faces.
        faces, bands = _collect_wall_faces(
            fill_ring(0, 100, 100, 300, 120, fill=(1.0, 1.0, 1.0))
        )
        self.assertEqual(faces, [])
        self.assertEqual(bands, [])

    def test_furniture_fill_class_excluded(self):
        # Two compact rings dominate the 0.9-gray class -> furniture: none
        # of its outlines become faces.
        paths = (
            fill_ring(0, 100, 100, 200, 160, fill=(0.9, 0.9, 0.9))
            + fill_ring(4, 300, 100, 400, 160, fill=(0.9, 0.9, 0.9))
        )
        faces, _ = _collect_wall_faces(paths)
        self.assertEqual(faces, [])

    def test_wall_fill_class_kept_with_polygons(self):
        # Band-dominant fill class -> wall: outlines become faces and the
        # rings are exposed as barrier polygons on the network.
        paths = (
            fill_ring(0, 100, 100, 400, 108, fill=(0.7, 0.7, 0.7))
            + fill_ring(4, 100, 200, 400, 208, fill=(0.7, 0.7, 0.7))
        )
        faces, _ = _collect_wall_faces(paths)
        # Long edges only — the 8px short caps stay under WALL_FACE_MIN_LEN_PX.
        self.assertEqual(len(faces), 4)
        self.assertTrue(all(f.wall_fill for f in faces))
        network = detect_wall_network(paths)
        self.assertEqual(len(network.fill_polygons), 2)


def marker_ring(start_idx, pts, fill):
    """Filled triangle/dart exploded into chained `l` items (a leader tip)."""
    ring = list(pts) + [pts[0]]
    return [
        path(start_idx + i, [ring[i], ring[i + 1]], stroke_width=0.0, fill=fill)
        for i in range(len(pts))
    ]


class TestMarkerRings(unittest.TestCase):
    """Leader/dimension arrowheads share the wall pen on Vectorworks-style
    exports; tiny triangle/dart rings are annotation, never wall material."""

    GRAY = (0.7, 0.7, 0.7)

    def walls(self):
        return (
            fill_ring(0, 100, 100, 400, 108, fill=self.GRAY)
            + fill_ring(4, 100, 200, 400, 208, fill=self.GRAY)
        )

    def test_arrowhead_triangle_is_not_wall_material(self):
        arrow = marker_ring(
            8, [(200.0, 150.0), (213.0, 147.0), (210.0, 158.0)], self.GRAY
        )
        network = detect_wall_network(self.walls() + arrow)
        # Bands only: no barrier polygon and no wall_fill faces for the arrow.
        self.assertEqual(len(network.fill_polygons), 2)
        arrow_indices = {p.path_index for p in arrow}
        self.assertFalse(
            [f for f in network.faces if f.wall_fill and f.indices & arrow_indices]
        )

    def test_concave_dart_is_not_wall_material(self):
        dart = marker_ring(
            8,
            [(200.0, 150.0), (214.0, 145.0), (210.0, 151.0), (213.0, 157.0)],
            self.GRAY,
        )
        network = detect_wall_network(self.walls() + dart)
        self.assertEqual(len(network.fill_polygons), 2)

    def test_small_convex_quad_stays_wall_material(self):
        # Same size regime as an arrowhead, but convex — a jamb stub seals.
        stub = fill_ring(8, 200, 150, 204, 170, fill=self.GRAY)
        network = detect_wall_network(self.walls() + stub)
        self.assertEqual(len(network.fill_polygons), 3)


def white_ring(x0, y0, x1, y1):
    """Accepted hollow-wall/joinery _FillRing over the given rectangle."""
    poly = shapely_box(x0, y0, x1, y1)
    short, long_ = _equivalent_sides(poly)
    return _FillRing(
        key=(1.0, 1.0, 1.0), poly=poly, short=short, long=long_, indices=set()
    )


class TestWhiteRunBridging(unittest.TestCase):
    """Bridges close OPEN SPANS in accepted white-ring runs; rings already
    connected by touching must never bridge — between small cavity segments
    on perpendicular runs of one chain, the redundant hull is thin enough to
    pass the band test and chords diagonally across the room corner."""

    def test_open_span_still_bridges(self):
        # Two collinear joinery boxes with an open front between them
        # (the wardrobe-run case) — the span must still be closed.
        a = white_ring(100, 100, 140, 110)
        b = white_ring(180, 100, 220, 110)
        bridges = _bridge_white_runs([a, b])
        self.assertEqual(len(bridges), 1)
        self.assertTrue(bridges[0].contains(ShapelyPoint(160, 105)))

    def test_touch_chained_corner_rings_never_bridge(self):
        # L-corner cavity chain: every ring touches the next, so there is no
        # gap to close anywhere. The far pair (a, d) sits within the bridge
        # gap and its hull passes the band test — the connectivity rule is
        # the only thing rejecting the diagonal chord across the corner.
        a = white_ring(100, 100, 112, 106)
        b = white_ring(112.5, 100, 140, 106)
        c = white_ring(140, 106.5, 152, 160)
        d = white_ring(140, 160.5, 152, 166)
        gap = a.poly.distance(d.poly)
        self.assertLessEqual(gap, WALL_JOINERY_BRIDGE_GAP_PX)
        hull = a.poly.union(d.poly).convex_hull
        short, _ = _equivalent_sides(hull)
        self.assertLessEqual(
            short, max(a.short, d.short) + WALL_JOINERY_BRIDGE_SLACK_PX
        )
        self.assertEqual(_bridge_white_runs([a, b, c, d]), [])

    def test_connected_components_bridge_once(self):
        # Three collinear clusters: closing a-b and b-c connects everything;
        # the redundant long chord a-c (also within gap range) is skipped.
        a = white_ring(100, 100, 120, 110)
        b = white_ring(150, 100, 170, 110)
        c = white_ring(195, 100, 215, 110)
        self.assertLessEqual(a.poly.distance(c.poly), WALL_JOINERY_BRIDGE_GAP_PX)
        self.assertEqual(len(_bridge_white_runs([a, b, c])), 2)


def paving_field(start_idx, x0, y0, pitch=31.0, cols=6, rows=5, pen=1.05):
    """Running-bond paving: continuous course lines, staggered joint lines.

    Mirrors the 5-1133 open-vestibule field: joints on alternating courses
    only, so joint rungs are chains of pitch-long pieces that never
    collinear-merge (gaps equal the pitch, far above the merge gap)."""
    paths = []
    idx = start_idx
    x1 = x0 + cols * pitch
    for r in range(rows + 1):
        paths.append(hline(idx, x0, x1, y0 + r * pitch, stroke_width=pen))
        idx += 1
    for r in range(rows):
        for c in range(1, cols):
            if (r + c) % 2 == 0:
                paths.append(vline(
                    idx, x0 + c * pitch, y0 + r * pitch, y0 + (r + 1) * pitch,
                    stroke_width=pen,
                ))
                idx += 1
    return paths


class TestLatticeDemotion(unittest.TestCase):
    """Striped fields (paving bonds, tile fields, treads) are not walls."""

    def _segments_inside(self, network, x0, y0, x1, y1):
        return [
            s for s in network.segments
            if x0 <= (s.p1[0] + s.p2[0]) / 2.0 <= x1
            and y0 <= (s.p1[1] + s.p2[1]) / 2.0 <= y1
        ]

    def test_paving_field_forms_no_walls(self):
        # A room provides real paired faces (the stroke reference) and the
        # field sits in open space beside it, exactly like the vestibule.
        paths = rect_room(0, 100, 100, 400, 400) + paving_field(50, 500, 100)
        network = detect_wall_network(paths)
        field = self._segments_inside(network, 495, 95, 700, 300)
        self.assertEqual(field, [])

    def test_paving_field_with_missing_rung_still_demoted(self):
        # One joint line eaten by a text mask leaves a 2x-pitch gap in the
        # course rungs; the run must chain across it (the 5-1133 field loses
        # its x=1070.8 joints under the "VESTIBULE" label).
        paths = rect_room(0, 100, 100, 400, 400)
        field = [
            p for p in paving_field(50, 500, 100)
            if not (p.points[0][1] == p.points[1][1]
                    and abs(p.points[0][1] - 193.0) < 1.0)
        ]
        network = detect_wall_network(paths + field)
        inside = self._segments_inside(network, 495, 95, 700, 300)
        self.assertEqual(inside, [])

    def test_four_parallel_faces_stay_walls(self):
        # A cavity party wall drawn leaf/cavity/leaf at equal width is four
        # same-pen faces at equal pitch — one rung short of a striped field,
        # and its pairs must survive.
        paths = rect_room(0, 100, 100, 400, 400) + [
            vline(50 + i, 500 + i * 12.0, 100, 400) for i in range(4)
        ]
        network = detect_wall_network(paths)
        inside = self._segments_inside(network, 495, 95, 545, 405)
        self.assertGreater(len(inside), 0)

    def test_stacked_wall_belts_stay_walls(self):
        # Parallel wall bands at quasi-equal spacing whose pieces occupy
        # DISJOINT spans chain into a rung ladder, but never coexist at one
        # cross-section — the EXISTING_FLOOR_PLANS-3228943 signature, where
        # envelope-glued chaining deleted the plan's central wall belt.
        paths = rect_room(0, 100, 100, 400, 400) + [
            hline(50, 500, 800, 500), hline(51, 500, 650, 508),
            hline(52, 650, 800, 516), hline(53, 500, 650, 524),
            hline(54, 650, 800, 532),
        ]
        network = detect_wall_network(paths)
        inside = self._segments_inside(network, 495, 495, 805, 537)
        self.assertGreater(len(inside), 0)

    def test_short_pieces_form_no_rungs(self):
        # Radiator/grille fins: many short parallel same-pen strokes at
        # equal pitch. Each rung is under WALL_LATTICE_MIN_RUNG_LEN_PX, so
        # no striped field is declared — and no face is demoted (the fins
        # were never faces; the flanking wall pair must survive).
        paths = rect_room(0, 100, 100, 400, 400) + [
            vline(50, 500, 100, 400), vline(51, 530, 100, 400),
        ] + [
            hline(60 + i, 505, 525, 110 + i * 10.0, stroke_width=1.5)
            for i in range(20)
        ]
        network = detect_wall_network(paths)
        inside = self._segments_inside(network, 495, 95, 545, 405)
        self.assertGreater(len(inside), 0)


RED = (1.0, 0.0, 0.0)
BLUE = (0.0, 0.0, 1.0)
GREY = (0.86, 0.86, 0.86)
MAGENTA = (0.75, 0.0, 1.0)


class TestPenGates(unittest.TestCase):
    """Stroke-color pen identity: pairing, faint-ink demotion, dimension
    chains, and one-sided hatch backing (the floor-plans signatures — the
    open-plan kitchen was chopped five ways by grey RSJ double lines, blue
    dimension chains, and cross-pen furniture/dimension pairs, all drawn AT
    the wall pen widths)."""

    def _segments_inside(self, network, x0, y0, x1, y1):
        return [
            s for s in network.segments
            if x0 <= (s.p1[0] + s.p2[0]) / 2.0 <= x1
            and y0 <= (s.p1[1] + s.p2[1]) / 2.0 <= y1
        ]

    def test_cross_pen_faces_do_not_pair(self):
        # A blue dimension line beside a red cabinet front at wall-like
        # spacing is annotation coincidence, never a wall band.
        base = rect_room(0, 100, 100, 400, 400)
        cross = base + [
            vline(50, 500, 100, 300, color=BLUE),
            vline(51, 514, 100, 300, color=RED),
        ]
        network = detect_wall_network(cross)
        self.assertEqual(self._segments_inside(network, 495, 95, 520, 305), [])
        same = base + [
            vline(50, 500, 100, 300),
            vline(51, 514, 100, 300),
        ]
        network = detect_wall_network(same)
        self.assertGreater(
            len(self._segments_inside(network, 495, 95, 520, 305)), 0
        )

    def test_light_pen_pair_needs_material(self):
        # A light-grey double line (an RSJ drawn over the room) is faint
        # reference ink in the wall pen width; without drawn material
        # between the faces it must not become a wall band.
        paths = rect_room(0, 100, 100, 400, 400) + [
            vline(50, 500, 100, 300, color=GREY),
            vline(51, 506, 100, 300, color=GREY),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(self._segments_inside(network, 495, 95, 512, 305), [])

    def test_dimension_line_with_end_ticks_excluded(self):
        # Oblique same-pen ticks centred on BOTH endpoints = dimension
        # chain member; it must not pair with the parallel wall face below.
        # Drawn in the WALL pen here so only the tick signature can block it.
        dim = [
            hline(50, 150, 350, 80),
            path(51, [(147.5, 77.5), (152.5, 82.5)]),
            path(52, [(347.5, 77.5), (352.5, 82.5)]),
        ]
        paths = rect_room(0, 100, 100, 400, 400) + dim
        network = detect_wall_network(paths)
        used = network.paired_face_indices()
        self.assertNotIn(50, used)
        # One-ended tick (a wall a chain terminates against) stays a face.
        paths = rect_room(0, 100, 100, 400, 400) + dim[:2]
        network = detect_wall_network(paths)
        self.assertIn(50, network.paired_face_indices())

    def test_hatched_band_face_is_material_backed(self):
        # A hatched band drawn with one long face, a short stub partner and
        # its hatch (floor-plans' dining east wall): the face's own same-pen
        # hatch is wall evidence even though pairing covers only the stub.
        paths = rect_room(0, 100, 100, 400, 400, thickness=8.0) + [
            vline(50, 500, 100, 300, color=MAGENTA, stroke_width=1.0),
            vline(51, 510, 280, 300, color=MAGENTA, stroke_width=1.0),
        ] + [
            path(60 + i, [(500.0, 100.0 + i * 8.0), (508.0, 108.0 + i * 8.0)],
                 color=MAGENTA, stroke_width=1.0)
            for i in range(25)
        ]
        network = detect_wall_network(paths)
        backed = [
            f for f in network.faces
            if 50 in f.indices and f.material_backed
        ]
        self.assertEqual(len(backed), 1)
        # The same face without the hatch carries no backing.
        network = detect_wall_network(paths[:10])
        self.assertEqual(
            [f for f in network.faces if 50 in f.indices and f.material_backed],
            [],
        )


if __name__ == "__main__":
    unittest.main()
