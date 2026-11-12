#!/usr/bin/env python3
"""Local (first three SPs) vs FirstMiddleLast seed estimates on truth-pure seeds, binned by the lever arm.
Reference track = smoothed fit at the start surface from the FML run (forcing off).
usage: sosloc.py <ref FML off sos.txt> name=<sos.txt> ..."""
import sys, collections, math, statistics as st
def width(v):
    if len(v) < 2: return float('nan')
    m = st.median(v); return 1.4826 * st.median(abs(x - m) for x in v)
def load(fn):
    E = {}; F = {}; rad = {}; comp = {}; sel = set(); eta = {}
    for l in open(fn):
        c = l[0]
        if c == 'S':
            f = l.split(); eta[(int(f[1]), int(f[2]), int(f[3]))] = float(f[4])
        elif c == 'T':
            a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            if f[6] == '1': sel.add(k)
            if k in rad: continue
            rs = {}; us = collections.defaultdict(set)
            for e in b.split():
                p = e.split(':'); rs[int(p[0])] = float(p[1]); us[int(p[0])].add(int(p[7]))
            rad[k] = [rs[i] for i in sorted(rs)]
            lab = [next(iter(us[i])) if len(us[i]) == 1 else -2 for i in sorted(us)]
            comp[k] = lab[0] >= 0 and all(x == lab[0] for x in lab)
        elif c == 'E':
            a, b, _ = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            par = [tuple(float(x) for x in e.split(':')) for e in b.split()]
            if k not in E: E[k] = [p[0] for p in par] + [par[4][1]]
            if f[4] == '1' and f[5] == '1' and k not in F: F[k] = [p[2] for p in par]
    return dict(E=E, F=F, rad=rad, comp=comp, sel=sel, eta=eta)
ref = load(sys.argv[1]); V = [("FML (default)", ref)] + [(a.split('=')[0], load(a.split('=')[1])) for a in sys.argv[2:]]
def dphi(e, f): return ((e[2] - f[2] + math.pi) % (2 * math.pi) - math.pi) * 1e3
def dth(e, f): return (e[3] - f[3]) * 1e3
def dqop(e, f): return (e[4] - f[4]) / abs(f[4])
for ty, tname in ((0, "pixel"), (1, "strip")):
    keys = [k for k in ref['F'] if k[1] == ty and ref['comp'].get(k) and len(ref['rad'].get(k, [])) >= 3 and k in ref['eta']
            and all(k in v['E'] for _, v in V)]
    def s01(k): return (ref['rad'][k][1] - ref['rad'][k][0]) * math.cosh(ref['eta'][k])
    def s02(k): return (ref['rad'][k][2] - ref['rad'][k][0]) * math.cosh(ref['eta'][k])
    edges = [0, 10, 20, 30, 40, 60, 80, 120, 1e9] if ty == 0 else [0, 20, 40, 80, 160, 320, 1e9]
    def t02(k): return ref['rad'][k][2] - ref['rad'][k][0]
    for lever, fn in (("SP0-SP1 distance", s01), ("SP0-SP2 distance", s02), ("SP0-SP2 transverse dr", t02)):
        print(f"\n### {tname}: {len(keys)} pure seeds with a fitted track in the reference; binned by {lever} [mm] (~dr*cosh eta)")
        print(f"{'bin':>10s} {'n':>7s} | " + " | ".join(f"{n[:13]:>13s} phi  th  qop  lost" for n, _ in V))
        for lo, hi in zip(edges[:-1], edges[1:]):
            ks = [k for k in keys if lo <= fn(k) < hi]
            if len(ks) < 50: continue
            row = f"{lo:4.0f}-{hi if hi < 1e8 else 'inf':>5} {len(ks):7d} |"
            for _, v in V:
                f_ = [ref['F'][k] for k in ks]; e_ = [v['E'][k] for k in ks]
                row += f" {width([dphi(e, f) for e, f in zip(e_, f_)]):9.2f} {width([dth(e, f) for e, f in zip(e_, f_)]):4.2f} {width([dqop(e, f) for e, f in zip(e_, f_)]):4.2f} {1000*sum(1 for k in ks if k not in v['sel'])/len(ks):5.1f} |"
            print(row)
    # sign of the problem: fraction with |dphi| or |dtheta| beyond the fixed 1.75 mrad initial sigma x 3
    print(f"\n{tname}: tail beyond 3 x 1.75 mrad (phi or theta), relative q/p error > 50%, and lost (per mille of pure found-in-reference seeds)")
    for n, v in V:
        a = sum(1 for k in keys if max(abs(dphi(v['E'][k], ref['F'][k])), abs(dth(v['E'][k], ref['F'][k]))) > 5.25)
        b = sum(1 for k in keys if abs(dqop(v['E'][k], ref['F'][k])) > 0.5)
        c = sum(1 for k in keys if k not in v['sel'])
        print(f"  {n:16s} dir tail {1000*a/len(keys):6.2f}   qop>50% {1000*b/len(keys):6.2f}   lost {1000*c/len(keys):6.2f}")
