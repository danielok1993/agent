"""Checkpoint pictures for the _gate_denominator step (s01 identity vs 0.542):
  1. the hall door's doorway plug and its jamb gap
  2. the living room: the furniture pen flipping to a wall pen (cushion cells)
Render = the baseline sweep's render.png (150 DPI, same frame)."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa
from PIL import Image, ImageDraw, ImageFont
import glob

OUT = "/Users/danielszweda/Documents/GitHub/UD/agent/docs/w-gate-iter3-checkpoints"
render_path = sorted(glob.glob("/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress_baseline/s01/*/pages/page_01/render.png"))[-1]
render = Image.open(render_path).convert("RGBA")
page = H.load("s01")[0]
try:
    FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    FONT_S = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
except Exception:
    FONT = FONT_S = ImageFont.load_default()


def draw_geom(draw, geom, fill, outline, scale, ox, oy, width=1):
    geoms = getattr(geom, "geoms", [geom])
    for g in geoms:
        if g.is_empty or g.geom_type != "Polygon":
            continue
        pts = [((x - ox) * scale, (y - oy) * scale) for x, y in g.exterior.coords]
        draw.polygon(pts, fill=fill, outline=outline)
        for ring in g.interiors:
            pts = [((x - ox) * scale, (y - oy) * scale) for x, y in ring.coords]
            draw.polygon(pts, fill=(255, 255, 255, 0), outline=outline)
        if width > 1:
            draw.line(pts + [pts[0]], fill=outline, width=width)


def panel(R, crop, scale, title, door_bbox=None, edge=None, show_faces_pen=None):
    x0, y0, x1, y1 = crop
    base = render.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * scale), int((y1 - y0) * scale)), Image.LANCZOS)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    bxp = box(*crop)
    # barrier union (light blue)
    draw_geom(d, R["barriers"].intersection(bxp), (80, 120, 255, 70), (80, 120, 255, 160), scale, x0, y0)
    # door seals (orange)
    for bb, rec in R["seals"].items():
        if rec["geom"] is not None and rec["geom"].intersects(bxp):
            draw_geom(d, rec["geom"].intersection(bxp), (255, 140, 0, 150), (200, 90, 0, 255), scale, x0, y0)
    # faces in a pen that fence at this factor (red pen) — drawn as thin red lines from the network
    if show_faces_pen is not None:
        net = R["extras"]["network"]
        for fc in net.faces:
            if fc.stroked and fc.pen == show_faces_pen:
                d.line([((fc.p1[0] - x0) * scale, (fc.p1[1] - y0) * scale), ((fc.p2[0] - x0) * scale, (fc.p2[1] - y0) * scale)],
                       fill=(255, 0, 0, 120), width=1)
    # rooms (green outline)
    for r in R["rooms"]:
        if r["poly"].intersects(bxp):
            pts = [((x - x0) * scale, (y - y0) * scale) for x, y in r["poly"].exterior.coords]
            d.line(pts + [pts[0]], fill=(0, 170, 0, 255), width=3)
    # profile samples of the door edge
    if door_bbox is not None:
        mat, skip, gates, out = R["plug_calls"][door_bbox]
        pr = profile(door_bbox, mat, gates, edge)
        for (px, py), cov, touch in zip(pr["pts"], pr["covered"], pr["touch"]):
            c = (0, 160, 0, 255) if touch else (230, 180, 0, 255) if cov else (220, 0, 0, 255)
            X, Y = (px - x0) * scale, (py - y0) * scale
            d.ellipse([X - 3, Y - 3, X + 3, Y + 3], fill=c, outline=(0, 0, 0, 255))
        # bbox
        bx0, by0, bx1, by1 = door_bbox
        d.rectangle([(bx0 - x0) * scale, (by0 - y0) * scale, (bx1 - x0) * scale, (by1 - y0) * scale], outline=(0, 0, 255, 255), width=2)
    img = Image.alpha_composite(base, ov)
    dd = ImageDraw.Draw(img)
    dd.rectangle([0, 0, img.width, 20], fill=(255, 255, 255, 230))
    dd.text((4, 3), title, fill=(0, 0, 0), font=FONT_S)
    return img


def side_by_side(panels, path, caption):
    w = sum(p.width for p in panels) + 10 * (len(panels) - 1)
    h = max(p.height for p in panels) + 24
    out = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    x = 0
    for p in panels:
        out.paste(p, (x, 24))
        x += p.width + 10
    ImageDraw.Draw(out).text((4, 4), caption, fill=(0, 0, 0), font=FONT)
    out.convert("RGB").save(path)
    print("wrote", path)


def main():
    """The two step-9 pictures (guarded so crop_step10.py can import the drawing helpers).""" 
    R1 = run_tapped(page, None)
    R2 = run_tapped(page, F542)
    hall = [bb for bb in R1["seals"] if abs(bb[0] - 424) < 3 and abs(bb[1] - 917) < 3][0]
    crop = (380, 880, 540, 980)
    p1 = panel(R1, crop, 5, "identity f=1.0: seal 15, half-width 5 — top-edge (doorway) plug interrupted; tail samples: green=touch, yellow=covered, red=no", hall, 0)
    p2 = panel(R2, crop, 5, "f=0.542: seal 8.13, half-width 2.71 — first sample 4.1px short of the jamb material; doorway plug lost, hall merges with the living room", hall, 0)
    side_by_side([p1, p2], f"{OUT}/step9_s01_hall_door_doorway_plug_identity_vs_0542.png",
                 "s01 hall door (424,917)-(467,958): the doorway is the TOP edge; its left jamb face sits 14.25px = 222mm (at 1:92.2) past the bbox corner. Blue = barrier, orange = door seals, green = room outlines")

    crop2 = (195, 400, 530, 920)
    p3 = panel(R1, crop2, 2, "identity: red (furniture pen) carries 13.7% of the paired face length -> not a wall pen; its lone faces do not fence", show_faces_pen=(1.0, 0.0, 0.0))
    p4 = panel(R2, crop2, 2, "f=0.542: red carries 15.2% >= ROOM_WALL_PEN_MIN_FRAC 0.15 -> wall pen; every red 1.5px line fences: 12 cushion cells + 2 slivers + 3 splits", show_faces_pen=(1.0, 0.0, 0.0))
    side_by_side([p3, p4], f"{OUT}/step9_s01_living_room_furniture_pen_flip_identity_vs_0542.png",
                 "s01 living room at identity vs the true factor: the furniture pen crosses the wall-pen fraction gate (13.7% -> 15.2% vs 0.15). Red = faces in the furniture pen, blue = barrier, green = rooms")


if __name__ == "__main__":
    main()
