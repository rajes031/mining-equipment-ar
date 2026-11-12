"""
make_blast_pattern.py -- a production blasthole pattern laid out at true scale.

This is the one model in the set that is not a machine. It is a piece of
ground: a bench top with a staggered three-row pattern drilled into it, the
crest in front, and one hole laid out on its side so you can see what is
inside it.

Why it exists: burden and spacing are the most quantitative things in opencast
mining and students only ever meet them as numbers. 5.5 m written on a slide
means nothing. 5.5 m paced out between two collars, with the crest one burden
in front of you, is a measurement you remember.

Design shown -- a 165 mm hole in coal overburden:
    bench height  10.0 m          burden      5.5 m
    subgrade       1.5 m          spacing     6.5 m
    hole depth    11.5 m          stemming    5.0 m
    charge column  6.5 m          about 160 kg of emulsion per hole
    volume per hole 357 m3        powder factor about 0.45 kg/m3

Axes: metres, Y up. The free face is at -Z, so the crest runs along X at
z = 0 and the pattern lies behind it in +Z -- a student standing on the
pattern faces -Z and looks out over the drop.

Everything sits on or above y = 0. That matters: model-viewer puts a model's
lowest point on the detected floor, so geometry hanging below the bench top
would lift the whole pattern into the air instead of burying it. Hence the
laid-out section hole rather than holes you look down into.

Run:  python make_blast_pattern.py
"""

from __future__ import annotations

import json
from pathlib import Path

from figure import add_scale_figure
from glbgen import Builder

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ------------------------------------------------------------ blast design

HOLE_DIA = 0.165
BURDEN = 5.5
SPACING = 6.5
BENCH_H = 10.0
SUBGRADE = 1.5
HOLE_DEPTH = BENCH_H + SUBGRADE        # 11.5
STEMMING = 5.0
CHARGE = HOLE_DEPTH - STEMMING         # 6.5

GROUND = 0.06                          # top of the thin bench-floor pad

# Staggered: four-hole rows alternating with three-hole rows, which is what
# gives each hole in the back row a free face between the two in front of it.
ROWS = [
    (BURDEN * 1.0, [-SPACING, 0.0, SPACING]),
    (BURDEN * 2.0, [-SPACING / 2, SPACING / 2]),
    (BURDEN * 3.0, [-SPACING, 0.0, SPACING]),
]

PAD_X0, PAD_X1 = -8.0, 11.6
PAD_Z0, PAD_Z1 = -0.8, 17.2

SECT_X = 10.4                          # laid-out hole, running along Z
SECT_Z0 = 4.0
SECT_R = 0.22                          # drawn oversize; see the part note


