#!/usr/bin/env python3
"""Tune the seed-end trimming offline on the dump (Q: truth per SP, X: positions).
Maps of P(wrong end SP) per seed type in r-|z| bins from odd events; rules evaluated on even events, as in the C++ code.
usage: trimtune.py <sos.txt> <maps.json>"""
import sys, json, collections, math
import numpy as np
from scipy.linalg import eig
RE = [0, 60, 120, 200, 350, 500, 700, 1100]; ZE = [0, 500, 1000, 1500, 2000, 2500, 3000, 3600]
def b(e, v): return min(max(np.searchsorted(e, v, side="right") - 1, 0), len(e) - 2)
seeds = {}
for l in open(sys.argv[1]):
    if l[0] == 'Q':
        a, rest = l.split('|'); f = a.split()
        lab = []
        for sp in rest.split():
            u = set(int(x) for x in sp.split(',')); lab.append(next(iter(u)) if len(u) == 1 else -2)
        seeds[(int(f[1]), int(f[2]), int(f[3]))] = [lab, None]
    elif l[0] == 'X':
        a, rest = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
        if k in seeds: seeds[k][1] = np.array([[float(x) for x in p.split(',')] for p in rest.split()])
# truth of each seed: wrong flags for matched/duplicate seeds, None for fakes
def wrongflags(lab):
    c = collections.Counter(x for x in lab if x >= 0)
    if not c: return None
    m, n = c.most_common(1)[0]
    if n < 3 or 2 * n < len(lab): return None
    return [x != m for x in lab]
S = {0: [], 1: []}
for (ev, ty, i), (lab, pos) in seeds.items():
    if pos is None or len(lab) != len(pos): continue
    S[ty].append((ev, wrongflags(lab), pos))
def rz(p): return math.hypot(p[0], p[1]), abs(p[2])
# ---- maps from odd events
maps = {}
for ty, name in ((0, "pixel"), (1, "strip")):
    W = {e: np.zeros((len(RE) - 1, len(ZE) - 1)) for e in ("first", "last")}; N = {e: np.zeros_like(W[e]) for e in W}
    for ev, w, pos in S[ty]:
        if w is None or ev % 2 == 0: continue
        for e, i in (("first", 0), ("last", -1)):
            r, z = rz(pos[i]); N[e][b(RE, r), b(ZE, z)] += 1; W[e][b(RE, r), b(ZE, z)] += w[i]
    maps[name] = {e: np.where(N[e] >= 50, W[e] / np.maximum(N[e], 1), 0.).round(4).ravel().tolist() for e in W}
    maps[name]["n"] = {e: N[e].ravel().astype(int).tolist() for e in N}
json.dump(dict(rEdges=RE, zEdges=ZE, maps=maps), open(sys.argv[2], "w"), indent=1)
for name in maps:
    for e in ("first", "last"):
        M = np.array(maps[name][e]).reshape(len(RE) - 1, len(ZE) - 1); Nn = np.array(maps[name]["n"][e]).reshape(M.shape)
        print(f"\n{name} {e} SP: P(wrong) [%] (rows r {RE}, cols |z| {ZE}); '.' = fewer than 50 seeds")
        for ir in range(M.shape[0]):
            print(f"  r {RE[ir]:4d}-{RE[ir+1]:<5d}" + "".join(f"{100*M[ir,iz]:7.1f}" if Nn[ir, iz] >= 50 else "      ." for iz in range(M.shape[1])))
# ---- residual: leave-one-out scores as in the C++ code
def taubin(P):
    x, y = P[:, 0], P[:, 1]; mx, my = x.mean(), y.mean(); x = x - mx; y = y - my; z = x * x + y * y
    mxx, myy, mxy, mxz, myz, mzz, mz = (x*x).mean(), (y*y).mean(), (x*y).mean(), (x*z).mean(), (y*z).mean(), (z*z).mean(), z.mean()
    if mz <= 0: return None
    M = np.array([[mzz - mz * mz, mxz, myz], [mxz, mxx, mxy], [myz, mxy, myy]]); Nm = np.diag([4 * mz, 1., 1.])
    vals, vecs = eig(M, Nm); vals = vals.real; a = vecs[:, np.argmin(np.where(vals >= -1e-12, vals, np.inf))].real
    A, B, C = a; 
    if A == 0: return None
    D = -A * mz; r2 = (B * B + C * C - 4 * A * D) / (4 * A * A)
    if not np.isfinite(r2) or r2 <= 0: return None
    return np.array([-B / (2 * A) + mx, -C / (2 * A) + my]), math.sqrt(r2)
def loo(others, p):
    c = taubin(others); dxy = abs(np.hypot(*(p[:2] - c[0])) - c[1]) if c else 0.
    r = np.hypot(others[:, 0], others[:, 1]); zz = others[:, 2]
    zab = (zz.max() - zz.min()) > (r.max() - r.min())
    X, Y = (zz, r) if zab else (r, zz); px, py = (p[2], math.hypot(p[0], p[1])) if zab else (math.hypot(p[0], p[1]), p[2])
    A = np.vstack([np.ones_like(X), X]).T; coef = np.linalg.lstsq(A, Y, rcond=None)[0]
    return dxy, abs(py - (coef[0] + coef[1] * px))
R = {0: [], 1: []}
for ty in (0, 1):
    for ev, w, pos in S[ty]:
        if ev % 2 == 1 or len(pos) < 5: continue
        R[ty].append((w, loo(pos[1:], pos[0]), loo(pos[:-1], pos[-1])))
for ty, name in ((0, "pixel"), (1, "strip")):
    print(f"\n{name}, seeds with >= 5 SPs (even events): leave-one-out residuals of the end SPs, quantiles [mm]")
    for e, j, idx in (("first", 1, 0), ("last", 2, -1)):
        for lab, sel in (("right", False), ("wrong", True)):
            v = [x[j] for x in R[ty] if x[0] is not None and x[0][idx] == sel]
            if len(v) < 20: continue
            a = np.array(v)
            print(f"  {e:5s} {lab:5s} n={len(a):7d}  xy 50/90/99%: " + " ".join(f"{q:.3f}" for q in np.quantile(a[:, 0], [.5, .9, .99])) +
                  "   rz 50/90/99%: " + " ".join(f"{q:.3f}" for q in np.quantile(a[:, 1], [.5, .9, .99])))
np.save(sys.argv[2].replace(".json", "_loo.npy"), np.array([(ty, *(x[0][0] if x[0] else -1, x[0][-1] if x[0] else -1), *x[1], *x[2], x[0] is not None and not any(x[0][1:-1]))
                                                          for ty in (0, 1) for x in R[ty]], dtype=float))
