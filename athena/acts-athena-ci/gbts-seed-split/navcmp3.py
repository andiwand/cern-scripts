#!/usr/bin/env python3
"""Same seeds, baseline vs nav variant: outcome of the seeds where the variant takes a foreign hit on an out-of-bounds
module, and of the rest. Also: per lost seed, the first difference. usage: navcmp3.py base_trace nav_trace"""
import sys, collections
HX = 48.3; HY = {2: 12.1, 4: 12.1, 6: 24.2, 8: 24.2}
def read(fn, want_out):
    R = {}; a = None
    for line in open(fn):
        if line[0] == "A":
            f = line.split()
            a = None
            if f[3] != "0" or f[4] != "5" or f[6] != "1": continue
            a = R[(int(f[1]), int(f[2]))] = dict(ntr=int(f[8]), fo=False, oo=False, nout=0)
        elif line[0] == "V" and a is not None and want_out:
            f = line.split()
            if len(f) < 20 or f[1] != "1" or f[15] != "23": continue
            lay = int(f[16])
            if max(abs(float(f[18])) - HX, abs(float(f[19])) - HY.get(lay, 24.2)) > 0:
                a["nout"] += 1
                if int(f[9]) > 0: a["fo" if f[11] != "1" else "oo"] = True
    return R
B = read(sys.argv[1], False); N = read(sys.argv[2], True)
C = collections.Counter()
for k, n in N.items():
    b = B.get(k)
    if b is None: C["unpaired"] += 1; continue
    g = "foreign hit on outside module" if n["fo"] else "own hit on outside module" if n["oo"] else "outside visit, no hit" if n["nout"] else "no outside visit"
    C[(g, "n")] += 1; C[(g, "base ok")] += b["ntr"] > 0; C[(g, "nav ok")] += n["ntr"] > 0
    C[(g, "lost")] += b["ntr"] > 0 and n["ntr"] == 0; C[(g, "gained")] += b["ntr"] == 0 and n["ntr"] > 0
print(f"unpaired {C['unpaired']}")
print(f"{'':32s} {'seeds':>7s} {'base no track':>14s} {'nav no track':>13s} {'lost':>6s} {'gained':>7s}")
for g in ("no outside visit", "outside visit, no hit", "own hit on outside module", "foreign hit on outside module"):
    n = C[(g, "n")]
    print(f"{g:32s} {n:7d} {1-C[(g,'base ok')]/max(n,1):14.3f} {1-C[(g,'nav ok')]/max(n,1):13.3f} {C[(g,'lost')]:6d} {C[(g,'gained')]:7d}")
