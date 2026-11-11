"""Build the drill rig GLB from the ASCII FBX that Blender cannot import.

Run:
  blender -b -noaudio --python make_drill.py -- <fbx> <texdir> <out.glb> <out.json>

The mesh data comes from fbx_ascii.py. This script turns it into Blender
objects, rebuilds the three-null control rig, re-textures it from the PBR
maps that ship in the fbx folder, decimates it to a tablet-sized budget and
exports glTF.

Two things about the source are worth knowing:

* It was authored Z-up in 3ds Max and exported Y-up, which the exporter
  recorded as a -90 degree PreRotation on the root null. Applying the
  hierarchy faithfully therefore leaves the rig on its back in Blender's
  Z-up world, so the root is turned +90 back at the end.
* The FBX points at VRay diffuse/reflection/glossiness maps that live in the
  3dsmax folders. Those are ignored. The fbx folder ships a metal/rough set
  instead -- BaseColor, Normal and a packed OcclusionRoughnessMetallic -- and
  that is exactly what glTF wants, so materials are rebuilt from those.
"""
import sys
import os
import json
import math

import bpy
from mathutils import Matrix, Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbx_ascii

argv = sys.argv[sys.argv.index("--") + 1:]
FBX, TEXDIR, OUT_GLB, OUT_JSON = argv[0], argv[1], argv[2], argv[3]

# FBX UnitScaleFactor is 1, i.e. centimetres.
UNIT = 0.01
# Triangle budget for a tablet. The source is ~705k, which would stall AR.
TRI_TARGET = 150000
# Textures are 4K; that is far more than a 7-inch screen can show and it
# would dominate the download.
TEX_SIZE = 1024

PBR = {
    "Piling_1_2_Piling_1": ("Piling_1_2_Piling_1_BaseColor.jpg",
                            "Piling_1_2_Piling_1_Normal.jpg",
                            "Piling_1_2_Piling_1_OcclusionRoughnessMetallic.jpg",
                            None),
    "Piling_1_2_Piling_2": ("Piling_1_2_Piling_2_BaseColor.jpg",
                            "Piling_1_2_Piling_2_Normal.jpg",
                            "Piling_1_2_Piling_2_OcclusionRoughnessMetallic.jpg",
                            None),
    "Piling_1_2_Piling_3": ("Piling_1_2_Piling_3_BaseColor.jpg",
                            "Piling_1_2_Piling_3_Normal.jpg",
                            "Piling_1_2_Piling_3_OcclusionRoughnessMetallic.jpg",
                            "Piling_1_2_Piling_3_Emissive.jpg"),
}
PLAIN = {   # base colour, metallic, roughness, alpha
    "glass2":       ((0.08, 0.12, 0.14), 0.0, 0.05, 0.35),
    "glass_window": ((0.08, 0.12, 0.14), 0.0, 0.05, 0.35),
    "emissive":     ((1.0, 0.72, 0.25), 0.0, 0.4, 1.0),
}

print("parsing %s" % FBX)
doc = fbx_ascii.parse(FBX)

# --- connections ------------------------------------------------------------
parent_of = {}
geo_of = {}
mats_of = {}
for kind, child, parent, _prop in doc["connections"]:
    if kind != "OO":
        continue
    if child in doc["models"] and (parent in doc["models"] or parent == 0):
        parent_of[child] = parent
    elif child in doc["geometries"] and parent in doc["models"]:
        geo_of[parent] = child
    elif child in doc["materials"] and parent in doc["models"]:
        mats_of.setdefault(parent, []).append(child)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene


# --- materials --------------------------------------------------------------
_img_cache = {}
TMPDIR = os.path.join(os.path.dirname(os.path.abspath(OUT_GLB)), "_tex")
os.makedirs(TMPDIR, exist_ok=True)


def load_image(fname, non_color):
    if fname in _img_cache:
        return _img_cache[fname]
    img = bpy.data.images.load(os.path.join(TEXDIR, fname))
    if max(img.size) > TEX_SIZE:
        img.scale(TEX_SIZE, TEX_SIZE)
        # scale() only resizes the in-memory buffer. pack() and the glTF
        # exporter both go back to the file on disk, so without writing the
        # resized buffer out the export still carries the original 4K JPEGs
        # -- which is a 27 MB GLB instead of a 7 MB one.
        out = os.path.join(TMPDIR, os.path.splitext(fname)[0] + ".jpg")
        bpy.context.scene.render.image_settings.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = 85
        img.filepath_raw = out
        img.file_format = "JPEG"
        img.save()
        img.filepath = out
        img.reload()
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    _img_cache[fname] = img
    return img


