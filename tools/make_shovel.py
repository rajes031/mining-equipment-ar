"""
make_shovel.py -- generates a true-scale hydraulic front shovel as GLB.

Reference machine: 140 t-class hydraulic mining shovel in face-shovel
configuration with a ~7.5 m3 bucket -- the CAT 6015 / Komatsu PC1250 /
Hitachi EX1200 / Tata Hitachi EX1200 family, the standard loading unit for
220 t dumpers in Indian opencast mines.

The machine is posed mid-dig: boom up, stick crowded forward, bucket teeth
near ground level at about 10 m reach. That pose is deliberate -- in AR you
want students to see the digging envelope, not a transport pose.

Axes: metres, Y up, the shovel faces -Z (towards the face), cab on the left.
Origin on the ground at the centre of the swing circle.

Run:  python make_shovel.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder, compose, rotate, translate

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

TRACK_GAUGE = 4.25          # centre-to-centre of the two crawlers
SHOE_WIDTH = 0.75
TRACK_LEN = 6.70
TRACK_TOP = 1.60            # top of track frame above ground
HOUSE_Y0 = 1.90             # underside of superstructure
HOUSE_Y1 = 4.50

# linkage pivots, all in the x = 0 plane
BOOM_FOOT = (0, 3.20, -2.20)
BOOM_TIP = (0, 7.60, -7.40)
STICK_END = (0, 4.20, -8.90)
BUCKET_CENTRE = (0, 3.05, -9.65)
SWING = (0.0, HOUSE_Y0, 0.0)      # the slew axis everything above turns on


def strut(p0, p1, x_offset=0.0):
    """Length and transform for a z-aligned primitive spanning p0 -> p1."""
    (_, y0, z0), (_, y1, z1) = p0, p1
    dy, dz = y1 - y0, z1 - z0
    length = math.hypot(dy, dz)
    theta = math.degrees(math.atan2(-dy, dz))
    mid = (x_offset, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    return length, compose(translate(*mid), rotate("x", theta))


def build() -> Builder:
    b = Builder("hydraulic_shovel_140t")

    b.material("body_yellow", (0.93, 0.66, 0.05), roughness=0.55, metallic=0.15)
    b.material("steel", (0.40, 0.42, 0.45), roughness=0.45, metallic=0.70)
    b.material("dark", (0.13, 0.13, 0.15), roughness=0.70, metallic=0.25)
    b.material("chrome", (0.80, 0.81, 0.84), roughness=0.15, metallic=0.95)
    b.material("wear", (0.28, 0.29, 0.32), roughness=0.35, metallic=0.85)
    b.material("glass", (0.42, 0.55, 0.62), roughness=0.08, metallic=0.0,
               alpha=0.42, double_sided=True)
    b.material("rail", (0.95, 0.78, 0.08), roughness=0.5, metallic=0.2)

    # -- undercarriage ----------------------------------------------------
    half_len = TRACK_LEN / 2.0
    chain = [(-half_len, 0.55), (-half_len + 0.45, 0.02),
             (half_len - 0.45, 0.02), (half_len, 0.55),
             (half_len, TRACK_TOP - 0.45), (half_len - 0.45, TRACK_TOP),
             (-half_len + 0.45, TRACK_TOP), (-half_len, TRACK_TOP - 0.45)]

    tracks = b.part(
        "crawler_tracks", "dark",
        label="Crawler tracks",
        note=("Two independently driven crawlers, 750 mm shoes. Ground "
              "bearing pressure is only about 2.2 kg/cm2 -- roughly a walking "
              "person -- which is how a 140 t machine works on a soft floor."),
        hotspot=(-TRACK_GAUGE / 2 - 0.5, 1.1, 0), hotspot_normal=(-1, 0.2, 0))
    for sx in (-1, 1):
        tracks.prism(chain, extent=SHOE_WIDTH, axis="x",
                     offset=(sx * TRACK_GAUGE / 2, 0, 0))

    rollers = b.part(
        "sprockets_idlers", "steel",
        label="Drive sprockets & idlers",
        note=("Travel motor and planetary drive at the sprocket end; track "
              "tension is set hydraulically at the idler. Shovels travel very "
              "little -- undercarriage wear comes mostly from swing and dig "
              "reaction forces."),
        hotspot=(TRACK_GAUGE / 2 + 0.5, 0.85, half_len - 0.6),
        hotspot_normal=(1, 0, 0.3))
    for sx in (-1, 1):
        x = sx * TRACK_GAUGE / 2
        rollers.cyl(center=(x, 0.82, half_len - 0.55), radius=0.72,
                    length=SHOE_WIDTH * 1.08, axis="x", segments=14)
        rollers.cyl(center=(x, 0.82, -half_len + 0.55), radius=0.72,
                    length=SHOE_WIDTH * 1.08, axis="x", segments=14)
        for i in range(5):
            z = -2.0 + i * 1.0
            rollers.cyl(center=(x, 0.35, z), radius=0.28,
                        length=SHOE_WIDTH * 0.9, axis="x", segments=8)

    carbody = b.part(
        "car_body", "steel",
        label="Car body & swing circle",
        note=("The car body ties the crawlers together and carries the swing "
              "bearing. All power and oil to the upper works passes through "
              "the centre swivel inside this ring."),
        hotspot=(0, 1.95, 1.2), hotspot_normal=(0, 1, 0.3))
    carbody.box(center=(0, 1.00, 0), size=(TRACK_GAUGE - 0.9, 0.95, 4.20))
    carbody.cyl(center=(0, 1.72, 0), radius=1.65, length=0.55, axis="y",
                segments=20)

    # -- upper works ------------------------------------------------------
    house = b.part(
        "superstructure", "body_yellow", pivot=SWING,
        label="Superstructure (house)",
        note=("Carries the diesel engine (about 600-800 kW), the main "
              "hydraulic pumps, oil coolers and tanks. Everything above the "
              "swing circle rotates 360 degrees."),
        hotspot=(TRACK_GAUGE / 2 + 0.4, 3.2, 0.5), hotspot_normal=(1, 0.2, 0))
    house.box(center=(0, (HOUSE_Y0 + HOUSE_Y1) / 2, 0.40),
              size=(4.80, HOUSE_Y1 - HOUSE_Y0, 6.40))
    house.box(center=(0, HOUSE_Y1 + 0.25, 1.40), size=(3.40, 0.50, 3.20))

    engine = b.part(
        "engine_cooling", "dark", parent="superstructure", pivot=SWING,
        label="Engine & cooling pack",
        note=("Diesel-hydraulic drive: the engine turns variable-displacement "
              "pumps, and oil does all the work. Electric-drive versions trail "
              "a cable and cut fuel cost where the pit layout allows it."),
        hotspot=(1.3, 5.1, 1.4), hotspot_normal=(0.3, 1, 0))
    engine.box(center=(1.20, 4.85, 1.60), size=(2.00, 0.70, 2.80))
    engine.cyl(center=(-1.40, 5.15, 0.60), radius=0.22, length=1.30, axis="y",
               segments=10)                                    # exhaust

    cwt = b.part(
        "counterweight", "body_yellow",
        parent="superstructure", pivot=SWING,
        label="Counterweight",
        note=("Balances the loaded bucket at full reach. Removing or "
              "under-specifying it is what turns a hard dig into a tipping "
              "incident."),
        hotspot=(0, 2.9, 4.0), hotspot_normal=(0, 0, 1))
    cwt.box(center=(0, 2.80, 3.85), size=(4.80, 1.80, 1.30))
    cwt.box(center=(0, 2.00, 3.95), size=(4.60, 0.40, 1.00))   # dark plinth

    cab = b.part(
        "cab", "body_yellow", parent="superstructure", pivot=SWING,
        label="Operator cab (FOPS)",
        note=("Mounted high on the left front for a clear view into the "
              "bucket. Falling-Object Protective Structure plus a rock "
              "deflector; the operator sits about 5 m up."),
        hotspot=(-2.6, 5.5, -2.30), hotspot_normal=(-1, 0.2, 0))
    cab.box(center=(-1.55, 5.65, -2.30), size=(1.90, 2.30, 2.20))
    cab.box(center=(-1.55, 6.90, -2.30), size=(2.10, 0.20, 2.40))

    glass = b.part(
        "cab_glass", "glass", parent="superstructure", pivot=SWING,
        label="Cab glazing",
        note="Large front and roof windows -- the operator must watch the "
             "bucket teeth, the face above, and the truck being loaded.",
        hotspot=(-1.55, 5.7, -3.45), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(-1.55, 5.75, -3.42), size=(1.60, 1.60, 0.08))
    glass.box(center=(-2.52, 5.75, -2.30), size=(0.08, 1.60, 1.70))
    glass.box(center=(-1.55, 6.78, -2.70), size=(1.60, 0.08, 1.20))

    rails = b.part(
        "walkways_rails", "rail", parent="superstructure", pivot=SWING,
        label="Walkways & handrails",
        note="Service access to pumps, filters and the cooling pack. Isolate "
             "and lock out hydraulics before any work on the upper works.",
        hotspot=(2.4, 4.9, -1.0), hotspot_normal=(1, 0.4, 0))
    for sx in (-1, 1):
        for z in (-2.2, -0.6, 1.0, 2.6):
            rails.cyl(center=(sx * 2.45, 4.95, z), radius=0.05, length=1.00,
                      axis="y", segments=8)
        rails.cyl(center=(sx * 2.45, 5.42, 0.20), radius=0.05, length=5.20,
                  axis="z", segments=8)

    ladder = b.part(
        "access_ladder", "steel", parent="superstructure", pivot=SWING,
        label="Access ladder",
        note="Retractable stairway, raised while digging. The machine must be "
             "shut down and the bucket grounded before anyone climbs.",
        hotspot=(-2.2, 1.6, -3.2), hotspot_normal=(-0.5, 0, -1))
    for sx in (-1, 1):
        ladder.cyl(center=(-1.90 + sx * 0.45, 1.20, -3.20), radius=0.05,
                   length=2.40, axis="y", segments=8)
    for i in range(5):
        ladder.box(center=(-1.90, 0.25 + i * 0.47, -3.20),
                   size=(0.85, 0.06, 0.24))

    # -- front-end attachment ---------------------------------------------
    boom = b.part(
        "boom", "body_yellow", parent="superstructure", pivot=BOOM_FOOT,
        label="Boom",
        note=("Fabricated box-section arm pinned to the house front. On a face "
              "shovel the boom is short and steep -- it is built to resist "
              "crowd forces into a vertical face rather than to reach down."),
        hotspot=(0.9, 5.9, -4.8), hotspot_normal=(0.6, 0.6, 0))
    length, xf = strut(BOOM_FOOT, BOOM_TIP)
    boom.box(center=(0, 0, 0), size=(1.35, 1.55, length), xform=xf)
    boom.cyl(center=BOOM_FOOT, radius=0.45, length=2.20, axis="x", segments=12)
    boom.cyl(center=BOOM_TIP, radius=0.40, length=1.70, axis="x", segments=12)

    stick = b.part(
        "stick", "body_yellow", parent="boom", pivot=BOOM_TIP,
        label="Stick (dipper arm)",
        note=("Carries the bucket and provides the crowd force that drives the "
              "teeth into the face. Stick length trades reach against "
              "breakout force."),
        hotspot=(0.8, 5.6, -8.9), hotspot_normal=(0.6, 0.3, -0.3))
    length, xf = strut(BOOM_TIP, STICK_END)
    stick.box(center=(0, 0, 0), size=(1.10, 1.25, length), xform=xf)
    stick.cyl(center=STICK_END, radius=0.34, length=1.50, axis="x", segments=12)

    bucket = b.part(
        "bucket", "wear", parent="stick", pivot=STICK_END,
        label="Bucket (7.5 m3)",
        note=("Bottom-dump face-shovel bucket: the floor unlatches and swings "
              "open to release the load. Four passes fill a 220 t dumper, so "
              "bucket size must match truck size -- that is the match factor."),
        hotspot=(1.6, 3.0, -9.6), hotspot_normal=(1, 0.2, 0))
    bw = 2.80
    back = [(-0.10, 0.00), (0.25, 0.00), (0.25, 2.30), (-0.10, 2.30)]
    bucket.prism(back, extent=bw, axis="x",
                 offset=(0, BUCKET_CENTRE[1] - 1.15, BUCKET_CENTRE[2] + 0.95))
    floor = [(-1.05, -0.05), (0.30, -0.05), (0.30, 0.28), (-1.05, 0.28)]
    bucket.prism(floor, extent=bw, axis="x",
                 offset=(0, BUCKET_CENTRE[1] - 1.15, BUCKET_CENTRE[2] + 0.70))
    side = [(-1.15, 0.00), (0.30, 0.00), (0.30, 2.30), (-0.60, 2.30)]
    for sx in (-1, 1):
        bucket.prism(side, extent=0.18, axis="x",
                     offset=(sx * (bw / 2 - 0.09), BUCKET_CENTRE[1] - 1.15,
                             BUCKET_CENTRE[2] + 0.70))
    top = [(-0.60, 2.05), (0.25, 2.05), (0.25, 2.30), (-0.60, 2.30)]
    bucket.prism(top, extent=bw, axis="x",
                 offset=(0, BUCKET_CENTRE[1] - 1.15, BUCKET_CENTRE[2] + 0.70))

    teeth = b.part(
        "bucket_teeth", "steel", parent="bucket", pivot=STICK_END,
        label="Teeth & GET",
        note=("Ground Engaging Tools: replaceable tooth adapters, side cutters "
              "and wear plates. Worn teeth raise dig time and fuel burn, and a "
              "tooth lost into the load can wreck a crusher."),
        hotspot=(0, 2.0, -10.6), hotspot_normal=(0, 0.2, -1))
    lip_y = BUCKET_CENTRE[1] - 1.20
    lip_z = BUCKET_CENTRE[2] - 0.35
    teeth.box(center=(0, lip_y + 0.12, lip_z), size=(bw, 0.26, 0.40))
    for i in range(6):
        x = -bw / 2 + 0.28 + i * (bw - 0.56) / 5
        tooth = [(-0.55, 0.10), (0.0, -0.02), (0.0, 0.34), (-0.42, 0.34)]
        teeth.prism(tooth, extent=0.24, axis="x",
                    offset=(x, lip_y, lip_z - 0.02))

    cyls = b.part(
        "hydraulic_cylinders", "chrome",
        parent="superstructure", pivot=SWING,
        label="Hydraulic cylinders",
        note=("Boom-hoist pair, stick cylinder and bucket cylinder, working at "
              "roughly 300-350 bar. Breakout force at the teeth -- not engine "
              "power -- is the shovel's real digging rating."),
        hotspot=(1.5, 4.6, -4.2), hotspot_normal=(1, 0.4, 0))
    for sx in (-1, 1):   # boom hoist
        length, xf = strut((0, 2.55, -1.20), (0, 5.05, -4.70),
                           x_offset=sx * 1.45)
        cyls.cyl(center=(0, 0, 0), radius=0.26, length=length, axis="z",
                 segments=12, xform=xf)
    length, xf = strut((0, 7.15, -5.00), (0, 5.55, -8.45))       # stick
    cyls.cyl(center=(0, 0, 0), radius=0.28, length=length, axis="z",
             segments=12, xform=xf)
    length, xf = strut((0, 6.10, -8.20), (0, 4.35, -9.35))       # bucket
    cyls.cyl(center=(0, 0, 0), radius=0.24, length=length, axis="z",
             segments=12, xform=xf)

    add_scale_figure(b, x=-4.60, z=-4.60)

    return b


SPECS = {
    "id": "shovel",
    "name": "Hydraulic front shovel",
    "subtitle": "140 t class, 7.5 m3 bucket -- CAT 6015 / PC1250 / EX1200 family",
    "category": "Loading",
    "summary": (
        "The loading half of a shovel-dumper system. A face shovel digs into a "
        "blasted vertical face, swings about 90 degrees and bottom-dumps into "
        "a truck. Four to five passes should fill one dumper -- if it takes "
        "more, the pair is mismatched and both machines lose money."),
    "specs": [
        ["Operating weight", "approx. 140 t"],
        ["Bucket capacity", "7.5 m3 (approx. 13-14 t of blasted rock)"],
        ["Engine", "approx. 600-800 kW diesel (electric drive optional)"],
        ["Hydraulic pressure", "approx. 300-350 bar"],
        ["Passes per 220 t truck", "4 to 5"],
        ["Cycle time", "approx. 28-35 s (dig, swing, dump, return)"],
        ["Max digging reach", "approx. 10.5 m at ground level"],
        ["Max digging height", "approx. 12 m -- governs safe face height"],
        ["Track gauge / shoe width", "4.25 m / 750 mm"],
        ["Overall width", "5.0 m over tracks"],
        ["Ground bearing pressure", "approx. 2.2 kg/cm2"],
        ["Productivity", "approx. 800-1000 t/h in good digging"],
    ],
    "safety": [
        "Never approach the machine until the operator has grounded the "
        "bucket and signalled you in -- the swing radius is a no-go zone.",
        "Trucks reverse in on the operator's side so the bucket never swings "
        "over the truck cab.",
        "Face height must stay within the shovel's digging height; overhangs "
        "and loose boulders above the bucket are a fatal hazard.",
        "Hydraulic oil at 300 bar injects through skin -- never search for a "
        "leak with your hand.",
    ],
    "ar_tips": [
        "Place the shovel and the dumper together on open ground to show why "
        "the bucket must clear a 6.1 m loading height.",
        "Walk round to the front: the bucket teeth sit about 10 m from the "
        "machine centre, which is the whole digging envelope in one view.",
    ],
}


def main():
    b = build()
    glb = WEB / "models" / "shovel.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/shovel.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]
    (WEB / "data" / "shovel.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print(f"shovel.glb  {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  "
          f"extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
