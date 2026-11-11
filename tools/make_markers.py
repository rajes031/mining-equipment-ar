"""
make_markers.py -- fetch the AR.js runtime and build printable markers.

Needed because the Redmi Pad 2 Pro (like most Android tablets) is not
ARCore-certified, so Scene Viewer and WebXR are both unavailable. Marker
tracking needs nothing but a camera, so it works on any tablet.

What this does:
  1. Vendors A-Frame and AR.js into web/vendor/ so the page also works with
     no internet at all -- important on a mine site.
  2. Rebuilds each marker image from the very .patt pattern file that AR.js
     matches against at runtime, so the printed sheet and the detector can
     never drift apart.
  3. Writes web/markers/*.png and the print sheet's data.

Run once:  python make_markers.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"
VENDOR = WEB / "vendor"
MARKERS = WEB / "markers"

AFRAME = "1.5.0"
ARJS = "3.4.5"

DOWNLOADS = {
    "aframe.min.js":
        f"https://cdn.jsdelivr.net/npm/aframe@{AFRAME}/dist/aframe-v{AFRAME}.min.js",
    "aframe-ar.js":
        f"https://cdn.jsdelivr.net/npm/@ar-js-org/ar.js@{ARJS}/aframe/build/aframe-ar.js",
}

PATTERNS = {
    "hiro": "https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/data/patt.hiro",
    "kanji": "https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/data/patt.kanji",
}

REFERENCE_HIRO = "https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/images/hiro.png"

# AR.js default patternRatio: the inner pattern occupies 50% of the marker,
# leaving a black border of 25% on every side. Printing a marker with the
# wrong border ratio is the most common reason detection "just doesn't work".
PATTERN_RATIO = 0.5

# The detector finds the marker by its black frame, so the frame needs white
# around it. The official hiro.png leaves 81 px of white on a 2000 px canvas,
# i.e. just over 4% per side; matched here. Printed on white paper the page
# itself extends the quiet zone, which is why a marker in the middle of a
# sheet tracks better than one printed to the edge.
QUIET_ZONE = 0.0405
PX = 1200            # output canvas in pixels (300 dpi at ~10 cm)


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mining-ar-build"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_patt(text: str) -> np.ndarray:
    """First rotation of an ARToolKit .patt file -> 16x16x3 uint8 array.

    Format: for each of 4 rotations, 16 rows of 16 red values, then the same
    for green and blue, blocks separated by blank lines.
    """
    rows = [ln for ln in text.splitlines() if ln.strip()]
    planes = []
    for plane in range(3):
        block = rows[plane * 16: (plane + 1) * 16]
        planes.append([[int(v) for v in ln.split()] for ln in block])
    arr = np.array(planes, dtype=np.uint8)          # (3, 16, 16)
    return np.transpose(arr, (1, 2, 0))             # (16, 16, 3)


def render_marker(pattern: np.ndarray, size: int = PX) -> Image.Image:
    """White quiet zone, black frame, 16x16 pattern filling the centre."""
    quiet_px = int(round(size * QUIET_ZONE))
    frame_px = size - 2 * quiet_px
    inner_px = int(round(frame_px * PATTERN_RATIO))
    offset = quiet_px + (frame_px - inner_px) // 2

    inner = Image.fromarray(pattern, "RGB").resize((inner_px, inner_px),
                                                   Image.NEAREST)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(Image.new("RGB", (frame_px, frame_px), (0, 0, 0)),
                 (quiet_px, quiet_px))
    canvas.paste(inner, (offset, offset))
    return canvas


def compare(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute difference, 0 = identical, as a sanity check."""
    size = (256, 256)
    x = np.asarray(a.convert("L").resize(size), dtype=np.float64)
    y = np.asarray(b.convert("L").resize(size), dtype=np.float64)
    return float(np.abs(x - y).mean())


def main():
    VENDOR.mkdir(parents=True, exist_ok=True)
    MARKERS.mkdir(parents=True, exist_ok=True)

    print("vendoring the AR runtime:")
    for name, url in DOWNLOADS.items():
        target = VENDOR / name
        data = fetch(url)
        target.write_bytes(data)
        print(f"  {name:18s} {len(data)/1024:8.0f} KB")

    print("\nbuilding markers from their pattern files:")
    built = {}
    for name, url in PATTERNS.items():
        patt = fetch(url).decode("ascii")
        (MARKERS / f"patt.{name}").write_text(patt, encoding="ascii")
        img = render_marker(parse_patt(patt))
        out = MARKERS / f"{name}.png"
        img.save(out, optimize=True)
        built[name] = img
        print(f"  {name:18s} {out.stat().st_size/1024:8.1f} KB  {img.size[0]}px")

    # Verify the method: our regenerated Hiro must match the official image.
    try:
        ref = Image.open(__import__("io").BytesIO(fetch(REFERENCE_HIRO)))
        diff = compare(built["hiro"], ref)
        verdict = "MATCH" if diff < 24 else "DIFFERS -- check before printing"
        print(f"\n  regenerated hiro vs official hiro.png: "
              f"mean abs diff {diff:.1f}/255 -> {verdict}")
    except Exception as exc:                       # offline is not fatal
        print(f"\n  (could not fetch reference image: {exc})")

    (MARKERS / "markers.json").write_text(json.dumps({
        "patternRatio": PATTERN_RATIO,
        "markers": [
            {"preset": "hiro", "image": "markers/hiro.png",
             "label": "Marker A"},
            {"preset": "kanji", "image": "markers/kanji.png",
             "label": "Marker B"},
        ],
        "aframe": AFRAME,
        "arjs": ARJS,
    }, indent=2), encoding="utf-8")
    print("\ndone -- print web/print-markers.html and open web/marker.html")


if __name__ == "__main__":
    main()
