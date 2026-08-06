"""Ask Gemini what each segmented region is.

One call per page. Each region goes as its own crop rather than one full-page
image: Google's docs state images are "cropped and scaled into 768x768 pixel
tiles", and these sheets are A1 (3508x4967px at 150 DPI), so a whole-sheet image
loses the detail that distinguishes a floor plan from an elevation. A 1536px
crop is 2x2 tiles, roughly 1,000 tokens. The per-request limit is 3,600 images,
so region count is never a constraint.

HISTORICAL, SUPERSEDED — do not read as validation of the code as it now
stands. A 2026-07-28 sweep over 20 pages returned 0 malformed responses and 0
missing region ids, cost 44,437 input tokens in total, and had 58 of its
regions scored by inspection with zero floor plans missed and zero false
positives. That was a different partition: the segmenter shipped here produces
157 regions over the 16 vector sheets in plans/ (26 on s03 alone, where
that sweep saw 10 — measured 2026-07-30 by running qualifying_clip_rects +
segment_page over page 1 of each file, substituting the page-fallback region
where the cut yielded <= 1). The accuracy score therefore describes regions
this code does not produce, and the per-page token figure is roughly 3x low on
clip-bearing sheets, which send one crop per region. Both need re-measuring
against the current cut before they mean anything.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
from typing import Optional

import fitz
from google.genai import types

from models import BBox, PageData, Region

MODEL = "gemini-2.5-flash"
SCALE = 150 / 72

# Each crop is scaled so its long edge hits this, regardless of its size on the
# sheet: a cramped location plan gets enlarged, a huge floor plan shrunk.
CROP_TARGET_LONG_EDGE_PX = 1536
CROP_MAX_ZOOM = 10.0

REGION_TYPES = [
    "floor_plan", "elevation", "section", "location_plan", "block_plan",
    "site_plan", "roof_plan", "schedule_table", "legend", "title_block",
    "detail", "other",
]

# Constrained decoding. JSON mode alone only asks for JSON; it does not
# constrain the decoder, and on 2026-08-05 a response for sheet s11 began
# as valid JSON, degenerated mid-stream into an off-topic fragment, and lost an
# object separator. With a schema the decoder cannot emit that. The prose shape
# stays in SYSTEM_PROMPT: it documents intent and steers the VALUES, which no
# schema can.
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["regions"],
    properties={
        "regions": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                # id is the whole matching contract — apply_classification
                # keys responses to regions by it and ignores items without.
                required=["id", "type", "confidence"],
                properties={
                    "id": types.Schema(type=types.Type.INTEGER),
                    "type": types.Schema(type=types.Type.STRING, enum=REGION_TYPES),
                    "title": types.Schema(type=types.Type.STRING, nullable=True),
                    "confidence": types.Schema(type=types.Type.NUMBER),
                    "contains_multiple": types.Schema(type=types.Type.BOOLEAN),
                    "notes": types.Schema(type=types.Type.STRING),
                },
            ),
        ),
    },
)

SYSTEM_PROMPT = f"""\
You are an expert reader of architectural drawing sheets (UK planning and
building-regulation drawings).

A single sheet has been mechanically split into separate drawing regions by
whitespace analysis. You will receive one cropped image per region, in order,
each preceded by its region number and any text found inside it.

For EACH region, identify what kind of drawing it is. Choose exactly one type:
{", ".join(REGION_TYPES)}

Guidance:
- floor_plan: a horizontal cut through a building showing rooms, wall thicknesses,
  door swings and window openings. This is the type that matters most - be precise.
- elevation: a vertical external face of the building - roof outline, windows drawn
  flat, ground line, often hatched brickwork. No door swing arcs, no room labels.
- section: a vertical cut, showing floor/roof build-ups and internal heights.
- location_plan / block_plan / site_plan: maps or site layouts, often with a red
  outline, street names, plot boundaries. Buildings appear as simple filled shapes
  with no internal room detail.
- roof_plan: a plan view showing roof pitches, ridges and hips, but no rooms.
- schedule_table: a table of doors, windows, or areas.
- title_block / legend / detail / other: sheet furniture, keys, construction
  details, or anything that fits nothing above.

A region may contain more than one drawing if the split was imperfect. If so, set
"contains_multiple": true and give the type of the dominant drawing.

Respond ONLY with valid JSON, no markdown fences:
{{"regions": [{{"id": <int>, "type": "<one of the list>", "title": "<drawing title or null>",
  "confidence": <float 0-1>, "contains_multiple": <bool>, "notes": "<short>"}}]}}
