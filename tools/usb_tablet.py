"""
usb_tablet.py -- serve the app to an Android tablet over the USB cable.

Why this is the best route when the tablet is plugged in:

  * No Wi-Fi, so campus networks that block device-to-device traffic (and
    IIT(BHU)'s does, like most institutional networks) are irrelevant.
  * No firewall rules.
  * **No certificate warning.** `adb reverse` makes the tablet's own
    localhost:8000 point at this computer's localhost:8000, and browsers treat
    localhost as a secure context. The camera works over plain http, so marker
    AR runs with no self-signed-certificate screen at all.

Run:  python usb_tablet.py
Then on the tablet open:  http://localhost:8000/

One-time setup on the tablet (HyperOS / Xiaomi):
  Settings -> About tablet -> tap "OS version" seven times
  Settings -> Additional settings -> Developer options -> USB debugging  (on)
  Plug in the cable, then tap "Allow" on the USB-debugging prompt.
"""

from __future__ import annotations

import argparse
import glob
import http.server
import os
import subprocess
import threading
import sys
import time
from pathlib import Path

import serve                      # reuse the handler and its MIME types

HERE = Path(__file__).resolve().parent

SETUP_HELP = """
The tablet is plugged in but ADB cannot see it yet. On the tablet:

  1. Settings -> About tablet -> tap "OS version" seven times
     (you should see "You are now a developer").
  2. Settings -> Additional settings -> Developer options -> turn on
     "USB debugging".
  3. Unplug and replug the cable. A dialog asks
     "Allow USB debugging?" -- tick "Always allow" and tap Allow.

On some Xiaomi builds you must also set the USB connection mode to
"File transfer (MTP)" rather than "Charging only" before the prompt appears.
"""


def find_adb() -> str | None:
    """Locate adb.exe without assuming it is on PATH."""
    from shutil import which
    found = which("adb")
    if found:
        return found

    patterns = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
                           r"\Google.PlatformTools*\platform-tools\adb.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%ProgramFiles%\Android\platform-tools\adb.exe"),
        r"C:\platform-tools\adb.exe",
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
    ]
    for pattern in patterns:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return None


def devices(adb: str):
    """-> list of (serial, state). State is 'device', 'unauthorized', ..."""
    out = subprocess.run([adb, "devices"], capture_output=True, text=True,
                         timeout=30).stdout
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            rows.append((parts[0], parts[1]))
    return rows


def wait_for_device(adb: str, timeout_s: int = 300):
    """Poll until one device is authorised, explaining whatever it finds."""
    said_setup = said_auth = False
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        found = devices(adb)
        ready = [s for s, st in found if st == "device"]
        if ready:
            return ready[0]

        if any(st == "unauthorized" for _, st in found):
            if not said_auth:
                print("\nThe tablet is connected but has not authorised this "
                      "computer.\nTap 'Allow' (and tick 'Always allow') on the "
                      "tablet's screen.\n")
                said_auth = True
        elif not said_setup:
            print(SETUP_HELP)
            print("Waiting for the tablet... (Ctrl+C to give up)\n")
            said_setup = True

        time.sleep(2)

    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--timeout", type=int, default=300,
                    help="seconds to wait for the tablet")
    args = ap.parse_args()

    if not (serve.WEB / "data" / "catalog.json").exists():
        sys.exit("No catalogue yet -- run 'python build.py' first.")
    if not (serve.WEB / "vendor" / "aframe-ar.js").exists():
        print("note: marker AR assets are missing -- run "
              "'python make_markers.py' if you need marker tracking.\n")

    adb = find_adb()
    if not adb:
        sys.exit("Could not find adb. Install it with:\n"
                 "    winget install --id Google.PlatformTools --scope user")
    print(f"using adb: {adb}")

    serial = wait_for_device(adb, args.timeout)
    if not serial:
        sys.exit("Gave up waiting for the tablet.")
    print(f"tablet connected: {serial}")

    # The key step: tablet's localhost:PORT -> this computer's localhost:PORT.
    def apply_reverse():
        subprocess.run([adb, "-s", serial, "reverse",
                        f"tcp:{args.port}", f"tcp:{args.port}"],
                       capture_output=True)

    apply_reverse()
    print(f"adb reverse set up on port {args.port}")

    # ADB drops every reverse rule when the device reconnects -- replugging the
    # cable, or the screen-lock cycling USB on some HyperOS builds, is enough.
    # The symptom is "site can't be reached" on a tablet that adb still lists
    # as connected, which is baffling unless you know. So keep re-applying.
    def watchdog():
        while True:
            time.sleep(5)
            out = subprocess.run([adb, "-s", serial, "reverse", "--list"],
                                 capture_output=True, text=True).stdout
            if f"tcp:{args.port}" not in out:
                apply_reverse()
                print(f"  (USB reconnected -- reverse rule re-applied)")

    threading.Thread(target=watchdog, daemon=True).start()

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", args.port),
                                            serve.Handler)
    print("\n" + "=" * 58)
    print("  On the TABLET, open Chrome and go to:")
    print(f"      http://localhost:{args.port}/")
    print()
    print("  No certificate warning, and the camera will work:")
    print("  browsers treat localhost as a secure origin.")
    print("=" * 58)
    print("\n  Ctrl+C to stop.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        subprocess.run([adb, "-s", serial, "reverse", "--remove",
                        f"tcp:{args.port}"], capture_output=True)
        print("adb reverse removed")


if __name__ == "__main__":
    main()
