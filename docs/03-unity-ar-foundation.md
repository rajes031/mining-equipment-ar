# Phase 2 — the native Android app (Unity + AR Foundation)

Move to Unity when you need something the web cannot do:

- **Animation** — a shovel digging and swinging, a dumper tipping, hydraulics
  extending. This is the big one for teaching.
- **Offline use** — an `.apk` on a tablet in a pit with no signal.
- **Image / marker tracking** — point the tablet at a machine's data plate or a
  printed card and have the model appear on it.
- **Interaction logging** — which parts a trainee looked at, how long, quiz
  scores. Needed if the AR session has to count towards statutory training
  records.
- **Occlusion and lighting estimation** — ARCore Depth API so the model is
  hidden correctly behind real objects.

Everything else, the web version already does better and updates instantly.

## Versions that work together

| | Choice |
|---|---|
| Unity | **6 LTS (6000.x)**, or 2022.3 LTS if you have existing work on it |
| AR Foundation | 6.x with Unity 6; 5.1.x with 2022.3 |
| Google ARCore XR Plugin | same major version as AR Foundation |
| glTF import | **glTFast** — Package Manager → Add by name → `com.unity.cloud.gltfast` |
| Render pipeline | URP, Mobile template |

Match AR Foundation and the ARCore plugin major versions exactly. Mismatches
are the single most common cause of "builds fine, black screen on device".

## Project setup, once

1. New project → **Universal 3D (Mobile)**.
2. Package Manager → install **AR Foundation** and **Google ARCore XR Plugin**.
3. Package Manager → Add package by name → `com.unity.cloud.gltfast`.
4. File → Build Settings → **Android** → Switch Platform.
5. Project Settings → **XR Plug-in Management** → Android tab → tick **ARCore**.
6. Project Settings → Player → Other Settings:
   - Graphics APIs: leave **OpenGLES3** only (remove Vulkan unless you have
     tested it on your target devices).
   - Minimum API Level: **Android 7.0 (API 24)** — ARCore's floor.
   - Scripting Backend: **IL2CPP**; Target Architectures: **ARM64** only.
   - Package name: something like `in.ac.yourinstitute.miningar`.
7. Project Settings → XR Plug-in Management → ARCore → Requirement:
   **Required** (the app only makes sense with AR) or **Optional** (so it still
   installs on non-ARCore tablets and falls back to a 3-D viewer).

## Scene setup

1. Delete the default **Main Camera**.
2. GameObject → XR → **AR Session**.
3. GameObject → XR → **XR Origin (AR)**.
4. On the XR Origin add **AR Plane Manager** and **AR Raycast Manager**.
5. Add `unity/Scripts/TapToPlace.cs` to the XR Origin and assign a machine
   prefab.

## Getting these models in

Drag `web/models/dumper.glb` into `Assets/`. glTFast imports it as a prefab
with the node hierarchy intact, so you get:

```
dumper
├── chassis
├── front_tyres
├── dump_body          ← hinges about the rear pivot pins
│   └── body_canopy
└── ...
```

and for the shovel the full chain `superstructure → boom → stick → bucket →
bucket_teeth`. Add `unity/Scripts/MachineRig.cs` to the root of the prefab and
call `SetBoom(14f)` or `StartCoroutine(rig.ShovelCycle())`.

Two things to check on first import:

- **Scale.** The models are authored in metres and glTF's unit is the metre, so
  the prefab's scale must stay at 1. If a dumper looks like a toy, something
  upstream rescaled it — fix it there, not with a scale factor on the prefab.
- **Rotation direction.** glTF is right-handed, Unity is left-handed, so an
  importer flips one axis and a lever may swing the wrong way. `MachineRig` has
  `invertHingeAxis` / `invertSwingAxis` for exactly this. Do not re-author the
  model.

If you would rather not use glTFast, open the GLB in Blender and export FBX —
but check the node names survive, because `MachineRig` finds parts by name.

## Materials

glTFast imports glTF PBR materials into URP's Lit shader. For the flat-shaded
teaching look, switch them to **Simple Lit** or an unlit shader with baked
shadow — cheaper, and it reads more clearly on a bright screen outdoors. Keep
one material per part if you want the fade/highlight behaviour from the web
version; the equivalent in Unity is setting `_BaseColor.a` with the material in
Transparent surface mode.

## Building

- Build Settings → **Build** produces an `.apk` you can sideload for classroom
  use. Enable "Developer options → Install via USB" on the tablet.
- For Play Store distribution you need an `.aab` and a signing key; for an
  institute's internal use, sideloading or an MDM push is simpler and avoids
  the review process entirely.
- First build takes 10–20 minutes. Subsequent builds are much faster if you
  leave "Development Build" off and do not change the IL2CPP settings.

## What to build first

Resist building a whole app. One scene, one machine, tap to place, one
animation button. Get that on a tablet in a classroom and watch where students
actually point it — that will tell you what phase 3 should be, and it will not
be what the plan says.
