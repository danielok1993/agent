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
from takeoff.heights import Heights
from takeoff.openings import assign_openings, opening_width_px
from takeoff.scale import (
    RoomScale, is_verified, select_room_scale, sheet_size_tokens, verify_sheet_size,
)
from takeoff.units import mm_per_px, px2_to_m2, px_to_m

STANDOFF_ASSUMPTION = f"standoff_corrected_{ROOM_WALL_DILATE_PX:g}px"
FLAT_CEILING_ASSUMPTION = "flat_ceiling"
HOLES_FILLED_ASSUMPTION = "holes_filled"   # detector fills fixture islands; they are floor


@dataclass
class RoomTakeoff:
    room_id: str
    label: Optional[str]
    scale: RoomScale
    mm_per_px: float
    floor_m2: float
    ceiling_m2: float
    perimeter_m: float
    height_m: float
    height_source: str
    wall_gross_m2: float
    openings: list = field(default_factory=list)
    wall_net_m2: float = 0.0
    assumptions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "label": self.label,
            "scale": self.scale.to_dict(),
            "mm_per_px": self.mm_per_px,
            "floor_m2": self.floor_m2,
            "ceiling_m2": self.ceiling_m2,
            "perimeter_m": self.perimeter_m,
            "height_m": self.height_m,
            "height_source": self.height_source,
            "wall_gross_m2": self.wall_gross_m2,
            "openings": list(self.openings),
            "wall_net_m2": self.wall_net_m2,
            "assumptions": list(self.assumptions),
        }


@dataclass
class TakeoffPage:
    page_number: int
    heights: Heights
    rooms: list = field(default_factory=list)
    unassigned_openings: list = field(default_factory=list)
    over_assigned_openings: list = field(default_factory=list)
    unscaled_rooms: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def totals(self) -> dict:
        return {
            "floor_m2": round(sum(r.floor_m2 for r in self.rooms), 2),
            "ceiling_m2": round(sum(r.ceiling_m2 for r in self.rooms), 2),
            "wall_net_m2": round(sum(r.wall_net_m2 for r in self.rooms), 2),
            "rooms_measured": len(self.rooms),
            "rooms_unscaled": len(self.unscaled_rooms),
        }

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "heights": self.heights.to_dict(),
            "rooms": [r.to_dict() for r in self.rooms],
            "unassigned_openings": list(self.unassigned_openings),
            "over_assigned_openings": [dict(o) for o in self.over_assigned_openings],
            "unscaled_rooms": list(self.unscaled_rooms),
            "totals": self.totals(),
        }

    def attributes_by_room(self) -> dict:
        out = {}
        for r in self.rooms:
            d = r.to_dict()
            d.pop("room_id")
            d.pop("label")
            out[r.room_id] = d
        return out


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
                    page_number: int, page_text: str, page_w_mm: float, page_h_mm: float) -> TakeoffPage:
    page = TakeoffPage(page_number=page_number, heights=heights)
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
        # A point ON the room, never its centroid: an L-shaped room's centroid
        # can fall outside both the polygon and its own floor_plan region.
        c = raw.representative_point()
        rs = select_room_scale((c.x, c.y), regions, page_scales, det_scale)
        if rs.denominator is None:
            page.unscaled_rooms.append(e.entity_id)
            continue
        rs = RoomScale(rs.denominator, rs.source, rs.region_id, is_verified(rs, sheet_matches))
        room_meta[e.entity_id] = (e, rs, poly)

    if page.unscaled_rooms:
        _warn(page, "TAKEOFF_NO_SCALE", "warning",
              f"{len(page.unscaled_rooms)} room(s) have no resolvable drawing scale; "
              "no quantities computed for them")

    # Openings → rooms.
    openings = [(e.entity_id, e.entity_type, e.bbox) for e in entities
                if e.entity_type in ("door", "window")]
    opening_by_id = {e.entity_id: e for e in entities if e.entity_type in ("door", "window")}
    assigned, unassigned, over_assigned = assign_openings(room_polys, openings)
    page.unassigned_openings = unassigned
    page.over_assigned_openings = [{"id": oid, "dropped_rooms": list(dropped)}
                                   for oid, dropped in over_assigned]
    if over_assigned:
        _warn(page, "TAKEOFF_OPENING_MULTI_ROOM", "info",
              f"{len(over_assigned)} opening(s) reached 3+ rooms; kept the two "
              "nearest room boundaries — an opening serves at most two spaces")

    for rid, (e, rs, poly) in room_meta.items():
        D = rs.denominator
        floor = px2_to_m2(poly.area, D)
        perim = px_to_m(poly.exterior.length, D)
        gross = perim * heights.ceiling_m
        ops = []
        deduct = 0.0
        for oid in assigned.get(rid, []):
            oe = opening_by_id[oid]
            w_px, w_src = opening_width_px(oe.entity_type, oe.bbox, evidence.get(oid, {}), poly)
            w_m = px_to_m(w_px, D)
            h_m = heights.door_m if oe.entity_type == "door" else heights.window_m
            clamped = h_m > heights.ceiling_m
            if clamped:
                h_m = heights.ceiling_m
                _warn(page, "TAKEOFF_OPENING_TALLER_THAN_CEILING", "info",
                      "An opening height exceeded the ceiling height and was clamped")
            area = w_m * h_m
            deduct += area
            op = {"id": oid, "type": oe.entity_type, "width_m": round(w_m, 2),
                  "height_m": round(h_m, 2), "area_m2": round(area, 2), "width_source": w_src}
            if clamped:
                op["clamped"] = True
            ops.append(op)
        room = RoomTakeoff(
            room_id=rid, label=e.label, scale=rs, mm_per_px=round(mm_per_px(D), 3),
            floor_m2=round(floor, 2), ceiling_m2=round(floor, 2), perimeter_m=round(perim, 2),
            height_m=heights.ceiling_m, height_source=heights.sources["ceiling"],
            wall_gross_m2=round(gross, 2), openings=ops,
            wall_net_m2=round(max(gross - deduct, 0.0), 2),
            assumptions=[FLAT_CEILING_ASSUMPTION, STANDOFF_ASSUMPTION, HOLES_FILLED_ASSUMPTION],
        )
        page.rooms.append(room)
        if not rs.verified:
            _warn(page, "SCALE_UNVERIFIED", "info",
                  "Room quantities rest on a scale that could not be tied to a verified "
                  "region source (viewport/user, or text confirmed by sheet size)")

    return page
