#!/usr/bin/env python3
"""Run the four deterministic navigator probes sequentially."""

import argparse, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--revision", required=True)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output-prefix", type=Path, required=True)
p.add_argument("--results", type=Path, required=True)
a = p.parse_args()
base = Path(__file__).parent
subprocess.run(
    [sys.executable, str(base / "probe.py"), "--input", str(a.input)], check=True
)
runs = []
for name, extra in [
    ("native", []),
    (
        "tryall10",
        ["--try-all-pt-max", "1000", "--far-limit-mm", "10", "--step-mm", "10"],
    ),
    ("tryall5", ["--try-all-pt-max", "1000", "--far-limit-mm", "5", "--step-mm", "5"]),
    (
        "tryall2p5",
        ["--try-all-pt-max", "1000", "--far-limit-mm", "2.5", "--step-mm", "2.5"],
    ),
]:
    out = Path(str(a.output_prefix) + "-" + name)
    runs.append(str(out))
    subprocess.run(
        [
            sys.executable,
            str(base / "run-scan.py"),
            "--variant",
            "probe-" + name,
            "--revision",
            a.revision,
            "--input",
            str(a.input),
            "--output",
            str(out),
            "--events",
            "1",
            "--transport-only",
            "--charged-p-min",
            ".001",
            "--charged-pt-min",
            ".001",
            "--max-steps",
            "5000",
            "--loop-fraction",
            "4",
            *extra,
        ],
        check=True,
    )
subprocess.run(
    [
        sys.executable,
        str(base / "probe.py"),
        "--input",
        str(a.input),
        "--runs",
        *runs,
        "--output",
        str(a.results / "probe.json"),
    ],
    check=True,
)
