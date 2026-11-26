"""
make_grader.py -- generates a true-scale motor grader as GLB.

Reference machine: 16 ft (4.9 m) moldboard mine grader, 27-32 t -- the
CAT 16 / Komatsu GD825 / BEML BG605 family. Its job is the haul road. Road
condition, not engine power, is what limits a 220 t truck's speed and tyre
life, so the grader is the cheapest productivity tool in the pit.

Six wheels: a steerable, leaning front axle and a tandem drive at the rear
on each side, with an articulated frame between the cab and the front.

Axes: metres, Y up, the grader faces -Z. Origin on the ground under the
articulation joint.

Run:  python make_grader.py
"""

from __future__ import annotations

from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder, compose, rotate, translate
from machkit import bar, standard_materials, tube, tyre, write_record

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

TYRE_R = 0.80               # 23.5R25 is about 1.6 m diameter
TYRE_W = 0.60
FRONT_Z = -5.20
FRONT_X = 1.15
TANDEM_Z = (1.30, 3.10)
REAR_X = 1.25
BLADE_LEN = 4.90            # 16 ft
BLADE_H = 0.80
BLADE_YAW = 35.0            # moldboard angle in plan
CIRCLE = (0.0, 0.72, -2.20)
ARTIC = (0.0, 1.25, -0.30)


