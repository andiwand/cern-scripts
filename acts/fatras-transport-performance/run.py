"""Run a recorded transport experiment with unchanged inclusive soft physics."""

import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--module", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=3)
p.add_argument("--input", type=Path, default=Path.home() / "cern/scripts/acts/fatras-runtime-model/results/2026-10-15/inputs")
p.add_argument("--step", type=float, default=5)
p.add_argument("--transport-only", action="store_true")
p.add_argument("--tools-root", type=Path, default=Path.home() / "cern/scripts/acts")
a = p.parse_args()
revision = subprocess.check_output(["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True).strip()
cmd = [
    str(a.tools_root / "fatras-neutral-hadrons/odd/run-env.sh"),
    str(a.tools_root / "fatras-low-momentum/run.py"),
    "--mode", "live", "--source", str(a.source), "--revision", revision,
    "--build", str(Path.home() / "cern/build/acts/acts/dev3"),
    "--input", str(a.input), "--output", str(a.output),
    "--module-dir", str(a.module), "--events", str(a.events), "--threads", "1",
    "--material-map", str(a.tools_root / "fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root"),
    "--navigation-mode", "2", "--navigation-step", str(a.step),
    "--max-steps", "50000", "--loops", "4", "--p-min", "0.0002", "--pt-min", "0.00005",
]
if a.transport_only:
    cmd += ["--transport-only"]
if a.output.exists():
    p.error("Refusing to overwrite a run directory")
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.with_suffix(".command.json").write_text(json.dumps(cmd, indent=2))
with a.output.with_suffix(".log").open("w") as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
meta_path = a.output / "metadata.json"
meta = json.loads(meta_path.read_text())
meta["transport_experiment"] = json.loads((a.module / "experiment-build.json").read_text())
meta["soft_physics"] = {"ionisation_cut_GeV": .0001, "photon_cut_GeV": .0010219979, "legacy_decays": False}
if a.transport_only:
    meta["pileup"] = None
    meta["sample"] = "Deterministic charged transport probes"
    meta["soft_physics"] = None
meta_path.write_text(json.dumps(meta, indent=2))
print(json.dumps({"output": str(a.output), "cpu_s_per_event": meta["sequencer_cpu_seconds"] / a.events, "statistics": meta["navigation"]["statistics"]}))
