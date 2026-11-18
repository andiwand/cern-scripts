#!/usr/bin/env python3
"""Particles behind pure 5-SP GBTS seeds at |eta| < 0.6: found by ACTS and by legacy tracking, split by whether the
particle leaves >= 9 own clusters (distinct surfaces) and whether all its pure seeds failed in the CKF.
Needs the splitsum caches: run `splitsum.py --pu acts=<acts dir> legacy=<legacy dir>` first.
usage: legacycmp.py <trace.txt> <acts dir> <legacy dir>"""
import sys, os, pickle, collections
trace, dA, dL = sys.argv[1:4]
sys.argv = ["deepdive.py", trace]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepdive.py")).read().split("def later(a):")[0])

def load(d):
    _, truth = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    idx = collections.defaultdict(list)
    for (ev, uid, pt, eta), v in truth.items(): idx[(ev, uid)].append((pt, eta, v[3] is not None))
    return idx
A, L = load(dA), load(dL)
def found(idx, ev, uid, pt, eta):
    c = [f for p, e, f in idx.get((ev, uid), []) if abs(p - pt) < 1. and abs(e - eta) < 1e-3]
    return c[0] if c else None

P = {}
for a in attempts():
    if a["n"] != 5 or not a["pure"] or a["att"] != 0 or a["T"] is None or a["T"]["pt"] < 1.0: continue
    T = a["T"]; k = (a["ev"], a["uid"])
    p = P.setdefault(k, dict(pt=T["pt"] * 1000., eta=T["eta"], ok=False, nsurf=0))
    p["ok"] |= a["ntr"] > 0
    p["nsurf"] = max(p["nsurf"], len({h["geo"] for h in a["H"]}))
C = collections.Counter(); miss = 0
for (ev, uid), p in P.items():
    fa, fl = found(A, ev, uid, p["pt"], p["eta"]), found(L, ev, uid, p["pt"], p["eta"])
    if fa is None or fl is None: miss += 1; continue
    g = ("seed ok" if p["ok"] else "all seeds fail", ">= 9 clusters" if p["nsurf"] >= 9 else "< 9 clusters")
    C[g + ("n",)] += 1; C[g + ("acts",)] += fa; C[g + ("legacy",)] += fl
    C[g + ("legacy only",)] += fl and not fa; C[g + ("acts only",)] += fa and not fl
print(f"{trace}: particles pT > 1 GeV behind pure 5-SP seeds: {len(P)}, not joined to the AOD truth: {miss}")
print(f"{'':16s} {'':14s} {'particles':>9s} {'ACTS found':>11s} {'legacy found':>13s} {'legacy only':>12s} {'ACTS only':>10s}")
for s in ("seed ok", "all seeds fail"):
    for r in (">= 9 clusters", "< 9 clusters"):
        n = C[(s, r, "n")]
        if not n: continue
        pc = lambda x: f"{C[(s, r, x)]:5d} {100*C[(s, r, x)]/n:5.1f}%"
        print(f"{s:16s} {r:14s} {n:9d} {pc('acts'):>11s} {pc('legacy'):>13s} {pc('legacy only'):>12s} {pc('acts only'):>10s}")

# legacy tracks of the particles only legacy finds: holes and hits
def best(d):
    _, truth = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    idx = collections.defaultdict(list)
    for (ev, uid, pt, eta), v in truth.items(): idx[(ev, uid)].append((pt, eta, v[3]))
    return idx
BL = best(dL); H = collections.Counter()
for (ev, uid), p in P.items():
    if p["ok"]: continue
    fa = found(A, ev, uid, p["pt"], p["eta"]); fl = found(L, ev, uid, p["pt"], p["eta"])
    if not (fl and not fa): continue
    q = [b for pt, e, b in BL[(ev, uid)] if abs(pt - p["pt"]) < 1. and abs(e - p["eta"]) < 1e-3][0]
    r = ">= 9 clusters" if p["nsurf"] >= 9 else "< 9 clusters"
    H[(r, "n")] += 1; H[(r, f"holes {min(q[2], 3)}")] += 1; H[(r, "hits <= 9")] += q[1] <= 9; H[(r, "prob < 0.9")] += q[0] < 0.9
print("legacy-only particles of failing pure seeds, their legacy track:")
for r in (">= 9 clusters", "< 9 clusters"):
    n = H[(r, "n")]
    print(f"   {r:14s} n={n:4d}  holes 0/1/2/3+: " + " / ".join(f"{100*H[(r, f'holes {h}')]/max(1,n):.0f}%" for h in range(4))
          + f"  hits <= 9: {100*H[(r, 'hits <= 9')]/max(1,n):.0f}%  match prob < 0.9: {100*H[(r, 'prob < 0.9')]/max(1,n):.0f}%")
