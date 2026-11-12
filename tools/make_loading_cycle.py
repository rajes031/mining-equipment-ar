"""
make_loading_cycle.py -- the shovel-dumper loading cycle, animated.

Composes the existing shovel and dumper generators into one scene and adds a
glTF animation: the truck reverses onto the spot, the shovel makes four
passes into it, the truck pulls away. It is the only model in the set that
shows a *system* rather than a machine, because haulage economics is about
the pair and not about either one.

Speed: the animation runs at roughly four times real time. A 140 t-class
shovel takes about 30 seconds per pass -- dig, swing loaded, dump, swing back
-- and watching that honestly would make a three-minute loop. The real
numbers are in the spec table; use those for cycle-time arithmetic, not a
stopwatch against the animation.

A deliberate mismatch is on display. This 7.5 m3 shovel would need about 18
passes to fill a 220 t truck, which is far too many: four to six is the band
you design for. The animation shows four passes, and the note on the bucket
spells out why the pairing is wrong and what would be right. Seeing a badly
matched pair is a better lesson than being told the rule.

Axes: metres, Y up. The face is at -Z. The shovel sits at the origin and
swings 90 degrees to its right, to the haul road at +X.

Run:  python make_loading_cycle.py
"""

from __future__ import annotations

import json
from pathlib import Path

import make_dumper
import make_shovel
from figure import add_scale_figure
from glbgen import Builder, compose, rotate, translate

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "web"

# ------------------------------------------------------------------ layout

SPOT = (8.6, 0.0, 3.5)      # where the truck stands to be loaded
ROAD_IN = 26.0              # it reverses in from here
ROAD_OUT = 30.0             # and drives out to here
SQUAT = -0.11               # how far the suspension settles under load

# ------------------------------------------------------------------ timing

T_ARRIVE = 5.0
T_FIRST_PASS = 6.0
PASS = 7.0
PASSES = 4
T_LAST = T_FIRST_PASS + PASS * PASSES       # 34.0
T_DEPART = T_LAST + 5.0                     # 39.0
T_END = T_DEPART + 1.0                      # 40.0

# Shovel pose at rest, as the generator builds it: teeth near ground at
# about 10 m reach. Every angle below is relative to that.
FACE_POSE = (-9.0, -12.0, -18.0)            # boom, stick, bucket
SWING_TO_TRUCK = -90.0                      # about Y: -Z swings round to +X


def shovel_pass(t0):
    """One dig-swing-dump-return pass as (t, boom, stick, bucket, swing)."""
    b, s, k = FACE_POSE
    return [
        (t0 + 0.0, b, s, k, 0.0),                 # teeth at the toe
        (t0 + 1.4, -4.0, 6.0, 14.0, 0.0),         # crowding up through the face
        (t0 + 2.2, 10.0, 4.0, 26.0, 0.0),         # breakout, bucket full
        # The boom has to come well up before the swing: the body rim is at
        # 6.3 m and the teeth have to clear it, both on the way in and while
        # the bucket tips.
        (t0 + 2.6, 36.0, -2.0, 26.0, -12.0),      # hoist clear, begin swing
        (t0 + 4.0, 36.0, -2.0, 26.0, SWING_TO_TRUCK),
        (t0 + 4.6, 36.0, -2.0, 26.0, SWING_TO_TRUCK),   # spotted over the body
        (t0 + 5.2, 36.0, -2.0, -24.0, SWING_TO_TRUCK),  # dump
        (t0 + 5.8, 36.0, -2.0, -6.0, SWING_TO_TRUCK),
        (t0 + 6.4, 14.0, -6.0, k, -30.0),         # swing back empty
        (t0 + PASS, b, s, k, 0.0),                # down to the face again
    ]


def shovel_channels():
    keys = [(0.0,) + FACE_POSE + (0.0,)]
    for i in range(PASSES):
        keys += shovel_pass(T_FIRST_PASS + i * PASS)
    keys.append((T_END,) + FACE_POSE + (0.0,))
    # Drop duplicate timestamps where one pass ends as the next begins.
    clean = []
    for k in keys:
        if clean and abs(k[0] - clean[-1][0]) < 1e-6:
            clean[-1] = k
        else:
            clean.append(k)
    times = [k[0] for k in clean]
    return [
        ("sh_superstructure", "rotation", times, [(0.0, k[4], 0.0) for k in clean]),
        ("sh_boom", "rotation", times, [(k[1], 0.0, 0.0) for k in clean]),
        ("sh_stick", "rotation", times, [(k[2], 0.0, 0.0) for k in clean]),
        ("sh_bucket", "rotation", times, [(k[3], 0.0, 0.0) for k in clean]),
    ]


def truck_channel():
    x, _, z = SPOT
    return ("truck", "translation",
            [0.0, T_ARRIVE, T_FIRST_PASS, T_LAST, T_DEPART, T_END],
            [(x, 0.0, ROAD_IN),
             (x, 0.0, z),
             (x, 0.0, z),
             (x, SQUAT, z),          # settles on its springs as it fills
             (x, SQUAT, ROAD_OUT),
             (x, 0.0, ROAD_OUT)])    # the next one is empty


