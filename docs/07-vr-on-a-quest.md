# VR on a Meta Quest

Every model in the catalogue can be walked around in VR, at the same true
scale it has in AR. The page is `web/vr.html`.

## Why this is a separate page

`model-viewer`, which the rest of the site uses, only ever requests a WebXR
`immersive-ar` session. It has no VR mode at all. So `vr.html` is a small
three.js application that loads exactly the same GLB files and requests
`immersive-vr` instead. Nothing about the models changed to make this work —
they were already metres, Y-up, origin on the ground.

## The easy way: no cable, no PC

**Open the site in the headset's own browser.** The Quest Browser supports
WebXR, the models are on a public URL, and nothing has to be installed:

1. Put the headset on, open the Browser.
2. Go to `https://rajes031.github.io/mining-equipment-ar/`
3. Tap **VR walkthrough**, pick a machine, press **Enter VR**.

This is the route to use in a classroom. There is nothing to set up on a
second machine and nothing to go wrong with a cable.

## The wired way: Quest Link to a PC

Worth it only when the PC's graphics are much stronger than the headset's, or
when the model is still being edited and you want to see changes immediately
from a local server.

1. Install **Meta Quest Link** on the PC and sign in.
2. Connect the headset with a USB 3 cable and enable **Link** from the Quick
   Settings panel inside the headset.
3. Make the Oculus runtime the **active OpenXR runtime** — Quest Link app,
   Settings → General → OpenXR Runtime → *Set Oculus as active*. If another
   runtime (SteamVR, Windows Mixed Reality) has claimed it, the browser will
   report no VR device and the Enter VR button stays greyed out.
4. In Chrome or Edge **on the PC**, open the site and press **Enter VR**.

For a local build, serve the folder and open that address instead:

```bash
python tools/serve.py
```

WebXR needs a secure context, which `localhost` counts as — so a plain
`http://localhost:...` address works without a certificate.

## Controls in the headset

| | |
|---|---|
| Left thumbstick | Walk, relative to where you are looking |
| Right thumbstick | Turn in 30° steps |
| **A** or **X** | Switch between life size and 1:10 |
| **B** or **Y** | Next machine |

Turning is deliberately **snap, not smooth**. Continuous turning is the
fastest way to make someone motion-sick, and a class of thirty is not the
place to find that out. Walking is smooth because it has to be — you cannot
teleport your way along a 14 m roadway and still get a feel for its length.

The 1:10 setting matters more than it sounds. The loading cycle is 26 m by
29 m and the drill rig is nearly 20 m tall; at life size you cannot see
either whole from inside. Shrinking to 1:10 turns the scene into a tabletop
model you can walk around in a few steps, then switch back to stand next to
a tyre.

## What suits VR and what does not

**Good in VR:** the bolted gallery, which is an enclosure you walk through —
this is the one thing VR does better than AR, because AR cannot replace the
room you are standing in. The roof support, standing under a 3.5 m canopy.
The drill rig, for its height. The loading cycle, which animates.

**Better in AR:** anything where the point is comparing the machine to the
real world around you. A dumper beside a real car in a real car park lands
harder than a dumper in an empty grey void.

## Notes for whoever maintains this

* three.js is pinned to a version in the import map. Draco-compressed models
  (the drill rig) need `DRACOLoader`; its decoder is loaded from the same
  CDN version, so bumping three.js moves both together.
* The camera is a child of a "player" group and VR locomotion moves the
  group, never the camera — in a session the camera's pose belongs to the
  headset and anything written to it is overwritten on the next frame.
  `OrbitControls` for the flat view assumes its camera is in world space, so
  the rig is parked at the origin whenever a session is not running.
* Reference space is `local-floor`, so y = 0 is the real floor and a 3.5 m
  canopy really is 3.5 m above the user's feet.
