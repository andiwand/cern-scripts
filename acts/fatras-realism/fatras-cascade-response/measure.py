import argparse

p = argparse.ArgumentParser(
    description="Alternating inclusive timings and independent worker/G4 replay"
)
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
p.add_argument(
    "--control-module",
    type=__import__("pathlib").Path,
    default=__import__("pathlib").Path.home()
    / "cern/scripts/acts/fatras-realism/fatras-radiative-secondaries/results/2026-10-16/pruned-build",
)
a = p.parse_args()
from pathlib import Path
import json, subprocess, sys

w = a.work
s = Path.home() / "cern/scripts/acts"
src = Path.home() / "cern/source/acts/acts/fatras-soft"
rev = subprocess.check_output(
    ["git", "-C", str(src), "rev-parse", "HEAD"], text=True
).strip()
for i in range(3):
    for name, module, compiled in [
        ("control", str(a.control_module), "0429b7c1e1225233246ce2c1d756a043e5f971ad"),
        ("current", str(w / "final-build/pruned-build"), rev),
    ]:
        out = w / f"{name}-{i}"
        cmd = [
            sys.executable,
            str(s / "fatras-radiative-secondaries/run.py"),
            "--source",
            str(src),
            "--module",
            module,
            "--output",
            str(out),
        ]
        subprocess.run(cmd, check=True)
        p = out / "metadata.json"
        meta = json.loads(p.read_text())
        meta["compiled_physics_revision"] = compiled
        meta["measurement"] = (
            "Sequential alternating three-event samples; no concurrent compilation or analysis"
        )
        p.write_text(json.dumps(meta, indent=2))
        print(name, i, meta["sequencer_cpu_seconds"] / 3, flush=True)
for threads in [1, 4]:
    out = w / f"standard-{threads}"
    subprocess.run(
        [
            sys.executable,
            str(s / "fatras-radiative-secondaries/run.py"),
            "--source",
            str(src),
            "--module",
            str(w / "final-build/bridge"),
            "--output",
            str(out),
            "--standard",
            "--threads",
            str(threads),
        ],
        check=True,
    )
cmd = json.loads(
    (
        s
        / "fatras-radiative-secondaries/results/2026-10-16/geant4-refreshed.command.json"
    ).read_text()
)
cmd[cmd.index("--output") + 1] = str(w / "geant4-refreshed")
cmd[cmd.index("--revision") + 1] = rev
(w / "geant4-refreshed.command.json").write_text(json.dumps(cmd, indent=2))
with (w / "geant4-refreshed.log").open("w") as f:
    subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
print("Measurement complete", flush=True)
