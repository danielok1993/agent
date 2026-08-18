"""Schedule detection — tables carry real bboxes.

detect_schedules used to emit bbox (0, 0, 0, 0) because pdfplumber's
extract_tables() returns bare text grids. Zero-area bboxes are unmatchable
in the regression sweep (iou() scores them 0.0 by design) and NMS's
center-distance rule collapses all of them onto one survivor, so every
confirmed schedule verdict reads as LOST forever. Tables now arrive as
{"bbox": <150-DPI px bbox>, "rows": <text grid>} and the candidate carries
the table's real bbox.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import fitz

from detection.schedules import detect_schedules
from extraction.extractor import SCALE
from extraction.plumber import extract_plumber_page


def _table(bbox, rows):
    return {"bbox": bbox, "rows": rows}


SCHEDULE_ROWS = [
    ["MARK", "WIDTH", "HEIGHT"],
    ["D1", "900", "2100"],
    ["D2", "826", "2040"],
]

NEUTRAL_ROWS = [
    ["AAA", "BBB"],
    ["CCC", "DDD"],
    ["EEE", "FFF"],
]


class TestDetectSchedulesBBox(unittest.TestCase):
    def test_candidate_carries_table_bbox(self):
        bbox = (100.0, 200.0, 500.0, 400.0)
        cands = detect_schedules([], [_table(bbox, SCHEDULE_ROWS)])
        self.assertEqual(len(cands), 1)
        self.assertEqual(tuple(cands[0].bbox), bbox)

    def test_two_tables_keep_distinct_bboxes(self):
        a = (100.0, 200.0, 500.0, 400.0)
        b = (600.0, 200.0, 900.0, 500.0)
        cands = detect_schedules(
            [], [_table(a, SCHEDULE_ROWS), _table(b, SCHEDULE_ROWS)])
        self.assertEqual([tuple(c.bbox) for c in cands], [a, b])

    def test_keyword_table_scores_higher_than_neutral(self):
        keyword, = detect_schedules([], [_table((0, 0, 10, 10), SCHEDULE_ROWS)])
        neutral, = detect_schedules([], [_table((0, 0, 10, 10), NEUTRAL_ROWS)])
        self.assertEqual(keyword.confidence, 0.60)
        self.assertEqual(neutral.confidence, 0.35)

    def test_row_col_and_density_gates_still_hold(self):
        too_few_rows = _table((0, 0, 10, 10), SCHEDULE_ROWS[:2])
        too_few_cols = _table((0, 0, 10, 10), [["a"], ["b"], ["c"]])
        too_sparse = _table(
            (0, 0, 10, 10),
            [["x", None, None, None, None, None, None, None]] +
            [[None] * 8 for _ in range(7)],
        )
        self.assertEqual(
            detect_schedules([], [too_few_rows, too_few_cols, too_sparse]), [])


class TestPlumberTableBBox(unittest.TestCase):
    """extract_plumber_page must surface each table's bbox, normalized to
    150-DPI pixel space with the same bare-SCALE convention as every other
    pdfplumber object in the module."""

    GRID = (100.0, 100.0, 300.0, 200.0)  # points, top-left origin

    def _make_pdf(self) -> str:
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        x0, y0, x1, y1 = self.GRID
        cols = [x0, (x0 + x1) / 2, x1]
        rows = [y0, y0 + 25, y0 + 50, y0 + 75, y1]
        for x in cols:
            page.draw_line((x, y0), (x, y1))
        for y in rows:
            page.draw_line((x0, y), (x1, y))
        cells = [["MARK", "WIDTH"], ["D1", "900"], ["D2", "826"], ["D3", "926"]]
        for r, (top, text_row) in enumerate(zip(rows, cells)):
            for c, text in enumerate(text_row):
                page.insert_text((cols[c] + 5, top + 18), text, fontsize=8)
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        doc.save(path)
        doc.close()
        return path

    def test_table_bbox_is_grid_bbox_in_pixel_space(self):
        path = self._make_pdf()
        try:
            plumber_page = extract_plumber_page(path, 0)
        finally:
            os.unlink(path)
        tables = plumber_page["tables"]
        self.assertEqual(len(tables), 1)
        self.assertIsInstance(tables[0], dict)
        bbox = tables[0]["bbox"]
        expected = tuple(v * SCALE for v in self.GRID)
        for got, want in zip(bbox, expected):
            self.assertAlmostEqual(got, want, delta=3.0)
        flat = " ".join(
            str(cell) for row in tables[0]["rows"] for cell in row if cell)
        self.assertIn("MARK", flat)

    def test_detect_schedules_accepts_plumber_output_end_to_end(self):
        path = self._make_pdf()
        try:
            plumber_page = extract_plumber_page(path, 0)
        finally:
            os.unlink(path)
        cands = detect_schedules([], plumber_page["tables"])
        self.assertEqual(len(cands), 1)
        self.assertGreater(
            (cands[0].bbox[2] - cands[0].bbox[0]) *
            (cands[0].bbox[3] - cands[0].bbox[1]),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
