"""Wall-network builder tests (detection/walls.py).

Synthetic PathPrimitive fixtures follow the test_window_detection.py pattern:
each helper builds atomic primitives directly in 150-DPI pixel space.
"""
import unittest

from shapely.geometry import (
    LineString as ShapelyLineString, Point as ShapelyPoint,
    Polygon as ShapelyPolygon, box as shapely_box,
)

from models import PathPrimitive
from detection import WallNetwork, detect_wall_network
from detection.rooms import detect_rooms
from detection.walls import (
    WALL_GATES_UNSCALED,
    WALL_JOINERY_BRIDGE_GAP_PX,
    WALL_JOINERY_BRIDGE_SLACK_PX,
    WALL_MAX_THICKNESS_PX,
    WALL_NETWORK_MIN_SEGMENTS,
    _FillRing,
    _bridge_white_runs,
    _Seg,
    _collect_fill_rings,
    _collect_wall_faces,
    _equivalent_sides,
    _fill_seam_indices,
    _is_dashed,
    _merge_collinear_segs,
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

    def test_ten_px_hatch_stroke_is_not_a_face(self):
        # WALL_FACE_MIN_LEN_PX stays 11px. The W-gate census (2026-09-04)
        # proposed 9 — the shortest paired faces sit ON the floor on every
        # sheet (the 100mm jamb nib: s02 11.2px, s03 11.2, s14 11.0) — and
        # iteration 2 tried it: a band's 45-degree hatch strokes are
        # T*sqrt(2) long, so a 7px band's hatch is 9.9px and the band-END
        # strokes (too few for the lattice rule) paired on s01 and s02.
        # A 10px 45-degree stroke stays out; a 12px nib is a face.
        faces, _ = _collect_wall_faces([path(0, [(100.0, 107.0), (107.0, 100.0)])])
        self.assertEqual(faces, [])

    def test_twelve_px_nib_is_a_face(self):
        faces, _ = _collect_wall_faces([hline(0, 100, 112, 100)])
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

    def test_stroked_fill_seam_is_not_a_face(self):
        # A filled band exported as two triangles that BOTH carry the shared
        # diagonal, every edge stroked in the fill's own colour at width 0
        # (recorded as 1.0px): the seam is found by _fill_seams, but the
        # 1.0px stroke otherwise admits it as a STROKED face regardless.
        paths = triangulated_band_h(0, 100, 400, 100, thickness=14.0)
        faces, _ = _collect_wall_faces(paths)
        seam = {1, 5}
        for f in faces:
            self.assertFalse(f.indices & seam, f)
        self.assertEqual(len(faces), 4)


def triangulated_band_h(start_idx, x0, x1, y, thickness=14.0,
                        fill=(0.6, 0.6, 0.6), stroke_width=1.0):
    """A filled wall band the exporter triangulated into two rings that
    each carry the shared diagonal (s03 EXISTING_BRICKWORK, s04/s08
    RR_Wall Hatches, s12, s17): six `l` items with the fill colour, and —
    the corpus signature — a self-coloured width-0 stroke recorded at
    1.0px. Triangle 2 starts where triangle 1 does NOT end, so the two
    chains close separately. Indices start_idx+1 and start_idx+5 are the
    seam."""
    y1 = y + thickness
    kw = dict(fill=fill, color=fill, stroke_width=stroke_width)
    return [
        path(start_idx, [(x0, y), (x1, y)], **kw),
        path(start_idx + 1, [(x1, y), (x0, y1)], **kw),      # seam
        path(start_idx + 2, [(x0, y1), (x0, y)], **kw),
        path(start_idx + 3, [(x1, y), (x1, y1)], **kw),
        path(start_idx + 4, [(x1, y1), (x0, y1)], **kw),
        path(start_idx + 5, [(x0, y1), (x1, y)], **kw),      # seam
    ]


def fan_triangulated_band_h(start_idx, x0, x1, y, thickness=14.0,
                            fill=(0.6, 0.6, 0.6)):
    """The same band triangulated as a FAN: triangle 2 starts at triangle
    1's start vertex, so the exporter's six fill-only `l` items (stroke 0,
    no stroke colour — s20's 19 grey wall-band chains, s04/s08's red
    demolition slivers, s18's black bands) chain into ONE six-edge chain
    that revisits its start after edge 3 and continues. Indices start_idx+2
    and start_idx+3 are the seam (the band's diagonal, drawn once per
    triangle)."""
    y1 = y + thickness
    a, b, c, d = (x0, y), (x1, y), (x1, y1), (x0, y1)
    kw = dict(fill=fill, color=None, stroke_width=0.0)
    return [
        path(start_idx, [a, b], **kw),
        path(start_idx + 1, [b, c], **kw),
        path(start_idx + 2, [c, a], **kw),      # seam — closes triangle 1 at A
        path(start_idx + 3, [a, c], **kw),      # seam — triangle 2 opens at A
        path(start_idx + 4, [c, d], **kw),
        path(start_idx + 5, [d, a], **kw),
    ]


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

    def test_merged_run_lies_on_its_longest_member_not_the_seed(self):
        # A stub is evidence of a line's EXTENT, never of its POSITION.
        # _merge_collinear_segs seeded every run with the FIRST unused
        # segment in path order and projected every later member onto that
        # seed's line, so a 12px jamb-stub edge drawn 3.75px off a band's
        # face (inside COLLINEAR_OFFSET_TOL) and earlier in path order
        # dragged the band's whole 400px face onto the stub's line (s03
        # room_0013: the 12px strip-stack joint at y=1778.42, paths
        # 15116/15148, seeded the run and the 416px band face at y=1782.17
        # joined at offset 3.75 — the merged face sat 3.8px into the room,
        # the pair measured 15.5px against its drawn 11.75, and the solid
        # fenced a 386x3.8px strip out of the BEDROOM; corpus-wide, 92 runs
        # on ten sheets hung a run more than 1px off its longest member on
        # a seed under half its length, 41 of them reaching a paired
        # segment). The run now lies on its LONGEST member's line.
        paths = [
            hline(0, 100, 112, 103.75),      # the stub, first in path order
            hline(1, 100, 500, 100),          # the 400px face
        ]
        network = detect_wall_network(paths)
        face = next(f for f in network.faces if 1 in f.indices)
        self.assertIn(0, face.indices)       # the stub still joins the run
        self.assertAlmostEqual(face.p1[1], 100.0, delta=0.01)
        self.assertAlmostEqual(face.p2[1], 100.0, delta=0.01)
        self.assertAlmostEqual(min(face.p1[0], face.p2[0]), 100.0, delta=0.01)
        self.assertAlmostEqual(max(face.p1[0], face.p2[0]), 500.0, delta=0.01)

    def test_stub_on_the_room_side_of_a_band_keeps_the_room_edge_at_the_face(self):
        # The same topology through detect_rooms: a closed room whose top
        # band carries a 12px stub 3.75px inside its room-side face, first
        # in path order. The merged inner face must stay ON the drawn face
        # (y=108) so the band pairs at its drawn 8px and the room's top
        # edge sits at the face's 2px standoff (y=110) — on the seed-line
        # anchor the inner face moved to y=111.75, the band measured 11.75
        # and the room edge stood 3.75px high across its whole width.
        paths = [hline(0, 108, 120, 111.75)] + rect_room(1, 100, 100, 500, 400)
        network = detect_wall_network(paths)
        top = next(f for f in network.faces if 2 in f.indices)
        self.assertAlmostEqual(top.p1[1], 108.0, delta=0.01)
        self.assertAlmostEqual(top.p2[1], 108.0, delta=0.01)
        rooms = detect_rooms(network, [], [], 1000.0, 800.0, [])
        self.assertEqual(len(rooms), 1)
        poly = ShapelyPolygon(rooms[0].evidence["polygon"])
        self.assertAlmostEqual(poly.bounds[1], 110.0, delta=0.05)
        self.assertAlmostEqual(poly.area, (492 - 108 - 4) * (392 - 108 - 4), delta=2.0)

    def test_merged_run_lies_on_the_member_line_the_drawn_ink_agrees_with(self):
        # The longest member is not always the wall face. A window's board
        # line is drawn parallel to the face a couple of px into the room
        # and spans the whole window, so it is LONGER than the face piece
        # beside it that it merges with — yet the face's line continues past
        # the opening while the board's stops at its jambs (s03 room_0013's
        # top band: the 68px face at y=1236.42 merged with the 141.8px board
        # line at 1238.67; the face's line carries ~360px of collinear
        # strong ink inside the run's extent and ~660px within one door
        # opening of it, the board's line only itself, and the longest-member
        # anchor moved the room edge 2.25px INTO the room, -877 px^2). The
        # run lies on the member line with the most collinear strong-ink
        # support within WALL_ANCHOR_SUPPORT_REACH_PX of its extent — the
        # face's 68px plus its 100px continuation beyond a 60px opening
        # (168) beats the board's 142 — so the run sits at y=100 and spans
        # only the merged members; the continuation is not bridged.
        paths = [
            hline(0, 100, 168, 100),          # the 68px face piece
            hline(1, 100, 242, 102.25),       # the 142px board line, 2.25px in
            hline(2, 302, 402, 100),          # the face continues past the opening
        ]
        network = detect_wall_network(paths)
        run = next(f for f in network.faces if {0, 1} <= set(f.indices))
        self.assertNotIn(2, run.indices)
        self.assertAlmostEqual(run.p1[1], 100.0, delta=0.01)
        self.assertAlmostEqual(run.p2[1], 100.0, delta=0.01)
        self.assertAlmostEqual(min(run.p1[0], run.p2[0]), 100.0, delta=0.01)
        self.assertAlmostEqual(max(run.p1[0], run.p2[0]), 242.0, delta=0.01)

    def test_window_board_line_does_not_pull_the_room_edge_into_the_room(self):
        # The same topology through detect_rooms: a closed room whose top
        # band's inner face (y=108) is a 68px piece beside a 142px board line
        # at 110.25, with the face continuing 60px further along. The merged
        # inner face must stay on the drawn face so the band pairs at its
        # drawn 8px and the room's top edge over the board line sits at the
        # face's 2px standoff (y=110) — on the longest-member anchor the
        # inner face moved to 110.25, the band measured 10.25 and the edge
        # stood 2.25px into the room across the board line's whole span.
        paths = [
            hline(0, 100, 500, 100),          # outer face
            hline(1, 100, 168, 108),          # inner face piece
            hline(2, 100, 242, 110.25),       # board line, 2.25px into the room
            hline(3, 302, 500, 108),          # inner face continues past the gap
        ] + wall_band_h(4, 100, 500, 392) + wall_band_v(6, 100, 100, 400) \
          + wall_band_v(8, 492, 100, 400)
        network = detect_wall_network(paths)
        top = next(f for f in network.faces if {1, 2} <= set(f.indices))
        self.assertAlmostEqual(top.p1[1], 108.0, delta=0.01)
        self.assertAlmostEqual(top.p2[1], 108.0, delta=0.01)
        rooms = detect_rooms(network, [], [], 1000.0, 800.0, [])
        self.assertEqual(len(rooms), 1)
        poly = ShapelyPolygon(rooms[0].evidence["polygon"])
        cut = poly.intersection(ShapelyLineString([(150, 0), (150, 800)]))
        self.assertAlmostEqual(cut.bounds[1], 110.0, delta=0.05)

    def test_brick_cell_diagonal_does_not_pair_into_the_room(self):
        # A vertical band (near face x=300 over 100-320, far face x=314 a
        # long run to 700) with ONE stroked corner-to-corner diagonal in
        # the same pen (the corpus strokes this was modelled on turned out
        # to be fill seams — s03 EXISTING_BRICKWORK is the wall FILL — and
        # are excluded upstream since 2026-09-02; this keeps the taper gate
        # honest for a genuinely stroked chord): 14px over 220px = 3.6 deg,
        # inside WALL_PARALLEL_ANGLE_TOL, so the chord is "parallel" to both faces
        # — but its spacing to either runs from the band's full width to
        # zero. Sampled at the far face's first endpoint (380px past the
        # cell, where the chord's line has crossed 24px beyond the face) it
        # pairs at 24px and the centerline lands 12px INTO the room, its
        # solid 26px (s03 rooms 0005/0013: a 15-29px strip fenced off the
        # bottom-right corner). The chord must lead the pair (its angle
        # bucket precedes the verticals'), and the band is filled — as on
        # s03, whose grey wall fill under a quarter of the phantom band
        # kept it clear of the far-side rule.
        paths = [
            vline(0, 300, 100, 320),
            path(1, [(314, 700), (314, 100)]),
            path(2, [(300, 100), (314, 320)]),
            path(3, [(300, 100), (314, 100), (314, 700), (300, 700)],
                 item_type="re", stroke_width=0.0, fill=(0.5, 0.5, 0.5)),
        ]
        network = detect_wall_network(paths)
        self.assertTrue(network.segments)
        for seg in network.segments:
            for x in (seg.p1[0], seg.p2[0]):
                self.assertGreaterEqual(x, 300.0 - 0.5, seg)
                self.assertLessEqual(x, 314.0 + 0.5, seg)
        self.assertTrue(any(
            abs(seg.thickness_px - 14.0) < 0.5 for seg in network.segments
        ))

    def test_self_coloured_fill_seam_never_reaches_the_network(self):
        # The corpus form of the "hatch-cell chord": a filled band's
        # triangulation seam with a self-coloured 1.0px stroke (s04 RR_Wall
        # Hatches: 50/50 seams became stroked faces; s03 248, s08 48, s12
        # 116, s17 128). Lying within WALL_PARALLEL_ANGLE_TOL of the band's
        # own faces (14px over 300px = 2.7 deg) it pairs with the NEXT cell's
        # face or merges collinearly into a run, and it sits in the paired
        # stroke reference. The seam rule's veto must cover every face tier,
        # not just the wall_fill flag. The drawn faces (black 1.5px, as s04's
        # RR_Walls lines over its fill) still pair at the band thickness.
        paths = triangulated_band_h(0, 100, 400, 100, thickness=14.0) + [
            hline(6, 100, 400, 100),
            hline(7, 100, 400, 114),
        ]
        network = detect_wall_network(paths)
        seam = {1, 5}
        for f in network.faces:
            self.assertFalse(set(f.indices) & seam, f)
        for seg in network.segments:
            self.assertFalse(set(seg.face_path_indices) & seam, seg)
        self.assertTrue(any(
            abs(seg.thickness_px - 14.0) < 0.5 for seg in network.segments
        ))

    def test_fan_triangulated_band_splits_at_the_exact_return(self):
        # A fill chain that returns EXACTLY to its own start vertex and then
        # continues is two rings drawn back to back, not one: shapely
        # rejects the self-touching six-edge polygon, so _collect_fill_rings
        # used to drop BOTH triangles, the seam was never found, and the
        # band's diagonal stayed an unstroked wall-fill face (the permissive
        # unrated-class rule) — s20's chord (552,2892)-(730,2881) in a 12px
        # grey band, 3.8 deg off its faces, paired with the next band's face
        # at a 0.49 taper ratio. Closing the ring at the exact return and
        # starting a new chain there recovers both triangles: the seam is
        # found, no face lies on it, the drawn faces still pair at the band
        # thickness, and the seam-united polygon is the rectangle itself.
        paths = fan_triangulated_band_h(0, 100, 400, 100, thickness=14.0)
        rings = _collect_fill_rings(paths)
        self.assertEqual(len(rings), 2)
        seam = _fill_seam_indices(rings, paths)
        self.assertEqual(seam, {2, 3})
        network = detect_wall_network(paths)
        for f in network.faces:
            self.assertFalse(set(f.indices) & seam, f)
        for seg in network.segments:
            self.assertFalse(set(seg.face_path_indices) & seam, seg)
        self.assertTrue(any(
            abs(seg.thickness_px - 14.0) < 0.5 for seg in network.segments
        ))
        self.assertEqual(len(network.fill_polygons), 1)
        self.assertAlmostEqual(network.fill_polygons[0].area, 300 * 14, delta=1.0)

    def test_sub_2px_sliver_seam_unites_and_never_spikes_into_the_room(self):
        # _fill_seams proved a seam by testing for fill 1px either side of
        # the edge midpoint, and a 1px probe leaves any fill thinner than
        # 2px: a 0.75px-tall sliver's two triangles (short 0.375 each —
        # a triangle's equivalent-rectangle side is its inradius, half the
        # sliver) never seam-united and each dilated ALONE, so the 0.36 deg
        # tip ran its mitre to the ROOM_RING_MITRE_LIMIT cap, 4px past the
        # vertex and 2px past the band's own 2px standoff (s03 room_0007:
        # the grey sliver under the bathroom's bottom band, paths 284-286,
        # bit a 2x4px notch out of the corridor corner). The probe now
        # stays inside the fill it tests (WALL_FILL_SEAM_PROBE_FRAC of the
        # thinnest sharing ring's short). Topology: an outer room; a
        # partition band 108..300 x 200..208 in its left half ending at a
        # thin stroked line x=300 whose 2px buffer bounds the corridor at
        # x=302; the sliver hugs the band's underside with its tip at the
        # band end (300, 208.75), exactly as on s03.
        paths = rect_room(0, 100, 100, 500, 400) + [
            hline(8, 108, 300, 200), hline(9, 108, 300, 208),
            vline(10, 300, 108, 392),
        ] + fan_triangulated_band_h(11, 108, 300, 208, thickness=0.75)
        rings = _collect_fill_rings(paths)
        self.assertEqual(len(rings), 2)
        self.assertLess(max(r.short for r in rings), 0.5)
        self.assertEqual(_fill_seam_indices(rings, paths), {13, 14})
        network = detect_wall_network(paths)
        self.assertEqual(len(network.fill_polygons), 1)
        self.assertAlmostEqual(network.fill_polygons[0].area, 192 * 0.75, delta=0.5)
        rooms = detect_rooms(network, [], [], 1000.0, 800.0, [])
        corridor = next(r for r in rooms if abs(r.bbox[0] - 302.0) < 0.5)
        poly = ShapelyPolygon(corridor.evidence["polygon"])
        # No corridor vertex past the standoff beside the tip (the spike
        # put one at x=304), and 1px inside the standoff is corridor floor.
        for x, y in poly.exterior.coords:
            if abs(y - 208.75) < 8.0:
                self.assertLessEqual(x, 302.01, (x, y))
        self.assertTrue(poly.contains(ShapelyPoint(303.0, 208.75)))

    def test_tapering_wall_still_pairs(self):
        # A boundary wall drawn converging (s03's rear wall: 15.4 -> 11.7px
        # over 142px, a quarter of its spacing) is one band, not a chord:
        # the pair must survive the taper gate.
        paths = [
            hline(0, 100, 400, 100),
            path(1, [(100, 116), (400, 112)]),
        ]
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 1)
        self.assertGreaterEqual(network.segments[0].thickness_px, 11.0)
        self.assertLessEqual(network.segments[0].thickness_px, 17.0)


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

    def test_material_at_2_7_per_100px_qualifies(self):
        # WALL_WEAK_MATERIAL_PER_100PX is 2.2 marks/100px — 2.6/m at 1:50
        # (W-gate census 2026-09-04, 3.0 -> 2.2). Real partition hatch at
        # true scales: s02's thinnest OK band 3.4/100 = 4.1/m, s15/s17
        # 4.4-4.6/m, s01 4.5/m — and s16's real hatched wall between two
        # windows (crop-verified) measures 5.4/100 at f=0.5 = 3.2/m, which
        # FAILED the scaled 6.0 gate. Noise: s02's glazing strip plus ticks
        # 1.7/100 = 2.0/m, s04 1.4/m. 2.2 sits 1.23x under s16's wall and
        # 1.3x over s02's strip. Eight spread marks over a 300px hairline
        # band = 2.67/100 must pair; five (1.67, the glazing-strip class)
        # must not.
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 214, stroke_width=0.45),
        ]
        for i, x in enumerate(range(115, 390, 37)):     # 8 marks, span 0.86
            paths.append(path(10 + i, [(x, 213), (x + 12, 201)], stroke_width=0.3))
        network = detect_wall_network(paths)
        self.assertEqual(len(network.segments), 1)
        self.assertAlmostEqual(network.segments[0].thickness_px, 14.0, delta=0.5)

    def test_material_at_1_7_per_100px_does_not_qualify(self):
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 214, stroke_width=0.45),
        ]
        for i, x in enumerate(range(115, 390, 62)):     # 5 marks, span 0.83
            paths.append(path(10 + i, [(x, 213), (x + 12, 201)], stroke_width=0.3))
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


