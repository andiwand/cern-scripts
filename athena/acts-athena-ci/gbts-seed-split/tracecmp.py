#!/usr/bin/env python3
"""Seeds whose full attempt failed and a sub-seed retry succeeded: what differs at the first strip layers.
usage: tracecmp.py <trace.txt of a retry run>"""
import sys, collections, statistics as st
sys.argv += ["--n", "5"]
exec(open(__file__.replace("tracecmp.py", "tracean.py")).read().split("C = collections.Counter()")[0].replace("fn = sys.argv[1]", "fn = sys.argv[1]"))
by = collections.defaultdict(dict)
for a in attempts():
    if a["n"] + (a["att"] > 0) != 5 or not a["pure"]: continue
    by[(a["ev"], a["seed"])][a["att"]] = a
def strip_first(a, pass_=1):
    """own-hit chi2/cut and residual/sigma at the first two strip radii visited in pass 1"""
    out = []
    for v in a["V"]:
        if v["p"] != pass_ or v["r"] < 330: continue
        out.append(v)
    return out
G = collections.Counter(); R = collections.defaultdict(list)
for k, d in by.items():
    if 0 not in d or d[0]["ntr"] > 0: continue
    rec = [x for x in (1, 2) if x in d and d[x]["ntr"] > 0]
    G["full fails"] += 1
    if not rec: G["  no child recovers"] += 1; continue
    G[f"  recovered by child {rec[0]} ({'without L0' if rec[0]==1 else 'without middle'})"] += 1
    c = d[rec[0]]
    for tag, a in (("full", d[0]), ("child", c)):
        sv = [v for v in strip_first(a) if v["pchi"] >= 0]
        first = min(sv, key=lambda v: v["r"]) if sv else None
        if first:
            R[(tag, "own hit chi2/cut at first strip surface with own hit")].append(first["pchi"] / first["cut"])
            R[(tag, "|res0|/sigma0 there")].append(abs(first["pr0"]) / max(first["s0"], 1e-6))
            R[(tag, "sigma0 [mm] there")].append(first["s0"])
        sp = [v for v in a["V"] if v["p"] == 1 and v["r"] < 330]
        R[(tag, "pixel visits (non-forced)")].append(len(sp))
for k, v in G.items(): print(f"{k:45s} {v}")
for k, v in sorted(R.items(), key=lambda x: (x[0][1], x[0][0])):
    v = sorted(v); print(f"  {k[1]:52s} {k[0]:5s} n={len(v):4d} median {st.median(v):8.3f}  p25 {v[len(v)//4]:8.3f}  p75 {v[3*len(v)//4]:8.3f}")
