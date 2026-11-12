"""
build.py -- regenerate every generated model, its preview, and the catalogue.

Run this after editing any make_*.py:

    python build.py

Two kinds of machine live in the catalogue and they are built differently:

* **Generated** -- drawn from scratch by a make_*.py in this folder. Running
  this script rebuilds them completely.
* **Converted** -- derived from a purchased asset pack by one of the Blender
  converters (see docs/06). Those need Blender and the original art, which is
  not in the repository, so this script does NOT rebuild them. It reads their
  existing data files and carries them into the catalogue unchanged.

That distinction matters: before it existed, running build.py silently
deleted the converted machines from catalog.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import make_blast_pattern
import make_dumper
import make_gallery
import make_roof_support
import make_shovel
import render_preview

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

GENERATORS = [
    make_dumper,
    make_shovel,
    make_roof_support,
    make_blast_pattern,
    make_gallery,
]

# Built by tools/make_dumper_glb.py and tools/make_drill_glb.py under Blender.
CONVERTED = ["dumper-detailed", "drill-rig"]

# Catalogue order: haulage and loading first, then the drilling and blasting
# pair, then underground. It follows the opencast cycle rather than the order
# the files happen to be built in.
ORDER = [
    "dumper-detailed",
    "dumper",
    "shovel",
    "drill-rig",
    "blast-pattern",
    "roof-support",
    "gallery",
]


def card(rec):
    return {
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
    }


def main():
    records = {}
    for mod in GENERATORS:
        rec = mod.main()
        records[rec["id"]] = rec

    render_preview.main()

    for rec in records.values():
        rec["thumbnail"] = "models/%s.png" % rec["id"]
        (WEB / "data" / f"{rec['id']}.json").write_text(
            json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    for cid in CONVERTED:
        path = WEB / "data" / f"{cid}.json"
        if not path.exists():
            print(f"  (converted model {cid} has no data file, skipped)")
            continue
        records[cid] = json.loads(path.read_text(encoding="utf-8"))

    machines = [card(records[i]) for i in ORDER if i in records]
    missing = [i for i in records if i not in ORDER]
    machines += [card(records[i]) for i in missing]
    if missing:
        print(f"  (not in ORDER, appended: {', '.join(missing)})")

    (WEB / "data" / "catalog.json").write_text(
        json.dumps({"title": "Mining Equipment AR", "machines": machines},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")

    total = sum(m["bytes"] for m in machines)
    print(f"\ncatalog.json  {len(machines)} machines, "
          f"{total/1024:.0f} KB of models total")


if __name__ == "__main__":
    main()
