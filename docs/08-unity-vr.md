# The Unity VR build

The WebXR page (`web/vr.html`, see `docs/07`) runs anywhere with no install,
and that is the whole point of it. What it cannot do is look good. It draws
flat-lit glTF with no shadows, on models cut down to a size a tablet can
download, and underground it has no way to make a roadway look like anything
other than a grey corridor.

This is the other build: a Unity project, for when the picture matters.

|                     | WebXR page            | Unity build                      |
|---------------------|-----------------------|----------------------------------|
| Install             | none, it is a URL     | an editor, or a sideloaded APK   |
| Drill rig           | 157k tris, 1K maps    | **601k tris, 4K maps**           |
| Shadows             | none                  | real time, soft                  |
| Underground         | flat grey             | cap lamp, darkness, dust haze    |
| Anti-aliasing       | browser default       | MSAA 4x                          |
| Part notes          | yes                   | yes, the same ones               |

Both read the same models from `web/models` and the same part notes from
`web/data`, so a machine only has to be built once.

## Where it lives

`unity-vr/` in this repo. Unity's `Library/` is several gigabytes and is
rebuilt from `Assets/` and `Packages/` whenever the project is opened, so it
is ignored, and so are the models: they are copies, and a copy in git goes
stale the first time a generator changes.

To fill an empty checkout:

```bash
python tools/vr_assets.py unity-vr
```

That copies every `web/models/*.glb` into `Assets/Models` and writes slimmed
part notes into `Assets/Resources/PartData`.

## Opening it

Unity **6000.0.34f1**. Other versions will probably work, but see the
glTFast note at the bottom before changing it.

Open `unity-vr` from Unity Hub, then open `Assets/Scenes/MiningVr.unity`.

The whole project is built by script, so it can also be rebuilt from a
command line without opening anything:

```bash
"C:/Program Files/Unity/Hub/Editor/6000.0.34f1/Editor/Unity.exe" -batchmode -quit -projectPath unity-vr -executeMethod MiningVrSetup.ConfigureXR -logFile -
```

`MiningVrSetup` has four steps, also on a **Mining VR** menu in the editor:
`ConfigureXR`, `BuildScene`, `BuildWindows`, `BuildQuest`. `BuildScene` is
the one to re-run after new models arrive.

## Seeing it in the headset

### Tethered, through Quest Link

This is the one to use while building: press Play and it is in the headset,
at full PC quality.

1. **Meta Quest Link** on the PC, headset on a USB 3 cable, Link enabled in
   the headset's Quick Settings.
2. Quest Link app → Settings → General → **OpenXR Runtime → Set Oculus as
   active**. If SteamVR holds the runtime, Unity reports no device and Play
   mode just runs on the monitor.
3. Open the scene and press **Play**.

### Untethered, as an APK

```bash
"…/Unity.exe" -batchmode -quit -projectPath unity-vr -executeMethod MiningVrSetup.BuildQuest -logFile -
adb install -r unity-vr/Builds/Quest/MiningVR.apk
```

It then sits in the headset's library under *Unknown Sources*. The headset
needs developer mode on, which is a switch in the Meta Horizon phone app.

The first APK went out with the web-sized models, on the theory that a
standalone chip could not carry a PC budget. That was worth checking rather
than assuming, and the headset keeps the numbers itself:

```bash
adb logcat -s VrApi
```

It printed `FPS=72/72, Stale=0, GPU%=0.32, CPU%=0.11, Free=3813MB, Temp=35.0C`
-- a locked frame rate with two thirds of the GPU idle. The caution had cost
picture quality for nothing, so the Android build ships the same models the
PC build does.

The second measurement is the one worth copying the method from. With the
601k rig in and the eye buffer at 1.25, a glance at the log looked fine:
every line said `FPS=72/72`. Reading all 213 lines of it did not -- 57 stale
frames, and the GPU touching 99% whenever the rig was close up. A frame rate
averaged over a capture hides exactly the thing that is felt in a headset,
so the aggregate to look at is **the worst second, not the mean**:

```bash
adb logcat -s VrApi > perf.log      # then count, do not skim
grep -c "Stale=0," perf.log
```

