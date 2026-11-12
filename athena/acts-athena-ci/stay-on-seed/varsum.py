#!/usr/bin/env python3
"""Efficiency / fakes / duplicates per variant AOD, with paired gains vs forcing on and off.
usage: varsum.py <name=AOD> ...   (first two: on, off)"""
import sys, pickle, os
sys.argv_s = sys.argv; sys.argv = sys.argv[:1]
from truthlib import scan
sys.argv = sys.argv_s
res = {}
for a in sys.argv[1:]:
    n, f = a.split('=', 1)
    cache = f + ".truthsum.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(f):
        res[n] = pickle.load(open(cache, 'rb'))
    else:
        res[n] = scan(f); pickle.dump(res[n], open(cache, 'wb'))
names = list(res)
def found(T, tag): return {k for k, v in T.items() if v[2] and v[3] == tag}
print(f"{'variant':14s} {'tracks':>8s} {'eff HS':>8s} {'eff PU':>8s} {'fake':>7s} {'dupl':>6s} | {'HS vs on':>10s} {'PU vs on':>12s} | {'HS vs off':>10s} {'PU vs off':>12s}")
for n in names:
    C, T = res[n]
    row = f"{n:14s} {C['tracks']:8d} {C['truth HS pT>1 matched']/C['truth HS pT>1']*100:7.2f}% {C['truth PU pT>1 matched']/C['truth PU pT>1']*100:7.2f}% {C['unlinked']/C['tracks']*100:6.2f}% {C['particles w/ >1 (duplicate)']:6d} |"
    for ref in names[:2]:
        Tr = res[ref][1]
        for tag in ("HS", "PU"):
            a, b = found(T, tag), found(Tr, tag)
            row += f" {'+'+str(len(a-b))+'/-'+str(len(b-a)):>11s}"
        row += " |"
    print(row)
