#!/usr/bin/env python3
"""Generate a training table and an independent midpoint reference for projectiles.

Default grid: 100 logarithmic nodes, 48 over 0.1-20 GeV/c plus 52 up to ~7 TeV/c.
The midpoint reference uses the geometric midpoints with fewer events and an
independent seed. Compare both with compare.py.

  calibrate.py --name kaons --projectiles 321 -321 --seed 20442 \
      --build GENERATOR_BUILD --data-root G4DATA --output DIR
"""

from pathlib import Path
import argparse, math, subprocess, sys

p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--build", type=Path, required=True, help="CMake build of this folder")
p.add_argument("--data-root", type=Path, required=True)
p.add_argument("--name", required=True, help="Table stem: silicon-NAME.table")
p.add_argument("--projectiles", type=int, nargs="+", required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--midpoint-seed", type=int, help="Default: seed + 2100")
p.add_argument("--events", type=int, default=512)
p.add_argument("--midpoint-events", type=int, default=256)
p.add_argument("--material", default="G4_Si")
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
grid = [0.1 * math.exp(math.log(200) * i / 47) for i in range(48)] + [
    20 * math.exp(math.log(350) * i / 52) for i in range(1, 53)
]
midpoints = [math.sqrt(x * y) for x, y in zip(grid, grid[1:])]
for name, points, events, seed in [
    (a.name, grid, a.events, a.seed),
    (a.name + "-midpoints", midpoints, a.midpoint_events, a.midpoint_seed or a.seed + 2100),
]:
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("generate.py")),
            "--build",
            str(a.build),
            "--data-root",
            str(a.data_root),
            "--material",
            a.material,
            "--output",
            str(a.output / f"silicon-{name}.table"),
            "--projectiles",
            *map(str, a.projectiles),
            "--events",
            str(events),
            "--seed",
            str(seed),
            "--momenta",
            *map(str, points),
        ],
        check=True,
    )
