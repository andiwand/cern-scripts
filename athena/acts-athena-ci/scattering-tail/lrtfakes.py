#!/usr/bin/env python3
"""LRT (InDetLargeD0TrackParticles) and primary track counts and fakes per variant, binned in |eta|, pT and |d0|.
fake = truthMatchProbability < 0.5 (no link counts as fake). usage: lrtfakes.py out.json <variant>=<aod>[,<aod>...] ...
Prints a table; writes per-bin counts for charts."""
import sys, json, math
ETA = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
PT = [0, 1, 1.5, 2, 3, 5, 10, 1e9]
D0 = [0, 2, 5, 10, 20, 50, 100, 300]
def b(E, x):
    for k in range(len(E) - 1):
        if E[k] <= x < E[k + 1]: return k
    return None
def prob(tp):
    return tp.auxdataConst['float']('truthMatchProbability') if tp.isAvailable['float']('truthMatchProbability') else -1.0
def scan(f):
    """Counts for one AOD file (runs in a worker process)."""
    import ROOT
    ROOT.xAOD.Init().ignore()
    ch = ROOT.TChain("CollectionTree"); ch.Add(f)
    t = ROOT.xAOD.MakeTransientTree(ch)
    R = {c: {ax: [[0, 0] for _ in range(len(E) - 1)] for ax, E in (("eta", ETA), ("pt", PT), ("d0", D0))} for c in ("lrt", "prim")}
    nev = t.GetEntries()
    for i in range(nev):
        t.GetEntry(i)
        for c, coll in (("lrt", t.InDetLargeD0TrackParticles), ("prim", t.InDetTrackParticles)):
            for tp in coll:
                fake = prob(tp) < 0.5
                for ax, E, x in (("eta", ETA, abs(tp.eta())), ("pt", PT, tp.pt() / 1000), ("d0", D0, abs(tp.d0()))):
                    k = b(E, x)
                    if k is None: continue
                    R[c][ax][k][0] += 1; R[c][ax][k][1] += fake
    return nev, R
if __name__ == "__main__":
    import multiprocessing as mp, os
    jobs = [(a.split("=", 1)[0], f) for a in sys.argv[2:] for f in a.split("=", 1)[1].split(",")]
    with mp.get_context("spawn").Pool(int(os.environ.get("NPROC", "16"))) as pool:
        res = pool.map(scan, [f for _, f in jobs])
    out = {}
    for (v, _), (nev, R) in zip(jobs, res):
        o = out.setdefault(v, dict(nev=0, R=None))
        o["nev"] += nev
        if o["R"] is None: o["R"] = R
        else:
            for c in R:
                for ax in R[c]:
                    for k, (n, fk) in enumerate(R[c][ax]): o["R"][c][ax][k][0] += n; o["R"][c][ax][k][1] += fk
    for v, o in out.items():
        for c in ("lrt", "prim"):
            n = sum(x[0] for x in o["R"][c]["eta"]); f = sum(x[1] for x in o["R"][c]["eta"])
            print(f"{v:5s} {c:5s} events {o['nev']} tracks {n:9d} ({n/o['nev']:8.1f}/ev) fakes {f:7d} = {100*f/max(n,1):.3f}%")
    json.dump(dict(edges=dict(eta=ETA, pt=PT[:-1] + [1000], d0=D0), data=out), open(sys.argv[1], "w"))
    vs = list(out)
    for c in ("lrt",):
        for ax, E in (("eta", ETA), ("pt", PT), ("d0", D0)):
            print(f"\n{c} fake rate vs {ax}")
            for k in range(len(E) - 1):
                row = f"  {E[k]:g}-{E[k+1]:g}".ljust(14)
                for v in vs:
                    n, f = out[v]["R"][c][ax][k]
                    row += f"{v}: {n:8d} {100*f/n if n else 0:7.3f}%  "
                print(row)
