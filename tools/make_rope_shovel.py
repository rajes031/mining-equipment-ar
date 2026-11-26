"""
make_rope_shovel.py -- generates a true-scale electric rope shovel as GLB.

Reference machine: approx. 40 m3 dipper electric rope shovel of about
1000 t -- the P&H 2800 / Cat 7395 class, the loading unit for 220-240 t
dumpers in large Indian coal mines. Students routinely confuse it with the
hydraulic shovel next to it in the catalogue; they are completely different
machines. Here the dipper is hoisted by wire ropes over the boom point and
pushed into the bank by a crowd mechanism, and everything runs on electricity
brought in by a trailing cable.

Axes: metres, Y up, the shovel faces -Z (towards the bank). Origin on the
ground at the centre of the swing circle.

Run:  python make_rope_shovel.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from figure import add_scale_figure
from glbgen import Builder
from machkit import bar, crawler_profile, standard_materials, tube, write_record

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

TRACK_GAUGE = 8.40
SHOE_W = 1.90
TRACK_LEN = 10.50
TRACK_TOP = 2.60
SWING = (0.0, 3.0, 0.0)

BOOM_FOOT = np.array([0.0, 4.8, -5.0])
BOOM_LEN = 18.0
BOOM_ANGLE = 45.0
GANTRY_TOP = 18.5
HANDLE_ANGLE = 25.0          # below horizontal, pointing forward
DIPPER_W, DIPPER_H, DIPPER_D = 4.0, 3.6, 3.4


def unit(deg_below, forward=True):
    a = math.radians(deg_below)
    return np.array([0.0, -math.sin(a), -math.cos(a) if forward else math.cos(a)])


def build() -> Builder:
    b = Builder("electric_rope_shovel_40m3")
    standard_materials(b)
    b.material("cable_orange", (0.88, 0.40, 0.06), roughness=0.8, metallic=0.0)

    # -- lower works ------------------------------------------------------
    half = TRACK_LEN / 2.0
    tracks = b.part(
        "crawlers", "dark",
        label="Crawlers",
        note=("Cast-steel shoes about 1.9 m wide. The shovel moves only a "
              "few metres at a time as the face advances, at under 2 km/h. "
              "Moving it far means unplugging and re-routing the trailing "
              "cable."),
        hotspot=(-TRACK_GAUGE / 2 - 1.1, 1.6, 1.0), hotspot_normal=(-1, 0.2, 0))
    for sx in (-1, 1):
        tracks.prism(crawler_profile(TRACK_LEN, TRACK_TOP, nose=0.9,
                                     chamfer=0.8),
                     extent=SHOE_W, axis="x",
                     offset=(sx * TRACK_GAUGE / 2, 0, 0))

    tumblers = b.part(
        "tumblers_rollers", "steel",
        label="Drive tumblers & rollers",
        note="Electric propel motors drive the rear tumblers through "
             "gearcases. Lower rollers carry the machine's 1000 t onto the "
             "shoes.",
        hotspot=(TRACK_GAUGE / 2 + 1.1, 1.3, half - 1.0),
        hotspot_normal=(1, 0, 0.3))
    for sx in (-1, 1):
        x = sx * TRACK_GAUGE / 2
        for z in (-half + 1.0, half - 1.0):
            tumblers.cyl(center=(x, 1.25, z), radius=1.15,
                         length=SHOE_W * 1.05, axis="x", segments=16)
        for i in range(6):
            tumblers.cyl(center=(x, 0.50, -3.0 + i * 1.2), radius=0.42,
                         length=SHOE_W * 0.85, axis="x", segments=10)

    carbody = b.part(
        "car_body", "steel",
        label="Car body & swing rack",
        note="Joins the crawlers and carries the roller circle and swing "
             "rack the whole upper works turns on.",
        hotspot=(0, 3.0, 4.2), hotspot_normal=(0, 0.4, 1))
    carbody.box(center=(0, 1.70, 0), size=(TRACK_GAUGE - SHOE_W - 0.2, 1.8, 6.0))
    carbody.cyl(center=(0, 2.70, 0), radius=4.3, length=0.6, axis="y",
                segments=28)

    cable = b.part(
        "trailing_cable", "cable_orange",
        label="Trailing cable",
        note=("Brings 6.6 kV (or 11 kV) from a substation to the shovel's "
              "collector rings. The machine stops if it is run over, and "
              "anyone handling it without authorisation can be killed. "
              "Vehicles cross it only on cable bridges."),
        hotspot=(3.4, 0.4, 9.0), hotspot_normal=(1, 1, 0))
    tube(cable, (2.0, 1.2, 2.8), (2.8, 0.12, 5.6), 0.10, segments=8)
    tube(cable, (2.8, 0.12, 5.6), (4.5, 0.12, 15.0), 0.10, segments=8)

    # -- upper works ------------------------------------------------------
    house = b.part(
        "machinery_house", "body_yellow", pivot=SWING,
        label="Machinery house",
        note=("Holds the hoist, crowd and swing motors and gearing and the "
              "AC drive cabinets -- several thousand kW in all. Some of the "
              "energy of lowering and swing-braking is regenerated back to "
              "the grid."),
        hotspot=(5.4, 7.5, 3.0), hotspot_normal=(1, 0.2, 0))
    house.box(center=(0, 3.60, 2.00), size=(10.5, 1.20, 13.0))     # deck
    house.box(center=(0, 7.10, 2.50), size=(10.0, 5.80, 11.0))
    house.box(center=(0, 10.35, 3.50), size=(7.0, 0.70, 7.0))

    cwt = b.part(
        "counterweight", "body_yellow", parent="machinery_house", pivot=SWING,
        label="Counterweight box",
        note="Filled with several hundred tonnes of ballast to balance the "
             "loaded dipper. The rear of the house sweeps round during "
             "swing -- the tail-swing zone behind the shovel is no-go.",
        hotspot=(0, 5.0, 10.6), hotspot_normal=(0, 0.2, 1))
    cwt.box(center=(0, 5.00, 9.30), size=(10.0, 2.60, 2.00))

    gantry = b.part(
        "gantry", "body_yellow", parent="machinery_house", pivot=SWING,
        label="Gantry (A-frame)",
        note="Holds the boom suspension ropes. With the boom foot pinned "
             "low on the house, this triangle is the shovel's backbone.",
        hotspot=(1.5, 16.0, 2.0), hotspot_normal=(1, 0.4, 0))
    for sx in (-1, 1):
        for z in (-2.0, 6.5):
            tube(gantry, (sx * 3.5, 10.0, z), (sx * 1.2, GANTRY_TOP, 1.0),
                 0.40, segments=10)
    gantry.cyl(center=(0, GANTRY_TOP, 1.0), radius=0.50, length=3.0,
               axis="x", segments=12)

    cab = b.part(
        "operator_cab", "body_yellow", parent="machinery_house", pivot=SWING,
        label="Operator's cab",
        note=("On the front left deck, about 10 m up, looking straight into "
              "the dipper. Trucks spot on the operator's side so the dipper "
              "never swings over a truck cab."),
        hotspot=(-5.2, 11.4, -2.0), hotspot_normal=(-1, 0.2, -0.3))
    cab.box(center=(-3.8, 11.30, -1.80), size=(2.6, 2.6, 2.8))

    glass = b.part(
        "cab_glass", "glass", parent="machinery_house", pivot=SWING,
        label="Cab glazing",
        note="Floor-to-roof front glass angled down at the dipper.",
        hotspot=(-3.8, 11.3, -3.3), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(-3.8, 11.35, -3.24), size=(2.2, 2.1, 0.06))
    glass.box(center=(-5.12, 11.35, -1.80), size=(0.06, 2.1, 2.2))

    # -- boom, handle, dipper ---------------------------------------------
    up_dir = np.array([0.0, math.sin(math.radians(BOOM_ANGLE)),
                       -math.cos(math.radians(BOOM_ANGLE))])
    tip = BOOM_FOOT + up_dir * BOOM_LEN
    boom = b.part(
        "boom", "body_yellow", parent="machinery_house",
        pivot=tuple(BOOM_FOOT),
        label="Boom",
        note=("Fixed at about 45 degrees and held by ropes from the gantry. "
              "Unlike a hydraulic shovel, the boom does not move while "
              "digging: the dipper is driven by the hoist ropes and the "
              "crowd."),
        hotspot=tuple(BOOM_FOOT + up_dir * 13 + np.array([1.0, 0.6, 0])),
        hotspot_normal=(1, 0.4, 0))
    bar(boom, BOOM_FOOT, tip, 1.6, 2.0)
    boom.cyl(center=tuple(BOOM_FOOT), radius=0.6, length=2.8, axis="x",
             segments=12)

    sheave = b.part(
        "boom_point_sheaves", "steel", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Boom point sheaves",
        note="The hoist ropes run over these, about 18 m up, and down to "
             "the dipper bail.",
        hotspot=tuple(tip + np.array([0.9, 1.0, -0.8])),
        hotspot_normal=(1, 0.3, -0.3))
    sheave.cyl(center=tuple(tip), radius=1.7, length=1.4, axis="x",
               segments=18)

    shipper = BOOM_FOOT + up_dir * BOOM_LEN * 0.5
    crowd = b.part(
        "shipper_shaft_crowd", "steel", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Shipper shaft & crowd",
        note=("The crowd motor turns the shipper shaft through the boom. "
              "Pinions on it drive racks on the handle, pushing the dipper "
              "into the bank while the hoist pulls it up -- two forces "
              "together make the dig."),
        hotspot=tuple(shipper + np.array([2.0, 0.4, 0])),
        hotspot_normal=(1, 0.2, 0))
    crowd.cyl(center=tuple(shipper), radius=0.55, length=3.8, axis="x",
              segments=12)
    for sx in (-1, 1):
        crowd.box(center=tuple(shipper + np.array([sx * 1.25, -0.2, 0])),
                  size=(0.8, 1.3, 1.6))                     # saddle blocks

    hdir = unit(HANDLE_ANGLE)
    h_back = shipper - hdir * 3.5
    h_front = shipper + hdir * 9.5
    handle = b.part(
        "dipper_handle", "body_yellow", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Dipper handle",
        note="Twin-leg handle straddling the boom, sliding in the saddle "
             "blocks as the crowd extends and retracts it.",
        hotspot=tuple(shipper + hdir * 6.0 + np.array([1.8, 0, 0])),
        hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        bar(handle, h_back + [sx * 1.25, 0, 0], h_front + [sx * 1.25, 0, 0],
            0.55, 0.85)

    D = h_front + np.array([0.0, -1.5, -1.2])
    dhw, dhh, dhd = DIPPER_W / 2, DIPPER_H / 2, DIPPER_D / 2
    dipper = b.part(
        "dipper", "wear", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Dipper (approx. 40 m3)",
        note=("About 65-70 t of blasted rock a pass: three to four passes "
              "fill a 220-240 t dumper. Matching dipper size to truck size "
              "is the basic decision of a shovel-dumper system."),
        hotspot=tuple(D + np.array([dhw + 0.4, 0.4, 0])),
        hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        dipper.box(center=tuple(D + [sx * (dhw - 0.12), 0, 0]),
                   size=(0.24, DIPPER_H, DIPPER_D))
    dipper.box(center=tuple(D + [0, dhh - 0.12, 0]),
               size=(DIPPER_W, 0.24, DIPPER_D))
    dipper.box(center=tuple(D + [0, 0, dhd - 0.15]),
               size=(DIPPER_W, DIPPER_H, 0.30))             # back wall

    door = b.part(
        "dipper_door", "dark", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Dipper door & trip",
        note="The bottom of the dipper is a hinged door held by a latch. "
             "Over the truck the operator trips the latch and the load "
             "falls out; the door slams shut as the dipper swings back.",
        hotspot=tuple(D + np.array([0, -dhh - 0.4, 0.4])),
        hotspot_normal=(0, -0.6, 0.6))
    door.box(center=tuple(D + [0, -dhh + 0.12, 0]),
             size=(DIPPER_W - 0.1, 0.24, DIPPER_D))

    teeth = b.part(
        "dipper_teeth", "steel", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Lip & teeth",
        note=("Teeth on the front lip break into the bank as the crowd "
              "pushes. Tooth changes are done with the dipper grounded and "
              "the machine locked out."),
        hotspot=tuple(D + np.array([0, -dhh + 0.3, -dhd - 1.0])),
        hotspot_normal=(0, 0.2, -1))
    teeth.box(center=tuple(D + [0, -dhh + 0.25, -dhd + 0.15]),
              size=(DIPPER_W, 0.5, 0.4))
    for i in range(5):
        x = -dhw + 0.45 + i * (DIPPER_W - 0.9) / 4
        teeth.prism([(0.0, 0.0), (-0.8, 0.10), (-0.8, 0.28), (0.0, 0.46)],
                    extent=0.28, axis="x",
                    offset=(D[0] + x, D[1] - dhh + 0.02, D[2] - dhd))

    bail_top = D + np.array([0, dhh + 2.2, -dhd - 0.5])
    bail = b.part(
        "bail", "steel", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Bail & equaliser",
        note="Links the two hoist ropes to the dipper and keeps their "
             "tension equal.",
        hotspot=tuple(bail_top + np.array([0.8, 0.2, 0])),
        hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        tube(bail, D + [sx * (dhw + 0.1), dhh - 0.4, -dhd + 0.5], bail_top,
             0.16, segments=8)
    bail.cyl(center=tuple(bail_top), radius=0.35, length=1.4, axis="x",
             segments=10)

    ropes = b.part(
        "wire_ropes", "rope", parent="machinery_house", pivot=SWING,
        label="Hoist & suspension ropes",
        note=("Hoist ropes wind on a drum in the house, run up over the "
              "gantry and boom point and down to the bail. Suspension ropes "
              "hold the boom. Ropes are inspected every shift and replaced "
              "on hours."),
        hotspot=tuple(tip + np.array([0.8, -5.0, -1.0])),
        hotspot_normal=(1, 0, 0))
    for sx in (-0.45, 0.45):
        tube(ropes, (sx, GANTRY_TOP, 1.0), tip + [sx, 0.9, 0.6], 0.07,
             segments=6)
        tube(ropes, tip + [sx, -0.4, -1.6], bail_top + [sx, 0, 0], 0.07,
             segments=6)
        tube(ropes, (sx, 10.4, 0.5), (sx, GANTRY_TOP - 0.4, 1.0), 0.07,
             segments=6)

    add_scale_figure(b, x=-7.5, z=-8.0)
    return b


SPECS = {
    "id": "rope-shovel",
    "name": "Electric rope shovel",
    "subtitle": "approx. 40 m3 dipper, approx. 1000 t -- P&H 2800 / Cat 7395 class",
    "category": "Loading",
    "summary": (
        "The big loading machine of large opencast mines. Electric, rope-"
        "operated and very long-lived -- 25 years or more -- it fills a "
        "220-240 t dumper in three or four passes. Compare it with the "
        "hydraulic shovel: here the boom is fixed and the dipper is hoisted "
        "by ropes and pushed by a crowd, not driven by cylinders."),
    "specs": [
        ["Dipper capacity", "approx. 35-45 m3 (approx. 65-70 t a pass)"],
        ["Passes per 220-240 t truck", "3 to 4"],
        ["Operating weight", "approx. 1000 t"],
        ["Power", "electric, 6.6 or 11 kV trailing cable"],
        ["Boom length", "approx. 18 m at 45 degrees"],
        ["Cutting height", "approx. 15-16 m"],
        ["Dumping height", "approx. 9-10 m"],
        ["Swing radius, rear", "approx. 9-10 m -- tail-swing zone"],
        ["Crawler width", "approx. 10.3 m over shoes"],
        ["Cycle time", "approx. 30-35 s"],
        ["Productivity", "approx. 3000-4000 t/h in good digging"],
    ],
    "safety": [
        "Approach only after the operator has seen you, grounded the "
        "dipper and signalled you in.",
        "The rear of the house swings out about 9 m: keep vehicles and "
        "people out of the tail-swing zone.",
        "The trailing cable is high-voltage. Never drive over it except on "
        "a bridge; only authorised electrical staff move it.",
        "Face height must stay within the cutting height -- overhangs "
        "above the dipper are a fatal hazard.",
    ],
    "ar_tips": [
        "Place it next to the hydraulic shovel and the 220 t dumper to "
        "compare the two loaders, and to see the dipper over the truck.",
        "Walk round to the back: the counterweight box sweeps a circle you "
        "would be standing in.",
    ],
}


def main():
    return write_record(build(), SPECS, WEB, "rope-shovel")


if __name__ == "__main__":
    main()
