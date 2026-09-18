#!/usr/bin/env python3
"""ActsCore vs ActsTrk pixel space point formation, normalised to a control algorithm."""
import re, sys, glob, os, statistics
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")
TARGET = "ActsPixelSpacePointFormationAlg"
CONTROL = os.environ.get("CONTROL", "ActsPixelClusterizationAlg")
def read(logfile):
    out = {}
    with open(logfile, errors="replace") as f:
        for line in f:
            m = PAT.search(line.rstrip())
            if m: out[m.group(3)] = (int(m.group(1)), float(m.group(2)))
    return out
tag = sys.argv[1] if len(sys.argv) > 1 else "p"
# job directories live in the acts-athena-ci run area, not next to this script
base = os.environ.get("ACI_RUN", "/home/astefl/source/acts/acts-athena-ci/run")
res = {}
for v in ("core", "trk"):
    rows = []
    for d in sorted(glob.glob(os.path.join(base, f"{tag}_{v}_*"))):
        log = os.path.join(d, "log.RAWtoALL")
        if not os.path.exists(log): continue
        r = read(log)
        if TARGET in r and CONTROL in r:
            rows.append((os.path.basename(d), r[TARGET][1], r[CONTROL][1]))
    res[v] = rows
for v in ("core", "trk"):
    print(f"=== {v}")
    for name, t, c in res[v]:
        print(f"  {name:20s} {TARGET}={t:9.2f}  {CONTROL}={c:9.2f}  ratio={t/c:.4f}")
    if res[v]:
        raw = [t for _, t, _ in res[v]]
        rat = [t/c for _, t, c in res[v]]
        print(f"  mean raw = {statistics.mean(raw):9.2f} ms"
              + (f" sd={statistics.stdev(raw):6.2f} ({100*statistics.stdev(raw)/statistics.mean(raw):.1f}%)" if len(raw)>1 else ""))
        print(f"  mean norm= {statistics.mean(rat):9.5f}"
              + (f" sd={statistics.stdev(rat):8.5f} ({100*statistics.stdev(rat)/statistics.mean(rat):.1f}%)" if len(rat)>1 else ""))
if res["core"] and res["trk"]:
    c = statistics.mean([t/x for _, t, x in res["core"]])
    t = statistics.mean([t/x for _, t, x in res["trk"]])
    cr = statistics.mean([t for _, t, _ in res["core"]])
    tr = statistics.mean([t for _, t, _ in res["trk"]])
    print(f"\nActsCore vs ActsTrk: normalised {100*(c/t-1):+.1f}%   raw {100*(cr/tr-1):+.1f}%")
