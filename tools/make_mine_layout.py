"""
make_mine_layout.py -- a generic large opencast coal mine, as a 1:700 model.

Not any particular mine. It is the typical layout of a big Singrauli-style
coal mine -- an 80 m pit with 15 m benches and 30 m berms on all four walls,
one 1 in 16 haul road spiralling from crest to floor, a terraced dump beside
the pit, and a coal handling plant loading a railway siding -- built from
typical dimensions rather than traced from anyone's imagery.

The dump follows the general look of big Singrauli dumps on satellite
images -- a wedding cake of many narrow terraces stepping up to a planted
top -- but its shape and sizes are typical values, not traced.

The whole mine is built at true scale in metres and then shrunk to 1:700, so
the model is a table-top diorama about 2.5 m by 2.2 m: big enough to walk
round in AR, small enough to fit in a classroom. All the machines in it are
the catalogue's own generators, placed at work.

Layout, true scale (x across strike, z along strike, y up, ground at y = 0):

    x < -360   surface: haul road, CHP, silo and siding, workshop, office
    -340..260  the pit (z -560..560): benches step in 38 m per 15 m, so
               the floor at -80 m is 160 m in from the crest all round
    260..320   surface strip with the dragline at the crest
    320..1200  terraced dump: 10 m lifts up to a planted top 80 m above
               ground, with terrace-to-terrace ramps on its pit face and a
               service road up its south flank

Run:  python make_mine_layout.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import make_dozer
import make_dragline
import make_dumper
import make_grader
import make_rope_shovel
import make_shovel
import make_surface_miner
from glbgen import Builder, compose, rotate, translate
from machkit import bar, standard_materials, write_record

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

SCALE = 1.0 / 700.0
CELL = 8.0
X0, X1 = -504.0, 1240.0
Z0, Z1 = -760.0, 760.0
BASE = -110.0

# ---- the pit: a bowl with benches on all four walls -------------------------
# 80 m deep: four 15 m overburden benches, then the 20 m coal seam. Every
# berm is 30 m wide and every face takes 8 m of plan (about 62 degrees), so
# the walls step in 38 m per bench and the floor is 160 m in from the crest.
BENCH_H, BERM_W, FACE_W = 15.0, 30.0, 8.0
COAL_TOP, COAL_FLOOR = -60.0, -80.0
PIT = dict(x0=-340.0, x1=260.0, z0=-560.0, z1=560.0, r=180.0)
PIT_X = [0, 8, 38, 46, 76, 84, 114, 122, 152, 160]      # inset from crest
PIT_Y = [0, -15, -15, -30, -30, -45, -45, COAL_TOP, COAL_TOP, COAL_FLOOR]
FLOOR_INSET = PIT_X[-1]
RAMP_GRADE = 1.0 / 16.0
RAMP_HALF_W = 14.0                     # 28 m: over 3x a 7.7 m wide truck
SUMP = dict(x0=-170.0, x1=-130.0, z0=-390.0, z1=-350.0)
SPOIL_SLOPE = 0.75                     # tan 37 degrees, angle of repose

# ---- the terraced dump beside the pit ------------------------------------------
# A rounded rectangle at ground level, built up in 10 m lifts to a planted
# top 80 m above ground -- tight terraces on the pit side, wider beyond, the
# top pushed off-centre, as big Singrauli dumps look from above.
LIFT = 10.0
BERM_PIT, BERM_FAR, BERM_SPREAD = 30.0, 26.0, 200.0
DUMP = dict(x0=320.0, x1=1200.0, z0=-700.0, z1=660.0, r=240.0)
FACE = LIFT / SPOIL_SLOPE              # 13.3 m of slope per lift
DUMP_TOP = 80.0
TOP_Z = -120.0                         # the planted top sits south of centre

# short ramps joining each dump terrace to the next, 1 in 16, switching
# direction at every lift so a dumper climbs from the ground to the top
DUMP_RAMP_ZC = -20.0
DUMP_RAMP_LEN = LIFT / RAMP_GRADE      # 160 m per 10 m lift

# plantation road: along the ground to the dump toe, then up the south flank
DUMP_ROAD = [(1180.0, -760.0), (1150.0, -690.0), (740.0, -200.0)]
DUMP_ROAD_HALF_W = 7.0


# ---------------------------------------------------------------- terrain

def rounded_inset(box, x, z):
    """Signed distance inside a rounded rectangle (+ inside)."""
    cx, cz = (box["x0"] + box["x1"]) / 2, (box["z0"] + box["z1"]) / 2
    hx = (box["x1"] - box["x0"]) / 2 - box["r"]
    hz = (box["z1"] - box["z0"]) / 2 - box["r"]
    qx, qz = np.abs(x - cx) - hx, np.abs(z - cz) - hz
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0))
    inside = np.minimum(np.maximum(qx, qz), 0)
    return box["r"] - outside - inside


def contour_point(box, d, p):
    """Point p metres along the pit contour inset d, starting at the south
    end of the west wall and running north (clockwise seen from above)."""
    cx, cz = (box["x0"] + box["x1"]) / 2, (box["z0"] + box["z1"]) / 2
    r = max(box["r"] - d, 20.0)
    hx = (box["x1"] - box["x0"]) / 2 - d - r       # straight half-lengths
    hz = (box["z1"] - box["z0"]) / 2 - d - r
    arc = math.pi / 2 * r
    legs = [("w", 2 * hz), ("nw", arc), ("n", 2 * hx), ("ne", arc),
            ("e", 2 * hz), ("se", arc), ("s", 2 * hx), ("sw", arc)]
    for name, length in legs * 2:
        if p > length:
            p -= length
            continue
        f = p / length if length else 0.0
        if name == "w":
            return cx - hx - r, cz - hz + p
        if name == "n":
            return cx - hx + p, cz + hz + r
        if name == "e":
            return cx + hx + r, cz + hz - p
        if name == "s":
            return cx + hx - p, cz - hz - r
        a = f * math.pi / 2
        if name == "nw":
            return cx - hx - r * math.cos(a), cz + hz + r * math.sin(a)
        if name == "ne":
            return cx + hx + r * math.sin(a), cz + hz + r * math.cos(a)
        if name == "se":
            return cx + hx + r * math.cos(a), cz - hz - r * math.sin(a)
        return cx - hx - r * math.sin(a), cz - hz - r * math.cos(a)
    raise ValueError("p beyond two laps")


def build_ramp_path():
    """One haul road spiralling down the pit walls from crest to floor.

    It drops 1 m in 16 and moves in from the crest as it drops, so it stays
    on the walls: in at the crest of the west wall, down the west wall,
    round the north-west corner and along the north wall to the floor.
    """
    length = -COAL_FLOOR / RAMP_GRADE              # 1280 m
    pts = []
    for p in np.arange(0.0, length + 8.0, 8.0):
        d = FLOOR_INSET * min(p / length, 1.0)
        pts.append(contour_point(PIT, d, p))
    # run on across the floor so the road ends on it
    (ax, az), (bx, bz) = pts[-2], pts[-1]
    k = 40.0 / math.hypot(bx - ax, bz - az)
    pts.append((bx + (bx - ax) * k, bz + (bz - az) * k))
    return pts


RAMP_PATH = build_ramp_path()


def path_field(path, x, z):
    """Distance to a polyline, and the distance along it to that point."""
    best_d = np.full(np.shape(x), np.inf)
    best_s = np.zeros(np.shape(x))
    s0 = 0.0
    for (ax, az), (bx, bz) in zip(path, path[1:]):
        dx, dz = bx - ax, bz - az
        seg = math.hypot(dx, dz)
        t = np.clip(((x - ax) * dx + (z - az) * dz) / (seg * seg), 0, 1)
        d = np.hypot(x - (ax + t * dx), z - (az + t * dz))
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_s = np.where(better, s0 + t * seg, best_s)
        s0 += seg
    return best_d, best_s


def ramp_field(x, z):
    """Distance to the haul road centre line, and the road level there."""
    d, s = path_field(RAMP_PATH, x, z)
    return d, np.maximum(COAL_FLOOR, -s * RAMP_GRADE)


def pit_height(x, z):
    return np.interp(rounded_inset(PIT, x, z), PIT_X, PIT_Y, left=0.0)


def dump_inset(x, z):
    return rounded_inset(DUMP, x, z)


def berm_spacing(x, z):
    """Horizontal metres per lift: tight on the pit side, wide beyond."""
    fx = np.clip((x - DUMP["x0"]) / (DUMP["x1"] - DUMP["x0"]), 0, 1)
    fz = (np.hypot(z - TOP_Z, 160.0) - 160.0) / (DUMP["z1"] - DUMP["z0"])
    return BERM_PIT + fx * (BERM_FAR + BERM_SPREAD * fz)


def dump_height(x, z):
    u = dump_inset(x, z) / berm_spacing(x, z)
    k = np.floor(u)
    run = (u - k) * berm_spacing(x, z)
    h = np.minimum(LIFT * (k + np.minimum(run / FACE, 1.0)), DUMP_TOP)
    return np.maximum(h, 0.0)


def dump_ramp(x, z):
    """Mask and level of the terrace-to-terrace ramps on the dump's pit face.

    Each ramp lies against one terrace face, over the face and half the
    berm below it, and climbs one lift along strike. Alternate lifts climb
    in opposite directions, so the top of one ramp is the foot of the next.
    """
    s = berm_spacing(x, z)
    u = dump_inset(x, z) / s
    k = np.floor(u + 0.5 * (s - FACE) / s)
    run = (u - k) * s
    t = (z - (DUMP_RAMP_ZC - DUMP_RAMP_LEN / 2)) / DUMP_RAMP_LEN
    t = np.where(np.mod(k, 2) == 0, t, 1.0 - t)
    cx = (DUMP["x0"] + DUMP["x1"]) / 2
    on = ((run <= FACE) & (t >= 0) & (t <= 1) & (x < cx)
          & (k >= 0) & (k < DUMP_TOP / LIFT))
    return on, LIFT * (k + np.clip(t, 0, 1))


def dump_road_level(x, z):
    d, s = path_field(DUMP_ROAD, x, z)
    (ax, az), (bx, bz) = DUMP_ROAD[0], DUMP_ROAD[1]
    flat = math.hypot(bx - ax, bz - az)
    climb = sum(math.hypot(q[0] - p[0], q[1] - p[1])
                for p, q in zip(DUMP_ROAD[1:], DUMP_ROAD[2:]))
    return d, np.clip((s - flat) * DUMP_TOP / climb, 0.0, DUMP_TOP)


def height(x, z):
    pit, dump = pit_height(x, z), dump_height(x, z)
    h = np.where(dump > 0, np.maximum(pit, dump), pit)
    on, level = dump_ramp(x, z)
    h = np.where(on, level, h)
    in_sump = ((x > SUMP["x0"]) & (x < SUMP["x1"]) &
               (z > SUMP["z0"]) & (z < SUMP["z1"]))
    h = np.where(in_sump, COAL_FLOOR - 6.0, h)
    d, level = ramp_field(x, z)
    h = np.where(d <= RAMP_HALF_W, level, h)
    d, level = dump_road_level(x, z)
    return np.where(d <= DUMP_ROAD_HALF_W, level, h)


def classify(cx, cz, avg, flat):
    d, _ = ramp_field(cx, cz)
    if d <= RAMP_HALF_W:
        return "haul_ramp"
    d, _ = dump_road_level(cx, cz)
    if d <= DUMP_ROAD_HALF_W:
        return "dump_road"
    if dump_ramp(cx, cz)[0]:
        return "dump_ramps"
    if flat and avg >= DUMP_TOP - 0.01:
        return "reclaimed_top"
    if avg > 0.5:
        return "internal_dump"
    if avg >= -0.5:
        return "original_ground"
    if flat and avg <= COAL_FLOOR + 0.01:
        return "coal_floor"
    if avg <= COAL_TOP + 0.01:
        return "coal_seam"
    return "overburden_benches"


def emit_terrain(parts):
    xs = np.arange(X0, X1 + CELL / 2, CELL)
    zs = np.arange(Z0, Z1 + CELL / 2, CELL)
    gx, gz = np.meshgrid(xs, zs)
    H = height(gx, gz)
    nz, nx = H.shape

    for j in range(nz - 1):
        i = 0
        while i < nx - 1:
            c = (H[j, i], H[j, i + 1], H[j + 1, i + 1], H[j + 1, i])
            flat = max(c) - min(c) < 1e-6
            cls = classify(xs[i] + CELL / 2, zs[j] + CELL / 2,
                           sum(c) / 4.0, flat)
            k = i + 1
            if flat:                          # merge a run of equal flats
                while k < nx - 1:
                    c2 = (H[j, k], H[j, k + 1], H[j + 1, k + 1], H[j + 1, k])
                    if max(c2) - min(c2) > 1e-6 or abs(c2[0] - c[0]) > 1e-6:
                        break
                    if classify(xs[k] + CELL / 2, zs[j] + CELL / 2,
                                c2[0], True) != cls:
                        break
                    k += 1
            x0, x1, z0, z1 = xs[i], xs[k], zs[j], zs[j + 1]
            a = (x0, H[j, i], z0)
            b_ = (x0, H[j + 1, i], z1)
            cc = (x1, H[j + 1, k], z1)
            d = (x1, H[j, k], z0)
            parts[cls].tri(a, b_, cc)
            parts[cls].tri(a, cc, d)
            i = k
    return xs, zs, H


def emit_skirts(parts, xs, zs, H):
    """Vertical edges of the model, banded by stratum -- a cut-away section."""
    bands = [(BASE, COAL_FLOOR, "coal_floor"), (COAL_FLOOR, COAL_TOP, "coal_seam"),
             (COAL_TOP, 0.0, "overburden_benches"),
             (0.0, DUMP_TOP + 1.0, "internal_dump")]
    edges = [
        ([(x, Z0) for x in xs], [H[0, i] for i in range(len(xs))], (0, 0, -1)),
        ([(x, Z1) for x in xs], [H[-1, i] for i in range(len(xs))], (0, 0, 1)),
        ([(X0, z) for z in zs], [H[j, 0] for j in range(len(zs))], (-1, 0, 0)),
        ([(X1, z) for z in zs], [H[j, -1] for j in range(len(zs))], (1, 0, 0)),
    ]
    for pts, hs, out in edges:
        for (p, hp), (q, hq) in zip(zip(pts, hs), zip(pts[1:], hs[1:])):
            for lo, hi, cls in bands:
                tp, tq = min(max(hp, lo), hi), min(max(hq, lo), hi)
                if tp <= lo and tq <= lo:
                    continue
                quad = [(p[0], lo, p[1]), (q[0], lo, q[1]),
                        (q[0], tq, q[1]), (p[0], tp, p[1])]
                facing(parts[cls], quad, out)
    facing(parts["coal_floor"], [(X0, BASE, Z0), (X1, BASE, Z0),
                                 (X1, BASE, Z1), (X0, BASE, Z1)], (0, -1, 0))


def facing(part, quad, out):
    a, b, c, d = (np.asarray(v, dtype=float) for v in quad)
    n = np.cross(b - a, c - a)
    if np.dot(n, out) < 0:
        a, b, c, d = a, d, c, b
    part.tri(a, b, c)
    part.tri(a, c, d)


# ---------------------------------------------------------------- build

TERRAIN = {
    "original_ground": ("ground", "Original ground (surface)",
        "The undisturbed surface. Topsoil is stripped ahead of mining and "
        "stored separately -- it is the most valuable material for "
        "reclamation, and losing it under the dumps is the commonest "
        "reclamation failure.", (-430, 1, -420), (0, 1, 0)),
    "overburden_benches": ("overburden", "Overburden benches (15 m high, 30 m wide)",
        "Overburden, drilled, blasted and removed by shovels and dumpers in "
        "four benches of 15 m. Each berm is 30 m wide -- twice the bench "
        "height, room for the shovel, a truck spotting and a truck passing "
        "-- and each face stands at about 62 degrees. The benches step all "
        "the way round the pit, which is what gives an opencast mine its "
        "stepped, amphitheatre look from above.", (199, -30, -300),
        (-0.3, 1, 0)),
    "coal_seam": ("coal", "Coal seam (approx. 20 m)",
        "The coal, 20 m thick, at the bottom of the pit -- from 60 m down to "
        "the 80 m floor. It is cut by surface miners or blasted and loaded "
        "by shovels. Fires start on long-exposed coal benches, so they are "
        "not left standing.", (-203, -60, 80), (0, 1, 0)),
    "coal_floor": ("floor_rock", "Pit floor (80 m deep)",
        "The bottom of the pit, about 80 m below the surface and 280 m "
        "across: room for the loading shovel, trucks turning and the sump. "
        "It is kept graded towards the sump so water does not stand on the "
        "haul road.", (0, -80, 0), (0, 1, 0)),
    "haul_ramp": ("road", "Haul road (1 in 16, 28 m wide)",
        "The one road between the pit floor and the surface. It spirals "
        "down the pit walls -- in at the west crest, down the west wall, "
        "round the corner and along the north wall to the floor -- at no "
        "steeper than 1 in 16, so dropping 80 m takes about 1.3 km of road. "
        "28 m wide, more than three times the widest truck, with a bund of "
        "at least axle height on the open edge.",
        (RAMP_PATH[60][0], 0, RAMP_PATH[60][1]), (0, 1, 0)),
    "dump_ramps": ("road", "Dump ramps (terrace to terrace, 1 in 16)",
        "A short ramp on every terrace face, 160 m long and about 22 m "
        "wide, climbing one 10 m lift. The ramps alternate direction, so a "
        "loaded dumper drives up one ramp, turns on the berm and takes the "
        "next -- from the ground right up to the dump top. Every berm used "
        "as a road keeps a safety bund on its open edge.",
        (380, 0, -20), (-0.3, 1, 0)),
    "internal_dump": ("spoil_light", "Terraced overburden dump (10 m lifts)",
        "Overburden from the pit, built up in eight 10 m lifts to a top 80 m "
        "above the original surface. Each lift is at the 37 degree angle of "
        "repose with a berm behind it, so the overall slope is well under "
        "28 degrees. The toe must never be undercut, and every berm slopes "
        "back into the dump with a drain.", (480, 0, 300), (-0.3, 1, 0)),
    "reclaimed_top": ("grass", "Reclaimed dump top (plantation)",
        "Once a dump reaches its final height its top is graded, covered "
        "with the stored topsoil and planted -- grass first to bind the "
        "surface, then native trees. Seen from a satellite, reclaimed dump "
        "tops show as green patches among the bare terraces.",
        (760, 81, -60), (0, 1, 0)),
    "dump_road": ("road", "Dump access road",
        "A service road climbing the dump flank at about 1 in 9 for "
        "plantation crews, water tankers and inspection -- not for loaded "
        "dumpers. It has a berm on its open edge like any haul road.",
        (900, 40, -460), (0, 1, 0)),
}


def build() -> Builder:
    b = Builder("opencast_mine_layout")
    standard_materials(b)
    b.material("ground", (0.47, 0.46, 0.30), roughness=0.95, metallic=0.0)
    b.material("overburden", (0.60, 0.51, 0.40), roughness=0.92, metallic=0.0)
    b.material("overburden_dark", (0.52, 0.45, 0.37), roughness=0.92,
               metallic=0.0)
    b.material("coal", (0.08, 0.08, 0.09), roughness=0.55, metallic=0.1)
    b.material("floor_rock", (0.44, 0.44, 0.46), roughness=0.9, metallic=0.0)
    b.material("road", (0.66, 0.63, 0.57), roughness=0.95, metallic=0.0)
    b.material("spoil", (0.66, 0.58, 0.47), roughness=0.95, metallic=0.0)
    b.material("spoil_light", (0.72, 0.65, 0.52), roughness=0.95, metallic=0.0)
    b.material("grass", (0.36, 0.46, 0.22), roughness=0.95, metallic=0.0)
    b.material("trees", (0.16, 0.30, 0.13), roughness=0.95, metallic=0.0)
    b.material("water", (0.20, 0.36, 0.50), roughness=0.1, metallic=0.0,
               alpha=0.85)
    b.material("concrete", (0.74, 0.74, 0.72), roughness=0.8, metallic=0.0)
    b.material("roof_blue", (0.25, 0.42, 0.62), roughness=0.6, metallic=0.3)
    b.material("wagon", (0.42, 0.22, 0.15), roughness=0.7, metallic=0.4)

    parts = {}
    for key, (mat, label, note, hot, nrm) in TERRAIN.items():
        if key != "original_ground":
            y = float(height(np.array([hot[0]]), np.array([hot[2]]))[0])
            hot = (hot[0], y + 1.0, hot[2])
        parts[key] = b.part(key, mat, label=label, note=note, hotspot=hot,
                            hotspot_normal=nrm)
    xs, zs, H = emit_terrain(parts)
    emit_skirts(parts, xs, zs, H)

    # -- water ---------------------------------------------------------------
    sump = b.part(
        "sump", "water",
        label="Sump (pit dewatering)",
        note=("The low point of the floor, where rain and seepage collect "
              "and are pumped out. Before the monsoon the pumps are sized "
              "for the worst storm on record -- a flooded pit floor stops "
              "the mine and can trap machines."),
        hotspot=(-150, COAL_FLOOR - 1, -370), hotspot_normal=(0, 1, 0))
    sump.box(center=((SUMP["x0"] + SUMP["x1"]) / 2, COAL_FLOOR - 2.5,
                     (SUMP["z0"] + SUMP["z1"]) / 2),
             size=(SUMP["x1"] - SUMP["x0"], 7.0, SUMP["z1"] - SUMP["z0"]))
    drain = b.part(
        "garland_drain", "water",
        label="Garland drain",
        note=("A drain round the pit crest that catches surface run-off "
              "before it can pour over the highwall, flood the pit or "
              "soften the benches. A statutory requirement before the "
              "monsoon."),
        hotspot=(-362, 0.5, 300), hotspot_normal=(0, 1, 0))
    drain.box(center=(-362, 0.15, 0), size=(3.0, 0.3, PIT["z1"] - PIT["z0"]))

    # -- plantation on the dump top, and the forest beyond the lease ---------
    trees = b.part(
        "plantation", "trees",
        label="Plantation on the reclaimed dump",
        note=("Native species -- sal, khair, neem, bamboo -- planted at "
              "about 2500 per hectare on the topsoiled dump top. In a few "
              "years the canopy closes and the dump reads as forest from "
              "above, which is how reclamation progress is checked on "
              "satellite images."),
        hotspot=(700, DUMP_TOP + 14, 40), hotspot_normal=(0, 1, 0))
    rng = np.random.default_rng(7)
    for tx in np.arange(X0 + 8, X1 - 8, 16.0):
        for tz in np.arange(Z0 + 8, Z1 - 8, 16.0):
            px = tx + rng.uniform(-6, 6)
            pz = tz + rng.uniform(-6, 6)
            r = rng.uniform(3.5, 6.0)
            ring_x = px + np.array([0, r, -r, 0, 0])
            ring_z = pz + np.array([0, 0, 0, r, -r])
            hs = height(ring_x, ring_z)
            on_top = np.all(hs >= DUMP_TOP - 0.01)
            forest = (np.all(np.abs(hs) < 0.01) and dump_inset(px, pz) < -30
                      and (px > 900 or (px > 560 and pz > 640)))
            if not (on_top or forest):
                continue
            if dump_road_level(px, pz)[0] < DUMP_ROAD_HALF_W + 6:
                continue
            tall = rng.uniform(9.0, 15.0)
            trees.cyl(center=(px, hs[0] + tall / 2, pz), radius=r,
                      length=tall, axis="y", segments=6)

    # -- surface infrastructure ----------------------------------------------
    roads = b.part(
        "surface_roads", "road",
        label="Surface haul roads",
        note="Coal goes to the CHP, overburden to the external dump. Roads "
             "are kept separate from light-vehicle routes wherever possible "
             "-- a 220 t truck driver cannot see a jeep.",
        hotspot=(-390, 0.5, 120), hotspot_normal=(0, 1, 0))
    roads.box(center=(-390, 0.2, 40), size=(28, 0.4, 1320))
    sx, sz = RAMP_PATH[0]                          # haul road at the crest
    roads.box(center=((sx - 404) / 2, 0.2, sz), size=(sx + 404, 0.4, 28))
    roads.box(center=(-4, 0.2, -630), size=(800, 0.4, 28))     # to the dump
    roads.box(center=(-390, 0.2, -660), size=(28, 0.4, 88))

    chp = b.part(
        "coal_handling_plant", "concrete",
        label="Coal handling plant (CHP)",
        note=("Trucks tip into the receiving hopper; the coal is crushed to "
              "a sized product (typically under 100 mm) and belted to the "
              "silo. For a pit-head power station it may go straight onto "
              "a merry-go-round train or a long conveyor."),
        hotspot=(-470, 31, 560), hotspot_normal=(0, 1, 0))
    chp.box(center=(-470, 15, 560), size=(36, 30, 30))
    chp.box(center=(-444, 5, 560), size=(14, 10, 22))            # hopper

    conv = b.part(
        "conveyor_to_silo", "steel",
        label="Conveyor gallery",
        note="An enclosed, inclined belt from the crusher to the top of the "
             "silo -- enclosed to keep coal dust in and rain out. Belt "
             "inclines are kept under about 16-18 degrees or the coal "
             "rolls back.",
        hotspot=(-470, 36, 490), hotspot_normal=(1, 1, 0))
    bar(conv, (-470, 26, 545), (-470, 46, 420), 4.0, 3.5)
    for z in (520, 480, 445):
        y = 26 + (545 - z) / 125 * 20
        conv.box(center=(-470, y / 2, z), size=(1.0, y, 1.0))

    silo = b.part(
        "loading_silo", "concrete",
        label="Rapid loading silo",
        note="Holds a train-load or more, and loads each wagon to its "
             "weight in about a minute as the rake creeps underneath. "
             "Accurate loading avoids under-loaded wagons and overload "
             "penalties.",
        hotspot=(-458, 30, 405), hotspot_normal=(1, 0.3, 0))
    silo.cyl(center=(-470, 28, 405), radius=11.0, length=36.0, axis="y",
             segments=20)
    for sx in (-1, 1):
        for sz in (-1, 1):
            silo.box(center=(-470 + sx * 7, 5, 405 + sz * 7),
                     size=(1.5, 10, 1.5))

    rail = b.part(
        "railway_siding", "dark",
        label="Railway siding",
        note="Coal leaves by rail in rakes of about 58 wagons, nearly "
             "4000 t each. At pit-head power stations a merry-go-round "
             "loop runs trains continuously between silo and boiler.",
        hotspot=(-470, 2, -40), hotspot_normal=(0, 1, 0))
    rail.box(center=(-470, 0.4, 0), size=(8.0, 0.8, Z1 - Z0))
    for sx in (-1, 1):
        rail.box(center=(-470 + sx * 0.84, 1.0, 0), size=(0.2, 0.4, Z1 - Z0))

    wagons = b.part(
        "coal_rake", "wagon",
        label="Coal rake (wagons)",
        note="Open wagons being loaded under the silo, about 60 t of coal "
             "each.",
        hotspot=(-466, 5, 300), hotspot_normal=(1, 0.3, 0))
    for k in range(14):
        z = 392 - k * 11.5
        wagons.box(center=(-470, 2.9, z), size=(3.2, 3.4, 10.6))

    shed = b.part(
        "workshop", "roof_blue",
        label="Heavy-equipment workshop",
        note="Bays tall enough to tip a dumper body and lift a dragline "
             "motor. Most of a machine's availability is won or lost here.",
        hotspot=(-434, 17, -120), hotspot_normal=(1, 0.5, 0))
    shed.box(center=(-434, 7.5, -120), size=(40, 15, 64))
    shed.prism([(-454, 15), (-414, 15), (-434, 20)], extent=64, axis="z",
               offset=(0, 0, -120))

    office = b.part(
        "mine_office", "concrete",
        label="Mine office & first aid",
        note="Manager's office, shift control room, first-aid room and the "
             "statutory registers. The muster point for an emergency.",
        hotspot=(-434, 11, -260), hotspot_normal=(1, 0.5, 0))
    office.box(center=(-434, 5, -260), size=(30, 10, 22))

    power = b.part(
        "substation", "steel",
        label="Substation (6.6 kV feed)",
        note="Steps down the grid supply and feeds the dragline and rope "
             "shovels through trailing cables. Only authorised electrical "
             "staff work here.",
        hotspot=(-434, 7, 40), hotspot_normal=(1, 0.5, 0))
    power.box(center=(-434, 3, 40), size=(18, 6, 18))
    for sx in (-1, 1):
        power.box(center=(-434 + sx * 9, 1.0, 40), size=(0.4, 2.0, 22))

    mag = b.part(
        "explosives_magazine", "concrete",
        label="Explosives magazine",
        note=("Far from everything else, behind earth mounds, fenced and "
              "guarded, at the distances set by the licence. Bulk "
              "explosive is now usually mixed in the hole by a pump truck, "
              "so far less is stored."),
        hotspot=(-440, 6, -720), hotspot_normal=(0, 1, 0))
    mag.box(center=(-440, 2, -720), size=(10, 4, 10))
    for sx in (-1, 1):
        mag.prism([(-12, 0), (-8, 0), (-10, 6)], extent=26, axis="z",
                  offset=(-440 + sx * 10 + (0 if sx < 0 else 20), 0, -720))

    # -- the fleet at work -----------------------------------------------------
    def place(builder, prefix, x, y, z, yaw=0.0, pitch=0.0):
        xf = compose(translate(x, y, z), rotate("x", pitch), rotate("y", yaw))
        added = b.absorb(builder, prefix=prefix, xform=xf,
                         drop=("scale_figure",))
        return added

    fleet = {}
    climb = -math.degrees(math.atan(RAMP_GRADE))
    fleet["dl_house"] = place(make_dragline.build(), "dl_", 290, 0.0, 150,
                              yaw=90)
    fleet["rs_machinery_house"] = place(make_rope_shovel.build(), "rs_",
                                        240, -15, -200, yaw=-90)
    fleet["t1_dump_body"] = place(make_dumper.build(), "t1_", 228, -15,
                                  -174, yaw=0)
    fleet["hs_superstructure"] = place(make_shovel.build(), "hs_", -60,
                                       COAL_FLOOR, -150, yaw=90)
    fleet["t2_dump_body"] = place(make_dumper.build(), "t2_", -46,
                                  COAL_FLOOR, -170)
    # a loaded dumper climbing the haul road, part-way up the west wall
    (ax, az), (px, pz), (bx, bz) = RAMP_PATH[74], RAMP_PATH[75], RAMP_PATH[76]
    _, t3_y = ramp_field(np.array([px]), np.array([pz]))
    fleet["t3_dump_body"] = place(make_dumper.build(), "t3_", px,
                                  float(t3_y[0]), pz,
                                  yaw=math.degrees(math.atan2(bx - ax, bz - az)),
                                  pitch=climb)
    # a loaded dumper half-way up the dump ramp that climbs from 20 m to 30 m
    xs_ = np.arange(DUMP["x0"] - 20, DUMP["x0"] + 400, 1.0)
    on, lv = dump_ramp(xs_, np.full_like(xs_, DUMP_RAMP_ZC))
    pick = np.flatnonzero(on & (np.abs(lv - 25.0) < 0.01))
    t4_x = float(xs_[pick].mean())
    fleet["t4_dump_body"] = place(make_dumper.build(), "t4_", t4_x, 25.0,
                                  DUMP_RAMP_ZC, yaw=180, pitch=climb)
    fleet["sm_chassis"] = place(make_surface_miner.build(), "sm_", -203,
                                COAL_TOP, -40)
    fleet["dz_engine_hood"] = place(make_dozer.build(), "dz_", 690, DUMP_TOP,
                                    -150, yaw=-90)
    fleet["gr_cab"] = place(make_grader.build(), "gr_", -390, 0.4, 200)

    roles = {
        "dl_house": ("Dragline at the crest",
            "Standing on the surface between the pit and the dump, reaching "
            "nearly 90 m out over the benches to dig overburden and cast it "
            "back towards the dump -- no trucks."),
        "rs_machinery_house": ("Rope shovel loading a dumper",
            "Working the first 15 m overburden bench. The truck spots "
            "beside it on the operator's side; three or four passes load "
            "it."),
        "t1_dump_body": ("Dumper under the shovel",
            "Overburden goes up the haul road and out to the terraced "
            "dump."),
        "hs_superstructure": ("Hydraulic shovel on coal",
            "Loading coal from the bottom bench at the pit floor. Coal "
            "loading needs a clean floor and care at the seam floor to "
            "keep stone out of the product."),
        "t2_dump_body": ("Coal dumper",
            "Loaded at the face, out along the floor and up the ramp to the "
            "CHP."),
        "t3_dump_body": ("Loaded dumper on the ramp",
            "Climbing at 1 in 16. A loaded 220 t truck manages about "
            "10-12 km/h on this grade."),
        "t4_dump_body": ("Dumper climbing the dump ramps",
            "Carrying overburden from the pit up the dump: one 160 m ramp "
            "per terrace, a turn on the berm, then the next ramp, until it "
            "reaches the lift being tipped."),
        "sm_chassis": ("Surface miner on the coal bench",
            "Cutting the top coal bench in thin layers with no blasting, "
            "loading straight into trucks."),
        "dz_engine_hood": ("Dozer on the dump top",
            "Grading the final dump top and spreading topsoil ahead of the "
            "planters, and keeping the crest berm intact."),
        "gr_cab": ("Grader on the haul road",
            "Keeping the surface haul road smooth and crowned to shed "
            "water."),
    }
    by_name = {p.name: p for p in b._parts}
    for key, (label, note) in roles.items():
        p = by_name[key]
        added = fleet[key]
        lo = np.min([q.bounds()[0] for q in added], axis=0)
        hi = np.max([q.bounds()[1] for q in added], axis=0)
        p.label, p.note = label, note
        p._hotspot = ((lo[0] + hi[0]) / 2, hi[1] + 2.0, (lo[2] + hi[2]) / 2)
        p.hotspot_normal = (0, 1, 0)

    # -- shrink to 1:700 ---------------------------------------------------------
    s = np.diag([SCALE, SCALE, SCALE, 1.0])
    for p in b._parts:
        n = np.asarray(p.hotspot_normal, dtype=float)
        p.transform(s)
        p.hotspot_normal = tuple(n / (np.linalg.norm(n) or 1.0))

    b.labelled = list(TERRAIN) + ["sump", "garland_drain", "plantation",
                                  "surface_roads",
                                  "coal_handling_plant", "conveyor_to_silo",
                                  "loading_silo", "railway_siding",
                                  "coal_rake", "workshop", "mine_office",
                                  "substation", "explosives_magazine"] \
        + list(roles)
    return b


SPECS = {
    "id": "mine-layout",
    "name": "Opencast coal mine layout",
    "subtitle": "Generic Singrauli-style dragline + shovel-dumper mine -- 1:700 scale model",
    "category": "Mine layout",
    "summary": (
        "A whole opencast coal mine as a table-top model: an 80 m deep pit "
        "with 15 m benches and 30 m berms stepping down all four walls, one "
        "1 in 16 haul road spiralling from the crest to the floor, the coal "
        "at the bottom, a terraced overburden dump beside the pit rising to "
        "a planted top, and the coal handling plant loading a train. A "
        "typical layout built from typical dimensions -- not a copy of any "
        "real mine."),
    "specs": [
        ["Model scale", "1:700 -- 1 cm on the model is 7 m in the mine"],
        ["Area shown", "approx. 1.75 km x 1.5 km"],
        ["Pit size at the crest", "approx. 600 m x 1120 m"],
        ["Pit depth", "80 m to the floor"],
        ["Benches", "15 m high, 30 m wide berms, faces about 62 degrees"],
        ["Overburden", "60 m: four 15 m benches"],
        ["Coal seam", "20 m, from 60 m to 80 m depth"],
        ["Pit floor", "approx. 280 m x 800 m"],
        ["Haul road", "one road, 1 in 16, 28 m wide, approx. 1.3 km, spiralling down the walls"],
        ["Overburden dump", "eight 10 m lifts to a top 80 m above ground"],
        ["Dump ramps", "one per terrace, 1 in 16, 160 m long, alternating direction"],
        ["Dump top", "topsoiled and planted"],
        ["Dump footprint", "approx. 0.9 km x 1.35 km"],
        ["Dump access road", "approx. 1 in 9, up the south flank"],
        ["Stripping ratio (floor area)", "approx. 2.1 m3 of overburden per tonne of coal"],
    ],
    "safety": [
        "Haul roads: gradient not steeper than 1 in 16, width at least three "
        "times the widest vehicle, berms of at least axle height on every "
        "open edge.",
        "Bench height within the digging height of the machine working it, "
        "and benches wide enough for the shovel, a spotting truck and a "
        "passing truck.",
        "Garland drains and sump pumps ready before the monsoon.",
        "Dump toes are never undercut and dump edges always carry a berm; "
        "most dump accidents start there.",
        "Explosives magazine isolated at licence distances; blasting only "
        "with the danger zone cleared and guarded.",
    ],
    "ar_tips": [
        "Place it on an open floor: at 1:700 it is about 2.5 m by 2.2 m. "
        "Kneel at the end to look up the haul ramp the way a truck driver "
        "would, then look down on the dump from above to see it the way a "
        "satellite does.",
        "Find each machine -- the labels say what it is doing in the "
        "mining cycle -- then open its own page to see it full size.",
    ],
}


def main():
    b = build()
    record = write_record(b, SPECS, WEB, "mine-layout")
    keep = set(b.labelled)
    record["parts"] = [p for p in record["parts"] if p["node"] in keep]
    import json
    (WEB / "data" / "mine-layout.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


if __name__ == "__main__":
    main()
