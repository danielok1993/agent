"""The confirmed door-less narrow spaces the ceiling alone holds out (s07's
cupboard, s15's space, s20's passage), rendered with zoom16's overlay.
Usage: .venv/bin/python tools/census_scratch/step16/zoom16_true.py OUT_DIR
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zoom16  # noqa: E402

TARGETS = [
    ("s07", "cupboard_confirmed_610mm_context", (454, 190, 486, 290), 80, 3.0),
    ("s15", "space_confirmed_601mm_context", (766, 1549, 833, 1669), 90, 2.5),
    ("s20", "passage_confirmed_599mm_context", (554, 2812, 948, 2878), 90, 1.8),
]

if __name__ == "__main__":
    zoom16.main(Path(sys.argv[1]), "step16", TARGETS)