Cascades were the first thing cut, since each one re-draws every shadow
caster and four of them is four more passes over the whole rig. Two to 70 m
on Android, against the PC's four to 140 m.

That was not enough. Moving in close to the rig -- which is what the dolly
on the right thumbstick is for -- took it to 464 stale frames in 24 seconds
and 29.9 ms frames, three times over a 13.9 ms budget. Standing back had
hidden it. **Measure a machine from where a student will actually stand,
which is as close to it as the controls allow.**

So the Android drill rig is **206,756 triangles with the 4K maps kept**. The
two costs are separable and they are not equally worth paying for: 1K to 4K
maps is most of what is visible on a rig at arm's length, while 157k to 601k
triangles is silhouette refinement nobody can see and the shadow pass redraws
every frame. Rebuild it with:

```bash
DRILL_TRI_TARGET=200000 DRILL_TEX_SIZE=4096 blender -b -noaudio   --python tools/make_drill_glb.py -- <fbx> <texdir> <out.glb> <out.json>
```

The PC build still gets 601k through Link, where it costs nothing.

One setting that does **not** work and should not be trusted here:
`XRSettings.eyeTextureResolutionScale`, which `VrPlayer.renderScale` drives.
The Quest reports `eye buffer 1680x1760` whatever it is set to, so on this
runtime it is a no-op. It is left in because it is harmless and may apply on
the PC, but no performance claim should rest on it.

`VrApi` stays the authority if a heavier machine is added later. Anything
other than a locked 72 with no stale frames means turning something down, in
that order: cascades, then triangles, then texture size.

## Controls

| | |
|---|---|
| Left thumbstick | Walk, relative to where you are looking |
| Right thumbstick ◀ ▶ | Turn in 30° steps |
| Right thumbstick ▲ ▼ | Move in towards the machine, or back out |
| **Trigger** | Read out the part you are pointing at |
| **Grip, held** | Turn the machine: hold and move that hand sideways |
| **Grip, tapped** | Clear the read-out |
| **X** | Hands-free turntable, on and off |
| **A** | Life size ↔ 1:10 |
| **B** | Next machine |
| **Y** | Step round the machine, 45° a press |

There are three ways to see the other side of something, because they are
wanted at different moments. **Y** walks the student round it in 45° steps,
always at a sensible distance and always facing it. The **grip** turns the
machine instead, which is what a demonstrator wants while standing still
and talking. **X** does that on its own, hands free.

Stepping with **Y** rather than orbiting on a thumbstick is a comfort
decision, not a tidiness one: circling an object means the whole world
sliding across the eyes while the body feels nothing, which is the most
reliable way there is to make someone ill in a headset. It is also the
better shape for teaching -- a front, a quarter, a side, an end.

The right thumbstick's other axis moves straight in at the machine and
stops at its skin, or at nothing at all for the models that are a roadway
and meant to be stood inside. Walking there with the left stick still
works and always will, but a drill rig is viewed from 30 m away, and
crossing that on a walk stick is slow and drifts off line the whole time.

**Y** replaced a plain stand-back, and the grip and **X** are new, because
walking the whole way round a machine is mostly not possible. A 19.6 m
drill rig is over 60 m in circumference, and the guardian boundary in a
standalone headset is a couple of metres across. So the machine turns
instead of the student, which also costs nothing in comfort: the world
stays still, which is the opposite of every kind of moving the player.

Grip still clears the read-out, on a tap. A grip pressed and released
without the hand going anywhere is not an attempt to turn anything, and
splitting the two on an angle threshold meant the control did not have to
be moved to a different button and learnt again.

## What the scene does

* **Surface machines** get a sun with soft shadows, a sky, and a 600 m pit
  floor with a procedural gravel texture. The texture is generated rather
  than shipped, so there is nothing to license or lose.
* **Underground models** (the gallery, the roof support) kill the sun, the
  sky and the ground plane, drop the ambient to almost nothing, add an
  exponential fog for dust, and light the scene from a **cap lamp on the
  user's head**. That one change is most of what makes a bolted roadway feel
  like a mine rather than a corridor.
* **Pointing** at a part names it over your hand; the trigger ghosts
  everything else, puts a lit board beside the part, and drops a warm light
  on it.

