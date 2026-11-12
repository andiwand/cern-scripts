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
TYPE = {0: 'pixel', 1: 'strip'}
