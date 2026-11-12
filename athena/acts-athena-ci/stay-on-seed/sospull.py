#!/usr/bin/env python3
"""Residuals/pulls of true seed hits (OFF selector records) and seed estimate vs fitted track (E lines).
usage: sospull.py <on/sos.txt> <off/sos.txt>"""
import sys, collections, math, statistics as st
exec(open(__file__.replace("sospull.py", "sosclean.py")).read().split("SA, TA, _ = load")[0])
def loadE(fn):
    E = {}
    for l in open(fn):
        if l[0] != 'E': continue
        a, b, c = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
        if f[4] != '1': continue
        par = [tuple(float(x) for x in e.split(':')) for e in b.split()]
        cal = [tuple(float(x) for x in e.split(':')) for e in c.split()[1:]]
        if k not in E: E[k] = (par, cal, f[5] == '1')
    return E
def loadR(fn):
    R = {}
    for l in open(fn):
        if l[0] != 'R': continue
        a, b = l.split('|'); f = a.split(); R[(int(f[1]), int(f[2]), int(f[3]))] = [tuple(float(x) for x in e.split(':')) for e in b.split()]
    return R
def width(v):   # robust sigma from the median absolute deviation
    m = st.median(v); return 1.4826 * st.median(abs(x - m) for x in v), m
def q(v, f): v = sorted(v); return v[int(f * (len(v) - 1))]
SA, TA, _ = load(sys.argv[1]); SB, TB, _ = load(sys.argv[2]); RB = loadR(sys.argv[2]); EA = loadE(sys.argv[1])
def comp(k):
    t = anyt(TA.get(k, [])) or anyt(TB.get(k, []))
    return composition(t['ms'])[0] if t else "none"
for ty, name in ((0, "pixel"), (1, "strip")):
    pure = [k for k in SB if k[1] == ty and k in SA and comp(k) == "pure"]
    onlyOn = {k for k in pure if best(TA.get(k, [])) and not best(TB.get(k, []))}
    print(f"\n======== {name}: {len(pure)} truth-pure seeds")
    # --- 1. true-hit residual decomposition at SP1/SP2 while still on track (OFF run)
    for grp, keys in (("all pure", pure), ("pure, found only with forcing", onlyOn)):
        for sp in (1, 2):
            pul = [[], []]; r = [[], []]; sv = [[], []]; sp_ = [[], []]
            for k in keys:
                recs = RB.get(k, [])
                prev_ok = all(x[2] == 0 for x in recs if 0 < int(x[0]) < sp)
                x = next((x for x in recs if int(x[0]) == sp), None)
                if x is None or (grp == "all pure" and not prev_ok): continue
                dim = int(x[6]); rr = (x[7], x[8]); V = (x[9], x[11]); P = (x[12], x[14])
                for i in range(dim):
                    if V[i] + P[i] <= 0: continue
                    pul[i].append(rr[i] / math.sqrt(V[i] + P[i])); r[i].append(rr[i] * 1000); sv[i].append(math.sqrt(V[i]) * 1000); sp_[i].append(math.sqrt(P[i]) * 1000)
            for i in range(2):
                if len(pul[i]) < 30: continue
                w, m = width(pul[i]); tail = sum(abs(x) > 3 for x in pul[i]) / len(pul[i])
                rw, rm = width(r[i])
                print(f"  {grp:30s} SP{sp} loc{i}: n={len(pul[i]):7d}  pull core width {w:.2f} (mean {m:+.2f}), |pull|>3 {tail:.3f} | residual core {rw:7.1f} um, 90%|r| {q([abs(x) for x in r[i]], .9):7.1f} um | sigma_meas {st.median(sv[i]):6.1f} um, sigma_pred median {st.median(sp_[i]):7.1f} um")
    # --- 2. seed estimate vs the fitted track at the start surface (ON run, selected tracks of pure seeds)
    names = ["loc0 [mm]", "loc1 [mm]", "phi [mrad]", "theta [mrad]", "q/p [e/GeV]"]
    scale = [1, 1, 1000, 1000, 1]
    for grp, keys in (("all pure", pure), ("pure, found only with forcing", onlyOn)):
        print(f"  estimate - fit at the start SP, {grp}:")
        ks = [k for k in keys if k in EA]
        for i in range(5):
            d = []; s = []; pl = []
            for k in ks:
                par = EA[k][0][i]; diff = par[0] - par[2]
                if i == 2: diff = (diff + math.pi) % (2 * math.pi) - math.pi
                d.append(diff * scale[i]); s.append(par[1] * scale[i]); pl.append(diff / par[1] if par[1] > 0 else 0)
            if len(d) < 30: continue
            w, m = width(d); pw, pm = width(pl)
            print(f"     {names[i]:13s} n={len(d):7d}  diff core {w:9.4f} (median {m:+.4f}), 90%|diff| {q([abs(x) for x in d], .9):9.4f}, 99% {q([abs(x) for x in d], .99):9.4f} | sigma_est {st.median(s):8.4f} -> pull core {pw:.3f}, |pull|>1 {sum(abs(x) > 1 for x in pl)/len(pl):.3f}")
    # relative q/p and relative pT error of the estimate
    ks = [k for k in pure if k in EA]
    rel = [(EA[k][0][4][0] - EA[k][0][4][2]) / EA[k][0][4][2] for k in ks if EA[k][0][4][2] != 0]
    w, m = width(rel)
    print(f"  q/p estimate relative to fit: core {w:.3f} (median {m:+.3f}), 90%|rel| {q([abs(x) for x in rel], .9):.3f}, 99% {q([abs(x) for x in rel], .99):.3f}")
    # calibrated vs selection measurement covariance (OFF run: same track has both)