def build() -> Builder:
    b = Builder("motor_grader_16ft")
    standard_materials(b)

    # -- wheels -----------------------------------------------------------
    tyres = b.part(
        "tyres", "rubber",
        label="Tyres (23.5R25)",
        note=("Six driven or steered tyres about 1.6 m tall. A grader rarely "
              "wears out tyres -- it saves them on the trucks. A 40.00R57 "
              "truck tyre costs many lakhs, and most are lost to cuts from "
              "rock spill the grader should have cleared."),
        hotspot=(-REAR_X - 0.35, 0.8, TANDEM_Z[0]), hotspot_normal=(-1, 0, 0))
    hubs = b.part(
        "wheel_rims", "steel",
        label="Rims & hubs",
        note="Front wheels lean up to about 18 degrees so the grader can hold "
             "a line against the sideways push of an angled blade.",
        hotspot=(FRONT_X + 0.35, 0.8, FRONT_Z), hotspot_normal=(1, 0, 0))
    for sx in (-1, 1):
        tyre(tyres, hubs, (sx * FRONT_X, TYRE_R, FRONT_Z), TYRE_R, TYRE_W)
        for z in TANDEM_Z:
            tyre(tyres, hubs, (sx * REAR_X, TYRE_R, z), TYRE_R, TYRE_W)

    tandem = b.part(
        "tandem_drive", "dark",
        label="Tandem drive",
        note=("Each side's two rear wheels are chain-driven from a tandem "
              "case that oscillates, so all four keep traction over rough "
              "ground. That is what lets a grader hold a blade height to a "
              "few centimetres."),
        hotspot=(0.85, 0.85, 2.2), hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        tandem.box(center=(sx * 0.82, 0.82, sum(TANDEM_Z) / 2),
                   size=(0.26, 0.62, 2.70))
    tandem.box(center=(0, 0.85, sum(TANDEM_Z) / 2), size=(1.40, 0.40, 0.50))

    axle = b.part(
        "front_axle", "steel",
        label="Front axle (steer & lean)",
        note="Steering, wheel lean and oscillation all happen here. Combined "
             "with the articulation the grader can crab -- tandem offset from "
             "the front -- to keep its wheels off a freshly cut windrow.",
        hotspot=(0, 0.8, FRONT_Z - 0.3), hotspot_normal=(0, 0.3, -1))
    axle.box(center=(0, 0.80, FRONT_Z), size=(2.0, 0.26, 0.32))
    axle.box(center=(0, 1.15, FRONT_Z), size=(0.40, 0.50, 0.40))

    # -- front frame ------------------------------------------------------
    frame = b.part(
        "front_frame", "body_yellow",
        label="Front frame (gooseneck)",
        note="The long beam from the cab to the front axle. Everything the "
             "blade does is hung from it, so its length is what makes a "
             "grader so good at smoothing: the blade averages out the bumps "
             "between the axles.",
        hotspot=(0.4, 1.9, -3.8), hotspot_normal=(0.6, 1, 0))
    frame.box(center=(0, 1.85, FRONT_Z - 0.10), size=(0.55, 0.55, 0.90))
    bar(frame, (0, 1.85, FRONT_Z + 0.30), (0, 1.45, ARTIC[2] - 0.30), 0.48, 0.55)
    frame.box(center=(0, 1.62, -3.00), size=(1.30, 0.28, 0.40))   # lift saddle
    frame.box(center=(0, 1.15, FRONT_Z - 0.75), size=(1.80, 0.50, 0.24))

    artic = b.part(
        "articulation", "steel",
        label="Articulation joint",
        note=("The frame bends here, up to about 25 degrees each way. It "
              "halves the turning circle and lets the operator offset the "
              "rear wheels. Keep clear: the gap between frames closes with "
              "great force when the machine steers."),
        hotspot=(0.45, 1.25, ARTIC[2]), hotspot_normal=(1, 0.3, 0))
    artic.cyl(center=ARTIC, radius=0.32, length=0.70, axis="y", segments=12)

    # -- blade group ------------------------------------------------------
    drawbar = b.part(
        "drawbar", "body_yellow",
        label="Drawbar",
        note="A-frame pulled from a ball joint at the front of the frame. "
             "It carries the circle and the blade, and is what the lift "
             "cylinders raise, lower and swing sideways.",
        hotspot=(0.5, 1.0, -3.6), hotspot_normal=(0.6, 1, 0))
    apex = (0, 1.25, FRONT_Z + 0.45)
    for sx in (-1, 1):
        bar(drawbar, apex, (sx * 0.80, 0.80, CIRCLE[2] + 0.30), 0.20, 0.24)
    drawbar.cyl(center=apex, radius=0.20, length=0.30, axis="y", segments=10)

    circle = b.part(
        "circle", "steel",
        label="Circle (turntable)",
        note="A geared ring that rotates the blade to any angle, and even "
             "right round for back-grading. Blade angle decides whether "
             "material rolls off the end or is carried.",
        hotspot=(0.95, 0.75, CIRCLE[2]), hotspot_normal=(1, 0.6, 0))
    circle.cyl(center=CIRCLE, radius=0.98, length=0.14, axis="y",
               segments=24, inner_radius=0.80)

    place = compose(translate(0, 0, CIRCLE[2] + 0.15), rotate("y", BLADE_YAW))
    blade = b.part(
        "moldboard", "body_yellow",
        label="Moldboard (4.9 m)",
        note=("Angled about 30-45 degrees, the blade cuts high spots and "
              "rolls material along its face to fill the low ones, leaving "
              "a windrow. A mine road should keep a 2-3 % crossfall to "
              "shed water -- standing water is what makes potholes."),
        hotspot=(-1.6, 0.6, -1.0), hotspot_normal=(-0.3, 0.4, -1))
    curve = [(0.12, 0.05), (-0.06, 0.40), (-0.02, BLADE_H)]
    t = 0.10
    for (z0, y0), (z1, y1) in zip(curve, curve[1:]):
        blade.prism([(z0, y0), (z1, y1), (z1 + t, y1), (z0 + t, y0)],
                    extent=BLADE_LEN, axis="x", xform=place)
    blade.box(center=(0, 0.70, 0.30), size=(1.80, 0.22, 0.30), xform=place)

    edge = b.part(
        "blade_edge", "wear",
        label="Cutting edge & end bits",
        note="Hardened, bolt-on and replaceable. A worn edge leaves a "
             "rounded, washboard surface no matter how good the operator is.",
        hotspot=(1.6, 0.05, -3.5), hotspot_normal=(0.3, 0.2, -1))
    edge.box(center=(0, 0.06, 0.12), size=(BLADE_LEN, 0.12, 0.10), xform=place)

    cyl = b.part(
        "lift_cylinders", "chrome",
        label="Blade lift cylinders",
        note="Raise, lower and tilt the blade independently at each end -- "
             "that is how a crossfall is cut. Never reach between the "
             "drawbar and the frame while the engine is running.",
        hotspot=(0.85, 1.45, -2.7), hotspot_normal=(1, 0.4, 0))
    for sx in (-1, 1):
        tube(cyl, (sx * 0.55, 1.68, -3.00), (sx * 0.92, 0.88, -2.40), 0.08)
    tube(cyl, (0.62, 1.55, -3.10), (1.10, 0.85, -3.30), 0.06)       # side shift

    # -- rear: cab, engine, ripper ----------------------------------------
    rear = b.part(
        "rear_frame", "body_yellow",
        label="Rear frame",
        note="Carries the engine, transmission and tandems, and the cab "
             "just ahead of them.",
        hotspot=(0.5, 1.1, 4.6), hotspot_normal=(1, 0.2, 0.4))
    rear.box(center=(0, 1.05, 2.40), size=(0.90, 0.50, 5.20))
    for sx in (-1, 1):                                    # fenders
        rear.box(center=(sx * REAR_X, 1.72, sum(TANDEM_Z) / 2),
                 size=(TYRE_W + 0.10, 0.06, 2.80))

    hood = b.part(
        "engine_hood", "body_yellow",
        label="Engine compartment",
        note="Diesel of about 220-250 kW and a powershift transmission. "
             "Graders work in a low gear at walking pace when cutting, and "
             "travel at up to about 45 km/h between jobs.",
        hotspot=(0.8, 2.0, 3.4), hotspot_normal=(1, 0.4, 0))
    hood.box(center=(0, 1.85, 3.45), size=(1.50, 1.30, 3.00))
    hood.box(center=(0, 1.75, 5.02), size=(1.40, 1.10, 0.12))

    stack = b.part(
        "exhaust", "steel",
        label="Exhaust stack",
        note="Exhaust and intake are kept high and to the rear, away from "
             "the operator's view forward.",
        hotspot=(0.4, 3.1, 2.6), hotspot_normal=(0.3, 1, 0))
    stack.cyl(center=(0.40, 2.85, 2.60), radius=0.08, length=0.75,
              axis="y", segments=8)

    cab = b.part(
        "cab", "body_yellow",
        label="Cab with ROPS",
        note=("High, glassy cab ahead of the rear wheels so the operator can "
              "see both blade ends and the front tyres. Graders share the "
              "haul road with 220 t trucks whose drivers cannot see them: "
              "flashing beacon, buggy whip and radio contact, always."),
        hotspot=(-1.0, 2.8, 0.4), hotspot_normal=(-1, 0.3, 0))
    cab.box(center=(0, 3.56, 0.40), size=(2.00, 0.12, 1.80))
    cab.box(center=(0, 1.55, 0.40), size=(1.90, 0.20, 1.70))
    for sx in (-1, 1):
        for z in (-0.40, 1.20):
            cab.box(center=(sx * 0.92, 2.55, z), size=(0.10, 2.00, 0.10))
    cab.cyl(center=(0.0, 3.70, 0.90), radius=0.12, length=0.16, axis="y",
            segments=10)                                       # beacon

    glass = b.part(
        "cab_glass", "glass",
        label="Cab glazing",
        note="Glass down to the floor at the front, so the operator can see "
             "the blade toe and heel without leaning out.",
        hotspot=(0, 2.4, -0.45), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(0, 2.50, -0.42), size=(1.74, 1.80, 0.05))
    glass.box(center=(0, 2.50, 1.22), size=(1.74, 1.80, 0.05))
    for sx in (-1, 1):
        glass.box(center=(sx * 0.93, 2.50, 0.40), size=(0.05, 1.80, 1.50))

    ripper = b.part(
        "rear_ripper", "steel", pivot=(0, 1.15, 5.00),
        label="Rear ripper",
        note="Breaks up a hard, compacted road surface or windrowed rock "
             "before the blade can cut it.",
        hotspot=(0.9, 0.7, 5.6), hotspot_normal=(1, 0.2, 0.5))
    for sx in (-1, 1):
        bar(ripper, (sx * 0.55, 1.15, 5.00), (sx * 0.55, 0.95, 5.55), 0.14, 0.18)
    ripper.box(center=(0, 0.95, 5.62), size=(1.90, 0.24, 0.24))
    for x in (-0.70, 0.0, 0.70):
        ripper.prism([(5.52, 0.90), (5.72, 0.90), (5.66, 0.12), (5.48, 0.20)],
                     extent=0.08, axis="x", offset=(x, 0, 0))

    add_scale_figure(b, x=-2.80, z=-6.40)
    return b


SPECS = {
    "id": "grader",
    "name": "Motor grader",
    "subtitle": "16 ft (4.9 m) moldboard mine grader -- CAT 16 / GD825 / BG605 family",
    "category": "Support equipment",
    "summary": (
        "The haul-road machine. A good road lets a loaded truck run faster, "
        "use less fuel and keep its tyres; a bad one costs more than the "
        "grader does. Graders keep the surface smooth and crowned, cut the "
        "drains, clear spillage and dress the berms."),
    "specs": [
        ["Moldboard", "4.9 m (16 ft) x approx. 0.8 m"],
        ["Operating weight", "approx. 27-32 t"],
        ["Engine", "approx. 220-250 kW diesel"],
        ["Tyres", "6 x 23.5R25, approx. 1.6 m diameter"],
        ["Overall length", "approx. 11 m with rear ripper"],
        ["Width over tyres", "approx. 3.1 m"],
        ["Height to cab roof", "approx. 3.6 m"],
        ["Frame articulation", "approx. +/- 25 degrees"],
        ["Top speed", "approx. 45 km/h"],
        ["Typical road crossfall", "2-3 % to shed water"],
    ],
    "safety": [
        "Trucks cannot see a grader close in front or behind them. Work "
        "with the beacon on and in radio contact with every truck on the "
        "road.",
        "Grade with the traffic, not against it, and never park in a "
        "blind corner or over a crest.",
        "Never stand in the articulation zone -- the frames swing together "
        "when the machine steers.",
        "Leave windrows out of the travelled lane; a windrow can steer a "
        "truck tyre or hide a rock.",
    ],
    "ar_tips": [
        "Walk to the front: the moldboard is angled so it sweeps "
        "material to one side -- you can see where the windrow would form.",
        "Place it beside the 220 t dumper to see who must give way to "
        "whom on a haul road.",
    ],
}


def main():
    return write_record(build(), SPECS, WEB, "grader")


if __name__ == "__main__":
    main()
