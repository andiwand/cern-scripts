import argparse

p = argparse.ArgumentParser()
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
p.add_argument("--variant", choices=["optimized", "guarded"], default="guarded")
a = p.parse_args()
variant = a.variant
from pathlib import Path
import json, subprocess, sys, hashlib

w = a.work
s = Path.home() / "cern/scripts/acts"
src = Path.home() / "cern/source/acts/acts/fatras-soft"
for i in range(3):
    out = w / f"{variant}-{i}"
    subprocess.run(
        [
            sys.executable,
            str(s / "fatras-radiative-secondaries/run.py"),
            "--source",
            str(src),
            "--module",
            str(w / f"{variant}-build/pruned-build"),
            "--output",
            str(out),
        ],
        check=True,
    )
    for f in out.glob("event*.csv"):
        assert (
            hashlib.sha256(f.read_bytes()).digest()
            == hashlib.sha256((w / "current-0" / f.name).read_bytes()).digest()
        ), f
    print(
        i,
        json.loads((out / "metadata.json").read_text())["sequencer_cpu_seconds"] / 3,
        "identical",
        flush=True,
    )
for trial, threads in enumerate([1, 4, 4, 4]):
    out = w / (
        f"{variant}-standard-{threads}" + (f"-repeat{trial-1}" if trial > 1 else "")
    )
    subprocess.run(
        [
            sys.executable,
            str(s / "fatras-radiative-secondaries/run.py"),
            "--source",
            str(src),
            "--module",
            str(w / f"{variant}-build/bridge"),
            "--output",
            str(out),
            "--standard",
            "--threads",
            str(threads),
        ],
        check=True,
    )
print("Optimized measurements complete", flush=True)
