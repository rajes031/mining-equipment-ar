"""
make_mine_layout.py -- a generic large opencast coal mine, as a 1:700 model.

Not any particular mine. It is the typical layout of a big Singrauli-style
coal mine -- a walking dragline stripping the lower overburden and casting it
straight into the mined-out void, shovel-dumper benches above it, a thick
seam worked in two benches, a 1 in 16 haul ramp, internal and external dumps,
and a coal handling plant loading a railway siding -- built from typical
dimensions rather than traced from anyone's imagery.

The dump follows the general look of big Singrauli dumps on satellite
images -- a wedding cake of many narrow terraces stepping up to a planted
top -- but its shape and sizes are typical values, not traced.

The whole mine is built at true scale in metres and then shrunk to 1:700, so
the model is a table-top diorama about 2.5 m by 2.2 m: big enough to walk
round in AR, small enough to fit in a classroom. All the machines in it are
the catalogue's own generators, placed at work.

Layout, true scale (x across strike, z along strike, y up, ground at y = 0):

    x < -360   surface: haul road, CHP, silo and siding, workshop, office
    -360..-232 two shovel-dumper overburden benches, 12 m high
    -232..-160 dragline bench at -36 m
    -160..-56  dragline highwall, then the coal seam in two 10 m benches
    -56..16    coal floor at -86 m
    16..1200   terraced dump: 10 m lifts from the coal floor up to a planted
               top 80 m above ground, reached by a road up its south flank
    z > 560    haul ramp switchbacks cut into the end wall

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

COAL_TOP, COAL_FLOOR = -66.0, -86.0
PIT_HALF = 560.0                       # half-length of the pit along strike
RAMP_GRADE = 1.0 / 16.0
RAMP_HALF_W = 14.0                     # 28 m: over 3x a 7.7 m wide truck

# highwall section, crest to coal floor: (x, level) corners
HW_X = [-2000, -360, -352, -304, -296, -240, -232, -160, -152, -112, -104,
        -64, -56, 16]
HW_Y = [0, 0, -12, -12, -24, -24, -36, -36, COAL_TOP, COAL_TOP, -76, -76,
        COAL_FLOOR, COAL_FLOOR]
SPOIL_TOE_X = 16.0
SPOIL_SLOPE = 0.75                     # tan 37 degrees, angle of repose
VOID_X1 = 500.0                        # mined-out void runs this far east
SUMP = dict(x0=-40.0, x1=8.0, z0=-232.0, z1=-184.0, depth=-92.0)

# The big terraced dump: a rounded rectangle at ground level, built up in
# 10 m lifts to a planted top 80 m above ground. Below ground its lifts carry
# on down into the void to the coal floor, so from the pit side it is one
# long staircase of ~17 terraces -- tight on the pit side, wider on the far
# side, with the top pushed off-centre, as big Singrauli dumps look from
# above.
DUMP = dict(x0=274.0, x1=1200.0, z0=-700.0, z1=660.0, r=240.0)
LIFT = 10.0
FACE = LIFT / SPOIL_SLOPE              # 13.3 m of slope per lift
DUMP_TOP = 80.0
BERM_PIT, BERM_FAR, BERM_SPREAD = 30.0, 26.0, 200.0
TOP_Z = -120.0                         # the planted top sits south of centre

# plantation road: along the ground to the dump toe, then up the south flank
DUMP_ROAD = [(1180.0, -760.0), (1150.0, -690.0), (640.0, -220.0)]
DUMP_ROAD_HALF_W = 7.0

# haul ramp centre line: floor -> up through the end wall -> switchbacks
RAMP_PATH = [(-20.0, 240.0), (-20.0, 600.0), (-330.0, 600.0),
             (-330.0, 648.0), (-20.0, 648.0), (-20.0, 696.0),
             (-330.0, 696.0)]


# ---------------------------------------------------------------- terrain

def hw(x):
    return np.interp(x, HW_X, HW_Y)


def ramp_field(x, z):
    """Distance to the ramp centre line, and the ramp level there."""
    best_d = np.full(np.shape(x), np.inf)
    best_s = np.zeros(np.shape(x))
    s0 = 0.0
    for (ax, az), (bx, bz) in zip(RAMP_PATH, RAMP_PATH[1:]):
        dx, dz = bx - ax, bz - az
        seg = math.hypot(dx, dz)
        t = np.clip(((x - ax) * dx + (z - az) * dz) / (seg * seg), 0, 1)
        px, pz = ax + t * dx, az + t * dz
        d = np.hypot(x - px, z - pz)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_s = np.where(better, s0 + t * seg, best_s)
        s0 += seg
    level = np.minimum(0.0, COAL_FLOOR + best_s * RAMP_GRADE)
    return best_d, level


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


def dump_inset(x, z):
    """Signed distance inside the dump's ground-level outline (+ inside)."""
    cx, cz = (DUMP["x0"] + DUMP["x1"]) / 2, (DUMP["z0"] + DUMP["z1"]) / 2
    hx = (DUMP["x1"] - DUMP["x0"]) / 2 - DUMP["r"]
    hz = (DUMP["z1"] - DUMP["z0"]) / 2 - DUMP["r"]
    qx, qz = np.abs(x - cx) - hx, np.abs(z - cz) - hz
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0))
    inside = np.minimum(np.maximum(qx, qz), 0)
    return DUMP["r"] - outside - inside


