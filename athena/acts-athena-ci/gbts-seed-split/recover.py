#!/usr/bin/env python3
"""Of the particles legacy finds and ACTS (baseline) loses, behind pure 5-SP seeds with >= 9 own clusters at |eta|<0.6:
how many does each ACTS variant find? Also how many baseline-found ones each variant loses.
Needs splitsum caches (splitsum.py --pu ...) in every dir.
usage: recover.py <baseline trace> <baseline dir> <legacy dir> name=dir ..."""
import sys, os, pickle, collections
trace, dA, dL = sys.argv[1:4]; vs = [a.split("=", 1) for a in sys.argv[4:]]
sys.argv = ["deepdive.py", trace]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepdive.py")).read().split("def later(a):")[0])
def load(d):
    _, truth = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    idx = collections.defaultdict(list)
    for (ev, uid, pt, eta), v in truth.items(): idx[(ev, uid)].append((pt, eta, v[3] is not None))
    return idx
def found(idx, ev, uid, pt, eta):
    c = [f for p, e, f in idx.get((ev, uid), []) if abs(p - pt) < 1. and abs(e - eta) < 1e-3]
    return c[0] if c else None
A, L = load(dA), load(dL); V = [(n, load(d)) for n, d in vs]
P = {}
for a in attempts():
    if a["n"] != 5 or not a["pure"] or a["att"] != 0 or a["T"] is None or a["T"]["pt"] < 1.0: continue
    k = (a["ev"], a["uid"]); T = a["T"]
    p = P.setdefault(k, dict(pt=T["pt"] * 1000., eta=T["eta"], ok=False, ns=0))
    p["ok"] |= a["ntr"] > 0; p["ns"] = max(p["ns"], len({h["geo"] for h in a["H"]}))
C = collections.Counter()
for (ev, uid), p in P.items():
    fa, fl = found(A, ev, uid, p["pt"], p["eta"]), found(L, ev, uid, p["pt"], p["eta"])
    if fa is None or fl is None: continue
    tgt = (not p["ok"]) and p["ns"] >= 9 and fl and not fa
    C["target"] += tgt; C["base found"] += fa
    for n, idx in V:
        f = found(idx, ev, uid, p["pt"], p["eta"])
        if tgt and f: C[(n, "recovered")] += 1
        if fa and f is False: C[(n, "lost")] += 1
        if not fa and f: C[(n, "gained")] += 1
print(f"legacy-only target particles: {C['target']}; baseline-found particles behind pure 5-SP seeds: {C['base found']}")
for n, _ in V:
    print(f"   {n:16s} target recovered {C[(n, 'recovered')]:4d} ({100*C[(n, 'recovered')]/max(1, C['target']):4.1f}%)   all: gained {C[(n, 'gained')]:4d} lost {C[(n, 'lost')]:4d}")
