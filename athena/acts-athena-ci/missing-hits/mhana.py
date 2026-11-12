#!/usr/bin/env python3
"""Missing-hits analysis.
usage: mhana.py <off/sos.txt> <on/sos.txt> [out.json]
 1. layer map: gid (vol/lay) -> r, |z| range of the seed space points
 2. OFF: SP1 residual tail of pure pixel seeds vs cluster size and layer of SP0/SP1
 3. truth helix: z of each seed SP against the truth particle's helix (prompt particles), vs cluster size and pT
 4. ON: smoothed loc1 residuals of the pixel hits of selected tracks, vs layer and cluster length"""
import sys, math, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import load, width, q, pure_uid

OFF = load(sys.argv[1], "WXQRVS")
ON = load(sys.argv[2], "WXQYKV")
OUT = {}
BZ = 2.0  # T, solenoid in the pixel volume

# --- 1. layer map
geo = collections.defaultdict(list)
for D in (OFF, ON):
    for k, W in D['W'].items():
        if k[1] != '0' or k not in D['X']: continue
        for sp, x in zip(W, D['X'][k]):
            p = sp[0]
            if p: geo[(p['vol'], p['lay'])].append((math.hypot(x[0], x[1]), abs(x[2])))
def lname(vl):
    g = geo.get(vl)
    if not g: return f"{vl[0]}/{vl[1]}"
    r = sorted(a for a, _ in g); z = sorted(b for _, b in g)
    rr = (r[len(r)//50], r[-len(r)//50 - 1]); zz = (z[len(z)//50], z[-len(z)//50 - 1])
    kind = "B" if rr[1] - rr[0] < zz[1] - zz[0] else "E"
    return f"{vl[0]}/{vl[1]} {kind} r{rr[0]:.0f}-{rr[1]:.0f} z{zz[0]:.0f}-{zz[1]:.0f}"
print("== layers (pixel seed SPs)")
LAY = {}
for vl in sorted(geo):
    LAY[vl] = lname(vl); print(f"  {LAY[vl]:42s} n={len(geo[vl])}")
OUT['layers'] = {f"{a}/{b}": LAY[(a, b)] for a, b in LAY}

# --- 2. SP1 tail vs cluster shape
print("\n== OFF: SP1 loc1 residual of pure pixel seeds vs SP1/SP0 cluster")
rows = []
for k, recs in OFF['R'].items():
    if k[1] != '0' or pure_uid(OFF['Q'], k) is None or k not in OFF['W']: continue
    r = next((x for x in recs if x['j'] == 1), None)
    if r is None or r['dim'] != 2: continue
    W = OFF['W'][k]
    if len(W) < 3 or not W[1][0] or not W[0][0]: continue
    rows.append((abs(r['r1']) * 1e3, r['rank'], W[0][0], W[1][0], W, k))
def tailtab(keyf, label, keys=None):
    g = collections.defaultdict(list)
    for row in rows: g[keyf(row)].append(row)
    print(f"  by {label}:")
    res = {}
    for kk in sorted(g, key=lambda z: (str(type(z)), z)):
        v = g[kk]
        if len(v) < 200: continue
        t = sum(x[0] > 200 for x in v) / len(v); fl = sum(x[1] != 0 for x in v) / len(v)
        print(f"    {str(kk):44s} n={len(v):7d}  |r1| median {q([x[0] for x in v], .5):6.1f} um  >200um {t:6.1%}  outranked {fl:6.2%}")
        res[str(kk)] = dict(n=len(v), med=q([x[0] for x in v], .5), tail=t, flip=fl)
    return res
OUT['tail_sp1_layer'] = tailtab(lambda r: LAY.get((r[3]['vol'], r[3]['lay']), "?"), "SP1 layer")
OUT['tail_sp1_neta'] = tailtab(lambda r: min(r[3]['nEta'], 12), "SP1 cluster size in eta (12 = >=12)")
OUT['tail_sp0_neta'] = tailtab(lambda r: min(r[2]['nEta'], 12), "SP0 cluster size in eta")
OUT['tail_sp1_shape'] = tailtab(lambda r: ("line" if r[3]['nRDO'] == r[3]['nEta'] * r[3]['nPhi'] or r[3]['nPhi'] == 1 and r[3]['nRDO'] == r[3]['nEta'] else
                                           "gappy/2D" ), "SP1 cluster shape (all cells of the box filled or a 1-wide line)")
def sigma1(p): return math.sqrt(p['c11']) * 1e3
OUT['tail_sp1_sig'] = tailtab(lambda r: round(sigma1(r[3]), 1), "SP1 loc1 sigma [um]")

# --- 3. truth helix in r-z
print("\n== truth helix: z(SP) - z(truth helix at r(SP)), pure pixel seeds of prompt particles")
def ztruth(V, x):
    vx, vy, vz, phi, eta, pt, ch = V
    if ch == 0 or pt <= 0: return None
    R = pt / 1000. / (0.3 * BZ) * 1000.  # mm
    d = math.hypot(x[0] - vx, x[1] - vy)
    if d > 2 * R: return None
    s = 2 * R * math.asin(d / (2 * R))
    return vz + s * math.sinh(eta)
hel = collections.defaultdict(list)
helrows = []
for k, W in OFF['W'].items():
    if k[1] != '0' or k not in OFF['X']: continue
    u = pure_uid(OFF['Q'], k)
    if u is None: continue
    V = OFF['V'].get((k[0], str(u)))
    if V is None or math.hypot(V[0], V[1]) > 2 or V[5] < 700: continue
    X = OFF['X'][k]
    dz = []
    for i, (sp, x) in enumerate(zip(W, X)):
        p = sp[0]; zt = ztruth(V, x)
        if p is None or zt is None: dz.append(None); continue
        dz.append((x[2] - zt) * 1e3)
    if any(d is None for d in dz): continue
    # remove the overall offset (vertex z resolution of the truth is exact, but keep it honest): use dz relative to SP0
    for i, (sp, d) in enumerate(zip(W, dz)):
        p = sp[0]
        bar = "B" if LAY.get((p['vol'], p['lay']), "? ?").split()[1] == "B" else "E"
        hel[(bar, min(p['nEta'], 12))].append(d)
    helrows.append((k, V, dz, W, X))
print("  barrel/endcap, nEta: n, z residual to truth helix core width / median / 90% |dz| [um]")
OUT['helix'] = {}
for kk in sorted(hel):
    v = hel[kk]
    if len(v) < 200: continue
    w, m = width(v)
    print(f"    {kk[0]} nEta {kk[1]:2d}: n={len(v):7d}  core {w:7.1f}  median {m:+7.1f}  90% {q([abs(x) for x in v], .9):7.1f}")
    OUT['helix'][f"{kk[0]} {kk[1]}"] = dict(n=len(v), core=w, med=m, q90=q([abs(x) for x in v], .9))
# by pT for the barrel: MS grows with 1/p, a cluster problem does not
print("  barrel SPs by truth pT:")
byp = collections.defaultdict(list)
for k, V, dz, W, X in helrows:
    for sp, d, x in zip(W, dz, X):
        if LAY.get((sp[0]['vol'], sp[0]['lay']), "? ?").split()[1] != "B": continue
        b = next(b for b in (1, 1.5, 2, 5, 1e9) if V[5] / 1000 < b)
        byp[b].append(d)
for b in sorted(byp):
    w, m = width(byp[b]); print(f"    pT < {b:g} GeV: n={len(byp[b]):7d} core {w:7.1f}  90% {q([abs(x) for x in byp[b]], .9):7.1f}")

# seeds in the SP1 tail: which SP is off the truth helix?
print("  seeds in the SP1 tail vs the rest: per-SP |dz to truth| median [um] (SP0, SP1, SP2, ..., last)")
tailk = {row[5] for row in rows if row[0] > 200}
allk = {row[5] for row in rows}
for name, sel in (("tail", lambda k: k in tailk), ("core", lambda k: k in allk and k not in tailk)):
    per = collections.defaultdict(list)
    for k, V, dz, W, X in helrows:
        if not sel(k): continue
        n = len(dz)
        for i, d in enumerate(dz):
            lab = "last" if i == n - 1 else ("mid" if i == n // 2 else str(i))
            per[lab].append(abs(d))
    print(f"    {name}: " + "  ".join(f"{lab} {q(per[lab], .5):6.1f}/{q(per[lab], .9):6.1f}" for lab in ("0", "1", "2", "mid", "last") if per[lab]))
# SP1 offset relative to the line through SP0 and the truth direction: separates SP0 vs SP1
OUT['helix_tail'] = {}

# --- 4. ON: track residuals
print("\n== ON: unbiased loc1 residual of pixel hits on selected tracks (hit truth == track majority)")
tr = collections.defaultdict(list); trl = collections.defaultdict(list)
for k, lst in ON['Y'].items():
    if k[1] != '0': continue
    Ks = ON['K'].get(k, [])
    for (sel, sts), kk in zip(lst, Ks):
        if not sel: continue
        maj = kk[1]
        for s in sts:
            if s['flag'] != 'M' or s['truth'] != maj or maj < 0: continue
            un = s['c11'] - s['C11']   # unbiased residual: r_s * V / (V - C), pull r_s / sqrt(V - C)
            if un <= 0: continue
            r1 = (s['ly'] - s['p1']) * s['c11'] / un * 1e3
            tanA = abs(s['dy'] / s['dz']) if s['dz'] else 99
            lay = LAY.get((s['vol'], s['lay']), f"{s['vol']}/{s['lay']}")
            tr[(lay, min(s['nEta'], 12))].append((r1, (s['ly'] - s['p1']) / math.sqrt(un)))
            trl[lay].append((r1, s['nEta'], tanA))
OUT['track'] = {}
for lay in sorted(trl):
    v = trl[lay]
    if len(v) < 500: continue
    w, m = width([x[0] for x in v])
    print(f"  {lay}: n={len(v)} loc1 residual core {w:.1f} um, 90% {q([abs(x[0]) for x in v], .9):.1f}")
    for ne in range(1, 13):
        vv = tr.get((lay, ne))
        if not vv or len(vv) < 100: continue
        w, m = width([x[0] for x in vv]); pw, _ = width([x[1] for x in vv if x[1] == x[1]])
        print(f"      nEta {ne:2d}: n={len(vv):7d} core {w:6.1f} um (median {m:+5.1f}) 90% {q([abs(x[0]) for x in vv], .9):6.1f}  pull core {pw:.2f}")
        OUT['track'][f"{lay}|{ne}"] = dict(n=len(vv), core=w, med=m, q90=q([abs(x[0]) for x in vv], .9), pull=pw)
if len(sys.argv) > 3: json.dump(OUT, open(sys.argv[3], 'w'), indent=1)
