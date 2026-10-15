"""Time-shift regression: photons must not inherit the neutral-hadron clock."""

import argparse, csv, json, math, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--material-map", type=Path, required=True)
a = p.parse_args()
keys = [
    "particle_id_pv",
    "particle_id_sv",
    "particle_id_part",
    "particle_id_gen",
    "particle_id_subpart",
    "particle_type",
    "process",
    "vx",
    "vy",
    "vz",
    "vt",
    "px",
    "py",
    "pz",
    "m",
    "q",
]
for name, time in [("prompt", 0), ("late", 2997924.58)]:
    inp = a.work / ("photons-" + name + "-input")
    inp.mkdir()
    with (inp / "event000000000-particles.csv").open("w") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(keys)
        for i in range(300):
            phi = 2 * math.pi * i / 300
            eta = -2 + 4 * ((i * 137) % 300) / 300
            writer.writerow(
                [
                    1,
                    0,
                    i + 1,
                    0,
                    0,
                    22,
                    0,
                    0,
                    0,
                    0,
                    time,
                    math.cos(phi),
                    math.sin(phi),
                    math.sinh(eta),
                    0,
                    0,
                ]
            )
    subprocess.run(
        [
            "python3",
            str(Path(__file__).with_name("run.py")),
            "--source",
            str(a.source),
            "--build",
            str(a.build),
            "--work",
            str(a.work),
            "--case",
            "standard",
            "--events",
            "1",
            "--input",
            str(inp),
            "--material-map",
            str(a.material_map),
            "--output",
            str(a.work / ("photons-" + name)),
        ],
        check=True,
    )


def read(name):
    with (a.work / ("photons-" + name) / "event000000000-hits.csv").open() as f:
        return list(csv.DictReader(f))


left, right = read("prompt"), read("late")
assert len(left) == len(right) and len(left) > 0
# Single precision CSV positions can differ in their last digits; compare the
# same ordered hit identities, energies and positions with rounding tolerance.
maxdiff = 0
for x, y in zip(left, right):
    for key in [
        "geometry_id",
        "particle_id_pv",
        "particle_id_sv",
        "particle_id_part",
        "particle_id_gen",
        "particle_id_subpart",
    ]:
        assert x[key] == y[key]
    # Hit CSV time is float32: at 10 us its spacing is 0.25 mm/c.
    assert abs((float(y["tt"]) - float(x["tt"])) - 2997924.58) < 0.3
    for key in ["tx", "ty", "tz", "tpx", "tpy", "tpz", "te", "deltae"]:
        diff = abs(float(x[key]) - float(y[key]))
        maxdiff = max(maxdiff, diff)
        assert diff < 1e-4
(a.work / "late-photon-check.json").write_text(
    json.dumps(
        {
            "input_photons": 300,
            "late_time_ns": 10000,
            "matched_hits": len(left),
            "max_coordinate_or_momentum_difference": maxdiff,
        },
        indent=2,
    )
)
