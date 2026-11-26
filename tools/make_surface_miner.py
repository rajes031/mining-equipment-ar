"""
make_surface_miner.py -- generates a true-scale surface miner as GLB.

Reference machine: 2.5 m cutting-width, centre-drum surface miner of about
100 t -- the Wirtgen 2500 SM / L&T KSM class, now common in Indian coal and
limestone mines. It cuts the seam in layers with a rotating drum, so there is
no drilling, no blasting and no primary crusher, and the output goes straight
onto trucks from a slewing conveyor.

Axes: metres, Y up, the machine cuts towards -Z. Origin on the ground under
the cutting drum's mid-length.

Run:  python make_surface_miner.py
"""

from __future__ import annotations

import math
from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder, compose, rotate, translate
from machkit import (bar, crawler_profile, link, standard_materials, tube,
                     write_record)

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

CUT_WIDTH = 2.50
DRUM_R = 0.66               # cutting circle about 1.3 m
DRUM = (0.0, 0.72, 0.50)    # drum axis centre
CRAWLER_X = 1.55
CRAWLER_Z = 3.40
CRAWLER_LEN = 2.80
CRAWLER_H = 0.95
CHASSIS_Y = (1.70, 2.70)
CONV_PIVOT = (0.0, 2.35, -4.80)   # discharge-conveyor slew/luff pivot
CONV_LEN = 11.0
CONV_RISE = 17.0                  # degrees


