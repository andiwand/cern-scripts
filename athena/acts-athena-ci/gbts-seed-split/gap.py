#!/usr/bin/env python3
"""Barrel (|eta| < 0.6, pT > 1 GeV, HS + PU) efficiency of each ACTS variant and its gap to a legacy reference.
usage: gap.py <legacy dir> name=dir ...   (splitsum_pu.pkl in every dir)"""
import sys, pickle, os
def load(d):
    _, t = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    return {k: v[3] is not None for k, v in t.items() if v[1] in ("0.0-0.3", "0.3-0.6")}
L = load(sys.argv[1]); N = len(L)
print(f"legacy eff {100*sum(L.values())/N:.2f}%  N {N}")
for a in sys.argv[2:]:
    n, d = a.split("=", 1); A = load(d)
    g = sum(1 for k in L if L[k] and not A.get(k)); l = sum(1 for k in L if A.get(k) and not L[k])
    print(f"{n:16s} eff {100*sum(A.values())/N:.2f}%  legacy-only {g:4d}  acts-only {l:4d}  gap legacy - acts {100*(g-l)/N:+.2f}%")
