"""
mine_services.py -- the working services of the mine layout, at true size.

Three things the bare terrain does not have, all built on draft_layout's
plan so they sit where the contour plan shows them:

* the dewatering system: a pontoon pump in each sump, a pump station on the
  floor beside it, a booster on the west wall, 500 mm pipelines on saddles up
  the walls to two settling ponds, gate valves, and culverts wherever a pipe
  crosses a truck route -- so nothing has to be stepped over by a truck;
* drivable road surfaces for the haul road and the dump road, following the
  road's own grade rather than the 8 m terrain grid, with a safety bund
  along every open edge;
* the truck routes (coal to the CHP, overburden to the dump), loading and
  tipping points and a spawn pose, exported for the VR app so a dumper can
  be driven through the mine next.

Plan points are (x east, y north); model points are (x, y up, z south).
"""

from __future__ import annotations

import math

import numpy as np

import draft_layout as D
from glbgen import compose, rotate, translate
from machkit import link

PIPE_R = 0.25                    # 500 mm main
HOSE_R = 0.15                    # 300 mm flexible hose from the pontoons
PIPE_Y = 0.35                    # pipe centre above the ground, on saddles
WATER_Y = D.FLOOR - 1.5          # sump water surface
ROAD_LIFT = 0.25                 # running surface above the levelled terrain
CLEAR = 10.0                     # a pipe this close to a truck route is buried


def M(p, y=0.0):
    return (float(p[0]), float(y), float(-p[1]))


def ground(p):
    return float(D.fields(np.array([p[0]]), np.array([p[1]]))["h"][0])


def pit_pt(deg, inset):
    return D.pit_point(math.radians(deg), inset)


def local_pt(u, v):
    return D.to_world(u, v, D.PIT_C, D.PIT_ROT)


def densify(path, step):
    out = [tuple(path[0])]
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        n = max(1, int(math.ceil(math.hypot(bx - ax, by - ay) / step)))
        for k in range(1, n + 1):
            out.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
    return out


def yaw_for(heading):
    """Yaw (degrees) that points a -Z-nosed model along a plan heading."""
    dx, dz = heading[0], -heading[1]
    return math.degrees(math.atan2(-dx, -dz))


# ------------------------------------------------------------------ routes

SURFACE_TO_CHP = [D.HAUL[0], (D.HAUL[0][0] - 200, D.HAUL[0][1] + 160),
                  (-860, 560), (-870, 470), (-885, 430)]    # to the hopper apron
SURFACE_TO_DUMP = [D.HAUL[0], (D.HAUL[0][0] + 260, D.HAUL[0][1] + 120),
                   (620, 560), (D.DUMP_ROAD[0][0] - 40, D.DUMP_ROAD[0][1] + 30),
                   D.DUMP_ROAD[0]]
SURFACE_SERVICE = [(-860, 560), (-860, -500), (-900, -620)]
SURFACE_ROADS = [SURFACE_TO_CHP, SURFACE_TO_DUMP, SURFACE_SERVICE]

# where the work is
COAL_SHOVEL_W = pit_pt(180, 178)                  # hydraulic shovel, facing the face


def _beside(p, deg, inset, metres):
    """A point `metres` along the wall from a shovel -- where a truck
    stands to be loaded: within the bucket's reach, beside the machine."""
    a, b = pit_pt(deg - 1, inset), pit_pt(deg + 1, inset)
    t = np.subtract(b, a)
    t /= np.linalg.norm(t)
    return (p[0] + t[0] * metres, p[1] + t[1] * metres)


COAL_FACE_W = _beside(COAL_SHOVEL_W, 180, 178, 10.5)   # truck stands here to load
SPUR_TOE = local_pt(40, -30)                      # rope shovel digs the spur
OB_LOAD = local_pt(70, -15)                       # the parked display truck
OB_BAY = local_pt(18, -30)                        # beside the rope shovel, in reach
CHP_TIP = (-900.0, 430.0)                         # reverse in to the hopper