SPECS = {
    "id": "loading-cycle",
    "name": "Shovel–dumper loading cycle",
    "category": "Loading",
    "subtitle": "Animated — truck spots, four passes, truck away",
    "summary":
        "Loading is a two-machine system, and its output is set by whichever "
        "machine is waiting. Too few trucks and the shovel stands idle "
        "between them; too many and the trucks queue at the face. The ratio "
        "that balances the two is the match factor, and it falls straight "
        "out of the two cycle times you can see here: how long the shovel "
        "takes per pass, and how long a truck is away on the haul. The "
        "animation runs at about four times real speed — use the cycle times "
        "in the specs for any arithmetic, not a stopwatch.",
    "specs": [
        ["Shovel", "140 t class, 7.5 m³ bucket"],
        ["Truck", "220 t payload, rear-dump"],
        ["Shovel cycle (real)", "approx. 30 s — dig 8 s, swing loaded 7 s, dump 5 s, swing back 10 s"],
        ["Swing angle shown", "90° — keep it under 90° if the layout allows"],
        ["Bucket payload", "approx. 12 t (7.5 m³ × 1.8 t/m³ × 0.9 fill)"],
        ["Passes to fill this truck", "approx. 18 — far too many, see the bucket note"],
        ["Passes you design for", "4 to 6"],
        ["Spot time", "approx. 40 s to reverse in and settle"],
        ["Animation speed", "approx. 4× real time, 40 s loop"],
    ],
    "safety": [
        "The truck is spotted by the shovel operator, and no truck moves "
        "under a loaded bucket. The bucket never swings over the cab.",
        "Operators keep positive radio contact and an agreed horn code. A "
        "truck that reverses on an assumption is the commonest way people "
        "are killed at a loading face.",
        "Light vehicles stay a full truck length clear of the loading area "
        "and never approach without being acknowledged by both operators.",
        "The face behind the shovel is as much a hazard as the machines. "
        "Watch for loose on the highwall before anyone walks the floor.",
    ],
    "ar_tips": [
        "This is a loading bay, not a machine: about 25 m by 26 m. View it "
        "on screen first and save AR for a large open area.",
        "Count the passes and time the swing. Then halve the haul distance "
        "in your head and ask how many trucks the shovel could keep busy — "
        "that is match factor, and the animation gives you both numbers.",
        "Watch the truck settle on its suspension as it fills.",
    ],
}


def build():
    b = Builder("loading_cycle")

    # Ground, face and muckpile first, so the dig has something to dig into.
    b.material("bench_rock", (0.44, 0.41, 0.37), roughness=0.95, metallic=0.0)
    b.material("muck", (0.38, 0.35, 0.32), roughness=0.98, metallic=0.0)

    pad = b.part(
        "bench_floor", "bench_rock",
        label="Loading floor",
        note="The floor the shovel and the trucks share. Keeping it clean and "
             "level is not housekeeping: a rough floor slows every truck "
             "spotting onto it, and spot time is dead time for the shovel.",
        hotspot=(0.0, 0.05, 12.0), hotspot_normal=(0, 1, 0))
    pad.box(center=(0.5, 0.025, 1.0), size=(26.0, 0.05, 28.0))

    face = b.part(
        "bench_face", "bench_rock",
        label="Bench face (highwall)",
        note="A face shovel digs upward into the face rather than down into "
             "the floor, which is what the boom-stick-bucket geometry here is "
             "shaped for. Face height is matched to the machine: much above "
             "the shovel's maximum cutting height and the top of the face has "
             "to be brought down separately, which is slow and dangerous.",
        hotspot=(-3.0, 8.0, -11.2), hotspot_normal=(0, 0.3, 1))
    face.prism([(-14.0, 0.0), (-11.2, 0.0), (-11.6, 10.0), (-14.0, 10.0)],
               extent=18.0, axis="x", offset=(-3.0, 0.0, 0.0))

    pile = b.part(
        "muckpile", "muck",
        label="Muckpile",
        note="Blasted rock at the toe of the face. Its fragmentation is set "
             "by the blast, not by the shovel, and it decides how fast the "
             "bucket fills. Coarse, blocky muck means a part-full bucket on "
             "every pass, which quietly costs more than most people expect.",
        hotspot=(-3.0, 1.6, -9.0), hotspot_normal=(0, 0.6, 1))
    pile.prism([(-11.2, 0.0), (-6.6, 0.0), (-11.2, 3.4)],
               extent=16.0, axis="x", offset=(-3.0, 0.0, 0.0))

    # The two machines, each from its own generator. Both ship with their own
    # scale figure; two of them would stand in the parts list as duplicates
    # and, worse, put a person inside the loading area. One is added below,
    # standing where a person could actually be.
    b.absorb(make_shovel.build(), prefix="sh_", drop=("scale_figure",))
    b.group("truck", origin=SPOT)
    b.absorb(make_dumper.build(), prefix="tr_",
             xform=compose(translate(*SPOT), rotate("y", 180.0)),
             parent="truck", drop=("scale_figure",))

    # Well back from both machines and out of the swing circle.
    add_scale_figure(b, x=-6.5, z=12.5, facing_deg=160.0)

    b.animate("loading-cycle", shovel_channels() + [truck_channel()])
    return b


def main():
    b = build()
    glb = WEB / "models" / "loading-cycle.glb"
    summary = b.write(glb)
    record = dict(SPECS)
    record["model"] = "models/loading-cycle.glb"
    record["extents_m"] = summary["extents_m"]
    record["triangles"] = summary["triangles"]
    record["bytes"] = summary["bytes"]
    record["parts"] = summary["parts"]
    record["animation"] = {"name": "loading-cycle", "seconds": T_END,
                           "speed_vs_real": 4}
    (WEB / "data" / "loading-cycle.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"loading-cycle.glb {summary['bytes']/1024:7.1f} KB  "
          f"{summary['triangles']:5d} tris  "
          f"{len(summary['parts'])} parts  extents {summary['extents_m']}")
    return record


if __name__ == "__main__":
    main()