SPECS = {
    "id": "blast-pattern",
    "name": "Blasthole pattern (bench blast)",
    "category": "Drilling & blasting",
    "subtitle": "165 mm holes, 5.5 m burden × 6.5 m spacing, 10 m bench",
    "summary":
        "A production bench blast, staggered in three rows, set out at full "
        "size on the ground. Burden is the distance from a hole to the "
        "nearest free face; spacing is the distance between holes along a "
        "row. Those two numbers, with hole diameter and bench height, decide "
        "fragmentation, throw, ground vibration and flyrock — and they are "
        "the numbers a blast designer actually chooses. Walk between the "
        "collars and the geometry stops being arithmetic. One hole is laid "
        "out on its side at the edge of the pattern so the charge column, "
        "the stemming and the subgrade drilling are visible.",
    "specs": [
        ["Hole diameter", "165 mm"],
        ["Bench height", "10.0 m"],
        ["Burden", "5.5 m (about 33 × hole diameter)"],
        ["Spacing", "6.5 m (1.18 × burden, staggered)"],
        ["Subgrade drilling", "1.5 m below floor level"],
        ["Total hole depth", "11.5 m"],
        ["Stemming", "5.0 m (about 0.9 × burden)"],
        ["Charge column", "6.5 m, site-mixed emulsion"],
        ["Charge per hole", "approx. 160 kg"],
        ["Rock broken per hole", "357 m³ (5.5 × 6.5 × 10)"],
        ["Powder factor", "approx. 0.45 kg/m³"],
        ["Initiation", "Row-to-row surface delays, firing towards the face"],
    ],
    "safety": [
        "Stemming is not spoil. Too little, or the wrong material, and the "
        "charge vents up the hole — that is where flyrock and airblast come "
        "from, not from the burden.",
        "The front-row burden is measured to the real face, not to the "
        "designed crest. A face that has sloughed leaves an under-burdened "
        "hole, and an under-burdened hole throws rock.",
        "Never drill or charge within the danger zone of a hole already "
        "primed, and never re-drill a socket or a misfired hole.",
        "Keep clear of the crest. Drilling close to an unsupported edge is "
        "how rigs go over the face; the berm is there to stop that.",
        "Ground vibration is controlled by the maximum charge per delay, not "
        "by the total charge. That is why delays exist.",
    ],
    "ar_tips": [
        "This needs real space: about 20 m by 18 m, so a car park or a "
        "playing field, not a classroom.",
        "Stand on a collar in the front row and pace the 5.5 m to the crest. "
        "That single walk teaches burden better than any diagram.",
        "Walk the length of the laid-out hole — 11.5 m — and you understand "
        "why a drill rig needs a mast that tall.",
        "No room outdoors? Print a marker and view the same pattern at 1:50 "
        "on a desk.",
    ],
}


