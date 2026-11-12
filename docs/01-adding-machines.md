# Adding another machine

Three routes, in the order I'd try them.

## Route A — generate it, like the two already here

Best for teaching models. You control the envelope, the part breakdown and the
file size, there is no licence to worry about, and the parts come out named and
hinged so they can be animated later.

Copy `tools/make_shovel.py`, change the numbers, run `python tools/build.py`.
The pattern is always:

1. Put the published envelope figures at the top as named constants
   (overall length/width/height, wheelbase or track gauge, tyre or bucket size).
   Work in metres. Nose towards `-Z`, up is `+Y`, origin on the ground at the
   machine's centre.
2. Build each component with `part(...)` plus `box`, `cyl` and `prism`. One
   `part` per thing a trainee would name out loud — that is the right
   granularity, because every part becomes a tappable label.
3. Give each part a `label` and a `note`. The note is the lesson; write the
   thing an experienced operator would tell a new one, not a dictionary
   definition.
4. For anything that moves, set `pivot=` to the joint in world coordinates and
   `parent=` to the part it hangs from.

Good candidates to add next, roughly in order of teaching value:

| Machine | Why it earns its place |
|---|---|
| Rope (electric) shovel | The other half of "shovel"; completely different machine from the hydraulic one, and students conflate them |
| Dragline | Nothing conveys a 100 m boom like standing under one |
| Surface miner | Increasingly common in Indian limestone and coal, rarely seen by students |
| Drill (blasthole) | Pairs with blast-design teaching |
| Dozer / grader | Haul-road maintenance, the thing that actually limits truck speed |
| Underground LHD and SDL | Different scale lesson entirely — tight headroom |

### Shapes the generator can make

- `box(center, size, xform)` — the workhorse.
- `cyl(center, radius, length, axis, segments, inner_radius, xform)` — set
  `inner_radius` for a tyre, ring gear or pipe.
- `prism(profile, extent, axis, offset, xform)` — extrude a **convex** 2-D
  outline. Truck trays, track frames, buckets and teeth are all prisms. For a
  non-convex outline, split it into convex pieces in the same part; it costs
  nothing.
- `strut(p0, p1, x_offset)` in the make scripts — length and transform for a
  cylinder or box spanning two points, for cylinders and linkages.

Winding does not matter: every primitive's normals are oriented outwards
automatically.

## Route B — buy or download a model

Faster to something photoreal, slower to something usable, and you must read
the licence.

| Source | Notes |
|---|---|
| Sketchfab | Largest selection; filter by **Downloadable** and by CC licence. Many mining models are CC-BY, which means you must credit the author visibly. |
| CGTrader, TurboSquid | Paid, generally higher quality. Check the licence covers your use — "editorial only" models cannot be used in commercial training. |
| GrabCAD | Engineering CAD, often very heavy, licence varies per upload. |
| Manufacturer sites | Caterpillar, Komatsu, Liebherr, Epiroc and Sandvik publish promotional 3-D and AR assets. Ask the local dealer — for a training institute they will often supply models and cutaways on request. This is the most under-used route. |

Two cautions. **Trade dress**: a model that carries a manufacturer's livery,
logo and model number is their branding — fine for teaching inside your
institute, risky in anything you publish or sell. Generic yellow avoids the
question. **Fidelity**: a 2 million-triangle CAD model of a dumper looks no
better on a phone than a 20 thousand-triangle one, and will not load.

## Route C — convert CAD you already have

If the department has STEP/IGES/SolidWorks files:

1. Open in FreeCAD (free) or CAD Assistant (free, by Open Cascade).
2. Tessellate with a coarse deviation — 5–10 mm is plenty for a 13 m truck.
3. Export OBJ or glTF.
4. Decimate and re-material in Blender, then export GLB. See
   [02-optimising-for-mobile.md](02-optimising-for-mobile.md).

Expect to throw away all the internal geometry. A trainee never sees the inside
of a gearbox, and it can easily be 90% of the triangles.

## Keeping the part notes honest

Everything shown to a student is either a published figure for the machine
class or a general engineering fact. Where a number varies between
manufacturers, the files say "approx." and name the class rather than implying
one maker's exact spec. Keep that habit — a specific-looking wrong number is
worse than an honest range, and someone will eventually check.

## Animating a model, and composing two

`tools/make_loading_cycle.py` is the worked example: it builds no geometry of
its own, it composes the shovel and the dumper and animates them.

**Composing.** `Builder.absorb(other, prefix, xform, parent, drop)` pulls
another builder's materials and parts in, renames them with `prefix` (so two
machines can both own a `cab`), moves them by `xform`, and re-parents what
were roots over there. `drop` leaves parts behind — both machines ship a
scale figure and the scene only wants one.

**Groups.** A part can only rotate about its own pivot, which is right for a
boom and no use for driving a truck down a haul road. `Builder.group(name,
origin)` adds a node with no geometry to hang parts from and animate. Parts
given a group as their parent need no pivot of their own; their geometry is
expressed relative to the group's origin automatically.

**Animating.** `Builder.animate(name, channels)`, where each channel is
`(node_name, path, times, values)` and `path` is `translation`, `rotation` or
`scale`. Rotations are authored as XYZ Euler **degrees** and converted to
quaternions on write, because degrees per axis can be read and corrected by
hand and quaternions cannot.

Then add `"animation": {"name": ..., "seconds": ...}` to the model's record.
The viewer shows its play/pause control, and starts the clip, based on that
field rather than on model-viewer's `availableAnimations` — that list is only
populated once the scene has rendered a frame, so it reads empty on a
backgrounded tab and the control would never appear. An animated model also
starts with part labels off: forty hotspots swarm over a two-machine scene
and drift about as it moves.

**Checking it.** Static renders cannot show a clip. Import the GLB into
Blender and step to a time:

```bash
blender -b -noaudio --python render_anim.py -- model.glb out/ 7.4 11.2
```

Blender bakes glTF animation onto the objects as actions keyed in frames, so
a time in seconds is `t * fps`. Measuring where the bucket teeth actually end
up at the dump, rather than eyeballing it, is what caught the bucket dipping
0.6 m into the truck body on the first attempt.
