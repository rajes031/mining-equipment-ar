# Getting it onto the tablets

## First check: is your device ARCore-certified?

Open **`check.html`** on the device. It queries WebXR in the browser and gives
a definitive answer in two seconds.

A second, less reliable check is to open the Play Store and search
**"Google Play Services for AR"**:

- **It appears and installs** -> you have ARCore.
- **No result at all** -> inconclusive, NOT a no. The app may be preinstalled
  as a system component and hidden from search. Open `check.html` instead.

**The Play Store test gives false negatives.** On many devices Google Play
Services for AR is preinstalled as a hidden system component and never appears
in search, even though AR works perfectly. The **Redmi Pad 2 Pro** is exactly
such a device: the Play Store shows nothing, Xiaomi's own FAQ claims it "does
not support AR", and yet it runs full WebXR floor-placement AR and is listed by
Google as supporting the Depth API.

So use `web/check.html` instead, which queries WebXR directly in the browser.
That is what actually decides whether AR runs. Trust it over the Play Store,
over the manufacturer's FAQ, and over any spec sheet.

ARCore certification is still granted per model by Google, and many tablets do
lack it. Before buying hardware for a lab, check the exact model on
<https://developers.google.com/ar/devices> -- the brand tells you nothing.

**If check.html says no, use Marker AR** -- see
[05-marker-ar-without-arcore.md](05-marker-ar-without-arcore.md). It needs only
a camera and works on any tablet.

## How Android AR actually works here

Two different mechanisms sit behind the one "View in AR" button:

| | **Scene Viewer** | **WebXR** |
|---|---|---|
| What it is | A Google app on the device that opens your model full-screen | AR running inside the web page |
| Needs HTTPS | Not strictly, but unreliable without it | **Yes** — secure context required |
| Feels like | Leaving your app and coming back | Staying in your app |
| Availability | Any ARCore device with Google Play Services for AR | ARCore device + Chrome 81+ |

`ar-modes="webxr scene-viewer quick-look"` tries them in that order, so over
HTTPS you get in-page AR and otherwise fall back to Scene Viewer. The practical
consequence: **serve over HTTPS**. Everything below is about that.

## Option 1 — GitHub Pages (recommended)

Free, HTTPS, no server to run, and students can open it from anywhere.

```bash
cd mining-ar/web
git init && git add . && git commit -m "Mining equipment AR"
git branch -M main
git remote add origin https://github.com/<you>/mining-ar.git
git push -u origin main
```

Then Settings → Pages → Deploy from branch → `main` / root. Within a minute the
site is at `https://<you>.github.io/mining-ar/`. Push to update it.

The whole `web/` folder is static — no build step, no server code. Netlify,
Cloudflare Pages, GitLab Pages and your institute's own web server all work the
same way. If you use an institute server, make sure it sends `.glb` as
`model/gltf-binary`; some default configurations send it as
`application/octet-stream`, which Scene Viewer rejects.

## Option 2 — your laptop, over the classroom Wi-Fi

```bash
python tools/serve.py --https
```

It prints an address like `https://192.168.1.14:8000/`. Type that into Chrome
on the tablet, accept the certificate warning once (Advanced → Proceed), and
AR works. The certificate is self-signed and generated on first run; the
warning is expected and is not a sign anything is wrong.

Both devices must be on the same network, and many campus Wi-Fi networks block
device-to-device traffic — if the tablet cannot reach the laptop, that is
usually why. A phone hotspot is the quick workaround.

## Option 3 — fully offline, no network at all

For a pit or a field visit with no signal:

1. Vendor the viewer library so nothing is fetched from a CDN:

   ```bash
   mkdir -p web/vendor
   curl -L -o web/vendor/model-viewer.min.js \
     https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js
   ```

   Then in `web/viewer.html` change the script `src` to
   `vendor/model-viewer.min.js`.

2. Serve from the tablet itself, or add a service worker to cache the page.
   The simplest reliable approach is the Unity app in
   [03-unity-ar-foundation.md](03-unity-ar-foundation.md) — an `.apk` carries
   its models inside it and needs nothing.

Note that Scene Viewer AR needs the model at a URL the device can reach, so a
fully offline web page should use WebXR (HTTPS from a local server) rather than
Scene Viewer.

## Setting up a classroom set of tablets

- Open the page once on each device so Chrome caches it, and bookmark it to the
  home screen (Chrome → ⋮ → Add to Home screen). It then opens like an app.
- Check **Google Play Services for AR** is installed and current — it is a
  separate Play Store entry from Chrome and is what actually does the tracking.
- Verify the device is on [Google's ARCore supported devices
  list](https://developers.google.com/ar/devices). Cheap tablets frequently are
  not, even recent ones. This catches people out when buying for a lab: check
  the exact model number before ordering, not the brand.

## Running a session that works

Three practical things, learned the hard way by anyone who has demonstrated AR
to a room:

- **Floor, not table.** These machines are 13–15 m long. At 1:1 they need real
  space — a corridor, a hall, or outdoors. A classroom with desks will not fit a
  dumper and students end up standing inside it.
- **Texture on the ground.** ARCore finds planes from visual features. A plain
  polished floor in flat light gives it almost nothing; a dusty concrete apron
  works immediately. If tracking will not start, put a bag or a sheet of paper
  on the floor.
- **Point down and move sideways first.** The model does not appear until a
  plane is found. Tell students to sweep the tablet slowly across the floor
  rather than holding it still and waiting.
