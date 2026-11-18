#!/usr/bin/env python3
"""Barrel (|eta| < 0.6, pT > 1 GeV, HS + PU) efficiency gap legacy vs ACTS, broken down by cause, one cause per particle.
Particles legacy finds and ACTS not: no pure 5-SP seed / seed ok but track lost / < 9 own clusters / CKF failure;
CKF failures classified by the first defect along r on the longest dropped pass-1 branch (pure 5-SP seeds preferred,
else impure or 4-SP seeds).
Each class also shows the fraction a fix variant recovers.
usage: breakdown.py <trace> <acts dir> <legacy dir> name=dir ..."""
import sys, os, pickle, collections, math
import numpy as np
trace, dA, dL = sys.argv[1:4]; VAR = [a.split("=", 1) for a in sys.argv[4:]]
sys.argv = ["deepdive.py", trace]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepdive.py")).read().split("def later(a):")[0])
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracedown.py")).read()
exec(src[src.index("HX = 48.3"):src.index("def surf_rz")])   # HX, HY, plane_point, edge

def load(d):
    _, truth = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    return {(k[0], k[1], k[2], k[3]): v[3] is not None for k, v in truth.items() if v[1] in ("0.0-0.3", "0.3-0.6")}
A, L = load(dA), load(dL); VF = [(n, load(d)) for n, d in VAR]
N = len(A)
idx = collections.defaultdict(list)
for k in A: idx[(k[0], k[1])].append(k)
def key(ev, uid, pt, eta):
    c = [k for k in idx.get((ev, uid), []) if abs(k[2] - pt) < 1. and abs(k[3] - eta) < 1e-3]
    return c[0] if c else None

def classify(a):
    drops = [s for s in a["S"] if s["p"] == 1 and s["res"] == 1]
    if not drops: return "other: no dropped branch"
    b = max(drops, key=lambda s: (s["nm"], -s["nh"])); sts = b["states"]
    rmax = max(s["r"] for s in sts)
    pix = [h for h in a["H"] if not h["strip"]]
    vis = [v for v in a["V"] if v["p"] == 1 and "geo" in v]
    side = lambda vol, lay, r: (vol, lay, round(r))
    own = collections.defaultdict(list)
    for h in a["H"]:
        if not h["strip"]: continue
        g = geo(h["geo"]); r = math.hypot(*h["c"][:2])
        own[side(g["vol"], g["lay"], r)].append(h)
    vis_s = collections.defaultdict(list)
    for v in vis:
        if v["r"] > 330: vis_s[side(v["vol"], v["lay"], v["r"])].append(v)
    st_s = collections.defaultdict(list)
    for s in sts:
        if s["r"] <= 330: continue
        vv = [v for v in vis if abs(v["r"] - s["r"]) < 0.05 and abs(v["z"] - s["z"]) < 0.05]
        s["v"] = vv[0] if vv else None
        if s["v"] is not None: st_s[side(s["v"]["vol"], s["v"]["lay"], s["r"])].append(s)
    def hedge(h, lay):
        loc0 = float(np.dot(h["g"] - h["c"], h["ex"])); pp = plane_point(pix, h)
        return edge(loc0, pp[1] if pp else 0., lay)
    sides = sorted(set(own) | set(vis_s) | set(st_s), key=lambda k: k[2])
    for S in sides:
        if S[2] > rmax + 5: break
        o = own.get(S, []); st = st_s.get(S, []); ogeo = {h["geo"] for h in o}
        vgeo = {v["geo"] for v in vis_s.get(S, [])}
        if any(s["type"] == 0 and s["isP"] == 1 for s in st): continue
        if any(s["type"] == 1 and s["isP"] == 1 for s in st): return "large kink: own hit an outlier"
        bad = [s for s in st if s["type"] in (0, 1, 2)]
        if not bad:
            if o and not (ogeo & vgeo):
                return "own hit on a module never visited: " + ("at the edge (< 0.5 mm)" if min(hedge(h, S[1]) for h in o) < 0.5 else "central")
            continue
        s = bad[0]; v = s["v"]
        e = edge(v["loc0"], v["loc1"], v["lay"]) if v["vol"] == 23 else 99.
        if v["geo"] in ogeo:
            if s["type"] == 0 and 0 <= v["pchi"] < v["cut"]: return "competing chi2: foreign hit picked, own hit in the cut"
            return "large kink: own hit on the module, outside the cut"
        if s["type"] == 2 and e < 1.: return "edge hole (< 1 mm): " + ("own hit on the neighbour" if o else "no own hit on the layer")
        if o: return "wrong neighbouring module: " + ("hole" if s["type"] == 2 else "foreign hit picked")
        return "own hit missing on the layer: " + ("hole" if s["type"] == 2 else "foreign hit picked")
    return "other: no strip defect (pixel holes, branch end)"

