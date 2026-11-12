"""
glbgen.py -- a dependency-light glTF 2.0 / GLB writer for parametric machines.

Why this exists: mining-equipment AR needs models that are (a) true to scale in
metres, (b) split into *named* parts so the viewer can label them, and (c) small
enough to download over mine-site 4G. Hand-built parametric geometry gives all
three, and needs no Blender on the build machine.

Conventions (glTF): metres, Y up, -Z forward. Model origin sits on the ground
plane at the machine's centre, which is what ARCore expects for floor placement.

API
---
    b = Builder()
    b.material("cat_yellow", (0.98, 0.70, 0.05), roughness=0.55)
    p = b.part("dump_body", "cat_yellow", label="Dump body (tray)",
               note="Holds the payload; tipped by twin hoist cylinders.")
    p.box(center=(0, 4, 0), size=(6, 2, 10))
    p.cyl(center=(0, 1, 0), radius=0.4, length=3, axis="x")
    b.write("out.glb", parts_json="out.parts.json")

Each part is merged into one mesh/node, so part count == draw calls. Keep parts
in the low tens for mobile.
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- transforms


def identity() -> np.ndarray:
    return np.eye(4, dtype=np.float64)


def translate(x: float, y: float, z: float) -> np.ndarray:
    m = identity()
    m[:3, 3] = (x, y, z)
    return m


def rotate(axis: str, degrees: float) -> np.ndarray:
    """Right-handed rotation about a principal axis."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    m = identity()
    if axis == "x":
        m[1, 1], m[1, 2], m[2, 1], m[2, 2] = c, -s, s, c
    elif axis == "y":
        m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c
    elif axis == "z":
        m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c
    else:
        raise ValueError("axis must be x, y or z (got %r)" % axis)
    return m


def compose(*mats: np.ndarray) -> np.ndarray:
    """compose(A, B) applies B first, then A."""
    out = identity()
    for m in mats:
        out = out @ m
    return out


def _apply(xform, verts: np.ndarray) -> np.ndarray:
    if xform is None:
        return verts
    homog = np.hstack([verts, np.ones((len(verts), 1))])
    return (homog @ xform.T)[:, :3]


# ---------------------------------------------------------------- primitives

_BOX_FACES = (
    # signed unit corners per face, wound CCW as seen from outside
    ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),      # +Z
    ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)),  # -Z
    ((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)),      # +X
    ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),  # -X
    ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)),      # +Y
    ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),  # -Y
)


