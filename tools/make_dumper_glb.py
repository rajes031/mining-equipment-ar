"""Turn the marketplace haul-truck OBJ into a teaching GLB for the AR site.

The asset arrives as one mesh with two materials and no part structure, but it
was modelled as separate solids, so separating by loose parts recovers 231
shells. Those shells are unnamed, so they are grouped into teaching assemblies
by where they sit in the machine's own bounding box -- which is stable,
because the geometry never moves.

Axes in Blender after OBJ import (Z-up):
    X  width,  -135.5 .. +135.5      (left/right)
    Y  length, -210.3 .. +210.3      (FRONT is -Y, REAR is +Y)
    Z  height,    0.0 .. +238.7

Front/rear was read off the wheels: +Y carries twice as many shells as -Y,
i.e. dual tyres, i.e. the drive axle, i.e. the rear of a rear-dump truck.
"""
import sys
import os
import json
import math

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT_GLB, OUT_JSON = argv[0], argv[1], argv[2]

# The OBJ header declares centimetres, so metres need a factor of 1/100.
UNIT = 0.01
# On top of that the artist did not model to real-world size: the machine is
# only 4.21 m long as supplied. Scaling by 3.0 fits the 220 t class (CAT 793F
# / Komatsu 830E): it is the geometric mean of the three per-axis factors
# needed to hit a 793F's 13.1 x 8.5 x 6.6 m, so the residual error is spread
# evenly across the axes instead of being forced onto one.
CLASS_SCALE = 3.0
SCALE = UNIT * CLASS_SCALE


def classify(cx, cy, cz, sx, sy, sz):
    """Name the assembly a shell belongs to, from its bounding box."""
    wheel = 20.0 < cz < 115.0 and abs(cx) > 40.0
    if wheel and -140.0 < cy < -55.0:
        return "tyre_front_left" if cx > 0 else "tyre_front_right"
    if wheel and 55.0 < cy < 145.0:
        return "tyre_rear_left" if cx > 0 else "tyre_rear_right"
    # Operator cab: high up, offset to one side, forward of the front axle.
    if cz > 148.0 and 30.0 < cx < 115.0 and -145.0 < cy < -80.0:
        return "operator_cab"
    # Access ladder and front platform: at the very front face, any height.
    if cy < -162.0:
        return "access_ladder"
    # Everything else up high is the dump body, including its canopy.
    if cz > 140.0:
        return "dump_body"
    return "chassis_frame"


# base colour, metallic, roughness
COLOURS = {
    "dump_body":        ((0.86, 0.60, 0.05), 0.25, 0.50),
    "chassis_frame":    ((0.80, 0.56, 0.05), 0.30, 0.55),
    "operator_cab":     ((0.86, 0.60, 0.05), 0.25, 0.45),
    "access_ladder":    ((0.72, 0.50, 0.04), 0.35, 0.55),
    "tyre_front_left":  ((0.035, 0.035, 0.040), 0.0, 0.92),
    "tyre_front_right": ((0.035, 0.035, 0.040), 0.0, 0.92),
    "tyre_rear_left":   ((0.035, 0.035, 0.040), 0.0, 0.92),
    "tyre_rear_right":  ((0.035, 0.035, 0.040), 0.0, 0.92),
}
GLASS = ((0.055, 0.085, 0.10), 0.0, 0.08)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=SRC)

src = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]

# Which of the two source materials is the grey one? That is the glass/trim.
grey_idx = None
for i, m in enumerate(src.data.materials):
    if m and m.name.endswith("SG"):
        grey_idx = i

bpy.context.view_layer.objects.active = src
src.select_set(True)
bpy.ops.mesh.separate(type="LOOSE")

shells = [o for o in bpy.context.scene.objects if o.type == "MESH"]
groups = {}
for o in shells:
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    c = (mn + mx) / 2.0
    s = mx - mn
    groups.setdefault(classify(c.x, c.y, c.z, s.x, s.y, s.z), []).append(o)


def mat(name, spec):
    col, metal, rough = spec
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return m


