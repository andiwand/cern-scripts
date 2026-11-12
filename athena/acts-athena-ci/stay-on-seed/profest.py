#!/usr/bin/env python3
"""Inclusive samples under the seed parameter estimation, per key frame. usage: profest.py a/collapsed.collapsed b/collapsed.collapsed"""
import sys, collections
KEYS = ["estimateTrackParamsFromAllSpacePoints", "Acts::estimateTrackParamsFromSpacePoints", "fitCircleTaubin", "estimateTrackParamsFromSeed",
        "propagateToSurface", "estimateTrackParamCovariance", "operator new", "malloc", "free", "__pow", "pow", "atan2", "getField", "SelfAdjoint", "calibrateStrip", "intersect"]
res = []
for fn in sys.argv[1:]:
    C = collections.Counter(); tot = 0; child = collections.Counter(); leaf = collections.Counter()
    for l in open(fn):
        n, st = l.rstrip("\n").split(" ", 1); n = int(n); fr = st.split(";")
        i = next((i for i, f in enumerate(fr) if "TrackParamsEstimation" in f), None)
        if i is None: continue
        tot += n; below = fr[i:]
        leaf[below[-1][:70]] += n
        for k in KEYS:
            if any(k in f for f in below): C[k] += n
    res.append((tot, C, leaf))
print("total estimation samples:", [r[0] for r in res])
for k in KEYS: print(f"{k:45s}" + "".join(f"{r[1][k]:8d}" for r in res))
L = set(k for r in res for k, _ in r[2].most_common(14))
print("\nleaves")
for k in sorted(L, key=lambda k: -res[-1][2][k]): print("".join(f"{r[2][k]:7d}" for r in res), k)
