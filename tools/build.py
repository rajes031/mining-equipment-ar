"""
build.py -- regenerate every model, preview and the catalogue index.

Run this after editing any make_*.py:

    python build.py
"""

from __future__ import annotations

import json
from pathlib import Path

import make_dumper
import make_shovel
import render_preview

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

GENERATORS = [make_dumper, make_shovel]


def main():
    records = []
    for mod in GENERATORS:
        records.append(mod.main())

    render_preview.main()

    machines = []
    for rec in records:
        rec["thumbnail"] = "models/%s.png" % rec["id"]
        (WEB / "data" / f"{rec['id']}.json").write_text(
            json.dumps(rec, indent=2), encoding="utf-8")
        machines.append({
            "id": rec["id"],
            "name": rec["name"],
            "subtitle": rec["subtitle"],
            "category": rec["category"],
            "thumbnail": rec["thumbnail"],
            "model": rec["model"],
            "extents_m": rec["extents_m"],
            "bytes": rec["bytes"],
            "triangles": rec["triangles"],
            "parts": len(rec["parts"]),
        })

    catalog = {
        "title": "Mining Equipment AR",
        "machines": machines,
    }
    (WEB / "data" / "catalog.json").write_text(
        json.dumps(catalog, indent=2), encoding="utf-8")

    total = sum(m["bytes"] for m in machines)
    print(f"\ncatalog.json  {len(machines)} machines, "
          f"{total/1024:.0f} KB of models total")


if __name__ == "__main__":
    main()