class Part:
    """Accumulates triangles for one named, single-material component."""

    def __init__(self, name, material, label="", note="", hotspot=None,
                 hotspot_normal=(0, 1, 0), pivot=None, parent=None):
        self.name = name
        self.material = material
        # `pivot` is the joint this part rotates about (world coords). Geometry
        # is re-centred on it and the node is translated back, so rotating the
        # node in Unity or three.js swings the part about its real hinge.
        # `parent` chains parts (boom -> stick -> bucket) so a parent's rotation
        # carries its children, which is what makes a dig cycle animatable.
        self.pivot = None if pivot is None else tuple(float(v) for v in pivot)
        self.parent = parent
        self.label = label or name.replace("_", " ").capitalize()
        self.note = note
        self._hotspot = hotspot
        self.hotspot_normal = hotspot_normal
        self._tris = []     # list of (3, 3) float arrays
        self._groups = []   # (start, end) spans of one convex primitive each

    # -- geometry helpers ---------------------------------------------------

    def _begin(self):
        return len(self._tris)

    def _end(self, start, ref=None, invert=False):
        """Close a convex primitive so its normals can be auto-oriented.

        Faces are made to point away from `ref` (default: the primitive's own
        centroid, correct for any star-shaped solid). `invert=True` points them
        towards it instead -- used for the bore of an annulus, where "outward"
        for the surface means inward towards the axis.
        """
        if len(self._tris) > start:
            ref_pt = None if ref is None else np.asarray(ref, dtype=np.float64)
            self._groups.append((start, len(self._tris), ref_pt, invert))

    def tri(self, a, b, c):
        self._tris.append(np.array([a, b, c], dtype=np.float64))
        return self

    def quad(self, a, b, c, d):
        """Quad wound CCW from outside -> two triangles."""
        self.tri(a, b, c)
        self.tri(a, c, d)
        return self

    def box(self, center=(0, 0, 0), size=(1, 1, 1), xform=None):
        start = self._begin()
        cx, cy, cz = center
        hx, hy, hz = (s / 2.0 for s in size)
        for face in _BOX_FACES:
            pts = np.array([(cx + sx * hx, cy + sy * hy, cz + sz * hz)
                            for sx, sy, sz in face], dtype=np.float64)
            self.quad(*_apply(xform, pts))
        self._end(start)
        return self

    def prism(self, profile, extent, axis="x", offset=(0, 0, 0), xform=None):
        """Extrude a convex 2D polygon by `extent` along `axis` (winding free).

        The profile's (u, v) map onto the two axes other than `axis`:
            axis='x' : u = z, v = y   (side profile -- e.g. a truck tray)
            axis='y' : u = x, v = z   (plan profile)
            axis='z' : u = x, v = y   (front profile)
        """
        start = self._begin()
        prof = np.asarray(profile, dtype=np.float64)
        if len(prof) < 3:
            raise ValueError("profile needs >= 3 points")
        h = extent / 2.0
        ox, oy, oz = offset

        def pt(u, v, w):
            if axis == "x":
                return (ox + w, oy + v, oz + u)
            if axis == "y":
                return (ox + u, oy + w, oz + v)
            if axis == "z":
                return (ox + u, oy + v, oz + w)
            raise ValueError("axis must be x, y or z (got %r)" % axis)

        near = _apply(xform, np.array([pt(u, v, -h) for u, v in prof]))
        far = _apply(xform, np.array([pt(u, v, h) for u, v in prof]))

        n = len(prof)
        for i in range(1, n - 1):          # caps, fan triangulation
            self.tri(far[0], far[i], far[i + 1])
            self.tri(near[0], near[i + 1], near[i])
        for i in range(n):                 # walls
            j = (i + 1) % n
            self.quad(near[i], near[j], far[j], far[i])
        self._end(start)
        return self

    def cyl(self, center=(0, 0, 0), radius=1.0, length=1.0, axis="y",
            segments=16, caps=True, inner_radius=0.0, xform=None):
        """Cylinder, or annulus when inner_radius > 0 (tyres, rings, pipes)."""
        cx, cy, cz = center
        h = length / 2.0
        ring = [(math.cos(2 * math.pi * i / segments),
                 math.sin(2 * math.pi * i / segments)) for i in range(segments)]

        def pt(u, v, w):
            if axis == "x":
                return (cx + w, cy + v, cz + u)
            if axis == "y":
                return (cx + u, cy + w, cz + v)
            if axis == "z":
                return (cx + u, cy + v, cz + w)
            raise ValueError("axis must be x, y or z (got %r)" % axis)

        def P(u, v, w):
            return _apply(xform, np.array([pt(u, v, w)]))[0]

        R, r = radius, inner_radius
        axis_pt = P(0, 0, 0)

        outer = self._begin()
        for i in range(segments):
            j = (i + 1) % segments
            (ux, uy), (vx, vy) = ring[i], ring[j]
            a = P(ux * R, uy * R, -h)
            b = P(vx * R, vy * R, -h)
            c = P(vx * R, vy * R, h)
            d = P(ux * R, uy * R, h)
            self.quad(a, b, c, d)                       # outer wall
            if caps:
                if r > 0:
                    ai = P(ux * r, uy * r, -h)
                    bi = P(vx * r, vy * r, -h)
                    ci = P(vx * r, vy * r, h)
                    di = P(ux * r, uy * r, h)
                    self.quad(d, c, ci, di)             # +w ring face
                    self.quad(b, a, ai, bi)             # -w ring face
                else:
                    self.tri(P(0, 0, h), c, d)
                    self.tri(P(0, 0, -h), a, b)
        self._end(outer, ref=axis_pt)

        if r > 0:                                       # the bore faces inward
            bore = self._begin()
            for i in range(segments):
                j = (i + 1) % segments
                (ux, uy), (vx, vy) = ring[i], ring[j]
                self.quad(P(ux * r, uy * r, -h), P(vx * r, vy * r, -h),
                          P(vx * r, vy * r, h), P(ux * r, uy * r, h))
            self._end(bore, ref=axis_pt, invert=True)
        return self

    # -- output -------------------------------------------------------------

    def bounds(self):
        v = np.vstack(self._tris)
        return v.min(axis=0), v.max(axis=0)

    def hotspot(self):
        """Anchor point for a viewer annotation: explicit, else bbox centre."""
        if self._hotspot is not None:
            return tuple(float(x) for x in self._hotspot)
        lo, hi = self.bounds()
        return tuple(float(x) for x in (lo + hi) / 2.0)

    def _oriented_tris(self):
        """Triangles with every convex primitive's faces wound outwards."""
        tris = [t.copy() for t in self._tris]
        for start, end, ref, invert in self._groups:
            span = tris[start:end]
            ref_pt = ref
            if ref_pt is None:
                ref_pt = np.vstack(span).mean(axis=0)
            for t in span:
                n = np.cross(t[1] - t[0], t[2] - t[0])
                outward = np.dot(n, t.mean(axis=0) - ref_pt)
                if (outward < 0) != bool(invert):
                    t[[1, 2]] = t[[2, 1]]
        return tris

    def mesh_arrays(self):
        """-> positions (float32), normals (float32), indices (uint32).

        Flat-shaded: every triangle gets its own three vertices. Faceted is the
        right look for plate-steel machinery and keeps the writer trivial.
        """
        tris = np.vstack(self._oriented_tris()).astype(np.float32)
        n_tri = len(tris) // 3
        a, b, c = tris[0::3], tris[1::3], tris[2::3]
        face_n = np.cross(b - a, c - a)
        lens = np.linalg.norm(face_n, axis=1, keepdims=True)
        lens[lens == 0] = 1.0
        normals = np.repeat(face_n / lens, 3, axis=0).astype(np.float32)
        return tris, normals, np.arange(n_tri * 3, dtype=np.uint32)

    @property
    def triangle_count(self):
        return len(self._tris)

    # -- composition --------------------------------------------------------

    def transform(self, xform):
        """Move this part bodily by a 4x4 transform.

        Used when two separately-built machines are composed into one scene.
        The orientation reference points move with the geometry, so normals
        still come out facing the right way; the hotspot normal gets the
        rotation only, being a direction rather than a position.
        """
        self._tris = [_apply(xform, t) for t in self._tris]
        self._groups = [
            (s, e, None if r is None else _apply(xform, np.array([r]))[0], inv)
            for s, e, r, inv in self._groups
        ]
        if self.pivot is not None:
            self.pivot = tuple(_apply(xform, np.array([self.pivot]))[0])
        if self._hotspot is not None:
            self._hotspot = tuple(_apply(xform, np.array([self._hotspot]))[0])
        rot = np.asarray(xform, dtype=np.float64)[:3, :3]
        self.hotspot_normal = tuple(rot @ np.asarray(self.hotspot_normal,
                                                     dtype=np.float64))
        return self


