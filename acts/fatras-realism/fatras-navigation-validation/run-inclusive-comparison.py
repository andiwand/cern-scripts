#!/usr/bin/env python3
"""Sequential main/current/default-Geant4 comparison on unfiltered ID inputs."""

import argparse, json, os, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output-prefix", type=Path, required=True)
p.add_argument("--events", type=int, default=5)
p.add_argument("--revision", required=True)
a = p.parse_args()
root = Path("/Users/andreas/cern/scripts/acts")
runner = root / "fatras-charged-mesons/run-comparison.py"
envscript = root / "fatras-neutral-hadrons/odd/run-env.sh"
material = root / "fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root"
table = root / "fatras-neutral-refinement/data/2026-10-14/silicon-all-low.table"
for mode in ["main", "changed", "geant4"]:
    build = (
        Path("/private/tmp/acts-fatras-main-build")
        if mode == "main"
        else Path("/Users/andreas/cern/build/acts/acts/dev3")
    )
    source = (
        "/private/tmp/acts-fatras-main"
        if mode == "main"
        else "/Users/andreas/cern/source/acts/acts/dev3"
    )
    revision = (
        "300b664a3d9c32ec928208e7eb18df40e7b2721b" if mode == "main" else a.revision
    )
    out = Path(str(a.output_prefix) + "-" + mode)
    cmd = [
        "bash",
        str(envscript),
        str(runner),
        "--mode",
        mode,
        "--source",
        source,
        "--build",
        str(build),
        "--revision",
        revision,
        "--input",
        str(a.input),
        "--output",
        str(out),
        "--material-map",
        str(material),
        "--events",
        str(a.events),
    ]
    if mode == "changed":
        cmd.extend(["--table", str(table)])
    env = dict(os.environ)
    env["ACTS_VALIDATION_BUILD"] = str(build)
    env["PYTHONPATH"] = (
        str(root / "fatras-charged-mesons/data/2026-10-14")
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    with Path(str(out) + ".log").open("w") as log:
        proc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    Path(str(out) + "-command.json").write_text(
        json.dumps({"command": cmd, "returncode": proc.returncode}, indent=2) + "\n"
    )
    proc.check_returncode()
    print(mode, "complete", flush=True)
