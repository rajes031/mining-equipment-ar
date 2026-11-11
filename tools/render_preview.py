"""
render_preview.py -- offline preview renders of the generated GLB models.

A ~150-line painter's-algorithm rasteriser (numpy + PIL). Its job is twofold:
a sanity check that the geometry really looks like the machine before anyone
loads it on a tablet, and the catalogue thumbnails for the web app. It is not
a shader-accurate preview -- the phone does the real rendering.

Run:  python render_preview.py
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

LIGHT = np.array([-0.45, 0.78, -0.44])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
SKY = (236, 240, 245)
GROUND = (206, 203, 196)


# ---------------------------------------------------------------- GLB reader

def read_glb(path: Path):
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"{path.name} is not a glTF 2.0 binary")
    off, gltf, blob = 12, None, b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            blob = chunk
        off += 8 + clen
    if gltf is None:
        raise ValueError("no JSON chunk")

    dtypes = {5126: "<f4", 5125: "<u4", 5123: "<u2"}
    counts = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}

    def accessor(i):
        acc = gltf["accessors"][i]
        view = gltf["bufferViews"][acc["bufferView"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = acc["count"] * counts[acc["type"]]
        arr = np.frombuffer(blob, dtype=np.dtype(dtypes[acc["componentType"]]),
                            count=n, offset=start)
        return arr.reshape(acc["count"], counts[acc["type"]])

    parts = []

    def walk(node_index, offset):
        """Flatten the node hierarchy, accumulating translations.

        Parts that declare a pivot store their geometry relative to that joint
        and carry the offset on the node, so the preview has to resolve the
        hierarchy rather than read positions straight out of the buffers.
        """
        node = gltf["nodes"][node_index]
        here = offset + np.array(node.get("translation", (0, 0, 0)), dtype=np.float64)
        if "mesh" in node:
            mesh = gltf["meshes"][node["mesh"]]
            for prim in mesh["primitives"]:
                pos = accessor(prim["attributes"]["POSITION"]).astype(np.float64) + here
                nrm = accessor(prim["attributes"]["NORMAL"]).astype(np.float64)
                idx = accessor(prim["indices"]).reshape(-1).astype(np.int64)
                pbr = gltf["materials"][prim["material"]]["pbrMetallicRoughness"]
                parts.append({
                    "name": node.get("name", mesh.get("name", "?")),
                    "tris": pos[idx].reshape(-1, 3, 3),
                    "normals": nrm[idx].reshape(-1, 3, 3)[:, 0, :],
                    "color": np.array(pbr["baseColorFactor"][:3]),
                    "alpha": pbr["baseColorFactor"][3],
                    "metallic": pbr.get("metallicFactor", 0.0),
                })
        for child in node.get("children", []):
            walk(child, here)

    for root in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
        walk(root, np.zeros(3))
    return parts


# ---------------------------------------------------------------- rasteriser

def look_at(eye, target, up=(0, 1, 0)):
    eye, target = np.asarray(eye, float), np.asarray(target, float)
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = r, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def render(parts, out_png: Path, size=(1000, 640), fov_deg=32.0,
           azimuth=38.0, elevation=16.0, distance_factor=1.9, grid=True):
    verts = np.vstack([p["tris"].reshape(-1, 3) for p in parts])
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    centre = (lo + hi) / 2.0
    centre[1] = lo[1] + (hi[1] - lo[1]) * 0.42
    radius = float(np.linalg.norm(hi - lo)) / 2.0

    az, el = math.radians(azimuth), math.radians(elevation)
    dist = radius * distance_factor / math.tan(math.radians(fov_deg) / 2) * 0.55
    eye = centre + dist * np.array([math.sin(az) * math.cos(el),
                                    math.sin(el),
                                    math.cos(az) * math.cos(el)])
    view = look_at(eye, centre)

    W, H = size
    aspect = W / H
    fy = 1.0 / math.tan(math.radians(fov_deg) / 2)
    fx = fy / aspect

    def project(pts):
        """World -> screen pixels + view-space depth."""
        homog = np.hstack([pts, np.ones((len(pts), 1))])
        vs = (homog @ view.T)[:, :3]
        depth = -vs[:, 2]
        safe = np.where(depth < 1e-6, 1e-6, depth)
        sx = (vs[:, 0] * fx / safe * 0.5 + 0.5) * W
        sy = (0.5 - vs[:, 1] * fy / safe * 0.5) * H
        return np.stack([sx, sy], axis=1), depth

    img = Image.new("RGB", (W, H), SKY)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([0, int(H * 0.52), W, H], fill=GROUND)

    faces = []   # (depth, polygon, fill)

    if grid:
        step, extent = 2.0, max(radius * 1.6, 12.0)
        n = int(extent / step)
        for i in range(-n, n + 1):
            for a, bpt in (((i * step, 0, -extent), (i * step, 0, extent)),
                           ((-extent, 0, i * step), (extent, 0, i * step))):
                pts, dep = project(np.array([a, bpt], dtype=float))
                if dep.min() <= 0.1:
                    continue
                faces.append((dep.mean() + 1e4, [tuple(pts[0]), tuple(pts[1])],
                              (188, 184, 176, 255)))

    for part in parts:
        tris, normals = part["tris"], part["normals"]
        cents = tris.mean(axis=1)
        to_eye = eye - cents
        facing = np.einsum("ij,ij->i", normals, to_eye)
        shade = np.clip(normals @ LIGHT, 0, 1)
        base = part["color"]
        tint = 0.22 + 0.78 * shade
        spec = 0.18 * part["metallic"] * np.clip(normals @ LIGHT, 0, 1) ** 8
        alpha = int(round(255 * (0.55 if part["alpha"] < 1 else 1.0)))

        flat = tris.reshape(-1, 3)
        pts, dep = project(flat)
        pts, dep = pts.reshape(-1, 3, 2), dep.reshape(-1, 3)

        for i in range(len(tris)):
            if facing[i] <= 0 or dep[i].min() <= 0.05:
                continue
            rgb = np.clip(base * tint[i] + spec[i], 0, 1)
            rgb = np.clip(rgb ** (1 / 2.2) * 255, 0, 255).astype(int)
            faces.append((float(dep[i].mean()),
                          [tuple(p) for p in pts[i]],
                          (int(rgb[0]), int(rgb[1]), int(rgb[2]), alpha)))

    for _, poly, fill in sorted(faces, key=lambda f: -f[0]):
        if len(poly) == 2:
            draw.line(poly, fill=fill, width=1)
        else:
            draw.polygon(poly, fill=fill)

    img.save(out_png, optimize=True)
    return out_png


def main():
    views = {
        "": dict(azimuth=38.0, elevation=16.0),
        "-front": dict(azimuth=-18.0, elevation=11.0),
        "-rear": dict(azimuth=150.0, elevation=18.0),
    }
    for name in ("dumper", "shovel"):
        parts = read_glb(WEB / "models" / f"{name}.glb")
        for suffix, kw in views.items():
            out = WEB / "models" / f"{name}{suffix}.png"
            render(parts, out, **kw)
            print(f"{out.name:22s} {out.stat().st_size/1024:6.1f} KB")


if __name__ == "__main__":
    main()
