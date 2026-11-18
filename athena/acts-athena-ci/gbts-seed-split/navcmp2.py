#!/usr/bin/env python3
"""nav variants: per pure 5-SP seed attempt (pass 1), does a foreign hit taken on an out-of-bounds module spoil the rest?
usage: navcmp2.py trace.txt"""
import sys, collections, numpy as np
HX = 48.3; HY = {2: 12.1, 4: 12.1, 6: 24.2, 8: 24.2}
C = collections.Counter(); SIG = collections.defaultdict(list)
def flush(a):
    if a is None or not a["pure"] or a["n"] != 5: return
    vis = sorted([v for v in a["V"] if v[0] == 1], key=lambda v: v[1])
    bad = None
    for i, v in enumerate(vis):
        if v[5] and v[3] > 0 and not v[4]: bad = i; break
    g = "foreign hit on outside module" if bad is not None else "no such hit"
    C[(g, "attempts")] += 1; C[(g, "no track")] += a["ntr"] == 0
    later = vis[bad + 1:] if bad is not None else vis
    ins = [v for v in later if not v[5] and v[3] > 0]
    C[(g, "later inside pass")] += len(ins); C[(g, "later inside own")] += sum(v[4] for v in ins)
a = None
for line in open(sys.argv[1]):
    t = line[0]
    if t == "A":
        flush(a); f = line.split(); a = dict(n=int(f[4]), pure=f[6] == "1", ntr=int(f[8]), V=[])
    elif t == "V" and a is not None:
        f = line.split()
        if len(f) < 20: continue
        p, r = int(f[1]), float(f[2]); out = False
        if int(f[15]) == 23:
            lay = int(f[16]); out = max(abs(float(f[18])) - HX, abs(float(f[19])) - HY.get(lay, 24.2)) > 0
            SIG["outside" if out else "inside"].append(float(f[7]))
        a["V"].append((p, r, float(f[2]), int(f[9]), f[11] == "1", out))
flush(a)
for g in ("no such hit", "foreign hit on outside module"):
    n = C[(g, "attempts")]
    print(f"{g:32s} attempts {n:6d}  no track {C[(g,'no track')]/max(n,1):.3f}  later inside visits: own-best {C[(g,'later inside own')]/max(1,C[(g,'later inside pass')]):.3f}")
for k, v in SIG.items(): print(f"sigma(loc1) {k}: median {np.median(v):.2f} mm, 90% {np.percentile(v, 90):.2f} mm")
