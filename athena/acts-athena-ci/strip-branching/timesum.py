#!/usr/bin/env python3
"""Per-algorithm CPU for cycle.sh runs, normalised to ActsPixelClusterizationAlg. usage: timesum2.py <dir> <ref> <variant>..."""
import re, glob, sys, statistics as st
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")
CTRL = "ActsPixelClusterizationAlg"
base, vs = sys.argv[1], sys.argv[2:]
def read(f):
    o = {}
    for l in open(f, errors="replace"):
        m = PAT.search(l.rstrip())
        if m: o[m.group(3)] = float(m.group(2))
    return o
R = {v: [read(f) for f in sorted(glob.glob(f"{base}/c*/{v}/log.RAWtoALL"))] for v in vs}
print("cycles:", {v: len(r) for v, r in R.items()})
algs = ["ActsTrackFindingAlg", "ActsLargeRadiusTrackFindingAlg", "ActsHGTDTrackExtensionAlg", "ActsPriVxFinderAlg", "ActsPixelSeedingAlg", CTRL]
print(f"{'algorithm':34s}" + "".join(f"{v:>26s}" for v in vs))
for a in algs:
    row = f"{a:34s}"; ref = st.mean(r[a] / r[CTRL] for r in R[vs[0]])
    for v in vs:
        x = [r[a] / r[CTRL] for r in R[v]]; ms = st.mean(r[a] for r in R[v])
        row += f"{ms:10.0f} ms {100*(st.mean(x)/ref-1):+6.1f}% sd{100*st.stdev(x)/st.mean(x) if len(x)>1 else 0:4.1f}"
    print(row)
for v in vs: print(f"total {v}: " + ", ".join(f"{sum(r.values())/1000:.1f}" for r in R[v]) + " s")
