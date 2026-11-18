#!/usr/bin/env python3
"""Is a failing pure seed reconstructible? Own clusters of the particle (before its truth end vertex) vs minClusters = 9,
and the longest branch the CKF built. usage: ownclusters.py <trace.txt>"""
import sys, collections
src = open(__file__.replace("ownclusters.py", "deepdive.py")).read()
exec(src.split("def later(a):")[0])
C = collections.Counter(); N = collections.Counter(); B = collections.Counter()
for a in attempts():
    if a["n"] != 5 or not a["pure"] or a["att"] != 0 or a["T"] is None: continue
    ok = a["ntr"] > 0; r = a["T"]["endR"]
    grp = "end < 420" if 0 < r < 420 else "end 420-600" if 0 < r < 600 else "no end < 600"
    # distinct surfaces with an own cluster ~ what one track can collect
    nsurf = len({h["geo"] for h in a["H"]})
    npix = len({h["geo"] for h in a["H"] if not h["strip"]})
    rec = nsurf >= 9
    C[(grp, ok, rec)] += 1
    if not ok: N[(grp, min(nsurf, 12))] += 1
    if not ok and rec:
        drops = [s for s in a["S"] if s["p"] == 1 and s["res"] == 1]
        nm = max((s["nm"] for s in drops), default=-1)
        B[(grp, "longest dropped branch nMeas " + ("< 9" if nm < 9 else ">= 9"))] += 1
for grp in ["end < 420", "end 420-600", "no end < 600"]:
    f = C[(grp, False, True)] + C[(grp, False, False)]; o = C[(grp, True, True)] + C[(grp, True, False)]
    print(f"{grp:13s}: fail {f:5d}, of which >= 9 own surfaces {C[(grp, False, True)]:5d} ({100*C[(grp, False, True)]/max(1,f):5.1f}%) | "
          f"ok {o:5d}, of which < 9 own surfaces {C[(grp, True, False)]:5d}")
print("failing: own surfaces (pixel + strip, distinct) per group:")
for grp in ["end < 420", "end 420-600", "no end < 600"]:
    print(f"   {grp:13s} " + " ".join(f"{n}:{N[(grp, n)]}" for n in range(0, 13)))
print("failing with >= 9 own surfaces:")
for k, v in sorted(B.items()): print(f"   {k[0]:13s} {k[1]:40s} {v}")
