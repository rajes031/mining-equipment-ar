"""
make_dumper.py -- generates a true-scale rear-dump truck (dumper) as GLB.

Reference machine: 220 t-payload class rigid rear-dump truck, i.e. the
CAT 793 / Komatsu 830E / BEML BH100 family used in Indian opencast coal and
iron-ore mines. Dimensions below are the published envelope figures for that
class, rounded to the nearest 50 mm. The mesh is a teaching proxy, not an
engineering model: correct envelope, correct part breakdown, simplified shapes.

Axes: metres, Y up, machine nose towards -Z, operator's cab on the left (-X).
Origin on the ground at the machine centre, so ARCore floor placement lands it
standing on its tyres.

Run:  python make_dumper.py
"""

from __future__ import annotations

import math
from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder, compose, rotate, translate

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

LENGTH = 13.10          # overall, canopy to body rear
WIDTH = 7.67            # overall over front tyres
TYRE_R = 1.785          # 40.00R57, 3.57 m overall diameter
TYRE_W = 1.07
RIM_R = 0.95

FRONT_AXLE_Z = -3.60
REAR_AXLE_Z = 2.30      # wheelbase 5.90 m
TYRE_X_OUTER = 3.30     # front tyres and outer rear duals
TYRE_X_INNER = 2.15     # inner rear duals

NOSE_Z = -6.55
TAIL_Z = 6.55
DECK_Y = 4.25           # operator deck walking surface
BODY_FLOOR_FRONT_Y = 4.30
BODY_FLOOR_REAR_Y = 3.70
BODY_HALF_W = 3.50      # 7.0 m wide body
BODY_FRONT_Z = -4.30
BODY_REAR_Z = 6.55
BODY_PIVOT = (0.0, 3.35, 5.00)   # rear hinge the body tips about


