#!/usr/bin/env python3
"""Classify why a pure-seed CKF attempt found no track (pass-1 drop, longest branch).
usage: failclass.py <trace.txt> [--recoverable]   (--recoverable: only full attempts a retry recovered; needs a retry trace)"""
import sys, collections
fn = sys.argv[1]; REC = "--recoverable" in sys.argv
sys.argv = ["x", fn, "--n", "5"]
exec(open(__file__.replace("failclass.py", "tracean.py")).read().split("C = collections.Counter()")[0])
by = collections.defaultdict(dict)
for a in attempts():
    if a["n"] + (a["att"] > 0) != 5 or not a["pure"]: continue
    by[(a["ev"], a["seed"])][a["att"]] = a
def vis(a, s):
    return [v for v in a["V"] if v["p"] == 1 and abs(v["r"] - s["r"]) < 0.5 and abs(v["z"] - s["z"]) < 0.5]
def classify(a):
    drops = [s for s in a["S"] if s["p"] == 1 and s["res"] == 1]
    if not drops: return "no pass-1 drop (lost after the CKF)"
    b = max(drops, key=lambda s: (s["nm"], -s["nh"]))
    st_ = list(reversed(b["states"]))   # inner -> outer
    own_strip = [v for v in a["V"] if v["p"] == 1 and v["r"] > 330 and v["pchi"] >= 0]
    if not own_strip: return "no own strip hit on any visited surface (interaction / out of acceptance)"
    for s in st_:
        if s["type"] == 0 and s["isP"] == 0 and s["r"] > 330:
            vs = vis(a, s); own = [v["pchi"] / v["cut"] for v in vs if v["pchi"] >= 0]
            if own and min(own) < 1: return "foreign hit picked, own hit also within the cut"
            if own: return "foreign hit picked, own hit outside the cut"
            return "foreign hit picked, own hit not on that surface"
        if s["type"] == 2:
            vs = vis(a, s); own = [v["pchi"] / v["cut"] for v in vs if v["pchi"] >= 0]
            if own:
                x = min(own); return "hole, own hit at " + ("1-2x" if x < 2 else "2-5x" if x < 5 else ">5x") + " cut"
            holes = [h for h in st_ if h["type"] == 2]
            if len(holes) >= 2 and abs(holes[1]["r"] - holes[0]["r"]) < 12 and s is holes[0]: return "both sides of one strip module missed (2 holes), no own hit there"
            return "hole, no own hit on that surface"
    return "other"
C = collections.Counter(); N = 0
for k, d in by.items():
    if 0 not in d or d[0]["ntr"] > 0: continue
    if REC and not any(x in d and d[x]["ntr"] > 0 for x in (1, 2)): continue
    N += 1; C[classify(d[0])] += 1
print(f"{fn}: {'recoverable ' if REC else ''}failing pure 5-SP seeds: {N}")
for k, v in C.most_common(): print(f"  {v:6d} {100*v/N:5.1f}%  {k}")
