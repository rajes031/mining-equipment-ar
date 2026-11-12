"""
make_roof_support.py -- a single powered roof support (shield) at true scale.

Reference machine: a two-leg lemniscate shield of the kind used on Indian
longwall faces (Adriyala, Jhanjra, Moonidih) -- 1.75 m face pitch, operating
range about 2.2 to 4.8 m, roughly 1,000 t yield. It is shown set at 3.5 m,
which is a realistic working height for those seams.

Why this one is worth building: a shield is the single most startling object
in underground mining at 1:1. On a slide it is a diagram. In AR the student
walks under a canopy at head height and realises that 25 tonnes of steel is
all that stands between them and the roof -- and that there are a hundred and
fifty of them on one face.

Axes: metres, Y up. The coal face is at -Z and the goaf at +Z, matching the
shovel's convention of facing -Z. Origin on the floor at the centre of the
support. Supports sit shoulder to shoulder along X, so the 1.75 m width is
also the face pitch, and the stub of armoured face conveyor at the front is
cut to exactly that width -- one support's worth.

Run:  python make_roof_support.py
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

PITCH = 1.75                # face pitch = overall width
SET_HEIGHT = 3.50           # canopy top as posed
CANOPY_T = 0.32             # canopy thickness
CANOPY_UNDER = SET_HEIGHT - CANOPY_T

BASE_TOP = 0.45
PONTOON_X = 0.50            # centre of each base pontoon
PONTOON_W = 0.60
BASE_Z0, BASE_Z1 = -2.40, 2.20

CANOPY_X = 0.85
CANOPY_Z0, CANOPY_Z1 = -2.70, 1.50

LEG_X = 0.46
LEG_FOOT = (0.45, 0.30)     # (y, z) socket in the base
LEG_HEAD = (CANOPY_UNDER, -0.25)

SHIELD_TOP = (1.50, CANOPY_UNDER)    # (z, y) at the canopy rear
SHIELD_BOT = (2.10, 1.70)
SHIELD_T = 0.18

AFC_Z0, AFC_Z1 = -3.70, -2.95


def strut(p0, p1, x_offset=0.0):
    """Length and transform for a z-aligned primitive spanning p0 -> p1.

    Points are (y, z); the primitive is built along z and rotated about x, so
    a leg or a link can be described by its two pin centres and nothing else.
    """
    (y0, z0), (y1, z1) = p0, p1
    dy, dz = y1 - y0, z1 - z0
    length = math.hypot(dy, dz)
    theta = math.degrees(math.atan2(-dy, dz))
    mid = (x_offset, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    return length, compose(translate(*mid), rotate("x", theta))


def plate(z0, y0, z1, y1, thickness):
    """A (z, y) profile for a flat plate running from one pin line to another."""
    dz, dy = z1 - z0, y1 - y0
    ln = math.hypot(dz, dy)
    nz, ny = dy / ln, -dz / ln          # unit normal
    ox, oy = nz * thickness, ny * thickness
    return [(z0, y0), (z1, y1), (z1 + ox, y1 + oy), (z0 + ox, y0 + oy)]


SPECS = {
    "id": "roof-support",
    "name": "Powered roof support (shield)",
    "category": "Underground",
    "subtitle": "Two-leg lemniscate shield — 1.75 m pitch, set at 3.5 m",
    "summary":
        "On a longwall face the roof is not held up by pillars; it is held up "
        "by a line of hydraulic shields that walk forward behind the shearer. "
        "Each one sets against the roof, takes the load, and is then lowered, "
        "pushed forward about 0.8 m and re-set — so the supported span travels "
        "with the face and the roof behind it is allowed to cave. This is one "
        "support out of the hundred and fifty on a face. It is shown set at "
        "3.5 m with the canopy against the roof and the advance ram extended "
        "towards the conveyor.",
    "specs": [
        ["Type", "Two-leg shield, lemniscate linkage"],
        ["Face pitch (width)", "1.75 m — one support per 1.75 m of face"],
        ["Operating height", "2.2 – 4.8 m (shown set at 3.5 m)"],
        ["Yield load", "approx. 1,000 t (about 9.8 MN)"],
        ["Setting load", "approx. 750 t at 320 bar supply"],
        ["Legs", "2 × double-telescopic, approx. 400 mm bore"],
        ["Canopy length", "4.2 m"],
        ["Base length", "4.6 m"],
        ["Mass", "approx. 25–30 t per support"],
        ["Advance step", "approx. 0.8 m — one web of the shearer"],
        ["Supports per face", "130–180 for a 230–300 m face"],
    ],
    "safety": [
        "The canopy tip is the boundary of supported ground. Nothing and "
        "nobody goes beyond it — that is the definition of unsupported roof.",
        "A support that is not set to pressure is carrying nothing. Setting "
        "pressure is confirmed, not assumed, and a bank of low supports is a "
        "roof fall waiting for a trigger.",
        "Stay clear of the lemniscate linkage and the caving shield. When the "
        "support lowers and advances, that space closes and it will not stop.",
        "Advance in sequence. A gap left out of sequence concentrates load on "
        "its neighbours and unsupports the roof exactly where people work.",
        "Hydraulic fluid at 320 bar penetrates skin through a pinhole leak. "
        "Never run a hand along a hose to find one.",
    ],
    "ar_tips": [
        "Place it and walk underneath. The canopy is at 3.5 m, so you stand "
        "under it with room to spare — and that is the whole point.",
        "Look along the width: 1.75 m is one support. Picture 150 of them "
        "shoulder to shoulder and you have a 260 m longwall face.",
        "Fade everything except the legs. Two cylinders carry 1,000 t.",
    ],
}


def build():
    b = Builder("roof_support")
    b.material("steel_yellow", (0.82, 0.58, 0.06), roughness=0.55, metallic=0.25)
    b.material("steel_dark", (0.26, 0.27, 0.29), roughness=0.65, metallic=0.45)
    b.material("chrome", (0.78, 0.79, 0.82), roughness=0.18, metallic=0.95)
    b.material("hydraulics_red", (0.62, 0.11, 0.09), roughness=0.70, metallic=0.1)
    b.material("afc_steel", (0.34, 0.35, 0.37), roughness=0.60, metallic=0.55)

    # -- base ---------------------------------------------------------------
    base = b.part(
        "base", "steel_yellow",
        label="Base (floor pontoons)",
        note="Two skids spreading the support's load onto the floor. They are "
             "separate so the support can straddle an uneven floor and so the "
             "advance ram can sit between them. Soft floor is a real problem "
             "on longwall: a base that punches into the floor loses setting "
             "height and the canopy stops reaching the roof.",
        hotspot=(0.80, 0.30, -1.20), hotspot_normal=(1, 0.2, 0))
    for sx in (-1, 1):
        base.box(center=(sx * PONTOON_X, BASE_TOP / 2, (BASE_Z0 + BASE_Z1) / 2),
                 size=(PONTOON_W, BASE_TOP, BASE_Z1 - BASE_Z0))
    base.box(center=(0.0, 0.25, 1.88), size=(2 * PONTOON_X + PONTOON_W, 0.50, 0.65))

    # -- legs ---------------------------------------------------------------
    legs = b.part(
        "hydraulic_legs", "chrome",
        label="Hydraulic legs (2 × double-telescopic)",
        note="The two props that actually carry the roof. Fluid is pumped in "
             "to set the canopy hard against the roof, then the leg is locked; "
             "as the roof converges the leg resists until the yield valve "
             "opens at about 1,000 t and lets it shorten rather than burst. "
             "Yield load and setting load are different numbers and both "
             "matter: setting load is what you start with, yield is the most "
             "the support will ever give you.",
        hotspot=(0.0, 2.0, 0.30), hotspot_normal=(0, 0, -1))
    for sx in (-1, 1):
        ln, xf = strut(LEG_FOOT, LEG_HEAD, sx * LEG_X)
        # Barrel for the lower part of the stroke, bright rod above it.
        legs.cyl(radius=0.19, length=ln * 0.55, axis="z", segments=20,
                 xform=compose(xf, translate(0, 0, -ln * 0.225)))
        legs.cyl(radius=0.145, length=ln * 0.50, axis="z", segments=18,
                 xform=compose(xf, translate(0, 0, ln * 0.25)))

    # -- canopy -------------------------------------------------------------
    canopy = b.part(
        "canopy", "steel_yellow",
        label="Canopy",
        note="The roof beam. Its length is what decides how much ground stays "
             "supported between the face and the caving line, and its tip is "
             "the legal edge of supported roof. A canopy set level and hard "
             "carries load across its whole length; one set tip-low loads the "
             "front edge only and lets the roof break ahead of the face.",
        hotspot=(0.0, SET_HEIGHT, -1.60), hotspot_normal=(0, 1, 0))
    canopy.box(center=(0.0, SET_HEIGHT - CANOPY_T / 2,
                       (CANOPY_Z0 + CANOPY_Z1) / 2),
               size=(2 * CANOPY_X, CANOPY_T, CANOPY_Z1 - CANOPY_Z0))

    tip = b.part(
        "canopy_tip_extension", "steel_yellow",
        label="Canopy tip extension (flipper)",
        note="A hinged extension that reaches out over the conveyor to hold "
             "the newly exposed roof immediately behind the shearer drum, "
             "before the whole support can be advanced. It is the difference "
             "between supporting the face line and supporting it one web too "
             "late.",
        hotspot=(0.0, 3.44, -3.10), hotspot_normal=(0, 0.4, -1))
    tip.box(center=(0.0, 3.33, -2.92), size=(1.60, 0.22, 0.45))

    # -- caving shield and linkage -----------------------------------------
    shield = b.part(
        "caving_shield", "steel_yellow",
        label="Caving shield",
        note="The sloping plate across the back. It does not hold up the "
             "roof; it keeps the caved goaf out of the walkway and guides the "
             "broken rock away behind the support. Everything behind this "
             "plate is meant to collapse — that is how a longwall works.",
        hotspot=(0.0, 2.45, 2.30), hotspot_normal=(0, 0.3, 1))
    shield.prism(plate(SHIELD_TOP[0], SHIELD_TOP[1],
                       SHIELD_BOT[0], SHIELD_BOT[1], SHIELD_T),
                 extent=1.55, axis="x")

    links = b.part(
        "lemniscate_links", "steel_dark",
        label="Lemniscate linkage",
        note="Two unequal links on each side tying the caving shield to the "
             "base. Their geometry is the clever part: as the support is "
             "raised and lowered, the linkage makes the canopy tip travel "
             "almost straight up and down instead of swinging. That keeps the "
             "tip-to-face distance constant at every seam height.",
        hotspot=(0.70, 1.30, 1.90), hotspot_normal=(1, 0, 0.3))
    for sx in (-1, 1):
        ln, xf = strut((0.50, 1.35), (2.00, 2.00), sx * 0.40)
        links.box(center=(0, 0, 0), size=(0.14, 0.24, ln), xform=xf)
        ln, xf = strut((0.50, 2.05), (1.76, 2.26), sx * 0.63)
        links.box(center=(0, 0, 0), size=(0.12, 0.20, ln), xform=xf)

    # -- advance ram and conveyor ------------------------------------------
    ram = b.part(
        "advance_ram", "chrome",
        label="Advance (double-acting) ram",
        note="The ram between the base pontoons. Pushed one way it shoves the "
             "armoured face conveyor over towards the new face line; pulled "
             "the other, with the legs lowered, it drags the whole support "
             "forward to follow it. The conveyor is the anchor — the support "
             "pushes off it, which is why the two advance as a system and "
             "never independently.",
        hotspot=(0.0, 0.28, -3.10), hotspot_normal=(0, -0.2, -1))
    ram.cyl(center=(0.0, 0.28, -2.66), radius=0.13, length=0.52, axis="z",
            segments=18)
    ram.cyl(center=(0.0, 0.28, -3.12), radius=0.075, length=0.46, axis="z",
            segments=14)

    afc = b.part(
        "afc_pan", "afc_steel",
        label="Armoured face conveyor (one pan)",
        note="A single 1.75 m pan of the AFC — the same width as the support, "
             "because the face is built from repeats of exactly this module. "
             "The chain conveyor running in it carries the cut coal off the "
             "face, and its spill plate doubles as the track the shearer "
             "rides on.",
        hotspot=(0.0, 0.70, -3.60), hotspot_normal=(0, 0.3, -1))
    afc.box(center=(0.0, 0.19, (AFC_Z0 + AFC_Z1) / 2),
            size=(PITCH, 0.38, AFC_Z1 - AFC_Z0))
    afc.box(center=(0.0, 0.66, AFC_Z1 - 0.06), size=(PITCH, 0.56, 0.12))

    valves = b.part(
        "control_valve_bank", "hydraulics_red",
        label="Control valve bank and hoses",
        note="Where the support is operated from — and, on a modern face, "
             "where the electro-hydraulic controller sits so that supports "
             "can be set and advanced in automatic sequence from the "
             "neighbouring unit, keeping people out from under the newly "
             "exposed roof altogether.",
        hotspot=(-0.72, 1.35, 0.95), hotspot_normal=(-1, 0.2, 0))
    valves.box(center=(-0.52, 0.72, 0.95), size=(0.30, 0.54, 0.52))
    for i, yy in enumerate((0.56, 0.70)):
        valves.cyl(center=(-0.52, yy, 0.10), radius=0.035,
                   length=1.60, axis="z", segments=8)

    # Under the canopy, not beside it. A figure standing in the walkway with
    # 1.7 m of clear air above their hard hat is the whole lesson: the roof is
    # held by this and nothing else.
    add_scale_figure(b, x=0.0, z=-1.75, facing_deg=0.0)
    return b


def main():
    b = build()
    glb = WEB / "models" / "roof-support.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/roof-support.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]
    (WEB / "data" / "roof-support.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print(f"roof-support.glb  {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
