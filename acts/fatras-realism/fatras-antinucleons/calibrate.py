from pathlib import Path
import math, subprocess, sys
import argparse

p = argparse.ArgumentParser(
    description="Generate antinucleon training and midpoint samples"
)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--data-root", type=Path, required=True)
a = p.parse_args()
out = a.output
out.mkdir(parents=True, exist_ok=True)
shared = Path(__file__).resolve().parent.parent / "fatras-neutral-hadrons"
grid = [0.1 * math.exp(math.log(200) * i / 47) for i in range(48)] + [
    20 * math.exp(math.log(350) * i / 52) for i in range(1, 53)
]
for name, points, events, seed in [
    ("antinucleons", grid, 512, 14642),
    ("midpoints", [math.sqrt(a * b) for a, b in zip(grid, grid[1:])], 256, 17542),
]:
    subprocess.run(
        [
            sys.executable,
            str(shared / "generate.py"),
            "--build",
            str(a.build),
            "--data-root",
            str(a.data_root),
            "--output",
            str(out / f"silicon-{name}.table"),
            "--projectiles",
            "-2212",
            "-2112",
            "--events",
            str(events),
            "--seed",
            str(seed),
            "--momenta",
            *map(str, points),
        ],
        check=True,
    )
