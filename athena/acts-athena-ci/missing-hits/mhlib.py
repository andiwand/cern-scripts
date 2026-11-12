#!/usr/bin/env python3
"""Readers for the missing-hits dump lines (W, X, Q, R, V, Y, K, S) of the athena-sos diagnostic build."""
import math, collections, statistics as st

def pixtok(t):
    """'vol/lay/sens:nPhi:nEta:nRDO:lx:ly:c00:c11' -> dict (None for strip)."""
    f = t.split(':')
    if len(f) < 8: return None
    v, l, s = (int(x) for x in f[0].split('/')) if f[0] != '-' else (-1, -1, -1)
    return dict(vol=v, lay=l, sens=s, nPhi=int(f[1]), nEta=int(f[2]), nRDO=int(f[3]),
                lx=float(f[4]), ly=float(f[5]), c00=float(f[6]), c11=float(f[7]))

def load(fn, want="WXQRVYKS"):
    D = {c: {} for c in want}
    D['V'] = {}; D['Y'] = collections.defaultdict(list); D['K'] = collections.defaultdict(list)
    for l in open(fn):
        c = l[0]
        if c not in want or l[1] != ' ': continue
        if c == 'V':
            f = l.split(); D['V'][(f[1], f[2])] = tuple(float(x) for x in f[3:10]); continue
        if c == 'S':
            f = l.split(); D['S'][(f[1], f[2], f[3])] = (float(f[4]), float(f[5]), int(f[6]), int(f[7]), int(f[8])); continue
        if c == 'K':
            f = l.split(); D['K'][(f[1], f[2], f[3])].append((int(f[4]), int(f[5]), int(f[6]), int(f[7]))); continue
        a, b = l.split('|', 1); f = a.split(); k = (f[1], f[2], f[3])
        if c == 'W':
            D['W'][k] = [[pixtok(t) for t in sp.split(',')] for sp in b.split()]
        elif c == 'X':
            D['X'][k] = [tuple(float(x) for x in sp.split(',')) for sp in b.split()]
        elif c == 'Q':
            D['Q'][k] = (int(f[4]), float(f[5]), [[int(u) for u in sp.split(',')] for sp in b.split()])
        elif c == 'R':
            recs = []
            for e in b.split():
                x = e.split(':')
                recs.append(dict(j=int(x[0]), nPass=int(x[1]), rank=int(x[2]), chi2=float(x[3]), dim=int(x[6]),
                                 r0=float(x[7]), r1=float(x[8]), V00=float(x[9]), V11=float(x[11]), P00=float(x[12]), P11=float(x[14])))
            D['R'][k] = recs
        elif c == 'Y':
            sel = int(f[4]); st_ = []
            for e in b.split():
                x = e.split(':')
                d = pixtok(':'.join(x[:8]))
                d.update(p0=float(x[8]), p1=float(x[9]), C00=float(x[10]), C11=float(x[11]),
                         dx=float(x[12]), dy=float(x[13]), dz=float(x[14]), truth=int(x[15]), flag=x[16], chi2=float(x[17]))
                st_.append(d)
            D['Y'][k].append((sel, st_))
    return D

def width(v):
    if not v: return float('nan'), float('nan')
    m = st.median(v); return 1.4826 * st.median(abs(x - m) for x in v), m

def q(v, f):
    v = sorted(v); return v[int(f * (len(v) - 1))] if v else float('nan')

def pure_uid(Q, k):
    """common truth uid of all seed measurements, else None."""
    if k not in Q: return None
    us = {u for sp in Q[k][2] for u in sp}
    return next(iter(us)) if len(us) == 1 and next(iter(us)) >= 0 else None
