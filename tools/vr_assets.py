"""
vr_assets.py -- copy the built models and their part notes into the Unity VR
project.

The Unity project holds no models of its own. Everything it shows is built by
the generators in this folder and copied across, so there is one source of
truth for a machine and the AR page and the headset cannot drift apart.

Two things are different in the Unity copy:

* The part notes are slimmed to node, label and note. Unity's JsonUtility
  cannot represent the specs table (an array of arrays) and nothing in the
  headset reads it.
* A `<id>-hq.glb` beside a model wins. That is the same machine exported for
  a PC instead of a tablet -- the drill rig is 601k triangles and 4K textures
  there against 157k and 1K on the web. Build one with:

      DRILL_TRI_TARGET=600000 DRILL_TEX_SIZE=4096 blender -b -noaudio \\
        --python tools/make_drill_glb.py -- <fbx> <texdir> <out.glb> <out.json>

Run:  python tools/vr_assets.py [path-to-unity-project]
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WEB = REPO / "web"
DEFAULT_PROJECT = REPO.parent / "mining-vr"


def copy_models(project: Path) -> int:
    out = project / "Assets" / "Models"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for glb in sorted((WEB / "models").glob("*.glb")):
        target = out / glb.name
        if target.exists() and target.stat().st_mtime >= glb.stat().st_mtime:
            continue
        shutil.copy2(glb, target)
        print(f"  model  {glb.name:24s} {glb.stat().st_size / 1024:8.0f} KB")
        n += 1
    return n


def copy_notes(project: Path) -> int:
    out = project / "Assets" / "Resources" / "PartData"
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for src in sorted((WEB / "data").glob("*.json")):
        if src.stem == "catalog":
            continue
        record = json.loads(src.read_text(encoding="utf-8"))
        parts = record.get("parts")
        if not isinstance(parts, list):
            continue
        slim = {"parts": [{"node": p["node"],
                           "label": p.get("label", p["node"]),
                           "note": p.get("note", "")} for p in parts]}
        io.open(out / src.name, "w", encoding="utf-8", newline="\n").write(
            json.dumps(slim, indent=1, ensure_ascii=False) + "\n")
        print(f"  notes  {src.stem:24s} {len(parts):3d} parts")
        total += len(parts)
    return total


def main() -> int:
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROJECT
    if not (project / "Assets").is_dir():
        print(f"not a Unity project: {project}")
        return 1
    print(f"-> {project}")
    models = copy_models(project)
    notes = copy_notes(project)
    hq = sorted(p.name for p in (project / "Assets" / "Models").glob("*-hq.glb"))
    print(f"{models} models copied, {notes} part notes written")
    if hq:
        print("high-quality overrides in place: " + ", ".join(hq))
    print("Now rebuild the scene:")
    print('  Unity.exe -batchmode -quit -projectPath "%s" '
          "-executeMethod MiningVrSetup.BuildScene -logFile -" % project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