class TestThickMaterialPairs(unittest.TestCase):
    """Pier tier: strong faces spaced past WALL_MAX_THICKNESS_PX pair only
    on drawn material between them (floor-plans' bedroom chimney breast:
    a 19px wall bulging to 39px, hatched inside — unpaired, the hatch
    pocket survives free-space extraction as a phantom room). The fixture
    bulges to 44px — clear of the 36px plain cap whatever the W-gate
    recalibration settles on for it (40 was tried and reverted,
    2026-09-04)."""

    @staticmethod
    def _pier_paths(with_hatch):
        # Outer face x=100 full height; normal 20px band (inner x=120)
        # interrupted by a pier bulging to x=144 over y 300-400.
        paths = [
            vline(0, 100, 100, 500),
            vline(1, 120, 100, 300),
            hline(2, 120, 144, 300),
            vline(3, 144, 300, 400),
            hline(4, 120, 144, 400),
            vline(5, 120, 400, 500),
        ]
        if with_hatch:
            # 45-degree hatch inside the pier band, hairline pen (the real
            # pier's hatch is a demoted light grey — either way never a
            # strong face, but always material marks).
            for i, y in enumerate(range(305, 395, 15)):
                paths.append(path(
                    10 + i, [(106, y), (136, y + 30)], stroke_width=0.3,
                ))
        return paths

    def test_hatched_pier_pairs_past_normal_cap(self):
        network = detect_wall_network(self._pier_paths(with_hatch=True))
        thick = [s for s in network.segments
                 if s.thickness_px > WALL_MAX_THICKNESS_PX]
        self.assertEqual(len(thick), 1)
        seg = thick[0]
        self.assertAlmostEqual(seg.thickness_px, 44.0, delta=0.5)
        self.assertAlmostEqual(seg.p1[0], 122.0, delta=0.5)
        ys = sorted((seg.p1[1], seg.p2[1]))
        self.assertAlmostEqual(ys[0], 300.0, delta=2.0)
        self.assertAlmostEqual(ys[1], 400.0, delta=2.0)

    def test_bare_pier_spacing_does_not_pair(self):
        # Same geometry, no material: a face beside a corridor of pier-like
        # width must not become a wall band.
        network = detect_wall_network(self._pier_paths(with_hatch=False))
        self.assertFalse(any(s.thickness_px > WALL_MAX_THICKNESS_PX
                             for s in network.segments))


