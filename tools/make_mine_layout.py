"""
make_mine_layout.py -- a generic opencast coal mine, at true size (1:1).

Built from the same height field as the agreed 2D draft (draft_layout.py,
docs/mine-layout-draft.png), so the model and the contour plan match:

* an irregular oval pit, 80 m deep -- four 15 m overburden benches and a
  20 m coal seam, 30 m berms all round;
* one 28 m haul road at 1 in 16, three legs and two hairpins down the north
  wall to the floor;
* a dark coal floor with two water-filled sumps and an overburden spur
  running down into the pit between them;
* a terraced overburden dump beside the pit -- four 15 m lifts to a planted
  top -- with a spiral road;
* garland drain, sump pumps and a pipeline to a settling pond, the coal
  handling plant, silo and rail siding, workshop, office and magazine.

Typical values, not any real mine. Plan coordinates in draft_layout are x
east, y north; here the model's z runs south (z = -y), y is up, and the whole
thing is built and kept in metres -- 2.6 km x 1.75 km -- for walking round in
VR at true size. The VR app offers a 1:1000 table-top view as well.

Run:  python make_mine_layout.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import draft_layout as D
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

SCALE = 1.0                     # true size: metres in, metres out
CELL = 8.0
X0, X1 = D.XMIN, D.XMAX
Z0, Z1 = -D.YMAX, -D.YMIN
BASE = -110.0


def M(p, y=0.0):
    """Plan point (x east, y north) -> model point (x, y up, z south)."""
    return (p[0], y, -p[1])


def ground(px_, py_):
    """Terrain level at a plan point."""
    return float(D.fields(np.array([px_]), np.array([py_]))["h"][0])


# ---------------------------------------------------------------- terrain

def classify_grid(gx, gy):
    F = D.fields(gx, gy)
    h = F["h"]
    cls = np.full(h.shape, "overburden_benches", dtype=object)
    cls[h <= D.COAL_TOP + 0.01] = "coal_seam"
    cls[h <= D.FLOOR + 0.01] = "coal_floor"
    cls[np.abs(h) < 0.01] = "original_ground"
    cls[F["spur"]] = "ob_spur"
    cls[F["dump"]] = "ob_dump"
    cls[F["top"]] = "reclaimed_top"
    cls[F["droad"]] = "dump_road"
    cls[F["road"]] = "haul_road"
    return cls, F["water"]


def emit_terrain(parts):
    xs = np.arange(X0, X1 + CELL / 2, CELL)
    zs = np.arange(Z0, Z1 + CELL / 2, CELL)
    gx, gz = np.meshgrid(xs, zs)
    H = D.fields(gx, -gz)["h"]
    cx, cz = np.meshgrid(xs[:-1] + CELL / 2, zs[:-1] + CELL / 2)
    C, W = classify_grid(cx, -cz)
    nz, nx = H.shape
    for j in range(nz - 1):
        i = 0
        while i < nx - 1:
            c = (H[j, i], H[j, i + 1], H[j + 1, i + 1], H[j + 1, i])
            flat = max(c) - min(c) < 1e-6
            cls = C[j, i]
            k = i + 1
            if flat:
                while k < nx - 1:
                    c2 = (H[j, k], H[j, k + 1], H[j + 1, k + 1], H[j + 1, k])
                    if max(c2) - min(c2) > 1e-6 or abs(c2[0] - c[0]) > 1e-6:
                        break
                    if C[j, k] != cls:
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
    # water surface over the sumps
    lvl = D.FLOOR - 1.5
    for j in range(nz - 1):
        for i in range(nx - 1):
            if W[j, i]:
                x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
                parts["sumps"].tri((x0, lvl, z0), (x0, lvl, z1), (x1, lvl, z1))
                parts["sumps"].tri((x0, lvl, z0), (x1, lvl, z1), (x1, lvl, z0))
    return xs, zs, H


def facing(part, quad, out):
    a, b, c, d = (np.asarray(v, dtype=float) for v in quad)
    n = np.cross(b - a, c - a)
    if np.dot(n, out) < 0:
        a, b, c, d = a, d, c, b
    part.tri(a, b, c)
    part.tri(a, c, d)


def emit_skirts(parts, xs, zs, H):
    """Vertical edges of the model, banded by stratum -- a cut-away section."""
    bands = [(BASE, D.FLOOR, "coal_floor"), (D.FLOOR, D.COAL_TOP, "coal_seam"),
             (D.COAL_TOP, 0.0, "overburden_benches"),
             (0.0, D.DUMP_TOP + 1.0, "ob_dump")]
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
                facing(parts[cls], [(p[0], lo, p[1]), (q[0], lo, q[1]),
                                    (q[0], tq, q[1]), (p[0], tp, p[1])], out)
    facing(parts["coal_floor"], [(X0, BASE, Z0), (X1, BASE, Z0),
                                 (X1, BASE, Z1), (X0, BASE, Z1)], (0, -1, 0))


def ribbon(part, route, width, y):
    """A flat strip of the given width along a plan polyline, at height y."""
    for p, q in zip(route, route[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / n * width / 2, dx / n * width / 2
        ext = (dx / n * width / 2, dy / n * width / 2)     # overlap the joints
        a = (p[0] - ext[0], p[1] - ext[1])
        c = (q[0] + ext[0], q[1] + ext[1])
        quad = [M((a[0] + ox, a[1] + oy), y), M((c[0] + ox, c[1] + oy), y),
                M((c[0] - ox, c[1] - oy), y), M((a[0] - ox, a[1] - oy), y)]
        facing(part, quad, (0, 1, 0))


# ---------------------------------------------------------------- labels

def pit_pt(deg, inset):
    return D.pit_point(math.radians(deg), inset)


SUMP_W = D.to_world(D.SUMPS[0][0], D.SUMPS[0][1], D.PIT_C, D.PIT_ROT)
SUMP_E = D.to_world(D.SUMPS[1][0], D.SUMPS[1][1], D.PIT_C, D.PIT_ROT)


def _outward(deg):
    a, c = D.pit_point(math.radians(deg), 0.0), D.pit_point(math.radians(deg), 100.0)
    n = math.hypot(a[0] - c[0], a[1] - c[1])
    return ((a[0] - c[0]) / n, (a[1] - c[1]) / n)


# dragline on the surface just outside the east crest, facing into the pit
_o = _outward(8)
DRAGLINE_AT = pit_pt(8, -45)
DRAGLINE_FACING = (-_o[0], -_o[1])

# VR stations: where the player is put, and what they look at (plan points)
_PIT_MID = D.to_world(0, 0, D.PIT_C, D.PIT_ROT)
STATIONS = [
    ("Pit rim, south", pit_pt(-90, -70), _PIT_MID),
    ("Haul road, top", D.HAUL[0], D.HAUL[20]),
    ("Haul road, first hairpin", D.HAUL[40], D.HAUL[60]),
    ("Pit floor, west coal face", pit_pt(180, 225), pit_pt(180, 178)),
    ("Overburden spur", D.to_world(D.SPUR["u"], -170, D.PIT_C, D.PIT_ROT), _PIT_MID),
    ("Dragline", (DRAGLINE_AT[0] + _o[0] * 70, DRAGLINE_AT[1] + _o[1] * 70 + 40),
     DRAGLINE_AT),
    ("Dump top", (D.DUMP_C[0] - 60, D.DUMP_C[1] - 120), _PIT_MID),
    ("CHP and rail siding", (-860, 320), (-1000, 480)),
]


def vr_stations():
    out = []
    for name, p, look in STATIONS:
        y = max(ground(*p), D.FLOOR)
        out.append({"name": name,
                    "pos": {"x": p[0], "y": y, "z": -p[1]},
                    "look": {"x": look[0], "y": max(ground(*look), D.FLOOR),
                             "z": -look[1]}})
    return out

TERRAIN = {
    "original_ground": ("ground", "Original ground (RL 300)",
        "The undisturbed surface. Topsoil is stripped ahead of mining and "
        "stored separately -- it is the most valuable material for "
        "reclamation, and losing it under the dumps is the commonest "
        "reclamation failure.", (-650, 520)),
    "overburden_benches": ("overburden", "Overburden benches (15 m high, 30 m wide)",
        "Overburden, drilled, blasted and removed by shovels and dumpers in "
        "four benches of 15 m, from RL 300 down to RL 240. Each berm is "
        "30 m wide -- twice the bench height, room for the shovel, a truck "
        "spotting and a truck passing -- and each face stands at about 62 "
        "degrees.", pit_pt(-110, 23)),
    "coal_seam": ("coal", "Coal seam (20 m, RL 240 to RL 220)",
        "The coal, 20 m thick, at the bottom of the pit. It is cut by "
        "surface miners or blasted and loaded by shovels. Fires start on "
        "long-exposed coal, so faces are not left standing.",
        pit_pt(205, 137)),
    "coal_floor": ("floor_rock", "Pit floor (RL 220, 80 m deep)",
        "The bottom of the pit, about 0.95 km by 0.45 km. Room for the "
        "loading shovels, trucks turning and the sumps. It is graded "
        "towards the sumps so water does not stand on the roads.",
        D.to_world(0, 90, D.PIT_C, D.PIT_ROT)),
    "haul_road": ("road", "Haul road (1 in 16, 28 m wide)",
        "The one road between the pit floor and the surface: three legs "
        "and two hairpins down the north wall. No steeper than 1 in 16, "
        "28 m wide -- more than three times the widest truck -- with a bund "
        "of at least axle height on the open edge.", D.HAUL[40]),
    "ob_spur": ("spoil", "Overburden spur",
        "A tongue of overburden left running down into the pit from the "
        "south wall. It splits the floor into two working areas, each with "
        "its own sump, and is mined out or used for internal dumping as "
        "the pit advances.", D.to_world(D.SPUR["u"], -230, D.PIT_C, D.PIT_ROT)),
    "ob_dump": ("spoil_light", "Overburden dump (4 lifts of 15 m)",
        "Overburden from the pit, built in four 15 m lifts with 30 m berms "
        "to RL 360, 60 m above ground. Each face stands at the 37 degree "
        "angle of repose; the toe is never undercut and every berm slopes "
        "back into the dump with a drain.",
        D.dump_point(math.radians(-60), 75)),
    "reclaimed_top": ("grass", "Reclaimed dump top (plantation)",
        "Once a dump reaches its final height its top is graded, covered "
        "with stored topsoil and planted -- grass first, then native "
        "trees.", D.DUMP_C),
    "dump_road": ("road", "Dump road (1 in 16, spiral)",
        "Spirals up the dump from its pit-side toe so loaded dumpers can "
        "reach every lift being tipped.", D.DUMP_ROAD[30]),
    "sumps": ("water", "Sumps (pit dewatering)",
        "The low points of the floor, where rain and seepage collect and "
        "are pumped out. Before the monsoon the pumps are sized for the "
        "worst storm on record -- a flooded floor stops the mine.", SUMP_E),
}


# ---------------------------------------------------------------- build

def build() -> Builder:
    b = Builder("opencast_mine_layout")
    standard_materials(b)
    b.material("ground", (0.47, 0.46, 0.30), roughness=0.95, metallic=0.0)
    b.material("overburden", (0.56, 0.50, 0.43), roughness=0.92, metallic=0.0)
    b.material("coal", (0.08, 0.08, 0.09), roughness=0.55, metallic=0.1)
    b.material("floor_rock", (0.20, 0.20, 0.22), roughness=0.9, metallic=0.0)
    b.material("road", (0.36, 0.35, 0.34), roughness=0.95, metallic=0.0)
    b.material("spoil", (0.70, 0.64, 0.52), roughness=0.95, metallic=0.0)
    b.material("spoil_light", (0.74, 0.68, 0.55), roughness=0.95, metallic=0.0)
    b.material("grass", (0.36, 0.46, 0.22), roughness=0.95, metallic=0.0)
    b.material("trees", (0.16, 0.30, 0.13), roughness=0.95, metallic=0.0)
    b.material("water", (0.22, 0.40, 0.48), roughness=0.1, metallic=0.0,
               alpha=0.85)
    b.material("pipe", (0.10, 0.30, 0.65), roughness=0.4, metallic=0.3)
    b.material("concrete", (0.74, 0.74, 0.72), roughness=0.8, metallic=0.0)
    b.material("roof_blue", (0.25, 0.42, 0.62), roughness=0.6, metallic=0.3)
    b.material("wagon", (0.42, 0.22, 0.15), roughness=0.7, metallic=0.4)

    parts = {}
    for key, (mat, label, note, hot) in TERRAIN.items():
        y = ground(*hot) + 2.0
        if key == "sumps":
            y = D.FLOOR
        parts[key] = b.part(key, mat, label=label, note=note,
                            hotspot=M(hot, y), hotspot_normal=(0, 1, 0))
    xs, zs, H = emit_terrain(parts)
    emit_skirts(parts, xs, zs, H)

    # -- drainage -------------------------------------------------------------
    drain = b.part(
        "garland_drain", "water", label="Garland drain",
        note=("A drain round the pit, 30 m outside the crest, that catches "
              "surface run-off before it can pour over the benches, flood "
              "the pit or soften the walls. A statutory requirement before "
              "the monsoon."),
        hotspot=M(pit_pt(-60, -30), 1.0), hotspot_normal=(0, 1, 0))
    ribbon(drain, [pit_pt(t, -30) for t in np.arange(0, 361, 4)], 4.0, 0.5)

    pipe = b.part(
        "pump_pipeline", "pipe", label="Sump pumps & pipeline",
        note=("Pumps in the west sump lift the water up the wall in a "
              "pipeline laid beside the benches to the settling pond on the "
              "surface, where the silt drops out before the water is "
              "discharged or reused for dust suppression."),
        hotspot=M(SUMP_W, D.FLOOR + 6), hotspot_normal=(0, 1, 0))
    route = [SUMP_W] + [pit_pt(152, d) for d in (175, 140, 100, 60, 20)] + \
        [pit_pt(150, -60), (-800, 660)]
    fine = []
    for p, q in zip(route, route[1:]):
        for t in np.linspace(0, 1, 12, endpoint=False):
            fine.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    fine.append(route[-1])
    for p, q in zip(fine, fine[1:]):
        bar(pipe, M(p, max(ground(*p), D.FLOOR) + 1.5),
            M(q, max(ground(*q), D.FLOOR) + 1.5), 1.6, 1.6)
    for p in (SUMP_W, pit_pt(152, 60)):
        pipe.box(center=M(p, max(ground(*p), D.FLOOR) + 2.5), size=(8, 5, 6))

    pond = b.part(
        "settling_pond", "water", label="Settling pond",
        note=("Pit water is held here long enough for the suspended coal "
              "and clay to settle, so only clear water leaves the lease."),
        hotspot=M((-800, 710), 2.0), hotspot_normal=(0, 1, 0))
    pond.box(center=M((-800, 710), 0.3), size=(160, 0.6, 100))

    # -- trees on the reclaimed dump top --------------------------------------
    trees = b.part(
        "plantation", "trees", label="Plantation on the dump top",
        note=("Native species -- sal, khair, neem, bamboo -- planted at "
              "about 2500 per hectare on the topsoiled top. In a few years "
              "the canopy closes and the dump reads as forest from above."),
        hotspot=M(D.DUMP_C, D.DUMP_TOP + 16), hotspot_normal=(0, 1, 0))
    rng = np.random.default_rng(7)
    cx, cy = D.DUMP_C
    for tx in np.arange(cx - 200, cx + 200, 16.0):
        for ty in np.arange(cy - 260, cy + 260, 16.0):
            px_, py_ = tx + rng.uniform(-6, 6), ty + rng.uniform(-6, 6)
            r = rng.uniform(3.5, 6.0)
            F = D.fields(np.array([px_, px_ + r, px_ - r, px_, px_]),
                         np.array([py_, py_, py_, py_ + r, py_ - r]))
            if not F["top"].all():
                continue
            tall = rng.uniform(9.0, 15.0)
            trees.cyl(center=M((px_, py_), D.DUMP_TOP + tall / 2), radius=r,
                      length=tall, axis="y", segments=6)

    # -- surface roads --------------------------------------------------------
    roads = b.part(
        "surface_roads", "road", label="Surface roads",
        note=("Coal goes from the pit exit to the CHP, overburden to the "
              "dump. Light vehicles are kept on separate routes wherever "
              "possible -- a 220 t truck driver cannot see a jeep."),
        hotspot=M((-860, 100), 1.0), hotspot_normal=(0, 1, 0))
    ex, dst = D.HAUL[0], D.DUMP_ROAD[0]
    for route_ in ([ex, (ex[0] - 200, ex[1] + 160), (-860, 560), (-960, 430)],
                   [ex, (ex[0] + 260, ex[1] + 120), (620, 560),
                    (dst[0] - 40, dst[1] + 30), dst],
                   [(-860, 560), (-860, -500), (-900, -620)]):
        ribbon(roads, route_, 24.0, 0.6)

    # -- surface plant -------------------------------------------------------
    chp = b.part(
        "coal_handling_plant", "concrete", label="Coal handling plant (CHP)",
        note=("Trucks tip into the receiving hopper; the coal is crushed to "
              "a sized product and belted to the silo."),
        hotspot=M((-960, 430), 32), hotspot_normal=(0, 1, 0))
    chp.box(center=M((-960, 430), 15), size=(60, 30, 50))
    chp.box(center=M((-922, 430), 5), size=(16, 10, 24))
    conv = b.part(
        "conveyor_to_silo", "steel", label="Conveyor gallery",
        note="An enclosed belt from the crusher to the top of the silo.",
        hotspot=M((-1010, 500), 40), hotspot_normal=(1, 1, 0))
    bar(conv, M((-975, 455), 28), M((-1060, 545), 46), 4.0, 3.5)
    silo = b.part(
        "loading_silo", "concrete", label="Rapid loading silo",
        note=("Holds a train-load and loads each wagon to its weight in "
              "about a minute as the rake creeps underneath."),
        hotspot=M((-1060, 560), 48), hotspot_normal=(1, 0.3, 0))
    silo.cyl(center=M((-1060, 560), 28), radius=11.0, length=36.0, axis="y",
             segments=20)
    rail = b.part(
        "railway_siding", "dark", label="Railway siding",
        note=("Coal leaves by rail in rakes of about 58 wagons, nearly "
              "4000 t each."),
        hotspot=M((-1060, -300), 2), hotspot_normal=(0, 1, 0))
    rail.box(center=(-1060, 0.4, (Z0 + Z1) / 2), size=(8.0, 0.8, Z1 - Z0 - 20))
    wagons = b.part(
        "coal_rake", "wagon", label="Coal rake (wagons)",
        note="Open wagons being loaded under the silo, about 60 t each.",
        hotspot=M((-1060, 400), 6), hotspot_normal=(1, 0.3, 0))
    for k in range(16):
        wagons.box(center=M((-1060, 545 - k * 11.5), 2.9), size=(3.2, 3.4, 10.6))
    shed = b.part(
        "workshop", "roof_blue", label="Heavy-equipment workshop",
        note="Bays tall enough to tip a dumper body and lift a shovel motor.",
        hotspot=M((-930, -150), 20), hotspot_normal=(1, 0.5, 0))
    shed.box(center=M((-930, -150), 8), size=(64, 16, 40))
    office = b.part(
        "mine_office", "concrete", label="Mine office & first aid",
        note="Manager's office, control room, first aid -- the muster point.",
        hotspot=M((-930, -330), 12), hotspot_normal=(1, 0.5, 0))
    office.box(center=M((-930, -330), 5), size=(40, 10, 26))
    power = b.part(
        "substation", "steel", label="Substation",
        note="Feeds the shovels, pumps and plant. Authorised staff only.",
        hotspot=M((-930, 110), 8), hotspot_normal=(1, 0.5, 0))
    power.box(center=M((-930, 110), 3), size=(30, 6, 30))
    mag = b.part(
        "explosives_magazine", "concrete", label="Explosives magazine",
        note=("Far from everything else, mounded, fenced and guarded at the "
              "distances set by the licence."),
        hotspot=M((1380, -760), 6), hotspot_normal=(0, 1, 0))
    mag.box(center=M((1380, -760), 2), size=(12, 4, 12))

    # -- the fleet at work -----------------------------------------------------
    def place(builder, prefix, p, y, heading, pitch=0.0):
        """heading: plan direction (dx, dy) the machine's nose points to."""
        dx, dz = heading[0], -heading[1]
        yaw = math.degrees(math.atan2(-dx, -dz))
        xf = compose(translate(p[0], y, -p[1]), rotate("y", yaw),
                     rotate("x", pitch))
        return b.absorb(builder, prefix=prefix, xform=xf,
                        drop=("scale_figure",))

    def outward(deg):
        th = math.radians(deg)
        a = D.pit_point(th, 0.0)
        c = D.pit_point(th, 100.0)
        return (a[0] - c[0], a[1] - c[1])

    climb = -math.degrees(math.atan(D.GRADE))
    fleet = {}
    fleet["s1_superstructure"] = place(make_shovel.build(), "s1_",
                                       pit_pt(180, 178), D.FLOOR, outward(180))
    fleet["t1_dump_body"] = place(make_dumper.build(), "t1_", pit_pt(172, 186),
                                  D.FLOOR, outward(90))
    fleet["s2_superstructure"] = place(make_shovel.build(), "s2_",
                                       pit_pt(8, 178), D.FLOOR, outward(8))
    fleet["t2_dump_body"] = place(make_dumper.build(), "t2_", pit_pt(14, 188),
                                  D.FLOOR, outward(-80))
    fleet["sm_chassis"] = place(make_surface_miner.build(), "sm_",
                                pit_pt(205, 137), D.COAL_TOP, outward(115))
    fleet["rs_machinery_house"] = place(make_rope_shovel.build(), "rs_",
                                        pit_pt(-110, 26), -15.0, outward(-110))
    fleet["t3_dump_body"] = place(make_dumper.build(), "t3_", pit_pt(-100, 28),
                                  -15.0, outward(-10))
    a, p, c = D.HAUL[59], D.HAUL[60], D.HAUL[61]           # loaded, climbing
    fleet["t4_dump_body"] = place(make_dumper.build(), "t4_", p, ground(*p),
                                  (a[0] - c[0], a[1] - c[1]), climb)
    a, p, c = D.DUMP_ROAD[59], D.DUMP_ROAD[60], D.DUMP_ROAD[61]
    fleet["t5_dump_body"] = place(make_dumper.build(), "t5_", p, ground(*p),
                                  (c[0] - a[0], c[1] - a[1]), climb)
    fleet["dz_engine_hood"] = place(make_dozer.build(), "dz_",
                                    (D.DUMP_C[0] + 40, D.DUMP_C[1] - 150),
                                    D.DUMP_TOP, (1, 0))
    fleet["gr_cab"] = place(make_grader.build(), "gr_", (-860, 0), 0.6, (0, 1))
    # dragline at the east crest, boom out over the benches
    fleet["dl_house"] = place(make_dragline.build(), "dl_", DRAGLINE_AT, 0.0,
                              DRAGLINE_FACING)

    roles = {
        "s1_superstructure": ("Shovel on the west coal face",
            "Loading coal at the floor. Coal loading needs a clean floor and "
            "care at the seam floor to keep stone out of the product."),
        "t1_dump_body": ("Coal dumper (west face)",
            "Loaded at the face, then across the floor and up the haul road "
            "to the CHP."),
        "s2_superstructure": ("Shovel on the east coal face",
            "The second coal face, across the spur from the first."),
        "t2_dump_body": ("Coal dumper (east face)",
            "Waits to spot beside the shovel on the operator's side."),
        "sm_chassis": ("Surface miner on the coal bench",
            "Cutting the coal in thin layers with no blasting, loading "
            "straight into trucks."),
        "rs_machinery_house": ("Rope shovel on the first bench",
            "Loading blasted overburden on the 15 m bench; three or four "
            "passes fill a truck."),
        "t3_dump_body": ("Overburden dumper",
            "Carries the overburden up and out to the dump."),
        "t4_dump_body": ("Loaded dumper on the haul road",
            "Climbing at 1 in 16. A loaded 220 t truck manages about "
            "10-12 km/h on this grade."),
        "t5_dump_body": ("Dumper climbing the dump road",
            "Taking overburden up the spiral to the lift being tipped."),
        "dz_engine_hood": ("Dozer on the dump top",
            "Grading the final top and spreading topsoil ahead of the "
            "planters."),
        "dl_house": ("Dragline at the east crest",
            "Standing on the surface outside the crest, reaching nearly "
            "90 m out over the benches to dig overburden and cast it back "
            "towards the dump -- no trucks. It works from the surface so "
            "the walls below it are never loaded by its 3000 t weight."),
        "gr_cab": ("Grader on the surface road",
            "Keeping the road smooth and crowned to shed water."),
    }
    by_name = {pp.name: pp for pp in b._parts}
    for key, (label, note) in roles.items():
        pp = by_name[key]
        lo = np.min([q.bounds()[0] for q in fleet[key]], axis=0)
        hi = np.max([q.bounds()[1] for q in fleet[key]], axis=0)
        pp.label, pp.note = label, note
        pp._hotspot = ((lo[0] + hi[0]) / 2, hi[1] + 2.0, (lo[2] + hi[2]) / 2)
        pp.hotspot_normal = (0, 1, 0)

    # -- scale (1:1 -- kept as a step so a table-top build stays one line) ------------------------------------------------------
    s = np.diag([SCALE, SCALE, SCALE, 1.0])
    for pp in b._parts:
        n = np.asarray(pp.hotspot_normal, dtype=float)
        pp.transform(s)
        pp.hotspot_normal = tuple(n / (np.linalg.norm(n) or 1.0))

    b.labelled = list(TERRAIN) + [
        "garland_drain", "pump_pipeline", "settling_pond", "plantation",
        "surface_roads", "coal_handling_plant", "conveyor_to_silo",
        "loading_silo", "railway_siding", "coal_rake", "workshop",
        "mine_office", "substation", "explosives_magazine"] + list(roles)
    return b


