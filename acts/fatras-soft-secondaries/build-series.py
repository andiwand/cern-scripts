"""Build standard navigation and three bounded-search physics ablations."""

import argparse, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--geant4-lib", type=Path, required=True)
p.add_argument("--tools-root", type=Path, default=Path.home() / "cern/scripts/acts")
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=True)
for name, cut, legacy in [
    ("all", "0.0001", False),
    ("photon", "inf", True),
    ("ionisation", "0.0001", True),
]:
    bridge = a.work / ("bridge-" + name)
    args = [
        sys.executable,
        str(Path(__file__).with_name("build.py")),
        "--source",
        str(a.source),
        "--build",
        str(a.build),
        "--output",
        str(bridge),
        "--geant4-lib",
        str(a.geant4_lib),
        "--ion-cut",
        cut,
        "--tools-root",
        str(a.tools_root),
    ]
    if legacy:
        args += ["--legacy-decays", "--prepare-only"]
    with (a.work / (name + "-build.log")).open("w") as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(
            [
                sys.executable,
                str(a.tools_root / "fatras-low-momentum/build.py"),
                "--source",
                str(a.source),
                "--bridge",
                str(bridge),
                "--output",
                str(a.work / ("bounded-" + name + "-build")),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
