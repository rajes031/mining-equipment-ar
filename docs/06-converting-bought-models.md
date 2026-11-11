# Converting a bought 3D model into a teaching GLB

The machines in `tools/make_dumper.py` and `tools/make_shovel.py` are drawn
from scratch by code. The two in this document came the other way: bought as
3D-marketplace asset packs and converted. The route is different enough to be
worth writing down, because almost none of it is obvious.

Both converters need **Blender** (4.3 was used) and run headless:

```bash
blender -b -noaudio --python tools/make_dumper_glb.py -- <in.obj> <out.glb> <out.json>
```

## What a bought asset usually gets wrong

**It is not at real-world size.** The haul truck arrived 4.21 m long. That is
nobody's mistake — marketplace models are built to look right, not to measure
right — but a 1:1 AR app lives or dies on the scale being true. Check the
overall length against a real machine of the class before anything else.

**It has no part structure.** The truck was one mesh with two materials: no
tyres, no body, no cab, nothing to label or highlight. See below.

**Its textures may be unusable.** The truck's maps were only in a `.sbsar`, a
procedural Substance archive that needs Substance Player to render out. The
GLB uses flat PBR colours instead. The drill rig was luckier — its `fbx`
folder shipped BaseColor / Normal / OcclusionRoughnessMetallic, which is
exactly glTF's own packing.

**The units are declared in the file, so read them.** The truck's OBJ header
says centimetres; the FBX says `UnitScaleFactor: 1`, also centimetres. Both
converters apply a 1/100 factor. Forget it and the model is a hundred times
too big, which in AR means it never appears at all.

## Recovering parts from a single mesh

A model that looks like one lump usually is not. It was modelled as separate
solids that were never topologically joined, so **separating by loose parts**
gets them back — 231 shells for the haul truck.

Those shells are unnamed, so they are grouped into assemblies by **where they
sit in the machine's own bounding box**. That is stable, because the geometry
never moves. Front and rear were worked out from the wheels: one end carried
twice as many shells as the other, i.e. dual tyres, i.e. the drive axle of a
rear-dump truck.

Always render the result with one flat colour per group before trusting it.
A wrong rule looks perfectly fine once everything is painted the same yellow.

On the drill rig, loose separation is useless — the crawler alone is a
hundred-odd track shoes and Blender takes minutes to make that many objects.
There, `tools/make_drill_glb.py` partitions faces by centroid instead, using
split planes read off a histogram of the real geometry.

## Per-part materials are not optional

`web/viewer.js` highlights and isolates a part by setting alpha on **the
material named after it**, because model-viewer can address materials but not
nodes. So every converter gives each part its own material, named for the
part. A part made of more than one substance gets extra materials named
`<part>.<something>` — `operator_cab.glass_window` — and the viewer fades all
of a part's materials together. Without that, isolating the tyres leaves the
cab windows hanging in mid-air.

Material copies share their image datablocks, so the textures are still
exported only once.

## ASCII FBX: Blender will not open it

The drill rig is a 282 MB **ASCII** FBX. Blender's importer reads binary FBX
only and refuses ASCII outright:

```
RuntimeError: Error: ASCII FBX files are not supported
```

`tools/fbx_ascii.py` reads it directly, so no converter has to be downloaded.
It is about 200 lines. Two things make a naive line parser wrong:

* Large arrays wrap onto continuation lines carrying **no indentation and no
  key**, so indentation cannot tell you where a block ends.
* The last corner of every polygon in `PolygonVertexIndex` is **bit-inverted**
  (stored as `~i`, a negative number) to mark the end of the face.

It skips the arrays nobody needs — normals, binormals, tangents, smoothing —
without accumulating them, which is what keeps a 282 MB file fast and the peak
memory sane. The whole parse takes about a second.

Transforms are rebuilt as `T * PreRotation * R * S`, with EulerXYZ order,
which matches Blender's `"XYZ"`. `GeometricTranslation` is baked into the
vertices, because it offsets the mesh under the node and is **not** inherited
by children. The rig was authored Z-up in 3ds Max and exported Y-up, recorded
as a -90° PreRotation on the root null, so the root is turned +90° back at the
end to stand it up in Blender's world.

## Budgets

| | triangles | GLB |
|---|---|---|
| Drill rig as supplied | 704,533 | — |
| Drill rig shipped | 157,424 | 3.3 MB |
| Haul truck shipped | 20,416 | 0.8 MB |

Textures were 4K; they are rescaled to 1024. Note that Blender's
`image.scale()` only resizes the in-memory buffer — `pack()` and the glTF
exporter both go back to the file on disk, so the resized buffer has to be
**written out and the datablock repointed at it**. Miss that and the export
still carries the 4K originals: 27 MB instead of 10 MB.

The drill rig is **Draco-compressed** (10.4 MB → 3.3 MB). model-viewer fetches
the Draco decoder from `gstatic.com` on demand, so that model needs the
network for a little more than its own bytes. If that is ever a problem,
`make_drill_glb.py` writes the uncompressed GLB alongside it; swap the file.

## Licensing

These GLBs are derived from purchased asset packs, and publishing one on a
public site makes it downloadable. Neither pack shipped a licence file. Check
the marketplace terms before publishing a converted model, and keep the
original `.rar` archives — they are the only record of what was bought.
