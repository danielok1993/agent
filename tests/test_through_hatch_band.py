"""A band hatched THROUGH — every diagonal stroke ending on both faces — is a
drawn wall section whatever its thickness.

s05 (1:100, f=0.5) draws its first-floor left external wall as a 28px band
(~475mm) filled with 104 strokes at 135°, each 39px = 28 × √2 long, i.e.
clipped face-to-face by the hatch tool, at 6.2px pitch. 28px is past both the
scaled pair cap (18px) and the scaled thick-material cap (24px), and the
strokes are past the scaled material-mark length cap (24px), so the faces
never paired and the hatch interior was fenced as a 24×468px "room". The
sheet's other bands top out at 17.8px; corpus bands at identity reach 39px.

Through-hatch is the plan convention for CUT material: a floor pattern or a
fixture's hatch is clipped to its own boundary, never to two wall-pen faces
at wall spacing. Hatch that stops short of the faces is not through-hatch.
Coordinates at identity scale: a 64px band, hatch at 6px pitch. (The fixture
was s05's 56px-at-identity band until the W-gate census moved the thick cap
to 56 on 2026-09-04; s05's wall now pairs in the thick tier on its own
per-band mark cap, and this file pins the tier ABOVE it.)
"""
import math
import unittest

from detection.walls import detect_wall_network, WALL_THICK_MATERIAL_MAX_PX
from tests.test_wall_network import hline, path, rect_room, vline, wall_band_h

X0, X1, Y, TH = 100.0, 500.0, 200.0, 64.0
PITCH = 6.0


def hatch(start_idx, inset=0.0):
    """45° strokes across the band; inset > 0 stops them short of each face."""
    out = []
    x = X0 + 8.0
    i = start_idx
    while x + TH < X1 - 8.0:
        out.append(path(i, [(x + inset, Y + TH - inset), (x + TH - inset, Y + inset)]))
        x += PITCH
        i += 1
    return out


# WALL_NETWORK_MIN_SEGMENTS empties a network with fewer than four segments;
# an ordinary room elsewhere on the page keeps the band under test visible.
FILLER = rect_room(500, 700.0, 100.0, 1000.0, 400.0)


def band_segments(paths):
    net = detect_wall_network(paths + FILLER, [])
    return [s for s in net.segments if abs(s.thickness_px - TH) < 1.0]


class ThroughHatchBandTests(unittest.TestCase):
    def test_band_is_past_the_thick_tier(self):
        self.assertGreater(TH, WALL_THICK_MATERIAL_MAX_PX)

    def test_through_hatched_wide_band_pairs(self):
        paths = wall_band_h(0, X0, X1, Y, TH) + hatch(10)
        self.assertTrue(band_segments(paths), "through-hatched band did not pair")

    def test_hatch_stopping_short_of_the_faces_does_not_pair(self):
        paths = wall_band_h(0, X0, X1, Y, TH) + hatch(10, inset=8.0)
        self.assertFalse(band_segments(paths))

    def test_short_run_beside_a_corner_pairs_on_return_clipped_strokes(self):
        # A 44px run whose top meets a perpendicular return: the strokes over
        # its first band-width end on the return, not the far face. They are
        # still through-hatch (clipped by a boundary of the same region).
        # As on s05: the outer face runs on past the corner run, the inner
        # face is the short piece (a dashed run merged into 44px).
        y0, y1 = Y, Y + 44.0
        faces = [vline(0, X0, y0, y1 + TH), vline(1, X0 + TH, y0, y1), hline(2, X0, X0 + TH, y0)]
        # s05's hatch is two interleaved series (3.1px along the face);
        # that pitch keeps the strokes under the stair tread-run floor,
        # which a single coarser fan of corner-clipped strokes trips.
        strokes, i, y = [], 10, y0 + 3.0
        while y < y1 + TH:
            # 45° stroke from the left face at y up-right; clipped at the return
            top = max(y - TH, y0)
            strokes.append(path(i, [(X0, y), (X0 + (y - top), top)]))
            y += PITCH / 2.0
            i += 1
        self.assertTrue(band_segments(faces + strokes))

    def test_bare_wide_pair_does_not_pair(self):
        paths = wall_band_h(0, X0, X1, Y, TH)
        self.assertFalse(band_segments(paths))


class ThroughHatchCapReferenceTests(unittest.TestCase):
    """WALL_THROUGH_HATCH_MAX_PX is 72px — 610mm at 1:50 (W-gate census
    2026-09-04). The true class is s05's 475mm wall (28px at f=0.5 = 56px at
    identity): the old 64px cap left it 1.14x of headroom, 72 leaves 1.28x.
    The false class — through-hatched floors and fixtures — starts at 81.5px
    on s01 (1272mm at its true 1:92.2, detected at identity; 1.13x over 72),
    66.5-68px on s05 at f=0.5 (1.13-1.15m) and 94px on s20. A 68px band
    (575mm) hatched through must pair; bare, it must not."""

    TH68 = 68.0

    def _band(self, hatched):
        paths = wall_band_h(0, X0, X1, Y, self.TH68)
        if hatched:
            x, i = X0 + 8.0, 10
            while x + self.TH68 < X1 - 8.0:
                paths.append(path(i, [(x, Y + self.TH68), (x + self.TH68, Y)]))
                x += PITCH
                i += 1
        net = detect_wall_network(paths + FILLER, [])
        return [s for s in net.segments if abs(s.thickness_px - self.TH68) < 1.0]

    def test_68px_through_hatched_band_pairs(self):
        self.assertTrue(self._band(hatched=True), "68px through-hatched band did not pair")

    def test_68px_bare_pair_does_not_pair(self):
        self.assertFalse(self._band(hatched=False))

    def test_s05_wall_keeps_margin_at_half_scale(self):
        # s05's 28px band at f=0.5 must sit >= 1.25x under the scaled cap.
        from detection.walls import WallGates
        self.assertGreaterEqual(WallGates.at(0.5).WALL_THROUGH_HATCH_MAX_PX, 28.0 * 1.25)


if __name__ == "__main__":
    unittest.main()
