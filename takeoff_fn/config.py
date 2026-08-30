"""Constants for the takeoff callable.

Runtime sizing is justified in the design doc: 2 GiB matches rivet-mind's
heaviest precedent and covers the tmpfs cost of the output tree, which is
charged against memory on Cloud Functions.
"""
from __future__ import annotations

REGION = "europe-west2"
MEMORY_MIB = 2048
TIMEOUT_SECONDS = 900
MAX_INSTANCES = 3

# Vertex location for the region-classification and room-label calls, so
# drawings do not leave the region the rest of the app runs in.
VERTEX_LOCATION = "europe-west2"

TAKEOFF_COLLECTION = "takeoffs"

# A takeoff left at "processing" longer than this is assumed dead (an
# instance killed by timeout or OOM) and may be re-measured. rivet-mind owns
# the reaper that sweeps such records; this only stops a live run being
# double-started.
STALE_PROCESSING_SECONDS = 1800

STATUS_PROCESSING = "processing"
STATUS_AWAITING_REVIEW = "awaiting_review"
STATUS_FAILED = "failed"
STATUS_APPROVED = "approved"

# Uploaded on every run. ~7 MB/page.
STANDARD_ARTIFACTS = (
    "page.svg",
    "takeoff.json",
    "final_entities.json",
    "render.png",
    "overlay.png",
    "primitives.json",
    "candidates.json",
    "regions.json",
)

# Uploaded only when the request sets debug: true. ~21 MB/page.
DEBUG_ARTIFACTS = (
    "debug_trace.json",
    "debug_viewer.html",
)

# Written by run_extract at the run root, once every page has finished.
RUN_ARTIFACTS = (
    "summary.json",
    "warnings.json",
)

SVG_ARTIFACT = "page.svg"
