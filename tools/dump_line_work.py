"""Write one corpus sheet's line_work block, as takeoff.json carries it.

The web app's fixture (rivet-mind
src/features/takeoff/fixtures/takeoff.json) is sheet s02 page 1 and predates
line_work. Regenerating it through pipeline.py would re-run region
classification and room labelling — Gemini calls the fixture does not need.
This walks the three detection stages line_work depends on and nothing else.

Writes the JSON itself, rather than printing it, because `import fitz`
(pulled in transitively via tools/_corpus_page.py) puts a deprecation
warning on stdout — a `> file.json` redirect would have silently captured
that warning as invalid JSON ahead of the real output.

Usage:
    python tools/dump_line_work.py s02 1 /tmp/line_work.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detection.doors.assembly import door_open_leaf_path_indices  # noqa: E402
from detection.doors.detect import detect_doors  # noqa: E402
from detection.walls import detect_wall_network  # noqa: E402
from takeoff.document import line_work_dict  # noqa: E402
from tools._corpus_page import load_detection_pages  # noqa: E402


def main() -> int:
    slug = sys.argv[1]
    page_number = int(sys.argv[2])
    out_path = Path(sys.argv[3])
    for dp in load_detection_pages(slug, [page_number]):
        pd = dp.page_data
        doors = detect_doors(pd.paths, pd.text_spans, None,
                             scale_factor=dp.scale_factor)
        network = detect_wall_network(
            pd.paths, pd.text_spans,
            exclude_path_indices=door_open_leaf_path_indices(doors, pd.paths),
            scale_factor=dp.scale_factor,
        )
        out_path.write_text(json.dumps(line_work_dict(network)))
        print(f"{slug} page {page_number} -> {out_path}")
        return 0
    print(f"{slug}: no page {page_number}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
