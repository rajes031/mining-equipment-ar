"""
make_dragline.py -- generates a true-scale walking dragline as GLB.

Reference machine: the "24/96" class -- 24 m3 bucket on a 96 m boom -- the
size of walking dragline that strips overburden in the Singrauli coalfield
and elsewhere in India (BE 1570W / Marion 8050 family). It sits on the bench
above the coal, casts the overburden straight into the mined-out void behind
it, and never needs a truck.

At 1:1 the model is over 110 m long and 57 m tall, so in AR it needs a
playing field. That is the point: "nothing conveys a 100 m boom like standing
under one".

Axes: metres, Y up, boom pointing -Z. Origin on the ground at the centre of
the tub (the swing axis).

Run:  python make_dragline.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from figure import add_scale_figure
from glbgen import Builder
from machkit import bar, standard_materials, tube, write_record

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

TUB_R = 9.5
TUB_H = 2.2
HOUSE = dict(x=10.0, y0=2.6, y1=12.6, z0=-11.0, z1=14.0)
SWING = (0.0, TUB_H, 0.0)

BOOM_LEN = 96.0
BOOM_ANGLE = 32.0                       # degrees above horizontal
BOOM_FOOT = np.array([0.0, 6.0, -12.0])
FOOT_HALF_W, FOOT_HALF_D = 4.0, 2.4     # boom section at the foot
TIP_HALF_W, TIP_HALF_D = 1.4, 1.4       # and at the point
PANELS = 12

MAST_HEAD = (0.0, 40.0, -28.0)
A_FRAME_APEX = (0.0, 28.0, 6.0)
FAIRLEAD = (0.0, 3.6, -12.8)

BUCKET = np.array([0.0, 4.6, -76.0])    # bucket centre, mouth facing +Z
BKT_L, BKT_W, BKT_H = 4.6, 3.8, 2.8


def boom_axes():
    a = math.radians(BOOM_ANGLE)
    along = np.array([0.0, math.sin(a), -math.cos(a)])
    up = np.array([0.0, math.cos(a), math.sin(a)])      # boom's "top" side
    return along, up


def boom_corner(s, sx, sy):
    """Chord corner at fraction s along the boom; sx, sy = +/-1."""
    along, up = boom_axes()
    hw = FOOT_HALF_W + (TIP_HALF_W - FOOT_HALF_W) * s
    hd = FOOT_HALF_D + (TIP_HALF_D - FOOT_HALF_D) * s
    return (BOOM_FOOT + along * BOOM_LEN * s
            + np.array([sx * hw, 0, 0]) + up * sy * hd)


def boom_point():
    along, _ = boom_axes()
    return BOOM_FOOT + along * BOOM_LEN


def build() -> Builder:
    b = Builder("walking_dragline_24_96")
    standard_materials(b)

    # -- base: tub and walking gear --------------------------------------
    tub = b.part(
        "tub", "steel",
        label="Tub (base)",
        note=("A circular base about 19 m across that the whole machine "
              "sits on while digging. Its huge area keeps ground pressure "
              "low, around 2 kg/cm2 for a machine of over 2000 t. The bench "
              "it sits on must be level and well drained."),
        hotspot=(-TUB_R - 0.3, 1.2, -2.0), hotspot_normal=(-1, 0.2, -0.2))
    tub.cyl(center=(0, TUB_H / 2, 0), radius=TUB_R, length=TUB_H, axis="y",
            segments=32)

    shoes = b.part(
        "walking_shoes", "dark",
        label="Walking shoes",
        note=("To move, eccentric cams lift the machine onto these shoes, "
              "shuffle it back about 2 m, and set the tub down -- walking, "
              "not driving. Top speed is a few hundred metres an hour, and "
              "a move to a new pit can take weeks."),
        hotspot=(-14.0, 1.6, -11.5), hotspot_normal=(-0.4, 0.6, -1))
    for sx in (-1, 1):
        shoes.box(center=(sx * 14.0, 0.70, 0), size=(5.0, 1.40, 22.0))

    # -- house (revolving frame) -----------------------------------------
    hx, hy0, hy1, hz0, hz1 = (HOUSE[k] for k in ("x", "y0", "y1", "z0", "z1"))
    house = b.part(
        "house", "body_yellow", pivot=SWING,
        label="Machinery house",
        note=("Holds the hoist, drag, swing and walk motors and the "
              "motor-generator sets or drives -- several megawatts in all, "
              "fed at 6.6-11 kV by a trailing cable. The whole house "
              "swings on a roller circle on top of the tub."),
        hotspot=(hx + 0.3, 8.0, 4.0), hotspot_normal=(1, 0.2, 0))
    house.box(center=(0, (hy0 + hy1) / 2, (hz0 + hz1) / 2),
              size=(2 * hx, hy1 - hy0, hz1 - hz0))
    house.box(center=(0, hy1 + 0.8, 3.0), size=(12.0, 1.6, 14.0))

    walk = b.part(
        "walking_cams", "steel", parent="house", pivot=SWING,
        label="Walking cams & legs",
        note="Each side has an eccentric cam driving a leg down to its "
             "shoe. Walking turns the whole 2000 t machine into a very "
             "slow, very heavy pair of crutches.",
        hotspot=(hx + 1.6, 7.5, 0.0), hotspot_normal=(1, 0, 0))
    for sx in (-1, 1):
        walk.cyl(center=(sx * (hx + 1.0), 7.5, 0.0), radius=2.8, length=1.6,
                 axis="x", segments=20)
        for z in (-5.0, 5.0):
            bar(walk, (sx * (hx + 1.8), 7.5, 0.0), (sx * 14.0, 1.4, z),
                1.2, 1.2)

    cwt = b.part(
        "counterweight", "body_yellow", parent="house", pivot=SWING,
        label="Counterweight",
        note="Hundreds of tonnes of ballast at the back of the house, to "
             "balance a 96 m boom and a loaded bucket of 40 t or more at "
             "its end.",
        hotspot=(0, 6.0, hz1 + 3.6), hotspot_normal=(0, 0.2, 1))
    cwt.box(center=(0, 5.8, hz1 + 1.75), size=(2 * hx - 1.0, 6.4, 3.5))

    cab = b.part(
        "operator_cab", "body_yellow", parent="house", pivot=SWING,
        label="Operator's cab",
        note=("At the front left, looking down the boom. The operator "
              "judges the bucket nearly 90 m away; skilled draglining is "
              "about swinging and dumping on the move, in a cycle of about "
              "a minute."),
        hotspot=(-hx + 1.8, 13.8, hz0 - 1.2), hotspot_normal=(-0.5, 0.3, -1))
    cab.box(center=(-hx + 2.4, 13.8, hz0 + 1.2), size=(4.4, 3.2, 4.0))

    glass = b.part(
        "cab_glass", "glass", parent="house", pivot=SWING,
        label="Cab glazing",
        note="Front and floor windows, angled down towards the bucket.",
        hotspot=(-hx + 2.4, 13.8, hz0 - 0.9), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(-hx + 2.4, 13.9, hz0 - 0.82), size=(3.8, 2.4, 0.08))
    glass.box(center=(-hx + 0.16, 13.9, hz0 + 1.2), size=(0.08, 2.4, 3.4))

    fair = b.part(
        "fairlead", "steel", parent="house", pivot=SWING,
        label="Fairlead",
        note=("Sheaves that guide the drag ropes in from any angle as the "
              "house swings. Drag ropes wear fastest here and at the "
              "bucket -- a parted drag rope whips with lethal force."),
        hotspot=(3.0, 3.6, FAIRLEAD[2] - 1.5), hotspot_normal=(0.4, 0.2, -1))
    fair.box(center=(0, FAIRLEAD[1], FAIRLEAD[2] + 0.4), size=(5.0, 2.6, 2.4))
    for sx in (-1, 1):
        fair.cyl(center=(sx * 0.9, FAIRLEAD[1], FAIRLEAD[2] - 0.8),
                 radius=1.1, length=0.5, axis="y", segments=16)

    # -- A-frame and mast ------------------------------------------------
    aframe = b.part(
        "a_frame", "body_yellow", parent="house", pivot=SWING,
        label="A-frame",
        note="The fixed tower on the house roof that anchors the back "
             "stays of the mast.",
        hotspot=(3.0, 22.0, 6.0), hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        for z in (-2.0, 14.0):
            tube(aframe, (sx * 7.5, hy1, z), A_FRAME_APEX, 0.55, segments=10)

    mast = b.part(
        "mast", "body_yellow", parent="house", pivot=SWING,
        label="Mast",
        note="A tall strut leaning out over the boom. It gives the boom "
             "suspension ropes enough angle to hold a 96 m lattice boom "
             "with a loaded bucket.",
        hotspot=(1.5, 30.0, -22.0), hotspot_normal=(1, 0.3, -0.3))
    for sx in (-1, 1):
        tube(mast, (sx * 4.0, hy1, -9.5), MAST_HEAD, 0.65, segments=10)
    mast.cyl(center=MAST_HEAD, radius=0.9, length=3.0, axis="x", segments=12)

    # -- boom --------------------------------------------------------------
    boom = b.part(
        "boom", "body_yellow", parent="house", pivot=tuple(BOOM_FOOT),
        label="Boom (96 m lattice)",
        note=("A tapered tubular lattice, as long as a football pitch, held "
              "up only by ropes. Its angle is fixed while digging. Booms are "
              "inspected for cracks constantly: a dropped boom is the "
              "costliest accident a mine can have."),
        hotspot=tuple(boom_corner(0.35, 1, 1) + np.array([0.5, 0.5, 0])),
        hotspot_normal=(1, 0.5, 0))
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for sx, sy in corners:                                   # chords
        tube(boom, boom_corner(0, sx, sy), boom_corner(1, sx, sy), 0.32,
             segments=8)
    for i in range(PANELS + 1):                              # frames
        s = i / PANELS
        ring = [boom_corner(s, sx, sy) for sx, sy in corners]
        for k in range(4):
            tube(boom, ring[k], ring[(k + 1) % 4], 0.14, segments=6)
        if i < PANELS:                                       # lacing
            s1 = (i + 1) / PANELS
            nxt = [boom_corner(s1, sx, sy) for sx, sy in corners]
            for k in range(4):
                a, c = (ring[k], nxt[(k + 1) % 4]) if i % 2 == 0 else \
                       (ring[(k + 1) % 4], nxt[k])
                tube(boom, a, c, 0.12, segments=6)
    for sx in (-1, 1):
        boom.cyl(center=tuple(BOOM_FOOT + np.array([sx * FOOT_HALF_W, 0, 0])),
                 radius=0.8, length=1.4, axis="x", segments=12)

    tip = boom_point()
    sheave = b.part(
        "boom_point_sheaves", "steel", parent="boom", pivot=tuple(BOOM_FOOT),
        label="Boom point sheaves",
        note="The hoist ropes run over these at the very end of the boom, "
             "about 57 m above the ground.",
        hotspot=tuple(tip + np.array([0, 2.4, -1.0])),
        hotspot_normal=(0, 1, -0.4))
    sheave.cyl(center=tuple(tip), radius=2.0, length=1.6, axis="x",
               segments=18)

    ropes = b.part(
        "suspension_ropes", "rope", parent="house", pivot=SWING,
        label="Suspension ropes & back stays",
        note=("Fixed-length wire-rope pendants from the mast head to the "
              "boom, with back stays to the A-frame. They carry the whole "
              "boom. Pendants are replaced on a schedule, not when they "
              "look worn."),
        hotspot=(0.6, 46.0, -60.0), hotspot_normal=(1, 0.3, 0))
    for sx in (-0.8, 0.8):
        head = (sx, MAST_HEAD[1], MAST_HEAD[2])
        for s in (0.55, 1.0):
            tube(ropes, head, boom_corner(s, 0, 1) + np.array([sx, 0, 0]),
                 0.09, segments=6)
        tube(ropes, head, (sx, A_FRAME_APEX[1], A_FRAME_APEX[2]), 0.12,
             segments=6)

    # -- bucket and rigging -----------------------------------------------
    B = BUCKET
    bucket = b.part(
        "bucket", "wear",
        label="Bucket (24 m3)",
        note=("About 40 t of rock per pass. It is filled by being dragged "
              "towards the machine along the bench face, then hoisted, "
              "swung and dumped -- all by ropes, with nothing rigid between "
              "bucket and machine."),
        hotspot=tuple(B + np.array([BKT_W / 2 + 0.4, 0.4, 0])),
        hotspot_normal=(1, 0.2, 0))
    hl, hw, hh = BKT_L / 2, BKT_W / 2, BKT_H / 2
    bucket.box(center=tuple(B + [0, -hh + 0.12, 0]), size=(BKT_W, 0.25, BKT_L))
    side = [(-hl, -hh), (hl, -hh), (hl, 0.2), (hl - 1.3, hh), (-hl, hh)]
    for sx in (-1, 1):
        bucket.prism(side, extent=0.22, axis="x",
                     offset=(B[0] + sx * (hw - 0.11), B[1], B[2]))
    bucket.box(center=tuple(B + [0, 0, -hl + 0.12]), size=(BKT_W, BKT_H, 0.25))
    for sx in (-1, 1):                                       # arch legs
        bucket.box(center=tuple(B + [sx * (hw + 0.15), hh - 0.2, 0.9]),
                   size=(0.35, 1.4, 0.6))
    bucket.box(center=tuple(B + [0, hh + 0.65, 0.9]),
               size=(BKT_W + 0.65, 0.5, 0.6))                # arch

    teeth = b.part(
        "bucket_teeth", "steel",
        label="Lip & teeth",
        note="The teeth face the machine: the bucket digs as it is pulled "
             "in. Lost teeth end up in the coal and can wreck a crusher.",
        hotspot=tuple(B + np.array([0, -hh, hl + 0.8])),
        hotspot_normal=(0, 0.3, 1))
    teeth.box(center=tuple(B + [0, -hh + 0.15, hl - 0.2]),
              size=(BKT_W, 0.30, 0.50))
    for i in range(5):
        x = -hw + 0.4 + i * (BKT_W - 0.8) / 4
        teeth.prism([(0.0, 0.0), (0.75, 0.08), (0.75, 0.22), (0.0, 0.36)],
                    extent=0.26, axis="x",
                    offset=(B[0] + x, B[1] - hh, B[2] + hl))

    socket = B + np.array([0, 7.6, -0.6])        # hoist rope end
    spread_y = B[1] + 5.2
    hitch = B + np.array([0, -hh + 0.4, hl + 4.0])
    chains = b.part(
        "rigging_chains", "dark",
        label="Hoist & drag chains, spreader bar",
        note=("Hoist chains lift the bucket from its trunnions through a "
              "spreader bar; drag chains pull it from the front. The dump "
              "rope holds the front up until drag tension is released -- "
              "then the bucket tips and empties."),
        hotspot=tuple(B + np.array([hw + 0.8, 3.5, -0.4])),
        hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        tube(chains, B + [sx * (hw + 0.2), 0.0, -0.4],
             (sx * (hw + 0.6), spread_y, B[2] - 0.6), 0.10, segments=6)
        tube(chains, (sx * (hw + 0.6), spread_y, B[2] - 0.6), socket,
             0.10, segments=6)
        tube(chains, B + [sx * (hw + 0.05), -hh + 0.5, hl - 0.2], hitch,
             0.11, segments=6)
    chains.box(center=(0, spread_y, B[2] - 0.6), size=(BKT_W + 1.6, 0.35, 0.35))

    hoist = b.part(
        "hoist_drag_ropes", "rope",
        label="Hoist, drag & dump ropes",
        note=("Hoist ropes run over the boom point; drag ropes come in "
              "through the fairlead. Ropes of 75-100 mm diameter are "
              "consumables here, changed every few months. Nobody stands "
              "within the swing radius or under the boom."),
        hotspot=(0.4, 30.0, -86.0), hotspot_normal=(1, 0, 0))
    for sx in (-0.35, 0.35):
        tube(hoist, socket + [sx, 0, 0],
             tip + np.array([sx, -1.8, -0.6]), 0.06, segments=6)
        tube(hoist, hitch + [sx, 0, 0],
             (sx, FAIRLEAD[1], FAIRLEAD[2] - 1.0), 0.06, segments=6)
    tube(hoist, B + [0, hh + 0.9, 0.9], socket, 0.05, segments=6)   # dump

    add_scale_figure(b, x=-6.0, z=-14.5)
    return b


SPECS = {
    "id": "dragline",
    "name": "Walking dragline",
    "subtitle": "24 m3 bucket on a 96 m boom -- the 24/96 class, approx. 2000+ t",
    "category": "Overburden removal",
    "summary": (
        "The cheapest way to move overburden that exists, when the geology "
        "suits it. The dragline sits on the bench above the coal, digs the "
        "overburden below it and casts it directly into the mined-out "
        "void, with no trucks at all. In AR at full size it needs a "
        "playing field: this is a machine you stand under, not beside."),
    "specs": [
        ["Bucket capacity", "24 m3 (approx. 40-45 t of rock per pass)"],
        ["Boom length", "96 m at about 32 degrees"],
        ["Dump radius", "approx. 85-88 m"],
        ["Boom point height", "approx. 57 m"],
        ["Operating weight", "approx. 2000-2500 t"],
        ["Power", "electric, several MW, 6.6-11 kV trailing cable"],
        ["Tub diameter", "approx. 19 m"],
        ["Ground pressure (on tub)", "approx. 2 kg/cm2"],
        ["Cycle time", "approx. 55-65 s (drag, hoist, swing, dump, return)"],
        ["Walking", "approx. 2 m per step, a few hundred m/h"],
        ["Output", "roughly 10-15 Mm3 of overburden a year"],
    ],
    "safety": [
        "Keep out of the swing radius of the house AND the radius of the "
        "bucket -- nearly 90 m from the machine.",
        "Never stand in line with a drag rope under tension; a parted "
        "rope whips across the bench.",
        "The trailing cable carries 6.6-11 kV. Only authorised electrical "
        "staff handle it, and vehicles cross it only on a cable bridge.",
        "Bench stability under the tub is critical: watch for cracks at "
        "the highwall crest the dragline sits behind.",
    ],
    "ar_tips": [
        "Use an open ground at least 120 m long. Stand at the tub and look "
        "out along the boom to the bucket.",
        "Walk out to the bucket: the 1.8 m figure is beside the tub, and "
        "the bucket alone is larger than a room.",
        "If you have no space, view it at reduced scale on a table first "
        "-- then go outside.",
    ],
}


def main():
    return write_record(build(), SPECS, WEB, "dragline")


if __name__ == "__main__":
    main()
