"""Region filtering tests (layout/filter.py)."""
import unittest

from models import ImageRef, PageData, PathPrimitive, Region, TextSpan
from layout.filter import filter_page_data, region_text_spans

PAGE_W, PAGE_H = 1000.0, 800.0


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def span(text, x0, y0, x1, y1):
    return TextSpan(text=text, bbox=(x0, y0, x1, y1), font="Helvetica",
                    size=10.0, color=0, block_no=0, line_no=0)


def region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


class TestFilterPageData(unittest.TestCase):
    def setUp(self):
        self.left = path(0, 100.0, 100.0, 200.0, 200.0)     # centre (150,150)
        self.right = path(1, 600.0, 100.0, 700.0, 200.0)    # centre (650,150)
        self.outside = path(2, 800.0, 600.0, 900.0, 700.0)  # centre (850,650)
        self.page = PageData(
            page_number=1, width_px=PAGE_W, height_px=PAGE_H,
            paths=[self.left, self.right, self.outside],
            text_spans=[span("PLAN", 120.0, 220.0, 180.0, 232.0),
                        span("NOTES", 810.0, 610.0, 890.0, 622.0)],
            images=[ImageRef(xref=1, bbox=(110.0, 110.0, 190.0, 190.0),
                             width=80, height=80, colorspace="DeviceRGB",
                             pixel_area=0.01)],
            ocg_names=["walls"], page_type="vector-rich",
        )
        self.r0 = region("region_0000", (50.0, 50.0, 300.0, 300.0))
        self.r1 = region("region_0001", (550.0, 50.0, 750.0, 300.0))

    def test_keeps_only_primitives_whose_centre_is_in_a_region(self):
        out = filter_page_data(self.page, [self.r0, self.r1])
        self.assertEqual([p.path_index for p in out.paths], [0, 1])

    def test_page_dimensions_are_preserved(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual(out.width_px, PAGE_W)
        self.assertEqual(out.height_px, PAGE_H)

    def test_page_metadata_is_preserved(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual(out.page_number, 1)
        self.assertEqual(out.ocg_names, ["walls"])
        self.assertEqual(out.page_type, "vector-rich")

    def test_text_spans_and_images_are_filtered_too(self):
        out = filter_page_data(self.page, [self.r0])
        self.assertEqual([s.text for s in out.text_spans], ["PLAN"])
        self.assertEqual(len(out.images), 1)

    def test_original_page_data_is_not_mutated(self):
        filter_page_data(self.page, [self.r0])
        self.assertEqual(len(self.page.paths), 3)
        self.assertEqual(len(self.page.text_spans), 2)

    def test_regions_covering_everything_reproduce_the_original_path_set(self):
        whole = region("region_0000", (0.0, 0.0, PAGE_W, PAGE_H))
        out = filter_page_data(self.page, [whole])
        self.assertEqual([p.path_index for p in out.paths],
                         [p.path_index for p in self.page.paths])

    def test_empty_region_list_keeps_nothing(self):
        out = filter_page_data(self.page, [])
        self.assertEqual(out.paths, [])


class TestRegionTextSpans(unittest.TestCase):
    def test_returns_only_spans_inside_the_given_regions(self):
        page = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                        text_spans=[span("DOOR SCHEDULE", 600.0, 600.0, 750.0, 615.0),
                                    span("KITCHEN", 100.0, 100.0, 160.0, 112.0)])
        sched = region("region_0000", (550.0, 550.0, 800.0, 700.0), "schedule_table")
        self.assertEqual([s.text for s in region_text_spans(page, [sched])],
                         ["DOOR SCHEDULE"])


if __name__ == "__main__":
    unittest.main()