class Group:
    """A node with no geometry: somewhere to hang parts from and animate.

    A part can only be rotated about its own pivot, which is right for a boom
    or a dump body but no use for moving a whole machine along a haul road.
    A group gives the scene a handle for that.
    """

    def __init__(self, name, origin=(0.0, 0.0, 0.0), parent=None):
        self.name = name
        self.origin = tuple(float(v) for v in origin)
        self.parent = parent


def euler_to_quat(xyz_degrees):
    """Intrinsic XYZ Euler angles in degrees -> glTF (x, y, z, w) quaternion.

    Authoring animation in degrees per axis is far easier to read than
    quaternions, and every rotation in these models is about a single axis
    anyway -- swing about Y, boom and bucket about X.
    """
    rx, ry, rz = (math.radians(a) / 2.0 for a in xyz_degrees)
    c1, s1 = math.cos(rx), math.sin(rx)
    c2, s2 = math.cos(ry), math.sin(ry)
    c3, s3 = math.cos(rz), math.sin(rz)
    return (
        s1 * c2 * c3 + c1 * s2 * s3,
        c1 * s2 * c3 - s1 * c2 * s3,
        c1 * c2 * s3 + s1 * s2 * c3,
        c1 * c2 * c3 - s1 * s2 * s3,
    )


