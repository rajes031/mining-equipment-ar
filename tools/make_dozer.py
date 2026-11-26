"""
make_dozer.py -- generates a true-scale crawler dozer as GLB.

Reference machine: 65-70 t class crawler dozer with a semi-U blade and a
single-shank ripper -- the Komatsu D375A / CAT D10 / BEML BD355 family. In an
opencast mine it is the machine that builds and maintains everything the
trucks and shovels depend on: benches, ramps, dump edges, shovel floors and
haul-road berms.

Drawn with a conventional oval track (sprocket at track level) rather than an
elevated sprocket, so it stays generic.

Axes: metres, Y up, the dozer faces -Z (blade forward). Origin on the ground
at the centre of the track frames.

Run:  python make_dozer.py
"""

from __future__ import annotations

from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder
from machkit import (about_y, bar, crawler_profile, standard_materials, tube,
                     write_record)

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

TRACK_GAUGE = 2.55          # centre-to-centre of the crawlers
SHOE_WIDTH = 0.61
TRACK_LEN = 4.60            # sprocket to idler, overall
TRACK_TOP = 1.25
BLADE_CENTRE_W = 3.70       # straight centre section of the semi-U blade
WING_W = 0.65               # each angled wing
WING_ANGLE = 25.0           # degrees forward
BLADE_H = 2.20
ARM_X = 1.72                # push arms run outside the tracks

TRUNNION = (0.0, 0.75, -0.60)     # push-arm pivot on the track frame
RIPPER_PIVOT = (0.0, 1.10, 2.40)


