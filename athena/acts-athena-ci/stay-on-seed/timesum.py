#!/usr/bin/env python3
"""Per-algorithm CPU, main vs MR 92381, normalised to a control algorithm."""
import re, glob, os, statistics as st
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")
EVT = re.compile(r"PerfMonMTSvc\s+INFO\s+.*Event Loop\s*(?:CPU\s*)?.*?([0-9.]+)\s*ms")
CONTROL = "ActsPixelClusterizationAlg"
import sys
base = os.environ.get("RUN_ROOT", "/home/astefl/source/acts/acts-athena-ci/run/mr92381") + "/" + sys.argv[1]
def read(log):
    out = {}
    for line in open(log, errors="replace"):
        m = PAT.search(line.rstrip())
        if m: out[m.group(3)] = float(m.group(2))
    return out
runs = {s: [read(f) for f in sorted(glob.glob(f"{base}/{s}_*/log.RAWtoALL"))] for s in ("on", "off")}
runs = {s: [r for r in v if CONTROL in r] for s, v in runs.items()}
print(f"cycles: base {len(runs['on'])}, mr {len(runs['off'])}")
algs = sorted({a for r in runs["on"] for a in r if a.startswith("Acts")},
              key=lambda a: -st.mean(r.get(a, 0) for r in runs["on"]))
print(f"{'algorithm':48s} {'on ms':>10s} {'off ms':>10s} {'raw':>7s} {'norm':>7s} {'sd(norm) base/mr':>17s}")
for a in algs:
    m = [r[a] for r in runs["on"] if a in r]; p = [r[a] for r in runs["off"] if a in r]
    if not m or not p or st.mean(m) < 50: continue
    mn = [r[a]/r[CONTROL] for r in runs["on"] if a in r]; pn = [r[a]/r[CONTROL] for r in runs["off"] if a in r]
    sd = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0
    print(f"{a:48s} {st.mean(m):10.1f} {st.mean(p):10.1f} {100*(st.mean(p)/st.mean(m)-1):+6.1f}% {100*(st.mean(pn)/st.mean(mn)-1):+6.1f}%   {sd(mn):5.1f}%/{sd(pn):4.1f}%")
for s in ("on", "off"):
    tot = [sum(v for k, v in r.items()) for r in runs[s]]
    print(f"sum of all algorithms {s}: " + ", ".join(f"{t/1000:.1f} s" for t in tot))