class Builder:
    def __init__(self, name="model"):
        self.name = name
        self._materials = {}
        self._material_defs = []
        self._parts = []
        self._node_groups = []
        self._animations = []

    def material(self, key, color, roughness=0.6, metallic=0.1, alpha=1.0,
                 double_sided=False):
        if key in self._materials:
            return key
        mat = {
            "name": key,
            "pbrMetallicRoughness": {
                "baseColorFactor": [color[0], color[1], color[2], alpha],
                "metallicFactor": metallic,
                "roughnessFactor": roughness,
            },
            "doubleSided": double_sided,
        }
        if alpha < 1.0:
            mat["alphaMode"] = "BLEND"
        self._materials[key] = len(self._material_defs)
        self._material_defs.append(mat)
        return key

    def group(self, name, origin=(0.0, 0.0, 0.0), parent=None):
        g = Group(name, origin, parent)
        self._node_groups.append(g)
        return g

    def _group_names(self):
        return {g.name for g in self._node_groups}

    def part(self, name, material, **kw):
        if material not in self._materials:
            raise KeyError("material %r not defined" % material)
        parent = kw.get("parent")
        if parent is not None:
            known = [q.name for q in self._parts]
            if parent not in known and parent not in self._group_names():
                raise KeyError("parent %r must be created first" % parent)
            # A part hung off another PART needs its own pivot, because the
            # only reason to do that is to hinge it. A part hung off a GROUP
            # is just being carried along, so it needs no pivot of its own.
            if parent in known and kw.get("pivot") is None:
                raise ValueError("part %r has a parent so it needs a pivot: "
                                 "its geometry must be expressed relative to "
                                 "the joint it hangs from" % name)
        p = Part(name, material, **kw)
        self._parts.append(p)
        return p

    def absorb(self, other, prefix="", xform=None, parent=None, drop=()):
        """Pull another Builder's materials and parts into this one.

        Lets a scene be composed from machines that were each written as a
        standalone generator, rather than copying their geometry code. Parts
        are renamed with `prefix` (so two machines can both have a `cab`),
        moved by `xform`, and any part that was a root over there is hung off
        `parent` here.
        """
        for key, idx in other._materials.items():
            if key not in self._materials:
                defn = json.loads(json.dumps(other._material_defs[idx]))
                self._materials[key] = len(self._material_defs)
                self._material_defs.append(defn)
        added = []
        drop = set(drop)
        for p in other._parts:
            if p.name in drop:
                continue
            if xform is not None:
                p.transform(xform)
            p.name = prefix + p.name
            p.parent = (prefix + p.parent) if p.parent else parent
            self._parts.append(p)
            added.append(p)
        return added

    def animate(self, name, channels):
        """Add a glTF animation.

        `channels` is a list of (node_name, path, times, values) where path is
        "translation", "rotation" or "scale". Rotation values are XYZ Euler
        angles in degrees -- readable, and converted to quaternions on write.
        """
        self._animations.append({"name": name, "channels": list(channels)})
        return self

    # -- glTF assembly ------------------------------------------------------

    def _build_gltf(self):
        blob = bytearray()
        accessors, views, meshes, nodes = [], [], [], []

        def push(data, target=None):
            while len(blob) % 4:          # keep accessors 4-byte aligned
                blob.append(0)
            off = len(blob)
            blob.extend(data)
            view = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
            if target is not None:
                view["target"] = target
            views.append(view)
            return len(views) - 1

        def accessor(view, comp_type, count, type_, lo=None, hi=None):
            acc = {"bufferView": view, "componentType": comp_type,
                   "count": count, "type": type_}
            if lo is not None:
                acc["min"], acc["max"] = list(lo), list(hi)
            accessors.append(acc)
            return len(accessors) - 1

        FLOAT, UINT = 5126, 5125
        ARRAY_BUFFER, ELEMENT_ARRAY = 34962, 34963

        # One material per part, named after the part. Costs nothing at this
        # scale and lets the viewer fade, tint or isolate any single component
        # at runtime through model-viewer's scene-graph API, which can address
        # materials but not nodes.
        materials = []
        for part in self._parts:
            mat = json.loads(json.dumps(self._material_defs[self._materials[part.material]]))
            mat["name"] = part.name
            materials.append(mat)

        index_of = {p.name: i for i, p in enumerate(self._parts)}
        by_name = {p.name: p for p in self._parts}
        groups = {g.name: g for g in self._node_groups}

        def origin_of(name):
            """The point a node's children are expressed relative to."""
            if name in groups:
                return groups[name].origin
            p = by_name.get(name)
            if p is not None and p.pivot is not None:
                return p.pivot
            return (0.0, 0.0, 0.0)

        def node_origin(part):
            """Where this part's node sits, and so what its geometry is
            offset by. Its own pivot if it hinges; otherwise, if it is
            carried by a group, that group's origin; otherwise nothing."""
            if part.pivot is not None:
                return part.pivot
            if part.parent in groups:
                return groups[part.parent].origin
            return None

        for mat_index, part in enumerate(self._parts):
            pos, nrm, idx = part.mesh_arrays()
            local = node_origin(part)
            if local is not None:
                pos = (pos - np.array(local, dtype=np.float32)).astype(np.float32)
            v_pos = push(pos.tobytes(), ARRAY_BUFFER)
            v_nrm = push(nrm.tobytes(), ARRAY_BUFFER)
            v_idx = push(idx.tobytes(), ELEMENT_ARRAY)
            a_pos = accessor(v_pos, FLOAT, len(pos), "VEC3",
                             pos.min(axis=0).tolist(), pos.max(axis=0).tolist())
            a_nrm = accessor(v_nrm, FLOAT, len(nrm), "VEC3")
            a_idx = accessor(v_idx, UINT, len(idx), "SCALAR")
            meshes.append({
                "name": part.name,
                "primitives": [{
                    "attributes": {"POSITION": a_pos, "NORMAL": a_nrm},
                    "indices": a_idx,
                    "material": mat_index,
                    "mode": 4,
                }],
            })
            node = {"name": part.name, "mesh": len(meshes) - 1}
            if local is not None:
                parent_origin = origin_of(part.parent) if part.parent else (0.0,) * 3
                t = [local[i] - parent_origin[i] for i in range(3)]
                if any(abs(v) > 1e-9 for v in t):
                    node["translation"] = t
            nodes.append(node)

        for g in self._node_groups:       # group nodes come after the parts
            index_of[g.name] = len(nodes)
            parent_origin = origin_of(g.parent) if g.parent else (0.0,) * 3
            node = {"name": g.name}
            t = [g.origin[i] - parent_origin[i] for i in range(3)]
            if any(abs(v) > 1e-9 for v in t):
                node["translation"] = t
            nodes.append(node)

        for item in list(self._parts) + list(self._node_groups):
            if item.parent is not None:   # wire the parent chain
                nodes[index_of[item.parent]].setdefault(
                    "children", []).append(index_of[item.name])

        roots = [index_of[i.name]
                 for i in list(self._parts) + list(self._node_groups)
                 if i.parent is None]

        animations = []
        for anim in self._animations:
            samplers, chans = [], []
            for node_name, path, times, values in anim["channels"]:
                if node_name not in index_of:
                    raise KeyError("animation targets unknown node %r" % node_name)
                t = np.asarray(times, dtype=np.float32)
                # Animation accessors are plain data, not vertex attributes,
                # so they take no bufferView target. The input accessor needs
                # min/max; the spec requires it and players rely on it for
                # the clip length.
                a_t = accessor(push(t.tobytes()), FLOAT, len(t), "SCALAR",
                               [float(t.min())], [float(t.max())])
                if path == "rotation":
                    arr = np.array([euler_to_quat(v) for v in values],
                                   dtype=np.float32)
                    kind = "VEC4"
                else:
                    arr = np.asarray(values, dtype=np.float32).reshape(-1, 3)
                    kind = "VEC3"
                if len(arr) != len(t):
                    raise ValueError("channel %s/%s has %d times but %d values"
                                     % (node_name, path, len(t), len(arr)))
                a_v = accessor(push(arr.tobytes()), FLOAT, len(arr), kind)
                samplers.append({"input": a_t, "output": a_v,
                                 "interpolation": "LINEAR"})
                chans.append({"sampler": len(samplers) - 1,
                              "target": {"node": index_of[node_name],
                                         "path": path}})
            animations.append({"name": anim["name"], "samplers": samplers,
                               "channels": chans})

        gltf = {
            "asset": {"version": "2.0", "generator": "glbgen.py (mining-ar)"},
            "scene": 0,
            "scenes": [{"name": self.name, "nodes": roots}],
            "nodes": nodes,
            "meshes": meshes,
            "materials": materials,
            "accessors": accessors,
            "bufferViews": views,
            "buffers": [{"byteLength": len(blob)}],
        }
        if animations:
            gltf["animations"] = animations
        return gltf, bytes(blob)

    def write(self, path, parts_json=None):
        path = Path(path)
        gltf, blob = self._build_gltf()

        json_chunk = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        json_chunk += b" " * (-len(json_chunk) % 4)
        bin_chunk = blob + b"\x00" * (-len(blob) % 4)

        total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
        with path.open("wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(json_chunk), 0x4E4F534A))
            f.write(json_chunk)
            f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
            f.write(bin_chunk)

        # The scale figure is a teaching aid standing beside the machine, not
        # part of it -- it must not inflate the published envelope.
        machine = [p for p in self._parts
                   if not p.name.endswith("scale_figure")] or self._parts
        lo = np.min([p.bounds()[0] for p in machine], axis=0)
        hi = np.max([p.bounds()[1] for p in machine], axis=0)
        summary = {
            "model": self.name,
            "file": path.name,
            "bytes": path.stat().st_size,
            "triangles": sum(p.triangle_count for p in self._parts),
            "parts": [
                {
                    "node": p.name,
                    "label": p.label,
                    "note": p.note,
                    "position": list(p.hotspot()),
                    "normal": list(p.hotspot_normal),
                    "pivot": list(p.pivot) if p.pivot else None,
                    "parent": p.parent,
                    "triangles": p.triangle_count,
                }
                for p in self._parts
            ],
            "extents_m": {
                "width_x": round(float(hi[0] - lo[0]), 2),
                "height_y": round(float(hi[1] - lo[1]), 2),
                "length_z": round(float(hi[2] - lo[2]), 2),
            },
        }
        if parts_json:
            Path(parts_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