def build_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    if name in PLAIN:
        col, metal, rough, alpha = PLAIN[name]
        bsdf.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Alpha"].default_value = alpha
        if alpha < 1.0:
            m.blend_method = "BLEND"
        if name == "emissive":
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.72, 0.25, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.0
        return m

    base, nrm, orm, emis = PBR[name]

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = load_image(base, False)
    tex.location = (-700, 300)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    # Roughness in G and metallic in B of one image is the glTF packing, and
    # the exporter recognises it as such when both come off the same node.
    ormtex = nt.nodes.new("ShaderNodeTexImage")
    ormtex.image = load_image(orm, True)
    ormtex.location = (-700, 0)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-420, 0)
    nt.links.new(ormtex.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    ntex = nt.nodes.new("ShaderNodeTexImage")
    ntex.image = load_image(nrm, True)
    ntex.location = (-700, -300)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-420, -300)
    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    if emis:
        etex = nt.nodes.new("ShaderNodeTexImage")
        etex.image = load_image(emis, False)
        etex.location = (-700, -620)
        nt.links.new(etex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


bl_materials = {}
for mid, mrec in doc["materials"].items():
    bl_materials[mid] = build_material(mrec["name"])
    print("material %s" % mrec["name"])


# --- transforms -------------------------------------------------------------
def prop_vec(rec, key, default):
    v = rec["props"].get(key)
    if not v:
        return Vector(default)
    nums = [x for x in v if isinstance(x, float)]
    if len(nums) < 3:
        return Vector(default)
    return Vector(nums[:3])


def local_matrix(rec):
    """FBX local transform with the parts this file actually uses.

    The full product is T * Roff * Rp * Rpre * R * Rpost^-1 * Rp^-1 * Soff *
    Sp * S * Sp^-1; everything but T, Rpre, R and S is absent here. Rotation
    order is the FBX default EulerXYZ, which matches Blender's "XYZ".
    """
    t = prop_vec(rec, "Lcl Translation", (0, 0, 0))
    r = prop_vec(rec, "Lcl Rotation", (0, 0, 0))
    s = prop_vec(rec, "Lcl Scaling", (1, 1, 1))
    pre = prop_vec(rec, "PreRotation", (0, 0, 0))
    mt = Matrix.Translation(t)
    mpre = Euler([math.radians(a) for a in pre], "XYZ").to_matrix().to_4x4()
    mr = Euler([math.radians(a) for a in r], "XYZ").to_matrix().to_4x4()
    ms = Matrix.Diagonal(s.to_4d())
    return mt @ mpre @ mr @ ms


# --- build objects ----------------------------------------------------------
created = {}
for mid, mrec in doc["models"].items():
    name = mrec["name"]
    if mrec["subtype"] == "Mesh" and mid in geo_of:
        g = doc["geometries"][geo_of[mid]]
        verts = g["Vertices"]
        coords = [(verts[i], verts[i + 1], verts[i + 2])
                  for i in range(0, len(verts), 3)]
        faces = fbx_ascii.polygons(g["PolygonVertexIndex"])

        # GeometricTranslation offsets the mesh under the node and is NOT
        # inherited by children, so it is baked into the vertices here.
        go = prop_vec(mrec, "GeometricTranslation", (0, 0, 0))
        if go.length > 0:
            coords = [(c[0] + go.x, c[1] + go.y, c[2] + go.z) for c in coords]

        me = bpy.data.meshes.new(name)
        me.from_pydata(coords, [], faces)
        me.validate(clean_customdata=False)

        # UVs: ByPolygonVertex + IndexToDirect, so loop i reads UV[UVIndex[i]].
        uv = g.get("UV")
        uvi = g.get("UVIndex")
        if uv and uvi and len(uvi) == len(me.loops):
            layer = me.uv_layers.new(name="UVChannel_1")
            flat = [0.0] * (len(me.loops) * 2)
            for i, idx in enumerate(uvi):
                flat[i * 2] = uv[idx * 2]
                flat[i * 2 + 1] = uv[idx * 2 + 1]
            layer.data.foreach_set("uv", flat)

        ob = bpy.data.objects.new(name, me)

        slots = mats_of.get(mid, [])
        for sid in slots:
            me.materials.append(bl_materials[sid])
        mapping = g.get("LayerElementMaterial.MappingInformationType")
        marr = g.get("Materials") or [0]
        if slots:
            if mapping == "ByPolygon" and len(marr) == len(me.polygons):
                me.polygons.foreach_set("material_index", marr)
            else:
                idx = marr[0] if marr else 0
                for p in me.polygons:
                    p.material_index = idx
        print("mesh %-16s verts=%d faces=%d slots=%d map=%s"
              % (name, len(coords), len(faces), len(slots), mapping))
    else:
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_size = 100.0
        print("null %s" % name)

    scn.collection.objects.link(ob)
    ob.matrix_basis = local_matrix(mrec)
    created[mid] = ob

for mid, ob in created.items():
    pid = parent_of.get(mid, 0)
    if pid in created:
        ob.parent = created[pid]
        ob.matrix_parent_inverse = Matrix.Identity(4)

roots = [ob for mid, ob in created.items() if parent_of.get(mid, 0) not in created]

# Stand it up and put it in metres. The -90 PreRotation on the root is what
# took the Max Z-up scene to FBX Y-up; +90 here puts it back for Blender.
for ob in roots:
    ob.matrix_basis = (Matrix.Rotation(math.radians(90), 4, "X")
                       @ Matrix.Scale(UNIT, 4) @ ob.matrix_basis)

bpy.context.view_layer.update()

# Centre the machine on the origin and sit it on the ground, so model-viewer
# orbits around it and AR drops it at the user's feet rather than offset.
_mn = Vector((1e18,) * 3)
_mx = Vector((-1e18,) * 3)
for o in scn.objects:
    if o.type != "MESH":
        continue
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            _mn[i] = min(_mn[i], w[i])
            _mx[i] = max(_mx[i], w[i])
shift = Vector((-(_mn.x + _mx.x) / 2.0, -(_mn.y + _mx.y) / 2.0, -_mn.z))
for ob in roots:
    ob.matrix_basis = Matrix.Translation(shift) @ ob.matrix_basis
bpy.context.view_layer.update()

# --- split the three source meshes into named teaching parts ---------------
# The FBX gives one mesh per rig segment, which maps neatly onto the three
# control nulls but is far too coarse to label. Loose-part separation is no
# use here -- the crawler alone is a hundred-odd track shoes and Blender takes
# minutes to make that many objects -- so faces are partitioned by where their
# centroids sit, measured from a histogram of the real geometry.
SPLITS = {
    "Drilling_rig_3": [
        ("track_left", lambda x, y, z, m: x > 0.9),
        ("track_right", lambda x, y, z, m: x < -0.9),
        ("undercarriage_frame", lambda x, y, z, m: True),
    ],
    "Drilling_rig_1": [
        # Glazing and lights are only ever on the cab, so material is a surer
        # test than position for those faces.
        ("operator_cab", lambda x, y, z, m: m in ("glass2", "glass_window", "emissive")
            or (x < -0.55 and -2.1 < y < 0.7 and 1.0 < z < 3.35)),
        ("mast", lambda x, y, z, m: z >= 3.35 or y < -2.3),
        ("machinery_house", lambda x, y, z, m: True),
    ],
    "Drilling_rig_2": [
        ("drill_string", lambda x, y, z, m: True),
    ],
}


def _submesh(ob, poly_indices, name):
    """Build a new object from a subset of ob's polygons.

    Done by hand rather than with mesh.separate(): that operator reads the
    selection through edit mode, where the active select-mode decides whether
    per-face flags survive at all, and silently separated nothing here. Copying
    the polygons directly has no such hidden state.
    """
    me = ob.data
    uvlay = me.uv_layers.active
    vmap = {}
    verts = []
    faces = []
    uvs = []
    mats = []
    for pi in poly_indices:
        p = me.polygons[pi]
        face = []
        for li in range(p.loop_start, p.loop_start + p.loop_total):
            vi = me.loops[li].vertex_index
            j = vmap.get(vi)
            if j is None:
                j = len(verts)
                vmap[vi] = j
                verts.append(me.vertices[vi].co.copy())
            face.append(j)
            if uvlay is not None:
                u = uvlay.data[li].uv
                uvs.append(u[0])
                uvs.append(u[1])
        faces.append(face)
        mats.append(p.material_index)

    nm = bpy.data.meshes.new(name)
    nm.from_pydata(verts, [], faces)
    nm.validate(clean_customdata=False)
    for m in me.materials:
        nm.materials.append(m)
    if len(nm.polygons) == len(mats):
        nm.polygons.foreach_set("material_index", mats)
    if uvlay is not None and len(uvs) == len(nm.loops) * 2:
        nm.uv_layers.new(name=uvlay.name).data.foreach_set("uv", uvs)

    nob = bpy.data.objects.new(name, nm)
    scn.collection.objects.link(nob)
    nob.parent = ob.parent
    nob.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    nob.matrix_basis = ob.matrix_basis.copy()
    return nob


def split_mesh(ob, rules):
    """Partition ob's faces by the rules and return the resulting objects."""
    me = ob.data
    mw = ob.matrix_world
    matnames = [m.name if m else "" for m in me.materials]
    groups = {}
    for p in me.polygons:
        c = mw @ p.center
        mn = matnames[p.material_index] if p.material_index < len(matnames) else ""
        for name, pred in rules:
            if pred(c.x, c.y, c.z, mn):
                groups.setdefault(name, []).append(p.index)
                break

    present = [n for n, _ in rules if groups.get(n)]
    if len(present) <= 1:
        if present:
            ob.name = present[0]
            ob.data.name = present[0]
        return [ob]

    out = [_submesh(ob, groups[name], name) for name in present]
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


parts = []
for src_name, rules in SPLITS.items():
    ob = scn.objects.get(src_name)
    if ob is None:
        continue
    parts.extend(split_mesh(ob, rules))

# Each part needs its own materials, because the web viewer fades a part by
# setting alpha on the material named after it and these parts share the rig's
# three paint materials. Copies share their image datablocks, so the textures
# are still exported only once.
for ob in parts:
    for i, m in enumerate(list(ob.data.materials)):
        if m is None:
            continue
        copy = m.copy()
        copy.name = ob.name if i == 0 else "%s.%s" % (ob.name, m.name)
        ob.data.materials[i] = copy

meshes = [o for o in scn.objects if o.type == "MESH"]
tris_before = sum(len(o.data.loop_triangles) for o in meshes
                  if (o.data.calc_loop_triangles() or True))
print("triangles before decimate: %d" % tris_before)
for o in meshes:
    print("  part %-22s tris=%-7d parent=%s"
          % (o.name, len(o.data.loop_triangles),
             o.parent.name if o.parent else None))

# --- decimate ---------------------------------------------------------------
ratio = min(1.0, float(TRI_TARGET) / float(tris_before))
for o in meshes:
    o.data.calc_loop_triangles()
    n = len(o.data.loop_triangles)
    if n < 12000:
        continue           # already cheap; collapsing it only costs detail
    mod = o.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.calc_loop_triangles()
    print("decimated %-16s %d -> %d" % (o.name, n, len(o.data.loop_triangles)))

for o in meshes:
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception:
        pass

bpy.context.view_layer.update()

# --- report -----------------------------------------------------------------
mn = Vector((1e18,) * 3)
mx = Vector((-1e18,) * 3)
tris = 0
rows = []
for o in meshes:
    o.data.calc_loop_triangles()
    t = len(o.data.loop_triangles)
    tris += t
    omn = Vector((1e18,) * 3)
    omx = Vector((-1e18,) * 3)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
            omn[i] = min(omn[i], w[i]); omx[i] = max(omx[i], w[i])
    rows.append({"name": o.name, "tris": t,
                 "bbox_min": [round(v, 3) for v in omn],
                 "bbox_max": [round(v, 3) for v in omx],
                 "materials": [m.name for m in o.data.materials]})

info = {"tris": tris, "tris_before": tris_before, "decimate_ratio": ratio,
        "size_m": [round(mx[i] - mn[i], 3) for i in range(3)],
        "bbox_min": [round(v, 3) for v in mn],
        "bbox_max": [round(v, 3) for v in mx],
        "nulls": [o.name for o in scn.objects if o.type == "EMPTY"],
        "meshes": rows}
with open(OUT_JSON, "w") as f:
    json.dump(info, f, indent=1)
print("INFO " + json.dumps({k: v for k, v in info.items() if k != "meshes"}))
for r in rows:
    print("  %-16s tris=%-7d %s" % (r["name"], r["tris"], r["materials"]))

bpy.ops.object.select_all(action="SELECT")
common = dict(
    export_format="GLB", use_selection=True,
    export_yup=True, export_apply=True, export_materials="EXPORT",
    export_image_format="AUTO", export_jpeg_quality=80,
    export_normals=True, export_texcoords=True,
    export_cameras=False, export_lights=False,
)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, **common)
print("EXPORTED %s %d bytes" % (OUT_GLB, os.path.getsize(OUT_GLB)))

# Draco roughly quarters the geometry, at the cost of needing a decoder that
# model-viewer fetches from a CDN. Both files are written so the plain one
# stays available if the decoder turns out to be a problem on the tablet.
# 14-bit positions over a 20 m machine is about 1 mm, far finer than needed.
draco_path = OUT_GLB.replace(".glb", "-draco.glb")
bpy.ops.export_scene.gltf(
    filepath=draco_path,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=10,
    export_draco_texcoord_quantization=12,
    **common)
print("EXPORTED %s %d bytes" % (draco_path, os.path.getsize(draco_path)))