class TestPerBandMarkCap(unittest.TestCase):
    """The material-mark length cap is per band (_mark_len_cap): the
    page-wide WALL_HATCH_MAX_LEN_PX (48px) or the band's own 45-degree
    diagonal T*sqrt(2) plus 2px of slack, whichever is larger. W-gate census
    2026-09-04, row 11: hatch is clipped to the band it fills, so a
    cap-thickness band's strokes are ~51px (s02 51.5, s20 50.2, s01 55.7,
    s05 49.5 at f=0.5, s06 50.2) — 27-64% of in-band strokes exceeded the
    fixed cap on s05/s06/s12/s13/s20 and no thick-tier band over 34px could
    ever pass its own material gate."""

    FILLER = rect_room(500, 700, 100, 1000, 400)

    def test_forty_px_band_with_through_hatch_passes_thick_tier(self):
        # 40px band (over the 36px plain cap, inside the thick tier) hatched
        # face to face at 45 degrees: every stroke is 40*sqrt(2) = 56.6px,
        # over the page-wide 48px cap, under the band's own 58.6px cap.
        paths = [hline(0, 100, 400, 100), hline(1, 100, 400, 140)]
        x, i = 108.0, 10
        while x + 40.0 < 392.0:
            paths.append(path(i, [(x, 140.0), (x + 40.0, 100.0)], stroke_width=0.3))
            x += 6.0
            i += 1
        network = detect_wall_network(paths + self.FILLER)
        self.assertTrue(
            any(abs(s.thickness_px - 40.0) < 0.5 for s in network.segments),
            "40px through-hatched band did not pair in the thick tier",
        )

    def test_long_oblique_stroke_is_not_material_for_thin_band(self):
        # A 12px hairline band crossed by 59px 45-degree strokes (leader
        # lines, a winder's risers): the band's cap is max(48, 12*sqrt(2)+2)
        # = 48, so the strokes are not its material and it does not pair,
        # dense and spread as they are (8 over 300px = 2.7/100px).
        paths = [
            hline(0, 100, 400, 200, stroke_width=0.45),
            hline(1, 100, 400, 212, stroke_width=0.45),
        ]
        for i, x in enumerate(range(110, 390, 37)):
            paths.append(path(10 + i, [(x, 227.0), (x + 41.7, 185.3)], stroke_width=0.3))
        network = detect_wall_network(paths + self.FILLER)
        self.assertFalse(
            any(abs(s.thickness_px - 12.0) < 0.5 for s in network.segments)
        )

    def test_fifty_px_band_with_short_interior_hatch_pairs_in_thick_tier(self):
        # WALL_THICK_MATERIAL_MAX_PX is 56px — 475mm at 1:50 (W-gate census
        # 2026-09-04, 48 -> 56, moved only together with the per-band cap:
        # at f=0.5 a 56 cap is 28px and s05's 475mm wall pairs at exactly
        # 28px, so it falls from the THROUGH tier into the THICK tier, whose
        # fixed 24px mark cap could not see its 39px strokes). True class:
        # material-backed thick pairs at 377-400mm (s15, s20 47.2px = 1.01x
        # under the old cap), s16 305-336, s05 475; the false class —
        # hatched fixtures and floors — is gated by material. A 50px band
        # filled with SHORT interior strokes (a coarse pattern, 30px at
        # 45 degrees, none reaching a face) is not THROUGH-hatched and lands
        # in the through tier at 48, where it fails; in the thick tier its
        # interior marks are material.
        paths = [hline(0, 100, 400, 100), hline(1, 100, 400, 150)]
        x, i = 108.0, 10
        while x + 21.0 < 392.0:
            paths.append(path(i, [(x, 135.5), (x + 21.0, 114.5)], stroke_width=0.3))
            x += 6.0
            i += 1
        network = detect_wall_network(paths + self.FILLER)
        self.assertTrue(
            any(abs(s.thickness_px - 50.0) < 0.5 for s in network.segments),
            "50px band with short interior hatch did not pair in the thick tier",
        )

    def test_long_marks_count_only_face_to_face(self):
        # s17 room_0006's stair flight: two stringers 48px apart, two 8px
        # arrowhead barbs, a 54px cut line clipped stringer to stringer and
        # a 49px one touching only one stringer. Four marks over 141px is
        # exactly the material floor; a long stroke that is not through-
        # hatch is a cut line, not material, so the flight stays furniture.
        paths = [vline(0, 100, 100, 241), vline(1, 148, 100, 241)]
        paths += [
            path(10, [(118.0, 120.5), (124.0, 114.8)], stroke_width=1.0),   # barbs
            path(11, [(124.0, 114.8), (130.0, 120.5)], stroke_width=1.0),
            path(12, [(148.0, 206.0), (100.0, 233.0)], stroke_width=1.0),   # face to face
            path(13, [(148.0, 205.9), (123.8, 248.2)], stroke_width=1.0),   # one face only
        ]
        network = detect_wall_network(paths + self.FILLER)
        self.assertFalse(
            any(abs(s.thickness_px - 48.0) < 0.5 for s in network.segments)
        )
        # With BOTH long strokes clipped face to face they are through-hatch
        # and the four marks pair the band (the pin's negative control).
        paths[-1] = path(13, [(148.0, 190.0), (100.0, 217.0)], stroke_width=1.0)
        network = detect_wall_network(paths + self.FILLER)
        self.assertTrue(
            any(abs(s.thickness_px - 48.0) < 0.5 for s in network.segments)
        )


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

    def test_cross_corridor_pair_does_not_inflate_wall_run(self):
        # Another wall's face across a corridor of wall-like width pairs with
        # the left wall's outer face (spacing 35 < WALL_MAX_THICKNESS_PX) over
        # a short overlap. The redundancy collapse must not absorb that pair
        # into the left wall's run: its corridor-wide thickness would poison
        # the whole run (floor-plans bathroom: a 7.2px wall run took th 35.2
        # from a stair-corridor pair and fenced a 16px strip out of the room).
        paths = rect_room(0, 100, 100, 400, 300, thickness=8.0)
        paths.append(vline(8, 135.0, 240.0, 290.0))
        network = detect_wall_network(paths)
        runs = [
            s for s in network.segments
            if abs(s.p1[0] - s.p2[0]) < 1.0
            and 98.0 <= (s.p1[0] + s.p2[0]) / 2.0 <= 112.0
            and abs(s.p2[1] - s.p1[1]) >= 150.0
        ]
        self.assertTrue(runs, "left wall run missing from the network")
        for s in runs:
            self.assertLessEqual(s.thickness_px, 12.0)

    def test_local_pier_does_not_inflate_collinear_wall_run(self):
        # A jamb-scale pier (nib) drawn as a small box on the room side of
        # the right wall: its room-side face pairs with the wall's OUTER face
        # into a short, thicker centerline offset < COLLINEAR_OFFSET_TOL from
        # the band's own centerline. The collinear merge must not fuse the
        # two and carry the pier's thickness over the whole run (s03 kitchen:
        # a 16.5px nib pair stamped th 13.8 onto a 6px band over 272px and
        # held the room outline 6px off the wall; same signature on s02
        # (877,314) and s01 (818,907)).
        paths = rect_room(0, 100, 100, 400, 300, thickness=6.0)
        paths += [
            vline(8, 387.0, 190.0, 206.0),
            hline(9, 387.0, 394.0, 190.0),
            hline(10, 387.0, 394.0, 206.0),
        ]
        network = detect_wall_network(paths)
        runs = [
            s for s in network.segments
            if abs(s.p1[0] - s.p2[0]) < 1.0
            and 395.0 <= (s.p1[0] + s.p2[0]) / 2.0 <= 399.0
            and abs(s.p2[1] - s.p1[1]) >= 150.0
        ]
        self.assertTrue(runs, "right wall run missing from the network")
        for s in runs:
            self.assertLessEqual(s.thickness_px, 8.0)


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

    def test_bare_band_at_38px_does_not_pair(self):
        # WALL_MAX_THICKNESS_PX stays 36px (305mm at 1:50). The W-gate
        # census (2026-09-04) proposed 40 and iteration 2 tried it: the
        # 36-40px band holds drawn fixtures at wall spacing that spacing
        # cannot separate from walls — s02's WC wall face paired at 38.25px
        # with a hairline basin edge over the dashed section line's dashes
        # and notched the WC 14%; s01's kitchen units are 38.5px deep (600mm
        # at its true 1:92.2) and their side stubs paired — against s17's
        # real 37px cavity wall, whose reveal phantoms it removed. A bare
        # 38px pair is a corridor until a mark-class rule separates them.
        paths = [hline(0, 100, 400, 100), hline(1, 100, 400, 138)]
        paths += rect_room(500, 700, 100, 1000, 400)
        network = detect_wall_network(paths)
        self.assertFalse(
            any(abs(s.thickness_px - 38.0) < 0.5 for s in network.segments)
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
        bridges = _bridge_white_runs([a, b], gates=WALL_GATES_UNSCALED)
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
        self.assertEqual(
            _bridge_white_runs([a, b, c, d], gates=WALL_GATES_UNSCALED), []
        )

    def test_connected_components_bridge_once(self):
        # Three collinear clusters: closing a-b and b-c connects everything;
        # the redundant long chord a-c (also within gap range) is skipped.
        a = white_ring(100, 100, 120, 110)
        b = white_ring(150, 100, 170, 110)
        c = white_ring(195, 100, 215, 110)
        self.assertLessEqual(a.poly.distance(c.poly), WALL_JOINERY_BRIDGE_GAP_PX)
        self.assertEqual(
            len(_bridge_white_runs([a, b, c], gates=WALL_GATES_UNSCALED)), 2
        )


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
        # cross-section — the s07 signature, where
        # envelope-glued chaining deleted the plan's central wall belt.
        paths = rect_room(0, 100, 100, 400, 400) + [
            hline(50, 500, 800, 500), hline(51, 500, 650, 508),
            hline(52, 650, 800, 516), hline(53, 500, 650, 524),
            hline(54, 650, 800, 532),
        ]
        network = detect_wall_network(paths)
        inside = self._segments_inside(network, 495, 495, 805, 537)
        self.assertGreater(len(inside), 0)

    def test_short_pieces_form_a_field_and_flanking_walls_survive(self):
        # Radiator/grille fins: many short parallel same-pen strokes at
        # equal pitch between two wall faces. The fins are a striped field
        # (there is no rung length floor — short strokes at wall pitch five
        # deep are still never walls) and are demoted; the perpendicular
        # flanking wall pair is a different direction cluster and survives.
        paths = rect_room(0, 100, 100, 400, 400) + [
            vline(50, 500, 100, 400), vline(51, 530, 100, 400),
        ] + [
            hline(60 + i, 505, 525, 110 + i * 10.0, stroke_width=1.5)
            for i in range(20)
        ]
        network = detect_wall_network(paths)
        inside = self._segments_inside(network, 495, 95, 545, 405)
        self.assertGreater(len(inside), 0)
        used = network.paired_face_indices()
        self.assertFalse(used & set(range(60, 80)))

    def test_short_rung_field_is_demoted(self):
        # Stair treads / balustrade rungs: 7 same-pen strokes 40px long at
        # 13px pitch (s17's treads measure 47.7px, s18's ramp balustrade
        # 12.75px). Under the old 48px rung floor they stayed strong and
        # paired into 13px "walls" across the stair.
        paths = rect_room(0, 100, 100, 400, 400) + [
            hline(50 + i, 500, 540, 100 + i * 13.0) for i in range(7)
        ]
        network = detect_wall_network(paths)
        self.assertEqual(self._segments_inside(network, 495, 95, 545, 185), [])

    def test_long_face_beside_a_short_stack_keeps_its_rights(self):
        # A room's wall face coexists with a short equal-pitch stack (a
        # radiator's edge lines drawn parallel to the wall) over a fraction
        # of its length. Only the rungs lying in the stacked span are the
        # field; the wall face keeps its rights and the room's band pairs.
        paths = rect_room(0, 100, 100, 400, 400) + [
            hline(50 + i, 200, 240, 108 + (i + 1) * 12.0) for i in range(4)
        ]
        network = detect_wall_network(paths)
        top = [
            s for s in self._segments_inside(network, 95, 95, 405, 125)
            if abs(s.p1[1] - s.p2[1]) < 1.0
        ]
        self.assertGreater(len(top), 0)
        used = network.paired_face_indices()
        self.assertFalse(used & {50, 51, 52, 53})

    def test_hatch_field_forms_no_diagonal_walls(self):
        # A wall band's 45deg hatch: short same-pen strokes at a pitch far
        # tighter than any wall. Two strokes of one field pair with each
        # other like any parallel pen mates, and at an L-corner the phantom
        # diagonal band juts out of the wall and chamfers the room corner
        # (measured on floor-plans: strokes 28.1px apart cut ~16px off
        # room_0000's and room_0001's top-right corners). Pitch is what
        # proves the strokes are not walls, not their length or angle.
        paths = rect_room(0, 100, 100, 400, 400)
        idx = 50
        for i in range(20):
            # 135deg strokes at ~4px perpendicular pitch, 27px long, stepped
            # along the band exactly as CAD hatch is emitted.
            x = 500 + i * 5.7
            paths.append(path(idx, [(x, 220.0), (x + 19.2, 200.8)],
                              stroke_width=1.0))
            idx += 1
        network = detect_wall_network(paths)
        field = self._segments_inside(network, 495, 195, 640, 225)
        self.assertEqual(field, [])

    def test_stray_row_far_along_the_axis_does_not_break_the_run(self):
        # A 12-rung field with one unrelated same-pen stroke sitting at an
        # intermediate offset but FAR along the axis (s17: a 49px stroke
        # 2000px away). The stray row must be skipped, not treated as a
        # break in the run — otherwise the rungs past it stay strong (s03:
        # 3 of 22 roof-tile rungs survived and paired into phantom bands).
        paths = rect_room(0, 100, 100, 400, 400) + [
            vline(50 + i, 500 + i * 6.0, 100, 400) for i in range(12)
        ] + [vline(80, 515, 600, 700)]
        network = detect_wall_network(paths)
        field = self._segments_inside(network, 495, 95, 575, 405)
        self.assertEqual(field, [])

    def test_collinear_wall_line_far_from_the_field_is_not_a_rung(self):
        # A room's wall face that merely happens to be collinear with one
        # rung of a distant field (s17: the WC's top face at y=1167 shares
        # its offset with a roof-tile rung 2000px to the right) is not a
        # member of that rung: rows are extent-aware, so the field demotes
        # and the wall face still pairs.
        paths = [
            hline(50 + i, 1500, 1800, 100 + i * 6.0) for i in range(12)
        ] + rect_room(0, 100, 118, 400, 400)
        network = detect_wall_network(paths)
        field = self._segments_inside(network, 1495, 95, 1805, 175)
        self.assertEqual(field, [])
        top = [
            s for s in self._segments_inside(network, 95, 110, 405, 135)
            if abs(s.p1[1] - s.p2[1]) < 1.0
        ]
        self.assertGreater(len(top), 0)

    def test_rung_split_by_a_wide_text_mask_still_chains(self):
        # A course line interrupted by a text mask wider than the touch gap
        # is two extent-separated pieces at one offset. Both lie inside the
        # field's span, so both are that rung — the second must not read as
        # a zero-pitch break in the run.
        paths = rect_room(0, 100, 100, 400, 400)
        field = []
        for p in paving_field(50, 500, 100):
            if (p.points[0][1] == p.points[1][1]
                    and abs(p.points[0][1] - 193.0) < 1.0):
                field.append(hline(p.path_index, 500.0, 580.0, 193.0,
                                   stroke_width=1.05))
                field.append(hline(p.path_index + 500, 610.0, 686.0, 193.0,
                                   stroke_width=1.05))
            else:
                field.append(p)
        network = detect_wall_network(paths + field)
        inside = self._segments_inside(network, 495, 95, 700, 300)
        self.assertEqual(inside, [])

    def test_wall_pitch_diagonal_pair_survives(self):
        # The lattice rule keys on PITCH, not on being diagonal: a genuine
        # 45deg bay wall (5-1133) is two faces at wall spacing and must
        # still pair.
        paths = rect_room(0, 100, 100, 400, 400) + [
            path(50, [(500, 300), (600, 200)], stroke_width=1.5),
            path(51, [(511, 311), (611, 211)], stroke_width=1.5),
        ]
        network = detect_wall_network(paths)
        bay = self._segments_inside(network, 495, 195, 615, 315)
        self.assertGreater(len(bay), 0)


    def test_fill_stub_does_not_launder_wall_fill_onto_a_long_stroke(self):
        # A wall-rated fill ring's short outline edge (a jamb stub) is
        # collinear with a 350px stroked line above it (a roof-tile stripe
        # on s03). Merging them must not stamp wall_fill — fill evidence —
        # over the whole stroke: the run's fill members cover 5% of it.
        stub = _Seg(p1=(100.0, 500.0), p2=(100.0, 517.0), indices={1},
                    wall_fill=True, pen=None)
        stroke = _Seg(p1=(100.0, 150.0), p2=(100.0, 500.0), indices={2},
                      stroked=True, stroke_width=1.5, pen=(0.6, 0.6, 0.6))
        merged = _merge_collinear_segs([stub, stroke], gap_px=6.0)
        self.assertEqual(len(merged), 1)
        self.assertFalse(merged[0].wall_fill)
        # Control: a fill outline coincident with its own drawn-over stroke
        # keeps the flag.
        outline = _Seg(p1=(100.0, 150.0), p2=(100.0, 500.0), indices={3},
                       wall_fill=True, pen=None)
        merged = _merge_collinear_segs([outline, stroke], gap_px=6.0)
        self.assertEqual(len(merged), 1)
        self.assertTrue(merged[0].wall_fill)


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

    def test_dimension_line_with_arrowheads_excluded(self):
        # Open arrowheads — two short strokes meeting AT the endpoint on
        # opposite sides of the line (s16: 9px barbs at ~12deg) — are the
        # other common dimension terminator; the line is annotation and must
        # not pair with the wall face below (measured on s16: an unrecognized
        # "3550" dimension line and its end bar fenced a 205x38px strip out
        # of the room as a phantom).
        dim = [
            hline(50, 150, 350, 80),
            path(51, [(150.0, 80.0), (159.0, 78.0)]),
            path(52, [(150.0, 80.0), (159.0, 82.0)]),
            path(53, [(350.0, 80.0), (341.0, 78.0)]),
            path(54, [(350.0, 80.0), (341.0, 82.0)]),
        ]
        paths = rect_room(0, 100, 100, 400, 400) + dim
        network = detect_wall_network(paths)
        self.assertNotIn(50, network.paired_face_indices())
        # The open head drawn base-first (s16): barb bases straddle the
        # endpoint 2px either side and the tip sits on the line 9px beyond.
        open_head = dim[:1] + [
            path(51, [(150.0, 78.0), (141.0, 80.0)]),
            path(52, [(150.0, 82.0), (141.0, 80.0)]),
            path(53, [(350.0, 78.0), (359.0, 80.0)]),
            path(54, [(350.0, 82.0), (359.0, 80.0)]),
        ]
        paths = rect_room(0, 100, 100, 400, 400) + open_head
        network = detect_wall_network(paths)
        self.assertNotIn(50, network.paired_face_indices())
        # Barbs on ONE side only (a hatch stroke pair touching a face end
        # from inside the band) are no arrowhead: the line stays a face.
        one_sided = dim[:1] + [
            path(51, [(150.0, 80.0), (159.0, 78.0)]),
            path(52, [(150.0, 80.0), (159.0, 76.0)]),
            path(53, [(350.0, 80.0), (341.0, 78.0)]),
            path(54, [(350.0, 80.0), (341.0, 76.0)]),
        ]
        paths = rect_room(0, 100, 100, 400, 400) + one_sided
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


class TestAnnotationLayerVeto(unittest.TestCase):
    """Linework on an annotation-named layer (section callouts, dimension
    and text layers) is never wall evidence, whatever its pen: on s04 a
    page-wide cyan section callout line (layer "Symbols_Dynamic Callouts",
    1.19px — the wall pen's width) paired over a short subspan with a
    parallel wall face, took full-length barrier rights and chopped rooms
    0000/0001/0003 at y=767."""

    def _room_with_crossing(self, layer):
        paths = rect_room(0, 100, 100, 600, 400)
        # Page-wide line at wall pen, on `layer`, crossing the room, plus a
        # short parallel stub 10px away that it would pair with.
        paths.append(hline(8, 20, 900, 250, layer=layer))
        paths.append(hline(9, 300, 340, 260))
        return paths

    def test_callout_layer_line_never_pairs_or_barriers(self):
        paths = self._room_with_crossing("Symbols_Dynamic Callouts")
        net = detect_wall_network(paths, [])
        self.assertNotIn(8, net.paired_face_indices())
        self.assertFalse(any(8 in f.indices for f in net.faces))
        rooms = detect_rooms(net, [], [], 1000.0, 800.0, [])
        self.assertEqual(len(rooms), 1)
        self.assertAlmostEqual(rooms[0].bbox[3], 390.0, delta=2.5)

    def test_unlayered_line_still_pairs(self):
        # Control: the same geometry without the layer keeps its rights.
        paths = self._room_with_crossing(None)
        net = detect_wall_network(paths, [])
        self.assertIn(8, net.paired_face_indices())

    def test_wall_layer_and_grouping_layer_stay_eligible(self):
        for layer in ("RR_Walls", "Wall Dimensions", "TEXT"):
            paths = self._room_with_crossing(layer)
            net = detect_wall_network(paths, [])
            self.assertIn(8, net.paired_face_indices(), layer)


class TestFarSidePairs(unittest.TestCase):
    """A wall face paired ACROSS the room with parallel wall-pen ink — a
    kitchen counter front, a wardrobe front — at just under the thickness
    cap (measured on s03: worktop outline 35.2px off the inner faces). The
    tighter kept pair on the far side of the shared face is the wall; the
    material-less band on this side is free space."""

    def _thicknesses(self, network):
        return sorted(round(s.thickness_px, 1) for s in network.segments)

    def test_counter_front_does_not_pair_with_wall_face(self):
        paths = rect_room(0, 100, 100, 500, 400)
        # Counter front 34px inside the left wall's inner face (x=108).
        paths.append(vline(50, 142, 150, 350))
        network = detect_wall_network(paths)
        self.assertNotIn(34.0, self._thicknesses(network))
        self.assertIn(8.0, self._thicknesses(network))

    def test_counter_front_beside_filled_band_does_not_pair(self):
        # Wall drawn as a filled rectangle with stroked outline faces (the
        # Vectorworks signature) — the band on the far side of the shared
        # face is a filled band, not a face pair.
        wall = [
            path(0, [(100, 100), (100, 400), (108, 400), (108, 100)],
                 item_type="re", fill=(0.6, 0.6, 0.6)),
            vline(1, 100, 100, 400), vline(2, 108, 100, 400),
        ]
        paths = wall + [vline(3, 142, 150, 350)]
        network = detect_wall_network(paths)
        self.assertNotIn(34.0, self._thicknesses(network))

    def test_hatched_cavity_keeps_its_pair(self):
        # Leaf / hatched cavity / leaf: the cavity pair shares a face with
        # each tighter leaf pair but carries drawn material, so it stays.
        paths = wall_band_h(0, 100, 400, 100) + wall_band_h(2, 100, 400, 130)
        idx = 10
        for x in range(104, 392, 10):
            paths.append(path(idx, [(x, 129), (x + 10, 109)], stroke_width=0.6))
            idx += 1
        network = detect_wall_network(paths)
        # The redundancy collapse may fold the 22px cavity pair into the
        # 30px leaf-outer/leaf-inner pair; either way the cavity stays wall.
        self.assertGreaterEqual(max(self._thicknesses(network)), 22.0)

    def test_unhatched_corridor_between_walls_does_not_pair(self):
        # Two 8px walls 30px apart: the inner faces pair across the corridor
        # at 30px, sharing a face with each real wall — dropped, the walls
        # themselves stay.
        paths = wall_band_h(0, 100, 400, 100) + wall_band_h(2, 100, 400, 138)
        network = detect_wall_network(paths)
        ths = self._thicknesses(network)
        self.assertNotIn(30.0, ths)
        self.assertEqual(ths.count(8.0), 2)

    def test_counter_front_loses_lone_face_rights(self):
        # The partner of a dropped far-side pair, paired with nothing else,
        # is the fixture front: it must not keep the pen-weight lone-barrier
        # rights the rooms stage grants stroked faces, or the counter strip
        # still fences off.
        paths = rect_room(0, 100, 100, 500, 400) + [vline(50, 142, 150, 350)]
        network = detect_wall_network(paths)
        counter = [f for f in network.faces if 50 in f.indices]
        self.assertEqual(len(counter), 1)
        self.assertFalse(counter[0].stroked)
        wall = [f for f in network.faces if 4 in f.indices]
        self.assertTrue(wall and all(f.stroked for f in wall))


class TestVectorTextExclusion(unittest.TestCase):
    """Stick-font text drawn as line strokes (s06/s11/s16/s20: no text
    spans, every label is a cluster of short `l` items in the wall pen)
    must never enter face collection: at 1:100 the glyph stems clear the
    scaled face floor and the parallel stems of an H pair at wall-like
    spacing into a mini band, notching the room outline around the word
    (s06 BATH & TOILET / LANDING)."""

    @staticmethod
    def _word(start_idx, x, y, **kw):
        """'HITL' in 14px stick glyphs, cap line y, baseline y + 14."""
        h = 14.0
        return [
            vline(start_idx, x, y, y + h, **kw),                    # H
            vline(start_idx + 1, x + 6, y, y + h, **kw),
            hline(start_idx + 2, x, x + 6, y + 7, **kw),
            vline(start_idx + 3, x + 14, y, y + h, **kw),           # I
            hline(start_idx + 4, x + 20, x + 30, y, **kw),          # T
            vline(start_idx + 5, x + 25, y, y + h, **kw),
            vline(start_idx + 6, x + 36, y, y + h, **kw),           # L
            hline(start_idx + 7, x + 36, x + 44, y + h, **kw),
        ]

    def test_glyph_row_inside_room_never_becomes_faces(self):
        word = self._word(50, 200, 200)
        paths = rect_room(0, 100, 100, 400, 400) + word
        network = detect_wall_network(paths)
        face_idx = {i for f in network.faces for i in f.indices}
        self.assertFalse(face_idx & {p.path_index for p in word})
        # The room walls themselves are untouched.
        self.assertEqual(len(network.paired_face_indices() & set(range(8))), 8)

    def test_glyph_row_touching_wall_linework_is_not_text(self):
        # The same strokes standing ON a wall face (jamb nibs, end caps)
        # are connected wall ink, not freestanding glyphs.
        word = self._word(50, 200, 108)      # tops land on the inner face y=108
        paths = rect_room(0, 100, 100, 400, 400) + word
        network = detect_wall_network(paths)
        face_idx = {i for f in network.faces for i in f.indices}
        self.assertTrue(face_idx & {p.path_index for p in word})

    def test_lone_pier_and_parallel_stroke_row_are_not_text(self):
        from detection.walls import _vector_text_indices
        # A freestanding hatched pier box: one glyph-sized component, no row.
        pier = [
            hline(50, 200, 220, 200), hline(51, 200, 220, 216),
            vline(52, 200, 200, 216), vline(53, 220, 200, 216),
            path(54, [(200.0, 216.0), (216.0, 200.0)]),
            path(55, [(204.0, 216.0), (220.0, 200.0)]),
        ]
        self.assertEqual(_vector_text_indices(pier), set())
        # Three mutually parallel single strokes at glyph spacing (loose
        # hatch) have no multi-stroke member and no angle diversity.
        strokes = [
            path(60 + k, [(200.0 + 8 * k, 200.0), (208.0 + 8 * k, 214.0)])
            for k in range(3)
        ]
        self.assertEqual(_vector_text_indices(strokes), set())
        # The real word is recognised on its own.
        word = self._word(70, 200, 200)
        self.assertEqual(
            _vector_text_indices(word), {p.path_index for p in word}
        )
