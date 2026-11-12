#!/usr/bin/env python3
"""Seed estimate theta vs the fitted track's theta at SP0 (E lines, forced run), for pure barrel pixel seeds of prompt
particles, binned in p and |eta|: multiple scattering inside the seed gives dtheta*p flat, an estimator floor gives
dtheta flat. Also the same for the weighted-fit estimate if a second dump is given.
usage: mhfit.py <on/sos.txt> [out.json]"""
import sys, math, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import width, q
fn = sys.argv[1]
E = {}; Q = {}; V = {}; X = {}
for l in open(fn):
    c = l[0]
    if c == 'E':
        a, b, _ = l.split('|', 2); f = a.split()
        if f[2] != '0' or f[4] != '1' or (f[1], f[2], f[3]) in E: continue
        E[(f[1], f[2], f[3])] = [tuple(float(y) for y in e.split(':')) for e in b.split()]
    elif c == 'Q':
        a, b = l.split('|', 1); f = a.split()
        if f[2] == '0': Q[(f[1], f[2], f[3])] = {int(u) for sp in b.split() for u in sp.split(',')}
    elif c == 'V':
        f = l.split(); V[(f[1], f[2])] = tuple(float(x) for x in f[3:10])
    elif c == 'X':
        a, b = l.split('|', 1); f = a.split()
        if f[2] == '0': X[(f[1], f[2], f[3])] = [tuple(float(x) for x in sp.split(',')) for sp in b.split()]
rows = []
for k, e in E.items():
    us = Q.get(k)
    if not us or len(us) != 1 or min(us) < 0: continue
    v = V.get((k[0], str(min(us))))
    if v is None or math.hypot(v[0], v[1]) > 2: continue
    x = X.get(k)
    if not x or abs(x[0][2]) > 380 or math.hypot(*x[0][:2]) > 320: continue  # SP0 in the barrel
    p = v[5] / 1000 * math.cosh(v[4])
    dth = (e[3][0] - e[3][2]) * 1e3; dthT = (e[3][2] - 2 * math.atan(math.exp(-v[4]))) * 1e3
    rows.append(dict(p=p, eta=abs(v[4]), dth=dth, dthT=dthT, n=len(x)))
print(f"pure prompt pixel seeds with SP0 in the barrel and a selected track: {len(rows)}")
OUT = {'p': {}, 'eta': {}}
print("by p: estimate - fit theta at SP0 (core), x p; fit - truth(production) for reference")
for lo, hi in ((.5, 1), (1, 1.5), (1.5, 2.5), (2.5, 5), (5, 10), (10, 1e9)):
    v = [r for r in rows if lo <= r['p'] < hi]
    if len(v) < 100: continue
    w, _ = width([r['dth'] for r in v]); wp, _ = width([r['dth'] * r['p'] for r in v]); wt, _ = width([r['dthT'] for r in v])
    OUT['p'][f"{lo:g}-{hi:g}"] = dict(n=len(v), dth=w, dthp=wp, fitTruth=wt)
    print(f"  p {lo:4g}-{hi:<5g} n={len(v):6d}  est-fit {w:5.2f} mrad  x p {wp:5.2f} mrad GeV | fit-truth {wt:5.2f} mrad")
print("by |eta| (p 2.5-10 GeV, and all p)")
for lo, hi in ((0, .5), (.5, 1), (1, 1.5), (1.5, 2), (2, 2.7)):
    v = [r for r in rows if lo <= r['eta'] < hi]; vh = [r for r in v if 2.5 <= r['p'] < 10]
    if len(v) < 100: continue
    w, _ = width([r['dth'] for r in v]); wh = width([r['dth'] for r in vh])[0] if len(vh) > 50 else float('nan')
    OUT['eta'][f"{lo}-{hi}"] = dict(n=len(v), dth=w, nh=len(vh), dthh=wh)
    print(f"  |eta| {lo}-{hi} n={len(v):6d}  est-fit {w:5.2f} mrad | p 2.5-10: n={len(vh):5d} {wh:5.2f} mrad")
if len(sys.argv) > 2: json.dump(OUT, open(sys.argv[2], 'w'), indent=1)
