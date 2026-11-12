"""Render a glTF animation at chosen times, to check the poses line up.

Run: blender -b -noaudio --python render_anim.py -- <glb> <outdir> t1 t2 ...

Blender's glTF importer bakes animation onto the objects as actions keyed in
frames, so a time in seconds is just t * fps.
"""
import sys
import os

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, outdir = argv[0], argv[1]
times = [float(t) for t in argv[2:]] or [0.0]
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

scn = bpy.context.scene
FPS = scn.render.fps

print("ACTIONS " + ", ".join(sorted(a.name for a in bpy.data.actions)))
animated = [o.name for o in scn.objects
            if o.animation_data and o.animation_data.action]
print("ANIMATED " + ", ".join(sorted(animated)))

meshes = [o for o in scn.objects if o.type == "MESH"]
mn = Vector((1e18,) * 3)
mx = Vector((-1e18,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
centre = (mn + mx) / 2.0
span = max(mx[i] - mn[i] for i in range(3))

scn.render.engine = "BLENDER_EEVEE_NEXT"
scn.render.resolution_x = 1100
scn.render.resolution_y = 620
scn.world = bpy.data.worlds.new("w")
scn.world.use_nodes = True
scn.world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.70, 0.82, 1)
scn.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5

sun = bpy.data.lights.new("sun", type="SUN")
sun.energy = 3.6
so = bpy.data.objects.new("sun", sun)
so.rotation_euler = (0.95, 0.15, 2.2)
scn.collection.objects.link(so)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
aspect = float(scn.render.resolution_y) / float(scn.render.resolution_x)
cam_data.ortho_scale = span * 1.18
cam_data.clip_start = span * 0.01
cam_data.clip_end = span * 20
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam

# Looking from above and behind the haul road, so both machines and the gap
# between bucket and truck body are visible.
d = Vector((0.85, 0.75, 0.60)).normalized()
cam.location = centre + d * span * 3
cam.rotation_euler = (centre - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()

for t in times:
    scn.frame_set(int(round(t * FPS)))
    bpy.context.view_layer.update()
    # Report where the bucket teeth actually are at this instant.
    teeth = bpy.data.objects.get("sh_bucket_teeth")
    body = bpy.data.objects.get("tr_dump_body")
    info = ""
    for name, ob in (("teeth", teeth), ("body", body)):
        if ob is None:
            continue
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = [round(min(p[i] for p in pts), 2) for i in range(3)]
        hi = [round(max(p[i] for p in pts), 2) for i in range(3)]
        info += " %s=%s..%s" % (name, lo, hi)
    print("T %5.1f%s" % (t, info))
    scn.render.filepath = os.path.join(outdir, "t%05.1f.png" % t)
    bpy.ops.render.render(write_still=True)