P = {}
for a in attempts():
    if a["att"] != 0 or a["T"] is None: continue
    T = a["T"]; k = key(a["ev"], a["uid"], T["pt"] * 1000., T["eta"])
    if k is None: continue
    p = P.setdefault(k, dict(pure=False, ok=False, ns=0, fails=[], okany=False, failany=[]))
    p["ns"] = max(p["ns"], len({h["geo"] for h in a["H"]}))
    p["okany"] |= a["ntr"] > 0
    if a["ntr"] == 0: p["failany"].append(a)
    if a["n"] != 5 or not a["pure"]: continue
    p["pure"] = True; p["ok"] |= a["ntr"] > 0
    if a["ntr"] == 0: p["fails"].append(a)
C = collections.Counter(); R = collections.Counter(); SEEDK = collections.Counter()
def add(c, k, sign):
    C[(c, sign)] += 1
    if sign > 0:
        for n, vf in VF: R[(c, n)] += bool(vf.get(k))
for k in A:
    fa, fl = A[k], L.get(k)
    if fl is None or fa == fl: continue
    sign = 1 if fl else -1
    p = P.get(k)
    if sign < 0: c = "ACTS finds, legacy does not (legacy side not diagnosed)"
    elif p is None: c = "seeding: no ACTS pixel seed of the particle (>= 4 SPs, majority)"
    elif p["okany"]: c = "after the CKF: an ACTS seed made a track, particle not found (resolver / selection / matching)"
    elif p["ns"] < 9: c = "not reconstructible: < 9 own clusters (interaction)"
    else:
        fl = p["fails"] or p["failany"]
        a = max(fl, key=lambda a: max([s["nm"] for s in a["S"] if s["p"] == 1] or [0]))
        c = "CKF: " + classify(a)
        if not p["pure"]: SEEDK[c] += 1
    add(c, k, sign)
gain = sum(v for (c, s), v in C.items() if s > 0); loss = sum(v for (c, s), v in C.items() if s < 0)
print(f"barrel |eta| < 0.6, pT > 1 GeV, HS + PU: {N} particles. legacy finds {gain} ACTS does not, ACTS {loss} legacy does not:"
      f" legacy - ACTS = {gain - loss} = {100*(gain-loss)/N:+.2f}%")
print(f"{'cause':86s} {'leg only':>8s} {'ACTS only':>9s} {'net eff':>8s}  " + "  ".join(f"{n:>10s}" for n, _ in VF))
cs = sorted({c for c, _ in C}, key=lambda c: -(C[(c, 1)] - C[(c, -1)]))
for c in cs:
    g, l = C[(c, 1)], C[(c, -1)]
    print(f"{c:86s} {g:8d} {l:9d} {100*(g-l)/N:+7.2f}%  " + "  ".join(f"{100*R[(c, n)]/max(g,1):9.0f}%" for n, _ in VF))
print(f"CKF failures classified through impure or 4-SP seeds only (included above): {sum(SEEDK.values())}")
# efficiency on the reconstructible denominator: drop particles known to leave < 9 own clusters (traced, ns < 9)
NR = {k for k in A if k in P and P[k]["ns"] < 9}
Nr = N - len(NR)
ea = sum(1 for k in A if A[k] and k not in NR) / Nr; el = sum(1 for k in A if L.get(k) and k not in NR) / Nr
print(f"reconstructible denominator (drop {len(NR)} particles with < 9 own clusters): {Nr} particles, ACTS {100*ea:.2f}%, legacy {100*el:.2f}%, gap {100*(el-ea):+.2f}%")
print(f"standard denominator: ACTS {100*sum(A.values())/N:.2f}%, legacy {100*sum(1 for k in A if L.get(k))/N:.2f}%")