SPECS = {
    "id": "mine-layout",
    "name": "Opencast coal mine layout",
    "subtitle": "Generic opencast coal mine, 80 m deep -- true size (1:1) for VR",
    "category": "Mine layout",
    "summary": (
        "A whole opencast coal mine as a table-top model: an oval pit 80 m "
        "deep with 15 m benches and 30 m berms all round, one 1 in 16 haul "
        "road zig-zagging down the north wall, a dark coal floor with two "
        "water-filled sumps and an overburden spur between them, a terraced "
        "dump with a planted top, the dewatering system, and the coal "
        "handling plant loading a train. Typical values -- not a copy of "
        "any real mine. The matching contour plan is in "
        "docs/mine-layout-draft.png."),
    "specs": [
        ["Model scale", "1:1 true size; the VR app has a 1:1000 table-top view"],
        ["Area shown", "approx. 2.6 km x 1.75 km"],
        ["Pit at crest", "approx. 1.3 km x 0.8 km"],
        ["Pit depth", "80 m (RL 300 to RL 220)"],
        ["Benches", "15 m high, 30 m berms, faces about 62 degrees"],
        ["Overburden", "four 15 m benches = 60 m"],
        ["Coal seam", "20 m, RL 240 to RL 220"],
        ["Pit floor", "approx. 0.95 km x 0.45 km, two sumps"],
        ["Haul road", "one road, 28 m wide, 1 in 16, 3 legs + 2 hairpins"],
        ["Overburden dump", "four 15 m lifts to RL 360, 30 m berms"],
        ["Dump road", "spiral, 24 m wide, 1 in 16"],
        ["Safety line", "110 m beyond the crest (see contour plan)"],
        ["Stripping ratio (floor area)", "approx. 2.1 m3 of overburden per tonne of coal"],
    ],
    "safety": [
        "Haul roads: gradient not steeper than 1 in 16, width at least three "
        "times the widest vehicle, bunds of at least axle height on every "
        "open edge.",
        "Benches no higher than the digging height of the machine working "
        "them, and wide enough for the shovel, a spotting truck and a "
        "passing truck.",
        "Garland drain, sump pumps and pipeline ready before the monsoon.",
        "Dump toes are never undercut and dump edges always carry a bund.",
        "No structures inside the safety line; the magazine is isolated at "
        "licence distances.",
    ],
    "ar_tips": [
        "This model is the real size of the mine -- 2.6 km by 1.75 km. In "
        "the VR app, walk it, or press Y to jump between stations: pit "
        "rim, haul road, coal face, dragline, dump top and CHP.",
        "Press A in VR for the 1:1000 table-top view of the whole site.",
    ],
}


def main():
    b = build()
    record = write_record(b, SPECS, WEB, "mine-layout")
    keep = set(b.labelled)
    record["parts"] = [p for p in record["parts"] if p["node"] in keep]
    record["vr_stations"] = vr_stations()
    (WEB / "data" / "mine-layout.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


if __name__ == "__main__":
    main()
