#!/usr/bin/env python3
"""Strong-scaling and scheduling reproducibility probe; standard G4 data env required."""

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--executable", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events-per-point", type=int, default=512)
p.add_argument("--repeats", type=int, default=3)
p.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4, 8])
a = p.parse_args()
if (
    a.events_per_point < 1
    or a.repeats < 1
    or any(n < 1 for n in a.workers)
    or 1 not in a.workers
):
    p.error("positive counts and a one-worker baseline required")
a.output.mkdir(parents=True, exist_ok=True)
schedule = []
for repeat in range(a.repeats):
    for workers in a.workers if repeat % 2 == 0 else a.workers[::-1]:
        schedule.append((repeat, workers, "forward"))
schedule += [(a.repeats, n, "reverse") for n in sorted({1, max(a.workers)})]
runs = []
reference_hashes = None
for repeat, workers, order in schedule:
    dest = a.output / f"r{repeat}-w{workers}-{order}"
    if dest.exists():
        raise FileExistsError(dest)
    command = [
        str(a.executable.resolve()),
        str(dest),
        str(workers),
        str(a.events_per_point),
        order,
    ]
    with dest.with_suffix(".log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    row = json.loads((dest / "run.json").read_text())
    row.update(directory=dest.name, repeat=repeat, command=command)
    hashes = {}
    for name in ["events.csv", "products.csv", "rates.csv"]:
        path = dest / name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if reference_hashes is None:
            with (
                path.open("rb") as src,
                gzip.open(path.with_suffix(".csv.gz"), "wb") as dst,
            ):
                shutil.copyfileobj(src, dst)
    if reference_hashes is None:
        reference_hashes = hashes
    row["output_sha256"] = hashes
    row["byte_identical_to_first_run"] = hashes == reference_hashes
    runs.append(row)
    (a.output / "runs.json").write_text(json.dumps(runs, indent=2) + "\n")
    print(
        f"{dest.name}: {row['sampling_wall_s']:.3f}s, identical={row['byte_identical_to_first_run']}",
        flush=True,
    )
    if hashes != reference_hashes:
        raise RuntimeError("scheduling changed the sampled output; see hashes")
    for name in hashes:
        (dest / name).unlink()  # baseline compressed; matching outputs are redundant