"""


def render_region_crop(page: fitz.Page, bbox: BBox, out_path: str) -> tuple[int, int]:
    """Render one region as its own PNG, scaled so its long edge is about
    CROP_TARGET_LONG_EDGE_PX. Returns the rendered (width, height)."""
    rect = fitz.Rect(bbox[0] / SCALE, bbox[1] / SCALE, bbox[2] / SCALE, bbox[3] / SCALE)
    long_edge_pt = max(rect.width, rect.height)
    zoom = min(CROP_MAX_ZOOM, CROP_TARGET_LONG_EDGE_PX / max(1.0, long_edge_pt))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
    pix.save(out_path)
    return pix.width, pix.height


def region_title_text(page_data: PageData, bbox: BBox, limit: int = 6) -> list[str]:
    """Distinct text inside a region, largest font first. Many CAD exports
    outline their text to curves, in which case this is empty and the model
    works from the image alone."""
    inside = [
        t for t in page_data.text_spans
        if t.bbox[0] >= bbox[0] - 2 and t.bbox[2] <= bbox[2] + 2
        and t.bbox[1] >= bbox[1] - 2 and t.bbox[3] <= bbox[3] + 2
        and t.text.strip()
    ]
    inside.sort(key=lambda t: -t.size)
    seen: set[str] = set()
    out: list[str] = []
    for t in inside:
        s = t.text.strip()
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
        if len(out) >= limit:
            break
    return out


def build_request_parts(
    page: fitz.Page, page_data: PageData, regions: list[Region], crop_dir: str
) -> list:
    os.makedirs(crop_dir, exist_ok=True)
    parts = [types.Part.from_text(
        text=f"This sheet was split into {len(regions)} regions. Classify every one.")]
    for i, region in enumerate(regions):
        crop_path = os.path.join(crop_dir, f"{region.region_id}.png")
        render_region_crop(page, region.bbox, crop_path)
        text = region_title_text(page_data, region.bbox)
        w = region.bbox[2] - region.bbox[0]
        h = region.bbox[3] - region.bbox[1]
        parts.append(types.Part.from_text(
            text=f"REGION {i} — {w:.0f}x{h:.0f}px on the sheet. "
                 f"Text found inside: {text if text else 'none (text is outlined to curves)'}"))
        with open(crop_path, "rb") as f:
            parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/png"))
    return parts


def apply_classification(
    raw_text: str, regions: list[Region]
) -> tuple[list[Region], list[dict]]:
    """Apply a classification response to a region list.

    Returns new Region objects — the inputs are not mutated. A region the model
    did not address, or gave a type outside the taxonomy, stays "unclassified"
    or becomes "other" respectively, and is reported.
    """
    warnings: list[dict] = []
    out = [dataclasses.replace(r) for r in regions]

    text = re.sub(r"^```(?:json)?", "", raw_text.strip())
    text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        warnings.append({
            "warning_code": "REGION_CLASSIFY_PARSE_FAILURE",
            "severity": "error",
            "message": f"Region classification response was not valid JSON: {e}",
            "raw_response_snippet": raw_text[:300],
        })
        return out, warnings

    by_id = {}
    for item in parsed.get("regions", []):
        try:
            by_id[int(item.get("id"))] = item
        except (TypeError, ValueError):
            continue

    unaddressed: list[str] = []
    coerced: list[str] = []
    for i, region in enumerate(out):
        item = by_id.get(i)
        if item is None:
            unaddressed.append(region.region_id)
            continue
        rtype = item.get("type")
        if rtype not in REGION_TYPES:
            coerced.append(f"{region.region_id}={rtype!r}")
            rtype = "other"
        region.region_type = rtype
        title = item.get("title")
        region.title = title.strip() if isinstance(title, str) and title.strip() else None
        try:
            region.confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            region.confidence = 0.0
        region.contains_multiple = bool(item.get("contains_multiple", False))

    if unaddressed or coerced:
        details = []
        if unaddressed:
            details.append(f"unaddressed: {unaddressed}")
        if coerced:
            details.append(f"unknown types coerced to 'other': {coerced}")
        warnings.append({
            "warning_code": "REGION_CLASSIFY_INCOMPLETE",
            "severity": "warning",
            "message": "Region classification incomplete — " + "; ".join(details),
        })

    return out, warnings


def classify_regions(
    client,
    page: fitz.Page,
    page_data: PageData,
    regions: list[Region],
    crop_dir: str,
    model: str = MODEL,
) -> tuple[list[Region], list[dict]]:
    """One API call for the whole page. Returns classified regions + warnings."""
    if not regions:
        return [], []

    parts = build_request_parts(page, page_data, regions, crop_dir)
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    return apply_classification(response.text, regions)
