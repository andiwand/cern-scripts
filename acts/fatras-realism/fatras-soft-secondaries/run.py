"""Run one inclusive soft-secondary validation case using existing ODD tools."""

import argparse, json, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--work", type=Path, required=True)
p.add_argument(
    "--case",
    choices=["standard", "photon", "ionisation", "all", "soft", "geant4"],
    required=True,
)
p.add_argument("--events", type=int, default=3)
p.add_argument("--threads", type=int, default=1)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--material-map", type=Path, required=True)
p.add_argument("--output", type=Path)
p.add_argument("--tools-root", type=Path, default=Path.home() / "cern/scripts/acts")
p.add_argument("--world-module", type=Path)
a = p.parse_args()
bounded = a.case in ["photon", "ionisation", "all", "soft"]
if a.threads != 1 and (bounded or a.case == "geant4"):
    p.error("Bounded prototype and Geant4 reference require one worker")
if subprocess.check_output(
    ["git", "-C", str(a.source), "status", "--porcelain"], text=True
):
    p.error("Source checkout must be clean")
revision = subprocess.check_output(
    ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
).strip()
name = (
    "standard-final"
    if a.case == "standard"
    else "geant4" if a.case == "geant4" else "bounded-" + a.case
)
output = a.output or a.work / name
module = a.work / (
    "bounded-" + ("all" if a.case == "soft" else a.case) + "-build"
    if bounded
    else "bridge-all"
)
if a.case == "geant4":
    module = a.world_module or a.tools_root / "fatras-charged-mesons/data/2026-10-14"
runner = a.tools_root / (
    "fatras-low-momentum/run.py" if bounded else "fatras-runtime-model/run.py"
)
cmd = [
    str(a.tools_root / "fatras-neutral-hadrons/odd/run-env.sh"),
    str(runner),
    "--mode",
    "geant4" if a.case == "geant4" else "live",
    "--source",
    str(a.source),
    "--build",
    str(a.build),
    "--revision",
    revision,
    "--input",
    str(a.input),
    "--output",
    str(output),
    "--material-map",
    str(a.material_map),
    "--events",
    str(a.events),
    "--threads",
    str(a.threads),
    "--module-dir",
    str(module),
]
if bounded:
    cmd += ["--navigation-mode", "2", "--navigation-step", "5", "--max-steps", "50000"]
if a.case == "soft":
    cmd += ["--p-min", "0.0002", "--pt-min", "0.00005"]
a.work.mkdir(parents=True, exist_ok=True)
(a.work / (output.name + "-command.json")).write_text(json.dumps(cmd, indent=2))
with (a.work / (output.name + ".log")).open("w") as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
if a.case != "geant4":
    path = output / "metadata.json"
    meta = json.loads(path.read_text())
    physics = (
        a.work
        / ("bridge-" + (a.case if a.case in ["photon", "ionisation"] else "all"))
        / "soft-physics.json"
    )
    meta["soft_physics"] = json.loads(physics.read_text())
    path.write_text(json.dumps(meta, indent=2))