## Things that cost time here, so they are written down

* **glTFast 6.21 does not compile on 6000.0.34f1.** It calls an
  `ImageConversion.LoadImage` overload taking a `ReadOnlySpan<byte>` that
  this editor does not have. 6.14.1 is the last version without it and is
  what `Packages/manifest.json` pins. If the editor is upgraded, unpin it.
* **OpenXR features do not exist until they are refreshed.** Asking
  `FeatureHelpers` for a feature by id before calling
  `FeatureHelpers.RefreshFeatures(group)` returns nothing, which looks
  exactly like a wrong id. The ids are right:
  `OculusTouchControllerProfile` and `MetaQuestFeature`. Without the
  interaction profile the headset tracks but no button or thumbstick reports
  anything.
* **Never write a scale onto a glTF root node.** The drill rig's root is a
  node called `MOve_control` carrying `scale 0.01`, because the source model
  is in centimetres. Setting `localScale = 1` on it for the 1:1 switch made
  a 19.6 m rig 1,958 m tall. Every machine now hangs under a pivot of its
  own and the scale switch moves the pivot.
* **The built-in pipeline has no tone mapping.** Anything brighter than 1.0
  clips to flat white. The cap lamp started at intensity 4.2 and turned a
  coal roadway into a white-walled corridor; 1.45 over a 26 m range is a
  pool of light with darkness round it, which is both more useful and more
  honest.
* **Ghosting is a material swap, not a fade.** Fading in place means knowing
  each shader's own property names and blend keywords, and these models
  arrive with glTF shaders, Standard, and whatever a vendor pack ships. One
  shared ghost material works whatever the part is made of.
* **glTF animation imports as a clip and an Animator with no controller.**
  That plays nothing and reports no error, so the loading cycle was silently
  static. `BuildScene` now copies the clip out of the model (a sub-asset
  cannot be made to loop in place), sets it looping, builds a one-state
  controller round it, and sets the animator to `AlwaysAnimate` so it does
  not pause when the user walks round behind it.
* **A rotation about a point is a rotation and a translation.** Turning a
  machine about its own axis moves its pivot, so a machine left turned would
  come back round in the wrong place and `StandBack` would walk the student
  to where it used to be. Every machine records its home pose the first time
  it is shown and is put back there when it comes round again. The turntable
  axis is kept in the pivot's own space for the same family of reason: held
  in world coordinates it would have to be re-derived from the bounding box
  after each turn, and the box of a turned machine has a different centre,
  so the machine would crawl sideways as it span.
* **glTF imports have no colliders**, so the pointing ray goes straight
  through the machine. `BuildScene` adds a `MeshCollider` per renderer.
* **Tracking origin is set to Floor at runtime**, not in the inspector: the
  subsystem does not exist until the XR loader has started, a frame or two
  after `Awake`. Without it the model floats at eye height.
* Batchmode logs a licensing signature error (`Code 10 … verifying Licensing
  Client signature`) and then works anyway. It is noise; the serial is
  resolved two lines later.

## Checking it without a headset

There is no VR device on the build machine, so the scene is checked by
rendering it from where the player will be standing:

```bash
"…/Unity.exe" -batchmode -quit -projectPath unity-vr -executeMethod MiningVrSetup.Snapshot -machine gallery -readout 1 -part roof_bolts -out shot.png -logFile -
```

`-machine` is a catalogue id, `-readout` ghosts everything except `-part`,
and the read-out it draws is `PartReadout`'s own code rather than a
look-alike, so the board in the picture is the board in the headset.

The other half is `MiningVrSetup.Audit`, which prints what is actually in
the scene:

```
drill-rig         601396 tris    7 renderers    7 colliders  7/7 named  notes=7  anim=none
loading-cycle       4452 tris   38 renderers   38 colliders  38/38 named  notes=38  anim=Animator[loading-cycle]
```

It is cheap to run and it catches the failures that look like nothing at
all: a model that imported without colliders so the ray goes through it, a
renamed node that no longer matches its note, an animation with no player on
it.

Between them these catch scale, lighting, material, collider and animation
mistakes, which is most of them. They cannot catch anything about tracking,
comfort or the controllers.
