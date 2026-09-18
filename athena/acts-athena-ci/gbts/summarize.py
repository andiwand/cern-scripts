#!/usr/bin/env python3
"""Read per-algorithm CPU out of the PerfMonMTSvc Execute table of each run."""
import re, sys, glob, os, statistics

ALGS = ["ActsPixelSeedingAlg", "ActsLargeRadiusStripSeedingAlg",
        "ActsPixelClusterizationAlg", "ActsStripClusterizationAlg"]
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")

def read(logfile):
    out = {}
    with open(logfile, errors="replace") as f:
        for line in f:
            m = PAT.search(line.rstrip())
            if m:
                out[m.group(3)] = (int(m.group(1)), float(m.group(2)))
    return out

# job directories live in the acts-athena-ci run area, not next to this script
base = os.environ.get("ACI_RUN", "/home/astefl/source/acts/acts-athena-ci/run")
groups = {"base": [], "pr": [], "ftf": []}
for tag in groups:
    for d in sorted(glob.glob(os.path.join(base, f"{tag}_[0-9]"))):
        log = os.path.join(d, "log.RAWtoALL")
        if os.path.exists(log):
            r = read(log)
            if r:
                groups[tag].append((os.path.basename(d), r))

for alg in ALGS:
    print(f"\n=== {alg} ===")
    for tag in ("base", "pr", "ftf"):
        vals = []
        for name, r in groups[tag]:
            if alg in r:
                n, ms = r[alg]
                vals.append(ms)
                print(f"  {name:10s} n={n:3d}  {ms:10.2f} ms")
        if len(vals) > 1:
            print(f"  {tag:10s} mean={statistics.mean(vals):9.2f} ms  "
                  f"sd={statistics.stdev(vals):7.2f} ({100*statistics.stdev(vals)/statistics.mean(vals):.1f}%)")
        elif vals:
            print(f"  {tag:10s} mean={vals[0]:9.2f} ms")
