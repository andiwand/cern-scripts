#!/usr/bin/env python3
"""Error table of the seed estimate: estimate minus the fitted track at SP0 for pure pixel seeds with a selected track,
in |eta| x pT bins: robust sigma of phi [rad], theta [rad], q/p relative, and rho(phi, q/p) on the 3-sigma core.
Prints the Gaudi property values (row-major, eta outer). usage: mhcovtable.py <sos.txt> [out.json]"""
import sys, math, json, collections
import numpy as np
ETA = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.2]; P = [0, 1.5, 3.0, 6.0, 1e9]   # pT [GeV]
E = {}; Q = {}
for l in open(sys.argv[1]):
    c = l[0]
    if c == 'E':
        a, b, _ = l.split('|', 2); f = a.split()
        if f[2] != '0' or f[4] != '1' or (f[1], f[3]) in E: continue
        E[(f[1], f[3])] = [tuple(float(y) for y in e.split(':')) for e in b.split()]
    elif c == 'Q':
        a, b = l.split('|', 1); f = a.split()
        if f[2] == '0': Q[(f[1], f[3])] = {int(u) for sp in b.split() for u in sp.split(',')}
cells = collections.defaultdict(list)
for k, e in E.items():
    if len(Q.get(k, {-1})) != 1 or min(Q[k]) < 0: continue
    th = e[3][2]; qop = e[4][2]
    if qop == 0: continue
    eta = abs(-math.log(math.tan(th / 2))); p = math.sin(th) / abs(qop)
    ie = next((i for i in range(len(ETA) - 1) if ETA[i] <= eta < ETA[i + 1]), None)
    ip = next(i for i in range(len(P) - 1) if P[i] <= p < P[i + 1])
    if ie is None: continue
    dphi = (e[2][0] - e[2][2] + math.pi) % (2 * math.pi) - math.pi
    cells[(ie, ip)].append((dphi, e[3][0] - e[3][2], (e[4][0] - e[4][2]) / abs(qop)))
sphi, sth, sq, rho, n = [], [], [], [], []
print("  |eta|      pT [GeV]     n     sigma phi [mrad]  theta [mrad]  q/p rel   rho(phi,q/p)")
for ie in range(len(ETA) - 1):
    for ip in range(len(P) - 1):
        # a sparse cell takes the nearest populated pT bin of the same eta row
        order = sorted(range(len(P) - 1), key=lambda j: abs(j - ip))
        A = next((np.array(cells[(ie, j)]) for j in order if len(cells.get((ie, j), [])) >= 200), None)
        med = np.median(A, 0); s = 1.4826 * np.median(abs(A - med), 0)
        m = np.all(abs(A - med) < 3 * s, 1); r = np.corrcoef(A[m].T)[0, 2]
        sphi.append(float(s[0])); sth.append(float(s[1])); sq.append(float(s[2])); rho.append(float(r)); n.append(len(A))
        print(f"  {ETA[ie]:3.1f}-{ETA[ie+1]:3.1f}  {P[ip]:4g}-{P[ip+1]:<5g} {len(A):7d}   {s[0]*1e3:8.3f}        {s[1]*1e3:8.3f}    {s[2]:7.4f}   {r:+.2f}")
r6 = lambda v: [round(x, 6) for x in v]
cfg = {"covTableEtaEdges": ETA[1:-1], "covTablePEdges": P[1:-1], "covTableSigmaPhi": r6(sphi), "covTableSigmaTheta": r6(sth),
       "covTableSigmaQOverPRel": r6(sq), "covTableRhoPhiQOverP": [round(x, 3) for x in rho]}
print(json.dumps(cfg))
if len(sys.argv) > 2: json.dump(cfg, open(sys.argv[2], 'w'))
