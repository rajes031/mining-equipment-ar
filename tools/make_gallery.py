"""
make_gallery.py -- a bolted development gallery you can walk through at 1:1.

A 4.8 m by 3.0 m bord-and-pillar roadway, 14 m of it, supported by a pattern
of resin-grouted roof bolts with straps and mesh. The roof strata above are
drawn semi-transparent so the bolts are visible inside the rock they are
anchored into -- which is the whole point, because the part of roof support
that matters is the part nobody can see.

Why it works in AR where most underground scenes do not: a gallery is an
object you place on the floor and step into, not an environment that has to
replace the room you are standing in. Both ends are open, so you walk in one
and out of the other.

Construction note: the rock is built as slabs around the void rather than cut
out of a solid, because the generator has no boolean operations. That turns
out to be the right way anyway -- each slab's tunnel-facing surface is the
outward face of that slab, so the normals come out correct with no special
handling, and the open ends let you see in from outside too.

Axes: metres, Y up. The gallery runs along Z; drive in at z = 0.
Origin on the floor at the centre of the roadway.

Run:  python make_gallery.py
"""

from __future__ import annotations

import json
from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ---------------------------------------------------------------- envelope

WIDTH = 4.8                 # roadway width, a common statutory maximum
HEIGHT = 3.0                # roadway height
LENGTH = 14.0               # how much of it is modelled
HALF_W = WIDTH / 2.0

RIB_T = 2.0                 # thickness of coal shown either side
ROOF_T = 2.2                # thickness of roof strata shown above
FLOOR_T = 0.06

BOLT_LEN = 1.8
BOLT_R = 0.011              # 22 mm bar
BOLT_XS = [-1.8, -0.6, 0.6, 1.8]        # 1.2 m across the roadway
BOLT_ROW_PITCH = 1.2
PLATE = 0.20

RIB_BOLT_LEN = 1.5
RIB_BOLT_YS = [1.40, 2.35]
RIB_ROW_PITCH = 2.0

MESH_PITCH = 0.75
BEDDING_YS = [HEIGHT + 0.65, HEIGHT + 1.35, HEIGHT + 2.00]


def bolt_rows():
    z = BOLT_ROW_PITCH
    while z < LENGTH:
        yield z
        z += BOLT_ROW_PITCH


SPECS = {
    "id": "gallery",
    "name": "Bolted gallery (development roadway)",
    "category": "Underground",
    "subtitle": "4.8 m × 3.0 m roadway, 1.2 m bolt pattern — walk through it",
    "summary":
        "A development heading in a bord-and-pillar mine, supported by "
        "resin-grouted roof bolts on a 1.2 m square pattern with W-straps and "
        "mesh. Bolting does not prop the roof up from below; it binds the "
        "laminated strata above into a single thicker beam that can carry "
        "itself across the roadway. That is why the bolts are drawn here "
        "inside semi-transparent rock — what the support actually does "
        "happens entirely out of sight, above the roof line, and a bolt "
        "pattern you only see from below is a pattern you cannot reason "
        "about. Both ends are open: place it and walk through.",
    "specs": [
        ["Roadway width", "4.8 m"],
        ["Roadway height", "3.0 m"],
        ["Length modelled", "14 m"],
        ["Roof bolts", "22 mm bar, 1.8 m long, full-column resin grouted"],
        ["Bolt pattern", "1.2 m × 1.2 m — 4 bolts per row"],
        ["Bolt density", "about 0.69 bolts per m² of roof"],
        ["Anchorage", "Resin capsules, full encapsulation"],
        ["Surface support", "W-straps on each row, weldmesh between"],
        ["Rib bolts", "1.5 m, two per side per row at 2 m centres"],
        ["Typical bolt capacity", "approx. 12–15 t yield per bolt"],
    ],
    "safety": [
        "Never go under unsupported roof. The last row of bolts is the limit "
        "of supported ground, and the temptation to step one metre past it "
        "to look at something is how people are killed.",
        "The roof is tested before anyone works under it — sound it, look for "
        "fresh spalling, and check for bed separation. A drummy sound means "
        "a parting has opened above the bolt horizon.",
        "Bolt length has to exceed the thickness of the laminated beam it is "
        "binding. A 1.8 m bolt in strata that separates at 2.5 m anchors "
        "nothing and gives false confidence.",
        "Report and re-support any bolt with a loose plate, a sheared head or "
        "visible rust staining at the collar. The plate is the only part you "
        "can inspect; it is also the first part to tell you something moved.",
        "Ribs fail as often as roofs in coal. Rib bolts and mesh are not "
        "optional in a 3 m heading.",
    ],
    "ar_tips": [
        "Place it in a corridor or a hall about 16 m long and walk straight "
        "through. The roadway is 3.0 m high, so there is plenty of headroom "
        "— and realising that a 'low' coal roadway is still well above you "
        "is part of the lesson.",
        "Stop in the middle and look up. Fade everything except the bolts and "
        "you are left looking at the only thing holding the roof together.",
        "Pace the 1.2 m between bolt rows. That spacing is a design decision "
        "made from rock-mass rating, not a convention.",
    ],
}


