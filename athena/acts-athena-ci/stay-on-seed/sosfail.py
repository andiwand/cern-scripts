#!/usr/bin/env python3
"""Why the candidates of truth-pure seeds fail the selection without forcing (and pass with it).
usage: sosfail.py <on/sos.txt> <off/sos.txt>"""
import sys, collections
def load(fn):
    S = {}; T = collections.defaultdict(list)
    for l in open(fn):
        if l[0] == 'S':
            f = l.split(); S[(int(f[1]), int(f[2]), int(f[3]))] = dict(pt=float(f[5]), eta=float(f[4]), nm=int(f[7]), uid=int(f[8]))
        elif l[0] == 'T':
            a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            p = f[f.index('P') + 1:]
            codes = "".join(e.split(':')[3] for e in b.split())
            T[k].append(dict(sel=f[6] == '1', nm=int(f[7]), nh=int(f[8]), no=int(f[9]), chi2=float(f[10]), ntrue=int(f[12]),
                             d0=float(p[0]), z0=float(p[1]), pt=float(p[2]), eta=float(p[3]), npix=int(p[4]), nstr=int(p[5]), valid=p[6] == '1', codes=codes))
    return S, T
def reasons(t):
    a = abs(t['eta']); b = 0 if a < 2.0 else 1 if a < 2.6 else 2
    r = []
    if t['pt'] < [0.9, 0.4, 0.4][b]: r.append("pT")
    if abs(t['d0']) > [5, 5, 10][b]: r.append("d0")
    if abs(t['z0']) > 200: r.append("z0")
    if t['nm'] < [9, 8, 7][b]: r.append("nMeas")
    if t['npix'] < 3: r.append("nPix")
    if t['nh'] > 1: r.append("holes")
    if t['no'] > 1: r.append("outliers")
    if a > 4.0: r.append("eta")
    return "+".join(r) or ("other (valid=%d)" % t['valid'])
(SA, TA), (SB, TB) = load(sys.argv[1]), load(sys.argv[2])
best = lambda tr: max([t for t in tr if t['sel']], key=lambda t: t['nm'], default=None)
for ty in (0, 1):
    ks = [k for k in SB if k[1] == ty and SB[k]['uid'] >= 0 and k in SA and best(TA.get(k, [])) and not best(TB.get(k, []))]
    c = collections.Counter(); ex = []
    for k in ks:
        tr = TB.get(k, [])
        if not tr: c["no candidate (dropped by branch stopper)"] += 1; continue
        t = max(tr, key=lambda t: t['nm']); c[reasons(t)] += 1
        if len(ex) < 8: ex.append((k, best(TA[k]), t))
    print(f"type {ty}: {len(ks)} truth-pure seeds selected only with forcing; reason the forcing-off candidate fails:")
    for x, n in c.most_common(): print(f"   {n:5d}  {x}")
    for k, a, t in ex:
        print(f"   ex {k} seed pt {SB[k]['pt']:.2f}  ON: pt {a['pt']:.2f} d0 {a['d0']:+.2f} z0 {a['z0']:+.1f} nm {a['nm']} nh {a['nh']}  | OFF: pt {t['pt']:.2f} d0 {t['d0']:+.2f} z0 {t['z0']:+.1f} nm {t['nm']} nh {t['nh']} no {t['no']} true {t['ntrue']} {t['codes']}")