# Floor legs to the bottom of the haul road. The coal leg goes round the
# inner (east) side of the west sump, well clear of its edge: a truck
# cutting the corner between the sump and the wall ended up in it.
FLOOR_FROM_COAL = [COAL_FACE_W, local_pt(-400, -55), local_pt(-250, -70),
                   local_pt(-170, 30), local_pt(-150, 130), D.HAUL[-1]]
FLOOR_FROM_OB = [OB_BAY, local_pt(-30, 60), D.HAUL[-1]]


def dump_tip():
    """On the dump top beside the end of the dump road, facing out."""
    end = D.DUMP_ROAD[-1]
    u, v = D.to_local(end[0], end[1], D.DUMP_C, D.DUMP_ROT)
    th = math.atan2(v, u)
    at = D.dump_point(th, 185.0)
    out = D.dump_point(th, 150.0)
    return at, (out[0] - at[0], out[1] - at[1])


def routes():
    up_haul = list(reversed(D.HAUL))
    coal = FLOOR_FROM_COAL[:-1] + up_haul + SURFACE_TO_CHP[1:] + [CHP_TIP]
    tip, _ = dump_tip()
    ob = FLOOR_FROM_OB[:-1] + up_haul + SURFACE_TO_DUMP[1:] + \
        list(D.DUMP_ROAD[1:]) + [tip]
    return {"coal_to_chp": densify(coal, 10.0), "ob_to_dump": densify(ob, 10.0)}


def all_vehicle_lines():
    """Every line a truck may drive along -- pipes must not block them."""
    r = routes()
    return [r["coal_to_chp"], r["ob_to_dump"], D.HAUL, D.DUMP_ROAD] + SURFACE_ROADS


def near_route(p, lines, clear=CLEAR):
    for line in lines:
        d, _ = D.polyline_field(line, np.array([p[0]]), np.array([p[1]]))
        if d[0] <= clear:
            return True
    return False


# ------------------------------------------------------------------ roads

def road_surface(top, bund, path, levels, half_w):
    """A smooth running surface along a plan path at the given levels, with
    a bund on whichever edge drops away."""
    P = np.asarray(path, float)
    n = len(P)
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)                 # left normal
    y = np.asarray(levels, float) + ROAD_LIFT

    def side_open(k, sgn):
        probe = P[k] + sgn * N[k] * (half_w + D.SHOULDER + 6.0)
        return ground(probe) < levels[k] - 2.0

    open_l = [side_open(k, 1) for k in range(n)]
    open_r = [side_open(k, -1) for k in range(n)]
    for k in range(n - 1):
        a_l, a_r = P[k] + N[k] * half_w, P[k] - N[k] * half_w
        b_l, b_r = P[k + 1] + N[k + 1] * half_w, P[k + 1] - N[k + 1] * half_w
        quad = [M(a_l, y[k]), M(b_l, y[k + 1]), M(b_r, y[k + 1]), M(a_r, y[k])]
        _up(top, quad)
        for sgn, flags in ((1, open_l), (-1, open_r)):
            if not (flags[k] and flags[k + 1]):
                continue
            # bund: 2 m high, 5 m at the base, on the road's own edge
            def at(j, off):
                return P[j] + sgn * N[j] * off
            for j0, j1 in ((k, k + 1),):
                inner0, crest0, outer0 = at(j0, half_w - 5), at(j0, half_w - 2.5), at(j0, half_w)
                inner1, crest1, outer1 = at(j1, half_w - 5), at(j1, half_w - 2.5), at(j1, half_w)
                h0, h1 = y[j0], y[j1]
                _up(bund, [M(inner0, h0), M(inner1, h1), M(crest1, h1 + 2.0), M(crest0, h0 + 2.0)])
                _up(bund, [M(crest0, h0 + 2.0), M(crest1, h1 + 2.0), M(outer1, h1), M(outer0, h0)])


