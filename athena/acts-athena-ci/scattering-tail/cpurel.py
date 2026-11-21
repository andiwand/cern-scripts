import re, glob, statistics as st, json, sys
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")
CTRL = "ActsPixelClusterizationAlg"
def read(f):
    o = {}
    for l in open(f, errors="replace"):
        m = PAT.search(l.rstrip())
        if m: o[m.group(3)] = float(m.group(2))
    return o
out = {}
for base, vs, drop in (("cpu", ["t0","c5","t1","t5","w10"], set()), ("cpu2", ["t0","c4","t4","g4","c35","t35","g35","g5"], {"c2/t35"})):
    R = {v: [read(f) for f in sorted(glob.glob(f"{base}/c*/{v}/log.RAWtoALL")) if f.split('/')[-3]+'/'+v not in drop] for v in vs}
    for a in ["ActsTrackFindingAlg", "ActsLargeRadiusTrackFindingAlg", "ActsPriVxFinderAlg", "total"]:
        f = (lambda r: sum(r.values())) if a == "total" else (lambda r, a=a: r[a])
        ref = st.mean(f(r)/r[CTRL] for r in R["t0"])
        for v in vs[1:] + (["t0"] if base == "cpu" else []):
            out.setdefault(v, {})[a] = round(100*(st.mean(f(r)/r[CTRL] for r in R[v])/ref-1), 1)
            out[v]["n"] = len(R[v])
for v, d in out.items(): print(v, d)
json.dump(out, open(sys.argv[1], "w"))
