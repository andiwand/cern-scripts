#!/usr/bin/env python3
"""Run isolated reconstruction variants, retaining every log and exit code."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("output", type=Path)
p.add_argument("events", type=int)
p.add_argument("skip", type=int)
p.add_argument("variants", nargs="+")
p.add_argument("--parallel", type=int, default=3)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)


def run(variant):
    log = a.output / (variant + ".driver.log")
    with log.open("x") as stream:
        result = subprocess.run(
            [
                "bash",
                str(Path(__file__).with_name("run_nn.sh")),
                str(a.output / variant),
                variant,
                str(a.events),
                str(a.skip),
                "8",
                "1",
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
    print(variant, result.returncode, flush=True)
    return result.returncode


with ThreadPoolExecutor(max_workers=a.parallel) as pool:
    codes = list(pool.map(run, a.variants))
raise SystemExit(int(any(codes)))
