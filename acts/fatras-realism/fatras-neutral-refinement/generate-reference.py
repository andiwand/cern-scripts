#!/usr/bin/env python3
"""Generate reproducible neutral or material reference samples outside ACTS."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--generator", type=Path, required=True)
p.add_argument(
    "--datasets", type=Path, required=True, help="JSON with Geant4 datasets mapping"
)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--scan", choices=["neutral", "targets", "carbon"], required=True)
p.add_argument(
    "--diagnostic-rejection",
    action="store_true",
    help="Explicitly reject invalid residuals; produces conditional diagnostic spectra, not production calibration",
)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
datasets = json.loads(a.datasets.read_text())["datasets"]
env = dict(os.environ)
env.update(datasets)
if a.diagnostic_rejection:
    env["FATRAS_DIAGNOSTIC_REJECT_INVALID_RESIDUALS"] = "1"
else:
    env.pop("FATRAS_DIAGNOSTIC_REJECT_INVALID_RESIDUALS", None)
if a.scan == "neutral":
    targets, species, count, seed = ["Si"], "2112,-2112,130", 256, 38742
    grid = [0.001, 0.002, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.099]
elif a.scan == "targets":
    targets, species, count, seed = ["C", "Al", "Si"], "211,-211,2212", 1024, 40742
    grid = [0.15, 0.3, 0.7, 1.5, 5, 20]
else:
    targets, species, count, seed = ["C"], "211,-211,2212", 256, 41742
    grid = [0.1 * math.exp(i / 99 * math.log(70000)) for i in range(100)]
    grid[-1] = 7000
for target in targets:
    stem = a.output / f"{a.scan}-{target}"
    assert not stem.with_suffix(
        ".table"
    ).exists(), "Refuse to overwrite a reference sample"
    cmd = [
        str(a.generator.resolve()),
        str(stem.with_suffix(".table")),
        f"G4_{target}",
        str(count),
        str(seed),
        species,
        *[format(x, ".17g") for x in grid],
    ]
    meta = {
        "command": cmd,
        "datasets": datasets,
        "diagnostic_rejection": a.diagnostic_rejection,
        "generator_sha256": hashlib.sha256(a.generator.read_bytes()).hexdigest(),
    }
    with stem.with_suffix(".log").open("w") as log:
        result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    meta["returncode"] = result.returncode
    if result.returncode == 0:
        meta["table_sha256"] = hashlib.sha256(
            stem.with_suffix(".table").read_bytes()
        ).hexdigest()
    stem.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    result.check_returncode()
