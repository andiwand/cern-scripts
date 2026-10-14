#!/usr/bin/env python3
"""Reproduce the charged-pion extension and independent midpoint reference."""
import argparse
import math
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--base-table", type=Path, required=True)
p.add_argument("--generator-build", type=Path, required=True)
p.add_argument("--data-root", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--check", type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent
shared = here.parent / "fatras-neutral-hadrons"
for stem, seed, events, offset in [
    ("silicon-pion-high", 8342, 512, 0),
    ("silicon-pion-midpoints", 9242, 256, 0.5),
]:
    momenta = [20 * math.exp(math.log(350) * (i - offset) / 52) for i in range(1, 53)]
    subprocess.run(
        [
            sys.executable,
            str(shared / "generate.py"),
            "--build",
            str(a.generator_build),
            "--data-root",
            str(a.data_root),
            "--output",
            str(a.output / (stem + ".table")),
            "--projectiles",
            "211",
            "-211",
            "--seed",
            str(seed),
            "--events",
            str(events),
            "--momenta",
            *map(str, momenta),
        ],
        check=True,
    )
extended = a.output / "silicon-pion-extended.table"
subprocess.run(
    [
        sys.executable,
        str(here / "extend-table.py"),
        str(a.base_table),
        str(a.output / "silicon-pion-high.table"),
        "--output",
        str(extended),
    ],
    check=True,
)
if a.check:
    for path in [extended, a.output / "silicon-pion-midpoints.table"]:
        subprocess.run([str(a.check), str(path)], check=True)
subprocess.run(
    [
        sys.executable,
        str(shared / "compare.py"),
        str(extended),
        str(a.output / "silicon-pion-midpoints.table"),
        "--output",
        str(a.output / "high-midpoint-comparison.json"),
    ],
    check=True,
)