parts = []
for name, objs in groups.items():
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    # Rename the mesh datablock too: glTF names its meshes from the datablock,
    # and leaving "Industrial_009.037" in there makes the export unreadable.
    obj.name = name
    obj.data.name = name

    # Remap: every face keeps its body/glass distinction, but now under
    # materials named after THIS part, so the web viewer -- which can address
    # materials but not nodes -- can fade or isolate the part on its own.
    was_grey = [p.material_index == grey_idx for p in obj.data.polygons]
    obj.data.materials.clear()
    obj.data.materials.append(mat(name, COLOURS.get(name, COLOURS["chassis_frame"])))
    if any(was_grey):
        obj.data.materials.append(mat(name + ".glass", GLASS))
        for p, g in zip(obj.data.polygons, was_grey):
            p.material_index = 1 if g else 0
    else:
        for p in obj.data.polygons:
            p.material_index = 0
    parts.append(obj)

# Smooth only across shallow angles, so flat plate edges stay crisp instead
# of smearing into each other.
for obj in parts:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception:
        bpy.ops.object.shade_flat()

# --- scale to life size, sit it on the ground, centre it -------------------
mn = Vector((1e18,) * 3)
mx = Vector((-1e18,) * 3)
for o in parts:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])

offset = Vector(((mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0, mn.z))
for o in parts:
    o.location -= offset
    o.scale = (SCALE, SCALE, SCALE)

bpy.context.view_layer.update()
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)

# Give each part a sensible pivot, so a Unity rig can hinge the dump body
# without anyone having to re-origin it by hand later.
for o in parts:
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    if o.name == "dump_body":
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bpy.context.scene.cursor.location = Vector(
            (0.0, max(v.y for v in bb), min(v.z for v in bb)))
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    else:
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

# --- report + export -------------------------------------------------------
mn = Vector((1e18,) * 3)
mx = Vector((-1e18,) * 3)
tris = 0
rows = []
for o in parts:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    rows.append({"name": o.name, "tris": len(o.data.loop_triangles),
                 "materials": [m.name for m in o.data.materials]})

size = [round(mx[i] - mn[i], 3) for i in range(3)]

# --- hotspot anchors --------------------------------------------------------
# model-viewer wants each hotspot in glTF axes, which are Blender's rotated:
#   gltf_x = blender_x,  gltf_y = blender_z,  gltf_z = -blender_y
# The anchor sits on the part's own bounding box, pushed out along whichever
# axis the part lies furthest from the machine's centre. That keeps the dot on
# the visible skin of the part rather than buried inside the body.
def to_gltf(v):
    return [round(v.x, 3), round(v.z, 3), round(-v.y, 3)]


machine_centre = (mn + mx) / 2.0
for r in rows:
    o = bpy.data.objects[r["name"]]
    pmn = Vector((1e18,) * 3)
    pmx = Vector((-1e18,) * 3)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            pmn[i] = min(pmn[i], w[i])
            pmx[i] = max(pmx[i], w[i])
    pc = (pmn + pmx) / 2.0
    away = pc - machine_centre
    span = pmx - pmn
    # Dominant axis, measured relative to the part's own size so a long thin
    # part is not pushed out along its length.
    order = sorted(range(3), key=lambda i: -abs(away[i]) / max(span[i], 1e-6))
    k = order[0]
    s = 1.0 if away[k] >= 0 else -1.0
    # Never anchor on the underside: a downward-facing hotspot is hidden from
    # every angle a person can actually stand at, so it would never appear.
    if k == 2 and s < 0:
        k = order[1]
        s = 1.0 if away[k] >= 0 else -1.0
    anchor = pc.copy()
    anchor[k] = pmx[k] if s > 0 else pmn[k]
    nrm = Vector((0.0, 0.0, 0.0))
    nrm[k] = s
    r["position"] = to_gltf(anchor)
    r["normal"] = to_gltf(nrm)

info = {"scale": SCALE, "tris": tris,
        "parts": sorted(rows, key=lambda r: -r["tris"]),
        "width_x": size[0], "length_y": size[1], "height_z": size[2],
        "ground_z": round(mn.z, 4)}
json.dump(info, open(OUT_JSON, "w"), indent=1)
print("INFO " + json.dumps({k: v for k, v in info.items() if k != "parts"}))
for r in info["parts"]:
    print("  %-18s %6d  %s" % (r["name"], r["tris"], r["materials"]))

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB, export_format="GLB", use_selection=True,
    export_yup=True, export_apply=True, export_materials="EXPORT",
    export_normals=True, export_texcoords=True, export_cameras=False,
    export_lights=False,
)
print("EXPORTED " + OUT_GLB)
