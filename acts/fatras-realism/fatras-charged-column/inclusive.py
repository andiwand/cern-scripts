"""Serial matched-event CPU repetitions and standard-navigation worker check."""

import argparse
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
s = Path(__file__).resolve().parent.parent
old = s / "fatras-photon-column/results/2026-10-16/runtime-build/pruned-build"
for i in range(3):
    for name, module in [
        ("control", old),
        ("current", a.work / "runtime-build/pruned-build"),
    ]:
        subprocess.run(
            [
                sys.executable,
                str(s / "fatras-radiative-secondaries/run.py"),
                "--source",
                str(a.source),
                "--module",
                str(module),
                "--output",
                str(a.work / f"{name}-{i}"),
            ],
            check=True,
        )
for threads in [1, 4]:
    subprocess.run(
        [
            sys.executable,
            str(s / "fatras-radiative-secondaries/run.py"),
            "--source",
            str(a.source),
            "--module",
            str(a.work / "runtime-build/bridge"),
            "--output",
            str(a.work / f"standard-{threads}"),
            "--standard",
            "--threads",
            str(threads),
        ],
        check=True,
    )
