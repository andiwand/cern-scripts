#!/usr/bin/env python3
"""Direction error of the seed estimate (vs fitted track at the start SP) by pT, first gap and eta, pixel pure seeds.
usage: sosdir.py <on/sos.txt> <off/sos.txt>"""
import sys, collections, statistics as st, math
src = open(__file__.replace("sosdir.py", "sospull.py")).read()
exec(src.split("SA, TA, _ = load(sys.argv[1])")[0].replace('open(__file__.replace("sospull.py", "sosclean.py"))', 'open(__file__.replace("sosdir.py", "sosclean.py"))'))
SA, TA, _ = load(sys.argv[1]); SB, TB, _ = load(sys.argv[2]); EA = loadE(sys.argv[1])
rad = {}
for l in open(sys.argv[1]):
    if l[0] != 'T': continue
    a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
    if k in rad or f[2] != '0': continue
    rs = {}
    for e in b.split():
        p = e.split(':'); rs[int(p[0])] = float(p[1])
    rad[k] = [rs[i] for i in sorted(rs)]
def comp(k):
    t = anyt(TA.get(k, [])) or anyt(TB.get(k, []))
    return composition(t['ms'])[0] if t else "none"
pure = [k for k in SB if k[1] == 0 and k in SA and comp(k) == "pure" and k in EA and k in rad]
only = set(k for k in pure if best(TA.get(k, [])) and not best(TB.get(k, [])))
def ptb(k):
    p = abs(1 / EA[k][0][4][2]) * math.sin(EA[k][0][3][2])
    return "pT<1" if p < 1 else "pT1-2" if p < 2 else "pT2-5" if p < 5 else "pT>=5"
def gapb(k):
    g = rad[k][1] - rad[k][0]; return "gap<10" if g < 10 else "gap10-30" if g < 30 else "gap30-60" if g < 60 else "gap>=60"
def etab(k):
    e = abs(SA[k]['eta']); return "eta<1.5" if e < 1.5 else "eta1.5-2.5" if e < 2.5 else "eta>=2.5"
def dphi(k):
    par = EA[k][0]; return ((par[2][0] - par[2][2] + math.pi) % (2 * math.pi) - math.pi) * 1000
def dth(k):
    par = EA[k][0]; return (par[3][0] - par[3][2]) * 1000
print(f"{'class':12s} {'n':>8s} {'phi core mrad':>14s} {'theta core':>11s} {'lost w/o forcing':>18s}")
for fn in (ptb, gapb, etab):
    H = collections.defaultdict(lambda: [[], [], 0])
    for k in pure:
        b = fn(k); H[b][0].append(dphi(k)); H[b][1].append(dth(k)); H[b][2] += k in only
    for b in sorted(H):
        v = H[b]; n = len(v[0])
        if n < 200: continue
        print(f"{b:12s} {n:8d} {width(v[0])[0]:14.2f} {width(v[1])[0]:11.2f} {v[2]/n*1000:14.2f} per mille")
for name, f in (("phi", dphi), ("theta", dth)):
    print(f"\n{name} core [mrad] by first gap (rows) x fitted pT (cols)")
    H = collections.defaultdict(list)
    for k in pure: H[(gapb(k), ptb(k))].append(f(k))
    cols = ["pT<1", "pT1-2", "pT2-5", "pT>=5"]
    print(" " * 10 + "".join(f"{c:>10s}" for c in cols))
    for g in ("gap<10", "gap10-30", "gap30-60", "gap>=60"):
        print(f"{g:10s}" + "".join(f"{width(H[(g,c)])[0]:10.2f}" if len(H[(g, c)]) > 100 else f"{'-':>10s}" for c in cols))
