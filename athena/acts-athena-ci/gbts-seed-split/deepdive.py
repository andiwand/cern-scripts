#!/usr/bin/env python3
"""Pixel -> strip extrapolation of pure 5-SP GBTS seeds at |eta| < 0.6 (extended CKF trace with T/H lines).
Questions: truth (interactions, electrons), seed parameters vs truth, predicted state at the first strip surface vs truth,
the physical pixel->strip kink from a helix through the particle's own pixel clusters, and whether the own strip
cluster sat on a surface the CKF never visited (overlaps).
usage: deepdive.py <trace.txt> [--n 5]"""
import sys, math, collections
import numpy as np

fn = sys.argv[1]; NSP = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5
BZ = 2.0  # T, ITk solenoid; only used for the truth phi at a radius
RINT = float(sys.argv[sys.argv.index("--rint") + 1]) if "--rint" in sys.argv else 420.

def geo(v):
    return dict(vol=v >> 56, lay=(v >> 36) & 0xfff, sens=(v >> 8) & 0xfffff)

def attempts():
    cur = None
    for line in open(fn):
        if not line.endswith("\n"): break
        t = line[0]
        f = line.split()
        if t == "A":
            if cur: yield cur
            cur = dict(ev=int(f[1]), seed=int(f[2]), att=int(f[3]), n=int(f[4]), eta=float(f[5]), pure=f[6] == "1",
                       uid=int(f[7]), ntr=int(f[8]), T=None, E=None, H=[], K=[], V=[], S=[])
        elif t == "T":
            x = list(map(float, f[1:]))
            cur["T"] = dict(pdg=int(x[0]), q=x[1], pt=x[2] / 1000., eta=x[3], phi=x[4], vx=x[5], vy=x[6], vz=x[7], endR=x[8],
                            qop=x[9], theta=x[10], phiS=x[11], sqop=x[12], stheta=x[13], sphi=x[14], rS=x[15])
        elif t == "E":
            x = f[3:]
            cur["E"] = dict(r=float(f[1]), z=float(f[2]),
                            kids=[(int(x[i]), float(x[i + 1]) / 1000., int(x[i + 2])) for i in range(0, len(x) - 2, 3)])
        elif t in "HK":
            x = list(map(float, f[3:]))
            cur[t].append(dict(strip=f[1] == "1", geo=int(f[2]), g=np.array(x[0:3]), c=np.array(x[3:6]),
                                 ex=np.array(x[6:9]), ey=np.array(x[9:12])))
        elif t == "V":
            v = dict(p=int(f[1]), r=float(f[2]), z=float(f[3]), cut=float(f[4]), s0=float(f[6]), nc=int(f[8]), npass=int(f[9]),
                     best=float(f[10]), bestP=f[11] == "1", pchi=float(f[12]), pr0=float(f[13]), vol=int(f[15]), lay=int(f[16]))
            if len(f) > 17:
                v.update(geo=int(f[17]), loc0=float(f[18]), loc1=float(f[19]), phi=float(f[20]), theta=float(f[21]),
                         qop=float(f[22]), sphi=float(f[23]), stheta=float(f[24]), sqop=float(f[25]))
            if len(f) > 26: v["bestUid"] = int(f[26])
            cur["V"].append(v)
        elif t == "S":
            pp = line.rstrip("\n").split(" | "); h = pp[0].split()
            sts = [dict(type=int(x.split()[0]), r=float(x.split()[1]), z=float(x.split()[2]), isP=int(x.split()[4])) for x in pp[1:]]
            cur["S"].append(dict(p=int(h[1]), res=int(h[2]), nm=int(h[3]), nh=int(h[4]), states=sts))
    if cur: yield cur

def truth_phi(T, r):
    """phi of the truth momentum at radius r for a particle from (vx, vy); sign of the bend fixed by the charge"""
    R = T["pt"] / (0.3 * BZ) * 1000.  # mm
    return T["phi"] - T["q"] * math.asin(min(1., r / (2 * R)))

def dphi(a, b): return (a - b + math.pi) % (2 * math.pi) - math.pi

