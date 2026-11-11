"""
figure.py -- a 1.8 m human stand-in, for scale.

The single most effective thing in an equipment AR lesson is a person next to
the machine. On a phone screen a dumper is just a yellow shape; beside a 1.8 m
figure it is suddenly a four-storey machine whose tyre is taller than you are.
The viewer can fade this part out, so it never gets in the way in real AR where
there is a real person standing there already.
"""

from __future__ import annotations


def add_scale_figure(builder, x: float, z: float, facing_deg: float = 0.0,
                     material: str = "figure_hiviz"):
    """Add a simple 1.8 m PPE-clad figure standing at (x, 0, z)."""
    builder.material(material, (0.95, 0.42, 0.06), roughness=0.75, metallic=0.0)
    builder.material(material + "_hat", (0.98, 0.85, 0.10), roughness=0.5)

    p = builder.part(
        "scale_figure", material,
        label="1.8 m person (for scale)",
        note=("A person in PPE, 1.8 m tall, standing clear of the machine. "
              "Use the scale toggle to hide them. In real AR at 1:1 you can "
              "simply walk up to the machine yourself."),
        hotspot=(x, 2.05, z), hotspot_normal=(0, 1, 0))

    # legs
    for sx in (-1, 1):
        p.box(center=(x + sx * 0.12, 0.42, z), size=(0.17, 0.84, 0.21))
        p.box(center=(x + sx * 0.12, 0.04, z - 0.04), size=(0.17, 0.08, 0.29))
    # torso + hi-vis vest line
    p.box(center=(x, 1.14, z), size=(0.45, 0.60, 0.24))
    p.box(center=(x, 0.86, z), size=(0.40, 0.08, 0.26))
    # arms
    for sx in (-1, 1):
        p.box(center=(x + sx * 0.30, 1.10, z), size=(0.13, 0.62, 0.17))
    # neck + head
    p.box(center=(x, 1.50, z), size=(0.13, 0.12, 0.13))
    p.box(center=(x, 1.67, z), size=(0.21, 0.24, 0.23))
    # hard hat
    p.cyl(center=(x, 1.81, z), radius=0.15, length=0.10, axis="y", segments=12)
    p.cyl(center=(x, 1.76, z), radius=0.20, length=0.03, axis="y", segments=12)
    return p