def build():
    b = Builder("blast_pattern")
    b.material("rock", (0.42, 0.40, 0.37), roughness=0.95, metallic=0.0)
    b.material("berm_rock", (0.47, 0.42, 0.35), roughness=0.95, metallic=0.0)
    b.material("hazard", (0.95, 0.78, 0.08), roughness=0.6, metallic=0.0)
    b.material("hole_dark", (0.12, 0.12, 0.13), roughness=0.85, metallic=0.0)
    b.material("burden_blue", (0.08, 0.48, 0.80), roughness=0.5, metallic=0.0)
    b.material("spacing_green", (0.11, 0.60, 0.30), roughness=0.5, metallic=0.0)
    b.material("initiation_orange", (0.92, 0.36, 0.04), roughness=0.5, metallic=0.0)
    b.material("stemming_sand", (0.80, 0.68, 0.44), roughness=0.9, metallic=0.0)
    b.material("explosive_red", (0.78, 0.20, 0.09), roughness=0.7, metallic=0.0)
    b.material("subgrade_grey", (0.33, 0.32, 0.32), roughness=0.85, metallic=0.0)

    # -- the bench top ------------------------------------------------------
    floor = b.part(
        "bench_floor", "rock",
        label="Bench top",
        note="The working surface the rig stands on and the holes are "
             "collared from. Bench height is fixed by the machines that have "
             "to work it — the shovel has to be able to dig the muckpile and "
             "the drill has to reach the depth — so it is a planning "
             "decision long before it is a blasting one.",
        hotspot=(-6.0, GROUND, 14.0), hotspot_normal=(0, 1, 0))
    floor.box(center=((PAD_X0 + PAD_X1) / 2, GROUND / 2, (PAD_Z0 + PAD_Z1) / 2),
              size=(PAD_X1 - PAD_X0, GROUND, PAD_Z1 - PAD_Z0))

    berm = b.part(
        "crest_berm", "berm_rock",
        label="Crest and safety berm",
        note="The edge of the bench, and the windrow along it. A berm has to "
             "be at least axle height of the largest machine on the bench — "
             "it is not a marker, it is a physical stop. Everything in front "
             "of this line is a 10 m drop.",
        hotspot=(0.0, 0.95, -0.45), hotspot_normal=(0, 0.5, -1))
    # The crest runs along X, so the windrow's cross-section is in (z, y) and
    # it is extruded along X -- axis="x" maps u to z and v to y.
    berm.prism([(-0.75, GROUND), (0.75, GROUND), (0.35, 0.90), (-0.35, 0.90)],
               extent=18.0, axis="x", offset=(0.0, 0.0, 0.0))

    hazard = b.part(
        "free_face_line", "hazard",
        label="Free face (the crest line)",
        note="Burden is measured from a hole to the nearest free face, and "
             "for the front row that face is this edge. It is the only "
             "direction the rock can move, which is why the whole pattern is "
             "timed to break towards it. Take the free face away and the "
             "same charge in the same hole will crater upwards instead.",
        hotspot=(6.0, 0.10, 0.0), hotspot_normal=(0, 1, -0.3))
    for sx in (-1, 1):
        hazard.box(center=(sx * 4.5, GROUND + 0.02, 0.95),
                   size=(8.4, 0.05, 0.22))

    # -- the holes ----------------------------------------------------------
    collars = b.part(
        "blasthole_collars", "hole_dark",
        label="Blasthole collars (165 mm)",
        note="Eleven holes in three staggered rows. The holes themselves are "
             "drawn at their true 165 mm; the pale ring round each one is the "
             "collar of drill cuttings, which is what you actually see when "
             "you walk a drilled pattern. Staggering the rows gives every "
             "hole in the back rows a free face opening between the two in "
             "front of it.",
        hotspot=(0.0, 0.25, BURDEN), hotspot_normal=(0, 1, 0))
    for z, xs in ROWS:
        for x in xs:
            collars.cyl(center=(x, GROUND + 0.025, z), radius=0.25,
                        length=0.05, axis="y", segments=16)
            collars.cyl(center=(x, GROUND + 0.09, z), radius=HOLE_DIA / 2,
                        length=0.16, axis="y", segments=12)

    # -- dimension markers --------------------------------------------------
    burden_m = b.part(
        "burden_marker", "burden_blue",
        label="Burden — 5.5 m",
        note="The distance from a hole to the nearest free face, measured "
             "perpendicular to it. Burden is the single most powerful number "
             "in the design: too large and the charge cannot break out, so it "
             "vents up the hole and leaves toe; too small and it throws rock "
             "a long way. A useful first guess is 25 to 35 times the hole "
             "diameter, which for 165 mm gives roughly 4 to 6 m.",
        hotspot=(-SPACING, 0.30, BURDEN / 2), hotspot_normal=(0, 1, 0))
    # Chunky on purpose: these two bars are the lesson, and a thin strip on
    # the ground disappears when you are standing on it looking along it.
    burden_m.box(center=(-SPACING, GROUND + 0.08, BURDEN / 2),
                 size=(0.30, 0.16, BURDEN))
    for zz in (0.0, BURDEN):
        burden_m.box(center=(-SPACING, GROUND + 0.28, zz), size=(0.80, 0.56, 0.16))

    spacing_m = b.part(
        "spacing_marker", "spacing_green",
        label="Spacing — 6.5 m",
        note="The distance between neighbouring holes along a row. Spacing is "
             "normally 1.1 to 1.3 times the burden; much wider and the cracks "
             "between adjacent holes never link up, leaving coarse blocks on "
             "the row line. Burden and spacing together set the volume each "
             "hole has to break, and so the powder factor.",
        hotspot=(SPACING / 2, 0.30, BURDEN), hotspot_normal=(0, 1, 0))
    spacing_m.box(center=(SPACING / 2, GROUND + 0.08, BURDEN),
                  size=(SPACING, 0.16, 0.30))
    for xx in (0.0, SPACING):
        spacing_m.box(center=(xx, GROUND + 0.28, BURDEN), size=(0.16, 0.56, 0.80))

    # -- initiation ---------------------------------------------------------
    init = b.part(
        "initiation_sequence", "initiation_orange",
        label="Surface delays and firing direction",
        note="The holes do not go off together. Surface delays fire them hole "
             "by hole and row by row, towards the free face, so each hole has "
             "somewhere to break into by the time its turn comes. Delays also "
             "control vibration: what a seismograph responds to is the "
             "maximum charge on any single delay, not the total in the blast. "
             "The arrows show the direction the blast runs.",
        hotspot=(-SPACING, 0.30, BURDEN * 3), hotspot_normal=(0, 1, 0))
    for z, xs in ROWS:                       # trunkline along each row
        init.box(center=((min(xs) + max(xs)) / 2, GROUND + 0.03, z),
                 size=(max(xs) - min(xs), 0.05, 0.10))
    for z0, z1 in ((ROWS[2][0], ROWS[1][0]), (ROWS[1][0], ROWS[0][0])):
        init.box(center=(-SPACING + 0.4, GROUND + 0.03, (z0 + z1) / 2),
                 size=(0.10, 0.05, abs(z1 - z0)))
    for z, xs in ROWS:                       # a chevron per hole, facing out
        for x in xs:
            init.prism([(-0.55, 0.0), (0.0, -0.95), (0.55, 0.0), (0.0, -0.45)],
                       extent=0.07, axis="y",
                       offset=(x, GROUND + 0.035, z - 0.75))

    # -- the hole laid out on its side -------------------------------------
    stem = b.part(
        "stemming_zone", "stemming_sand",
        label="Stemming — top 5.0 m",
        note="Crushed angular aggregate rammed into the top of the hole. Its "
             "job is to hold the explosion gases in long enough for them to "
             "break rock instead of blowing out of the collar. Drill cuttings "
             "are the usual temptation and the usual mistake: fine, rounded "
             "material flows straight out. Stemming length is about 0.9 times "
             "the burden — less invites flyrock, more leaves a hard top.",
        hotspot=(SECT_X, SECT_R * 2, SECT_Z0 + STEMMING / 2),
        hotspot_normal=(1, 0.4, 0))
    stem.cyl(center=(SECT_X, GROUND + SECT_R, SECT_Z0 + STEMMING / 2),
             radius=SECT_R, length=STEMMING, axis="z", segments=20)

    charge = b.part(
        "charge_column", "explosive_red",
        label="Charge column — 6.5 m, about 160 kg",
        note="Site-mixed emulsion pumped into the hole, with a cartridge "
             "primer and detonator near the bottom. The charge is drawn here "
             "at roughly two and a half times true diameter so you can see "
             "it: a real 165 mm column is barely wider than your hand. "
             "Dividing 160 kg by the 357 m³ this hole has to break gives the "
             "powder factor, about 0.45 kg/m³.",
        hotspot=(SECT_X, SECT_R * 2, SECT_Z0 + STEMMING + CHARGE / 2),
        hotspot_normal=(1, 0.4, 0))
    charge.cyl(center=(SECT_X, GROUND + SECT_R,
                       SECT_Z0 + STEMMING + CHARGE / 2),
               radius=SECT_R, length=CHARGE, axis="z", segments=20)

    sub = b.part(
        "subgrade_section", "subgrade_grey",
        label="Subgrade drilling — 1.5 m below floor",
        note="The hole is drilled past the intended floor, usually about 0.3 "
             "times the burden. Without it the charge cannot break the rock "
             "at the very bottom and the blast leaves toe — humps across the "
             "floor that the shovel cannot clean up and that wreck truck "
             "tyres and haul-road grade. The marker shows which part of the "
             "hole is below floor level.",
        hotspot=(SECT_X - 0.6, 0.35, SECT_Z0 + HOLE_DEPTH - SUBGRADE / 2),
        hotspot_normal=(-1, 0.3, 0))
    sub.box(center=(SECT_X - 0.52, GROUND + 0.05,
                    SECT_Z0 + HOLE_DEPTH - SUBGRADE / 2),
            size=(0.30, 0.08, SUBGRADE))
    sub.box(center=(SECT_X - 0.52, GROUND + 0.30, SECT_Z0 + BENCH_H),
            size=(0.60, 0.58, 0.10))

    add_scale_figure(b, x=-SPACING / 2 - 1.4, z=BURDEN * 1.5, facing_deg=180.0)
    return b


def main():
    b = build()
    glb = WEB / "models" / "blast-pattern.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/blast-pattern.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]
    (WEB / "data" / "blast-pattern.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print(f"blast-pattern.glb {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
