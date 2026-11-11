# Optimising models for phones and tablets

The models here are 160–230 KB and 1 800–2 600 triangles, which is nothing.
That headroom is deliberate: it leaves room for the detailed models you will
eventually import, and it means the app works on a four-year-old tablet over a
weak signal. The moment you bring in a downloaded or CAD-derived machine, these
are the numbers to hold yourself to.

## Budgets that work in practice

| | Per machine | Whole scene |
|---|---|---|
| Triangles | 30 k–100 k | under 300 k |
| Draw calls (materials × parts) | under 40 | under 100 |
| Texture memory | under 30 MB | under 100 MB |
| GLB file size | under 8 MB | — |

A mid-range Android device renders this at 30 fps while also running ARCore's
tracking, which is itself eating a camera stream and a chunk of GPU. AR is not
a normal 3-D budget: assume you get about half the device for your model.

## The order to do things in

**1. Decimate.** In Blender, Modifier → Decimate → Collapse, ratio 0.1–0.3 on
the heavy parts. Mechanical surfaces survive this much better than organic
ones. Delete internal geometry entirely — anything a trainee cannot see from
outside the machine is pure cost.

**2. Reduce material count, not just triangles.** Each material on each mesh is
a draw call. Merging ten shades of grey into one grey is often a bigger win
than another decimation pass.

**3. Bake, don't layer.** Replace a stack of PBR maps with one baked base
colour texture plus a single roughness/metallic map. For teaching models, flat
colours with good shading (what this project does) read more clearly than
photoreal rust anyway — the student is looking for the part, not the patina.

**4. Resize textures.** 2048² is the practical ceiling on a phone and 1024² is
usually enough. A 4096² texture costs 64 MB in memory once uncompressed.

**5. Compress, last.** Two independent compressions:

```bash
# Geometry: Draco. 5-10x smaller, costs a short decode on load.
npx gltf-pipeline -i machine.glb -o machine.draco.glb -d

# Textures: KTX2 / Basis Universal. Stays compressed in GPU memory,
# which is the part that actually matters on a phone.
npx gltf-transform optimize machine.glb machine.opt.glb --texture-compress ktx2
```

`gltf-transform` (`npm i -g @gltf-transform/cli`) is the better of the two
tools today; `optimize` runs dedup, prune, instancing, Draco and texture
compression in one pass. Both need Node.js, which this project otherwise does
not require.

Check the result loads in <https://gltf-viewer.donmccurdy.com/> before you put
it on a tablet.

## Keep the part structure through the pipeline

Decimation and compression preserve node names if you let them. Do not "join
all" in Blender to reduce draw calls — you would lose the per-part labels, the
highlight feature and any chance of animating the machine. Merge *within* a
part, never across parts.

The viewer addresses parts through **materials named after the part**, because
model-viewer's scene-graph API can reach materials but not nodes. If you
re-material a model in Blender, keep one material per part and keep the names,
or `viewer.js` will not be able to highlight anything.

## Measuring instead of guessing

- `python tools/build.py` prints triangles, parts and file size per machine.
- On the tablet, Chrome → `chrome://inspect` from a desktop gives you a real
  profiler over USB.
- In the viewer, model-viewer fires a `load` event; the time from navigation to
  that event is what a student actually experiences. Over a mine-site 4G link,
  budget 1 second per 300 KB.
