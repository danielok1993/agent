"""compute_takeoff — the pure core: rooms + scale + heights → metres.

No I/O, no prompting, no globals. pipeline.run_extract resolves heights once
per run, calls this per page after finalize_candidates, and writes the
result. Rooms without a resolvable scale are listed, never zeroed. Warnings
travel on TakeoffPage.warnings for the caller to fold into the page list —
the same shape PageScales.warnings uses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from shapely.geometry import Polygon

from detection.rooms import ROOM_WALL_DILATE_PX
from scale.resolver import scale_summary_dict
from takeoff.heights import Heights
from takeoff.openings import (
    assign_openings, opening_width_px, opening_width_px_from_evidence,
)
from takeoff.plausibility import (
    assess_scale, dimension_matches as match_dimensions, leaf_width_px,
)
from takeoff.scale import (
    RoomScale, is_verified, select_room_scale, sheet_size_tokens, verify_sheet_size,
)
from takeoff.units import mm_per_px, px2_to_m2, px_to_m

STANDOFF_ASSUMPTION = f"standoff_corrected_{ROOM_WALL_DILATE_PX:g}px"
FLAT_CEILING_ASSUMPTION = "flat_ceiling"
HOLES_FILLED_ASSUMPTION = "holes_filled"   # detector fills fixture islands; they are floor

# 150 DPI is where extraction/extractor.py normalises every coordinate; the
# PDF's own user space is 72 dpi. Kept here rather than imported from
# extraction/ so takeoff/ stays free of that dependency — extractor.SCALE is
# its reciprocal.
TAKEOFF_DPI = 150
PT_PER_PX = 72.0 / TAKEOFF_DPI


@dataclass
class PageFrame:
    """The space every coordinate in this document lives in.

    extractor.page_transform has ALREADY applied the page's /Rotate, so these
    coordinates match the rendered page. `rotation` is provenance only — a
    consumer must not re-apply it.
    """
    width_px: float
    height_px: float
    rotation: int = 0
    dpi: int = TAKEOFF_DPI

    def to_dict(self) -> dict:
        return {
            "width_px": round(self.width_px, 1),
            "height_px": round(self.height_px, 1),
            "dpi": self.dpi,
            "origin": "top-left",
            "y_axis": "down",
            "pdf_width_pt": round(self.width_px * PT_PER_PX, 1),
            "pdf_height_pt": round(self.height_px * PT_PER_PX, 1),
            "rotation": self.rotation,
        }


@dataclass
class RoomTakeoff:
    room_id: str
    label: Optional[str]
    confidence: float
    bbox: tuple
    polygon: list
    opening_ids: list = field(default_factory=list)
    scale: Optional[RoomScale] = None            # None when unresolvable
    mm_per_px: Optional[float] = None
    floor_m2: Optional[float] = None
    ceiling_m2: Optional[float] = None
    perimeter_m: Optional[float] = None
    height_m: Optional[float] = None
    height_source: Optional[str] = None
    wall_gross_m2: Optional[float] = None
    wall_net_m2: Optional[float] = None
    assumptions: list = field(default_factory=list)

    @property
    def measured(self) -> bool:
        """True when a scale resolved and quantities exist."""
        return self.scale is not None


@dataclass
class OpeningTakeoff:
    """One physical door or window, once. A shared opening carries both room
    ids rather than being duplicated under each room."""
    opening_id: str
    type: str                                  # "door" | "window"
    assembly_type: Optional[str]
    tag: Optional[str]
    confidence: float
    bbox: tuple
    room_ids: list = field(default_factory=list)        # [] when unassigned
    dropped_room_ids: list = field(default_factory=list)
    width_px: Optional[float] = None
    width_source: Optional[str] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    area_m2: Optional[float] = None
    clamped: bool = False


@dataclass
class TakeoffPage:
    page_number: int
    heights: Heights
    rooms: list = field(default_factory=list)
    openings: list = field(default_factory=list)
    unassigned_openings: list = field(default_factory=list)
    over_assigned_openings: list = field(default_factory=list)
    unscaled_rooms: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    dimension_matches: list = field(default_factory=list)   # DimensionMatch
    verdicts: dict = field(default_factory=dict)            # denominator → Verdict
    page_frame: Optional[PageFrame] = None
    scale_block: dict = field(default_factory=dict)

    def totals(self) -> dict:
        measured = [r for r in self.rooms if r.measured]
        return {
            "floor_m2": round(sum(r.floor_m2 for r in measured), 2),
            "ceiling_m2": round(sum(r.ceiling_m2 for r in measured), 2),
            "wall_net_m2": round(sum(r.wall_net_m2 for r in measured), 2),
            "rooms_measured": len(measured),
            "rooms_unscaled": len(self.rooms) - len(measured),
        }


def _warn(page: TakeoffPage, code: str, severity: str, message: str) -> None:
    if any(w["warning_code"] == code for w in page.warnings):
        return
    page.warnings.append({"page_number": page.page_number, "warning_code": code,
                          "severity": severity, "message": message})


def _largest_polygon(geom):
    """A Polygon from whatever shapely returned; MultiPolygon → its largest part."""
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]
    return max(parts, key=lambda g: g.area) if parts else None


def _room_polygon(entity) -> Optional[Polygon]:
    pts = entity.attributes.get("polygon")
    if not pts or len(pts) < 3:
        return None
    poly = Polygon([tuple(p) for p in pts])
    if not poly.is_valid:
        poly = poly.buffer(0)
        poly = _largest_polygon(poly)
        if poly is None:
            return None
    return poly if not poly.is_empty else None


def compute_takeoff(entities, candidates, page_scales, regions, det_scale, heights: Heights,
                    page_number: int, page_text: str, page_w_mm: float, page_h_mm: float,
                    paths=(), text_spans=(),
                    page_width_px: float = 0.0, page_height_px: float = 0.0,
                    page_rotation: int = 0,
                    dimension_matches: Optional[list] = None) -> TakeoffPage:
    """`dimension_matches`: the page's ticked-dimension-string matches, when
    the caller already has them — run_extract matches the full page once for
    the detection gates (scale/dimensions.py) and passes the list in; left
    None they are matched here from `paths` / `text_spans`."""
    page = TakeoffPage(page_number=page_number, heights=heights)
    page.page_frame = PageFrame(page_width_px, page_height_px, page_rotation)
    page.scale_block = scale_summary_dict(page_scales, det_scale)
    evidence = {c.candidate_id: c.evidence for c in candidates}

    tokens = sheet_size_tokens(page_text)
    sheet_matches, sheet_resized = verify_sheet_size(tokens, page_w_mm, page_h_mm)
    if sheet_resized:
        _warn(page, "SCALE_PRINT_RESIZED", "warning",
              f"Title block declares {'/'.join(sorted(tokens))} but the page is "
              f"{page_w_mm:.0f}x{page_h_mm:.0f} mm — looks like a half-/double-size print "
              "(two A-steps); the printed scale may be off by 2x")

    # Rooms: polygon, corrected for the barrier standoff, and its scale.
    # EVERY valid room takes part in opening assignment (so an opening on an
    # unscaled room is not mis-reported as free-space); only scaled rooms
    # get quantities.
    room_polys: dict[str, Polygon] = {}
    room_meta: dict[str, tuple] = {}
    room_raw: dict[str, Polygon] = {}
    # The entity's OWN ring, verbatim: takeoff.json overlays the same geometry
    # final_entities.json carries, so a repaired ring (buffer(0) keeps only a
    # bowtie's largest lobe) may drive the maths but is never published as the
    # room's outline.
    room_pts: dict[str, list[list[float]]] = {}
    unscaled_records: dict[str, RoomTakeoff] = {}
    for e in entities:
        if e.entity_type != "room":
            continue
        raw = _room_polygon(e)
        if raw is None:
            continue
        poly = raw.buffer(ROOM_WALL_DILATE_PX, join_style=2)   # 2 = mitre
        poly = _largest_polygon(poly)
        if poly is None:
            continue
        room_polys[e.entity_id] = poly
        room_raw[e.entity_id] = raw
        room_pts[e.entity_id] = [list(pt) for pt in e.attributes["polygon"]]
        # A point ON the room, never its centroid: an L-shaped room's centroid
        # can fall outside both the polygon and its own floor_plan region.
        c = raw.representative_point()
        rs = select_room_scale((c.x, c.y), regions, page_scales, det_scale)
        if rs.denominator is None:
            # Kept, with geometry: an unscaled room still has to appear on the
            # overlay, and it still takes part in opening assignment above.
            page.unscaled_rooms.append(e.entity_id)
            record = RoomTakeoff(
                room_id=e.entity_id, label=e.label, confidence=e.confidence,
                bbox=tuple(e.bbox), polygon=room_pts[e.entity_id],
            )
            unscaled_records[e.entity_id] = record
            page.rooms.append(record)
            continue
        rs = RoomScale(rs.denominator, rs.source, rs.region_id, is_verified(rs, sheet_matches))
        room_meta[e.entity_id] = (e, rs, poly)

    if page.unscaled_rooms:
        _warn(page, "TAKEOFF_NO_SCALE", "warning",
              f"{len(page.unscaled_rooms)} room(s) have no resolvable drawing scale; "
              "no quantities computed for them")

    # Openings → rooms. Each opening is measured ONCE, against the polygon of
    # its first assigned room: the room polygon only matters to the bbox_edge
    # fallback, and one physical opening has one width.
    openings = [(e.entity_id, e.entity_type, e.bbox) for e in entities
                if e.entity_type in ("door", "window")]
    opening_by_id = {e.entity_id: e for e in entities if e.entity_type in ("door", "window")}
    assigned, unassigned, over_assigned = assign_openings(room_polys, openings)

    # An unscaled room's record is built before assignment runs, but it does
    # take part in it — so give it its opening ids now. Without this the
    # document names the room on the opening while the room names no opening,
    # and referential integrity holds in one direction only.
    for rid, record in unscaled_records.items():
        record.opening_ids = list(assigned.get(rid, []))

    page.unassigned_openings = unassigned
    page.over_assigned_openings = [{"id": oid, "dropped_rooms": list(dropped)}
                                   for oid, dropped in over_assigned]
    if over_assigned:
        _warn(page, "TAKEOFF_OPENING_MULTI_ROOM", "info",
              f"{len(over_assigned)} opening(s) reached 3+ rooms; kept the two "
              "nearest room boundaries — an opening serves at most two spaces")

    # Invert assigned (room → [opening]) into opening → [room], preserving the
    # room order the entity list gave, so the "first" room is deterministic.
    rooms_by_opening: dict[str, list[str]] = {}
    for rid in room_polys:
        for oid in assigned.get(rid, []):
            rooms_by_opening.setdefault(oid, []).append(rid)
    dropped_by_opening = {oid: list(dropped) for oid, dropped in over_assigned}

    # Plausibility: one verdict per denominator in use on the page, from the
    # doors assigned to rooms at that scale and the page's dimension strings.
    leaves_by_denom: dict[float, list[float]] = {}
    for rid, (_e, rs, _poly) in room_meta.items():
        bucket = leaves_by_denom.setdefault(rs.denominator, [])
        for oid in assigned.get(rid, []):
            if opening_by_id[oid].entity_type != "door":
                continue
            w = leaf_width_px(evidence.get(oid, {}))
            if w is not None:
                bucket.append(w)
    page.dimension_matches = (dimension_matches if dimension_matches is not None
                              else match_dimensions(list(paths), list(text_spans)))
    verdicts = {D: assess_scale(D, leaves, page.dimension_matches)
                for D, leaves in leaves_by_denom.items()}
    page.verdicts = verdicts
    for D, v in verdicts.items():
        if v.status == "implausible":
            _warn(page, "SCALE_IMPLAUSIBLE", "warning", v.describe(D))

    # Page-level opening records. A room's scale is what converts px to metres,
    # so an opening in no room — or in an unscaled one — keeps its pixel width
    # and gets no metres.
    opening_records: dict[str, OpeningTakeoff] = {}
    for oid, oe in opening_by_id.items():
        rids = rooms_by_opening.get(oid, [])
        # Prefer a SCALED room: room_polys holds every valid room, room_meta
        # only the scaled ones, so rids[0] can be an unscaled neighbour — and
        # picking it would leave the scaled room deducting nothing for this
        # opening. Falls back to rids[0] when no assigned room has a scale.
        # A shared opening is converted to metres once, at this primary
        # room's denominator — on a (hypothetical) mixed-scale page the
        # other room deducts the same area_m2 rather than its own conversion.
        primary = next((r for r in rids if r in room_meta), rids[0] if rids else None)
        if primary is not None:
            w_px, w_src = opening_width_px(
                oe.entity_type, oe.bbox, evidence.get(oid, {}), room_polys[primary])
        else:
            hit = opening_width_px_from_evidence(oe.entity_type, evidence.get(oid, {}))
            w_px, w_src = hit if hit is not None else (None, None)

        rec = OpeningTakeoff(
            opening_id=oid,
            type=oe.entity_type,
            assembly_type=(oe.attributes or {}).get("assembly_type"),
            tag=oe.label,
            confidence=oe.confidence,
            bbox=tuple(oe.bbox),
            room_ids=list(rids),
            dropped_room_ids=dropped_by_opening.get(oid, []),
            width_px=round(w_px, 2) if w_px is not None else None,
            width_source=w_src,
        )

        D = room_meta[primary][1].denominator if primary in room_meta else None
        if D is not None and w_px is not None:
            h_m = heights.door_m if oe.entity_type == "door" else heights.window_m
            if h_m > heights.ceiling_m:
                h_m = heights.ceiling_m
                rec.clamped = True
                _warn(page, "TAKEOFF_OPENING_TALLER_THAN_CEILING", "info",
                      "An opening height exceeded the ceiling height and was clamped")
            w_m = px_to_m(w_px, D)
            rec.width_m = round(w_m, 2)
            rec.height_m = round(h_m, 2)
            rec.area_m2 = round(w_m * h_m, 2)
        opening_records[oid] = rec
    page.openings = [opening_records[oid] for oid in opening_by_id]

    for rid, (e, rs, poly) in room_meta.items():
        D = rs.denominator
        v = verdicts.get(D)
        rs = RoomScale(rs.denominator, rs.source, rs.region_id,
                       is_verified(rs, sheet_matches, v), v)
        room_meta[rid] = (e, rs, poly)
        floor = px2_to_m2(poly.area, D)
        perim = px_to_m(poly.exterior.length, D)
        gross = perim * heights.ceiling_m
        opening_ids = list(assigned.get(rid, []))
        deduct = sum(opening_records[oid].area_m2 or 0.0 for oid in opening_ids)
        room = RoomTakeoff(
            room_id=rid, label=e.label, confidence=e.confidence,
            bbox=tuple(e.bbox),
            polygon=room_pts[rid],
            opening_ids=opening_ids,
            scale=rs, mm_per_px=round(mm_per_px(D), 3),
            floor_m2=round(floor, 2), ceiling_m2=round(floor, 2),
            perimeter_m=round(perim, 2),
            height_m=heights.ceiling_m, height_source=heights.sources["ceiling"],
            wall_gross_m2=round(gross, 2),
            wall_net_m2=round(max(gross - deduct, 0.0), 2),
            assumptions=[FLAT_CEILING_ASSUMPTION, STANDOFF_ASSUMPTION, HOLES_FILLED_ASSUMPTION],
        )
        page.rooms.append(room)
        if not rs.verified and (v is None or v.status != "implausible"):
            _warn(page, "SCALE_UNVERIFIED", "info",
                  "Room quantities rest on a scale that could not be tied to a verified "
                  "region source (viewport/user, or text confirmed by sheet size)")

    return page
