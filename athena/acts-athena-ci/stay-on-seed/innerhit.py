#!/usr/bin/env python3
"""Innermost hit of the found tracks vs the particle's innermost pixel cluster, from K and P lines of a dump.
Reconstructable primaries (status 1, charged, prodR < 300 mm, pT > 0.9 GeV, |eta| < 4) with an innermost pixel cluster;
per particle the selected track with most of its measurements (>= 50%).
usage: innerhit.py <sos.txt> [name]"""
import sys, collections, json
P = {}; K = {}
for l in open(sys.argv[1]):
    if l[0] == 'P':
        f = l.split()
        if len(f) < 12: continue
        ev, idx, pt, eta, q, st, pr, rI = int(f[1]), int(f[2]), float(f[3]), float(f[4]), float(f[5]), int(f[6]), float(f[8]), float(f[11])
        if st == 1 and q != 0 and pr < 300 and pt >= 900 and abs(eta) < 4 and rI > 0: P[(ev, idx)] = (eta, rI)
    elif l[0] == 'K':
        f = l.split(); ev, sel, maj, mc, nm, rMin, uMin = int(f[1]), f[4] == '1', int(f[5]), int(f[6]), int(f[7]), float(f[8]), int(f[9])
        if not sel or maj < 0 or 2 * mc < nm: continue
        k = (ev, maj)
        if k not in K or mc > K[k][0]: K[k] = (mc, rMin, uMin)
C = collections.defaultdict(collections.Counter)
for k, (mc, rMin, uMin) in K.items():
    if k not in P: continue
    eta, rI = P[k]; reg = "|eta|<1.5" if abs(eta) < 1.5 else "1.5-2.5" if abs(eta) < 2.5 else ">=2.5"
    if uMin != k[1]: cat = "wrong"
    elif abs(rMin - rI) < 0.5: cat = "right"
    elif rMin - rI < 15: cat = "same layer"
    else: cat = "missed"
    for r in (reg, "all"): C[r][cat] += 1; C[r]["n"] += 1
name = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
res = {r: {c: C[r][c] / C[r]["n"] for c in ("right", "same layer", "missed", "wrong")} | {"n": C[r]["n"]} for r in C}
print(f"{name:22s} " + "  ".join(f"{r}: n={res[r]['n']} miss {100*res[r]['missed']:.2f}% wrong {100*res[r]['wrong']:.2f}%" for r in ("all", "|eta|<1.5", "1.5-2.5", ">=2.5") if r in res))
print("JSON " + json.dumps({name: res}))
