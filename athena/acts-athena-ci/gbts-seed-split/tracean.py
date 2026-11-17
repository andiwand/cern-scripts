#!/usr/bin/env python3
"""CKF trace of pixel seeds (TrackFindingAlg traceFile). Why do pure seeds find no track?
usage: tracean.py <trace.txt> [--n 5] [--attempt 0]"""
import sys, collections, statistics as st
fn = sys.argv[1]; NSP = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5
ATT = int(sys.argv[sys.argv.index("--attempt") + 1]) if "--attempt" in sys.argv else 0
def attempts():
    cur = None
    for line in open(fn):
        if not line.endswith("\n"): break   # truncated tail
        t = line.split(" ", 1)[0]
        if t == "A":
            if cur: yield cur
            f = line.split(); cur = dict(ev=int(f[1]), seed=int(f[2]), att=int(f[3]), n=int(f[4]), eta=float(f[5]), pure=f[6] == "1", uid=int(f[7]), ntr=int(f[8]), V=[], S=[])
        elif t == "V":
            f = line.split(); cur["V"].append(dict(p=int(f[1]), r=float(f[2]), z=float(f[3]), cut=float(f[4]), cutO=float(f[5]), s0=float(f[6]), s1=float(f[7]),
                                                  nc=int(f[8]), npass=int(f[9]), best=float(f[10]), bestP=f[11] == "1", pchi=float(f[12]), pr0=float(f[13]), pr1=float(f[14])))
        elif t == "S":
            p = line.rstrip("\n").split(" | "); h = p[0].split()
            st_ = [dict(type=int(x.split()[0]), r=float(x.split()[1]), z=float(x.split()[2]), chi2=float(x.split()[3]), isP=int(x.split()[4])) for x in p[1:]]
            cur["S"].append(dict(p=int(h[1]), res=int(h[2]), nm=int(h[3]), nh=int(h[4]), no=int(h[5]), states=st_))
    if cur: yield cur
def lay(r): return "pix" if r < 330 else "strip"
def holeclass(a, s):
    vs = [v for v in a["V"] if v["p"] == 1 and abs(v["r"] - s["r"]) < 0.5 and abs(v["z"] - s["z"]) < 0.5]
    if not vs: return "no measurement on surface"
    pv = [v for v in vs if v["pchi"] >= 0]
    if not pv:
        return "measurements, none of the particle"
    v = min(pv, key=lambda v: v["pchi"]); x = v["pchi"] / v["cut"]
    return "own hit, chi2 " + ("< cut (taken elsewhere?)" if x < 1 else "1-2x cut" if x < 2 else "2-5x cut" if x < 5 else "5-20x cut" if x < 20 else ">20x cut")
C = collections.Counter(); H = collections.Counter(); FH = collections.Counter(); W = collections.Counter(); NM = collections.Counter(); HR = collections.Counter()
SIG = collections.defaultdict(list)
for a in attempts():
    if a["n"] != NSP or not a["pure"] or a["att"] != ATT: continue
    ok = a["ntr"] > 0; C["seeds"] += 1; C["fail"] += not ok
    for v in a["V"]:
        if v["p"] == 1 and v["pchi"] >= 0: SIG[("fail" if not ok else "ok", lay(v["r"]))].append(v["pchi"] / v["cut"])
    if ok: continue
    drops = [s for s in a["S"] if s["p"] == 1 and s["res"] == 1]
    if not drops: C["fail without a pass-1 drop"] += 1; continue
    b = max(drops, key=lambda s: (s["nm"], -s["nh"]))
    NM[(b["nm"], b["nh"], b["no"])] += 1
    holes = [s for s in b["states"] if s["type"] == 2]
    for s in holes: H[(lay(s["r"]), holeclass(a, s))] += 1
    if holes:
        first = holes[-1]   # states are tip -> start, so the innermost hole is last
        FH[(lay(first["r"]), holeclass(a, first))] += 1; HR[round(first["r"] / 10) * 10] += 1
    wrong = [s for s in b["states"] if s["type"] == 0 and s["isP"] == 0]
    W["branch with a foreign hit" if wrong else "branch all own hits"] += 1
    if wrong: W["  foreign hit layer " + lay(wrong[-1]["r"])] += 1
print(f"{fn}: pure {NSP}-SP seeds, attempt {ATT}: {C['seeds']}, no track {C['fail']} ({100*C['fail']/max(1,C['seeds']):.1f}%), without pass-1 drop {C['fail without a pass-1 drop']}")
print("longest dropped branch (nMeas, nHoles, nOutliers):", ", ".join(f"{k}: {v}" for k, v in NM.most_common(6)))
print("holes on the longest dropped branch:")
for k, v in sorted(H.items(), key=lambda x: -x[1]): print(f"   {k[0]:5s} {k[1]:40s} {v}")
print("innermost hole of that branch:")
for k, v in sorted(FH.items(), key=lambda x: -x[1]): print(f"   {k[0]:5s} {k[1]:40s} {v}")
print("innermost hole radius [mm]:", ", ".join(f"{k}: {v}" for k, v in sorted(HR.items()) if v >= 3))
for k, v in W.items(): print(f"   {k}: {v}")
print("own-hit chi2 / cut on visited surfaces (median, 90%, frac > 1):")
for k, v in sorted(SIG.items()):
    v = sorted(v); print(f"   {k[0]:4s} {k[1]:5s} n={len(v):6d} median {st.median(v):.3f} p90 {v[int(0.9*len(v))]:.3f} >1: {100*sum(x>1 for x in v)/len(v):.1f}%")
