#!/usr/bin/env python3
"""Simulate the trimming rules on even events (matched + duplicate seeds): wrong vs right end SPs dropped.
Map rule as in the C++ code; residual rule uses the first-pass leave-one-out scores for both ends.
usage: trimsim.py <sos.txt> <maps.json>"""
import sys, json, collections, math
import numpy as np
exec(open(sys.argv[0].replace("trimsim.py", "trimtune.py")).read().split("# ---- maps from odd events")[0].replace("sys.argv[1]", "SOS"), {"SOS": sys.argv[1], **globals()}) if False else None
src = open(sys.argv[0].replace("trimsim.py", "trimtune.py")).read()
g = {"__name__": "x"}; exec(src.split("# ---- maps from odd events")[0].replace("open(sys.argv[1])", f"open({sys.argv[1]!r})"), g)
exec(src[src.index("def taubin"):src.index("R = {0: [], 1: []}")], g)
S, RE, ZE, b, rz, loo = g["S"], g["RE"], g["ZE"], g["b"], g["rz"], g["loo"]
M = json.load(open(sys.argv[2]))["maps"]
def mapv(name, end, p):
    r, z = rz(p); return M[name][end][b(RE, r) * (len(ZE) - 1) + b(ZE, z)]
def trim(n, sf0, sl0, minKeep=3):
    i0, i1 = 0, n - 1; df = dl = False
    for _ in range(2):
        if i1 + 1 - i0 <= minKeep: break
        sf = -1 if df else sf0; sl = -1 if dl else sl0
        if max(sf, sl) <= 1: break
        if sl >= sf: i1 -= 1; dl = True
        else: i0 += 1; df = True
    return i0, i1
for ty, name in ((0, "pixel"), (1, "strip")):
    data = []
    for ev, w, pos in S[ty]:
        if ev % 2 == 1 or w is None: continue
        n = len(pos); lo = (loo(pos[1:], pos[0]), loo(pos[:-1], pos[-1])) if n >= 5 else None
        data.append((w, n, mapv(name, "first", pos[0]), mapv(name, "last", pos[-1]), lo))
    nw = sum(w[0] + w[-1] for w, *_ in data); nr = sum(2 - w[0] - w[-1] for w, *_ in data); nimp = sum(any(w) for w, *_ in data)
    print(f"\n### {name}: {len(data)} matched+duplicate seeds (even events), wrong end SPs {nw}, right end SPs {nr}, impure seeds {nimp}")
    print(f"{'rule':38s} {'wrong ends dropped':>19s} {'right ends dropped':>19s} {'impure -> clean':>16s} {'seeds trimmed':>14s}")
    def ev_rule(lab, f):
        dw = dr = clean = tr = 0
        for w, n, pf, pl, lo in data:
            sc = f(n, pf, pl, lo)
            if sc is None: i0, i1 = 0, n - 1
            else: i0, i1 = trim(n, *sc)
            tr += (i0, i1) != (0, n - 1)
            for i in range(0, i0): dw += w[i]; dr += not w[i]
            for i in range(i1 + 1, n): dw += w[i]; dr += not w[i]
            clean += any(w) and not any(w[i0:i1 + 1])
        print(f"{lab:38s} {dw:8d} ({100*dw/nw:5.1f}%) {dr:9d} ({100*dr/nr:5.2f}%) {clean:7d} ({100*clean/nimp:4.1f}%) {100*tr/len(data):12.1f}%")
    for t in (0.03, 0.05, 0.08, 0.12):
        ev_rule(f"map, threshold {t}", lambda n, pf, pl, lo, t=t: (pf / t, pl / t))
    for cxy in (0.3, 0.5, 0.8):
        for crz in (0.5, 1.0, 1e9):
            ev_rule(f"residual xy {cxy} rz {crz if crz < 1e8 else 'off'} (>=5 SP)", lambda n, pf, pl, lo, cxy=cxy, crz=crz: None if lo is None else (max(lo[0][0] / cxy, lo[0][1] / crz), max(lo[1][0] / cxy, lo[1][1] / crz)))
    for t in (0.05, 0.08):
        for cxy in (0.5,):
            ev_rule(f"residual xy {cxy} (>=5) + map {t} (<5)", lambda n, pf, pl, lo, t=t, cxy=cxy: (pf / t, pl / t) if lo is None else (lo[0][0] / cxy, lo[1][0] / cxy))
