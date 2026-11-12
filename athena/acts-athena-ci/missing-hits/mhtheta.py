#!/usr/bin/env python3
"""Is the SP1 loc1 miss of pure barrel pixel seeds the estimate's theta error, and is that error scattering-like?
usage: mhtheta.py <off/sos.txt> [out.json]
For pure pixel seeds of prompt particles with SP0 and SP1 in the barrel:
  dtheta = theta(estimate) - theta(truth), predicted SP1 z shift = dtheta * dr * cosh^2(eta) (straight line in r-z),
  compared with the observed SP1 loc1 residual; dtheta * p binned in p (scattering: flat; estimator bias: grows with p)."""
import sys, math, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import load, width, q, pure_uid
D = load(sys.argv[1], "WXQRVS")
th = lambda eta: 2 * math.atan(math.exp(-eta))
rows = []
for k, recs in D['R'].items():
    if k[1] != '0' or k not in D['S'] or k not in D['X']: continue
    u = pure_uid(D['Q'], k)
    if u is None: continue
    V = D['V'].get((k[0], str(u)))
    if V is None or math.hypot(V[0], V[1]) > 2: continue
    r = next((x for x in recs if x['j'] == 1), None)
    if r is None or r['dim'] != 2: continue
    X = D['X'][k]; W = D['W'][k]
    r0, r1 = math.hypot(*X[0][:2]), math.hypot(*X[1][:2])
    if abs(r1 - r0) < 20: continue          # SP1 must be a further layer, not an overlap
    barrel = abs(X[1][2]) < 380 and r1 < 320 and abs(X[0][2]) < 380
    etaT = V[4]; pT = V[5] / 1000; p = pT * math.cosh(etaT)
    dth = th(D['S'][k][0]) - th(etaT)
    pred = dth * (r1 - r0) * math.cosh(etaT) ** 2 * 1e3   # um, |dz| for a straight r-z line
    rows.append(dict(k=k, barrel=barrel, eta=abs(etaT), p=p, pT=pT, dth=dth * 1e3, pred=pred, r1=r['r1'] * 1e3,
                     sP=math.sqrt(max(r['P11'], 0)) * 1e3, rank=r['rank'], nEta0=W[0][0]['nEta'], nEta1=W[1][0]['nEta']))
print(f"pure prompt pixel seeds with SP1 on a new layer: {len(rows)}, barrel SP0+SP1: {sum(r['barrel'] for r in rows)}")
OUT = {}
def corr(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)
B = [r for r in rows if r['barrel']]
print("\nbarrel, by |eta|: theta error of the estimate, its predicted and the observed SP1 z miss")
print("  |eta|      n     dtheta core  |pred| med  |obs| med  obs>200   corr(obs,pred)  |obs-pred| med   sigmaP med  outranked")
OUT['eta'] = {}
for lo, hi in ((0, .5), (.5, 1), (1, 1.5), (1.5, 2), (2, 2.7)):
    v = [r for r in B if lo <= r['eta'] < hi]
    if len(v) < 100: continue
    w, _ = width([r['dth'] for r in v])
    c = corr([abs(r['r1']) for r in v], [abs(r['pred']) for r in v])
    cs = corr([r['r1'] for r in v], [r['pred'] for r in v])
    resid = min(q([abs(r['r1'] - r['pred']) for r in v], .5), q([abs(r['r1'] + r['pred']) for r in v], .5))
    row = dict(n=len(v), dth=w, pred=q([abs(r['pred']) for r in v], .5), obs=q([abs(r['r1']) for r in v], .5),
               tail=sum(abs(r['r1']) > 200 for r in v) / len(v), corr=cs, rem=resid, sP=q([r['sP'] for r in v], .5),
               flip=sum(r['rank'] != 0 for r in v) / len(v))
    OUT['eta'][f"{lo}-{hi}"] = row
    print(f"  {lo:.1f}-{hi:.1f} {len(v):7d}   {w:6.2f} mrad   {row['pred']:8.1f}   {row['obs']:8.1f}   {row['tail']:6.1%}   {cs:+.3f} ({c:+.2f} abs)   {resid:8.1f}       {row['sP']:7.1f}    {row['flip']:.2%}")
print("\nbarrel: theta error x p by p (multiple scattering gives a flat theta0 * p)")
OUT['p'] = {}
for lo, hi in ((.5, 1), (1, 1.5), (1.5, 2.5), (2.5, 5), (5, 20), (20, 1e9)):
    v = [r for r in B if lo <= r['p'] < hi]
    if len(v) < 100: continue
    w, _ = width([r['dth'] for r in v]); wp, _ = width([r['dth'] * r['p'] for r in v])
    OUT['p'][f"{lo}-{hi}"] = dict(n=len(v), dth=w, dthp=wp)
    print(f"  p {lo:5g}-{hi:<5g} GeV n={len(v):7d}  dtheta core {w:6.2f} mrad   dtheta*p core {wp:6.2f} mrad GeV")
print("\nbarrel, by SP0 cluster length: theta error of the estimate (cluster length ~ eta, so also by |eta| 1-1.5 only)")
OUT['nEta0'] = {}
for ne in range(1, 13):
    v = [r for r in B if min(r['nEta0'], 12) == ne]; v2 = [r for r in v if 1 <= r['eta'] < 1.5]
    if len(v) < 100: continue
    w, _ = width([r['dth'] for r in v]); w2 = width([r['dth'] for r in v2])[0] if len(v2) > 50 else float('nan')
    OUT['nEta0'][ne] = dict(n=len(v), dth=w, n2=len(v2), dth2=w2)
    print(f"  nEta0 {ne:2d}: n={len(v):6d} dtheta core {w:6.2f} mrad | at |eta| 1-1.5: n={len(v2):6d} {w2:6.2f} mrad")
if len(sys.argv) > 2: json.dump(OUT, open(sys.argv[2], 'w'), indent=1)
