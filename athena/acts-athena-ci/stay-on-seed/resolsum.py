#!/usr/bin/env python3
"""Resolution summary per variant vs main from resolextract.py arrays.
Bins |eta| x pT. Core: robust sigma (1.4826 MAD) per bin, ratio to main, averaged with main's bin counts.
Tail: fraction beyond 3 sigma_main(bin) from main's median. Wrong-hit tracks: truth-match probability < 1.
usage: resolsum.py <dir> <out.json> name..."""
import sys, json
import numpy as np
D = sys.argv[1]; names = sys.argv[3:]
EB = [0, 1.5, 2.5, 4.0]; PB = [1, 2, 5, 20, 1e9]; V = ["d0", "z0", "phi", "theta", "qpt"]
FINE = [i * 0.5 for i in range(9)]
def sig(x): m = np.median(x); return 1.4826 * np.median(np.abs(x - m)), m
ref = np.load(f"{D}/main.npy")
def bins(a, eb):
    ae = np.abs(a[:, 0]); ie = np.digitize(ae, eb) - 1; ip = np.digitize(a[:, 1], PB) - 1
    return ie, ip
R = {}
ie0, ip0 = bins(ref, EB); F0e, F0p = bins(ref, FINE)
refpar = {}
for j, v in enumerate(V):
    for e in range(len(EB) - 1):
        for p in range(len(PB) - 1):
            s = (ie0 == e) & (ip0 == p)
            if s.sum() > 50: refpar[(v, e, p)] = (*sig(ref[s, 3 + j]), s.sum())
    for e in range(len(FINE) - 1):
        for p in range(len(PB) - 1):
            s = (F0e == e) & (F0p == p)
            if s.sum() > 50: refpar[(v, "f", e, p)] = sig(ref[s, 3 + j])
out = {}
for n in names:
    a = np.load(f"{D}/{n}.npy"); ie, ip = bins(a, EB); fe, fp = bins(a, FINE)
    res = {"n": int(len(a)), "wrong": float(np.mean(a[:, 2] < 0.999))}
    for j, v in enumerate(V):
        num = den = 0.; tail = 0; ntot = 0
        for (vv, e, p), (s0, m0, n0) in [(k, x) for k, x in refpar.items() if k[0] == v and k[1] != "f"]:
            s = (ie == e) & (ip == p)
            if s.sum() < 50: continue
            sv, _ = sig(a[s, 3 + j]); num += n0 * sv / s0; den += n0
            tail += np.sum(np.abs(a[s, 3 + j] - m0) > 3 * s0); ntot += s.sum()
        res[v] = {"core": float(num / den - 1), "tail": float(tail / ntot)}
        # tail vs |eta| (fine bins, all pT)
        te = []
        for e in range(len(FINE) - 1):
            t_ = c_ = 0
            for p in range(len(PB) - 1):
                k = (v, "f", e, p)
                if k not in refpar: continue
                s = (fe == e) & (fp == p); s0, m0 = refpar[k][0], refpar[k][1]
                t_ += np.sum(np.abs(a[s, 3 + j] - m0) > 3 * s0); c_ += s.sum()
            te.append(float(t_ / c_) if c_ else None)
        res[v]["tailEta"] = te
    out[n] = res
    print(f"{n:22s} wrong {100*res['wrong']:5.2f}%  " + "  ".join(f"{v} {100*res[v]['core']:+5.2f}%/{100*res[v]['tail']:.2f}%" for v in V))
json.dump(dict(etaEdges=FINE, vars=V, res=out), open(sys.argv[2], "w"), indent=1)
