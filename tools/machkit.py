"""
machkit.py -- small shared helpers for the make_*.py machine generators.

The first two generators (dumper, shovel) each carried their own copy of the
materials and a 2-D `strut`. The machines added later need links that are not
in the x = 0 plane -- a dragline boom is a tapered lattice, a grader's drawbar
is an A-frame -- so the general 3-D version lives here, with the palette every
machine shares.
"""

from __future__ import annotations

import math

import numpy as np

from glbgen import compose, rotate, translate


def standard_materials(b):
    """The common machine palette. Generic yellow avoids trade dress."""
    b.material("body_yellow", (0.93, 0.66, 0.05), roughness=0.55, metallic=0.15)
    b.material("steel", (0.40, 0.42, 0.45), roughness=0.45, metallic=0.70)
    b.material("dark", (0.13, 0.13, 0.15), roughness=0.70, metallic=0.25)
    b.material("chrome", (0.80, 0.81, 0.84), roughness=0.15, metallic=0.95)
    b.material("wear", (0.28, 0.29, 0.32), roughness=0.35, metallic=0.85)
    b.material("glass", (0.42, 0.55, 0.62), roughness=0.08, metallic=0.0,
               alpha=0.42, double_sided=True)
    b.material("rail", (0.95, 0.78, 0.08), roughness=0.5, metallic=0.2)
    b.material("rubber", (0.07, 0.07, 0.08), roughness=0.92, metallic=0.0)
    b.material("rope", (0.22, 0.22, 0.24), roughness=0.55, metallic=0.80)


def link(p0, p1):
    """Length and transform for a z-aligned primitive spanning p0 -> p1.

    Works in any direction. The primitive's local x stays horizontal where
    it can, so a box link keeps its width horizontal and its depth "up".
    """
    a = np.asarray(p0, dtype=np.float64)
    c = np.asarray(p1, dtype=np.float64)
    d = c - a
    length = float(np.linalg.norm(d))
    if length < 1e-9:
        raise ValueError("link endpoints coincide: %r" % (p0,))
    z = d / length
    ref = np.array([0.0, 1.0, 0.0]) if abs(z[1]) < 0.95 else np.array([1.0, 0, 0])
    x = np.cross(ref, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = x, y, z
    m[:3, 3] = (a + c) / 2.0
    return length, m


def bar(part, p0, p1, width, depth):
    """Rectangular member between two points."""
    length, xf = link(p0, p1)
    part.box(center=(0, 0, 0), size=(width, depth, length), xform=xf)
    return part


def tube(part, p0, p1, radius, segments=8):
    """Round member between two points -- ropes, chords, cylinders."""
    length, xf = link(p0, p1)
    part.cyl(center=(0, 0, 0), radius=radius, length=length, axis="z",
             segments=segments, xform=xf)
    return part


def about_y(degrees, pivot):
    """Rotation about a vertical axis through `pivot` (x, z)."""
    px, pz = pivot
    return compose(translate(px, 0, pz), rotate("y", degrees),
                   translate(-px, 0, -pz))


def crawler_profile(length, height, nose=0.45, chamfer=0.40):
    """Side profile (z, y) of a crawler track loop, convex, centred on z=0."""
    h = length / 2.0
    return [(-h, nose), (-h + nose, 0.02), (h - nose, 0.02), (h, nose),
            (h, height - chamfer), (h - chamfer, height),
            (-h + chamfer, height), (-h, height - chamfer)]


def tyre(rubber_part, hub_part, center, radius, width, rim_ratio=0.62,
         segments=20):
    """Earthmover tyre on an x axle: rubber annulus plus a steel rim disc."""
    rubber_part.cyl(center=center, radius=radius, length=width, axis="x",
                    segments=segments, inner_radius=radius * rim_ratio)
    hub_part.cyl(center=center, radius=radius * rim_ratio, length=width * 0.8,
                 axis="x", segments=max(10, segments // 2))


def write_record(b, specs, web, name):
    """Write <name>.glb and data/<name>.json the way build.py expects."""
    import json
    glb = web / "models" / f"{name}.glb"
    summary = b.write(glb)
    record = dict(specs)
    record["model"] = f"models/{name}.glb"
    for key in ("extents_m", "triangles", "bytes", "parts"):
        record[key] = summary[key]
    (web / "data" / f"{name}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{name + '.glb':18s} {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  {len(summary['parts'])} parts  "
          f"extents {summary['extents_m']}")
    return record


def deg(rad):
    return math.degrees(rad)
