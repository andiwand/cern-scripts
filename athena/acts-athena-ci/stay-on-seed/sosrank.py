#!/usr/bin/env python3
"""Selector rank of seed hits (forcing off). usage: sosrank.py <on/sos.txt> <off/sos.txt>"""
import sys, collections
sys.argv_s = sys.argv; sys.argv = sys.argv[:1]
from sosana_lib import load, best
sys.argv = sys.argv_s
A = load(sys.argv[1]); B = load(sys.argv[2])
R = {}
for l in open(sys.argv[2]):
    if l[0] != 'R': continue
    a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
    R[k] = [tuple(float(x) for x in e.split(':')) for e in b.split()]
SA, TA = A; SB, TB = B
for ty in (0, 1):
    pure = [k for k in SB if k[1] == ty and SB[k]['uid'] >= 0 and k in SA]
    lost = [k for k in pure if best(TA.get(k, [])) and not best(TB.get(k, []))]
    both = [k for k in pure if best(TA.get(k, [])) and best(TB.get(k, []))]
    for lbl, ks in (("lost w/o forcing", lost), ("found both", both)):
        c = collections.Counter(); where = collections.Counter(); ratio = []; npass = []
        for k in ks:
            recs = [r for r in R.get(k, []) if r[0] > 0]   # skip the start SP
            bad = [r for r in recs if r[2] > 0]
            if not recs: c["no seed surface visited"] += 1
            elif bad:
                c["seed hit outranked on >=1 surface"] += 1; r = bad[0]
                where["SP%d" % min(int(r[0]), 3)] += 1; ratio.append(r[3] / max(r[4], 1e-6)); npass.append(r[1])
                if r[3] >= r[5]: c["  ... and seed hit above 7sigma there"] += 1
            elif any(r[3] >= r[5] for r in recs): c["seed hit best but above 7sigma"] += 1
            else: c["seed hit best and inside cut everywhere"] += 1
        print(f"type {ty} {lbl:18s} n={len(ks)}")
        for x, n in c.most_common(): print(f"   {n:7d} ({n/max(1,len(ks)):.3f})  {x}")
        if where: print("     first outranked at:", dict(sorted(where.items())), " median seedChi2/bestChi2", sorted(ratio)[len(ratio)//2] if ratio else "-", " median candidates passing", sorted(npass)[len(npass)//2] if npass else "-")
