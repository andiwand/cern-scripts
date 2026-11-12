#!/usr/bin/env python3
"""Analyse ACTS_SOS_DIAG dumps of forceTrackOnSeed on/off.
usage: sosana.py <on/sos.txt> <off/sos.txt>
S evt type iseed eta pt ntracks nmeas seedUid
T evt type iseed eta pt selected nMeas nHoles nOut chi2 seedUid nTrue nAny | isp:r:p|s:code:chi2:tr:pos:uid ..."""
import sys, collections
from scipy.stats import chi2 as C2, norm
def cut(sig, dim): return C2.ppf(1 - 2 * norm.sf(sig), dim)
CUT = {d: (cut(7, d), cut(10, d)) for d in (1, 2)}
def load(fn):
    S = {}; T = collections.defaultdict(list)
    for l in open(fn):
        if l[0] == 'S':
            f = l.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            S[k] = dict(eta=float(f[4]), pt=float(f[5]), ntr=int(f[6]), nm=int(f[7]), uid=int(f[8]))
        elif l[0] == 'T':
            a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            ms = []
            for e in b.split():
                isp, r, pt_, code, c2, tr, pos, uid = e.split(':')
                ms.append(dict(isp=int(isp), r=float(r), pix=pt_ == 'p', code=code, chi2=float(c2), tr=tr, pos=int(pos), uid=int(uid)))
            T[k].append(dict(eta=float(f[4]), pt=float(f[5]), sel=f[6] == '1', nm=int(f[7]), nh=int(f[8]), no=int(f[9]),
                             chi2=float(f[10]), uid=int(f[11]), ntrue=int(f[12]), nany=int(f[13]), ms=ms))
    return S, T
def spb(m, ms):
    last = max(x['isp'] for x in ms)
    i = m['isp']
    return 'last' if i == last else str(i) if i < 3 else 'mid'
def best(tr):
    s = [t for t in tr if t['sel']]
    return max(s, key=lambda t: t['nm']) if s else None
def ptb(pt): return "<1" if pt < 1 else "1-2" if pt < 2 else "2-5" if pt < 5 else ">=5"
def etab(e): return "<1.5" if abs(e) < 1.5 else "1.5-2.5" if abs(e) < 2.5 else ">=2.5"
on, off = load(sys.argv[1]), load(sys.argv[2])
TYPE = {0: 'pixel', 1: 'strip'}
for name, (S, T) in (("ON", on), ("OFF", off)):
    print(f"===== {name}: {len(S)} processed seeds, {sum(len(v) for v in T.values())} track candidates")
    for ty in (0, 1):
        keys = [k for k in S if k[1] == ty]
        tru = [k for k in keys if S[k]['uid'] >= 0]
        sel = [k for k in keys if best(T.get(k, []))]
        selt = [k for k in tru if best(T.get(k, []))]
        print(f"  {TYPE[ty]:5s} seeds {len(keys)}  truth-pure {len(tru)} ({len(tru)/max(1,len(keys)):.3f})  with selected track {len(sel)}  truth-pure with selected {len(selt)} ({len(selt)/max(1,len(tru)):.3f})")
        # seed measurement fate on the best selected track, by seed SP index, truth-pure seeds
        fate = collections.Counter()
        for k in tru:
            b = best(T.get(k, []))
            if not b: continue
            for m in b['ms']:
                fate[(spb(m, b['ms']), m['code'] + (m['tr'] if m['code'] in 'XY' else ''))] += 1
        sps = [x for x in ('0','1','2','mid','last') if any(j == x for j, _ in fate)]
        for i in sps:
            row = {c: n for (j, c), n in fate.items() if j == i}; tot = sum(row.values())
            print(f"    SP{i}: " + "  ".join(f"{c}={n} ({n/tot:.3f})" for c, n in sorted(row.items(), key=lambda x: -x[1])))
    if name == "ON":
        # chi2 of forced states vs the would-be cuts
        print("  forced seed states (code M), chi2 above the 7 sigma measurement / 10 sigma outlier cuts")
        H = collections.defaultdict(lambda: [0, 0, 0])
        for k, tr in T.items():
            for t in tr:
                for m in t['ms']:
                    if m['code'] != 'M' or m['chi2'] < 0: continue
                    d = 2 if m['pix'] else 1
                    sb = spb(m, t['ms'])
                    for key in [("all", TYPE[k[1]], sb), ("pt " + ptb(t['pt']), TYPE[k[1]], sb), ("eta " + etab(t['eta']), TYPE[k[1]], sb),
                                ("truth " + ("pure" if t['uid'] >= 0 else "mixed"), TYPE[k[1]], sb)]:
                        h = H[key]; h[0] += 1; h[1] += m['chi2'] > CUT[d][0]; h[2] += m['chi2'] > CUT[d][1]
        for key in sorted(H):
            n, a, b = H[key]
            if n < 200: continue
            print(f"    {key[0]:12s} {key[1]:5s} SP{key[2]}  n={n:8d}  >7s {a/n:.4f}  >10s {b/n:.4f}")
