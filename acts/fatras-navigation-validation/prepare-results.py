#!/usr/bin/env python3
"""Analyse completed trials, then losslessly compress bulky particle truth."""

import argparse, subprocess, sys, gzip, shutil, hashlib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("runs", nargs="+", type=Path)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
for run in a.runs:
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("analyse.py")),
            "--run",
            str(run),
            "--output",
            str(a.output / (run.name + ".json")),
            "--reference",
            "/Users/andreas/cern/scripts/acts/fatras-neutral-refinement/results/2026-10-14/secondary-gaps.json",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for source in run.glob("event*-particles_simulated.csv"):
        target = source.with_suffix(".csv.gz")
        assert not target.exists()
        with source.open("rb") as f, gzip.open(target, "wb", compresslevel=1) as g:
            shutil.copyfileobj(f, g)
        # Verify decompressed bytes before removing the redundant original.
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        with gzip.open(target, "rb") as g:
            digest = hashlib.sha256()
            for chunk in iter(lambda: g.read(1024 * 1024), b""):
                digest.update(chunk)
        assert digest.hexdigest() == expected
        source.unlink()
    print(run.name, flush=True)