def build() -> Builder:
    b = Builder("surface_miner_2500")
    standard_materials(b)
    b.material("tank_blue", (0.18, 0.33, 0.58), roughness=0.5, metallic=0.2)

    # -- crawlers and columns ---------------------------------------------
    crawl = b.part(
        "crawler_units", "dark",
        label="Four crawler units",
        note=("Four independently steered crawlers. The machine creeps "
              "forward at only a few metres a minute while cutting -- "
              "advance rate, not engine power, is what an operator tunes "
              "to the rock."),
        hotspot=(-CRAWLER_X - 0.4, 0.6, -CRAWLER_Z), hotspot_normal=(-1, 0.2, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            crawl.prism(crawler_profile(CRAWLER_LEN, CRAWLER_H, nose=0.35,
                                        chamfer=0.30),
                        extent=0.60, axis="x",
                        offset=(sx * CRAWLER_X, 0, sz * CRAWLER_Z))

    cols = b.part(
        "height_columns", "chrome",
        label="Height-adjustable columns",
        note=("Hydraulic legs between each crawler and the chassis. Raising "
              "or lowering them sets cutting depth and slope, controlled by "
              "sensors or GPS, which is how a surface miner cuts a seam "
              "floor flat to a few centimetres -- selective mining with "
              "very little dilution."),
        hotspot=(CRAWLER_X + 0.4, 1.3, CRAWLER_Z), hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            cols.cyl(center=(sx * CRAWLER_X, 1.32, sz * CRAWLER_Z),
                     radius=0.26, length=0.80, axis="y", segments=12)

    # -- chassis and drum -------------------------------------------------
    chassis = b.part(
        "chassis", "body_yellow",
        label="Machine frame",
        note="A stiff box frame: the drum's reaction to cutting rock is "
             "taken by the full machine weight of about 100 t pressing "
             "down on it.",
        hotspot=(1.75, 2.2, -2.0), hotspot_normal=(1, 0.2, 0))
    chassis.box(center=(0, sum(CHASSIS_Y) / 2, 0),
                size=(3.40, CHASSIS_Y[1] - CHASSIS_Y[0], 9.40))

    housing = b.part(
        "drum_housing", "body_yellow",
        label="Drum housing",
        note=("Encloses the drum on top and sides, with a hydraulic scraper "
              "behind it that leaves a clean, level floor. The housing "
              "contains the cut material so the drum can load it."),
        hotspot=(1.55, 1.2, 0.5), hotspot_normal=(1, 0, 0))
    for sx in (-1, 1):
        housing.box(center=(sx * 1.40, 1.05, DRUM[2]), size=(0.12, 1.30, 2.10))
    housing.box(center=(0, 1.62, DRUM[2] + 0.10), size=(2.90, 0.16, 2.30))
    housing.box(center=(0, 0.42, DRUM[2] + 1.10), size=(2.70, 0.70, 0.12))

    drum = b.part(
        "cutting_drum", "steel", pivot=DRUM,
        label="Cutting drum (2.5 m wide)",
        note=("Rotates against the direction of travel (up-cut), lifting "
              "the cut material. Spiral rows of picks steer it to the "
              "centre. Cutting depth up to about 0.65 m; product size is "
              "set by the depth of cut and advance speed, typically under "
              "about 100-150 mm, so it can skip the primary crusher."),
        hotspot=(0.4, 0.4, DRUM[2] - DRUM_R - 0.1), hotspot_normal=(0, 0, -1))
    drum.cyl(center=DRUM, radius=DRUM_R - 0.10, length=CUT_WIDTH, axis="x",
             segments=18)

    picks = b.part(
        "picks", "wear", parent="cutting_drum", pivot=DRUM,
        label="Picks (cutting tools)",
        note=("Tungsten-carbide-tipped conical picks in rotating holders, "
              "about 100-150 on a drum. They wear fast in abrasive rock and "
              "are changed every shift; worn picks raise dust and fuel use. "
              "Isolate the drum before anyone goes near it."),
        hotspot=(-0.9, 0.72 + DRUM_R, DRUM[2]), hotspot_normal=(0, 1, 0))
    n = 48
    for i in range(n):
        frac = i / (n - 1)
        x = -CUT_WIDTH / 2 + 0.08 + frac * (CUT_WIDTH - 0.16)
        # two spirals meeting in the middle, as on a real drum
        turns = 1.6 * (frac if x < 0 else 1 - frac)
        ang = 360.0 * turns + (180.0 if x >= 0 else 0.0)
        xf = compose(translate(*DRUM), rotate("x", ang),
                     translate(0, DRUM_R - 0.06, 0))
        picks.box(center=(x, 0, 0), size=(0.07, 0.18, 0.07), xform=xf)

    # -- conveyors --------------------------------------------------------
    primary = b.part(
        "primary_conveyor", "dark",
        label="Primary (loading) conveyor",
        note="Takes the cut material from the drum and carries it forward "
             "and up through the machine to the discharge conveyor.",
        hotspot=(0.6, 1.4, -2.6), hotspot_normal=(1, 0.4, 0))
    bar(primary, (0, 0.80, DRUM[2] - 0.90), (0, 2.25, -4.75), 1.00, 0.30)

    rad = math.radians(CONV_RISE)
    head = (0.0, CONV_PIVOT[1] + CONV_LEN * math.sin(rad),
            CONV_PIVOT[2] - CONV_LEN * math.cos(rad))
    conv = b.part(
        "discharge_conveyor", "body_yellow", pivot=CONV_PIVOT,
        label="Discharge conveyor",
        note=("Slews about +/- 60 degrees and luffs up and down, so the "
              "machine can load a truck driving alongside or behind it, or "
              "windrow the material on the floor for a loader. Discharge "
              "height about 5-5.5 m -- check it clears the truck body."),
        hotspot=(0.9, 4.2, -10.0), hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        bar(conv, (sx * 0.62, CONV_PIVOT[1], CONV_PIVOT[2]),
            (sx * 0.62, head[1], head[2]), 0.14, 0.50)
    for k in range(1, 6):
        t = k / 6.0
        p = (0, CONV_PIVOT[1] + t * (head[1] - CONV_PIVOT[1]) - 0.30,
             CONV_PIVOT[2] + t * (head[2] - CONV_PIVOT[2]))
        conv.box(center=p, size=(1.38, 0.12, 0.14))

    belt = b.part(
        "conveyor_belt", "rubber", parent="discharge_conveyor",
        pivot=CONV_PIVOT,
        label="Belt & head pulley",
        note="Never ride, cross or clear a running belt. Spillage is "
             "cleaned only with the conveyor isolated and locked out.",
        hotspot=(0, head[1] + 0.3, head[2]), hotspot_normal=(0, 1, -0.3))
    bar(belt, (0, CONV_PIVOT[1] + 0.12, CONV_PIVOT[2]),
        (0, head[1] + 0.12, head[2]), 1.00, 0.08)
    belt.cyl(center=head, radius=0.30, length=1.10, axis="x", segments=12)
    belt.box(center=(0, head[1] - 0.25, head[2] - 0.35),
             size=(1.20, 0.80, 0.10))                       # discharge hood

    slew = b.part(
        "slew_cylinders", "chrome",
        label="Luff & slew cylinders",
        note="Hold the conveyor's angle and swing. A conveyor swinging over "
             "a truck cab is the hazard to watch -- trucks are loaded from "
             "the side, never under the boom over the cab.",
        hotspot=(0.5, 2.9, -6.0), hotspot_normal=(1, 0.5, 0))
    for sx in (-1, 1):
        tube(slew, (sx * 0.55, 2.05, -4.40),
             (sx * 0.62, CONV_PIVOT[1] + 3.0 * math.sin(rad) - 0.25,
              CONV_PIVOT[2] - 3.0 * math.cos(rad)), 0.08)

    # -- upper works ------------------------------------------------------
    engine = b.part(
        "engine_pack", "body_yellow",
        label="Engine & drum drive",
        note="Diesel of about 750 kW. Most of it goes to the drum through a "
             "mechanical drive and clutch; the rest drives the crawlers, "
             "conveyors and water pumps hydraulically.",
        hotspot=(1.4, 3.6, 3.2), hotspot_normal=(1, 0.5, 0))
    engine.box(center=(0, 3.30, 3.00), size=(3.20, 1.20, 3.00))
    engine.box(center=(0.9, 4.10, 3.80), size=(0.30, 0.40, 0.30))

    tank = b.part(
        "water_system", "tank_blue",
        label="Water tank & dust sprays",
        note=("Water is sprayed at the drum to cool the picks and keep down "
              "respirable dust -- the main health hazard of the machine. "
              "Blocked nozzles mean silica or coal dust in the operator's "
              "and helper's lungs."),
        hotspot=(1.65, 3.2, -3.2), hotspot_normal=(1, 0.3, 0))
    tank.box(center=(0, 3.10, -3.20), size=(3.20, 0.80, 2.40))
    tank.cyl(center=(0, 1.55, DRUM[2] - 1.05), radius=0.06, length=2.60,
             axis="x", segments=8)

    cab = b.part(
        "operator_cab", "body_yellow",
        label="Operator's cabin",
        note="Sound-insulated, pressurised and filtered. From here the "
             "operator watches the cutting edge, the truck being loaded and "
             "the conveyor discharge.",
        hotspot=(-1.6, 3.6, 0.4), hotspot_normal=(-1, 0.3, 0))
    cab.box(center=(-0.60, 4.50, 0.40), size=(2.10, 0.12, 1.90))
    cab.box(center=(-0.60, 2.78, 0.40), size=(2.00, 0.16, 1.80))
    for sx in (-1, 1):
        for z in (-0.50, 1.30):
            cab.box(center=(-0.60 + sx * 0.97, 3.62, z),
                    size=(0.10, 1.70, 0.10))

    glass = b.part(
        "cab_glass", "glass",
        label="Cab glazing",
        note="All-round glass: the work is ahead (cut), alongside (truck) "
             "and above (conveyor).",
        hotspot=(-0.6, 3.6, -0.52), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(-0.60, 3.62, -0.48), size=(1.84, 1.60, 0.05))
    glass.box(center=(-0.60, 3.62, 1.28), size=(1.84, 1.60, 0.05))
    for sx in (-1, 1):
        glass.box(center=(-0.60 + sx * 0.98, 3.62, 0.40),
                  size=(0.05, 1.60, 1.64))

    rails = b.part(
        "walkways_rails", "rail",
        label="Walkways & handrails",
        note="Access ladders at the side. Board only when the drum is "
             "stopped and the operator has acknowledged you.",
        hotspot=(1.75, 3.4, 1.0), hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        for z in (-4.2, -1.6, 1.0, 4.2):
            rails.cyl(center=(sx * 1.66, 3.15, z), radius=0.04, length=0.90,
                      axis="y", segments=6)
        rails.cyl(center=(sx * 1.66, 3.60, 0.0), radius=0.04, length=8.40,
                  axis="z", segments=6)

    add_scale_figure(b, x=-3.20, z=-2.40)
    return b


SPECS = {
    "id": "surface-miner",
    "name": "Surface miner",
    "subtitle": "2.5 m cutting width, approx. 100 t -- Wirtgen 2500 SM / L&T KSM class",
    "category": "Continuous mining",
    "summary": (
        "Cuts coal or limestone directly from the bench in thin layers with "
        "a rotating drum, and loads it straight into trucks. No drilling, "
        "no blasting, no primary crushing -- which means no fly-rock or "
        "ground vibration near villages, and a clean, selective cut of "
        "thin seams and partings."),
    "specs": [
        ["Cutting width", "2.5 m"],
        ["Cutting depth", "up to approx. 0.65 m per pass"],
        ["Cutting drum diameter", "approx. 1.3 m with picks"],
        ["Operating weight", "approx. 95-100 t"],
        ["Engine", "approx. 750 kW diesel"],
        ["Discharge conveyor", "approx. 11 m, slews +/- 60 degrees"],
        ["Discharge height", "approx. 5-5.5 m"],
        ["Rock strength", "economic up to roughly 50-60 MPa UCS"],
        ["Output", "approx. 1000-2500 t/h, set by rock strength"],
        ["Product size", "typically under 100-150 mm"],
        ["Overall length", "approx. 20 m with conveyor"],
    ],
    "safety": [
        "Nobody near the drum while it turns. Pick changes only with the "
        "drum isolated, locked out and the engine stopped.",
        "Dust sprays must be working before cutting starts -- respirable "
        "silica and coal dust are the long-term killers.",
        "Trucks load alongside on the operator's signal; never position "
        "a truck where the conveyor swings over its cab.",
        "Mark out the cutting lane: the machine moves slowly but cannot "
        "stop a drum instantly.",
    ],
    "ar_tips": [
        "Walk round to the side and look under the frame: the drum is in "
        "the middle of the machine, between the front and rear crawlers.",
        "Stand at the conveyor's head: that is where a truck body has to "
        "be, about 11 m ahead of the machine.",
    ],
}


def main():
    return write_record(build(), SPECS, WEB, "surface-miner")


if __name__ == "__main__":
    main()