def build() -> Builder:
    b = Builder("crawler_dozer_70t")
    standard_materials(b)

    # -- undercarriage ----------------------------------------------------
    half = TRACK_LEN / 2.0
    tracks = b.part(
        "crawler_tracks", "dark",
        label="Crawler tracks",
        note=("610 mm single-grouser shoes. Ground pressure is about "
              "1.4 kg/cm2, which is why a 70 t dozer can work a wet dump "
              "edge a truck could never reach. Undercarriage is roughly half "
              "a dozer's lifetime repair bill -- avoid needless high-speed "
              "reverse and spinning on rock."),
        hotspot=(-TRACK_GAUGE / 2 - 0.4, 0.8, 0.6), hotspot_normal=(-1, 0.2, 0))
    for sx in (-1, 1):
        tracks.prism(crawler_profile(TRACK_LEN, TRACK_TOP, nose=0.50),
                     extent=SHOE_WIDTH, axis="x",
                     offset=(sx * TRACK_GAUGE / 2, 0, 0))

    rollers = b.part(
        "sprockets_idlers", "steel",
        label="Sprocket, idler & rollers",
        note=("Final drive and sprocket at the rear, recoil spring and idler "
              "at the front. Check track sag every shift: too tight and the "
              "bushings wear fast, too loose and the track can come off on a "
              "side slope."),
        hotspot=(TRACK_GAUGE / 2 + 0.4, 0.75, half - 0.5),
        hotspot_normal=(1, 0, 0.3))
    for sx in (-1, 1):
        x = sx * TRACK_GAUGE / 2
        rollers.cyl(center=(x, 0.62, -half + 0.48), radius=0.44,
                    length=SHOE_WIDTH * 1.05, axis="x", segments=14)
        rollers.cyl(center=(x, 0.70, half - 0.50), radius=0.52,
                    length=SHOE_WIDTH * 1.05, axis="x", segments=14)
        for i in range(6):
            rollers.cyl(center=(x, 0.24, -1.45 + i * 0.58), radius=0.19,
                        length=SHOE_WIDTH * 0.9, axis="x", segments=8)
        rollers.cyl(center=(x, 1.10, -0.6), radius=0.12,
                    length=SHOE_WIDTH * 0.7, axis="x", segments=8)
        rollers.cyl(center=(x, 1.10, 0.8), radius=0.12,
                    length=SHOE_WIDTH * 0.7, axis="x", segments=8)

    frame = b.part(
        "main_frame", "body_yellow",
        label="Main frame & fenders",
        note=("Box-section frame carrying the engine, transmission and the "
              "track-frame pivot shaft. The fenders double as walkways -- "
              "three points of contact getting on and off."),
        hotspot=(0.9, 1.45, 1.6), hotspot_normal=(0.4, 1, 0))
    frame.box(center=(0, 1.00, 0.0), size=(1.40, 0.70, 4.40))
    for sx in (-1, 1):
        frame.box(center=(sx * TRACK_GAUGE / 2, 1.33, 0.9),
                  size=(0.85, 0.08, 2.9))

    hood = b.part(
        "engine_hood", "body_yellow",
        label="Engine compartment",
        note=("Diesel of about 450 kW driving a torque converter and "
              "powershift transmission. The torque converter lets the "
              "operator load the blade until the tracks are about to slip, "
              "without stalling the engine."),
        hotspot=(0.9, 2.3, -1.2), hotspot_normal=(1, 0.4, 0))
    hood.box(center=(0, 2.00, -1.00), size=(1.70, 1.40, 2.90))
    hood.box(center=(0, 2.74, -0.70), size=(1.30, 0.08, 2.00))

    grille = b.part(
        "radiator_guard", "dark",
        label="Radiator & front guard",
        note=("Heavy guard over the radiator: the blade throws rock back "
              "towards the machine. A blocked core is the usual cause of "
              "overheating on a dusty bench -- blow it out daily."),
        hotspot=(0, 2.0, -2.65), hotspot_normal=(0, 0.2, -1))
    grille.box(center=(0, 1.95, -2.52), size=(1.76, 1.50, 0.16))

    stack = b.part(
        "exhaust_precleaner", "steel",
        label="Exhaust & air precleaner",
        note=("Intake is taken high and through a cyclone precleaner, away "
              "from the dust the blade raises."),
        hotspot=(0.45, 3.4, -1.6), hotspot_normal=(0.3, 1, 0))
    stack.cyl(center=(0.45, 3.10, -1.60), radius=0.10, length=0.90,
              axis="y", segments=10)
    stack.cyl(center=(-0.45, 3.00, -1.90), radius=0.16, length=0.60,
              axis="y", segments=10)

    cab = b.part(
        "cab_rops", "body_yellow",
        label="Cab with ROPS / FOPS",
        note=("Roll-Over and Falling-Object Protective Structure. It only "
              "works if the operator is wearing the seat belt -- dozers "
              "work on slopes and dump edges, and roll-overs kill unbelted "
              "operators."),
        hotspot=(-1.1, 3.2, 1.2), hotspot_normal=(-1, 0.3, 0))
    cab.box(center=(0, 3.92, 1.20), size=(2.10, 0.12, 1.90))     # roof
    for sx in (-1, 1):
        for z in (0.30, 2.10):
            cab.box(center=(sx * 1.00, 2.65, z), size=(0.12, 2.50, 0.12))
    cab.box(center=(0, 1.55, 1.20), size=(1.95, 0.30, 1.85))      # floor

    glass = b.part(
        "cab_glass", "glass",
        label="Cab glazing",
        note=("The operator watches the blade corners and the ripper tip, "
              "both through glass. Keep it clean; on a dump edge the view of "
              "the crest is the whole job."),
        hotspot=(0, 2.9, 0.25), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(0, 2.80, 0.32), size=(1.80, 2.0, 0.06))
    glass.box(center=(0, 2.80, 2.08), size=(1.80, 2.0, 0.06))
    for sx in (-1, 1):
        glass.box(center=(sx * 0.97, 2.80, 1.20), size=(0.06, 2.0, 1.66))

    tank = b.part(
        "fuel_tank", "body_yellow",
        label="Fuel tank",
        note=("Behind the cab, protected by the ripper frame. Refuel with "
              "the blade and ripper grounded and the engine off."),
        hotspot=(0.95, 1.85, 2.45), hotspot_normal=(1, 0.2, 0.3))
    tank.box(center=(0, 1.85, 2.42), size=(1.80, 1.00, 0.56))

    rails = b.part(
        "handrails", "rail",
        label="Handrails & steps",
        note="Access is up the left side over the track. Never use the "
             "tracks or the blade lift cylinders as a step.",
        hotspot=(-1.8, 2.0, 1.8), hotspot_normal=(-1, 0.3, 0))
    for sx in (-1, 1):
        for z in (0.0, 2.2):
            rails.cyl(center=(sx * 1.62, 1.80, z), radius=0.04, length=0.90,
                      axis="y", segments=6)
        rails.cyl(center=(sx * 1.62, 2.24, 1.1), radius=0.04, length=2.25,
                  axis="z", segments=6)

    # -- blade, hinged at the push-arm trunnions --------------------------
    blade = b.part(
        "blade", "body_yellow", pivot=TRUNNION,
        label="Semi-U blade (approx. 18 m3)",
        note=("Straight centre with angled wings, so it carries a big load "
              "without spilling at the ends, yet still cuts. Productive "
              "pushing distance is short -- beyond about 60-90 m a dozer "
              "loses most of its load and a loader and truck are cheaper."),
        hotspot=(-1.2, 1.6, -4.3), hotspot_normal=(0, 0.3, -1))
    curve = [(-4.30, 0.05), (-4.08, 0.75), (-4.02, 1.50), (-4.22, BLADE_H)]
    t = 0.26
    for (z0, y0), (z1, y1) in zip(curve, curve[1:]):
        slab = [(z0, y0), (z1, y1), (z1 + t, y1), (z0 + t, y0)]
        blade.prism(slab, extent=BLADE_CENTRE_W, axis="x")
        for sx in (-1, 1):
            hinge = (sx * BLADE_CENTRE_W / 2, -4.10)
            blade.prism(slab, extent=WING_W, axis="x",
                        offset=(sx * (BLADE_CENTRE_W + WING_W) / 2, 0, 0),
                        xform=about_y(sx * WING_ANGLE, hinge))
    blade.box(center=(0, 1.15, -3.72), size=(3.40, 1.70, 0.40))   # back box

    edge = b.part(
        "cutting_edge", "wear", parent="blade", pivot=TRUNNION,
        label="Cutting edge & end bits",
        note=("Bolt-on, reversible and replaceable. Run it down to the bolt "
              "holes and you are wearing out the moldboard itself."),
        hotspot=(0.8, 0.14, -4.45), hotspot_normal=(0, 0.2, -1))
    edge.box(center=(0, 0.12, -4.30), size=(BLADE_CENTRE_W, 0.24, 0.14))
    for sx in (-1, 1):
        hinge = (sx * BLADE_CENTRE_W / 2, -4.10)
        edge.box(center=(sx * (BLADE_CENTRE_W + WING_W) / 2, 0.12, -4.30),
                 size=(WING_W, 0.24, 0.14),
                 xform=about_y(sx * WING_ANGLE, hinge))

    arms = b.part(
        "push_arms", "body_yellow", parent="blade", pivot=TRUNNION,
        label="Push arms",
        note=("Transfer the whole tractive effort of the tracks into the "
              "blade. They pivot on trunnions on the track frames, so the "
              "blade rises and falls in an arc."),
        hotspot=(ARM_X + 0.2, 0.8, -2.0), hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        bar(arms, (sx * ARM_X, TRUNNION[1], TRUNNION[2]),
            (sx * ARM_X, 0.60, -3.62), 0.24, 0.40)
        arms.cyl(center=(sx * ARM_X, TRUNNION[1], TRUNNION[2]), radius=0.22,
                 length=0.32, axis="x", segments=10)

    cyl = b.part(
        "hydraulic_cylinders", "chrome",
        label="Lift & tilt cylinders",
        note=("Two lift cylinders raise and lower the blade, a tilt cylinder "
              "drops one corner to cut a ditch or a crossfall. Never work "
              "under a raised blade: lower it to the ground."),
        hotspot=(0.95, 2.1, -3.0), hotspot_normal=(0.6, 0.6, -0.4))
    for sx in (-1, 1):
        tube(cyl, (sx * 0.95, 2.30, -2.40), (sx * 0.95, 1.85, -3.78), 0.11,
             segments=10)
    tube(cyl, (ARM_X, 1.05, -1.25), (1.45, 1.95, -3.75), 0.09, segments=10)

    # -- ripper, hinged at the rear frame ---------------------------------
    ripper = b.part(
        "ripper", "body_yellow", pivot=RIPPER_PIVOT,
        label="Ripper frame",
        note=("Parallelogram linkage that keeps the shank at a constant "
              "angle as it goes down. Ripping lets a dozer loosen soft rock "
              "and coal so it can be pushed or loaded with no blasting."),
        hotspot=(0.9, 1.3, 3.3), hotspot_normal=(1, 0.3, 0.4))
    for sx in (-1, 1):
        bar(ripper, (sx * 0.62, 1.00, 2.35), (sx * 0.62, 0.95, 3.30), 0.16, 0.24)
        bar(ripper, (sx * 0.62, 1.75, 2.40), (sx * 0.62, 1.60, 3.30), 0.16, 0.24)
    ripper.box(center=(0, 1.25, 3.40), size=(1.60, 0.75, 0.34))

    shank = b.part(
        "ripper_shank", "wear", parent="ripper", pivot=RIPPER_PIVOT,
        label="Ripper shank & tip",
        note=("Single shank, penetration up to about 1.5 m. Rip in the "
              "direction the trucks or dozer will push, and lift out before "
              "turning -- turning with the shank in the ground breaks it."),
        hotspot=(0.25, 0.4, 3.6), hotspot_normal=(1, 0, 0.3))
    shank.prism([(3.42, 1.55), (3.74, 1.55), (3.56, 0.26), (3.26, 0.26)],
                extent=0.16, axis="x")
    shank.prism([(3.00, 0.06), (3.44, 0.16), (3.44, 0.40), (3.16, 0.32)],
                extent=0.20, axis="x")

    rcyl = b.part(
        "ripper_cylinders", "chrome",
        label="Ripper cylinders",
        note="Lift and tip cylinders. The tip cylinder rocks the shank to "
             "pry rock loose as the dozer moves forward.",
        hotspot=(0.5, 1.95, 2.8), hotspot_normal=(0.5, 1, 0.2))
    for sx in (-1, 1):
        tube(rcyl, (sx * 0.45, 1.95, 2.10), (sx * 0.45, 1.55, 3.25), 0.09,
             segments=10)

    add_scale_figure(b, x=-3.40, z=-3.00)
    return b


SPECS = {
    "id": "dozer",
    "name": "Crawler dozer",
    "subtitle": "65-70 t class, semi-U blade and ripper -- D375A / D10 / BD355 family",
    "category": "Support equipment",
    "summary": (
        "The machine that makes the mine work. Dozers build and dress "
        "benches, cut ramps, clean up around the shovel, push the dump "
        "edge, and build the berms that stop trucks going over it. They "
        "also rip soft rock and coal that does not need blasting."),
    "specs": [
        ["Operating weight", "approx. 65-70 t with blade and ripper"],
        ["Engine", "approx. 450 kW diesel"],
        ["Blade", "semi-U, approx. 18 m3, approx. 5 m wide x 2.2 m high"],
        ["Ripper", "single shank, penetration up to approx. 1.5 m"],
        ["Track gauge / shoe width", "2.55 m / 610 mm"],
        ["Ground pressure", "approx. 1.4 kg/cm2"],
        ["Overall length", "approx. 8 m with blade and ripper"],
        ["Height to cab roof", "approx. 4.0 m"],
        ["Travel speed", "approx. 0-11 km/h forward, 0-14 km/h reverse"],
        ["Economic push distance", "under about 60-90 m"],
    ],
    "safety": [
        "Dump-edge work: push from a safe distance with a berm in front, "
        "never drive to the crest to look over it.",
        "Seat belt always -- the ROPS only protects a belted operator.",
        "Lower blade and ripper to the ground whenever the dozer is parked "
        "or anyone works on it.",
        "Keep 2-3 machine lengths clear of the shovel and trucks, and get "
        "the shovel operator's acknowledgement before entering its swing.",
    ],
    "ar_tips": [
        "Stand in front of the blade: at 2.2 m high it is taller than you, "
        "and the operator cannot see you from the seat.",
        "Walk to the back to see the ripper tip -- the shank goes into the "
        "ground under where you would be standing.",
    ],
}


def main():
    return write_record(build(), SPECS, WEB, "dozer")


if __name__ == "__main__":
    main()
