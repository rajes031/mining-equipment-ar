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