def berm_spacing(x, z):
    """Horizontal metres per lift: tight on the pit side, wide beyond."""
    fx = np.clip((x - DUMP["x0"]) / (DUMP["x1"] - DUMP["x0"]), 0, 1)
    fz = (np.hypot(z - TOP_Z, 160.0) - 160.0) / (DUMP["z1"] - DUMP["z0"])
    return BERM_PIT + fx * (BERM_FAR + BERM_SPREAD * fz)


def dump_height(x, z):
    u = dump_inset(x, z) / berm_spacing(x, z)
    k = np.floor(u)
    run = (u - k) * berm_spacing(x, z)
    return np.minimum(LIFT * (k + np.minimum(run / FACE, 1.0)), DUMP_TOP)


def dump_road_level(x, z):
    d, s = path_field(DUMP_ROAD, x, z)
    (ax, az), (bx, bz) = DUMP_ROAD[0], DUMP_ROAD[1]
    flat = math.hypot(bx - ax, bz - az)
    climb = sum(math.hypot(q[0] - p[0], q[1] - p[1])
                for p, q in zip(DUMP_ROAD[1:], DUMP_ROAD[2:]))
    return d, np.clip((s - flat) * DUMP_TOP / climb, 0.0, DUMP_TOP)


def height(x, z):
    e = PIT_HALF - np.abs(z)                 # distance in from the pit end
    end_wall = hw(-360.0 + e)
    void = np.where(x < VOID_X1, COAL_FLOOR, 0.0)
    cut = np.maximum(np.where(x <= SPOIL_TOE_X, hw(x), void), end_wall)
    h = np.where(x > SPOIL_TOE_X, np.maximum(cut, dump_height(x, z)), cut)
    in_sump = ((x > SUMP["x0"]) & (x < SUMP["x1"]) &
               (z > SUMP["z0"]) & (z < SUMP["z1"]))
    h = np.where(in_sump, SUMP["depth"], h)
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
    if flat and avg >= DUMP_TOP - 0.01:
        return "reclaimed_top"
    if avg > 0.5 or (cx > SPOIL_TOE_X and avg > COAL_FLOOR + 0.1
                     and abs(cz) < PIT_HALF + 40):
        return "internal_dump"
    if avg >= -0.5:
        return "original_ground"
    if flat and avg <= COAL_FLOOR + 0.01:
        return "coal_floor"
    if avg <= COAL_TOP + 0.01:
        return "coal_seam"
    if avg <= -36.0 + 0.01:
        return "dragline_bench"
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
    "overburden_benches": ("overburden", "Overburden benches (shovel-dumper)",
        "Upper overburden, drilled, blasted and removed by rope shovels and "
        "dumpers in 12 m benches. Benches are kept wider than they are "
        "high, and each working bench wide enough for the shovel, a truck "
        "spotting and a truck passing.", (-300, -12, -300), (-0.3, 1, 0)),
    "dragline_bench": ("overburden_dark", "Dragline bench & highwall",
        "The dragline sits on this bench, about 36 m down, and digs the "
        "30 m of overburden below it down to the top of the coal, casting "
        "it across the pit onto the spoil side. The steep face below it is "
        "the highwall -- watch it for cracks after every blast.",
        (-196, -34, -250), (0, 1, 0)),
    "coal_seam": ("coal", "Coal seam (approx. 20 m, two benches)",
        "A thick seam, worked in two 10 m benches by shovels and surface "
        "miners. Partings and the roof and floor contact are mined "
        "carefully to keep dilution down; fires start on long-exposed coal "
        "benches, so they are not left standing.", (-132, -64, -320),
        (0, 1, 0)),
    "coal_floor": ("floor_rock", "Coal floor (pit bottom)",
        "The working floor at about 86 m depth, 70 m wide -- room for the "
        "loading shovel, trucks turning and the sump. It is kept graded "
        "towards the sump so water does not stand on the haul route.",
        (-20, -85, 0), (0, 1, 0)),
    "haul_ramp": ("road", "Haul ramp (1 in 16, 28 m wide)",
        "Gradient not steeper than 1 in 16 and width at least three times "
        "the widest truck. At that grade, climbing 86 m takes about 1.4 km "
        "of ramp -- which is why it switches back three times in the end "
        "wall. Berms of at least axle height on every open edge.",
        (-175, -40, 648), (0, 1, 0)),
    "internal_dump": ("spoil_light", "Terraced overburden dump (10 m lifts)",
        "Overburden put back into the mined-out void and then built up "
        "above ground: about 17 terraces from the coal floor to a top 80 m "
        "above the original surface. Each lift is 10 m at the 37 degree "
        "angle of repose, with a berm behind it, so the overall slope is "
        "well under 28 degrees. The toe must never be undercut, and every "
        "berm slopes back into the dump with a drain.", (420, 41, 300),
        (-0.3, 1, 0)),
    "reclaimed_top": ("grass", "Reclaimed dump top (plantation)",
        "Once a dump reaches its final height its top is graded, covered "
        "with the stored topsoil and planted -- grass first to bind the "
        "surface, then native trees. Seen from a satellite, reclaimed dump "
        "tops show as green patches among the bare terraces.",
        (700, 81, -60), (0, 1, 0)),
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
        if key in ("internal_dump", "reclaimed_top", "dump_road"):
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
        hotspot=(-16, -87, -208), hotspot_normal=(0, 1, 0))
    sump.box(center=((SUMP["x0"] + SUMP["x1"]) / 2, -88.5,
                     (SUMP["z0"] + SUMP["z1"]) / 2),
             size=(SUMP["x1"] - SUMP["x0"], 7.0, SUMP["z1"] - SUMP["z0"]))
    drain = b.part(
        "garland_drain", "water",
        label="Garland drain",
        note=("A drain round the pit crest that catches surface run-off "
              "before it can pour over the highwall, flood the pit or "
              "soften the benches. A statutory requirement before the "
              "monsoon."),
        hotspot=(-368, 0.5, 300), hotspot_normal=(0, 1, 0))
    drain.box(center=(-368, 0.15, 0), size=(3.0, 0.3, 2 * PIT_HALF))

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
    roads.box(center=(-367, 0.2, 696), size=(74, 0.4, 28))
    roads.box(center=(-42, 0.2, -600), size=(724, 0.4, 28))     # to the dump

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
    fleet["dl_house"] = place(make_dragline.build(), "dl_", -196, -36, 40,
                              yaw=-90)
    fleet["rs_machinery_house"] = place(make_rope_shovel.build(), "rs_",
                                        -274, -24, -160, yaw=90)
    fleet["t1_dump_body"] = place(make_dumper.build(), "t1_", -262, -24,
                                  -134, yaw=0)
    fleet["hs_superstructure"] = place(make_shovel.build(), "hs_", -44, -86,
                                       120, yaw=90)
    fleet["t2_dump_body"] = place(make_dumper.build(), "t2_", -30, -86, 100)
    ramp_y = COAL_FLOOR + (400 - 240) * RAMP_GRADE
    fleet["t3_dump_body"] = place(make_dumper.build(), "t3_", -20, ramp_y,
                                  400, yaw=180,
                                  pitch=-math.degrees(math.atan(RAMP_GRADE)))
    fleet["sm_chassis"] = place(make_surface_miner.build(), "sm_", -132, -66,
                                -40)
    fleet["dz_engine_hood"] = place(make_dozer.build(), "dz_", 580, DUMP_TOP,
                                    -150, yaw=-90)
    fleet["gr_cab"] = place(make_grader.build(), "gr_", -390, 0.4, 200)

    roles = {
        "dl_house": ("Dragline at work",
            "Sitting on its bench, digging the lower overburden and casting "
            "it straight across the pit onto the spoil side -- no trucks. "
            "Its bucket is nearly 90 m out from the tub."),
        "rs_machinery_house": ("Rope shovel loading a dumper",
            "Working the upper overburden bench face. The truck spots "
            "beside it on the operator's side; three or four passes load "
            "it."),
        "t1_dump_body": ("Dumper under the shovel",
            "Overburden goes to the internal dump by in-pit roads, or up "
            "and out to the external dump."),
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

    # -- shrink to 1:500 ---------------------------------------------------------
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
        "A whole opencast coal mine as a table-top model: the dragline "
        "stripping overburden and casting it into the void, shovel-dumper "
        "benches above it, the coal worked in two benches, a 1 in 16 haul "
        "ramp switching back out of the pit, a huge terraced overburden "
        "dump climbing out of the void to a planted top, and the coal "
        "handling plant loading a train. A typical layout built from "
        "typical dimensions -- not a copy of any real mine."),
    "specs": [
        ["Model scale", "1:700 -- 1 cm on the model is 7 m in the mine"],
        ["Area shown", "approx. 1.75 km x 1.5 km"],
        ["Pit depth to coal floor", "approx. 86 m"],
        ["Overburden", "approx. 66 m: 3 shovel benches (36 m) + dragline cut (30 m)"],
        ["Coal seam", "approx. 20 m, two 10 m benches"],
        ["Bench height (shovel-dumper)", "12 m, benches 48-56 m wide"],
        ["Dragline bench", "at approx. 36 m depth, 72 m wide"],
        ["Pit floor width", "approx. 72 m"],
        ["Haul ramp", "1 in 16, 28 m wide, approx. 1.4 km long"],
        ["Spoil slope", "approx. 37 degrees (angle of repose)"],
        ["Overburden dump", "10 m lifts, approx. 17 terraces from coal floor to top"],
        ["Dump top", "80 m above original ground, topsoiled and planted"],
        ["Dump footprint above ground", "approx. 0.9 km x 1.35 km"],
        ["Dump access road", "approx. 1 in 9, up the south flank"],
        ["Stripping ratio (this section)", "approx. 2.4 m3 of overburden per tonne of coal"],
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
