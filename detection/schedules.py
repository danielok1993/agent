from __future__ import annotations
import re
from models import Candidate, TextSpan

# ---------------------------------------------------------------------------
# Schedule detection constants
# ---------------------------------------------------------------------------
SCHEDULE_TABLE_MIN_ROWS     = 3
SCHEDULE_TABLE_MIN_COLS     = 2
SCHEDULE_MIN_CELL_DENSITY   = 0.15
SCHEDULE_KEYWORDS           = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|mark|width|height)"
)


SCHEDULE_KEYWORDS_RE = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|type|mark)"
)


def detect_schedules(
    text_spans: list[TextSpan],
    plumber_tables: list[list[list[str | None]]],
) -> list[Candidate]:
    candidates = []
    cand_idx = 0

    for table in plumber_tables:
        if len(table) < SCHEDULE_TABLE_MIN_ROWS:
            continue
        max_cols = max((len(row) for row in table), default=0)
        if max_cols < SCHEDULE_TABLE_MIN_COLS:
            continue

        total_cells = sum(len(row) for row in table)
        non_empty = sum(1 for row in table for cell in row if cell and str(cell).strip())
        density = non_empty / total_cells if total_cells > 0 else 0
        if density < SCHEDULE_MIN_CELL_DENSITY:
            continue

        all_text = " ".join(
            str(cell) for row in table for cell in row if cell
        )
        is_schedule = bool(SCHEDULE_KEYWORDS_RE.search(all_text))
        confidence = 0.60 if is_schedule else 0.35

        candidates.append(Candidate(
            candidate_id=f"schedule_{cand_idx:04d}",
            entity_type="schedule",
            bbox=(0, 0, 0, 0),  # pdfplumber tables don't always have bbox
            confidence=round(confidence, 3),
            evidence={
                "rows": len(table),
                "cols": max_cols,
                "cell_density": round(density, 3),
                "is_schedule_keyword": is_schedule,
                "sample_text": all_text[:200],
            },
        ))
        cand_idx += 1

    return candidates