def strut(p0, p1, x_offset=0.0):
    """Length and transform for a z-aligned primitive spanning p0 -> p1.

    Both points are given in the x = 0 plane; `x_offset` shifts the finished
    strut sideways. Only an X-rotation is needed because every linkage on this
    machine lies in a vertical fore-aft plane.
    """
    (_, y0, z0), (_, y1, z1) = p0, p1
    dy, dz = y1 - y0, z1 - z0
    length = math.hypot(dy, dz)
    theta = math.degrees(math.atan2(-dy, dz))
    mid = (x_offset, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    return length, compose(translate(*mid), rotate("x", theta))


def build() -> Builder:
    b = Builder("dumper_220t")

    b.material("body_yellow", (0.93, 0.66, 0.05), roughness=0.55, metallic=0.15)
    b.material("tyre", (0.055, 0.055, 0.06), roughness=0.92, metallic=0.0)
    b.material("steel", (0.42, 0.44, 0.47), roughness=0.45, metallic=0.70)
    b.material("dark", (0.14, 0.14, 0.16), roughness=0.65, metallic=0.30)
    b.material("chrome", (0.78, 0.79, 0.82), roughness=0.18, metallic=0.95)
    b.material("glass", (0.42, 0.55, 0.62), roughness=0.08, metallic=0.0,
               alpha=0.42, double_sided=True)
    b.material("rail", (0.95, 0.78, 0.08), roughness=0.5, metallic=0.2)

    # -- chassis ---------------------------------------------------------
    ch = b.part(
        "chassis", "steel",
        label="Main frame / chassis",
        note=("Box-section fabricated steel frame that carries engine, axles "
              "and body. Fatigue life of the frame, not the engine, usually "
              "decides a dumper's economic life."),
        hotspot=(0, 2.15, -1.6), hotspot_normal=(0, -1, 0))
    ch.box(center=(0, 2.05, 0.0), size=(3.60, 1.10, 9.60))      # main rails
    ch.box(center=(0, 1.60, -5.60), size=(5.60, 1.20, 1.20))    # front bumper
    ch.box(center=(0, 2.55, -4.60), size=(4.20, 0.45, 1.00))    # front cross
    ch.box(center=(0, 2.70, 4.70), size=(3.20, 1.30, 1.20))     # rear cross

    # -- running gear ----------------------------------------------------
    susp = b.part(
        "suspension", "dark",
        label="Suspension & front axle",
        note=("Oil-pneumatic (nitrogen over oil) struts. On a 220 t truck each "
              "front strut carries roughly 45 t when loaded; strut pressure is "
              "what payload-monitoring systems actually measure."),
        hotspot=(0, 2.9, -3.6), hotspot_normal=(0, 0, -1))
    susp.box(center=(0, 1.80, FRONT_AXLE_Z), size=(5.50, 0.60, 0.70))
    for sx in (-1, 1):
        susp.cyl(center=(sx * 2.60, 2.85, FRONT_AXLE_Z), radius=0.26,
                 length=1.90, axis="y", segments=12)

    rear = b.part(
        "rear_axle", "dark",
        label="Rear axle & final drives",
        note=("Electric-drive trucks carry an AC/DC wheel motor and two-stage "
              "planetary final drive in each rear hub; mechanical-drive trucks "
              "use a torque converter and powershift transmission instead."),
        hotspot=(0, 2.6, REAR_AXLE_Z), hotspot_normal=(0, 0, 1))
    rear.box(center=(0, 1.79, REAR_AXLE_Z), size=(3.20, 1.30, 1.40))
    for sx in (-1, 1):
        rear.cyl(center=(sx * 1.90, 1.79, REAR_AXLE_Z), radius=0.62,
                 length=0.70, axis="x", segments=14)

    tyre_positions = [
        (-TYRE_X_OUTER, FRONT_AXLE_Z), (TYRE_X_OUTER, FRONT_AXLE_Z),
    ]
    rear_positions = [
        (-TYRE_X_OUTER, REAR_AXLE_Z), (-TYRE_X_INNER, REAR_AXLE_Z),
        (TYRE_X_INNER, REAR_AXLE_Z), (TYRE_X_OUTER, REAR_AXLE_Z),
    ]

    ft = b.part(
        "front_tyres", "tyre",
        label="Front tyres (40.00R57)",
        note=("3.57 m tall, about 4.5 t each, and roughly 5-6% of total "
              "operating cost. Steering axle runs singles; TKPH rating limits "
              "how fast a loaded truck may cycle in hot weather."),
        hotspot=(-TYRE_X_OUTER - 0.1, TYRE_R + 0.9, FRONT_AXLE_Z),
        hotspot_normal=(-1, 0.3, 0))
    for x, z in tyre_positions:
        ft.cyl(center=(x, TYRE_R, z), radius=TYRE_R, length=TYRE_W, axis="x",
               segments=18, inner_radius=RIM_R)

    rt = b.part(
        "rear_tyres", "tyre",
        label="Rear tyres (dual)",
        note=("Four tyres on the drive axle share about 67% of gross weight. "
              "Unequal inflation between a dual pair overloads one tyre and is "
              "a common cause of premature failure."),
        hotspot=(TYRE_X_OUTER + 0.1, TYRE_R + 0.9, REAR_AXLE_Z),
        hotspot_normal=(1, 0.3, 0))
    for x, z in rear_positions:
        rt.cyl(center=(x, TYRE_R, z), radius=TYRE_R, length=TYRE_W, axis="x",
               segments=18, inner_radius=RIM_R)

    rims = b.part(
        "wheel_rims", "steel",
        label="Wheels & rims",
        note="Five-piece lock-ring rims. Never approach a hot or inflating "
             "rim from the side -- always from the tread face.",
        hotspot=(-TYRE_X_OUTER - 0.6, TYRE_R, FRONT_AXLE_Z),
        hotspot_normal=(-1, 0, 0))
    for x, z in tyre_positions + rear_positions:
        rims.cyl(center=(x, TYRE_R, z), radius=RIM_R, length=TYRE_W * 0.98,
                 axis="x", segments=14)

    # -- power train enclosure -------------------------------------------
    hood = b.part(
        "engine_hood", "body_yellow",
        label="Engine enclosure",
        note=("Houses a ~2500 kW (3400 hp) quad-turbo diesel. On diesel-"
              "electric trucks it drives an alternator feeding the wheel "
              "motors; there is no driveshaft to the rear axle."),
        hotspot=(0, 3.8, -4.9), hotspot_normal=(0, 0.4, -1))
    hood.box(center=(0, 2.95, -4.45), size=(3.60, 1.90, 2.70))
    hood.box(center=(0, 3.35, -2.90), size=(3.00, 1.10, 1.40))

    grille = b.part(
        "radiator_grille", "dark",
        label="Radiator & grille",
        note="Rejects roughly as much heat as the engine makes power. Plugged "
             "cores from spillage and dust are a top cause of derating.",
        hotspot=(0, 3.0, -5.9), hotspot_normal=(0, 0, -1))
    grille.box(center=(0, 2.95, -5.82), size=(3.10, 1.70, 0.16))

    tank = b.part(
        "fuel_tank", "steel",
        label="Fuel tank",
        note="Around 4500 litres -- about one 12-hour shift. Fuel burn of "
             "roughly 350-450 l/h dominates operating cost.",
        hotspot=(2.3, 2.4, 0.4), hotspot_normal=(1, 0, 0))
    tank.cyl(center=(2.30, 2.30, 0.40), radius=0.85, length=3.40, axis="z",
             segments=14)

    stacks = b.part(
        "exhaust_stacks", "dark",
        label="Exhaust stacks",
        note="Routed up alongside the body front wall; exhaust heat is also "
             "used to warm the body floor in cold climates to stop sticky "
             "material freezing on.",
        hotspot=(0.9, 5.4, -3.9), hotspot_normal=(0.5, 0.5, -1))
    for sx in (-1, 1):
        stacks.cyl(center=(sx * 0.95, 4.60, -3.95), radius=0.17, length=2.60,
                   axis="y", segments=10)

    # -- operator station ------------------------------------------------
    deck = b.part(
        "operator_deck", "body_yellow",
        label="Operator deck",
        note="Non-slip walkway giving access to the cab and to service "
             "points. Three-point contact on the ladder is mandatory; falls "
             "from dumper decks are a leading injury category.",
        hotspot=(1.9, 4.35, -4.4), hotspot_normal=(0.6, 1, 0))
    deck.box(center=(0, DECK_Y, -4.40), size=(6.00, 0.18, 2.60))
    deck.box(center=(0, 4.05, -4.40), size=(5.40, 0.30, 0.20))

    cab = b.part(
        "cab", "body_yellow",
        label="Operator cab (ROPS/FOPS)",
        note=("Sound-suppressed, pressurised and air-conditioned, certified "
              "as Roll-Over and Falling-Object Protective Structure. Houses "
              "the payload display, retarder control and tyre-pressure "
              "monitor."),
        hotspot=(-2.95, 5.3, -4.70), hotspot_normal=(-1, 0.2, 0))
    cab.box(center=(-1.75, 5.25, -4.70), size=(2.30, 1.90, 2.30))
    cab.box(center=(-1.75, 6.25, -4.70), size=(2.52, 0.10, 2.52))   # ROPS roof

    glass = b.part(
        "cab_glass", "glass",
        label="Cab glazing",
        note="Laminated screens plus mirrors and cameras. Even so, a loaded "
             "dumper has large blind areas -- light vehicles must keep a safe "
             "distance and make positive radio contact.",
        hotspot=(-1.75, 5.5, -5.9), hotspot_normal=(0, 0.2, -1))
    glass.box(center=(-1.75, 5.45, -5.87), size=(2.00, 1.15, 0.08))
    glass.box(center=(-2.92, 5.45, -4.70), size=(0.08, 1.15, 1.70))
    glass.box(center=(-0.58, 5.45, -4.70), size=(0.08, 1.15, 1.70))

    rails = b.part(
        "handrails", "rail",
        label="Handrails & walkways",
        note="Yellow handrails mark every legitimate access route. Climbing "
             "anywhere else on a 6 m tall machine is prohibited.",
        hotspot=(2.9, 5.1, -4.4), hotspot_normal=(1, 0.4, 0))
    for z in (-5.60, -4.40, -3.20):
        rails.cyl(center=(2.85, 4.85, z), radius=0.05, length=1.20, axis="y",
                  segments=8)
    rails.cyl(center=(2.85, 5.45, -4.40), radius=0.05, length=2.50, axis="z",
              segments=8)
    rails.cyl(center=(2.85, 4.95, -4.40), radius=0.04, length=2.50, axis="z",
              segments=8)

    ladder = b.part(
        "access_ladder", "steel",
        label="Access ladder",
        note="Inclined stairway from ground to deck, often with a powered "
             "lower flight. Face the steps and keep three-point contact.",
        hotspot=(-1.0, 2.6, -6.3), hotspot_normal=(0, 0, -1))
    for sx in (-1, 1):
        ladder.cyl(center=(-1.00 + sx * 0.55, 2.55, -6.05), radius=0.055,
                   length=3.80, axis="y", segments=8)
    for i in range(8):
        y = 0.85 + i * 0.47
        ladder.box(center=(-1.00, y, -6.05 - 0.02 * i), size=(1.00, 0.06, 0.26))

    # -- dump body -------------------------------------------------------
    body = b.part(
        "dump_body", "body_yellow", pivot=BODY_PIVOT,
        label="Dump body (tray)",
        note=("Abrasion-resistant steel body of roughly 130 m3 struck / 170 m3 "
              "heaped (2:1). Body choice is a trade-off: a lighter body hauls "
              "more payload, a thicker one survives blocky blasted rock."),
        hotspot=(-3.6, 5.6, 1.2), hotspot_normal=(-1, 0.3, 0))
    floor = [(BODY_FRONT_Z, BODY_FLOOR_FRONT_Y),
             (BODY_REAR_Z, BODY_FLOOR_REAR_Y),
             (BODY_REAR_Z, BODY_FLOOR_REAR_Y - 0.28),
             (BODY_FRONT_Z, BODY_FLOOR_FRONT_Y - 0.28)]
    body.prism(floor, extent=BODY_HALF_W * 2, axis="x")
    side = [(BODY_FRONT_Z, BODY_FLOOR_FRONT_Y),
            (BODY_REAR_Z, BODY_FLOOR_REAR_Y),
            (BODY_REAR_Z, 5.30),
            (BODY_FRONT_Z, 6.30)]
    for sx in (-1, 1):
        body.prism(side, extent=0.16, axis="x",
                   offset=(sx * (BODY_HALF_W - 0.08), 0, 0))
    front_wall = [(BODY_FRONT_Z, BODY_FLOOR_FRONT_Y - 0.28),
                  (BODY_FRONT_Z + 0.26, BODY_FLOOR_FRONT_Y - 0.28),
                  (BODY_FRONT_Z + 0.26, 6.30),
                  (BODY_FRONT_Z, 6.30)]
    body.prism(front_wall, extent=BODY_HALF_W * 2, axis="x")
    # longitudinal stiffeners under the floor
    for sx in (-1, 0, 1):
        body.box(center=(sx * 2.10, 3.80, 1.10), size=(0.22, 0.45, 9.60))

    canopy = b.part(
        "body_canopy", "body_yellow",
        parent="dump_body", pivot=BODY_PIVOT,
        label="Body canopy (rock guard)",
        note="Forward extension of the body over the cab. It protects the "
             "operator while loading -- which is why a shovel never swings a "
             "bucket over the cab side of the truck.",
        hotspot=(0, 6.7, -5.3), hotspot_normal=(0, 1, -0.3))
    canopy.box(center=(0, 6.45, -5.30), size=(BODY_HALF_W * 2, 0.22, 2.70))
    canopy.box(center=(0, 6.26, -6.52), size=(BODY_HALF_W * 2, 0.30, 0.22))

    hoist = b.part(
        "hoist_cylinders", "chrome",
        label="Hoist cylinders",
        note=("Twin three-stage cylinders tip the body to about 45 degrees in "
              "12-15 seconds. Never tip on a side slope and never travel with "
              "the body raised -- it is the classic dumper overturn."),
        hotspot=(1.4, 3.3, -0.4), hotspot_normal=(1, 0.3, 0))
    for sx in (-1, 1):
        length, xf = strut((0, 2.55, -1.90), (0, 3.95, 1.30), x_offset=sx * 1.30)
        hoist.cyl(center=(0, 0, 0), radius=0.23, length=length, axis="z",
                  segments=12, xform=xf)
        length, xf = strut((0, 2.40, -2.05), (0, 2.85, -1.00), x_offset=sx * 1.30)
        hoist.cyl(center=(0, 0, 0), radius=0.33, length=length, axis="z",
                  segments=12, xform=xf)

    pivot = b.part(
        "body_pivot", "dark",
        label="Body pivot pins",
        note="The body hinges on these rear pins. Lubrication here is a "
             "daily-check item; a seized pin tears the body mounting.",
        hotspot=(0, 3.3, 5.2), hotspot_normal=(0, -0.4, 1))
    pivot.cyl(center=BODY_PIVOT, radius=0.30, length=7.00, axis="x",
              segments=12)

    add_scale_figure(b, x=-5.40, z=-5.20)

    return b


SPECS = {
    "id": "dumper",
    "name": "Rear-dump truck -- schematic",
    "subtitle": "220 t class, simplified geometry, 20 labelled parts -- CAT 793 / Komatsu 830E family",
    "category": "Haulage",
    "summary": (
        "The haulage half of a shovel-dumper system. A rigid-frame rear-dump "
        "truck takes a loaded bucket from the shovel and hauls it to the "
        "crusher, stockpile or dump. Match factor -- shovel passes per truck "
        "against truck cycle time -- is what keeps both machines busy."),
    "specs": [
        ["Nominal payload", "220 t (approx. 136 m3 of broken rock)"],
        ["Gross operating weight", "approx. 385 t loaded"],
        ["Engine", "approx. 2500 kW (3400 hp) diesel"],
        ["Drive", "Diesel-electric (AC/DC wheel motors) or mechanical"],
        ["Body capacity", "approx. 130 m3 struck / 170 m3 heaped (2:1)"],
        ["Overall length", "13.1 m"],
        ["Overall width", "7.67 m"],
        ["Height, body down", "6.5 m (approx. 13 m with body raised)"],
        ["Loading height", "6.1 m -- sets the minimum shovel dump height"],
        ["Tyres", "6 x 40.00R57, 3.57 m diameter"],
        ["Top speed", "approx. 55 km/h empty on a level haul road"],
        ["Turning circle", "approx. 30 m -- governs dump-point layout"],
    ],
    "safety": [
        "Blind spots are large: never park a light vehicle within one truck "
        "length, and always make positive radio contact before approaching.",
        "Never travel with the body raised, and never tip across a slope.",
        "Haul-road berms must be at least axle-height of the largest truck.",
        "Wheel-chock and isolate before any work on tyres or hydraulics.",
    ],
    "ar_tips": [
        "Place it on open ground: the model is 13 m long and needs about 20 m "
        "of clear floor to walk around at 1:1.",
        "Use the 1:1 scale button, then stand next to a tyre -- the tyre is "
        "taller than two people. That is the lesson students remember.",
    ],
}


def main():
    b = build()
    glb = WEB / "models" / "dumper.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/dumper.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]

    import json
    (WEB / "data" / "dumper.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print(f"dumper.glb  {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  "
          f"extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
