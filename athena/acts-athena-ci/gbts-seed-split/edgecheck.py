#!/usr/bin/env python3
"""Where on the module are the predictions of strip holes? Distance of the predicted (loc0, loc1) to the module edge.
usage: edgecheck.py <trace.txt>"""
import sys, collections, numpy as np
sys.argv = [sys.argv[0], sys.argv[1]]
src = open(__file__.replace("edgecheck.py", "deepdive.py")).read()
exec(src.split("cls = lambda a:")[0].split("def later(a):")[0])
# half sizes per (vol, lay) from the extent of all predictions on visited strip surfaces
ext = collections.defaultdict(lambda: [0., 0.])
rows = []
for a in attempts():
    if a["n"] != NSP or not a["pure"] or a["att"] != 0 or a["T"] is None: continue
    ok = a["ntr"] > 0
    for v in a["V"]:
        if v["p"] != 1 or v["r"] < 330 or "loc0" not in v: continue
        e = ext[(v["vol"], v["lay"])]; e[0] = max(e[0], abs(v["loc0"])); e[1] = max(e[1], abs(v["loc1"]))
    rows.append(a)
print("prediction extent (≈ half sizes) per strip layer:", {k: [round(x, 1) for x in v] for k, v in sorted(ext.items())})
D = collections.defaultdict(list)
for a in rows:
    ok = a["ntr"] > 0
    own = {h["geo"] for h in a["H"] if h["strip"]}
    for v in a["V"]:
        if v["p"] != 1 or v["r"] < 330 or "loc0" not in v: continue
        hx, hy = ext[(v["vol"], v["lay"])]
        d = min(hx - abs(v["loc0"]), hy - abs(v["loc1"]))
        kind = "own cluster on surface" if v["geo"] in own else "no own cluster, particle has one on the same layer" if any(
            (g >> 56, (g >> 36) & 0xfff) == (v["vol"], v["lay"]) for g in own) else "no own cluster on the layer"
        D[(ok, kind)].append(d)
for (ok, kind), d in sorted(D.items()):
    d = np.array(d)
    print(f"{'ok  ' if ok else 'fail'} {kind:52s} n={len(d):7d} edge dist < 0.5 mm {100*np.mean(d<0.5):5.1f}%  < 1 mm {100*np.mean(d<1):5.1f}%  < 2 mm {100*np.mean(d<2):5.1f}%")
