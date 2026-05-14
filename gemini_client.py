from __future__ import annotations
import base64
import json
import os
import re
from typing import Optional
from google import genai
from google.genai import types
from models import PageData, Candidate

MODEL = "gemini-2.5-flash"

REQUIRED_KEYS = {"doors", "windows", "walls", "labels", "schedules", "rejected_candidates"}

SYSTEM_PROMPT = """\
You are an expert architectural drawing interpreter specialising in CAD-originated floor plans, elevations, and construction documents.

You will receive:
1. A full-resolution PNG render of one PDF page at 150 DPI.
2. A JSON object named "candidates" listing geometry elements detected by heuristics, each with a bounding box in pixel coordinates (top-left origin, y increases downward), a type guess, and supporting evidence.

Your task:
- Review each candidate visually against the image.
- Classify each candidate as one of: door, window, wall, label, schedule, or rejected.
- For doors and windows, extract any visible label (e.g. "D01", "W-3", "FD-12").
- Assign a confidence score from 0.0 to 1.0 for each accepted candidate.
- Use "rejected" for candidates that are clearly not architectural elements (e.g. title block lines, hatching, north arrows, dimensions).

RULES:
- Respond ONLY with valid JSON. No prose, no markdown fences, no explanation outside the JSON.
- If a candidate is ambiguous but plausibly architectural, accept it with confidence <= 0.5.
- Do not invent candidates not in the input list.

OUTPUT SCHEMA (respond with exactly this structure):
{
  "page_number": <integer>,
  "page_notes": "<optional observation about page quality or content>",
  "doors": [
    {"candidate_id": "<str>", "label": "<str|null>", "confidence": <float>, "notes": "<optional>"}
  ],
  "windows": [
    {"candidate_id": "<str>", "label": "<str|null>", "confidence": <float>, "notes": "<optional>"}
  ],
  "walls": [
    {"candidate_id": "<str>", "thickness_px": <int|null>, "confidence": <float>, "notes": "<optional>"}
  ],
  "labels": [
    {"candidate_id": "<str>", "text": "<str>", "confidence": <float>}
  ],
  "schedules": [
    {"candidate_id": "<str>", "rows": <int|null>, "cols": <int|null>, "confidence": <float>}
  ],
  "rejected_candidates": [
    {"candidate_id": "<str>", "reason": "<str>"}
  ]
}
"""


def init_client() -> genai.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, timeout=5,
            )
            project = result.stdout.strip() or None
        except Exception:
            pass
    if not project:
        raise EnvironmentError(
            "No GCP project found. Set GOOGLE_CLOUD_PROJECT or run:\n"
            "  gcloud config set project YOUR_PROJECT_ID\n"
            "Then authenticate with:\n"
            "  gcloud auth application-default login"
        )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)


def should_skip_gemini(page_data: PageData, candidates: list[Candidate]) -> bool:
    return page_data.page_type == "raster-heavy" and len(candidates) == 0


def encode_image_inline(png_path: str) -> types.Part:
    with open(png_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return types.Part.from_bytes(data=base64.b64decode(data), mime_type="image/png")


def _candidate_to_dict(c: Candidate) -> dict:
    return {
        "candidate_id": c.candidate_id,
        "entity_type": c.entity_type,
        "bbox": list(c.bbox),
        "confidence": c.confidence,
        "evidence": c.evidence,
    }


def build_user_message(page_data: PageData, candidates: list[Candidate]) -> str:
    candidate_list = [_candidate_to_dict(c) for c in candidates]
    payload = {
        "page_number": page_data.page_number,
        "page_type": page_data.page_type,
        "width_px": round(page_data.width_px, 1),
        "height_px": round(page_data.height_px, 1),
        "ocg_layers": page_data.ocg_names,
        "candidates": candidate_list,
    }
    return (
        f"Please classify the candidates for page {page_data.page_number}.\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```"
    )


def parse_gemini_response(raw_text: str) -> dict:
    text = raw_text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    parsed = json.loads(text)
    return parsed


def _validate_response(parsed: dict, candidates: list[Candidate]) -> list[dict]:
    warnings = []
    missing = REQUIRED_KEYS - set(parsed.keys())
    if missing:
        warnings.append({
            "warning_code": "GEMINI_SCHEMA_MISMATCH",
            "severity": "warning",
            "message": f"Gemini response missing keys: {sorted(missing)}",
        })

    known_ids = {c.candidate_id for c in candidates}
    for key in ("doors", "windows", "walls", "labels", "schedules", "rejected_candidates"):
        for item in parsed.get(key, []):
            cid = item.get("candidate_id", "")
            if cid and cid not in known_ids:
                warnings.append({
                    "warning_code": "GEMINI_UNKNOWN_CANDIDATE_ID",
                    "severity": "warning",
                    "message": f"Gemini returned unknown candidate_id: {cid!r}",
                })

    return warnings


def call_gemini(
    client: genai.Client,
    page_data: PageData,
    candidates: list[Candidate],
    render_png_path: str,
    model: str = MODEL,
) -> tuple[dict, list[dict]]:
    image_part = encode_image_inline(render_png_path)
    user_text = build_user_message(page_data, candidates)

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_text),
                    image_part,
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    raw_text = response.text
    try:
        parsed = parse_gemini_response(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        parse_warning = {
            "warning_code": "GEMINI_PARSE_FAILURE",
            "severity": "error",
            "message": f"Gemini response for page {page_data.page_number} was not valid JSON: {e}",
            "raw_response_snippet": raw_text[:300],
        }
        empty_result = {
            "page_number": page_data.page_number,
            "page_notes": "parse failure",
            "doors": [], "windows": [], "walls": [],
            "labels": [], "schedules": [], "rejected_candidates": [],
        }
        return empty_result, [parse_warning]

    validation_warnings = _validate_response(parsed, candidates)
    return parsed, validation_warnings
