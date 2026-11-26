"""
draft_layout.py -- a 2D contour plan of the proposed opencast mine layout.

A draft to agree the layout on paper before the 3D model is built from the
same height field. Plan coordinates are metres, x east, y north, levels as
RL (reduced level) with the original ground at RL 300.

Drawn from typical values, with the general look of the reference images:
an irregular oval pit benched all round, a serpentine haul road down one
wall, a dark coal floor with water-filled sumps and an overburden spur
between them, a terraced overburden dump beside the pit, and the drainage
system (garland drain, sump pumps, pipeline, settling pond).

Run:  python draft_layout.py      ->  docs/mine-layout-draft.png
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "mine-layout-draft.png"

GROUND_RL = 300.0
RES = 2.0                                   # metres per pixel
XMIN, XMAX = -1100.0, 1500.0
YMIN, YMAX = -850.0, 900.0

# ---- pit -----------------------------------------------------------------
# 80 m deep: four 15 m overburden benches, then the 20 m coal seam; every
# berm 30 m, every face 8 m in plan (about 62 degrees).
PIT_C = (0.0, 0.0)
PIT_A, PIT_B = 640.0, 400.0                 # crest semi-axes
PIT_ROT = math.radians(15.0)                # long axis 15 deg north of east
PIT_X = [0, 8, 38, 46, 76, 84, 114, 122, 152, 160]
PIT_Y = [0, -15, -15, -30, -30, -45, -45, -60, -60, -80]
COAL_TOP, FLOOR = -60.0, -80.0
SUMPS = [(-330.0, 40.0, 90.0, 60.0), (300.0, -40.0, 80.0, 55.0)]  # local u, v
SUMP_LEVEL = -86.0
SPUR = dict(u=40.0, half_top=35.0, v_tip=-110.0, top=-45.0)        # local

# ---- haul road (one road, crest to floor) --------------------------------
GRADE = 1.0 / 16.0
ROAD_HW = 14.0                              # 28 m wide
ROAD_TH = (math.radians(50.0), math.radians(130.0))   # north wall
ROAD_INSETS = [30.0, 90.0, 150.0]
HAIRPIN_R = 30.0

# ---- overburden dump ------------------------------------------------------
DUMP_C = (1060.0, 330.0)
DUMP_A, DUMP_B = 300.0, 420.0
DUMP_ROT = math.radians(10.0)
DUMP_X = [0, 20, 50, 70, 100, 120, 150, 170, 200]
DUMP_Y = [0, 15, 15, 30, 30, 45, 45, 60, 60]
DUMP_TOP = 60.0
DUMP_ROAD_HW = 12.0


# ------------------------------------------------------------------ geometry

def to_local(x, y, c, rot):
    dx, dy = x - c[0], y - c[1]
    return dx * math.cos(rot) + dy * math.sin(rot), \
        -dx * math.sin(rot) + dy * math.cos(rot)


def to_world(u, v, c, rot):
    return c[0] + u * math.cos(rot) - v * math.sin(rot), \
        c[1] + u * math.sin(rot) + v * math.cos(rot)


def pit_r(th):
    base = PIT_A * PIT_B / np.sqrt((PIT_B * np.cos(th)) ** 2 +
                                   (PIT_A * np.sin(th)) ** 2)
    return base * (1 + 0.05 * np.cos(2 * th + 0.8) + 0.035 * np.cos(3 * th - 0.4))


def pit_inset(x, y):
    u, v = to_local(x, y, PIT_C, PIT_ROT)
    th = np.arctan2(v, u)
    return pit_r(th) - np.hypot(u, v)


def pit_point(th, d):
    """World point on the pit contour inset d (radially) at local angle th."""
    r = float(pit_r(th)) - d
    return to_world(r * math.cos(th), r * math.sin(th), PIT_C, PIT_ROT)


def dump_r(th):
    return DUMP_A * DUMP_B / np.sqrt((DUMP_B * np.cos(th)) ** 2 +
                                     (DUMP_A * np.sin(th)) ** 2)


def dump_inset(x, y):
    u, v = to_local(x, y, DUMP_C, DUMP_ROT)
    return dump_r(np.arctan2(v, u)) - np.hypot(u, v)


def dump_point(th, d):
    r = float(dump_r(th)) - d
    return to_world(r * math.cos(th), r * math.sin(th), DUMP_C, DUMP_ROT)


def haul_road_path():
    """Serpentine down the north wall: four legs joined by hairpins."""
    pts = []
    t0, t1 = ROAD_TH
    pts.append(pit_point(t0, -40.0))                # on the surface
    for k, d in enumerate(ROAD_INSETS):
        a, b = (t0, t1) if k % 2 == 0 else (t1, t0)
        for t in np.linspace(a, b, 40):
            pts.append(pit_point(t, d))
        if k + 1 < len(ROAD_INSETS):                # hairpin inwards
            for phi in np.linspace(0, math.pi, 12)[1:-1]:
                dd = d + HAIRPIN_R * (1 - math.cos(phi))
                sign = 1 if k % 2 == 0 else -1
                tt = b + sign * HAIRPIN_R * math.sin(phi) / float(pit_r(b))
                pts.append(pit_point(tt, dd))
    end_t = ROAD_TH[1] if len(ROAD_INSETS) % 2 else ROAD_TH[0]
    for d in (170.0, 200.0, 230.0):                 # out onto the floor
        pts.append(pit_point(end_t, d))
    return pts


def dump_road_path():
    """Spiral up the dump from its pit-side toe to the top."""
    length = DUMP_TOP / GRADE
    pts, s, th, d = [], 0.0, math.radians(200.0), -20.0
    while s < length + 40:
        pts.append(dump_point(th, d))
        d = min(-20.0 + 220.0 * s / length, 200.0)
        r = float(dump_r(th)) - d
        th -= 8.0 / max(r, 40.0)
        s += 8.0
    return pts


def polyline_field(path, x, y):
    best_d = np.full(np.shape(x), np.inf)
    best_s = np.zeros(np.shape(x))
    s0 = 0.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        seg = math.hypot(dx, dy) or 1e-9
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / (seg * seg), 0, 1)
        d = np.hypot(x - (ax + t * dx), y - (ay + t * dy))
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_s = np.where(better, s0 + t * seg, best_s)
        s0 += seg
    return best_d, best_s


HAUL = haul_road_path()
DUMP_ROAD = dump_road_path()


def fields(x, y):
    """Relative level (m from original ground) and feature masks."""
    ins = pit_inset(x, y)
    h = np.interp(ins, PIT_X, PIT_Y, left=0.0)
    u, v = to_local(x, y, PIT_C, PIT_ROT)
    # overburden spur running down from the south wall into the pit
    spur = (SPUR["top"] - SPOIL * np.maximum(np.abs(u - SPUR["u"]) - SPUR["half_top"], 0)
            - SPOIL * np.maximum(v - SPUR["v_tip"], 0))
    spur_on = (ins > 0) & (spur > h)
    h = np.where(spur_on, spur, h)
    water = np.zeros(np.shape(x), bool)
    for su, sv, a, b in SUMPS:
        water |= ((u - su) / a) ** 2 + ((v - sv) / b) ** 2 < 1
    water &= h <= FLOOR + 0.1
    h = np.where(water, SUMP_LEVEL, h)
    dh = np.interp(dump_inset(x, y), DUMP_X, DUMP_Y, left=0.0)
    dump_on = dh > 0
    h = np.where(dump_on, dh, h)
    d, s = polyline_field(HAUL, x, y)
    road = d <= ROAD_HW
    h = np.where(road, np.maximum(FLOOR, -np.maximum(s - 40.0, 0) * GRADE), h)
    d2, s2 = polyline_field(DUMP_ROAD, x, y)
    droad = (d2 <= DUMP_ROAD_HW) & (dh > 0)
    h = np.where(droad, np.minimum(np.maximum(s2 - 20, 0) * GRADE, DUMP_TOP), h)
    return dict(h=h, inset=ins, water=water, spur=spur_on & ~road,
                dump=dump_on, road=road, droad=droad,
                top=dump_on & (dh >= DUMP_TOP - 0.01) & ~droad)


SPOIL = 0.75


# ------------------------------------------------------------------ drawing

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def px(x, y):
    return (x - XMIN) / RES, (YMAX - y) / RES


def halo_text(draw, xy, text, f, fill=(25, 25, 25), anchor="mm"):
    x, y = xy
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            draw.text((x + dx, y + dy), text, font=f, fill=(255, 255, 255),
                      anchor=anchor)
    draw.text(xy, text, font=f, fill=fill, anchor=anchor)


def edge(mask):
    e = np.zeros(mask.shape, bool)
    e[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    e[1:, :] |= mask[1:, :] != mask[:-1, :]
    return e


def thicken(mask, n=1):
    out = mask.copy()
    for _ in range(n):
        m = out.copy()
        m[1:, :] |= out[:-1, :]
        m[:-1, :] |= out[1:, :]
        m[:, 1:] |= out[:, :-1]
        m[:, :-1] |= out[:, 1:]
        out = m
    return out


def plan_image():
    xs = XMIN + (np.arange(int((XMAX - XMIN) / RES)) + 0.5) * RES
    ys = YMAX - (np.arange(int((YMAX - YMIN) / RES)) + 0.5) * RES
    gx, gy = np.meshgrid(xs, ys)
    F = fields(gx, gy)
    h = F["h"]

    # hypsometric tint
    rgb = np.zeros(h.shape + (3,))
    t = np.clip(-h / 60.0, 0, 1)[..., None]
    rgb[:] = (1 - t) * np.array([196, 186, 160]) + t * np.array([150, 138, 122])
    rgb[h <= COAL_TOP + 0.01] = (60, 60, 66)
    rgb[np.abs(h) < 0.01] = (203, 199, 170)
    rgb[F["spur"]] = (214, 200, 168)
    dmask = F["dump"]
    td = np.clip(h / DUMP_TOP, 0, 1)[..., None]
    drgb = (1 - td) * np.array([222, 206, 168]) + td * np.array([236, 224, 192])
    rgb = np.where(dmask[..., None], drgb, rgb)
    rgb[F["top"]] = (118, 150, 88)
    rgb[F["water"]] = (92, 142, 168)
    rgb[F["road"] | F["droad"]] = (112, 110, 106)

    # hillshade, light from the north-west
    dr, dc = np.gradient(h, RES)
    nx, ny = -dc, dr                       # dh/dx east, dh/dy north (rows run south)
    nz = np.ones_like(h)
    n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    L = np.array([-0.55, 0.55, 0.63])
    shade = (nx * L[0] + ny * L[1] + nz * L[2]) / n
    rgb *= (0.55 + 0.55 * np.clip(shade, 0, 1))[..., None]

    # contours: 5 m thin, bench levels bold
    band = np.floor((h + 0.01) / 5.0)
    thin = edge(band) & ~F["water"]
    bold = np.zeros_like(thin)
    for lvl in (0, -15, -30, -45, -60, -80, 15, 30, 45, 60):
        bold |= edge(h >= lvl - 0.01) & ~F["water"]
    rgb[thin] = rgb[thin] * 0.55
    rgb[thicken(bold, 1)] = (70, 52, 36)

    # garland drain and safety boundary around the pit, dump toe drain
    ins = F["inset"]
    garland = thicken(edge(ins >= -30.0), 1)
    rgb[garland & ~F["road"]] = (40, 110, 190)
    safety = edge(ins >= -110.0)
    dash = ((np.arange(h.shape[1])[None, :] + np.arange(h.shape[0])[:, None]) // 10) % 2 == 0
    rgb[thicken(safety, 1) & dash] = (200, 40, 40)
    rgb[thicken(edge(dump_inset(gx, gy) >= -20.0), 0) & ~F["droad"]] = (40, 110, 190)

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    return img, F, gx, gy


def draw_symbol(d, X, Y, kind, f):
    colours = {"S": (232, 96, 40), "D": (240, 196, 30), "SM": (232, 150, 40),
               "Dr": (60, 120, 200), "Dz": (240, 196, 30), "P": (40, 110, 190),
               "DL": (200, 70, 30)}
    c = colours[kind]
    d.ellipse([X - 9, Y - 9, X + 9, Y + 9], fill=c, outline=(20, 20, 20), width=2)
    d.text((X, Y), kind, font=f, fill=(15, 15, 15), anchor="mm")


def main():
    plan, F, gx, gy = plan_image()
    PW, PH = plan.size
    MARGIN, TITLE, SEC_H, LEG_W = 16, 64, 300, 470
    W = MARGIN * 3 + PW + LEG_W
    H = TITLE + MARGIN * 3 + PH + SEC_H
    page = Image.new("RGB", (W, H), (250, 249, 245))
    page.paste(plan, (MARGIN, TITLE))
    d = ImageDraw.Draw(page)
    f10, f12, f14 = font(12), font(14), font(16)
    b14, b18, b26 = font(15, True), font(19, True), font(26, True)
    ox, oy = MARGIN, TITLE

    def P(x, y):
        X, Y = px(x, y)
        return X + ox, Y + oy

    d.text((MARGIN, 16), "Opencast coal mine -- draft layout plan with contours",
           font=b26, fill=(30, 30, 30))
    d.text((MARGIN + 760, 24), "Typical values, not any real mine.  "
           "Levels are RL in metres, original ground RL 300.", font=f14,
           fill=(90, 90, 90))
    d.rectangle([ox, oy, ox + PW, oy + PH], outline=(60, 60, 60), width=2)

    # faults (assumed, after the geology-plan reference)
    for (a, b), name in ((((-760, -640), (260, 860)), "F1"),
                         (((-120, -840), (720, 760)), "F2")):
        steps = 60
        for i in range(0, steps, 2):
            p0 = (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
            p1 = (a[0] + (b[0] - a[0]) * (i + 1) / steps,
                  a[1] + (b[1] - a[1]) * (i + 1) / steps)
            d.line([P(*p0), P(*p1)], fill=(30, 100, 50), width=3)
        halo_text(d, P(b[0] - 40, b[1] - 60), f"{name} fault (assumed)", f12,
                  fill=(30, 100, 50))

    # surface roads
    exit_pt = HAUL[0]
    dump_start = DUMP_ROAD[0]
    roads = [
        [exit_pt, (exit_pt[0] - 200, exit_pt[1] + 160), (-860, 560), (-960, 430)],
        [exit_pt, (exit_pt[0] + 260, exit_pt[1] + 120), (620, 560),
         (dump_start[0] - 40, dump_start[1] + 30), dump_start],
        [(-860, 560), (-860, -500), (-900, -620)],
    ]
    for r in roads:
        d.line([P(*p) for p in r], fill=(90, 88, 84), width=12, joint="curve")
        d.line([P(*p) for p in r], fill=(140, 138, 132), width=8, joint="curve")

    # infrastructure (west, beyond the safety line)
    def box(x, y, w, h, fill, label, lab_dx=0, lab_dy=-1):
        x0, y0 = P(x - w / 2, y + h / 2)
        x1, y1 = P(x + w / 2, y - h / 2)
        d.rectangle([x0, y0, x1, y1], fill=fill, outline=(30, 30, 30), width=2)
        halo_text(d, ((x0 + x1) / 2 + lab_dx, (y0 if lab_dy < 0 else y1)
                      + lab_dy * 12), label, f12)

    d.line([P(-1060, YMIN + 10), P(-1060, YMAX - 10)], fill=(40, 40, 40), width=5)
    for yy in np.arange(YMIN + 20, YMAX - 20, 24):
        d.line([P(-1068, yy), P(-1052, yy)], fill=(40, 40, 40), width=2)
    halo_text(d, P(-990, 870), "Railway siding", f12)
    box(-960, 430, 90, 70, (200, 200, 196), "CHP", lab_dy=1)
    box(-1015, 560, 40, 40, (200, 200, 196), "Silo", lab_dy=-1)
    d.line([P(-960, 465), P(-1015, 540)], fill=(60, 60, 60), width=4)
    box(-930, -150, 100, 70, (120, 160, 200), "Workshop")
    box(-930, -330, 70, 50, (220, 220, 214), "Mine office", lab_dy=1)
    box(-930, 110, 50, 50, (180, 180, 180), "Substation")
    box(1380, -760, 40, 40, (220, 220, 214), "Magazine", lab_dx=-30)

    # drainage: settling pond, pump pipeline from the west sump
    pond = [P(-880, 760), P(-720, 760), P(-720, 660), P(-880, 660)]
    d.polygon(pond, fill=(92, 142, 168), outline=(30, 70, 110))
    halo_text(d, P(-800, 795), "Settling pond", f12)
    su, sv = SUMPS[0][0], SUMPS[0][1]
    s_w = to_world(su, sv, PIT_C, PIT_ROT)
    crest = pit_point(math.radians(150.0), -60.0)
    pipe = [s_w, pit_point(math.radians(152.0), 100.0), crest, (-800, 660)]
    d.line([P(*p) for p in pipe], fill=(20, 80, 170), width=4)
    draw_symbol(d, *P(*s_w), "P", f10)
    draw_symbol(d, *P(*pit_point(math.radians(152.0), 60.0)), "P", f10)

    # machines
    for th, ins, kind in ((180, 175, "S"), (172, 182, "D"), (8, 178, "S"),
                          (14, 184, "D"), (205, 137, "SM"), (250, 23, "Dr"),
                          (262, 23, "Dr")):
        draw_symbol(d, *P(*pit_point(math.radians(th), ins)), kind, f10)
    draw_symbol(d, *P(*pit_point(math.radians(8.0), -45.0)), "DL", f10)
    draw_symbol(d, *P(*HAUL[60]), "D", f10)
    draw_symbol(d, *P(*DUMP_ROAD[60]), "D", f10)
    draw_symbol(d, *P(DUMP_C[0] + 20, DUMP_C[1] + 20), "Dz", f10)

    # labels in the plan
    for txt, (x, y) in (
            ("OPENCAST PIT", (-160, 170)), ("Floor RL 220 (coal)", (-40, 60)),
            ("OB spur", to_world(SPUR["u"], -250, PIT_C, PIT_ROT)),
            ("Sump", to_world(SUMPS[1][0], SUMPS[1][1] - 80, PIT_C, PIT_ROT)),
            ("Sump", to_world(SUMPS[0][0], SUMPS[0][1] - 80, PIT_C, PIT_ROT)),
            ("OB DUMP", (DUMP_C[0], DUMP_C[1] + 260)),
            ("Top RL 360 (planted)", (DUMP_C[0], DUMP_C[1] - 40)),
            ("Haul road 1:16", pit_point(math.radians(90), -75)),
            ("Garland drain", pit_point(math.radians(-60), -55)),
            ("Safety line (crest + 110 m)", pit_point(math.radians(-100), -140)),
            ("Dump road 1:16", DUMP_ROAD[30])):
        halo_text(d, P(x, y), txt, b14 if txt.isupper() else f12)

    # RL labels down the south-west wall
    for ins, rl in ((23, 285), (61, 270), (99, 255), (137, 240), (190, 220),
                    (-25, 300)):
        halo_text(d, P(*pit_point(math.radians(-140), ins)), str(rl), f10,
                  fill=(90, 50, 20))
    for ins, rl in ((35, 315), (85, 330), (135, 345), (185, 360)):
        halo_text(d, P(*dump_point(math.radians(-60), ins)), str(rl), f10,
                  fill=(90, 50, 20))

    # section line A-A' through pit and dump
    A = (-1000.0, -268.0 + 0.0)
    B = (1460.0, 448.0)
    d.line([P(*A), P(*B)], fill=(20, 20, 20), width=2)
    for pt, nm in ((A, "A"), (B, "A'")):
        X, Y = P(*pt)
        d.ellipse([X - 12, Y - 12, X + 12, Y + 12], fill=(255, 255, 255),
                  outline=(20, 20, 20), width=2)
        d.text((X, Y), nm, font=b14, fill=(20, 20, 20), anchor="mm")

    # north arrow and scale bar
    nx_, ny_ = ox + PW - 60, oy + 70
    d.polygon([(nx_, ny_ - 40), (nx_ - 14, ny_ + 10), (nx_, ny_),
               (nx_ + 14, ny_ + 10)], fill=(30, 30, 30))
    d.text((nx_, ny_ + 26), "N", font=b18, fill=(30, 30, 30), anchor="mm")
    sx0, sy0 = ox + 30, oy + PH - 40
    for i in range(5):
        c = (30, 30, 30) if i % 2 == 0 else (255, 255, 255)
        d.rectangle([sx0 + i * 50, sy0, sx0 + (i + 1) * 50, sy0 + 10], fill=c,
                    outline=(30, 30, 30))
    for i, lab in ((0, "0"), (2, "200"), (5, "500 m")):
        halo_text(d, (sx0 + i * 50, sy0 + 24), lab, f10)

    # ------------------------------------------------ section A-A'
    sx, sy = MARGIN, TITLE + PH + MARGIN * 2
    sw, sh = PW, SEC_H - MARGIN
    d.rectangle([sx, sy, sx + sw, sy + sh], fill=(255, 255, 255),
                outline=(60, 60, 60), width=2)
    d.text((sx + 12, sy + 8), "Section A-A'  (vertical scale x3)", font=b14,
           fill=(30, 30, 30))
    n = sw - 40
    tt = np.linspace(0, 1, n)
    lx = A[0] + (B[0] - A[0]) * tt
    ly = A[1] + (B[1] - A[1]) * tt
    S = fields(lx, ly)
    prof = S["h"]
    vs = 3.0 * (n / math.hypot(B[0] - A[0], B[1] - A[1]))   # px per metre
    base_y = sy + 120

    def Y_(lvl):
        return base_y - lvl * vs

    for i in range(n):
        X = sx + 20 + i
        top = prof[i]
        # strata: overburden to RL 240, coal 240-220, floor rock below
        d.line([(X, Y_(min(top, 0))), (X, Y_(COAL_TOP))], fill=(176, 156, 128))
        if top > COAL_TOP:
            pass
        d.line([(X, Y_(min(top, COAL_TOP))), (X, Y_(FLOOR))], fill=(50, 50, 56))
        d.line([(X, Y_(min(top, FLOOR))), (X, Y_(-110))], fill=(140, 140, 146))
        if top > 0:
            col = (118, 150, 88) if top >= DUMP_TOP - 0.01 else (226, 210, 172)
            d.line([(X, Y_(top)), (X, Y_(0))], fill=col)
        if S["water"][i]:
            d.line([(X, Y_(SUMP_LEVEL + 3)), (X, Y_(SUMP_LEVEL))],
                   fill=(92, 142, 168))
    # mask the excavated part white above the profile
    for i in range(n):
        X = sx + 20 + i
        if prof[i] < 0:
            d.line([(X, Y_(0)), (X, Y_(prof[i]) - 1)], fill=(255, 255, 255))
    d.line([(sx + 20 + i, Y_(prof[i])) for i in range(n)], fill=(30, 30, 30),
           width=2)
    for lvl, rl in ((60, 360), (0, 300), (-30, 270), (-60, 240), (-80, 220)):
        d.line([(sx + 14, Y_(lvl)), (sx + 20, Y_(lvl))], fill=(30, 30, 30))
        d.text((sx + 4, Y_(lvl)), f"{rl}", font=f10, fill=(60, 60, 60), anchor="lm")
    halo_text(d, (sx + 40, sy + sh - 16), "A", b14)
    halo_text(d, (sx + sw - 30, sy + sh - 16), "A'", b14)
    for txt, frac, lvl in (("Pit, 80 m deep", 0.36, -95), ("OB dump +60 m", 0.82, 75),
                           ("Coal seam 20 m", 0.08, -70), ("Benches 15 m / berms 30 m",
                                                          0.22, 12)):
        halo_text(d, (sx + 20 + frac * n, Y_(lvl)), txt, f12)

    # ------------------------------------------------ legend & data
    lx0, ly0 = MARGIN * 2 + PW, TITLE
    d.rectangle([lx0, ly0, lx0 + LEG_W - MARGIN, H - MARGIN], fill=(255, 255, 255),
                outline=(60, 60, 60), width=2)
    y = ly0 + 14
    d.text((lx0 + 14, y), "Design values", font=b18, fill=(30, 30, 30))
    y += 32
    rows = [
        ("Pit at crest", "approx. 1.3 km x 0.8 km"),
        ("Pit depth", "80 m (RL 300 to RL 220)"),
        ("Benches", "15 m high, 30 m berms, faces ~62 deg"),
        ("Overburden", "4 benches = 60 m"),
        ("Coal seam", "20 m, RL 240 to RL 220"),
        ("Pit floor", "approx. 0.95 km x 0.45 km"),
        ("Haul road", "one road, 28 m wide, 1 in 16,"),
        ("", "3 legs + 2 hairpins down N wall"),
        ("Sumps", "2, water at RL 214"),
        ("OB dump", "4 lifts of 15 m to RL 360,"),
        ("", "30 m berms, planted top"),
        ("Dump road", "spiral, 24 m wide, 1 in 16"),
        ("Safety line", "110 m beyond the crest"),
        ("Contours", "5 m; bold = bench levels"),
    ]
    for k, v in rows:
        d.text((lx0 + 14, y), k, font=b14 if k else f14, fill=(40, 40, 40))
        d.text((lx0 + 150, y), v, font=f14, fill=(40, 40, 40))
        y += 23
    y += 12
    d.text((lx0 + 14, y), "Legend", font=b18, fill=(30, 30, 30))
    y += 34

    def key(sample, text):
        nonlocal y
        sample(lx0 + 20, y)
        d.text((lx0 + 80, y), text, font=f14, fill=(40, 40, 40), anchor="lm")
        y += 26

    def swatch(c):
        return lambda X, Y: d.rectangle([X, Y - 8, X + 44, Y + 8], fill=c,
                                        outline=(60, 60, 60))

    def line(c, w, dashed=False):
        def f(X, Y):
            if dashed:
                for i in range(0, 44, 12):
                    d.line([(X + i, Y), (X + i + 7, Y)], fill=c, width=w)
            else:
                d.line([(X, Y), (X + 44, Y)], fill=c, width=w)
        return f

    def sym(kind):
        return lambda X, Y: draw_symbol(d, X + 22, Y, kind, f10)

    key(swatch((203, 199, 170)), "Original ground (RL 300)")
    key(swatch((170, 156, 136)), "Overburden benches")
    key(swatch((60, 60, 66)), "Coal seam & floor")
    key(swatch((214, 200, 168)), "OB spur / dump")
    key(swatch((118, 150, 88)), "Plantation (reclaimed top)")
    key(swatch((92, 142, 168)), "Water: sumps, settling pond")
    key(line((112, 110, 106), 8), "Haul & dump roads")
    key(line((70, 52, 36), 3), "Contour at bench level")
    key(line((120, 110, 95), 1), "Contour, 5 m interval")
    key(line((40, 110, 190), 3), "Garland & toe drains")
    key(line((20, 80, 170), 4), "Pump pipeline to pond")
    key(line((200, 40, 40), 3, True), "Safety line (no structures)")
    key(line((30, 100, 50), 3, True), "Fault (assumed)")
    for kind, text in (("S", "Shovel at the face"), ("D", "Dumper"),
                       ("SM", "Surface miner on coal"), ("Dr", "Drill on bench"),
                       ("Dz", "Dozer on dump"), ("DL", "Dragline at the crest"),
                       ("P", "Dewatering pump")):
        key(sym(kind), text)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    page.save(OUT, optimize=True)
    print(OUT, page.size)


if __name__ == "__main__":
    main()
