"""Inclusive radiation validation; default G4 reference and material are unchanged."""

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--module", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=3)
p.add_argument(
    "--input",
    type=Path,
    default=Path.home()
    / "cern/scripts/acts/fatras-runtime-model/results/2026-10-15/inputs",
)
p.add_argument("--brems-cut-MeV", type=float, default=0.1)
p.add_argument("--photon-cut-MeV", type=float, default=0.1)
p.add_argument("--disable-compton", action="store_true")
p.add_argument("--standard", action="store_true")
p.add_argument("--threads", type=int, default=1)
p.add_argument("--inside-env", action="store_true", help=argparse.SUPPRESS)
a = p.parse_args()
tools = Path(__file__).resolve().parent.parent
if not a.inside_env:
    if a.output.exists():
        p.error("Refusing to overwrite output")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(tools / "fatras-neutral-hadrons/odd/run-env.sh"),
        str(Path(__file__).resolve()),
        *sys.argv[1:],
        "--inside-env",
    ]
    a.output.with_suffix(".command.json").write_text(json.dumps(command, indent=2))
    with a.output.with_suffix(".log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(a.output)
    sys.exit()
sys.path.insert(0, str(a.module))
import acts.examples
import runtime_fatras

runtime_fatras.configure_photons(a.photon_cut_MeV * 0.001, not a.disable_compton)
runtime_fatras.configure_radiation(a.brems_cut_MeV * 0.001)
revision = subprocess.check_output(
    ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
).strip()
# The frozen base Config predates Compton. Supply its new fields through the
# compiled bridge, and omit only that field from the old Python Config copy.
common = a.output.with_suffix(".runner.py")
script = (tools / "fatras-runtime-model/run.py").read_text()
assert script.count('if key != "level":') == 1
common.write_text(
    script.replace(
        'if key != "level":',
        'if key not in ("level", "emComptonScattering", "emBremsstrahlungPhotonMinEnergy"):',
    )
)
runner = common if a.standard else tools / "fatras-low-momentum/run.py"
args = [
    "--mode",
    "live",
    "--source",
    str(a.source),
    "--revision",
    revision,
    "--build",
    str(Path.home() / "cern/build/acts/acts/dev3"),
    "--input",
    str(a.input),
    "--output",
    str(a.output),
    "--module-dir",
    str(a.module),
    "--events",
    str(a.events),
    "--threads",
    str(a.threads),
    "--material-map",
    str(tools / "fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root"),
]
if not a.standard:
    args += [
        "--runner",
        str(common),
        "--navigation-mode",
        "2",
        "--navigation-step",
        "5",
        "--max-steps",
        "50000",
        "--loops",
        "4",
        "--p-min",
        ".0002",
        "--pt-min",
        ".00005",
    ]
sys.argv = [str(runner), *args]
runpy.run_path(str(runner), run_name="__main__")
path = a.output / "metadata.json"
meta = json.loads(path.read_text())
meta["soft_physics"] = {
    "ionisation_cut_GeV": 0.0001,
    "photon_cut_GeV": a.photon_cut_MeV * 0.001,
    "compton": not a.disable_compton,
    "legacy_decays": False,
    "brems_production_cut_GeV": (
        a.brems_cut_MeV * 0.001 if a.brems_cut_MeV != float("inf") else None
    ),
    "coupled_electron_losses": a.brems_cut_MeV != float("inf"),
}
meta["radiation_module_sha256"] = hashlib.sha256(
    (a.module / "runtime_fatras.so").read_bytes()
).hexdigest()
meta["radiation_build"] = json.loads(
    (
        a.module / ("module-build.json" if a.standard else "experiment-build.json")
    ).read_text()
)
if (a.input / "probes.json").exists():
    meta["pileup"] = None
    meta["sample"] = "Controlled photon probes; see input/probes.json"
path.write_text(json.dumps(meta, indent=2))
