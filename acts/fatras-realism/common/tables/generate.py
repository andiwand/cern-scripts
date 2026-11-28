#!/usr/bin/env python3
"""Generate a Fatras interaction library with the external Geant4 generator.

Build the generator first: cmake -S . -B BUILD -DGeant4_DIR=...; cmake --build BUILD
Supported projectiles: 211, -211, 2212, -2212, 2112, -2112, 130, 321, -321.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--projectiles", type=int, nargs="+", default=[2112, 130])
    p.add_argument("--material", default="G4_Si")
    p.add_argument("--events", type=int, default=512)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--momenta",
        type=float,
        nargs="+",
        default=[0.1 * math.exp(math.log(200) * i / 47) for i in range(48)],
    )
    p.add_argument(
        "--diagnostic-rejection",
        action="store_true",
        help="Reject nonphysical residuals instead of failing; conditional diagnostic spectra only, never production calibration",
    )
    a = p.parse_args()
    if a.output.exists():
        p.error("output already exists")
    env = dict(os.environ)
    datasets = {
        "G4ENSDFSTATEDATA": "G4ENSDFSTATE",
        "G4LEDATA": "G4EMLOW",
        "G4LEVELGAMMADATA": "PhotonEvaporation",
        "G4RADIOACTIVEDATA": "RadioactiveDecay",
        "G4PARTICLEXSDATA": "G4PARTICLEXS",
        "G4SAIDXSDATA": "G4SAIDDATA",
        "G4ABLADATA": "G4ABLA",
        "G4INCLDATA": "G4INCL",
        "G4NEUTRONHPDATA": "G4NDL",
        "G4PIIDATA": "G4PII",
        "G4REALSURFACEDATA": "RealSurface",
    }
    for key, stem in datasets.items():
        paths = sorted(a.data_root.glob(stem + "*"))
        if len(paths) != 1:
            p.error(f"expected one {stem} dataset in {a.data_root}")
        env[key] = str(paths[0].resolve())
    env.pop("FATRAS_DIAGNOSTIC_REJECT_INVALID_RESIDUALS", None)
    if a.diagnostic_rejection:
        env["FATRAS_DIAGNOSTIC_REJECT_INVALID_RESIDUALS"] = "1"
    binary = a.build.resolve() / "generate-table"
    command = [
        str(binary),
        str(a.output.resolve()),
        a.material,
        str(a.events),
        str(a.seed),
        ",".join(map(str, a.projectiles)),
        *map(str, a.momenta),
    ]
    with a.output.with_suffix(".log").open("w") as log:
        subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True
        )
    metadata = {
        "command": command,
        "physics_list": "FTFP_BERT",
        "projectiles": a.projectiles,
        "seed": a.seed,
        "events_per_node": a.events,
        "diagnostic_rejection": a.diagnostic_rejection,
        "datasets": {key: env[key] for key in datasets},
        "generator_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(
            Path(__file__).with_name("generate.cpp").read_bytes()
        ).hexdigest(),
        "table_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
        "limitations": "Elemental targets; residual includes untransported nuclear fragments and local deposits. Not a full detector simulation or a production calibration.",
    }
    a.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(a.output)


if __name__ == "__main__":
    main()
