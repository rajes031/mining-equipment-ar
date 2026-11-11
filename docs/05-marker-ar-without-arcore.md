# Marker AR — for tablets without ARCore

Some Android devices are not ARCore-certified. No ARCore means no Scene Viewer
and no WebXR: the floor-placement AR in `viewer.html` simply cannot run.

(The Redmi Pad 2 Pro this project was first tested on turned out to be fine --
the Play Store hid the AR component from search and Xiaomi's FAQ was wrong.
Always confirm with `check.html` before assuming a device cannot do AR.)

Marker tracking is the way round it. It uses nothing but the camera, so it
works on any device -- and it is worth having even when floor AR does work,
because the scale is exact and known, measured from the printed marker. A
1:25 dumper on a desk is a better classroom object than a 1:1 one you cannot
fit in the room.

## Using it

**If the tablet is plugged in by USB — the easy route.** No Wi-Fi, no
firewall, and no certificate warning, because `adb reverse` puts the server on
the tablet's own `localhost`, which browsers treat as a secure origin:

```bash
python tools/make_markers.py    # once -- vendors the libraries, builds markers
python tools/usb_tablet.py      # waits for the tablet, then serves
```

Then open `http://localhost:8000/` on the tablet. One-time tablet setup is
printed by the script (enable USB debugging).

**Over Wi-Fi instead**, https is mandatory, because the camera is only
available to secure pages:

```bash
python tools/serve.py --https
```

1. Print `web/print-markers.html` on plain A4 at **100% / Actual size**. Check
   the 100 mm ruler line on the sheet with a real ruler.
2. Lay the markers flat on a table. Tape them down.
3. On the tablet open the viewer — `http://localhost:8000/marker.html` over
   USB, or `https://<pc-ip>:8000/marker.html` over Wi-Fi (accept the
   certificate) — and allow the camera.
4. Point at a marker. Marker A is the dumper, Marker B the shovel. Put both on
   the table to see the pair together at matched scale.

## What you realistically get

| Scale | Dumper becomes | Works on |
|---|---|---|
| 1:50 | 0.26 m | a desk |
| **1:25** | **0.53 m** | a desk — the default, and the sweet spot |
| 1:10 | 1.32 m | the floor, with an A3 marker |
| 1:5 | 2.64 m | the floor, A3 marker, good light |

**1:1 is not achievable this way, and the reason is physics, not software.**
ARToolKit needs the marker to occupy a decent fraction of the frame; detection
range is roughly ten times the marker width, so a 140 mm marker works to about
1.5 m. At 1:1 a dumper is 13 m long and you would have to stand 15–20 m back to
see it — at which distance the marker is a few pixels and tracking is long
gone. Printing an A0 marker pushes the range to a few metres, not twenty.

So: **marker AR for scale models, an ARCore phone for the life-size moment.**
Any mid-range Android phone from the last few years will do the latter, and
`viewer.html` already handles it with no changes.

## How the scale maths works

A marker defines a coordinate system in which one unit equals the marker's
physical width. The models are authored in metres, so:

```
scale = 1 / (ratio × markerWidthInMetres)
```

A 140 mm marker at 1:25 gives `1 / (25 × 0.14) = 0.2857`. The viewer does this
for you — but if you print at a size other than 140 mm you **must** type the
real width into the box, or every scale on screen is wrong. This is why the
print sheet carries a ruler.

The machine is also pushed clear of the marker along +Z, by half its own
length plus a margin. Without that it stands on top of the marker, hides it
from the camera, and the tracking drops the moment the model appears — a
confusing failure that looks like a bug in the model.

## Why the markers are generated, not downloaded

`tools/make_markers.py` rebuilds each marker image from the same `.patt`
pattern file that AR.js matches against at runtime, so the paper and the
detector cannot drift apart. It then checks itself by regenerating the Hiro
marker and comparing against the official `hiro.png` (mean absolute difference
under 24/255 passes; it currently scores about 9.5, the residual being the
16×16 pattern upscale against vector-sharp original art).

The white border around the black frame is not decoration — it is the quiet
zone the detector needs to find the frame's edges. The official marker leaves
just over 4% per side and these match it.

## When tracking misbehaves

| Symptom | Cause |
|---|---|
| Nothing appears | Page is on http, not https — no camera. Or the marker is printed too small. |
| Model flickers in and out | Glare on a glossy print, or the marker is curled. Use plain paper, tape it flat. |
| Model jitters | Normal at high scale ratios; every pixel of marker error is multiplied. Print bigger, add light. |
| Model appears then vanishes | The model is covering the marker. Should not happen — the +Z offset handles it — but check the printed width is what you typed. |
| Works on the laptop, not the tablet | Certificate not accepted on the tablet yet, or campus Wi-Fi is blocking device-to-device traffic. |

Good light and a matte print fix the large majority of problems.

## Offline use

`make_markers.py` vendors A-Frame and AR.js into `web/vendor/` (about 3 MB
together), and `marker.html` loads them from there, not from a CDN. With the
models served locally the whole thing runs with no internet at all — which
matters for a pit visit.