def _up(part, quad):
    a, b, c, d = (np.asarray(v, float) for v in quad)
    n = np.cross(b - a, c - a)
    if n[1] < 0:
        a, b, c, d = a, d, c, b
    part.tri(a, b, c)
    part.tri(a, c, d)


# ------------------------------------------------------------------ pipes

def pipe_line(pipe, saddles, culverts, valves, plan_path, radius, lines,
              start_y=None, valve_every=160.0):
    """Lay a pipe along a plan path on saddles, buried at route crossings."""
    pts = densify(plan_path, 3.0)
    ys, buried = [], []
    for i, p in enumerate(pts):
        g = max(ground(p), D.FLOOR - 6.0)
        if i == 0 and start_y is not None:
            ys.append(start_y)
            buried.append(False)
            continue
        b = near_route(p, lines)
        buried.append(b)
        ys.append(g - 1.2 if b else g + PIPE_Y)
    run = 0.0
    for i in range(len(pts) - 1):
        a, c = M(pts[i], ys[i]), M(pts[i + 1], ys[i + 1])
        if np.allclose(a, c):
            continue
        if not (buried[i] and buried[i + 1]):
            L, xf = link(a, c)
            pipe.cyl(center=(0, 0, 0), radius=radius, length=L + 0.05, axis="z",
                     segments=10, xform=xf)
        seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        run += seg
        if not buried[i] and int((run - seg) // 12) != int(run // 12):
            g = ys[i] - PIPE_Y
            saddles.box(center=M(pts[i], g + 0.15), size=(0.9, 0.3, 0.9))
        if valve_every and not buried[i] and int((run - seg) // valve_every) != int(run // valve_every):
            valves.box(center=M(pts[i], ys[i]), size=(0.9, 0.9, 0.9))
            valves.cyl(center=M(pts[i], ys[i] + 1.1), radius=0.45, length=0.08,
                       axis="y", segments=12)
            valves.cyl(center=M(pts[i], ys[i] + 0.7), radius=0.06, length=0.8,
                       axis="y", segments=6)
        if buried[i] != buried[i + 1]:           # culvert headwall
            p = pts[i] if not buried[i] else pts[i + 1]
            g = ground(p)
            culverts.box(center=M(p, g + 0.6), size=(3.0, 1.2, 3.0))
    return pts, ys


def pump_unit(parts, p, y, heading, big=True):
    """A horizontal centrifugal pump set on a skid under a shelter.

    parts: dict of Builder parts by role. Local frame: -z along heading,
    x across, y up."""
    s = 1.0 if big else 0.75
    base = compose(translate(*M(p, y)), rotate("y", yaw_for(heading)))

    def X(x, yy, z):
        return compose(base, translate(x * s, yy * s, z * s))

    parts["skid"].box(center=(0, 0, 0), size=(3.4 * s, 0.4 * s, 8.0 * s), xform=X(0, 0.2, 0))
    parts["casing"].cyl(center=(0, 0, 0), radius=1.0 * s, length=0.8 * s, axis="x",
                        segments=18, xform=X(0, 1.5, -2.0))
    parts["motor"].cyl(center=(0, 0, 0), radius=0.7 * s, length=2.8 * s, axis="z",
                       segments=16, xform=X(0, 1.2, 1.4))
    parts["motor"].box(center=(0, 0, 0), size=(1.0 * s, 0.6 * s, 1.0 * s), xform=X(0, 0.5, 1.4))
    parts["casing"].box(center=(0, 0, 0), size=(0.9 * s, 0.9 * s, 0.9 * s), xform=X(0, 1.2, -0.5))
    parts["casing"].cyl(center=(0, 0, 0), radius=0.28 * s, length=2.6 * s, axis="y",
                        segments=10, xform=X(0, 3.0, -2.0))
    parts["casing"].cyl(center=(0, 0, 0), radius=0.32 * s, length=2.2 * s, axis="z",
                        segments=10, xform=X(0, 1.5, -3.6))
    parts["panel"].box(center=(0, 0, 0), size=(1.4 * s, 2.0 * s, 0.6 * s), xform=X(2.6, 1.0, 2.5))
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts["shelter"].box(center=(0, 0, 0), size=(0.2 * s, 4.2 * s, 0.2 * s),
                                 xform=X(sx * 2.4, 2.1, sz * 4.2))
    parts["shelter"].box(center=(0, 0, 0), size=(5.4 * s, 0.25 * s, 9.2 * s), xform=X(0, 4.3, 0))


def pontoon(parts, p, heading):
    """A floating pump on the sump: deck, pump, rails, float drums."""
    base = compose(translate(*M(p, WATER_Y)), rotate("y", yaw_for(heading)))

    def X(x, y, z):
        return compose(base, translate(x, y, z))

    parts["pontoon"].box(center=(0, 0, 0), size=(5.0, 0.5, 7.0), xform=X(0, 0.45, 0))
    for sx in (-1, 1):
        parts["pontoon"].cyl(center=(0, 0, 0), radius=0.55, length=7.0, axis="z",
                             segments=12, xform=X(sx * 2.0, 0.1, 0))
        parts["panel"].box(center=(0, 0, 0), size=(0.08, 1.1, 7.0), xform=X(sx * 2.45, 1.25, 0))
    parts["casing"].cyl(center=(0, 0, 0), radius=0.6, length=1.4, axis="y",
                        segments=14, xform=X(0, 1.4, 0.8))
    parts["motor"].cyl(center=(0, 0, 0), radius=0.5, length=1.6, axis="y",
                       segments=14, xform=X(0, 2.9, 0.8))
    parts["panel"].box(center=(0, 0, 0), size=(1.2, 1.6, 0.5), xform=X(0, 1.5, -2.4))


# ------------------------------------------------------------------ build

DRAIN = {
    # pump stations on the floor between each sump and its wall
    "west_station": pit_pt(152, 190),
    "east_station": pit_pt(-15, 190),
    "west_pontoon": local_pt(-300, 60),
    "east_pontoon": local_pt(275, -40),
    "booster": pit_pt(149, 66),
    "pond_w": (-800.0, 710.0),
    "pond_e": pit_pt(-15, -170),
}


def build(b):
    """Add the dewatering system, drivable roads and bunds to a Builder.

    Returns the part names to label."""
    lines = all_vehicle_lines()
    b.material("pump_blue", (0.12, 0.30, 0.62), roughness=0.45, metallic=0.6)
    b.material("motor_grey", (0.35, 0.37, 0.40), roughness=0.5, metallic=0.6)
    b.material("road_top", (0.30, 0.29, 0.28), roughness=0.9, metallic=0.0)

    def station_parts(tag, label, note, hot, floating=False):
        roles = {"motor": "motor_grey", "panel": "steel"}
        roles.update({"pontoon": "body_yellow"} if floating else
                     {"skid": "concrete", "shelter": "roof_blue"})
        out = {"casing": b.part(f"{tag}_pump", "pump_blue", label=label,
                                note=note, hotspot=hot, hotspot_normal=(0, 1, 0))}
        out.update({k: b.part(f"{tag}_{k}", m) for k, m in roles.items()})
        return out

    labelled = []

    # -- west: pontoon -> floor station -> booster -> crest -> pond --------
    ws, es = DRAIN["west_station"], DRAIN["east_station"]
    out_w = (pit_pt(152, 0)[0] - ws[0], pit_pt(152, 0)[1] - ws[1])
    W = station_parts("west_station", "Main dewatering pump (west sump)",
                      "Horizontal centrifugal pump on a skid under a shelter. It "
                      "takes from the pontoon pump in the sump and lifts the "
                      "water up the wall -- about 80 m of static head plus "
                      "friction -- to the settling pond. Sized before the "
                      "monsoon for the worst storm on record.",
                      M(ws, D.FLOOR + 6))
    pump_unit(W, ws, D.FLOOR, out_w)
    Wp = station_parts("west_pontoon", "Pontoon pump (west sump)",
                       "A pump on floats, so it rides up and down with the "
                       "water instead of drowning or running dry. A flexible "
                       "hose carries the water to the pump station on the "
                       "floor.", M(DRAIN["west_pontoon"], WATER_Y + 4), floating=True)
    pontoon(Wp, DRAIN["west_pontoon"], out_w)
    bst = DRAIN["booster"]
    B_ = station_parts("booster", "Booster pump (berm RL 270)",
                       "Half way up, a second pump adds head so neither pump "
                       "works at the edge of its curve. Booster stations sit "
                       "on a berm, clear of the face below, with room to "
                       "change a motor.", M(bst, ground(bst) + 6))
    pump_unit(B_, bst, ground(bst), out_w, big=False)
    labelled += ["west_station_pump", "west_pontoon_pump", "booster_pump"]

    pipe = b.part("dewatering_pipeline", "pipe",
                  label="Dewatering pipeline (500 mm)",
                  note=("Steel main laid on concrete saddles from the sump "
                        "pumps up the wall to the settling ponds, with gate "
                        "valves to isolate each length. Where it meets a "
                        "truck route it goes under it in a culvert -- a pipe "
                        "lying across a haul road is a hazard and a broken "
                        "pipe."),
                  hotspot=M(pit_pt(152, 100), ground(pit_pt(152, 100)) + 3),
                  hotspot_normal=(0, 1, 0))
    hose = b.part("pontoon_hoses", "dark")
    saddles = b.part("pipe_saddles", "concrete")
    culv = b.part("pipe_culverts", "concrete", label="Pipe culvert (road crossing)",
                  note=("Where a pipe meets a truck route it is taken under "
                        "the road in a culvert with headwalls each side, so "
                        "the road stays level and the pipe stays whole."))
    valves = b.part("pipe_valves", "steel", label="Gate valves",
                    note=("Isolating valves every 160 m or so, so a burst "
                          "length can be shut off and replaced without "
                          "draining the whole main."))
    labelled += ["dewatering_pipeline", "pipe_culverts", "pipe_valves"]

    # hoses from the pontoons to the stations
    for pon, st in ((DRAIN["west_pontoon"], ws), (DRAIN["east_pontoon"], es)):
        pipe_line(hose, saddles, culv, valves, [pon, st], HOSE_R, lines,
                  start_y=WATER_Y + 0.9, valve_every=0)

    west_path = [ws] + [pit_pt(152, d) for d in (175, 140, 100, 66)] + \
        [pit_pt(152, d) for d in (40, 0, -20, -60)] + [(-760, 620), (-800, 660)]
    pipe_line(pipe, saddles, culv, valves, west_path, PIPE_R, lines)

    # -- east: pontoon -> floor station -> crest -> pond 2 -----------------
    out_e = (pit_pt(-15, 0)[0] - es[0], pit_pt(-15, 0)[1] - es[1])
    E = station_parts("east_station", "Dewatering pump (east sump)",
                      "The east sump's own pump set, lifting to the second "
                      "settling pond outside the east crest.", M(es, D.FLOOR + 6))
    pump_unit(E, es, D.FLOOR, out_e)
    Ep = station_parts("east_pontoon", "Pontoon pump (east sump)",
                       "Floating pump on the east sump.",
                       M(DRAIN["east_pontoon"], WATER_Y + 4), floating=True)
    pontoon(Ep, DRAIN["east_pontoon"], out_e)
    labelled += ["east_station_pump", "east_pontoon_pump"]
    pe = DRAIN["pond_e"]
    east_path = [es] + [pit_pt(-15, d) for d in (175, 120, 60, 0, -60, -140)]
    pipe_line(pipe, saddles, culv, valves, east_path, PIPE_R, lines)

    # -- settling ponds -----------------------------------------------------
    for tag, p, size, label in (("settling_pond", DRAIN["pond_w"], (160, 100),
                                 "Settling pond (west)"),
                                ("settling_pond_2", pe, (110, 80),
                                 "Settling pond (east)")):
        pond = b.part(tag, "water", label=label,
                      note=("Pit water is held long enough for the coal and "
                            "clay fines to settle, so only clear water leaves "
                            "the lease -- or goes back for dust suppression "
                            "on the haul roads."),
                      hotspot=M(p, 2.0), hotspot_normal=(0, 1, 0))
        pond.box(center=M(p, 0.3), size=(size[0], 0.6, size[1]))
        bank = b.part(tag + "_bank", "spoil")
        for dx, dz, w, d in ((0, size[1] / 2 + 2, size[0] + 8, 4),
                             (0, -size[1] / 2 - 2, size[0] + 8, 4),
                             (size[0] / 2 + 2, 0, 4, size[1]),
                             (-size[0] / 2 - 2, 0, 4, size[1])):
            bank.box(center=(p[0] + dx, 1.0, -p[1] + dz), size=(w, 2.0, d))
        labelled.append(tag)

    # -- drivable road surfaces and bunds ----------------------------------
    top = b.part("road_running_surface", "road_top",
                 label="Haul road running surface",
                 note=("The surface the trucks drive on, graded to a steady "
                       "1 in 16 with a crossfall to shed water. It is what a "
                       "driven dumper's wheels will run on."),
                 hotspot=M(D.HAUL[30], D.haul_level(D.path_lengths(D.HAUL))[30] + 2),
                 hotspot_normal=(0, 1, 0))
    bund = b.part("safety_bunds", "spoil", label="Safety bunds (windrows)",
                  note=("A bund of rock along every open road edge, at least "
                        "as high as the axle of the largest truck. It will "
                        "not stop a runaway at speed; it warns a driver and "
                        "stops a slow drift over the edge."),
                  hotspot=M(D.HAUL[50], D.haul_level(D.path_lengths(D.HAUL))[50] + 4),
                  hotspot_normal=(0, 1, 0))
    road_surface(top, bund, D.HAUL, D.haul_level(D.path_lengths(D.HAUL)),
                 D.ROAD_HW)
    road_surface(top, bund, D.DUMP_ROAD,
                 D.dump_road_level(D.path_lengths(D.DUMP_ROAD)), D.DUMP_ROAD_HW)
    labelled += ["road_running_surface", "safety_bunds"]
    return labelled


def drive_data():
    """Routes, loading and tipping points and a spawn for driving a dumper."""
    def pts3(path):
        return [{"x": p[0], "y": max(ground(p), D.FLOOR), "z": -p[1]} for p in path]

    def pose(p, heading, name):
        return {"name": name, "pos": {"x": p[0], "y": max(ground(p), D.FLOOR),
                                      "z": -p[1]},
                "heading": {"x": heading[0], "y": 0.0, "z": -heading[1]}}

    r = routes()
    tip, tip_dir = dump_tip()
    face_dir = (pit_pt(180, 150)[0] - COAL_FACE_W[0], pit_pt(180, 150)[1] - COAL_FACE_W[1])
    return {
        "note": ("Plan routes for a driven dumper. y is the terrain level at "
                 "each point; raycast down for the exact running surface."),
        "routes": [{"name": k, "points": pts3(v)} for k, v in r.items()],
        # The student starts empty on the open floor south of the west sump,
        # facing the coal face -- not in the loading bay, which the
        # automatic fleet uses.
        "spawn": pose(local_pt(-330, -110), face_dir,
                      "Pit floor, south of the west sump"),
        "load_points": [pose(COAL_FACE_W, face_dir, "Coal shovel, west face"),
                        pose(OB_BAY, (SPUR_TOE[0] - OB_BAY[0], SPUR_TOE[1] - OB_BAY[1]),
                             "Rope shovel, overburden spur")],
        "tip_points": [pose(CHP_TIP, (-1.0, 0.0), "CHP receiving hopper"),
                       pose(tip, tip_dir, "Dump top, active tipping edge")],
        "speed_limits_kmh": {"haul_road_loaded_up": 12, "haul_road_empty_down": 25,
                             "floor": 20, "surface": 40},
    }
