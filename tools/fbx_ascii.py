"""A minimal reader for ASCII FBX 7.x -- enough to rebuild meshes and a rig.

Blender only imports *binary* FBX; it refuses ASCII outright. This reads the
ASCII form directly so no converter has to be downloaded.

ASCII FBX is a nested, tab-indented text format:

    Objects:  {
        Geometry: 3799889728, "Geometry::", "Mesh" {
            Vertices: *715230 {
                a: 1.0,2.0,3.0,
    4.0,5.0,6.0
            }
            PolygonVertexIndex: *925588 {
                a: 0,1,-3,...
            }
        }
    }
    Connections:  {
        C: "OO",3711269408,3711286944
    }

Two things make a naive line parser wrong, and both are handled here:

* Big arrays wrap onto continuation lines that carry NO indentation and no
  key, so indentation alone cannot tell you where a block ends. The reader
  tracks an explicit array state instead and stops on the closing brace.
* The last index of every polygon in PolygonVertexIndex is bit-inverted
  (stored as ~i, a negative number) to mark the end of the face.

Only the arrays actually needed are materialised. Normals, binormals,
tangents and smoothing are skipped without being accumulated, which is what
keeps a 282 MB file to a sane peak memory.
"""
import re

BLOCK = re.compile(r'^\s*([A-Za-z0-9_]+):\s*(.*?)\s*\{\s*$')
ARRAY = re.compile(r'^\s*([A-Za-z0-9_]+):\s*\*(\d+)\s*\{\s*$')
CLOSE = re.compile(r'^\s*\}\s*$')
OBJECT = re.compile(
    r'^\s*(Model|Geometry|Material|Texture|Video|NodeAttribute):\s*'
    r'(\d+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\{')
CONN = re.compile(r'^\s*C:\s*"(O[OP])"\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*"([^"]*)")?')
PROP = re.compile(r'^\s*P:\s*"([^"]+)"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*(?:,(.*))?$')
STRFIELD = re.compile(r'^\s*(RelativeFilename|FileName|Filename|Media|'
                      r'MappingInformationType|ReferenceInformationType|Name):\s*"([^"]*)"')

# Arrays worth keeping. Everything else inside a Geometry is stepped over.
WANTED_ARRAYS = {"Vertices", "PolygonVertexIndex", "UV", "UVIndex", "Materials"}


def _numbers(chunks, as_int):
    """Flatten the collected text of an array into a list of numbers."""
    text = "".join(chunks)
    out = []
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(int(tok) if as_int else float(tok))
    return out


def parse(path):
    """Return {geometries, models, materials, textures, videos, connections}."""
    geometries = {}
    models = {}
    materials = {}
    textures = {}
    videos = {}
    connections = []          # (kind, child_id, parent_id, prop_name)

    # Where we are: a stack of (kind, id) for the object blocks, and a shallow
    # stack of plain block names so LayerElement* can be told apart.
    obj_stack = []
    name_stack = []
    cur_geo = None
    cur_layer = None          # name of the LayerElement* we are inside

    in_array = None           # (key, count, chunks, as_int) or None
    skip_array_depth = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # ---- inside an array we are collecting --------------------
            if in_array is not None:
                if CLOSE.match(line):
                    key, _n, chunks, as_int = in_array
                    vals = _numbers(chunks, as_int)
                    in_array = None
                    name_stack.pop()
                    if cur_geo is not None:
                        if key in ("UV", "UVIndex") and cur_layer == "LayerElementUV":
                            cur_geo[key] = vals
                        elif key == "Materials" and cur_layer == "LayerElementMaterial":
                            cur_geo["Materials"] = vals
                        elif key in ("Vertices", "PolygonVertexIndex"):
                            cur_geo[key] = vals
                    continue
                s = line.strip()
                if s.startswith("a:"):
                    s = s[2:]
                in_array[2].append(s)
                continue

            # ---- inside an array we are deliberately ignoring ----------
            if skip_array_depth is not None:
                if CLOSE.match(line):
                    skip_array_depth = None
                    name_stack.pop()
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            m = ARRAY.match(line)
            if m:
                key, count = m.group(1), int(m.group(2))
                name_stack.append(key)
                if key in WANTED_ARRAYS and cur_geo is not None:
                    as_int = key in ("PolygonVertexIndex", "UVIndex", "Materials")
                    in_array = (key, count, [], as_int)
                else:
                    skip_array_depth = len(name_stack)
                continue

            m = OBJECT.match(line)
            if m:
                kind, oid, fullname, subtype = m.group(1), int(m.group(2)), m.group(3), m.group(4)
                name = fullname.split("::", 1)[-1]
                rec = {"id": oid, "name": name, "subtype": subtype, "props": {}}
                if kind == "Geometry":
                    geometries[oid] = rec
                    cur_geo = rec
                elif kind == "Model":
                    models[oid] = rec
                elif kind == "Material":
                    materials[oid] = rec
                elif kind == "Texture":
                    textures[oid] = rec
                elif kind == "Video":
                    videos[oid] = rec
                obj_stack.append((kind, oid, rec))
                name_stack.append(kind)
                continue

            m = BLOCK.match(line)
            if m:
                key = m.group(1)
                name_stack.append(key)
                if key.startswith("LayerElement"):
                    cur_layer = key
                continue

            if CLOSE.match(line):
                if name_stack:
                    closed = name_stack.pop()
                    if closed.startswith("LayerElement"):
                        cur_layer = None
                    if obj_stack and obj_stack[-1][0] == closed:
                        kind, _oid, _rec = obj_stack.pop()
                        if kind == "Geometry":
                            cur_geo = None
                continue

            m = CONN.match(line)
            if m:
                connections.append((m.group(1), int(m.group(2)),
                                    int(m.group(3)), m.group(4)))
                continue

            m = PROP.match(line)
            if m and obj_stack:
                key, rest = m.group(1), (m.group(2) or "")
                rec = obj_stack[-1][2]
                vals = []
                for tok in rest.split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    try:
                        vals.append(float(tok))
                    except ValueError:
                        vals.append(tok.strip('"'))
                rec["props"][key] = vals
                continue

            m = STRFIELD.match(line)
            if m and obj_stack:
                obj_stack[-1][2][m.group(1)] = m.group(2)
                # MappingInformationType belongs to the layer, not the object.
                if cur_geo is not None and cur_layer and m.group(1) in (
                        "MappingInformationType", "ReferenceInformationType"):
                    cur_geo[cur_layer + "." + m.group(1)] = m.group(2)
                continue

    return {"geometries": geometries, "models": models, "materials": materials,
            "textures": textures, "videos": videos, "connections": connections}


def polygons(poly_index):
    """Split a PolygonVertexIndex array into faces.

    The last corner of every face is stored bit-inverted, which is how the
    format marks the end of a face without writing a per-face count.
    """
    faces = []
    cur = []
    for i in poly_index:
        if i < 0:
            cur.append(~i)
            faces.append(cur)
            cur = []
        else:
            cur.append(i)
    return faces
