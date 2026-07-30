"""Region outlines on the overlay (extraction/renderer.py)."""
import os
import shutil
import tempfile
import unittest

from PIL import Image

from models import Entity, Region
from extraction.renderer import REGION_OUTLINE_COLORS, draw_overlay


class TestDrawOverlayWithRegions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.render = os.path.join(self.tmp, "render.png")
        Image.new("RGB", (400, 300), (255, 255, 255)).save(self.render)
        self.out = os.path.join(self.tmp, "overlay.png")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overlay_is_written_without_regions(self):
        draw_overlay(self.render, [], [], self.out)
        self.assertTrue(os.path.exists(self.out))

    def test_overlay_is_written_with_regions(self):
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [], [], self.out, regions=regions)
        self.assertTrue(os.path.exists(self.out))

    def test_region_outline_changes_pixels(self):
        draw_overlay(self.render, [], [], self.out)
        plain = Image.open(self.out).convert("RGB").tobytes()
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [], [], self.out, regions=regions)
        with_regions = Image.open(self.out).convert("RGB").tobytes()
        self.assertNotEqual(plain, with_regions)

    def test_entities_still_draw_alongside_regions(self):
        entity = Entity(entity_id="door_0001", entity_type="door",
                        bbox=(50.0, 50.0, 90.0, 90.0), confidence=0.8,
                        source="heuristic")
        regions = [Region(region_id="region_0000", bbox=(10.0, 10.0, 200.0, 200.0),
                          region_type="floor_plan")]
        draw_overlay(self.render, [entity], [], self.out, regions=regions)
        self.assertTrue(os.path.exists(self.out))

    def test_floor_plan_and_other_types_use_different_colours(self):
        self.assertNotEqual(REGION_OUTLINE_COLORS["floor_plan"],
                            REGION_OUTLINE_COLORS["other"])


if __name__ == "__main__":
    unittest.main()
