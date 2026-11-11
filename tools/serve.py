"""
serve.py -- serve web/ to the phones and tablets on your network.

    python serve.py              # http  -- fine for Scene Viewer AR on Android
    python serve.py --https      # https -- needed for WebXR ("in-page" AR)
    python serve.py --port 9000

Why the https flag matters: WebXR only runs in a secure context, so over plain
http Chrome will fall back to Google's Scene Viewer app (still real AR, just a
separate screen). With --https you get AR inside the page, at the cost of a
one-time "connection is not private" warning on each device, because the
certificate is self-signed. Tap Advanced -> Proceed.

Nothing here is meant to face the internet. For classroom or site-wide use,
publish the web/ folder to GitHub Pages or any static host (see docs/04).
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.server
import ipaddress
import socket
import ssl
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"
CERT = HERE / ".dev-cert.pem"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".usdz": "model/vnd.usdz+zip",
        ".js": "text/javascript",
        ".json": "application/json",
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def end_headers(self):
        # Dev server: never let a tablet cache a model you just rebuilt.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def local_addresses():
    """Best-effort list of this machine's LAN addresses."""
    found = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))       # no packets sent, just route lookup
        found.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None,
                                       socket.AF_INET):
            addr = info[4][0]
            if addr not in found and not addr.startswith("127."):
                found.append(addr)
    except OSError:
        pass
    return found


def ensure_cert(hosts):
    """Self-signed certificate covering localhost and this machine's LAN IPs."""
    if CERT.exists():
        age = dt.datetime.now() - dt.datetime.fromtimestamp(CERT.stat().st_mtime)
        if age.days < 300:
            return CERT
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        sys.exit("--https needs the 'cryptography' package: pip install cryptography")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "mining-ar dev")])
    alt = [x509.DNSName("localhost")]
    for h in hosts:
        try:
            alt.append(x509.IPAddress(ipaddress.ip_address(h)))
        except ValueError:
            alt.append(x509.DNSName(h))
    alt.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))

    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False)
            .sign(key, hashes.SHA256()))

    CERT.write_bytes(
        key.private_bytes(serialization.Encoding.PEM,
                          serialization.PrivateFormat.TraditionalOpenSSL,
                          serialization.NoEncryption())
        + cert.public_bytes(serialization.Encoding.PEM))
    print(f"wrote a fresh self-signed certificate to {CERT.name}")
    return CERT


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--https", action="store_true",
                    help="serve over TLS so WebXR in-page AR works")
    args = ap.parse_args()

    if not (WEB / "data" / "catalog.json").exists():
        sys.exit("No catalogue yet -- run 'python build.py' first.")

    hosts = local_addresses()
    scheme = "https" if args.https else "http"

    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    if args.https:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(ensure_cert(hosts))
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print("\nMining Equipment AR -- serving", WEB)
    print(f"  on this computer : {scheme}://localhost:{args.port}/")
    for h in hosts:
        print(f"  on your tablet   : {scheme}://{h}:{args.port}/")
    if args.https:
        print("\n  The certificate is self-signed: on the tablet tap")
        print("  'Advanced' then 'Proceed' the first time.")
    else:
        print("\n  Plain http: Android will open AR in Google's Scene Viewer.")
        print("  For in-page WebXR AR, restart with --https.")
    print("\n  Ctrl+C to stop.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