def circle_fit(xy):
    x, y = xy[:, 0], xy[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    sol, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    xc, yc = sol[0], sol[1]; R = math.sqrt(sol[2] + xc * xc + yc * yc)
    return xc, yc, R

def helix_on_plane(pix, h):
    """Helix through the own pixel clusters (circle in xy, z linear in r), intersected with the plane of cluster h.
    Returns the predicted loc0 - hit loc0 [mm], or None."""
    if len(pix) < 3: return None
    P = np.array([p["g"] for p in pix])
    xc, yc, R = circle_fit(P[:, :2])
    r = np.hypot(P[:, 0], P[:, 1])
    kz = np.polyfit(r, P[:, 2], 1)
    n = np.cross(h["ex"], h["ey"])
    # walk along the circle on the side of the outermost pixel cluster, from it outwards
    o = P[np.argmax(r)]
    a0 = math.atan2(o[1] - yc, o[0] - xc)
    # direction of travel: increasing radius
    def pt(a):
        x = xc + R * math.cos(a); y = yc + R * math.sin(a)
        return np.array([x, y, np.polyval(kz, math.hypot(x, y))])
    s = 1 if math.hypot(*pt(a0 + 1e-3)[:2]) > math.hypot(*pt(a0)[:2]) else -1
    f = lambda a: float(np.dot(pt(a) - h["c"], n))
    a, step = a0, s * 2. / R  # 2 mm steps
    fa = f(a)
    for _ in range(2000):
        b = a + step; fb = f(b)
        if fa * fb <= 0:
            for _ in range(40):
                m = 0.5 * (a + b); fm = f(m)
                if fa * fm <= 0: b, fb = m, fm
                else: a, fa = m, fm
            X = pt(0.5 * (a + b))
            return float(np.dot(X - h["c"], h["ex"])) - float(np.dot(h["g"] - h["c"], h["ex"]))
        a, fa = b, fb
    return None

def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else float("nan")
def summ(name, v):
    if not v: print(f"   {name:46s} n=0"); return
    a = np.array(v); med = np.median(a); mad = 1.4826 * np.median(np.abs(a - med))
    print(f"   {name:46s} n={len(a):6d} median {med:+8.3f} width(MAD) {mad:7.3f} rms {a.std():8.3f}"
          f" |x|>3: {100*np.mean(np.abs(a)>3):5.1f}%  |x|>5: {100*np.mean(np.abs(a)>5):5.1f}%")
def absq(name, v):
    if not v: return
    a = np.abs(np.array(v))
    print(f"   {name:46s} n={len(a):6d} median {np.median(a):8.3f} p90 {q(a,0.9):8.3f} p99 {q(a,0.99):8.3f}")

def later(a):
    drops = [x for x in a["S"] if x["p"] == 1 and x["res"] == 1]
    if not drops: return "no pass-1 drop"
    b = max(drops, key=lambda x: (x["nm"], -x["nh"]))
    vis = lambda st: [v for v in a["V"] if v["p"] == 1 and abs(v["r"] - st["r"]) < 0.5 and abs(v["z"] - st["z"]) < 0.5]
    for st in reversed(b["states"]):
        if st["r"] < 330: continue
        if st["type"] == 0 and st["isP"] == 0:
            own = [v["pchi"] / v["cut"] for v in vis(st) if v["pchi"] >= 0]
            return "foreign hit taken, own hit " + ("in the cut" if own and min(own) < 1 else "outside the cut" if own else "not on that surface")
        if st["type"] == 2:
            own = [v["pchi"] / v["cut"] for v in vis(st) if v["pchi"] >= 0]
            if own: return "hole, own hit outside the cut"
            holes = [h for h in reversed(b["states"]) if h["type"] == 2]
            if len(holes) >= 2 and abs(holes[1]["r"] - holes[0]["r"]) < 12 and st is holes[0]: return "double-sided module missed (2 holes)"
            return "hole, no own hit there"
    return "other"
LT = collections.Counter(); EL = collections.Counter(); EV = collections.Counter(); ELSE = collections.Counter()
cls = lambda a: "ok" if a["ntr"] > 0 else "fail"
SV = collections.Counter(); ER = collections.Counter(); ER2 = collections.Counter(); FC = collections.Counter(); KT = collections.defaultdict(list)
C = collections.Counter(); P = collections.defaultdict(list); OV = collections.Counter(); TR = collections.Counter()
for a in attempts():
    if a["n"] != NSP or not a["pure"] or a["att"] != 0 or a["T"] is None: continue
    k = cls(a); T = a["T"]; C[k] += 1
    if T["pt"] <= 0: continue
    # truth
    strips = [h for h in a["H"] if h["strip"]]; pix = [h for h in a["H"] if not h["strip"]]
    TR[(k, "electron")] += abs(T["pdg"]) == 11
    TR[(k, "end vertex r < 400 mm")] += 0 < T["endR"] < 400
    TR[(k, "no own strip cluster")] += not strips
    TR[(k, "pT < 1.5 GeV")] += T["pt"] < 1.5
    # seed parameters vs truth
    th = 2 * math.atan(math.exp(-T["eta"])); p = T["pt"] * math.cosh(T["eta"]); qopT = T["q"] / p
    P[(k, "seed  q/p pull")].append((T["qop"] - qopT) / T["sqop"])
    P[(k, "seed  theta pull")].append((T["theta"] - th) / T["stheta"])
    # first strip visit of pass 1
    sv = [v for v in a["V"] if v["p"] == 1 and v["r"] > 330 and "geo" in v]
    if not sv: continue
    v = sv[0]
    P[(k, "strip1 q/p pull")].append((v["qop"] - qopT) / v["sqop"])
    P[(k, "strip1 theta pull")].append((v["theta"] - th) / v["stheta"])
    P[(k, "strip1 sigma loc0 [mm]")].append(v["s0"])
    if v["pchi"] >= 0:
        P[(k, "strip1 own-hit residual / sigma")].append(v["pr0"] / v["s0"])
    # pixel -> strip kink of the particle itself and the CKF prediction vs that helix
    sid = {h["geo"]: h for h in strips}
    hv = sid.get(v["geo"])
    if hv is not None:
        d = helix_on_plane(pix, hv)
        if d is not None:
            P[(k, "strip1 helix(own pix) - own hit [mm]")].append(d)
            P[(k, "strip1 helix(own pix) - own hit / CKF sigma")].append(d / v["s0"])
            if v["pchi"] >= 0:
                # CKF prediction - helix prediction = -(own residual) - (hit - helix) ... in loc0
                P[(k, "strip1 CKF pred - helix pred / CKF sigma")].append((-v["pr0"] - d) / v["s0"])
                # frame check: measurement loc0 (CKF) vs (global - centre) . ex of the cluster
                P[(k, "check meas loc0 - (G-C).ex [mm]")].append(v["loc0"] + v["pr0"] - float(np.dot(hv["g"] - hv["c"], hv["ex"])))
    interacted = 0 < T["endR"] < RINT
    if k == "fail": ER[min(int(T["endR"] // 50) * 50, 1000) if T["endR"] > 0 else -1] += 1
    kink = None
    if hv is not None:
        d = helix_on_plane(pix, hv)
        if d is not None: kink = d / v["s0"]
    if not interacted and kink is not None:
        KT[(k, T["pt"] < 1.5)].append(kink)
    if k == "fail":
        own_vis = [w for w in sv if w["pchi"] >= 0]
        if interacted: FC[f"particle ends before r = {RINT:.0f} mm (interaction / decay)"] += 1
        elif not strips: FC["no strip cluster at all, no end vertex"] += 1
        elif hv is None and not any(h["geo"] in {w["geo"] for w in sv} for h in strips):
            FC["own strip clusters only on surfaces never visited"] += 1
        elif kink is not None and abs(kink) > 5: FC["kink pixel -> first strip > 5 sigma"] += 1
        elif kink is not None and abs(kink) > 3: FC["kink pixel -> first strip 3-5 sigma"] += 1
        elif hv is None:
            FC["first strip surface visited has no own cluster (own cluster elsewhere)"] += 1
            sameL = [h for h in strips if (geo(h["geo"])["vol"], geo(h["geo"])["lay"]) == (v["vol"], v["lay"])]
            ELSE["own cluster on the same layer, other module (visited later)" if any(h["geo"] in {w["geo"] for w in sv} for h in sameL)
                 else "own cluster on the same layer, module never visited" if sameL else "no own cluster on that layer, later layers only"] += 1
        else:
            FC["first strip own hit within 3 sigma: dies later"] += 1; LT[later(a)] += 1
    # end vertex before 600 mm: does the particle survive under a new id?
    E = a["E"]
    if E is not None and 0 < E["r"] < 600:
        same = [c for c in E["kids"] if c[0] == T["pdg"] and c[1] > 0.5 * T["pt"]]
        charged_lead = max([c for c in E["kids"]], key=lambda c: c[1], default=None)
        kind = ("survives (same pdg, > 50% pT)" if same else
                "leading child < 50% pT" if E["kids"] else "no children stored")
        EL[(k, kind)] += 1
        if same and a["K"]:
            kst = sorted([h for h in a["K"] if h["strip"]], key=lambda h: np.hypot(*h["g"][:2]))
            vis = {w["geo"]: w for w in sv}
            if not kst: SV[(k, "continuation has no strip cluster")] += 1
            else:
                h0 = kst[0]; w = vis.get(h0["geo"])
                d = helix_on_plane(pix, h0)
                sig = w["s0"] if w else v["s0"]
                if d is None: SV[(k, "continuation: no helix")] += 1
                else:
                    x = abs(d) / sig
                    SV[(k, "continuation 1st strip hit " + ("< 3" if x < 3 else "3-7" if x < 7 else "7-30" if x < 30 else "> 30")
                        + " sigma from the pixel helix" + ("" if w else ", surface not visited"))] += 1
        elif same: SV[(k, "continuation has no cluster at all")] += 1
        if k == "fail" and same:
            kid = {c[2] for c in same}
            took = any(w.get("bestUid") in kid for w in sv)
            EV["continuation is the best candidate on a visited strip surface" if took else "continuation never the best candidate"] += 1
    if E is not None and E["r"] > 0: ER2[(k, int(E["r"] // 10) * 10)] += 1
    # overlaps: first strip layer the CKF visits, does the particle have a cluster there and was its surface visited?
    L = (v["vol"], v["lay"])
    own_L = [h for h in strips if (geo(h["geo"])["vol"], geo(h["geo"])["lay"]) == L]
    vis_L = {w["geo"] for w in sv if (w["vol"], w["lay"]) == L}
    if not own_L: OV[(k, "no own cluster on that layer")] += 1
    elif all(h["geo"] in vis_L for h in own_L): OV[(k, "own surface(s) visited")] += 1
    elif any(h["geo"] in vis_L for h in own_L): OV[(k, "some own surfaces not visited")] += 1
    else: OV[(k, "own cluster on a surface never visited")] += 1
    OV[(k, f"own clusters on layer: {min(len(own_L),4)}")] += 1

print(f"{fn}: pure {NSP}-SP seeds, attempt 0: ok {C['ok']}, fail {C['fail']}")
print("truth:")
for k in ["electron", "end vertex r < 400 mm", "no own strip cluster", "pT < 1.5 GeV"]:
    print(f"   {k:30s} ok {100*TR[('ok',k)]/max(1,C['ok']):5.1f}%   fail {100*TR[('fail',k)]/max(1,C['fail']):5.1f}%")
print("pulls (ideal: median 0, width 1):")
names = sorted({n for _, n in P})
for n in names:
    for k in ("ok", "fail"):
        if "sigma loc0" in n: absq(f"{k:4s} {n}", P[(k, n)])
        elif "[mm]" in n: absq(f"{k:4s} {n}", P[(k, n)])
        else: summ(f"{k:4s} {n}", P[(k, n)])
print("first strip layer visited: own clusters vs visited surfaces:")
for k in ("ok", "fail"):
    tot = sum(v for (kk, n), v in OV.items() if kk == k and not n.startswith("own clusters on"))
    for (kk, n), v in sorted(OV.items()):
        if kk == k: print(f"   {k:4s} {n:42s} {v:6d} {100*v/max(1,tot):5.1f}%")
print("failures by cause (first match wins):")
tot = sum(FC.values())
for n, v in FC.most_common(): print(f"   {n:70s} {v:5d} {100*v/tot:5.1f}%")
print("failures: end vertex radius [mm] (-1 = none):", ", ".join(f"{k}: {v}" for k, v in sorted(ER.items())))
print("kink pixel -> first strip own hit / CKF sigma, particles without end vertex before 420 mm:")
for (k, lo), v in sorted(KT.items()):
    a = np.abs(np.array(v)); print(f"   {k:4s} pT {'< 1.5' if lo else '>=1.5'} GeV n={len(a):6d} >3: {100*np.mean(a>3):5.2f}%  >5: {100*np.mean(a>5):5.2f}%  >7: {100*np.mean(a>7):5.2f}%")
allk = np.abs(np.array([x for v in KT.values() for x in v]))
print(f"   all seeds: n={len(allk)} >3: {100*np.mean(allk>3):.2f}% (Gauss 0.27%) >5: {100*np.mean(allk>5):.2f}% >7: {100*np.mean(allk>7):.2f}%")
print("'own cluster elsewhere' failures:")
for n, v in ELSE.most_common(): print(f"   {n:70s} {v:5d}")
print("'dies later' failures (first problem on the longest dropped branch outside the pixels):")
for n, v in LT.most_common(): print(f"   {n:70s} {v:5d}")
print("particles with an end vertex before 600 mm:")
for (k, n), v in sorted(EL.items()): print(f"   {k:4s} {n:40s} {v:5d}")
for n, v in EV.most_common(): print(f"   fail, survivor: {n:60s} {v:5d}")
print("end vertex radius of all traced particles, 10 mm bins, 200-600 mm (ok+fail):")
print("   " + ", ".join(f"{r}: {ER2[('ok', r)] + ER2[('fail', r)]}" for r in range(200, 600, 10)))
print("surviving continuations (end vertex < 600 mm):")
for (k, n), v in sorted(SV.items()): print(f"   {k:4s} {n:70s} {v:5d}")