def build():
    b = Builder("gallery")
    b.material("coal", (0.09, 0.085, 0.085), roughness=0.92, metallic=0.0)
    b.material("floor_rock", (0.36, 0.34, 0.31), roughness=0.95, metallic=0.0)
    # Semi-transparent and double-sided: you look up through the roof from
    # inside the roadway and at the bolts through it from outside.
    b.material("roof_rock", (0.52, 0.49, 0.44), roughness=0.9, metallic=0.0,
               alpha=0.30, double_sided=True)
    b.material("bedding", (0.30, 0.27, 0.24), roughness=0.9, metallic=0.0,
               alpha=0.55, double_sided=True)
    b.material("bolt_steel", (0.66, 0.67, 0.70), roughness=0.35, metallic=0.85)
    b.material("strap_steel", (0.52, 0.53, 0.56), roughness=0.45, metallic=0.75)
    b.material("mesh_steel", (0.46, 0.47, 0.50), roughness=0.55, metallic=0.6)

    mid_z = LENGTH / 2.0

    # -- the excavation -----------------------------------------------------
    floor = b.part(
        "gallery_floor", "floor_rock",
        label="Floor",
        note="Often the weakest horizon in a coal roadway and the one nobody "
             "supports. Floor heave squeezes the roadway closed from below, "
             "and in a wet seam it turns a 3 m heading into a 2.5 m one over "
             "a few months.",
        hotspot=(0.0, FLOOR_T, mid_z), hotspot_normal=(0, 1, 0))
    floor.box(center=(0.0, FLOOR_T / 2, mid_z),
              size=(WIDTH + 2 * RIB_T, FLOOR_T, LENGTH))

    ribs = b.part(
        "coal_ribs", "coal",
        label="Coal ribs (sides)",
        note="The solid coal either side. In bord-and-pillar these are the "
             "pillars that carry the overburden, so what is left standing is "
             "a mine-design decision, not a local one — pillar size comes "
             "from depth, seam height and the extraction ratio you are "
             "willing to accept.",
        hotspot=(HALF_W, 1.6, mid_z), hotspot_normal=(-1, 0, 0))
    for sx in (-1, 1):
        ribs.box(center=(sx * (HALF_W + RIB_T / 2), HEIGHT / 2, mid_z),
                 size=(RIB_T, HEIGHT, LENGTH))

    roof = b.part(
        "roof_strata", "roof_rock",
        label="Roof strata",
        note="The rock above the roadway, drawn transparent so the bolts "
             "inside it are visible. Immediate roof in Indian coal measures "
             "is usually laminated shale or sandy shale — strong enough in a "
             "thick bed, weak across the partings between beds. Unbolted, "
             "each thin lamination has to span the full 4.8 m on its own and "
             "sags away from the one above it.",
        hotspot=(0.0, HEIGHT + ROOF_T, mid_z), hotspot_normal=(0, 1, 0))
    roof.box(center=(0.0, HEIGHT + ROOF_T / 2, mid_z),
             size=(WIDTH + 2 * RIB_T, ROOF_T, LENGTH))

    beds = b.part(
        "bedding_planes", "bedding",
        label="Bedding planes",
        note="The partings the whole support problem turns on. Laminated "
             "strata slip and separate along these surfaces; bolts clamp the "
             "laminations together so that several thin beams act as one "
             "thick one, and a thick beam deflects far less than the same "
             "thickness of loose leaves. This is why bolt length is chosen "
             "against where the separation is expected, not against the "
             "roadway width.",
        hotspot=(0.0, BEDDING_YS[1], 1.0), hotspot_normal=(0, 0, -1))
    for y in BEDDING_YS:
        beds.box(center=(0.0, y, mid_z),
                 size=(WIDTH + 2 * RIB_T, 0.05, LENGTH))

    # -- support ------------------------------------------------------------
    bolts = b.part(
        "roof_bolts", "bolt_steel",
        label="Roof bolts (22 mm × 1.8 m, resin grouted)",
        note="Full-column resin anchorage: a resin capsule is pushed to the "
             "back of the hole and the bar spun through it, so the bar is "
             "bonded to the rock along its whole length rather than gripped "
             "only at the far end. That makes the bolt stiff — it picks up "
             "load after a fraction of a millimetre of bed separation, which "
             "is what stops the separation rather than merely surviving it.",
        hotspot=(0.6, HEIGHT + BOLT_LEN, 2.4), hotspot_normal=(0, 1, 0))
    for z in bolt_rows():
        for x in BOLT_XS:
            bolts.cyl(center=(x, HEIGHT + BOLT_LEN / 2, z), radius=BOLT_R,
                      length=BOLT_LEN, axis="y", segments=8)
            bolts.box(center=(x, HEIGHT - 0.015, z),
                      size=(PLATE, 0.03, PLATE))

    straps = b.part(
        "w_straps", "strap_steel",
        label="W-straps",
        note="A pressed steel channel run across the roadway under each row "
             "of bolt plates. It spreads what each bolt holds over the whole "
             "row, so the roof between two bolts cannot sag down past them. "
             "Cheap, and it does more for surface control than adding bolts.",
        hotspot=(0.0, HEIGHT - 0.10, BOLT_ROW_PITCH * 2), hotspot_normal=(0, -1, 0))
    for z in bolt_rows():
        straps.box(center=(0.0, HEIGHT - 0.055, z), size=(4.2, 0.05, 0.14))

    mesh = b.part(
        "weldmesh", "mesh_steel",
        label="Weldmesh",
        note="Holds the small stuff. Bolts and straps keep the roof beam "
             "together, but neither stops a fist-sized piece of shale "
             "dropping out between them, and that is what actually injures "
             "people day to day. Mesh is the difference between a bruise and "
             "a fatality.",
        hotspot=(-1.8, HEIGHT - 0.14, mid_z), hotspot_normal=(0, -1, 0))
    n_long = int(WIDTH / MESH_PITCH)
    for i in range(n_long + 1):
        x = -HALF_W + i * MESH_PITCH
        mesh.box(center=(x, HEIGHT - 0.12, mid_z), size=(0.012, 0.012, LENGTH))
    n_cross = int(LENGTH / MESH_PITCH)
    for i in range(n_cross + 1):
        z = i * MESH_PITCH
        mesh.box(center=(0.0, HEIGHT - 0.13, z), size=(WIDTH, 0.012, 0.012))

    rib_bolts = b.part(
        "rib_bolts", "bolt_steel",
        label="Rib bolts",
        note="Shorter bolts into the sides. In a 3 m heading the ribs are as "
             "tall as a person and coal spalls off them as the pillar takes "
             "load; an unbolted rib in a stressed pillar sheds slabs without "
             "warning. They are often fibreglass rather than steel so a "
             "future cut through the pillar does not have to chew steel.",
        hotspot=(-HALF_W, RIB_BOLT_YS[1], 4.0), hotspot_normal=(1, 0, 0))
    z = RIB_ROW_PITCH / 2
    while z < LENGTH:
        for sx in (-1, 1):
            for y in RIB_BOLT_YS:
                rib_bolts.cyl(
                    center=(sx * (HALF_W + RIB_BOLT_LEN / 2), y, z),
                    radius=BOLT_R, length=RIB_BOLT_LEN, axis="x", segments=8)
                rib_bolts.box(center=(sx * (HALF_W - 0.015), y, z),
                              size=(0.03, PLATE, PLATE))
        z += RIB_ROW_PITCH

    add_scale_figure(b, x=-1.1, z=mid_z + 1.5, facing_deg=0.0)
    return b


def main():
    b = build()
    glb = WEB / "models" / "gallery.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/gallery.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]
    (WEB / "data" / "gallery.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print(f"gallery.glb       {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
