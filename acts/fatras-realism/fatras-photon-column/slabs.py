"""Targeted matched-material validation of sampled photon birth columns."""

import argparse
import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
w = a.work
out = w / "slabs"
out.mkdir(parents=True, exist_ok=True)
cases = []
for pdg, energy, mat, mode, profile, slices in [
    (22, 1, "G4_Si", "primary", "common", [1, 20, 1000]),
    (22, 20, "G4_Si", "cascade", "common", [1, 1000]),
    (11, 20, "G4_Si", "cascade", "common", [1, 1000]),
    (22, 5, "G4_Cu", "primary", "common", [1, 1000]),
    (22, 20, "G4_Si", "cascade", "full", [1, 1000]),
    (11, 20, "G4_Si", "cascade", "full", [1, 1000]),
]:
    cases.extend((pdg, energy, mat, mode, profile, n) for n in slices)
binary = w / "slab-build/slab"
for i, (pdg, energy, mat, mode, profile, slices) in enumerate(cases):
    target = out / f"{mode}-{profile}-{mat}-{pdg}-{energy}-30-fatras-{slices}.csv"
    if target.with_suffix(".json").exists():
        raise RuntimeError(f"Refusing to overwrite {target}")
    command = [
        str(binary),
        "fatras",
        mat,
        str(pdg),
        str(energy),
        "30",
        "100000",
        str(slices),
        profile,
        mode,
        str(400000 + i),
        str(target),
    ]
    start = time.monotonic()
    with target.with_suffix(".log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    values = {r["metric"]: float(r["mean"]) for r in csv.DictReader(target.open())}
    assert values["photoelectric"] == values["annihilation"] == 0
    target.with_suffix(".json").write_text(
        json.dumps(
            dict(
                command=command,
                seed=400000 + i,
                n=100000,
                backend="fatras",
                material=mat,
                pdg=pdg,
                energy_MeV=energy,
                thickness_mm=30,
                profile=profile,
                mode=mode,
                slices=slices,
                wall_seconds=time.monotonic() - start,
                binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            ),
            indent=2,
        )
    )
    print(i + 1, len(cases), target.name, flush=True)
